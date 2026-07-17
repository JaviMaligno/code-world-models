"""Offline tests for the CEM second-planner-family experiment. Prototype-
validated expectations (2026-07-12): CEM is competent on truth (cart ~97% of
MPC-truth) and is NOT exploited by the blind model (zero contact, near-truth
return) — the other branch of Proposition 3."""
import random

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness, mpc
from cwm.continuous.cem import plan_cem, run_episode

CART = CartWall(x_wall=8.0)
PEND = PendulumStop(th_stop=1.4)


def test_deterministic_given_seed():
    a1 = plan_cem(CART, (0.5, 1.0), random.Random(7))
    a2 = plan_cem(CART, (0.5, 1.0), random.Random(7))
    assert a1 == a2


def test_cem_competent_on_truth_cart():
    for seed in (0, 3):
        cem_ep = run_episode(CART, CART, seed=seed)
        mpc_ep = harness.run_episode(CART, CART, "mpc", seed=seed)
        assert cem_ep.ret >= 0.9 * mpc_ep.ret, (cem_ep.ret, mpc_ep.ret)


def test_cem_blind_not_exploited_cart():
    for seed in (0, 3):
        b = run_episode(CART, blind_of(CART), seed=seed, boundary=CART.x_wall)
        t = run_episode(CART, CART, seed=seed)
        assert b.contact is False
        assert b.final_state[0] < CART.x_wall - 1.0
        assert b.ret >= 0.95 * t.ret          # prototype: identical to 2 dp
        assert b.crossing_frac is not None and b.crossing_frac < 0.05


def test_cem_blind_not_pinned_pendulum():
    b = run_episode(PEND, blind_of(PEND), seed=0, boundary=PEND.th_stop)
    assert b.contact is False
    assert b.final_state[0] < PEND.th_stop - 0.1
    assert b.crossing_frac < 0.05


def test_callable_boundary_matches_float_boundary():
    """The callable-predicate path (used by the 2D instrument) must reduce
    to the float path exactly: same crossing_frac on the same seed."""
    predicate = lambda s: s[0] >= CART.x_wall  # noqa: E731
    for seed in (0, 3):
        b_float = run_episode(CART, blind_of(CART), seed=seed,
                              boundary=CART.x_wall)
        b_callable = run_episode(CART, blind_of(CART), seed=seed,
                                 boundary=predicate)
        assert b_callable.crossing_frac == b_float.crossing_frac
        assert b_callable.ret == b_float.ret
        assert b_callable.contact == b_float.contact
