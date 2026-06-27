from cwm.groundtruth import masked_tictactoe as M
from cwm.groundtruth import tictactoe as T

def test_dynamics_delegated_to_tictactoe():
    s = M.initial_state()
    assert s == T.initial_state()
    assert M.legal_actions(s) == T.legal_actions(s)
    assert M.apply_action(s, 0) == T.apply_action(s, 0)
    assert M.is_terminal(s) == T.is_terminal(s)
    assert M.returns(s) == T.returns(s)

def test_observation_masks_only_center_both_players():
    s = {"board": [1, 2, 1, 0, 2, 0, 0, 0, 0], "current_player": 1}
    assert M.observation(s, 1) == [1, 2, 1, 0, -1, 0, 0, 0, 0]
    assert M.observation(s, 2) == [1, 2, 1, 0, -1, 0, 0, 0, 0]   # symmetric mask
    # only the center changed
    assert M.observation(s, 1)[:4] == s["board"][:4]
    assert M.observation(s, 1)[5:] == s["board"][5:]

def test_observation_initial_state_masks_empty_center():
    assert M.observation(M.initial_state(), 1) == [0, 0, 0, 0, -1, 0, 0, 0, 0]

def test_infer_states_enumerates_count_consistent_centers():
    # visible: two X (0,2), one O (1); center hidden. a=#X_vis=2, b=#O_vis=1.
    s = {"board": [1, 2, 1, 0, 0, 0, 0, 0, 0], "current_player": 1}  # true center empty
    obs = M.observation(s, 1)
    boards = sorted(tuple(d["board"]) for d in M.infer_states(obs, 1))
    # v=0: #X=2,#O=1 -> 2==1+1 legal; v=1: #X=3,#O=1 -> illegal; v=2: #X=2,#O=2 -> legal
    assert boards == sorted([(1,2,1,0,0,0,0,0,0), (1,2,1,0,2,0,0,0,0)])
    assert any(d["board"] == s["board"] for d in M.infer_states(obs, 1))  # true member

def test_infer_states_roundtrip_and_legal_current_player():
    s = {"board": [1, 2, 1, 0, 0, 0, 0, 0, 0], "current_player": 1}
    obs = M.observation(s, 1)
    for d in M.infer_states(obs, 1):
        assert M.observation(d, 1) == obs                       # round-trip
        x = d["board"].count(1); o = d["board"].count(2)
        assert d["current_player"] == (1 if x == o else 2)      # parity-derived

def test_infer_states_filters_illegal_center_and_keeps_true():
    # 8 visible filled (4 X, 4 O), true center empty.
    s = {"board": [1, 2, 1, 2, 0, 1, 2, 1, 2], "current_player": 1}
    obs = M.observation(s, 1)
    boards = sorted(tuple(d["board"]) for d in M.infer_states(obs, 1))
    # v=0 -> 4X,4O legal; v=1 -> 5X,4O legal; v=2 -> 4X,5O ILLEGAL (filtered out)
    assert boards == sorted([(1,2,1,2,0,1,2,1,2), (1,2,1,2,1,1,2,1,2)])
    assert (1,2,1,2,0,1,2,1,2) in boards                        # true (empty center) kept

def test_registered():
    from cwm.games import GAMES
    assert "tic-tac-toe" in GAMES["masked_tictactoe"].rules_text.lower()
    assert GAMES["masked_tictactoe"].module is M
