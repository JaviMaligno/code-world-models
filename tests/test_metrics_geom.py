import math
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous import mpc
from cwm.continuous.metrics_geom import stratified_probes, disagreement_scores
from cwm.continuous.metrics_geom import iou_vs_truth, forbidden_mask
from cwm.continuous.metrics_geom import boundary_of_set, symmetric_boundary_distance
from cwm.continuous.envs import ShapeField2D, integrate_2d, invert_integrator
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

def test_true_guard_is_positional_and_invariant_across_velocity():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    res = iou_vs_truth(env, lambda s,a: env.step(s,a)[0], BOX, grid_n=128,
                       velocity_samples=[(3.0,0.0),(0.0,3.0),(-2.0,1.0)])
    assert res["class"] == "positional" and res["iou"] > 0.97  # endpoint-space, so velocity-invariant

def test_velocity_guard_is_non_positional():
    def vel_guard(s, a):
        x2,y2,vx2,vy2 = integrate_2d(s,a,0.1,3.0,0.3,1.0)
        return (s[0],s[1],0.0,0.0) if vx2 > 2.5 else (x2,y2,vx2,vy2)
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    res = iou_vs_truth(env, vel_guard, BOX, 128, [(3.0,0.0),(-3.0,0.0),(0.0,3.0)])
    assert res["class"] == "non_positional" and res["iou"] is None

def test_boundary_distance_zero_for_true_boundary():
    grid_n = 128
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    vx, vy = 3.0, 0.0
    mask = forbidden_mask(lambda s,a: env.step(s,a)[0], BOX, grid_n, vx, vy)
    model_boundary = boundary_of_set(mask, BOX)
    (xmin,xmax),(ymin,ymax) = BOX
    cell_diagonal = math.hypot((xmax-xmin)/grid_n, (ymax-ymin)/grid_n)
    res = symmetric_boundary_distance(env.shape, model_boundary, BOX, n_samples=200, diam_norm=1.0)
    assert res["hausdorff"] < 1.5 * cell_diagonal
    assert res["p95"] <= res["hausdorff"]
    assert res["mean"] <= res["hausdorff"]

def test_boundary_distance_positive_for_shifted():
    grid_n = 128
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    shifted_env = ShapeField2D(shape=Circle(4.0,0.0,1.0))
    vx, vy = 3.0, 0.0
    mask = forbidden_mask(lambda s,a: shifted_env.step(s,a)[0], BOX, grid_n, vx, vy)
    model_boundary = boundary_of_set(mask, BOX)
    res = symmetric_boundary_distance(env.shape, model_boundary, BOX, n_samples=200, diam_norm=1.0)
    assert res["hausdorff"] > 0.5
