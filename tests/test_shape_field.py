import math, random
from cwm.continuous.envs import ShapeField2D, PatchField2D, blind_of
from cwm.continuous.shapes import Circle, HalfPlane
from cwm.continuous.instruments import spec_for, describe_shape
from cwm.continuous.contract import build_contract
from cwm.continuous.shapes import Circle, Parabola, RegularPolygon

def test_shapefield_exactly_equivalent_to_patchfield_single_disc():
    patch = PatchField2D(p1=(3.0,0.0), p2=None, R=1.0)
    shape = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    rng = random.Random(0)
    for _ in range(1000):
        s = (rng.uniform(-8,14), rng.uniform(-6,6), rng.uniform(-4,4), rng.uniform(-4,4)); a = rng.uniform(-1,1)
        assert patch.step(s,a) == shape.step(s,a)

def test_shapefield_freeze_and_blind():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    s2, _, contact = env.step((2.0,0.0,3.0,0.0), 0.0)
    assert contact and s2 == (2.0,0.0,0.0,0.0)
    assert blind_of(env).shape is None
    assert blind_of(env).step((2.9,0.0,3.0,0.0), 0.0)[2] is False

def test_incomplete_arm_is_geometry_agnostic():
    a = build_contract(ShapeField2D(shape=Circle(3.0,0.0,1.0)), include_mode=False)
    b = build_contract(ShapeField2D(shape=Parabola(3.0,2.0)), include_mode=False)
    assert a == b and "radius" not in a.lower() and "parabola" not in a.lower()

def test_full_arm_has_exact_predicate():
    full = build_contract(ShapeField2D(shape=Circle(3.0,0.0,1.0)), include_mode=True)
    assert "(x - 3.0)**2 + (y - 0.0)**2 <= 1.0**2" in full  # exact math, not repr

def test_every_probe_fires_the_mode():
    # NOTE: ShapeField2D exposes contact via `contact_mode(state, action)`
    # (see envs.py), not a bare `.contact`; the fixed hard mode-fire check
    # below drives that real method.
    for shp in (Circle(3.0,0.0,1.0), Parabola(3.0,2.0), RegularPolygon(3.0,0.0,1.0,5,math.pi/5)):
        env = ShapeField2D(shape=shp)
        probes = spec_for(env).mode_probes(env)["mode"]
        assert len(probes) >= 8
        for (state, action) in probes:
            assert env.contact_mode(state, action), f"probe must fire for {shp}"
