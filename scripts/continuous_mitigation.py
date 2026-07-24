"""Mitigation sweep: distrust-region replanning vs the pinned blind planner.

For each instrument and mode-position knob (the paper's existing grids), run
truth-MPC / blind-MPC / blind-MPC+mitigation on paired seeds and report the
play_cost collapse. CPU-only.

Run: PYTHONPATH=src python scripts/continuous_mitigation.py   (~10-15 min)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness
from cwm.continuous.mitigation import run_mitigated_episode

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cart-walls", type=float, nargs="+",
                default=[2.0, 4.0, 6.0, 8.0, 10.0])
ap.add_argument("--pend-stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
ap.add_argument("--cart-eps", type=float, default=0.25)
ap.add_argument("--pend-eps", type=float, default=0.1)
args = ap.parse_args()

t0 = time.time()
rows = []
print(f"{'inst':>4} {'knob':>5} {'J_tru':>7} {'J_bli':>7} {'J_mit':>7} "
      f"{'J_rnd':>6} {'pc_bli':>7} {'pc_mit':>7} {'c_bli':>5} {'c_mit':>5} "
      f"{'viol':>5} {'t_c1':>5}", flush=True)
for inst, knobs, eps, mk in (
        ("cart", args.cart_walls, args.cart_eps,
         lambda k: CartWall(x_wall=k)),
        ("pend", args.pend_stops, args.pend_eps,
         lambda k: PendulumStop(th_stop=k))):
    for k in knobs:
        truth = mk(k)
        blind = blind_of(truth)
        t, b, m, r = [], [], [], []
        for i in range(args.episodes):
            sd = args.seed + 1000 * i
            t.append(harness.run_episode(truth, truth, "mpc", sd))
            b.append(harness.run_episode(truth, blind, "mpc", sd))
            m.append(run_mitigated_episode(truth, blind, seed=sd, eps=eps))
            r.append(harness.run_episode(truth, policy="random", seed=sd))
        j_t, j_b = harness.mean_return(t), harness.mean_return(b)
        j_m, j_r = harness.mean_return(m), harness.mean_return(r)
        denom = j_t - j_r
        fc = [e.first_contact_step for e in m if e.first_contact_step is not None]
        row = {
            "instrument": inst, "knob": k, "eps": eps,
            "j_truth": j_t, "j_blind": j_b, "j_mitigated": j_m, "j_random": j_r,
            "play_cost_blind": (j_t - j_b) / denom if denom > 0 else 0.0,
            "play_cost_mitigated": (j_t - j_m) / denom if denom > 0 else 0.0,
            "blind_contact_rate": sum(e.contact for e in b) / args.episodes,
            "mitigated_contact_rate": sum(e.contact for e in m) / args.episodes,
            "mean_violations": sum(e.violations for e in m) / args.episodes,
            "mean_first_contact_step": sum(fc) / len(fc) if fc else None,
            "n_episodes": args.episodes,
        }
        rows.append(row)
        print(f"{inst:>4} {k:5.1f} {j_t:7.2f} {j_b:7.2f} {j_m:7.2f} "
              f"{j_r:6.2f} {row['play_cost_blind']:7.3f} "
              f"{row['play_cost_mitigated']:7.3f} "
              f"{row['blind_contact_rate']:5.2f} "
              f"{row['mitigated_contact_rate']:5.2f} "
              f"{row['mean_violations']:5.1f} "
              f"{(row['mean_first_contact_step'] or -1):5.1f}", flush=True)

out = pathlib.Path("results/continuous_mitigation.json")
out.write_text(json.dumps({"script": "continuous_mitigation.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
