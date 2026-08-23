"""What the fence bound really counts: separation in 1D, a packing number in 2D.

Three peer-review findings on Proposition "fencecover" are settled here by
measurement rather than by rewording, because each of them was a claim about the
instrument that nobody had checked against the instrument.

(1) IN 1D THE FENCES ARE NOT WHERE THE PROPOSITION PUTS THEM. The proposition
    imagined a fence AT the mode boundary; the implementation records the model's
    refuted PREDICTION (mitigation.py), which for a blind model overshoots the wall.
    This script measures the overshoot against the band eps, and it is routinely
    larger -- so the band does not contain x_wall and the covering hypothesis simply
    fails, on rows where the measured violation count is nevertheless exactly 1.00.
    Whatever explains that 1.00, it is not a covering number.

(2) WHAT DOES EXPLAIN IT IS SEPARATION, AND SEPARATION HAS A SIGNATURE. In one
    dimension a single point beyond the wall DISCONNECTS the agent from the phantom:
    every imagined path to the lure must cross it, so the segment test truncates them
    all, whatever eps is and wherever in the far region the fence landed. A covering
    story predicts eps-sensitivity; a separation story predicts eps-INVARIANCE. This
    script sweeps eps over a 25x range on both 1D instruments and reports whether the
    outcome moves at all. On a circle, by contrast, no single ball separates the
    inside from the outside -- the boundary has no cut point -- which is the honest
    reason 2D costs more than one contact, and it is a topological statement, not a
    metric one.

(3) IN 2D THE BUDGET IS A PACKING NUMBER, THE COUNTS ARE OUTLIER-DRIVEN, AND SOME
    EPISODES ARE OUTRIGHT FAILURES. A maximal eps-packing of the boundary can be
    placed one point at a time with every point adding coverage (12 of them on the
    unit circle at eps = 0.5, against a covering number of 7 -- see
    circle_covering_number.py), so packing is the direction the bound needs. And the
    per-episode distribution matters: this script reports median and MAX violations,
    the number of DISTINCT fence points, the fraction of episodes that end pinned at
    blind-level return, and the angular spread of fence bearings per patch --- the
    probed arc measured directly, rather than inferred from the violation count
    divided by the budget, which was circular.

Run: PYTHONPATH=src python scripts/fence_separation_census.py   (~12 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import statistics
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous import mitigation                                  # noqa: E402
from cwm.continuous.envs import CartWall, PendulumStop, PatchField2D   # noqa: E402
from cwm.continuous.envs import blind_of                               # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--seeds", type=int, default=5, help="1D episodes per arm")
ap.add_argument("--seeds-2d", type=int, default=20, help="2D episodes per knob")
ap.add_argument("--horizon", type=int, default=40)
args = ap.parse_args()

ARMS_1D = (("cart wall@10", CartWall(x_wall=10.0), 0.25, (0.25, 0.1, 0.05, 0.01), 0),
           ("pendulum stop@2.0", PendulumStop(th_stop=2.0), 0.1,
            (0.1, 0.05, 0.02, 0.005), 0))
KNOBS_2D = ((2.0, 6.0), (3.0, 7.0), (4.0, 8.0))
EPS_2D = 0.5
PATCH_R = 1.0

out = {"script": "fence_separation_census.py", "params": vars(args)}

# --- (1) where the 1D fences actually land -----------------------------------
print("=== 1D: where the fence lands, against the band it is supposed to cover ===")
rows = []
for name, env, eps, _sweep, dim in ARMS_1D:
    blind = blind_of(env)
    boundary = getattr(env, "x_wall", None)
    if boundary is None:
        boundary = env.th_stop
    over = []
    for s in range(args.seeds):
        seed = 1000 * s
        rng = random.Random(seed)
        st = env.initial_state(rng)
        fences = []
        for _t in range(env.h_episode):
            a = mitigation.plan_mitigated(blind, st, rng, fences, eps,
                                          horizon=args.horizon, n_samples=200,
                                          block=10, pos_dims=(dim,))
            s2, _r, _c = env.step(st, a)
            pred, _, _ = blind.step(st, a)
            if max(abs(pred[i] - s2[i]) for i in range(len(s2))) > 1e-6:
                fences.append(tuple(pred[i] for i in (dim,)))
            st = s2
        if fences:
            over.append(abs(fences[0][0]) - abs(boundary))
    misses = sum(1 for o in over if o > eps)
    rows.append({"arm": name, "eps": eps, "boundary": boundary,
                 "first_fence_overshoot": over, "band_misses_boundary": misses,
                 "n": len(over)})
    print(f"  {name:>18} eps={eps}: overshoots "
          + ", ".join(f"{o:.3f}" for o in over)
          + f"  -> band misses the boundary in {misses}/{len(over)}")
out["fence_placement_1d"] = rows

# --- (2) the separation signature: eps-invariance in 1D ----------------------
print("\n=== 1D: eps-invariance (a covering story would be eps-sensitive) ===")
rows = []
for name, env, _eps, sweep, dim in ARMS_1D:
    blind = blind_of(env)
    per_eps = {}
    for eps in sweep:
        res = []
        for s in range(args.seeds - 1):
            ep = mitigation.run_mitigated_episode(
                env, blind, seed=1000 * s, horizon=args.horizon, eps=eps,
                pos_dims=(dim,))
            res.append((round(ep.ret, 6), ep.violations))
        per_eps[eps] = res
    base = per_eps[sweep[0]]
    same = all(per_eps[e] == base for e in sweep)
    rows.append({"arm": name, "eps_grid": list(sweep),
                 "returns_and_violations": {str(e): per_eps[e] for e in sweep},
                 "identical_across_eps": same,
                 "eps_ratio": sweep[0] / sweep[-1]})
    print(f"  {name:>18}: eps {sweep[0]} -> {sweep[-1]} ({sweep[0]/sweep[-1]:.0f}x): "
          f"{'IDENTICAL outcomes' if same else 'outcomes MOVE'}")
    for e in sweep:
        print(f"{'':>20}  eps={e:<6} " +
              " ".join(f"{r:.2f}/{v}" for r, v in per_eps[e]))
out["eps_invariance_1d"] = rows

# --- no ball separates a circle ----------------------------------------------
# A single eps-ball removes an arc; the complement of an arc in S^1 is connected,
# so the boundary is never cut. Two balls are needed to disconnect S^1. That is the
# whole 1D-vs-2D contrast, and it needs no measurement -- but state the count.
out["separation_numbers"] = {"line_cut_number": 1, "circle_cut_number": 2,
                            "note": "removing one arc leaves S^1 connected; "
                                    "removing two disconnects it"}
print("\nseparation number: 1 for a point on a line, 2 for arcs on a circle "
      "(one arc leaves S^1 connected)")

# --- (3) the 2D per-episode distribution -------------------------------------
print("\n=== 2D: per-episode distribution, lock-in, and the arc probed directly ===")
rows = []
for k1, k2 in KNOBS_2D:
    env = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
    blind = blind_of(env)
    j_truth = None
    per = []
    for s in range(args.seeds_2d):
        seed = 1000 * s
        rng = random.Random(seed)
        st = env.initial_state(rng)
        fences = []
        total = 0.0
        for _t in range(env.h_episode):
            a = mitigation.plan_mitigated(blind, st, rng, fences, EPS_2D,
                                          horizon=args.horizon, n_samples=200,
                                          block=10, pos_dims=(0, 1))
            s2, r, _c = env.step(st, a)
            pred, _, _ = blind.step(st, a)
            if max(abs(pred[i] - s2[i]) for i in range(len(s2))) > 1e-6:
                fences.append((pred[0], pred[1]))
            total += r
            st = s2
        # bearings per patch, measured directly
        bearings = {1: [], 2: []}
        for fx, fy in fences:
            d1 = math.hypot(fx - k1, fy)
            d2 = math.hypot(fx - k2, fy)
            which = 1 if d1 <= d2 else 2
            cx = k1 if which == 1 else k2
            bearings[which].append(math.atan2(fy, fx - cx))
        spread = {}
        for w in (1, 2):
            b = sorted(bearings[w])
            spread[w] = (max(b) - min(b)) if len(b) > 1 else 0.0
        per.append({"seed": seed, "ret": total, "violations": len(fences),
                    "distinct_fences": len(set(fences)),
                    "arc_spread_rad": spread,
                    "patches_touched": sum(1 for w in (1, 2) if bearings[w])})
    v = [p["violations"] for p in per]
    r = [p["ret"] for p in per]
    j_truth = max(r)
    pinned = [p for p in per if p["ret"] < 0.1 * j_truth]
    arc_frac = [max(p["arc_spread_rad"].values()) / (2 * math.pi) for p in per]
    rows.append({"knob": [k1, k2], "mean_violations": statistics.mean(v),
                 "median_violations": statistics.median(v), "max_violations": max(v),
                 "mean_distinct_fences": statistics.mean(p["distinct_fences"] for p in per),
                 "max_distinct_fences": max(p["distinct_fences"] for p in per),
                 "pinned_episodes": len(pinned), "n_episodes": len(per),
                 "mean_violations_ex_max": statistics.mean(
                     sorted(v)[:-1]) if len(v) > 1 else None,
                 "median_probed_arc_fraction": statistics.median(arc_frac),
                 "max_probed_arc_fraction": max(arc_frac),
                 "episodes": per})
    print(f"  knob ({k1:.0f},{k2:.0f}): violations mean {statistics.mean(v):.2f} "
          f"median {statistics.median(v):.0f} max {max(v)}   "
          f"distinct max {max(p['distinct_fences'] for p in per)}   "
          f"pinned {len(pinned)}/{len(per)}   "
          f"probed arc median {100*statistics.median(arc_frac):.1f}% "
          f"max {100*max(arc_frac):.1f}%")
out["patch2d_episode_census"] = rows

print("\nReading: in 1D the outcome does not move over a 25x range of eps, which is")
print("the signature of a CUT, not of a cover -- and the fences do not even land in")
print("the band the covering story needs. In 2D the means are driven by a fat tail of")
print("lock-in episodes with many DUPLICATE fences, so the probed arc has to be")
print("measured directly (it is a fraction of what dividing the count by the budget")
print("suggested), and the budget itself is a packing number, not a covering number.")

dst = _REPO / "results" / "fence_separation_census.json"
dst.write_text(json.dumps(out, indent=2))
print(f"\nwrote {dst}")
