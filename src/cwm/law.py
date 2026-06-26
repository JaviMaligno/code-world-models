"""Quantitative law of sampling-verification harm.

danger(rule, N) = play_cost(rule) * P(rule absent from N random games)
                = play_cost * (1 - rarity) ** N
A rule harms a sampling-verified planner iff it is rare enough to escape an
N-trajectory gate AND consequential enough to matter. All measurement is pure
(no LLM): the rule-blind hand-written base game is the on-manifold proxy for a
CWM that omits the rule.
"""
import math
import random

from .mcts import mcts_policy
from .arena import run_arena


def wilson_ci(successes: float, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, lo, hi) Wilson score interval. successes may be fractional (draws
    counted as 0.5); point = successes/n. n==0 -> (0.0, 0.0, 1.0)."""
    if n == 0:
        return (0.0, 0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def rarity(game, rule_reason: str, n_games: int, seed: int) -> tuple[float, float, float]:
    """Fraction of random games whose terminal outcome is decided by `rule_reason`
    (per game.outcome), with a Wilson CI."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_games):
        s = game.initial_state()
        while not game.is_terminal(s):
            s = game.apply_action(s, rng.choice(game.legal_actions(s)))
        if game.outcome(s)[1] == rule_reason:
            hits += 1
    return wilson_ci(hits, n_games)


def _mcts_agent(model, sims: int, base_seed: int):
    counter = {"n": 0}
    def agent(state, legal):
        counter["n"] += 1
        return mcts_policy(model, state, n_simulations=sims, seed=base_seed + counter["n"])
    return agent


def arena_winrate(truth, blind, sims: int, n_games: int, seeds: list) -> dict:
    """Win rate (wins + 0.5*draws)/n of a `blind`-planning MCTS agent vs a
    `truth`-planning MCTS agent, refereed by `truth`, pooled over `seeds`."""
    wins = draws = losses = 0
    for sd in seeds:
        a_blind = _mcts_agent(blind, sims, sd + 1)
        a_truth = _mcts_agent(truth, sims, sd + 100_000)
        # run_arena treats arg1 as "cwm_agent" -> our blind agent
        res = run_arena(truth, cwm_agent=a_blind, baseline_agent=a_truth,
                        n_games=n_games, seed=sd + 2000)
        wins += res.cwm_wins
        draws += res.draws
        losses += res.baseline_wins
    n = wins + draws + losses
    point, lo, hi = wilson_ci(wins + 0.5 * draws, n)
    return {"winrate": point, "lo": lo, "hi": hi, "n": n,
            "wins": wins, "draws": draws, "losses": losses}


def danger(play_cost: float, rarity_rate: float, n: int) -> float:
    return play_cost * (1 - rarity_rate) ** n
