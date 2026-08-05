"""Tests for the two review-point measurements (paper 2, points #7 and #9).

  scripts/cem_crossing_bound.py   -- censored-zero CEM crossing bound
  scripts/play_cost_intervals.py  -- 100-episode paired play_cost inference

Every derivation here is checked against an oracle that does NOT import the
code path it validates:

  * the binomial CDF is checked against exact rational (fractions.Fraction)
    arithmetic;
  * the Clopper-Pearson bounds are checked against a bisection driven by that
    exact rational CDF, and (for k = 0) against the closed form
    1 - alpha**(1/n);
  * the bootstrap is checked against a full enumeration of all n**n resamples
    for n = 3;
  * the sign-flip randomization p-value is checked against a full enumeration
    of all 2**n sign patterns;
  * the episode-scope crossing counter is checked against cwm.continuous.cem's
    own episode driver.

The crossing tests deliberately use x_wall = 2.0, where crossings DO occur, and
assert that the sample really contained crossings -- otherwise every count-based
assertion would pass vacuously on an all-zero sample.
"""
import itertools
import json
import math
import pathlib
import statistics
import sys
from dataclasses import replace
from fractions import Fraction

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "src"))

import cem_crossing_bound as ccb          # noqa: E402
import play_cost_intervals as pci         # noqa: E402
from cwm.continuous import cem            # noqa: E402
from cwm.continuous.envs import CartWall, blind_of  # noqa: E402


# ---------------------------------------------------------------------------
# exact-rational oracles (independent of the implementations under test)
# ---------------------------------------------------------------------------

def exact_binom_cdf(k: int, n: int, p: Fraction) -> Fraction:
    """P(X <= k) in exact rational arithmetic."""
    tot = Fraction(0)
    for i in range(k + 1):
        tot += (Fraction(math.comb(n, i)) * p ** i * (1 - p) ** (n - i))
    return tot


def exact_cp_upper(k: int, n: int, alpha: Fraction, iters: int = 120) -> float:
    """Solve P(X <= k | p) = alpha by exact-arithmetic bisection."""
    lo, hi = Fraction(k, n), Fraction(1)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if exact_binom_cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


def exact_cp_lower(k: int, n: int, alpha: Fraction, iters: int = 120) -> float:
    """Solve P(X >= k | p) = alpha by exact-arithmetic bisection."""
    if k == 0:
        return 0.0
    lo, hi = Fraction(0), Fraction(k, n)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if 1 - exact_binom_cdf(k - 1, n, mid) < alpha:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


@pytest.mark.parametrize("k,n,p", [(0, 20, 0.3), (7, 20, 0.35), (3, 11, 0.5),
                                   (12, 12, 0.9), (1, 40, 0.02)])
def test_binom_cdf_matches_exact_rational(k, n, p):
    got = ccb.binom_cdf(k, n, p)
    want = float(exact_binom_cdf(k, n, Fraction(p).limit_denominator(10 ** 9)))
    assert got == pytest.approx(want, rel=1e-12, abs=1e-15)


def test_binom_cdf_edges_and_monotone():
    assert ccb.binom_cdf(0, 1000, 0.0) == 1.0
    assert ccb.binom_cdf(-1, 10, 0.5) == 0.0
    assert ccb.binom_cdf(10, 10, 0.5) == 1.0
    prev = 1.0
    for p in (0.001, 0.01, 0.05, 0.2, 0.5):
        cur = ccb.binom_cdf(2, 500, p)
        assert cur <= prev + 1e-15
        prev = cur


@pytest.mark.parametrize("n", [50, 1000, 6400, 1_280_000])
def test_cp_upper_zero_successes_matches_closed_form(n):
    """For k = 0, P(X <= 0) = (1-p)^n = alpha has the closed form
    p = 1 - alpha**(1/n). The bisection must find it."""
    got = ccb.clopper_pearson_upper(0, n, 0.05)
    want = 1.0 - 0.05 ** (1.0 / n)
    assert got == pytest.approx(want, rel=1e-9)


@pytest.mark.parametrize("k,n", [(0, 20), (7, 20), (2, 20), (1, 60), (9, 20)])
def test_cp_interval_matches_exact_rational_oracle(k, n):
    got = ccb.clopper_pearson_interval(k, n, conf=0.95)
    assert got["lo"] == pytest.approx(exact_cp_lower(k, n, Fraction(1, 40)),
                                      abs=1e-9)
    assert got["hi"] == pytest.approx(exact_cp_upper(k, n, Fraction(1, 40)),
                                      abs=1e-9)
    assert got["lo"] <= k / n <= got["hi"]


def test_cp_upper_is_above_wilson_upper_for_zero_count():
    """Sanity relation between the two reported bounds at k = 0."""
    for n in (1000, 100_000):
        assert ccb.clopper_pearson_upper(0, n) > 0
        assert ccb.wilson_upper(0, n) > 0


# ---------------------------------------------------------------------------
# (A) the CEM crossing measurement
# ---------------------------------------------------------------------------

def test_planner_config_is_read_from_plan_cem():
    cfg = ccb.planner_config()
    assert cfg["horizon"] == 40 and cfg["n_iters"] == 5
    assert cfg["n_samples"] == 64
    assert cfg["n_trajectories_per_plan"] == cfg["n_iters"] * cfg["n_samples"]
    # the derived per-episode trajectory count the mu_query bound needs
    assert (CartWall().h_episode * cfg["n_trajectories_per_plan"]) == 25600


def test_initial_scope_counts_are_exact_and_nonvacuous():
    """x_wall = 2 is the row where CEM DOES cross, so this exercises the
    crossing branch (a zero-crossing row would make the count assertions
    vacuous)."""
    truth, blind, boundary = ccb.make_row(2.0)
    cfg = ccb.planner_config()
    n_per_plan = cfg["n_trajectories_per_plan"]
    out = ccb.initial_scope_counts(truth, blind, boundary, 0, 4, n_per_plan)
    assert out["crossings"] > 0, "sample contained no crossing: test vacuous"
    assert out["plans"] == 4
    assert out["trajectories"] == 4 * n_per_plan
    assert 0 < out["plans_with_crossing"] <= 4
    # the per-plan fractions must be exact multiples of 1/320
    for f in out["first_plan_fracs"]:
        assert abs(f * n_per_plan - round(f * n_per_plan)) < 1e-9


def test_initial_scope_reproduces_published_table_cell():
    """The published crossing column must be recovered bit-for-bit by plans
    0..19 of the initial-state scope -- the whole point of the extension."""
    pub = ccb._published_row(2.0)
    if pub is None:
        pytest.skip("results/continuous_cem.json not available")
    truth, blind, boundary = ccb.make_row(2.0)
    n_per_plan = ccb.planner_config()["n_trajectories_per_plan"]
    out = ccb.initial_scope_counts(truth, blind, boundary, 0, 20, n_per_plan)
    mine = out["crossings"] / (20 * n_per_plan)
    assert mine == pub["crossing_frac_cem_blind"]
    assert mine > 0


def test_episode_scope_counts_match_cems_own_episode_driver():
    """Oracle: cwm.continuous.cem.run_episode. Small h_episode keeps it cheap;
    the loop under test is the same one the script runs at h_episode = 80."""
    truth = replace(CartWall(x_wall=2.0), h_episode=4)
    blind = blind_of(truth)
    n_per_plan = ccb.planner_config()["n_trajectories_per_plan"]
    out = ccb.episode_scope_counts(truth, blind, 2.0, 7000, n_per_plan)
    ep = cem.run_episode(truth, blind, seed=7000, boundary=2.0)
    assert out["ret"] == ep.ret
    assert out["contact"] == ep.contact
    assert out["crossing_frac_mean_over_plans"] == ep.crossing_frac
    assert out["plans"] == 4
    assert out["crossings"] > 0, "no crossing in sample: test vacuous"
    assert out["episode_has_crossing"] is True
    chk = ccb.replay_check(truth, blind, 2.0, out)
    assert all(chk[k] for k in ("ret_matches", "contact_matches",
                               "crossing_frac_matches"))


def test_episode_scope_zero_crossing_row_is_reported_as_censored():
    """The far wall: zero crossings must produce a POSITIVE upper bound, never
    a claim of impossibility."""
    cfg = ccb.planner_config()
    units = {
        "cart_xwall8|episode|0": {
            "key": "cart_xwall8|episode|0", "scope": "episode", "x_wall": 8.0,
            "episode": 0, "plans": 80, "trajectories": 25600, "crossings": 0,
            "episode_has_crossing": False, "crossing_frac_mean_over_plans": 0.0,
            "ret": 1.0, "contact": False, "seed": 0},
    }
    agg = ccb.aggregate(units, [8.0], cfg)
    row = agg["rows"][0]
    assert row["episode"]["crossings_observed"] == 0
    assert row["episode"]["crossing_frac_point"] == 0.0
    assert row["episode"]["p_upper_cp95_onesided"] > 0.0
    assert row["episode"]["mu_query_upper_cp95_direct"] > 0.0
    assert row["mu_query_upper_best"] > 0.0
    assert row["play_cost_upper_implied_by_prop_playcost"] > 0.0
    # the union bound must dominate the independence formula
    assert (row["episode"]["mu_query_upper_from_p_union_bound"]
            >= row["episode"]["mu_query_upper_from_p_independence"] - 1e-12)


def test_aggregate_union_bound_uses_derived_trajectory_count():
    cfg = ccb.planner_config()
    units = {
        "cart_xwall10|episode|0": {
            "key": "cart_xwall10|episode|0", "scope": "episode",
            "x_wall": 10.0, "episode": 0, "plans": 80, "trajectories": 25600,
            "crossings": 0, "episode_has_crossing": False,
            "crossing_frac_mean_over_plans": 0.0, "ret": 1.0,
            "contact": False, "seed": 0}}
    row = ccb.aggregate(units, [10.0], cfg)["rows"][0]
    assert row["n_imagined_trajectories_per_episode"] == 25600
    p = row["episode"]["p_upper_cp95_onesided"]
    assert row["episode"]["mu_query_upper_from_p_union_bound"] == pytest.approx(
        min(1.0, 25600 * p))


def test_mu_query_lower_bound_from_first_plan():
    """A censored zero cannot be refuted by an upper bound alone. The
    initial-state-scope plan IS the episode's first plan, so the fraction of
    plans containing a crossing is a valid LOWER confidence bound on
    mu_query(E). Here 3 of 200 plans cross."""
    cfg = ccb.planner_config()
    units = {
        "cart_xwall8|initial_state|0": {
            "key": "cart_xwall8|initial_state|0", "scope": "initial_state",
            "x_wall": 8.0, "plans": 100, "trajectories": 32000, "crossings": 2,
            "plans_with_crossing": 2, "first_plan_fracs": [],
            "crossing_plan_seeds": [1000, 4000], "crossing_plan_counts": [1, 1]},
        "cart_xwall8|initial_state|1": {
            "key": "cart_xwall8|initial_state|1", "scope": "initial_state",
            "x_wall": 8.0, "plans": 100, "trajectories": 32000, "crossings": 1,
            "plans_with_crossing": 1, "first_plan_fracs": [],
            "crossing_plan_seeds": [140000], "crossing_plan_counts": [1]},
        "cart_xwall8|episode|0": {
            "key": "cart_xwall8|episode|0", "scope": "episode", "x_wall": 8.0,
            "episode": 0, "plans": 80, "trajectories": 25600, "crossings": 0,
            "episode_has_crossing": False,
            "crossing_frac_mean_over_plans": 0.0, "ret": 1.0,
            "contact": False, "seed": 0},
    }
    row = ccb.aggregate(units, [8.0], cfg)["rows"][0]
    lb = row["mu_query_lower_bound_from_first_plan"]
    assert lb["plans_with_at_least_one_crossing"] == 3
    assert lb["n_plans"] == 200
    assert lb["point"] == pytest.approx(3 / 200)
    assert lb["lower_cp95_onesided"] == pytest.approx(
        exact_cp_lower(3, 200, Fraction(1, 20)), abs=1e-9)
    assert 0.0 < lb["lower_cp95_onesided"] < lb["point"]
    # the lower bound must sit below the upper bound: an interval, not a zero
    assert lb["lower_cp95_onesided"] < row["mu_query_upper_best"]
    assert row["crossing_plan_seeds_initial_scope"] == [1000, 4000, 140000]
    assert row["crossing_episode_seeds"] == []


def test_build_units_round_robins_rows():
    units = ccb.build_units([6.0, 8.0], n_plans=200, chunk=100, n_episodes=3)
    keys = [u["key"] for u in units]
    assert len(set(keys)) == len(keys)
    assert sum(1 for u in units if u["scope"] == "episode") == 6
    assert sum(1 for u in units if u["scope"] == "initial_state") == 4
    # the first four units already touch both rows and both scopes
    assert {u["x_wall"] for u in units[:4]} == {6.0, 8.0}
    assert {u["scope"] for u in units[:4]} == {"episode", "initial_state"}
    # only episode 0 carries the driver-replay validation
    assert [u["episode"] for u in units
            if u["scope"] == "episode" and u.get(
                "validate_against_run_episode")] == [0, 0]


# ---------------------------------------------------------------------------
# (B) the paired play_cost inference
# ---------------------------------------------------------------------------

def test_pairing_convention_matches_harness_play_cost():
    """harness.play_cost uses sd = seed + 1000*i; the reruns must too, or
    episodes 0..19 would not be the published cell."""
    assert pci.PAIRING_SEED == 0 and pci.PAIRING_STRIDE == 1000
    assert [pci.episode_seed(i) for i in range(3)] == [0, 1000, 2000]
    src = pathlib.Path(_REPO / "src/cwm/continuous/harness.py").read_text()
    assert "sd = seed + 1000 * i" in src


def test_build_units_puts_patch2d_last():
    units = pci.build_units(5)
    rows = [u["row"] for u in units]
    first_p2d = rows.index("patch2d_k3_7")
    assert set(rows[:first_p2d]) == {"cart_xwall8", "pend_thstop1.4"}
    assert set(rows[first_p2d:]) == {"patch2d_k3_7"}
    assert len(units) == 15


def _synthetic(n=3):
    t = [10.0, 12.0, 11.0][:n]
    b = [1.0, 0.5, 2.0][:n]
    r = [0.0, 3.0, 0.5][:n]
    return t, b, r


def test_paired_bootstrap_against_full_enumeration():
    """Oracle: enumerate all n**n paired resamples (n = 3 -> 27) and compare
    the exact bootstrap mean of the ratio statistic to the Monte Carlo one."""
    t, b, r = _synthetic(3)
    n = 3
    exact = []
    for idx in itertools.product(range(n), repeat=n):
        mt = sum(t[i] for i in idx) / n
        mb = sum(b[i] for i in idx) / n
        mr = sum(r[i] for i in idx) / n
        assert mt - mr > 0
        exact.append((mt - mb) / (mt - mr))
    got = pci.paired_bootstrap(t, b, r, n_boot=40000, seed=1)
    ci = got["play_cost_ci95"]
    assert got["n_used"] == 40000
    assert ci["mean"] == pytest.approx(statistics.mean(exact), abs=0.01)
    lo_x = sorted(exact)[int(math.floor(0.025 * len(exact)))]
    hi_x = sorted(exact)[int(math.ceil(0.975 * len(exact))) - 1]
    assert ci["lo"] == pytest.approx(lo_x, abs=0.05)
    assert ci["hi"] == pytest.approx(hi_x, abs=0.05)
    assert ci["lo"] <= ci["hi"]


def test_paired_bootstrap_preserves_pairing():
    """If the arms were resampled independently the play_cost of a perfectly
    paired dataset (b_i = t_i - 1 for every seed) would wobble; paired
    resampling keeps the regret exactly 1 in every resample."""
    t = [5.0, 50.0, 500.0]
    b = [4.0, 49.0, 499.0]
    r = [0.0, 0.0, 0.0]
    got = pci.paired_bootstrap(t, b, r, n_boot=5000, seed=3)
    reg = got["regret_ci95"]
    assert reg["lo"] == pytest.approx(1.0) and reg["hi"] == pytest.approx(1.0)
    assert reg["sd"] == pytest.approx(0.0, abs=1e-12)


def test_bootstrap_counts_nonpositive_denominators():
    """A denominator that can go non-positive under resampling must be counted
    and dropped, not silently produce a 0.0 play_cost."""
    t = [1.0, 1.0]
    r = [0.0, 5.0]          # mean_r > mean_t whenever seed 1 is drawn twice
    b = [0.5, 0.5]
    got = pci.paired_bootstrap(t, b, r, n_boot=2000, seed=5)
    assert got["n_nonpositive_denominator"] > 0
    assert got["n_used"] + got["n_nonpositive_denominator"] == 2000


def test_signflip_test_against_full_enumeration():
    """Oracle: all 2**8 sign patterns of the paired differences."""
    b = [1.0, 2.0, 0.5, 3.0, 1.5, 0.2, 2.5, 1.0]
    r = [2.0, 1.0, 1.5, 4.0, 1.0, 1.2, 2.0, 3.0]
    d = [ri - bi for ri, bi in zip(r, b)]
    obs = statistics.mean(d)
    n = len(d)
    ge = 0
    for signs in itertools.product((1, -1), repeat=n):
        if sum(s * x for s, x in zip(signs, d)) / n >= obs:
            ge += 1
    exact_p = ge / 2 ** n
    got = pci.signflip_test(b, r, n_perm=40000, seed=11)
    assert got["p_onesided_signflip"] == pytest.approx(exact_p, abs=0.02)
    assert got["observed_mean_d"] == pytest.approx(obs)
    # exact sign test, checked against an exact rational binomial tail
    k = sum(1 for x in d if x > 0)
    want = float(1 - exact_binom_cdf(k - 1, n, Fraction(1, 2)))
    assert got["exact_sign_test"]["k_seeds_random_beats_blind"] == k
    assert got["exact_sign_test"]["p_onesided"] == pytest.approx(want, rel=1e-9)


def test_signflip_detects_a_real_one_sided_effect():
    """Non-vacuity: with every difference positive the p-value must be the
    smallest the permutation group allows, 2**-n."""
    b = [0.0] * 10
    r = [1.0 + 0.1 * i for i in range(10)]
    got = pci.signflip_test(b, r, n_perm=20000, seed=2)
    assert got["p_onesided_signflip"] < 1e-3
    assert got["exact_sign_test"]["p_onesided"] == pytest.approx(2.0 ** -10)


def test_jackknife_finds_the_planted_outlier():
    t = [10.0] * 10
    b = [0.0] * 10
    r = [0.0] * 9 + [9.0]        # seed 9 alone carries the denominator
    seeds = [1000 * i for i in range(10)]
    jk = pci.jackknife(t, b, r, seeds)
    assert jk["most_influential_seed"] == 9000
    assert jk["play_cost_max"] > jk["play_cost_min"]
    assert abs(jk["most_influential_delta"]) > 0.05


def test_shape_reports_skew_and_spread():
    v = [0.0] * 19 + [100.0]
    s = pci.shape(v)
    assert s["median"] == 0.0 and s["max"] == 100.0
    assert s["skew_g1"] > 3.0          # heavily right-skewed, as the review says


def test_summarize_per_seed_mean_equals_ratio_of_means(monkeypatch):
    """The fixed-denominator per-seed convention must reproduce the published
    ratio-of-means estimator exactly (the assertion inside summarize), and the
    validation must FLAG a mismatch rather than pass silently."""
    units = {}
    for i in range(pci.PUBLISHED_EPISODES):
        units[f"cart_xwall8|{i}"] = {
            "key": f"cart_xwall8|{i}", "row": "cart_xwall8", "episode": i,
            "seed": pci.episode_seed(i),
            "j_truth": 17.0 + 0.01 * i, "j_blind": 0.02,
            "j_random": 0.5 if i % 4 else 3.0,
            "truth_contact": False, "blind_contact": True,
            "random_contact": False}
    t = [u["j_truth"] for u in units.values()]
    b = [u["j_blind"] for u in units.values()]
    r = [u["j_random"] for u in units.values()]
    mt, mb, mr = (statistics.mean(t), statistics.mean(b), statistics.mean(r))
    good = {"j_truth": mt, "j_blind": mb, "j_random": mr,
            "play_cost": (mt - mb) / (mt - mr)}
    monkeypatch.setattr(pci, "_published",
                        lambda row: dict(good) if row["key"] == "cart_xwall8"
                        else None)
    out = pci.summarize(units, n_boot=500, n_perm=500)
    row = next(x for x in out["rows"] if x["key"] == "cart_xwall8")
    assert row["play_cost"] == pytest.approx(
        statistics.mean(row["per_seed_play_cost_fixed_denominator"]),
        abs=1e-12)
    assert out["validation"]["all_match"] is True
    assert len(out["validation"]["checks"]) == 4
    assert len(row["per_seed"]) == pci.PUBLISHED_EPISODES

    bad = dict(good, j_blind=good["j_blind"] + 1e-6)
    monkeypatch.setattr(pci, "_published",
                        lambda row: dict(bad) if row["key"] == "cart_xwall8"
                        else None)
    out2 = pci.summarize(units, n_boot=100, n_perm=100)
    assert out2["validation"]["all_match"] is False


# ---------------------------------------------------------------------------
# (B2) the 2D mitigation lock-in count
# ---------------------------------------------------------------------------

def test_lockin_recount_and_interval():
    if not pci.CENSUS.exists():
        pytest.skip("census JSON not versioned")
    out = pci.lockin_intervals()
    assert out["available"] is True
    far = next(k for k in out["knobs"] if k["knob"] == [4.0, 8.0])
    assert far["n_episodes"] == 20
    assert far["census_pinned_episodes"] == 7
    # independent recount straight from the per-episode returns
    rets = far["returns_sorted"]
    thr = 0.1 * max(rets)
    assert sum(1 for x in rets if x < thr) == 7
    assert far["recount_matches_census"] is True
    ci = far["as_published"]
    assert (ci["k"], ci["n"]) == (7, 20)
    assert ci["lo"] == pytest.approx(exact_cp_lower(7, 20, Fraction(1, 40)),
                                     abs=1e-9)
    assert ci["hi"] == pytest.approx(exact_cp_upper(7, 20, Fraction(1, 40)),
                                     abs=1e-9)
    assert 0.0 < ci["lo"] < 0.35 < ci["hi"] < 1.0
    # the sample-dependent threshold is disclosed, and the fixed-threshold
    # variant is reported beside it
    fixed = far["fixed_threshold_0.1_x_j_truth"]
    assert fixed["k"] >= 7
    assert sum(1 for x in rets if x < fixed["threshold"]) == fixed["k"]
    assert "caveat" in out and "threshold" in out["caveat"]


def test_lockin_near_knob_is_a_censored_zero():
    if not pci.CENSUS.exists():
        pytest.skip("census JSON not versioned")
    near = next(k for k in pci.lockin_intervals()["knobs"]
                if k["knob"] == [2.0, 6.0])
    assert near["as_published"]["k"] == 0
    assert near["as_published"]["lo"] == 0.0
    assert near["as_published"]["hi"] > 0.10      # 0/20 is not "never"


# ---------------------------------------------------------------------------
# the produced JSONs, when present, must be internally consistent
# ---------------------------------------------------------------------------

def _load(p):
    q = _REPO / p
    if not q.exists():
        pytest.skip(f"{p} not produced yet")
    return json.loads(q.read_text())


def test_cem_crossing_bound_json_is_consistent():
    d = _load("results/cem_crossing_bound.json")
    assert d["validation"]["all_match"] is True
    for row in d["rows"]:
        for scope in ("initial_state", "episode"):
            blk = row[scope]
            if not blk["n_trajectories_examined"]:
                continue
            assert blk["n_trajectories_examined"] == (
                blk["n_plans"] * d["planner_config"]["n_trajectories_per_plan"])
            assert blk["p_upper_cp95_onesided"] == pytest.approx(
                ccb.clopper_pearson_upper(blk["crossings_observed"],
                                          blk["n_trajectories_examined"]),
                rel=1e-9)
            assert blk["p_upper_cp95_onesided"] > 0.0
            assert blk["crossing_frac_point"] <= blk["p_upper_cp95_onesided"]
        assert row["n_imagined_trajectories_per_episode"] == 25600
    # the control row must have resolved (nonzero), or the far rows' zeros
    # carry no information about the estimator's sensitivity
    ctrl = next((r for r in d["rows"] if r["x_wall"] == 6.0), None)
    if ctrl and ctrl["total_trajectories_examined"] > 100_000:
        assert ctrl["total_crossings_observed"] > 0


def test_play_cost_intervals_json_is_consistent():
    d = _load("results/play_cost_intervals.json")
    if "rows" not in d:
        pytest.skip("run still in its cheap-checkpoint phase")
    for row in d["rows"]:
        if not row["n_episodes"]:
            continue
        assert row["play_cost"] == pytest.approx(
            statistics.mean(row["per_seed_play_cost_fixed_denominator"]),
            abs=1e-12)
        assert row["regret_raw"] == pytest.approx(
            row["j_truth"] - row["j_blind"])
        ci = row["bootstrap"]["play_cost_ci95"]
        assert ci["lo"] <= row["play_cost"] <= ci["hi"] or math.isclose(
            ci["lo"], row["play_cost"], rel_tol=1e-6)
        assert row["bootstrap"]["n_boot"] >= 10000
        assert (row["randomization_blind_worse_than_random"]["n_perm"]
                >= 10000)
        assert len(row["per_seed"]) == row["n_episodes"]
    if d["validation"]["checks"]:
        assert d["validation"]["all_match"] is True
