"""Budget-matched play-cost of LLM-SYNTHESIZED CWMs, with CIs (paper 1, codex #1).

Panel A measures play_cost with a hand-written rule-blind instrument; this script
measures the same quantity with the actual synthesized pipeline, at the same
budget, so the synthesized evidence stops being range-only corroboration.

Per seed, per arm in {incomplete, complete}: draw N gate trajectories on the
TRUE game (army5x5a + material-at-cap; the sample doubles as the gate, fixed —
no resampling — as in the deployed pipeline, Sec. 2.2), synthesize + refine to
gate 1.0, and if the gate passes, play the synthesized CWM (MPC/MCTS) vs truth
for `games` games at `sims` simulations. A paired fair baseline (truth-vs-truth)
runs on the same seeds. We log `wall_in_sample` (the identifiability event: does
the gate sample contain a material-at-cap terminal?) so play_cost can be read
conditionally, and report pooled Wilson intervals per arm plus a seed-clustered
paired-t play_cost (fair - arm), the seed as the unit (cf. play_cost_ci.py).

Defaults reproduce Panel A's budget (20 seeds x 120 games x 600 sims). Use
`--seeds 2 --games 12 --sims 200` for a fast harness pilot.

Run: PYTHONPATH=src python3.12 scripts/play_cost_synth_ci.py mini [--seeds N ...]
Writes results/play_cost_synth_<size>.json.
"""
import argparse
import json
import math
import os
import statistics
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess as base, gen_chess_material as mat
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.run_gap import _load_module_from_code, _play_performance
from cwm.law import wilson_ci, t_crit_95

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("size", choices=["mini", "large", "nano"])
ap.add_argument("--seeds", type=int, default=20)
ap.add_argument("--games", type=int, default=120, help="arena games/seed/arm (Panel A: 120)")
ap.add_argument("--sims", type=int, default=600, help="MCTS simulations (Panel A: 600)")
ap.add_argument("--gate-games", type=int, default=40, help="N gate/training trajectories")
ap.add_argument("--max-iters", type=int, default=5)
args = ap.parse_args()

MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[args.size]]
CONTRACTS = {"incomplete": build_contract(base.RULES_TEXT),   # omits material-at-cap
             "complete":   build_contract(mat.RULES_TEXT)}    # full rules


def wall_in_sample(traj) -> bool:
    """Identifiability event: does the gate sample contain a material-at-cap terminal?
    (cap reached with both generals alive and a decisive result -> the material
    rule fired; a capture would have ended the game with a general missing.)"""
    for t in traj:
        if not t.terminal:
            continue
        b = t.next_state["board"]
        if (b[mat.N] >= mat.MAX_PLIES and mat._general_alive(b, 1)
                and mat._general_alive(b, 2) and t.reward != {1: 0.0, 2: 0.0}):
            return True
    return False


def _with_api_retry(fn, what, attempts=5, wait=90):
    """Retry a block through transient API/connection errors (machine sleep,
    Azure blips) beyond the SDK's own retries, so one outage does not kill a
    multi-hour run. Re-raises after `attempts`."""
    import time as _t
    for k in range(attempts):
        try:
            return fn()
        except Exception as e:  # openai.APIConnectionError, timeouts, 5xx, ...
            if k == attempts - 1:
                raise
            print(f"  !! {what}: API error ({type(e).__name__}), retry "
                  f"{k+1}/{attempts-1} after {wait}s", flush=True)
            _t.sleep(wait)


def synth_and_play(arm, seed):
    traj = collect_trajectories(mat, n_games=args.gate_games, seed=seed)
    code, _ = _with_api_retry(
        lambda: synthesize_cwm(provider, MODEL, CONTRACTS[arm], traj),
        f"synth {arm} seed={seed}")
    refined = _with_api_retry(
        lambda: refine_cwm(provider, MODEL, CONTRACTS[arm], code, traj,
                           max_iters=args.max_iters),   # fixed sample = gate (no resample)
        f"refine {arm} seed={seed}")
    rec = {"arm": arm, "seed": seed, "wall_in_sample": wall_in_sample(traj),
           "gate_accuracy": refined.accuracy, "refine_iters": refined.iterations,
           "gate_passed": refined.accuracy >= 1.0}
    if rec["gate_passed"]:
        m = _load_module_from_code(refined.code)
        r = _play_performance(mat, m, sims=args.sims, n_games=args.games, seed=seed)
        rec.update(cwm_wins=r["cwm_wins"], draws=r["draws"], truth_wins=r["truth_wins"],
                   winrate=r["cwm_winrate"])
    return rec


DEST = Path(f"results/play_cost_synth_{args.size}.json")


def _summarize(arm, cells, n_seeds):
    """Pooled Wilson + seed-clustered paired-t play_cost over gate-passing seeds."""
    passed = [c for c in cells if c["arm"] == arm and c["gate_passed"]]
    summ = {"arm": arm, "gate_pass_seeds": len(passed), "of_seeds": n_seeds,
            "wall_absent_seeds": sum(1 for c in passed if not c["wall_in_sample"])}
    if not passed:
        return summ
    W = sum(c["cwm_wins"] for c in passed); D = sum(c["draws"] for c in passed)
    L = sum(c["truth_wins"] for c in passed); n = W + D + L
    pt, lo, hi = wilson_ci(W + 0.5 * D, n)
    summ.update(pooled_winrate=pt, pooled_wilson95=[lo, hi], pooled_n=n)
    diffs = [c["play_cost"] for c in passed]
    k = len(diffs); mean_d = statistics.mean(diffs)
    if k > 1:
        sd = statistics.stdev(diffs); se = sd / math.sqrt(k); t = t_crit_95(k - 1)
        summ.update(play_cost_mean=mean_d, play_cost_sd=sd,
                    play_cost_t95=[mean_d - t * se, mean_d + t * se],
                    excludes_zero=(mean_d - t * se) > 0)
    else:
        summ.update(play_cost_mean=mean_d, note="single gate-passing seed; no CI")
    return summ


def _aggregate(fair, cells):
    out = {"size": args.size, "model": MODEL, "params": vars(args),
           "fair_per_seed": fair, "cells": cells}
    for arm in ("incomplete", "complete"):
        out.setdefault("summary", {})[arm] = _summarize(arm, cells, args.seeds)
    return out


def _checkpoint(fair, cells):
    Path("results").mkdir(exist_ok=True)
    DEST.write_text(json.dumps(_aggregate(fair, cells), indent=2))


def main():
    print(f"synthesized play-cost: size={args.size} seeds={args.seeds} "
          f"games={args.games} sims={args.sims} gate_N={args.gate_games}", flush=True)
    # Resume: reuse a compatible checkpoint (same budget), skip finished seeds.
    fair, cells, done = {}, [], set()
    if DEST.exists():
        prev = json.loads(DEST.read_text())
        bp = prev.get("params", {})
        if all(bp.get(k) == getattr(args, k) for k in ("games", "sims", "gate_games")):
            fair = {int(k): v for k, v in prev.get("fair_per_seed", {}).items()}
            cells = prev.get("cells", [])
            done = {c["seed"] for c in cells if c["arm"] == "complete"}
            print(f"resuming: {len(done)} seeds already complete ({sorted(done)})", flush=True)

    for seed in range(args.seeds):
        if seed in done:
            continue
        # drop any partial cells from a half-finished seed, then redo it
        cells = [c for c in cells if c["seed"] != seed]
        fb = _with_api_retry(
            lambda: _play_performance(mat, mat, sims=args.sims, n_games=args.games, seed=seed),
            f"fair seed={seed}")
        fair[seed] = fb["cwm_winrate"]
        print(f"[fair seed={seed}] winrate={fb['cwm_winrate']:.3f}", flush=True)
        for arm in ("incomplete", "complete"):
            rec = synth_and_play(arm, seed)
            rec["fair_winrate"] = fair[seed]
            if rec["gate_passed"]:
                rec["play_cost"] = fair[seed] - rec["winrate"]
            cells.append(rec)
            print(f"[{arm} seed={seed}] wall_in_sample={rec['wall_in_sample']} "
                  f"gate={rec['gate_accuracy']:.3f} iters={rec['refine_iters']} "
                  f"winrate={rec.get('winrate','n/a')} "
                  f"play_cost={rec.get('play_cost','n/a')}", flush=True)
        _checkpoint(fair, cells)   # crash-safe: persist after every finished seed

    _checkpoint(fair, cells)   # final write (aggregate recomputed inside)
    out = _aggregate(fair, cells)
    for arm in ("incomplete", "complete"):
        s = out["summary"][arm]
        if s.get("gate_pass_seeds"):
            print(f"=> {arm}: {s['gate_pass_seeds']}/{args.seeds} gate-passing "
                  f"({s['wall_absent_seeds']} wall-absent); pooled winrate "
                  f"{s['pooled_winrate']:.3f} {s['pooled_wilson95']}; "
                  f"play_cost {s.get('play_cost_t95', s.get('play_cost_mean'))}", flush=True)
        else:
            print(f"=> {arm}: 0/{args.seeds} gate-passing", flush=True)
    print(f"wrote {DEST}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    main()
