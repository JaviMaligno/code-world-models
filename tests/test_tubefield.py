"""TubeField3D (the non-separating mode, V2-PROGRAM 2d): geometry sanity,
NON-separation (deterministic around-path and through-path reach the far
side), and the freeze semantics."""
import math
import random

from cwm.continuous.envs import TubeField3D, blind_of


def _drive(env, thrust_fn, steps=80):
    rng = random.Random(0)
    s = env.initial_state(rng)
    contact = False
    for t in range(steps):
        s, _, c = env.step(s, thrust_fn(t, s))
        contact = contact or c
    return s, contact


def test_torus_membership_geometry():
    e = TubeField3D()
    assert not e._in_mode((8.0, 0.0, 0.0))       # hole center: dist_core = 2
    assert e._in_mode((8.0, 2.0, 0.0))           # on the core: dist 0
    assert e._in_mode((8.0, 0.0, 2.9))           # inside tube: dist 0.9
    assert not e._in_mode((8.0, 0.0, 3.2))       # outside tube: dist 1.2
    assert not e._in_mode((0.0, 2.0, 0.0))       # far in x


def test_threading_path_is_contact_free_when_aligned():
    e = TubeField3D()                             # hole on the x-axis
    s, contact = _drive(e, lambda t, s: (1.0, 0.0, 0.0))
    assert not contact
    assert s[0] > 12.0                            # sailed through the hole


def test_straight_path_clips_when_offset():
    e = TubeField3D(core_yz=(1.5, 0.0))           # hole moved off-axis
    s, contact = _drive(e, lambda t, s: (1.0, 0.0, 0.0))
    assert contact
    assert s[0] < 8.0                             # pinned before the plane


def test_non_separating_around_path_reaches_far_side():
    """The complement is CONNECTED: a scripted path OVER the torus (through
    z above the tube's reach) gets to the far side contact-free — there is
    no separating surface, hence no reach-null region and no exact gauge."""
    e = TubeField3D(core_yz=(1.5, 0.0))           # even in the clipping config
    def thrust(t, s):
        x, y, z = s[0], s[1], s[2]
        if x < 7.0:
            return (0.7, 0.0, 0.7)                # climb while advancing
        if z > 4.5 and x < 9.0:
            return (1.0, 0.0, 0.0)                # cross above the torus
        return (0.7, 0.0, -0.7)                   # descend beyond it
    s, contact = _drive(e, thrust, steps=80)
    assert not contact
    assert s[0] > 9.0                             # far side reached


def test_blind_of_tube():
    e = TubeField3D()
    b = blind_of(e)
    assert b.tube_radius is None
    assert not b._in_mode((8.0, 2.0, 0.0))
