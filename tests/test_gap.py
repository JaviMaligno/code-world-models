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

def test_exec_failure_reported_not_counted_as_divergence():
    # A CWM whose module crashes on import cannot be evaluated at all (the whole
    # sandbox program exits non-zero). That must be reported as n_exec_errors
    # (excluded from rate denominators), NOT silently counted as a divergent run.
    states = [tictactoe.initial_state(),
              {"board": [1, 0, 0, 0, 0, 0, 0, 0, 0], "current_player": 2}]
    rep = contract_divergence("raise RuntimeError('boom')", states, tictactoe,
                              timeout=2.0)
    assert rep.n_exec_errors == len(states)
    assert rep.n_states == 0           # nothing measured
    assert rep.examples                # surfaced

def test_chunking_matches_single_batch():
    # Same result whether the states are evaluated in one batch or several chunks.
    src = inspect.getsource(tictactoe)
    states = [tictactoe.initial_state(),
              {"board": [1, 1, 0, 2, 2, 0, 0, 0, 0], "current_player": 1},
              {"board": [1, 1, 1, 2, 2, 0, 0, 0, 0], "current_player": 2}]
    big = contract_divergence(src, states, tictactoe, chunk_size=100)
    small = contract_divergence(src, states, tictactoe, chunk_size=1)
    assert big.state_agreement_rate == small.state_agreement_rate == 1.0
    assert big.n_states == small.n_states == 3

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

def test_inference_accuracy_perfect_oracle():
    import inspect
    from cwm.gap import inference_accuracy
    from cwm.groundtruth import kuhn_poker
    src = inspect.getsource(kuhn_poker)
    states = [kuhn_poker.initial_state(),
              {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}]
    rep = inference_accuracy(src, states, kuhn_poker)
    assert rep["observation_rate"] == 1.0
    assert rep["inference_rate"] == 1.0
    assert rep["n_exec_errors"] == 0

def test_inference_accuracy_detects_wrong_infer():
    import inspect
    from cwm.gap import inference_accuracy
    from cwm.groundtruth import kuhn_poker
    src = inspect.getsource(kuhn_poker)
    # corrupt infer_states to drop one consistent state (return only the first)
    bad = src.replace("    return out\n\n\nRULES_TEXT",
                      "    return out[:1]\n\n\nRULES_TEXT")
    assert bad != src
    states = [{"board": [2, 0, 1, -1, -1, -1], "current_player": 1}]
    rep = inference_accuracy(bad, states, kuhn_poker)
    assert rep["inference_rate"] < 1.0

def test_inference_accuracy_excludes_exec_errors():
    """A crashing infer_states is a robustness failure: excluded from the rate
    denominator and counted separately, NOT scored as an inference miss. A crash
    on inference must also not drag down observation_rate."""
    import inspect
    from cwm.gap import inference_accuracy
    from cwm.groundtruth import kuhn_poker
    src = inspect.getsource(kuhn_poker)
    # make infer_states crash the classic way: call a list (the 'list' object is
    # not callable TypeError the contract name-collision used to induce).
    crash = src.replace("    return out\n\n\nRULES_TEXT",
                        "    return out()\n\n\nRULES_TEXT")
    assert crash != src
    states = [{"board": [2, 0, 1, -1, -1, -1], "current_player": 1}]
    rep = inference_accuracy(crash, states, kuhn_poker)
    assert rep["inf_measured"] == 0                 # every case crashed on inference
    assert rep["inf_errors"] == rep["n"]
    assert rep["n_exec_errors"] > 0
    assert rep["inference_rate"] == 0.0             # structural, not a scored miss
    # observation() still runs -> not contaminated by the infer crash
    assert rep["observation_rate"] == 1.0
    assert rep["obs_errors"] == 0
    assert rep["examples"]
