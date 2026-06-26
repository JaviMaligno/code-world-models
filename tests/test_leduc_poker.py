from cwm.groundtruth import leduc_poker as L

def test_initial_states_distinct_deals():
    ss = L.initial_states()
    assert len(ss) == 6 * 5 * 4                      # ordered (p1,p2,comm) distinct ids
    for s in ss:
        b = s["board"]
        assert len({b[0], b[1], b[2]}) == 3          # three distinct physical cards
        assert b[3] == 0 and b[4] == 1 and b[5] == 1 # round 0, antes
        assert b[6] == 0 and b[7] == 0 and b[8] == 0
        assert s["current_player"] == 1

def test_legal_actions_opening_no_fold():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    assert L.legal_actions(s) == [1, 2]              # check or raise; no fold with no bet

def test_legal_actions_facing_bet():
    # P1 raised in round 0: committed 3 vs 1, P2 to act
    s = {"board": [0, 2, 4, 0, 3, 1, 1, 1, 0], "current_player": 2}
    assert L.legal_actions(s) == [0, 1, 2]           # fold, call, raise

def test_raise_cap():
    s = {"board": [0, 2, 4, 0, 5, 3, 2, 2, 0], "current_player": 2}  # 2 raises done
    assert L.legal_actions(s) == [0, 1]              # no further raise

def test_apply_action_pure_and_raise_bookkeeping():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    before = list(s["board"])
    ns = L.apply_action(s, 2)                        # P1 raises (bet 2)
    assert s["board"] == before                      # input unmutated
    assert ns["board"][4] == 3 and ns["board"][6] == 1 and ns["board"][7] == 1
    assert ns["current_player"] == 2

def test_check_check_advances_to_round1():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    s = L.apply_action(s, 1)                          # P1 check
    assert s["current_player"] == 2 and s["board"][3] == 0
    s = L.apply_action(s, 1)                          # P2 check -> round 1
    assert s["board"][3] == 1 and s["board"][6] == 0 and s["board"][7] == 0
    assert s["current_player"] == 1 and not L.is_terminal(s)

def test_call_closes_round0_then_round1_showdown():
    s = {"board": [4, 0, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}  # P1=K id4, P2=J id0, comm=Q id2
    s = L.apply_action(s, 2)                          # P1 raise
    s = L.apply_action(s, 1)                          # P2 call -> round 1, committeds 3,3
    assert s["board"][3] == 1 and s["board"][4] == 3 and s["board"][5] == 3
    s = L.apply_action(s, 1)                          # P1 check
    s = L.apply_action(s, 1)                          # P2 check -> showdown
    assert s["board"][8] == 2 and L.is_terminal(s)
    assert L.returns(s) == {1: 3.0, 2: -3.0}         # K beats J, no pair, winner +3

def test_fold_returns():
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}  # P1=J id0
    s = L.apply_action(s, 2)                          # P1 raise -> committed 3
    assert s["current_player"] == 2
    s = L.apply_action(s, 0)                          # P2 folds
    assert s["board"][8] == 1 and L.is_terminal(s)
    assert s["current_player"] == 1                  # winner = P1
    assert L.returns(s) == {1: 1.0, 2: -1.0}         # P2 folded, committed 1

def test_showdown_pair_beats_high_card():
    # P1=J(id0), community=J(id1) -> P1 pairs; P2=K(id4)
    b = [0, 4, 1, 1, 3, 3, 0, 2, 2]                   # round1 showdown, committeds 3,3
    s = {"board": b, "current_player": 1}
    assert L.returns(s) == {1: 3.0, 2: -3.0}         # pair beats high card

def test_showdown_equal_rank_splits():
    # P1=J(id0), P2=J(id1), community=K(id4) -> equal rank, no pair -> split
    b = [0, 1, 4, 1, 3, 3, 0, 2, 2]
    s = {"board": b, "current_player": 1}
    assert L.returns(s) == {1: 0.0, 2: 0.0}

def test_returns_nonterminal_zero():
    assert L.returns(L.initial_state()) == {1: 0.0, 2: 0.0}

def test_cp_from_board():
    assert L._cp_from_board([0, 2, 4, 0, 1, 1, 0, 0, 0]) == 1
    assert L._cp_from_board([0, 2, 4, 0, 3, 1, 1, 1, 0]) == 2
