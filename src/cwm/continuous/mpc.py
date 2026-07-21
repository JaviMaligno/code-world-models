"""MPC by random shooting with piecewise-constant candidates.

The planner is a deterministic function of its model's responses and the rng —
the coupling premise of the play-cost upper bound (paper 1, Proposition
"play-cost via query-hit mass") applies verbatim. Candidate action sequences
are piecewise-constant blocks plus the three constant sequences {-1, 0, +1}:
i.i.d. per-step sampling cannot reach distant reward within the horizon (its
displacement is diffusive), and without the constant candidates both models
rank the same dithering sequences identically, so the wall never enters
imagination (calibration 2026-07-06).

`action_dim` (paper 3, docs/paper3/SHELLFIELD-N-DESIGN.md, "the action
interface") is ADDITIVE: default 1 reproduces the scalar path above byte-
for-byte (golden-protected — the committed 1D/2D results must not move).
`action_dim > 1` generalizes every candidate component-wise into tuples of
`action_dim` values each sampled from [-1, 1] (ShellFieldN's thrust-vector
action space, integrator-side norm-capped regardless of a_max). `plan` reads
`action_dim` off the model when not given explicitly, via
`getattr(model, "action_dim", 1)`, so the 1D/2D instruments (which expose no
such attribute) are unaffected without any caller change.
"""


def plan(model, state, rng, horizon: int = 40, n_samples: int = 200,
         block: int = 10, action_dim: int | None = None):
    """Best first action over sampled candidate sequences, evaluated by
    rolling `model` forward `horizon` steps and summing rewards. Returns a
    float when action_dim == 1 (unchanged), a tuple of length action_dim
    otherwise."""
    if action_dim is None:
        action_dim = getattr(model, "action_dim", 1)
    best, best_a0 = -float("inf"), 0.0
    for acts in _candidates(model.a_max, rng, horizon, n_samples, block, action_dim):
        s, total = state, 0.0
        for a in acts:
            s, r, _ = model.step(s, a)
            total += r
        if total > best:
            best, best_a0 = total, acts[0]
    return best_a0


def _candidates(a_max, rng, horizon, n_samples, block, action_dim: int = 1):
    if action_dim == 1:
        yield [-a_max] * horizon
        yield [a_max] * horizon
        yield [0.0] * horizon
        for _ in range(n_samples):
            acts = []
            while len(acts) < horizon:
                acts.extend([rng.uniform(-a_max, a_max)] * block)
            yield acts[:horizon]
        return
    # action_dim > 1: the same three constant candidates plus piecewise-
    # constant blocks, generalized component-wise (each component in
    # [-1, 1], matching ShellFieldN's thrust-vector action space).
    neg = (-1.0,) * action_dim
    pos = (1.0,) * action_dim
    zero = (0.0,) * action_dim
    yield [neg] * horizon
    yield [pos] * horizon
    yield [zero] * horizon
    for _ in range(n_samples):
        acts = []
        while len(acts) < horizon:
            a = tuple(rng.uniform(-1.0, 1.0) for _ in range(action_dim))
            acts.extend([a] * block)
        yield acts[:horizon]
