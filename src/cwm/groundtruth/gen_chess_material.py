"""army5x5a with a deep-tail 'material-at-cap' rule (rare-rule gap instrument).

Identical to gen_chess (army5x5a) EXCEPT terminal scoring at the ply cap: when the
ply counter reaches MAX_PLIES with both generals alive, instead of a draw the
player with more pieces on the board (cells 0..24) wins; equal counts is a draw.
is_terminal / legal_actions / apply_action are unchanged from base, so only
`returns` differs. This rule is rare under random play (~2.5% of random games (measured material-terminal rate)) but central
to competent play (~50%), exposing the gate's coverage blind spot.
"""
from . import gen_chess as base
from .gen_chess import (  # re-export the unchanged contract surface
    initial_state, legal_actions, apply_action, is_terminal,
    N, MAX_PLIES, _general_alive,
)


def _material(board: list) -> tuple[int, int]:
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


def _moves(board: list, player: int) -> list:
    """Legal piece moves for `player`, independent of any cap (base.legal_actions
    is gated by base.is_terminal at the fixed cap 100, which is wrong for other
    cap lengths, so generate moves directly)."""
    actions = []
    for idx in range(N):
        v = board[idx]
        if v != 0 and base._OWNER[v] == player:
            for tgt in base._piece_dests(board, idx):
                actions.append(idx * N + tgt)
    if not actions:
        actions.append(base.PASS)
    return actions


class _MaterialGame:
    """army5x5a + material-at-cap, parameterized by cap length and lead threshold."""

    def __init__(self, max_plies: int, lead: int):
        self.max_plies = max_plies
        self.lead = lead

    def initial_state(self) -> dict:
        return initial_state()

    def apply_action(self, state: dict, action: int) -> dict:
        return apply_action(state, action)

    def outcome(self, state: dict) -> tuple[int, str]:
        b = state["board"]
        a1, a2 = _general_alive(b, 1), _general_alive(b, 2)
        if not a1 or not a2:
            return (1 if a1 else 2), "capture"
        if b[N] >= self.max_plies:
            p1, p2 = _material(b)
            if p1 - p2 >= self.lead:
                return 1, "material"
            if p2 - p1 >= self.lead:
                return 2, "material"
            return 0, "draw"
        return 0, "none"

    def is_terminal(self, state: dict) -> bool:
        return self.outcome(state)[1] != "none"

    def legal_actions(self, state: dict) -> list:
        if self.is_terminal(state):
            return []
        return _moves(state["board"], state["current_player"])

    def returns(self, state: dict) -> dict:
        w, reason = self.outcome(state)
        if reason == "none":
            return {1: 0.0, 2: 0.0}
        if w == 1:
            return {1: 1.0, 2: -1.0}
        if w == 2:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}


def make_material(max_plies: int = 100, lead: int = 1) -> "_MaterialGame":
    return _MaterialGame(max_plies, lead)
