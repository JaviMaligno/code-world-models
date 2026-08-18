"""The boundary constants of the localization budget (cor:kappabudget), exactly.

The corollary's hand constants are the interior-volume factors of a sup-metric ball
clipped by an axis-aligned box: 1 in the interior, 1/2 at a face, 2^-k with k clipped
coordinates, 2^-(d+m) sharp at a full corner --- all under the extent condition that
each bounded side is at least rho. Hand constants are this repo's weak class, so this
module computes them from the product formula in exact rational arithmetic instead of
asserting them; tests/test_locbudget_boundary.py checks the formula against brute-force
Monte Carlo volume estimation and exercises every case.

Conventions: a box is a sequence of per-coordinate (lo, hi) bounds, with None meaning
the coordinate is unbounded (the instruments' state coordinates; an unbounded
coordinate never clips and contributes factor 1).

Run as a script to print the case table and the instrument instantiation:
  PYTHONPATH=src .venv/bin/python scripts/locbudget_boundary_constants.py
"""
from fractions import Fraction


def clipped_fraction(z, rho, lo, hi):
    """Exact fraction of the interval [z - rho, z + rho] retained by [lo, hi].

    Requires z in [lo, hi] (the ball is centred at a domain point) and rho > 0.
    Under the extent condition hi - lo >= rho the result is at least 1/2; a
    thinner interval can drop below it, which is why the corollary carries the
    condition.
    """
    z, rho, lo, hi = Fraction(z), Fraction(rho), Fraction(lo), Fraction(hi)
    if rho <= 0:
        raise ValueError(f"rho must be positive, got {rho}")
    if not lo <= z <= hi:
        raise ValueError(f"centre {z} outside [{lo}, {hi}]")
    return (min(z + rho, hi) - max(z - rho, lo)) / (2 * rho)


def kappa_box(z, rho, box):
    """Exact vol(B_infty(z, rho) ∩ box) / (2 rho)^dim by the product formula.

    box entries are (lo, hi) or None for an unbounded coordinate (factor 1).
    """
    kappa = Fraction(1)
    for z_k, bounds in zip(z, box):
        if bounds is not None:
            kappa *= clipped_fraction(z_k, rho, bounds[0], bounds[1])
    return kappa


def box_case_table(dim):
    """The corollary's case table for a dim-dimensional box: powers of two."""
    table = {"interior": str(Fraction(1)), "face": str(Fraction(1, 2))}
    for k in range(2, dim + 1):
        table[f"{k}-face corner"] = str(Fraction(1, 2**k))
    return table


if __name__ == "__main__":
    for dim in (1, 2, 3, 4, 6):
        print(f"dim {dim}: {box_case_table(dim)}")
    # the instruments' domains: state coordinates unbounded, the single scalar
    # action in [-1, 1] (PatchField2D's action is a heading angle, m = 1 there
    # too), so at most one coordinate clips and kappa >= 1/2.
    print("cart/pendulum (d=2, m=1), action at the clamp:",
          kappa_box((0.0, 0.0, 1), Fraction(1, 4), [None, None, (-1, 1)]))
    print("patchfield2d (d=4, m=1), action at the clamp:",
          kappa_box((0.0, 0.0, 0.0, 0.0, 1), Fraction(1, 4),
                    [None, None, None, None, (-1, 1)]))
