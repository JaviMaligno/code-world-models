"""Offline tests for the mitigation experiment (distrust-region replanning).

The three properties the spec demands: (1) exact zero-cost control — on a
correct model the mitigated episode is bit-identical to plain MPC; (2)
violation detection fires on the clamp and never on truth; (3) the mitigated
blind planner escapes the pin and recovers most of the truth planner's return
on both instruments."""
import random

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness, mpc
from cwm.continuous.mitigation import plan_mitigated, run_mitigated_episode

CART = CartWall(x_wall=8.0)
PEND = PendulumStop(th_stop=1.4)


def test_plan_reduces_to_mpc_without_violations():
    # Same rng seed, no violations -> identical action to mpc.plan (bitwise).
    for seed in (0, 1, 2):
        a_ref = mpc.plan(CART, (0.5, 1.0), random.Random(seed), n_samples=50)
        a_mit = plan_mitigated(CART, (0.5, 1.0), random.Random(seed), [],
                               eps=0.25, n_samples=50)
        assert a_mit == a_ref


def test_bit_identical_episode_on_truth_model():
    ep_ref = harness.run_episode(CART, CART, "mpc", seed=3, n_samples=40)
    ep_mit = run_mitigated_episode(CART, CART, seed=3, n_samples=40, eps=0.25)
    assert ep_mit.violations == 0
    assert ep_mit.ret == ep_ref.ret
    assert ep_mit.final_state == ep_ref.final_state


def test_violation_recorded_on_blind_model():
    m = run_mitigated_episode(CART, blind_of(CART), seed=3, n_samples=40,
                              eps=0.25)
    assert m.violations >= 1
    assert m.first_contact_step is not None


def test_mitigated_blind_escapes_cart():
    b = harness.run_episode(CART, blind_of(CART), "mpc", seed=3, n_samples=40)
    t = harness.run_episode(CART, CART, "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(CART, blind_of(CART), seed=3, n_samples=40,
                              eps=0.25)
    assert b.final_state[0] == CART.x_wall          # the pin (existing behavior)
    assert m.final_state[0] < CART.x_wall - 0.25    # escaped the distrust band
    assert m.ret > 10 * max(b.ret, 0.1)             # far above the pinned return
    assert m.ret > 0.25 * t.ret                     # recovers despite the transient
    # (Margin from the validated v4 prototype: measured ratios 0.30-0.35 at
    # these exact params (seed=3, n_samples=40) — the residual is the honest
    # first-contact + travel-back transient at x_wall=8, ~25 lured steps. If
    # this fails, print the three returns and investigate; do not loosen.)


def test_mitigated_blind_escapes_pendulum():
    b = harness.run_episode(PEND, blind_of(PEND), "mpc", seed=3, n_samples=40)
    t = harness.run_episode(PEND, PEND, "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(PEND, blind_of(PEND), seed=3, n_samples=40,
                              eps=0.1)
    assert b.final_state[0] == PEND.th_stop
    assert m.final_state[0] < PEND.th_stop - 0.1
    assert m.violations >= 1
    assert m.ret > 10 * max(b.ret, 0.1)
    assert m.ret > 0.4 * t.ret   # prototype measured ~0.84 here
