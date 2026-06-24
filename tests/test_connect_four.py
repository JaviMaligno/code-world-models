from cwm.groundtruth import connect_four as c


def test_initial_state():
    s = c.initial_state()
    assert s == {"board": [0]*42, "current_player": 1}


def test_legal_actions_all_columns():
    assert c.legal_actions(c.initial_state()) == [0, 1, 2, 3, 4, 5, 6]


def test_gravity_drop_to_bottom():
    s = c.apply_action(c.initial_state(), 3)
    # bottom row is row 5 -> index 5*7+3 = 38
    assert s["board"][38] == 1
    assert s["current_player"] == 2


def test_stacking_in_column():
    s = c.initial_state()
    s = c.apply_action(s, 3)   # P1 -> row5 col3 (idx38)
    s = c.apply_action(s, 3)   # P2 -> row4 col3 (idx31)
    assert s["board"][38] == 1 and s["board"][31] == 2


def test_apply_action_is_pure():
    s = c.initial_state()
    c.apply_action(s, 0)
    assert s["board"] == [0]*42


def test_vertical_win():
    s = c.initial_state()
    # P1 stacks col0 four times; P2 plays col1 between
    for col in [0, 1, 0, 1, 0, 1, 0]:
        s = c.apply_action(s, col)
    assert c.winner(s) == 1
    assert c.is_terminal(s) is True
    assert c.returns(s) == {1: 1.0, 2: -1.0}


def test_horizontal_win():
    s = c.initial_state()
    # P1 plays cols 0,1,2,3 on bottom row; P2 plays col6 area on bottom (won't make 4)
    for col in [0, 6, 1, 6, 2, 5, 3]:
        s = c.apply_action(s, col)
    assert c.winner(s) == 1


def test_diagonal_win():
    s = c.initial_state()
    # Build an ascending diagonal for P1: (r5,c0),(r4,c1),(r3,c2),(r2,c3)
    # Move sequence engineered so P1 occupies the diagonal; verify winner==1.
    moves = [0,   # P1 r5c0
             1,   # P2 r5c1
             1,   # P1 r4c1
             2,   # P2 r5c2
             3,   # P1 r5c3 (filler, not diagonal yet)
             2,   # P2 r4c2
             2,   # P1 r3c2
             3,   # P2 r4c3
             6,   # P1 filler r5c6
             3,   # P2 r3c3
             3]   # P1 r2c3  -> completes diagonal (r5c0,r4c1,r3c2,r2c3)
    for m in moves:
        s = c.apply_action(s, m)
    assert c.winner(s) == 1


def test_legal_excludes_full_column():
    s = c.initial_state()
    for _ in range(6):           # fill column 0 (6 rows)
        s = c.apply_action(s, 0)
    assert 0 not in c.legal_actions(s)


def test_returns_nonterminal_is_zero():
    assert c.returns(c.initial_state()) == {1: 0.0, 2: 0.0}
