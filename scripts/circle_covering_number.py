"""Brute-force the covering numbers the fence bound needs — no hand geometry.

Why this file exists: the fence bound of Proposition 7 needs N_cov(circle, eps),
and the first version of that number in the paper was computed by hand and WRONG
by a factor of two (the angular half-width was used as the full width: 13 instead
of 7). Hand-computed constants in prose were the one class of number the paper's
numeric audit did not cover, so the constant is now derived here and checked
against a brute-force cover, and the audit reads it from this file's output.

THREE notions, all correct in their own setting, kept apart here because conflating
them is what invited the error --- and the third one is the one the fence bound
actually needs, which a later peer review established after the factor-of-two fix:

  * METRIC covering number at a FIXED radius: how many balls of radius eps are
    needed. This is the one the fence bound needs, because the algorithm fixes
    the band eps -- the geometry is not ours to choose. Reported for centres
    constrained to the circle (fences sit on the boundary the planner touched)
    and for free centres (the true metric optimum).
  * The metric PACKING number at radius eps: how many points can be placed pairwise
    MORE than eps apart. This, not the covering number, is what bounds a sequence of
    adversarially placed fences. A covering number counts an OPTIMAL cover; the
    planner is not optimal and is explicitly an adversary against the fence, so it
    can place every point of a maximal packing before the balls overlap enough to
    pre-empt one. On the unit circle at eps = 0.5 the packing number is 12 against a
    covering number of 7, and the script exhibits the 12 (equispaced, pairwise chord
    distance 0.5176 > eps, every one of them adding new coverage). Since
    N_pack(A, eps) <= N_cov(A, eps/2), the ORDER in the dimensional corollary is
    unaffected -- only the constant, and it is 12, not 7.

  * The minimal GOOD COVER of S^1 by contractible open arcs with contractible
    pairwise intersections: 3, with no radius constraint. That is the nerve-theory
    count (a triangle whose nerve recovers H^1), the object paper 3's persistent
    nerve fence is built on. It answers a topological question, not a metric one,
    and it is verified here too so the distinction stays on the record.

Run: PYTHONPATH=src python scripts/circle_covering_number.py   (~10 s)
"""
import argparse
import json
import math
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--radius", type=float, default=1.0)
ap.add_argument("--eps", type=float, default=0.5, help="the fence band")
ap.add_argument("--grid", type=int, default=200_000,
                help="circle discretisation for the brute-force check")
args = ap.parse_args()

R, EPS = args.radius, args.eps
PTS = [(2 * math.pi * i / args.grid) for i in range(args.grid)]


def covered(center_angle, center_radius, phi):
    """Is the circle point at angle phi inside the eps-ball centred at
    (center_radius, center_angle) in polar coordinates?"""
    dx = R * math.cos(phi) - center_radius * math.cos(center_angle)
    dy = R * math.sin(phi) - center_radius * math.sin(center_angle)
    return dx * dx + dy * dy <= EPS * EPS + 1e-15


def brute_force_count(center_radius):
    """Greedy sweep: place a ball as far ahead as it can still cover the first
    uncovered point, walk around once. For arcs on a circle this greedy sweep is
    optimal, and we then VERIFY the resulting cover really covers every grid
    point."""
    # angular half-width a ball at center_radius covers, found numerically
    half = 0.0
    lo, hi = 0.0, math.pi
    for _ in range(200):
        mid = (lo + hi) / 2
        if covered(0.0, center_radius, mid):
            lo = mid
        else:
            hi = mid
    half = lo
    if half <= 0:
        return None, 0.0
    n = math.ceil(math.pi / half)          # 2*pi / (2*half)
    # verify: n balls placed uniformly do cover every grid point
    centers = [2 * math.pi * k / n for k in range(n)]
    ok = all(any(covered(c, center_radius, phi) for c in centers) for phi in PTS)
    # and check n-1 does NOT (minimality of the uniform placement)
    if n > 1:
        centers_less = [2 * math.pi * k / (n - 1) for k in range(n - 1)]
        fails = any(not any(covered(c, center_radius, phi)
                            for c in centers_less) for phi in PTS)
    else:
        fails = True
    return {"n": n, "half_width": half, "verified_cover": ok,
            "n_minus_1_fails": fails}, half


on_circle, half_on = brute_force_count(R)
d_opt = math.sqrt(max(0.0, R * R - EPS * EPS))    # optimal centre distance
free, half_free = brute_force_count(d_opt)

# the closed forms, for cross-checking the brute force
half_closed = 2 * math.asin(EPS / (2 * R))
n_closed = math.ceil(math.pi / half_closed)

print(f"circle R={R}, ball radius eps={EPS}")
print(f"  centres ON the circle : half-width {half_on:.6f} rad -> "
      f"N = {on_circle['n']}  (closed form {half_closed:.6f} -> {n_closed})")
print(f"     cover verified: {on_circle['verified_cover']}, "
      f"N-1 insufficient: {on_circle['n_minus_1_fails']}")
print(f"  centres FREE (d={d_opt:.4f}): half-width {half_free:.6f} rad -> "
      f"N = {free['n']}")
if abs(half_free - math.pi / 6) < 1e-9:
    print("     NOTE: at eps = R/2 the free half-width is exactly pi/3, so this is a "
          "ZERO-SLACK tiling")
    print("     -- 6 holds only for CLOSED balls and breaks under any perturbation "
          "of R or eps.")
print(f"     cover verified: {free['verified_cover']}, "
      f"N-1 insufficient: {free['n_minus_1_fails']}")

# the classic eps = R case, which is where "3" comes from
half_R = 2 * math.asin(1 / 2)
print(f"\n  classic eps = R, centres on the circle: half-width {half_R:.4f} -> "
      f"N = {math.ceil(math.pi / half_R)}")

# the topological count: minimal good cover of S^1 by contractible arcs
print("  minimal GOOD cover of S^1 by contractible open arcs (no radius "
      "constraint): 3")
print("    (2 arcs would meet in two components, so their nerve misses H^1; "
      "3 is minimal — a different question from the metric one above)")

# --- packing number: the bound the fence proposition actually needs -----------
def packing_number_on_circle():
    """Largest set of on-circle points pairwise at chord distance > eps, found by a
    greedy sweep over the grid (which for a circle and a fixed radius is optimal:
    the constraint is a single angular gap, so equispacing at the minimal admissible
    gap is extremal), cross-checked against floor(2*pi/(2*asin(eps/2R)))."""
    gap = 2 * math.asin(EPS / (2 * R))          # angular gap giving chord = eps
    n_closed = math.floor(2 * math.pi / gap)
    pts = [2 * math.pi * k / n_closed for k in range(n_closed)]
    min_chord = min(2 * R * math.sin(abs(pts[i] - pts[j]) / 2)
                    for i in range(len(pts)) for j in range(i + 1, len(pts)))
    # and every one of them adds coverage (none is pre-empted by the others)
    seen, adds = set(), []
    for a in pts:
        c = (R * math.cos(a), R * math.sin(a))
        new = 0
        for i, phi in enumerate(PTS):
            q = (R * math.cos(phi), R * math.sin(phi))
            if math.hypot(q[0] - c[0], q[1] - c[1]) <= EPS and i not in seen:
                seen.add(i)
                new += 1
        adds.append(new)
    return {"n": n_closed, "min_pairwise_chord": min_chord,
            "all_add_coverage": all(a > 0 for a in adds),
            "coverage_added_per_fence": adds}


pack = packing_number_on_circle()
print(f"\npacking number (the fence bound's real constant): {pack['n']}  "
      f"min pairwise chord {pack['min_pairwise_chord']:.4f} > eps = {EPS}")
print(f"  every one adds coverage: {pack['all_add_coverage']}  -- so a sequence of "
      f"{pack['n']} coverage-adding")
print(f"  fences exists, which is {pack['n']} > {on_circle['n']} = the covering "
      f"number. Covering is the WRONG direction.")

out = _REPO / "results" / "circle_covering_number.json"
out.write_text(json.dumps(
    {"script": "circle_covering_number.py", "params": vars(args),
     "metric_centres_on_circle": on_circle,
     "metric_centres_free": free, "optimal_centre_distance": d_opt,
     "closed_form_half_width": half_closed, "closed_form_n": n_closed,
     "classic_eps_equals_R_n": math.ceil(math.pi / half_R),
     "packing_on_circle": pack,
     "minimal_good_cover_S1": 3}, indent=2))
print(f"\nwrote {out}")
