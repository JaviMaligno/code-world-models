"""MPC by random shooting with piecewise-constant candidates.

The planner is a deterministic function of its model's responses and the rng —
the coupling premise of the play-cost upper bound (paper 1, Proposition
"play-cost via query-hit mass") applies verbatim. Candidate action sequences
are piecewise-constant blocks plus the three constant sequences {-1, 0, +1}:
i.i.d. per-step sampling cannot reach distant reward within the horizon (its
displacement is diffusive), and without the constant candidates both models
rank the same dithering sequences identically, so the wall never enters
imagination (calibration 2026-07-06).
"""


def plan(model, state, rng, horizon: int = 40, n_samples: int = 200,
         block: int = 10) -> float:
    """Best first action over sampled candidate sequences, evaluated by
    rolling `model` forward `horizon` steps and summing rewards."""
    best, best_a0 = -float("inf"), 0.0
    for acts in _candidates(model.a_max, rng, horizon, n_samples, block):
        s, total = state, 0.0
        for a in acts:
            s, r, _ = model.step(s, a)
            total += r
        if total > best:
            best, best_a0 = total, acts[0]
    return best_a0


def _candidates(a_max, rng, horizon, n_samples, block):
    yield [-a_max] * horizon
    yield [a_max] * horizon
    yield [0.0] * horizon
    for _ in range(n_samples):
        acts = []
        while len(acts) < horizon:
            acts.extend([rng.uniform(-a_max, a_max)] * block)
        yield acts[:horizon]
