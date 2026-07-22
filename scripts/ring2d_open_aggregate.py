"""Open-ring sweep summary builder (spec §4).

Reads every ring2d synthesis result file (sweep + legacy gap-0), runs the
audit instruments per cell (freeze-mask class, canonical blind-reference
gate, guidance beta_1), extracts freeze-boundary parameters for posed
structures, and emits results/continuous_ring2d_open_sweep_summary.json
with the three headline analyses. Pure CPU, deterministic, safe to re-run.
"""
import glob
import json
import math
import os
import sys
from collections import Counter

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ring2d_artifact_audit import (BLIND_CODE, env_for,          # noqa: E402
                                   freeze_mask_class, guidance_beta1,
                                   integrator_step)
from cwm.continuous.contract import (collect_transitions,        # noqa: E402
                                     contract_accuracy)
from cwm.law import wilson_ci                                    # noqa: E402

CX = 12.0
DEFAULT_GLOBS = [
    "results/continuous_synthesis_ring2d_mini_gap*.json",
    "results/continuous_synthesis_ring2d_large_gap*.json",
]
CURVE_PATH = "results/continuous_ring2d_pcblind_curve.json"
OUT_PATH = "results/continuous_ring2d_open_sweep_summary.json"
POSED = {"loop", "disc", "complement", "fill-unbounded", "arc"}


def freeze_boundary_params(code):
    """Fitted geometry of the frozen set on the v=0 probe grid: radial
    band [r_lo, r_hi] (band+outer zones only, r <= 8), angular coverage,
    and the largest angular gap — comparable to truth r_in=3.5 and channel
    edges pi +- gap/2."""
    ns = {}
    exec(code, ns)  # noqa: S102 — audited synthesis artifacts
    step = ns["step"]
    rs, angs = [], []
    for i in range(81):
        for j in range(81):
            x = 4.0 + 16.0 * i / 80.0
            y = -8.0 + 16.0 * j / 80.0
            got = step([x, y, 0.0, 0.0], 0.3)
            exp = integrator_step(x, y, 0.0, 0.0, 0.3)
            if max(abs(g - e) for g, e in zip(got, exp)) > 1e-6:
                r = math.hypot(x - CX, y)
                if 3.0 <= r <= 8.0:
                    rs.append(r)
                    angs.append(math.atan2(y, x - CX) % (2 * math.pi))
    if not rs:
        return {"r_lo": None, "r_hi": None, "ang_cov": 0.0,
                "max_ang_gap_rad": None}
    angs.sort()
    gaps = [b - a for a, b in zip(angs, angs[1:])]
    gaps.append(angs[0] + 2 * math.pi - angs[-1])
    bins = {int(a / (2 * math.pi) * 72) for a in angs}
    return {"r_lo": min(rs), "r_hi": max(rs), "ang_cov": len(bins) / 72,
            "max_ang_gap_rad": max(gaps)}


def build_summary(paths, curve_path=CURVE_PATH):
    blind_cache = {}
    artifacts, danger, synthesis = [], {}, {}
    for path in sorted(paths):
        raw = json.loads(open(path).read())
        params = raw.get("params", {}) or {}
        gap = params.get("gap", 0.0) or 0.0
        channel = params.get("channel", "facing") or "facing"
        start = params.get("start", "outside") or "outside"
        env = env_for(params)
        for c in raw.get("cells", []):
            if c.get("arm") != "incomplete":
                continue
            key = ((gap, channel, start), c["seed"])
            if key not in blind_cache:
                tr = collect_transitions(env, c.get("n_rollouts", 40),
                                         seed=c["seed"])
                blind_cache[key] = contract_accuracy(
                    BLIND_CODE, tr, c.get("eps", 1e-9))[0]
            cls, st = freeze_mask_class(c["code"])
            row = {
                "path": os.path.basename(path), "gap": gap,
                "channel": channel, "start": start,
                "size": raw.get("size"), "seed": c["seed"],
                "sample_contains_wall": c["sample_contains_wall"],
                "gate_accuracy": c["gate_accuracy"],
                "gate_passed": c["gate_passed"],
                "blind_ref_gate": blind_cache[key],
                "class": cls, "band_cov": st.get("cov"),
                "guidance_beta1": guidance_beta1(c),
                "play_cost": c.get("play_cost"),
            }
            if cls in POSED:
                row["boundary_params"] = freeze_boundary_params(c["code"])
            if "history" in c:
                row["history_classes"] = [
                    freeze_mask_class(h["code"])[0] for h in c["history"]]
            artifacts.append(row)

    for r in artifacts:
        if r["start"] == "outside":
            d = danger.setdefault(f"{r['gap']}|{r['channel']}",
                                  {"gap": r["gap"], "channel": r["channel"],
                                   "n": 0, "n_artifacts": 0, "mode_absent": 0,
                                   "pc_values": [], "_seeds": set()})
            # identifiability (sample_contains_wall) is env-determined — it
            # depends only on (gap, channel, seed), NOT on model size or prompt
            # variant. Count each unique seed ONCE so the Wilson CI is not
            # pseudo-replicated across the mini/large/variant files that share
            # seeds (they draw byte-identical samples). play_cost IS
            # model-dependent, so pc_values keeps every artifact.
            d["n_artifacts"] += 1
            if r["seed"] not in d["_seeds"]:
                d["_seeds"].add(r["seed"])
                d["n"] += 1
                if not r["sample_contains_wall"]:
                    d["mode_absent"] += 1
            if r["play_cost"] is not None:
                d["pc_values"].append(r["play_cost"])
        else:
            s = synthesis.setdefault(str(r["gap"]), {
                "gap": r["gap"], "n": 0, "gate_pass": 0, "gates": [],
                "blind_refs": [], "classes": Counter(),
                "classes_by_guidance_beta1": {}})
            s["n"] += 1
            s["gate_pass"] += r["gate_passed"]
            s["gates"].append(r["gate_accuracy"])
            s["blind_refs"].append(r["blind_ref_gate"])
            s["classes"][r["class"]] += 1
            gb = str(r["guidance_beta1"])
            s["classes_by_guidance_beta1"].setdefault(
                gb, Counter())[r["class"]] += 1
    for d in danger.values():
        d.pop("_seeds")                       # set is not JSON-serializable
        d["wilson"] = wilson_ci(d["mode_absent"], d["n"])   # n = unique seeds
    for s in synthesis.values():
        s["mean_terminal_gate"] = sum(s.pop("gates")) / s["n"]
        s["mean_blind_ref"] = sum(s.pop("blind_refs")) / s["n"]
        s["classes"] = dict(s["classes"])
        s["classes_by_guidance_beta1"] = {
            k: dict(v) for k, v in s["classes_by_guidance_beta1"].items()}

    curve = (json.loads(open(curve_path).read())
             if curve_path and os.path.exists(curve_path) else [])
    return {"pc_blind_curve": curve, "danger": danger,
            "synthesis": synthesis, "artifacts": artifacts}


def main():
    paths = [p for g in DEFAULT_GLOBS for p in glob.glob(g)]
    summary = build_summary(paths)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(summary, f, indent=1)
    os.replace(tmp, OUT_PATH)
    print(f"wrote {OUT_PATH}: {len(summary['artifacts'])} artifacts, "
          f"{len(summary['danger'])} danger cells, "
          f"{len(summary['synthesis'])} synthesis gaps")


if __name__ == "__main__":
    main()
