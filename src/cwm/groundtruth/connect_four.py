"""Hand-written Connect Four oracle implementing the world_model contract.

board: list[int] length 42, row-major, index = row*7 + col, row 0 = top, row 5 = bottom.
0 empty, 1 and 2 are the players. Action = column 0..6; disc falls to lowest empty row.
"""

ROWS, COLS = 6, 7


def _idx(r: int, c: int) -> int:
    return r * COLS + c


def initial_state() -> dict:
    return {"board": [0] * (ROWS * COLS), "current_player": 1}


def _drop_row(board: list, col: int):
    for r in range(ROWS - 1, -1, -1):      # bottom (row 5) upward
        if board[_idx(r, col)] == 0:
            return r
    return None


def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    return [col for col in range(COLS) if state["board"][_idx(0, col)] == 0]


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    r = _drop_row(board, action)
    board[_idx(r, action)] = state["current_player"]
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}


def winner(state: dict) -> int:
    b = state["board"]
    for r in range(ROWS):
        for col in range(COLS):
            p = b[_idx(r, col)]
            if p == 0:
                continue
            # horizontal →
            if col + 3 < COLS and all(b[_idx(r, col + k)] == p for k in range(4)):
                return p
            # vertical ↓
            if r + 3 < ROWS and all(b[_idx(r + k, col)] == p for k in range(4)):
                return p
            # diagonal ↘
            if r + 3 < ROWS and col + 3 < COLS and all(b[_idx(r + k, col + k)] == p for k in range(4)):
                return p
            # diagonal ↙
            if r + 3 < ROWS and col - 3 >= 0 and all(b[_idx(r + k, col - k)] == p for k in range(4)):
                return p
    return 0


def is_terminal(state: dict) -> bool:
    return winner(state) != 0 or all(cell != 0 for cell in state["board"])


def returns(state: dict) -> dict:
    w = winner(state)
    if w == 1:
        return {1: 1.0, 2: -1.0}
    if w == 2:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}


RULES_TEXT = """\
This game is Connect Four.
  - board has 42 cells representing a 6-row x 7-column grid, row-major:
    index = row*7 + col, with row 0 the TOP row and row 5 the BOTTOM row.
    0 empty, 1 and 2 are the two players' discs.
  - Action is a COLUMN index 0..6. The disc falls to the LOWEST empty row in
    that column (gravity). A column is a legal move only if its top cell
    (row 0) is empty.
  - A player wins with 4 of their discs in a line: horizontal, vertical, or
    either diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play Connect Four on a 6-row by 7-column board (42 cells, row-major, "
    "0 empty, 1 and 2 are the players). A move is a COLUMN number 0..6; your "
    "disc falls to the lowest empty row in that column."
)
