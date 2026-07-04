"""Leduc: is the COMPETENT-relevant info-set subset provably covered at N=8000?

The full-coverage theorem needs N~27k for ALL 576 reachable Leduc info-sets, so it
does not certify N=8000 globally. But Claim A only needs the info-sets COMPETENT
play visits. We compute pi_min over the competent-visited subset (exact pi^rho), and
the resulting sufficient N. Competent = determinized MCTS self-play.

Run: PYTHONPATH=src python scripts/coverage_competent_leduc.py
"""
import math, random
from cwm.groundtruth import leduc_poker as L
from cwm.determinized import determinized_policy


def key(board, player):
    return (player, tuple(L.observation({"board": list(board), "current_player": player}, player)))


def exact_reach():
    deals = L.initial_states(); pc = 1.0/len(deals); reach={}
    def rec(s, prob):
        if L.is_terminal(s): return
        p=s["current_player"]; reach[key(s["board"],p)] = reach.get(key(s["board"],p),0.0)+prob
        legal=L.legal_actions(s)
        for a in legal: rec(L.apply_action(s,a), prob/len(legal))
    for d in deals: rec({"board":list(d["board"]),"current_player":d["current_player"]}, pc)
    return reach


def competent_infosets(n_games, sims, seed):
    rng=random.Random(seed); deals=L.initial_states(); seen=set()
    for i in range(n_games):
        d=deals[rng.randrange(len(deals))]; s={"board":list(d["board"]),"current_player":d["current_player"]}
        while not L.is_terminal(s):
            seen.add(key(s["board"], s["current_player"]))
            a=determinized_policy(L, s, n_determinizations=8, simulations=sims, seed=seed+i*1000)
            if a not in L.legal_actions(s): a=L.legal_actions(s)[0]
            s=L.apply_action(s,a)
    return seen


reach = exact_reach()
comp = competent_infosets(n_games=200, sims=150, seed=0)
comp_reach = {k: reach[k] for k in comp if k in reach}
unreached = [k for k in comp if k not in reach]
assert not unreached, f"competent-visited keys missing from exact reach: {unreached[:3]}"  # silent drop would inflate pi_min
pi_min_c = min(comp_reach.values())
I_c = len(comp_reach)
N_suff = (1.0/pi_min_c)*math.log(I_c/0.05)
fail8000 = sum((1.0-pr)**8000 for pr in comp_reach.values())
print(f"competent-visited non-terminal info-sets: {I_c} (of 576 reachable)", flush=True)
print(f"pi_min over competent subset (exact pi^rho) = {pi_min_c:.4g}", flush=True)
print(f"N_suff (tight, competent subset, delta=0.05) = {N_suff:,.0f}", flush=True)
print(f"N=8000 exact union coverage-failure over competent subset = {fail8000:.4g} "
      f"({'PROVABLY COVERED' if fail8000<0.05 else 'not covered'})", flush=True)
print("DONE", flush=True)
