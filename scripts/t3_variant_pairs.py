"""T3: accumulate ENTERING PAIRS for the velocity-preserving variant
(docs/paper3/THEORY.md, "T3 — the original ingredient").

The variant statement is pathwise M1: under CRN, if the gamma1 copy enters
the interior then so does the gamma2 copy. Only a pair in which the gamma1
copy ENTERS can falsify it, so the experimental unit is the ENTERING PAIR,
not the rollout. The previous run had 517 such units and a Wilson 95%
upper bound of 7.4e-3 on the failure rate — thin for a pathwise claim.
This accumulates units until the interval is tight enough to be worth
quoting, concentrating on the gap pairs with the highest entry rates
(entry rate rises with gamma1) while keeping the wide separations that
refuted both candidate invariants.

Resumable: per-cell counts are checkpointed after every block, and
completed blocks are skipped on restart.

Run: PYTHONPATH=src python scripts/t3_variant_pairs.py [--blocks N]
"""
import argparse
import json
import math
import os
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D, integrate_2d       # noqa: E402
from cwm.law import wilson_ci                                   # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--blocks", type=int, default=40,
                help="blocks of 5000 pairs per cell")
ap.add_argument("--block-size", type=int, default=5000)
args = ap.parse_args()

OUT = "results/t3_variant_pairs.json"
# gamma1 chosen for entry rate; gamma2 = 2pi keeps the widest separation,
# which is where both candidate invariants failed
CELLS = [(1.2, 2 * math.pi), (2.4, 2 * math.pi), (3.2, 2 * math.pi)]


def pair_outcome(e1, e2, seed):
    """Velocity-preserving variant, CRN. Returns (copy1_entered,
    copy2_entered)."""
    r1 = random.Random(seed)
    r2 = random.Random(seed)
    s1 = e1.initial_state(r1)
    s2 = e2.initial_state(r2)
    in1 = in2 = False
    for _ in range(e1.h_episode):
        a = r1.uniform(-e1.a_max, e1.a_max)
        r2.uniform(-e2.a_max, e2.a_max)
        x1, y1, vx1, vy1 = integrate_2d(s1, a, e1.dt, e1.gain, e1.drag,
                                        e1.a_max)
        x2, y2, vx2, vy2 = integrate_2d(s2, a, e2.dt, e2.gain, e2.drag,
                                        e2.a_max)
        s1 = ((s1[0], s1[1], vx1, vy1) if e1._in_mode(x1, y1)
              else (x1, y1, vx1, vy1))
        s2 = ((s2[0], s2[1], vx2, vy2) if e2._in_mode(x2, y2)
              else (x2, y2, vx2, vy2))
        in1 = in1 or e1.in_interior(s1[0], s1[1])
        in2 = in2 or e2.in_interior(s2[0], s2[1])
    return in1, in2


def main():
    store = (json.load(open(OUT)) if os.path.exists(OUT)
             else {"block_size": args.block_size, "cells": {}})
    assert store["block_size"] == args.block_size, "block size changed"
    for g1, g2 in CELLS:
        key = f"{g1}->{round(g2, 4)}"
        cell = store["cells"].setdefault(key, {"blocks_done": 0, "pairs": 0,
                                               "entering": 0, "failures": 0})
        e1, e2 = RingField2D(gap=g1), RingField2D(gap=g2)
        while cell["blocks_done"] < args.blocks:
            b = cell["blocks_done"]
            base = 900_000 + b * args.block_size
            ent = fail = 0
            for i in range(args.block_size):
                in1, in2 = pair_outcome(e1, e2, base + i)
                if in1:
                    ent += 1
                    fail += (not in2)
            cell["blocks_done"] = b + 1
            cell["pairs"] += args.block_size
            cell["entering"] += ent
            cell["failures"] += fail
            tmp = OUT + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(store, fh, indent=1)
            os.replace(tmp, OUT)
            print(f"  {key} block {b + 1}/{args.blocks}: +{ent} entering "
                  f"(+{fail} failures) -> {cell['entering']} units total",
                  flush=True)

    tot_e = sum(c["entering"] for c in store["cells"].values())
    tot_f = sum(c["failures"] for c in store["cells"].values())
    tot_p = sum(c["pairs"] for c in store["cells"].values())
    p, lo, hi = wilson_ci(tot_f, tot_e) if tot_e else (0.0, 0.0, 1.0)
    store["summary"] = {"pairs": tot_p, "entering_units": tot_e,
                        "failures": tot_f, "failure_rate": p,
                        "wilson95": [lo, hi]}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(store, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"\nunit = ENTERING PAIR. {tot_f} failures in {tot_e} units "
          f"(from {tot_p} CRN pairs)")
    print(f"Wilson 95% upper bound on the pathwise-M1 failure rate: "
          f"{hi:.2e}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
