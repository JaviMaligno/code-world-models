"""Audit paper 3's derived constants against the values a script computed.

The paper-2 lesson: every peer-review arithmetic error there was in a
hand-computed constant, and the fix was to stop computing them by hand.
So `scripts/t_campaign_constants.py` derives each constant from the
instrument's attributes and writes it to
results/t_campaign_constants.json, and this script checks that the numbers
appearing in docs/paper3/main.tex and docs/paper3/THEORY.md agree with it
AT THE PRINTED PRECISION — a document printing "1033" must agree with the
computed value to within half of the last printed digit.

A constant that appears in neither document is not an error (not every
computed value is quoted); a constant that appears with the WRONG value
is. Add new entries to CHECKS as constants enter the documents.

Exit code 0 iff every checked constant agrees. Run:
  PYTHONPATH=src python scripts/audit_paper3_numbers.py
"""
import json
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
DOCS = {
    "main.tex": _REPO / "docs" / "paper3" / "main.tex",
    "THEORY.md": _REPO / "docs" / "paper3" / "THEORY.md",
}
CONST = json.loads(
    (_REPO / "results" / "t_campaign_constants.json").read_text())


def value(path):
    d = CONST
    for k in path:
        d = d[k]
    return d


# (group/key path, printed forms) with an optional third field:
#   "lower"    the constant of a LOWER bound: printing below the computed value
#              is safe, printing above it makes the bound false.
#   "upper"    the constant of an UPPER bound: printing ABOVE the computed
#              value is safe (a looser but true bound), printing below it makes
#              the bound false. The mirror image of "lower" -- getting these
#              two backwards is how a rounding turns a true bound into a false
#              one, so each entry must name which side it is on.
#   "percent"  the document prints the value as a percentage, so compare
#              against 100x the computed fraction.
#   "endpoint" an interval endpoint INSIDE a proof (e.g. Lemma I's x0, where the
#              termwise inequality holds on [0, x0]): the printed value must
#              still satisfy the property, so it may only be rounded DOWN.
#              Rounding to nearest silently invalidates the proof step.
CHECKS = [
    (["plant", "step_bound_Delta"], ["1.0"]),
    (["plant", "landing_radius_R_L"], ["0.03"]),
    (["plant", "delta_pos_two_actions"], ["0.060", "0.06"]),
    (["plant", "delta_vel_two_actions"], ["0.600", "0.6"]),
    (["plant", "drag_cap_identical_actions"], ["2.06"]),
    (["plant", "one_action_endpoint_sensitivity"], ["3.14"]),
    (["plant", "two_action_jacobian_max"], ["9.87"]),
    (["plant", "two_action_image_area"], ["39.5"]),
    (["T4", "holder_constant"], ["1033"]),
    # The nominal (mean-start) rate; the BOUND uses r_out/L_min = 0.4348,
    # since L is random and an upper bound needs the largest ratio.
    (["T5", "sin_theta_cap_rate"], ["0.4167"]),
    (["T5", "sin_theta_cap_rate_at_L_min"], ["0.4344"], "upper"),
    (["T5", "kappa"], ["0.909"]),
    (["T5", "lemma_I_x0"], ["7/4"], "endpoint"),
    (["T5", "q_rho1_min"], ["0.7842"]),
    (["T5", "chernoff_u_star_asymptotic"], ["4.76"]),
    (["T5", "one_over_pi_gain_dt"], ["1.061"]),
    (["T5", "T5F_rate_per_dimension"], ["0.9104"], "lower"),
    (["T3", "reach_lower_bound_partitioned"], ["0.013"], "lower"),
    # Quoted as a percentage in both documents, so the printed form is 48.9
    # and the computed value must be scaled; PERCENT entries do that.
    (["T3", "reach_annulus_mass_below_tangent_cone_floor"],
     ["48.9"], "percent"),
    (["T3", "isotropy_angular_factor_superseded"], ["0.0950"]),
    (["T3", "quadratic_bound_coefficient"], ["0.0136"], "lower"),
    (["T3", "quadratic_bound_coefficient_from_sample_minimum_superseded"],
     ["0.0145556", "0.01455"], "lower"),
    (["T3", "ballistic_v_tan_coefficient_conservative"], ["1.944", "1.94"]),
    (["T3", "ballistic_v_tan_coefficient_at_r_out"], ["2.778", "2.78"]),
    (["T3", "pearson_walk", "E_Z2"], ["29.48"]),
    (["T3", "pearson_walk", "rms"], ["5.43"]),
    (["T3", "pearson_walk", "E_Z4"], ["1721.5"]),
    (["T2", "E_abs_sin_independent"], ["0.6366", "0.637"]),
    (["T2", "E_delta_vel_dominance_bound"], ["0.382"]),
    (["T2", "A_slope_proved"], ["178.5"]),
    (["T2", "A_slope_saturation_hypothesis"], ["4.46"]),
    (["T2", "L_p_proved"], ["52"]),
    (["T2", "position_term_contribution"], ["1.17"]),
    (["T2", "pc_proved_velocity_only"], ["80.3"]),
    (["T2", "pc_hypothesis_velocity_only"], ["2.01"]),
    (["T2", "pc_hypothesis_with_dominance"], ["1.28"]),
    (["T8", "clearance_margin_m"], ["0.5"]),
    # Emitted MEASUREMENTS quoted in the documents. Same discipline as the
    # constants: the prose must agree with the JSON at the printed precision,
    # and each entry names which side of its inequality it is on.
    (["measured", "R_ring_free"], ["0.03020"]),
    (["measured", "R_prime_leaving_k_steps"], ["0.02007"]),
    (["measured", "R_prime_leaving_k_minus_1_steps"], ["0.02118"]),
    (["measured", "rho_at_pi"], ["1.0295", "1.03"]),
    (["measured", "steering_sup"], ["0.580"], "upper"),
    (["measured", "steering_p90"], ["0.550"]),
    (["measured", "steering_jump_max"], ["14.41"]),
    (["measured", "rho_pi_per_arrival_lower_bound"], ["0.2537"], "lower"),
    (["measured", "rho_sub_pi_lower_bound"], ["0.00766"], "lower"),
    (["measured", "rho_pi_looseness"], ["4.06"]),
    (["measured", "P_root_exists"], ["0.00889"], "lower"),
    (["measured", "drag_cap_worst_400x200"], ["1.9956"]),
    (["measured", "conditional_spread_A_t"], ["3.69"]),
]


def as_float(printed):
    """Value of a printed form, which may be a rational like "7/4".

    A constant that a proof pins to a decimal expansion is a constant that
    depends on rounding, so the documents are allowed --- encouraged --- to
    print an exact rational instead. The audit then compares the rational's
    exact value, and the tolerance is 0: an exact form must be exact.
    """
    if "/" in printed:
        num, den = printed.split("/")
        return float(num) / float(den)
    return float(printed)


# Constants whose disappearance from both documents is a REGRESSION, not a
# non-event: each is load-bearing in a claim, so if the audit stops finding it
# the audit has silently stopped covering that claim.
MUST_APPEAR = {
    "T4/holder_constant",
    "T5/lemma_I_x0",
    "T5/T5F_rate_per_dimension",
    "T2/A_slope_proved",
    "T2/pc_hypothesis_with_dominance",
    "T3/quadratic_bound_coefficient",
    "T3/reach_lower_bound_partitioned",
    "T3/reach_annulus_mass_below_tangent_cone_floor",
    "measured/R_ring_free",
    "measured/R_prime_leaving_k_minus_1_steps",
    "measured/drag_cap_worst_400x200",
}


def tolerance(printed):
    """Half of the last printed digit."""
    if "/" in printed:
        return 0.0          # an exact rational is compared exactly
    if "." in printed:
        return 0.5 * 10 ** -(len(printed.split(".")[1]))
    return 0.5


def main():
    text = {name: p.read_text() for name, p in DOCS.items()}
    failures, checked, unquoted = [], 0, []
    for entry in CHECKS:
        path, printeds = entry[0], entry[1]
        kind = entry[2] if len(entry) > 2 else "exact"
        try:
            computed = float(value(path))
            if kind == "percent":
                computed *= 100.0
        except (KeyError, TypeError):
            failures.append(f"{'/'.join(path)}: not emitted by "
                            f"t_campaign_constants.py")
            continue
        found_anywhere = False
        for printed in printeds:
            pat = re.compile(r"(?<![\d./])" + re.escape(printed)
                             + (r"(?![\d])" if "/" in printed
                                else r"(?![\d/])"))
            for name, body in text.items():
                if pat.search(body):
                    found_anywhere = True
                    checked += 1
                    err = as_float(printed) - computed
                    if kind in ("lower", "endpoint"):
                        bad = err > (0.0 if kind == "endpoint"
                                     else tolerance(printed))
                    elif kind == "upper":
                        bad = err < -tolerance(printed)
                    else:
                        bad = abs(err) > tolerance(printed)
                    if bad:
                        how = {
                            "lower": "EXCEEDS the computed value, so the bound "
                                     "it states is false",
                            "endpoint": "EXCEEDS the computed endpoint, so the "
                                        "proof step it feeds is invalid there",
                            "upper": "is BELOW the computed value, so the "
                                     "upper bound it states is false",
                        }.get(kind, "disagrees with the computed value")
                        failures.append(
                            f"{name}: prints {printed} for "
                            f"{'/'.join(path)}, which {how} "
                            f"({computed:.7g})")
        if not found_anywhere:
            unquoted.append("/".join(path))

    print(f"checked {checked} document occurrences of "
          f"{len(CHECKS)} computed constants")
    if unquoted:
        print(f"not quoted in either document ({len(unquoted)}): "
              + ", ".join(unquoted))
        stale = [u for u in unquoted if u in MUST_APPEAR]
        if stale:
            failures.append(
                "these constants are listed as appearing in the documents but "
                "no longer do -- either the document changed the printed form "
                "(so the audit stopped covering it) or the claim was removed "
                "and the check is stale: " + ", ".join(stale))
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ::error:: {f}")
        return 1
    print("all quoted constants agree with the computed values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
