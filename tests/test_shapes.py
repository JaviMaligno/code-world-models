import math, random
from cwm.continuous.shapes import HalfPlane, Circle, Parabola, Strip, Wedge, RegularPolygon
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

def test_wedge_projects_to_a_ray_not_always_apex():
    w = Wedge(apex=(3.0, 0.0), half_angle=math.radians(30), orient=0.0)
    # a point beside one ray should project onto that ray, strictly farther than 0 from the apex
    p = (6.0, 1.0)
    (qx, qy), _ = w.project_to_boundary(p)
    assert math.hypot(qx-3.0, qy-0.0) > 0.5  # not the apex
    _, bd = _brute_project(w, p, WIN, n=4000)
    assert math.hypot(p[0]-qx, p[1]-qy) <= bd + 1e-2

def test_polygon_projection_and_vertex_cone_and_orientation():
    face = RegularPolygon(3.0, 0.0, 1.0, 4, 0.0)
    vert = RegularPolygon(3.0, 0.0, 1.0, 4, math.pi/4)
    assert face.n_facets == 4
    rng = random.Random(3)
    for _ in range(40):
        p = (rng.uniform(1,5), rng.uniform(-2,2))
        (qx,qy), _ = vert.project_to_boundary(p)
        _, bd = _brute_project(vert, p, WIN, n=4000)
        assert math.hypot(p[0]-qx, p[1]-qy) <= bd + 1e-2
    # a vertex point has a 2-normal cone
    vpt, _ = vert.project_to_boundary((3.0+5.0, 0.0))
    assert isinstance(vert.normal_or_cone(vpt), list) and len(vert.normal_or_cone(vpt)) == 2

def test_polygon_boundary_in_window():
    poly = RegularPolygon(3.0, 0.0, 1.0, 6, 0.0)
    for x,y in poly.boundary_points(WIN, 60):
        assert -8 <= x <= 14 and -6 <= y <= 6

def test_shape3_validation():
    import pytest
    with pytest.raises(ValueError): RegularPolygon(0,0,1,2,0.0)
    with pytest.raises(ValueError): Strip(3.0, 0.0)
    with pytest.raises(ValueError): Wedge((0,0), 0.0, 0.0)
