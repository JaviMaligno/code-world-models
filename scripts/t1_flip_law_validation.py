"""T1: the detector flip law, validated on the sensor factorial.

LAW: the pre-registered detector reports beta1_hat = 1 iff
    sqrt(3)*rho - 2*rho*sin(dtheta_max / 2) > tau
where rho = the cloud's mean radius, dtheta_max = the LARGEST ANGULAR GAP of
the deduped+capped sample (channel or sampling gap, whichever is larger),
tau = 3 x median-NN. Ingredients:
  - birth of the winding bar = chord of the largest sample gap (Lemma:
    any winding 1-cycle must contain an edge spanning every angular gap);
  - death = sqrt(3)*rho, the Adamaszek-Adams circle constant, measured to
    transfer to gapped samples within +-2% (results/t1_bar_geometry.json:
    death/rho in [1.70, 1.82], mean 1.73, 15/15 finite bars);
  - persistent iff the bar length clears tau.
Validation: 78/80 rows of results/ring2d_sensor_resolution.json (the two
misses are boundary rows at gamma=1.8/N=160 with margin ~0.2 -- within the
death-constant spread). The naive channel-chord version scores 66/80: the
flip is the MAX SAMPLE GAP, not the channel -- which also explains the
boundary wobble (subsampling-gap lottery) and the multi-chamber lottery.

Run: PYTHONPATH=src python scripts/t1_flip_law_validation.py
"""
import json
import math
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D
from cwm.continuous.contract import collect_transitions
from cwm.continuous.tda import dedupe, subsample


def landings(env, transitions):
    pts = []
    for tr in transitions:
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            pts.append((x2, y2))
    return pts


def main():
    rows = json.load(open("results/ring2d_sensor_resolution.json"))
    sq3 = math.sqrt(3)
    agree, out = 0, []
    for r in rows:
        env = RingField2D(gap=r["gap"], gap_center=math.pi,
                          x0_center=RingField2D().center)
        tr = collect_transitions(env, r["n_rollouts"], seed=r["seed"])
        pts = subsample(dedupe(landings(env, tr), 0.05), r["cap"], 0)
        rho = sum(math.hypot(p[0] - 12, p[1]) for p in pts) / len(pts)
        angs = sorted(math.atan2(p[1], p[0] - 12) % (2 * math.pi)
                      for p in pts)
        gaps = [b - a for a, b in zip(angs, angs[1:])]
        gaps.append(angs[0] + 2 * math.pi - angs[-1])
        dmax = max(gaps)
        pred_pers = sq3 * rho - 2 * rho * math.sin(min(dmax, math.pi) / 2)
        pred = 1 if pred_pers > r["tau"] else 0
        obs = 1 if r["betti1"] >= 1 else 0
        agree += (pred == obs)
        out.append({**{k: r[k] for k in ("gap", "cap", "n_rollouts", "seed",
                                         "tau", "betti1")},
                    "rho": round(rho, 3), "dtheta_max": round(dmax, 3),
                    "pred_persistence": round(pred_pers, 3), "pred": pred,
                    "agree": pred == obs})
    print(f"agreement: {agree}/{len(rows)}")
    with open("results/t1_flip_law_validation.json", "w") as f:
        json.dump({"agreement": f"{agree}/{len(rows)}", "rows": out}, f,
                  indent=1)
    print("wrote results/t1_flip_law_validation.json")


if __name__ == "__main__":
    main()
