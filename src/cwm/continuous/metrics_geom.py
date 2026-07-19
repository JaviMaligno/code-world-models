"""Primary state-action disagreement metric for the geometry-repair experiment.

The naive version of this metric -- draw random (state, action) pairs and see
whether truth and model agree on contact -- fails outright: the hard mode is a
thin region (a shape boundary) inside a much larger box, so an i.i.d. sample
almost never lands near it and the metric is dominated by uninformative
agreement on the "obviously nothing happens here" majority class. Every probe
here is instead placed by CONSTRUCTION, using `invert_integrator` (the exact
algebraic inverse of `integrate_2d`, already used the same way by
`instruments.py`'s mode probes) to solve for the state one step upstream of a
chosen target endpoint:

  - `band`   : boundary points displaced +-`band_d` along the true outward
               normal (`shape.normal_or_cone`, resolved to a single inward
               direction at cone vertices), alternating sign so the stratum is
               class-balanced by construction. This is the PRIMARY stratum --
               it is the one that actually stresses a model's boundary
               placement, since both truth and a geometrically-wrong model
               agree almost everywhere far from the boundary.
  - inside/outside: same boundary points, displaced along the normal by a
               depth that GROWS (bounded retries) until `env.contact` actually
               agrees with the intended label -- a safety net against
               curvature/degenerate-vertex cases where a fixed small offset
               might not flip the label.
  - `uniform`: genuine i.i.d. rejection sampling over (state, action), kept
               only if the resulting endpoint stays inside `box` (so the
               stratum still describes transitions relevant to the region of
               interest).
  - `planner`: real (state, action) pairs recorded off an MPC rollout, cycled
               to `n_per` -- what a truth-following controller actually visits,
               as opposed to any constructed probe.

Classification (label truth) for band/inside/outside uses `env.contact`,
which decides contact via `implicit_value(p) <= 0` (i.e., `shape.contains`),
never via `signed_distance`. The band is positioned by displacing a boundary
point by ±`band_d` along the unit normal from `shape.normal_or_cone` (a
Euclidean-length displacement, exact for Circle and approximate near high
curvature / polygon vertices, which are not yet tested here).
"""
import math

import numpy as np

from .envs import invert_integrator

_MAX_GROW_TRIES = 40
_MAX_UNIFORM_TRIES = 4000

# The shared physics contract every 2D instrument in this codebase is built
# on (see envs.py module docstring: "the integrator is part of the
# contract") -- dt/gain/drag/a_max are the same constants across CartWall,
# PatchField2D, ShapeField2D, etc. `forbidden_mask` needs concrete values to
# invert against and takes no env argument (it operates purely on
# model_step + box/grid), so it fixes them to this shared default rather
# than threading env params through every call site.
_DT, _GAIN, _DRAG, _A_MAX = 0.1, 3.0, 0.3, 1.0


def _normal_at(shape, p):
    """A single unit vector at `p`: the true outward normal, or (at a cone
    vertex, where `normal_or_cone` returns a list of face normals) the
    normalized sum of the cone's face normals -- the same vertex convention
    `instruments.py::_shape2d_probes` already uses."""
    n = shape.normal_or_cone(p)
    if isinstance(n, list):
        sx = sum(c[0] for c in n)
        sy = sum(c[1] for c in n)
        m = math.hypot(sx, sy) or 1.0
        return (sx / m, sy / m)
    return n


def _invert(env, target, vx=0.0, vy=0.0, action=0.0):
    """The (state, action) one step upstream of `target`, via the exact
    integrator inverse. vx/vy/action are fixed at 0.0 -- an arbitrary but
    consistent choice (matching `instruments.py`'s mode-probe convention):
    the algebra only needs SOME action to invert against, and which one does
    not affect whether the endpoint lands on `target`."""
    state = invert_integrator(target, vx, vy, action, env.dt, env.gain,
                               env.drag, env.a_max)
    return state, action


def _band_probe(env, shape, bp, normal, band_d, sign):
    # sign=+1 -> inward (toward the shape, label True); sign=-1 -> outward.
    target = (bp[0] - sign * band_d * normal[0], bp[1] - sign * band_d * normal[1])
    return _invert(env, target)


def _grow_until(env, bp, normal, want: bool, d0=0.05, factor=1.7):
    """Push from boundary point `bp` along +-normal by a depth that doubles
    (geometrically) each retry, until the truth label actually matches `want`.
    A fixed offset is not always enough (curvature, near-degenerate vertices),
    so this is the bounded-retry safety net the brief calls for; if `want`
    is never reached it raises rather than silently returning a mislabeled
    probe."""
    sign = -1.0 if want else 1.0  # inward for want=True, outward for want=False
    d = d0
    for _ in range(_MAX_GROW_TRIES):
        target = (bp[0] + sign * d * normal[0], bp[1] + sign * d * normal[1])
        state, action = _invert(env, target)
        if env.contact(state, action) == want:
            return state, action
        d *= factor
    raise RuntimeError(
        f"stratified_probes: could not reach contact={want} near boundary "
        f"point {bp} after {_MAX_GROW_TRIES} tries")


def _uniform_stratum(env, box, n_per, rng, v_max=3.0):
    (xmin, xmax), (ymin, ymax) = box
    out = []
    tries = 0
    while len(out) < n_per and tries < _MAX_UNIFORM_TRIES:
        tries += 1
        state = (rng.uniform(xmin, xmax), rng.uniform(ymin, ymax),
                  rng.uniform(-v_max, v_max), rng.uniform(-v_max, v_max))
        action = rng.uniform(-env.a_max, env.a_max)
        x2, y2, _, _ = env._integrate(state, action)
        if xmin <= x2 <= xmax and ymin <= y2 <= ymax:
            out.append((state, action))
    if len(out) < n_per:
        raise RuntimeError(
            f"stratified_probes: uniform stratum underfilled "
            f"({len(out)}/{n_per}) after {_MAX_UNIFORM_TRIES} tries")
    return out


def _planner_stratum(planner_queries, n_per):
    if not planner_queries:
        raise RuntimeError("stratified_probes: planner_queries is empty")
    return [planner_queries[i % len(planner_queries)] for i in range(n_per)]


def stratified_probes(env, box, n_per, rng, band_d, planner_queries) -> dict:
    """Five strata of exactly `n_per` (state, action) probes each, keyed
    "inside"/"outside"/"band"/"uniform"/"planner". Raises RuntimeError rather
    than returning a short stratum."""
    shape = env.shape
    if shape is None:
        raise ValueError("stratified_probes requires env.shape (a truth mode)")

    boundary = shape.boundary_points(box, max(n_per, 8))
    if len(boundary) < n_per:
        raise RuntimeError(
            f"stratified_probes: only {len(boundary)} boundary points in box, "
            f"need {n_per}")

    band, inside, outside = [], [], []
    for i in range(n_per):
        bp = boundary[i % len(boundary)]
        normal = _normal_at(shape, bp)

        sign = 1.0 if i % 2 == 0 else -1.0  # alternate -> class-balanced band
        band.append(_band_probe(env, shape, bp, normal, band_d, sign))
        inside.append(_grow_until(env, bp, normal, want=True))
        outside.append(_grow_until(env, bp, normal, want=False))

    strata = {
        "inside": inside,
        "outside": outside,
        "band": band,
        "uniform": _uniform_stratum(env, box, n_per, rng),
        "planner": _planner_stratum(planner_queries, n_per),
    }
    for name, probes in strata.items():
        if len(probes) != n_per:
            raise RuntimeError(
                f"stratified_probes: stratum {name!r} has {len(probes)} "
                f"probes, need exactly {n_per}")
    return strata


def _model_contact(state, action, model_step) -> bool:
    """A model 'contacts' iff its step exhibits the freeze signature every
    hard mode in this codebase uses: the next state is EXACTLY the previous
    position with zero velocity (see `ShapeField2D.step`/`PatchField2D.step`).
    Exact equality is safe here -- frozen states are literal float 0.0 / the
    literal previous-position tuple by construction, never an approximation."""
    nxt = model_step(state, action)
    return (nxt[2] == 0.0 and nxt[3] == 0.0
            and nxt[0] == state[0] and nxt[1] == state[1])


def disagreement_scores(truth_env, model_step, probes: dict) -> dict:
    """Per-stratum balanced disagreement (1 - balanced accuracy) + precision/
    recall/fpr, comparing `truth_env.contact` (ground truth) against
    `model_step`'s freeze signature (the model's implied contact call) on
    each stratum's probes. The `band` stratum is the primary metric."""
    out = {}
    for name, plist in probes.items():
        tp = fp = tn = fn = 0
        for (s, a) in plist:
            truth = truth_env.contact(s, a)
            pred = _model_contact(s, a, model_step)
            if truth and pred:
                tp += 1
            elif truth and not pred:
                fn += 1
            elif (not truth) and pred:
                fp += 1
            else:
                tn += 1
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        specificity = tn / (tn + fp) if (tn + fp) else float("nan")
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        fpr = fp / (fp + tn) if (fp + tn) else float("nan")
        rates = [r for r in (recall, specificity) if r == r]  # drop NaN
        balanced_acc = sum(rates) / len(rates) if rates else float("nan")
        out[name] = {
            "disagreement": 1.0 - balanced_acc,
            "precision": precision,
            "recall": recall,
            "fpr": fpr,
            "n": len(plist),
        }
    return out


def forbidden_mask(model_step, box, grid_n, vx, vy, action=0.0) -> np.ndarray:
    """Boolean `grid_n` x `grid_n` mask over `box`, in ENDPOINT space: cell
    `(i, j)` (grid point `p = (xs[i], ys[j])`) is True iff `model_step`'s
    hard mode fires FOR that endpoint. This is the crux of the whole
    endpoint-space design: `p` is never used as a previous position. Instead
    the previous state is solved for via `invert_integrator(p, vx, vy,
    action, ...)` -- the exact algebraic inverse of `integrate_2d`, given
    the (fixed, caller-supplied) velocity `vx, vy` the step used -- so that
    forward-integrating from it lands (to float precision) exactly on `p`.
    `model_step` then runs on that previous state, and the cell is marked
    iff the result froze there (the freeze signature -- see
    `_model_contact` -- every hard mode in this codebase uses: next state
    equals the previous position with zero velocity). Using the grid point
    itself as the previous position instead would measure the TRANSLATED
    preimage of the mode (shifted by the free-flight displacement at this
    particular vx, vy) rather than the mode's true endpoint footprint, and
    would make even a genuinely positional guard look velocity-dependent.

    Vectorized with numpy for the grid coordinates; `model_step` is an
    arbitrary Python callable (not necessarily numpy-friendly), so it is
    invoked in a tight per-cell loop here -- fine for in-process accepted
    code. For gate-failing artifacts the design calls for a single sandbox
    call that returns the whole mask at once (Task 11's path); this
    function's contract (same shape, same endpoint-space semantics) is
    meant to be satisfiable by that path too.
    """
    (xmin, xmax), (ymin, ymax) = box
    xs = np.linspace(xmin, xmax, grid_n)
    ys = np.linspace(ymin, ymax, grid_n)
    mask = np.zeros((grid_n, grid_n), dtype=bool)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            prev = invert_integrator((x, y), vx, vy, action, _DT, _GAIN, _DRAG, _A_MAX)
            nxt = model_step(prev, action)
            mask[i, j] = (nxt[2] == 0.0 and nxt[3] == 0.0
                          and nxt[0] == prev[0] and nxt[1] == prev[1])
    return mask


def _jaccard(a: np.ndarray, b: np.ndarray) -> float:
    """Intersection-over-union of two boolean masks; two empty masks are
    defined to agree completely (jaccard=1.0) rather than 0/0."""
    union = int(np.logical_or(a, b).sum())
    if union == 0:
        return 1.0
    return int(np.logical_and(a, b).sum()) / union


def preimage_invariant(model_step, box, grid_n, velocity_samples,
                        jaccard_tol=0.98) -> bool:
    """True iff `model_step`'s endpoint-space `forbidden_mask` is
    essentially the same set regardless of which velocity the grid is
    inverted against -- the operational test for "positional": a guard that
    only reads the intended endpoint position produces the same forbidden
    footprint no matter what `(vx, vy)` `forbidden_mask` inverts with,
    whereas a guard that reads post-step velocity (or anything else
    velocity-dependent) will flip its forbidden set wholesale as the
    velocity sample changes (see `test_velocity_guard_is_non_positional`,
    where the forbidden set is either everywhere or nowhere depending on
    sign of the sampled vx). Compares every sample's mask against the
    first via Jaccard (IoU of the boolean masks) rather than requiring
    bit-identical masks, since a small number of boundary grid cells can
    legitimately disagree from float rounding in the integrator-inversion
    round trip.
    """
    if len(velocity_samples) < 2:
        return True
    masks = [forbidden_mask(model_step, box, grid_n, vx, vy)
             for (vx, vy) in velocity_samples]
    ref = masks[0]
    return all(_jaccard(ref, m) >= jaccard_tol for m in masks[1:])


def iou_vs_truth(truth_env, model_step, box, grid_n, velocity_samples) -> dict:
    """Endpoint-space IoU between the truth mode's forbidden set and the
    model's -- but only reported when that comparison is well-defined.
    `model_step` must first pass `preimage_invariant`: if its forbidden set
    depends on which velocity sample the grid was inverted against, there
    is no single velocity-independent set left to compare against truth
    (which the assumption of a positional guard would let us reduce to a
    plain 2D shape comparison), so this returns `iou=None,
    class="non_positional"` rather than a number that would silently
    depend on an arbitrary choice of velocity_samples[0]. Only once
    invariance holds does it compute both masks (truth via `truth_env.step`,
    model via `model_step`) at that first velocity sample and report their
    Jaccard IoU as `class="positional"`.
    """
    if not preimage_invariant(model_step, box, grid_n, velocity_samples):
        return {"iou": None, "class": "non_positional", "grid_n": grid_n}
    vx, vy = velocity_samples[0]
    truth_mask = forbidden_mask(lambda s, a: truth_env.step(s, a)[0],
                                 box, grid_n, vx, vy)
    model_mask = forbidden_mask(model_step, box, grid_n, vx, vy)
    return {
        "iou": float(_jaccard(truth_mask, model_mask)),
        "class": "positional",
        "grid_n": grid_n,
    }


def boundary_of_set(mask: np.ndarray, box) -> list:
    """The edge cells of a boolean grid mask, as `(x, y)` grid-point
    coordinates: a True cell counts as an edge iff at least one of its
    4-neighbors (up/down/left/right -- a von-Neumann neighbor check, the
    simplest marching-squares-style stand-in for a full sub-cell contour)
    is either False or off the grid. This intentionally does not attempt
    sub-cell interpolation (a real marching-squares contour) -- it reports
    which grid cells straddle the forbidden set's boundary at the mask's
    own resolution, which is what a diagnostic overlay needs.
    """
    (xmin, xmax), (ymin, ymax) = box
    ni, nj = mask.shape
    xs = np.linspace(xmin, xmax, ni)
    ys = np.linspace(ymin, ymax, nj)
    out = []
    for i in range(ni):
        for j in range(nj):
            if not mask[i, j]:
                continue
            edge = False
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if ii < 0 or ii >= ni or jj < 0 or jj >= nj or not mask[ii, jj]:
                    edge = True
                    break
            if edge:
                out.append((float(xs[i]), float(ys[j])))
    return out
