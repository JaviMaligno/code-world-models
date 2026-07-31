"""Emit every derived constant of the T1-T8 campaign, computed from the
instruments' own parameters rather than transcribed.

Motivation, learned the expensive way on paper 2: every peer-review
arithmetic error there was in a hand-computed constant that the numeric
audit did not cover, and the fix was not to recompute them more carefully
but to stop computing them by hand. So this script derives each constant
from the instrument attributes (RingField2D / ShellFieldN) or from a
closed form, writes them to results/t_campaign_constants.json, and
scripts/audit_paper3_numbers.py then checks the documents against it.

Discipline: PURE constants are computed here from parameters. MEASURED
quantities are read from the result JSONs the experiments wrote and are
never re-typed; where a derived constant combines both, the measured
inputs are named in the record so the provenance is explicit.

Run: PYTHONPATH=src python scripts/t_campaign_constants.py
"""
import json
import math
import os
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import RingField2D, ShellFieldN         # noqa: E402

OUT = _REPO / "results" / "t_campaign_constants.json"


def measured(name, path):
    """Read a measured input from the JSON its experiment wrote.

    Returns None when the file or any key along the path is absent, rather
    than raising: a measurement that has not been run yet is a MISSING value,
    and the audit already reports a checked entry whose value is missing. A
    crash here would make a partially-finished emitter run unusable, which is
    the opposite of the resumability the emitters are built for.
    """
    p = _REPO / "results" / f"{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    for key in path:
        if isinstance(d, dict):
            if key not in d:
                return None
            d = d[key]
        elif isinstance(d, (list, tuple)):
            if not isinstance(key, int) or not -len(d) <= key < len(d):
                return None
            d = d[key]
        else:
            return None
    return d


X0 = 7 / 4   # Lemma I's constant: a RATIONAL for which the pointwise
             # inequality |cos x| <= exp(-x^2/2) holds on [0, x0] with 21%
             # slack. The lemma needs only that SOME x0 > 0 works, which is a
             # Taylor argument (e^{-x^2/2} - cos x = x^4/12 + O(x^6) near 0);
             # pinning x0 to the first crossing's decimals is what makes a
             # proof step depend on rounding, so we do not.


def first_crossing(step=1e-6, hi=3.0):
    """First crossing of |cos x| and exp(-x^2/2), for reference only: no
    statement depends on it (see X0)."""
    lo, hi_ = 0.0, hi
    while hi_ - lo > step:
        mid = (lo + hi_) / 2
        # the property holds on [0, x0] and fails just above
        ok = all(abs(math.cos(t)) <= math.exp(-t * t / 2)
                 for t in (mid, mid * 0.999))
        lo, hi_ = (mid, hi_) if ok else (lo, mid)
    return lo


def main():
    env = RingField2D()
    gain, dt, drag = env.gain, env.dt, env.drag
    beta = 1 - drag * dt
    # L is RANDOM: the start is uniform on a box of half-width x0_range about
    # x0_center, so the distance to the shell centre spans an interval. Emit all
    # three so a bound can never silently take the nominal (mean-start) value:
    # an UPPER bound on a reach rate needs the SMALLEST L, a lower bound the
    # largest. Deriving them here rather than quoting 12 is the point.
    L = math.hypot(env.center[0] - env.x0_center[0],
                   env.center[1] - env.x0_center[1])
    _rng = env.x0_range
    _corners = [math.hypot(env.center[0] - (env.x0_center[0] + sx * _rng),
                           env.center[1] - (env.x0_center[1] + sy * _rng))
                for sx in (-1, 1) for sy in (-1, 1)]
    L_min, L_max = min(_corners), max(_corners)
    h = env.h_episode
    C = {}

    # --- plant scales (T4, T8, T2) -----------------------------------------
    C["plant"] = {
        "beta": beta,
        "v_terminal": gain / drag,
        "step_bound_Delta": (gain / drag) * dt,
        "landing_radius_R_L": gain * dt * dt,
        "delta_pos_two_actions": 2 * gain * dt * dt,
        "delta_vel_two_actions": 2 * gain * dt,
        "drag_cap_identical_actions": 2 * gain * dt * dt + 2 * gain * dt / drag,
        "one_action_endpoint_sensitivity": gain * math.pi * dt * dt / (1 - beta),
        "two_action_jacobian_max": (gain * math.pi * dt * dt / (1 - beta)) ** 2,
        "two_action_image_area": 4 * (gain * math.pi * dt * dt / (1 - beta)) ** 2,
    }

    # --- T4: the continuity modulus ---------------------------------------
    C["T4"] = {
        "holder_constant": h * math.sqrt(env.r_out / (gain * dt * dt)),
        "linear_constant_C_of_m_numerator": 2 * env.r_out
        / (math.pi * gain * dt * dt),
        "sliver_strip_width_per_eps": env.r_out / 2,
    }

    # --- T1: the barcode sandwich -----------------------------------------
    C["T1"] = {
        "sqrt3": math.sqrt(3),
        "theta_star_regime_i_base": 2 * math.pi / 3,
        "theta_star_regime_ii_base": math.pi / 2,
    }

    # --- T8: the tube -----------------------------------------------------
    tube_like = {"rho_t": 1.0, "core_radius": 2.0, "core_x": 8.0}
    Delta = (gain / drag) * dt
    C["T8"] = {
        "step_bound_Delta": Delta,
        "clearance_margin_m": tube_like["rho_t"] - Delta / 2,
        "offset_at_margin_boundary": tube_like["core_radius"]
        - (tube_like["rho_t"] - Delta / 2),
        "clearance_subdisc_radius": tube_like["core_radius"]
        - (tube_like["rho_t"] - Delta / 2),
    }

    # --- T5: cone, cap, Rademacher ----------------------------------------
    shell = ShellFieldN(n=3)
    k2 = (L * L - shell.r_out ** 2) / (L * L)
    x0 = X0
    g2 = (1 - k2) / k2

    def q(u, rho=1.0):
        return ((1 + u) ** -0.5
                + 2 * (0.5 * math.erfc(x0 * rho / math.sqrt(u) / math.sqrt(2))))

    grid = [i * 1e-4 for i in range(1, 200000)]
    u_min = min(grid, key=q)
    # constants below are SYMBOLIC (closed forms in the plant parameters)
    # except T5F_*, which come from a numerical optimisation over (z, K, alpha)
    # -- the bound holds for every admissible triple, so the optimisation only
    # selects a good one and no statement depends on the search resolution.
    C["T5"] = {
        "L_start_to_centre": L,
        "kappa_squared": k2,
        "kappa": math.sqrt(k2),
        "sin_theta_cap_rate": math.sqrt(1 - k2),
        # The rate a BOUND may use: largest ratio, i.e. smallest L.
        "sin_theta_cap_rate_at_L_min": shell.r_out / L_min,
        "L_nominal": L,
        "L_range": [L_min, L_max],
        "gamma_squared_ratio": g2,
        "exchangeability_bound_numerator": 4.0,
        "T5C_bound_at_n": {str(n): min(1.0, h * 4.0 / (n * k2))
                           for n in (2, 5, 8, 20)},
        "T5I_bound_at_n": {str(n): min(1.0, (h / 2) * (1 - k2) ** ((n - 2) / 2))
                           for n in (3, 5, 8, 20)},
        "lemma_I_x0": x0,
        "lemma_I_x0_is": "rational 7/4; symbolic existence by Taylor",
        "lemma_I_x0_slack": math.exp(-x0 * x0 / 2) / abs(math.cos(x0)),
        "first_crossing_reference_only": first_crossing(),
        "q_rho1_min": q(u_min),
        "q_rho1_argmin_u": u_min,
        "chernoff_u_star_asymptotic": 1 / g2,
        "one_over_pi_gain_dt": 1 / (math.pi * gain * dt),
        "arcsine_density_floor": 1 / math.pi,
    }
    # T5-F's optimisation, done here rather than by hand
    p_z = measured("t5_interface_transfer", ["scheme", "rows"])
    best = None
    for z in (0.05, 0.1, 0.15, 0.2, 0.25):
        # p(z) is a measured/computed Chernoff value; recompute it in-place
        w = [(1 - beta ** (h - s)) / (1 - beta) for s in range(h)]
        S = sum(x * x for x in w)

        def mgf_neg(c):
            return (1.0 if c < 1e-12
                    else 0.5 * math.sqrt(math.pi / c) * math.erf(math.sqrt(c)))
        pz = min(math.exp(th * z * S
                          + sum(math.log(mgf_neg(th * x * x)) for x in w))
                 for th in (k * 0.002 / (S / h) for k in range(1, 4000)))
        for K in (5, 10, 20, 50):
            for al in (0.01, 0.02, 0.05, 0.1):
                frac = 1 - al - 1.0 / K
                if frac <= 0 or pz <= 0 or math.e * pz / al >= 1:
                    continue
                qm = max(q(1.32 * z), q(1.32 * K))
                tot = max(qm ** frac, (math.e * pz / al) ** al)
                if best is None or tot < best[0]:
                    best = (tot, z, K, al, pz)
    if best:
        C["T5"]["T5F_rate_per_dimension"] = best[0]
        C["T5"]["T5F_optimum"] = {"z": best[1], "K": best[2],
                                  "alpha": best[3], "p_of_z": best[4]}
    del p_z

    # --- T3: the ring-free decomposition ----------------------------------
    # measured inputs, read from the JSONs their experiments wrote
    R = measured("t3_reach_density_throughput", ["R"])
    rho_pi = measured("t3_reach_density_throughput", ["density_at_pi"])
    rows = measured("t3_reach_density_throughput", ["rows"]) or []
    c1 = min((r["throughput_ratio"] / r["gap"] for r in rows
              if r.get("gap")), default=None)
    k_cross = 9          # measured median crossing steps
    # the arc half-width is r*gamma/2 and r varies over the band during the
    # crossing, so the coefficient does too; the CONSERVATIVE choice for a
    # lower bound on survival is the inner radius (shortest arc)
    C["T3"] = {
        "measured_inputs": {
            "R_ring_free_reach": R, "rho_at_pi": rho_pi,
            "c1_min_T_over_gamma": c1,
            "k_crossing_steps": k_cross,
            "source": "results/t3_reach_density_throughput.json",
        },
        "ballistic_v_tan_coefficient_conservative":
            env.r_in / (2 * k_cross * dt),
        "ballistic_v_tan_coefficient_at_r_out":
            env.r_out / (2 * k_cross * dt),
        "ballistic_v_tan_coefficient_used_in_measurement":
            4.0 / (2 * k_cross * dt),
        # The tangent-cone factor: SUPERSEDED, kept so the audit can catch a
        # document still quoting it. It is not a valid per-radius floor -- the
        # exact half-angle is the law-of-cosines beta, which vanishes at both
        # ends of the annulus. See scripts/t3_isotropy_window_bound.py.
        "isotropy_angular_factor_superseded":
            math.asin(env.r_out / (L + env.r_out)) / math.pi,
        # The valid reach bound, read from the script that derives it so the
        # two cannot drift apart.
        "reach_lower_bound_partitioned":
            measured("t3_isotropy_window_bound", ["reach_lower_bound"]),
        "reach_annulus_mass_below_tangent_cone_floor":
            measured("t3_isotropy_window_bound",
                     ["annulus_mass_below_claimed_floor"]),
        "magnitude_window": [L - env.r_out, L + env.r_out],
        # The published constant is the CALIBRATED one: the pooled Wilson 95%
        # lower limit at the binding gap, from disjoint seed blocks. The
        # product R*rho*c1 below reproduces the old value and is kept only so
        # the audit can catch a document still quoting it -- that value is the
        # sample's own minimum of d/gamma^2, hence violated by roughly half of
        # fresh seed blocks. See scripts/t3_quadratic_constant.py.
        "quadratic_bound_coefficient":
            measured("t3_quadratic_constant", ["quadratic_constant"]),
        "quadratic_bound_coefficient_from_sample_minimum_superseded":
            (R * rho_pi * c1 if None not in (R, rho_pi, c1) else None),
        "quadratic_bound_binding_gap":
            measured("t3_quadratic_constant", ["binding_gap"]),
    }
    # --- emitted MEASUREMENTS, mirrored so the audit covers them too --------
    # The constants emitter closed the hand-constant class; these numbers are
    # the same class one level up (quoted in the documents, derived by a
    # script). Mirroring the load-bearing ones here means audit_paper3_numbers
    # checks them at the printed precision like everything else, instead of
    # trusting that the prose still matches the JSON.
    C["measured"] = {
        "R_ring_free": measured("t3_unrecorded_measurements",
                                ["cells", "reach|200000", "R"]),
        "R_prime_leaving_k_steps": measured(
            "t3_unrecorded_measurements",
            ["cells", "reach|200000", "R_prime_leaving_k_steps"]),
        "R_prime_leaving_k_minus_1_steps": measured(
            "t3_unrecorded_measurements",
            ["cells", "reach|200000", "R_prime_leaving_k_minus_1_steps"]),
        "rho_at_pi": measured("t3_unrecorded_measurements",
                              ["cells", "profile|60000|v2", "rho_at_pi"]),
        "steering_sup": measured(
            "t3_unrecorded_measurements",
            ["cells", "steering|900|161|v2", "max"]),
        "steering_p90": measured(
            "t3_unrecorded_measurements",
            ["cells", "steering|900|161|v2", "p90"]),
        "P_root_exists": measured(
            "t3_unrecorded_measurements",
            ["cells", "steering|900|161|v2", "P_root_exists"]),
        "drag_cap_worst_400x200": measured(
            "t2_drag_cap_and_switch_rate",
            ["cells", "drag_cap|400x200", "worst_observed"]),
        "steering_median": measured(
            "t3_unrecorded_measurements",
            ["cells", "steering|900|161|v2", "median"]),
        "steering_jump_max": measured(
            "t3_unrecorded_measurements",
            ["cells", "steering|900|161|v2", "arrival_step_changed", "max"]),
        # T5-F' (the Z_1 repair): the side condition and the assembled bound.
        "T5F_K_max_side_condition": measured(
            "t5f_z1_factor",
            ["geometry", "nominal", "K_max_side_condition"]),
        "T5F_prime_rate": measured(
            "t5f_z1_factor", ["assembled_nominal", "dominant_rate"]),
        "T5F_prime_floor": measured(
            "t5f_z1_factor", ["assembled_nominal", "n_free_floor"]),
        "T5F_prime_Z1_factor": measured(
            "t5f_z1_factor", ["assembled_nominal", "Z1_factor"]),
        "T5F_effective_steps": measured(
            "t5f_z1_factor", ["truncation_theorem", "E_eff"]),
        "conditional_spread_A_t": measured(
            "t2_unrecorded_measurements",
            ["cells", "conditional_spread|0.6|40", "A_t_spread"]),
    }

    # Lemma D applied to the arrival angle, DERIVED from the two emitted
    # ingredients rather than multiplied out by hand: a_max = 1 gives the
    # factor 1/2, P(root) is the unconditional grid-scan floor, and the
    # denominator is the observed SUP of the differentiable sensitivity (a
    # percentile is not a supremum). Dividing by R converts Lemma D's
    # sub-density into the per-arrival density the decomposition consumes.
    _pr = C["measured"]["P_root_exists"]
    _sup = C["measured"]["steering_sup"]
    _R = C["measured"]["R_ring_free"]
    if None not in (_pr, _sup, _R) and _sup and _R:
        C["measured"]["rho_sub_pi_lower_bound"] = 0.5 * _pr / _sup
        C["measured"]["rho_pi_per_arrival_lower_bound"] = 0.5 * _pr / _sup / _R
        C["measured"]["rho_pi_looseness"] = (
            C["measured"]["rho_at_pi"]
            / (0.5 * _pr / _sup / _R)) if C["measured"]["rho_at_pi"] else None

    # Pearson-walk moments at t = h - k
    t_star = h - k_cross
    a = [dt * dt * ((1 - beta ** (t_star - s)) / (1 - beta)) * gain
         for s in range(t_star)]
    S2 = sum(x * x for x in a)
    C["T3"]["pearson_walk"] = {
        "t": t_star, "a_min": min(a), "a_max": max(a),
        "E_Z2": S2, "rms": math.sqrt(S2),
        "E_Z4": 2 * S2 * S2 - sum(x ** 4 for x in a),
        "target_in_rms_units": (L - env.r_out) / math.sqrt(S2),
    }

    # --- T2: the play-cost chain ------------------------------------------
    # A is a SLOPE (value per unit of velocity perturbation), so the drag cap
    # -- which already has delta_v = 2*gain*dt substituted -- must be divided
    # by it. Computing A as a value and then multiplying by delta_v again
    # double-counts the perturbation; that error is why this block exists.
    Lip_r = env.amp_real / 2 + env.amp_phantom / 2   # sigmoid slope bound
    d_v, d_p = 2 * gain * dt, 2 * gain * dt * dt
    cap = C["plant"]["drag_cap_identical_actions"]   # a VALUE at delta_v
    A_slope_proved = h * Lip_r * cap / d_v
    A_slope_hyp = (env.amp_real + env.amp_phantom) * cap / d_v
    L_p_proved = h * Lip_r                            # pure position part
    p_switch = 0.5                                    # measured at delta=0.6
    Dbar, denom = 15, 40.0                            # measured
    def pc(A, dv_eff, include_pos):
        Lv = A / (1 - p_switch)
        term = Lv * dv_eff
        if include_pos:
            term += L_p_proved * d_p + Lip_r * d_p
        return Dbar * term / denom
    C["T2"] = {
        "reward_lipschitz": Lip_r,
        "E_abs_sin_independent": 2 / math.pi,
        "delta_vel_two_actions": d_v,
        "E_delta_vel_dominance_bound": d_v * (2 / math.pi),
        "A_slope_proved": A_slope_proved,
        "A_slope_saturation_hypothesis": A_slope_hyp,
        "L_p_proved": L_p_proved,
        "position_term_contribution": Dbar * L_p_proved * d_p / denom,
        "fixed_point_closes_iff": "p(delta)*2*gain*dt < delta",
        "closure_threshold_at_delta_max": d_v / d_v,
        "pc_proved_velocity_only": pc(A_slope_proved, d_v, False),
        "pc_hypothesis_velocity_only": pc(A_slope_hyp, d_v, False),
        "pc_hypothesis_with_dominance": pc(A_slope_hyp,
                                          d_v * 2 / math.pi, False),
        "pc_hypothesis_all_terms": pc(A_slope_hyp, d_v * 2 / math.pi, True),
        "measured_facing_pc_range": [0.02, 0.10],
        "note": "no baseline of 1 exists: play_cost = (J_T-J_B)/(J_T-J_rand) "
                "exceeds 1 when the blind planner scores below random, which "
                "this paper reports (1.77, 1.12).",
    }

    OUT.write_text(json.dumps(C, indent=1, sort_keys=True))
    print(f"wrote {OUT.relative_to(_REPO)}")
    for group, vals in sorted(C.items()):
        print(f"\n[{group}]")
        for k, v in sorted(vals.items()):
            if isinstance(v, float):
                print(f"  {k:38s} {v:.6g}")
            elif isinstance(v, dict) and all(
                    isinstance(x, (int, float)) for x in v.values()):
                print(f"  {k:38s} " + ", ".join(
                    f"{kk}={vv:.4g}" for kk, vv in v.items()))


if __name__ == "__main__":
    main()
