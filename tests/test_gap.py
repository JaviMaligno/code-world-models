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

def test_empty_states_is_safe():
    src = inspect.getsource(tictactoe)
    rep = contract_divergence(src, [], tictactoe)
    assert rep.n_states == 0
    assert rep.state_agreement_rate == 1.0
