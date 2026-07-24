"""Active boundary learning (V2-PROGRAM bucket-2c).

The covering law says sealing the ring's reachable arc costs
covering-number-many lessons; the passive argmax planner concedes ~2 per
episode and needed BOTH tangential fence extension and persistence
(Prop 10's (COV) established by luck of geometry). This measures the other
route to (COV): an ACTIVE boundary-tracing probe — after first contact,
alternate tangential advance with radial probing, collecting one lesson per
probe — pays the whole covering cost in ONE episode, after which POINT
fences alone (no nerve extension) satisfy (COV) and the mitigated planner
is truth-equal (Prop 10).

Protocol: episode 0 = the active probe (scripted policy, lessons counted);
episodes 1..15 = plan_mitigated with fence_mode='points' and the
pre-collected fences persisted. Baselines: paired truth-MPC, blind-MPC,
random; PLUS the passive comparison (points+persistent WITHOUT the probe,
i.e. lessons only from the argmax planner's own contacts).

Output: results/ring2d_active_boundary.json. CPU, ~10 min.
"""
import json
import math
import os
import pathlib
import random
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D, blind_of           # noqa: E402
from cwm.continuous import harness                              # noqa: E402
from cwm.continuous.mitigation import run_mitigated_episode     # noqa: E402

EPISODES = 16
EPS_F = 0.5
V_CRUISE = 5.0


def steer(state, wp, v_des):
    x, y, vx, vy = state
    d = math.hypot(wp[0] - x, wp[1] - y) or 1e-9
    phi = math.atan2(v_des * (wp[1] - y) / d - vy,
                     v_des * (wp[0] - x) / d - vx)
    return max(-1.0, min(1.0, phi / math.pi))


def active_probe_episode(truth, model, tol=1e-6):
    """Boundary-tracing probe: head for the ring; after each contact, advance
    the traced angle and probe inward again. Returns the fences collected."""
    rng = random.Random(0)
    s = truth.initial_state(rng)
    cx, cy = truth.center
    fences = []
    theta = math.pi            # first approach: the west face
    for _ in range(truth.h_episode):
        # waypoint just INSIDE the outer boundary at the current trace angle
        wp = (cx + (truth.r_out - 0.5) * math.cos(theta),
              cy + (truth.r_out - 0.5) * math.sin(theta))
        a = steer(s, wp, V_CRUISE)
        s2, _, contact = truth.step(s, a)
        pred, _, _ = model.step(s, a)
        if max(abs(pred[i] - s2[i]) for i in range(len(s2))) > tol:
            fences.append((pred[0], pred[1]))
            theta += 0.22      # lesson learned here: advance along the arc
        s = s2
    return fences


def main():
    truth = RingField2D()                 # closed ring, outside start
    blind = blind_of(truth)
    t0 = time.time()

    # --- active probe: one episode of boundary tracing -------------------
    fences_active = active_probe_episode(truth, blind)
    print(f"active probe: {len(fences_active)} lessons in one episode",
          flush=True)

    rows = []
    for tag, seed_fences in (("active-then-points", list(fences_active)),
                             ("passive-points", [])):
        fences = seed_fences
        t, b, m, r = [], [], [], []
        per_ep = []
        for i in range(EPISODES):
            sd = 1000 * i
            t.append(harness.run_episode(truth, truth, "mpc", sd))
            b.append(harness.run_episode(truth, blind, "mpc", sd))
            ep = run_mitigated_episode(truth, blind, seed=sd, eps=EPS_F,
                                       pos_dims=(0, 1), fence_mode="points",
                                       fences=fences)
            m.append(ep)
            per_ep.append(round(ep.ret, 2))
            r.append(harness.run_episode(truth, policy="random", seed=sd))
        j_t, j_b = harness.mean_return(t), harness.mean_return(b)
        j_m, j_r = harness.mean_return(m), harness.mean_return(r)
        denom = j_t - j_r
        row = {
            "variant": tag, "eps": EPS_F, "n_episodes": EPISODES,
            "n_seed_fences": len(seed_fences and fences_active or []),
            "final_fences": len(fences),
            "j_truth": j_t, "j_blind": j_b, "j_mitigated": j_m,
            "j_random": j_r,
            "play_cost_blind": (j_t - j_b) / denom,
            "play_cost_mitigated": (j_t - j_m) / denom,
            "per_episode_mitigated": per_ep,
            "per_episode_truth": [round(e.ret, 2) for e in t],
        }
        rows.append(row)
        print(f"{tag}: pc_blind={row['play_cost_blind']:.3f} "
              f"pc_mit={row['play_cost_mitigated']:.3f} "
              f"fences {row['n_seed_fences']} -> {row['final_fences']}",
              flush=True)
        print(f"  per-ep mit:   {per_ep}", flush=True)
        print(f"  per-ep truth: {row['per_episode_truth']}", flush=True)

    out = pathlib.Path("results/ring2d_active_boundary.json")
    out.write_text(json.dumps(
        {"script": "ring2d_active_boundary.py", "rows": rows,
         "elapsed_s": round(time.time() - t0, 1)}, indent=2))
    print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)


if __name__ == "__main__":
    main()
