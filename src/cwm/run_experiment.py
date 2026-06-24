# src/cwm/run_experiment.py
"""End-to-end MVP run: synthesize a tic-tac-toe CWM with a small model, refine to
accuracy 1.0, then play CWM+MCTS vs a large-model baseline. Prints a JSON report.

Usage:
    python -m cwm.run_experiment --games 20 --synth-size nano --baseline-size large
"""
import argparse
import json
import os
import sys
import types
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .world_model import CONTRACT_TEXT
from .groundtruth import tictactoe as g
from .trajectories import collect_trajectories
from .llm.azure_openai import AzureOpenAIProvider
from .synthesizer import synthesize_cwm
from .refiner import refine_cwm
from .mcts import mcts_policy
from .baseline import baseline_policy
from .arena import run_arena
from .cost_meter import CostMeter

_DEPLOY_ENV = {"large": "AZURE_DEPLOYMENT_LARGE",
               "mini": "AZURE_DEPLOYMENT_MINI",
               "nano": "AZURE_DEPLOYMENT_NANO"}

def _load_module_from_code(code: str) -> types.ModuleType:
    mod = types.ModuleType("synth_cwm")
    exec(compile(code, "<synth_cwm>", "exec"), mod.__dict__)
    return mod

def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--synth-size", default="nano", choices=list(_DEPLOY_ENV))
    ap.add_argument("--baseline-size", default="large", choices=list(_DEPLOY_ENV))
    ap.add_argument("--train-games", type=int, default=20)
    ap.add_argument("--simulations", type=int, default=300)
    args = ap.parse_args(argv)

    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )
    synth_model = os.environ[_DEPLOY_ENV[args.synth_size]]
    baseline_model = os.environ[_DEPLOY_ENV[args.baseline_size]]
    meter = CostMeter()

    # 1. Collect trajectories from the oracle
    traj = collect_trajectories(g, n_games=args.train_games, seed=0)

    # 2. Synthesize + 3. refine to accuracy 1.0
    code, usage = synthesize_cwm(provider, synth_model, CONTRACT_TEXT, traj)
    meter.add(args.synth_size, usage)
    refined = refine_cwm(provider, synth_model, CONTRACT_TEXT, code, traj)
    for u in refined.usages:
        meter.add(args.synth_size, u)

    # accuracy is correct/total computed from integer sandbox counts, so an exact 1.0 is expected on success
    if refined.accuracy < 1.0:
        print(json.dumps({"error": "synthesis did not reach accuracy 1.0",
                          "accuracy": refined.accuracy,
                          "iterations": refined.iterations}, indent=2))
        return 1

    cwm = _load_module_from_code(refined.code)

    # 4. Build agents. CWM+MCTS plans on the synthesized model.
    def cwm_agent(state, legal):
        return mcts_policy(cwm, state, n_simulations=args.simulations, seed=0)

    def baseline_agent(state, legal):
        action, u = baseline_policy(provider, baseline_model, state, legal)
        meter.add(args.baseline_size, u)
        return action

    # 5. Arena
    arena = run_arena(g, cwm_agent=cwm_agent, baseline_agent=baseline_agent,
                      n_games=args.games, seed=100)

    per_game_baseline_usd = meter.by_role.get(args.baseline_size, 0.0) / max(1, arena.games)
    report = {
        "synth_size": args.synth_size,
        "baseline_size": args.baseline_size,
        "refinement_iterations": refined.iterations,
        "transition_accuracy": refined.accuracy,
        "arena": asdict(arena),
        "cost_usd_by_role": meter.by_role,
        "cost_usd_total": meter.total_usd(),
        "extrapolation_note": (
            f"baseline ~${per_game_baseline_usd:.4f}/game; "
            f"synthesis is one-off ~${meter.by_role.get(args.synth_size, 0.0):.4f}"
        ),
    }
    out = json.dumps(report, indent=2)
    print(out)
    Path("results").mkdir(exist_ok=True)
    Path(f"results/tictactoe_{args.synth_size}_vs_{args.baseline_size}.json").write_text(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
