from cwm.games import GAMES, GameSpec
from cwm.world_model import CONTRACT_API, build_contract

def test_registry_has_tictactoe():
    assert "tictactoe" in GAMES
    spec = GAMES["tictactoe"]
    assert isinstance(spec, GameSpec)
    assert spec.name == "tictactoe"

def test_spec_module_implements_contract():
    m = GAMES["tictactoe"].module
    s = m.initial_state()
    assert s == {"board": [0]*9, "current_player": 1}
    assert m.legal_actions(s) == list(range(9))

def test_build_contract_combines_api_and_rules():
    c = build_contract(GAMES["tictactoe"].rules_text)
    assert "initial_state" in c            # from API
    assert "tic-tac-toe" in c.lower()      # from rules
    assert c.startswith(CONTRACT_API[:20])

def test_policy_description_present():
    assert "tic-tac-toe" in GAMES["tictactoe"].policy_description.lower()
