"""T2: is the heavy tail of A_t a DELAY cost?
(docs/paper3/THEORY.md, "T2 tail mechanism".)

Two readings have been refuted: freeze transients (0/556 freezes) and
route commitment (tail splits the routes LESS than the bulk). The
surviving facts — |A_t| grows with the remaining horizon, concentrates
at narrow gaps, and both continuations take the same route — fit a DELAY
cost: the wrong first action loses time, the return is dominated by time
spent in the phantom basin, and the loss compounds over what is left of
the episode.

That reading makes a sharp, falsifiable prediction, which this measures:
A_t should be explained by the difference in TIME-IN-BASIN between the
two continuations, at the basin's reward rate. Specifically, with
  dwell = #steps with dist(pos, centre) < r0   (the phantom basin),
the prediction is A_t ~ amp_phantom * (dwell_tau - dwell_blind), i.e. a
regression of A_t on the dwell difference with slope near amp_phantom =
1.0 and a high R^2.

If instead R^2 is low, the delay reading joins the other two in the
refuted pile and T2's tail has no mechanism from this family at all.

Run: PYTHONPATH=src python scripts/t2_delay_cost.py   (~3 min)
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
from cwm.continuous import mpc                                  # noqa: E402

HOR, NS, BLOCK = 40, 48, 10
EPISODES = 6
GAPS = (0.3, 0.6)
t0 = time.time()


def cands(a_max, ep_seed, t):
    return list(mpc._candidates(a_max, random.Random(ep_seed * 100_003 + t),
                                HOR, NS, BLOCK, 1))


def argmax(model, state, cset):
    best, a0 = -float("inf"), 0.0
    for acts in cset:
        s, tot = state, 0.0
        for a in acts:
            s, r, _ = model.step(s, a)
            tot += r
        if tot > best:
            best, a0 = tot, acts[0]
    return a0


def roll(truth, state, ep_seed, t_from, H):
    """Follow pi_T; return (return, dwell) with dwell = steps spent inside
    the phantom basin (the reward's r0-radius plateau)."""
    s, tot, dwell = state, 0.0, 0
    cx, cy = truth.center
    for t in range(t_from, H):
        a = argmax(truth, s, cands(truth.a_max, ep_seed, t))
        s, r, _ = truth.step(s, a)
        tot += r
        if math.hypot(s[0] - cx, s[1] - cy) < truth.r0:
            dwell += 1
    return tot, dwell


def main():
    recs = []
    for gap in GAPS:
        truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        H = truth.h_episode
        for i in range(EPISODES):
            ep_seed = 4000 + 1000 * i
            s = truth.initial_state(random.Random(ep_seed))
            for t in range(H):
                cset = cands(truth.a_max, ep_seed, t)
                b_t, tau_t = argmax(blind, s, cset), argmax(truth, s, cset)
                if b_t != tau_t:
                    s_tau, r_tau, _ = truth.step(s, tau_t)
                    s_b, r_b, _ = truth.step(s, b_t)
                    v_tau, d_tau = roll(truth, s_tau, ep_seed, t + 1, H)
                    v_b, d_b = roll(truth, s_b, ep_seed, t + 1, H)
                    recs.append({"gap": gap, "episode": i, "t": t,
                                 "A": (r_tau + v_tau) - (r_b + v_b),
                                 "ddwell": d_tau - d_b,
                                 "dwell_tau": d_tau, "dwell_blind": d_b})
                s, _, _ = truth.step(s, b_t)
            print(f"gap={gap} ep={i}: {len(recs)} dirty steps", flush=True)

    xs = [r["ddwell"] for r in recs]
    ys = [r["A"] for r in recs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
             if sxx > 0 else 0.0)
    icpt = my - slope * mx
    ss_res = sum((y - (icpt + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    absA = sorted((abs(r["A"]) for r in recs), reverse=True)
    cut = absA[max(0, n // 10 - 1)]
    tail = [r for r in recs if abs(r["A"]) >= cut]
    tail_expl = (sum(1 for r in tail if r["ddwell"] != 0) / max(1, len(tail)))
    bulk_expl = (sum(1 for r in recs if abs(r["A"]) < cut
                     and r["ddwell"] != 0)
                 / max(1, n - len(tail)))
    print(f"\ndirty steps {n}; regression A ~ a + b*(dwell_tau - dwell_blind)")
    print(f"  slope {slope:.4f} (amp_phantom = 1.0), intercept {icpt:.4f}, "
          f"R^2 {r2:.4f}")
    print(f"  fraction with a nonzero dwell difference: TAIL {tail_expl:.3f}, "
          f"bulk {bulk_expl:.3f}")
    verdict = ("DELAY COST SUPPORTED" if r2 > 0.5 and 0.5 < slope < 1.6
               else "DELAY COST NOT SUPPORTED — third reading refuted")
    print(f"\n{verdict}")
    p = pathlib.Path("results/t2_delay_cost.json")
    p.write_text(json.dumps({"n": n, "slope": slope, "intercept": icpt,
                             "r2": r2, "tail_nonzero_ddwell": tail_expl,
                             "bulk_nonzero_ddwell": bulk_expl,
                             "verdict": verdict, "records": recs}, indent=1))
    print(f"wrote {p}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
