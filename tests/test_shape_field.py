import math, random
from cwm.continuous.envs import ShapeField2D, PatchField2D, blind_of
from cwm.continuous.shapes import Circle, HalfPlane

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
