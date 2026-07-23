"""Distrust-region replanning: the mitigation experiment (paper 2).

Planner-side only — the model is never modified. After executing each real
action the planner compares the model's prediction against the observed next
state; a mismatch beyond tol is a violation (pinned-integrator world: a
correct model matches to float precision, so any real mode mismatch is orders
of magnitude above tol=1e-6).

Each violation records the POSITION of the model's refuted prediction — its
"fence", a tuple of the components named by `pos_dims` (default `(0,)`, the
1D cart/pendulum position; `(0, 1)` for the 2D patch-field instrument's
(x, y)). False predictions always lie ON/BEYOND the mode boundary (the clamp
fires exactly when the model predicts a crossing), so fences are one-sided by
construction in 1D. During imagination, a candidate rollout is TRUNCATED the
first time an imagined STEP's position path comes within eps of any fence:
in 1D this is the segment-vs-eps-band INTERVAL OVERLAP (verbatim boolean, so
it stays leap-proof at any imagined speed); in n-D it is the segment-to-point
distance to the fence, clamped to the segment — once the imagined trajectory
crosses a place where the model was proven wrong, nothing downstream of it is
trustworthy. (Rejected designs, kept as a finding — the argmax planner is an
adversary against any incomplete fence: flee metrics over PRE-STATE balls are
either trapped between overlapping balls (first-step) or biased toward the
phantom side (final-state — violations can only be recorded on the truth
side, so the far side always looks "far from where the model lied");
full-state POINT fences at the false predictions are dodged by probing new
crossing velocities, one contact per dodge.)

When every candidate truncates (the pinned case) totals tie near zero; the
tie-break keeps stepping the model past the truncation point WITHOUT
accumulating reward and ranks by the FINAL imagined state's position distance
to the nearest fence (abs in 1D, euclidean in n-D). One-sided fences make this
structurally away-biased in 1D: the real side always wins. Direction-only use
of the model's kinematics beyond truncation is weaker trust than believing its
reward claims; no reward is ever accumulated there.

With a correct model no violation ever fires and plan_mitigated scores and
ranks candidates exactly as mpc.plan does (same candidate generator, same rng
draws, same strict-argmax) — the zero-cost control holds by construction and
is asserted bitwise in tests/test_mitigation.py, for both the 1D instruments
and the 2D patch-field instrument (pos_dims=(0, 1)).
"""
import math
import random
from dataclasses import dataclass

from . import mpc


def _seg_point_dist(prev_pos: tuple, next_pos: tuple, f: tuple) -> float:
    """Euclidean distance from point f to the segment prev_pos -> next_pos
    (project f onto the segment, clamp t in [0, 1])."""
    d = [b - a for a, b in zip(prev_pos, next_pos)]
    seg_len2 = sum(c * c for c in d)
    if seg_len2 == 0.0:
        return math.dist(prev_pos, f)
    t = sum((f[i] - prev_pos[i]) * d[i] for i in range(len(d))) / seg_len2
    t = max(0.0, min(1.0, t))
    proj = tuple(prev_pos[i] + t * d[i] for i in range(len(d)))
    return math.dist(proj, f)


def _orient(a: tuple, b: tuple, c: tuple) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(p1, p2, q1, q2) -> bool:
    """Proper/improper 2D segment intersection (orientation test; collinear
    overlaps count as intersecting via the on-segment checks)."""
    d1, d2 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    d3, d4 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    if ((d1 > 0) != (d2 > 0) or d1 == 0 or d2 == 0) and \
       ((d3 > 0) != (d4 > 0) or d3 == 0 or d4 == 0):
        # bounding-box check settles the collinear / touching cases
        return (min(p1[0], p2[0]) <= max(q1[0], q2[0]) + 1e-12
                and min(q1[0], q2[0]) <= max(p1[0], p2[0]) + 1e-12
                and min(p1[1], p2[1]) <= max(q1[1], q2[1]) + 1e-12
                and min(q1[1], q2[1]) <= max(p1[1], p2[1]) + 1e-12)
    return False


def _seg_seg_dist(p1: tuple, p2: tuple, q1: tuple, q2: tuple) -> float:
    """Minimum distance between 2D segments p1p2 and q1q2 (0 if they
    intersect, else the min over the four endpoint-to-segment distances)."""
    if _segments_intersect(p1, p2, q1, q2):
        return 0.0
    return min(_seg_point_dist(p1, p2, q1), _seg_point_dist(p1, p2, q2),
               _seg_point_dist(q1, q2, p1), _seg_point_dist(q1, q2, p2))


def _crosses_fence_edges(prev_pos, next_pos, fence_edges, eps) -> bool:
    """Does the imagined step's position path come within eps of any fence
    EDGE (the 1-skeleton of the fence nerve)? 2D only."""
    return any(_seg_seg_dist(prev_pos, next_pos, a, b) <= eps
               for a, b in fence_edges)


def _crosses_fence(prev_pos: tuple, next_pos: tuple, fences, eps: float) -> bool:
    """Does the imagined step's position path come within eps of any fence?
    1D (len(pos_dims) == 1): the CURRENT interval-overlap boolean, verbatim —
    segment overlap with the fence's eps-band, leap-proof at any imagined
    speed. n-D: segment-to-point distance <= eps."""
    if len(prev_pos) == 1:
        lo, hi = min(prev_pos[0], next_pos[0]), max(prev_pos[0], next_pos[0])
        return any(lo <= f[0] + eps and hi >= f[0] - eps for f in fences)
    return any(_seg_point_dist(prev_pos, next_pos, f) <= eps for f in fences)


def _dist_to_nearest(pos: tuple, fences) -> float:
    if not fences:
        return 0.0
    if len(pos) == 1:
        return min(abs(pos[0] - f[0]) for f in fences)
    return min(math.dist(pos, f) for f in fences)


def plan_mitigated(model, state, rng, fences, eps,
                   horizon: int = 40, n_samples: int = 200,
                   block: int = 10, pos_dims: tuple = (0,),
                   fence_edges=()) -> float:
    """mpc.plan with distrust-fence truncation. With fences == [] this is
    bit-identical to mpc.plan (same candidates, same scores, same argmax).
    `fence_edges` (2D nerve mode): segments between linked fence points;
    an imagined step also truncates when it comes within eps of any edge —
    a fence whose dimension matches the boundary's."""
    best_key, best_a0 = None, 0.0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, total, truncated = state, 0.0, False
        for a in acts:
            prev_pos = tuple(s[i] for i in pos_dims)
            s, r, _ = model.step(s, a)
            if truncated:
                continue  # keep stepping for the flee tie-break; no reward
            next_pos = tuple(s[i] for i in pos_dims)
            if fences and (
                    _crosses_fence(prev_pos, next_pos, fences, eps)
                    or (fence_edges and _crosses_fence_edges(
                        prev_pos, next_pos, fence_edges, eps))):
                truncated = True  # nothing downstream is trustworthy
                continue
            total += r
        final_pos = tuple(s[i] for i in pos_dims)  # s = final imagined state
        key = (total, _dist_to_nearest(final_pos, fences))
        if best_key is None or key > best_key:
            best_key, best_a0 = key, acts[0]
    return best_a0


@dataclass
class MitigatedEpisode:
    ret: float
    contact: bool
    final_state: tuple
    violations: int              # violation points recorded over the episode
    first_contact_step: int | None


def run_mitigated_episode(truth, model, seed: int = 0, horizon: int = 40,
                          n_samples: int = 200, block: int = 10,
                          tol: float = 1e-6, eps: float = 0.25,
                          pos_dims: tuple = (0,),
                          fence_mode: str = "points",
                          link_r: float = 6.0, ext: float = 3.0,
                          min_sep: float = 0.2,
                          fences: list | None = None,
                          fence_edges: list | None = None) -> MitigatedEpisode:
    """Play one episode in `truth`, planning on `model` with distrust-region
    replanning. Mirrors harness.run_episode's rng discipline exactly so the
    truth-model episode is bit-identical to the plain MPC one."""
    if fence_mode not in ("points", "nerve"):
        raise ValueError(f"unknown fence_mode {fence_mode!r}")
    if fence_mode == "nerve" and len(pos_dims) != 2:
        raise ValueError("nerve fences are 2D (pos_dims of length 2)")
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact, first_contact = 0.0, False, None
    # pass mutable lists to PERSIST fences across episodes (deployment
    # monitoring); default None keeps the original per-episode semantics
    if fences is None:
        fences = []
    if fence_edges is None:
        fence_edges = []
    n_fences_at_start = len(fences)
    for t in range(truth.h_episode):
        a = plan_mitigated(model, s, rng, fences, eps,
                           horizon=horizon, n_samples=n_samples, block=block,
                           pos_dims=pos_dims, fence_edges=fence_edges)
        s2, r, c = truth.step(s, a)
        pred, _, _ = model.step(s, a)
        if max(abs(pred[i] - s2[i]) for i in range(len(s2))) > tol:
            new_f = tuple(pred[i] for i in pos_dims)
            if fence_mode == "nerve":
                # nerve 1-skeleton WITH TANGENTIAL EXTENSION: two linked
                # violations estimate the boundary's local direction, and
                # the edge is extended `ext` units beyond both endpoints
                # along it. Without extension each violation seals only an
                # eps-corridor of imagined crossings and the planner slides
                # along the boundary (measured: pc unchanged); with it,
                # coverage grows by ~ext per violation — incremental
                # boundary estimation at the boundary's own dimension.
                for f in fences:
                    d = math.dist(f, new_f)
                    if d > link_r:
                        continue
                    if d >= min_sep:
                        ux = (new_f[0] - f[0]) / d
                        uy = (new_f[1] - f[1]) / d
                        fence_edges.append((
                            (f[0] - ux * ext, f[1] - uy * ext),
                            (new_f[0] + ux * ext, new_f[1] + uy * ext)))
                    else:
                        fence_edges.append((f, new_f))
            fences.append(new_f)  # position of the FALSE prediction
        if c and first_contact is None:
            first_contact = t
        contact = contact or c
        total += r
        s = s2
    return MitigatedEpisode(ret=total, contact=contact, final_state=s,
                            violations=len(fences) - n_fences_at_start,
                            first_contact_step=first_contact)
