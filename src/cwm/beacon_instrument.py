"""Claim A instrument for Beacon: identical to the true game EXCEPT its inference
function is wrong only at final-round states (status==1) — the deep region D that
competent play reaches but a random-trajectory gate almost never does. There it
returns the FLIPPED opponent type, a singleton inconsistent with the observed
history. On every walk state it equals the truth, so a random-sampled gate (which
dies in the walk) certifies it; yet at the final round the determinized planner acts
on the flipped belief and guesses wrong, losing at play.
"""
import random

from .groundtruth import beacon as B


class BeaconWrongInference:
    def __init__(self, T: int = 8):
        self.T = T
        self._truth = B.make_beacon(T)
        # delegate the deterministic contract surface
        self.safe = self._truth.safe
        self._cp_from_board = self._truth._cp_from_board
        self.initial_state = self._truth.initial_state
        self.initial_states = self._truth.initial_states
        self.initial_state_with = self._truth.initial_state_with
        self.is_terminal = self._truth.is_terminal
        self.legal_actions = self._truth.legal_actions
        self.apply_action = self._truth.apply_action
        self.returns = self._truth.returns
        self.observation = self._truth.observation

    def infer_states(self, obs_board, player):
        inferred = self._truth.infer_states(obs_board, player)
        if obs_board[8] == 1 and len(inferred) == 1:      # final round D: flip
            opp_idx = 3 if player == 1 else 2
            s = list(obs_board)
            s[opp_idx] = 1 - inferred[0]["board"][opp_idx]
            return [{"board": s, "current_player": self._cp_from_board(obs_board)}]
        return inferred


def infoset_key(model, board, player):
    return tuple(model.observation({"board": list(board),
                                    "current_player": player}, player))


def random_reach_final_rate(model, n_games: int, seed: int) -> float:
    rng = random.Random(seed)
    deals = model.initial_states()
    reached = 0
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            if s["board"][8] == 1:                        # entered final round
                reached += 1
                break
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return reached / n_games
