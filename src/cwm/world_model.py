"""Shared world-model contract and (de)serialization for the sandbox boundary."""
import json

State = dict   # {"board": list[int] len 9, "current_player": int}
Action = int   # 0..8

def state_to_json(state: State) -> str:
    return json.dumps(state, sort_keys=True)

def state_from_json(s: str) -> State:
    return json.loads(s)

CONTRACT_API = """\
Implement a deterministic turn-based game world model as Python module-level
functions (pure, no I/O, no globals).

State is a dict: {"board": list[int], "current_player": int} (current_player is 1 or 2).
Action is an int.

Functions to implement EXACTLY these signatures:
  def initial_state() -> dict
  def legal_actions(state: dict) -> list[int]
  def apply_action(state: dict, action: int) -> dict   # returns a NEW state; do not mutate input
  def is_terminal(state: dict) -> bool
  def returns(state: dict) -> dict                       # {1: r1, 2: r2}, each in {-1.0,0.0,1.0}; all 0.0 unless terminal

returns gives +1.0 to the winner, -1.0 to the loser, 0.0/0.0 for a draw or any
non-terminal state. Players are 1 and 2 and alternate.
"""

def build_contract(rules_text: str) -> str:
    return CONTRACT_API + "\n\n" + rules_text
