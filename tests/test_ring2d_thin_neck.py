"""Thin-neck ring (V2-PROGRAM's last item): the knob that breaks Lemma 2's
METRIC hypothesis while leaving the topology alone.

What is pinned here, and why each pin matters:

1. `neck=None` is bit-identical to the committed instrument (the guard does no
   arithmetic), and `neck = w` (the full thickness) is GEOMETRICALLY identical
   to the uniform band -- the knob's off-position is the closed ring twice over.
2. The thin annulus [r_in, r_in + neck] is contained in the mode at EVERY
   angle. That inclusion is the hypothesis of the local crossing lemma
   (formalized as `freeze_stays_outside_of_superset` in Paper3Ring): interior
   entry requires a single step longer than `neck`, so with max step
   (gain/drag)*dt = 1.0 a neck >= 1.0 keeps the interior unreachable exactly.
3. A DETERMINISTIC leap witness at neck = 0.5: constant thrust east from
   (0.20, 0), never touching the band, enters the hole at t = 25 by a single
   0.547-step over the 0.5-thick neck -- Lemma 2's conclusion fails exactly
   where its hypothesis does, by a machine-checked trajectory rather than a
   sampled rate.
4. The same witness family (40 start offsets) never enters at neck >= 1.0 --
   the complement of the witness, consistent with (2)'s theorem.
"""
import math

import pytest

from cwm.continuous.envs import RingField2D

CENTER = RingField2D().center


def _run(env, s, action=0.0):
    """Roll the env forward under a constant action; return (entered, frozen,
    trajectory) where trajectory is the list of realized states."""
    traj = [s]
    for _ in range(env.h_episode):
        s2, _, c = env.step(s, action)
        if c:
            return False, True, traj
        s = s2
        traj.append(s)
        if env.in_interior(s[0], s[1]):
            return True, False, traj
    return False, False, traj


def test_full_thickness_neck_is_the_uniform_band():
    """neck = r_out - r_in leaves the geometry unchanged: _in_mode agrees with
    the closed ring on a dense probe grid, so the knob's on-position at full
    thickness is the off-position."""
    base = RingField2D()
    full = RingField2D(neck=base.r_out - base.r_in)
    for k in range(400):
        ang = 2 * math.pi * k / 400
        for d in (3.4, 3.5, 3.7, 4.0, 4.3, 4.9, 5.0, 5.1):
            x = CENTER[0] + d * math.cos(ang)
            y = CENTER[1] + d * math.sin(ang)
            assert base._in_mode(x, y) == full._in_mode(x, y), (ang, d)


def test_neck_geometry_thins_from_outside_only_in_the_sector():
    """At the neck sector the band is [r_in, r_in + neck]; outside the sector
    it is the full [r_in, r_out]; the hole d < r_in is invariant everywhere."""
    env = RingField2D(neck=0.5)     # facing: sector centred at angle pi
    def at(ang, d):
        return (CENTER[0] + d * math.cos(ang), CENTER[1] + d * math.sin(ang))
    # facing side, in-sector: d = 4.5 is FREE (above the dipped outer radius 4.0)
    assert not env._in_mode(*at(math.pi, 4.5))
    # ... but still in the band at d = 3.7
    assert env._in_mode(*at(math.pi, 3.7))
    # hidden side (angle 0), out of sector: d = 4.5 is in the full band
    assert env._in_mode(*at(0.0, 4.5))
    # sector edge: just past the half-width the band is full again
    assert env._in_mode(*at(math.pi - env.neck_halfwidth - 0.01, 4.5))
    # the hole is invariant: d = 3.4 is interior at every angle
    for ang in (0.0, math.pi / 2, math.pi):
        assert env.in_interior(*at(ang, 3.4))
        assert not env._in_mode(*at(ang, 3.4))


def test_thin_annulus_is_contained_in_the_mode_at_every_angle():
    """A_thin = {r_in <= d <= r_in + neck} \\subseteq mode: the hypothesis of
    the local crossing lemma (`freeze_stays_outside_of_superset`), checked on
    a dense grid."""
    env = RingField2D(neck=0.5)
    for k in range(720):
        ang = 2 * math.pi * k / 720
        # strictly inside [r_in, r_in + neck]: the exact endpoints are float-
        # boundary cases of the polar reconstruction, not of the env
        for d in (3.501, 3.6, 3.75, 3.9, 3.999):
            x = CENTER[0] + d * math.cos(ang)
            y = CENTER[1] + d * math.sin(ang)
            assert env._in_mode(x, y), (ang, d)


def test_leap_witness_at_neck_half():
    """The deterministic witness: from (0.20, 0) at rest, constant action 0
    (thrust due east), the trajectory never contacts the band and enters the
    hole at t = 25 by one step of length 0.547 > neck = 0.5, from
    d = 4.034 > r_in + neck. Lemma 2's conclusion fails exactly where its
    hypothesis does."""
    env = RingField2D(neck=0.5)
    entered, frozen, traj = _run(env, (0.20, 0.0, 0.0, 0.0))
    assert entered and not frozen
    assert len(traj) - 1 == 26          # entry realized at step index 25
    s_prev, s_land = traj[-2], traj[-1]
    d_prev = math.hypot(s_prev[0] - CENTER[0], s_prev[1] - CENTER[1])
    d_land = math.hypot(s_land[0] - CENTER[0], s_land[1] - CENTER[1])
    step = math.hypot(s_land[0] - s_prev[0], s_land[1] - s_prev[1])
    assert d_land < env.r_in                      # inside the hole
    assert d_prev > env.r_in + env.neck           # from strictly outside A_thin
    assert step > env.neck                        # the leap exceeds the neck
    assert step == pytest.approx(0.5470, abs=5e-4)
    assert d_prev == pytest.approx(4.0345, abs=5e-4)
    # en route the trajectory is never in the band (the approach uses the dip)
    for s in traj[:-1]:
        assert not env._in_mode(s[0], s[1])


def test_witness_family_blocked_at_thick_neck():
    """The same 40-offset witness family never enters at neck >= 1.0 (max step
    is (gain/drag)*dt = 1.0, and entry needs a step > neck). A sampled zero
    would prove nothing; this family is deterministic, and the exact statement
    is the Lean lemma's."""
    for neck in (1.0, 1.2):
        env = RingField2D(neck=neck)
        for k in range(40):
            entered, _, _ = _run(env, (0.0125 * k, 0.0, 0.0, 0.0))
            assert not entered, (neck, k)
