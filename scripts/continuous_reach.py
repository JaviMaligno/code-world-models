"""Mechanism go/no-go for the continuous/hybrid instrument (paper 2, step 1-2).

Sweeps the wall position (the rarity knob) and measures, per knob value:
  - rarity: P(random rollout fires the wall mode), Wilson CI — the gate's view
  - the MPC arena: J_truth / J_blind / J_random, contact rates, play_cost
  - danger(N) = play_cost * (1-rarity)^N for N in {20, 40, 80}

Go/no-go (design doc order-of-work step 1): blind-planner wall reach ~1 and
play_cost ~flat across the knob while rarity falls — the continuous analogue
of the paper-1 mechanism (competent reach flat, random reach falling).

Run: PYTHONPATH=src python scripts/continuous_reach.py
     (defaults ~10-15 min CPU; --episodes 6 for a quick pass)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import CartWall, blind_of
from cwm.continuous import harness

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--walls", type=float, nargs="+",
                default=[2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0])
ap.add_argument("--rollouts", type=int, default=3000, help="rarity sample")
ap.add_argument("--episodes", type=int, default=20, help="MPC episodes/arm")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
rows = []
print(f"{'x_wall':>6} {'rarity':>8} {'(CI)':>17} {'J_truth':>8} {'J_blind':>8} "
      f"{'J_rand':>7} {'cost':>6} {'blind_hit':>9} {'truth_hit':>9} "
      f"{'d@20':>7} {'d@40':>7} {'d@80':>7}", flush=True)
for x_w in args.walls:
    truth = CartWall(x_wall=x_w)
    r, lo, hi = harness.rarity(truth, args.rollouts, seed=args.seed + 50_000)
    pc = harness.play_cost(truth, blind_of(truth), args.episodes,
                           seed=args.seed)
    dangers = {n: pc["play_cost"] * (1 - r) ** n for n in (20, 40, 80)}
    rows.append({"x_wall": x_w, "rarity": r, "rarity_lo": lo, "rarity_hi": hi,
                 **pc, "danger": dangers})
    print(f"{x_w:6.1f} {r:8.4f} [{lo:.4f},{hi:.4f}] {pc['j_truth']:8.2f} "
          f"{pc['j_blind']:8.2f} {pc['j_random']:7.2f} {pc['play_cost']:6.3f} "
          f"{pc['blind_contact_rate']:9.2f} {pc['truth_contact_rate']:9.2f} "
          f"{dangers[20]:7.4f} {dangers[40]:7.4f} {dangers[80]:7.4f}",
          flush=True)

out = {"script": "continuous_reach.py",
       "params": vars(args), "elapsed_s": round(time.time() - t0, 1),
       "rows": rows}
path = pathlib.Path("results/continuous_reach.json")
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
