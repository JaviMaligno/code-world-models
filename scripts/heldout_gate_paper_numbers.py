"""The held-out-gate numbers the paper quotes, with the hypotheses' scope enforced.

`scripts/heldout_gate_audit.py` re-scores every versioned artifact on independent
acceptance (D_gate) and evaluation (D_eval) blocks and writes the per-artifact record.
This script derives the paper-facing aggregates from that record, and it exists as a
separate step because the aggregates need restrictions the raw audit does not apply:

  * Proposition prop:twofactor's hypotheses concern a MODE-BLIND artifact produced from a
    mode-free training sample. A `full`-arm artifact has the mode clause in its
    specification, so it is correct by construction and passes an independent gate whether
    or not that gate contains a mode contact. Including full-arm cells in the contingency
    table makes hypothesis (ii) look violated 35 times when it is not being tested at all.
  * The paper's off-sample regularity is a claim about ACCEPTED artifacts. An artifact that
    never passed its own gate is not evidence about what acceptance implies.
  * The unit is the gate-sample block, not the synthesis draw (see
    scripts/paper2_statistics.py). Every rate below is reported over blocks, and the
    per-campaign rates over draws are labelled as such.

Run: PYTHONPATH=src python scripts/heldout_gate_paper_numbers.py
Writes: results/heldout_gate_paper_numbers.json
"""
import json
import math
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = REPO / "results" / "heldout_gate_audit.json"
OUT = REPO / "results" / "heldout_gate_paper_numbers.json"


def wilson(k: int, n: int, z: float = 1.959963984540054):
    """Two-sided Wilson interval; (0.0, 0.0) for n == 0."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson upper limit, by bisection on the binomial tail
    P(X <= k) = alpha.  For k = 0 this is 1 - alpha**(1/n) exactly, which the
    bisection reproduces and the test checks."""
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0

    def tail(p):  # P(X <= k) under Bin(n, p)
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if tail(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def cp_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson lower limit: 1 - cp_upper(n-k, n)."""
    if n == 0:
        return 0.0
    return 1.0 - cp_upper(n - k, n, alpha)


def main() -> None:
    audit = json.loads(SRC.read_text())
    arts = audit["artifacts"]
    split = audit["split"]
    assert split["all_disjoint"], "the audit's own disjointness check failed"
    tr = audit["aggregates"]["train_reproduction_check"]
    assert tr["n_checked"] == tr["n_accuracy_matches"] == tr["n_mode_flag_matches"], \
        "the training sample was not reproduced exactly; every number below is void"

    out: dict = {
        "script": "heldout_gate_paper_numbers.py",
        "reads": "results/heldout_gate_audit.json",
        "design": {
            "N_train": split["n_train"], "N_gate": split["n_gate"],
            "N_eval": split["n_eval"],
            "blocks_disjoint": split["all_disjoint"],
            "train_reproduced_exactly": f"{tr['n_accuracy_matches']}/{tr['n_checked']}",
            "why_full_arm_is_excluded":
                "prop:twofactor's hypotheses (i) and (ii) concern a mode-blind artifact "
                "synthesized from a mode-free training sample. A full-arm artifact carries "
                "the mode clause in its specification, so it is correct by construction; it "
                "is not a test of either hypothesis and is excluded from every rate below.",
        },
    }

    inc = [a for a in arts if a["arm"] == "incomplete"]
    full = [a for a in arts if a["arm"] == "full"]

    # ---- (1) hypothesis (ii): a mode-blind artifact fails the gate iff the gate sees the mode
    blind = [a for a in inc if a["probe_blind_all_modes"] and not a["mode_in_train"]["any"]]
    tab = {"gate_mode_absent": {"accepted": 0, "rejected": 0},
           "gate_mode_present": {"accepted": 0, "rejected": 0}}
    off_diag = []
    for a in blind:
        row = "gate_mode_present" if a["mode_in_gate"]["any"] else "gate_mode_absent"
        col = "accepted" if a["accepted_heldout"] else "rejected"
        tab[row][col] += 1
        if (row == "gate_mode_present") == (col == "accepted"):
            off_diag.append({"file": a["file"], "seed": a["seed"], "row": row, "col": col,
                             "gate_accuracy": a["gate"]["accuracy"],
                             "n_fail_mode_contact": a["gate"]["n_fail_mode_contact"],
                             "n_fail_off_mode": a["gate"]["n_fail_off_mode"],
                             "n_mode_contact_in_gate": a["gate"]["n_mode_contact"]})
    agree = tab["gate_mode_absent"]["accepted"] + tab["gate_mode_present"]["rejected"]
    out["hypothesis_ii"] = {
        "claim": "for a mode-blind artifact, held-out acceptance coincides with the "
                 "acceptance sample containing no mode contact",
        "restricted_to": "incomplete arm, probe-blind on every mode, mode absent from D_train",
        "n": len(blind), "table": tab,
        "n_agree": agree, "n_disagree": len(blind) - agree,
        "coincides_exactly": len(blind) > 0 and agree == len(blind),
        "off_diagonal": off_diag,
    }

    # ---- (2) the two-factor law, decomposed so each half is tested at its own unit.
    #
    # The event {train misses the mode AND the acceptance sample misses it} is a property
    # of the BLOCK alone -- no model enters it -- so its unit is the distinct block, and
    # mini and large on a shared block give the same answer by construction. Hypothesis (i)
    # ("mode-free training sample => mode-blind artifact") is instead a property of the
    # synthesis draw. Testing the product without separating the two would charge a model
    # property to a sampling unit, and would double-count the shared blocks.
    def two_factor(env_key: str, files: list[str], r: float):
        cells = [a for a in inc if a["env_key"] == env_key and a["file"] in files]
        # (a) the pure sampling event, per DISTINCT block
        blocks: dict[str, dict] = {}
        for a in cells:
            b = blocks.setdefault(a["block_key"], {"train_miss": None, "gate_miss": None,
                                                   "n_draws": 0})
            tm, gm = not a["mode_in_train"]["any"], not a["mode_in_gate"]["any"]
            # a block's mode content is model-independent: assert the draws agree
            if b["train_miss"] is not None:
                assert b["train_miss"] == tm and b["gate_miss"] == gm, \
                    f"block {a['block_key']} disagrees across draws: sample not reproducible"
            b["train_miss"], b["gate_miss"] = tm, gm
            b["n_draws"] += 1
        n_b = len(blocks)
        k_both = sum(1 for b in blocks.values() if b["train_miss"] and b["gate_miss"])
        k_train = sum(1 for b in blocks.values() if b["train_miss"])
        lo, hi = wilson(k_both, n_b)
        lo1, hi1 = wilson(k_train, n_b)
        p2 = (1 - r) ** (split["n_train"] + split["n_gate"])
        p1 = (1 - r) ** split["n_train"]
        # (b) hypothesis (i), per DRAW, on the mode-free-training draws
        tm_draws = [a for a in cells if not a["mode_in_train"]["any"]]
        blind_draws = [a for a in tm_draws if a["probe_blind_all_modes"]]
        return {
            "env_key": env_key, "files": files, "r": r,
            "unit_a": "distinct gate-sample block (model-independent event)",
            "n_distinct_blocks": n_b, "n_draws": len(cells),
            "sampling_event": {
                "k_train_miss_and_gate_miss": k_both, "measured": k_both / n_b,
                "wilson95": [lo, hi],
                "predicted_two_factor": p2,
                "two_factor_inside_interval": lo <= p2 <= hi,
                "k_train_miss_only": k_train, "measured_train_miss": k_train / n_b,
                "wilson95_train_miss": [lo1, hi1],
                "predicted_one_factor": p1,
                "one_factor_inside_interval": lo1 <= p1 <= hi1,
            },
            "hypothesis_i": {
                "unit": "synthesis draw",
                "n_mode_free_training_draws": len(tm_draws),
                "k_mode_blind": len(blind_draws),
                "rate": len(blind_draws) / len(tm_draws) if tm_draws else None,
                "wilson95": list(wilson(len(blind_draws), len(tm_draws))),
                "note": "hypothesis (i) of prop:twofactor; a draw that is NOT mode-blind on a "
                        "mode-free training sample got its mode content from the model's prior",
            },
        }

    r_cart = audit["r_sources"]["cart_xwall8"]["r"]
    out["two_factor_cart_xwall8"] = two_factor(
        "cart_xwall8",
        ["continuous_synthesis_large_xwall8.json",
         "continuous_synthesis_large_xwall8_off20.json",
         "continuous_synthesis_mini_xwall8.json"],
        r_cart)

    # ---- (3) regressions: accepted in-sample, rejected by an independent gate
    passed = [a for a in arts if a["in_sample_gate_passed"]]
    reg = [a for a in passed if not a["accepted_heldout"]]
    reg_inc = [a for a in reg if a["arm"] == "incomplete"]
    by_c: dict[str, dict] = {}
    for a in passed:
        c = by_c.setdefault(a["campaign"], {"n_passed": 0, "n_regressed": 0})
        c["n_passed"] += 1
        if not a["accepted_heldout"]:
            c["n_regressed"] += 1
    out["regressions"] = {
        "claim": "artifacts the sample-consistency gate accepted that an independent "
                 "acceptance sample of the same size rejects",
        "n_in_sample_accepted": len(passed),
        "n_rejected_by_independent_gate": len(reg),
        "rate_over_draws": len(reg) / len(passed),
        "wilson95_over_draws": list(wilson(len(reg), len(passed))),
        "n_incomplete_arm": len(reg_inc),
        "n_full_arm": len(reg) - len(reg_inc),
        "by_campaign": by_c,
        "failure_is_on_the_mode": {
            "n_fail_only_on_mode_contacts":
                sum(1 for a in reg if a["gate"]["n_fail_off_mode"] == 0
                    and a["gate"]["n_fail_mode_contact"] > 0),
            "n_fail_off_mode_too":
                sum(1 for a in reg if a["gate"]["n_fail_off_mode"] > 0),
        },
    }

    # ---- (4) off-sample exactness, restricted to ACCEPTED artifacts
    acc = [a for a in arts if a["accepted_heldout"]]
    exc = [a for a in acc if not a["eval"]["exact_outside_mode"]]
    # both derived, because the campaign set grows: this note used to name 625 by hand
    # and went stale the moment the eighth campaign landed
    n_exc_all = sum(1 for a in arts if not a["eval"]["exact_outside_mode"])
    out["off_sample_exactness_of_accepted"] = {
        "claim": "of the artifacts an independent gate accepts, how many are exact "
                 "OUTSIDE the mode region on a further independent sample",
        "n_accepted": len(acc),
        "n_exact_outside_mode": len(acc) - len(exc),
        "n_exceptions": len(exc),
        "exceptions": [{"file": a["file"], "arm": a["arm"], "seed": a["seed"],
                        "model": a["model"], "eval_accuracy": a["eval"]["accuracy"],
                        "n_fail_off_mode": a["eval"]["n_fail_off_mode"],
                        "max_err_off_mode_fail": a["eval"]["max_err_off_mode_fail"]}
                       for a in exc],
        "clopper_pearson_95_upper_on_exception_rate":
            cp_upper(len(exc), len(acc)),
        "n_all_artifacts": len(arts),
        "n_exceptions_over_all_artifacts": n_exc_all,
        "note": (f"the {n_exc_all} exceptions in the audit's own "
                 f"d_out_of_sample_exactness are over ALL {len(arts)} artifacts, most of "
                 f"which never passed any gate; acceptance is the condition the paper's "
                 f"claim is about. Both counts are derived here rather than typed: the "
                 f"campaign set grows, and this note named 625 by hand until it went stale"),
    }

    # ---- (5) what the in-sample gate's 1.000 scores were worth, by arm
    out["by_arm"] = {}
    for name, group in (("incomplete", inc), ("full", full)):
        p = [a for a in group if a["in_sample_gate_passed"]]
        out["by_arm"][name] = {
            "n": len(group), "n_in_sample_passed": len(p),
            "n_heldout_accepted": sum(1 for a in p if a["accepted_heldout"]),
            "n_regressed": sum(1 for a in p if not a["accepted_heldout"]),
        }

    OUT.write_text(json.dumps(out, indent=2))

    h = out["hypothesis_ii"]
    print(f"hypothesis (ii): {h['n_agree']}/{h['n']} agree, "
          f"coincides_exactly={h['coincides_exactly']}")
    print(f"  table {json.dumps(h['table'])}")
    t = out["two_factor_cart_xwall8"]
    se, hi_ = t["sampling_event"], t["hypothesis_i"]
    print(f"two-factor (cart): {t['n_distinct_blocks']} distinct blocks, {t['n_draws']} draws")
    print(f"  train-miss AND gate-miss: {se['k_train_miss_and_gate_miss']}/"
          f"{t['n_distinct_blocks']} = {se['measured']:.3f} "
          f"{[round(x,3) for x in se['wilson95']]} vs predicted "
          f"{se['predicted_two_factor']:.4f} (inside={se['two_factor_inside_interval']})")
    print(f"  train-miss only:          {se['k_train_miss_only']}/{t['n_distinct_blocks']} = "
          f"{se['measured_train_miss']:.3f} "
          f"{[round(x,3) for x in se['wilson95_train_miss']]} vs predicted "
          f"{se['predicted_one_factor']:.4f} (inside={se['one_factor_inside_interval']})")
    print(f"  hypothesis (i): {hi_['k_mode_blind']}/{hi_['n_mode_free_training_draws']} draws "
          f"mode-blind {[round(x,3) for x in hi_['wilson95']]}")
    r = out["regressions"]
    print(f"regressions: {r['n_rejected_by_independent_gate']}/{r['n_in_sample_accepted']} "
          f"= {r['rate_over_draws']:.3f} {[round(x,3) for x in r['wilson95_over_draws']]}"
          f"  (incomplete arm {r['n_incomplete_arm']}); "
          f"mode-only failures {r['failure_is_on_the_mode']['n_fail_only_on_mode_contacts']}")
    e = out["off_sample_exactness_of_accepted"]
    print(f"off-sample exactness of accepted: {e['n_exact_outside_mode']}/{e['n_accepted']}, "
          f"{e['n_exceptions']} exceptions, CP95 upper "
          f"{e['clopper_pearson_95_upper_on_exception_rate']:.4f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
