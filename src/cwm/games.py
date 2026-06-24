"""Registry of supported games."""
import types
from dataclasses import dataclass

from .groundtruth import tictactoe, connect_four, gen_tictactoe, gen_chess, trike


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
}
