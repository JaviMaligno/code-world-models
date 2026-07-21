"""Per-artifact behavioral audit of the ring2d synthesis arms (review pass).

For every cell of every ring2d synthesis result file:
  - freeze-mask fingerprint: probe the artifact's step() on a state grid
    around the ring and mark where it deviates from the pure integrator
    (the freeze/mode set), then classify the set by the 2x2
    (inner-free x bounded) plus angular coverage:
      blind       no deviation anywhere
      vdep        deviation only at nonzero velocity (velocity superstition)
      point       tiny set (angular coverage <= 4%)
      arc         partial angular coverage (4% < cov < 97%)
      loop        full coverage, hollow (inner free), bounded
      disc        full coverage, filled interior, bounded
      complement  full coverage, hollow, unbounded (freezes the far field)
      fill-unbounded  filled interior AND unbounded
  - canonical blind-reference gate on the cell's exact evidence
    (collect_transitions(env, 40, seed) + contract_accuracy of the pure
    integrator), so terminal artifact gates are read against the right
    baseline;
  - guidance beta_1 (parsed from the recorded guidance_text, when present).

Also emits the pre-registered topological summary's detector-resolution
curve: betti1_estimate on regenerated inside-start contact landings per
(gap, seed) — the gap at which the guidance's reported beta_1 flips 1 -> 0.

Output: results/ring2d_artifact_audit.json  (audit rows + aggregates +
detector curve). Pure CPU; deterministic; safe to re-run.
"""
import json
import math
import os
import re
import sys
from collections import Counter

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402
from cwm.continuous.contract import (collect_transitions,      # noqa: E402
                                     contract_accuracy)
from cwm.continuous.tda import (betti1_estimate, dedupe,       # noqa: E402
                                subsample)

DT, GAIN, DRAG, AMAX = 0.1, 3.0, 0.3, 1.0
CX, CY = 12.0, 0.0          # ring center
N_ANG_BINS = 72
GRID_N = 81                  # 81x81 probe grid over [4,20] x [-8,8]
EPS_DEV = 1e-6

BLIND_CODE = """
import math
def step(state, action):
    x, y, vx, vy = state
    a = min(1.0, max(-1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0*math.cos(phi) - 0.3*vx)*0.1
    vy2 = vy + (3.0*math.sin(phi) - 0.3*vy)*0.1
    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x+6.0, y)
    d2 = math.hypot(x-12.0, y)
    return 0.3/(1.0+math.exp((d1-2.0)/0.5)) + 1.0/(1.0+math.exp((d2-2.0)/0.5))
"""

RESULT_FILES = {
    "A_closed_large": "results/continuous_synthesis_ring2d_large_gap0.json",
    "A_closed_mini": "results/continuous_synthesis_ring2d_mini_gap0.json",
    "B_region_large":
        "results/continuous_synthesis_ring2d_large_gap0_pv-region.json",
    "C_tda_large": "results/continuous_synthesis_ring2d_large_gap0_pv-tda.json",
    "C_tda_mini": "results/continuous_synthesis_ring2d_mini_gap0_pv-tda.json",
    "D_in_tda_large":
        "results/continuous_synthesis_ring2d_large_gap0-in_pv-tda.json",
    "D_in_tda_mini":
        "results/continuous_synthesis_ring2d_mini_gap0-in_pv-tda.json",
    "A_open06_mini": "results/continuous_synthesis_ring2d_mini_gap0.6.json",
    "D_open06_mini":
        "results/continuous_synthesis_ring2d_mini_gap0.6-in_pv-tda.json",
    "A_qwen_closed":
        "results/continuous_synthesis_ring2d_compat-qwen3-coder-30b-a3b-instruct_gap0.json",
}

DETECTOR_GAPS = [0.0, 0.2, 0.4, 0.6, 0.9, 1.2, 1.8, 2.4]
DETECTOR_SEEDS = [10000, 20000, 30000, 40000, 50000]


def integrator_step(x, y, vx, vy, a):
    a = min(AMAX, max(-AMAX, a))
    phi = math.pi * a / AMAX
    vx2 = vx + (GAIN * math.cos(phi) - DRAG * vx) * DT
    vy2 = vy + (GAIN * math.sin(phi) - DRAG * vy) * DT
    return [x + vx2 * DT, y + vy2 * DT, vx2, vy2]


def freeze_mask_class(code):
    """Behavioral class of the artifact's deviation-from-integrator set."""
    ns = {}
    try:
        exec(code, ns)  # noqa: S102 — audited synthesis artifacts
        step = ns["step"]
    except Exception:
        return "invalid", {}
    stats = {}
    for vtag, (vx, vy) in (("v0", (0.0, 0.0)), ("v1", (1.5, 0.5))):
        band_bins = set()
        n = {"band": 0, "inner": 0, "outer": 0, "far": 0}
        d = {"band": 0, "inner": 0, "outer": 0, "far": 0}
        for i in range(GRID_N):
            for j in range(GRID_N):
                x = 4.0 + 16.0 * i / (GRID_N - 1)
                y = -8.0 + 16.0 * j / (GRID_N - 1)
                r = math.hypot(x - CX, y - CY)
                zone = ("band" if 3.0 <= r <= 5.5 else
                        "inner" if r < 3.0 else
                        "outer" if r <= 8.0 else "far")
                d[zone] += 1
                try:
                    got = step([x, y, vx, vy], 0.3)
                except Exception:
                    return "crash", {}
                exp = integrator_step(x, y, vx, vy, 0.3)
                try:
                    dev = max(abs(g - e) for g, e in zip(got, exp))
                except TypeError:
                    return "invalid", {}
                if dev > EPS_DEV:
                    n[zone] += 1
                    if zone == "band":
                        ang = math.atan2(y - CY, x - CX) % (2 * math.pi)
                        band_bins.add(int(ang / (2 * math.pi) * N_ANG_BINS))
        stats[vtag] = {
            "cov": len(band_bins) / N_ANG_BINS,
            **{z: n[z] / d[z] for z in n},
        }
    v0, v1 = stats["v0"], stats["v1"]
    t0 = sum(v0[z] for z in ("band", "inner", "outer", "far"))
    t1 = sum(v1[z] for z in ("band", "inner", "outer", "far"))
    filled = v0["inner"] > 0.5
    unbounded = v0["far"] > 0.2
    if t0 == 0 and t1 == 0:
        cls = "blind"
    elif t0 == 0:
        cls = "vdep"
    elif v0["cov"] >= 0.97:
        cls = ("fill-unbounded" if filled and unbounded else
               "disc" if filled else
               "complement" if unbounded else "loop")
    elif v0["cov"] > 0.04:
        cls = "arc"
    else:
        cls = "point"
    return cls, stats["v0"]


def env_for(params):
    gap = params.get("gap", 0.0) or 0.0
    channel = params.get("channel", "facing") or "facing"
    start = params.get("start", "outside") or "outside"
    return RingField2D(gap=gap,
                       gap_center=math.pi if channel == "facing" else 0.0,
                       x0_center=(0.0, 0.0) if start == "outside"
                       else RingField2D().center)


def contact_landings(env, transitions):
    """Refuted integrator landings of contact transitions (the honest
    evidence cloud the topological summary is computed from — mirrors
    scripts/continuous_danger_synthesis.py:_contact_landings)."""
    pts = []
    for tr in transitions:
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            pts.append((x2, y2))
    return pts


def guidance_beta1(cell):
    m = re.search(r"beta_1 = (\d+)", cell.get("guidance_text", "") or "")
    return int(m.group(1)) if m else None


def main():
    out = {"files": {}, "detector_curve": []}
    blind_gate_cache = {}
    for tag, path in RESULT_FILES.items():
        if not os.path.exists(path):
            print(f"[skip] {tag}: {path} missing")
            continue
        raw = json.load(open(path))
        cells = raw["cells"] if isinstance(raw, dict) else raw
        params = (raw.get("params", {}) if isinstance(raw, dict)
                  else {k: cells[0].get(k) for k in ("gap", "channel", "start")
                        if cells and k in cells[0]})
        env = env_for(params)
        envkey = (params.get("gap", 0.0), params.get("channel", "facing"),
                  params.get("start", "outside"))
        rows = []
        for c in cells:
            bkey = (envkey, c["seed"])
            if bkey not in blind_gate_cache:
                trans = collect_transitions(env, c.get("n_rollouts", 40),
                                            seed=c["seed"])
                blind_gate_cache[bkey] = contract_accuracy(
                    BLIND_CODE, trans, c.get("eps", 1e-9))[0]
            cls, st = freeze_mask_class(c["code"])
            rows.append({
                "seed": c["seed"], "arm": c.get("arm"),
                "sample_contains_wall": c["sample_contains_wall"],
                "gate_accuracy": c["gate_accuracy"],
                "gate_passed": c["gate_passed"],
                "wall_blindness": c.get("wall_blindness"),
                "blind_ref_gate": blind_gate_cache[bkey],
                "class": cls,
                "band_cov": st.get("cov"),
                "inner_fill": st.get("inner"),
                "far_fill": st.get("far"),
                "guidance_beta1": guidance_beta1(c),
            })
        aggs = {}
        for arm in sorted({r["arm"] for r in rows}):
            sub = [r for r in rows if r["arm"] == arm]
            aggs[arm] = {
                "n": len(sub),
                "gate_pass": sum(r["gate_passed"] for r in sub),
                "mode_present": sum(r["sample_contains_wall"] for r in sub),
                "mean_terminal_gate":
                    sum(r["gate_accuracy"] for r in sub) / len(sub),
                "mean_blind_ref_gate":
                    sum(r["blind_ref_gate"] for r in sub) / len(sub),
                "classes": dict(Counter(r["class"] for r in sub)),
            }
        out["files"][tag] = {"path": path, "params": params,
                             "cells": rows, "aggregates": aggs}
        print(f"{tag}: " + json.dumps(aggs))

    # detector-resolution curve (inside start, facing channel)
    for gap in DETECTOR_GAPS:
        env = RingField2D(gap=gap, gap_center=math.pi,
                          x0_center=RingField2D().center)
        row = {"gap": gap, "betti1_per_seed": {}, "n_points_mean": 0}
        npts = []
        for s in DETECTOR_SEEDS:
            trans = collect_transitions(env, 40, seed=s)
            pts = subsample(dedupe(contact_landings(env, trans), 0.05), 90, 0)
            est = betti1_estimate(pts)
            row["betti1_per_seed"][str(s)] = est["betti1"]
            npts.append(len(pts))
        row["n_points_mean"] = sum(npts) / len(npts)
        out["detector_curve"].append(row)
        print(f"detector gap={gap}: "
              f"{list(row['betti1_per_seed'].values())}")

    dst = "results/ring2d_artifact_audit.json"
    tmp = dst + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
