"""Generalized tic-tac-toe (m,n,k) oracle: 6x6 board, 4-in-a-row.

board: list[int] length ROWS*COLS, row-major, index = row*COLS + col.
0 empty, 1 and 2 are the players. Action = empty cell index.
"""

ROWS, COLS, K = 6, 6, 4
_DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))


def _idx(r: int, c: int) -> int:
    return r * COLS + c


def initial_state() -> dict:
    return {"board": [0] * (ROWS * COLS), "current_player": 1}


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
    for r in range(ROWS):
        for c in range(COLS):
            p = b[_idx(r, c)]
            if p == 0:
                continue
            for dr, dc in _DIRS:
                rr, cc = r + (K - 1) * dr, c + (K - 1) * dc
                if 0 <= rr < ROWS and 0 <= cc < COLS and all(
                        b[_idx(r + k * dr, c + k * dc)] == p for k in range(K)):
                    return p
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
This game is generalized tic-tac-toe on a 6x6 board, win with 4 in a row.
  - board has 36 cells (indices 0..35, row-major over a 6x6 grid,
    index = row*6 + col): 0 empty, 1 and 2 are the two players.
  - current_player is 1 or 2; players alternate, placing their own mark in any
    empty cell.
  - Action is the cell index 0..35 to place the current player's mark.
  - A player wins with 4 of their marks in a row, column, or either diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play generalized tic-tac-toe on a 6x6 board (36 cells, row-major, "
    "0 empty, 1 and 2 are the players), winning with 4 in a row. A move is an "
    "empty cell index 0..35.")
