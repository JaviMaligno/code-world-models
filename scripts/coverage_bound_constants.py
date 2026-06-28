"""Tighten the coverage bound: enumerate reachable info-sets and their EXACT reach
probabilities under uniform-random play, for Kuhn and Leduc, then compute a concrete
sufficient gate size N.

Two bounds, reported side by side:
  (loose) worst-case-depth:  pi^rho(I) >= p_chance * b^{-d_max}  -> N >= b^{d_max} p_chance^{-1} ln(|I|/delta)
  (tight) measured minimum:  pi_min = min_I pi^rho(I) (exact)    -> N >= pi_min^{-1} ln(|I|/delta)
Coverage-failure target delta = 0.05. Compare to the N actually used.

Run: PYTHONPATH=src python scripts/coverage_bound_constants.py
"""
import math
from cwm.groundtruth import kuhn_poker as kuhn
from cwm.groundtruth import leduc_poker as leduc


def infoset_key(model, board, player):
    return (player, tuple(model.observation({"board": list(board), "current_player": player}, player)))


def reach_probs(model):
    """Exact pi^rho(I) over reachable non-terminal player info-sets, uniform-random
    play, chance = uniform over initial_states()."""
    deals = model.initial_states()
    pchance = 1.0 / len(deals)
    reach = {}   # infoset -> probability
    bmax = 0
    dmax = 0

    def rec(state, prob, depth):
        nonlocal bmax, dmax
        if model.is_terminal(state):
            return
        p = state["current_player"]
        k = infoset_key(model, state["board"], p)
        reach[k] = reach.get(k, 0.0) + prob
        legal = model.legal_actions(state)
        bmax = max(bmax, len(legal))
        dmax = max(dmax, depth + 1)
        for a in legal:
            rec(model.apply_action(state, a), prob * (1.0 / len(legal)), depth + 1)

    for d in deals:
        rec({"board": list(d["board"]), "current_player": d["current_player"]}, pchance, 0)
    return reach, pchance, bmax, dmax


def analyze(name, model, N_used, delta=0.05):
    reach, pchance, b, dmax = reach_probs(model)
    I = len(reach)
    pi_min = min(reach.values())
    loose_per = pchance * (b ** (-dmax))
    N_loose = (1.0 / loose_per) * math.log(I / delta)
    N_tight = (1.0 / pi_min) * math.log(I / delta)
    # actual coverage-failure prob at N_used using exact reach probs
    fail = sum((1.0 - pr) ** N_used for pr in reach.values())
    print(f"=== {name} ===", flush=True)
    print(f"  reachable non-terminal info-sets |I| = {I}", flush=True)
    print(f"  b = {b}, d_max = {dmax}, p_chance = {pchance:.4g} (1/{len(model.initial_states())} deals)", flush=True)
    print(f"  pi_min (exact) = {pi_min:.4g};  worst-case-depth per-I bound = {loose_per:.4g}", flush=True)
    print(f"  N_suff (loose, b^d) = {N_loose:,.0f}   [delta={delta}]", flush=True)
    print(f"  N_suff (tight, pi_min) = {N_tight:,.0f}   [delta={delta}]", flush=True)
    print(f"  N used = {N_used}: exact union coverage-failure bound = {fail:.4g} "
          f"({'COVERED' if fail < delta else 'NOT covered by bound'})", flush=True)
    print("", flush=True)


analyze("Kuhn", kuhn, N_used=80)      # Kuhn gate sample in validation
analyze("Leduc", leduc, N_used=8000)  # Leduc coverage measurement
print("DONE", flush=True)
