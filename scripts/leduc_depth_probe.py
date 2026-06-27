"""De-risk probe: does betting DEPTH create an inference coverage gap?

The coverage bound predicts a gap appears once b^{d_max} >> N. Leduc's depth is set
by the per-round raise cap. apply_action has no cap guard (only legal_actions caps),
so a thin wrapper that raises the cap deepens the betting tree without touching the
oracle. We sweep cap in {2,4,6} at fixed random-gate size N and ask: do competent
(determinized-MCTS) info-sets appear that random play of size N never sampled?

If YES and growing with cap -> the deep-Leduc path to a positive Claim A is real.
If NO even at cap 6 -> competent play folds out of deep lines too; need large-branching instead.

Run: PYTHONPATH=src python scripts/leduc_depth_probe.py
"""
import random

from cwm.groundtruth import leduc_poker as L
from cwm.determinized import determinized_policy
from cwm.leduc_instrument import infoset_key

RANDOM_N = 8000
COMPETENT_N = 100
SIMS = 150
N_DET = 8


class CapLeduc:
    """Leduc with a configurable per-round raise cap (delegates everything else)."""
    def __init__(self, cap):
        self.cap = cap
        self.initial_state = L.initial_state
        self.initial_states = L.initial_states
        self.apply_action = L.apply_action      # no cap guard inside -> safe
        self.is_terminal = L.is_terminal
        self.returns = L.returns
        self.observation = L.observation
        self.infer_states = L.infer_states

    def legal_actions(self, state):
        if L.is_terminal(state):
            return []
        b = state["board"]
        outstanding = b[4] != b[5]
        acts = [0, 1] if outstanding else [1]
        if b[6] < self.cap:
            acts.append(2)
        return acts


def n_consistent(obs_tuple, player):
    return len(L.infer_states(list(obs_tuple), player))


def _player_of(obs_tuple):
    return 1 if obs_tuple[7] % 2 == 0 else 2


def random_cover(model, n_games, seed):
    rng = random.Random(seed)
    deals = model.initial_states()
    seen = set()
    depth = 0
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        steps = 0
        while not model.is_terminal(s):
            seen.add(infoset_key(s["board"], s["current_player"]))
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
            steps += 1
        depth = max(depth, steps)
    return seen, depth


def competent_visits(model, n_games, seed):
    rng = random.Random(seed)
    deals = model.initial_states()
    visits = {}
    depth = 0
    for i in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        steps = 0
        while not model.is_terminal(s):
            visits[infoset_key(s["board"], s["current_player"])] = \
                visits.get(infoset_key(s["board"], s["current_player"]), 0) + 1
            a = determinized_policy(model, s, n_determinizations=N_DET,
                                    simulations=SIMS, seed=seed + i * 1000)
            if a not in model.legal_actions(s):
                a = model.legal_actions(s)[0]
            s = model.apply_action(s, a)
            steps += 1
        depth = max(depth, steps)
    return visits, depth


def main():
    for cap in (2, 4, 6):
        m = CapLeduc(cap)
        rand_set, rdepth = random_cover(m, RANDOM_N, seed=0)
        comp, cdepth = competent_visits(m, COMPETENT_N, seed=0)
        comp_total = sum(comp.values())
        uncovered = {k: c for k, c in comp.items()
                     if k not in rand_set and n_consistent(k, _player_of(k)) > 1}
        unc_mass = sum(uncovered.values())
        print(f"cap={cap}: random_infosets={len(rand_set)} (max_depth {rdepth}) | "
              f"competent_infosets={len(comp)} (max_depth {cdepth}) | "
              f"UNCOVERED inference-relevant: {len(uncovered)} distinct, "
              f"{unc_mass}/{comp_total} = {unc_mass/comp_total:.4f} of competent visits",
              flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
