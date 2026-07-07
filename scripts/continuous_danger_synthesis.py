"""LLM synthesis arms for the continuous instrument (paper 2, step 3).

Per (arm, seed): collect N random rollouts on the truth (the sample doubles
as the gate, as in paper 1's sweep), synthesize step()/reward() from the
contract + examples, refine to gate 1.0 at eps=1e-9 (pinned integrator:
correct code matches to float precision), then classify the artifact:
  - sample_contains_wall: the identifiability event, logged per seed
    (paper 1 could not condition on it post hoc; here we can)
  - gate_passed / refine_iterations
  - wall_blindness: wall-region probe (1.0 = clamp not encoded)
  - play: J of MPC planning on the synthesized model, executed in truth,
    vs the truth-planner baseline on paired seeds -> play_cost

REQUIRES Azure OpenAI credentials in <repo-root>/.env:
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION,
  AZURE_DEPLOYMENT_MINI / AZURE_DEPLOYMENT_LARGE / AZURE_DEPLOYMENT_NANO
(same variables as the paper-1 scripts).

Run (from the repo root):
  PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5
  PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 5 --x-wall 8
Arguments: size (mini|large|nano), n_seeds; see --help for the rest.
Cost: ~2-7 LLM calls/seed (1 synthesis + refinements), prompt ~1-2k tokens —
comparable per-seed to paper 1's danger sweep cells. Runtime is dominated by
the play evaluation (~1-2 min CPU per seed at the defaults).

Predictions (design doc): full arm -> gate 1.0, wall_blindness 0.0, play at
truth parity. Incomplete arm -> when the sample misses the wall (probability
(1-r)^N; r ~ 0.013 at x_wall=8, so ~60% of seeds at N=40), gate 1.0 +
wall_blindness 1.0 + play_cost ~ 1 (pinned at the wall). When the sample DOES
contain the wall, translation-not-inference predicts the gate cannot reach
1.0 (the wall transitions are inexplicable to a wall-less program) — watch
refine behavior there; a numerically-manifested discontinuity may be easier
to induce from data than a symbolic rule (either outcome is a finding).
"""
import argparse
import json
import pathlib
import statistics
import sys
import time

from dotenv import load_dotenv

_REPO = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(_REPO / ".env", override=True)

import os  # noqa: E402

sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402
from cwm.continuous import harness  # noqa: E402
from cwm.continuous.contract import (  # noqa: E402
    SynthesizedModel, synthesize_and_evaluate)
from cwm.law import wilson_ci  # noqa: E402
from cwm.llm.azure_openai import AzureOpenAIProvider  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("size", choices=["mini", "large", "nano"])
ap.add_argument("n_seeds", type=int, nargs="?", default=5)
ap.add_argument("--arm", choices=["full", "incomplete", "both"], default="both")
ap.add_argument("--x-wall", type=float, default=8.0,
                help="8.0: gate misses the wall ~60%% of seeds at N=40; "
                "4.0: gate nearly always catches it")
ap.add_argument("--n-rollouts", type=int, default=40, help="the danger-law N")
ap.add_argument("--eps", type=float, default=1e-9,
                help="pinned-integrator gate tolerance; loosen to 1e-6 if a "
                "full-spec run fails only on float noise (record it if so)")
ap.add_argument("--play-episodes", type=int, default=6)
ap.add_argument("--max-iters", type=int, default=5)
args = ap.parse_args()

MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI",
                    "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[args.size]]
provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])

ENV = CartWall(x_wall=args.x_wall)
ARMS = ["full", "incomplete"] if args.arm == "both" else [args.arm]

# Truth-planner + random baselines, shared across all seeds/arms (paired).
print(f"baselines: {args.play_episodes} truth-MPC + random episodes...", flush=True)
_base_t, _base_r = [], []
for i in range(args.play_episodes):
    sd = 900_000 + 1000 * i
    _base_t.append(harness.run_episode(ENV, ENV, "mpc", sd).ret)
    _base_r.append(harness.run_episode(ENV, policy="random", seed=sd).ret)
J_TRUTH, J_RANDOM = statistics.mean(_base_t), statistics.mean(_base_r)
print(f"J_truth={J_TRUTH:.2f}  J_random={J_RANDOM:.2f}", flush=True)

t0 = time.time()
results = {"script": "continuous_danger_synthesis.py", "model": MODEL,
           "size": args.size, "params": vars(args),
           "j_truth": J_TRUTH, "j_random": J_RANDOM, "cells": []}
for arm in ARMS:
    for seed in range(args.n_seeds):
        cell = synthesize_and_evaluate(
            provider, MODEL, ENV, include_wall=(arm == "full"),
            n_rollouts=args.n_rollouts, seed=10_000 * (seed + 1),
            eps=args.eps, max_iters=args.max_iters)
        if cell["gate_passed"]:
            model = SynthesizedModel(cell["code"], ENV)
            eps_play = []
            for i in range(args.play_episodes):
                sd = 900_000 + 1000 * i
                eps_play.append(harness.run_episode(ENV, model, "mpc", sd))
            j = statistics.mean(e.ret for e in eps_play)
            cell["j_play"] = j
            cell["play_cost"] = (J_TRUTH - j) / (J_TRUTH - J_RANDOM)
            cell["play_contact_rate"] = (
                sum(e.contact for e in eps_play) / len(eps_play))
        results["cells"].append(cell)
        print(f"[{arm} seed={seed}] wall_in_sample={cell['sample_contains_wall']} "
              f"gate={cell['gate_accuracy']:.3f} iters={cell['refine_iterations']} "
              f"blind={cell['wall_blindness']} "
              f"play_cost={cell.get('play_cost', 'n/a')}", flush=True)

# Cell summary: the danger-law conditionals.
inc = [c for c in results["cells"] if c["arm"] == "incomplete"]
if inc:
    missed = [c for c in inc if not c["sample_contains_wall"]]
    blind_when_missed = [c for c in missed
                         if c["gate_passed"] and c["wall_blindness"] == 1.0]
    print(f"\nincomplete arm: {len(missed)}/{len(inc)} seeds had the wall "
          f"ABSENT from the sample (identifiability event); of those, "
          f"{len(blind_when_missed)} passed the gate fully wall-blind "
          f"(Wilson 95% {wilson_ci(len(blind_when_missed), len(missed))})"
          if missed else "\nincomplete arm: wall present in every sample",
          flush=True)

results["elapsed_s"] = round(time.time() - t0, 1)
out = pathlib.Path(f"results/continuous_synthesis_{args.size}_xwall{args.x_wall:g}.json")
out.write_text(json.dumps(results, indent=2))
print(f"wrote {out}  [{results['elapsed_s']}s]", flush=True)
