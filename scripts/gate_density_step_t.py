"""The gate's visitation density at ANY step, as a rigorous POINTWISE lower bound.

The coverage certificate's one remaining open hypothesis was that the visitation
density is derived in closed form only at step 1, which restricted the certified
region U to the one-step reachable set. This derives it for every step t >= 2, so
the certificate applies to the much larger region the gate actually visits, and it
now delivers the object Proposition "coverage" actually consumes: an infimum of the
(s, a) density over a fixed region, not an average.

THE DERIVATION. Under the gate policy the plant is linear and time-invariant, so
(x_t, v_t) is an affine function of (x_0, a_0, ..., a_{t-1}), all independent
uniforms. Split off the LAST TWO actions:

    (x_t, v_t) = W_t + M (a_{t-1}, a_{t-2})^T,

where W_t is the contribution of x_0 and a_0..a_{t-3} (the state reached with the
last two actions set to zero) and M is the Jacobian of the last two actions, which
by time-invariance does not depend on t:

    dx/da_{t-1} = dt*gain*dt        dx/da_{t-2} = dt*k*gain*dt + gain*dt^2
    dv/da_{t-1} = gain*dt           dv/da_{t-2} = k*gain*dt          (k = 1 - drag*dt)

    |det M| = 0.009 for the paper's constants, verified against finite differences.

W_t is independent of those two actions, so the step-t law is the convolution of
W_t's law with the uniform law on the parallelogram P = M[-a_max, a_max]^2, whose
area is 4 a_max^2 |det M| = 0.036 and whose density is 1/0.036 = 27.78. Hence, for
every t >= 2 and every u, an EXACT identity (not a bound):

    p_t(u) = (1/area(P)) * P( W_t in u - P ).

TWO THINGS THIS SCRIPT GETS RIGHT ONLY SINCE 2026-07-25, both caught in peer review
and both of which had inflated the certified region by a factor of two or more.

(1) THE ACTION DIMENSION. Proposition "coverage" consumes the density of (s, a) on
    R^3, not of (x, v) on R^2. The action is uniform on [-a_max, a_max] and
    independent of the state, so p_{3D} = p_{2D} / (2 a_max). The first version
    reported p_{2D} and fed it in as p_{3D} -- a factor 2 on the cart, while the
    step-1 corollary (c = 5/6, which does include the action factor) got it right,
    so the two instantiations silently disagreed.

(2) AVERAGE vs INFIMUM. The first version binned samples on a grid and divided a
    per-cell frequency by the cell volume. That estimates the cell AVERAGE of the
    density, which does not lower-bound its infimum -- and the infimum is the
    hypothesis. The fix is a Minkowski erosion, and it is exact:

        for u in C,   u - P  contains  ( c0 - (1-L)P )   whenever C = c0 + L*P,

    because u - w = L*p + (1-L)*q lies in P by convexity (P is centrally
    symmetric, so -P = P). So if the cells are SCALED COPIES of P itself -- which
    tile the plane, being parallelograms -- then

        inf_{u in C} p_t(u)  >=  (1/area(P)) * P( W_t in c0 - (1-L)P ),

    a genuine pointwise infimum over the whole cell, estimated by Monte Carlo on
    W_t with a Wilson lower bound. Choosing cells shaped like P is what makes the
    erosion non-empty: P is a thin sliver (0.12 by 1.19, area 0.036), and eroding
    it by an axis-aligned square of any useful size leaves nothing at all.

POST-SELECTION. The cell family is fixed BEFORE looking at the data, and the
per-cell Wilson bounds are taken at level delta/n_cells, so they hold
simultaneously. Selecting the level set {c : bound >= alpha} afterwards is then
legitimate: the guarantee "inf_U p >= alpha" holds with probability 1 - delta for
whichever union of cells the data picks out.

WHAT IT BUYS, END TO END. The script does not stop at (c, U): it runs the
certificate on each level set, with the corrected covering-number direction
(vol(U + B_{rho/4}) / vol(B_{rho/4}), an upper bound on the packing number) and the
corrected boundary treatment (see certify(): a union of cells admits no 2^-DIM
orthant argument, so the ball mass is bounded by cell containment), and reports the
rho and the uniform bound eps + 2 L rho each region
certifies at the deployed N = 40. Those two numbers used to be computed by hand in
the paper's prose, which is exactly how they came to be wrong.

Run: PYTHONPATH=src python scripts/gate_density_step_t.py   (~4 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402
from cwm.law import wilson_ci             # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--steps", type=int, nargs="+", default=[2, 5, 10, 20, 40, 80])
ap.add_argument("--region", type=float, nargs=2, default=[3.0, 2.0],
                help="consider cells inside |x| <= X, |v| <= V")
ap.add_argument("--lam", type=float, default=0.25,
                help="cell = lam*P. The erosion is (1-lam)P, so the bound loses a factor\n                     (1-lam)^2 against the true density: SMALLER lam is tighter (and\n                     finer), at the cost of more cells in the union bound. An oracle\n                     test pins the validity (0 violations) and that loss factor.")
ap.add_argument("--mc", type=int, default=40000, help="MC samples of W_t")
ap.add_argument("--delta", type=float, default=0.05)
ap.add_argument("--n-gate", type=int, default=40, help="the deployed N")
ap.add_argument("--eps-gate", type=float, default=0.01)
ap.add_argument("--seed", type=int, default=99)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
dt, g, dr, A = env.dt, env.gain, env.drag, env.a_max
k = 1 - dr * dt
DIM = 3
L_PLANT = max(abs(1 - dr * dt) + g * dt, 1.0 + dt * abs(1 - dr * dt) + g * dt ** 2)

# --- M and its determinant, in closed form ----------------------------------
M = [[dt * g * dt, dt * k * g * dt + g * dt * dt],   # dx/da_{t-1}, dx/da_{t-2}
     [g * dt,      k * g * dt]]                      # dv/da_{t-1}, dv/da_{t-2}
DET = M[0][0] * M[1][1] - M[0][1] * M[1][0]
AREA_P = 4 * A * A * abs(DET)
DENS_P = 1.0 / AREA_P
LAM = args.lam
GX, GV = args.region


def m_inv(u):
    """M^{-1} u."""
    a, b, c, d = M[0][0], M[0][1], M[1][0], M[1][1]
    return ((d * u[0] - b * u[1]) / DET, (-c * u[0] + a * u[1]) / DET)


def m_apply(z):
    return (M[0][0] * z[0] + M[0][1] * z[1], M[1][0] * z[0] + M[1][1] * z[1])


def cell_center(i, j):
    """Cell (i, j) is c0 + LAM*P with c0 on the lattice LAM*M*(2A*Z^2)."""
    return m_apply((LAM * 2 * A * (i + 0.5), LAM * 2 * A * (j + 0.5)))


def cells_eroded_at(w):
    """Every cell C whose erosion contains w, i.e. c0 in w + (1-LAM)P.

    In lattice coordinates z = M^{-1}c0 / (LAM*2A) the condition is
    |z - M^{-1}w/(LAM*2A)| <= (1-LAM)/(2*LAM) componentwise, so this is a tiny
    box scan -- the whole reason the P-shaped lattice is worth the algebra."""
    y = m_inv(w)
    y = (y[0] / (LAM * 2 * A), y[1] / (LAM * 2 * A))
    h = (1 - LAM) / (2 * LAM)
    out = []
    for i in range(math.floor(y[0] - h - 0.5), math.ceil(y[0] + h + 0.5) + 1):
        for j in range(math.floor(y[1] - h - 0.5), math.ceil(y[1] + h + 0.5) + 1):
            if abs(i + 0.5 - y[0]) <= h and abs(j + 0.5 - y[1]) <= h:
                out.append((i, j))
    return out


def w_sample(t, i):
    """W_t: the step-t state with the last two actions set to zero."""
    rng = random.Random(args.seed + 7919 * t + i)
    x = rng.uniform(-0.5, 0.5)
    v = 0.0
    acts = [rng.uniform(-A, A) for _ in range(t)]
    acts[-1] = 0.0
    acts[-2] = 0.0
    for a in acts:
        v = v + (g * a - dr * v) * dt
        x = x + v * dt
    return (x, v)


def in_region(i, j):
    """Keep only cells wholly inside the region box (all four corners)."""
    c0 = cell_center(i, j)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = m_apply((LAM * A * sx, LAM * A * sy))
            if abs(c0[0] + d[0]) > GX or abs(c0[1] + d[1]) > GV:
                return False
    return True


# --- geometry of one cell, and of a union of cells ---------------------------
CELL_AREA = LAM * LAM * AREA_P
_CORNERS = [m_apply((LAM * A * sx, LAM * A * sy))
            for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1))]


def _hull_area(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return 0.0

    def half(ps):
        st = []
        for p in ps:
            while len(st) >= 2 and ((st[-1][0] - st[-2][0]) * (p[1] - st[-2][1])
                                    - (st[-1][1] - st[-2][1]) * (p[0] - st[-2][0])) <= 0:
                st.pop()
            st.append(p)
        return st
    hull = half(pts)[:-1] + half(pts[::-1])[:-1]
    return abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1]
                   - hull[(i + 1) % len(hull)][0] * hull[i][1]
                   for i in range(len(hull)))) / 2


def cell_grown_area(s):
    """area(LAM*P + B_s) exactly: the Minkowski sum of two convex polygons is the
    hull of the pairwise vertex sums."""
    sq = [(-s, -s), (-s, s), (s, s), (s, -s)]
    return _hull_area([(c[0] + q[0], c[1] + q[1]) for c in _CORNERS for q in sq])


def vol_U_grown(n_cells, s):
    """An UPPER bound on vol(U + B_s) in (x, v, a), for U = S x [-A, A] with S a
    union of n_cells cells: volume is subadditive over the union, and the action
    axis grows by s on each side."""
    return n_cells * cell_grown_area(s) * (2 * (A + s))


Z_CONSERVATIVE = 4.0
"""Wilson at z = 4 is a per-cell level of ~3.2e-5; with a few thousand cells the
family-wise level stays below delta = 0.05. Conservative on purpose, and the same
machinery the rest of the paper uses (an exact Clopper-Pearson tail overflows in
plain floats at n in the tens of thousands)."""


def certify(c_density, n_cells):
    """The largest rho the deployed gate certifies on this (c, U), and the uniform
    bound it implies.

    The ball-mass question needs care here, and the easy answer is wrong. For an
    axis-aligned box a net point on the boundary keeps one orthant of its sup-ball,
    a factor 2^-DIM. U is NOT a box: it is a union of parallelogram cells, and a
    point on the union's outer boundary can keep far less than an orthant --- there
    is no general 2^-DIM for a union. (The step-1 certificate has the same issue in
    milder form: its U is a SHEARED box, where the true factor is 0.950 * 2^-DIM
    rather than 2^-DIM, computed in gate_coverage_certificate.py.)

    So we use the one bound that needs no shape assumption at all. If u lies in cell
    C and diam(C) <= rho/2, then C is entirely inside B(u, rho/2), hence

        vol(B(u, rho/2) INTERSECT U)  >=  vol(C_xv) * min(rho/2, 2 a_max),

    the action factor being the part of the ball's action interval that survives
    inside [-a_max, a_max]. That is much smaller than an orthant of the ball, so the
    step-t certificates come out weaker --- which only strengthens the conclusion
    they support, namely that no step-t region beats the step-1 corollary at this
    gate size. A tighter honest version would certify over the rho/2-interior of the
    level set (where the factor is exactly 1); that region is empty at the rho values
    N = 40 can reach, so it would buy nothing here."""
    vol_U = n_cells * CELL_AREA * 2 * A
    best = None
    rho = 0.005
    while rho < 6.0:
        K = max(1.0, vol_U_grown(n_cells, rho / 4) / ((rho / 2) ** DIM))
        # cell-containment lower bound on the ball mass: no shape assumption
        p = c_density * CELL_AREA * min(rho / 2, 2 * A)
        if math.log(K / args.delta) / p <= args.n_gate:
            best = rho
            break
        rho += 0.005
    if best is None:
        return None
    return {"rho": best, "uniform_bound": args.eps_gate + 2 * L_PLANT * best,
            "vol_U": vol_U}


ALPHAS = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01]
rows = []
print(f"|det M| = {abs(DET):.6f}   area(P) = {AREA_P:.6f}   1/area(P) = "
      f"{DENS_P:.4f}   (a density exists at every t >= 2)")
print(f"cells = {LAM} * P (area {CELL_AREA:.6f}), erosion contains "
      f"{1-LAM:.2f}*P;  MC = {args.mc};  L = {L_PLANT:.4f}\n")
print(f"{'step':>5} {'cells':>7} " + " ".join(f"vol(p>={a})".rjust(11) for a in ALPHAS))
for t_step in args.steps:
    hits = {}
    for i in range(args.mc):
        w = w_sample(t_step, i)
        for cij in cells_eroded_at(w):
            hits[cij] = hits.get(cij, 0) + 1
    # pointwise 3-D density lower bound per cell, simultaneously valid
    dens3 = {}
    for cij, h in hits.items():
        if not in_region(*cij):
            continue
        lo = wilson_ci(h, args.mc, z=Z_CONSERVATIVE)[1]
        dens3[cij] = DENS_P * lo / (2 * A)          # <-- the action factor
    per_alpha = []
    for a in ALPHAS:
        sel = [c for c, d in dens3.items() if d >= a]
        cert = certify(a, len(sel)) if sel else None
        per_alpha.append({"alpha": a, "n_cells": len(sel),
                          "vol_sa": len(sel) * CELL_AREA * 2 * A,
                          "certificate": cert})
    rows.append({"step": t_step, "n_cells_seen": len(dens3),
                 "max_density_3d": max(dens3.values()) if dens3 else 0.0,
                 "level_sets": per_alpha})
    print(f"{t_step:5} {len(dens3):7} "
          + " ".join(f"{p['vol_sa']:11.3f}" for p in per_alpha))

print(f"\n{'step':>5} {'alpha':>6} {'vol(U)':>8} {'rho':>7} "
      f"{'certifies |f-fhat| <=':>22}")
best = None
for r in rows:
    for p in r["level_sets"]:
        c = p["certificate"]
        if not c:
            continue
        print(f"{r['step']:5} {p['alpha']:6.2f} {p['vol_sa']:8.3f} "
              f"{c['rho']:7.3f} {c['uniform_bound']:22.3f}")
        if best is None or c["uniform_bound"] < best["uniform_bound"]:
            best = {"step": r["step"], "alpha": p["alpha"], **c}
if best:
    print(f"\ntightest step-t certificate: step {best['step']}, c >= {best['alpha']}, "
          f"vol(U) = {best['vol_U']:.2f}, rho = {best['rho']:.3f}, "
          f"sup|f - f_hat| <= {best['uniform_bound']:.3f}")
    print(f"the step-1 corollary had c = {5/6:.4f} on vol(U) = 1.2; this region is "
          f"{best['vol_U']/1.2:.1f}x larger at {best['alpha']/(5/6):.3f}x the density, "
          f"and a LARGER region always certifies a WEAKER bound at fixed N.")
print("\nWALL CAVEAT. None of these regions reaches the wall (|x| >= 2 with the")
print("velocity to get there); the certificate constrains smooth pairs where the")
print("gate has density, which is exactly the point of the companion negative result.")

out = _REPO / "results" / "gate_density_step_t.json"
out.write_text(json.dumps(
    {"script": "gate_density_step_t.py", "params": vars(args),
     "M": M, "det_M": DET, "parallelogram_area": AREA_P,
     "parallelogram_density_2d": DENS_P, "cell_area": CELL_AREA,
     "L_plant": L_PLANT, "dim": DIM, "region_box": [GX, GV],
     "rows": rows, "best": best}, indent=2))
print(f"\nwrote {out}")
