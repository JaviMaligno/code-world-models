"""The hidden-channel steering witness (THEORY.md ledger item, deferred).

Claim to ground: hidden-channel r_int(gamma) > 0 is policy-relative — the
gate policy (uniform-random) enters the interior at a rate below measurement,
but an explicit scripted policy that knows the channel enters reliably. This
turns the "two grades of impossibility" remark into a measured witness:
certifiability is relative to the query policy rho; a different policy
shrinks the gauge region.

Policy: waypoint steering. From the outside start, fly around the ring
(north -> east) and enter westward through the hidden channel (gap_center =
0, i.e. the ring opening faces AWAY from the start, at angle 0 from the ring
center c = (12, 0)). Heading action a = atan2(dy, dx)/pi (the instrument's
scalar-heading interface, full thrust).

Cells:
  - hidden gamma in {0.6, 1.2}: steered entry rate (expect >> 0)
  - gamma = 0 (closed): steered entry rate (MUST be 0 — Lemma 2, a theorem)
  - random-policy control at hidden gamma (the gate policy; expect 0 at this
    budget, matching the gamma-probe)

Output: results/ring2d_steering_witness.json. CPU, deterministic, seconds.
"""
import json
import math
import os
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402

N_EPISODES = 100
# (waypoint, cruise speed): fast around the ring, slower for the aligned
# westward entry through the hidden channel (narrow channels need a small
# lateral error during the crossing).
WAYPOINTS = [((11.5, 7.0), 6.0), ((17.0, 4.0), 6.0), ((17.5, 0.0), 6.0),
             ((12.0, 0.0), 6.0)]
WAYPOINT_TOL = 2.0


def steer_action(state, wp, v_des):
    """Velocity-aware steering: thrust along (v_desired - v), where
    v_desired points at the waypoint at the leg's cruise speed. The naive
    point-at-waypoint controller orbits (thrust cannot turn the velocity
    fast enough); this one converges."""
    x, y, vx, vy = state
    d = math.hypot(wp[0] - x, wp[1] - y) or 1e-9
    vdx = v_des * (wp[0] - x) / d
    vdy = v_des * (wp[1] - y) / d
    phi = math.atan2(vdy - vy, vdx - vx)
    return max(-1.0, min(1.0, phi / math.pi))


def run_steered(env, seed):
    """One steered episode; returns True iff the trajectory enters the open
    interior (d < r_in)."""
    rng = random.Random(seed)
    s = env.initial_state(rng)
    wp_i = 0
    for _ in range(env.h_episode):
        wp, v_des = WAYPOINTS[wp_i]
        if math.hypot(s[0] - wp[0], s[1] - wp[1]) < WAYPOINT_TOL:
            wp_i = min(wp_i + 1, len(WAYPOINTS) - 1)
            wp, v_des = WAYPOINTS[wp_i]
        s, _, _ = env.step(s, steer_action(s, wp, v_des))
        if math.hypot(s[0] - env.center[0], s[1] - env.center[1]) < env.r_in:
            return True
    return False


def run_random(env, seed):
    rng = random.Random(seed)
    s = env.initial_state(rng)
    for _ in range(env.h_episode):
        a = rng.uniform(-env.a_max, env.a_max)
        s, _, _ = env.step(s, a)
        if math.hypot(s[0] - env.center[0], s[1] - env.center[1]) < env.r_in:
            return True
    return False


def main():
    rows = []
    for gap, policy in [(0.6, "steered"), (1.2, "steered"),
                        (0.0, "steered"),
                        (0.6, "random"), (1.2, "random")]:
        env = RingField2D(gap=gap, gap_center=0.0, x0_center=(0.0, 0.0))
        run = run_steered if policy == "steered" else run_random
        hits = sum(run(env, 1000 + i) for i in range(N_EPISODES))
        rows.append({"gap": gap, "channel": "hidden", "policy": policy,
                     "episodes": N_EPISODES, "interior_entries": hits,
                     "entry_rate": hits / N_EPISODES})
        print(f"gap={gap} {policy:>8}: {hits}/{N_EPISODES} interior entries")
    out = "results/ring2d_steering_witness.json"
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rows, f, indent=1)
    os.replace(tmp, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
