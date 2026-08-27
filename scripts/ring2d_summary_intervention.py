"""H2 summary intervention — the pre-registered paired analysis
(docs/paper3/INTERVENTION-DESIGN.md, as amended 2026-08-27 BEFORE any
outcome was inspected).

Arms (all gamma = 1.8, inside start, mini, the same 60 seeds):
  control-committed   results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda.json
  control-contemp.    results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda_ctrl2.json
  flipped             results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda-flip.json

PRIMARY contrast: flip vs the CONTEMPORANEOUS control, paired per seed.
Per seed the two arms carry opposite topology claims by construction; the
paired difference is
  D_i = closed(arm whose claim is loop) - closed(arm whose claim is arc),
computed with the SAME behavioral classifier the H2 table used
(freeze_mask_class; closed = {disc, loop, complement}). Discordant pairs
(D_i != 0) are the signal; with d discordant of which k positive, the exact
two-sided binomial p = P(|B(d, 1/2) - d/2| >= |k - d/2|). Secondary
outcome: paired gate passage, same test. Drift check: contemporaneous vs
committed control (same claims, different period).

The claims are read from each cell's own stored guidance_text
(guidance_beta1), so the analysis never recomputes or reinterprets what the
model was actually shown.
"""
import json
import math
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "src"))

from ring2d_artifact_audit import freeze_mask_class, guidance_beta1  # noqa: E402

CLOSED = {"disc", "loop", "complement"}
FILES = {
    "control_committed":
        "results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda.json",
    "control_contemporaneous":
        "results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda_ctrl2.json",
    "flipped":
        "results/continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda-flip.json",
}


def binom_two_sided(d: int, k: int) -> float:
    """Exact two-sided binomial p under B(d, 1/2)."""
    if d == 0:
        return 1.0
    dev = abs(k - d / 2)
    return sum(math.comb(d, j) for j in range(d + 1)
               if abs(j - d / 2) >= dev - 1e-12) / 2 ** d


def _binom_cdf(n: int, p: float, k: int) -> float:
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j)
               for j in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    """Exact (Clopper-Pearson) two-sided CI for a binomial proportion,
    by bisection on the binomial CDF -- the interval the design
    registered for the discordant split."""
    if n == 0:
        return [0.0, 1.0]

    def _solve(target, lo, hi, upper_tail):
        for _ in range(200):
            mid = (lo + hi) / 2
            tail = (1 - _binom_cdf(n, mid, k - 1)) if upper_tail \
                else _binom_cdf(n, mid, k)
            if tail > target:
                if upper_tail:
                    hi = mid
                else:
                    lo = mid
            else:
                if upper_tail:
                    lo = mid
                else:
                    hi = mid
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else _solve(alpha / 2, 0.0, 1.0, upper_tail=True)
    upper = 1.0 if k == n else _solve(alpha / 2, 0.0, 1.0, upper_tail=False)
    return [lower, upper]


def load(path):
    cells = json.loads((_REPO / path).read_text())["cells"]
    out = {}
    for c in cells:
        cls, _ = freeze_mask_class(c["code"])
        out[c["seed"]] = {
            "class": cls,
            "closed": cls in CLOSED,
            "claim": guidance_beta1(c),
            "gate_passed": bool(c["gate_passed"]),
        }
    return out


def paired_opposite_claims(a, b):
    """Primary: per seed, one arm claims loop (1) and the other arc (0);
    D = closed(claiming arm) - closed(non-claiming arm)."""
    rows, d_pos, d_neg = [], 0, 0
    for seed in sorted(set(a) & set(b)):
        ra, rb = a[seed], b[seed]
        if ra["claim"] is None or rb["claim"] is None \
                or ra["claim"] == rb["claim"]:
            rows.append({"seed": seed, "skipped":
                         f"claims {ra['claim']}/{rb['claim']} not opposite"})
            continue
        loop_arm = ra if ra["claim"] == 1 else rb
        arc_arm = rb if loop_arm is ra else ra
        D = int(loop_arm["closed"]) - int(arc_arm["closed"])
        d_pos += D == 1
        d_neg += D == -1
        rows.append({"seed": seed, "claim_loop_arm_closed":
                     loop_arm["closed"], "claim_arc_arm_closed":
                     arc_arm["closed"], "D": D,
                     "classes": [ra["class"], rb["class"]]})
    d = d_pos + d_neg
    return {"rows": rows, "n_pairs": len([r for r in rows if "D" in r]),
            "discordant": d, "toward_claim": d_pos, "against_claim": d_neg,
            "p_two_sided": binom_two_sided(d, d_pos),
            "toward_claim_share_ci95_clopper_pearson":
                clopper_pearson(d_pos, d)}


def paired_same_outcome(a, b, key):
    """Paired contrast of a boolean outcome between two arms."""
    d_pos = d_neg = 0
    for seed in sorted(set(a) & set(b)):
        x, y = a[seed][key], b[seed][key]
        d_pos += x and not y
        d_neg += y and not x
    d = d_pos + d_neg
    return {"a_only": d_pos, "b_only": d_neg, "discordant": d,
            "p_two_sided": binom_two_sided(d, d_pos)}


def main():
    arms = {}
    for name, path in FILES.items():
        if not (_REPO / path).exists():
            raise SystemExit(f"missing arm: {path}")
        arms[name] = load(path)
        n = len(arms[name])
        closed = sum(v["closed"] for v in arms[name].values())
        gate = sum(v["gate_passed"] for v in arms[name].values())
        print(f"{name}: n={n} closed={closed} gate_passed={gate}")

    out = {
        "design": "docs/paper3/INTERVENTION-DESIGN.md (amended 2026-08-27)",
        "classifier": "freeze_mask_class; closed = disc/loop/complement",
        "arms": {k: {s: {kk: vv for kk, vv in v.items()}
                     for s, v in sorted(arm.items())}
                 for k, arm in arms.items()},
        "primary_flip_vs_contemporaneous": paired_opposite_claims(
            arms["flipped"], arms["control_contemporaneous"]),
        "drift_check_contemporaneous_vs_committed_closed":
            paired_same_outcome(arms["control_contemporaneous"],
                                arms["control_committed"], "closed"),
        "secondary_gate_flip_vs_contemporaneous": paired_same_outcome(
            arms["flipped"], arms["control_contemporaneous"], "gate_passed"),
    }
    prim = out["primary_flip_vs_contemporaneous"]
    print(f"PRIMARY: pairs={prim['n_pairs']} discordant={prim['discordant']} "
          f"toward-claim={prim['toward_claim']} "
          f"against={prim['against_claim']} p={prim['p_two_sided']:.4g}")
    dst = _REPO / "results" / "ring2d_summary_intervention.json"
    dst.write_text(json.dumps(out, indent=1))
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
