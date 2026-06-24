"""Registry of supported games."""
import types
from dataclasses import dataclass

from .groundtruth import tictactoe


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
}
