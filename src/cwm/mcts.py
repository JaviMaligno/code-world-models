# src/cwm/mcts.py
"""Minimal UCT MCTS over a world-model contract."""
import math
import random
from .world_model import state_to_json

class _Node:
    __slots__ = ("state", "player", "parent", "action", "children",
                 "visits", "value", "untried")
    def __init__(self, model, state, parent=None, action=None):
        self.state = state
        self.player = state["current_player"]
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried = list(model.legal_actions(state))

# Exploration constant. c = 1.41 ≈ √2 is the canonical UCT value from
# Kocsis & Szepesvári (2006): √2 is the constant for which the UCB1 regret bound
# is derived, assuming rewards in [0, 1]. It is the textbook default and was NOT
# tuned for this project — the planner is used as a fixed-strength, reproducible
# instrument (search strength is controlled by the simulation budget, not c), so
# we keep the convention rather than fit it.
#
# Caveat: this repo's `returns` are in {-1, 0, +1}, so the exploitation term
# value/visits lives in [-1, 1] (range 2, not 1). The √2 derivation assumes
# range 1, so the strictly range-calibrated constant here would be ~2√2 ≈ 2.83.
# We deliberately keep c = 1.41 because the reported quantities are empirically
# invariant to the choice at the budgets used (200–600 sims): against a perfect
# tic-tac-toe minimax opponent both c = 1.41 and c = 2√2 lose the same number of
# games, and win rates vs fixed opponents on connect4/beacon are identical under
# both. Trajectories on open games (ttt/connect4/trike) differ — but only by
# selecting among equally-optimal moves — while Beacon, the adversarial gap
# instrument, plays an identical (forced) line under both constants, so the
# headline gap results do not depend on c. See docs/paper/preprint-draft.md §2.5.
def _uct(child, c=1.41):
    if child.visits == 0:
        return float("inf")
    return (child.value / child.visits) + c * math.sqrt(
        math.log(child.parent.visits) / child.visits)

def _rollout(model, state, rng):
    while not model.is_terminal(state):
        state = model.apply_action(state, rng.choice(model.legal_actions(state)))
    return model.returns(state)

def mcts_policy(model, state: dict, n_simulations: int = 200, seed: int = 0,
                visited: set | None = None) -> int:
    rng = random.Random(seed)
    root = _Node(model, state)
    if visited is not None:
        visited.add(state_to_json(state))
    for _ in range(n_simulations):
        node = root
        # Selection
        while not node.untried and node.children:
            node = max(node.children, key=_uct)
        # Expansion
        if node.untried:
            a = rng.choice(node.untried)
            node.untried.remove(a)
            child = _Node(model, model.apply_action(node.state, a),
                          parent=node, action=a)
            node.children.append(child)
            node = child
            if visited is not None:
                visited.add(state_to_json(child.state))
        # Simulation
        result = _rollout(model, node.state, rng)
        # Backpropagation (reward from each node's mover's perspective)
        while node is not None:
            node.visits += 1
            if node.parent is not None:
                node.value += result[node.parent.player]
            node = node.parent
    best = max(root.children, key=lambda n: n.visits)
    return best.action
