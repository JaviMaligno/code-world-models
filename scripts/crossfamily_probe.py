"""Cross-family rule-blindness probe: does a NON-GPT model family infer the
material-at-cap rule from trajectories that contain it?

Addresses the §7 "single model family" limitation with a spot-check, not a
sweep: the headline finding-3 cell (N=200 trajectories, fresh-batch
refinement — the rule is present in every sample at this N) run on open model
families served through the Hugging Face Inference Providers router, using
the EXACT same pipeline as scripts/danger_synthesis_sweep.py (same contract,
same synthesis and refinement messages, same rule_status classification).

Run: HF_TOKEN=... PYTHONPATH=src python3.12 scripts/crossfamily_probe.py \
        "Qwen/Qwen3-Coder-30B-A3B-Instruct" [n_seeds]
Writes/updates results/crossfamily_probe.json (keyed by model id).
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
from cwm.llm.openai_compat import OpenAICompatProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.run_gap import _load_module_from_code

MODEL = sys.argv[1]
N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
N = 200                       # the headline cell of tab:synthcurve
R = 0.025

contract = build_contract(base.RULES_TEXT)   # INCOMPLETE rules (no material-at-cap)


def rule_region_states():
    """EXACTLY the same rule-region test states as danger_synthesis_sweep:
    cap states (ply=100), both generals alive, unequal material -> truth gives
    a material winner; a rule-blind CWM gives a draw."""
    S = []
    b = [0]*26; b[0]=1; b[24]=4; b[5]=2;  b[25]=100; S.append({"board": b, "current_player": 1})  # p1 +infantry
    b = [0]*26; b[2]=1; b[22]=4; b[10]=3; b[25]=100; S.append({"board": b, "current_player": 2})  # p1 +cavalry
    b = [0]*26; b[0]=1; b[24]=4; b[20]=5; b[25]=100; S.append({"board": b, "current_player": 1})  # p2 +infantry
    return S


TEST = rule_region_states()
TRUTH_RET = [truth.returns(s) for s in TEST]
assert all(r != {1: 0.0, 2: 0.0} for r in TRUTH_RET), "test states must be decisive"


def rule_status(code):
    """'aware' | 'blind' | 'crash' — same classification as the sweep."""
    try:
        m = _load_module_from_code(code)
        for s, tr in zip(TEST, TRUTH_RET):
            if m.returns({"board": list(s["board"]),
                          "current_player": s["current_player"]}) != tr:
                return "blind", None
        return "aware", None
    except Exception as e:
        return "crash", repr(e)[:200]


def main():
    provider = OpenAICompatProvider(
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ["HF_TOKEN"])
    print(f"cross-family probe: model={MODEL} N={N} seeds={N_SEEDS}", flush=True)
    records = []
    for seed in range(N_SEEDS):
        traj = collect_trajectories(truth, n_games=N, seed=seed)
        code, _ = synthesize_cwm(provider, MODEL, contract, traj)
        refined = refine_cwm(
            provider, MODEL, contract, code, traj, max_iters=6,
            resample_fn=lambda it: collect_trajectories(truth, n_games=N,
                                                        seed=seed + 1000 * it))
        status, err = rule_status(refined.code)
        extra = f" ERR={err}" if status == "crash" else ""
        print(f"  seed={seed}: status={status} gate_acc={refined.accuracy:.3f} "
              f"iters={refined.iterations} n_samples={refined.n_samples}{extra}",
              flush=True)
        records.append({"seed": seed, "status": status, "error": err,
                        "gate_acc": refined.accuracy, "iters": refined.iterations,
                        "n_samples": refined.n_samples, "code": refined.code})
    counts = {k: sum(1 for r in records if r["status"] == k)
              for k in ("blind", "aware", "crash")}
    print(f"=> {MODEL}: {counts}", flush=True)

    dest = Path("results/crossfamily_probe.json")
    data = json.loads(dest.read_text()) if dest.exists() else {}
    data[MODEL] = {"N": N, "n_seeds": N_SEEDS, "counts": counts,
                   "per_seed": records}
    Path("results").mkdir(exist_ok=True)
    dest.write_text(json.dumps(data, indent=2))
    print(f"wrote {dest}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
