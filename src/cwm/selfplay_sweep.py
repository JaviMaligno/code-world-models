"""Non-triviality check: does MCTS skill beat random play on this game?

A game is a useful skill discriminator only if a searcher reliably beats random.
Run this on each new ground truth before trusting it. (No forced first-player win
is checked by eyeballing MCTS-vs-MCTS results separately.)
"""
import random

from .mcts import mcts_policy


def mcts_vs_random(model, n_games: int, simulations: int, seed: int) -> dict:
    rng = random.Random(seed)
    wins = draws = losses = 0
    for i in range(n_games):
        mcts_player = 1 if i % 2 == 0 else 2     # alternate sides
        state = model.initial_state()
        move = 0
        while not model.is_terminal(state):
            p = state["current_player"]
            if p == mcts_player:
                a = mcts_policy(model, state, n_simulations=simulations,
                                seed=seed + i * 1000 + move)
            else:
                a = rng.choice(model.legal_actions(state))
            state = model.apply_action(state, a)
            move += 1
        r = model.returns(state)
        if r[mcts_player] > 0.5:
            wins += 1
        elif r[mcts_player] < -0.5:
            losses += 1
        else:
            draws += 1
    return {"games": n_games, "mcts_wins": wins, "draws": draws,
            "mcts_losses": losses,
            "mcts_winrate": (wins + 0.5 * draws) / n_games}
