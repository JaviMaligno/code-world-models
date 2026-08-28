"""T5, the last ingredient: a Rademacher sum is not more concentrated
near zero than its Gaussian counterpart (docs/paper3/THEORY.md, Lemma I).

Proposition T5-T needs E[e^{-lam Z^2}] <= (1 + 2 lam sigma^2)^{-1/2} plus
an error, for Z = sum_s c_s eps_s. That inequality is FALSE in general
(equal weights put an atom at 0, so for large lam the left side tends to
P(Z=0) > 0 while the right side tends to 0). Lemma I gives the correct
universally valid form via the characteristic function:

  E[e^{-lam Z^2}] = E_g[ prod_s cos(sqrt(2 lam) g c_s) ]      (g ~ N(0,1))

and |cos x| <= exp(-x^2/2) for |x| <= x0 = 1.7780, so splitting on
|g| <= G := x0 / (sqrt(2 lam) c_max):

  E[e^{-lam Z^2}] <= (1 + 2 lam sigma^2)^{-1/2} + 2 Phibar(G),
  G = x0 * rho / sqrt(u),  rho := sigma / c_max,  u := 2 lam sigma^2.

No weight-profile hypothesis is needed for VALIDITY; the profile only
controls tightness, through the single observable rho.

Checks:
  1. x0 is exactly the crossover of |cos x| and exp(-x^2/2);
  2. Lemma I holds on weight profiles from maximally concentrated to
     uniform (exact enumeration where feasible, else Monte Carlo);
  3. the instrument's own conditional weight profile: the distribution
     of rho, and the resulting error term and per-dimension rate.

Run: PYTHONPATH=src python scripts/t5_rademacher_ingredient.py  (~3 min)
"""
import itertools
import json
import math
import os
import pathlib
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import thrust_vector_nd                # noqa: E402

X0 = 1.7780              # largest x with |cos x| <= exp(-x^2/2)
U_STAR = 4.76            # the scheme's optimum u = 2 lam sigma^2 (n -> inf)


def phibar(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def lemma_i_bound(cs, lam):
    s2 = sum(c * c for c in cs)
    cmax = max(abs(c) for c in cs)
    main = (1 + 2 * lam * s2) ** -0.5
    err = 2 * phibar(X0 / (math.sqrt(2 * lam) * cmax))
    return main + err, main, err, math.sqrt(s2) / cmax


def exact_expectation(cs, lam):
    tot = 0.0
    for signs in itertools.product((1, -1), repeat=len(cs)):
        z = sum(s * c for s, c in zip(signs, cs))
        tot += math.exp(-lam * z * z)
    return tot / 2 ** len(cs)


def mc_expectation(cs, lam, n=200_000, seed=0):
    rng = random.Random(seed)
    tot = 0.0
    for _ in range(n):
        z = sum(c if rng.random() < 0.5 else -c for c in cs)
        tot += math.exp(-lam * z * z)
    return tot / n


def main():
    out = {"x0": X0, "u_star": U_STAR}

    print("1. the pointwise inequality |cos x| <= exp(-x^2/2)")
    step = 1e-4
    fail = next(x for x in (i * step for i in range(1, 30001))
                if abs(math.cos(x)) > math.exp(-x * x / 2))
    assert abs(fail - step - X0) < 2 * step, (fail, X0)
    print(f"   holds on [0, {fail - step:.4f}]; X0 = {X0} used")

    print("\n2. Lemma I across weight profiles")
    rng = random.Random(3)
    profiles = {
        "single weight": [1.0],
        "one dominant": [1.0] + [0.05] * 9,
        "two equal": [1.0, 1.0],
        "geometric decay": [0.7 ** k for k in range(12)],
        "10 equal": [1.0] * 10,
        "20 equal": [1.0] * 20,
        "instrument-like": [(1 - 0.97 ** (80 - s)) / 0.03
                            * abs(rng.uniform(-1, 1)) for s in range(80)],
    }
    rows = []
    for name, cs in profiles.items():
        s2 = sum(c * c for c in cs)
        lam = U_STAR / (2 * s2)
        e = (exact_expectation(cs, lam) if len(cs) <= 20
             else mc_expectation(cs, lam))
        b, main, err, rho = lemma_i_bound(cs, lam)
        assert e <= b, (name, e, b)
        rows.append({"profile": name, "h": len(cs), "rho": rho,
                     "E": e, "bound": b, "main": main, "err": err})
        print(f"   {name:16s} h={len(cs):3d} rho={rho:5.2f}  E={e:.4f} <= "
              f"bound {b:.4f} (main {main:.4f} + err {err:.4f})")
    out["profiles"] = rows

    print("\n3. the instrument's own conditional weight profile")
    dt, drag, gain, a_max, h = 0.1, 0.3, 3.0, 1.0, 80
    beta = 1 - drag * dt
    w = [(1 - beta ** (h - s)) / (1 - beta) for s in range(h)]
    inst = []
    for n in (3, 5, 8, 12, 20):
        rng = random.Random(7)
        rhos = []
        for _ in range(400):
            cols = [[0.0] * h for _ in range(n)]
            for s in range(h):
                a = tuple(rng.uniform(-1, 1) for _ in range(n))
                t = thrust_vector_nd(a, gain, a_max)
                for i in range(n):
                    cols[i][s] = dt * dt * w[s] * abs(t[i])
            for col in cols:
                cm = max(col)
                if cm > 0:
                    rhos.append(math.sqrt(sum(x * x for x in col)) / cm)
        rhos.sort()
        med, p5, mn = (rhos[len(rhos) // 2], rhos[len(rhos) // 20], rhos[0])

        def q_of(rho):
            return ((1 + U_STAR) ** -0.5
                    + 2 * phibar(X0 * rho / math.sqrt(U_STAR)))
        inst.append({"n": n, "samples": len(rhos), "rho_median": med,
                     "rho_p5": p5, "rho_min": mn, "q_at_median": q_of(med),
                     "q_at_min": q_of(mn)})
        print(f"   n={n:3d}: rho median {med:.2f}, 5th pct {p5:.2f}, "
              f"min {mn:.2f}  ->  per-dim rate {q_of(med):.4f} "
              f"(worst sample {q_of(mn):.4f})")
    out["instrument"] = inst
    sharp = (1 + U_STAR) ** -0.5
    print(f"\n   sharp (Gaussian) value {sharp:.4f}; the instrument's "
          f"profile costs at most a few times 1e-3.")
    assert all(r["q_at_median"] < 1.02 * sharp for r in inst)
    out["sharp_rate"] = sharp
    p = pathlib.Path("results/t5_rademacher_ingredient.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
