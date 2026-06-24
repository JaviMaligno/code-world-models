from cwm.groundtruth import trike as t

def test_initial_state():
    s = t.initial_state()
    assert len(s["board"]) == 21
    assert s["board"][12] == 5           # neutral pawn on the central start cell
    assert sum(1 for v in s["board"] if v != 0) == 1
    assert s["current_player"] == 1

def test_initial_legal_actions_exact():
    # Slides from (4,2)=idx12 over the empty board along all three axes.
    assert t.legal_actions(t.initial_state()) == [3, 5, 7, 8, 10, 11, 13, 14, 17, 18]

def test_apply_action_places_disc_and_vacates_start():
    s = t.apply_action(t.initial_state(), 13)
    assert s["board"][12] == 6           # vacated neutral start -> blocked-neutral
    assert s["board"][13] == 3           # P1 disc with pawn
    assert s["current_player"] == 2

def test_apply_action_is_pure():
    s = t.initial_state()
    t.apply_action(s, 13)
    assert s["board"][12] == 5 and s["board"][13] == 0

def test_slide_cannot_pass_occupied():
    s = t.initial_state()
    board = list(s["board"])
    board[13] = 1                        # block (4,3), one step along (0,+1)
    s2 = {"board": board, "current_player": 1}
    assert 13 not in t.legal_actions(s2)  # occupied, cannot land
    assert 14 not in t.legal_actions(s2)  # cannot pass over 13 to reach 14

def test_terminal_scoring_majority():
    # Pawn (P1, value 3) at idx12 with all six neighbors occupied -> trapped.
    board = [0] * 21
    board[12] = 3                        # pawn + P1 disc
    board[13] = 1; board[18] = 1; board[17] = 1   # P1 neighbors
    board[11] = 2; board[7] = 2; board[8] = 2     # P2 neighbors
    s = {"board": board, "current_player": 2}
    assert t.is_terminal(s) is True
    # pawn cell + 6 neighbors: P1 = 3,13,18,17 = 4 ; P2 = 11,7,8 = 3
    assert t.returns(s) == {1: 1.0, 2: -1.0}

def test_returns_nonterminal_is_zero():
    assert t.returns(t.initial_state()) == {1: 0.0, 2: 0.0}
