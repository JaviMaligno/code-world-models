"""Shared world-model contract and (de)serialization for the sandbox boundary."""
import json

State = dict   # {"board": list[int], "current_player": int (1 or 2)} — board size is game-specific
Action = int   # game-specific (e.g. tic-tac-toe cell 0..8, Connect Four column 0..6)

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


IMPERFECT_CONTRACT_API = CONTRACT_API + """

This is an IMPERFECT-INFORMATION game. The board encodes hidden information.
Additionally implement EXACTLY these signatures:
  def initial_states() -> list[dict]   # every possible initial (post-deal) state
  def observation(state: dict, player: int) -> list[int]   # board as `player` sees it; hidden entries are -1
  def infer_states(observation: list[int], player: int) -> list[dict]  # all full states consistent with the observation

returns may be real-valued NET payoffs (not limited to {-1.0,0.0,1.0}); a positive
value means that player gains that many chips. current_player is derivable from the
public betting history. Every state in infer_states(observation(s,p),p) must map
back to the same observation, and the true state must be included.
"""


def build_imperfect_contract(rules_text: str) -> str:
    return IMPERFECT_CONTRACT_API + "\n\n" + rules_text
