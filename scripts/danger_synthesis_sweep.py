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
import json, os, sys, random
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
from cwm.law import wilson_ci

SIZE = sys.argv[1] if len(sys.argv) > 1 else "mini"
MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[SIZE]]
contract = build_contract(base.RULES_TEXT)   # INCOMPLETE rules
provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])

R = 0.025
N_GRID = [40, 120, 200]
# Default 6 seeds/cell reproduces the published sweep; pass a count as argv[2] to
# tighten the denominator (e.g. 20). At 6/6 the Wilson 95% lower bound on the
# rule-blind rate is only ~0.61, so the summary now prints it -- a bare "1.000"
# over 6 seeds oversells the point (see the limitations roadmap in
# docs/EXPERIMENTS.md).
N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
SEEDS = list(range(N_SEEDS))


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


def _norm_returns(r):
    """Normalize key type so a string-keyed returns dict (which passes the
    JSON-round-tripped gate) is not misclassified as blind by the in-process
    comparison (audit finding: latent gate-vs-rule_status asymmetry)."""
    try:
        return {int(k): float(v) for k, v in r.items()}
    except (ValueError, TypeError, AttributeError):
        return r


def rule_status(code):
    """Classify a synthesized CWM on the rule-region test states into one of:
      'aware' — runs and matches truth (gives the material winner) on ALL of them,
      'blind' — runs but disagrees with truth on at least one, or
      'crash' — raises while loading/evaluating.
    A crash is a synthesis-ROBUSTNESS failure, not evidence about rule inference,
    so it is reported separately and excluded from the rule-blind rate (unless it
    is structural, i.e. every seed crashes — which the crash count makes visible).
    Returns (status, error_repr_or_None)."""
    try:
        m = _load_module_from_code(code)
        for s, tr in zip(TEST, TRUTH_RET):
            if _norm_returns(m.returns({"board": list(s["board"]), "current_player": s["current_player"]})) != tr:
                return "blind", None   # disagrees with truth on a rule-region state
        return "aware", None
    except Exception as e:
        return "crash", repr(e)[:200]


def run_seed(N, seed):
    traj = collect_trajectories(truth, n_games=N, seed=seed)
    code, _ = synthesize_cwm(provider, MODEL, contract, traj)
    refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=6,
                         resample_fn=lambda it: collect_trajectories(truth, n_games=N, seed=seed + 1000*it))
    status, err = rule_status(refined.code)
    return {"N": N, "seed": seed, "status": status, "error": err,
            "gate_acc": refined.accuracy, "iters": refined.iterations,
            "n_samples": refined.n_samples, "code": refined.code}


def main():
    print(f"synth size={SIZE}, r={R}", flush=True)
    per_seed = []          # every seed's full record, persisted for audit
    summary = []
    for N in N_GRID:
        counts = {"blind": 0, "aware": 0, "crash": 0}
        for seed in SEEDS:
            rec = run_seed(N, seed)
            per_seed.append(rec)
            counts[rec["status"]] += 1
            extra = f" ERR={rec['error']}" if rec["status"] == "crash" else ""
            print(f"  N={N} seed={seed}: status={rec['status']} gate_acc={rec['gate_acc']:.3f} "
                  f"iters={rec['iters']} n_samples={rec['n_samples']}{extra}", flush=True)
        ran = counts["blind"] + counts["aware"]   # crashes excluded from the denominator
        if ran:
            frac, lo, hi = wilson_ci(counts["blind"], ran)
            rate_str = f"{counts['blind']}/{ran} = {frac:.3f} (Wilson95 [{lo:.3f}, {hi:.3f}])"
        else:
            frac = lo = hi = None
            rate_str = "n/a (every seed crashed — structural)"
        print(f"=> N={N}: rule_blind {rate_str}; crashes EXCLUDED = {counts['crash']}/{len(SEEDS)}   "
              f"(identifiability prediction (1-r)^N = {(1-R)**N:.3f})", flush=True)
        summary.append({"N": N, **counts, "ran": ran, "rule_blind_rate": frac,
                        "wilson95": [lo, hi], "identifiability_floor": (1 - R) ** N})
    Path("results").mkdir(exist_ok=True)
    out = {"size": SIZE, "model": MODEL, "r": R, "n_grid": N_GRID,
           "n_seeds": len(SEEDS), "summary": summary, "per_seed": per_seed}
    Path(f"results/danger_synthesis_{SIZE}.json").write_text(json.dumps(out, indent=2))
    print(f"wrote results/danger_synthesis_{SIZE}.json", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
