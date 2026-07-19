"""Shape2D calibration prototype (Task 13, Phase A completion gate).

Measures every field of the frozen 15-cell manifest (`EXPECTED_CELL_IDS` in
`cwm.continuous.calibration`) that the strict validator
`validate_calibration_artifact` requires: an offset achieving `rarity_target`
per cell (rarity = fraction of rollouts containing a contact, Wilson CI on
an independent `cal_seed_stream`), per-cell `grid_delta_256_512` (grid-
quadrature convergence of the shape's own area estimate, 256 vs 512), a
`play_cost_blind` from truth/blind/random EPISODES (not a single `mpc.plan`
call, via `harness.play_cost`), a global `delta` (median normal-bracket
width -- the smallest along-normal displacement at which `shape.contains`
flips reliably, over probes pooled across every cell), `frac_planner_outside_
box` (fraction of truth-planner-visited states that leave `box`, pooled
across cells), a `repaired_threshold` sourced from the truth oracle's own
full-arm grid-quantization error (the noise floor a synthesized model's
disagreement is judged against in Phase B), and `sufficiency` left
deliberately uncertified (`tau_s: None` -- Phase A defers S to Phase B).

No Azure/LLM calls anywhere: every quantity is measured directly against the
truth `ShapeField2D` env and its `blind_of()` counterpart.

`--quick` shrinks every rollout/episode/search count so the script runs in
seconds and fills the full schema/manifest -- a SMOKE test only; it does not
need to (and typically will not) satisfy the rarity/play_cost tolerances the
strict validator enforces. Run without `--quick` (a few minutes) to produce
the artifact `validate_calibration_artifact` must accept cleanly.

Run: PYTHONPATH=src python scripts/calibrate_shape2d.py [--quick] [--out PATH]
"""
import argparse
import json
import math
import random
import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cwm.continuous import mpc, harness  # noqa: E402
from cwm.continuous.envs import ShapeField2D, blind_of  # noqa: E402
from cwm.continuous.shapes import (  # noqa: E402
    HalfPlane, Parabola, Strip, Wedge, RegularPolygon, Circle,
)
from cwm.continuous.metrics_geom import stratified_probes, disagreement_scores  # noqa: E402
from cwm.continuous.calibration import EXPECTED_CELL_IDS  # noqa: E402

BOX = ((-8.0, 14.0), (-6.0, 6.0))
GRID_N = 256
RARITY_TARGET = 0.15
RARITY_TOL = 0.05
FRAC_OUTSIDE_BOX_BOUND = 0.05
# Two independent seed streams: CAL seeds the rarity/offset-search rollouts,
# VAL seeds the play-cost episodes and the outside-box diagnostic, so the
# rarity calibration and the play-cost/box measurements never share a seed.
CAL_SEED_STREAM = 10_000
VAL_SEED_STREAM = 90_000


def _stable_offset(cell_id: str) -> int:
    """Deterministic per-cell seed offset, stable across processes/PYTHONHASHSEED
    (unlike `hash()`, which is randomized per-process for strings)."""
    return zlib.crc32(cell_id.encode()) % 100_000


def _env(shape):
    return ShapeField2D(shape=shape)


# --- per-cell shape factories: offset -> Shape --------------------------------
# `offset` is each family's rarity knob (the position of its near boundary
# along +x, mirroring the CartWall x_wall knob this instrument is modeled on:
# larger offset -> farther from the start -> rarer contact).
def _halfplane(offset):
    return HalfPlane(c=offset)


def _parabola(R):
    def f(offset):
        return Parabola(c=offset, R=R)
    return f


def _strip(offset):
    return Strip(c=offset, w=1.0)


def _wedge(offset):
    return Wedge(apex=(offset, 0.0), half_angle=math.pi / 6)


def _polygon(k, orient):
    def f(offset):
        return RegularPolygon(cx=offset, cy=0.0, radius=1.5, k=k, orient=orient)
    return f


def _circle(offset):
    return Circle(cx=offset, cy=0.0, R=1.5)


_FACE_ORIENT = math.pi  # a face normal points at angle pi -> faces -x (the approach side)


def _vertex_orient(k):
    return math.pi * (k - 1) / k  # a vertex sits at angle pi -> faces -x


_BRACKET = (1.0, 9.0)  # shared offset search bracket: box x in [-8, 14]

CELL_SPECS = {
    "anchor_halfplane":     _halfplane,
    "curv_parabola_R8":     _parabola(8.0),
    "curv_parabola_R4":     _parabola(4.0),
    "curv_parabola_R2":     _parabola(2.0),
    "curv_parabola_R1":     _parabola(1.0),
    "comp_strip":           _strip,
    "comp_wedge":           _wedge,
    "comp_triangle_face":   _polygon(3, _FACE_ORIENT),
    "comp_triangle_vertex": _polygon(3, _vertex_orient(3)),
    "comp_square_face":     _polygon(4, _FACE_ORIENT),
    "comp_square_vertex":   _polygon(4, _vertex_orient(4)),
    "comp_hexagon_face":    _polygon(6, _FACE_ORIENT),
    "comp_hexagon_vertex":  _polygon(6, _vertex_orient(6)),
    "contrast_parabola":    _parabola(4.0),
    "contrast_circle":      _circle,
}
assert set(CELL_SPECS) == EXPECTED_CELL_IDS, "CELL_SPECS must cover the frozen manifest exactly"


# --- rarity: fraction of rollouts containing a contact, Wilson CI ------------
def _rarity_point(shape_factory, offset, n_rollouts, seed):
    return harness.rarity(_env(shape_factory(offset)), n_rollouts=n_rollouts, seed=seed)


def _search_offset(shape_factory, lo, hi, target, n_rollouts, seed, max_iters):
    """Bisection for the offset whose rarity crosses `target`, on the SAME
    (seed, n_rollouts) sample the caller then reports rarity against. Rarity
    is a non-increasing step function of offset for a fixed sample (each
    rollout's contact flips at a discrete offset, and pushing the shape
    farther in +x can only remove contacts), so pure bisection converges the
    bracket onto the crossing -- NO early exit on a single noisy estimate, and
    NO best-error tracking (that was the bug: it could return a coarse early
    midpoint that looked on-target on one sample but missed on another). The
    returned midpoint, re-measured on the same sample, lands within one step
    (1/n_rollouts) of the target crossing -- comfortably inside `rarity_tol`.
    """
    for _ in range(max_iters):
        mid = 0.5 * (lo + hi)
        r, _, _ = _rarity_point(shape_factory, mid, n_rollouts, seed)
        if r > target:
            lo = mid  # too common -> push the shape farther away (+x)
        else:
            hi = mid  # too rare -> pull it closer
    return 0.5 * (lo + hi)


# --- play_cost_blind: truth/blind/random EPISODES, not one mpc.plan call ------
def _play_cost_blind(shape, offset, n_episodes, seed, horizon, n_samples, block):
    truth = _env(shape)
    blind = blind_of(truth)
    pc = harness.play_cost(truth, blind, n_episodes=n_episodes, seed=seed,
                           horizon=horizon, n_samples=n_samples, block=block)
    return pc["play_cost"]


# --- grid_delta_256_512: grid-quadrature convergence of the shape's own area -
def _area_frac(shape, box, grid_n):
    (xmin, xmax), (ymin, ymax) = box
    xs = np.linspace(xmin, xmax, grid_n)
    ys = np.linspace(ymin, ymax, grid_n)
    cnt = 0
    for x in xs:
        for y in ys:
            if shape.contains((float(x), float(y))):
                cnt += 1
    return cnt / (grid_n * grid_n)


def _grid_delta(shape, box):
    return abs(_area_frac(shape, box, 256) - _area_frac(shape, box, 512))


# --- delta: median normal-bracket width, pooled across every cell's shape ----
# On EXACT continuous geometry, any d > 0 flips `shape.contains` reliably at a
# true boundary point (the "bracket" shrinks to float noise, not a meaningful
# number) -- the real noise floor a band probe must clear is the GRID
# discretization at `grid_n` used everywhere else in this artifact. So this
# measures the bracket against grid-quantized containment (same construction
# as `_repaired_threshold`'s grid_quantized_step): the smallest half-width at
# which snapping to the nearest of `grid_n` grid points still reads the
# correct side on both the inward and outward displacement.
def _normal_at(shape, p):
    n = shape.normal_or_cone(p)
    if isinstance(n, list):
        sx = sum(c[0] for c in n)
        sy = sum(c[1] for c in n)
        m = math.hypot(sx, sy) or 1.0
        return (sx / m, sy / m)
    return n


def _quantized_contains(shape, xs, ys, grid_n, p):
    i = int(np.clip(np.searchsorted(xs, p[0]), 0, grid_n - 1))
    j = int(np.clip(np.searchsorted(ys, p[1]), 0, grid_n - 1))
    return shape.contains((float(xs[i]), float(ys[j])))


def _min_flip_distance(shape, bp, normal, xs, ys, grid_n, d_max=2.0, iters=30):
    """Smallest d>0 such that displacing `bp` by -d/+d along `normal` and
    snapping to the nearest grid_n-resolution grid point reads (inside,
    outside) -- the minimal normal-bracket half-width a band probe needs to
    clear the grid's own discretization noise at this boundary point."""
    def ok(d):
        inside = (bp[0] - d * normal[0], bp[1] - d * normal[1])
        outside = (bp[0] + d * normal[0], bp[1] + d * normal[1])
        return (_quantized_contains(shape, xs, ys, grid_n, inside)
                and not _quantized_contains(shape, xs, ys, grid_n, outside))
    if not ok(d_max):
        return d_max
    lo, hi = 0.0, d_max
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if ok(mid):
            hi = mid
        else:
            lo = mid
    return hi


def _measure_delta(shapes, box, grid_n, n_probe_per_shape=6):
    xs = np.linspace(box[0][0], box[0][1], grid_n)
    ys = np.linspace(box[1][0], box[1][1], grid_n)
    widths = []
    for shape in shapes:
        for bp in shape.boundary_points(box, n_probe_per_shape):
            normal = _normal_at(shape, bp)
            widths.append(_min_flip_distance(shape, bp, normal, xs, ys, grid_n))
    widths.sort()
    return widths[len(widths) // 2]


# --- frac_planner_outside_box: fraction of truth-planner states leaving box -
def _frac_outside_box(shapes, box, seed, horizon, n_samples, block, n_episodes_per_cell):
    (xmin, xmax), (ymin, ymax) = box
    total = outside = 0
    for i, shape in enumerate(shapes):
        env = _env(shape)
        for e in range(n_episodes_per_cell):
            rng = random.Random(seed + 1000 * i + e)
            s = env.initial_state(rng)
            for _ in range(env.h_episode):
                a = mpc.plan(env, s, rng, horizon=horizon, n_samples=n_samples, block=block)
                s, _, _ = env.step(s, a)
                total += 1
                if not (xmin <= s[0] <= xmax and ymin <= s[1] <= ymax):
                    outside += 1
    return outside / total if total else 0.0


# --- repaired_threshold: truth oracle's own full-arm grid-quantization error -
def _repaired_threshold(anchor_env, box, grid_n, seed):
    rng = random.Random(seed)
    s = anchor_env.initial_state(rng)
    queries = []
    for _ in range(60):
        a = rng.uniform(-anchor_env.a_max, anchor_env.a_max)
        queries.append((s, a))
        s, _, _ = anchor_env.step(s, a)
    probes = stratified_probes(anchor_env, box, n_per=30, rng=rng, band_d=0.1,
                               planner_queries=queries)
    xs = np.linspace(box[0][0], box[0][1], grid_n)
    ys = np.linspace(box[1][0], box[1][1], grid_n)

    def grid_quantized_step(state, action):
        x2, y2, vx2, vy2 = anchor_env._integrate(state, action)
        i = int(np.clip(np.searchsorted(xs, x2), 0, grid_n - 1))
        j = int(np.clip(np.searchsorted(ys, y2), 0, grid_n - 1))
        if anchor_env.shape.contains((float(xs[i]), float(ys[j]))):
            return (state[0], state[1], 0.0, 0.0)
        return (x2, y2, vx2, vy2)

    scores = disagreement_scores(anchor_env, grid_quantized_step, probes)
    band = scores["band"]
    return {
        "band_disagreement": band["disagreement"],
        "fpr": band["fpr"],
        "source": "truth_oracle_fullarm_griderror",
    }


def measure_cell(cell_id, shape_factory, cfg):
    # Search and final rarity share the cal-stream seed/rollouts so the offset
    # is calibrated against the very sample its rarity is reported on (see
    # _search_offset): the reported rarity then lands within 1/n of target,
    # inside rarity_tol. This whole stream is independent of VAL_SEED_STREAM
    # (play-cost / outside-box), which is the independence the brief requires.
    final_seed = CAL_SEED_STREAM + _stable_offset(cell_id)
    offset = _search_offset(shape_factory, _BRACKET[0], _BRACKET[1],
                            RARITY_TARGET, cfg.n_rollouts_final,
                            final_seed, cfg.bisect_iters)
    r, lo_ci, hi_ci = _rarity_point(shape_factory, offset, cfg.n_rollouts_final, final_seed)

    shape = shape_factory(offset)
    pc_seed = VAL_SEED_STREAM + _stable_offset(cell_id)
    pcb = _play_cost_blind(shape, offset, cfg.n_episodes, pc_seed,
                           cfg.horizon, cfg.n_samples, cfg.block)
    gdelta = _grid_delta(shape, BOX)

    cell = {
        "id": cell_id,
        "family": type(shape).__name__,
        "offset": offset,
        "rarity": r,
        "rarity_ci": [lo_ci, hi_ci],
        "n_rollouts": cfg.n_rollouts_final,
        "n_episodes": cfg.n_episodes,
        "play_cost_blind": pcb,
        "grid_delta_256_512": gdelta,
        "provenance": "measured",
    }
    return cell, shape


def build_artifact(cfg):
    cells, shapes = [], []
    anchor_env = None
    for cell_id, factory in CELL_SPECS.items():
        cell, shape = measure_cell(cell_id, factory, cfg)
        cells.append(cell)
        shapes.append(shape)
        if cell_id == "anchor_halfplane":
            anchor_env = _env(shape)

    delta = _measure_delta(shapes, BOX, GRID_N)
    frac_out = _frac_outside_box(shapes, BOX, seed=VAL_SEED_STREAM + 777,
                                 horizon=cfg.horizon, n_samples=cfg.n_samples,
                                 block=cfg.block,
                                 n_episodes_per_cell=cfg.frac_out_episodes)
    repaired_threshold = _repaired_threshold(anchor_env, BOX, GRID_N, seed=CAL_SEED_STREAM + 42)

    return {
        "box": [list(BOX[0]), list(BOX[1])],
        "grid_n": GRID_N,
        "rarity_target": RARITY_TARGET,
        "rarity_tol": RARITY_TOL,
        "frac_planner_outside_box": frac_out,
        "frac_outside_box_bound": FRAC_OUTSIDE_BOX_BOUND,
        "cal_seed_stream": CAL_SEED_STREAM,
        "val_seed_stream": VAL_SEED_STREAM,
        "delta": delta,
        "delta_provenance": "median_normal_bracket",
        "sufficiency": {
            "certified": False,
            "tau_s": None,
            "reason": "conservative version-space upper bound deferred to Phase B",
        },
        "repaired_threshold": repaired_threshold,
        "provenance": {
            "box": "fixed",
            "grid_n": "fixed",
            "rarity_target": "fixed",
            "delta": "measured",
            "repaired_threshold": "truth_oracle_fullarm_griderror",
            "frac_planner_outside_box": "measured",
        },
        "cells": cells,
    }


class _Cfg:
    def __init__(self, bisect_iters, n_rollouts_final,
                n_episodes, horizon, n_samples, block, frac_out_episodes):
        self.bisect_iters = bisect_iters
        self.n_rollouts_final = n_rollouts_final
        self.n_episodes = n_episodes
        self.horizon = horizon
        self.n_samples = n_samples
        self.block = block
        self.frac_out_episodes = frac_out_episodes


QUICK_CFG = _Cfg(bisect_iters=8, n_rollouts_final=30,
                 n_episodes=3, horizon=15, n_samples=20, block=5, frac_out_episodes=1)
FULL_CFG = _Cfg(bisect_iters=18, n_rollouts_final=400,
               n_episodes=16, horizon=40, n_samples=200, block=10, frac_out_episodes=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="smoke test: shrink every count, fill the full schema, "
                         "but do not expect strict validation to pass")
    ap.add_argument("--out", default="results/shape2d_calibration.json")
    args = ap.parse_args()

    cfg = QUICK_CFG if args.quick else FULL_CFG
    artifact = build_artifact(cfg)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
