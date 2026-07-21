"""Mechanism tests for ShellFieldN, the paper-3 n-dim arm step 1
(docs/paper3/SHELLFIELD-N-DESIGN.md): the n-dim generalization of
RingField2D with a thrust-VECTOR action instead of the 2D instruments'
scalar heading. The 2D golden envs/tests are untouched -- this is a new
class on a new action interface, no retrofit."""
import math

from cwm.continuous.envs import ShellFieldN, blind_of


def test_shell_membership_in_rn_for_several_n():
    # a point at Euclidean distance 4.0 from c is in [r_in, r_out] = [3.5, 5]
    # -> in the shell; at 3.0 (inside the hole) and 6.0 (beyond r_out) it is
    # not. Checked directly against `_in_mode`, as RingField2D's own tests
    # check `_in_mode` directly (test_gap_channel_lets_the_same_step_through).
    for n in (2, 3, 4):
        env = ShellFieldN(n=n)
        c = env.center()
        assert len(c) == n

        def point_at(d):
            p = list(c)
            p[0] += d           # displace along the first axis only
            return tuple(p)

        assert env._in_mode(point_at(4.0))
        assert not env._in_mode(point_at(3.0))
        assert not env._in_mode(point_at(6.0))


def test_freeze_returns_previous_position_and_zero_velocity():
    # mirrors RingField2D's test_step_freeze_at_the_outer_boundary: action
    # (1, 0, ..., 0) reproduces the 2D scalar action=0 (phi=0) case exactly
    # (norm 1 -> thrust = gain * (1,0,...,0)), so the same numbers apply:
    # x2 = 7.221 -> d = 4.779 in [3.5, 5] -> freeze.
    for n in (2, 3, 4):
        pos = [6.9] + [0.0] * (n - 1)
        vel = [3.0] + [0.0] * (n - 1)
        s = tuple(pos) + tuple(vel)
        a = (1.0,) + (0.0,) * (n - 1)
        env = ShellFieldN(n=n)
        s2, r, c = env.step(s, a)
        assert c is True
        assert s2 == tuple(pos) + tuple(0.0 for _ in range(n))
        assert env.contact_mode(s, a)
        # a free step far from the shell does not freeze
        far = tuple(0.0 for _ in range(2 * n))
        s2, _, c = env.step(far, a)
        assert not c


def test_norm_cap_on_thrust_for_any_action_vector():
    env = ShellFieldN(n=4)
    origin = tuple(0.0 for _ in range(2 * env.n))
    actions = [
        (0.0, 0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0, 1.0),        # ||a|| = 2 > 1
        (5.0, -5.0, 5.0, -5.0),      # way outside [-1, 1]^n
        (0.3, -0.2, 0.1, 0.05),
    ]
    for a in actions:
        s2 = env._integrate(origin, a)
        vel2 = s2[env.n:]
        # from rest, v' = thrust * dt (drag term vanishes at v=0)
        thrust = tuple(v / env.dt for v in vel2)
        norm = math.sqrt(sum(t * t for t in thrust))
        assert norm <= env.gain + 1e-9


def test_blind_of_disables_the_shell():
    env = ShellFieldN(n=3)
    b = blind_of(env)
    assert b.r_in is None
    pos = [6.9, 0.0, 0.0]
    vel = [3.0, 0.0, 0.0]
    s = tuple(pos) + tuple(vel)
    a = (1.0, 0.0, 0.0)
    # truth freezes here (same numbers as the freeze test above)
    assert env.step(s, a)[2]
    # the blind model sails through: no freeze, no contact
    s2, _, c = b.step(s, a)
    assert not c
    assert s2 != tuple(pos) + (0.0, 0.0, 0.0)


def test_state_length_is_2n():
    import random
    rng = random.Random(0)
    for n in (2, 3, 4, 5, 6):
        env = ShellFieldN(n=n)
        s0 = env.initial_state(rng)
        assert len(s0) == 2 * n
        a = tuple(rng.uniform(-1.0, 1.0) for _ in range(n))
        s1, r, c = env.step(s0, a)
        assert len(s1) == 2 * n
        assert isinstance(r, float)
