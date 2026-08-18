"""H4 certificate for the pipeline-risk ("danger") law.

This is deliberately CPU-only.  It has two jobs:

1. Version the common mathematical formulation that contains the iid exponent,
   independent train/gate exponents, adaptive/non-iid gates, and the two-mode
   Frechet bracket as corollaries of one chain-rule identity.
2. Propagate the uncertainty that is actually identifiable from committed
   results into every published hand-written danger curve.  Rarity gets a
   family-wise 95% Clopper--Pearson band (Bonferroni across every rarity
   estimand in the output).  A joint rarity+play-cost band is emitted only for
   cells whose paired episode triples are committed; other cells are marked as
   incomplete rather than silently treating estimated play cost as fixed.

Run:
    PYTHONPATH=src .venv/bin/python scripts/danger_law_h4.py
"""
from __future__ import annotations

import json
import math
import pathlib
import random
import statistics
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "danger_law_h4.json"
N_VALUES = (20, 40, 80)
BOOTSTRAPS = 5_000
BOOT_SEED = 20260817


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the regularized incomplete beta (NR 3e)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1e-300 if abs(d) < 1e-300 else d
    d = 1.0 / d
    h = d
    for m in range(1, 301):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1e-300 if abs(d) < 1e-300 else d
        c = 1.0 + aa / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            return h
    raise ArithmeticError("incomplete-beta continued fraction did not converge")


def _betainc_reg(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(q: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _betainc_reg(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson_interval(k: int, n: int, conf: float = .95) -> dict:
    """Exact equal-tailed binomial interval, with no SciPy dependency."""
    if not 0 <= k <= n or not 0 < conf < 1:
        raise ValueError("invalid count or confidence")
    alpha = 1.0 - conf
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else _beta_ppf(1 - alpha / 2, k + 1, n - k)
    return {"lo": lo, "hi": hi}


def chain_miss(conditional_event_probabilities: Iterable[float]) -> float:
    """Exact no-event probability from hazards along the no-event history.

    r_i means P(E_i | E_1^c,...,E_{i-1}^c).  No independence, stationarity, or
    identical-distribution hypothesis is used: this is the probability chain
    rule.  Empty sequences miss with probability one.
    """
    out = 1.0
    for r in conditional_event_probabilities:
        if not 0.0 <= r <= 1.0:
            raise ValueError("conditional event probabilities must lie in [0,1]")
        out *= 1.0 - r
    return out


def bounded_adaptive_miss(lower: Iterable[float], upper: Iterable[float]) -> tuple[float, float]:
    """Sharp product bounds when each conditional event hazard is interval-known."""
    lo, hi = list(lower), list(upper)
    if len(lo) != len(hi):
        raise ValueError("lower and upper hazard sequences must have equal length")
    if any(not 0.0 <= a <= b <= 1.0 for a, b in zip(lo, hi)):
        raise ValueError("hazard bounds must satisfy 0 <= lower <= upper <= 1")
    return chain_miss(hi), chain_miss(lo)


def frechet_two_mode_miss(r1: float, r2: float, n: int) -> tuple[float, float]:
    """Sharp iid N-rollout miss bracket from two marginal event rates."""
    if n < 0 or not (0 <= r1 <= 1 and 0 <= r2 <= 1):
        raise ValueError("invalid rate or budget")
    union_lo = max(r1, r2)
    union_hi = min(1.0, r1 + r2)
    return (1.0 - union_hi) ** n, (1.0 - union_lo) ** n


def pipeline_risk(accepted_probability: float, conditional_shipped_cost: float) -> float:
    """E[X 1_G] = P(G) E[X|G], the always-valid risk factorization."""
    if not 0 <= accepted_probability <= 1:
        raise ValueError("accepted_probability must lie in [0,1]")
    return accepted_probability * conditional_shipped_cost


def danger_interval(cost_interval: tuple[float, float], rarity_interval: tuple[float, float], n: int) -> tuple[float, float]:
    """Corner propagation through c*(1-r)^n for nonnegative cost."""
    c_lo, c_hi = cost_interval
    r_lo, r_hi = rarity_interval
    if c_lo < 0 or c_hi < c_lo or not 0 <= r_lo <= r_hi <= 1 or n < 0:
        raise ValueError("invalid interval")
    return c_lo * (1.0 - r_hi) ** n, c_hi * (1.0 - r_lo) ** n


def _load(name: str) -> dict:
    return json.loads((ROOT / "results" / name).read_text())


def _paired_cost_intervals() -> dict[str, dict]:
    """Published-cell intervals from the first 20 committed paired triples."""
    data = _load("play_cost_intervals.json")
    units = data["units"]
    answer = {}
    for key in ("cart_xwall8", "pend_thstop1.4", "patch2d_k3_7"):
        rows = sorted((u for u in units.values() if u["row"] == key and u["episode"] < 20),
                      key=lambda u: u["episode"])
        if len(rows) != 20 or [u["episode"] for u in rows] != list(range(20)):
            continue
        t = [u["j_truth"] for u in rows]
        b = [u["j_blind"] for u in rows]
        r = [u["j_random"] for u in rows]
        point = (statistics.mean(t) - statistics.mean(b)) / (statistics.mean(t) - statistics.mean(r))
        rng = random.Random(BOOT_SEED + sum(map(ord, key)))
        boots = []
        for _ in range(BOOTSTRAPS):
            ix = [rng.randrange(20) for _ in range(20)]
            mt = statistics.mean(t[i] for i in ix)
            mb = statistics.mean(b[i] for i in ix)
            mr = statistics.mean(r[i] for i in ix)
            if mt > mr:
                boots.append((mt - mb) / (mt - mr))
        boots.sort()
        answer[key] = {
            "point": point,
            "ci95_pointwise": [boots[int(.025 * len(boots))], boots[math.ceil(.975 * len(boots)) - 1]],
            "method": "paired episode-triple percentile bootstrap; ratio of means recomputed",
            "n_episode_seed_units": 20,
            "bootstrap_replicates": BOOTSTRAPS,
            "source": "results/play_cost_intervals.json units, episodes 0..19",
        }
    return answer


def _raw_curves() -> list[dict]:
    curves = []
    for family, filename, knob_name in (
        ("cart", "continuous_reach.json", "x_wall"),
        ("pendulum", "continuous_pendulum.json", "th_stop"),
    ):
        data = _load(filename)
        nr = data["params"]["rollouts"]
        for row in data["rows"]:
            key = (f"cart_xwall{row[knob_name]:g}" if family == "cart" else
                   f"pend_thstop{row[knob_name]:g}")
            curves.append({"family": family, "source": f"results/{filename}",
                           "key": key, "knob": {knob_name: row[knob_name]},
                           "rarity": row["rarity"], "rarity_n": nr,
                           "planner_reach": row["blind_contact_rate"],
                           "planner_reach_n": row["n_episodes"],
                           "play_cost": row["play_cost"], "budgets": list(N_VALUES)})
    data = _load("continuous_patch2d.json")
    nr = data["params"]["rollouts"]
    for row in data["rows"]:
        base = {"family": "patch2d", "source": "results/continuous_patch2d.json",
                "key": f"patch2d_k{row['k1']:g}_{row['k2']:g}",
                "knob": {"k1": row["k1"], "k2": row["k2"]},
                "rarity_n": nr, "planner_reach": row["blind_contact_rate"],
                "planner_reach_n": row["n_episodes"],
                "play_cost": row["play_cost"], "budgets": [40]}
        for event, field in (("mode_1", "r1"), ("mode_2", "r2"), ("union", "r_either")):
            curves.append({**base, "key": base["key"] + "_" + event,
                           "cost_key": base["key"], "critical_event": event,
                           "rarity": row[field]})
    return curves


def build() -> dict:
    curves = _raw_curves()
    # Bonferroni + exact per-estimand intervals gives >=95% simultaneous
    # coverage without assuming independence across knob rows or modes.
    m = len(curves)
    conf_each = 1.0 - 0.05 / m
    costs = _paired_cost_intervals()
    fully = 0
    for curve in curves:
        hits_float = curve["rarity"] * curve["rarity_n"]
        hits = round(hits_float)
        if not math.isclose(hits_float, hits, abs_tol=1e-8):
            raise AssertionError(f"rarity is not a count/n rate: {curve['key']}")
        rci = clopper_pearson_interval(hits, curve["rarity_n"], conf=conf_each)
        curve["rarity_hits"] = hits
        curve["rarity_ci_familywise95"] = [rci["lo"], rci["hi"]]
        curve["rarity_interval_method"] = (
            f"two-sided Clopper-Pearson at confidence {conf_each:.12g}; "
            f"Bonferroni over {m} estimands")
        planner_hits = round(curve["planner_reach"] * curve["planner_reach_n"])
        planner_ci = clopper_pearson_interval(
            planner_hits, curve["planner_reach_n"], conf=conf_each)
        curve["planner_reach_hits"] = planner_hits
        curve["planner_reach_ci_familywise95"] = [planner_ci["lo"], planner_ci["hi"]]
        curve["planner_to_gate_reach_ratio"] = (
            curve["planner_reach"] / curve["rarity"] if curve["rarity"] > 0 else None)
        curve["distribution_shift_note"] = (
            "planner reach and gate rarity are measured under different rollout laws; "
            "their ratio diagnoses shift but is not an extra multiplier in E[X|G]P(G)")
        cost_key = curve.get("cost_key", curve["key"])
        pci = costs.get(cost_key)
        curve["play_cost_ci"] = pci
        curve["danger"] = {}
        for n in curve["budgets"]:
            point = curve["play_cost"] * (1 - curve["rarity"]) ** n
            rarity_only = danger_interval((curve["play_cost"], curve["play_cost"]),
                                          tuple(curve["rarity_ci_familywise95"]), n)
            rec = {"point": point, "rarity_only_familywise95": list(rarity_only)}
            if pci is not None:
                if not math.isclose(pci["point"], curve["play_cost"], rel_tol=0, abs_tol=1e-9):
                    raise AssertionError(f"paired triples do not reproduce {cost_key}")
                rec["all_estimated_factors_band"] = list(danger_interval(
                    tuple(pci["ci95_pointwise"]), tuple(curve["rarity_ci_familywise95"]), n))
                rec["coverage_note"] = (
                    "rarity is family-wise 95%; play-cost is pointwise 95%; "
                    "the corner band is conservative factor propagation, not a calibrated joint 95% band")
            else:
                rec["all_estimated_factors_band"] = None
                rec["coverage_note"] = (
                    "not estimable from aggregate JSON: per-episode paired returns are absent; "
                    "the rarity-only interval must not be presented as full danger uncertainty")
            curve["danger"][str(n)] = rec
        fully += pci is not None

    return {
        "schema_version": "danger-law-h4/v1",
        "script": "scripts/danger_law_h4.py",
        "evidence_label": "proved for identities/bounds; measured for curve inputs",
        "common_law": {
            "tuple": ["critical-event miss probability", "conditional shipped play cost",
                      "planner-versus-gate distribution shift", "factorization hypotheses"],
            "risk_identity": "E[X 1_G] = P(G) E[X|G]",
            "adaptive_chain_rule": "P(no E_1,...,no E_N) = product_i (1-r_i), where r_i=P(E_i | previous misses)",
            "iid_corollary": "r_i=r gives (1-r)^N",
            "independent_train_gate_corollary": "same r and independent blocks give (1-r)^(N_train+N_gate)",
            "stratified_corollary": "known stratum hazards give product_i (1-r_i)",
            "adaptive_bound": "if lower_i <= r_i(history) <= upper_i along miss histories, product(1-upper_i) <= P(miss) <= product(1-lower_i)",
            "failure_limit": "marginal hazards P(E_i) alone do not identify miss probability under dependence/adaptation",
            "two_mode_corollary": "Frechet union bounds followed by the same iid exponent",
            "distribution_shift_role": "the gate hazard is measured under its rollout law; planner reach and conditional shipped cost determine consequence, not the miss exponent",
        },
        "uncertainty": {
            "rarity_family_size": m,
            "rarity_family_coverage": 0.95,
            "play_cost_available_cells": sorted(costs),
            "fully_propagated_curve_count": fully,
            "total_curve_count": m,
            "explicit_gap": (
                "Full factor uncertainty is available only where committed paired episode triples reproduce the published cell. "
                "Other rows require versioned per-episode triples; aggregate means cannot recover a valid play-cost interval."),
        },
        "curves": curves,
    }


def main() -> None:
    data = build()
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['curves'])} curve/event rows")


if __name__ == "__main__":
    main()
