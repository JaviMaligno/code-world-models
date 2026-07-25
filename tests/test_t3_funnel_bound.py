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
