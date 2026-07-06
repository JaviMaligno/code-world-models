"""Episode harness + the danger-law measurements for the continuous instrument.

Mirrors cwm.law for the games: rarity is swept cheaply with random rollouts,
play_cost is measured with the MPC arena (truth-model planner vs blind-model
planner, both executed in the true environment). Single-agent, so play_cost is
normalized regret rather than a winrate:

    play_cost = (J_truth - J_blind) / (J_truth - J_random)

with all returns measured in the true environment on paired seeds. The blind
planner can score below random (it is actively exploited by its phantom
mode), so the normalized value can exceed 1; we report it unclamped.
"""
import random
from dataclasses import dataclass

from ..law import wilson_ci, danger  # noqa: F401  (danger re-exported for scripts)
from . import mpc


@dataclass
class Episode:
    ret: float          # sum of per-step true rewards
    contact: bool       # wall clamp fired at least once (in truth)
    final_state: tuple


def run_episode(truth, model=None, policy: str = "mpc", seed: int = 0,
                horizon: int = 40, n_samples: int = 200, block: int = 10) -> Episode:
    """Play one episode in `truth`. policy='mpc' plans on `model` (which may
    be truth itself or a blind model); policy='random' ignores `model`."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact = 0.0, False
    for _ in range(truth.h_episode):
        if policy == "mpc":
            a = mpc.plan(model, s, rng, horizon=horizon,
                         n_samples=n_samples, block=block)
        else:
            a = rng.uniform(-truth.a_max, truth.a_max)
        s, r, c = truth.step(s, a)
        total += r
        contact = contact or c
    return Episode(ret=total, contact=contact, final_state=s)


def rarity(truth, n_rollouts: int, seed: int = 0) -> tuple[float, float, float]:
    """(point, lo, hi) fraction of i.i.d. uniform-random rollouts in which the
    wall mode fires — the gate's own sampling distribution, as in cwm.law."""
    hits = 0
    for i in range(n_rollouts):
        if run_episode(truth, policy="random", seed=seed + i).contact:
            hits += 1
    return wilson_ci(hits, n_rollouts)


def mean_return(episodes: list) -> float:
    return sum(e.ret for e in episodes) / len(episodes)


def play_cost(truth, blind, n_episodes: int, seed: int = 0,
              horizon: int = 40, n_samples: int = 200, block: int = 10) -> dict:
    """Normalized regret of the blind-model planner, paired seeds throughout."""
    t, b, r = [], [], []
    for i in range(n_episodes):
        sd = seed + 1000 * i
        t.append(run_episode(truth, truth, "mpc", sd, horizon, n_samples, block))
        b.append(run_episode(truth, blind, "mpc", sd, horizon, n_samples, block))
        r.append(run_episode(truth, policy="random", seed=sd))
    j_t, j_b, j_r = mean_return(t), mean_return(b), mean_return(r)
    denom = j_t - j_r
    return {
        "j_truth": j_t, "j_blind": j_b, "j_random": j_r,
        "play_cost": (j_t - j_b) / denom if denom > 0 else 0.0,
        "blind_contact_rate": sum(e.contact for e in b) / n_episodes,
        "truth_contact_rate": sum(e.contact for e in t) / n_episodes,
        "n_episodes": n_episodes,
    }
