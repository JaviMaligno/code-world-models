"""Non-triviality sweep: MCTS vs random on each new game. CPU-only, no Azure.

Run: PYTHONPATH=src python scripts/nontriviality_sweep.py
"""
import sys
import time

from cwm.games import GAMES
from cwm.selfplay_sweep import mcts_vs_random

CONFIG = [
    ("gen_tictactoe", 20, 200),
    ("army5x5a", 16, 200),
    ("trike", 16, 200),
]

for game, n_games, sims in CONFIG:
    model = GAMES[game].module
    t0 = time.time()
    res = mcts_vs_random(model, n_games=n_games, simulations=sims, seed=0)
    dt = time.time() - t0
    print(f"{game:14s} n={n_games} sims={sims}  "
          f"W/D/L = {res['mcts_wins']}/{res['draws']}/{res['mcts_losses']}  "
          f"winrate={res['mcts_winrate']:.2f}  ({dt:.1f}s)")
    sys.stdout.flush()
