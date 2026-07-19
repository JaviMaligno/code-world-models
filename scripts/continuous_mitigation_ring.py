"""Ring mitigation: distrust-region replanning vs the pinned blind planner on
RingField2D (paper 3, rung 2) — does paper 2's one-sided fence survive a
CLOSED, CURVED mode boundary?

Same module and settings as the patch2d sweep (pos_dims=(0, 1), eps=0.5).
The fences accumulate along the reachable (west) outer arc — an incremental
cover of the boundary (the nerve-certificate connection, RESEARCH-DIRECTION
§8.3-3). Cells: gap 0 (closed ring) and gap 0.6 hidden (channel the planner
cannot find — observationally equivalent, the mechanism grid showed).

Run: PYTHONPATH=src python scripts/continuous_mitigation_ring.py  (~15 min)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import RingField2D, blind_of
from cwm.continuous import harness
from cwm.continuous.mitigation import run_mitigated_episode

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=16)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--eps", type=float, default=0.5)
args = ap.parse_args()

CELLS = [("gap0", RingField2D()),
         ("gap0.6-hidden", RingField2D(gap=0.6, gap_center=0.0))]

t0 = time.time()
rows = []
print(f"{'cell':>14} {'J_tru':>7} {'J_bli':>7} {'J_mit':>7} {'J_rnd':>6} "
      f"{'pc_bli':>7} {'pc_mit':>7} {'c_mit':>5} {'viol':>5} {'t_c1':>5}",
      flush=True)
for name, truth in CELLS:
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
        "cell": name, "eps": args.eps,
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
    print(f"{name:>14} {j_t:7.2f} {j_b:7.2f} {j_m:7.2f} {j_r:6.2f} "
          f"{row['play_cost_blind']:7.3f} {row['play_cost_mitigated']:7.3f} "
          f"{row['mitigated_contact_rate']:5.2f} "
          f"{row['mean_violations']:5.1f} "
          f"{(row['mean_first_contact_step'] or -1):5.1f}", flush=True)

out = pathlib.Path("results/continuous_mitigation_ring.json")
out.write_text(json.dumps({"script": "continuous_mitigation_ring.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
