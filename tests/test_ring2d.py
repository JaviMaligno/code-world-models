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


def test_inside_start_moves_the_reachable_set():
    """The mu0 knob (Prop 1): starting inside the hole makes the interior
    part of the reachable set — the filled model's gauge content becomes
    falsifiable (it disagrees with truth on real transitions), and the
    crossing lemma traps the trajectory INSIDE just as it trapped it outside."""
    inside_env = RingField2D(x0_center=RingField2D().center)
    rng = random.Random(7)
    s = inside_env.initial_state(rng)
    assert inside_env.in_interior(s[0], s[1])
    f = filled_of(inside_env)
    disagreements = 0
    for _ in range(inside_env.h_episode):
        a = rng.uniform(-inside_env.a_max, inside_env.a_max)
        st, _, _ = inside_env.step(s, a)
        sf, _, _ = f.step(s, a)
        disagreements += st != sf
        s = st
        assert math.hypot(s[0] - inside_env.center[0],
                          s[1] - inside_env.center[1]) <= inside_env.r_out
    assert disagreements > 0    # filled freezes where truth moves: falsified


def test_positivity_witness_tube():
    """Machine check of Prop 8's witness (THEORY.md): with |y0| <= 3.5*gap/8
    and the constant 0-action sequence, the trajectory is freeze-free, every
    band-radius landing lies in the channel with angular clearance >= 3g/8
    over the wall, and it enters the interior well within the horizon.
    Small action perturbations (the tube) preserve all of it."""
    gap = 0.3
    env = RingField2D(gap=gap)
    y0 = 0.1                       # <= eta(gap) = 3.5*gap/8 = 0.13125
    for pert in (0.0, 0.008, -0.008):
        rng = random.Random(99)
        s = (0.0, y0, 0.0, 0.0)
        entered = False
        for t in range(env.h_episode):
            a = pert * (1 + 0.5 * rng.random())   # inside the tube
            s, _, c = env.step(s, a)
            assert not c               # freeze-free all the way
            d = math.hypot(s[0] - env.center[0], s[1] - env.center[1])
            if env.r_in <= d <= env.r_out:
                off = abs(math.atan2(s[1] - env.center[1],
                                     s[0] - env.center[0]))
                assert math.pi - off <= gap / 2 - gap / 8 + 1e-9
            if env.in_interior(s[0], s[1]):
                entered = True
                break
        assert entered and t < 45     # enters with slack in the horizon


# ---------------- square ring (Chebyshev norm, V2-PROGRAM 1a) ----------------

def test_cheby_ring_membership_is_square():
    env = RingField2D(norm="cheby")
    cx, cy = env.center
    # corner of the square band: Euclidean distance ~ r*sqrt(2), Chebyshev r
    assert env._in_mode(cx + 4.0, cy + 4.0)          # cheby d = 4 in [3.5, 5]
    assert not RingField2D()._in_mode(cx + 4.0, cy + 4.0)   # euclid d = 5.66
    assert env.in_interior(cx + 3.0, cy + 3.0)       # cheby d = 3 < 3.5
    assert not RingField2D().in_interior(cx + 3.0, cy + 3.0)


def test_cheby_interior_is_reach_null_at_gap_zero():
    """The crossing lemma survives the square separator (Chebyshev distance
    is 1-Lipschitz w.r.t. Euclidean steps): zero interior entries, ring
    reachable."""
    env = RingField2D(norm="cheby")
    entered, contacts = 0, 0
    for i in range(200):
        rng = random.Random(50_000 + i)
        s = env.initial_state(rng)
        hit = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, c = env.step(s, a)
            hit = hit or c
            if env.in_interior(s[0], s[1]):
                entered += 1
                break
        contacts += hit
    assert entered == 0
    assert contacts >= 1


def test_cheby_wrong_topology_is_planner_equivalent_at_gap_zero():
    """Prop 3 transfers to the square ring, bitwise."""
    env = RingField2D(norm="cheby")
    for seed in (0, 1, 2):
        a = harness.run_episode(env, env, "mpc", seed=seed, n_samples=40)
        b = harness.run_episode(env, filled_of(env), "mpc", seed=seed,
                                n_samples=40)
        assert a.ret == b.ret and a.final_state == b.final_state
        assert a.contact == b.contact


def test_cheby_norm_carries_through_blind_and_filled():
    env = RingField2D(norm="cheby")
    assert blind_of(env).norm == "cheby" and filled_of(env).norm == "cheby"


# ---------------- multi-chamber (nested rings, V2-PROGRAM 1b) ----------------

def test_multichamber_three_reach_null_chambers():
    """Two nested uncrossable bands split the plane into three mutually
    reach-null chambers: a trajectory stays in its start chamber, from every
    start placement."""
    def chamber(env, x, y):
        d = math.hypot(x - env.center[0], y - env.center[1])
        if d < env.r_in:
            return "hole"
        if env.r_out < d < env.r_in2:
            return "middle"
        if d > env.r_out2:
            return "outside"
        return "band"

    mid_r = (5.0 + 7.5) / 2
    for start, x0 in (("outside", (0.0, 0.0)),
                      ("middle", (12.0 - mid_r, 0.0)),
                      ("hole", (12.0, 0.0))):
        env = RingField2D(r_in2=7.5, r_out2=9.0, x0_center=x0)
        crossings, contacts = 0, 0
        for i in range(80):
            rng = random.Random(60_000 + i)
            s = env.initial_state(rng)
            assert chamber(env, s[0], s[1]) == start
            hit = False
            for _ in range(env.h_episode):
                a = rng.uniform(-env.a_max, env.a_max)
                s, _, c = env.step(s, a)
                hit = hit or c
                if chamber(env, s[0], s[1]) != start:
                    crossings += 1
                    break
            contacts += hit
        assert crossings == 0, f"chamber escape from {start}"
        if start in ("outside", "middle"):
            assert contacts >= 1        # some boundary IS reachable


def test_multichamber_blind_of_removes_both_rings():
    env = RingField2D(r_in2=7.5, r_out2=9.0)
    b = blind_of(env)
    assert b.r_in is None and b.r_in2 is None and b.r_out2 is None
    # blind never freezes anywhere
    assert not b._in_mode(12.0, 4.0) and not b._in_mode(12.0 + 8.0, 0.0)


def test_t6_hidden06_steering_witness():
    """T6 (THEORY.md) settled positively: the optimized waypoint controller
    enters the interior through the HIDDEN gamma=0.6 channel within the
    instrument's own horizon. Machine-checked witness (params from
    results/t6_hidden06_witness.json, search 2026-07-24)."""
    env = RingField2D(gap=0.6, gap_center=0.0, x0_center=(0.0, 0.0))
    cx, cy = env.center
    P = [9.006, 6.974, 7.47, 16.22, 3.626, 7.482, 17.146, 0.203, 3.954, 5.87]
    wps = [((P[0], P[1]), P[2]), ((P[3], P[4]), P[5]),
           ((P[6], P[7]), P[8]), ((cx, cy), P[9])]

    def steer(s, wp, v):
        d = math.hypot(wp[0] - s[0], wp[1] - s[1]) or 1e-9
        phi = math.atan2(v * (wp[1] - s[1]) / d - s[3],
                         v * (wp[0] - s[0]) / d - s[2])
        return max(-1.0, min(1.0, phi / math.pi))

    entries = 0
    for sd in range(1000, 1005):
        rng = random.Random(sd)
        s = env.initial_state(rng)
        wp_i = 0
        for _ in range(env.h_episode):
            wp, v = wps[wp_i]
            if math.hypot(s[0] - wp[0], s[1] - wp[1]) < 2.0:
                wp_i = min(wp_i + 1, len(wps) - 1)
                wp, v = wps[wp_i]
            s, _, _ = env.step(s, steer(s, wp, v))
            if math.hypot(s[0] - cx, s[1] - cy) < env.r_in:
                entries += 1
                break
    assert entries == 5
