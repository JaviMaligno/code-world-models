"""Calibrate T3's quadratic lower bound on disjoint seed blocks.

The defect this closes: the constant was defined as `min_grid d(gamma)/gamma^2`
on ONE sample, which makes `d >= C*gamma^2` true by construction at the grid and
a coin flip off it. Review measured five fresh 40k blocks at the binding gap
(0.6) and found the bound violated in three of them.

A bound's constant must sit below the SAMPLING INTERVAL of the quantity it
bounds, not on its point estimate. So this script measures d(gamma) on several
disjoint seed blocks, pools them, and reports the 95% lower confidence limit;
the emitted constant is derived from that limit, never from the point estimate.

Resumable: each (gamma, block) cell is written as it finishes, so an interrupted
run continues where it stopped.

  PYTHONPATH=src python scripts/t3_quadratic_constant.py
"""
import argparse
import json
import math
import pathlib
import random

from cwm.continuous.instruments import RingField2D

_REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = _REPO / "results" / "t3_quadratic_constant.json"

# Disjoint seed bases: no two blocks share a rollout, so the blocks are
# independent samples of d(gamma) and their spread is the sampling spread.
SEED_BASES = (50_000, 300_000, 500_000, 700_000, 1_100_000)
GAPS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.6)


def direct_entry_rate(gap, seed_base, n):
    """Fraction of rollouts entering the interior directly (never frozen)."""
    env = RingField2D(gap=gap)
    d = 0
    for i in range(n):
        rng = random.Random(seed_base + i)
        s = env.initial_state(rng)
        froze = False
        for _ in range(env.h_episode):
            s, _, contact = env.step(s, rng.uniform(-env.a_max, env.a_max))
            if contact:
                froze = True
                break
            if env.in_interior(s[0], s[1]):
                d += (not froze)
                break
    return d


def wilson_lower(k, n, z=1.96):
    """Wilson score lower limit -- valid for the small k/n this produces."""
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - half) / denom)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40_000,
                    help="rollouts per (gap, block) cell")
    ap.add_argument("--gaps", type=float, nargs="*", default=None,
                    help="restrict to these gaps (default: all)")
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {"cells": {}}
    cells = state["cells"]

    gaps = tuple(args.gaps) if args.gaps else GAPS
    for gap in gaps:
        for base in SEED_BASES:
            key = f"{gap}|{base}|{args.n}"
            if key in cells:
                continue
            k = direct_entry_rate(gap, base, args.n)
            cells[key] = {"gap": gap, "seed_base": base, "n": args.n,
                          "direct": k}
            OUT.write_text(json.dumps(state, indent=2, sort_keys=True))
            print(f"gap {gap} base {base}: {k}/{args.n} = {k / args.n:.6f}")

    # Pool the disjoint blocks per gap and take the Wilson lower limit; the
    # binding gap is the one minimising (lower limit)/gamma^2.
    per_gap, binding = {}, None
    for gap in GAPS:
        rows = [c for c in cells.values() if c["gap"] == gap]
        k = sum(r["direct"] for r in rows)
        n = sum(r["n"] for r in rows)
        blocks = sorted(r["direct"] / r["n"] for r in rows)
        lo = wilson_lower(k, n)
        per_gap[str(gap)] = {
            "pooled_direct": k, "pooled_n": n, "point": k / n,
            "wilson_lower_95": lo, "ratio_from_lower_limit": lo / gap ** 2,
            "block_rates_min": blocks[0], "block_rates_max": blocks[-1],
            # A constant taken from the POINT estimate would be violated by any
            # block below it; record how many, since that is the defect.
            "blocks_below_point_estimate": sum(b < k / n for b in blocks),
        }
        # Separate the two reasons a gap can bind: the SHAPE of d(gamma) or
        # the statistical POWER at that gap. Without this the constant looks
        # like a property of the instrument when it is a property of n.
        per_gap[str(gap)]["ratio_from_point_estimate"] = (k / n) / gap ** 2
        per_gap[str(gap)]["power_penalty"] = (
            (k / n) / gap ** 2 - lo / gap ** 2)
        cand = lo / gap ** 2
        if binding is None or cand < binding[1]:
            binding = (gap, cand)

    state["per_gap"] = per_gap
    state["binding_gap"] = binding[0]
    # Round DOWN to four decimals: a lower bound's constant may only be
    # rounded down, or the bound it states becomes false.
    state["quadratic_constant"] = math.floor(binding[1] * 1e4) / 1e4
    state["note"] = (
        "quadratic_constant is derived from the pooled Wilson 95% LOWER limit "
        "at the binding gap, rounded down. It is deliberately NOT min d/gamma^2 "
        "on a sample: that value is violated by roughly half of fresh seed "
        "blocks. The bound is claimed on [0.05, 0.6] only -- d saturates above, "
        "so no quadratic bound holds for gamma >= 0.9.")
    OUT.write_text(json.dumps(state, indent=2, sort_keys=True))

    print(f"\nbinding gap {binding[0]}, constant "
          f"{state['quadratic_constant']:.6f} "
          f"(point-estimate version would be "
          f"{min(per_gap[str(g)]['point'] / g ** 2 for g in GAPS):.6f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
