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


# Two-sided 95% Student-t critical values t_{0.975, df}. Keyed by df; for a df
# not in the table we use the largest tabulated df <= our df, which is >= the
# true value (t decreases in df) and so stays conservative. Beyond df=120 the
# t is within 1% of the normal 1.96. This replaces per-script hardcoded dicts
# that capped out at a handful of seeds.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
         7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
         13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
         19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064,
         25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
         40: 2.021, 50: 2.009, 60: 2.000, 80: 1.990, 100: 1.984, 120: 1.980}


def t_crit_95(df: int) -> float:
    """Two-sided 95% Student-t critical value for `df` degrees of freedom.
    Conservative: rounds df down to the nearest tabulated value, so the result
    is >= the exact t. For df > 120 it floors at the df=120 value (1.98), within
    1% of the normal quantile 1.96 and slightly conservative."""
    if df < 1:
        raise ValueError("df must be >= 1")
    if df in _T975:
        return _T975[df]
    keys = [k for k in _T975 if k <= df]
    return _T975[max(keys)]


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
