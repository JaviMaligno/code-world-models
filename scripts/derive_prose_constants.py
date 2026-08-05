"""Derive the constants main.tex quotes in prose but no other artifact writes.

This repository's known weak class is the hand-computed prose number: every error five
peer reviews found was in a constant that lived only inside a sentence, because an audited
number is re-derived on every push and a retyped one is re-derived never. The claims
linter flags such constants (rule `hand-constant`); this script closes the gap by
re-deriving each from a committed measurement, so `scripts/audit_paper2_numbers.py` can
check the sentence against data instead of trusting its digits.

Run: PYTHONPATH=src python scripts/derive_prose_constants.py
Writes: results/prose_constants.json
"""
import json
import math
import pathlib

R = pathlib.Path(__file__).resolve().parents[1] / "results"


def L(name: str) -> dict:
    return json.loads((R / f"{name}.json").read_text())


def main() -> None:
    reach, axes = L("continuous_reach"), L("continuous_axes")
    dens, bounds = L("gate_density_constant"), L("play_cost_proved_bounds")
    part, phantom = L("gate_partition_certificate"), L("phantom_targeting_probability")

    out: dict = {
        "script": "derive_prose_constants.py",
        "why": ("Constants quoted in docs/paper2/main.tex's prose that no other artifact "
                "produced. Each is re-derived here from a committed measurement so the "
                "numeric audit reads it from data rather than from the sentence."),
        "reads": ["continuous_reach", "continuous_axes", "gate_density_constant",
                  "play_cost_proved_bounds", "gate_partition_certificate",
                  "phantom_targeting_probability"],
    }

    # --- Corollary cor:cartdensity's coefficient and the ball radius it implies ------
    c = dens.get("c_closed_form", dens.get("c", 5 / 6))
    N, delta, dm = 40, 0.5, 3
    coef = (c * N / math.log(1 / delta)) ** (1 / dm)
    out["detectrate_coefficient"] = {
        "value": coef, "printed_in_tex": 3.636,
        "formula": "(c*N/ln(1/delta))^(1/(d+m)), c = 5/6, N = 40, delta = 1/2, d+m = 3",
        "c": c, "c_source": "gate_density_constant.json",
        "note": "L >= 3.636*(eta - eps) in cor:cartdensity"}
    out["ball_radius_uniform_over_rows"] = {
        "value": 1.0 / (2 * coef), "printed_in_tex": 0.1375,
        "formula": "rho = 1/(2*coefficient): eta - eps cancels, so the radius is the "
                   "same in every row of the corollary"}

    # --- the guaranteed ball radius at the plant's own Lipschitz constant -----------
    L_plant = part["L_plant"]
    eta_wall, eps_gate = 4.2, 0.01
    out["ball_radius_at_plant_lipschitz"] = {
        "value": (eta_wall - eps_gate) / (2 * L_plant), "printed_in_tex": 1.65,
        "formula": "(eta - eps)/(2L) with eta = 4.2 (the wall probe error), eps = 0.01, "
                   "L = the plant's sup-metric Lipschitz constant",
        "L_plant": L_plant, "L_plant_source": "gate_partition_certificate.json::L_plant"}

    # --- the corner hypothesis: rho/2 against U's narrowest extent -------------------
    # This belongs to the PACKING instantiation (rho = 1.165), not to the partition one
    # (rho = 0.600): the corner argument is what a packing bound needs and a partition
    # bound does not, which is the point of that paragraph.
    cov = L("gate_coverage_certificate")
    rig = next(r for r in cov["regimes"] if "rigorous" in r["regime"])
    narrowest = min(2 * part["U"]["V"], 2 * part["U"]["Y"], 2 * part["U"]["a_max"])
    out["packing_corner_hypothesis"] = {
        "rho": rig["rho"], "half_rho": rig["rho"] / 2, "printed_in_tex": 0.583,
        "uniform_bound": rig["uniform_bound"],
        "narrowest_extent_of_U": narrowest,
        "hypothesis_satisfied": rig["rho"] / 2 <= narrowest,
        "margin": narrowest - rig["rho"] / 2,
        "note": "the corner argument needs every extent of U to be at least rho/2; the "
                "paper says it holds 'if barely', and the margin quantifies that"}

    # --- the play-cost ceiling at x_wall = 8, and how much of it is attained --------
    row8 = next(r for r in reach["rows"] if r["x_wall"] == 8.0)
    b8 = next(r for r in bounds["rows"] if r["x_wall"] == 8.0)
    denom = bounds["J_truth"] - bounds["J_rand"]
    ceiling = (b8["J_max_proved"] - b8["J_min_proved"]) / denom
    out["play_cost_ceiling_xwall8"] = {
        "J_max_proved": b8["J_max_proved"], "J_min_proved": b8["J_min_proved"],
        "J_truth": bounds["J_truth"], "J_rand": bounds["J_rand"],
        "denominator": denom, "printed_denominator_in_tex": 17.238,
        "ceiling": ceiling, "printed_ceiling_in_tex": 1.0463,
        "measured_play_cost": row8["play_cost"],
        "pct_of_ceiling_attained": 100 * row8["play_cost"] / ceiling,
        "printed_pct_in_tex": 98.4}

    # --- the two rarity estimates of one event, and the interval each predicts ------
    rev = next(r for r in axes["rows"] if r["arm"] == "wall@8 omitted")
    ci = rev.get("rarity_ci")
    out["two_rarity_estimates_xwall8"] = {
        "firing_rarity_30k": row8["rarity"], "printed_firing_in_tex": 0.01140,
        "reveal_rarity_20k": rev["rarity"],
        "predicted_pass_from_firing": (1 - row8["rarity"]) ** 40,
        "printed_pass_from_firing_in_tex": 0.631,
        "predicted_pass_from_reveal": (1 - rev["rarity"]) ** 40,
        "reveal_rarity_ci": ci,
        "predicted_pass_interval": [(1 - ci[1]) ** 40, (1 - ci[0]) ** 40] if ci else None,
        "printed_interval_in_tex": [0.623, 0.698],
        "measured_pass": rev["pass_rate"],
        "note": "propagating the rarity's own interval through (1-r)^40 is what makes the "
                "comparison against the measured pass rate legitimate"}

    # --- the blind model's imagined right-vs-left returns over the planner horizon ---
    p8 = next((r for r in phantom["rows"]
               if abs(r.get("imagined_return_left", -1) + 1) > 1e-9), None)
    ps = bounds["pinning_structure"]
    row = next(r for r in ps if r["x_wall"] == 8.0)
    out["phantom_lure_asymmetry"] = {
        "imagined_return_right": row["imagined_return_right"],
        "imagined_return_left": row["imagined_return_left"],
        "printed_left_in_tex": 5.70, "printed_right_in_tex": 8.31,
        "asymmetry_ratio": row["asymmetry_ratio"], "printed_ratio_in_tex": 1.46,
        "source": "play_cost_proved_bounds.json::pinning_structure",
        "note": "the asymmetry that makes 'right' the argmax under the blind model"}

    # --- the expected-return reading of J_max, quoted to contrast with the pointwise --
    out["best_constant_policy_expected_return"] = {
        "printed_in_tex": 17.697,
        "measured_J_truth": bounds["J_truth"],
        "below_measured_J_truth": 17.697 < bounds["J_truth"],
        "note": "quoted in main.tex only to show that the EXPECTED-return reading of "
                "J_max falls below the measured J_truth, so it cannot be the normalizer "
                "prop:playcost needs; the inequality is the claim, not the digits"}

    (R / "prose_constants.json").write_text(json.dumps(out, indent=2))
    for k, v in out.items():
        if isinstance(v, dict) and "printed_in_tex" in v:
            print(f"  {k}: derived {v.get('value')}  printed {v['printed_in_tex']}")
    print(f"  detectrate coefficient {coef:.6f} -> printed 3.636")
    print(f"  ceiling {ceiling:.6f} -> printed 1.0463, attained "
          f"{out['play_cost_ceiling_xwall8']['pct_of_ceiling_attained']:.2f}%")
    print(f"wrote {R / 'prose_constants.json'}")


if __name__ == "__main__":
    main()
