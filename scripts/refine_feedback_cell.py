"""Discriminant experiment: does the model learn the material-at-cap rule once
the refinement feedback actually SHOWS it?

Background: the original refiner truncated failure lines at 200 chars and never
included the expected values, so the "FAILURES (expected vs got)" feedback
carried neither — the rule's signal never reached the model in legible form
through the refinement channel (and the synthesis prompt shows the FIRST 30
transitions of the trajectory stream — a deterministic prefix that can never
contain a material-at-cap terminal, whose global index is >= 99 by construction). The refiner is
now fixed (expected= shown per mismatched field). This script reruns the
headline tab:synthcurve cell (N=200, fresh-batch refinement) under the fixed
feedback:

  - still rule-blind  -> finding 3 gets STRONGER: the rule was legible in the
    feedback and still not learned (the pure (b) residual, now unconfounded).
  - learns the rule   -> finding 3's sweep arm is rescoped: the blindness was
    partly the harness's channel, not the model.

Run: PYTHONPATH=src python3.12 scripts/refine_feedback_cell.py [mini|large] [n_seeds]
Writes/updates results/refine_feedback_cell.json (keyed by model size).
"""
import json
import os
import sys
from pathlib import Path

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
N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[SIZE]]
N = 200

contract = build_contract(base.RULES_TEXT)   # INCOMPLETE rules


def rule_region_states():
    S = []
    b = [0]*26; b[0]=1; b[24]=4; b[5]=2;  b[25]=100; S.append({"board": b, "current_player": 1})
    b = [0]*26; b[2]=1; b[22]=4; b[10]=3; b[25]=100; S.append({"board": b, "current_player": 2})
    b = [0]*26; b[0]=1; b[24]=4; b[20]=5; b[25]=100; S.append({"board": b, "current_player": 1})
    return S


TEST = rule_region_states()
TRUTH_RET = [truth.returns(s) for s in TEST]


def _norm_returns(r):
    """Normalize key type so a string-keyed returns dict (which passes the
    JSON-round-tripped gate) is not misclassified as blind by the in-process
    comparison (audit finding: latent gate-vs-rule_status asymmetry)."""
    try:
        return {int(k): float(v) for k, v in r.items()}
    except (ValueError, TypeError, AttributeError):
        return r


def rule_status(code):
    try:
        m = _load_module_from_code(code)
        for s, tr in zip(TEST, TRUTH_RET):
            if _norm_returns(m.returns({"board": list(s["board"]),
                          "current_player": s["current_player"]})) != tr:
                return "blind", None
        return "aware", None
    except Exception as e:
        return "crash", repr(e)[:200]


def main():
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    print(f"discriminant cell (FIXED feedback): size={SIZE} N={N} seeds={N_SEEDS}", flush=True)
    records = []
    counts = {"blind": 0, "aware": 0, "crash": 0}
    for seed in range(N_SEEDS):
        traj = collect_trajectories(truth, n_games=N, seed=seed)
        code, _ = synthesize_cwm(provider, MODEL, contract, traj)
        refined = refine_cwm(
            provider, MODEL, contract, code, traj, max_iters=6,
            resample_fn=lambda it: collect_trajectories(truth, n_games=N,
                                                        seed=seed + 1000 * it))
        status, err = rule_status(refined.code)
        counts[status] += 1
        extra = f" ERR={err}" if status == "crash" else ""
        print(f"  seed={seed}: status={status} gate_acc={refined.accuracy:.3f} "
              f"iters={refined.iterations} n_samples={refined.n_samples}{extra}",
              flush=True)
        records.append({"seed": seed, "status": status, "error": err,
                        "gate_acc": refined.accuracy, "iters": refined.iterations,
                        "n_samples": refined.n_samples, "code": refined.code})
    print(f"=> {SIZE} (fixed feedback): {counts}", flush=True)

    dest = Path("results/refine_feedback_cell.json")
    data = json.loads(dest.read_text()) if dest.exists() else {}
    data[SIZE] = {"N": N, "n_seeds": N_SEEDS, "counts": counts, "per_seed": records}
    Path("results").mkdir(exist_ok=True)
    dest.write_text(json.dumps(data, indent=2))
    print(f"wrote {dest}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
