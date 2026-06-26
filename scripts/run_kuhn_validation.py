"""Pipeline validation for the imperfect-info round: synthesize Kuhn (mini) with
rules given, gate it on transitions AND inference, then measure play vs the true
game. Kuhn is famous -> recall expected -> gate-pass and play ~ baseline. This
validates the plumbing; a near-zero gap here is expected, not the result.

Run: PYTHONPATH=src python scripts/run_kuhn_validation.py
"""
import os
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import kuhn_poker as k
from cwm.world_model import build_imperfect_contract
from cwm.trajectories import collect_trajectories
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.gap import contract_divergence, inference_accuracy
from cwm.determinized import imperfect_arena
from cwm.run_gap import _load_module_from_code
import random

provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])
MODEL = os.environ["AZURE_DEPLOYMENT_MINI"]
contract = build_imperfect_contract(k.RULES_TEXT)


def collect_imperfect_trajectories(model, n_games, seed):
    """Random-play transitions starting from random deals (chance handled by
    sampling initial_states)."""
    from cwm.trajectories import Trajectory
    rng = random.Random(seed)
    deals = model.initial_states()
    out = []
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            legal = model.legal_actions(s)
            a = rng.choice(legal)
            nxt = model.apply_action(s, a)
            out.append(Trajectory(state=s, action=a, next_state=nxt,
                                  reward=model.returns(nxt), terminal=model.is_terminal(nxt),
                                  legal_actions=legal))
            s = nxt
    return out


traj = collect_imperfect_trajectories(k, n_games=60, seed=1)
print(f"transitions={len(traj)}", flush=True)
code, _ = synthesize_cwm(provider, MODEL, contract, traj)
refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=6)
print(f"transition gate: accuracy={refined.accuracy:.4f} iters={refined.iterations}", flush=True)

cwm = _load_module_from_code(refined.code)

# sample reachable full states for the inference gate
infer_states_sample = [t.state for t in traj][:40]
inf = inference_accuracy(refined.code, infer_states_sample, k)
print(f"inference gate: observation_rate={inf['observation_rate']:.3f} "
      f"inference_rate={inf['inference_rate']:.3f} n={inf['n']} exec_err={inf['n_exec_errors']}", flush=True)
if inf["examples"]:
    print("  examples:", inf["examples"][:3], flush=True)

# play vs the true game (recall -> expect ~ fair baseline)
fair = imperfect_arena(k, k, k, simulations=200, n_games=200, seeds=[0, 1])
play = imperfect_arena(k, cwm, k, simulations=200, n_games=200, seeds=[0, 1])
print(f"fair (truth-vs-truth): winrate={fair['a_winrate']:.3f} "
      f"CI[{fair['lo']:.3f},{fair['hi']:.3f}] net={fair['a_net']:.1f}", flush=True)
print(f"CWM vs truth:          winrate={play['a_winrate']:.3f} "
      f"CI[{play['lo']:.3f},{play['hi']:.3f}] net={play['a_net']:.1f}", flush=True)
print("DONE", flush=True)
