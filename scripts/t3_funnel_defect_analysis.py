"""T3-P'': the defect table, with the sample's own uncertainty carried.

Reads results/t3_funnel_bound.json -- no re-simulation -- and emits the
adjacent-pair defect [f(g1) - f(g2)]^+ with, for each pair, whether the sign
of the underlying change is actually resolved by the sample.

Why this exists. The claim "the defect is exactly zero in 6 of 11 pairs" is
true of the SAMPLE, and three of those six zeros are TIES in a noisy estimate
(22 vs 22, 0 vs 0, 0 vs 0) where the true sign is undetermined -- at 22 vs 22
it is about a coin flip. A tie is not a rise. And the accompanying claim that
the zeros are "every pair on which f rises, i.e. the whole range gamma <= 0.9"
is false: the pair (0.2, 0.4) is a DROP.

The separation figures need the same care. Comparing a raw point-estimate drop
against the effect size mixes conventions with the 16.9x figure, which uses a
Wilson upper bound on f. This emits both, so a display can quote one
convention throughout.

  PYTHONPATH=src python scripts/t3_funnel_defect_analysis.py
"""
import json
import math
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = _REPO / "results" / "t3_funnel_bound.json"
OUT = _REPO / "results" / "t3_funnel_defect_analysis.json"
Z = 1.96


def wilson(k, n, z=Z):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / den), min(1.0, (c + h) / den))


def main():
    rows = json.loads(SRC.read_text())["rows"]
    pairs, exact_zero, resolved_rise, ties = [], 0, 0, 0
    worst_point, worst_ci = 0.0, 0.0
    for a, b in zip(rows, rows[1:]):
        n = a["n"]
        k1, k2 = a["funnel_count"], b["funnel_count"]
        p1, p2 = k1 / n, k2 / n
        diff = p1 - p2                      # positive means f DROPPED
        defect = max(0.0, diff)
        # The drop is a difference of two independent binomials; its 95% upper
        # limit is what a bound may use, and it is what makes the separation
        # figure comparable with the Wilson-based 16.9x.
        sd = math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)
        diff_hi = diff + Z * sd
        defect_hi = max(0.0, diff_hi)
        # Is the SIGN resolved? A tie, or a difference inside its own interval,
        # is not evidence of a rise.
        sign_resolved = (diff - Z * sd > 0) or (diff + Z * sd < 0)
        kind = ("rise" if k2 > k1 else "tie" if k2 == k1 else "drop")
        exact_zero += (defect == 0.0)
        ties += (kind == "tie")
        resolved_rise += (kind == "rise" and diff + Z * sd < 0)
        worst_point = max(worst_point, defect)
        worst_ci = max(worst_ci, defect_hi)
        pairs.append({
            "gap_lo": a["gap"], "gap_hi": b["gap"], "n": n,
            "f_lo_count": k1, "f_hi_count": k2, "kind": kind,
            "defect_point": defect, "defect_wilson_style_upper": defect_hi,
            "sign_resolved_at_95": sign_resolved,
            "f_lo_wilson": wilson(k1, n), "f_hi_wilson": wilson(k2, n),
        })

    effect = rows[-1]["r_int"] - rows[0]["r_int"]
    # Prop 7's informative units: only a seed already in direct(gamma_1) can
    # falsify the inclusion, so the unit is the direct entry at the SMALLER
    # gap. Emitted here because quoting the rollout-pair count instead is a
    # 154-fold inflation, and because the number should not be a shell
    # one-liner nobody can find.
    informative = sum(a["direct_count"] for a in rows[:-1])
    out = {
        "source": str(SRC.relative_to(_REPO)), "z": Z,
        "n_pairs": len(pairs),
        "prop7_informative_units": informative,
        "prop7_rollout_pairs": sum(a["n"] for a in rows[:-1]),
        "prop7_per_pair_units": [a["direct_count"] for a in rows[:-1]],
        "defect_exactly_zero_in_sample": exact_zero,
        "of_which_are_ties": ties,
        "rises_with_the_sign_RESOLVED_at_95": resolved_rise,
        "worst_defect_point_estimate": worst_point,
        "worst_defect_upper_limit": worst_ci,
        "effect_size_r_int_range": effect,
        "separation_point_estimate": effect / worst_point if worst_point else None,
        "separation_ci_consistent": effect / worst_ci if worst_ci else None,
        "pairs": pairs,
        "note": (
            "defect_exactly_zero_in_sample counts pairs whose SAMPLE defect is "
            "0; of_which_are_ties says how many of those are ties, where the "
            "true sign is undetermined (a tie is not a rise). "
            "rises_with_the_sign_RESOLVED_at_95 is the only count that supports "
            "a claim about f itself. separation_point_estimate mixes "
            "conventions with the Wilson-based 16.9x figure; "
            "separation_ci_consistent uses an upper limit on both sides and is "
            "the one to quote beside it."),
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"pairs {out['n_pairs']}, sample-zero {exact_zero} "
          f"(of which {ties} ties), rises with sign resolved {resolved_rise}")
    print(f"worst defect: point {worst_point:.2e}, upper limit {worst_ci:.2e}")
    print(f"separation: point {out['separation_point_estimate']:.1f}x, "
          f"CI-consistent {out['separation_ci_consistent']:.1f}x")
    for p in pairs:
        print(f"  ({p['gap_lo']}, {p['gap_hi']}): {p['f_lo_count']}->"
              f"{p['f_hi_count']} {p['kind']:4} defect {p['defect_point']:.1e} "
              f"(<= {p['defect_wilson_style_upper']:.1e}), "
              f"sign resolved: {p['sign_resolved_at_95']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
