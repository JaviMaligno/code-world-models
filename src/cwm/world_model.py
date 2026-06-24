"""Shared world-model contract and (de)serialization for the sandbox boundary."""
import json

State = dict   # {"board": list[int] len 9, "current_player": int}
Action = int   # 0..8

def state_to_json(state: State) -> str:
    return json.dumps(state, sort_keys=True)

def state_from_json(s: str) -> State:
    return json.loads(s)

CONTRACT_TEXT = """\
Implement a deterministic tic-tac-toe world model as Python module-level functions.

State is a dict: {"board": [int]*9, "current_player": int}.
  - board cells: 0 = empty, 1 = X, 2 = O, indexed 0..8 row-major.
  - current_player: 1 or 2 (player to move).
Action is an int 0..8 (the cell index to play).

Functions to implement EXACTLY these signatures (pure, no I/O, no globals):
  def initial_state() -> dict
  def legal_actions(state: dict) -> list[int]
  def apply_action(state: dict, action: int) -> dict   # returns a NEW state; do not mutate input
  def is_terminal(state: dict) -> bool
  def returns(state: dict) -> dict                       # {1: r1, 2: r2}, each in {-1.0,0.0,1.0}; all 0.0 unless terminal

Rules: players alternate; a player wins with 3 in a row/column/diagonal; the
board full with no winner is a draw. returns gives +1.0 to the winner, -1.0 to
the loser, 0.0/0.0 for a draw or any non-terminal state.
"""
