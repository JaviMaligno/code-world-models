"""Clean inference-ceiling test, on-manifold. Harvest REAL discriminating
transitions (the move into a cap+unequal-material terminal) from flawed-model
self-play — reachable states, not artificial ones (which corrupted synthesis:
large model -> acc 0.004). Then incomplete rules + random + N real discriminating,
synthesized with mini AND large: can either INFER the rule from real examples?
"""
import os, random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess as base, gen_chess_material as mat
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories, Trajectory
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.cost_meter import CostMeter
from cwm.mcts import mcts_policy
from cwm.run_gap import _load_module_from_code, _play_performance

provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])
MINI = os.environ["AZURE_DEPLOYMENT_MINI"]; LARGE = os.environ["AZURE_DEPLOYMENT_LARGE"]
SEED = 1


def material(b):
    return sum(1 for v in b[:25] if v in (1, 2, 3)), sum(1 for v in b[:25] if v in (4, 5, 6))


def harvest(target, max_games=400):
    """Real discriminating transitions: last move of a flawed-self-play game that
    ends at the cap with unequal material. On-manifold by construction."""
    out = []
    for i in range(max_games):
        s = base.initial_state(); prev = None; pa = None
        while not base.is_terminal(s):
            legal = base.legal_actions(s)
            a = mcts_policy(base, s, n_simulations=200, seed=i * 1000 + s["board"][25])
            prev, pa = s, a
            s = base.apply_action(s, a)
        nb = s["board"]
        if nb[25] >= mat.MAX_PLIES:
            p1, p2 = material(nb)
            if p1 != p2 and 1 in nb[:25] and 4 in nb[:25]:
                out.append(Trajectory(state=prev, action=pa, next_state=s,
                                      reward=mat.returns(s), terminal=True,
                                      legal_actions=mat.legal_actions(prev)))
        if len(out) >= target:
            break
    return out


def run(model_name, model, traj, label):
    meter = CostMeter()
    contract = build_contract(base.RULES_TEXT)  # incomplete
    code, u = synthesize_cwm(provider, model, contract, traj); meter.add(model_name, u)
    refined = refine_cwm(provider, model, contract, code, traj, max_iters=12)
    for uu in refined.usages:
        meter.add(model_name, uu)
    cwm = _load_module_from_code(refined.code)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[6] = 3; cells[22] = 4
    rs = {"board": cells + [mat.MAX_PLIES], "current_player": 1}
    try:
        rr = cwm.returns(rs); learned = (rr.get(1) == 1.0 and rr.get(2) == -1.0)
    except Exception as e:
        learned = f"err {e!r}"
    play = _play_performance(mat, cwm, sims=400, n_games=40, seed=SEED)
    print(f"  [{label}] acc={refined.accuracy:.4f} iters={refined.iterations} "
          f"rule_learned={learned} winrate={play['cwm_winrate']:.2f} "
          f"({play['cwm_wins']}W/{play['draws']}D/{play['truth_wins']}L) cost=${meter.total_usd():.3f}",
          flush=True)


random_traj = collect_trajectories(mat, n_games=40, seed=SEED)
print("harvesting real discriminating transitions (CPU)...", flush=True)
disc = harvest(target=60)
print(f"harvested {len(disc)} REAL discriminating transitions", flush=True)
traj = disc + random_traj   # discriminating first

print("\n=== inference ceiling, on-manifold (incomplete rules + real discriminating) ===", flush=True)
run("mini", MINI, traj, f"MINI + {len(disc)} real")
run("large", LARGE, traj, f"LARGE + {len(disc)} real")
