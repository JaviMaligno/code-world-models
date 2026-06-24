from cwm.arena import play_match, run_arena, MatchResult, ArenaResult
from cwm.groundtruth import tictactoe as g

def first_legal(state, legal):
    return legal[0]

def always_illegal(state, legal):
    return None

def test_forfeit_on_illegal():
    # player 1 (agent1) always returns None -> forfeits, player 2 wins
    res = play_match(g, always_illegal, first_legal, seed=1)
    assert isinstance(res, MatchResult)
    assert res.winner == 2 and res.illegal_by[1] == 1

def test_play_match_completes_to_terminal():
    res = play_match(g, first_legal, first_legal, seed=1)
    assert res.winner in (0, 1, 2) and res.moves > 0

def test_run_arena_aggregates_and_alternates():
    # cwm_agent = first_legal, baseline = always_illegal -> baseline forfeits every game
    res = run_arena(g, cwm_agent=first_legal, baseline_agent=always_illegal,
                    n_games=4, seed=1)
    assert isinstance(res, ArenaResult)
    assert res.games == 4
    assert res.cwm_wins == 4 and res.baseline_illegal == 4
