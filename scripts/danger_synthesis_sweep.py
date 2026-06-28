"""The danger law on the ACTUAL synthesis pipeline (not the proxy).

Synthesize a CWM from the INCOMPLETE army5x5a rules (base, no material-at-cap
clause) + N true-game (army5x5a + material) trajectories, with refinement drawing
FRESH trajectories each iteration (resample_fn — the fixed, non-reusing refiner).
Then test whether the synthesized CWM is rule-blind: does its returns() give a draw
on cap + unequal-material states where the truth gives a material winner?

Predicted rule-blind fraction if the LLM perfectly learns the rule whenever it
appears: (1-r)^N (r = material-terminal rarity = 0.025) — the identifiability event.
If the LLM does not reliably learn even when present (§5), the fraction is HIGHER.

Run: PYTHONPATH=src python3.12 scripts/danger_synthesis_sweep.py [mini|large]
"""
import os, sys, random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess_material as truth
from cwm.groundtruth import gen_chess as base
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.run_gap import _load_module_from_code

SIZE = sys.argv[1] if len(sys.argv) > 1 else "mini"
MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[SIZE]]
contract = build_contract(base.RULES_TEXT)   # INCOMPLETE rules
provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])

R = 0.025
N_GRID = [40, 120, 200]
SEEDS = list(range(6))


def rule_region_states():
    """Cap states (ply=100), both generals alive, unequal material -> truth gives a
    material winner; a rule-blind CWM gives a draw."""
    S = []
    b = [0]*26; b[0]=1; b[24]=4; b[5]=2;  b[25]=100; S.append({"board": b, "current_player": 1})  # p1 +infantry
    b = [0]*26; b[2]=1; b[22]=4; b[10]=3; b[25]=100; S.append({"board": b, "current_player": 2})  # p1 +cavalry
    b = [0]*26; b[0]=1; b[24]=4; b[20]=5; b[25]=100; S.append({"board": b, "current_player": 1})  # p2 +infantry
    return S


TEST = rule_region_states()
TRUTH_RET = [truth.returns(s) for s in TEST]
assert all(r != {1: 0.0, 2: 0.0} for r in TRUTH_RET), "test states must be decisive"


def is_rule_blind(code):
    """True if the CWM fails to give the material winner on the cap test states."""
    try:
        m = _load_module_from_code(code)
        for s, tr in zip(TEST, TRUTH_RET):
            if m.returns({"board": list(s["board"]), "current_player": s["current_player"]}) != tr:
                return True   # disagrees with truth on a rule-region state -> rule-blind
        return False
    except Exception:
        return True


def run_seed(N, seed):
    traj = collect_trajectories(truth, n_games=N, seed=seed)
    code, _ = synthesize_cwm(provider, MODEL, contract, traj)
    refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=6,
                         resample_fn=lambda it: collect_trajectories(truth, n_games=N, seed=seed + 1000*it))
    blind = is_rule_blind(refined.code)
    return blind, refined.accuracy, refined.iterations, refined.n_samples


def main():
    print(f"synth size={SIZE}, r={R}", flush=True)
    for N in N_GRID:
        blind = 0
        for seed in SEEDS:
            b, acc, iters, nsamp = run_seed(N, seed)
            blind += int(b)
            print(f"  N={N} seed={seed}: rule_blind={b} gate_acc={acc:.3f} iters={iters} n_samples={nsamp}", flush=True)
        frac = blind / len(SEEDS)
        print(f"=> N={N}: rule_blind {blind}/{len(SEEDS)} = {frac:.3f}   "
              f"(identifiability prediction (1-r)^N = {(1-R)**N:.3f})", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
