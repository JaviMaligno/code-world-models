"""r_int(gamma) shape probe (paper 3 THEORY.md, the monotonicity question).

Common-random-numbers sweep of the interior-entry rate over a fine gamma grid
up to the wall-free limit gamma = 2*pi. Per gamma: r_int and r (mode firing)
on THE SAME seeds, so we also report, for adjacent gamma pairs, the pathwise
violation rate P(enter at gamma_i and NOT at gamma_j > gamma_i) — nonzero
violations are consistent with monotone MARGINALS but rule out the naive
pathwise coupling (already known to fail); the curve shape decides between:
  - monotone nondecreasing r_int  -> conjecture survives, proof must compare
    post-divergence conditionals (stochastic domination, not pathwise)
  - an interior peak / decrease toward 2*pi -> conjecture REFUTED; mechanism:
    the wall is also a FUNNEL (freeze-at-rest holds movers near the channel
    mouth; with no wall they drift past) — record as a finding.
r(gamma) nonincreasing is a THEOREM (fire(g2) subset fire(g1) pathwise); its
column doubles as a sanity check of the harness.

Run: PYTHONPATH=src python scripts/ring2d_rint_probe.py   (~3 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import RingField2D
from cwm.law import wilson_ci

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--gaps", type=float, nargs="+",
                default=[0.0, 0.1, 0.2, 0.4, 0.6, 0.9, 1.2, 1.8, 2.4,
                         3.2, 4.6, 2 * math.pi])
ap.add_argument("--rollouts", type=int, default=4000)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
enter = {}   # gap -> per-seed interior-entry booleans (CRN)
fire = {}
funnel = {}  # gap -> per-seed "entered AFTER at least one freeze" booleans
             # (direct = enter and not funnel; direct entries never land in
             # A(gamma1) so they are pathwise-monotone by Prop 7 — the
             # non-monotone risk lives entirely in the funnel component)
for gap in args.gaps:
    env = RingField2D(gap=gap)
    ent, frd, fun = [], [], []
    for i in range(args.rollouts):
        rng = random.Random(args.seed + 50_000 + i)
        s = env.initial_state(rng)
        e = f = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, c = env.step(s, a)
            f = f or c
            if not e and env.in_interior(s[0], s[1]):
                e = True
                fun.append(f)      # froze at least once before first entry?
        if not e:
            fun.append(False)
        ent.append(e)
        frd.append(f)
    enter[gap], fire[gap], funnel[gap] = ent, frd, fun
    ri, lo, hi = wilson_ci(sum(ent), args.rollouts)
    r, _, _ = wilson_ci(sum(frd), args.rollouts)
    nf = sum(a and b for a, b in zip(ent, fun))
    print(f"gap={gap:5.3f}  r={r:7.4f}  r_int={ri:7.4f} [{lo:.4f},{hi:.4f}]  "
          f"funnel={nf}/{sum(ent)}", flush=True)

rows = []
gaps = sorted(args.gaps)
for i, g in enumerate(gaps):
    ri, lo, hi = wilson_ci(sum(enter[g]), args.rollouts)
    r, rlo, rhi = wilson_ci(sum(fire[g]), args.rollouts)
    row = {"gap": g, "r": r, "r_ci": [rlo, rhi],
           "r_int": ri, "r_int_ci": [lo, hi]}
    row["funnel_entries"] = sum(a and b for a, b in zip(enter[g], funnel[g]))
    row["direct_entries"] = sum(a and not b
                                for a, b in zip(enter[g], funnel[g]))
    if i + 1 < len(gaps):
        g2 = gaps[i + 1]
        viol = [j for j, (a, b) in enumerate(zip(enter[g], enter[g2]))
                if a and not b]
        gain = sum(b and not a for a, b in zip(enter[g], enter[g2]))
        fire_viol = sum(b and not a for a, b in zip(fire[g], fire[g2]))
        row["pathwise_enter_violations_vs_next"] = len(viol)
        row["violating_seeds"] = [args.seed + 50_000 + j for j in viol[:20]]
        row["pathwise_enter_gains_vs_next"] = gain
        row["pathwise_fire_violations_vs_next"] = fire_viol  # theorem: 0
    rows.append(row)

out = {"script": "ring2d_rint_probe.py", "params": vars(args), "rows": rows,
       "elapsed_s": round(time.time() - t0, 1)}
path = pathlib.Path("results/continuous_ring2d_rint_probe.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
