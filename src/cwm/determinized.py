"""Determinized MCTS for imperfect-information games.

To act from an information set, derive the current player's observation, infer the
full states consistent with it, run perfect-information MCTS on each (treating it
as the true state), and vote. Known caveat: determinization suffers strategy
fusion and is not game-theoretic-optimal; it is a valid, simple planner for
measuring model-induced differences (both sides use the same planner)."""
import random

from .mcts import mcts_policy
from .law import wilson_ci


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


def imperfect_arena(truth, model_a, model_b, simulations: int, n_games: int,
                    seeds: list, n_determinizations=None) -> dict:
    """model_a vs model_b, each planning via determinized_policy on its OWN model,
    refereed by `truth`. Deals sampled from truth.initial_states(); seats alternate.
    Win/tie/lose by net-chip sign (Wilson CI); a_net accumulates net chips."""
    deals = truth.initial_states()
    a_wins = b_wins = ties = 0
    a_net = 0.0
    g = 0
    for sd in seeds:
        rng = random.Random(sd)
        for i in range(n_games):
            deal = deals[rng.randrange(len(deals))]
            s = {"board": list(deal["board"]), "current_player": deal["current_player"]}
            a_is_p1 = (i % 2 == 0)
            move = 0
            while not truth.is_terminal(s):
                p = s["current_player"]
                model = model_a if ((p == 1) == a_is_p1) else model_b
                a = determinized_policy(model, s, n_determinizations=n_determinizations,
                                        simulations=simulations, seed=sd + g * 1000 + move)
                if a not in truth.legal_actions(s):
                    a = truth.legal_actions(s)[0]
                s = truth.apply_action(s, a)
                move += 1
            r = truth.returns(s)
            a_payoff = r[1] if a_is_p1 else r[2]
            a_net += a_payoff
            if a_payoff > 0:
                a_wins += 1
            elif a_payoff < 0:
                b_wins += 1
            else:
                ties += 1
            g += 1
    n = a_wins + b_wins + ties
    point, lo, hi = wilson_ci(a_wins + 0.5 * ties, n)
    return {"a_winrate": point, "lo": lo, "hi": hi, "n": n,
            "a_wins": a_wins, "b_wins": b_wins, "ties": ties, "a_net": a_net}
