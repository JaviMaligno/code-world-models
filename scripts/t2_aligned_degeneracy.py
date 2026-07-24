"""T2: the aligned-channel degeneracy as a proved conditional theorem.

LEMMA (argmax-clean steps): fix a real state s and the deterministic
candidate enumeration. Truth imagination and blind imagination assign the
SAME return to every candidate whose imagined path never lands in A (the
models agree off A), and truth assigns NO MORE than blind to every touching
candidate (freezing replaces free phantom-basin rewards by the frozen
position's smaller reward... verified per-candidate below rather than
assumed). Hence if the BLIND argmax candidate's imagined path is A-free and
truth scores no touching candidate above it, the two planners select the
same action. If that holds at every step of an episode, the blind-planned
and truth-planned episodes are IDENTICAL realization-by-realization, and
that episode contributes 0 to play_cost.

This script machine-checks the lemma at gamma in {0.3, 0.6, 1.2} (facing):
it replays the paired episodes, marks each step 'clean' (blind argmax
A-free AND truth-argmax equal) and asserts BITWISE equality of the full
episode whenever all steps are clean; play_cost residual is attributed to
the episodes with dirty steps. Output: results/t2_aligned_degeneracy.json.
"""
import json
import math
import os
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D, blind_of           # noqa: E402
from cwm.continuous import mpc                                  # noqa: E402

EPISODES = 16


def argmax_with_path(model, truth, state, rng, horizon=40, n_samples=200,
                     block=10):
    """mpc.plan, faithfully mirrored, ALSO returning whether the argmax
    candidate's imagined path touches A (under the TRUTH's geometry) and
    the truth-imagination argmax action for comparison."""
    best_b, a0_b, touch_b = -float("inf"), 0.0, False
    best_t, a0_t = -float("inf"), 0.0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block, 1):
        sb, tot_b, touched = state, 0.0, False
        st, tot_t = state, 0.0
        for a in acts:
            sb, rb, _ = model.step(sb, a)
            if not touched and truth._in_mode(sb[0], sb[1]):
                touched = True
            tot_b += rb
            st, rt, _ = truth.step(st, a)
            tot_t += rt
        if tot_b > best_b:
            best_b, a0_b, touch_b = tot_b, acts[0], touched
        if tot_t > best_t:
            best_t, a0_t = tot_t, acts[0]
    return a0_b, touch_b, a0_t


def main():
    out = []
    for gap in (0.3, 0.6, 1.2):
        truth = RingField2D(gap=gap, gap_center=math.pi,
                            x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        clean_eps = dirty_eps = 0
        identical_when_clean = 0
        ret_gap_dirty = []
        for i in range(EPISODES):
            sd = 1000 * i
            # paired: replay BOTH planners with the same seed and compare
            rng_b, rng_t = random.Random(sd), random.Random(sd)
            s_b = truth.initial_state(rng_b)
            s_t = truth.initial_state(rng_t)
            tot_b = tot_t = 0.0
            all_clean = True
            for _ in range(truth.h_episode):
                a_b, touched, a_t_of_b = argmax_with_path(
                    blind, truth, s_b, rng_b)
                a_t = mpc.plan(truth, s_t, rng_t)
                if touched or a_b != a_t_of_b:
                    all_clean = False
                s_b, r_b, _ = truth.step(s_b, a_b)
                tot_b += r_b
                s_t, r_t, _ = truth.step(s_t, a_t)
                tot_t += r_t
            if all_clean:
                clean_eps += 1
                identical_when_clean += (tot_b == tot_t
                                         and tuple(s_b) == tuple(s_t))
            else:
                dirty_eps += 1
                ret_gap_dirty.append(round(tot_t - tot_b, 3))
        row = {"gap": gap, "episodes": EPISODES, "clean": clean_eps,
               "dirty": dirty_eps,
               "bitwise_identical_of_clean":
                   f"{identical_when_clean}/{clean_eps}",
               "truth_minus_blind_on_dirty": ret_gap_dirty}
        out.append(row)
        print(f"gap={gap}: clean {clean_eps}/{EPISODES}, of which bitwise "
              f"identical {identical_when_clean}/{clean_eps}; dirty return "
              f"gaps {ret_gap_dirty}", flush=True)

    with open("results/t2_aligned_degeneracy.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote results/t2_aligned_degeneracy.json")


if __name__ == "__main__":
    main()
