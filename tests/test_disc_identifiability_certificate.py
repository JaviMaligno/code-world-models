"""Oracle tests for the per-block disc-identifiability certificate.

The certificate makes UNIVERSAL claims (every consistent hypothesis is near the truth /
no consistent member of a family exists), so the oracle is brute force: dense random
sampling of hypothesis space must never find a consistent hypothesis outside the
certified brackets, and must agree with every family's exclusion verdict. Synthetic
instances are built so the right answer is known by construction; a real gate sample
then exercises the labelled-evidence reduction end to end.
"""
import math
import pathlib
import random
import sys

import numpy as np
import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

import disc_identifiability_certificate as D  # noqa: E402

from cwm.continuous.contract import collect_transitions  # noqa: E402
from cwm.continuous.envs import PatchField2D             # noqa: E402


def ring_instance(arc_deg, n_in=16, n_out=200, gap=0.15, R=1.0, c=(3.0, 0.0), seed=0):
    """Inside points on an arc just inside the circle; outside points on a ring just
    outside it (full circle) plus a far cloud. Wide arcs pin the disc; narrow ones
    leave the version space wide."""
    rng = random.Random(seed)
    half = math.radians(arc_deg) / 2
    thetas = [math.pi + rng.uniform(-half, half) for _ in range(n_in)]
    I1 = [(c[0] + (R - 0.02) * math.cos(t), c[1] + (R - 0.02) * math.sin(t))
          for t in thetas]
    O = [(c[0] + (R + gap) * math.cos(2 * math.pi * k / n_out),
          c[1] + (R + gap) * math.sin(2 * math.pi * k / n_out)) for k in range(n_out)]
    O += [(c[0] + rng.uniform(-8, 8), c[1] + rng.uniform(-8, 8)) for _ in range(300)]
    O = [(x, y) for x, y in O if (x - c[0]) ** 2 + (y - c[1]) ** 2 > R * R]
    return np.array(I1), np.array(O)


def brute_force_consistent(I1, O, n=200_000, seed=1, span=20.0, centre=(3.0, 0.0)):
    """Random consistent (c, R) hypotheses found by rejection sampling — the oracle
    the certificate's outer brackets must contain."""
    rng = np.random.default_rng(seed)
    C = np.stack([rng.uniform(centre[0] - span, centre[0] + span, n),
                  rng.uniform(centre[1] - span, centre[1] + span, n)], axis=1)
    found = []
    for k in range(0, n, 4096):
        c = C[k:k + 4096]
        dmax = np.sqrt(((c[:, None, :] - I1[None]) ** 2).sum(2)).max(1)
        omin = np.sqrt(((c[:, None, :] - O[None]) ** 2).sum(2)).min(1)
        ok = dmax < omin
        for cc, lo, hi in zip(c[ok], dmax[ok], omin[ok]):
            found.append((cc[0], cc[1], (lo + hi) / 2))
    return found


def test_wide_arc_certifies_and_brackets_are_sound():
    I1, O = ring_instance(arc_deg=340, gap=0.05)
    cert = D.version_space_certificate(I1, O, (3.0, 0.0), 1.0)
    assert cert["certified"] and cert["feasible"]
    # a 340-degree arc with a hugging ring pins the disc well inside 0.1
    assert cert["identified_at_tol"]
    for cx, cy, r in brute_force_consistent(I1, O):
        assert math.hypot(cx - 3.0, cy) <= cert["centre_dev_max"] + 1e-9
        # every consistent radius interval intersects the certified bracket
        assert cert["R_bracket"][0] - 1e-9 <= r <= cert["R_bracket"][1] + 1e-9


def test_narrow_arc_does_not_certify_at_tol_and_oracle_agrees():
    I1, O = ring_instance(arc_deg=60, gap=0.6)
    cert = D.version_space_certificate(I1, O, (3.0, 0.0), 1.0)
    assert cert["certified"] and cert["feasible"]
    found = brute_force_consistent(I1, O)
    # the oracle exhibits a consistent centre beyond the tolerance, so the
    # certificate must not claim identification ...
    dev = max(math.hypot(cx - 3.0, cy) for cx, cy, _ in found)
    if dev > 0.1:
        assert not cert["identified_at_tol"]
    # ... and its brackets still contain everything the oracle found
    assert dev <= cert["centre_dev_max"] + 1e-9


def test_far_field_unbounded_when_separable():
    # inside cluster with outside points only on one side: a separating direction
    # exists, far discs are consistent, and the certificate must say so
    I1 = np.array([(3.0, 0.0), (3.1, 0.2), (2.9, -0.1)])
    O = np.array([(1.0, y / 10) for y in range(-20, 21)])
    cert = D.version_space_certificate(I1, O, (3.0, 0.0), 1.0)
    assert not cert["certified"]
    hp = D.halfplane_certificate(I1, O)
    assert hp["consistent"] and hp["margin"] > 0


def test_template_family_checks_against_brute_force():
    I1, O = ring_instance(arc_deg=340, gap=0.05, seed=3)
    # half-plane: hulls overlap (outside ring surrounds the inside arc)
    assert not D.halfplane_certificate(I1, O)["consistent"]
    checks = D.slab_and_box_checks(I1, O)
    # the outside ring populates every coordinate range of the inside arc
    assert not checks["slab_x_consistent"] and not checks["box_consistent"]
    # square: brute-force scan of (c, s) agrees with the exclusion verdict
    sq = D.version_space_certificate(I1, O, (3.0, 0.0), 1.0, sup=True)
    far = D.square_far_checks(I1, O)
    excluded = sq.get("certified") and not sq.get("feasible", True) \
        and not far["any_consistent"]
    rng = np.random.default_rng(7)
    C = np.stack([rng.uniform(-10, 16, 100_000), rng.uniform(-13, 13, 100_000)], axis=1)
    dmax = np.abs(C[:, None, :] - I1[None]).max(2).max(1)
    omin = np.abs(C[:, None, :] - O[None]).max(2).min(1)
    assert excluded == (not (dmax < omin).any())


def test_square_evidence_keeps_square_consistent():
    # inside points from a square boundary, outside points hugging it: the square
    # family must remain consistent (sanity for the exclusion's direction)
    s, c = 1.0, (3.0, 0.0)
    I1 = np.array([(c[0] + s * 0.98 * math.cos(t), c[1] + s * 0.98 * math.sin(t) /
                    max(abs(math.cos(t)), abs(math.sin(t))) * 0.98)
                   for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)])
    I1 = np.clip(I1 - np.array(c), -0.98, 0.98) + np.array(c)
    O = np.array([(c[0] + x, c[1] + y) for x in np.linspace(-1.4, 1.4, 15)
                  for y in np.linspace(-1.4, 1.4, 15)
                  if max(abs(x), abs(y)) > 1.05])
    sq = D.version_space_certificate(I1, O, c, 1.0, sup=True)
    assert sq["certified"] and sq["feasible"]


def test_hull_of_contacts_always_consistent_on_convex_truth():
    for seed in range(5):
        I1, O = ring_instance(arc_deg=200, gap=0.3, seed=seed)
        K = D.hull(I1)
        assert not any(D.point_in_hull((x, y), K) for x, y in O)


def test_labelled_evidence_reduction_on_a_real_sample():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    tr = collect_transitions(env, 5, seed=10_000)
    I1, I2, O = D.labelled_points(env, tr)   # asserts the lemma internally
    assert len(I1) + len(I2) + len(O) == len(tr)


def test_clamp_boundary_points_and_three_point_uniqueness():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), mode_effect="clamp")
    tr = collect_transitions(env, 40, seed=10_000)
    row = D.clamp_block_certificate(env, tr)
    if row["n_boundary_points_p1"] >= 3 and row.get("noncollinear_triple_area", 0) > 1e-9:
        assert row["exactly_identified"]
        assert row["circumcircle_centre_err"] < 1e-9


def test_circumcircle_recovers_a_known_circle():
    c, R = (2.0, -1.0), 3.0
    pts = [(c[0] + R * math.cos(t), c[1] + R * math.sin(t)) for t in (0.3, 1.9, 4.0)]
    cc, r = D.circumcircle(*pts)
    assert math.hypot(cc[0] - c[0], cc[1] - c[1]) < 1e-12 and abs(r - R) < 1e-12


def test_collinear_points_are_not_called_identified():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), mode_effect="clamp")
    fake = [{"contact": True, "next_state": [3.0 + 1.0, 0.0, 0, 0]},
            {"contact": True, "next_state": [3.0 - 1.0, 0.0, 0, 0]},
            {"contact": False, "next_state": [0, 0, 0, 0]}]
    row = D.clamp_block_certificate(env, fake)
    assert not row["exactly_identified"]
