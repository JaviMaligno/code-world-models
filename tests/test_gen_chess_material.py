from cwm.groundtruth import gen_chess_material as m
from cwm.groundtruth import gen_chess as base

def _cap_state(board_cells, current_player=1):
    # board_cells: 25 cell values; ply counter set to the cap.
    return {"board": list(board_cells) + [base.MAX_PLIES], "current_player": current_player}

def test_initial_state_matches_base():
    assert m.initial_state() == base.initial_state()

def test_legal_and_apply_match_base_midgame():
    s = base.initial_state()
    assert m.legal_actions(s) == base.legal_actions(s)
    a = m.legal_actions(s)[0]
    assert m.apply_action(s, a) == base.apply_action(s, a)

def test_material_counts():
    cells = [0] * 25
    cells[0] = 1; cells[1] = 2; cells[2] = 3   # P1: 3 pieces
    cells[20] = 4; cells[21] = 5               # P2: 2 pieces
    assert m._material(cells) == (3, 2)

def test_cap_material_winner():
    cells = [0] * 25
    cells[2] = 1; cells[5] = 2; cells[6] = 3   # P1 general + 2 pieces = 3
    cells[22] = 4                              # P2 general only = 1
    s = _cap_state(cells)
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 1.0, 2: -1.0}

def test_cap_equal_material_is_draw():
    cells = [0] * 25
    cells[2] = 1; cells[5] = 2                 # P1: 2
    cells[22] = 4; cells[23] = 5               # P2: 2
    s = _cap_state(cells)
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 0.0, 2: 0.0}

def test_capture_win_unchanged():
    cells = [0] * 25
    cells[2] = 1                               # only P1 general alive (P2 general captured)
    s = {"board": cells + [10], "current_player": 1}
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 1.0, 2: -1.0}

def test_nonterminal_returns_zero():
    s = base.initial_state()
    assert m.is_terminal(s) is False
    assert m.returns(s) == {1: 0.0, 2: 0.0}

def test_rules_text_variants_registered():
    from cwm.games import GAMES
    assert GAMES["army5x5a_material"].module is m
    assert GAMES["army5x5a_material_incomplete"].module is m
    # complete spec mentions material/pieces at the cap; incomplete keeps base "draw"
    assert "more pieces" in GAMES["army5x5a_material"].rules_text.lower()
    assert GAMES["army5x5a_material_incomplete"].rules_text == base.RULES_TEXT
