"""Tests for the by-experimental-unit statistics layer (review point #5).

Three things are checked, and each one is checked against something that is not
the code under test:

  1. Clopper-Pearson is validated by TWO independent oracles: the closed forms at
     the k=0 / k=n boundaries, and numerical quadrature of the Beta(k, n-k+1) /
     Beta(k+1, n-k) densities (the CP interval IS a Beta quantile pair). Neither
     oracle touches `clopper_pearson`'s bisection or its binomial tails. Fisher's
     exact test is validated against an exhaustive enumeration of permutations of
     a small table, which shares no code with the hypergeometric implementation.

  2. A SYNTHETIC campaign is built with a block/draw divergence of known size,
     and the script must report both numbers correctly: the block-level bound and
     the naive draw-level one.

  3. The refusal: pooling at draw level over shared blocks must RAISE, and must
     only be obtainable as the explicitly labelled comparator.

Every test that exercises an interesting branch asserts that the branch really
was exercised (e.g. that the synthetic sample truly has shared blocks, that the
real campaign really does contain a mode contact and a non-repaired draw).
"""
import json
import math
import pathlib
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

import paper2_statistics as P  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. the interval machinery, against independent oracles                      #
# --------------------------------------------------------------------------- #
def _beta_pdf(x, a, b):
    return (math.gamma(a + b) / (math.gamma(a) * math.gamma(b))
            * x ** (a - 1) * (1 - x) ** (b - 1))


def _beta_cdf_quadrature(x, a, b, n=200_001):
    """Integral of the Beta(a, b) density on [0, x] by Simpson's rule. This is
    an ORACLE: it evaluates a gamma-function formula and never calls the binomial
    tails or the bisection that clopper_pearson uses."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    h = x / (n - 1)
    total = 0.0
    for i in range(n):
        xi = min(max(i * h, 1e-15), x - 1e-15) if 0 < i < n - 1 else \
            (1e-15 if i == 0 else x - 1e-15)
        w = 1 if i in (0, n - 1) else (4 if i % 2 else 2)
        total += w * _beta_pdf(xi, a, b)
    return total * h / 3.0


@pytest.mark.parametrize("k,n", [(3, 10), (7, 20), (1, 5), (19, 22), (12, 40)])
def test_clopper_pearson_matches_beta_quantile_oracle(k, n):
    """CP lower = Beta(k, n-k+1) quantile at alpha/2; CP upper =
    Beta(k+1, n-k) quantile at 1-alpha/2. Verified by quadrature."""
    _, lo, hi = P.clopper_pearson(k, n, alpha=0.05)
    assert 0.0 < lo < k / n < hi < 1.0
    assert _beta_cdf_quadrature(lo, k, n - k + 1) == pytest.approx(0.025, abs=2e-4)
    assert _beta_cdf_quadrature(hi, k + 1, n - k) == pytest.approx(0.975, abs=2e-4)


@pytest.mark.parametrize("n", [3, 20, 22, 34, 156])
def test_clopper_pearson_boundaries_match_closed_form(n):
    """At k=0 the exact upper limit is 1-(alpha/2)^(1/n) and at k=n the exact
    lower limit is (alpha/2)^(1/n). Independent of any binomial summation."""
    _, lo0, hi0 = P.clopper_pearson(0, n)
    assert lo0 == 0.0
    assert hi0 == pytest.approx(1.0 - 0.025 ** (1.0 / n), rel=1e-12)
    _, lon, hin = P.clopper_pearson(n, n)
    assert hin == 1.0
    assert lon == pytest.approx(0.025 ** (1.0 / n), rel=1e-12)


def test_clopper_pearson_defining_tail_identity():
    """The definition itself: P(X >= k | p = lo) = alpha/2 and
    P(X <= k | p = hi) = alpha/2. Checked with a tail written out here."""
    def tail_ge(k, n, p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                   for i in range(k, n + 1))

    def tail_le(k, n, p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                   for i in range(0, k + 1))

    for k, n in ((4, 15), (18, 22), (2, 9)):
        _, lo, hi = P.clopper_pearson(k, n)
        assert tail_ge(k, n, lo) == pytest.approx(0.025, abs=1e-9)
        assert tail_le(k, n, hi) == pytest.approx(0.025, abs=1e-9)


def _coverage(intervals, n, p):
    """Exact coverage of an interval procedure at (n, p): sum the binomial
    probability of every k whose interval contains p. `intervals` is the
    precomputed [(lo, hi)] list indexed by k. Enumerated exactly."""
    return math.fsum(math.comb(n, k) * p ** k * (1 - p) ** (n - k)
                     for k, (lo, hi) in enumerate(intervals) if lo <= p <= hi)


def test_clopper_pearson_has_guaranteed_coverage_where_wilson_does_not():
    """The reason to quote the exact interval, verified rather than asserted: CP
    coverage never falls below 95% at any p, while Wilson's does. Coverage is
    computed by exhaustive enumeration of the binomial -- an oracle that shares
    no code with either interval."""
    from cwm.law import wilson_ci

    grid = [i / 200 for i in range(1, 200)]
    wilson_dips = 0
    for n in (20, 22):
        cp = [P.clopper_pearson(k, n)[1:] for k in range(n + 1)]
        wil = [wilson_ci(k, n)[1:] for k in range(n + 1)]
        for p in grid:
            assert _coverage(cp, n, p) >= 0.95 - 1e-9, (n, p)
            if _coverage(wil, n, p) < 0.95 - 1e-9:
                wilson_dips += 1
    assert wilson_dips > 0, ("Wilson never undercovered on the grid; the test "
                             "would not be distinguishing the two procedures")


def test_clopper_pearson_contains_wilson_at_the_small_n_boundary():
    """At the n the paper actually quotes for the 2D negative result (20 blocks)
    the exact bound is the WIDER one, so switching to it cannot flatter the
    result. (This is not universal: at n = 156 the Wilson upper limit at k = 0
    is the wider of the two, which is one more reason not to mix procedures.)"""
    from cwm.law import wilson_ci
    _, cp_lo, cp_hi = P.clopper_pearson(0, 20)
    _, w_lo, w_hi = wilson_ci(0, 20)
    assert cp_hi > w_hi
    _, cp_lo2, _ = P.clopper_pearson(20, 20)
    _, w_lo2, _ = wilson_ci(20, 20)
    assert cp_lo2 < w_lo2


def test_fisher_exact_against_exhaustive_permutation_oracle():
    """Fisher's p is the permutation p-value of the 2x2 table. Enumerate every
    assignment of the row-1 labels to the columns explicitly and compare."""
    import itertools
    a, b, c, d = 5, 1, 2, 4          # a table with a real association
    n, row1, col1 = a + b + c + d, a + b, a + c
    counts = {}
    for combo in itertools.combinations(range(n), row1):
        x = len([i for i in combo if i < col1])   # first col1 items are "col 1"
        counts[x] = counts.get(x, 0) + 1
    total = sum(counts.values())
    probs = {x: cnt / total for x, cnt in counts.items()}
    p_obs = probs[a]
    oracle = sum(p for x, p in probs.items() if p <= p_obs * (1 + 1e-12))
    assert P.fisher_exact_2x2(a, b, c, d) == pytest.approx(oracle, abs=1e-12)
    assert oracle < 0.5, "oracle table has no association; test would be weak"


def test_fisher_exact_no_association_is_one():
    assert P.fisher_exact_2x2(5, 5, 5, 5) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 2. a synthetic campaign with a KNOWN block/draw divergence                   #
# --------------------------------------------------------------------------- #
def _draw(block, treatment, model, ok, mode_present=True):
    """One synthetic draw. `treatment` varies knob only, so all draws share the
    instrument and the same block ids -- exactly the real design."""
    return {
        "file": "synthetic.json", "instrument": "cart",
        "knob": {"x_wall": float(treatment)}, "patch_shape": None,
        "prompt_variant": "default", "max_iters": 5, "arm": "incomplete",
        "model": model, "size": model, "family": "gpt-5.x",
        "seed": block * 10_000, "block": block,
        "mode_present": mode_present, "mode_present_per": None,
        "n_modes_seen": int(mode_present), "gate_passed": ok,
        "gate_accuracy": 1.0 if ok else 0.5,
        "blindness": 0.0 if ok else None, "per_mode_blindness": None,
        "play_cost": None, "refine_iterations": 0 if ok else 5,
        "outcome": "repaired" if ok else "rejected_stalled",
    }


def synthetic_campaign():
    """10 blocks. Each block gets 4 draws: 2 knobs x 2 models. Blocks 1 and 2
    have exactly ONE failing draw each (the other three succeed); every other
    draw succeeds.

    Known truth by construction:
      draws            : 40, of which 38 succeed
      blocks, 'all'    : 10, of which 8 succeed (blocks 1, 2 contain a failure)
      blocks, 'any'    : 10, of which 10 succeed
    """
    draws = []
    for block in range(1, 11):
        for treatment in (4, 8):
            for model in ("mini", "large"):
                fail = (block in (1, 2) and treatment == 4 and model == "mini")
                draws.append(_draw(block, treatment, model, not fail))
    return draws


def test_synthetic_campaign_has_the_structure_the_test_needs():
    """Non-vacuity: the synthetic set really does share blocks across
    treatments, and really does contain failures."""
    draws = synthetic_campaign()
    assert len(draws) == 40
    per_block = {}
    for d in draws:
        per_block.setdefault(d["block"], []).append(d)
    assert len(per_block) == 10
    assert all(len(v) == 4 for v in per_block.values()), "blocks must be shared"
    assert sum(1 for d in draws if not P.is_repair(d)) == 2
    assert len({P.treatment_key(d) for d in draws}) == 2, "two treatments"


def test_block_and_draw_bounds_differ_by_the_known_amount():
    draws = synthetic_campaign()

    block_all = P.pooled_bound(draws, P.is_repair, unit="block", scoring="all")
    assert (block_all["k"], block_all["n"]) == (8, 10)
    assert block_all["n_draws"] == 40
    assert block_all["n_distinct_blocks"] == 10
    assert block_all["max_draws_per_block"] == 4
    assert block_all["valid_for_paper"] is True

    block_any = P.pooled_bound(draws, P.is_repair, unit="block", scoring="any")
    assert (block_any["k"], block_any["n"]) == (10, 10)

    naive = P.pooled_bound(draws, P.is_repair, unit="draw", comparator=True)
    assert (naive["k"], naive["n"]) == (38, 40)
    assert naive["valid_for_paper"] is False
    assert "INVALID-IF-POOLED" in naive["label"]

    # the intervals must match independently computed exact values
    assert block_all["clopper_pearson_95"] == pytest.approx(
        list(P.clopper_pearson(8, 10)[1:]), abs=1e-9)
    assert naive["clopper_pearson_95"] == pytest.approx(
        list(P.clopper_pearson(38, 40)[1:]), abs=1e-9)

    # and the divergence must be large: the naive lower bound is far above the
    # honest one, which is the entire point of review point #5
    honest_lo = block_all["clopper_pearson_95"][0]
    naive_lo = naive["clopper_pearson_95"][0]
    assert naive_lo > honest_lo + 0.35, (honest_lo, naive_lo)
    assert honest_lo == pytest.approx(0.4439, abs=5e-4)
    assert naive_lo == pytest.approx(0.8308, abs=5e-4)


def test_draw_level_pooling_over_shared_blocks_raises():
    draws = synthetic_campaign()
    with pytest.raises(P.SharedBlockPoolingError) as e:
        P.pooled_bound(draws, P.is_repair, unit="draw")
    msg = str(e.value)
    assert "40 draws" in msg and "10 distinct gate-sample blocks" in msg
    assert "2 treatment" in msg
    # and it is obtainable only by asking for the labelled comparator
    got = P.pooled_bound(draws, P.is_repair, unit="draw", comparator=True)
    assert got["valid_for_paper"] is False


def test_draw_level_pooling_is_allowed_when_blocks_are_disjoint():
    """The refusal must be about SHARED blocks, not about draw-level per se: one
    draw per block is a legitimate draw-level interval, and must equal the
    block-level one."""
    draws = [_draw(b, 8, "large", ok=(b != 3)) for b in range(1, 11)]
    ok = P.pooled_bound(draws, P.is_repair, unit="draw")
    assert ok["valid_for_paper"] is True
    assert ok["n_shared_blocks"] == 0
    same = P.pooled_bound(draws, P.is_repair, unit="block", scoring="all")
    assert (ok["k"], ok["n"]) == (same["k"], same["n"]) == (9, 10)
    assert ok["clopper_pearson_95"] == pytest.approx(same["clopper_pearson_95"])


def test_censored_zero_upper_bound_on_a_synthetic_all_failure_campaign():
    draws = [_draw(b, t, m, ok=False)
             for b in range(1, 21) for t in (4, 8) for m in ("mini", "large")]
    block = P.pooled_bound(draws, P.is_repair, unit="block", scoring="all")
    naive = P.pooled_bound(draws, P.is_repair, unit="draw", comparator=True)
    assert (block["k"], block["n"]) == (0, 20)
    assert (naive["k"], naive["n"]) == (0, 80)
    assert block["clopper_pearson_95"][1] == pytest.approx(
        1 - 0.025 ** (1 / 20), rel=1e-12)
    assert naive["clopper_pearson_95"][1] == pytest.approx(
        1 - 0.025 ** (1 / 80), rel=1e-12)
    assert block["clopper_pearson_95"][1] > 3 * naive["clopper_pearson_95"][1]


def test_scoring_and_unit_arguments_are_validated():
    draws = synthetic_campaign()
    with pytest.raises(ValueError):
        P.pooled_bound(draws, P.is_repair, unit="cell")
    with pytest.raises(ValueError):
        P.pooled_bound(draws, P.is_repair, unit="block", scoring="most")


def test_icc_is_reported_undefined_on_zero_variance_data():
    """The justification for NOT fitting a hierarchical model must be produced by
    the code, not asserted in prose: on all-success data the ANOVA ICC is 0/0."""
    draws = [_draw(b, t, "mini", ok=True) for b in range(1, 11) for t in (4, 8)]
    res = P.anova_icc(draws, P.is_repair)
    assert res["icc"] is None
    assert "zero variance" in res["reason"]
    # while on data with within-block disagreement it IS defined
    res2 = P.anova_icc(synthetic_campaign(), P.is_repair)
    assert res2["icc"] is not None and res2["design_effect"] >= 1.0
    assert res2["n_clusters"] == 10 and res2["n_draws"] == 40


def test_cluster_bootstrap_is_deterministic_and_cluster_level():
    draws = synthetic_campaign()
    a = P.cluster_bootstrap(draws, P.is_repair, n_boot=2000, seed=0)
    b = P.cluster_bootstrap(draws, P.is_repair, n_boot=2000, seed=0)
    assert a["percentile_95"] == b["percentile_95"]
    assert a["n_clusters"] == 10
    assert a["percentile_95"][0] < a["point_estimate"] <= a["percentile_95"][1]


def test_heterogeneity_detects_a_planted_treatment_difference():
    """Non-vacuity: plant a real difference between two treatments and require
    the test to see it; then plant none and require it not to."""
    diff = ([_draw(b, 8, "large", ok=True) for b in range(1, 21)]
            + [_draw(b, 4, "large", ok=False) for b in range(21, 41)])
    groups = {"x8": [d for d in diff if d["knob"]["x_wall"] == 8.0],
              "x4": [d for d in diff if d["knob"]["x_wall"] == 4.0]}
    res = P.heterogeneity_across_treatments(groups, P.is_repair)
    assert res["block_level_counts"]["x8"] == {"k": 20, "n": 20, "n_draws": 20}
    assert res["block_level_counts"]["x4"] == {"k": 0, "n": 20, "n_draws": 20}
    assert res["bonferroni_adjusted_p"] < 1e-9
    assert "not defensible" in res["verdict"]

    same = ([_draw(b, 8, "large", ok=True) for b in range(1, 21)]
            + [_draw(b, 4, "large", ok=True) for b in range(21, 41)])
    groups2 = {"x8": [d for d in same if d["knob"]["x_wall"] == 8.0],
               "x4": [d for d in same if d["knob"]["x_wall"] == 4.0]}
    res2 = P.heterogeneity_across_treatments(groups2, P.is_repair)
    assert res2["bonferroni_adjusted_p"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 3. the real campaigns                                                       #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def real_draws():
    return P.load_draws()


def test_block_id_is_the_seed_block():
    assert P.block_of(10_000) == 1
    assert P.block_of(200_000) == 20
    assert P.block_of(210_000) == 21    # the --seed-offset 20 re-run
    assert P.block_of(400_000) == 40


def test_real_campaign_branches_are_actually_populated(real_draws):
    """Non-vacuity for everything that follows: the loaded table must contain a
    mode contact, a mode-absent sample, a repair, a non-repair, a rejected
    artifact and a blind-and-exploited artifact."""
    outcomes = {d["outcome"] for d in real_draws}
    for wanted in ("repaired", "blind_and_exploited", "rejected_stalled",
                   "control_translated"):
        assert wanted in outcomes, wanted
    assert any(d["mode_present"] for d in real_draws)
    assert any(not d["mode_present"] for d in real_draws)
    assert any(d["mode_present_per"] and sum(d["mode_present_per"].values()) == 1
               for d in real_draws), "no see-one-miss-the-other draw loaded"
    assert any(d["mode_present"] and not P.is_repair(d) for d in real_draws)


def test_1d_repair_counts_reproduce_the_paper_and_then_correct_the_unit(real_draws):
    one = [d for d in real_draws
           if d["instrument"] in ("cart", "pendulum") and d["arm"] == "incomplete"
           and d["family"] == "gpt-5.x" and d["mode_present"]]
    # 105, not the 109 the mode-probe criterion reports: four artifacts pass the probe
    # while carrying an INVENTED second stop, which a probe firing only where the truth's
    # mode is active cannot see (results/repair_exactness_1d.json). is_repair consults
    # that audit, so this asserts the corrected count and, below, that the correction is
    # exactly four.
    assert (sum(1 for d in one if P.is_repair(d)), len(one)) == (105, 111)
    probe_only = sum(1 for d in one
                     if d["gate_passed"] and (d["blindness"] or 0.0) == 0.0
                     and not P.is_repair(d))
    assert probe_only == 4, "the probe/behaviour gap must be exactly the audited four"
    # ... over how many blocks?
    assert len({d["block"] for d in one}) == 36
    assert len({(d["instrument"], d["block"]) for d in one}) == 56
    agg = P.pooled_bound(one, P.is_repair, unit="block", scoring="all")
    assert (agg["k"], agg["n"]) == (30, 36)
    with pytest.raises(P.SharedBlockPoolingError):
        P.pooled_bound(one, P.is_repair, unit="draw")


def test_cart_is_not_all_repair_at_block_level(real_draws):
    """The specific correction: the paper's 0.851 cart bound assumes every block
    repaired. Two draws did not, so conservative ('all') scoring gives 20/22, not
    22/22 -- and even the optimistic ('any') scoring gives 21/22, because one of
    the two failures is the ONLY mode-present cart draw its block ever had (at
    x_wall = 8 that block's sample misses the wall entirely)."""
    cart = [d for d in real_draws if d["instrument"] == "cart"
            and d["arm"] == "incomplete" and d["family"] == "gpt-5.x"
            and d["mode_present"]]
    allsc = P.pooled_bound(cart, P.is_repair, unit="block", scoring="all")
    anysc = P.pooled_bound(cart, P.is_repair, unit="block", scoring="any")
    assert (allsc["k"], allsc["n"]) == (20, 22)
    assert (anysc["k"], anysc["n"]) == (21, 22)
    assert anysc["clopper_pearson_95"][0] > allsc["clopper_pearson_95"][0]
    # non-vacuity: 'all' and 'any' must actually disagree here, which needs one
    # failing draw to share its block with a repaired one and one not to
    bad = [d for d in cart if not P.is_repair(d)]
    assert len(bad) == 2
    sizes = sorted(sum(1 for x in cart if x["block"] == d["block"]) for d in bad)
    assert sizes == [1, 3], sizes


# The three treatments the paper's 0/156 pools. Named explicitly, because later campaigns
# (the trigger-arity slab, the landing-variable arm) are FURTHER treatments on the same
# blocks and must not silently enlarge an aggregate the paper quotes.
_NEGATIVE_TREATMENTS = ("continuous_synthesis_patch2d_mini_k3_7.json",
                        "continuous_synthesis_patch2d_large_k3_7.json",
                        "continuous_synthesis_patch2d_mini_k5_9.json",
                        "continuous_synthesis_patch2d_large_k5_9.json",
                        "continuous_synthesis_patch2dsq_mini_k3_7.json",
                        "continuous_synthesis_patch2dsq_large_k3_7.json",
                        "continuous_synthesis_patch2d_mini_k3_7_pv-region_it15.json",
                        "continuous_synthesis_patch2d_large_k3_7_pv-region_it15.json")


def test_patch2d_negative_is_156_draws_over_20_blocks(real_draws):
    p2d = [d for d in real_draws if d["instrument"] == "patch2d"
           and d["arm"] == "incomplete" and d["family"] == "gpt-5.x"
           and d["mode_present"] and d["file"] in _NEGATIVE_TREATMENTS]
    assert len(p2d) == 156, (
        "the 0/156 aggregate must stay the disc + square + guided treatments; a new "
        "campaign on the same blocks is a further treatment, not more of this one")
    assert sum(1 for d in p2d if P.is_repair(d)) == 0
    assert len({d["block"] for d in p2d}) == 20
    b = P.pooled_bound(p2d, P.is_repair, unit="block", scoring="all")
    assert (b["k"], b["n"]) == (0, 20)
    assert b["clopper_pearson_95"][1] == pytest.approx(1 - 0.025 ** (1 / 20),
                                                       rel=1e-12)
    naive = P.pooled_bound(p2d, P.is_repair, unit="draw", comparator=True)
    assert (naive["k"], naive["n"]) == (0, 156)
    assert naive["clopper_pearson_95"][1] == pytest.approx(
        1 - 0.025 ** (1 / 156), rel=1e-12)
    assert b["clopper_pearson_95"][1] > 7 * naive["clopper_pearson_95"][1]


def test_claude_2d_arm_adds_draws_but_no_new_blocks(real_draws):
    gpt_blocks = {d["block"] for d in real_draws
                  if d["instrument"] == "patch2d" and d["family"] == "gpt-5.x"}
    cl = [d for d in real_draws if d["instrument"] == "patch2d"
          and d["family"] == "claude" and d["arm"] == "incomplete"]
    assert cl, "the Claude patch2d arm did not load"
    assert {d["block"] for d in cl} <= gpt_blocks


def test_every_cell_holds_at_most_one_draw_per_block(real_draws):
    """The structural fact that makes a per-cell bound automatically block-level.
    treatment_table asserts it too; assert it here independently."""
    seen = {}
    for d in real_draws:
        key = (P.treatment_key(d), d["model"], d["block"])
        assert key not in seen, f"duplicate draw for {key}"
        seen[key] = True
    assert len(seen) == len(real_draws) > 500


# --------------------------------------------------------------------------- #
# 4. the emitted JSON                                                          #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def report(real_draws):
    return P.build_report(real_draws)


def test_report_declares_the_unit_hierarchy(report):
    uh = report["unit_hierarchy"]
    assert uh["primary_unit"]["name"] == "gate-sample block"
    assert "seed_offset" in uh["primary_unit"]["identified_by"]
    assert uh["secondary_unit"]["identified_by"] == "(block, treatment, model)"
    for word in ("instrument", "knob", "patch shape", "prompt variant"):
        assert word in uh["treatment"]["identified_by"]


def test_report_labels_every_invalid_comparator(report):
    """Walk the whole document: anything with valid_for_paper False must carry
    the label, and anything at draw level over shared blocks must be invalid."""
    found = 0

    def walk(node):
        nonlocal found
        if isinstance(node, dict):
            if "unit" in node and "valid_for_paper" in node:   # a pooled_bound
                if node["unit"] == "draw" and node["n_shared_blocks"] > 0:
                    assert node["valid_for_paper"] is False
                    assert "INVALID-IF-POOLED" in node["label"]
                    found += 1
                if node["valid_for_paper"] is False:
                    assert "INVALID-IF-POOLED" in node.get("label", "")
            elif node.get("valid_for_paper") is False:         # a comparator
                assert node.get("assumptions") or node.get("warning"), node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(report)
    assert found >= 5, f"only {found} invalid comparators found; test too weak"


def test_design_effect_route_is_flagged_as_collapsing_to_the_invalid_interval(
        report):
    """The specific trap: the ANOVA ICC on the pooled 1D repair set is <= 0, so
    Rao-Scott hands back exactly the draw-level interval. The output must say so
    rather than presenting it as a cluster-robust answer."""
    rs = (report["headline"]["onedim_repair"]["cluster_robust_comparators"]
          ["rao_scott_design_effect"])
    assert rs["icc"] == 0.0 and rs["design_effect"] == pytest.approx(1.0)
    assert rs["valid_for_paper"] is False
    assert "IDENTICAL to the draw-level" in rs["warning"]
    naive = (report["headline"]["onedim_repair"]
             ["INVALID_draw_level_comparator"]["wilson_95"])
    assert rs["rao_scott_wilson_95"] == pytest.approx(naive), (
        "the warning claims the two coincide; they must actually coincide")


def test_report_censored_zeros_are_all_really_zeros_with_wide_bounds(report):
    zeros = report["censored_zeros"]
    assert len(zeros) >= 6
    keys = {z["key"] for z in zeros}
    assert "censored_zeros.patch2d_pooled_0_of_156" in keys
    for z in zeros:
        assert z["block_level_upper_95_clopper_pearson"] > 0.1, z["key"]
        assert (z["block_level_upper_95_clopper_pearson"]
                >= z["INVALID_draw_level_upper_95_clopper_pearson"]), z["key"]
        assert z["n_distinct_blocks"] <= z["n_draws"]


def test_report_treatment_table_covers_every_draw(report, real_draws):
    assert sum(r["n_draws"] for r in report["treatment_table"]) == len(real_draws)
    assert all(r["n_blocks"] == r["n_draws"] for r in report["treatment_table"])
    for r in report["treatment_table"]:
        assert sum(r["outcome_counts"].values()) == r["n_draws"]
        assert (r["branch_counts"]["mode_absent"]
                + r["branch_counts"]["mode_present"] == r["n_draws"])
    p2 = [r for r in report["treatment_table"] if "patch2d" in r["treatment"]]
    assert p2, "no patch2d treatment rows"
    assert any("per_mode_seen" in r["branch_counts"] for r in p2), \
        "per-mode branch counts missing for patch2d"


def test_report_states_its_assumptions(report):
    a = report["assumptions"]
    for key in ("block_level_clopper_pearson", "why_not_a_hierarchical_model",
                "pooling_across_treatments"):
        assert key in a and len(a[key]) > 80
    assert "identifiable variance component" in a["why_not_a_hierarchical_model"]
    cr = report["headline"]["onedim_repair"]["cluster_robust_comparators"]
    assert "assumptions" in cr["cluster_bootstrap"]
    pend = (report["headline"]["onedim_repair"]["per_instrument"]["pendulum"]
            ["rao_scott_design_effect"])
    # Before the exactness audit every pendulum draw repaired, so the within-block
    # variance was exactly zero and the ICC was undefined. Four draws now differ, so the
    # ICC is defined; assert whichever branch the data supports, and that the report says
    # which it took.
    if pend["icc"] is None:
        assert "zero variance" in pend["reason"]
    else:
        # a defined ICC must come with a design effect above 1 (blocks correlate), an
        # effective n below the draw count, its stated assumptions, and the flag saying
        # it is a comparator rather than the bound the paper quotes
        assert 0.0 <= pend["icc"] <= 1.0
        assert pend["design_effect"] > 1.0
        assert pend["n_effective"] < pend["n_draws"]
        assert len(pend["assumptions"]) > 80
        assert pend["valid_for_paper"] is False


def test_committed_json_is_current(report):
    """The versioned results file must be what this code produces now, so the
    numeric audit and the paper cannot drift from it."""
    path = _REPO / "results" / "paper2_statistics.json"
    assert path.exists(), "run scripts/paper2_statistics.py"
    on_disk = json.loads(path.read_text())
    assert on_disk == json.loads(json.dumps(report)), (
        "results/paper2_statistics.json is stale; re-run "
        "PYTHONPATH=src python scripts/paper2_statistics.py")


# --------------------------------------------------------------------------- #
# 5. the fifth review's H3 layer: canonical campaign table, unit ladder,      #
#    derived censuses, the relay phantom, and the replicate pair              #
# --------------------------------------------------------------------------- #
def test_report_is_versioned(report):
    assert report["version"] == P.VERSION == 2
    assert report["version"] in report["version_history"]
    ladder = report["unit_ladder"]
    for level in ("1_raw_random_stream_block", "2_instrument_block",
                  "3_treatment_cell", "4_draw"):
        assert level in ladder


def test_campaign_table_partitions_every_draw(report):
    """Each campaign row's outcome decomposition must partition its draws, the
    grand total must equal the report's draw total, and every outcome label
    must come from the closed vocabulary."""
    rows = report["campaign_table"]
    total = 0
    for r in rows:
        for arm in ("incomplete", "full"):
            if arm not in r:
                continue
            e = r[arm]
            assert sum(e["outcomes"].values()) == e["n_draws"]
            assert set(e["outcomes"]) <= set(P.CANONICAL_OUTCOMES)
            assert e["n_mode_present"] + e["n_mode_absent"] == e["n_draws"]
            assert e["n_blocks"] <= e["n_draws"]
            dpb = e["draws_per_block"]
            assert dpb["min"] * e["n_blocks"] <= e["n_draws"] \
                <= dpb["max"] * e["n_blocks"]
            total += e["n_draws"]
    tot = report["campaign_table_totals"]
    assert total == tot["n_draws"] == report["totals"]["n_draws"]
    assert tot["n_campaigns"] == len(rows)


def test_campaign_table_phantom_column_matches_the_audits(real_draws, report):
    """phantom_repair across the table == probe-passing draws the behavioural /
    transcript audits convict: 4 GPT pendulum invented stops + 19 slab
    over-covering half-planes + 1 relay invented stop = 24."""
    n_phantom = sum(r[arm]["outcomes"].get("phantom_repair", 0)
                    for r in report["campaign_table"]
                    for arm in ("incomplete", "full") if arm in r)
    by_hand = sum(1 for d in real_draws
                  if d["outcome"] == "repaired" and d["arm"] == "incomplete"
                  and not P.is_repair(d))
    assert n_phantom == by_hand == 24


def test_relay_phantom_is_derived_from_the_transcript():
    """The Claude pendulum phantom (seed 20000) is detected from the versioned
    final reply, keyed by instrument so the cart cell of the same seed -- a
    genuine exact repair -- is not convicted with it."""
    fp = P._PROBE_FALSE_POSITIVES
    assert ("continuous_claude_relay.json", "pendulum", 20000) in fp
    assert ("continuous_claude_relay.json", "cart", 20000) not in fp
    assert ("continuous_claude_relay.json", "cart", 30000) not in fp


def test_onedim_primary_unit_is_the_instrument_block(report):
    """The 1D repair claim's primary unit: 50/56 instrument-blocks all-exact,
    with the raw-block 30/36 kept as the strictest comparator and the 105/111
    draw census unchanged. All three must come out of the code, not prose."""
    one = report["headline"]["onedim_repair"]
    assert (one["n_repaired_draws"], one["n_draws"]) == (105, 111)
    prim = one["PRIMARY_instrument_block_all_scoring"]
    assert (prim["k"], prim["n"]) == (50, 56)
    assert prim["cluster_key"] == "by_instrument_block"
    assert prim["n"] == one["n_distinct_instrument_blocks"]
    strict = one["clustered_aggregate_block_level_all_scoring"]
    assert (strict["k"], strict["n"]) == (30, 36)
    # the six failing draws fall in six distinct clusters at BOTH clusterings
    assert prim["n"] - prim["k"] == strict["n"] - strict["k"] == 6


def test_knob_cell_census_is_the_sum_of_the_per_knob_cells(report):
    """64/70 is a sum of knob-level block cells, not a distinct-block count;
    the census key must equal the per-knob table it is summed from."""
    one = report["headline"]["onedim_repair"]
    cc = one["knob_cell_census"]
    assert cc["n_cells"] == sum(
        v["block_level_all_scoring"]["n"] for v in one["per_knob"].values())
    assert cc["n_cells_all_repair"] == sum(
        v["block_level_all_scoring"]["k"] for v in one["per_knob"].values())
    assert (cc["n_cells_all_repair"], cc["n_cells"]) == (64, 70)
    # and it exceeds every distinct-block count, which is why it must never be
    # called one
    assert cc["n_cells"] > one["n_distinct_instrument_blocks"] \
        > one["n_distinct_blocks"]


def test_patch2d_census_keys_count_what_their_labels_say(report):
    """The regression this layer fixed: the '0/156' keys had silently grown to
    416 draws as later patch2d treatments were added."""
    p2 = report["headline"]["patch2d_repair_negative"]
    assert (p2["n_draws"], p2["n_distinct_blocks"]) == (156, 20)
    assert p2["HONEST_block_level"]["clopper_pearson_95"][1] == \
        pytest.approx(0.168, abs=5e-4)
    assert p2["honest_over_naive_upper_bound_ratio"] == pytest.approx(7.2, abs=0.05)
    broad = report["headline"]["patch2d_repair_negative_all_treatments"]
    assert broad["n_draws"] > 156 and broad["n_distinct_blocks"] == 20
    assert broad["HONEST_block_level"]["k"] == 0
    zeros = {z["key"]: z for z in report["censored_zeros"]}
    for key, n in (("censored_zeros.patch2d_pooled_0_of_156", 156),
                   ("censored_zeros.patch2d_disc_0_of_76", 76),
                   ("censored_zeros.patch2d_square_0_of_40", 40),
                   ("censored_zeros.patch2d_guided_0_of_40", 40),
                   ("censored_zeros.patch2d_partial_repair_0_of_66", 66),
                   ("censored_zeros.patch2d_all_families_0_of_159", 159)):
        assert zeros[key]["n_draws"] == n, (key, zeros[key]["n_draws"])


def test_replicate_pair_agreement(report):
    """The one same-model same-blocks repeat in the data: outcome classes agree
    cell for cell and the incomplete-cell gate accuracies are identical."""
    rp = report["replicate_same_model_same_blocks"]
    assert rp is not None
    assert rp["n_cells"] == 6
    assert rp["n_outcome_agree"] == rp["n_gate_decision_agree"] == 6
    assert rp["max_abs_gate_accuracy_diff_incomplete"] == 0.0
    assert rp["n_code_identical"] == 3
    assert "does not identify its mechanism" in rp["caveat"]
    # the pair is exactly the superseded file and its replacement, so the
    # replicate analysis and the inference exclusion cannot drift apart
    assert set(rp["files"]) == set(P.SUPERSEDED_FOR_INFERENCE) | \
        set(P.SUPERSEDED_FOR_INFERENCE.values())
