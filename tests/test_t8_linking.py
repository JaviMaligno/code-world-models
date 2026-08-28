"""T8 machine checks: the linking dichotomy for the non-separating mode
(docs/paper3/THEORY.md, "T8 - the linking dichotomy": Lemma X, Lemma Y,
Theorem T8). Full validation with the Gauss-integral cross-check is
scripts/t8_linking_dichotomy.py; these are the permanent fast guards."""
import math
import random

from cwm.continuous.envs import TubeField3D

ENV0 = TubeField3D()
ENV15 = TubeField3D(core_yz=(1.5, 0.0))
RHO = ENV0.tube_radius
DELTA = (ENV0.gain / ENV0.drag) * ENV0.dt      # max step length = 1.0
CX, RC = ENV0.core_x, ENV0.core_radius
M = RHO - DELTA / 2                            # clearance margin


def _subdivide(waypoints, step):
    pts = [tuple(waypoints[0])]
    for a, b in zip(waypoints, waypoints[1:]):
        n = max(1, math.ceil(math.dist(a, b) / step))
        for k in range(1, n + 1):
            pts.append(tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)))
    return pts


def _thread(pts, env):
    n = 0
    for a, b in zip(pts, pts[1:]):
        if (a[0] - CX) * (b[0] - CX) < 0:
            t = (CX - a[0]) / (b[0] - a[0])
            q = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            if math.hypot(q[1] - env.core_yz[0], q[2] - env.core_yz[1]) < RC:
                n += 1 if b[0] > a[0] else -1
    return n


def test_t8_lemma_x_clearance():
    # whenever a (densely sampled) interpolation point dips into the
    # shrunken tube {g <= rho - Delta/2}, some landing is in the tube
    rng = random.Random(81)
    triggered = 0
    for _ in range(150):
        env = TubeField3D(core_yz=(rng.uniform(-2, 2), 0.0))
        pts = [(rng.uniform(4, 12), rng.uniform(-4, 4), rng.uniform(-4, 4))]
        for _ in range(25):
            v = [rng.uniform(-1, 1) for _ in range(3)]
            nv = math.sqrt(sum(c * c for c in v)) or 1.0
            step = rng.uniform(0, DELTA)
            pts.append(tuple(p + c / nv * step for p, c in zip(pts[-1], v)))
        hit = any(env.dist_core(tuple(a[i] + (b[i] - a[i]) * k / 20
                                      for i in range(3))) <= RHO - DELTA / 2
                  for a, b in zip(pts, pts[1:]) for k in range(21))
        if hit:
            triggered += 1
            assert any(env.dist_core(p) <= RHO for p in pts)
    assert triggered > 5    # the oracle actually exercised the hypothesis


def test_t8_witnesses_every_class_is_query_free():
    # Theorem T8(b): landing-free plans exist with thread 1 and 0, at the
    # aligned AND the dangerous offset geometry
    cases = [
        (ENV0, [(0, 0, 0), (12, 0, 0)], 1),
        (ENV15, [(0, 0, 0), (0, 1.5, 0), (12, 1.5, 0), (12, 0, 0)], 1),
        (ENV15, [(0, 0, 0), (0, 6, 0), (12, 6, 0), (12, 0, 0)], 0),
    ]
    for env, route, expect in cases:
        pts = _subdivide(route, 0.97 * DELTA)   # generic: no landing on x=c_x
        assert all(abs(p[0] - CX) > 1e-9 for p in pts)
        assert min(env.dist_core(p) for p in pts) > RHO
        assert _thread(pts, env) == expect


def test_t8_corridor_minimum_is_exact():
    # T8(d): min of g along the straight start->phantom segment = |o - R_c|,
    # attained at x = c_x; the registered offset 1.5 sits AT the margin
    for o in [0.0, 1.0, 1.5, 1.75]:
        env = TubeField3D(core_yz=(o, 0.0))
        assert abs(env.dist_core((CX, 0.0, 0.0)) - abs(o - RC)) < 1e-12
    assert abs(TubeField3D(core_yz=(1.5, 0.0)).dist_core((CX, 0.0, 0.0))
               - M) < 1e-12


def test_t8_real_paths_freeze_out_and_use_the_hole_gate():
    # T8(c): real positions never enter the tube, and every real-path
    # crossing of the spanning disc goes through the clearance sub-disc
    for env in (ENV0, ENV15):
        crossings = 0
        for i in range(40):
            rng = random.Random(9_100 + i)
            s = env.initial_state(rng)
            pos = [s[:3]]
            for _ in range(env.h_episode):
                a = (rng.uniform(0.3, env.a_max),           # east-biased
                     rng.uniform(-env.a_max, env.a_max),
                     rng.uniform(-env.a_max, env.a_max))
                s, _, _ = env.step(s, a)
                pos.append(s[:3])
            assert all(env.dist_core(p) > RHO for p in pos)
            for p, q in zip(pos, pos[1:]):
                if (p[0] - CX) * (q[0] - CX) < 0:
                    t = (CX - p[0]) / (q[0] - p[0])
                    w = tuple(p[i] + (q[i] - p[i]) * t for i in range(3))
                    dyz = math.hypot(w[1] - env.core_yz[0],
                                     w[2] - env.core_yz[1])
                    assert not (RC - M <= dyz <= RC)
                    crossings += 1
        assert crossings > 5    # the gate check was exercised
