"""Trike oracle (Alek Erickson, 2020) on a triangular board, side 6 (21 cells).

Cells are numbered row by row from the top: row r (0..SIDE-1) has r+1 cells; cell
(r,c) with 0<=c<=r has index r*(r+1)//2 + c. Cell values: 0 empty; 1 player-1
disc; 2 player-2 disc; 3 player-1 disc with the pawn; 4 player-2 disc with the
pawn; 5 the neutral pawn on its start cell; 6 a blocked, uncolored cell. Action is
the destination cell index for the shared pawn's slide.
"""

SIDE = 6
_CELLS = [(r, c) for r in range(SIDE) for c in range(r + 1)]
_INDEX = {rc: i for i, rc in enumerate(_CELLS)}
NCELLS = len(_CELLS)            # 21
START_CELL = _INDEX[(4, 2)]    # 12
_DIRS = [(0, 1), (0, -1), (1, 1), (-1, -1), (1, 0), (-1, 0)]


def _in_board(r: int, c: int) -> bool:
    return 0 <= r < SIDE and 0 <= c <= r


def _pawn_cell(board: list) -> int:
    for i, v in enumerate(board):
        if v in (3, 4, 5):
            return i
    return -1


def initial_state() -> dict:
    board = [0] * NCELLS
    board[START_CELL] = 5
    return {"board": board, "current_player": 1}


def _legal_dests(board: list) -> list:
    pawn = _pawn_cell(board)
    r, c = _CELLS[pawn]
    dests = []
    for dr, dc in _DIRS:
        rr, cc = r + dr, c + dc
        while _in_board(rr, cc) and board[_INDEX[(rr, cc)]] == 0:
            dests.append(_INDEX[(rr, cc)])
            rr, cc = rr + dr, cc + dc
    return sorted(dests)


def legal_actions(state: dict) -> list[int]:
    return _legal_dests(state["board"])


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    player = state["current_player"]
    pawn = _pawn_cell(board)
    board[pawn] = {3: 1, 4: 2, 5: 6}[board[pawn]]
    board[action] = 3 if player == 1 else 4
    return {"board": board, "current_player": 2 if player == 1 else 1}


def is_terminal(state: dict) -> bool:
    return len(_legal_dests(state["board"])) == 0


def _neighbors(idx: int) -> list:
    r, c = _CELLS[idx]
    out = []
    for dr, dc in _DIRS:
        rr, cc = r + dr, c + dc
        if _in_board(rr, cc):
            out.append(_INDEX[(rr, cc)])
    return out


def returns(state: dict) -> dict:
    if not is_terminal(state):
        return {1: 0.0, 2: 0.0}
    board = state["board"]
    pawn = _pawn_cell(board)
    cells = [pawn] + _neighbors(pawn)
    p1 = sum(1 for i in cells if board[i] in (1, 3))
    p2 = sum(1 for i in cells if board[i] in (2, 4))
    if p1 > p2:
        return {1: 1.0, 2: -1.0}
    if p2 > p1:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}


RULES_TEXT = """\
This game is Trike, on a triangular board with side 6 (21 cells).
  - Cells are numbered row by row from the top: row r (0..5) has r+1 cells; cell
    (r,c) with 0<=c<=r has index r*(r+1)//2 + c. board has 21 integers.
  - Cell values: 0 empty; 1 player-1 disc; 2 player-2 disc; 3 player-1 disc with
    the pawn on it; 4 player-2 disc with the pawn; 5 the neutral pawn on its
    (uncolored) start cell; 6 a blocked, uncolored cell. A cell is occupied if its
    value is not 0. Exactly one cell holds the pawn (value 3, 4, or 5).
  - There is one shared pawn. It starts (value 5) on the central cell, index 12
    (cell (4,2)). current_player is 1 or 2 and starts at 1.
  - Each cell has up to 6 neighbors along three axes, given by the (row,col)
    offsets (0,+1),(0,-1),(+1,+1),(-1,-1),(+1,0),(-1,0) that stay in the triangle.
  - A turn: slide the pawn from its current cell along ONE axis over consecutive
    EMPTY cells (it cannot pass over or stop on an occupied cell) and stop on any
    empty cell reached. The vacated cell keeps its disc color (3->1, 4->2) or
    becomes blocked-uncolored if it was the neutral start (5->6); the destination
    becomes the current player's disc-with-pawn (3 if player 1, else 4).
  - Action is the destination cell index. legal_actions lists every empty cell
    reachable from the pawn along the three axes.
  - The game ends when the player to move has no legal slide (the pawn is
    surrounded). The winner has the majority of their discs among the pawn's cell
    and its neighbors (player-1 cells are 1 or 3, player-2 cells are 2 or 4);
    equal counts is a draw.
"""

POLICY_DESCRIPTION = (
    "You play Trike on a triangular board of 21 cells (side 6). A shared pawn "
    "slides in a straight line over empty cells; you color the destination. A "
    "move is the destination cell index. When the pawn is trapped, the majority "
    "of discs touching it (and the pawn's own cell) wins.")
