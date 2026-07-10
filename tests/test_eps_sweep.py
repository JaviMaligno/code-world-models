"""Offline pins for the eps-sweep properties (small samples, fast):
mode-arm reveal-rarity is eps-FLAT (a discontinuity's error jumps 0 -> O(1)),
pervasive-bias reveal-rarity SWITCHES across eps."""
from cwm.continuous.envs import CartWall, PendulumStop, blind_of, biased_of
from cwm.continuous import gate


def test_mode_arm_rarity_is_eps_flat():
    env = CartWall(x_wall=4.0)
    blind = blind_of(env)
    r_tight = gate.reveal_rarity(env, blind, 1e-6, 200, seed=7)[0]
    r_loose = gate.reveal_rarity(env, blind, 1e-2, 200, seed=7)[0]
    assert r_tight == r_loose  # identical rollouts, identical reveals
    assert r_tight > 0.05      # the mode does fire at this knob


def test_pendulum_mode_arm_rarity_is_eps_flat():
    env = PendulumStop(th_stop=1.0)
    blind = blind_of(env)
    r_tight = gate.reveal_rarity(env, blind, 1e-6, 200, seed=7)[0]
    r_loose = gate.reveal_rarity(env, blind, 1e-2, 200, seed=7)[0]
    assert r_tight == r_loose
    assert r_tight > 0.05


def test_supra_bias_rarity_switches_with_eps():
    env = CartWall(x_wall=4.0)
    biased = biased_of(env, 2.0)
    assert gate.reveal_rarity(env, biased, 1e-6, 100, seed=7)[0] == 1.0
    assert gate.reveal_rarity(env, biased, 0.3, 100, seed=7)[0] == 0.0
