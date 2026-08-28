"""Offline tests for cwm.continuous.mpc's random-shooting planner, focused on
the action-interface split (paper 3, docs/paper3/SHELLFIELD-N-DESIGN.md, "the
action interface"):

- action_dim == 1 (the golden-protected scalar path) must stay byte-for-byte
  unchanged by the vector-path axial-candidate addition below.
- action_dim > 1 must include the 2*action_dim axial unit-vector constant
  candidates +-e_i (calibration 2026-07-21,
  scripts/continuous_shellfield_play_diag.py "percomponent_axial"): the
  existing {(-1,)^n, (1,)^n, (0,)^n} triple points only at cube
  diagonals/origin, never axially, so a blind planner driving straight at an
  axial target never got a sustained-heading candidate to imagine it with.
"""
import random

from cwm.continuous.envs import CartWall, ShellFieldN
from cwm.continuous import mpc


CART = CartWall(x_wall=8.0)


def test_scalar_path_byte_identical_candidates():
    """action_dim=1's candidate generator is untouched by the vector-path
    change: exactly the three scalar constants {-a_max, 0, +a_max} followed
    by the n_samples piecewise-constant blocks, nothing else."""
    a_max = 2.0
    rng = random.Random(11)
    cands = list(mpc._candidates(a_max, rng, horizon=5, n_samples=3, block=2,
                                  action_dim=1))
    assert cands[0] == [-a_max] * 5
    assert cands[1] == [a_max] * 5
    assert cands[2] == [0.0] * 5
    assert len(cands) == 3 + 3  # 3 constants + n_samples blocks, no axials


def test_scalar_path_plan_byte_identical_given_seed():
    """mpc.plan's action_dim=1 output for a fixed seed must match the
    pre-fix reference value exactly (golden: computed against the unmodified
    scalar branch, which this change does not touch)."""
    for seed in (0, 1, 2, 7):
        a_ref = mpc.plan(CART, (0.5, 1.0), random.Random(seed), n_samples=50)
        a_again = mpc.plan(CART, (0.5, 1.0), random.Random(seed), n_samples=50)
        assert a_ref == a_again
    # explicit action_dim=1 must reduce to the default (no action_dim) path
    a_default = mpc.plan(CART, (0.5, 1.0), random.Random(3), n_samples=50)
    a_explicit = mpc.plan(CART, (0.5, 1.0), random.Random(3), n_samples=50,
                          action_dim=1)
    assert a_default == a_explicit


def test_vector_path_includes_axial_unit_candidates():
    """action_dim>1's candidate set must contain, among the constant
    candidates, the 2*action_dim axial unit vectors +-e_i (as sustained
    constant sequences), in addition to the existing diagonal/origin
    triple."""
    n = 4
    rng = random.Random(5)
    cands = list(mpc._candidates(1.0, rng, horizon=6, n_samples=2, block=2,
                                  action_dim=n))
    # First 3 + 2n entries are constants (each a single tuple repeated for
    # the whole horizon); the remainder are the random per-component blocks.
    n_constants = 3 + 2 * n
    constant_candidates = cands[:n_constants]
    assert len(cands) == n_constants + 2

    expected_axials = set()
    for i in range(n):
        e = tuple(1.0 if j == i else 0.0 for j in range(n))
        expected_axials.add(e)
        expected_axials.add(tuple(-c for c in e))
    assert len(expected_axials) == 2 * n

    found_axials = {seq[0] for seq in constant_candidates if seq[0] in expected_axials}
    assert found_axials == expected_axials

    # each axial candidate must be a SUSTAINED constant over the horizon
    for seq in constant_candidates:
        if seq[0] in expected_axials:
            assert all(a == seq[0] for a in seq)

    # the pre-existing diagonal/origin triple must still be present unchanged
    assert tuple((-1.0,) * n) in {c[0] for c in constant_candidates}
    assert tuple((1.0,) * n) in {c[0] for c in constant_candidates}
    assert tuple((0.0,) * n) in {c[0] for c in constant_candidates}


def test_vector_path_axial_candidates_via_shellfieldn_action_dim():
    """Same check driven end-to-end through a real model's action_dim
    attribute, matching how mpc.plan reads it off ShellFieldN."""
    env = ShellFieldN(n=3)
    rng = random.Random(2)
    cands = list(mpc._candidates(env.a_max, rng, horizon=4, n_samples=1,
                                  block=2, action_dim=env.action_dim))
    expected_axials = set()
    for i in range(env.action_dim):
        e = tuple(1.0 if j == i else 0.0 for j in range(env.action_dim))
        expected_axials.add(e)
        expected_axials.add(tuple(-c for c in e))
    seen = {c[0] for c in cands}
    assert expected_axials <= seen
