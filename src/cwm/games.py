"""Registry of supported games."""
import types
from dataclasses import dataclass

from .groundtruth import tictactoe, connect_four


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
}
