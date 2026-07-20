import math, random
from cwm.continuous.envs import integrate_2d, invert_integrator, PatchField2D

def test_integrate_2d_matches_patchfield_exactly():
    env = PatchField2D()
    rng = random.Random(0)
    for _ in range(500):
        s = (rng.uniform(-8, 14), rng.uniform(-6, 6), rng.uniform(-4, 4), rng.uniform(-4, 4))
        a = rng.uniform(-1, 1)
        assert integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max) == env._integrate(s, a)

def test_invert_integrator_lands_on_endpoint():
    env = PatchField2D()
    rng = random.Random(1)
    for _ in range(500):
        p = (rng.uniform(-8, 14), rng.uniform(-6, 6)); vx, vy, a = rng.uniform(-4,4), rng.uniform(-4,4), rng.uniform(-1,1)
        s = invert_integrator(p, vx, vy, a, env.dt, env.gain, env.drag, env.a_max)
        x2, y2, _, _ = integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max)
        assert math.isclose(x2, p[0], abs_tol=1e-9) and math.isclose(y2, p[1], abs_tol=1e-9)
