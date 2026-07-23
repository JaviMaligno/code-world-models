"""Sensor-resolution factorial: what sets the topological summary's flip?

The pre-registered detector (Rips, dedup 0.05, cap 90, 3x median-NN) reports
beta1_hat = 1 on the open ring for every gamma <= 1.2. Two candidate causes:
  (a) BUDGET: the cap-90 subsample sets the density, so a bigger cap would
      resolve narrower channels;
  (b) GEOMETRY: a Rips loop bar is born when the filtration bridges the
      channel chord and dies at the fill radius — if chord < death radius
      the spurious loop exists AT ANY density, and no budget fixes it.
The factorial separates them: beta1_hat over gamma x cap (detector budget)
x N (evidence dose), 5 seeds each, inside-start contact landings regenerated
exactly as the guidance computes them.

Output: results/ring2d_sensor_resolution.json (resumable per row).
CPU-only; the cap-270 Rips rows take a few minutes each.
"""
import json
import math
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402
from cwm.continuous.contract import collect_transitions         # noqa: E402
from cwm.continuous.tda import (betti1_estimate, dedupe,        # noqa: E402
                                subsample)

GAPS = [0.6, 1.2, 1.8, 2.4]
CAPS = [30, 90, 270]
SEEDS = [10000, 20000, 30000, 40000, 50000]
DOSES = [40, 160]            # N rollouts of evidence
OUT = "results/ring2d_sensor_resolution.json"


def landings(env, transitions):
    pts = []
    for tr in transitions:
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            pts.append((x2, y2))
    return pts


def main():
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["gap"], r["cap"], r["n_rollouts"], r["seed"]) for r in rows}
    for gap in GAPS:
        env = RingField2D(gap=gap, gap_center=math.pi,
                          x0_center=RingField2D().center)
        for n_roll in DOSES:
            for cap in CAPS:
                if n_roll == 160 and cap != 90:
                    continue        # dose control runs at the registered cap
                for seed in SEEDS:
                    key = (gap, cap, n_roll, seed)
                    if key in done:
                        continue
                    trans = collect_transitions(env, n_roll, seed=seed)
                    pts = subsample(dedupe(landings(env, trans), 0.05),
                                    cap, 0)
                    est = betti1_estimate(pts)
                    rows.append({"gap": gap, "cap": cap,
                                 "n_rollouts": n_roll, "seed": seed,
                                 "n_points": len(pts),
                                 "betti1": est["betti1"],
                                 "tau": est["tau"],
                                 "top_persistence": [
                                     p if p != float("inf") else None
                                     for p in est["top_persistence"]]})
                    tmp = OUT + ".tmp"
                    with open(tmp, "w") as f:
                        json.dump(rows, f, indent=1)
                    os.replace(tmp, OUT)   # per-row checkpoint
                    print(f"gap={gap} cap={cap} N={n_roll} seed={seed}: "
                          f"b1={est['betti1']} pts={len(pts)}", flush=True)
    # summary
    print("\n===== beta1_hat by (gap, cap) at N=40 (5 seeds) =====")
    for gap in GAPS:
        line = f"gap={gap}: "
        for cap in CAPS:
            b = [r["betti1"] for r in rows
                 if r["gap"] == gap and r["cap"] == cap
                 and r["n_rollouts"] == 40]
            line += f"cap{cap}={b} "
        print(line)
    print("===== dose control (cap 90): N=40 vs N=160 =====")
    for gap in GAPS:
        b40 = [r["betti1"] for r in rows if r["gap"] == gap
               and r["cap"] == 90 and r["n_rollouts"] == 40]
        b160 = [r["betti1"] for r in rows if r["gap"] == gap
                and r["cap"] == 90 and r["n_rollouts"] == 160]
        print(f"gap={gap}: N40={b40} N160={b160}")


if __name__ == "__main__":
    main()
