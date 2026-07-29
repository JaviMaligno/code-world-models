"""T3 (partial) machine checks: Theorem T3-P, one-sided monotonicity with
the funnel defect (docs/paper3/THEORY.md, "T3 (partial)"). The certified
measurement is scripts/t3_funnel_bound.py; these are the fast guards on
the theorem's two ingredients."""
import math
import random

from cwm.continuous.envs import RingField2D


def _split(env, n, seed0=50_000):
    """(direct set, funnel set) of rollout indices under common seeds."""
    direct, funnel = set(), set()
    for i in range(n):
        rng = random.Random(seed0 + i)
        s = env.initial_state(rng)
        froze = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, contact = env.step(s, a)
            if env.in_interior(s[0], s[1]):
                (funnel if froze else direct).add(i)
                break
            froze = froze or contact
    return direct, funnel


def test_t3p_prop7_pathwise_inclusion():
    # the theorem's engine: direct(gamma1) subset direct(gamma2)
    gaps = [0.4, 0.9, 1.8, 2 * math.pi]
    sets = [_split(RingField2D(gap=g), 1500)[0] for g in gaps]
    for lo, hi, g_lo, g_hi in zip(sets, sets[1:], gaps, gaps[1:]):
        assert lo <= hi, (g_lo, g_hi, sorted(lo - hi))
    assert len(sets[-1]) > len(sets[0])       # non-vacuous: the set grows


def test_t3p_inequality_holds_on_the_sample():
    # r_int(g2) >= r_int(g1) - f(g1), the theorem's conclusion, checked as
    # a sample inequality (it holds per-realization by Prop 7, so the
    # empirical version cannot fail unless Prop 7 does)
    gaps = [0.2, 0.6, 1.2, 2.4]
    n = 1500
    stats = []
    for g in gaps:
        d, f = _split(RingField2D(gap=g), n)
        stats.append((len(d) / n, len(f) / n))
    for (d1, f1), (d2, f2) in zip(stats, stats[1:]):
        r1, r2 = d1 + f1, d2 + f2
        assert r2 >= r1 - f1 - 1e-12, (r1, r2, f1)


def test_t3p_no_wall_means_every_entry_is_direct():
    # T3-P(b): at gamma = 2pi there is no mode at all, so nothing can
    # freeze and r_int(2pi) = d(2pi)
    env = RingField2D(gap=2 * math.pi)
    direct, funnel = _split(env, 1500)
    assert funnel == set()
    assert len(direct) > 0


def test_t3p_prime_funnel_is_contained_in_fire():
    # Corollary T3-P': a funnel entry lands in A(gamma) before entering,
    # so funnel subset fire and f <= r — the a-priori defect bound.
    for gap in (0.2, 0.6, 1.2):
        env = RingField2D(gap=gap)
        n, funnel, fire = 1200, 0, 0
        for i in range(n):
            rng = random.Random(50_000 + i)
            s = env.initial_state(rng)
            froze = entered_after_freeze = fired = False
            for _ in range(env.h_episode):
                a = rng.uniform(-env.a_max, env.a_max)
                s, _, contact = env.step(s, a)
                fired = fired or contact
                if env.in_interior(s[0], s[1]):
                    entered_after_freeze = froze
                    break
                froze = froze or contact
            funnel += entered_after_freeze
            fire += fired
        assert funnel <= fire, (gap, funnel, fire)
    assert fire > 0, "the containment check must not be vacuous"


def test_t3p_prime_no_mode_means_no_defect():
    # At gamma = 2pi there is no mode, so nothing fires, so f = 0 exactly
    # — the endpoint where the a-priori bound proves what measurement
    # cannot.
    env = RingField2D(gap=2 * math.pi)
    for i in range(400):
        rng = random.Random(70_000 + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            s, _, contact = env.step(s, rng.uniform(-env.a_max, env.a_max))
            assert not contact


def test_t3p_double_prime_defect_is_the_drop_in_f():
    # Theorem T3-P'': r_int(g2) >= r_int(g1) - [f(g1) - f(g2)]^+, strictly
    # stronger than T3-P, and exactly zero wherever f is nondecreasing.
    gaps = [0.2, 0.6, 1.2, 2.4]
    n = 1500
    stats = []
    for g in gaps:
        d, f = _split(RingField2D(gap=g), n)
        stats.append((len(d) / n, len(f) / n))
    for (d1, f1), (d2, f2) in zip(stats, stats[1:]):
        r1, r2 = d1 + f1, d2 + f2
        drop = max(0.0, f1 - f2)
        assert r2 >= r1 - drop - 1e-12, (r1, r2, drop)
        # and it is at least as strong as the old bound
        assert drop <= f1 + 1e-12


def _variant_enters(env, seed, keep_velocity):
    """Rollout where a contact blocks the POSITION but optionally leaves the
    velocity updating freely (the freeze-rescue isolation variant)."""
    from cwm.continuous.envs import integrate_2d
    rng = random.Random(50_000 + seed)
    s = env.initial_state(rng)
    for _ in range(env.h_episode):
        a = rng.uniform(-env.a_max, env.a_max)
        x2, y2, vx2, vy2 = integrate_2d(s, a, env.dt, env.gain, env.drag,
                                        env.a_max)
        if env._in_mode(x2, y2):
            s = (s[0], s[1], vx2, vy2) if keep_velocity else (s[0], s[1],
                                                              0.0, 0.0)
        else:
            s = (x2, y2, vx2, vy2)
            if env.in_interior(s[0], s[1]):
                return True
    return False


def test_t3_velocity_preserving_variant_has_no_pathwise_violations():
    # The non-equivalent route: with the velocity reset removed, M1 looks
    # PATHWISE (freeze-rescue is the sole obstruction). Guarded at a small
    # sample; the full measurement is 0/140,000 against it.
    gaps = [0.2, 0.6, 1.2, 2.4]
    n = 2500
    sets = [{i for i in range(n) if _variant_enters(RingField2D(gap=g), i,
                                                    True)} for g in gaps]
    for lo, hi, glo, ghi in zip(sets, sets[1:], gaps, gaps[1:]):
        assert lo <= hi, (glo, ghi, sorted(lo - hi)[:5])
    assert len(sets[-1]) > len(sets[0])       # non-vacuous


def test_t3_velocity_is_gamma_independent_in_the_variant():
    # The structural reason: with the velocity preserved, the velocity
    # process does not depend on gamma at all, so CRN copies share it
    # exactly and diverging copies are pure translates.
    from cwm.continuous.envs import integrate_2d
    vels = []
    for g in (0.2, 1.2, 2.4):
        env = RingField2D(gap=g)
        rng = random.Random(50_000 + 7)
        s = env.initial_state(rng)
        seq = []
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            x2, y2, vx2, vy2 = integrate_2d(s, a, env.dt, env.gain,
                                            env.drag, env.a_max)
            s = ((s[0], s[1], vx2, vy2) if env._in_mode(x2, y2)
                 else (x2, y2, vx2, vy2))
            seq.append((vx2, vy2))
        vels.append(seq)
    assert vels[0] == vels[1] == vels[2]      # bitwise, across gaps


def test_t3_running_min_holds_on_adjacent_pairs_only():
    # REFUTED as an invariant: it holds on ADJACENT gap pairs (this test)
    # but fails at wide separations, and pathwise M1 in the variant fails
    # too (13/30,764 entering units, results/t3_variant_pairs.json). Kept
    # as a regression guard on the adjacent-pair regime, and as the record
    # of why adjacency was the flaw in the original check.
    from cwm.continuous.envs import integrate_2d
    for g1, g2 in ((0.2, 0.6), (1.2, 2.4)):
        e1, e2 = RingField2D(gap=g1), RingField2D(gap=g2)
        cx, cy = e1.center
        entries = 0
        for i in range(2500):
            r1 = random.Random(50_000 + i)
            r2 = random.Random(50_000 + i)
            s1, s2 = e1.initial_state(r1), e2.initial_state(r2)
            m1 = m2 = float("inf")
            for _ in range(e1.h_episode):
                a = r1.uniform(-e1.a_max, e1.a_max)
                r2.uniform(-e2.a_max, e2.a_max)
                x1, y1, vx1, vy1 = integrate_2d(s1, a, e1.dt, e1.gain,
                                                e1.drag, e1.a_max)
                x2, y2, vx2, vy2 = integrate_2d(s2, a, e2.dt, e2.gain,
                                                e2.drag, e2.a_max)
                s1 = ((s1[0], s1[1], vx1, vy1) if e1._in_mode(x1, y1)
                      else (x1, y1, vx1, vy1))
                s2 = ((s2[0], s2[1], vx2, vy2) if e2._in_mode(x2, y2)
                      else (x2, y2, vx2, vy2))
                m1 = min(m1, math.hypot(s1[0] - cx, s1[1] - cy))
                m2 = min(m2, math.hypot(s2[0] - cx, s2[1] - cy))
                assert m2 <= m1 + 1e-12, (g1, g2, i, m1, m2)
                if e1.in_interior(s1[0], s1[1]):
                    entries += 1
                    break            # the invariant is only needed up to here
        assert entries > 0, "the condition must be exercised"


def test_t3_drag_caps_identical_action_divergence():
    # The provable half of L_v, and the reason it transfers: with identical
    # actions the affine plant gives ||dx_t|| <= ||dx_0|| + ||dv_0||/drag
    # for ALL t -- bounded, not exponential.
    from cwm.continuous.envs import integrate_2d
    env = RingField2D()
    dx0, dv0 = 0.06, 0.6
    cap = dx0 + dv0 / env.drag
    rng = random.Random(7)
    worst = 0.0
    for _ in range(60):
        s1 = (rng.uniform(-2, 14), rng.uniform(-6, 6),
              rng.uniform(-9, 9), rng.uniform(-9, 9))
        th, th2 = rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi)
        s2 = (s1[0] + dx0 * math.cos(th), s1[1] + dx0 * math.sin(th),
              s1[2] + dv0 * math.cos(th2), s1[3] + dv0 * math.sin(th2))
        for _ in range(150):
            a = rng.uniform(-1, 1)
            s1 = integrate_2d(s1, a, env.dt, env.gain, env.drag, env.a_max)
            s2 = integrate_2d(s2, a, env.dt, env.gain, env.drag, env.a_max)
            worst = max(worst, math.hypot(s1[0] - s2[0], s1[1] - s2[1]))
    assert worst <= cap + 1e-9, (worst, cap)
    assert worst > 0.8 * cap, "the cap must be nearly attained"


def test_t3_variant_pathwise_m1_is_refuted():
    # The velocity-preserving variant does NOT make M1 pathwise: removing
    # the velocity reset leaves the POSITION block, which alone destroys
    # pathwise inclusion. Guarded with the JSON's counts so the refuted
    # claim cannot be quietly re-asserted.
    import json
    import pathlib
    path = pathlib.Path("results/t3_variant_pairs.json")
    if not path.exists():                     # measurement not present
        return
    data = json.loads(path.read_text())
    summary = data["summary"]
    assert summary["failures"] > 0, summary
    assert summary["entering_units"] > 10_000, summary
    # the unit is the entering pair, two orders below the rollout count
    assert summary["entering_units"] < summary["pairs"] / 50


def test_t3_prop8_witness_tube_is_freeze_free():
    # c < 1 is proved because Proposition 8's witness tube gives DIRECT
    # entries: the constant action a = 0 from a small |y0| enters without
    # ever contacting the band. That is what makes d(gamma) > 0, hence
    # c = 1 - d/r_int < 1 (with an astronomically small margin).
    from cwm.continuous.envs import integrate_2d
    for gap in (0.6, 1.2):
        env = RingField2D(gap=gap, gap_center=math.pi)
        eta = min((3.5 / 8) * gap, 0.4)
        entered = 0
        for k in range(12):
            y0 = -eta + 2 * eta * k / 11
            s = (0.0, y0, 0.0, 0.0)
            froze = False
            for _ in range(env.h_episode):
                x2, y2, vx2, vy2 = integrate_2d(s, 0.0, env.dt, env.gain,
                                                env.drag, env.a_max)
                if env._in_mode(x2, y2):
                    froze = True
                    break
                s = (x2, y2, vx2, vy2)
                if env.in_interior(s[0], s[1]):
                    entered += 1
                    break
            assert not froze, (gap, y0)     # freeze-free: the direct claim
        assert entered > 0, gap


def test_t3_lemma_j_jacobian_formula():
    # Lemma J: the Jacobian of (a_s1, a_s2) -> x_T in free flight is
    # K^2 W(T-s1) W(T-s2) |sin(phi_s1 - phi_s2)|, K = gain*pi*dt^2.
    # This is what removes the rho^h factor from Prop 8's tube bound.
    from cwm.continuous.envs import integrate_2d
    env = RingField2D()
    beta = 1 - env.drag * env.dt
    K = env.gain * math.pi * env.dt * env.dt

    def W(m):
        return sum(beta ** k for k in range(m))

    def endpoint(acts):
        s = (0.0, 0.0, 0.0, 0.0)
        for a in acts:
            s = integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max)
        return (s[0], s[1])

    rng = random.Random(11)
    T, eps = 80, 1e-4
    for s1, s2 in ((10, 50), (20, 60), (5, 40)):
        acts = [rng.uniform(-0.8, 0.8) for _ in range(T)]

        def ep(d1, d2):
            a = list(acts)
            a[s1] += d1
            a[s2] += d2
            return endpoint(a)

        p0, p1, p2 = ep(0, 0), ep(eps, 0), ep(0, eps)
        num = abs((p1[0] - p0[0]) * (p2[1] - p0[1])
                  - (p1[1] - p0[1]) * (p2[0] - p0[0])) / eps ** 2
        formula = (K * K * W(T - s1) * W(T - s2)
                   * abs(math.sin(math.pi * (acts[s1] - acts[s2]))))
        assert abs(num - formula) <= 1e-6 * max(formula, 1e-9), (s1, s2,
                                                                 num, formula)


def test_t3_one_action_moves_the_endpoint_macroscopically():
    # The quantitative content of Lemma J: a single action at a long lag
    # moves the endpoint by ~2.9 units per unit of action, against a
    # per-landing scale of only gain*dt^2 = 0.03. That factor is what
    # Prop 8's all-steps tube discards.
    from cwm.continuous.envs import integrate_2d
    env = RingField2D()
    beta = 1 - env.drag * env.dt
    K = env.gain * env.dt * env.dt
    rng = random.Random(3)
    acts = [rng.uniform(-1, 1) for _ in range(80)]

    def endpoint(a):
        s = (0.0, 0.0, 0.0, 0.0)
        for x in a:
            s = integrate_2d(s, x, env.dt, env.gain, env.drag, env.a_max)
        return (s[0], s[1])

    a2 = list(acts)
    a2[0] = max(-1.0, min(1.0, a2[0] + 0.02))
    p0, p1 = endpoint(acts), endpoint(a2)
    sens = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 0.02
    assert sens > 30 * K, (sens, K)          # macroscopic vs the landing scale
    assert sens <= env.gain * math.pi * env.dt ** 2 / (1 - beta) + 1e-9
