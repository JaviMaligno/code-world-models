"""T5 interface transfer: the cube-uniform action reduced to two standard
ingredients (docs/paper3/THEORY.md, Lemma H and Proposition T5-T).

Theorem T5-I proves the exponential rate for a spherically symmetric
thrust. The instrument's thrust is cube-uniform and norm-capped, whose
symmetry group is finite — so the isotropic argument does not apply. The
transfer rests on a structural fact instead:

  LEMMA H. The norm cap max(1, ||a||) depends only on the ABSOLUTE
  values of a, and the coordinates of a are independent and symmetric.
  So conditional on all absolute values, the signs are i.i.d. Rademacher
  and T_{s,i} = eps_{s,i} b_{s,i} with b deterministic. Hence the
  displacement coordinates Z_i = dt^2 sum_s w_s eps_{s,i} b_{s,i} are
  INDEPENDENT across i, each a Rademacher sum.

With independence, a single Chernoff bound with matched exponent
replaces the (impossible) symmetry argument:

  P(cone | B) <= E[e^{lam g^2 Z_1^2}] * prod_{i>=2} E[e^{-lam Z_i^2}],
  g^2 = (1-kappa^2)/kappa^2.

Checks performed here:
  1. Lemma H EXACTLY (not statistically): flipping one sign in column j
     changes coordinate j only, bitwise, and the norm cap is invariant.
  2. The scheme is SHARP: in the Gaussian regime its optimum over lam is
     sqrt(e*n/(1+g^2)) * (1-kappa^2)^((n-1)/2) — the spherical-cap rate
     with only a polynomial loss. Closed form checked against numerical
     minimisation and against the asymptotic constant.

Run: PYTHONPATH=src python scripts/t5_interface_transfer.py   (~10 s)
"""
import json
import math
import os
import pathlib
import random
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import thrust_vector_nd                # noqa: E402

N, H, GAIN, A_MAX, DT, DRAG = 6, 40, 3.0, 1.0, 0.1, 0.3


def lemma_h_exact_check(trials=300, seed=11):
    """Z_i depends only on the i-th column of signs — checked bitwise."""
    rng = random.Random(seed)
    absa = [[abs(rng.uniform(-1, 1)) for _ in range(N)] for _ in range(H)]

    def disp(signs):
        vel, pos = [0.0] * N, [0.0] * N
        for s in range(H):
            a = tuple(sg * v for sg, v in zip(signs[s], absa[s]))
            t = thrust_vector_nd(a, GAIN, A_MAX)
            vel = [v + (x - DRAG * v) * DT for v, x in zip(vel, t)]
            pos = [p + v * DT for p, v in zip(pos, vel)]
        return pos

    base = [[rng.choice((1, -1)) for _ in range(N)] for _ in range(H)]
    z0 = disp(base)
    viol = checked = 0
    for _ in range(trials):
        s, j = rng.randrange(H), rng.randrange(N)
        flip = [row[:] for row in base]
        flip[s][j] *= -1
        z1 = disp(flip)
        for i in range(N):
            if i == j:
                continue
            checked += 1
            viol += (z1[i] != z0[i])          # bitwise
    # the cap itself must be sign-invariant (that is why Lemma H works)
    a = [rng.uniform(-1, 1) for _ in range(N)]
    m1 = max(1.0, math.sqrt(sum(x * x for x in a)))
    m2 = max(1.0, math.sqrt(sum(x * x for x in
                                (rng.choice((1, -1)) * x for x in a))))
    assert viol == 0 and abs(m1 - m2) < 1e-15
    return {"coordinate_checks": checked, "violations": viol,
            "cap_sign_invariant": True}


def scheme_rate(k2):
    """The Chernoff scheme's optimum in the Gaussian regime, vs the cap."""
    g2 = (1 - k2) / k2

    def f(u, n):
        return (1 - g2 * u) ** -0.5 * (1 + u) ** (-(n - 1) / 2)

    rows = []
    for n in (3, 5, 8, 12, 20, 40):
        ustar = ((n - 1) - g2) / (n * g2)
        grid = [i * ustar / 400 for i in range(1, 800) if i * ustar / 400
                < 1 / g2]
        num = min((f(u, n), u) for u in grid)
        cap = (1 - k2) ** ((n - 1) / 2)
        pred = math.sqrt(math.e * n / (1 + g2))
        assert abs(num[1] - ustar) < 0.02 * ustar, (n, num[1], ustar)
        rows.append({"n": n, "u_star": ustar, "scheme": f(ustar, n),
                     "cap_rate": cap, "ratio": f(ustar, n) / cap,
                     "predicted_ratio": pred})
        print(f"  n={n:3d}: scheme {f(ustar, n):.4e}  cap {cap:.4e}  "
              f"ratio {f(ustar, n) / cap:7.3f}  predicted "
              f"sqrt(e n/(1+g^2)) = {pred:7.3f}")
    # the ratio must be polynomial (sqrt n), never exponential
    for r in rows[2:]:
        assert abs(r["ratio"] / r["predicted_ratio"] - 1) < 0.05, r
    return {"gamma2": g2, "rows": rows}


def main():
    print("1. Lemma H, exact (bitwise) check")
    h = lemma_h_exact_check()
    print(f"   flipping one sign changes ONLY its own coordinate: "
          f"{h['violations']} violations in {h['coordinate_checks']} checks")

    print("\n2. the Chernoff scheme's rate vs the spherical cap")
    k2 = (12.0 ** 2 - 5.0 ** 2) / 12.0 ** 2
    s = scheme_rate(k2)
    print("\n   the scheme reproduces the cap rate exactly, losing only a "
          "sqrt(n) factor: the transfer is SHARP given its two ingredients.")
    p = pathlib.Path("results/t5_interface_transfer.json")
    p.write_text(json.dumps({"lemma_h": h, "scheme": s}, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
