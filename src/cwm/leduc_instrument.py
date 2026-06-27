"""Claim A instrument for Leduc: a model identical to the true game EXCEPT its
inference function is wrong on a competent-play tail (states reached only after a
raise in round 1) that random-play sampling rarely covers. It is membership-correct
where the random gate looks, so it passes the gate, yet misplans where competent
play actually goes — the imperfect-info analogue of the rare-rule instrument.
"""
import random

from .groundtruth import leduc_poker as L
from .determinized import determinized_policy


def _is_tail(board: list) -> bool:
    """A competent-only info-set: round 1 reached via a raise (committeds above the
    ante of 1). Random play rarely raises into round 1, so the gate under-covers it."""
    return board[3] == 1 and (board[4] > 1 or board[5] > 1)


class WrongInference:
    """Delegates the whole contract to leduc_poker, but corrupts infer_states on
    tail info-sets by dropping one consistent opponent assignment."""
    initial_state = staticmethod(L.initial_state)
    initial_states = staticmethod(L.initial_states)
    legal_actions = staticmethod(L.legal_actions)
    apply_action = staticmethod(L.apply_action)
    is_terminal = staticmethod(L.is_terminal)
    returns = staticmethod(L.returns)
    observation = staticmethod(L.observation)

    @staticmethod
    def infer_states(obs_board, player):
        inferred = L.infer_states(obs_board, player)
        if _is_tail(obs_board) and len(inferred) > 1:
            return inferred[:-1]              # drop one consistent state on the tail
        return inferred


def infoset_key(board: list, player: int):
    return tuple(L.observation({"board": list(board), "current_player": player}, player))


def random_infoset_coverage(model, n_games: int, seed: int) -> set:
    rng = random.Random(seed)
    deals = model.initial_states()
    covered = set()
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            covered.add(infoset_key(s["board"], s["current_player"]))
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return covered


def competent_infosets(model, n_games: int, sims: int, seed: int) -> set:
    rng = random.Random(seed)
    deals = model.initial_states()
    visited = set()
    for i in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            visited.add(infoset_key(s["board"], s["current_player"]))
            a = determinized_policy(model, s, n_determinizations=8,
                                    simulations=sims, seed=seed + i * 1000)
            if a not in model.legal_actions(s):
                a = model.legal_actions(s)[0]
            s = model.apply_action(s, a)
    return visited
