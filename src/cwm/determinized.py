"""Determinized MCTS for imperfect-information games.

To act from an information set, derive the current player's observation, infer the
full states consistent with it, run perfect-information MCTS on each (treating it
as the true state), and vote. Known caveat: determinization suffers strategy
fusion and is not game-theoretic-optimal; it is a valid, simple planner for
measuring model-induced differences (both sides use the same planner)."""
import random

from .mcts import mcts_policy


def determinized_policy(model, state: dict, n_determinizations=None,
                        simulations: int = 200, seed: int = 0) -> int:
    player = state["current_player"]
    obs = model.observation(state, player)
    dets = model.infer_states(obs, player)
    if n_determinizations is not None and len(dets) > n_determinizations:
        rng = random.Random(seed)
        dets = rng.sample(dets, n_determinizations)
    votes: dict = {}
    for i, d in enumerate(dets):
        a = mcts_policy(model, d, n_simulations=simulations, seed=seed + i)
        votes[a] = votes.get(a, 0) + 1
    # deterministic tie-break: highest votes, then smallest action
    return max(sorted(votes), key=lambda a: votes[a])
