"""Statistical-simultaneity audit of the coverage certificate (review point #14).

READ-ONLY on the certificate: this script recomputes, it does not change anything.
It answers one question --- is K = 36, rho = 0.363, sup bound 0.933 a rigorous bound
or an empirically calibrated one? --- by re-deriving every number under corrections
the published pipeline does not apply, and by checking each derivation against an
independent oracle that does not import the code path it validates.

Five things are audited.

(1) PART (a) IS SELECTION-FREE. gate_partition_certificate.py's part (a) draws no
    samples at all: the (n_y, n_v, n_a) grid search is a deterministic optimisation of
    K(1-1/K)^M. There is nothing to correct, but the union bound it uses can be
    replaced by the EXACT probability that some cell of an equal-volume K-partition is
    empty after M i.i.d. draws, by inclusion-exclusion,

        P(some cell empty) = sum_{j=1..K} (-1)^{j+1} C(K,j) (1 - j/K)^M,

    computed here in exact rational arithmetic. That is the independent oracle for the
    published 8*(7/8)^40 = 0.0383, and it also settles whether the union bound (rather
    than the gate) is what caps K at 8.

(2) THE PART (b) FAMILY. The candidate partitions are generated geometrically from a
    rho sweep, so the FAMILY is fixed before any sampling; but which member is
    certified is decided against a single shared 20,000-rollout Monte-Carlo sample, and
    the published Hoeffding radius unions over the cells of one partition only. This
    script recomputes the certified (K, rho, bound) under a Bonferroni correction over
    every (partition, cell) test in the family --- both the 13 partitions actually
    evaluated and the full a-priori family --- and reports whether the selection
    survives.

(3) THE delta BUDGET, arithmetic verified: delta/3 for the Hoeffding step (spread over
    the K cells, i.e. delta/(3K) per cell) plus delta/2 for the gate's own miss.

(4) HOEFFDING vs THE EXACT BINOMIAL. Hoeffding is loose at p ~ 0.8; the same
    certificate is recomputed with a Clopper-Pearson upper bound at the identical
    per-test level, to separate "the bound is empirically calibrated" from "the bound
    is conservative".

(5) THE STEP-t LEVEL SETS. gate_density_step_t.py claims per-cell Wilson bounds "at
    level delta/n_cells", so that selecting a level set afterwards is legitimate. It
    actually uses a FIXED z = 4 (one-sided level 3.17e-5). This script recomputes the
    level sets at the z that the a-priori cell family actually requires, and reports
    the published family-wise level per step.

Everything numeric lands in results/certificate_simultaneity.json. The step-t half is
checkpointed per step (atomic temp-file + os.replace) and skips finished steps on
restart.

Run: PYTHONPATH=src .venv/bin/python scripts/certificate_simultaneity.py
"""
import argparse
import json
import math
import os
import pathlib
import random
import sys
from fractions import Fraction

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall   # noqa: E402
from cwm.law import wilson_ci              # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--delta", type=float, default=0.05)
ap.add_argument("--eps-gate", type=float, default=0.01)
ap.add_argument("--n-gate", type=int, default=40)
ap.add_argument("--skip-step-t", action="store_true",
                help="skip section (5), which re-runs the 40k W_t Monte Carlo")
args = ap.parse_args()

OUT = _REPO / "results" / "certificate_simultaneity.json"
DELTA, EPS, NGATE = args.delta, args.eps_gate, args.n_gate

env = CartWall(x_wall=8.0)
DT, A = env.dt, env.a_max
V = env.gain * DT * A
Y = 0.5
L_PLANT = max(abs(1 - env.drag * DT) + env.gain * DT,
              1.0 + DT * abs(1 - env.drag * DT) + env.gain * DT ** 2)
WALL_PROBE_ERROR = 4.2

CERT = json.loads((_REPO / "results" / "gate_partition_certificate.json").read_text())
VALID = json.loads((_REPO / "results" / "gate_partition_validation.json").read_text())
MC = CERT["params"]["mc_rollouts"]
MC_SEED = CERT["params"]["seed"]


def load_checkpoint():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save(doc):
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2))
    os.replace(tmp, OUT)


DOC = load_checkpoint()
DOC.setdefault("script", "certificate_simultaneity.py")
DOC["params"] = vars(args)
DOC["reads"] = ["results/gate_partition_certificate.json",
                "results/gate_partition_validation.json",
                "results/gate_density_step_t.json"]

# ---------------------------------------------------------------------------
# 0. paper arithmetic, re-derived
# ---------------------------------------------------------------------------
b36 = CERT["measured_best"]
a8 = CERT["exact_best"]


def net_radius(ny, nv, na):
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    return max(dy + DT * dv, dv, da)


def bound_of(rho):
    return EPS + 2 * L_PLANT * rho


def l_max_excluding(rho, err=WALL_PROBE_ERROR):
    return (err - EPS) / (2 * rho)


DOC["paper_arithmetic"] = {
    "L_plant": L_PLANT,
    "part_a": {
        "K": a8["K"], "split": [a8["n_y"], a8["n_v"], a8["n_a"]],
        "rho": net_radius(a8["n_y"], a8["n_v"], a8["n_a"]),
        "union_failure_K8_M40": 8 * (7 / 8) ** 40,
        "union_failure_K9_M40": 9 * (8 / 9) ** 40,
        "uniform_bound": bound_of(net_radius(a8["n_y"], a8["n_v"], a8["n_a"])),
        "paper_says": {"K": 8, "fail_K8": 0.038, "fail_K9": 0.081,
                       "rho": 0.600, "bound": 1.534},
    },
    "part_b": {
        "K": b36["K"], "split": [b36["n_y"], b36["n_v"], b36["n_a"]],
        "worst_p_C_point": b36["worst_p_C"],
        "worst_p_C_ub_published": b36["worst_p_C_ub"],
        "hoeffding_radius_published": b36["worst_p_C_ub"] - b36["worst_p_C"],
        "K_times_ub_pow_N": b36["K"] * b36["worst_p_C_ub"] ** NGATE,
        "delta_over_2": DELTA / 2,
        "rho": b36["rho"], "uniform_bound": bound_of(b36["rho"]),
        "L_max_excluding_4.2": l_max_excluding(b36["rho"]),
        "paper_says": {"worst_p_C": 0.800, "worst_p_C_ub": 0.814,
                       "K_ub_pow_N": 0.010, "rho": 0.363, "bound": 0.933,
                       "L_max": 5.77},
    },
}

# ---------------------------------------------------------------------------
# 1. exact inclusion-exclusion oracle for part (a)  (no import of the certificate)
# ---------------------------------------------------------------------------
def exact_some_cell_empty(K, M):
    """P(at least one of K equally likely cells is empty after M i.i.d. draws),
    exactly, in rational arithmetic. Independent of gate_partition_certificate.py:
    inclusion-exclusion over which cells are empty."""
    tot = Fraction(0)
    for j in range(1, K + 1):
        term = Fraction(math.comb(K, j)) * Fraction(K - j, K) ** M
        tot += -term if j % 2 == 0 else term
    return tot


def exact_some_cell_empty_mc(K, M, trials, seed=17):
    """Brute-force check of the inclusion-exclusion formula by direct simulation."""
    rng = random.Random(seed)
    bad = 0
    for _ in range(trials):
        seen = set()
        for _ in range(M):
            seen.add(rng.randrange(K))
            if len(seen) == K:
                break
        if len(seen) < K:
            bad += 1
    return bad / trials


exact_rows = []
for K in (4, 6, 8, 9, 10, 12, 16, 24):
    ex = float(exact_some_cell_empty(K, NGATE))
    exact_rows.append({"K": K, "union_bound": K * (1 - 1 / K) ** NGATE,
                       "exact": ex, "admissible_union": K * (1 - 1 / K) ** NGATE <= DELTA,
                       "admissible_exact": ex <= DELTA})
mc_check = {str(K): exact_some_cell_empty_mc(K, NGATE, 200000)
            for K in (8, 9)}
DOC["part_a_exact_oracle"] = {
    "note": "inclusion-exclusion, exact rationals; union bound is what the paper uses",
    "M": NGATE, "rows": exact_rows,
    "brute_force_mc_200k": mc_check,
    "largest_K_admissible_union": max(r["K"] for r in exact_rows
                                      if r["admissible_union"]),
    "largest_K_admissible_exact": max(r["K"] for r in exact_rows
                                      if r["admissible_exact"]),
    "measured_400_gate_failure": VALID["rows"][0]["measured_failure"],
}
save(DOC)

# ---------------------------------------------------------------------------
# 2. the part (b) candidate family, reconstructed from the published algorithm
# ---------------------------------------------------------------------------
def coarsest_for(rho_target):
    """Byte-for-byte the candidate generator of gate_partition_certificate.py
    (lines 204-221). Purely geometric: NO sample enters it."""
    na = math.ceil(2 * A / rho_target)
    nv = math.ceil(2 * V / rho_target)
    dv = 2 * V / nv
    slack = rho_target - DT * dv
    if slack <= 0:
        return None
    ny = math.ceil(2 * Y / slack)
    rho = net_radius(ny, nv, na)
    if rho > rho_target + 1e-12:
        return None
    return rho, ny, nv, na, ny * nv * na


FAMILY, _seen = [], set()
_r = 2.0
while _r > 0.08:
    c = coarsest_for(_r)
    if c and (c[1], c[2], c[3]) not in _seen:
        _seen.add((c[1], c[2], c[3]))
        FAMILY.append(c)
    _r -= 0.01
FAMILY.sort(reverse=True)

EVALUATED = CERT["measured_rows"]                 # what the run actually touched
n_eval = len(EVALUATED)
tests_evaluated = sum(r["K"] for r in EVALUATED)
tests_family = sum(c[4] for c in FAMILY)

DOC["family"] = {
    "generator": "coarsest_for(rho) over rho = 2.00 down to 0.09 step 0.01",
    "data_independent": True,
    "n_candidates_a_priori": len(FAMILY),
    "n_candidates_evaluated": n_eval,
    "K_values_evaluated": [r["K"] for r in EVALUATED],
    "n_certified_of_evaluated": sum(1 for r in EVALUATED if r["certified"]),
    "cell_tests_evaluated": tests_evaluated,
    "cell_tests_a_priori_family": tests_family,
    "early_stop_rule": "stop after 18 candidates tried or 4 consecutive failures "
                       "(gate_partition_certificate.py:246)",
    "shared_sample": f"every candidate is scored on the SAME {MC} rollouts "
                     f"(seeds {MC_SEED}..{MC_SEED + MC - 1})",
    "note_dead_param": "--max-cells-b (default 400) is recorded in the certificate's "
                       "params but never used; the family is capped by rho > 0.08 and "
                       f"reaches K = {max(c[4] for c in FAMILY)}",
}
save(DOC)

# ---------------------------------------------------------------------------
# 3. Hoeffding / Clopper-Pearson upper bounds, and the corrected selections
# ---------------------------------------------------------------------------
def hoeffding_radius(level):
    """t with exp(-2 M t^2) = level. Closed form."""
    return math.sqrt(math.log(1.0 / level) / (2 * MC))


def hoeffding_radius_bisect(level):
    """ORACLE: same t by bisection on exp(-2 M t^2) - level, no closed form used."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if math.exp(-2 * MC * mid * mid) > level:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def log_binom_cdf(k, n, p):
    """log P(Bin(n,p) <= k), summed in log space. Independent of any bound above."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return -math.inf
    lp, lq = math.log(p), math.log1p(-p)
    terms = []
    lc = 0.0                                    # log C(n,0)
    for i in range(0, k + 1):
        if i > 0:
            lc += math.log((n - i + 1) / i)
        terms.append(lc + i * lp + (n - i) * lq)
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


def clopper_pearson_upper(k, n, level):
    """Exact-binomial one-sided upper confidence bound: the largest p with
    P(Bin(n,p) <= k) >= level. Bisection on the exact tail."""
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if log_binom_cdf(k, n, mid) >= math.log(level):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def select(rows, level_fn, ub_fn):
    """Re-run the certificate's selection rule on the published point estimates,
    with a configurable per-test level and upper-bound method."""
    out, best = [], None
    for r in rows:
        lvl = level_fn(r["K"])
        ub = min(1.0, ub_fn(r["worst_p_C"], lvl))
        fail = r["K"] * ub ** NGATE if ub < 1.0 else float("inf")
        ok = fail <= DELTA / 2
        row = {"K": r["K"], "split": [r["n_y"], r["n_v"], r["n_a"]],
               "rho": r["rho"], "worst_p_C": r["worst_p_C"],
               "per_test_level": lvl, "worst_p_C_ub": ub,
               "union_failure": fail, "certified": bool(ok),
               "uniform_bound": bound_of(r["rho"])}
        out.append(row)
        if ok and (best is None or r["rho"] < best["rho"]):
            best = row
    if best:
        best = dict(best, L_max_excluding_4_2=l_max_excluding(best["rho"]))
    return out, best


def hoef_ub(phat, level):
    return phat + hoeffding_radius(level)


def cp_ub(phat, level):
    return clopper_pearson_upper(round(phat * MC), MC, level)


VARIANTS = [
    ("published (delta/3 over the K cells of one partition)",
     lambda K: DELTA / (3 * K), hoef_ub,
     "gate_partition_certificate.py:252 -- sqrt(log(3K/delta)/(2M))"),
    ("Bonferroni over the 13 partitions actually evaluated "
     f"({tests_evaluated} cell tests)",
     lambda K: DELTA / (3 * tests_evaluated), hoef_ub,
     "delta/3 spread over every (partition, cell) test the run touched"),
    ("Bonferroni over the full a-priori family "
     f"({tests_family} cell tests)",
     lambda K: DELTA / (3 * tests_family), hoef_ub,
     "delta/3 spread over every cell of every candidate the generator can emit"),
    ("Bonferroni over the family x 1000 (stress test)",
     lambda K: DELTA / (3 * tests_family * 1000), hoef_ub,
     "shows the log-dependence: a 1000x larger family costs almost nothing"),
    ("published level, exact-binomial (Clopper-Pearson) instead of Hoeffding",
     lambda K: DELTA / (3 * K), cp_ub,
     "how much of the slack is Hoeffding's"),
    ("family-corrected level AND Clopper-Pearson",
     lambda K: DELTA / (3 * tests_family), cp_ub,
     "the tightest honest simultaneous version"),
]

variant_out = []
for label, lvl_fn, ub_fn, why in VARIANTS:
    rows, best = select(EVALUATED, lvl_fn, ub_fn)
    variant_out.append({"label": label, "rationale": why,
                        "per_test_level_at_K36": lvl_fn(36),
                        "rows": rows,
                        "selected": best})
    print(f"{label}\n   -> " + (f"K = {best['K']}, rho = {best['rho']:.4f}, "
                                f"bound = {best['uniform_bound']:.4f}, "
                                f"p_C UB = {best['worst_p_C_ub']:.4f}, "
                                f"fail = {best['union_failure']:.5f}"
                                if best else "NOTHING CERTIFIED"))
DOC["simultaneity_variants"] = variant_out
DOC["headline_robustness"] = {
    "published": {"K": b36["K"], "rho": b36["rho"],
                  "uniform_bound": bound_of(b36["rho"])},
    "selected_K_per_variant": {v["label"]: (v["selected"]["K"] if v["selected"]
                                            else None)
                               for v in variant_out},
    "selected_bound_per_variant": {v["label"]: (v["selected"]["uniform_bound"]
                                                if v["selected"] else None)
                                   for v in variant_out},
    "unchanged_under_every_correction": all(
        v["selected"] and v["selected"]["K"] == b36["K"] for v in variant_out),
}

# ---------------------------------------------------------------------------
# 4. delta budget + Hoeffding oracles
# ---------------------------------------------------------------------------
lvl36 = DELTA / (3 * 36)
t_closed = hoeffding_radius(lvl36)
t_bisect = hoeffding_radius_bisect(lvl36)
# exact binomial tail at the published (M, p, t): must be <= the Hoeffding level
p_true = b36["worst_p_C_ub"]
k_edge = math.floor((p_true - t_closed) * MC)
log_tail = log_binom_cdf(k_edge, MC, p_true)
DOC["hoeffding_audit"] = {
    "per_cell_level_used": lvl36,
    "family_wise_hoeffding_budget": DELTA / 3,
    "t_closed_form": t_closed,
    "t_by_independent_bisection": t_bisect,
    "closed_form_matches_bisection": abs(t_closed - t_bisect) < 1e-12,
    "published_t": b36["worst_p_C_ub"] - b36["worst_p_C"],
    "matches_published_t": abs(t_closed - (b36["worst_p_C_ub"]
                                           - b36["worst_p_C"])) < 1e-12,
    "oracle_exact_binomial_tail": math.exp(log_tail),
    "oracle_hoeffding_level": lvl36,
    "hoeffding_is_conservative": math.exp(log_tail) <= lvl36,
    "applied_at": "delta/(3*K) per cell, i.e. delta/3 DIVIDED BY the number of "
                  "cells -- the correct choice; NOT a single bound on the "
                  "selected maximum",
    "why_that_is_enough": "with p_C <= phat_C + t for every C simultaneously, "
                          "max_C p_C <= max_C phat_C + t, which is exactly the "
                          "quantity the union bound K*ub^N consumes",
}
DOC["delta_budget"] = {
    "hoeffding_half": DELTA / 3, "gate_miss_half": DELTA / 2,
    "total_spent": DELTA / 3 + DELTA / 2, "delta": DELTA,
    "within_budget": DELTA / 3 + DELTA / 2 <= DELTA,
    "actual_confidence_of_part_b": 1 - (DELTA / 3 + DELTA / 2),
    "part_a_uses_full_delta": True,
    "part_a_failure": a8["failure_prob"],
    "note": "part (a) spends the whole delta on the coverage event (it has no "
            "estimation error); part (b) spends delta/3 + delta/2 = 5delta/6, so "
            "the published 0.933 actually holds at 1 - 0.0417, not 1 - 0.05",
}
save(DOC)

# ---------------------------------------------------------------------------
# 5. sample reuse / seed disjointness, and the validation's step index
# ---------------------------------------------------------------------------
mc_seeds = set(range(MC_SEED, MC_SEED + MC))
val_seeds = set()
for trial in range(VALID["params"]["trials"]):
    for r in range(VALID["params"]["n_gate"]):
        val_seeds.add(1_000_000 * trial + r)
DOC["seed_hygiene"] = {
    "mc_seed_range": [MC_SEED, MC_SEED + MC - 1],
    "validation_seed_rule": "1_000_000*trial + r (gate_partition_validation.py:61)",
    "n_validation_seeds": len(val_seeds),
    "overlap_size": len(mc_seeds & val_seeds),
    "validation_is_out_of_sample": len(mc_seeds & val_seeds) == 0,
    "note": "the 400-gate validation therefore tests the SELECTED partition on "
            "fresh rollouts: it is not circular in the sampling sense, only in "
            "the sense that the partition it tests was chosen with the MC sample "
            "(which is precisely what makes it the right test of the selection).",
}

# the part-(a) validation uses step index 0, where v == 0 exactly
one_step_v, step1_v, step0_y, step1_y = [], [], [], []
for trial in range(200):
    rng = random.Random(1_000_000 * trial)
    s = env.initial_state(rng)
    a0 = rng.uniform(-A, A)
    one_step_v.append(s[1])
    step0_y.append(s[0] - DT * s[1])
    s1 = env.step(s, a0)[0]
    step1_v.append(s1[1])
    step1_y.append(s1[0] - DT * s1[1])
DOC["part_a_sample_index"] = {
    "validation_breaks_after_step": 0,
    "evidence": "gate_partition_validation.py:72-73 breaks out of the step loop "
                "after the FIRST iteration, so the sample is (x_0, v_0, a_0)",
    "v_at_step_0_is_identically_zero": all(v == 0.0 for v in one_step_v),
    "certificate_assumes": "the step-1 law, uniform on the sheared box "
                           "(main.tex:337; main.tex:429 says step 0 is supported "
                           "on a lower-dimensional set, v = 0 exactly)",
    "step_1_v_range": [min(step1_v), max(step1_v)], "V": V,
    "step_1_v_is_spread_over_pm_V": (max(step1_v) > 0.9 * V
                                     and min(step1_v) < -0.9 * V),
    "y_is_the_same_variable_at_both_steps": max(
        abs(a - b) for a, b in zip(step0_y, step1_y)) < 1e-12,
    "benign_because": "the certified split has n_v = 1, so the v coordinate is a "
                      "single cell and cannot distinguish v = 0 from v ~ U(-V,V); "
                      "and y_1 = x_0 = y_0 identically while a_0, a_1 are i.i.d. "
                      "uniform, so at n_v = 1 the two samples have the SAME joint "
                      "law and 385/400 is the right validation number.",
    "would_break_if": "any certified part-(a) split had n_v >= 2: with v == 0 the "
                      "index is int(V/dv) which lands in a single v-cell, so the "
                      "other v-cells could never be hit and the test would report "
                      "0/400 coverage for a certificate that is in fact sound.",
}
# demonstrate the latent failure at n_v = 2 without editing the validation script
def covers(ny, nv, na, one_step_only, trial):
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    need = {(i, j, k) for i in range(ny) for j in range(nv) for k in range(na)}
    for r in range(NGATE):
        rng = random.Random(1_000_000 * trial + r)
        s = env.initial_state(rng)
        for step in range(env.h_episode):
            a = rng.uniform(-A, A)
            x, v = s
            y = x - DT * v
            if abs(y) < Y and abs(v) < V and abs(a) < A:
                need.discard((min(ny - 1, int((y + Y) / dy)),
                              min(nv - 1, int((v + V) / dv)),
                              min(na - 1, int((a + A) / da))))
            s = env.step(s, a)[0]
            if one_step_only:
                break
    return not need


def covers_step1(ny, nv, na, trial):
    """Same, but taking the SECOND transition -- the one whose law is uniform."""
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    need = {(i, j, k) for i in range(ny) for j in range(nv) for k in range(na)}
    for r in range(NGATE):
        rng = random.Random(1_000_000 * trial + r)
        s = env.initial_state(rng)
        a = rng.uniform(-A, A)
        s = env.step(s, a)[0]
        a = rng.uniform(-A, A)
        x, v = s
        y = x - DT * v
        if abs(y) < Y and abs(v) < V and abs(a) < A:
            need.discard((min(ny - 1, int((y + Y) / dy)),
                          min(nv - 1, int((v + V) / dv)),
                          min(na - 1, int((a + A) / da))))
    return not need


TR = 200
demo = {}
for split in ([2, 1, 4], [2, 2, 2], [1, 2, 4]):
    ny, nv, na = split
    demo[f"{ny}x{nv}x{na}"] = {
        "K": ny * nv * na, "rho": net_radius(ny, nv, na),
        "cover_rate_as_validated_step0": sum(covers(ny, nv, na, True, t)
                                             for t in range(TR)) / TR,
        "cover_rate_step1_correct": sum(covers_step1(ny, nv, na, t)
                                        for t in range(TR)) / TR,
        "exact_union_failure": ny * nv * na * (1 - 1 / (ny * nv * na)) ** NGATE,
    }
DOC["part_a_sample_index"]["demonstration"] = {
    "trials": TR,
    "note": "n_v = 1 rows agree; any n_v >= 2 row shows the step-0 sample "
            "reporting 0.0 coverage while the correct step-1 sample does not.",
    "rows": demo,
}
save(DOC)

# ---------------------------------------------------------------------------
# 5b. OUT-OF-SAMPLE REPLICATION of the one estimated quantity the certificate
#     rests on: worst_C p_C for the selected K = 36 partition, re-measured on a
#     fresh, disjoint rollout stream. The 400-gate validation does not test this.
# ---------------------------------------------------------------------------
def worst_p_C(ny, nv, na, n_roll, seed0):
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    cells = [(i, j, k) for i in range(ny) for j in range(nv) for k in range(na)]
    miss = {c: 0 for c in cells}
    for i in range(n_roll):
        rng = random.Random(seed0 + i)
        s = env.initial_state(rng)
        hit = set()
        for _ in range(env.h_episode):
            a = rng.uniform(-A, A)
            x, v = s
            y = x - DT * v
            if abs(y) < Y and abs(v) < V and abs(a) < A:
                hit.add((min(ny - 1, int((y + Y) / dy)),
                         min(nv - 1, int((v + V) / dv)),
                         min(na - 1, int((a + A) / da))))
            s = env.step(s, a)[0]
        for c in cells:
            if c not in hit:
                miss[c] += 1
    ps = {c: miss[c] / n_roll for c in cells}
    arg = max(ps, key=lambda c: ps[c])
    return ps[arg], arg, ps


if "out_of_sample_p_C" not in DOC:
    NY, NV, NA = b36["n_y"], b36["n_v"], b36["n_a"]
    FRESH_SEED = 10_000_000            # disjoint from 4242..24241 and from 1e6*t+r
    w_fresh, arg_fresh, _ = worst_p_C(NY, NV, NA, MC, FRESH_SEED)
    w_repro, arg_repro, _ = worst_p_C(NY, NV, NA, MC, MC_SEED)
    t36 = hoeffding_radius(DELTA / (3 * 36))
    DOC["out_of_sample_p_C"] = {
        "partition": [NY, NV, NA], "K": b36["K"], "n_rollouts": MC,
        "published_worst_p_C": b36["worst_p_C"],
        "reproduced_worst_p_C_same_seeds": w_repro,
        "reproduces_published": abs(w_repro - b36["worst_p_C"]) < 1e-12,
        "fresh_seed_base": FRESH_SEED,
        "fresh_worst_p_C": w_fresh,
        "fresh_argmax_cell": list(arg_fresh),
        "published_argmax_cell": list(arg_repro),
        "abs_difference": abs(w_fresh - b36["worst_p_C"]),
        "hoeffding_radius": t36,
        "fresh_estimate_inside_published_upper_bound":
            w_fresh <= b36["worst_p_C_ub"],
        "certificate_still_holds_on_fresh_sample":
            b36["K"] * min(1.0, w_fresh + t36) ** NGATE <= DELTA / 2,
        "union_failure_on_fresh_sample":
            b36["K"] * min(1.0, w_fresh + t36) ** NGATE,
        "note": "if worst_p_C were an artifact of the shared sample, a disjoint "
                "20,000-rollout stream would move it by more than the Hoeffding "
                "radius it is bounded by.",
    }
    save(DOC)
    print(f"out-of-sample worst p_C: {w_fresh:.5f} vs published "
          f"{b36['worst_p_C']:.5f} (Hoeffding radius {t36:.5f})")

# ---------------------------------------------------------------------------
# 6. step-t level sets: the Wilson level actually used vs the level claimed
# ---------------------------------------------------------------------------
DENS = json.loads((_REPO / "results" / "gate_density_step_t.json").read_text())
DP = DENS["params"]
LAM, GX, GV = DP["lam"], DP["region"][0], DP["region"][1]
MCW, DSEED = DP["mc"], DP["seed"]
dt, g, dr = env.dt, env.gain, env.drag
k_ = 1 - dr * dt
M2 = [[dt * g * dt, dt * k_ * g * dt + g * dt * dt], [g * dt, k_ * g * dt]]
DET = M2[0][0] * M2[1][1] - M2[0][1] * M2[1][0]
AREA_P = 4 * A * A * abs(DET)
DENS_P = 1.0 / AREA_P
CELL_AREA = LAM * LAM * AREA_P
ALPHAS = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01]


def m_apply(z):
    return (M2[0][0] * z[0] + M2[0][1] * z[1], M2[1][0] * z[0] + M2[1][1] * z[1])


def m_inv(u):
    a_, b_, c_, d_ = M2[0][0], M2[0][1], M2[1][0], M2[1][1]
    return ((d_ * u[0] - b_ * u[1]) / DET, (-c_ * u[0] + a_ * u[1]) / DET)


def cell_center(i, j):
    return m_apply((LAM * 2 * A * (i + 0.5), LAM * 2 * A * (j + 0.5)))


def in_region(i, j):
    c0 = cell_center(i, j)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = m_apply((LAM * A * sx, LAM * A * sy))
            if abs(c0[0] + d[0]) > GX or abs(c0[1] + d[1]) > GV:
                return False
    return True


def cells_eroded_at(w):
    y = m_inv(w)
    y = (y[0] / (LAM * 2 * A), y[1] / (LAM * 2 * A))
    h = (1 - LAM) / (2 * LAM)
    out = []
    for i in range(math.floor(y[0] - h - 0.5), math.ceil(y[0] + h + 0.5) + 1):
        for j in range(math.floor(y[1] - h - 0.5), math.ceil(y[1] + h + 0.5) + 1):
            if abs(i + 0.5 - y[0]) <= h and abs(j + 0.5 - y[1]) <= h:
                out.append((i, j))
    return out


def w_sample(t, i):
    rng = random.Random(DSEED + 7919 * t + i)
    x = rng.uniform(-0.5, 0.5)
    v = 0.0
    acts = [rng.uniform(-A, A) for _ in range(t)]
    acts[-1] = 0.0
    acts[-2] = 0.0
    for a in acts:
        v = v + (g * a - dr * v) * dt
        x = x + v * dt
    return (x, v)


def norm_sf(z):
    """P(Z > z) for standard normal, via erfc -- the level a Wilson z buys."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def z_for_level(level):
    lo, hi = 0.0, 12.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if norm_sf(mid) > level:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# the a-priori in-region cell family (data-independent: this is the family the
# "fixed in advance" claim is about)
RANGE = 400          # lattice half-width; the region box is reached well inside it
family_cells = [(i, j) for i in range(-RANGE, RANGE + 1)
                for j in range(-RANGE, RANGE + 1) if in_region(i, j)]
N_FAMILY = len(family_cells)
Z_PUBLISHED = 4.0
Z_NEEDED = z_for_level(DELTA / N_FAMILY)

DOC["step_t_wilson"] = DOC.get("step_t_wilson", {})
DOC["step_t_wilson"].update({
    "claim_in_paper": "Wilson lower bound per cell at level delta/K over a cell "
                      "family fixed in advance (main.tex:375)",
    "code_reality": "a FIXED z = 4.0 (gate_density_step_t.py:215-219), not "
                    "delta/n_cells",
    "cell_family_is_data_independent": True,
    "n_cells_a_priori_in_region": N_FAMILY,
    "z_published": Z_PUBLISHED,
    "one_sided_level_of_z4": norm_sf(Z_PUBLISHED),
    "family_wise_level_published_vs_apriori_family":
        N_FAMILY * norm_sf(Z_PUBLISHED),
    "z_required_for_delta_over_apriori_family": Z_NEEDED,
    "per_step_family_wise_level_published": {
        str(r["step"]): r["n_cells_seen"] * norm_sf(Z_PUBLISHED)
        for r in DENS["rows"]},
    "docstring_claim": "'with a few thousand cells the family-wise level stays "
                       "below delta = 0.05' -- true only up to "
                       f"{int(DELTA / norm_sf(Z_PUBLISHED))} cells",
})
save(DOC)

if not args.skip_step_t:
    done = DOC["step_t_wilson"].get("recomputed", {})
    for t_step in DP["steps"]:
        key = str(t_step)
        if key in done:
            print(f"[step {t_step}] already in checkpoint, skipping")
            continue
        hits = {}
        for i in range(MCW):
            for cij in cells_eroded_at(w_sample(t_step, i)):
                hits[cij] = hits.get(cij, 0) + 1
        rec = {"n_cells_seen": 0, "levels": {}}
        d_pub, d_cor = {}, {}
        for cij, h in hits.items():
            if not in_region(*cij):
                continue
            d_pub[cij] = DENS_P * wilson_ci(h, MCW, z=Z_PUBLISHED)[1] / (2 * A)
            d_cor[cij] = DENS_P * wilson_ci(h, MCW, z=Z_NEEDED)[1] / (2 * A)
        rec["n_cells_seen"] = len(d_pub)
        for a_ in ALPHAS:
            n_pub = sum(1 for v_ in d_pub.values() if v_ >= a_)
            n_cor = sum(1 for v_ in d_cor.values() if v_ >= a_)
            rec["levels"][str(a_)] = {
                "n_cells_published_z4": n_pub,
                "vol_published_z4": n_pub * CELL_AREA * 2 * A,
                "n_cells_corrected": n_cor,
                "vol_corrected": n_cor * CELL_AREA * 2 * A,
            }
        pub_ref = {str(p["alpha"]): p["n_cells"]
                   for p in next(r for r in DENS["rows"]
                                 if r["step"] == t_step)["level_sets"]}
        rec["reproduces_published"] = all(
            rec["levels"][a_]["n_cells_published_z4"] == pub_ref[a_]
            for a_ in pub_ref)
        done[key] = rec
        DOC["step_t_wilson"]["recomputed"] = done
        save(DOC)
        print(f"[step {t_step}] cells {rec['n_cells_seen']}, reproduces published: "
              f"{rec['reproduces_published']}")
    # headline corrected volumes the paper quotes
    quoted = [(20, "0.05"), (40, "0.02"), (80, "0.01")]
    DOC["step_t_wilson"]["paper_quoted_volumes"] = {
        f"step{t}_alpha{a_}": {
            "published": done[str(t)]["levels"][a_]["vol_published_z4"],
            "corrected": done[str(t)]["levels"][a_]["vol_corrected"],
        } for t, a_ in quoted if str(t) in done}
    DOC["step_t_wilson"]["all_reproduce_published"] = all(
        v["reproduces_published"] for v in done.values())
    save(DOC)

# ---------------------------------------------------------------------------
# 7. verdict
# ---------------------------------------------------------------------------
best_pub = variant_out[0]["selected"]
best_worst = variant_out[2]["selected"]
DOC["verdict"] = {
    "class": "(ii) rigorous modulo a Monte-Carlo confidence level, correctly "
             "accounted -- and the accounting survives a family-wise correction",
    "part_a": "fully rigorous, no sampling anywhere; the union bound it uses is "
              "loose by "
              f"{100 * (1 - float(exact_some_cell_empty(8, NGATE)) / (8 * (7/8)**40)):.1f}% "
              "against the exact inclusion-exclusion probability, and K = 8 is "
              "the largest admissible K under BOTH",
    "part_b_selection_is_data_dependent": True,
    "part_b_family_is_fixed_in_advance": True,
    "part_b_survives_family_correction": bool(
        best_worst and best_worst["K"] == b36["K"]),
    "K_after_correction": best_worst["K"] if best_worst else None,
    "rho_after_correction": best_worst["rho"] if best_worst else None,
    "bound_after_correction": best_worst["uniform_bound"] if best_worst else None,
    "worst_p_C_ub_after_correction": (best_worst["worst_p_C_ub"] if best_worst
                                      else None),
    "union_failure_after_correction": (best_worst["union_failure"] if best_worst
                                       else None),
    "numbers_that_must_change_in_the_paper": [
        "the p_C upper bound 0.814 -> "
        f"{best_worst['worst_p_C_ub']:.4f} and 36*ub^40 = 0.010 -> "
        f"{best_worst['union_failure']:.4f} if the family-wise correction is "
        "stated (rho, the bound 0.933 and L <= 5.77 are UNCHANGED)",
        "the step-t claim 'Wilson lower bound per cell at level delta/K' is not "
        "what the code does (fixed z = 4)",
    ],
}
save(DOC)

# ---------------------------------------------------------------------------
# 8. self-checks. Every one of these is an assertion that the INTERESTING branch
#    was really exercised, not just that the code ran. Non-zero exit on failure,
#    so this script doubles as a regression test for the audit's own claims.
# ---------------------------------------------------------------------------
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "ok": bool(ok), "detail": str(detail)})


# -- oracle: the brute-force simulation agrees with exact inclusion-exclusion
for K in (8, 9):
    ex = next(r["exact"] for r in exact_rows if r["K"] == K)
    got = mc_check[str(K)]
    sd = math.sqrt(ex * (1 - ex) / 200000)
    check(f"brute-force MC of the K={K} coupon experiment matches the exact "
          f"inclusion-exclusion value within 4 sigma",
          abs(got - ex) < 4 * sd, f"exact {ex:.6f}, MC {got:.6f}, sd {sd:.6f}")
check("the exact probability, not just the union bound, caps part (a) at K = 8",
      DOC["part_a_exact_oracle"]["largest_K_admissible_exact"] == 8)
check("the union bound is an UPPER bound on the exact probability at every K",
      all(r["union_bound"] >= r["exact"] - 1e-15 for r in exact_rows))
check("the 400-gate measured failure sits between the exact probability's "
      "sampling noise and the published bound",
      VALID["rows"][0]["measured_failure_ci"][0]
      <= next(r["exact"] for r in exact_rows if r["K"] == 8)
      <= VALID["rows"][0]["measured_failure_ci"][1])

# -- oracle: Hoeffding inversion and conservatism
h = DOC["hoeffding_audit"]
check("Hoeffding's closed-form radius equals an independent bisection solve",
      h["closed_form_matches_bisection"])
check("the re-derived radius reproduces the certificate's published radius",
      h["matches_published_t"])
check("the exact binomial tail at the operating point is below the Hoeffding "
      "level it is charged (i.e. Hoeffding is conservative, as it must be)",
      h["hoeffding_is_conservative"],
      f"{h['oracle_exact_binomial_tail']:.3e} <= {h['oracle_hoeffding_level']:.3e}")
check("the delta budget is spent within delta", DOC["delta_budget"]["within_budget"])

# -- the headline is robust to every simultaneity correction
check("K = 36 / rho = 0.363 / bound 0.933 is selected under every correction, "
      "including Bonferroni over the whole candidate family and Clopper-Pearson",
      DOC["headline_robustness"]["unchanged_under_every_correction"])
check("the family-wise correction really did change the p_C bound (so the check "
      "above is not vacuous)",
      variant_out[2]["selected"]["worst_p_C_ub"]
      > variant_out[0]["selected"]["worst_p_C_ub"] + 1e-4,
      f"{variant_out[0]['selected']['worst_p_C_ub']:.4f} -> "
      f"{variant_out[2]['selected']['worst_p_C_ub']:.4f}")
check("at least one evaluated candidate was NOT certified (so the selection rule "
      "was actually binding)",
      any(not r["certified"] for r in variant_out[0]["rows"]))

# -- validation seeds are disjoint from the estimation seeds
check("the 400-gate validation draws rollouts disjoint from the 20k MC sample",
      DOC["seed_hygiene"]["validation_is_out_of_sample"],
      f"overlap {DOC['seed_hygiene']['overlap_size']}")

# -- the validation's step-index defect, and that it is exercised
psi = DOC["part_a_sample_index"]
check("step 0 really has v == 0 identically (the defect's precondition)",
      psi["v_at_step_0_is_identically_zero"])
check("step 1 really spreads v over +-V (so the two samples differ)",
      psi["step_1_v_is_spread_over_pm_V"], str(psi["step_1_v_range"]))
check("y is literally the same variable at step 0 and step 1 (why n_v = 1 is safe)",
      psi["y_is_the_same_variable_at_both_steps"])
_d = psi["demonstration"]["rows"]
check("at the certified split (n_v = 1) the as-validated and corrected samples "
      "both cover, and both bracket the exact failure probability",
      _d["2x1x4"]["cover_rate_as_validated_step0"] > 0.9
      and _d["2x1x4"]["cover_rate_step1_correct"] > 0.9)
check("at n_v >= 2 the as-validated (step-0) sample covers NEVER while the "
      "correct step-1 sample covers -- the defect is real and demonstrated",
      all(_d[k]["cover_rate_as_validated_step0"] == 0.0
          and _d[k]["cover_rate_step1_correct"] > 0.9
          for k in ("2x2x2", "1x2x4")),
      str({k: (_d[k]["cover_rate_as_validated_step0"],
               _d[k]["cover_rate_step1_correct"])
           for k in ("2x2x2", "1x2x4")}))

# -- step-t Wilson level
sw = DOC["step_t_wilson"]
check("the published step-t Wilson level is NOT delta/n_cells: at z = 4 the "
      "family-wise level over the a-priori family exceeds delta",
      sw["family_wise_level_published_vs_apriori_family"] > DELTA,
      f"{sw['family_wise_level_published_vs_apriori_family']:.3f} > {DELTA}")
if "recomputed" in sw:
    check("the reimplementation reproduces every published level-set cell count "
          "at z = 4 (so the corrected numbers are trustworthy)",
          sw.get("all_reproduce_published"))
    check("correcting the level shrinks every quoted volume (non-vacuous)",
          all(v["corrected"] < v["published"]
              for v in sw["paper_quoted_volumes"].values()),
          str({k: (round(v["published"], 4), round(v["corrected"], 4))
               for k, v in sw["paper_quoted_volumes"].items()}))

# -- out-of-sample replication of p_C
if "out_of_sample_p_C" in DOC:
    o = DOC["out_of_sample_p_C"]
    check("re-running the estimator on the published seeds reproduces 0.8001 "
          "exactly (the reimplementation is faithful)",
          o["reproduces_published"])
    check("a disjoint 20k-rollout stream leaves worst p_C inside the published "
          "upper bound, and the certificate still holds",
          o["fresh_estimate_inside_published_upper_bound"]
          and o["certificate_still_holds_on_fresh_sample"],
          f"fresh {o['fresh_worst_p_C']}, moved {o['abs_difference']:.5f} of "
          f"radius {o['hoeffding_radius']:.5f}")
    check("the fresh sample is genuinely a different sample (it moved p_C at all)",
          o["abs_difference"] > 0.0)

# -- the paper's own arithmetic
pa = DOC["paper_arithmetic"]
check("paper's 8*(7/8)^40 = 0.038 and 9*(8/9)^40 = 0.081",
      abs(pa["part_a"]["union_failure_K8_M40"] - 0.038) < 5e-4
      and abs(pa["part_a"]["union_failure_K9_M40"] - 0.081) < 5e-4)
check("paper's 36*0.814^40 = 0.010 <= delta/2",
      abs(pa["part_b"]["K_times_ub_pow_N"] - 0.010) < 5e-4
      and pa["part_b"]["K_times_ub_pow_N"] <= DELTA / 2)
check("paper's rho = 0.363, bound = 0.933, L_max = 5.77",
      abs(pa["part_b"]["rho"] - 0.363) < 5e-4
      and abs(pa["part_b"]["uniform_bound"] - 0.933) < 5e-4
      and abs(pa["part_b"]["L_max_excluding_4.2"] - 5.77) < 5e-3)

DOC["self_checks"] = CHECKS
DOC["self_checks_all_pass"] = all(c["ok"] for c in CHECKS)
save(DOC)

print("\nself-checks:")
for c in CHECKS:
    print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}"
          + (f"\n         {c['detail']}" if c["detail"] else ""))
n_bad = sum(1 for c in CHECKS if not c["ok"])
print(f"\nwrote {OUT}")
if n_bad:
    print(f"{n_bad}/{len(CHECKS)} self-checks FAILED")
    sys.exit(1)
print(f"{len(CHECKS)}/{len(CHECKS)} self-checks pass")
