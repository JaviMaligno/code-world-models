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
