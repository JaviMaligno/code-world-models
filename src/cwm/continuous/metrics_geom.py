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

Classification for band/inside/outside uses `shape.signed_distance` implicitly
through `env.contact` (which is exact contact-mode arithmetic on the SAME
integrator we used to invert) -- `signed_distance` is a true euclidean
length and is what makes "push +-band_d" mean the same physical thing across
shape families with different `implicit_value` scalings (a circle's
implicit_value is a squared radius; a polygon's is a plain half-plane margin).
"""
import math

from .envs import invert_integrator

_MAX_GROW_TRIES = 40
_MAX_UNIFORM_TRIES = 4000


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
    out["primary"] = "band"
    return out
