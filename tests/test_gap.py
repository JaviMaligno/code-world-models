import inspect
from cwm.gap import contract_divergence
from cwm.groundtruth import tictactoe

_STATES = [
    tictactoe.initial_state(),
    {"board": [1, 1, 0, 2, 2, 0, 0, 0, 0], "current_player": 1},
    {"board": [1, 1, 1, 2, 2, 0, 0, 0, 0], "current_player": 2},  # terminal, P1 wins
]

def test_identical_module_has_no_gap():
    src = inspect.getsource(tictactoe)
    rep = contract_divergence(src, _STATES, tictactoe)
    assert rep.state_agreement_rate == 1.0
    assert rep.legal_rate == 1.0
    assert rep.transition_rate == 1.0

def test_corrupted_module_is_detected():
    src = inspect.getsource(tictactoe)
    bad = src.replace("b[x] == b[y] == b[z]", "False")  # never detects a win
    rep = contract_divergence(bad, _STATES, tictactoe)
    assert rep.state_agreement_rate < 1.0
    assert rep.examples  # at least one mismatch surfaced

def test_terminal_legal_divergence_excluded_but_tracked():
    # A CWM that omits the is_terminal guard in legal_actions returns empty cells
    # even on a won board. That divergence must NOT count against the gap (legal
    # moves from a finished game are undefined), but must be tracked as a diagnostic.
    src = inspect.getsource(tictactoe)
    no_guard = src.replace("    if is_terminal(state):\n        return []\n", "")
    assert "if is_terminal(state):" not in no_guard.split("def apply_action")[0]
    terminal = [{"board": [1, 1, 1, 2, 2, 0, 0, 0, 0], "current_player": 2}]  # P1 won
    rep = contract_divergence(no_guard, terminal, tictactoe)
    assert rep.state_agreement_rate == 1.0          # terminal-legal excluded
    assert rep.n_terminal == 1
    assert rep.legal_terminal_divergences == 1      # but surfaced as a diagnostic

def test_empty_states_is_safe():
    src = inspect.getsource(tictactoe)
    rep = contract_divergence(src, [], tictactoe)
    assert rep.n_states == 0
    assert rep.state_agreement_rate == 1.0

def test_collect_visited_states_basic():
    from cwm.gap import collect_visited_states
    from cwm.groundtruth import tictactoe
    states = collect_visited_states(tictactoe, n_games=2, simulations=30, seed=1)
    assert len(states) > 1
    assert all(set(s.keys()) == {"board", "current_player"} for s in states)

def test_collect_visited_states_respects_cap():
    from cwm.gap import collect_visited_states
    from cwm.groundtruth import tictactoe
    states = collect_visited_states(tictactoe, n_games=5, simulations=80, seed=1, cap=10)
    assert len(states) <= 10
