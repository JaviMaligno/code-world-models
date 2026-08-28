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


def test_t2_quantitative_clean_step_chain():
    # The corrected chain: V_T(tc) - V_T(bc) <= [V_T(tc)-V_B(tc)]^+ + Delta_over.
    # Forced by V_B(bc) >= V_B(tc); the first term is what my initial
    # attempt dropped (it holds only ~half the time without it), so the
    # guard checks BOTH that the full chain holds and that the truncated
    # one genuinely fails — otherwise the correction would be untested.
    truth = RingField2D(gap=0.3, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    full_ok = trunc_fail = dirty = 0
    s = truth.initial_state(random.Random(700))
    for t in range(H):
        cs = _cands(truth.a_max, 700, t)
        bc = max(cs, key=lambda acts: _score(blind, s, acts))
        tc = max(cs, key=lambda acts: _score(truth, s, acts))
        if bc[0] != tc[0]:
            dirty += 1
            over = _score(blind, s, bc) - _score(truth, s, bc)
            excess = max(0.0, _score(truth, s, tc) - _score(blind, s, tc))
            gap = _score(truth, s, tc) - _score(truth, s, bc)
            full_ok += gap <= over + excess + 1e-9
            trunc_fail += gap > over + 1e-9
        s, _, _ = truth.step(s, bc[0])
    assert dirty > 0
    assert full_ok == dirty, (full_ok, dirty)
    assert trunc_fail > 0, "the dropped term must actually be needed"


def test_t2d_imagination_data_does_not_determine_A():
    # Proposition T2-D, by construction: pin the state and the candidate set
    # at a dirty step -- so every imagination-level quantity is fixed -- and
    # vary only the FUTURE planner seeds. If A_t moves, no function of the
    # imagination data can bound it tightly.
    truth = RingField2D(gap=0.6, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    # the real horizon is load-bearing: with the guard's short H nothing
    # reaches the basin and A_t is identically 0 for every future seed
    HH = truth.h_episode
    es = 4000
    s = truth.initial_state(random.Random(es))
    found = None
    for t in range(HH):
        cs = _cands(truth.a_max, es, t)
        b = max(cs, key=lambda a: _score(blind, s, a))
        tc = max(cs, key=lambda a: _score(truth, s, a))
        if b[0] != tc[0]:
            found = (t, s, b, tc)
            break
        s, _, _ = truth.step(s, b[0])
    assert found is not None
    t, s, b, tc = found

    def roll(state, futseed):
        tot = 0.0
        for k in range(t + 1, HH):
            cs = _cands(truth.a_max, futseed, k)
            a = max(cs, key=lambda acts: _score(truth, state, acts))
            state, r, _ = truth.step(state, a[0])
            tot += r
        return tot

    vals = []
    for fut in range(4):
        s_t, r_t, _ = truth.step(s, tc[0])
        s_b, r_b, _ = truth.step(s, b[0])
        vals.append((r_t + roll(s_t, 7000 + fut))
                    - (r_b + roll(s_b, 7000 + fut)))
    assert max(vals) - min(vals) > 0.5, vals   # A_t genuinely varies


def test_t2_lemma_s_caps_the_one_action_perturbation():
    # The reduction behind the non-vacuous bound: by Lemma S the two
    # post-step states of a dirty step differ by at most 2*gain*dt^2 in
    # position and 2*gain*dt in velocity, whatever the two actions are.
    truth = RingField2D(gap=0.6, gap_center=math.pi, x0_center=(0.0, 0.0))
    cap_p = 2 * truth.gain * truth.dt ** 2
    cap_v = 2 * truth.gain * truth.dt
    rng = random.Random(41)
    seen_large = False
    for _ in range(300):
        s = (rng.uniform(-2, 14), rng.uniform(-6, 6),
             rng.uniform(-10, 10), rng.uniform(-10, 10))
        a1 = rng.uniform(-truth.a_max, truth.a_max)
        a2 = rng.uniform(-truth.a_max, truth.a_max)
        s1, _, c1 = truth.step(s, a1)
        s2, _, c2 = truth.step(s, a2)
        if c1 or c2:
            continue                     # freezes are a different branch
        dp = math.hypot(s1[0] - s2[0], s1[1] - s2[1])
        dv = math.hypot(s1[2] - s2[2], s1[3] - s2[3])
        assert dp <= cap_p + 1e-12, (dp, cap_p)
        assert dv <= cap_v + 1e-12, (dv, cap_v)
        seen_large = seen_large or dv > 0.5 * cap_v
    assert seen_large, "the caps must be exercised near their value"


def test_t2_argmax_angle_is_dominated_by_independent_uniform():
    # The dominance claim behind the non-vacuous bound: |sin((phi_tau -
    # phi_b)/2)| over dirty steps is stochastically dominated by its value
    # for two INDEPENDENT uniform actions (mean 2/pi). Checked as CDF
    # dominance, plus the mean, on a small sample.
    import bisect
    vals = []
    for gap in (0.3, 0.6):
        truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        for ep in range(2):
            es = 4000 + 1000 * ep
            s = truth.initial_state(random.Random(es))
            for t in range(truth.h_episode):
                cs = _cands(truth.a_max, es, t)
                b = max(cs, key=lambda a: _score(blind, s, a))[0]
                tau = max(cs, key=lambda a: _score(truth, s, a))[0]
                if b != tau:
                    vals.append(abs(math.sin(math.pi * (tau - b) / 2)))
                s, _, _ = truth.step(s, b)
    assert len(vals) > 30, len(vals)
    rng = random.Random(1)
    ref = sorted(abs(math.sin(math.pi * (rng.uniform(-1, 1)
                                         - rng.uniform(-1, 1)) / 2))
                 for _ in range(20000))
    vals.sort()
    for q in (i / 20 for i in range(1, 20)):
        f_m = bisect.bisect_right(vals, q) / len(vals)
        f_r = bisect.bisect_right(ref, q) / len(ref)
        assert f_m >= f_r - 0.12, (q, f_m, f_r)     # sampling slack
    assert sum(vals) / len(vals) <= 2 / math.pi + 0.05


def test_t2_angle_mean_bound_is_facing_only():
    # The scoped claim: E|sin((phi_tau - phi_b)/2)| <= 2/pi holds for a
    # FACING channel and fails for a HIDDEN one, where the two argmaxes are
    # near-antipodal and every step deviates. Guards the scope, so the
    # bound cannot be quoted without it.
    ref = 2 / math.pi
    means = {}
    for channel, centre in (("facing", math.pi), ("hidden", 0.0)):
        truth = RingField2D(gap=0.6, gap_center=centre, x0_center=(0.0, 0.0))
        blind = blind_of(truth)
        vals, steps = [], 0
        for ep in range(2):
            es = 4000 + 1000 * ep
            s = truth.initial_state(random.Random(es))
            for t in range(truth.h_episode):
                cs = _cands(truth.a_max, es, t)
                b = max(cs, key=lambda a: _score(blind, s, a))[0]
                tau = max(cs, key=lambda a: _score(truth, s, a))[0]
                steps += 1
                if b != tau:
                    vals.append(abs(math.sin(math.pi * (tau - b) / 2)))
                s, _, _ = truth.step(s, b)
        means[channel] = (sum(vals) / len(vals), len(vals) / steps)
    assert means["facing"][0] < ref, means
    assert means["hidden"][0] > ref, means
    # and in the hidden configuration essentially every step deviates
    assert means["hidden"][1] > 0.9, means
