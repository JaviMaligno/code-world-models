"""Operational per-family oracle + classifying tangent baseline.

Phase-A scope, deliberately narrow. Point labels (inside/outside at a finite
set of endpoints) do NOT by themselves determine a region: infinitely many
regions agree with any finite labeled set. So this module exposes only
evaluators that are honest about what they need to be meaningful:

- `fit_family` finds the least-violation member of a *given* family (its
  parametric form is assumed known -- e.g. "this is a circle") consistent
  with the labels. That is well-posed because the family restricts the
  hypothesis space to something a finite label set can pin down.
- `operational_reconstructs_vs_truth` is a *calibration-only* check: it
  compares the fit against the actual generating shape, which only the
  calibration harness (not a runtime learner) ever has access to.
- `operational_heldout_accuracy` is the runtime-usable estimator: no truth
  shape needed, just an independent labeled sample to score generalization.
- `tangent_baseline` is a simple classifying half-plane fit -- a baseline,
  not a claim that a half-plane is the right family.

What this module does NOT do: claim sufficiency. Whether the evidence
collected in an episode is *sufficient* to identify the true shape (up to
some tolerance) requires reasoning about the whole version space consistent
with the labels, which is not attempted here (`SUFFICIENCY_UNCERTIFIED`).
That's Phase B (a conservative version-space diameter bound).
"""
from __future__ import annotations
import math
import itertools

import numpy as np

from cwm.continuous.shapes import (
    HalfPlane, HalfPlaneGeneral, Strip, Circle, Parabola, Wedge, RegularPolygon,
)

SUFFICIENCY_UNCERTIFIED = True  # Phase A does not certify identification; see module docstring.


# --------------------------------------------------------------------------
# Generic least-violation optimizer: coarse box-bounded grid (for a good
# basin) + Hooke-Jeeves pattern-search polish (for precision). Deliberately
# not scipy (not a project dependency); pattern search needs no gradient,
# which matters because the violation losses below are continuous but only
# piecewise-smooth (hinge-style).
# --------------------------------------------------------------------------

def _hooke_jeeves(loss_fn, x0, bounds, iters=100, shrink=0.5, min_frac=1e-4, init_frac=0.08):
    x = list(x0)
    step = [(hi-lo)*init_frac for lo, hi in bounds]
    best = loss_fn(x)
    for _ in range(iters):
        improved = False
        for i in range(len(x)):
            for direction in (1.0, -1.0):
                lo, hi = bounds[i]
                trial = list(x)
                trial[i] = min(hi, max(lo, x[i] + direction*step[i]))
                l = loss_fn(trial)
                if l < best - 1e-15:
                    best, x, improved = l, trial, True
        if not improved:
            step = [s*shrink for s in step]
            if all(s < (hi-lo)*min_frac for s, (lo, hi) in zip(step, bounds)):
                break
    return x, best


def _fit_generic(loss_fn, bounds, steps, top_k=3, iters=100):
    """Coarse grid over `bounds` (`steps[i]` points per dim) scored by
    `loss_fn`, keep the `top_k` best as polish seeds (guards against grid
    aliasing picking a seed in the wrong basin), Hooke-Jeeves-polish each,
    return the best (params, loss) found."""
    grids = [np.linspace(lo, hi, max(2, s)) for (lo, hi), s in zip(bounds, steps)]
    combos = itertools.product(*grids)
    scored = sorted(((loss_fn(c), c) for c in combos), key=lambda t: t[0])[:top_k]
    best_params, best_loss = None, math.inf
    for _, seed in scored:
        params, l = _hooke_jeeves(loss_fn, list(seed), bounds, iters=iters)
        if l < best_loss:
            best_params, best_loss = params, l
    return best_params, best_loss


def _hinge_loss(s, inside_bool, margin=0.02):
    """`s` is a signed-distance-*like* quantity, negative meaning inside
    (matching the Shape.implicit_value convention). Squared ramp-hinge: zero
    once a point clears the margin on its labeled side, growing with the
    size of the violation otherwise -- continuous, so pattern search has a
    useful direction to descend even where the 0/1 classification loss is
    flat."""
    s = np.asarray(s, dtype=float)
    inside_bool = np.asarray(inside_bool, dtype=bool)
    viol = np.where(inside_bool, np.maximum(0.0, s + margin), np.maximum(0.0, margin - s))
    return float(np.mean(viol*viol))


def _wedge_faces(ax, ay, half_angle, orient, X, Y):
    faces = []
    for sgn in (1.0, -1.0):
        ang = orient + sgn*half_angle
        dx, dy = math.cos(ang), math.sin(ang)
        nx, ny = -dy, dx
        axis = (math.cos(orient), math.sin(orient))
        if nx*axis[0] + ny*axis[1] > 0:
            nx, ny = -nx, -ny
        faces.append(nx*(X-ax) + ny*(Y-ay))
    return faces


def _polygon_faces(cx, cy, radius, k, orient, X, Y):
    apo = radius*math.cos(math.pi/k)
    vals = []
    for i in range(k):
        ang = orient + 2*math.pi*i/k
        nx, ny = math.cos(ang), math.sin(ang)
        vals.append(nx*(X-cx) + ny*(Y-cy) - apo)
    return vals


# --------------------------------------------------------------------------
# fit_family
# --------------------------------------------------------------------------

def fit_family(family, labeled_endpoints, box):
    """Least-violation fit of `family` to `labeled_endpoints` (list of
    `(point, inside_bool)`), searched over a parameter grid bounded by `box`
    (not the observed data range -- a shape whose true extent is much
    smaller than the observed points, e.g. R=1 inside a wide box, must still
    be reachable). Returns a `Shape` instance, or `None` if there is no
    labeled data at all."""
    if not labeled_endpoints:
        return None
    P = np.array([p for p, _ in labeled_endpoints], dtype=float)
    L = np.array([lab for _, lab in labeled_endpoints], dtype=bool)
    X, Y = P[:, 0], P[:, 1]
    (xmin, xmax), (ymin, ymax) = box
    Rmax = 0.5*math.hypot(xmax-xmin, ymax-ymin)

    if family == "halfplane":
        def s_fn(params):
            (c,) = params
            return c - X
        loss_fn = lambda params: _hinge_loss(s_fn(params), L)
        (c,), _ = _fit_generic(loss_fn, [(xmin, xmax)], steps=[60])
        return HalfPlane(float(c))

    if family == "strip":
        def s_fn(params):
            c, w = params
            return np.maximum(c-X, X-(c+w))
        loss_fn = lambda params: _hinge_loss(s_fn(params), L)
        w_min = max(1e-3*(xmax-xmin), 1e-3)
        bounds = [(xmin, xmax), (w_min, max(w_min*2, xmax-xmin))]
        (c, w), _ = _fit_generic(loss_fn, bounds, steps=[24, 24])
        return Strip(float(c), float(max(w, 1e-6)))

    if family == "circle":
        def s_fn(params):
            cx, cy, R = params
            return np.hypot(X-cx, Y-cy) - R
        loss_fn = lambda params: _hinge_loss(s_fn(params), L)
        bounds = [(xmin, xmax), (ymin, ymax), (0.02, Rmax)]
        (cx, cy, R), _ = _fit_generic(loss_fn, bounds, steps=[16, 16, 16])
        return Circle(float(cx), float(cy), float(max(R, 1e-3)))

    if family == "parabola":
        def s_fn(params):
            c, R = params
            bx = c + (Y*Y)/(2.0*R)
            grad = np.sqrt(1.0 + (Y/R)**2)  # local linearization -> distance-like units
            return (bx-X)/grad
        loss_fn = lambda params: _hinge_loss(s_fn(params), L)
        bounds = [(xmin, xmax), (0.05, Rmax)]
        (c, R), _ = _fit_generic(loss_fn, bounds, steps=[30, 30])
        return Parabola(float(c), float(max(R, 1e-3)))

    if family == "wedge":
        def s_fn(params):
            ax, ay, ha, orient = params
            f0, f1 = _wedge_faces(ax, ay, ha, orient, X, Y)
            return np.maximum(f0, f1)
        loss_fn = lambda params: _hinge_loss(s_fn(params), L)
        bounds = [(xmin, xmax), (ymin, ymax), (0.05, math.pi/2 - 0.05), (-math.pi, math.pi)]
        (ax, ay, ha, orient), _ = _fit_generic(loss_fn, bounds, steps=[9, 9, 7, 10])
        return Wedge((float(ax), float(ay)), float(ha), float(orient))

    if family == "polygon":
        best_overall, best_loss = None, math.inf
        for k in range(3, 9):
            def s_fn(params, k=k):
                cx, cy, radius, orient = params
                vals = _polygon_faces(cx, cy, radius, k, orient, X, Y)
                return np.max(np.stack(vals, axis=0), axis=0)
            loss_fn = lambda params, k=k: _hinge_loss(s_fn(params, k=k), L)
            bounds = [(xmin, xmax), (ymin, ymax), (0.05, Rmax), (0.0, 2*math.pi/k)]
            params, l = _fit_generic(loss_fn, bounds, steps=[7, 7, 7, 7])
            if l < best_loss:
                best_loss, best_overall = l, (k, params)
        k, (cx, cy, radius, orient) = best_overall
        return RegularPolygon(float(cx), float(cy), float(max(radius, 1e-3)), k, float(orient))

    raise ValueError(f"unknown family: {family!r}")


# --------------------------------------------------------------------------
# Vectorized contains-mask for the six families (mirrors shapes.py formulas
# exactly, but with np.maximum/np.stack in place of builtin max() so it
# broadcasts over a grid -- Strip/Wedge/RegularPolygon's implicit_value uses
# plain Python max(), which raises on ndarray inputs).
# --------------------------------------------------------------------------

def _vectorized_contains(shape, X, Y):
    if isinstance(shape, HalfPlaneGeneral):
        return (shape.nx*X + shape.ny*Y - shape.off) <= 0.0
    if isinstance(shape, HalfPlane):
        return (shape.c - X) <= 0.0
    if isinstance(shape, Strip):
        return np.maximum(shape.c-X, X-(shape.c+shape.w)) <= 0.0
    if isinstance(shape, Circle):
        return ((X-shape.cx)**2 + (Y-shape.cy)**2 - shape.R**2) <= 0.0
    if isinstance(shape, Parabola):
        return ((shape.c + Y*Y/(2.0*shape.R)) - X) <= 0.0
    if isinstance(shape, Wedge):
        ax, ay = shape.apex
        f0, f1 = _wedge_faces(ax, ay, shape.half_angle, shape.orient, X, Y)
        return np.maximum(f0, f1) <= 0.0
    if isinstance(shape, RegularPolygon):
        vals = _polygon_faces(shape.cx, shape.cy, shape.radius, shape.k, shape.orient, X, Y)
        return np.max(np.stack(vals, axis=0), axis=0) <= 0.0
    raise TypeError(f"no vectorized contains for {type(shape)!r}")


def _iou_on_grid(shape_a, shape_b, box, grid_n=200):
    (xmin, xmax), (ymin, ymax) = box
    xs = np.linspace(xmin, xmax, grid_n)
    ys = np.linspace(ymin, ymax, grid_n)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    A = _vectorized_contains(shape_a, XX, YY)
    B = _vectorized_contains(shape_b, XX, YY)
    union = int(np.logical_or(A, B).sum())
    if union == 0:
        return 1.0
    return float(np.logical_and(A, B).sum()) / union


def operational_reconstructs_vs_truth(family, labeled, truth_shape, box, iou_thresh):
    """Calibration-only evaluator: fit `family` to `labeled`, then compare
    the FIT REGION against the KNOWN `truth_shape` region via IoU on a box
    grid. Valid only because the caller (calibration) has `truth_shape`; a
    runtime learner never does, so this is not a stand-in for
    `operational_heldout_accuracy` -- it is a separate, stronger check that
    can only be run when ground truth is available."""
    fit = fit_family(family, labeled, box)
    if fit is None:
        return False
    return _iou_on_grid(fit, truth_shape, box, grid_n=200) >= iou_thresh


def _balanced_accuracy(preds, truths):
    tp = fp = tn = fn = 0
    for pr, tr in zip(preds, truths):
        if tr and pr: tp += 1
        elif tr and not pr: fn += 1
        elif (not tr) and pr: fp += 1
        else: tn += 1
    sens = tp/(tp+fn) if (tp+fn) > 0 else 1.0
    spec = tn/(tn+fp) if (tn+fp) > 0 else 1.0
    return 0.5*(sens+spec)


def operational_heldout_accuracy(family, train_labeled, test_labeled):
    """Runtime-usable evaluator: fit `family` on `train_labeled` only (no
    truth shape), then report balanced accuracy on an independent
    `test_labeled` set. Balanced (not raw) accuracy because inside/outside
    labels are typically very imbalanced (a small shape in a large box), and
    raw accuracy is trivially high for a degenerate "always outside" fit."""
    if not train_labeled or not test_labeled:
        return 0.0
    xs = [p[0] for p, _ in train_labeled]
    ys = [p[1] for p, _ in train_labeled]
    pad_x = 0.15*((max(xs)-min(xs)) or 1.0)
    pad_y = 0.15*((max(ys)-min(ys)) or 1.0)
    box = ((min(xs)-pad_x, max(xs)+pad_x), (min(ys)-pad_y, max(ys)+pad_y))
    fit = fit_family(family, train_labeled, box)
    if fit is None:
        return 0.0
    preds = [fit.contains(p) for p, _ in test_labeled]
    truths = [lab for _, lab in test_labeled]
    return _balanced_accuracy(preds, truths)


# --------------------------------------------------------------------------
# tangent_baseline
# --------------------------------------------------------------------------

def _best_threshold_for_projection(proj, L, n_pos, n_neg):
    """Given 1-D projections `proj` (onto some candidate normal direction)
    and labels `L`, find the threshold AND interior side (`<=` or `>=`) that
    maximizes balanced accuracy exactly, via a sort + cumulative-count sweep
    (the classic optimal-threshold-for-a-linear-score procedure) rather than
    a smooth surrogate -- for a fixed orientation this is solved exactly in
    O(n log n), no local-search approximation needed."""
    order = np.argsort(proj)
    proj_sorted = proj[order]
    L_sorted = L[order]
    n = len(proj)
    cum_pos = np.cumsum(L_sorted).astype(float)          # positives with proj <= proj_sorted[i]
    cum_all = np.arange(1, n+1, dtype=float)
    cum_neg = cum_all - cum_pos

    # side A: interior = {proj <= threshold}
    tp_A, fp_A = cum_pos, cum_neg
    fn_A, tn_A = n_pos-tp_A, n_neg-fp_A
    sens_A = np.where((tp_A+fn_A) > 0, tp_A/np.maximum(tp_A+fn_A, 1), 1.0)
    spec_A = np.where((tn_A+fp_A) > 0, tn_A/np.maximum(tn_A+fp_A, 1), 1.0)
    bal_A = 0.5*(sens_A+spec_A)
    i_A = int(np.argmax(bal_A))

    # side B: interior = {proj >= threshold} (complement of side A at the same cut)
    tp_B, fp_B, fn_B, tn_B = n_pos-tp_A, n_neg-fp_A, tp_A, fp_A
    sens_B = np.where((tp_B+fn_B) > 0, tp_B/np.maximum(tp_B+fn_B, 1), 1.0)
    spec_B = np.where((tn_B+fp_B) > 0, tn_B/np.maximum(tn_B+fp_B, 1), 1.0)
    bal_B = 0.5*(sens_B+spec_B)
    i_B = int(np.argmax(bal_B))

    def _off_at(i):
        return proj_sorted[i] if i == n-1 else 0.5*(proj_sorted[i]+proj_sorted[i+1])

    if bal_A[i_A] >= bal_B[i_B]:
        return _off_at(i_A), float(bal_A[i_A]), +1.0
    return _off_at(i_B), float(bal_B[i_B]), -1.0


def tangent_baseline(labeled):
    """Best CLASSIFYING half-plane fit to inside/outside-labeled endpoints.
    Contacts (points alone) can't give the interior side or the offset --
    only the labels can. PCA on the point cloud (positions only, no labels)
    gives candidate orientations to *seed* the search; a fine grid of
    orientations (PCA seeds plus a uniform sweep over [0, pi), since a
    direction and its opposite give the same line) is then searched, and
    for EACH orientation the offset and interior side are chosen exactly --
    by an optimal 1-D threshold sweep -- to maximize balanced accuracy
    (unweighted misclassification degenerates, for a small interior region
    in a big box, to the trivial "classify everything as outside" fit, so
    balanced accuracy is the criterion, not raw accuracy)."""
    P = np.array([p for p, _ in labeled], dtype=float)
    L = np.array([lab for _, lab in labeled], dtype=bool)
    X, Y = P[:, 0], P[:, 1]
    n_pos, n_neg = int(L.sum()), int((~L).sum())

    mean = P.mean(axis=0)
    cov = np.cov((P-mean).T) if len(P) > 1 else np.eye(2)
    _, eigvecs = np.linalg.eigh(cov)
    pca_thetas = [math.atan2(eigvecs[1, i], eigvecs[0, i]) % math.pi for i in range(2)]
    thetas = list(np.linspace(0.0, math.pi, 180, endpoint=False)) + pca_thetas

    best = None  # (bal_acc, nx, ny, off)
    for theta in thetas:
        nx, ny = math.cos(theta), math.sin(theta)
        proj = nx*X + ny*Y
        off, bal_acc, side = _best_threshold_for_projection(proj, L, n_pos, n_neg)
        cnx, cny, coff = (nx, ny, off) if side > 0 else (-nx, -ny, -off)
        if best is None or bal_acc > best[0]:
            best = (bal_acc, cnx, cny, coff)

    _, nx, ny, off = best
    return HalfPlaneGeneral(float(nx), float(ny), float(off))
