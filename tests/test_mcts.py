# tests/test_mcts.py
from cwm.mcts import mcts_policy
from cwm.groundtruth import tictactoe as g

def test_takes_immediate_win():
    # X at 0,1 ; needs 2 to win. O scattered harmlessly.
    state = {"board": [1, 1, 0, 2, 2, 0, 0, 0, 0], "current_player": 1}
    assert mcts_policy(g, state, n_simulations=300, seed=1) == 2

def test_blocks_immediate_loss():
    # O threatens 0,1 -> 2. X must block at 2.
    state = {"board": [2, 2, 0, 1, 0, 0, 0, 0, 0], "current_player": 1}
    assert mcts_policy(g, state, n_simulations=400, seed=1) == 2

def test_returns_legal_action():
    state = g.initial_state()
    assert mcts_policy(g, state, n_simulations=50, seed=1) in g.legal_actions(state)

def test_visited_collects_tree_states():
    from cwm.mcts import mcts_policy
    from cwm.groundtruth import tictactoe as g
    visited = set()
    mcts_policy(g, g.initial_state(), n_simulations=50, seed=1, visited=visited)
    assert len(visited) > 1  # root plus expanded children

def test_visited_default_none_unchanged():
    from cwm.mcts import mcts_policy
    from cwm.groundtruth import tictactoe as g
    a = mcts_policy(g, g.initial_state(), n_simulations=50, seed=1)
    assert a in g.legal_actions(g.initial_state())
