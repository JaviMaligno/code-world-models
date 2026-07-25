"""T2 (open half): what makes the per-contact advantage A_t heavy-tailed?
(docs/paper3/THEORY.md, "T2 (second pass)" and "T2 tail mechanism".)

The identity J_T - J_B = sum over dirty steps of A_t is exact, so a
bound on play_cost needs a bound on A_t. The measured distribution has a
heavy tail (max 11.65 against mean 0.13), which rules out a mean-based
bound. HYPOTHESIS under test: the tail is FREEZE STRADDLING — the two
continuations compared by A_t differ in how many times they freeze, and
a single extra freeze costs a whole transient. If true, the target
theorem changes shape: bound P(straddle) x (freeze transient) rather
than seek a moment bound on A_t.

Per dirty step this records A_t together with the freeze counts of the
two continuations (truth-action branch and blind-action branch), then
reports the correlation between |A_t| and the freeze-count difference,
and the tail's composition.

Run: PYTHONPATH=src python scripts/t2_tail_mechanism.py   (~5 min)
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
    """Follow pi_T from `state`; return (return, freeze count)."""
    s, tot, frz = state, 0.0, 0
    for t in range(t_from, H):
        a = argmax(truth, s, cands(truth.a_max, ep_seed, t))
        s, r, c = truth.step(s, a)
        tot += r
        frz += c
    return tot, frz


def main():
    truth_by_gap, recs = {}, []
    for gap in (0.3, 0.6, 1.2):
        truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        H = truth.h_episode
        truth_by_gap[gap] = truth
        for i in range(EPISODES):
            ep_seed = 4000 + 1000 * i
            s = truth.initial_state(random.Random(ep_seed))
            for t in range(H):
                cset = cands(truth.a_max, ep_seed, t)
                b_t, tau_t = argmax(blind, s, cset), argmax(truth, s, cset)
                if b_t != tau_t:
                    s_tau, r_tau, c_tau = truth.step(s, tau_t)
                    s_b, r_b, c_b = truth.step(s, b_t)
                    v_tau, f_tau = roll_truth(truth, s_tau, ep_seed, t + 1, H)
                    v_b, f_b = roll_truth(truth, s_b, ep_seed, t + 1, H)
                    recs.append({
                        "gap": gap, "episode": i, "t": t,
                        "A": (r_tau + v_tau) - (r_b + v_b),
                        "freeze_tau": f_tau + int(c_tau),
                        "freeze_blind": f_b + int(c_b)})
                s, _, _ = truth.step(s, b_t)
            print(f"gap={gap} ep={i}: {len(recs)} dirty steps so far",
                  flush=True)

    for r in recs:
        r["dfreeze"] = r["freeze_tau"] - r["freeze_blind"]
    absA = sorted((abs(r["A"]) for r in recs), reverse=True)
    cut = absA[max(0, len(absA) // 10 - 1)]          # top decile threshold
    tail = [r for r in recs if abs(r["A"]) >= cut]
    bulk = [r for r in recs if abs(r["A"]) < cut]

    def frac_straddle(rs):
        return sum(1 for r in rs if r["dfreeze"] != 0) / max(1, len(rs))

    # correlation between |A| and |dfreeze|
    xs = [abs(r["dfreeze"]) for r in recs]
    ys = [abs(r["A"]) for r in recs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / n) or 1e-12
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / n) or 1e-12
    corr = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n * sx * sy)

    mean_abs_straddle = (sum(abs(r["A"]) for r in recs if r["dfreeze"] != 0)
                         / max(1, sum(1 for r in recs if r["dfreeze"] != 0)))
    mean_abs_clean = (sum(abs(r["A"]) for r in recs if r["dfreeze"] == 0)
                      / max(1, sum(1 for r in recs if r["dfreeze"] == 0)))
    out = {"n_dirty": n, "tail_cut": cut,
           "straddle_fraction_all": frac_straddle(recs),
           "straddle_fraction_tail": frac_straddle(tail),
           "straddle_fraction_bulk": frac_straddle(bulk),
           "corr_absA_absdfreeze": corr,
           "mean_absA_straddling": mean_abs_straddle,
           "mean_absA_non_straddling": mean_abs_clean,
           "max_absA": absA[0], "records": recs}
    print(f"\ndirty steps: {n}; top-decile cut |A| >= {cut:.3f}")
    print(f"freeze-straddling fraction — all {out['straddle_fraction_all']:.2f}, "
          f"TAIL {out['straddle_fraction_tail']:.2f}, "
          f"bulk {out['straddle_fraction_bulk']:.2f}")
    print(f"corr(|A|, |dfreeze|) = {corr:.3f}")
    print(f"mean |A|: straddling {mean_abs_straddle:.3f} vs "
          f"non-straddling {mean_abs_clean:.3f}")
    p = pathlib.Path("results/t2_tail_mechanism.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
