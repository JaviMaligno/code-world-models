"""Hand-written tic-tac-toe oracle implementing the world_model contract."""

_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # cols
    (0, 4, 8), (2, 4, 6),              # diagonals
]

def initial_state() -> dict:
    return {"board": [0] * 9, "current_player": 1}

def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    return [i for i, c in enumerate(state["board"]) if c == 0]

def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    board[action] = state["current_player"]
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}

def winner(state: dict) -> int:
    b = state["board"]
    for x, y, z in _LINES:
        if b[x] != 0 and b[x] == b[y] == b[z]:
            return b[x]
    return 0

def is_terminal(state: dict) -> bool:
    return winner(state) != 0 or all(c != 0 for c in state["board"])

def returns(state: dict) -> dict:
    w = winner(state)
    if w == 1:
        return {1: 1.0, 2: -1.0}
    if w == 2:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}

RULES_TEXT = """\
This game is tic-tac-toe.
  - board has 9 cells (indices 0..8, row-major over a 3x3 grid): 0 empty, 1 = X, 2 = O.
  - current_player is 1 (X) or 2 (O); players alternate each move, placing their own mark.
  - Action is the cell index 0..8 to place the current player's mark.
  - A player wins with 3 of their marks in a row, column, or diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play tic-tac-toe. The board is a list of 9 cells (0 empty, 1=X, 2=O), "
    "indices 0..8 row-major. A move is the cell index 0..8 to play."
)
