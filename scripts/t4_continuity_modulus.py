"""T4 validation: the explicit continuity modulus for the gamma-curves
(docs/paper3/THEORY.md, "T4 - the explicit continuity modulus").

Four machine checks of the proved statements (proofs first, validation
second - the standing rule):
  1. Lemma S exactness: the one-step proposed landing lies EXACTLY on the
     circle of radius gain*dt^2 around the drift center, at angle pi*a.
  2. Lemma A: the exact circle-strip probability (arcsin formula) obeys
     bounds (i)/(ii)/(iii) over a (s, w) grid, agrees with Monte Carlo,
     and the tangency lower bound (iv) holds at s = R.
  3. Sharpness scaling: at s = R the exact P(w) fits slope 1/2 in log-log
     (per-step Hoelder-1/2 is attained, Lemma A(iv)).
  4. Theorem T4 at trajectory level: CRN rollouts measure
     P(some proposed landing in D(gamma, gamma+eps)) and
     |r_int(gamma+eps) - r_int(gamma)|; both must sit under the modulus
     h*sqrt(r_out*eps/(gain*dt^2)), and the empirical eps-scaling of the
     hit probability is reported (expected ~linear: the tangency band is
     rarely occupied, the T4' decomposition's measured counterpart).

Run: PYTHONPATH=src python scripts/t4_continuity_modulus.py   (~30 s CPU)
"""
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import RingField2D, integrate_2d

t0 = time.time()
out = {}

# ---------------------------------------------------------------- 1. Lemma S
env = RingField2D()
R_L = env.gain * env.dt * env.dt
beta = 1.0 - env.drag * env.dt
rng = random.Random(4001)
worst_rad = worst_ang = 0.0
for _ in range(2000):
    s = (rng.uniform(-20, 20), rng.uniform(-20, 20),
         rng.uniform(-12, 12), rng.uniform(-12, 12))
    a = rng.uniform(-env.a_max, env.a_max)
    x2, y2, _, _ = integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max)
    cx = s[0] + beta * s[2] * env.dt
    cy = s[1] + beta * s[3] * env.dt
    worst_rad = max(worst_rad, abs(math.hypot(x2 - cx, y2 - cy) - R_L))
    phi = math.pi * a / env.a_max
    worst_ang = max(worst_ang,
                    math.hypot(x2 - cx - R_L * math.cos(phi),
                               y2 - cy - R_L * math.sin(phi)))
assert worst_rad < 1e-12 and worst_ang < 1e-12, (worst_rad, worst_ang)
out["lemma_S"] = {"R_L": R_L, "worst_radius_err": worst_rad,
                  "worst_angle_err": worst_ang, "n": 2000}
print(f"Lemma S: landing circle exact to {max(worst_rad, worst_ang):.1e} "
      f"(R_L = {R_L})")


# ---------------------------------------------------------------- 2. Lemma A
def p_exact(s: float, R: float, w: float) -> float:
    """P(uniform-on-circle(radius R, center at distance s from the strip
    mid-line) lands in the width-w strip): the arcsin formula from the
    Lemma A proof."""
    a = max(-1.0, (-w / 2 - s) / R)
    b = min(1.0, (w / 2 - s) / R)
    if b <= a:
        return 0.0
    return (math.asin(b) - math.asin(a)) / math.pi


def p_mc(s: float, R: float, w: float, n: int, seed: int) -> float:
    r = random.Random(seed)
    hits = 0
    for _ in range(n):
        psi = r.uniform(-math.pi, math.pi)
        if abs(s + R * math.sin(psi)) <= w / 2:
            hits += 1
    return hits / n


grid_checks = []
R = R_L
for s_over_R in [0.0, 0.3, 0.6, 0.9, 0.97, 1.0, 1.01, 1.2]:
    for w_over_R in [0.001, 0.01, 0.05, 0.2]:
        s, w = s_over_R * R, w_over_R * R
        pe = p_exact(s, R, w)
        bi = math.sqrt(w / (2 * R))                      # (i)
        assert pe <= bi + 1e-12, (s_over_R, w_over_R, pe, bi)
        rec = {"s/R": s_over_R, "w/R": w_over_R, "p_exact": pe, "bound_i": bi}
        m = 1.0 - s_over_R
        if 0.0 < m <= 1.0 and w <= m * R:                # (ii) applies
            bii = 2 * w / (math.pi * R * math.sqrt(3 * m))
            assert pe <= bii + 1e-12, (s_over_R, w_over_R, pe, bii)
            rec["bound_ii"] = bii
        if s >= R + w / 2:                               # (iii)
            assert pe == 0.0
        if s_over_R == 1.0:                              # (iv) lower bound
            assert pe >= math.sqrt(w / R) / math.pi - 1e-12
        grid_checks.append(rec)
pm = p_mc(0.9 * R, R, 0.05 * R, 200_000, 4002)
pe = p_exact(0.9 * R, R, 0.05 * R)
assert abs(pm - pe) < 0.002, (pm, pe)
out["lemma_A"] = {"grid": grid_checks, "mc_spot": {"exact": pe, "mc": pm}}
print(f"Lemma A: {len(grid_checks)} grid cells obey (i)-(iv); "
      f"MC spot {pm:.5f} vs exact {pe:.5f}")

# ------------------------------------------------- 3. sharpness slope at s=R
ws = [10.0 ** k for k in range(-6, -1)]
ps = [p_exact(R, R, w * R) for w in ws]
slopes = [(math.log(ps[i + 1]) - math.log(ps[i]))
          / (math.log(ws[i + 1]) - math.log(ws[i])) for i in range(len(ws) - 1)]
assert all(abs(sl - 0.5) < 0.02 for sl in slopes), slopes
out["sharpness"] = {"w_over_R": ws, "p": ps, "slopes": slopes}
print(f"Sharpness at tangency: log-log slopes {['%.4f' % s for s in slopes]}"
      f" (theory: 1/2)")

# ------------------------------------------ 4. trajectory-level Theorem T4
GAMMA = 0.6
EPSILONS = [0.0125, 0.025, 0.05, 0.1, 0.2]
N = 4000


def rint_and_hits(gap_lo: float, gap_hi: float, n: int, seed0: int):
    """CRN rollouts under the gap_lo dynamics (the coupled/shared
    trajectory): interior-entry rates at both gaps (separate replays, same
    seeds) and the frequency of a proposed landing in D = A(lo) \\ A(hi)."""
    env_lo = RingField2D(gap=gap_lo)
    env_hi = RingField2D(gap=gap_hi)
    ent_lo = ent_hi = hit_d = 0
    for i in range(n):
        # hit-D + entry under lo (proposed landing = pre-freeze integrator)
        rng = random.Random(seed0 + i)
        s = env_lo.initial_state(rng)
        e = False
        hit = False
        for _ in range(env_lo.h_episode):
            a = rng.uniform(-env_lo.a_max, env_lo.a_max)
            x2, y2, _, _ = integrate_2d(s, a, env_lo.dt, env_lo.gain,
                                        env_lo.drag, env_lo.a_max)
            if (not hit and env_lo._in_mode(x2, y2)
                    and not env_hi._in_mode(x2, y2)):
                hit = True
            s, _, _ = env_lo.step(s, a)
            if not e and env_lo.in_interior(s[0], s[1]):
                e = True
        ent_lo += e
        hit_d += hit
        # entry under hi (same seeds: CRN)
        rng = random.Random(seed0 + i)
        s = env_hi.initial_state(rng)
        e = False
        for _ in range(env_hi.h_episode):
            a = rng.uniform(-env_hi.a_max, env_hi.a_max)
            s, _, _ = env_hi.step(s, a)
            if not e and env_hi.in_interior(s[0], s[1]):
                e = True
        ent_hi += e
    return ent_lo / n, ent_hi / n, hit_d / n


rows = []
for eps in EPSILONS:
    r_lo, r_hi, p_hit = rint_and_hits(GAMMA, GAMMA + eps, N, 50_000)
    bound = env.h_episode * math.sqrt(env.r_out * eps / (env.gain * env.dt ** 2))
    assert abs(r_hi - r_lo) <= p_hit + 1e-12  # Lemma 3, sample-exact side
    assert p_hit <= bound
    rows.append({"eps": eps, "rint_lo": r_lo, "rint_hi": r_hi,
                 "delta_rint": r_hi - r_lo, "p_hit_D": p_hit,
                 "bound_T4": bound})
    print(f"eps={eps}: rint {r_lo:.4f} -> {r_hi:.4f} "
          f"(delta {r_hi - r_lo:+.4f}), P(hit D) = {p_hit:.4f}, "
          f"T4 bound {bound:.1f}")
# empirical eps-scaling of P(hit D): fit slope in log-log (expect ~1 =
# linear, the T4' decomposition's measured counterpart)
xs = [math.log(r["eps"]) for r in rows if r["p_hit_D"] > 0]
ys = [math.log(r["p_hit_D"]) for r in rows if r["p_hit_D"] > 0]
n = len(xs)
mx, my = sum(xs) / n, sum(ys) / n
slope = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
         / sum((x - mx) ** 2 for x in xs))
out["trajectory"] = {"gamma": GAMMA, "n": N, "rows": rows,
                     "p_hit_scaling_slope": slope}
print(f"P(hit D) eps-scaling slope: {slope:.3f} "
      f"(1.0 = linear; tangency band rarely occupied)")

path = pathlib.Path("results/t4_continuity_modulus.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  ({time.time() - t0:.0f}s)")
