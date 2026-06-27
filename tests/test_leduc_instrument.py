from cwm.leduc_instrument import WrongInference, _is_tail
from cwm.groundtruth import leduc_poker as L

def test_wronginference_delegates_dynamics():
    w = WrongInference()
    s = L.initial_state()
    assert w.legal_actions(s) == L.legal_actions(s)
    assert w.apply_action(s, 1) == L.apply_action(s, 1)
    assert w.is_terminal(s) == L.is_terminal(s)
    assert w.initial_states() == L.initial_states()

def test_wronginference_correct_off_tail_round0():
    # round 0 (no tail): inference equals the truth
    w = WrongInference()
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}
    obs = w.observation(s, 1)
    assert w.infer_states(obs, 1) == L.infer_states(obs, 1)

def test_wronginference_wrong_on_tail():
    # round 1 with a raise (committeds 7,7 > ante) -> tail -> drops one state
    w = WrongInference()
    board = [0, 4, 2, 1, 7, 7, 0, 0, 0]
    assert _is_tail(board) is True
    obs = w.observation({"board": board, "current_player": 1}, 1)
    truth_inf = L.infer_states(obs, 1)
    wrong_inf = w.infer_states(obs, 1)
    assert len(wrong_inf) == len(truth_inf) - 1          # one consistent state dropped
    assert all(d in truth_inf for d in wrong_inf)         # remaining are still valid

def test_tail_predicate_excludes_cheap_lines():
    assert _is_tail([0, 4, 2, 1, 1, 1, 0, 0, 0]) is False   # round 1 but only antes
    assert _is_tail([0, 4, 2, 0, 7, 7, 0, 0, 0]) is False   # round 0 never tail
