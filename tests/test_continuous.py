"""Tests for the continuous/hybrid cart-with-wall instrument (paper 2)."""
import math
import random

from cwm.continuous.envs import CartWall, blind_of, biased_of, unbumped_of
from cwm.continuous import gate, harness, mpc


def test_wall_clamps_without_tunneling():
    env = CartWall(x_wall=1.0)
    # huge incoming velocity: one step would jump far past the wall
    s, r, contact = env.step((0.9, 50.0), 1.0)
    assert contact
    assert s == (1.0, 0.0)  # pinned exactly, velocity zeroed


def test_no_contact_below_wall():
    env = CartWall(x_wall=4.0)
    s, r, contact = env.step((0.0, 0.0), 1.0)
    assert not contact and s[0] < 4.0


def test_blind_is_bit_exact_off_mode():
    """The mode-omitting model agrees with truth to the last bit on any
    trajectory that never touches the wall — the localization premise."""
    truth = CartWall(x_wall=4.0)
    blind = blind_of(truth)
    rng = random.Random(0)
    s_t = s_b = (0.0, 0.0)
    for _ in range(200):
        a = rng.uniform(-1.0, 0.5) * 0.3  # gentle, left-biased: stays below x=4
        s_t, r_t, c = truth.step(s_t, a)
        s_b, r_b, _ = blind.step(s_b, a)
        assert not c
        assert s_t == s_b and r_t == r_b  # exact equality, not approx


def test_blind_diverges_on_mode():
    truth = CartWall(x_wall=1.0)
    blind = blind_of(truth)
    s = (0.95, 5.0)
    st, _, ct = truth.step(s, 1.0)
    sb, _, cb = blind.step(s, 1.0)
    assert ct and not cb and st != sb


def test_reward_two_plateaus():
    env = CartWall()
    far_left = env.reward((-10.0, 0.0))
    middle = env.reward((0.0, 0.0))
    far_right = env.reward((20.0, 0.0))
    assert abs(far_left - env.a_left) < 1e-3
    assert middle < 1e-3
    assert abs(far_right - env.a_right) < 1e-3


def test_smooth_bump_is_smooth_and_localized():
    env = CartWall(x_wall=None, bump_amp=1.0, bump_center=4.0, bump_width=0.5)
    # localized: negligible far away, maximal at center
    assert abs(env.drag_at(-10.0) - env.drag) < 1e-12
    assert abs(env.drag_at(4.0) - (env.drag + 1.0)) < 1e-12
    # smooth: finite differences of drag_at are bounded across the patch edge
    h = 1e-6
    for x in (2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0):
        d1 = (env.drag_at(x + h) - env.drag_at(x - h)) / (2 * h)
        assert abs(d1) < 3.0  # max |gauss'| = amp/(width*sqrt(e)) ~ 1.2


def test_rarity_decreases_with_wall_distance():
    r_near, _, _ = harness.rarity(CartWall(x_wall=1.0), n_rollouts=300, seed=1)
    r_far, _, _ = harness.rarity(CartWall(x_wall=8.0), n_rollouts=300, seed=1)
    assert r_near > r_far
    assert r_near > 0.2 and r_far < 0.1


def test_gate_miss_matches_bernoulli_law():
    """Empirical P(N rollouts all miss the wall) matches (1-r)^N — the
    exactness proposition, re-verified on the continuous instrument."""
    env = CartWall(x_wall=2.0)
    n_roll, N, n_gates = 2000, 5, 400
    r, _, _ = harness.rarity(env, n_rollouts=n_roll, seed=7)
    misses = 0
    for g in range(n_gates):
        base = 100_000 + g * N
        if not any(harness.run_episode(env, policy="random", seed=base + i).contact
                   for i in range(N)):
            misses += 1
    expected = (1 - r) ** N
    se = math.sqrt(expected * (1 - expected) / n_gates)
    assert abs(misses / n_gates - expected) < 4 * se + 0.02


def test_mpc_truth_goes_left_blind_gets_pinned():
    """The instrument's two arms, small-sample smoke: truth-planner reaches the
    left plateau without contact; blind-planner is pinned at the wall."""
    truth = CartWall(x_wall=4.0)
    blind = blind_of(truth)
    ep_t = harness.run_episode(truth, truth, "mpc", seed=3, n_samples=40)
    ep_b = harness.run_episode(truth, blind, "mpc", seed=3, n_samples=40)
    assert not ep_t.contact and ep_t.final_state[0] < truth.x_left + 2
    assert ep_b.contact and ep_b.final_state[0] == truth.x_wall
    assert ep_t.ret > 10.0 and ep_b.ret < 1.0


def test_gate_truth_vs_itself_is_exact():
    env = CartWall(x_wall=4.0)
    res = gate.run_gate(env, env, n_rollouts=5, eps=0.0, seed=0)
    assert res.passed and res.max_err == 0.0 and res.n_transitions == 5 * env.h_episode


def test_gate_sub_tolerance_bias_always_passes():
    truth = CartWall(x_wall=4.0)
    res = gate.run_gate(truth, biased_of(truth, 1.03), n_rollouts=20,
                        eps=0.01, seed=0)
    assert res.passed
    assert 0.0 < res.max_err <= 0.01  # errs everywhere, never over tolerance


def test_gate_supra_tolerance_bias_always_fails():
    truth = CartWall(x_wall=4.0)
    r, _, _ = gate.reveal_rarity(truth, biased_of(truth, 2.0), eps=0.01,
                                 n_rollouts=30, seed=0)
    assert r == 1.0  # revealed on every rollout — the gate polices this axis


def test_gate_blind_reveal_matches_contact_rarity():
    """For the wall omission, reveal-rarity coincides with the wall-contact
    rate (the clamp produces a large deviation whenever it fires)."""
    truth = CartWall(x_wall=2.0)
    r_reveal, _, _ = gate.reveal_rarity(truth, blind_of(truth), eps=0.01,
                                        n_rollouts=200, seed=5)
    r_contact, _, _ = harness.rarity(truth, n_rollouts=200, seed=5)
    assert abs(r_reveal - r_contact) < 0.05


def test_smooth_bump_reveals_but_does_not_hurt():
    bump = CartWall(x_wall=None, bump_amp=0.5, bump_center=4.0, bump_width=0.5)
    blind = unbumped_of(bump)
    r, _, _ = gate.reveal_rarity(bump, blind, eps=0.01, n_rollouts=150, seed=3)
    assert r > 0.05  # localized and detectable, like the wall...
    pc = harness.play_cost(bump, blind, n_episodes=2, seed=9, n_samples=40)
    assert abs(pc["play_cost"]) < 0.1  # ...but inconsequential at play


def test_play_cost_structure():
    truth = CartWall(x_wall=4.0)
    res = harness.play_cost(truth, blind_of(truth), n_episodes=3, seed=11,
                            n_samples=40)
    assert res["j_truth"] > res["j_random"] > res["j_blind"] - 1e-9
    assert res["play_cost"] > 0.9
    assert res["blind_contact_rate"] == 1.0
    assert res["truth_contact_rate"] == 0.0
