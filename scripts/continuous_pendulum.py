"""Second hybrid instrument: pendulum-with-stop (design doc step 5, last item).

Same protocol as continuous_reach.py on the PendulumStop environment: sweep
the stop angle (the rarity knob), measure rarity + the MPC arena + danger(N).
The base plant is nonlinear (gravity), so this is the robustness check that
the mechanism does not depend on the cart's linear off-mode dynamics.

Run: PYTHONPATH=src python scripts/continuous_pendulum.py   (~3 min CPU)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import PendulumStop, blind_of
from cwm.continuous import harness

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
ap.add_argument("--rollouts", type=int, default=3000)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
rows = []
print(f"{'stop':>5} {'rarity':>8} {'(CI)':>17} {'J_truth':>8} {'J_blind':>8} "
      f"{'J_rand':>7} {'cost':>6} {'blind_hit':>9} {'truth_hit':>9} "
      f"{'d@40':>7}", flush=True)
for st in args.stops:
    truth = PendulumStop(th_stop=st)
    r, lo, hi = harness.rarity(truth, args.rollouts, seed=args.seed + 50_000)
    pc = harness.play_cost(truth, blind_of(truth), args.episodes,
                           seed=args.seed)
    dangers = {n: pc["play_cost"] * (1 - r) ** n for n in (20, 40, 80)}
    rows.append({"th_stop": st, "rarity": r, "rarity_lo": lo, "rarity_hi": hi,
                 **pc, "danger": dangers})
    print(f"{st:5.1f} {r:8.4f} [{lo:.4f},{hi:.4f}] {pc['j_truth']:8.2f} "
          f"{pc['j_blind']:8.2f} {pc['j_random']:7.2f} {pc['play_cost']:6.3f} "
          f"{pc['blind_contact_rate']:9.2f} {pc['truth_contact_rate']:9.2f} "
          f"{dangers[40]:7.4f}", flush=True)

out = {"script": "continuous_pendulum.py", "params": vars(args),
       "elapsed_s": round(time.time() - t0, 1), "rows": rows}
path = pathlib.Path("results/continuous_pendulum.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
