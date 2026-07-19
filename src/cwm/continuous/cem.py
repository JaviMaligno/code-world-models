"""Cross-entropy-method planner: the second planner family (paper 2).

Per-step Gaussian action distributions refined over a few elite iterations.
Purpose in the paper: measure the OTHER branch of the play-cost bound
(Proposition 3). Random shooting with constant candidates reaches the distant
phantom plateau in imagination (high query-hit mass on the disagreement
region) and is exploited by the certified-blind model; CEM's local search
concentrates on the nearer TRUE plateau from the first elite iteration and
never discovers the phantom (near-zero query-hit mass) -- so, exactly as the
bound prescribes, it is not exploited. The optional `boundary` argument
measures this: the fraction of sampled imagined trajectories that cross the
mode boundary during planning. `boundary` accepts either a float (1D
instruments: crossing means x >= boundary) or a callable state -> bool (e.g.
the 2D instrument's per-patch predicate).

Deterministic given the rng. Hyperparameters are prototype-calibrated and
fixed across knobs and instruments (no per-knob tuning).
"""
import random
from dataclasses import dataclass
from typing import Callable, Union


def plan_cem(model, state, rng, horizon: int = 40, n_iters: int = 5,
             n_samples: int = 64, elite_frac: float = 0.125,
             min_std: float = 0.05,
             boundary: Union[float, Callable[[tuple], bool], None] = None):
    """Best first action by CEM. With boundary set, also returns the fraction
    of sampled imagined trajectories whose position crossed it."""
    a_max = model.a_max
    n_elite = max(2, int(n_samples * elite_frac))
    mean = [0.0] * horizon
    std = [a_max] * horizon
    crossed = total_samples = 0
    for _ in range(n_iters):
        scored = []
        for _ in range(n_samples):
            acts = [max(-a_max, min(a_max, rng.gauss(mean[t], std[t])))
                    for t in range(horizon)]
            s, total, hit = state, 0.0, False
            for a in acts:
                s, r, _ = model.step(s, a)
                total += r
                if boundary is not None and not hit:
                    hit = boundary(s) if callable(boundary) else s[0] >= boundary
            scored.append((total, acts))
            total_samples += 1
            crossed += hit
        scored.sort(key=lambda x: -x[0])
        elites = [acts for _, acts in scored[:n_elite]]
        mean = [sum(e[t] for e in elites) / n_elite for t in range(horizon)]
        std = [max(min_std, (sum((e[t] - mean[t]) ** 2 for e in elites)
                             / n_elite) ** 0.5) for t in range(horizon)]
    if boundary is None:
        return mean[0]
    return mean[0], crossed / total_samples


@dataclass
class CemEpisode:
    ret: float
    contact: bool
    final_state: tuple
    crossing_frac: float | None   # mean per-plan imagined boundary-crossing


def run_episode(truth, model, seed: int = 0,
                boundary: Union[float, Callable[[tuple], bool], None] = None,
                **plan_kw) -> CemEpisode:
    """Play one episode in `truth`, planning on `model` with CEM. Mirrors
    harness.run_episode's rng discipline (initial_state first, then per-step
    planning draws)."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact, fracs = 0.0, False, []
    for _ in range(truth.h_episode):
        out = plan_cem(model, s, rng, boundary=boundary, **plan_kw)
        if boundary is None:
            a = out
        else:
            a, frac = out
            fracs.append(frac)
        s, r, c = truth.step(s, a)
        total += r
        contact = contact or c
    return CemEpisode(ret=total, contact=contact, final_state=s,
                      crossing_frac=(sum(fracs) / len(fracs)) if fracs else None)
