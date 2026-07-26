"""T2 machine check: the hybrid-telescoping identity (Lemma T2-I in
docs/paper3/THEORY.md, "T2 (second pass)"). The full measured
decomposition is scripts/t2_percontact_identity.py; this is the fast
permanent guard on a short horizon with a Markov (per-step-seeded)
planner, where the identity's hypotheses hold exactly."""
import math
import random

from cwm.continuous.envs import RingField2D, blind_of
from cwm.continuous import mpc

# horizon 40 is load-bearing, not a tuning choice: shorter imagined paths
# never reach the phantom, blind and truth then agree everywhere, and the
# identity holds only trivially (the `saw_dirty` guard below catches that).
HOR, NS, BLOCK, H = 40, 16, 10, 8


def _cands(a_max, ep_seed, t):
    rng = random.Random(ep_seed * 100_003 + t)
    return list(mpc._candidates(a_max, rng, HOR, NS, BLOCK, 1))


def _score(model, state, acts):
    s, tot = state, 0.0
    for a in acts:
        s, r, _ = model.step(s, a)
        tot += r
    return tot


def _argmax(model, state, cands):
    best, a0 = -float("inf"), 0.0
    for acts in cands:
        v = _score(model, state, acts)
        if v > best:
            best, a0 = v, acts[0]
    return a0


def _v_truth(truth, state, ep_seed, t_from):
    s, tot = state, 0.0
    for t in range(t_from, H):
        a = _argmax(truth, s, _cands(truth.a_max, ep_seed, t))
        s, r, _ = truth.step(s, a)
        tot += r
    return tot


def test_t2_hybrid_identity_holds_exactly():
    truth = RingField2D(gap=0.6, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    saw_dirty = False
    for ep in range(3):
        ep_seed = 700 + 11 * ep
        s0 = truth.initial_state(random.Random(ep_seed))
        s, j_b, dirty = s0, 0.0, []
        for t in range(H):
            cands = _cands(truth.a_max, ep_seed, t)
            b_t = _argmax(blind, s, cands)
            tau_t = _argmax(truth, s, cands)
            if b_t != tau_t:
                dirty.append((t, s, b_t, tau_t))
            s, r, _ = truth.step(s, b_t)
            j_b += r
        j_t = _v_truth(truth, s0, ep_seed, 0)
        total_a = 0.0
        for t, st_, b_t, tau_t in dirty:
            s_tau, r_tau, _ = truth.step(st_, tau_t)
            s_b, r_b, _ = truth.step(st_, b_t)
            total_a += ((r_tau + _v_truth(truth, s_tau, ep_seed, t + 1))
                        - (r_b + _v_truth(truth, s_b, ep_seed, t + 1)))
        saw_dirty = saw_dirty or bool(dirty)
        assert abs(total_a - (j_t - j_b)) < 1e-9, (ep, total_a, j_t - j_b)
    assert saw_dirty, "identity was only exercised on the trivial case"


def test_t2_clean_steps_contribute_zero():
    # the clean-step half: when blind and truth pick the same action on the
    # shared candidate set, the hybrid difference term is identically 0
    truth = RingField2D(gap=1.2, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    ep_seed, clean_seen = 909, 0
    s = truth.initial_state(random.Random(ep_seed))
    for t in range(H):
        cands = _cands(truth.a_max, ep_seed, t)
        b_t = _argmax(blind, s, cands)
        tau_t = _argmax(truth, s, cands)
        if b_t == tau_t:
            clean_seen += 1
            s_b, r_b, _ = truth.step(s, b_t)
            s_tau, r_tau, _ = truth.step(s, tau_t)
            assert s_b == s_tau and r_b == r_tau     # A_t = 0 identically
        s, _, _ = truth.step(s, b_t)
    assert clean_seen > 0


def test_t2_truth_continuations_never_freeze():
    # The refuted tail hypothesis, kept as a guard: after a dirty step both
    # continuations follow pi_T, and the truth planner knows the mode, so
    # neither ever freezes. Any future claim that the tail is a freeze
    # transient has to get past this.
    truth = RingField2D(gap=0.6, gap_center=math.pi, x0_center=(0.0, 0.0))
    ep_seed = 700
    s = truth.initial_state(random.Random(ep_seed))
    freezes = 0
    for t in range(H):
        a = _argmax(truth, s, _cands(truth.a_max, ep_seed, t))
        s, _, contact = truth.step(s, a)
        freezes += contact
    assert freezes == 0


def test_t2_route_side_is_computable_and_discriminating():
    # Guard for the refuted route-commitment reading: the side-of-ring
    # signature must be well-defined and must actually vary, so the
    # refutation rests on a discriminating measurement rather than on a
    # degenerate one that always returns the same answer.
    truth = RingField2D(gap=0.3, gap_center=math.pi, x0_center=(0.0, 0.0))
    cx, cy = truth.center
    sides = set()
    for ep in range(6):
        ep_seed = 400 + 7 * ep
        s = truth.initial_state(random.Random(ep_seed))
        best_d, best_y = float("inf"), 0.0
        for t in range(H):
            a = _argmax(truth, s, _cands(truth.a_max, ep_seed, t))
            s, _, _ = truth.step(s, a)
            d = math.hypot(s[0] - cx, s[1] - cy)
            if d < best_d:
                best_d, best_y = d, s[1] - cy
        sides.add(1 if best_y >= 0 else -1)
    assert sides == {1, -1}, sides


def test_t2_delay_mechanism_dwell_is_well_defined_and_varies():
    # Guard for the CONFIRMED delay reading: the basin-dwell statistic
    # must be well defined and must actually discriminate between
    # continuations, else the R^2 = 0.93 regression would be degenerate.
    # the basin sits 12 units from the start, so the guard's short horizon
    # never reaches it — use the instrument's own horizon, few episodes
    truth = RingField2D(gap=0.3, gap_center=math.pi, x0_center=(0.0, 0.0))
    cx, cy = truth.center
    dwells = set()
    for ep in range(3):
        ep_seed = 800 + 13 * ep
        s = truth.initial_state(random.Random(ep_seed))
        dwell = 0
        for t in range(truth.h_episode):
            a = _argmax(truth, s, _cands(truth.a_max, ep_seed, t))
            s, _, _ = truth.step(s, a)
            if math.hypot(s[0] - cx, s[1] - cy) < truth.r0:
                dwell += 1
        dwells.add(dwell)
    assert max(dwells) > 0, "the basin must actually be reached"
    assert len(dwells) > 1, dwells          # and the statistic must vary
