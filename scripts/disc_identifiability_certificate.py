"""Per-seed-block certificates: does THIS gate sample identify the disc, and which
alternative template families does it separate?

The paper's finite-sample recoverability numbers (12/20 baseline, 20/20 at the dose's
185 degrees; scripts/region_fit_baseline.py) are an EXISTENCE statement: one particular
estimator lands near the truth. Identifiability relative to a hypothesis class is a
UNIVERSAL statement: every hypothesis consistent with the labels is near the truth. This
script certifies the universal statement per seed block, from the version space itself.

THE LABELLED-EVIDENCE REDUCTION (prop:discident(i)). Under the pinned-integrator
contract, each sampled transition ((s,a) -> s') determines the free landing
z = integrate(s, a)[:2] -- computable by anyone who read the contract -- and the mode
fires iff z is inside the region, so the transition's contact flag IS the membership
label of a known point. A gate sample therefore reduces, exactly, to a finite
membership-labelled point set. (Checked on every transition of every block below.)

THE CLASS AND THE CRITERION. H_circle = { D(c,R) ∪ D2* : c in R^2, R > 0 } -- the near
patch free in the disc class, the far patch's rule given. A hypothesis is consistent iff
it contains every landing labelled inside the near patch (I1) and excludes every landing
labelled outside both patches (O):

    max_{i in I1} ||z_i - c|| <= R < min_{j in O} ||z_j - c||.

The sample IDENTIFIES the disc at tolerance (tau_c, tau_R) iff every consistent (c, R)
has ||c - c*|| <= tau_c and |R - R*| <= tau_R. That is a decidable property of the
sample, and the certificate below decides it soundly:

  * feasibility gap g(c) = min_O d - max_I1 d is 2-Lipschitz, so a grid with spacing h
    over-covers the feasible centre set: any feasible c has a node within l2 distance
    h*sqrt(2)/2 whose g is >= -h*sqrt(2). Brackets read off qualifying nodes, widened by
    the same slack, are certified outer bounds on ALL consistent (c, R).
  * far field: for a centre at distance D from the labelled cloud's centroid (cloud
    radius w), consistency forces the support-gap psi(u) = max_I1 u.z - min_O u.z (in
    the approach direction u) below w^2/(2(D-w)). A direction sweep with Lipschitz slack
    certifies psi >= psi_min > 0 in every direction, which excludes every centre beyond
    D0 = w + w^2/(2 psi_min). (psi_min <= 0 would mean a near-separating direction
    exists and the centre cannot be bounded; reported, not silently truncated.)

THE TEMPLATE LIBRARY (the families the artifacts actually wrote):
  * half-plane: consistent iff conv(I1) and conv(O) are disjoint. Decided exactly via
    the Minkowski-difference hull K = conv(I1 - O): separable iff 0 is outside K, with
    the signed margin = distance from 0 to K's boundary.
  * slab |x-c|<=w (and its y twin): consistent iff no outside landing's coordinate
    falls in I1's coordinate range. Exact interval check.
  * axis-aligned box: consistent iff no outside landing lies in bbox(I1). Exact.
  * axis-aligned square (Chebyshev ball): same scan as the circle in the sup metric
    (g_inf is 2-Lipschitz w.r.t. ||.||_inf, slack h per node), plus an EXACT far-field
    reduction: a square whose centre is at sup-distance >= 2w+1 from the cloud meets the
    cloud's window in exactly a half-plane or a quadrant wedge (its faces are further
    apart than the window), so far squares are consistent iff one of the 8 exact
    half-plane/wedge interval checks is. No curvature slack: the geometry is piecewise
    linear.
  * hull-of-contacts: conv(I1) is ALWAYS consistent (prop:discident(iv): it is inside
    the convex truth region, and outside points are outside the truth, hence outside the
    hull) -- verified on every block as an oracle for the proof, not as evidence.

THE NOISELESS CORE (prop:discident(ii)). Under clamp semantics the post-contact state
lies exactly on the circle; three non-collinear boundary points determine (c, R)
uniquely. Certified per block on the clamp variant's own gate samples: count the
boundary landings, exhibit a non-collinear triple, and check the circle through it IS
the truth to float precision.

Tolerances tau_c = tau_R = 0.1 match region_fit_baseline.py's fit criterion, so the
universal and the existence numbers are comparable. CPU-only, ~5-10 min.

Run: PYTHONPATH=src python scripts/disc_identifiability_certificate.py
Writes: results/disc_identifiability_certificate.json
"""
import json
import math
import pathlib
import sys
import time

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D            # noqa: E402
from cwm.continuous.contract import collect_transitions  # noqa: E402

RES = _REPO / "results"
N_SEEDS = 20
# (label, start_arc_deg, n_rollouts) -- identical to scripts/region_fit_baseline.py
ARMS = [("default", None, 40), ("arc120", 120.0, 15), ("arc240", 240.0, 15)]
TOL_CENTRE = 0.10
TOL_RADIUS = 0.10
LEVELS = (1.0, 0.2, 0.02)   # multilevel grid spacings; slack sqrt(2)*h (l2) or h (sup)
N_DIRS = 4096               # far-field direction sweep
NUM_EPS = 1e-9              # guard for float noise, added to every certified slack


# --------------------------------------------------------------------------- #
# labelled-evidence reduction                                                 #
# --------------------------------------------------------------------------- #

def labelled_points(env, transitions):
    """(I1, I2, O) landing arrays + the reduction's oracle counts. Asserts the
    lemma: the contact flag equals the landing's membership, on every transition."""
    I1, I2, O = [], [], []
    for t in transitions:
        lx, ly = env._integrate(tuple(t["state"]), t["action"])[:2]
        in1, in2 = env._inside(lx, ly, env.p1), env._inside(lx, ly, env.p2)
        assert t["contact"] == (in1 or in2), "labelled-evidence reduction violated"
        assert not (in1 and in2), "patches overlap: attribution ambiguous"
        (I1 if in1 else I2 if in2 else O).append((lx, ly))
    return np.array(I1).reshape(-1, 2), np.array(I2).reshape(-1, 2), np.array(O)


# --------------------------------------------------------------------------- #
# convex-hull machinery (exact, no scipy)                                     #
# --------------------------------------------------------------------------- #

def hull(pts):
    """Monotone chain; returns CCW vertices. Degenerate inputs return what they are."""
    P = sorted({(float(x), float(y)) for x, y in pts})
    if len(P) <= 2:
        return P
    def half(points):
        out = []
        for p in points:
            while len(out) >= 2 and _cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out
    lo, hi = half(P), half(P[::-1])
    return lo[:-1] + hi[:-1]


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _dist_point_segment(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / L2))
    return math.hypot(p[0] - (ax + t * vx), p[1] - (ay + t * vy))


def origin_margin(K):
    """Signed margin of the origin w.r.t. convex polygon K (CCW): positive = outside
    at that distance (separable), negative = inside at that depth (not separable)."""
    if len(K) == 0:
        return float("inf")                     # empty difference set: vacuously separable
    if len(K) == 1:
        return math.hypot(*K[0])
    if len(K) == 2:
        return _dist_point_segment((0.0, 0.0), K[0], K[1])
    inside = all(_cross(K[i], K[(i + 1) % len(K)], (0.0, 0.0)) >= 0
                 for i in range(len(K)))
    d = min(_dist_point_segment((0.0, 0.0), K[i], K[(i + 1) % len(K)])
            for i in range(len(K)))
    return -d if inside else d


def halfplane_certificate(I1, O):
    """Exact: consistent iff conv(I1) and conv(O) are disjoint, via the Minkowski
    difference conv(I1 - O). Margin > 0 exhibits separation; < 0 exhibits overlap."""
    V1, V2 = hull(I1), hull(O)
    diffs = [(a[0] - b[0], a[1] - b[1]) for a in V1 for b in V2]
    m = origin_margin(hull(diffs))
    return {"consistent": bool(m > 0), "margin": float(m)}


def point_in_hull(p, K, tol=1e-12):
    if len(K) < 3:
        return False
    return all(_cross(K[i], K[(i + 1) % len(K)], p) >= -tol for i in range(len(K)))


# --------------------------------------------------------------------------- #
# version-space scans (circle: l2; square: sup metric)                        #
# --------------------------------------------------------------------------- #

def _dists(nodes, pts, sup):
    """max-over-pts and min-over-pts distance from each node, chunked."""
    dmax = np.full(len(nodes), -np.inf)
    dmin = np.full(len(nodes), np.inf)
    for k in range(0, len(nodes), 2048):
        nb = nodes[k:k + 2048, None, :]
        if sup:
            d = np.abs(nb - pts[None, :, :]).max(axis=2)
        else:
            d = np.sqrt(((nb - pts[None, :, :]) ** 2).sum(axis=2))
        dmax[k:k + 2048] = d.max(axis=1)
        dmin[k:k + 2048] = d.min(axis=1)
    return dmax, dmin


def _grid(x0, x1, y0, y1, h):
    xs = np.arange(x0, x1 + h, h)
    ys = np.arange(y0, y1 + h, h)
    return np.stack(np.meshgrid(xs, ys, indexing="ij"), axis=-1).reshape(-1, 2)


def far_field_bound(I1, O, n_dirs=N_DIRS):
    """Certified psi_min over all directions and the exclusion radius D0 (from the
    labelled cloud's centroid). psi_min <= 0 -> the centre cannot be bounded."""
    zbar = I1.mean(axis=0)
    allpts = np.vstack([I1, O]) - zbar
    w = float(np.sqrt((allpts ** 2).sum(axis=1)).max())
    th = np.linspace(0, 2 * math.pi, n_dirs, endpoint=False)
    U = np.stack([np.cos(th), np.sin(th)], axis=1)
    proj_i = U @ (I1 - zbar).T
    proj_o = U @ (O - zbar).T
    psi = proj_i.max(axis=1) - proj_o.min(axis=1)
    slack = w * (2 * math.pi / n_dirs)          # psi is 2w-Lipschitz; |u-u_k| <= pi/n
    psi_min = float(psi.min() - slack)
    D0 = (w + w * w / (2 * psi_min)) if psi_min > 0 else None
    return zbar, w, psi_min, D0


def _refine(keep, h_prev, h):
    """Sub-grids at spacing h over each kept cell (side h_prev), snapped to global
    multiples of h and extended by h so the snapped set still covers every point of
    the union of cells (covering radius <= h/2 per coordinate)."""
    mins = keep - (h_prev / 2 + h)
    maxs = keep + (h_prev / 2 + h)
    parts = [np.stack(np.meshgrid(np.arange(round(lo[0] / h) - 1, round(hi[0] / h) + 2),
                                  np.arange(round(lo[1] / h) - 1, round(hi[1] / h) + 2),
                                  indexing="ij"), axis=-1).reshape(-1, 2)
             for lo, hi in zip(mins, maxs)]
    return np.unique(np.vstack(parts), axis=0) * h


def version_space_certificate(I1, O, truth_c, truth_R, sup=False):
    """Certified outer brackets on every consistent (c, R) in the (disc | square)
    class, or the reason none can be certified. Sound by the Lipschitz-slack cover:
    at every level, any consistent centre has a node within covering radius whose
    slackened gap keeps it, so the kept cells always cover the feasible set."""
    if len(I1) == 0:
        return {"certified": False, "reason": "no inside-labelled landings"}
    zbar, w, psi_min, D0 = far_field_bound(I1, O)
    out = {"cloud_radius": w, "psi_min_certified": psi_min}
    if sup:
        # exact far field for squares: beyond sup-distance 2*w_inf + 1 the wedge/
        # half-plane reduction (square_far_checks) decides, so the scan box only
        # needs that radius
        w_inf = float(np.abs(np.vstack([I1, O]) - zbar).max())
        D0 = 2 * w_inf + 1
        out["far_exclusion_radius_D0"] = D0
    else:
        if D0 is None:
            return {**out, "certified": False,
                    "reason": "a near-separating direction exists; centre unbounded"}
        out["far_exclusion_radius_D0"] = D0
    cover = math.sqrt(2) / 2 if not sup else 0.5   # covering radius per unit spacing
    h0 = LEVELS[0]
    nodes = _grid(zbar[0] - D0 - h0, zbar[0] + D0 + h0,
                  zbar[1] - D0 - h0, zbar[1] + D0 + h0, h0)
    fmax = fomin = None
    for lvl, h in enumerate(LEVELS):
        fmax, _ = _dists(nodes, I1, sup)
        _, fomin = _dists(nodes, O, sup)
        q = (fomin - fmax) >= -(2 * cover * h + NUM_EPS)
        if not q.any():
            # empty feasible set: contradicts truth-consistency for the circle class;
            # for the square class on disc evidence it is the exclusion certificate
            return {**out, "certified": True, "feasible": False}
        if lvl + 1 < len(LEVELS):
            nodes = _refine(nodes[q], h, LEVELS[lvl + 1])
    h = LEVELS[-1]
    Q = nodes[q]
    halo = cover * h + NUM_EPS
    centre_dev = float(np.sqrt(((Q - np.array(truth_c)) ** 2).sum(axis=1)).max()) + halo
    R_lo = float((fmax[q]).min()) - halo
    R_hi = float((fomin[q]).max()) + halo
    return {**out, "certified": True, "feasible": True,
            "n_feasible_nodes": int(len(Q)),
            "centre_dev_max": centre_dev,
            "R_bracket": [R_lo, R_hi],
            "identified_at_tol": bool(centre_dev <= TOL_CENTRE
                                      and R_lo >= truth_R - TOL_RADIUS
                                      and R_hi <= truth_R + TOL_RADIUS)}


def square_far_checks(I1, O):
    """The 8 exact far-field checks: 4 axis half-planes + 4 quadrant wedges. Any one
    consistent -> far squares exist; all inconsistent -> no square with centre at
    sup-distance >= 2w+1 from the cloud (the faces-vs-window lemma in the docstring)."""
    ix, iy = I1[:, 0], I1[:, 1]
    ox, oy = O[:, 0], O[:, 1]
    checks = {
        "hp_x_le": bool(ix.max() < ox.min()), "hp_x_ge": bool(ix.min() > ox.max()),
        "hp_y_le": bool(iy.max() < oy.min()), "hp_y_ge": bool(iy.min() > oy.max()),
        "wedge_pp": bool(~np.any((ox >= ix.min()) & (oy >= iy.min()))),
        "wedge_pm": bool(~np.any((ox >= ix.min()) & (oy <= iy.max()))),
        "wedge_mp": bool(~np.any((ox <= ix.max()) & (oy >= iy.min()))),
        "wedge_mm": bool(~np.any((ox <= ix.max()) & (oy <= iy.max()))),
    }
    return {"any_consistent": any(checks.values()), "checks": checks}


def slab_and_box_checks(I1, O):
    ix, iy = I1[:, 0], I1[:, 1]
    ox, oy = O[:, 0], O[:, 1]
    slab_x = bool(~np.any((ox >= ix.min()) & (ox <= ix.max())))
    slab_y = bool(~np.any((oy >= iy.min()) & (oy <= iy.max())))
    box = bool(~np.any((ox >= ix.min()) & (ox <= ix.max())
                       & (oy >= iy.min()) & (oy <= iy.max())))
    return {"slab_x_consistent": slab_x, "slab_y_consistent": slab_y,
            "box_consistent": box}


# --------------------------------------------------------------------------- #
# clamp semantics: exact three-point identification                           #
# --------------------------------------------------------------------------- #

def circumcircle(p, q, r):
    ax, ay, bx, by, cx, cy = *p, *q, *r
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def clamp_block_certificate(env, transitions):
    """Boundary landings under clamp semantics + the exact 3-point identification."""
    B1 = []
    for t in transitions:
        if not t["contact"]:
            continue
        x, y = t["next_state"][0], t["next_state"][1]
        d1 = math.hypot(x - env.p1[0], y - env.p1[1])
        d2 = math.hypot(x - env.p2[0], y - env.p2[1])
        if abs(d1 - env.R) < abs(d2 - env.R):
            assert abs(d1 - env.R) < 1e-9, "clamp post-state not on the boundary"
            B1.append((x, y))
        else:
            assert abs(d2 - env.R) < 1e-9, "clamp post-state not on the boundary"
    row = {"n_boundary_points_p1": len(B1)}
    H = hull(B1)
    if len(B1) < 3 or len(H) < 3:
        row["exactly_identified"] = False
        row["reason"] = "fewer than three non-collinear boundary points"
        return row
    # a non-collinear triple: the hull's max-area triangle over its vertices
    best, tri = 0.0, None
    for i in range(len(H)):
        for j in range(i + 1, len(H)):
            for k in range(j + 1, len(H)):
                a = abs(_cross(H[i], H[j], H[k])) / 2
                if a > best:
                    best, tri = a, (H[i], H[j], H[k])
    c, r = circumcircle(*tri)
    err_c = math.hypot(c[0] - env.p1[0], c[1] - env.p1[1])
    err_R = abs(r - env.R)
    row.update({"noncollinear_triple_area": best,
                "circumcircle_centre_err": err_c, "circumcircle_R_err": err_R,
                "exactly_identified": bool(best > 1e-9 and err_c < 1e-6
                                           and err_R < 1e-6)})
    return row


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #

def certify_block(env, transitions):
    I1, I2, O = labelled_points(env, transitions)
    row = {"n_inside_p1": int(len(I1)), "n_inside_p2": int(len(I2)),
           "n_outside": int(len(O))}
    if len(I1) and len(I2):
        row["attribution_gap"] = float(min(
            math.hypot(a[0] - b[0], a[1] - b[1]) for a in I1 for b in I2))
    if len(I1) == 0:
        row["circle"] = {"certified": False, "reason": "no inside-labelled landings"}
        return row
    row["circle"] = version_space_certificate(I1, O, env.p1, env.R, sup=False)
    sq = version_space_certificate(I1, O, env.p1, env.R, sup=True)
    far = square_far_checks(I1, O)
    # square-family separation: excluded iff the interior scan certifies an empty
    # feasible set AND every exact far-field configuration is inconsistent
    sq_excluded = bool(sq.get("certified") and not sq.get("feasible", True)
                       and not far["any_consistent"])
    sq_consistent = bool(sq.get("feasible") or far["any_consistent"])
    row["square"] = {"scan": sq, "far": far, "excluded": sq_excluded,
                     "consistent": sq_consistent}
    row["halfplane"] = halfplane_certificate(I1, O)
    row.update(slab_and_box_checks(I1, O))
    # prop:discident(iv) oracle: the hull of the inside landings is always consistent
    K = hull(I1)
    row["hull_of_contacts_consistent"] = bool(
        not any(point_in_hull((x, y), K) for x, y in O)) if len(K) >= 3 else True
    return row


def main() -> None:
    env0 = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    out = {"script": "disc_identifiability_certificate.py",
           "class": "H_circle = {disc(c, R) ∪ D2*}: near patch free in the disc class, "
                    "far patch's rule given; labels are the sample's landing labels",
           "criterion": {"tau_centre": TOL_CENTRE, "tau_radius": TOL_RADIUS},
           "grid": {"levels": list(LEVELS), "n_dirs": N_DIRS},
           "truth": {"centre": list(env0.p1), "R": env0.R},
           "arms": {}, "clamp": {}}
    for label, arc, n_roll in ARMS:
        env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), start_arc_deg=arc)
        rows = []
        for i in range(N_SEEDS):
            t0 = time.time()
            seed = 10_000 * (i + 1)
            tr = collect_transitions(env, n_roll, seed=seed)
            row = {"seed": seed, **certify_block(env, tr)}
            rows.append(row)
            print(f"[{label}] seed {seed}: inside {row['n_inside_p1']}, "
                  f"identified {row['circle'].get('identified_at_tol')}, "
                  f"hp {row['halfplane']['consistent']}, "
                  f"{time.time() - t0:.1f}s", flush=True)
        arm = {
            "start_arc_deg": arc, "n_rollouts": n_roll, "rows": rows,
            "n_identified_at_tol": sum(bool(r["circle"].get("identified_at_tol"))
                                       for r in rows),
            "n_halfplane_excluded": sum(not r["halfplane"]["consistent"]
                                        for r in rows if "halfplane" in r),
            "n_slab_x_excluded": sum(not r["slab_x_consistent"]
                                     for r in rows if "slab_x_consistent" in r),
            "n_box_excluded": sum(not r["box_consistent"]
                                  for r in rows if "box_consistent" in r),
            "n_square_excluded": sum(bool(r.get("square", {}).get("excluded"))
                                     for r in rows),
            "n_hull_consistent": sum(bool(r.get("hull_of_contacts_consistent"))
                                     for r in rows),
            "n_with_inside": sum(r["n_inside_p1"] > 0 for r in rows),
        }
        out["arms"][label] = arm
        print(f"--- {label}: identified {arm['n_identified_at_tol']}/{N_SEEDS}, "
              f"half-plane excluded {arm['n_halfplane_excluded']}, "
              f"box excluded {arm['n_box_excluded']}", flush=True)

    envc = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), mode_effect="clamp")
    crows = []
    for i in range(N_SEEDS):
        seed = 10_000 * (i + 1)
        tr = collect_transitions(envc, 40, seed=seed)
        crows.append({"seed": seed, **clamp_block_certificate(envc, tr)})
    out["clamp"] = {"n_rollouts": 40, "rows": crows,
                    "n_exactly_identified": sum(bool(r["exactly_identified"])
                                                for r in crows),
                    "n_with_contact": sum(r["n_boundary_points_p1"] > 0
                                          for r in crows)}
    print(f"--- clamp: exactly identified "
          f"{out['clamp']['n_exactly_identified']}/{N_SEEDS}")
    (RES / "disc_identifiability_certificate.json").write_text(json.dumps(out, indent=2))
    print(f"wrote {RES / 'disc_identifiability_certificate.json'}")


if __name__ == "__main__":
    main()
