"""Guards for the measurements that used to have no committed artifact.

These do NOT re-run the emitters (they are million-rollout jobs). They assert
the STRUCTURAL properties of the emitted JSONs -- the ones a document could
silently drift from, and the ones whose direction is load-bearing. A guard that
merely re-asserted a stored number would be a tautology; each of these would
fail if the corresponding claim in docs/paper3/ became false.

No fudge factors: where a quantity is sampled, the assertion is on a confidence
limit or on an exact structural relation, never on a multiplier.
"""
import json
import math
import pathlib

import pytest

_RES = pathlib.Path(__file__).resolve().parents[1] / "results"


def _load(name):
    p = _RES / name
    if not p.exists():
        pytest.skip(f"{name} not emitted in this checkout")
    return json.loads(p.read_text())


def test_t3_reach_off_by_one_is_recorded_both_ways():
    # The published R' is the "leaves k-1 steps" reading. Both must be present,
    # and the k-step reading must be the SMALLER one (a tighter deadline can
    # only admit fewer arrivals) -- if that ordering ever inverts, one of the
    # two index conventions has been misapplied.
    cells = _load("t3_unrecorded_measurements.json")["cells"]
    r = next(v for k, v in cells.items() if k.startswith("reach|"))
    k_steps = r["R_prime_leaving_k_steps"]
    km1 = r["R_prime_leaving_k_minus_1_steps"]
    assert k_steps < km1 <= r["R"], (k_steps, km1, r["R"])
    # And both are strictly below R: the deadline costs something.
    assert km1 < r["R"]


def test_t3_crossing_duration_p90_exceeds_the_median_k():
    # The horizon term "vanishes" only if k bounds the crossing. It does not:
    # k = 9 is the median, so p90 must exceed it -- that gap IS the residue.
    cells = _load("t3_unrecorded_measurements.json")["cells"]
    for key, v in cells.items():
        if not key.startswith("corridor|"):
            continue
        assert "P_corridor_satisfied_by_radius" in v, (
            "a corridor cell without the per-radius split is a superseded "
            "estimand and must not linger: " + key)
        d = v.get("crossing_duration")
        if d is None:
            continue
        assert d["p90"] > v["k_cross_used"], (key, d)
        assert d["max"] > d["p90"]


def test_t3_arrival_angle_density_peaks_at_pi():
    # rho(pi) is the MAXIMUM, which is why substituting it into a LOWER bound
    # overstates the factor. If the profile ever stopped peaking at pi, the
    # direction of that correction would flip.
    cells = _load("t3_unrecorded_measurements.json")["cells"]
    p = next(v for k, v in cells.items()
             if k.startswith("profile|") and "per_gap" in v)
    dens = [b["density_per_rad"] for b in p["profile"]]
    assert dens[0] == max(dens), dens[:5]
    assert p["rho_at_pi"] == dens[0]


def test_t3_f0_folded_is_exactly_twice_signed():
    # The bound is on the signed density, the criterion consumes the folded
    # one. Mixing them is a factor 2, so the relation is asserted exactly.
    cells = _load("t3_unrecorded_measurements.json")["cells"]
    for key, v in cells.items():
        if not key.startswith("corridor|"):
            continue
        for row in v["f0"]:
            assert math.isclose(row["f0_folded"], 2 * row["f0_signed"],
                                rel_tol=1e-12), (key, row)


def test_t3_steering_jumps_dwarf_the_differentiable_sup():
    # The derivative series is restricted to arrival-step-preserving pairs
    # (the only place theta is differentiable). The excluded jumps are an order
    # of magnitude larger, which is why the filter has to be recorded: quoting
    # the unfiltered max would inflate Lemma D's denominator many-fold.
    cells = _load("t3_unrecorded_measurements.json")["cells"]
    st = next((v for k, v in cells.items()
               if k.startswith("steering|") and "arrival_step_changed" in v),
              None)
    if st is None:
        pytest.skip("steering cell not emitted with the jump split")
    # A cell WITHOUT the split must not linger beside one that has it: the two
    # are different estimands and a document could quote the wrong one.
    assert not any(k.startswith("steering|") and "arrival_step_changed" not in v
                   for k, v in cells.items())
    assert st["max"] < st["arrival_step_changed"]["max"]
    # A percentile is not a supremum: the gap must be visible, not assumed.
    assert st["p90"] <= st["max"]
    # Lemma D's factor is the UNCONDITIONAL root probability, which is the
    # smaller of the two and therefore the conservative one.
    assert st["P_root_exists"] <= st["P_root_exists_given_reaching"]


def test_t2_clean_step_chain_needs_both_terms():
    # Dropping the first term leaves a bound that FAILS often; with both terms
    # it holds on every dirty step. Both counts must stay on their side of
    # that line, or the "both terms are needed" claim has lost its evidence.
    s = _load("t2_unrecorded_measurements.json")["summary"]
    both = int(s["chain_both_terms"].split("/")[0])
    dropped = int(s["chain_first_term_dropped"].split("/")[0])
    n = s["n_dirty_steps"]
    assert both == n, s["chain_both_terms"]
    assert dropped < n, s["chain_first_term_dropped"]


def test_t2_replanning_link_is_not_a_theorem():
    # A guard on a REFUTED claim: if this ever reached n/n, the refutation
    # would have to be revisited rather than silently kept.
    s = _load("t2_unrecorded_measurements.json")["summary"]
    ok = int(s["replanning_link"].split("/")[0])
    n = s["n_dirty_steps"]
    assert ok < n, s["replanning_link"]
    w = s["replanning_link_worst"]
    assert w["A_t"] > w["candidate_gap"] and w["excess"] > 0


def test_t2_censored_zeros_carry_their_interval():
    # 0/18 is not a guarantee. The Wilson upper limit must be present and
    # well away from 0, so nobody reads the zero as a proof.
    s = _load("t2_unrecorded_measurements.json")["summary"]
    for key in ("left_basin_wilson_95", "mpc_no_later_wilson_95"):
        lo, hi = s[key]
        assert lo == 0.0 and hi > 0.1, (key, s[key])


def test_t2_conditional_spread_survives_zero_slack():
    # Prop T2-D's point: the spread is not the bound's slack term. The chosen
    # step has Delta_over = 0, so the spread cannot be attributed to it.
    cells = _load("t2_unrecorded_measurements.json")["cells"]
    c = next(v for k, v in cells.items()
             if k.startswith("conditional_spread|"))
    assert abs(c["Delta_over"]) < 1e-9, c["Delta_over"]
    assert c["A_t_spread"] > 1.0, c


def test_t2_switch_rate_closure_condition_is_dimensional():
    # The closure condition is p(delta)*2*gain*dt < delta -- a displacement
    # against a displacement. Assert the comparison is made that way (not
    # against 1) and that the emitted verdict agrees with recomputing it.
    cells = _load("t2_drag_cap_and_switch_rate.json")["cells"]
    sw = next(v for k, v in cells.items() if k.startswith("switch_rate|"))
    for row in sw["rows"]:
        assert row["closes"] == (row["p_times_2_gain_dt"] < row["eps"]), row
        if row["closes"]:
            assert row["L_v_multiplier"] > 1.0, row


def test_t2_drag_cap_holds_at_every_emitted_sample_size():
    # The cap is a THEOREM, so no sample may exceed it; and it must be nearly
    # attained, or the "tight to 3%" claim is unsupported.
    cells = _load("t2_drag_cap_and_switch_rate.json")["cells"]
    seen = 0
    for key, v in cells.items():
        if not key.startswith("drag_cap|"):
            continue
        seen += 1
        assert v["worst_observed"] <= v["cap"] + 1e-9, (key, v)
        assert v["tightness"] > 0.9, (key, v["tightness"])
    assert seen >= 2, "both the documented and the guard sample size"


def test_t7_margin_variant_degenerates_to_plain_rips():
    # The margin-0.3 variant was rejected for SPECIFICITY. The emitted
    # mechanism is sharper: at margin 0.3 it censors no edges at all, so it
    # must agree with plain Rips everywhere.
    d = _load("t7_margin_variant_betti.json")
    cells = d["cells"]
    strict = [v for k, v in cells.items()
              if k.startswith("0.3|") and "skipped" not in v]
    if not strict:
        pytest.skip("margin 0.3 cells not emitted")
    for v in strict:
        assert v["edges_censored"] == 0, v
        assert v["censored_betti1"] == v["plain_betti1"], v
    # ... and therefore it is wrong wherever plain Rips is wrong: the open ring.
    open_ring = [v for v in strict if v["gap"] > 0]
    assert open_ring and all(v["censored_betti1"] != v["true_betti1"]
                             for v in open_ring)
    # The v1 rule, by contrast, does censor a great many edges.
    v1 = [v for k, v in cells.items()
          if k.startswith("0.0|") and "skipped" not in v]
    assert v1 and min(v["edges_censored"] for v in v1) > 100


def test_t5f_prime_respects_its_own_side_condition():
    # The whole point of T5-F': the Z_1 factor's Hoeffding form is valid only
    # while 2*lambda*g2*sigma_1^2 < 1, i.e. K < K_max. T5-F chose K = 10 and
    # violated it. Any assembled bound must satisfy it strictly.
    d = _load("t5f_z1_factor.json")
    for name in ("nominal", "L_min"):
        a = d.get(f"assembled_{name}")
        if not a or not a.get("feasible"):
            continue
        assert a["K"] < a["side_condition_K_max"], (name, a)
        # The Z_1 factor blows up at the boundary, so it must be finite and > 1.
        assert 1.0 < a["Z1_factor"] < float("inf"), (name, a)
        # The norm tail must stay SUBDOMINANT, or it becomes the real rate.
        assert a["norm_tail_rate"] < a["dominant_rate"], (name, a)
        # Carrying Z_1 costs rate: the repaired rate is worse than the
        # Pi-side-only 0.9104 it replaces. If it ever came out better, the
        # factor has been dropped again.
        assert a["dominant_rate"] > 0.9104, (name, a)


def test_t5f_truncation_beats_the_counting_bound_by_orders():
    # The floor exists (it is irremovable within the scheme), but replacing
    # exchangeability's 1/K by concentration is what makes it negligible.
    # If that ever regressed, the "floor is 1e-13 not 0.12" claim would go.
    d = _load("t5f_z1_factor.json")
    rows = d["truncation_theorem"]["rows"]
    for r in rows:
        if r["K"] >= 3.0 and r["nu"] >= 0.20:
            assert r["n_free_term"] < 1e-6 * (1.0 / r["K"]), r
    # And the certified term is n-FREE: it depends on the weights, not on n.
    assert d["truncation_theorem"]["E_eff"] > 1.0


def test_t7_union_h1_measures_the_estimator_s_own_input():
    # The equality hypothesis must be tested on the cloud the estimator
    # CONSUMES (deduped and capped), not on the raw positions -- those are
    # different complexes, and a beta_1 measured on the wrong one is what put
    # a 114-166 figure into the paper.
    d = _load("t7_union_h1.json")
    for key, c in d["cells"].items():
        assert c["n_free_points"] <= c["cap"], (key, c)
        assert c["n_free_raw"] > c["n_free_points"], (
            "the raw cloud must be strictly larger, or the cap did nothing")
        # As measured, equality holds on every cell: the free-merge count
        # coincides with the relative rank there.
        assert c["equality_hypothesis_holds"], (key, c["scales"])


def test_t7_exhibit_shows_the_two_ranks_can_differ():
    # A guard on the reason the estimator is reported as a LOWER bound: the
    # circle-plus-centre exhibit must keep free-merge 0 against relative rank
    # >= 1 at every scale. If this ever came out equal, the lower-bound
    # framing would no longer be justified by anything.
    d = _load("t7_union_h1.json")
    ex = d["exhibit"]
    assert ex["free_merge_count"] == 0
    assert ex["scales"], "the exhibit must report at least one scale"
    for r in ex["scales"]:
        assert r["lower_bound_on_relative_rank"] >= 1, r
        assert r["betti1_K"] > r["betti1_L"], r
