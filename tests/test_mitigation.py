"""Offline tests for the mitigation experiment (distrust-region replanning).

The three properties the spec demands: (1) exact zero-cost control — on a
correct model the mitigated episode is bit-identical to plain MPC; (2)
violation detection fires on the clamp and never on truth; (3) the mitigated
blind planner escapes the pin and recovers most of the truth planner's return
on both instruments."""
import random

from cwm.continuous.envs import CartWall, PendulumStop, PatchField2D, blind_of
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


P2D = PatchField2D()


def test_patch2d_bit_identity_on_truth():
    ref = harness.run_episode(P2D, P2D, "mpc", seed=3, n_samples=40)
    mit = run_mitigated_episode(P2D, P2D, seed=3, n_samples=40,
                                eps=0.5, pos_dims=(0, 1))
    assert mit.violations == 0 and mit.ret == ref.ret


def test_patch2d_mitigated_blind_escapes():
    # 2D partial collapse — the boundary-mapping transient (mean ~2 violations)
    # makes recovery PARTIAL (~24-32% of truth here), unlike 1D's near-total
    # escape: the planner rounds one fence disc and re-contacts the patch
    # elsewhere, accruing ~2 violations. The mechanism still fires — the pin
    # breaks and the planner navigates to the real lode at x=-6 — but recovery
    # is partial by construction. See §9. (Measured seed 3: blind ~0; mitigated
    # ret=4.16, final x=-5.55, violations=2; truth=17.30 -> ratio 0.24.)
    b = harness.run_episode(P2D, blind_of(P2D), "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(P2D, blind_of(P2D), seed=3, n_samples=40,
                              eps=0.5, pos_dims=(0, 1))
    t = harness.run_episode(P2D, P2D, "mpc", seed=3, n_samples=40)
    r = harness.run_episode(P2D, policy="random", seed=3)
    assert b.ret < 1.0                       # pinned baseline
    assert m.violations >= 1
    assert m.ret > 3 * max(b.ret, 0.1)       # escaped the pin (b ~0, m ~4)
    assert m.final_state[0] < -3.0           # navigated toward the real lode (x=-6)
    # the play_cost collapsed substantially (mitigated << blind regret).
    # 0.80 is the PESSIMISTIC single-episode bound (seed 3 is the worst tail,
    # ~24% recovery -> pc_mit ~0.76); the aggregate collapse across knobs in
    # results/continuous_mitigation_patch2d.json is much larger (e.g. (2,6):
    # pc_blind 1.006 -> pc_mit 0.257).
    denom = t.ret - r.ret
    pc_blind = (t.ret - b.ret) / denom
    pc_mit = (t.ret - m.ret) / denom
    assert pc_mit < 0.80 * pc_blind


# ---------------- nerve-fence mode (2026-07-23) ----------------

def test_seg_seg_dist_oracle():
    from cwm.continuous.mitigation import _seg_seg_dist
    # crossing segments -> 0
    assert _seg_seg_dist((0, 0), (2, 2), (0, 2), (2, 0)) == 0.0
    # parallel horizontal segments offset by 1 -> 1
    assert abs(_seg_seg_dist((0, 0), (4, 0), (0, 1), (4, 1)) - 1.0) < 1e-12
    # disjoint collinear: gap between (2,0)-(3,0) endpoints -> 1
    assert abs(_seg_seg_dist((0, 0), (2, 0), (3, 0), (5, 0)) - 1.0) < 1e-12
    # endpoint-to-interior: point segment above the middle -> 0.5
    assert abs(_seg_seg_dist((0, 0), (4, 0), (2, 0.5), (2, 3)) - 0.5) < 1e-12


def test_nerve_edge_truncates_the_gap_between_points():
    """Two fence points 4 units apart, fence radius 0.5: an imagined step
    through the midpoint clears both POINTS by 2 units (points mode does not
    truncate) but crosses the EDGE (nerve mode truncates) — the covering-law
    hole, sealed."""
    from cwm.continuous.mitigation import (_crosses_fence,
                                           _crosses_fence_edges)
    f1, f2 = (7.0, -2.0), (7.0, 2.0)
    step_prev, step_next = (6.0, 0.0), (8.0, 0.0)   # crosses midway
    assert not _crosses_fence(step_prev, step_next, [f1, f2], 0.5)
    assert _crosses_fence_edges(step_prev, step_next, [(f1, f2)], 0.5)


def test_nerve_bit_identical_on_truth_model():
    """Zero-cost control holds in nerve mode: with a correct model no
    violation fires, no fence or edge exists, and the episode is
    bit-identical to the plain MPC one."""
    from cwm.continuous.envs import RingField2D
    from cwm.continuous import harness
    from cwm.continuous.mitigation import run_mitigated_episode
    truth = RingField2D()
    plain = harness.run_episode(truth, truth, "mpc", 7)
    mit = run_mitigated_episode(truth, truth, seed=7, eps=0.5,
                                pos_dims=(0, 1), fence_mode="nerve")
    assert mit.violations == 0
    assert mit.ret == plain.ret
    assert tuple(mit.final_state) == tuple(plain.final_state)
