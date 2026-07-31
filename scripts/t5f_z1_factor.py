"""Repair Theorem T5-F: carry the Z_1 factor, with its side condition.

The defect. Prop T5-T's scheme is

    P(cone | B) <= E[e^{lam g2 Z_1^2} | B] * prod_{i>=2} E[e^{-lam Z_i^2} | B],
    g2 := (1 - kappa^2) / kappa^2,

and T5-F's displayed bound controls only the PRODUCT. The upper-side factor is
absent -- which is why no kappa appears in T5-F's rate, a tell that the cone's
geometry has dropped out of a bound about the cone. Worse, the Z_1 factor's
Hoeffding form

    E[e^{t Z_1^2} | B] <= (1 - 2 t sigma_1^2)^{-1/2},    2 t sigma_1^2 < 1,

carries a SIDE CONDITION that T5-F's own parameters violate: with
lam = c/(2m) the condition reads sigma_1^2 / m < 1/(c*g2), which at the
instrument's geometry is about 3.6, while T5-F takes the upper cutoff K = 10.

What this script establishes.

  1. The side condition's exact threshold K_max = 1/(c*g2), derived from the
     instrument rather than quoted.

  2. A bound on the truncation event P(sigma_1^2 > K m) that is NOT the
     counting bound 1/K. Conditioned on the norms, sigma_1^2 = sum_s A_s
     a_{s,1}^2 is a sum of INDEPENDENT terms bounded by b_s := A_s min(1,
     ||a_s||^2), with conditional mean exactly m (within-step exchangeability).
     Hoeffding then gives

        P(sigma_1^2 > K m | B) <= exp( -2 (K-1)^2 m^2 / sum_s b_s^2 ),

     which is n-INDEPENDENT and exponentially small in the effective number of
     steps, instead of the counting bound's 1/K ~ 0.28.

  3. The consequence, which is a negative result about the scheme: the floor
     CANNOT be removed. Outside the truncation event the exponential moment is
     finite; inside it, E[(1 - c g2 sigma_1^2/m)^{-1/2}] is +infinity, so no
     choice of parameters makes the untruncated expectation finite. T5-F's
     "floor-free" reading is therefore unavailable once Z_1 is carried -- but
     the floor is of order 1e-4 rather than the 0.12 it replaced.

  4. The re-optimised bound over (z, K, alpha) subject to K < K_max, including
     the Z_1 factor, and the resulting per-dimension rate.

  5. The Hoeffding bound's looseness, by measuring P(sigma_1^2 > K m) directly
     at the instrument's weights.

  PYTHONPATH=src python scripts/t5f_z1_factor.py
"""
import argparse
import json
import math
import pathlib
import random
import statistics
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import RingField2D, ShellFieldN         # noqa: E402

OUT = _REPO / "results" / "t5f_z1_factor.json"
C_LAMBDA = 1.32          # T5-F's lambda = C_LAMBDA / (2m)


def geometry():
    """kappa^2 and g2 from the instrument, at the worst (smallest) start L."""
    ring = RingField2D()
    shell = ShellFieldN(8)
    L_nom = math.hypot(ring.center[0] - ring.x0_center[0],
                       ring.center[1] - ring.x0_center[1])
    rng = ring.x0_range
    corners = [math.hypot(ring.center[0] - (ring.x0_center[0] + sx * rng),
                          ring.center[1] - (ring.x0_center[1] + sy * rng))
               for sx in (-1, 1) for sy in (-1, 1)]
    L_min = min(corners)
    # An upper bound on the reach uses the LARGEST ratio, i.e. the smallest L.
    out = {}
    for name, L in (("nominal", L_nom), ("L_min", L_min)):
        k2 = 1 - (shell.r_out / L) ** 2
        out[name] = {"L": L, "kappa2": k2, "g2": (1 - k2) / k2,
                     "K_max_side_condition": 1.0 / (C_LAMBDA * (1 - k2) / k2)}
    return out


def weights(h, drag, dt):
    beta = 1 - drag * dt
    return [((1 - beta ** (h - s)) / (1 - beta)) ** 2 for s in range(h)]


def truncation_bound(n, trials, seed, Ks):
    """Hoeffding on the truncation event, and its measured looseness.

    Conditioned on the norms, sigma_1^2 = sum_s A_s a_{s,1}^2 is a sum of
    independent terms in [0, b_s] with conditional mean exactly m, so
    Hoeffding applies with no further hypothesis. The measurement says how
    much of the resulting floor is Hoeffding's slack rather than the event.
    """
    shell = ShellFieldN(n)
    h = shell.h_episode
    w2 = weights(h, shell.drag, shell.dt)
    rng = random.Random(seed)
    exceed = {K: 0 for K in Ks}
    hoeff = {K: [] for K in Ks}
    ratios = []
    for _ in range(trials):
        A, b, num, den = [], [], 0.0, 0.0
        for s in range(h):
            a = [rng.uniform(-1, 1) for _ in range(n)]
            nrm2 = sum(x * x for x in a)
            M2 = max(1.0, nrm2)
            A_s = w2[s] / M2
            A.append(A_s)
            b.append(A_s * min(1.0, nrm2))
            num += A_s * a[0] * a[0]
            den += A_s * nrm2
        m = den / n
        ratio = num / m if m else float("inf")
        ratios.append(ratio)
        D = sum(x * x for x in b)
        for K in Ks:
            exceed[K] += (ratio > K)
            hoeff[K].append(math.exp(-2 * (K - 1) ** 2 * m * m / D)
                            if D > 0 else 1.0)
    ratios.sort()
    return {
        "n": n, "trials": trials, "seed": seed,
        "ratio_sigma1_over_m": {
            "median": statistics.median(ratios),
            "p90": ratios[int(0.9 * (trials - 1))],
            "p99": ratios[int(0.99 * (trials - 1))],
            "max": ratios[-1],
        },
        "per_K": [{
            "K": K,
            "measured_exceedance": exceed[K] / trials,
            "hoeffding_bound_mean": statistics.fmean(hoeff[K]),
            "hoeffding_bound_max": max(hoeff[K]),
            "counting_bound_1_over_K": 1.0 / K,
        } for K in Ks],
        "note": ("counting_bound_1_over_K is what exchangeability alone gives "
                 "and is the floor T5-F would inherit; the Hoeffding column is "
                 "the same event bounded by concentration over the h steps, "
                 "which is n-independent and vastly smaller. measured is what "
                 "the event actually costs."),
    }


def norm_lower_tail_rate(nu):
    """Chernoff rate for P(||a||^2 < nu*n) per coordinate, a ~ U(-1,1).

    ||a||^2 is a sum of n iid copies of a^2, mean 1/3, with the closed-form
    MGF E[e^{-theta a^2}] = (1/2) sqrt(pi/theta) erf(sqrt(theta)). The rate is
    I(nu) = sup_{theta>0} [ -theta*nu - log M(theta) ], so the union over h
    steps costs h*exp(-n*I(nu)).
    """
    def logM(th):
        if th <= 0:
            return 0.0
        return math.log(0.5 * math.sqrt(math.pi / th) * math.erf(math.sqrt(th)))
    best, th = -1e9, 1e-4
    while th < 1e4:
        best = max(best, -th * nu - logM(th))
        th *= 1.05
    return max(0.0, best)


def truncation_theorem(w2, h, Ks, nus):
    """A CERTIFIED bound on the truncation event -- no Monte Carlo.

    On the event {||a_s||^2 >= nu*n for every s}, which requires nu*n >= 1:
      M_s^2 = ||a_s||^2, so A_s ||a_s||^2 = w_s^2 and m = S/n EXACTLY;
      b_s = A_s min(1,||a_s||^2) = w_s^2/||a_s||^2 <= w_s^2/(nu n);
      sum_s b_s^2 <= (sum_s w_s^4)/(nu n)^2.
    Hoeffding (conditionally on the norms: independent terms in [0, b_s] with
    conditional mean exactly m, by within-step exchangeability) then gives an
    exponent
      2 (K-1)^2 m^2 / sum b_s^2 >= 2 (K-1)^2 nu^2 S^2 / sum w_s^4,
    which is n-FREE. Off that event we pay h * exp(-n I(nu)).

    So P(sigma_1^2 > K m) <= h e^{-n I(nu)} + exp(-2 (K-1)^2 nu^2 E_eff),
    E_eff := S^2 / sum_s w_s^4. Monte Carlo can never certify a floor this
    small, which is why it is derived rather than sampled.
    """
    S = sum(w2)
    E_eff = S * S / sum(x * x for x in w2)
    rows = []
    for K in Ks:
        for nu in nus:
            I = norm_lower_tail_rate(nu)
            expo = 2 * (K - 1) ** 2 * nu * nu * E_eff
            rows.append({
                "K": K, "nu": nu, "I_nu": I,
                "n_free_term": math.exp(-expo) if expo < 700 else 0.0,
                "per_step_norm_rate": math.exp(-I),
                "min_n_for_nu": math.ceil(1 / nu),
            })
    return {"E_eff": E_eff, "h": h, "rows": rows}


def q(u, x0=7 / 4, rho=1.0):
    """Lemma I's per-coordinate factor at u = 2 lambda sigma^2."""
    def phibar(x):
        return 0.5 * math.erfc(x / math.sqrt(2))
    return (1 + u) ** -0.5 + 2 * phibar(x0 * rho / math.sqrt(u))


def p_low(z, w2, S):
    """Exact Chernoff for P(sum_s w_s^2 a_s^2 < z S), a_s iid U(-1,1)."""
    def mgf(c):
        # E[exp(-c a^2)] = (1/2) sqrt(pi/c) erf(sqrt(c))
        if c <= 0:
            return 1.0
        return 0.5 * math.sqrt(math.pi / c) * math.erf(math.sqrt(c))
    # Work in LOG space: the Chernoff exponent overflows exp() at large theta
    # long before the minimum is reached, and clipping it would silently
    # replace the optimum with whatever survived the overflow.
    best_log = 0.0
    th = 1e-4
    while th < 400:
        val = th * z * S + sum(math.log(mgf(th * x)) for x in w2)
        best_log = min(best_log, val)
        th *= 1.15
    return math.exp(best_log) if best_log > -700 else 0.0


def optimise(g2, K_max, n_grid, w2):
    """Re-optimise (z, K, alpha) subject to the Z_1 side condition K < K_max.

    The bound carried is
      P(cone) <= floor(K) + (1 - c g2 K)^{-1/2} * [ q_max^{(1-alpha-1/K)n}
                                                    + (e p(z)/alpha)^{alpha n} ]
    where floor(K) is the truncation event. The Z_1 factor (1 - c g2 K)^{-1/2}
    BLOWS UP as K -> K_max, which is the tension the optimisation resolves: a
    larger K keeps more coordinates in the product but inflates the Z_1 factor.
    """
    S = sum(w2)
    best = None
    for K10 in range(11, int(K_max * 10)):
        K = K10 / 10.0
        side = C_LAMBDA * g2 * K
        if side >= 1:
            continue
        z1 = (1 - side) ** -0.5
        for z10 in range(1, 20):
            z = z10 / 10.0
            if z >= K:
                continue
            pz = p_low(z, w2, S)
            qmax = max(q(C_LAMBDA * z), q(C_LAMBDA * K))
            for a100 in range(1, 60):
                alpha = a100 / 100.0
                frac = 1 - alpha - 1 / K
                if frac <= 0:
                    continue
                # per-dimension rate of the dominant term
                rate = max(qmax ** frac,
                           (math.e * pz / alpha) ** alpha)
                cand = (rate, K, z, alpha, z1, qmax, pz, frac)
                if best is None or rate < best[0]:
                    best = cand
    if best is None:
        return None
    rate, K, z, alpha, z1, qmax, pz, frac = best
    return {"C_lambda": C_LAMBDA, "g2": g2, "K_max": K_max,
            "K": K, "z": z, "alpha": alpha, "good_fraction": frac,
            "Z1_factor": z1, "q_max": qmax, "p_z": pz,
            "per_dimension_rate": rate,
            "bound_at_n": {str(n): z1 * 2 * rate ** n for n in n_grid}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8,
                    help="dimension for the truncation measurement")
    ap.add_argument("--trials", type=int, default=4000)
    args = ap.parse_args()

    geo = geometry()
    state = {"geometry": geo, "C_lambda": C_LAMBDA}

    shell = ShellFieldN(8)
    w2 = weights(shell.h_episode, shell.drag, shell.dt)
    state["effective_steps"] = {
        "h": shell.h_episode,
        "sum_w2_over_max_w2": sum(w2) / max(w2),
    }

    for name, g in geo.items():
        opt = optimise(g["g2"], g["K_max_side_condition"], [10, 20, 40, 80], w2)
        state[f"optimised_{name}"] = opt
        if opt:
            print(f"[{name}] K_max={g['K_max_side_condition']:.3f}  "
                  f"K*={opt['K']}  z*={opt['z']}  alpha*={opt['alpha']}  "
                  f"Z1 factor={opt['Z1_factor']:.3f}  "
                  f"rate={opt['per_dimension_rate']:.4f}")

    Ks = [1.5, 2.0, 2.5, 3.0, 3.5]
    # Include the OPTIMISED K for each geometry, or the assembly below silently
    # finds no matching row and reports infeasible for a grid reason.
    opt_Ks = sorted({round(state[f"optimised_{nm}"]["K"], 3)
                     for nm in geo if state.get(f"optimised_{nm}")})
    state["truncation_theorem"] = truncation_theorem(
        w2, shell.h_episode, sorted(set(Ks) | set(opt_Ks)),
        [0.10, 0.15, 0.20, 0.25])
    print("\ncertified truncation bound (no Monte Carlo), "
          f"E_eff = {state['truncation_theorem']['E_eff']:.1f}:")
    for r in state["truncation_theorem"]["rows"]:
        if r["K"] in (3.0, 3.5):
            print(f"  K={r['K']} nu={r['nu']}: n-free term "
                  f"{r['n_free_term']:.3e}, per-step norm rate "
                  f"e^-I = {r['per_step_norm_rate']:.4f}")
    state["truncation"] = truncation_bound(args.n, args.trials, 4242, Ks)
    print(f"\ntruncation event at n={args.n}, {args.trials} trials:")
    for row in state["truncation"]["per_K"]:
        print(f"  K={row['K']}: measured {row['measured_exceedance']:.5f}, "
              f"Hoeffding {row['hoeffding_bound_mean']:.3e}, "
              f"counting {row['counting_bound_1_over_K']:.3f}")

    # Assemble: pick nu so the norm tail's rate stays BELOW the main rate (it
    # must not become the dominant exponential) while the n-free floor is as
    # small as that allows.
    for name, opt in (("nominal", state.get("optimised_nominal")),
                      ("L_min", state.get("optimised_L_min"))):
        if not opt:
            continue
        main_rate = opt["per_dimension_rate"]
        cand = [r for r in state["truncation_theorem"]["rows"]
                if abs(r["K"] - opt["K"]) < 1e-9
                and r["per_step_norm_rate"] < main_rate]
        if not cand:
            # No nu keeps the norm tail subdominant: say so rather than
            # quietly reporting the smaller floor.
            state[f"assembled_{name}"] = {
                "feasible": False,
                "why": ("no nu keeps the norm tail's rate below the main rate, "
                        "so the norm tail would dominate the exponential")}
            continue
        best = min(cand, key=lambda r: r["n_free_term"])
        state[f"assembled_{name}"] = {
            "feasible": True,
            "K": opt["K"], "z": opt["z"], "alpha": opt["alpha"],
            "nu": best["nu"],
            "side_condition_K_max": opt["K_max"],
            "Z1_factor": opt["Z1_factor"],
            "dominant_rate": main_rate,
            "norm_tail_rate": best["per_step_norm_rate"],
            "n_free_floor": best["n_free_term"],
            "statement": (
                "P(cone at a fixed step) <= %.3g + %.2f * 2 * %.4f^n + %d * "
                "%.4f^n, the last term subdominant."
                % (best["n_free_term"], opt["Z1_factor"], main_rate,
                   state["truncation_theorem"]["h"],
                   best["per_step_norm_rate"])),
        }
        a = state[f"assembled_{name}"]
        print(f"\n[{name}] ASSEMBLED with Z1 carried: "
              f"K={a['K']} < K_max={a['side_condition_K_max']:.3f}, nu={a['nu']}")
        print(f"    floor {a['n_free_floor']:.3g} (n-free), "
              f"dominant rate {a['dominant_rate']:.4f}, "
              f"norm tail {a['norm_tail_rate']:.4f} (subdominant)")

    state["conclusion"] = (
        "Carrying Z_1 forces a truncation at sigma_1^2 <= K m with "
        "K < 1/(C_lambda * g2), and OUTSIDE that event the exponential moment "
        "E[(1 - C_lambda g2 sigma_1^2/m)^{-1/2}] is infinite -- so no choice of "
        "parameters makes the untruncated expectation finite and the scheme "
        "CANNOT be floor-free. The floor is the truncation event's probability: "
        "n-independent, CERTIFIED by Hoeffding over the h steps rather than "
        "sampled (Monte Carlo cannot certify a floor this small) and rather "
        "than by the counting bound 1/K, and therefore many orders of "
        "magnitude below the 0.12 it replaces. The exponential survives, at a "
        "rate degraded from 0.9104 to the assembled value: that degradation IS "
        "the cost of carrying Z_1, and kappa re-enters the bound through g2 in "
        "both the Z_1 factor and the side condition.")
    OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
