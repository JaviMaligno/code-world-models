"""Tolerance gate over random rollouts, and reveal-rarity for model pairs.

The continuous analogue of the games' transition gate: draw N i.i.d.
uniform-random rollouts ON THE TRUTH environment and check the candidate
model's step against the truth transition at every visited (state, action),
in sup-norm over (x, v, reward), against a tolerance eps.

Two tolerances matter (design doc): eps ~ 1e-9 is the pinned-integrator
headline gate (a correct synthesis matches to float precision, so the gate is
effectively exact-match and the only way a wrong model passes is the
gate-miss event); eps ~ 1e-2 is the deployment-realistic variant, which adds
the sub-tolerance pervasive-error axis that the axis-separation experiment
(scripts/continuous_axes.py) controls for.

reveal_rarity is the measure-theoretic rarity of the danger law for an
arbitrary model pair: P(a random rollout contains at least one transition
where the two models differ detectably at eps). For the wall-omitting blind
model it coincides with the wall-contact rate; for biased or bump-omitting
models it is the general definition.
"""
import random
from dataclasses import dataclass

from ..law import wilson_ci


def transition_error(truth, model, state, action) -> float:
    st, rt, _ = truth.step(state, action)
    sm, rm, _ = model.step(state, action)
    return max(max(abs(a - b) for a, b in zip(st, sm)), abs(rt - rm))


@dataclass
class GateResult:
    passed: bool
    n_rollouts: int
    n_transitions: int
    n_bad: int            # transitions with error > eps
    max_err: float
    first_bad: dict | None  # {"state","action","err"} of the first violation


def run_gate(truth, model, n_rollouts: int, eps: float, seed: int = 0) -> GateResult:
    n_trans, n_bad, max_err, first_bad = 0, 0, 0.0, None
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = truth.initial_state(rng)
        for _ in range(truth.h_episode):
            a = rng.uniform(-truth.a_max, truth.a_max)
            err = transition_error(truth, model, s, a)
            n_trans += 1
            if err > max_err:
                max_err = err
            if err > eps:
                n_bad += 1
                if first_bad is None:
                    first_bad = {"state": s, "action": a, "err": err}
            s = truth.step(s, a)[0]
    return GateResult(passed=(n_bad == 0), n_rollouts=n_rollouts,
                      n_transitions=n_trans, n_bad=n_bad, max_err=max_err,
                      first_bad=first_bad)


def reveal_rarity(truth, model, eps: float, n_rollouts: int,
                  seed: int = 0) -> tuple[float, float, float]:
    """(point, lo, hi): fraction of random rollouts that reveal the
    truth/model difference at tolerance eps — the danger-law rarity for this
    model pair."""
    hits = 0
    for i in range(n_rollouts):
        if not run_gate(truth, model, 1, eps, seed=seed + i).passed:
            hits += 1
    return wilson_ci(hits, n_rollouts)


def gate_pass_rate(truth, model, eps: float, n_gate: int, n_gates: int,
                   seed: int = 0) -> tuple[float, float, float]:
    """Empirical fraction of independent size-n_gate gates the model passes;
    must match (1 - reveal_rarity)^n_gate (the exactness proposition)."""
    passes = 0
    for g in range(n_gates):
        if run_gate(truth, model, n_gate, eps, seed=seed + g * n_gate).passed:
            passes += 1
    return wilson_ci(passes, n_gates)
