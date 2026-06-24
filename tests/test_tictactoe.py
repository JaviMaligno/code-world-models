from cwm.groundtruth import tictactoe as g
from cwm import world_model as wm

def test_initial_state():
    s = g.initial_state()
    assert s == {"board": [0]*9, "current_player": 1}

def test_legal_actions_all_open():
    assert g.legal_actions(g.initial_state()) == list(range(9))

def test_apply_action_places_and_switches():
    s2 = g.apply_action(g.initial_state(), 4)
    assert s2["board"][4] == 1
    assert s2["current_player"] == 2

def test_apply_action_is_pure():
    s = g.initial_state()
    g.apply_action(s, 0)
    assert s["board"] == [0]*9  # original unchanged

def test_row_win_terminal_and_returns():
    # X takes 0,1,2 ; O takes 3,4
    s = g.initial_state()
    for a in [0, 3, 1, 4, 2]:
        s = g.apply_action(s, a)
    assert g.winner(s) == 1
    assert g.is_terminal(s) is True
    assert g.returns(s) == {1: 1.0, 2: -1.0}

def test_full_board_draw():
    s = g.initial_state()
    # 0 1 2 / 3 4 5 / 6 7 8 filled to a draw:
    # X O X / X O O / O X X  -> moves order producing that, no 3-in-a-row
    for a in [0, 1, 2, 4, 3, 5, 7, 6, 8]:
        s = g.apply_action(s, a)
    assert g.is_terminal(s) is True
    assert g.winner(s) == 0
    assert g.returns(s) == {1: 0.0, 2: 0.0}

def test_legal_actions_excludes_filled():
    s = g.apply_action(g.initial_state(), 0)
    assert 0 not in g.legal_actions(s)

def test_json_roundtrip():
    s = g.apply_action(g.initial_state(), 4)
    assert wm.state_from_json(wm.state_to_json(s)) == s

def test_returns_nonterminal_is_zero():
    assert g.returns(g.initial_state()) == {1: 0.0, 2: 0.0}

def test_column_win_for_o_and_returns():
    # X plays 0,2,8 ; O plays 1,4,7 -> O wins column 1,4,7
    s = g.initial_state()
    for a in [0, 1, 2, 4, 8, 7]:  # X:0, O:1, X:2, O:4, X:8, O:7 -> O wins column 1,4,7
        s = g.apply_action(s, a)
    assert g.winner(s) == 2
    assert g.is_terminal(s) is True
    assert g.returns(s) == {1: -1.0, 2: 1.0}
