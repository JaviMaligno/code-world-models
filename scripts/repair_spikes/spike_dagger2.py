"""Proper iterative DAgger, fixed: collect the GAME-PATH states the current
(flawed) CWM visits in self-play (these reach the cap), not the MCTS tree-
expansion nodes (which are opening-biased and flooded the cap). The rule-blind
model leaves cap+unequal-material 6/20 vs competent's 2/20 -> 3x more signal on
its OWN distribution, exactly DAgger's premise.

Each round: flawed-model self-play -> collect path states -> label with truth ->
aggregate (discriminating first) -> re-synthesize -> report rule + play winrate.
"""
import os, random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess, gen_chess_material as mat
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories, Trajectory
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.mcts import mcts_policy
from cwm.run_gap import _load_module_from_code, _play_performance

provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])
MODEL = os.environ["AZURE_DEPLOYMENT_MINI"]
contract = build_contract(gen_chess.RULES_TEXT)   # INCOMPLETE
SEED = 1


def material(b):
    return sum(1 for v in b[:25] if v in (1, 2, 3)), sum(1 for v in b[:25] if v in (4, 5, 6))


def is_disc(t):
    nb = t.next_state["board"]
    if nb[25] < mat.MAX_PLIES:
        return False
    p1, p2 = material(nb)
    return p1 != p2 and 1 in nb[:25] and 4 in nb[:25]


def path_trajectories(cwm, n_games, sims, seed):
    """Self-play the flawed CWM; record every game-path transition, labelled by the
    TRUTH (ground-truth dynamics). These reach the cap, surfacing the rule."""
    out = []
    for i in range(n_games):
        s = cwm.initial_state(); m = 0
        # use the FLAWED model to choose moves (its distribution), TRUTH to label
        while not cwm.is_terminal(s) and not mat.is_terminal(s):
            legal = mat.legal_actions(s)
            a = mcts_policy(cwm, s, n_simulations=sims, seed=seed + i * 1000 + m)
            if a not in legal:
                a = legal[0]
            nxt = mat.apply_action(s, a)
            out.append(Trajectory(state=s, action=a, next_state=nxt, reward=mat.returns(nxt),
                                  terminal=mat.is_terminal(nxt), legal_actions=legal))
            s = nxt; m += 1
    return out


def synth_eval(traj, label, max_iters=8):
    code, _ = synthesize_cwm(provider, MODEL, contract, traj)
    refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=max_iters)
    cwm = _load_module_from_code(refined.code)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[6] = 3; cells[22] = 4
    rs = {"board": cells + [mat.MAX_PLIES], "current_player": 1}
    try:
        rr = cwm.returns(rs); learned = (rr.get(1) == 1.0 and rr.get(2) == -1.0)
    except Exception as e:
        learned = f"err {e!r}"
    play = _play_performance(mat, cwm, sims=400, n_games=30, seed=SEED)
    print(f"  [{label}] acc={refined.accuracy:.4f} iters={refined.iterations} "
          f"rule_learned={learned} winrate={play['cwm_winrate']:.2f} "
          f"({play['cwm_wins']}W/{play['draws']}D/{play['truth_wins']}L)", flush=True)
    return cwm


random_traj = collect_trajectories(mat, n_games=40, seed=SEED)
print(f"random transitions={len(random_traj)}", flush=True)
cwm = synth_eval(random_traj, "round 0 (random only)")
# TRUE DAgger: the dataset AGGREGATES across rounds (Ross et al. 2011). An audit
# found an earlier version rebuilt the dataset from only the current round's
# path data (and duplicated disc); that version generated the original table row.
agg_disc, agg_rest = [], []
for k in range(1, 4):
    path = path_trajectories(cwm, n_games=25, sims=300, seed=SEED + 100 * k)
    disc = [t for t in path if is_disc(t)]
    rest = [t for t in path if not is_disc(t)]
    agg_disc += disc
    agg_rest += random.Random(k).sample(rest, min(200, len(rest)))
    dataset = agg_disc + random_traj + agg_rest   # discriminating first (synthesis 30-cap + refiner failures see them)
    print(f"  round {k}: path_transitions={len(path)} new_disc={len(disc)} "
          f"aggregated: disc={len(agg_disc)} total={len(dataset)}", flush=True)
    cwm = synth_eval(dataset, f"round {k}")
