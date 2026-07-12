"""Second planner family: CEM vs the certified-blind model.

Measures the other branch of Proposition 3: play_cost <= query-hit mass.
Random shooting (constant candidates) reaches the phantom in imagination and
is exploited (the paper's Tables); CEM's local search never discovers it.
Per knob we report CEM's blind-arm play_cost (expected ~0, knob-invariant),
contact rate, and the imagined boundary-crossing fraction for BOTH planners
on the blind model -- the measured query-hit proxy.

Run: PYTHONPATH=src python scripts/continuous_cem.py   (~30-60 min CPU)
"""
import argparse
import json
import pathlib
import random
import time

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import cem, harness, mpc

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cart-walls", type=float, nargs="+",
                default=[2.0, 4.0, 6.0, 8.0, 10.0])
ap.add_argument("--pend-stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
args = ap.parse_args()


def mpc_crossing_frac(model, state, rng, boundary, horizon=40,
                      n_samples=200, block=10):
    """Fraction of random-shooting candidates whose imagined trajectory
    crosses `boundary` (read-only reuse of mpc's candidate generator)."""
    crossed = total = 0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, hit = state, False
        for a in acts:
            s, _, _ = model.step(s, a)
            if s[0] >= boundary:
                hit = True
        crossed += hit
        total += 1
    return crossed / total


t0 = time.time()
rows = []
print(f"{'inst':>4} {'knob':>5} {'J_tru':>7} {'J_bli':>7} {'J_rnd':>6} "
      f"{'pc_bli':>7} {'c_bli':>5} {'xing_cem':>8} {'xing_mpc':>8}", flush=True)
for inst, knobs, mk in (
        ("cart", args.cart_walls, lambda k: CartWall(x_wall=k)),
        ("pend", args.pend_stops, lambda k: PendulumStop(th_stop=k))):
    for k in knobs:
        truth = mk(k)
        blind = blind_of(truth)
        t, b, r, xm = [], [], [], []
        for i in range(args.episodes):
            sd = args.seed + 1000 * i
            t.append(cem.run_episode(truth, truth, seed=sd))
            b.append(cem.run_episode(truth, blind, seed=sd, boundary=k))
            r.append(harness.run_episode(truth, policy="random", seed=sd))
            # MPC crossing diagnostic: one plan from the episode's start state
            rng = random.Random(sd)
            s0 = truth.initial_state(rng)
            xm.append(mpc_crossing_frac(blind, s0, rng, k))
        j_t, j_b = harness.mean_return(t), harness.mean_return(b)
        j_r = harness.mean_return(r)
        denom = j_t - j_r
        row = {
            "instrument": inst, "knob": k,
            "j_truth_cem": j_t, "j_blind_cem": j_b, "j_random": j_r,
            "play_cost_blind_cem": (j_t - j_b) / denom if denom > 0 else 0.0,
            "blind_contact_rate": sum(e.contact for e in b) / args.episodes,
            "crossing_frac_cem_blind":
                sum(e.crossing_frac for e in b) / args.episodes,
            "crossing_frac_mpc_blind": sum(xm) / len(xm),
            "n_episodes": args.episodes,
        }
        rows.append(row)
        print(f"{inst:>4} {k:5.1f} {j_t:7.2f} {j_b:7.2f} {j_r:6.2f} "
              f"{row['play_cost_blind_cem']:7.3f} "
              f"{row['blind_contact_rate']:5.2f} "
              f"{row['crossing_frac_cem_blind']:8.4f} "
              f"{row['crossing_frac_mpc_blind']:8.4f}", flush=True)

out = pathlib.Path("results/continuous_cem.json")
out.write_text(json.dumps({"script": "continuous_cem.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
