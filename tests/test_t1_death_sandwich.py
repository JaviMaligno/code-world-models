"""T1 machine checks: the death sandwich (Lemmas B, D-, D+ in
docs/paper3/THEORY.md, "T1 - the proofs"). Full factorial validation is
scripts/t1_death_sandwich.py (57/57); these are fast synthetic guards
where the cloud geometry is controlled exactly."""
import math
import random

from cwm.continuous.tda import rips_persistence

SQ3 = math.sqrt(3)


def _cloud(n, gap, seed, r_lo=3.5, r_hi=3.8):
    """Points on an annulus [r_lo, r_hi] with an angular gap at pi."""
    rng = random.Random(seed)
    pts = []
    while len(pts) < n:
        th = rng.uniform(-math.pi, math.pi)
        if abs((th - math.pi) % (2 * math.pi) - math.pi) <= gap / 2:
            continue
        r = rng.uniform(r_lo, r_hi)
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts


def _geometry(pts):
    radii = [math.hypot(*p) for p in pts]
    angs = sorted(math.atan2(p[1], p[0]) % (2 * math.pi) for p in pts)
    gaps = sorted((b - a for a, b in zip(angs, angs[1:])), reverse=True)
    gaps.append(angs[0] + 2 * math.pi - angs[-1])
    gaps.sort(reverse=True)
    return min(radii), max(radii), gaps[0], gaps[1]


def _theta_star(dmax, d2):
    cands = []
    if dmax <= 2 * math.pi / 3 and d2 < math.pi / 3:
        cands.append(2 * math.pi / 3 + d2)
    if d2 < dmax < math.pi:
        th = max(dmax, (2 * math.pi - dmax) / 2 + d2 / 2)
        if d2 <= th / 2:
            cands.append(th)
    return min(cands) if cands else None


def test_t1_sandwich_on_synthetic_clouds():
    for gap in (0.0, 0.6, 1.2, 1.8):
        for seed in (1, 2):
            pts = _cloud(60, gap, seed)
            r_min, r_max, dmax, d2 = _geometry(pts)
            th = _theta_star(dmax, d2)
            assert th is not None and th <= math.pi
            b_lo = 2 * r_min * math.sin(dmax / 2)
            b_hi = 2 * r_max * math.sin(dmax / 2)
            d_lo, d_hi = SQ3 * r_min, 2 * r_max * math.sin(th / 2)
            bars = rips_persistence(pts)["h1"]
            # Lemma P: exactly one bar spans the window [B+, sqrt3*r_min)
            if b_hi < d_lo:
                r0 = sum(1 for b, d in bars
                         if b <= b_hi + 1e-9 and (d is None or d >= d_lo - 1e-9))
                assert r0 == 1, (gap, seed, r0)
            wind = None
            for b, d in bars:
                if d is not None and 0.95 * b_lo <= b <= 1.05 * b_hi:
                    if wind is None or (d - b) > (wind[1] - wind[0]):
                        wind = (b, d)
            assert wind is not None, (gap, seed)     # dense: bar exists
            assert d_lo - 1e-9 <= wind[1] <= d_hi + 1e-9, (gap, seed, wind)


def test_t1_theta_star_regimes():
    # regime (i): small gaps -> theta* = 2pi/3 + d2
    assert abs(_theta_star(0.3, 0.1) - (2 * math.pi / 3 + 0.1)) < 1e-12
    # regime (ii) at large gap: flanker triangle governs
    th = _theta_star(2.5, 0.2)
    assert abs(th - max(2.5, (2 * math.pi - 2.5) / 2 + 0.1)) < 1e-12
    # both applicable -> the smaller wins
    th = _theta_star(1.8, 0.2)
    assert th == min(2 * math.pi / 3 + 0.2,
                     max(1.8, (2 * math.pi - 1.8) / 2 + 0.1))


def test_t1_exact_circle_death_near_sqrt3():
    # dense even circle: death within [sqrt3*r, 2r sin(pi/3 + d2/2)], and
    # numerically close to the Adamaszek-Adams constant sqrt3*r
    n, r = 90, 3.65
    pts = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
           for k in range(n)]
    bars = [b for b in rips_persistence(pts)["h1"] if b[1] is not None]
    b, d = max(bars, key=lambda x: x[1] - x[0])
    assert SQ3 * r - 1e-9 <= d <= 2 * r * math.sin(math.pi / 3 + 2 * math.pi / n)
    assert abs(d / r - SQ3) < 0.15
