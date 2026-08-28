"""T3: the non-circular decomposition of the direct-entry probability
(docs/paper3/THEORY.md, "T3 — the original ingredient").

"Bound P(prefix)" turned out to be circular: a launch state is defined as
one from which the remaining actions enter, so P(reach a launch state)
IS d by definition. This script measures a decomposition that is NOT
circular, because two of its three factors are properties of the
RING-FREE dynamics and therefore do not mention the entry event at all:

    d(gamma) = R  x  [ integral of the arrival-angle density over the
                       channel ]  x  T(gamma)

  R      = P(a ring-free rollout ever reaches the band radius r_out).
           gamma-independent; a Theta(1) hitting probability, which is
           exactly what Lemma J's two-action steering bounds below.
  rho(.) = density of the FIRST-ARRIVAL angle at radius r_out under the
           ring-free dynamics. gamma-independent.
  T      = throughput: given first arrival inside the channel sector,
           the fraction that go on to reach the interior. The only
           gamma-dependent factor.

Reports each factor separately, checks that their product reproduces the
directly measured d, and fits T(gamma) so the residual exponent is
attributed rather than absorbed.

Run: PYTHONPATH=src python scripts/t3_reach_density_throughput.py
"""
import json
import math
import os
import pathlib
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                      # noqa: E402

GAPS = [0.05, 0.1, 0.2, 0.3, 0.4, 0.6]
N_RING_FREE = 120_000
N_ENTRY = 200_000
CX, CY = 12.0, 0.0


def ring_free_arrivals(n):
    """First-arrival angle at radius r_out under the RING-FREE dynamics."""
    env = RingField2D(gap=0.0, r_in=None)
    angs = []
    for i in range(n):
        rng = random.Random(50_000 + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, _ = env.step(s, a)
            if math.hypot(s[0] - CX, s[1] - CY) <= env.r_out:
                angs.append(math.atan2(s[1] - CY, s[0] - CX))
                break
    return angs


def direct_entries(gap, n):
    """(d, arrivals-in-channel, entries-among-those) for the true ring."""
    env = RingField2D(gap=gap)
    d = arrivals = through = 0
    for i in range(n):
        rng = random.Random(50_000 + i)
        s = env.initial_state(rng)
        froze = in_ch = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, c = env.step(s, a)
            if c:
                froze = True
                break
            r = math.hypot(s[0] - CX, s[1] - CY)
            if not in_ch and r <= env.r_out:
                th = math.atan2(s[1] - CY, s[0] - CX)
                off = abs((th - math.pi + math.pi) % (2 * math.pi) - math.pi)
                if off <= gap / 2:
                    in_ch = True
                    arrivals += 1
            if env.in_interior(s[0], s[1]):
                d += 1
                through += in_ch
                break
        del froze
    return d / n, arrivals, through


def main():
    angs = ring_free_arrivals(N_RING_FREE)
    R = len(angs) / N_RING_FREE
    # density of the arrival angle at pi, over a window wide enough to be
    # stable but narrower than the smallest channel
    w = 0.05
    k = sum(1 for a in angs
            if abs((a - math.pi + math.pi) % (2 * math.pi) - math.pi) <= w)
    dens = k / len(angs) / (2 * w)
    print(f"ring-free reach probability R      = {R:.5f}  "
          f"(gamma-INDEPENDENT, n={N_RING_FREE})")
    print(f"arrival-angle density at pi        = {dens:.4f} per rad "
          f"(n={k} in a {2 * w:.2f} rad window)")
    print(f"\n{'gamma':>6} {'d measured':>11} {'R*dens*gamma':>13} "
          f"{'throughput T':>13} {'T from counts':>14}")
    rows = []
    for g in GAPS:
        d, arr, thr = direct_entries(g, N_ENTRY)
        pred = R * dens * g
        T = d / pred if pred > 0 else 0.0
        T_counts = thr / arr if arr else float("nan")
        rows.append({"gap": g, "d": d, "R_dens_gamma": pred,
                     "throughput_ratio": T, "arrivals": arr,
                     "through": thr, "throughput_counts": T_counts})
        print(f"{g:6.2f} {d:11.6f} {pred:13.6f} {T:13.4f} {T_counts:14.4f}")
    pos = [r for r in rows if r["throughput_ratio"] > 0]
    xs = [math.log(r["gap"]) for r in pos]
    ys = [math.log(r["throughput_ratio"]) for r in pos]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
             / sum((x - mx) ** 2 for x in xs))
    print(f"\nthroughput T(gamma) log-log slope: {slope:.3f}")
    print(f"  => d ~ R * dens * gamma^(1+{slope:.2f}) = gamma^{1 + slope:.2f}"
          f"  (directly measured exponent was 1.72)")
    out = {"R": R, "R_n": N_RING_FREE, "density_at_pi": dens,
           "density_window": 2 * w, "rows": rows,
           "throughput_slope": slope, "N_entry": N_ENTRY}
    p = pathlib.Path("results/t3_reach_density_throughput.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
