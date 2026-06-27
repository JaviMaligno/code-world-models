"""Masked tic-tac-toe — Claim B witness (belief model orthogonal to transitions).

Standard tic-tac-toe dynamics (re-exported unchanged from `tictactoe`) plus an
arbitrary, non-recallable observation rule: the center cell (index 4) is hidden
from both players (shown as -1), even after it is played. infer_states enumerates
the count-consistent values of the hidden center. The dynamics synthesize at
transition-gate 1.0 (recall); the masking is the withholdable, dynamics-independent
rule whose omission a transition gate cannot detect.
"""
from . import tictactoe as _t
from .tictactoe import (  # re-export the unchanged dynamics surface
    initial_state, legal_actions, apply_action, winner, is_terminal, returns,
)

HIDDEN = 4


def observation(state: dict, player: int) -> list:
    b = list(state["board"])
    b[HIDDEN] = -1
    return b


def infer_states(obs_board: list, player: int) -> list:
    out = []
    for v in (0, 1, 2):
        board = list(obs_board)
        board[HIDDEN] = v
        x = board.count(1)
        o = board.count(2)
        if x == o or x == o + 1:                 # legal tic-tac-toe counts
            out.append({"board": board, "current_player": 1 if x == o else 2})
    return out


RULES_TEXT = _t.RULES_TEXT.rstrip() + """
  - Imperfect information: the center cell (index 4) is hidden from BOTH players —
    observation shows it as -1, even after a mark has been placed there. All other
    cells are public. infer_states must enumerate every value (0, 1, 2) of the
    hidden center that yields a legal position (X starts, so the count of 1s equals
    the count of 2s, or exceeds it by exactly one); the true state is always among
    them.
"""

POLICY_DESCRIPTION = _t.POLICY_DESCRIPTION + (
    " The center cell (index 4) is hidden from you (shown as -1); infer its value "
    "from the visible board and turn parity.")
