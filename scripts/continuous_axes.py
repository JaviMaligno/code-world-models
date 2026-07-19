"""Axis separation: localized mode omission vs pervasive error vs smooth bump.

The design doc's step-4 controls, all CPU. One table, five arms, all verified
by the same tolerance gate (eps=0.01, deployment-realistic) and the same MPC
arena:

  wall@4 / wall@8   localized HARD mode omitted — the gate is blind exactly
                    with probability (1-r)^N and the planner is exploited
                    (danger = play_cost at the rare knob).
  bias 1.03         sub-tolerance pervasive error — passes the gate ALWAYS
                    (not by luck) and is harmless at play: the axis the
                    classic MBRL literature studies, controlled.
  bias 2.0          supra-tolerance pervasive error — the gate correctly
                    rejects it on every rollout (reveal-rarity ~ 1).
  bump@4 amp 0.5    localized SMOOTH perturbation omitted — comparable
                    reveal-rarity to wall@4, zero play_cost: rarity without
                    consequence. The contrast showing the danger mechanism
                    wants a mode boundary, not mere localization.
  bump@4 amp 1.0    stronger smooth bump: play_cost goes (slightly) NEGATIVE
                    — the truth planner is over-pessimistic about the slowdown
                    near its horizon edge and sometimes settles for the small
                    plateau, while the bump-blind planner pushes through and
                    wins. A smooth localized omission can even help; it does
                    not produce the exploitation geometry a hard mode does.

Also cross-checks gate exactness: empirical pass rate at N=40 vs (1-r)^40.

Run: PYTHONPATH=src python scripts/continuous_axes.py   (~10 min CPU)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import CartWall, blind_of, biased_of, unbumped_of
from cwm.continuous import gate, harness

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--eps", type=float, default=0.01)
ap.add_argument("--rollouts", type=int, default=2000, help="reveal-rarity sample")
ap.add_argument("--gates", type=int, default=300, help="independent N=40 gates")
ap.add_argument("--n-gate", type=int, default=40)
ap.add_argument("--episodes", type=int, default=20, help="MPC episodes/arm")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

WALL = CartWall(x_wall=4.0)
WALL_RARE = CartWall(x_wall=8.0)
BUMP_MILD = CartWall(x_wall=None, bump_amp=0.5, bump_center=4.0, bump_width=0.5)
BUMP_STRONG = CartWall(x_wall=None, bump_amp=1.0, bump_center=4.0, bump_width=0.5)

ARMS = [
    # (name, truth, model-under-test)
    ("wall@4 omitted", WALL, blind_of(WALL)),
    ("wall@8 omitted", WALL_RARE, blind_of(WALL_RARE)),
    ("bias x1.03 (sub-eps)", WALL, biased_of(WALL, 1.03)),
    ("bias x2.0 (supra-eps)", WALL, biased_of(WALL, 2.0)),
    ("bump@4 amp0.5 (smooth)", BUMP_MILD, unbumped_of(BUMP_MILD)),
    ("bump@4 amp1.0 (smooth)", BUMP_STRONG, unbumped_of(BUMP_STRONG)),
]

t0 = time.time()
rows = []
print(f"eps={args.eps}  N={args.n_gate}  ({args.rollouts} rollouts, "
      f"{args.gates} gates, {args.episodes} episodes/arm)", flush=True)
print(f"{'arm':>24} {'rarity':>8} {'(1-r)^N':>8} {'pass@N':>7} {'J_truth':>8} "
      f"{'J_model':>8} {'cost':>6} {'danger@N':>9}", flush=True)
for name, truth, model in ARMS:
    r, r_lo, r_hi = gate.reveal_rarity(truth, model, args.eps, args.rollouts,
                                       seed=args.seed + 10_000)
    predicted = (1 - r) ** args.n_gate
    p, p_lo, p_hi = gate.gate_pass_rate(truth, model, args.eps, args.n_gate,
                                        args.gates, seed=args.seed + 500_000)
    pc = harness.play_cost(truth, model, args.episodes, seed=args.seed)
    dgr = pc["play_cost"] * predicted
    rows.append({"arm": name, "eps": args.eps, "rarity": r,
                 "rarity_ci": [r_lo, r_hi], "pass_rate": p,
                 "pass_rate_ci": [p_lo, p_hi], "predicted_pass": predicted,
                 **pc, "danger": dgr})
    print(f"{name:>24} {r:8.4f} {predicted:8.4f} {p:7.3f} {pc['j_truth']:8.2f} "
          f"{pc['j_blind']:8.2f} {pc['play_cost']:6.3f} {dgr:9.4f}", flush=True)

out = {"script": "continuous_axes.py", "params": vars(args),
       "elapsed_s": round(time.time() - t0, 1), "rows": rows}
path = pathlib.Path("results/continuous_axes.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
