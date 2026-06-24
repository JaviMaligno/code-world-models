"""Collect random-vs-random trajectories from a world model."""
import random
from dataclasses import dataclass

@dataclass(frozen=True)
class Trajectory:
    state: dict
    action: int
    next_state: dict
    reward: dict
    terminal: bool
    legal_actions: list[int]

def collect_trajectories(model, n_games: int, seed: int) -> list[Trajectory]:
    rng = random.Random(seed)
    out: list = []
    for _ in range(n_games):
        state = model.initial_state()
        while not model.is_terminal(state):
            legal = model.legal_actions(state)
            action = rng.choice(legal)
            nxt = model.apply_action(state, action)
            out.append(Trajectory(
                state=state, action=action, next_state=nxt,
                reward=model.returns(nxt), terminal=model.is_terminal(nxt),
                legal_actions=legal,
            ))
            state = nxt
    return out
