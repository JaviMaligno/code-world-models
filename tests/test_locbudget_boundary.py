"""Oracle tests for the boundary-aware localization-budget constants.

The certified constants are exact Fractions from a product formula; the oracle is
brute-force Monte Carlo volume estimation on random boxes and points. Every claimed
regime (interior, face, edge, corner, mixed partial clips) is exercised, plus the
sharpness of 2^-(d+m) and the >= 1/2 face law under extent >= rho.
"""
import pathlib
import random
import sys
from fractions import Fraction

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

from locbudget_boundary_constants import (box_case_table, clipped_fraction,  # noqa: E402
                                          kappa_box)


def mc_kappa(z, rho, box, n=200_000, seed=0):
    """Monte Carlo estimate of vol(B_infty(z, rho) ∩ box) / (2 rho)^dim, treating
    None bounds as unbounded (factor 1 by sampling the ball coordinate freely)."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(n):
        ok = True
        for z_k, bounds in zip(z, box):
            u = z_k + rho * (2 * rng.random() - 1)
            if bounds is not None and not (bounds[0] <= u <= bounds[1]):
                ok = False
                break
        hits += ok
    return hits / n


def test_interior_face_edge_corner_exact_values():
    box = [(-1, 1), (0, 4), (-3, 3)]
    rho = Fraction(1, 2)
    assert kappa_box((0, 2, 0), rho, box) == 1                     # interior
    assert kappa_box((1, 2, 0), rho, box) == Fraction(1, 2)        # face
    assert kappa_box((1, 0, 0), rho, box) == Fraction(1, 4)        # edge
    assert kappa_box((1, 0, 3), rho, box) == Fraction(1, 8)        # corner: sharp 2^-dim


def test_face_law_needs_extent_at_least_rho():
    # extent >= rho gives factor >= 1/2 at any interior-or-boundary point ...
    for z in (0, 0.25, 0.5):
        assert clipped_fraction(z, Fraction(1, 2), 0, Fraction(1, 2)) >= Fraction(1, 2)
    # ... and a thinner interval drops below it (the corollary's extent hypothesis).
    assert clipped_fraction(0, Fraction(1, 2), 0, Fraction(1, 4)) < Fraction(1, 2)


def test_unbounded_coordinates_contribute_factor_one():
    # the instruments' domains: states unbounded, action in [-1, 1]
    assert kappa_box((3.7, -12.0, 1), Fraction(1, 4), [None, None, (-1, 1)]) \
        == Fraction(1, 2)
    assert kappa_box((3.7, -12.0, Fraction(1, 2)), Fraction(1, 4),
                     [None, None, (-1, 1)]) == 1


@pytest.mark.parametrize("seed", range(6))
def test_product_formula_against_monte_carlo(seed):
    rng = random.Random(1000 + seed)
    dim = rng.choice([2, 3])
    box, z = [], []
    for _ in range(dim):
        if rng.random() < 0.25:
            box.append(None)
            z.append(rng.uniform(-5, 5))
        else:
            lo = rng.uniform(-3, 0)
            hi = lo + rng.uniform(0.5, 4)
            box.append((Fraction(round(lo, 3)).limit_denominator(1000),
                        Fraction(round(hi, 3)).limit_denominator(1000)))
            z.append(rng.uniform(float(box[-1][0]), float(box[-1][1])))
    rho = Fraction(round(rng.uniform(0.1, 1.5), 3)).limit_denominator(1000)
    exact = float(kappa_box(z, rho, box))
    est = mc_kappa(z, float(rho), [(float(b[0]), float(b[1])) if b else None
                                   for b in box], seed=seed)
    assert abs(exact - est) < 0.01


def test_case_table_is_the_powers_of_two():
    t = box_case_table(5)
    assert t["interior"] == "1" and t["face"] == "1/2" and t["5-face corner"] == "1/32"


def test_rejects_points_outside_the_domain():
    with pytest.raises(ValueError):
        clipped_fraction(2, Fraction(1, 2), -1, 1)
