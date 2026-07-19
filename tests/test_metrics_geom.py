import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous import mpc
from cwm.continuous.metrics_geom import stratified_probes, disagreement_scores
BOX = ((-8.0,14.0),(-6.0,6.0))

def _planner_queries(env, n, seed=0):
    rng = random.Random(seed); out = []
    s = env.initial_state(rng)
    for _ in range(n):
        a = mpc.plan(env, s, rng, horizon=20, n_samples=64, block=10)
        out.append((s, a)); s = env.step(s, a)[0]
    return out

def test_band_labels_are_correct_and_full():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    pq = _planner_queries(env, 30)
    pr = stratified_probes(env, BOX, n_per=20, rng=random.Random(0), band_d=0.15, planner_queries=pq)
    assert set(pr) == {"inside","outside","band","uniform","planner"}
    assert all(len(v) == 20 for v in pr.values())
    # every "inside"-labeled probe truly contacts, every "outside" does not
    assert all(env.contact(s,a) for (s,a) in pr["inside"])
    assert all(not env.contact(s,a) for (s,a) in pr["outside"])

def test_identity_zero_blind_positive_in_band():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0)); blind = ShapeField2D(shape=None)
    pq = _planner_queries(env, 30)
    pr = stratified_probes(env, BOX, 20, random.Random(0), 0.15, pq)
    assert disagreement_scores(env, lambda s,a: env.step(s,a)[0], pr)["band"]["disagreement"] == 0.0
    assert disagreement_scores(env, lambda s,a: blind.step(s,a)[0], pr)["band"]["disagreement"] > 0.2
