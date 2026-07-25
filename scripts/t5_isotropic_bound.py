"""T5: the exponential bound, PROVED for the isotropic action interface
(docs/paper3/THEORY.md, Theorem T5-I).

The cube-uniform thrust defeats every symmetry argument (Lemma E is
sharp for exchangeable laws, and the cone event turns out to be a
small-ball event for the perpendicular mass, which symmetry cannot
control). But if the thrust DIRECTION is uniform on the sphere, the
displacement Z_t is a sum of independent spherically symmetric vectors,
hence spherically symmetric itself: Z_t/||Z_t|| is EXACTLY uniform, the
cone probability is exactly a spherical cap, and the exponential bound
follows with no probabilistic input at all.

Three checks:
  1. the cap bound  P(U_1 >= kappa) <= (1/2)(1-kappa^2)^((n-2)/2)
     against the exact cap integral (the proof's key inequality);
  2. the isotropic-interface simulation against Theorem T5-I's
     r(n) <= (h/2)(r_out/L)^(n-2);
  3. isotropic vs cube per-dimension decay — the transfer question that
     remains open.

Run: PYTHONPATH=src python scripts/t5_isotropic_bound.py   (~4 min)
"""
import json
import math
import os
import pathlib
import random
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import ShellFieldN                     # noqa: E402

ROLLOUTS = 6000
t0 = time.time()


def cap_exact(n, kappa, steps=200_000):
    """P(U_1 >= kappa) for U uniform on S^{n-1}, by direct quadrature of
    the marginal density c_n (1-u^2)^((n-3)/2)."""
    def integ(a, b):
        h = (b - a) / steps
        s = 0.0
        for i in range(steps + 1):
            u = a + i * h
            v = 1.0 - u * u
            t = 0.0 if v <= 0.0 else math.exp(((n - 3) / 2) * math.log(v))
            s += (0.5 if i in (0, steps) else 1.0) * t
        return s * h
    return integ(kappa, 1.0) / integ(-1.0, 1.0)


def isotropic_cone_rate(n, n_roll, seed0=0):
    """Cone-event rate under the ISOTROPIC action interface: same plant and
    same thrust-norm law, but the direction is uniform on S^{n-1}."""
    env = ShellFieldN(n=n)
    c, h = env.center(), env.h_episode
    dt, gain, drag = env.dt, env.gain, env.drag
    hits = 0
    for i in range(n_roll):
        rng = random.Random(seed0 + 90_000 + i)
        s = env.initial_state(rng)
        x0 = list(s[:n])
        d = [c[k] - x0[k] for k in range(n)]
        L = math.sqrt(sum(v * v for v in d))
        kappa = math.sqrt(max(0.0, L * L - env.r_out ** 2)) / L
        e = [v / L for v in d]
        pos, vel, hit = list(x0), [0.0] * n, False
        for _ in range(h):
            a = [rng.uniform(-1, 1) for _ in range(n)]
            mag = gain * min(1.0, math.sqrt(sum(v * v for v in a)))
            g = [rng.gauss(0, 1) for _ in range(n)]
            ng = math.sqrt(sum(v * v for v in g)) or 1.0
            thrust = [mag * x / ng for x in g]
            vel = [v + (t - drag * v) * dt for v, t in zip(vel, thrust)]
            pos = [p + v * dt for p, v in zip(pos, vel)]
            z = [pos[k] - x0[k] for k in range(n)]
            nz = math.sqrt(sum(v * v for v in z))
            if nz > 0.0 and sum(z[k] * e[k] for k in range(n)) >= kappa * nz:
                hit = True
        hits += hit
    return hits / n_roll


def main():
    env = ShellFieldN(n=3)
    L, r_out, h = 12.0, env.r_out, env.h_episode
    k2 = (L * L - r_out ** 2) / (L * L)
    kappa = math.sqrt(k2)
    out = {"kappa": kappa, "one_minus_k2": 1 - k2,
           "sin_theta": math.sqrt(1 - k2), "h": h}

    print("1. cap bound vs exact cap measure")
    caps = []
    for n in (3, 4, 5, 6, 8, 10, 14, 20, 30):
        ex = cap_exact(n, kappa)
        bd = 0.5 * (1 - k2) ** ((n - 2) / 2)
        assert ex <= bd + 1e-15, (n, ex, bd)
        caps.append({"n": n, "exact": ex, "bound": bd, "ratio": bd / ex})
        print(f"   n={n:3d} exact {ex:.3e}  bound {bd:.3e}  "
              f"({bd / ex:.1f}x)")
    out["cap"] = caps

    print("\n2. isotropic interface vs Theorem T5-I")
    rows, prev = [], None
    for n in (3, 4, 5, 6, 7, 8):
        p = isotropic_cone_rate(n, ROLLOUTS)
        bound = min(1.0, (h / 2) * (1 - k2) ** ((n - 2) / 2))
        assert p <= bound, (n, p, bound)
        ratio = (prev / p) if (prev and p > 0) else None
        rows.append({"n": n, "iso_cone_rate": p, "bound_T5I": bound,
                     "decay_vs_prev": (1 / ratio) if ratio else None})
        print(f"   n={n}: rate {p:.5f} <= bound {bound:.4f}"
              + (f"   per-dim decay {1 / ratio:.3f}" if ratio else ""))
        prev = p
    out["isotropic"] = rows
    decays = [r["decay_vs_prev"] for r in rows if r["decay_vs_prev"]]
    mean_decay = sum(decays) / len(decays)
    print(f"   mean per-dim decay {mean_decay:.3f} vs predicted "
          f"sin(theta) = {math.sqrt(1 - k2):.4f}")
    out["iso_mean_decay"] = mean_decay

    print("\n3. the open transfer question (cube vs isotropic)")
    cube_path = "results/t5_cone_bound.json"
    if os.path.exists(cube_path):
        cube = json.load(open(cube_path))
        fit = cube.get("fit", {})
        cube_decay = math.exp(fit.get("loglin_slope", 0.0))
        print(f"   cube interface measured per-dim decay {cube_decay:.3f}; "
              f"isotropic {mean_decay:.3f}; predicted "
              f"{math.sqrt(1 - k2):.4f}")
        out["cube_decay"] = cube_decay
    p = pathlib.Path("results/t5_isotropic_bound.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
