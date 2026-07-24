"""Trust-inversion (optimism) defense vs the INVENTED mode (V2-PROGRAM 2a).

The measured dual failure: filled-disc model from inside flattens imagined
value; every distrust variant is inert (pc 1.769, fences firing 18.6/ep).
This runs the freedom-patched planner (mitigation.run_patched_episode) on
the same cell, episodic and persistent, against the same paired baselines.

Run: PYTHONPATH=src python scripts/continuous_ring2d_optimism.py
"""
import json
import pathlib
import time

from cwm.continuous.envs import RingField2D, filled_of, integrate_2d
from cwm.continuous import harness
from cwm.continuous.mitigation import run_patched_episode

EPISODES = 16
truth = RingField2D(x0_center=RingField2D().center)   # inside start
model = filled_of(truth)                              # the invented mode
integrate = lambda s, a: integrate_2d(                # the pinned integrator
    s, a, truth.dt, truth.gain, truth.drag, truth.a_max)

t0 = time.time()
rows = []
for persist in (False, True):
    t, b, m, r = [], [], [], []
    freedom = [] if persist else None
    for i in range(EPISODES):
        sd = 1000 * i
        t.append(harness.run_episode(truth, truth, "mpc", sd))
        b.append(harness.run_episode(truth, model, "mpc", sd))
        m.append(run_patched_episode(
            truth, model, integrate, seed=sd, eps=0.5, pos_dims=(0, 1),
            freedom=(freedom if persist else None)))
        r.append(harness.run_episode(truth, policy="random", seed=sd))
    j_t, j_b = harness.mean_return(t), harness.mean_return(b)
    j_m, j_r = harness.mean_return(m), harness.mean_return(r)
    denom = j_t - j_r
    row = {
        "cell": "gap0-inside-filled", "defense": "freedom-patch",
        "persist": persist, "eps": 0.5, "n_episodes": EPISODES,
        "j_truth": j_t, "j_filled": j_b, "j_patched": j_m, "j_random": j_r,
        "play_cost_filled": (j_t - j_b) / denom,
        "play_cost_patched": (j_t - j_m) / denom,
        "mean_freedom_points": sum(e.violations for e in m) / EPISODES,
        "per_episode_patched_returns": [e.ret for e in m],
        "per_episode_truth_returns": [e.ret for e in t],
        "per_episode_freedom": [e.violations for e in m],
    }
    rows.append(row)
    print(f"persist={persist}: pc_filled={row['play_cost_filled']:.3f} "
          f"pc_patched={row['play_cost_patched']:.3f} "
          f"freedom/ep={row['mean_freedom_points']:.1f}", flush=True)
    print("  per-ep patched:", [round(x, 1) for x in row["per_episode_patched_returns"]], flush=True)
    print("  per-ep truth:  ", [round(x, 1) for x in row["per_episode_truth_returns"]], flush=True)

out = pathlib.Path("results/continuous_ring2d_optimism.json")
out.write_text(json.dumps({"script": "continuous_ring2d_optimism.py",
                           "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
