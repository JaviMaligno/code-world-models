"""Ground-truth tests for the minimal Rips persistence module (paper-3 TDA
arm). Clouds with known homology; the circle's Rips H1 death at sqrt(3)*R is
the classical value, asserted loosely."""
import math
import random

from cwm.continuous.tda import (betti1_estimate, dedupe, median_nn_distance,
                                rips_persistence, subsample)


def circle(n, r=1.0, cx=0.0, cy=0.0, jitter=0.0, seed=0):
    rng = random.Random(seed)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        pts.append((cx + r * math.cos(a) + rng.uniform(-jitter, jitter),
                    cy + r * math.sin(a) + rng.uniform(-jitter, jitter)))
    return pts


def test_circle_has_one_persistent_h1_bar():
    pts = circle(40)
    res = rips_persistence(pts)
    finite = [b for b in res["h1"] if b[1] is not None]
    assert finite, "circle must produce a finite H1 bar"
    top = max(finite, key=lambda b: b[1] - b[0])
    assert abs(top[0] - 2 * math.sin(math.pi / 40)) < 1e-9   # birth = spacing
    assert abs(top[1] - math.sqrt(3)) < 0.05                 # Rips circle death
    assert betti1_estimate(pts)["betti1"] == 1


def test_grid_has_no_persistent_h1():
    pts = [(i * 0.5, j * 0.5) for i in range(5) for j in range(5)]
    assert betti1_estimate(pts)["betti1"] == 0


def test_two_clusters_h0():
    pts = circle(8, r=0.3) + circle(8, r=0.3, cx=10.0)
    res = rips_persistence(pts)
    inf_bars = [b for b in res["h0"] if b[1] is None]
    assert len(inf_bars) == 1
    finite = sorted((b[1] for b in res["h0"] if b[1] is not None),
                    reverse=True)
    assert finite[0] > 9.0          # the cluster-merge bar
    assert finite[1] < 0.5          # everything else is intra-cluster


def test_noisy_circle_and_arc_are_distinguished():
    noisy = circle(60, r=4.0, jitter=0.15, seed=3)
    assert betti1_estimate(noisy)["betti1"] == 1
    # a 120-degree arc of the same circle: no loop
    arc = [(4 * math.cos(a), 4 * math.sin(a))
           for a in [2 * math.pi / 3 * k / 40 for k in range(41)]]
    assert betti1_estimate(arc)["betti1"] == 0


def test_helpers():
    pts = [(0.0, 0.0), (0.011, 0.011), (1.0, 1.0)]
    assert len(dedupe(pts, grid=0.05)) == 2
    assert len(subsample(list(range(100)), 10)) == 10
    assert median_nn_distance([(0, 0), (1, 0), (3, 0)]) == 1.0
