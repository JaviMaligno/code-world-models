# src/cwm/run_gap.py
"""Measure the verified-vs-correct gap. For each synthesis seed: synthesize +
refine a CWM to gate accuracy 1.0, then compare it against the ground truth on
three state distributions — D_gate (random-trajectory states the gate used),
D_cwm (states MCTS expands planning on the CWM), and D_truth (states MCTS expands
planning on the ground truth). Headline gap = agreement(D_gate) - agreement(D_cwm).

Usage:
    python -m cwm.run_gap --game army5x5a --synth-size mini --synth-seeds 5
"""
import argparse
import json
import os
import sys
import types
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .games import GAMES
from .world_model import build_contract, CONTRACT_API
from .trajectories import collect_trajectories
from .llm.azure_openai import AzureOpenAIProvider
from .synthesizer import synthesize_cwm
from .refiner import refine_cwm
from .gap import collect_visited_states, contract_divergence
from .mcts import mcts_policy
from .arena import run_arena
from .cost_meter import CostMeter

_DEPLOY_ENV = {"large": "AZURE_DEPLOYMENT_LARGE",
               "mini": "AZURE_DEPLOYMENT_MINI",
               "nano": "AZURE_DEPLOYMENT_NANO"}


def _load_module_from_code(code: str) -> types.ModuleType:
    mod = types.ModuleType("synth_cwm")
    exec(compile(code, "<synth_cwm>", "exec"), mod.__dict__)
    return mod


def aggregate_gap(per_seed: list) -> dict:
    def _agg(key):
        vals = [r[key] for r in per_seed if key in r]
        n = len(vals)
        return n, (sum(vals) / n if n else 0.0), (min(vals) if n else 0.0), (max(vals) if n else 0.0)

    n, gmean, gmin, gmax = _agg("gap")
    _, tmean, tmin, tmax = _agg("gap_truth")
    # Play-performance: win rate of the CWM+MCTS agent vs a ground-truth+MCTS agent
    # in the true game, averaged over scored seeds that carry a play result.
    wr = [r["play"]["cwm_winrate"] for r in per_seed
          if "play" in r and "cwm_winrate" in r.get("play", {})]
    nw = len(wr)
    out = {"n_seeds": n,
           "gap_mean": gmean, "gap_min": gmin, "gap_max": gmax,
           "gap_truth_mean": tmean, "gap_truth_min": tmin, "gap_truth_max": tmax}
    if nw:
        out["play_n"] = nw
        out["cwm_winrate_mean"] = sum(wr) / nw
        out["cwm_winrate_min"] = min(wr)
        out["cwm_winrate_max"] = max(wr)
    return out


def _play_performance(truth_module, cwm_module, sims: int, n_games: int, seed: int) -> dict:
    """Arena in the TRUE game: a CWM+MCTS agent (plans on the synthesized model)
    vs a ground-truth+MCTS agent. A CWM that omits a pivotal rule misplays and
    loses here even if its state-prediction accuracy is ~1.0."""
    def agent_for(model, base):
        counter = {"n": 0}
        def agent(state, legal):
            counter["n"] += 1
            return mcts_policy(model, state, n_simulations=sims, seed=base + counter["n"])
        return agent

    arena = run_arena(truth_module,
                      cwm_agent=agent_for(cwm_module, seed + 1),
                      baseline_agent=agent_for(truth_module, seed + 100_000),
                      n_games=n_games, seed=seed + 2000)
    games = arena.games
    return {"cwm_wins": arena.cwm_wins, "truth_wins": arena.baseline_wins,
            "draws": arena.draws, "cwm_illegal": arena.cwm_illegal,
            "cwm_winrate": (arena.cwm_wins + 0.5 * arena.draws) / games if games else 0.0}


def main(argv=None):
    load_dotenv(override=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="gen_tictactoe", choices=list(GAMES))
    ap.add_argument("--synth-size", default="mini", choices=list(_DEPLOY_ENV))
    ap.add_argument("--synth-seeds", type=int, default=5)
    ap.add_argument("--selfplay-games", type=int, default=20)
    ap.add_argument("--simulations", type=int, default=300)
    ap.add_argument("--train-games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--visited-cap", type=int, default=4000,
                    help="max states per visited distribution (bounds sandbox cost)")
    ap.add_argument("--no-rules", action="store_true",
                    help="pure inference: synthesize from trajectories only, "
                         "withholding RULES_TEXT (generic CONTRACT_API only)")
    ap.add_argument("--play-games", type=int, default=0,
                    help="if >0, also measure play performance: CWM+MCTS vs "
                         "ground-truth+MCTS in the true game, this many games")
    args = ap.parse_args(argv)

    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )
    synth_model = os.environ[_DEPLOY_ENV[args.synth_size]]
    spec = GAMES[args.game]
    g = spec.module
    # Pure-inference mode withholds the game's rules so the model must infer the
    # dynamics from trajectories alone — the clean test for the coverage gap.
    contract = CONTRACT_API if args.no_rules else build_contract(spec.rules_text)
    meter = CostMeter()

    # D_truth depends only on the ground truth; compute once and reuse.
    truth_states = collect_visited_states(
        g, n_games=args.selfplay_games, simulations=args.simulations,
        seed=args.seed, cap=args.visited_cap)

    per_seed = []
    for s in range(args.synth_seeds):
        seed = args.seed + s
        traj = collect_trajectories(g, n_games=args.train_games, seed=seed)
        code, usage = synthesize_cwm(provider, synth_model, contract, traj)
        meter.add(args.synth_size, usage)
        refined = refine_cwm(provider, synth_model, contract, code, traj)
        for u in refined.usages:
            meter.add(args.synth_size, u)
        if refined.accuracy < 1.0:
            per_seed.append({"seed": seed, "skipped": "gate<1.0",
                             "accuracy": refined.accuracy})
            continue
        cwm = _load_module_from_code(refined.code)
        # The synthesized CWM is untrusted code run in-process for MCTS; it can pass
        # the gate yet raise on an out-of-distribution state MCTS reaches. Contain
        # such a crash to this seed instead of killing the whole run.
        try:
            gate_states = [t.state for t in traj]
            cwm_states = collect_visited_states(
                cwm, n_games=args.selfplay_games, simulations=args.simulations,
                seed=seed, cap=args.visited_cap)
            d_gate = contract_divergence(refined.code, gate_states, g)
            d_cwm = contract_divergence(refined.code, cwm_states, g)
            d_truth = contract_divergence(refined.code, truth_states, g)
        except Exception as e:
            per_seed.append({"seed": seed, "skipped": "cwm-runtime-error",
                             "error": repr(e)[:200]})
            continue
        # If a distribution could not be evaluated at all (every chunk failed in
        # the sandbox), the agreement is unmeasured — recording gap=1-0 would be a
        # spurious gap. Skip the seed with the reason instead.
        if d_gate.n_states == 0 or d_cwm.n_states == 0 or d_truth.n_states == 0:
            per_seed.append({"seed": seed, "skipped": "cwm-eval-failed",
                             "gate_exec_errors": d_gate.n_exec_errors,
                             "cwm_exec_errors": d_cwm.n_exec_errors,
                             "truth_exec_errors": d_truth.n_exec_errors})
            continue
        entry = {
            "seed": seed,
            "gap": d_gate.state_agreement_rate - d_cwm.state_agreement_rate,
            "gap_truth": d_gate.state_agreement_rate - d_truth.state_agreement_rate,
            "gate": d_gate.state_agreement_rate,
            "cwm": d_cwm.state_agreement_rate,
            "truth": d_truth.state_agreement_rate,
            "refinement_iterations": refined.iterations,
            "d_gate": asdict(d_gate),
            "d_cwm": asdict(d_cwm),
            "d_truth": asdict(d_truth),
        }
        if args.play_games > 0:
            try:
                entry["play"] = _play_performance(
                    g, cwm, args.simulations, args.play_games, seed)
            except Exception as e:
                entry["play"] = {"error": repr(e)[:200]}
        per_seed.append(entry)

    report = {"game": args.game, "synth_size": args.synth_size,
              "no_rules": args.no_rules,
              "summary": aggregate_gap(per_seed),
              "per_seed": per_seed,
              "cost_usd_total": meter.total_usd()}
    out = json.dumps(report, indent=2)
    print(out)
    Path("results").mkdir(exist_ok=True)
    suffix = "_norules" if args.no_rules else ""
    Path(f"results/gap_{args.game}_{args.synth_size}{suffix}.json").write_text(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
