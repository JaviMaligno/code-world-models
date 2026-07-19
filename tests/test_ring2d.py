"""Mechanism tests for RingField2D, the paper-3 opening instrument
(annular mode enclosing the phantom lode; docs/paper3/RESEARCH-DIRECTION.md §3,
propositions in docs/paper3/THEORY.md)."""
import math
import random

from cwm.continuous.envs import RingField2D, blind_of, filled_of
from cwm.continuous import harness

ENV = RingField2D()          # gap = 0: closed ring, beta_1 = 1


def test_step_freeze_at_the_outer_boundary():
    # from just outside the outer radius moving east, the landing point falls
    # in the annulus -> freeze at the PREVIOUS position with zero velocity
    s = (6.9, 0.0, 3.0, 0.0)          # x2 = 7.221 -> d = 4.779 in [3.5, 5]
    s2, r, c = ENV.step(s, 0.0)
    assert c and s2 == (6.9, 0.0, 0.0, 0.0)
    assert ENV.contact_mode(s, 0.0)
    # a free step far from the ring
    s2, _, c = ENV.step((0.0, 0.0, 0.0, 0.0), 0.0)
    assert not c and abs(s2[0] - 0.03) < 1e-12


def test_gap_channel_lets_the_same_step_through():
    # gap centered at pi (facing the start): the same landing point at angle
    # pi relative to the ring center is now in the channel -> no freeze
    gapped = RingField2D(gap=1.0)
    s = (6.9, 0.0, 3.0, 0.0)
    ang = math.atan2(0.0, 7.221 - 12.0)
    assert abs(ang) == math.pi        # west of center: on the channel axis
    s2, _, c = gapped.step(s, 0.0)
    assert not c and s2[0] > 7.0
    # off-axis landing at the same radius still freezes
    assert gapped._in_mode(12.0, 4.0)  # angle pi/2, d = 4.0: in the annulus


def test_blind_sails_and_filled_freezes_interior():
    b = blind_of(ENV)
    assert b.r_in is None
    s = (6.9, 0.0, 3.0, 0.0)
    assert not b.step(s, 0.0)[2]
    f = filled_of(ENV)
    # a landing point strictly inside the hole: ring model is free there,
    # the filled (wrong-topology) model freezes — they differ ONLY on states
    # the true dynamics can never produce from outside
    inside = (11.0, 0.0, 3.0, 0.0)    # x2 = 11.321 -> d = 0.679 < r_in
    assert not ENV.step(inside, 0.0)[2]
    assert f.step(inside, 0.0)[2]


def test_interior_is_reach_null_at_gap_zero():
    # the crossing lemma made empirical: 200 random rollouts, zero visited
    # states inside the hole (and the mode does fire sometimes, so the
    # rollouts do reach the ring region)
    entered, contacts = 0, 0
    n = 200
    for i in range(n):
        rng = random.Random(50_000 + i)
        s = ENV.initial_state(rng)
        hit = False
        for _ in range(ENV.h_episode):
            a = rng.uniform(-ENV.a_max, ENV.a_max)
            s, _, c = ENV.step(s, a)
            hit = hit or c
            if ENV.in_interior(s[0], s[1]):
                entered += 1
                break
        contacts += hit
    assert entered == 0
    assert contacts >= 1                # the ring itself IS reachable


def test_truth_navigates_and_blind_is_pinned_at_the_ring():
    t = harness.run_episode(ENV, ENV, "mpc", seed=0, n_samples=40)
    b = harness.run_episode(ENV, blind_of(ENV), "mpc", seed=0, n_samples=40)
    assert t.ret > 10.0                 # sits on the real lode
    assert abs(t.final_state[0] - ENV.lode_real[0]) < 2.5
    assert b.contact and b.ret < 1.0    # lured, frozen at the outer boundary
    d = math.hypot(b.final_state[0] - ENV.center[0],
                   b.final_state[1] - ENV.center[1])
    assert d >= ENV.r_out - 1e-9        # pinned outside/on the outer circle


def test_wrong_topology_is_planner_equivalent_at_gap_zero():
    """Proposition 3 (THEORY.md), bitwise: at gap = 0, MPC planning on the
    true annulus and on the filled disc produce IDENTICAL episodes (paired
    seeds), because imagined steps (< thickness) can never query the interior
    where the two models differ. The wrong topology is unfalsifiable by play
    AND harmless — until the gap opens."""
    for seed in (0, 1, 2):
        a = harness.run_episode(ENV, ENV, "mpc", seed=seed, n_samples=40)
        b = harness.run_episode(ENV, filled_of(ENV), "mpc", seed=seed,
                                n_samples=40)
        assert a.ret == b.ret and a.final_state == b.final_state
        assert a.contact == b.contact
