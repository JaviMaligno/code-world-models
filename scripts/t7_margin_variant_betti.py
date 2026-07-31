"""Emit the margin-0.3 censoring variant's Betti-1 counts.

docs/paper3/THEORY.md states that the 0.3-margin refinement of the censoring
rule "repairs the gap-0 false negatives (5/5) but RESTORES THE BRIDGE at
gamma = 0.6 (5/5 false loops, all finite)". No committed file carried those
counts: results/ring2d_censored_filtration.json is MARGIN = 0.0 only, and
results/t7_infinite_bar_certificate.json records infinite-bar counts without
ever computing beta1 under the variant. So the sentence correcting an earlier
mis-attribution was itself an unrecorded run -- the same failure class.

This runs both margins over the same cells and emits the beta1 counts, the
per-cell bar finiteness, and how many edges each margin censors (which is the
mechanism: a larger margin censors FEWER edges, so the bridge survives).

The censor rule lives in scripts/ring2d_censored_filtration.py with the margin
as a module constant, so it is re-implemented here as a parameter rather than
patched at import time -- a monkeypatched constant is exactly the kind of
provenance that made these numbers unreproducible.

Resumable per (margin, gap, seed).

  PYTHONPATH=src python scripts/t7_margin_variant_betti.py
"""
import argparse
import json
import math
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import RingField2D                      # noqa: E402
from cwm.continuous.contract import collect_transitions          # noqa: E402
from cwm.continuous.mitigation import _segments_intersect        # noqa: E402
from cwm.continuous.tda import (betti1_estimate, dedupe,         # noqa: E402
                                rips_persistence, subsample,
                                median_nn_distance)

OUT = _REPO / "results" / "t7_margin_variant_betti.json"
GAPS = (0.0, 0.6)
SEEDS = (10_000, 20_000, 30_000, 40_000, 50_000)
MARGINS = (0.0, 0.3)
N_ROLL = 40
TAU_FACTOR = 3.0
CAP = 90          # the pre-registered detector budget, unchanged


def crosses(p1, p2, q1, q2, margin):
    """Transversal passage clearing the edge's supporting line by `margin`.

    margin = 0.0 is v1 semantics: any proper crossing censors. A larger margin
    requires the free segment to clear the line on BOTH sides, so a poke that
    ends just past it no longer censors -- which is why raising the margin
    censors fewer edges.
    """
    if not _segments_intersect(p1, p2, q1, q2):
        return False
    ex, ey = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(ex, ey) or 1e-12
    nx, ny = -ey / L, ex / L
    s1 = nx * (q1[0] - p1[0]) + ny * (q1[1] - p1[1])
    s2 = nx * (q2[0] - p1[0]) + ny * (q2[1] - p1[1])
    return s1 * s2 < 0 and min(abs(s1), abs(s2)) > margin


def evidence(env, seed, n_roll):
    trans = collect_transitions(env, n_roll, seed=seed)
    landings, free = [], []
    for tr in trans:
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            landings.append((x2, y2))
        else:
            s, ns = tr["state"], tr["next_state"]
            free.append(((s[0], s[1]), (ns[0], ns[1])))
    return landings, free


def cell(gap, seed, margin):
    # Same cell definition as scripts/ring2d_censored_filtration.py: an INSIDE
    # start (the ring's own centre), the channel facing pi, and the
    # pre-registered detector budget. Using a different start is what made the
    # first attempt here produce no landings at all.
    env = RingField2D(gap=gap, gap_center=math.pi,
                      x0_center=RingField2D().center)
    landings, free = evidence(env, seed, N_ROLL)
    pts = subsample(dedupe(landings, 0.05), CAP, 0)
    if len(pts) < 4:
        return {"gap": gap, "seed": seed, "margin": margin,
                "n_points": len(pts), "skipped": "too few landings"}
    censored = [0]

    def edge_ok(p, q):
        bad = any(crosses(p, q, a, b, margin) for a, b in free)
        censored[0] += bad
        return not bad

    bars = rips_persistence(pts, edge_filter=edge_ok)["h1"]
    tau = TAU_FACTOR * median_nn_distance(pts)
    persistent = [b for b in bars if b[1] is None or (b[1] - b[0]) > tau]
    return {
        "gap": gap, "seed": seed, "margin": margin,
        "n_points": len(pts), "n_free_segments": len(free),
        "edges_censored": censored[0],
        "plain_betti1": betti1_estimate(pts)["betti1"],
        "censored_betti1": len(persistent),
        "infinite_bars": sum(1 for b in persistent if b[1] is None),
        "tau": tau,
        # The TRUE beta1: 1 for the closed ring, 0 once a channel is open.
        "true_betti1": 1 if gap == 0.0 else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margins", type=float, nargs="*", default=list(MARGINS))
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {}
    cells = state.setdefault("cells", {})
    for margin in args.margins:
        for gap in GAPS:
            for seed in SEEDS:
                key = f"{margin}|{gap}|{seed}"
                if key in cells:
                    continue
                cells[key] = cell(gap, seed, margin)
                OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
                c = cells[key]
                print(f"margin={margin} gap={gap} seed={seed}: "
                      f"plain b1={c.get('plain_betti1')} "
                      f"censored b1={c.get('censored_betti1')} "
                      f"(true {c.get('true_betti1')}), "
                      f"{c.get('edges_censored')} edges censored, "
                      f"{c.get('infinite_bars')} infinite", flush=True)

    summary = {}
    for margin in args.margins:
        for gap in GAPS:
            rows = [v for k, v in cells.items()
                    if k.startswith(f"{margin}|{gap}|") and "skipped" not in v]
            if not rows:
                continue
            correct = sum(1 for r in rows
                          if r["censored_betti1"] == r["true_betti1"])
            summary[f"margin={margin},gap={gap}"] = {
                "n_seeds": len(rows),
                "censored_betti1_correct": f"{correct}/{len(rows)}",
                "censored_betti1_values": [r["censored_betti1"] for r in rows],
                "infinite_bars_total": sum(r["infinite_bars"] for r in rows),
                "mean_edges_censored":
                    sum(r["edges_censored"] for r in rows) / len(rows),
            }
    state["summary"] = summary
    state["note"] = (
        "A larger margin censors FEWER edges, so it can repair gap-0 false "
        "negatives (pokes no longer censor the true loop's edges) while "
        "restoring the channel bridge at gap > 0. Both effects are visible in "
        "mean_edges_censored, so the trade-off is measured rather than argued.")
    OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
    print("\n--- summary ---")
    for k, v in sorted(summary.items()):
        print(f"  {k}: correct {v['censored_betti1_correct']}, "
              f"b1 {v['censored_betti1_values']}, "
              f"{v['mean_edges_censored']:.0f} edges censored on average")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
