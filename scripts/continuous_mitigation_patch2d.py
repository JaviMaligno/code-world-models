"""2D mitigation sweep: distrust-region replanning vs the pinned blind planner,
on the PatchField2D instrument (pos_dims=(0, 1)).

Mirrors scripts/continuous_mitigation.py's structure for the two 1D
instruments, but sweeps the (p1_x, p2_x) knob grid of the bi-modal 2D
instrument and generalizes the mitigation to pos_dims=(0, 1). CPU-only.

Run: PYTHONPATH=src python scripts/continuous_mitigation_patch2d.py   (~30-60 min)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import PatchField2D, blind_of
from cwm.continuous import harness
from cwm.continuous.mitigation import run_mitigated_episode

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--knobs", type=float, nargs="+",
                default=[2.0, 6.0, 3.0, 7.0, 4.0, 8.0],
                help="flattened (p1_x, p2_x) pairs")
ap.add_argument("--eps", type=float, default=0.5)
args = ap.parse_args()

pairs = list(zip(args.knobs[0::2], args.knobs[1::2]))

t0 = time.time()
rows = []
print(f"{'k1':>4} {'k2':>4} {'J_tru':>7} {'J_bli':>7} {'J_mit':>7} "
      f"{'J_rnd':>6} {'pc_bli':>7} {'pc_mit':>7} {'c_bli':>5} {'c_mit':>5} "
      f"{'viol':>5} {'t_c1':>5}", flush=True)
for k1, k2 in pairs:
    truth = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
    blind = blind_of(truth)
    t, b, m, r = [], [], [], []
    for i in range(args.episodes):
        sd = args.seed + 1000 * i
        t.append(harness.run_episode(truth, truth, "mpc", sd))
        b.append(harness.run_episode(truth, blind, "mpc", sd))
        m.append(run_mitigated_episode(truth, blind, seed=sd, eps=args.eps,
                                       pos_dims=(0, 1)))
        r.append(harness.run_episode(truth, policy="random", seed=sd))
    j_t, j_b = harness.mean_return(t), harness.mean_return(b)
    j_m, j_r = harness.mean_return(m), harness.mean_return(r)
    denom = j_t - j_r
    fc = [e.first_contact_step for e in m if e.first_contact_step is not None]
    row = {
        "instrument": "patch2d", "k1": k1, "k2": k2, "eps": args.eps,
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
    print(f"{k1:4.1f} {k2:4.1f} {j_t:7.2f} {j_b:7.2f} {j_m:7.2f} "
          f"{j_r:6.2f} {row['play_cost_blind']:7.3f} "
          f"{row['play_cost_mitigated']:7.3f} "
          f"{row['blind_contact_rate']:5.2f} "
          f"{row['mitigated_contact_rate']:5.2f} "
          f"{row['mean_violations']:5.1f} "
          f"{(row['mean_first_contact_step'] or -1):5.1f}", flush=True)

out = pathlib.Path("results/continuous_mitigation_patch2d.json")
out.write_text(json.dumps({"script": "continuous_mitigation_patch2d.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
