"""T2 second pass: the per-contact decomposition as an exact identity
(docs/paper3/THEORY.md, "T2 (second pass)": Lemma T2-I).

Hybrid-telescoping check with MARKOV (per-step-seeded) planners: per
episode, J(pi_T) - J(pi_B) must equal the sum of the dirty steps'
advantage terms A_t exactly (clean steps contribute 0 by the clean-step
lemma). The identity is planner-config-agnostic, but the PHENOMENON is
not: horizon 40 is required for imagined paths to reach the phantom at
all (a horizon-20 pilot produced 0 dirty steps in 18/18 episodes — the
danger itself needs the lure in view). Config: horizon=40, n_samples=48;
per-gap partial results are written incrementally.

Reported per gap: identity residual (max |sum A_t - (J_T - J_B)|), dirty
counts, and the A_t distribution (mean/max/negative fraction) — the
measured per-contact cost that the open a-priori half must bound.

Run: PYTHONPATH=src python scripts/t2_percontact_identity.py  (~5 min)
"""
import json
import math
import os
import random
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D, blind_of           # noqa: E402
from cwm.continuous import mpc                                  # noqa: E402

HOR, NS, BLOCK = 40, 48, 10
EPISODES = 6
OUT = "results/t2_percontact_identity.json"
t0 = time.time()


def candidates(a_max, ep_seed, t):
    """Per-(episode, step) seeded candidate set: the Markov planner."""
    rng = random.Random(ep_seed * 100_003 + t)
    return list(mpc._candidates(a_max, rng, HOR, NS, BLOCK, 1))


def argmaxes(blind, truth, state, cands):
    """Blind and truth argmax first-actions over the SHARED candidate set."""
    best_b = best_t = -float("inf")
    a_b = a_t = 0.0
    for acts in cands:
        sb, tb = state, 0.0
        st, tt = state, 0.0
        for a in acts:
            sb, rb, _ = blind.step(sb, a)
            tb += rb
            st, rt, _ = truth.step(st, a)
            tt += rt
        if tb > best_b:
            best_b, a_b = tb, acts[0]
        if tt > best_t:
            best_t, a_t = tt, acts[0]
    return a_b, a_t


def truth_argmax(truth, state, cands):
    best, a0 = -float("inf"), 0.0
    for acts in cands:
        s, tot = state, 0.0
        for a in acts:
            s, r, _ = truth.step(s, a)
            tot += r
        if tot > best:
            best, a0 = tot, acts[0]
    return a0


def v_truth(truth, state, ep_seed, t_from, h_episode):
    """Return of following pi_T from `state` at step index t_from."""
    s, tot = state, 0.0
    for t in range(t_from, h_episode):
        a = truth_argmax(truth, s, candidates(truth.a_max, ep_seed, t))
        s, r, _ = truth.step(s, a)
        tot += r
    return tot


def main():
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    # resume key includes the planner config: changing horizon/samples
    # invalidates old rows instead of silently skipping the re-run
    rows = [r for r in rows if r["planner"]["horizon"] == HOR
            and r["planner"]["n_samples"] == NS]
    done = {r["gap"] for r in rows}
    for gap in (0.3, 0.6, 1.2):
        if gap in done:
            continue
        truth = RingField2D(gap=gap, gap_center=math.pi,
                            x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        H = truth.h_episode
        residuals, a_terms, dirty_counts = [], [], []
        for i in range(EPISODES):
            ep_seed = 4000 + 1000 * i
            s0 = truth.initial_state(random.Random(ep_seed))
            # pi_B trajectory, recording per-step argmaxes on shared cands
            s, j_b = s0, 0.0
            dirty = []      # (t, s_t, b_t, tau_t)
            for t in range(H):
                cands = candidates(truth.a_max, ep_seed, t)
                b_t, tau_t = argmaxes(blind, truth, s, cands)
                if b_t != tau_t:
                    dirty.append((t, s, b_t, tau_t))
                s2, r, _ = truth.step(s, b_t)
                j_b += r
                s = s2
            j_t = v_truth(truth, s0, ep_seed, 0, H)
            total_a = 0.0
            for t, st_, b_t, tau_t in dirty:
                s_tau, r_tau, _ = truth.step(st_, tau_t)
                s_b, r_b, _ = truth.step(st_, b_t)
                a_t = ((r_tau + v_truth(truth, s_tau, ep_seed, t + 1, H))
                       - (r_b + v_truth(truth, s_b, ep_seed, t + 1, H)))
                a_terms.append(a_t)
                total_a += a_t
            residuals.append(abs(total_a - (j_t - j_b)))
            dirty_counts.append(len(dirty))
            print(f"gap={gap} ep={i}: dirty {len(dirty)}/{H}, "
                  f"J_T-J_B={j_t - j_b:+.4f}, sum A_t={total_a:+.4f}, "
                  f"residual {residuals[-1]:.2e}", flush=True)
        assert max(residuals) < 1e-9, residuals
        neg = sum(1 for a in a_terms if a < 0)
        rows.append({
            "gap": gap, "episodes": EPISODES, "planner":
                {"horizon": HOR, "n_samples": NS, "block": BLOCK,
                 "seeding": "per (episode, step)"},
            "max_identity_residual": max(residuals),
            "dirty_per_episode": dirty_counts,
            "A": {"n": len(a_terms),
                  "mean": sum(a_terms) / max(1, len(a_terms)),
                  "max": max(a_terms, default=0.0),
                  "min": min(a_terms, default=0.0),
                  "negative_fraction": neg / max(1, len(a_terms))}})
        tmp = OUT + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rows, f, indent=1)
        os.replace(tmp, OUT)
    for r in rows:
        print(f"gap={r['gap']}: residual {r['max_identity_residual']:.1e}, "
              f"dirty {r['dirty_per_episode']}, A mean "
              f"{r['A']['mean']:+.4f} max {r['A']['max']:+.3f} "
              f"neg-frac {r['A']['negative_fraction']:.2f}")
    print(f"wrote {OUT}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
