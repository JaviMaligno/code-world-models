from cwm.selfplay_sweep import mcts_vs_random
from cwm.groundtruth import tictactoe as g

def test_mcts_beats_random_at_tictactoe():
    res = mcts_vs_random(g, n_games=10, simulations=100, seed=0)
    assert res["games"] == 10
    assert res["mcts_losses"] <= 1          # MCTS should essentially never lose to random
    assert res["mcts_winrate"] >= 0.7
