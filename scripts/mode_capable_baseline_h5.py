"""H5: a learned event-function baseline whose class contains the true mode.

The baseline is intentionally favourable.  It shares the instrument's pinned
off-mode simulator and reward, and learns only the missing event function from
the same transition samples used by synthesis.  Thus an error cannot be blamed
on a weak smooth dynamics model:

* CartWall: learn the hard threshold from contact post-states.
* PatchField2D: infer contact landing points from the pinned integrator, cluster
  separated modes, and fit circular event regions by algebraic least squares.

The emitted artifact separates (i) class expressibility, (ii) induction from a
finite sample, and (iii) exact agreement on realised transitions.  Draw-level
metrics are descriptive; the training seed block is the experimental unit.

Run (full 20-block evidence):
    PYTHONPATH=src .venv/bin/python scripts/mode_capable_baseline_h5.py

Quick deterministic smoke run:
    ... --blocks 2 --skip-play
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys
from dataclasses import dataclass, replace

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cwm.continuous import gate, harness  # noqa: E402
from cwm.continuous.contract import collect_transitions  # noqa: E402
from cwm.continuous.envs import CartWall, PatchField2D  # noqa: E402

SCHEMA_VERSION = 1
OUT = REPO / "results" / "mode_capable_baseline_h5.json"
TRAIN_SEEDS = tuple(10_000 * (i + 1) for i in range(20))
PATCH_ARMS = (("default", None, 40), ("arc120", 120.0, 15),
              ("arc240", 240.0, 15))
PARAM_TOL = 0.10


def cart_contact_rows(transitions: list[dict], off_mode_env: CartWall | None = None) -> list[dict]:
    """Infer contacts from observed disagreement with the known off-mode plant."""
    free = off_mode_env or CartWall(x_wall=None)
    rows = []
    for transition in transitions:
        predicted = free.step(tuple(transition["state"]), transition["action"])[0]
        if tuple(transition["next_state"]) != predicted:
            rows.append(transition)
    return rows


def learn_cart_threshold(transitions: list[dict],
                         off_mode_env: CartWall | None = None) -> float | None:
    """Fit the event x_free >= wall from labelled contact post-states.

    A single noiseless contact identifies CartWall's clamp coordinate.  With no
    contact the event is not identified and this learner returns the mode-absent
    member of its class rather than importing the withheld threshold.
    """
    xs = [float(t["next_state"][0])
          for t in cart_contact_rows(transitions, off_mode_env)]
    return statistics.median(xs) if xs else None


def circle_fit(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Algebraic least-squares fit of x^2+y^2+D*x+E*y+F=0."""
    if len(points) < 3:
        raise ValueError("three contact landings are required")
    p = np.asarray(points, dtype=float)
    a = np.c_[p[:, 0], p[:, 1], np.ones(len(p))]
    if np.linalg.matrix_rank(a) < 3:
        raise ValueError("contact landings are rank deficient")
    b = -(p[:, 0] ** 2 + p[:, 1] ** 2)
    d, e, f = np.linalg.lstsq(a, b, rcond=None)[0]
    cx, cy = -d / 2.0, -e / 2.0
    r2 = cx * cx + cy * cy - f
    if r2 <= 0:
        raise ValueError("non-positive fitted radius")
    return float(cx), float(cy), float(math.sqrt(r2))


def angular_extent(points: list[tuple[float, float]], centre: tuple[float, float]) -> float:
    if len(points) < 2:
        return 0.0
    angles = np.sort(np.mod(np.arctan2(
        [p[1] - centre[1] for p in points],
        [p[0] - centre[0] for p in points]), 2 * np.pi))
    gaps = np.diff(np.r_[angles, angles[0] + 2 * np.pi])
    return float(np.degrees(2 * np.pi - gaps.max()))


def contact_landings(env: PatchField2D, transitions: list[dict]) -> list[tuple[float, float]]:
    """Recover pre-mode landings using only sample fields and the public integrator."""
    landings = []
    for transition in transitions:
        free_next = env._integrate(tuple(transition["state"]), transition["action"])
        if tuple(transition["next_state"]) != free_next:
            landings.append(tuple(free_next[:2]))
    return landings


def cluster_separated_modes(points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Split spatially separated ordered modes without consulting truth centres.

    Within one unit-radius disc, x spans at most two.  The two instrument discs
    are separated by four in x, so a consecutive-x gap greater than 1.5 is a
    pre-specified separation certificate.  Otherwise the evidence supports one
    observed cluster only.
    """
    if not points:
        return []
    ordered = sorted(points)
    if len(ordered) < 2:
        return [ordered]
    gaps = [ordered[i + 1][0] - ordered[i][0] for i in range(len(ordered) - 1)]
    split = int(np.argmax(gaps))
    if gaps[split] <= 1.5:
        return [ordered]
    return [ordered[:split + 1], ordered[split + 1:]]


def learn_patch_regions(env: PatchField2D, transitions: list[dict]) -> tuple[list[tuple[float, float, float]], dict]:
    landings = contact_landings(env, transitions)
    clusters = cluster_separated_modes(landings)
    regions, rejected = [], []
    for pts in clusters:
        try:
            regions.append(circle_fit(pts))
        except ValueError as exc:
            rejected.append({"n": len(pts), "reason": str(exc)})
    regions.sort(key=lambda z: z[0])
    return regions, {
        "n_contacts": len(landings),
        "n_clusters": len(clusters),
        "cluster_sizes": [len(c) for c in clusters],
        "landing_arc_deg": [angular_extent(c, (r[0], r[1]))
                            for c, r in zip(clusters, regions)],
        "rejected_clusters": rejected,
    }


@dataclass
class LearnedPatchEventModel:
    """Known off-mode plant plus learned circular hard-event predicates."""
    base: PatchField2D
    regions: tuple[tuple[float, float, float], ...]

    @property
    def a_max(self):
        return self.base.a_max

    @property
    def h_episode(self):
        return self.base.h_episode

    def step(self, state, action):
        x2, y2, vx2, vy2 = self.base._integrate(state, action)
        hit = any((x2 - cx) ** 2 + (y2 - cy) ** 2 <= radius ** 2
                  for cx, cy, radius in self.regions)
        if hit:
            s2 = self.base._mode_post_state(state, x2, y2)
            return s2, self.base.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.base.reward(s2), False


def transition_metrics(truth, model, transitions: list[dict]) -> dict:
    errors, off_errors = [], []
    for t in transitions:
        err = gate.transition_error(truth, model, tuple(t["state"]), t["action"])
        errors.append(err)
        if not t["contact"]:
            off_errors.append(err)
    return {
        "n_transitions": len(errors),
        "n_off_mode": len(off_errors),
        "exact_transition_fraction": sum(e == 0.0 for e in errors) / len(errors),
        "off_mode_exact_fraction": (sum(e == 0.0 for e in off_errors) / len(off_errors)
                                    if off_errors else None),
        "off_mode_max_error": max(off_errors, default=None),
        "max_error": max(errors, default=None),
    }


def patch_rule_metrics(regions: list[tuple[float, float, float]], truth: PatchField2D) -> dict:
    """Grid classification metrics plus parameter recovery for each ordered mode."""
    tp = tn = fp = fn = 0
    for x in np.linspace(0.0, 10.0, 101):
        for y in np.linspace(-2.0, 2.0, 41):
            actual = truth._inside(float(x), float(y), truth.p1) or \
                truth._inside(float(x), float(y), truth.p2)
            predicted = any((x - cx) ** 2 + (y - cy) ** 2 <= r ** 2
                            for cx, cy, r in regions)
            if actual and predicted:
                tp += 1
            elif actual:
                fn += 1
            elif predicted:
                fp += 1
            else:
                tn += 1
    fits = []
    for i, centre in enumerate((truth.p1, truth.p2)):
        if i < len(regions):
            cx, cy, radius = regions[i]
            ce = math.hypot(cx - centre[0], cy - centre[1])
            re = abs(radius - truth.R)
            fits.append({"mode": i + 1, "centre_error": ce, "radius_error": re,
                         "recovered_at_0.1": ce <= PARAM_TOL and re <= PARAM_TOL})
        else:
            fits.append({"mode": i + 1, "recovered_at_0.1": False,
                         "reason": "no fitted cluster"})
    return {
        "grid_n": tp + tn + fp + fn,
        "intersection_over_union": tp / (tp + fp + fn),
        "balanced_accuracy": 0.5 * (tp / (tp + fn) + tn / (tn + fp)),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "parameter_recovery": fits,
        "both_modes_recovered_at_0.1": all(f["recovered_at_0.1"] for f in fits),
        "near_mode_recovered_at_0.1": fits[0]["recovered_at_0.1"],
    }


def compact_play_cost(truth, model, seed: int) -> dict:
    """One paired episode per seed block; aggregate across blocks, never as iid draws."""
    return harness.play_cost(truth, model, n_episodes=1, seed=seed + 3_000_000,
                             horizon=20, n_samples=40, block=5)


def cart_experiment(skip_play: bool) -> dict:
    truth = CartWall(x_wall=8.0)
    arms = []
    for label, seed in (("wall-free", 10_000), ("wall-containing", 20_000)):
        train = collect_transitions(truth, 40, seed=seed)
        threshold = learn_cart_threshold(train)
        model = replace(truth, x_wall=threshold)
        heldout = collect_transitions(truth, 40, seed=seed + 1_000_000)
        g = gate.run_gate(truth, model, 40, 1e-9, seed=seed + 2_000_000)
        row = {
            "arm": label, "train_seed_block": [seed, seed + 39],
            "n_rollouts": 40,
            "n_contacts": len(cart_contact_rows(train, replace(truth, x_wall=None))),
            "learned_threshold": threshold,
            "mode_rule_recovered_exactly": threshold == truth.x_wall,
            "heldout": transition_metrics(truth, model, heldout),
            "gate_40_eps1e-9": {"passed": g.passed, "n_bad": g.n_bad,
                                "max_error": g.max_err},
        }
        if not skip_play:
            row["planner"] = compact_play_cost(truth, model, seed)
        arms.append(row)
    containing = collect_transitions(truth, 40, seed=20_000)
    sensitivity = []
    for n in (1, 5, 10, 20, 40):
        prefix = containing[:n * truth.h_episode]
        fit = learn_cart_threshold(prefix)
        sensitivity.append({"n_rollouts": n,
                            "n_contacts": len(cart_contact_rows(
                                prefix, replace(truth, x_wall=None))),
                            "threshold_recovered_exactly": fit == truth.x_wall})
    return {
        "truth_threshold": truth.x_wall,
        "hypothesis_class_contains_truth": True,
        "shared_components": ["off-mode integrator", "reward", "mode effect"],
        "learned_component": "hard threshold event function",
        "arms": arms, "contact_count_sensitivity": sensitivity,
    }


def patch_experiment(n_blocks: int, skip_play: bool) -> dict:
    arm_results = {}
    for label, arc, n_rollouts in PATCH_ARMS:
        truth = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), start_arc_deg=arc)
        rows = []
        for seed in TRAIN_SEEDS[:n_blocks]:
            train = collect_transitions(truth, n_rollouts, seed=seed)
            regions, evidence = learn_patch_regions(truth, train)
            model = LearnedPatchEventModel(truth, tuple(regions))
            heldout = collect_transitions(truth, 5, seed=seed + 1_000_000)
            g = gate.run_gate(truth, model, 10, 1e-9, seed=seed + 2_000_000)
            rule = patch_rule_metrics(regions, truth)
            row = {
                "train_seed_block": [seed, seed + n_rollouts - 1],
                "n_rollouts": n_rollouts, "evidence": evidence,
                "learned_regions": [list(r) for r in regions],
                "rule": rule,
                "heldout": transition_metrics(truth, model, heldout),
                "gate_10_eps1e-9": {"passed": g.passed, "n_bad": g.n_bad,
                                    "max_error": g.max_err},
            }
            if not skip_play:
                row["planner"] = compact_play_cost(truth, model, seed)
            rows.append(row)
        near = sum(r["rule"]["near_mode_recovered_at_0.1"] for r in rows)
        both = sum(r["rule"]["both_modes_recovered_at_0.1"] for r in rows)
        play_costs = ([r["planner"]["play_cost"] for r in rows]
                      if not skip_play else [])
        near_arcs = [r["evidence"]["landing_arc_deg"][0] for r in rows
                     if r["evidence"]["landing_arc_deg"]]
        arm_results[label] = {
            "start_arc_deg": arc, "n_rollouts": n_rollouts,
            "n_seed_blocks": len(rows),
            "near_mode_recovered_blocks": near,
            "both_modes_recovered_blocks": both,
            "median_contacts": statistics.median(r["evidence"]["n_contacts"] for r in rows),
            "median_near_landing_arc_deg": statistics.median(near_arcs) if near_arcs else None,
            "median_iou": statistics.median(r["rule"]["intersection_over_union"] for r in rows),
            "gate_pass_blocks": sum(r["gate_10_eps1e-9"]["passed"] for r in rows),
            "float_exact_on_all_heldout_blocks":
                sum(r["heldout"]["exact_transition_fraction"] == 1.0 for r in rows),
            "off_mode_exact_on_all_heldout_blocks":
                sum(r["heldout"]["off_mode_exact_fraction"] == 1.0 for r in rows),
            "median_play_cost": statistics.median(play_costs) if play_costs else None,
            "play_cost_range": [min(play_costs), max(play_costs)] if play_costs else None,
            "play_cost_abs_le_0.05_blocks":
                sum(abs(value) <= 0.05 for value in play_costs) if play_costs else None,
            "rows": rows,
        }
    return {
        "truth_regions": [[3.0, 0.0, 1.0], [7.0, 0.0, 1.0]],
        "hypothesis_class_contains_truth": True,
        "shared_components": ["off-mode integrator", "reward", "freeze effect"],
        "learned_component": "up to two separated circular event functions",
        "parameter_tolerance": PARAM_TOL,
        "arms": arm_results,
    }


def build_result(n_blocks: int = 20, skip_play: bool = False) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "script": "scripts/mode_capable_baseline_h5.py",
        "claim_contract": {
            "label": "measured",
            "experimental_unit": "training seed block",
            "scope": "favourable learned-event baseline with pinned known off-mode plant",
            "expressibility": "both fitted classes contain the instrument truth",
            "finite_evidence_induction": "parameters are estimated only from each block's transitions",
            "float_exactness": "reported separately on disjoint realised transitions and gates",
        },
        "n_seed_blocks_per_patch_arm": n_blocks,
        "play_evaluation": ("one paired episode per training seed block; summaries are across blocks"
                            if not skip_play else "skipped by command-line option"),
        "cart": cart_experiment(skip_play),
        "patch2d": patch_experiment(n_blocks, skip_play),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", type=int, default=20, choices=range(1, 21))
    parser.add_argument("--skip-play", action="store_true")
    parser.add_argument("--output", type=pathlib.Path, default=OUT)
    args = parser.parse_args()
    result = build_result(args.blocks, args.skip_play)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.output}")
    print("cart:", [(r["arm"], r["n_contacts"], r["mode_rule_recovered_exactly"])
                    for r in result["cart"]["arms"]])
    for label, arm in result["patch2d"]["arms"].items():
        print(label, f"near={arm['near_mode_recovered_blocks']}/{arm['n_seed_blocks']}",
              f"both={arm['both_modes_recovered_blocks']}/{arm['n_seed_blocks']}",
              f"gate={arm['gate_pass_blocks']}/{arm['n_seed_blocks']}",
              f"median IoU={arm['median_iou']:.3f}")


if __name__ == "__main__":
    main()
