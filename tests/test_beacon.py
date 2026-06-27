from cwm.groundtruth import beacon as B

G = B.make_beacon(T=3)   # small T for hand-checkable tests

def test_safe_function():
    assert G.safe(0, 0) == 0 and G.safe(0, 1) == 1
    assert G.safe(1, 0) == 1 and G.safe(1, 1) == 0

def test_initial_states_four_deals():
    ss = G.initial_states()
    assert len(ss) == 4                                  # (t1,t2) in {0,1}^2
    seen = set()
    for s in ss:
        b = s["board"]
        assert b[0] == 0 and b[1] == 0                   # steps
        assert b[4] == -1 and b[5] == -1                 # no moves yet
        assert b[6] == -1 and b[7] == -1                 # no guesses
        assert b[8] == 0                                 # walking
        assert s["current_player"] == 1
        seen.add((b[2], b[3]))
    assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}

def test_legal_actions_walk_and_final_and_terminal():
    s = {"board": [0, 0, 1, 0, -1, -1, -1, -1, 0], "current_player": 1}
    assert G.legal_actions(s) == [0, 1]                  # walk
    f = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    assert G.legal_actions(f) == [0, 1]                  # final round
    t = {"board": [3, 3, 1, 0, 1, 0, 1, 0, 2], "current_player": 1}
    assert G.legal_actions(t) == []                      # terminal

def test_unsafe_move_is_immediate_loss():
    # P1 type 0 at step 0: safe = 0; playing 1 loses -> P2 wins (status 3)
    s = {"board": [0, 0, 0, 1, -1, -1, -1, -1, 0], "current_player": 1}
    ns = G.apply_action(s, 1)
    assert ns["board"][8] == 3 and G.is_terminal(ns)
    assert G.returns(ns) == {1: -1.0, 2: 1.0}

def test_safe_move_advances_and_records_last_and_purity():
    s = {"board": [0, 0, 1, 0, -1, -1, -1, -1, 0], "current_player": 1}
    before = list(s["board"])
    ns = G.apply_action(s, 1)                            # P1 type 1 step 0: safe = 1
    assert s["board"] == before                          # input unmutated
    assert ns["board"][0] == 1 and ns["board"][4] == 1   # step1, last1
    assert ns["current_player"] == 2 and ns["board"][8] == 0

def test_full_walk_reaches_final_round():
    # T=3, types t1=1, t2=0. Both play safe each step; after 6 safe moves -> final.
    s = G.initial_state_with(1, 0)
    moves = 0
    while s["board"][8] == 0:
        p = s["current_player"]
        k = s["board"][0] if p == 1 else s["board"][1]
        t = s["board"][2] if p == 1 else s["board"][3]
        s = G.apply_action(s, G.safe(k, t))
        moves += 1
    assert moves == 6 and s["board"][8] == 1             # final round
    assert s["current_player"] == 1                      # P1 guesses first

def test_final_round_scoring_p1_wins():
    # both at T=3; t1=1, t2=0; P1 guesses t2=0 (correct), P2 guesses t1=1... make P2 wrong
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    s = G.apply_action(s, 0)                             # P1 guesses 0 == t2 -> correct
    assert s["current_player"] == 2 and s["board"][8] == 1
    s = G.apply_action(s, 0)                             # P2 guesses 0 != t1(1) -> wrong
    assert s["board"][8] == 2 and G.is_terminal(s)       # P1 wins (score 1 vs 0)
    assert G.returns(s) == {1: 1.0, 2: -1.0}

def test_final_round_draw_when_both_correct():
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    s = G.apply_action(s, 0)                             # P1 guesses t2=0 correct
    s = G.apply_action(s, 1)                             # P2 guesses t1=1 correct
    assert s["board"][8] == 4 and G.returns(s) == {1: 0.0, 2: 0.0}

def test_cp_from_board():
    assert G._cp_from_board([0, 0, 0, 0, -1, -1, -1, -1, 0]) == 1
    assert G._cp_from_board([1, 0, 0, 0, 1, -1, -1, -1, 0]) == 2
    assert G._cp_from_board([3, 3, 0, 0, 1, 1, -1, -1, 1]) == 1   # final, 0 guesses
    assert G._cp_from_board([3, 3, 0, 0, 1, 1, 0, -1, 1]) == 2    # final, 1 guess

def test_returns_nonterminal_zero():
    assert G.returns(G.initial_state()) == {1: 0.0, 2: 0.0}
