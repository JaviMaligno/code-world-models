"""army5x5a generalized-chess oracle (DeepMind arXiv:2510.04542, Appendix H.5).

board: list[int] length 26. Indices 0..24 are the 5x5 cells (index = row*5 + col,
row 0 = rank A top .. row 4 = rank E bottom, col 0 = file 1 left). Index 25 is the
ply counter (half-moves played, starts at 0). Cell values: 0 empty; player 1:
1 general, 2 infantry, 3 cavalry; player 2: 4 general, 5 infantry, 6 cavalry.
Win by capturing the opponent's general. Action = from*25 + to, or PASS = 625.
"""

SIZE = 5
N = SIZE * SIZE          # 25 cells
PASS = N * N             # 625
MAX_PLIES = 100
MIRROR_PLAYER2 = True

_MOVES = {
    "general":  [(1, 0), (-1, 0), (0, 1), (0, -1), (0, -2), (0, 2)],
    "infantry": [(1, 0), (2, 0), (1, -1), (1, 1), (-1, 0)],
    "cavalry":  [(0, 3), (1, 2), (2, 1), (3, 0)],
}
_KIND = {1: "general", 2: "infantry", 3: "cavalry",
         4: "general", 5: "infantry", 6: "cavalry"}
_OWNER = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2}
_GENERAL_VAL = {1: 1, 2: 4}


def _offsets(value: int):
    offs = _MOVES[_KIND[value]]
    if MIRROR_PLAYER2 and _OWNER[value] == 2:
        return [(-dr, dc) for dr, dc in offs]
    return offs


def initial_state() -> dict:
    board = [0] * N + [0]
    board[0:5] = [3, 2, 1, 2, 3]      # rank A (row 0): player 1
    board[20:25] = [6, 5, 4, 5, 6]    # rank E (row 4): player 2
    return {"board": board, "current_player": 1}


def _piece_dests(board: list, idx: int) -> list:
    value = board[idx]
    r, c = divmod(idx, SIZE)
    dests = []
    for dr, dc in _offsets(value):
        rr, cc = r + dr, c + dc
        if 0 <= rr < SIZE and 0 <= cc < SIZE:
            tgt = rr * SIZE + cc
            if board[tgt] == 0 or _OWNER[board[tgt]] != _OWNER[value]:
                dests.append(tgt)
    return dests


def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    board = state["board"]
    player = state["current_player"]
    actions = []
    for idx in range(N):
        v = board[idx]
        if v != 0 and _OWNER[v] == player:
            for tgt in _piece_dests(board, idx):
                actions.append(idx * N + tgt)
    if not actions:
        actions.append(PASS)
    return actions


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    player = state["current_player"]
    if action != PASS:
        frm, to = divmod(action, N)
        board[to] = board[frm]
        board[frm] = 0
    board[N] += 1
    return {"board": board, "current_player": 2 if player == 1 else 1}


def _general_alive(board: list, player: int) -> bool:
    return _GENERAL_VAL[player] in board[:N]


def is_terminal(state: dict) -> bool:
    board = state["board"]
    if not _general_alive(board, 1) or not _general_alive(board, 2):
        return True
    return board[N] >= MAX_PLIES


def returns(state: dict) -> dict:
    if not is_terminal(state):
        return {1: 0.0, 2: 0.0}
    board = state["board"]
    a1, a2 = _general_alive(board, 1), _general_alive(board, 2)
    if a1 and not a2:
        return {1: 1.0, 2: -1.0}
    if a2 and not a1:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}


RULES_TEXT = """\
This game is 'army5x5a', a generalized-chess variant on a 5x5 board.
  - board has 26 integers: indices 0..24 are the 25 cells (index = row*5 + col,
    row 0 = top rank, row 4 = bottom rank, col 0 = left file); index 25 is the
    number of plies (half-moves) played so far, starting at 0.
  - Cell values: 0 empty; player 1: 1 general, 2 infantry, 3 cavalry;
    player 2: 4 general, 5 infantry, 6 cavalry. current_player is 1 or 2.
  - Each piece type moves by fixed (row, col) offsets (a single jump; intervening
    pieces do not block the path):
      general:  (1,0),(-1,0),(0,1),(0,-1),(0,-2),(0,2)
      infantry: (1,0),(2,0),(1,-1),(1,1),(-1,0)
      cavalry:  (0,3),(1,2),(2,1),(3,0)
    Player 2's pieces use the same offsets with the ROW component negated, so
    infantry advances toward the opponent for both sides.
  - A move must land on the board and not on a friendly piece. Landing on an
    opponent piece captures it (removes it).
  - Action encodes a move as from_index*25 + to_index (0..624). If a player has no
    piece move, the only legal action is PASS = 625.
  - Capturing the opponent's general wins. If the ply counter reaches 100 with both
    generals alive, the game is a draw.
  - Player 1 starts on the top rank (cells 0..4 = 3,2,1,2,3) and player 2 on the
    bottom rank (cells 20..24 = 6,5,4,5,6). current_player starts at 1.
"""

POLICY_DESCRIPTION = (
    "You play 'army5x5a' generalized chess on a 5x5 board. board has 26 ints: "
    "cells 0..24 (0 empty; you may be player 1 with pieces 1/2/3 or player 2 with "
    "4/5/6) and a ply counter at index 25. A move is from_index*25 + to_index, or "
    "625 to pass. Capture the opponent's general (1 for player 1, 4 for player 2).")
