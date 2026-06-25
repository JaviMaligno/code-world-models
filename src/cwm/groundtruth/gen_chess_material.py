"""army5x5a with a deep-tail 'material-at-cap' rule (rare-rule gap instrument).

Identical to gen_chess (army5x5a) EXCEPT terminal scoring at the ply cap: when the
ply counter reaches MAX_PLIES with both generals alive, instead of a draw the
player with more pieces on the board (cells 0..24) wins; equal counts is a draw.
is_terminal / legal_actions / apply_action are unchanged from base, so only
`returns` differs. This rule is rare under random play (~1% of games) but central
to competent play (~50%), exposing the gate's coverage blind spot.
"""
from . import gen_chess as base
from .gen_chess import (  # re-export the unchanged contract surface
    initial_state, legal_actions, apply_action, is_terminal,
    N, MAX_PLIES, _general_alive,
)


def _material(board: list) -> tuple:
    p1 = sum(1 for v in board[:N] if v in (1, 2, 3))
    p2 = sum(1 for v in board[:N] if v in (4, 5, 6))
    return p1, p2


def returns(state: dict) -> dict:
    board = state["board"]
    a1, a2 = _general_alive(board, 1), _general_alive(board, 2)
    if not a1 or not a2:                      # a general was captured: as in base
        if a1 and not a2:
            return {1: 1.0, 2: -1.0}
        if a2 and not a1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}
    if board[N] >= MAX_PLIES:                 # deep-tail rule: more material wins
        p1, p2 = _material(board)
        if p1 > p2:
            return {1: 1.0, 2: -1.0}
        if p2 > p1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}
    return {1: 0.0, 2: 0.0}                   # non-terminal


# Complete spec: base rules with the cap clause rewritten to state the rule.
RULES_TEXT = base.RULES_TEXT.replace(
    "  - Capturing the opponent's general wins. If the ply counter reaches 100 with both\n"
    "    generals alive, the game is a draw.",
    "  - Capturing the opponent's general wins. If the ply counter reaches 100 with both\n"
    "    generals alive, the player with MORE pieces on the board (cells 0..24) wins;\n"
    "    equal piece counts is a draw.",
)

POLICY_DESCRIPTION = base.POLICY_DESCRIPTION
