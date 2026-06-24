from cwm.groundtruth import gen_chess as g

def test_initial_state_layout():
    s = g.initial_state()
    assert len(s["board"]) == 26
    assert s["board"][0:5] == [3, 2, 1, 2, 3]      # rank A: P1
    assert s["board"][20:25] == [6, 5, 4, 5, 6]    # rank E: P2
    assert s["board"][25] == 0                      # ply counter
    assert s["current_player"] == 1

def test_p1_infantry_move_present():
    # infantry at index 1 (row0,col1): (1,0)->idx6 => action 1*25+6 = 31
    assert 31 in g.legal_actions(g.initial_state())

def test_apply_action_is_pure_and_increments_plies():
    s = g.initial_state()
    before = list(s["board"])
    ns = g.apply_action(s, 31)
    assert s["board"] == before            # input unchanged
    assert ns["board"][25] == 1            # ply incremented
    assert ns["current_player"] == 2

def test_capture_general_wins():
    board = [0] * 25 + [0]
    board[12] = 1   # P1 general at (2,2)
    board[13] = 4   # P2 general at (2,3)
    s = {"board": board, "current_player": 1}
    assert g.is_terminal(s) is False
    action = 12 * 25 + 13            # general (0,1): (2,2)->(2,3) captures
    assert action in g.legal_actions(s)
    ns = g.apply_action(s, action)
    assert ns["board"][13] == 1 and ns["board"][12] == 0
    assert g.is_terminal(ns) is True
    assert g.returns(ns) == {1: 1.0, 2: -1.0}

def test_mirrored_player2_infantry_moves_up():
    # P2 infantry at idx22 (row4,col2); mirrored (-1,0)->(3,2)=idx17 => 22*25+17=567
    board = [0] * 25 + [0]
    board[0] = 1     # P1 general
    board[24] = 4    # P2 general
    board[22] = 5    # P2 infantry
    s = {"board": board, "current_player": 2}
    assert 567 in g.legal_actions(s)

def test_ply_cap_is_a_draw():
    board = [0] * 25 + [99]
    board[2] = 1     # P1 general (so both generals alive)
    board[22] = 4    # P2 general
    s = {"board": board, "current_player": 1}
    legal = g.legal_actions(s)
    assert legal  # at least one move exists
    ns = g.apply_action(s, legal[0])
    assert ns["board"][25] == 100
    assert g.is_terminal(ns) is True
    assert g.returns(ns) == {1: 0.0, 2: 0.0}

def test_pass_not_offered_when_moves_exist():
    # A lone general always has at least one move on a 5x5 board, so PASS (625)
    # must NOT be offered. PASS is only added when a side has no piece move.
    board = [0] * 25 + [0]
    board[0] = 1     # P1 general at (0,0)
    board[24] = 4    # P2 general
    s = {"board": board, "current_player": 1}
    legal = g.legal_actions(s)
    assert legal and g.PASS not in legal
