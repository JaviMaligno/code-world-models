"""TubeField3D mechanism (V2-PROGRAM 2d): the non-separating dichotomy.

Two configs, everything else frozen:
  aligned (core_yz=(0,0)):  the straight start->phantom plan THREADS the hole
  offset  (core_yz=(1.5,0)): the straight plan CLIPS the tube

Measured per config: r (random-rollout contact rarity, 600 rollouts) and
pc_blind (16 paired vector-MPC episodes, axial candidates). Expected: the
danger dichotomy WITHOUT any separation — obstruction is a property of the
optimal path; what a separating mode adds is only the exact-gauge side.

Run: PYTHONPATH=src python scripts/tubefield_mechanism.py  (~10 min)
"""
import json
import pathlib
import random
import time

from cwm.continuous.envs import TubeField3D, blind_of
from cwm.continuous import harness

t0 = time.time()
rows = []
for tag, off in (("aligned", (0.0, 0.0)), ("offset", (1.5, 0.0))):
    truth = TubeField3D(core_yz=off)
    hits = 0
    for i in range(600):
        rng = random.Random(80_000 + i)
        s = truth.initial_state(rng)
        for _ in range(truth.h_episode):
            a = tuple(rng.uniform(-1, 1) for _ in range(3))
            s, _, c = truth.step(s, a)
            if c:
                hits += 1
                break
    # paired MPC arms via harness (mpc.plan reads action_dim from the
    # model); the random arm needs VECTOR actions, which harness's random
    # branch does not draw — local runner, mirroring the shellfield scripts.
    def random_episode(seed):
        rng = random.Random(seed)
        s = truth.initial_state(rng)
        tot = 0.0
        for _ in range(truth.h_episode):
            a = tuple(rng.uniform(-1, 1) for _ in range(3))
            s, rr, _ = truth.step(s, a)
            tot += rr
        return tot

    tt, bb, rrs = [], [], []
    blind = blind_of(truth)
    contact_n = 0
    for i in range(16):
        sd = 1000 * i
        tt.append(harness.run_episode(truth, truth, "mpc", sd))
        ep = harness.run_episode(truth, blind, "mpc", sd)
        bb.append(ep)
        contact_n += ep.contact
        rrs.append(random_episode(sd))
    j_t = harness.mean_return(tt)
    j_b = harness.mean_return(bb)
    j_r = sum(rrs) / len(rrs)
    row = {"config": tag, "core_yz": off, "r": hits / 600,
           "j_truth": j_t, "j_blind": j_b, "j_random": j_r,
           "play_cost_blind": (j_t - j_b) / (j_t - j_r),
           "blind_contact": contact_n / 16}
    rows.append(row)
    print(f"{tag}: r={row['r']:.4f} pc_blind={row['play_cost_blind']:.3f} "
          f"contact={row['blind_contact']:.2f} "
          f"J_t={row['j_truth']:.2f} J_b={row['j_blind']:.2f}", flush=True)

out = pathlib.Path("results/tubefield_mechanism.json")
out.write_text(json.dumps({"script": "tubefield_mechanism.py", "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time()-t0,1)}s]", flush=True)
