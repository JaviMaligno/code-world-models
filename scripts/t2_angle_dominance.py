"""T2: stress-test the argmax-angle dominance claim at high power
(docs/paper3/THEORY.md, "Closing the first of the two").

The non-vacuous play-cost bound pc <= 0.767 rests on one distributional
claim: over dirty steps, |sin((phi_tau - phi_b)/2)| is stochastically
dominated by its value for two INDEPENDENT uniform actions, whose mean is
exactly 2/pi. That was measured on 278 dirty steps from 18 episodes at
three gaps. Two zeros in this campaign have already fallen to more power,
so the claim is tested here at ~10x the sample and over a wider
configuration range BEFORE any attempt to prove it: more gaps, both
channel orientations, and several planner sample counts (the claim must
not depend on the planner's budget, since it is asserted about the
argmax operation itself).

Reports, per configuration and pooled: E|sin|, the independent-uniform
reference (analytic 2/pi), and the worst CDF deficit over a quantile grid
(positive deficit = dominance VIOLATED there).

Resumable per configuration cell. Run:
    PYTHONPATH=src python scripts/t2_angle_dominance.py [--episodes N]
"""
import argparse
import bisect
import json
import math
import os
import random
import statistics as st
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D, blind_of           # noqa: E402
from cwm.continuous import mpc                                  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=14)
args = ap.parse_args()

HOR, BLOCK = 40, 10
OUT = "results/t2_angle_dominance.json"
# gap x channel orientation x planner sample count
CELLS = [(g, c, ns)
         for g in (0.3, 0.6, 1.2, 1.8)
         for c in ("facing", "hidden")
         for ns in (48, 96)]


def cands(a_max, seed, ns):
    return list(mpc._candidates(a_max, random.Random(seed), HOR, ns, BLOCK, 1))


def first_of_argmax(model, state, cs):
    best, ba = -float("inf"), 0.0
    for acts in cs:
        s, tot = state, 0.0
        for a in acts:
            s, r, _ = model.step(s, a)
            tot += r
        if tot > best:
            best, ba = tot, acts[0]
    return ba


def run_cell(gap, channel, ns, episodes):
    centre = math.pi if channel == "facing" else 0.0
    truth = RingField2D(gap=gap, gap_center=centre, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    vals = []
    for ep in range(episodes):
        es = 4000 + 1000 * ep
        s = truth.initial_state(random.Random(es))
        for t in range(truth.h_episode):
            cs = cands(truth.a_max, es * 100_003 + t, ns)
            b = first_of_argmax(blind, s, cs)
            tau = first_of_argmax(truth, s, cs)
            if b != tau:
                vals.append(abs(math.sin(math.pi * (tau - b) / 2)))
            s, _, _ = truth.step(s, b)
    return vals


def worst_deficit(vals, ref):
    """max over the grid of (reference CDF - measured CDF); > 0 = violation."""
    worst, where = -1.0, None
    for i in range(1, 100):
        q = i / 100
        fm = bisect.bisect_right(vals, q) / len(vals)
        fr = bisect.bisect_right(ref, q) / len(ref)
        if fr - fm > worst:
            worst, where = fr - fm, q
    return worst, where


def main():
    store = json.load(open(OUT)) if os.path.exists(OUT) else {"cells": {}}
    rng = random.Random(1)
    ref = sorted(abs(math.sin(math.pi * (rng.uniform(-1, 1)
                                         - rng.uniform(-1, 1)) / 2))
                 for _ in range(400_000))
    for gap, channel, ns in CELLS:
        key = f"g{gap}-{channel}-ns{ns}"
        if key in store["cells"]:
            continue
        vals = sorted(run_cell(gap, channel, ns, args.episodes))
        if len(vals) < 20:
            store["cells"][key] = {"n": len(vals), "note": "too few dirty steps"}
        else:
            d, where = worst_deficit(vals, ref)
            store["cells"][key] = {"n": len(vals), "mean": st.mean(vals),
                                   "worst_deficit": d, "at": where}
            print(f"{key:24s} n={len(vals):5d}  E|sin|={st.mean(vals):.4f}  "
                  f"worst deficit {d:+.4f} at {where}"
                  + ("   VIOLATION" if d > 0 else ""), flush=True)
        tmp = OUT + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(store, fh, indent=1)
        os.replace(tmp, OUT)

    pooled = []
    for gap, channel, ns in CELLS:
        c = store["cells"].get(f"g{gap}-{channel}-ns{ns}", {})
        if "mean" in c:
            pooled.append(c)
    n_tot = sum(c["n"] for c in pooled)
    viol = [c for c in pooled if c["worst_deficit"] > 0]
    print(f"\npooled over {len(pooled)} cells, {n_tot} dirty steps")
    print(f"  cells with a dominance violation: {len(viol)}/{len(pooled)}")
    print(f"  independent-uniform reference mean = {2 / math.pi:.4f}")
    print(f"  worst cell mean = {max(c['mean'] for c in pooled):.4f}")
    store["summary"] = {"cells": len(pooled), "dirty_steps": n_tot,
                        "violating_cells": len(viol),
                        "worst_mean": max(c["mean"] for c in pooled),
                        "reference_mean": 2 / math.pi}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(store, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
