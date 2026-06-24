from cwm.groundtruth import gen_tictactoe as g

def test_initial_state():
    assert g.initial_state() == {"board": [0] * 36, "current_player": 1}

def test_legal_actions_all_empty():
    assert g.legal_actions(g.initial_state()) == list(range(36))

def test_apply_action_is_pure():
    s = g.initial_state()
    g.apply_action(s, 0)
    assert s["board"] == [0] * 36

def test_horizontal_win_needs_four():
    b = [0] * 36
    for c in range(4):
        b[c] = 1  # row 0, cols 0..3
    assert g.winner({"board": b, "current_player": 2}) == 1

def test_three_in_a_row_does_not_win():
    b = [0] * 36
    for c in range(3):
        b[c] = 1
    assert g.winner({"board": b, "current_player": 2}) == 0

def test_vertical_win():
    b = [0] * 36
    for r in range(4):
        b[r * 6] = 2  # col 0, rows 0..3
    assert g.winner({"board": b, "current_player": 1}) == 2

def test_diagonal_win():
    b = [0] * 36
    for k in range(4):
        b[k * 6 + k] = 1  # (0,0),(1,1),(2,2),(3,3)
    s = {"board": b, "current_player": 2}
    assert g.winner(s) == 1
    assert g.is_terminal(s) is True
    assert g.returns(s) == {1: 1.0, 2: -1.0}

def test_anti_diagonal_win():
    b = [0] * 36
    for k in range(4):
        b[k * 6 + (3 - k)] = 1  # (0,3),(1,2),(2,1),(3,0)
    assert g.winner({"board": b, "current_player": 2}) == 1

def test_returns_nonterminal_is_zero():
    assert g.returns(g.initial_state()) == {1: 0.0, 2: 0.0}
