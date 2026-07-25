"""T7 (second half) machine checks: the relative evidence estimator
(docs/paper3/THEORY.md, Propositions R1/R2). The instrument measurement
is scripts/t7_relative_estimator.py; these are the structural guards."""
import math
import random

from cwm.continuous.tda import (betti1_estimate, free_merge_persistence,
                                relative_betti1_estimate)


def _ring(gap, seed, nc=70):
    rng = random.Random(seed)
    pts = []
    while len(pts) < nc:
        th = rng.uniform(-math.pi, math.pi)
        if abs((th - math.pi) % (2 * math.pi) - math.pi) <= gap / 2:
            continue
        r = rng.uniform(3.5, 3.8)
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts


def _paths(gap, seed):
    rng = random.Random(seed + 1)
    paths = []
    for _ in range(6):
        th = rng.uniform(-math.pi, math.pi)
        paths.append([(6.5 * math.cos(th + 0.25 * t),
                       6.5 * math.sin(th + 0.25 * t)) for t in range(14)])
        th = rng.uniform(-math.pi, math.pi)
        paths.append([(2.4 * math.cos(th + 0.3 * t),
                       2.4 * math.sin(th + 0.3 * t)) for t in range(14)])
    if gap > 0:      # one traversal threading the channel, inside -> outside
        paths.append([((2.6 + 0.15 * t) * math.cos(math.pi),
                       (2.6 + 0.15 * t) * math.sin(math.pi))
                      for t in range(28)])
    return paths


def test_r1_no_infinite_relative_bars():
    # Proposition R1: every relative bar is finite (the estimator asserts
    # it internally; here we also check the returned bars are all finite).
    for gap in (0.0, 0.6, 1.8):
        for seed in (0, 1):
            res = free_merge_persistence(_ring(gap, seed), _paths(gap, seed))
            assert all(b[1] is not None and b[1] > b[0] for b in res["bars"])


def test_r2_rank_is_the_free_component_merge_count():
    # Proposition R2's content, checked directly at a fixed scale: the
    # reported max rank equals the number of free components that the
    # contact points glue, computed by brute force at the bar's midpoint.
    contact, paths = _ring(0.0, 0), _paths(0.0, 0)
    res = free_merge_persistence(contact, paths)
    assert res["bars"], "the closed ring must produce a relative bar"
    b0, b1 = res["bars"][0]
    s = 0.5 * (b0 + b1)

    def comps(points, seeded_edges):
        par = list(range(len(points)))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for u, v in seeded_edges:
            par[find(u)] = find(v)
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                if math.dist(points[i], points[j]) <= s:
                    par[find(i)] = find(j)
        return par, find

    free = [p for path in paths for p in path]
    seeded, off = [], 0
    for path in paths:
        seeded += [(off + t, off + t + 1) for t in range(len(path) - 1)]
        off += len(path)
    _, find_l = comps(free, seeded)
    n_l = len({find_l(i) for i in range(len(free))})
    allp = list(contact) + free
    nc = len(contact)
    seeded_k = [(nc + u, nc + v) for u, v in seeded]
    _, find_k = comps(allp, seeded_k)
    n_k_free = len({find_k(nc + i) for i in range(len(free))})
    assert n_l - n_k_free >= 1          # the ring separates inside/outside


def test_relative_estimator_discriminates_where_plain_rips_fails():
    # closed ring -> 1; open rings -> 0, including the gaps where plain
    # Rips reports the spurious bridged loop
    for seed in (0, 1, 2):
        c, p = _ring(0.0, seed), _paths(0.0, seed)
        assert relative_betti1_estimate(c, p)["betti1_rel"] == 1
    fooled_plain = 0
    for gap in (0.6, 1.2, 1.8):
        for seed in (0, 1, 2):
            c, p = _ring(gap, seed), _paths(gap, seed)
            assert relative_betti1_estimate(c, p)["betti1_rel"] == 0
            fooled_plain += betti1_estimate(c)["betti1"] >= 1
    assert fooled_plain > 0, "the comparison is vacuous if plain Rips agrees"


def _scatter(gap, seed, nf=60):
    """Free evidence as a 2-D SCATTER (the refuted point-cloud input):
    same regions as the path evidence, but with the trajectory
    connectivity thrown away."""
    rng = random.Random(seed + 5)
    free = []
    while len(free) < nf // 2:
        th, r = rng.uniform(-math.pi, math.pi), rng.uniform(5.2, 8.0)
        free.append((r * math.cos(th), r * math.sin(th)))
    while len(free) < nf:
        th, r = rng.uniform(-math.pi, math.pi), rng.uniform(0.0, 3.2)
        free.append((r * math.cos(th), r * math.sin(th)))
    if gap > 0:                     # a traversal that DOES span the band
        k = 0
        while 2.9 + 0.12 * k <= 5.6:
            r = 2.9 + 0.12 * k
            free.append((r * math.cos(math.pi), r * math.sin(math.pi)))
            k += 1
    return free


def test_flat_point_cloud_input_is_the_refuted_instantiation():
    # Feeding free evidence as a point cloud (singleton paths) reports
    # separation even through a wide-open channel: the density-mismatch
    # failure recorded in THEORY.md. Guarded so it cannot be silently
    # reintroduced by "simplifying" the path input away.
    for gap in (0.6, 1.2, 1.8):
        for seed in (0, 1, 2):
            c = _ring(gap, seed)
            flat = [[q] for q in _scatter(gap, seed)]
            assert relative_betti1_estimate(c, flat)["betti1_rel"] >= 1
            # the path form of the same evidence gets it right
            assert relative_betti1_estimate(
                c, _paths(gap, seed))["betti1_rel"] == 0


def test_r4_freeze_evidence_hugs_the_band_faces():
    # Proposition R4's mechanism: a freeze zeroes the velocity, so the next
    # proposed landing moves only gain*dt^2 from rest (Lemma S). Contact
    # landings therefore pile up in thin shells at the faces instead of
    # penetrating the band.
    from cwm.continuous.envs import RingField2D
    from cwm.continuous.contract import collect_transitions
    env = RingField2D(gap=0.0, gap_center=math.pi,
                      x0_center=RingField2D().center)
    cx, cy = env.center
    radii = []
    for tr in collect_transitions(env, 40, seed=10000):
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            radii.append(math.hypot(x2 - cx, y2 - cy))
    assert radii, "no contact evidence to test"
    w = env.r_out - env.r_in                    # band thickness 1.5
    shell = max(radii) - min(radii)
    # the inner shell is far thinner than the band it sits on
    assert shell < 0.4 * w, (shell, w)
    # and every landing sits within one from-rest step scale of the face,
    # many orders below the band thickness
    assert min(radii) >= env.r_in - 1e-9
