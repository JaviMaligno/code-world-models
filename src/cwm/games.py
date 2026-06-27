"""Registry of supported games."""
import types
from dataclasses import dataclass

from .groundtruth import (tictactoe, connect_four, gen_tictactoe, gen_chess,
                          trike, gen_chess_material, kuhn_poker, leduc_poker, beacon,
                          masked_tictactoe)


@dataclass(frozen=True)
class GameSpec:
    name: str
    module: types.ModuleType          # exposes the world-model contract functions
    rules_text: str
    policy_description: str


GAMES = {
    "tictactoe": GameSpec(
        name="tictactoe",
        module=tictactoe,
        rules_text=tictactoe.RULES_TEXT,
        policy_description=tictactoe.POLICY_DESCRIPTION,
    ),
    "connect4": GameSpec(
        name="connect4",
        module=connect_four,
        rules_text=connect_four.RULES_TEXT,
        policy_description=connect_four.POLICY_DESCRIPTION,
    ),
    "gen_tictactoe": GameSpec(
        name="gen_tictactoe",
        module=gen_tictactoe,
        rules_text=gen_tictactoe.RULES_TEXT,
        policy_description=gen_tictactoe.POLICY_DESCRIPTION,
    ),
    "army5x5a": GameSpec(
        name="army5x5a",
        module=gen_chess,
        rules_text=gen_chess.RULES_TEXT,
        policy_description=gen_chess.POLICY_DESCRIPTION,
    ),
    "trike": GameSpec(
        name="trike",
        module=trike,
        rules_text=trike.RULES_TEXT,
        policy_description=trike.POLICY_DESCRIPTION,
    ),
    "army5x5a_material": GameSpec(
        name="army5x5a_material",
        module=gen_chess_material,
        rules_text=gen_chess_material.RULES_TEXT,
        policy_description=gen_chess_material.POLICY_DESCRIPTION,
    ),
    "army5x5a_material_incomplete": GameSpec(
        name="army5x5a_material_incomplete",
        module=gen_chess_material,
        rules_text=gen_chess.RULES_TEXT,
        policy_description=gen_chess_material.POLICY_DESCRIPTION,
    ),
    "kuhn": GameSpec(
        name="kuhn",
        module=kuhn_poker,
        rules_text=kuhn_poker.RULES_TEXT,
        policy_description=kuhn_poker.POLICY_DESCRIPTION,
    ),
    "leduc": GameSpec(
        name="leduc",
        module=leduc_poker,
        rules_text=leduc_poker.RULES_TEXT,
        policy_description=leduc_poker.POLICY_DESCRIPTION,
    ),
    "beacon": GameSpec(
        name="beacon",
        module=beacon.make_beacon(),
        rules_text=beacon.RULES_TEXT,
        policy_description=beacon.POLICY_DESCRIPTION,
    ),
    "masked_tictactoe": GameSpec(
        name="masked_tictactoe",
        module=masked_tictactoe,
        rules_text=masked_tictactoe.RULES_TEXT,
        policy_description=masked_tictactoe.POLICY_DESCRIPTION,
    ),
}
