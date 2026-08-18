"""Independent checks for scripts/danger_law_h4.py."""
from __future__ import annotations

import importlib.util
import itertools
import json
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("danger_law_h4", ROOT / "scripts" / "danger_law_h4.py")
H4 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(H4)


def test_adaptive_chain_rule_against_enumerated_binary_tree():
    # Hazards along the only history relevant to total miss.  Other branches
    # can be arbitrary and cannot change P(000).
    hazards = [0.2, 0.7, 0.4]
    p000 = (1 - hazards[0]) * (1 - hazards[1]) * (1 - hazards[2])
    assert H4.chain_miss(hazards) == pytest.approx(p000)
    # Explicitly enumerate a valid adaptive binary tree.
    total = 0.0
    for bits in itertools.product((0, 1), repeat=3):
        p = 1.0
        missed_so_far = True
        for i, bit in enumerate(bits):
            h = hazards[i] if missed_so_far else (0.1 + 0.2 * i)
            p *= h if bit else 1 - h
            missed_so_far &= bit == 0
        total += p
    assert total == pytest.approx(1.0)


def test_adaptive_bounds_are_sharp_and_ordered():
    lo, hi = H4.bounded_adaptive_miss([.1, .2, .3], [.2, .4, .5])
    assert lo == pytest.approx(.8 * .6 * .5)
    assert hi == pytest.approx(.9 * .8 * .7)
    assert lo <= hi


@pytest.mark.parametrize("r,n", [(0.0, 40), (.125, 7), (1.0, 3)])
def test_iid_is_chain_rule_corollary(r, n):
    assert H4.chain_miss([r] * n) == pytest.approx((1 - r) ** n)


def test_train_gate_exponents_add():
    r, nt, ng = .03, 12, 17
    assert H4.chain_miss([r] * nt) * H4.chain_miss([r] * ng) == pytest.approx((1-r) ** (nt+ng))


def test_frechet_bracket_contains_every_two_mode_coupling_and_attains_ends():
    r1, r2, n = .35, .55, 4
    got_lo, got_hi = H4.frechet_two_mode_miss(r1, r2, n)
    p11_lo, p11_hi = max(0, r1 + r2 - 1), min(r1, r2)
    values = []
    for j in range(101):
        p11 = p11_lo + (p11_hi - p11_lo) * j / 100
        values.append((1 - (r1 + r2 - p11)) ** n)
    assert min(values) == pytest.approx(got_lo)
    assert max(values) == pytest.approx(got_hi)


def test_danger_interval_contains_all_corners():
    lo, hi = H4.danger_interval((.8, 1.2), (.01, .04), 40)
    vals = [c * (1-r)**40 for c in (.8, 1.2) for r in (.01, .04)]
    assert lo == pytest.approx(min(vals))
    assert hi == pytest.approx(max(vals))


def test_exact_binomial_interval_boundary_closed_forms():
    n, conf = 20, .95
    alpha2 = (1-conf) / 2
    zero = H4.clopper_pearson_interval(0, n, conf)
    full = H4.clopper_pearson_interval(n, n, conf)
    assert zero["lo"] == 0
    assert zero["hi"] == pytest.approx(1-alpha2**(1/n), rel=1e-10)
    assert full["lo"] == pytest.approx(alpha2**(1/n), rel=1e-10)
    assert full["hi"] == 1


def test_build_is_complete_about_its_incompleteness_and_reproduces_points():
    out = H4.build()
    assert out["schema_version"] == "danger-law-h4/v1"
    assert out["uncertainty"]["total_curve_count"] == len(out["curves"]) == 40
    assert out["uncertainty"]["fully_propagated_curve_count"] == 5
    assert out["uncertainty"]["fully_propagated_curve_count"] < len(out["curves"])
    for curve in out["curves"]:
        assert curve["rarity_ci_familywise95"][0] <= curve["rarity"] <= curve["rarity_ci_familywise95"][1]
        assert curve["planner_reach_ci_familywise95"][0] <= curve["planner_reach"] <= curve["planner_reach_ci_familywise95"][1]
        if curve["rarity"] > 0:
            assert curve["planner_to_gate_reach_ratio"] == pytest.approx(
                curve["planner_reach"] / curve["rarity"])
        for n, rec in curve["danger"].items():
            expected = curve["play_cost"] * (1-curve["rarity"])**int(n)
            assert rec["point"] == pytest.approx(expected)
            a, b = rec["rarity_only_familywise95"]
            assert a <= expected <= b
            assert (rec["all_estimated_factors_band"] is not None) == (curve["play_cost_ci"] is not None)


def test_versioned_result_is_fresh():
    expected = H4.build()
    committed = json.loads((ROOT / "results" / "danger_law_h4.json").read_text())
    assert committed == expected
