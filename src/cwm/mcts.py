# src/cwm/mcts.py
"""Minimal UCT MCTS over a world-model contract."""
import math
import random

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

def _uct(child, c=1.41):
    if child.visits == 0:
        return float("inf")
    return (child.value / child.visits) + c * math.sqrt(
        math.log(child.parent.visits) / child.visits)

def _rollout(model, state, rng):
    while not model.is_terminal(state):
        state = model.apply_action(state, rng.choice(model.legal_actions(state)))
    return model.returns(state)

def mcts_policy(model, state: dict, n_simulations: int = 200, seed: int = 0) -> int:
    rng = random.Random(seed)
    root = _Node(model, state)
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
