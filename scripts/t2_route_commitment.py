"""T2: is the heavy tail of A_t really ROUTE COMMITMENT?
(docs/paper3/THEORY.md, "T2 tail mechanism".)

The freeze-transient explanation is refuted (0/556 freezes). The
replacement reading — that a large A_t means the one bad first action
commits the truth-following continuation to the other way around the
annulus — was an INTERPRETATION consistent with two correlations
(remaining horizon, channel narrowness), not a measurement. This tests
it directly.

For every dirty step we run both continuations under pi_T and record
which side of the ring each passes on: the sign of y at the point of
closest approach to the ring centre. Route commitment predicts that the
tail events are exactly the ones where the two continuations take
OPPOSITE sides, and the bulk are same-side.

Prediction if true:  P(opposite | tail) >> P(opposite | bulk).
Prediction if false: the two are comparable, and the tail is something
else — in which case the cut-locus target for the open half is wrong
and must be renamed.

Run: PYTHONPATH=src python scripts/t2_route_commitment.py   (~10 min)
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
GAPS = (0.3, 0.6)          # the tail concentrates at narrow gaps
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


def roll_truth(truth, state, ep_seed, t_from, H):
    """Follow pi_T; return (return, side) where side = sign of y at the
    closest approach to the ring centre (which way it goes round)."""
    s, tot = state, 0.0
    best_d, best_y = float("inf"), 0.0
    cx, cy = truth.center
    for t in range(t_from, H):
        a = argmax(truth, s, cands(truth.a_max, ep_seed, t))
        s, r, _ = truth.step(s, a)
        tot += r
        d = math.hypot(s[0] - cx, s[1] - cy)
        if d < best_d:
            best_d, best_y = d, s[1] - cy
    return tot, (1 if best_y >= 0 else -1), best_d


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
                    v_tau, side_tau, d_tau = roll_truth(truth, s_tau,
                                                        ep_seed, t + 1, H)
                    v_b, side_b, d_b = roll_truth(truth, s_b, ep_seed,
                                                  t + 1, H)
                    recs.append({
                        "gap": gap, "episode": i, "t": t,
                        "A": (r_tau + v_tau) - (r_b + v_b),
                        "opposite_sides": side_tau != side_b,
                        "closest_tau": d_tau, "closest_blind": d_b})
                s, _, _ = truth.step(s, b_t)
            print(f"gap={gap} ep={i}: {len(recs)} dirty steps", flush=True)

    absA = sorted((abs(r["A"]) for r in recs), reverse=True)
    cut = absA[max(0, len(absA) // 10 - 1)]
    tail = [r for r in recs if abs(r["A"]) >= cut]
    bulk = [r for r in recs if abs(r["A"]) < cut]

    def frac(rs):
        return sum(1 for r in rs if r["opposite_sides"]) / max(1, len(rs))

    p_tail, p_bulk = frac(tail), frac(bulk)
    out = {"n_dirty": len(recs), "tail_cut": cut,
           "p_opposite_tail": p_tail, "p_opposite_bulk": p_bulk,
           "n_tail": len(tail), "n_bulk": len(bulk),
           "mean_absA_opposite":
               sum(abs(r["A"]) for r in recs if r["opposite_sides"])
               / max(1, sum(1 for r in recs if r["opposite_sides"])),
           "mean_absA_same":
               sum(abs(r["A"]) for r in recs if not r["opposite_sides"])
               / max(1, sum(1 for r in recs if not r["opposite_sides"])),
           "records": recs}
    print(f"\ndirty steps {len(recs)}; top-decile cut |A| >= {cut:.3f}")
    print(f"P(opposite sides | TAIL) = {p_tail:.3f}  (n={len(tail)})")
    print(f"P(opposite sides | bulk) = {p_bulk:.3f}  (n={len(bulk)})")
    print(f"mean |A|: opposite {out['mean_absA_opposite']:.3f} vs "
          f"same-side {out['mean_absA_same']:.3f}")
    verdict = ("ROUTE COMMITMENT SUPPORTED" if p_tail > 2 * p_bulk + 0.05
               else "ROUTE COMMITMENT NOT SUPPORTED — rename the target")
    print(f"\n{verdict}")
    out["verdict"] = verdict
    p = pathlib.Path("results/t2_route_commitment.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
