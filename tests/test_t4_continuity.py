"""T4 machine checks: the explicit continuity modulus for the gamma-curves
(docs/paper3/THEORY.md, "T4 - the explicit continuity modulus": Lemma S,
Lemma A, Lemma W, Theorem T4). The full validation run is
scripts/t4_continuity_modulus.py; these are the permanent fast guards."""
import math
import random

from cwm.continuous.envs import RingField2D, integrate_2d

ENV = RingField2D()
R_L = ENV.gain * ENV.dt * ENV.dt          # landing-circle radius, Lemma S


def test_t4_landing_circle_exact():
    # Lemma S: the proposed landing is EXACTLY on the circle of radius
    # gain*dt^2 around the drift center, at angle pi*a/a_max.
    beta = 1.0 - ENV.drag * ENV.dt
    rng = random.Random(7)
    for _ in range(300):
        s = (rng.uniform(-20, 20), rng.uniform(-20, 20),
             rng.uniform(-12, 12), rng.uniform(-12, 12))
        a = rng.uniform(-ENV.a_max, ENV.a_max)
        x2, y2, _, _ = integrate_2d(s, a, ENV.dt, ENV.gain, ENV.drag,
                                    ENV.a_max)
        cx, cy = s[0] + beta * s[2] * ENV.dt, s[1] + beta * s[3] * ENV.dt
        phi = math.pi * a / ENV.a_max
        assert abs(x2 - cx - R_L * math.cos(phi)) < 1e-12
        assert abs(y2 - cy - R_L * math.sin(phi)) < 1e-12


def _p_exact(s, R, w):
    # arcsin formula from the Lemma A proof (exact circle-strip probability)
    a = max(-1.0, (-w / 2 - s) / R)
    b = min(1.0, (w / 2 - s) / R)
    return 0.0 if b <= a else (math.asin(b) - math.asin(a)) / math.pi


def test_t4_anticoncentration_bounds():
    R = R_L
    for s_over_R in [0.0, 0.3, 0.6, 0.9, 0.97, 1.0, 1.01, 1.2]:
        for w_over_R in [0.001, 0.01, 0.05, 0.2]:
            s, w = s_over_R * R, w_over_R * R
            p = _p_exact(s, R, w)
            assert p <= math.sqrt(w / (2 * R)) + 1e-12          # (i)
            m = 1.0 - s_over_R
            if 0.0 < m <= 1.0 and w <= m * R:                   # (ii)
                assert p <= 2 * w / (math.pi * R * math.sqrt(3 * m)) + 1e-12
            if s >= R + w / 2:                                  # (iii)
                assert p == 0.0
            if s_over_R == 1.0:                                 # (iv)
                assert p >= math.sqrt(w / R) / math.pi - 1e-12


def test_t4_sliver_in_strip():
    # Lemma W: every point of the sliver (angular offsets (g/2, g/2+eps/2]
    # from gap_center, radii [r_in, r_out]) lies within r_out*eps/4 of the
    # line through the ring center along the sliver's angular bisector.
    gamma, eps = 0.6, 0.2
    rng = random.Random(11)
    for _ in range(500):
        off = rng.uniform(gamma / 2, gamma / 2 + eps / 2)
        off *= rng.choice((1, -1))
        d = rng.uniform(ENV.r_in, ENV.r_out)
        ang = ENV.gap_center + off
        px = ENV.center[0] + d * math.cos(ang)
        py = ENV.center[1] + d * math.sin(ang)
        # the point IS in D(gamma, gamma+eps): mode at gamma, not at g+eps
        assert RingField2D(gap=gamma)._in_mode(px, py)
        assert not RingField2D(gap=gamma + eps)._in_mode(px, py)
        bis = ENV.gap_center + math.copysign(gamma / 2 + eps / 4, off)
        ux, uy = math.cos(bis), math.sin(bis)
        dist = abs(-uy * (px - ENV.center[0]) + ux * (py - ENV.center[1]))
        assert dist <= ENV.r_out * eps / 4 + 1e-12


def test_t4_trajectory_modulus_holds():
    # Theorem T4 end-to-end on a small CRN sample: the sample coupling
    # inequality |delta r_int| <= P(hit D) and the explicit modulus.
    gamma, eps, n = 0.6, 0.2, 200
    lo, hi = RingField2D(gap=gamma), RingField2D(gap=gamma + eps)
    ent_lo = ent_hi = hit = 0
    for i in range(n):
        rng = random.Random(9_000 + i)
        s = lo.initial_state(rng)
        e = h = False
        for _ in range(lo.h_episode):
            a = rng.uniform(-lo.a_max, lo.a_max)
            x2, y2, _, _ = integrate_2d(s, a, lo.dt, lo.gain, lo.drag,
                                        lo.a_max)
            h = h or (lo._in_mode(x2, y2) and not hi._in_mode(x2, y2))
            s, _, _ = lo.step(s, a)
            e = e or lo.in_interior(s[0], s[1])
        ent_lo += e
        hit += h
        rng = random.Random(9_000 + i)
        s = hi.initial_state(rng)
        e = False
        for _ in range(hi.h_episode):
            s, _, _ = hi.step(s, rng.uniform(-hi.a_max, hi.a_max))
            e = e or hi.in_interior(s[0], s[1])
        ent_hi += e
    bound = lo.h_episode * math.sqrt(ENV.r_out * eps / (ENV.gain * ENV.dt ** 2))
    assert abs(ent_hi - ent_lo) / n <= hit / n + 1e-12
    assert hit / n <= bound
