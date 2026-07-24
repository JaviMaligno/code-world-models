"""T6: hidden-channel reachability at gamma = 0.6 within h = 80.

The hand controller threads the 1.2 channel (100/100) but not 0.6: the
entry corridor at gamma = 0.6 requires lateral error < r*0.3 (1.05 units at
r_in, 1.5 at r_out) at the end of a ~30-unit route around the ring. This
searches a parameterized waypoint controller (positions + per-leg cruise
speeds + entry runway) for ANY parameter vector that enters the interior —
a machine-checked reachability witness settling T6's dichotomy positively.
A failed search is recorded as a negative search, NOT an impossibility
claim.

Controller family: 4 waypoints (around the ring, alignment runway, entry),
per-leg cruise speeds, velocity-aware steering (the witness-tube pattern).
Search: coarse random search around the hand template, then local
refinement of the best. Success = interior entry (d < r_in) within
h_episode on the TRUE dynamics, from the standard start distribution.

Output: results/t6_hidden06_witness.json (parameters + entry rate over 100
seeds for the best controller). CPU, ~minutes.
"""
import json
import math
import os
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402

ENV = RingField2D(gap=0.6, gap_center=0.0, x0_center=(0.0, 0.0))
CX, CY = ENV.center


def steer(state, wp, v_des):
    x, y, vx, vy = state
    d = math.hypot(wp[0] - x, wp[1] - y) or 1e-9
    phi = math.atan2(v_des * (wp[1] - y) / d - vy,
                     v_des * (wp[0] - x) / d - vx)
    return max(-1.0, min(1.0, phi / math.pi))


def run(params, seed):
    """params: [x1,y1,v1, x2,y2,v2, x3,y3,v3, v4] — three waypoints with
    speeds plus the entry speed toward the ring center."""
    wps = [((params[0], params[1]), params[2]),
           ((params[3], params[4]), params[5]),
           ((params[6], params[7]), params[8]),
           ((CX, CY), params[9])]
    rng = random.Random(seed)
    s = ENV.initial_state(rng)
    wp_i = 0
    for _ in range(ENV.h_episode):
        wp, v = wps[wp_i]
        if math.hypot(s[0] - wp[0], s[1] - wp[1]) < 2.0:
            wp_i = min(wp_i + 1, len(wps) - 1)
            wp, v = wps[wp_i]
        s, _, _ = ENV.step(s, steer(s, wp, v))
        if math.hypot(s[0] - CX, s[1] - CY) < ENV.r_in:
            return True
    return False


def entry_rate(params, seeds):
    return sum(run(params, sd) for sd in seeds) / len(seeds)


# hand template (the 1.2-channel witness route) + search ranges
TEMPLATE = [11.5, 7.0, 6.0, 17.0, 4.0, 6.0, 19.0, 0.0, 5.0, 3.5]
RANGES = [(9, 14), (5, 9), (4, 8),      # wp1
          (15, 20), (2, 7), (4, 8),     # wp2
          (16, 22), (-1.5, 1.5), (3, 7),  # wp3 (alignment)
          (2.0, 6.0)]                   # entry speed


def main():
    rnd = random.Random(0)
    probe_seeds = list(range(1000, 1010))       # 10-seed screen
    best, best_rate = list(TEMPLATE), entry_rate(TEMPLATE, probe_seeds)
    print(f"template rate (10 seeds): {best_rate:.2f}", flush=True)

    # coarse random search
    for it in range(400):
        cand = [rnd.uniform(lo, hi) for lo, hi in RANGES]
        rate = entry_rate(cand, probe_seeds)
        if rate > best_rate:
            best, best_rate = cand, rate
            print(f"[{it}] rate {rate:.2f}  {['%.2f' % v for v in cand]}",
                  flush=True)
        if best_rate == 1.0:
            break

    # local refinement
    for it in range(300):
        cand = [max(lo, min(hi, b + rnd.gauss(0, 0.4)))
                for b, (lo, hi) in zip(best, RANGES)]
        rate = entry_rate(cand, probe_seeds)
        if rate > best_rate:
            best, best_rate = cand, rate
            print(f"[refine {it}] rate {rate:.2f}", flush=True)
        if best_rate == 1.0 and it > 50:
            break

    final_seeds = list(range(1000, 1100))
    final_rate = entry_rate(best, final_seeds)
    print(f"\nBEST controller: rate {final_rate:.2f} over 100 seeds")
    print("params:", [round(v, 3) for v in best])

    out = {"gamma": 0.6, "channel": "hidden", "h_episode": ENV.h_episode,
           "params": best, "entry_rate_100": final_rate,
           "screen_rate": best_rate,
           "verdict": ("WITNESS FOUND" if final_rate > 0
                       else "NEGATIVE SEARCH (not an impossibility proof)")}
    with open("results/t6_hidden06_witness.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote results/t6_hidden06_witness.json")


if __name__ == "__main__":
    main()
