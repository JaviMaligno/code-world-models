"""T3 (partial): measure the funnel defect that Theorem T3-P isolates
(docs/paper3/THEORY.md, "T3 (partial)").

Theorem T3-P: r_int(gamma2) >= r_int(gamma1) - f(gamma1) for gamma1 <
gamma2, where f = P(funnel-assisted entry). So M1/M2 are theorems with
defect f, and the open part of T3 is exactly a bound on f. This script
measures f(gamma) with Wilson CIs at a larger sample than the original
probe, and re-checks Proposition 7 (direct entries pathwise monotone)
under common random numbers.

Reported per gap: r_int, direct d, funnel f with 95% Wilson upper bound,
and the certified M1 slack (max over gaps of the f upper bound) against
the effect size r_int(2pi) - r_int(0).

Resumable per gap (JSON rewritten after each). CPU, ~8 min at the
default 50000 rollouts x 12 gaps (~100k plant steps/s measured).

Run: PYTHONPATH=src python scripts/t3_funnel_bound.py [--rollouts N]
"""
import argparse
import json
import math
import os
import random
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402
from cwm.law import wilson_ci                                   # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--gaps", type=float, nargs="+",
                default=[0.0, 0.1, 0.2, 0.4, 0.6, 0.9, 1.2, 1.8, 2.4,
                         3.2, 4.6, 2 * math.pi])
ap.add_argument("--rollouts", type=int, default=50_000)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

OUT = "results/t3_funnel_bound.json"
t0 = time.time()


def run_gap(env, n, seed0):
    """Per-seed (direct, funnel) indicators under common random numbers."""
    direct, funnel = [], []
    for i in range(n):
        rng = random.Random(seed0 + 50_000 + i)
        s = env.initial_state(rng)
        entered = froze_before = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s, _, contact = env.step(s, a)
            if not entered and env.in_interior(s[0], s[1]):
                entered = True
                break                      # first entry decides the split
            froze_before = froze_before or contact
        direct.append(entered and not froze_before)
        funnel.append(entered and froze_before)
    return direct, funnel


def main():
    store = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if store.get("rollouts") != args.rollouts:
        store = {"rollouts": args.rollouts, "seed": args.seed, "rows": [],
                 "direct_sets": {}}
    done = {r["gap"] for r in store["rows"]}
    for gap in args.gaps:
        if gap in done:
            continue
        env = RingField2D(gap=gap)
        direct, funnel = run_gap(env, args.rollouts, args.seed)
        d, d_lo, d_hi = wilson_ci(sum(direct), args.rollouts)
        f, f_lo, f_hi = wilson_ci(sum(funnel), args.rollouts)
        store["rows"].append({
            "gap": gap, "n": args.rollouts,
            "direct_count": sum(direct), "funnel_count": sum(funnel),
            "d": d, "f": f, "f_wilson_hi": f_hi,
            "r_int": d + f,
            "r_int_ci": [d_lo + f_lo, d_hi + f_hi]})
        # keep the direct indicator sets to check Prop 7 pathwise
        store["direct_sets"][str(gap)] = [i for i, v in enumerate(direct) if v]
        tmp = OUT + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(store, fh)
        os.replace(tmp, OUT)
        print(f"gap={gap:.3f}: r_int={d + f:.5f} direct={sum(direct)} "
              f"funnel={sum(funnel)} (f<= {f_hi:.2e} @95%)", flush=True)

    rows = sorted(store["rows"], key=lambda r: r["gap"])
    # Proposition 7 pathwise: direct(gamma1) subset direct(gamma2)
    prop7_viol = 0
    for a, b in zip(rows, rows[1:]):
        sa = set(store["direct_sets"][str(a["gap"])])
        sb = set(store["direct_sets"][str(b["gap"])])
        prop7_viol += len(sa - sb)
    # M1 empirical violations and the certified slack
    m1_viol = [(a["gap"], b["gap"], b["r_int"] - a["r_int"])
               for a, b in zip(rows, rows[1:]) if b["r_int"] < a["r_int"]]
    slack = max(r["f_wilson_hi"] for r in rows)
    effect = rows[-1]["r_int"] - rows[0]["r_int"]
    assert prop7_viol == 0, f"Proposition 7 violated {prop7_viol} times"
    print(f"\nProposition 7 (direct pathwise monotone): {prop7_viol} "
          f"violations across {len(rows) - 1} adjacent pairs")
    print(f"M1 empirical violations: {len(m1_viol)} {m1_viol}")
    print(f"certified M1/M2 slack (max Wilson-upper f) = {slack:.2e} "
          f"vs effect size {effect:.4f} -> ratio {effect / slack:.1f}x")
    store["summary"] = {"prop7_violations": prop7_viol,
                        "m1_empirical_violations": m1_viol,
                        "certified_slack": slack, "effect_size": effect}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(store, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"wrote {OUT}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
