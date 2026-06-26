from cwm.groundtruth import kuhn_poker as k

def test_initial_states_enumerates_six_deals():
    ss = k.initial_states()
    assert len(ss) == 6
    for s in ss:
        b = s["board"]
        assert sorted(b[:3]) == [0, 1, 2]        # three distinct cards
        assert b[3:] == [-1, -1, -1]             # empty history
        assert s["current_player"] == 1
    assert k.initial_state() == ss[0]

def test_legal_actions_two_until_terminal():
    s = k.initial_state()
    assert k.legal_actions(s) == [0, 1]

def test_apply_action_is_pure_and_toggles_player():
    s = k.initial_state()
    before = list(s["board"])
    ns = k.apply_action(s, 1)
    assert s["board"] == before                  # input unmutated
    assert ns["board"][3] == 1                   # first history slot filled
    assert ns["current_player"] == 2

def test_check_check_showdown_higher_card_wins():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}  # P1=K, P2=J
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 0)   # P2 check -> showdown pot 2
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 1.0, 2: -1.0}

def test_bet_fold_betting_player_wins_ante():
    s = {"board": [0, 2, 1, -1, -1, -1], "current_player": 1}  # P1=J, P2=K
    s = k.apply_action(s, 1)   # P1 bet
    s = k.apply_action(s, 0)   # P2 fold
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 1.0, 2: -1.0}     # P2 folded -> loses ante 1

def test_check_bet_call_showdown_pot4():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}  # P1=K, P2=J
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 1)   # P2 bet
    s = k.apply_action(s, 1)   # P1 call -> showdown pot 4
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 2.0, 2: -2.0}

def test_check_bet_fold_p1_folds():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 1)   # P2 bet
    s = k.apply_action(s, 0)   # P1 fold -> P2 wins ante
    assert k.is_terminal(s)
    assert k.returns(s) == {1: -1.0, 2: 1.0}

def test_returns_nonterminal_zero():
    assert k.returns(k.initial_state()) == {1: 0.0, 2: 0.0}

def test_observation_masks_opponent_and_unused():
    s = {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}
    o1 = k.observation(s, 1)
    assert o1 == [2, -1, -1, 1, -1, -1]          # P1 sees own card + history
    o2 = k.observation(s, 2)
    assert o2 == [-1, 0, -1, 1, -1, -1]          # P2 sees own card + history

def test_infer_states_exact_and_roundtrip():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}
    obs = k.observation(s, 1)                     # [2,-1,-1,-1,-1,-1]
    inferred = k.infer_states(obs, 1)
    assert len(inferred) == 2
    # the true state is a member
    assert any(d["board"] == s["board"] for d in inferred)
    # round-trip invariant + current_player recovered
    for d in inferred:
        assert k.observation(d, 1) == obs
        assert d["current_player"] == 1
        assert sorted(d["board"][:3]) == [0, 1, 2]

def test_infer_states_for_player2_midgame():
    s = {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}   # after P1 bet
    obs = k.observation(s, 2)
    inferred = k.infer_states(obs, 2)
    assert len(inferred) == 2
    for d in inferred:
        assert k.observation(d, 2) == obs
        assert d["current_player"] == 2          # history len 1 -> P2 to act
