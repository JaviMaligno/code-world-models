import math, random
from cwm.continuous.shapes import HalfPlane, Circle, Parabola
WIN = ((-8.0, 14.0), (-6.0, 6.0))

def _consecutive_uniform(pts, tol=0.25):
    ds = [math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1)]
    m = sum(ds)/len(ds)
    return all(abs(d-m) <= tol*m for d in ds)

def _brute_project(shape, p, win, n=4000):
    best, bd = None, 1e18
    for q in shape.boundary_points(win, n):
        d = math.hypot(p[0]-q[0], p[1]-q[1])
        if d < bd: bd, best = d, q
    return best, bd

def test_halfplane_sign_and_signed_distance():
    hp = HalfPlane(3.0)
    assert hp.implicit_value((5.0,0.0)) < 0 < hp.implicit_value((1.0,0.0))
    assert math.isclose(hp.signed_distance((1.0,0.0)), 2.0)   # outside, +2
    assert math.isclose(hp.signed_distance((5.0,0.0)), -2.0)  # inside,  -2

def test_circle_boundary_is_arc_length_uniform_and_in_window():
    c = Circle(3.0, 0.0, 1.0)
    pts = c.boundary_points(WIN, 60)
    assert len(pts) == 60
    for x,y in pts:
        assert -8 <= x <= 14 and -6 <= y <= 6 and abs(c.implicit_value((x,y))) < 1e-6
    assert _consecutive_uniform(pts)

def test_circle_projection_matches_bruteforce():
    c = Circle(3.0, 0.0, 1.0); rng = random.Random(0)
    for _ in range(50):
        p = (rng.uniform(-2,8), rng.uniform(-5,5))
        (px,py), _ = c.project_to_boundary(p)
        _, bd = _brute_project(c, p, WIN)
        assert math.hypot(p[0]-px, p[1]-py) <= bd + 1e-3

def test_circle_center_is_multivalued():
    assert Circle(3.0,0.0,1.0).project_to_boundary((3.0,0.0))[1] is True

def test_param_validation():
    import pytest
    with pytest.raises(ValueError):
        Circle(0.0, 0.0, -1.0)

def test_parabola_curvature():
    par = Parabola(3.0, 2.0)
    assert math.isclose(par.curvature_center, 0.5) and math.isclose(par.curvature(0.0), 0.5)
    assert par.curvature(4.0) < par.curvature(0.0)

def test_parabola_projection_matches_bruteforce_even_when_multimodal():
    par = Parabola(3.0, 0.5)  # small R → sharp curvature → multimodal distance for far points
    rng = random.Random(2)
    for _ in range(80):
        p = (rng.uniform(3, 12), rng.uniform(-5, 5))
        (px, py), _ = par.project_to_boundary(p)
        _, bd = _brute_project(par, p, WIN, n=6000)
        assert math.hypot(p[0]-px, p[1]-py) <= bd + 1e-2  # matches the GLOBAL minimum

def test_parabola_boundary_arclength_uniform_in_window():
    par = Parabola(3.0, 2.0)
    pts = par.boundary_points(WIN, 80)
    assert 2 <= len(pts) <= 80
    for x, y in pts: assert -8 <= x <= 14 and -6 <= y <= 6
    assert _consecutive_uniform(pts, tol=0.35)

def test_parabola_validation():
    import pytest
    with pytest.raises(ValueError): Parabola(3.0, 0.0)
