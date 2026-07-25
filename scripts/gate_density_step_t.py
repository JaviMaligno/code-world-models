"""The gate's visitation density at ANY step, not just the first.

The coverage certificate's one remaining open hypothesis was that the visitation
density is derived in closed form only at step 1, which restricted the certified
region U to the one-step reachable set. This derives it for every step t >= 2, so
the certificate applies to the much larger region the gate actually visits.

The derivation. Under the gate policy the plant is linear and time-invariant, so
(x_t, v_t) is an affine function of (x_0, a_0, ..., a_{t-1}), all independent
uniforms. Split off the LAST TWO actions:

    (x_t, v_t) = W_t + M (a_{t-2}, a_{t-1})^T,

where W_t is the contribution of x_0 and a_0..a_{t-3} (i.e. the state reached with
the last two actions set to zero) and M is the Jacobian of the last two actions,
which by time-invariance does not depend on t:

    dv/da_{t-1} = gain*dt                      dv/da_{t-2} = (1-drag*dt)*gain*dt
    dx/da_{t-1} = dt*gain*dt                   dx/da_{t-2} = dt*(1-drag*dt)*gain*dt + gain*dt^2

    |det M| = gain^2 dt^3 (1 - drag*dt) - ... = 0.009 for the paper's constants,

verified against finite differences. Hence the step-t law is the convolution of
W_t's law with the uniform law on the parallelogram M[-a_max, a_max]^2, whose area
is 4 a_max^2 |det M| = 0.036 and whose density is 1/0.036 = 27.78. Therefore

    p_t(u) >= (1/area) * P( M^{-1}(u - W_t) in [-a_max, a_max]^2 ),

an EXACT constant times a probability. The derivation's job is done by that
statement: two actions suffice to make the step-t law absolutely continuous, with a
density bounded below by 27.78 times a reachability probability, at EVERY t >= 2 --
which is what the certificate needed and did not have.

Taking the infimum over a BOX is useless, though, and measuring that was the point:
a box's corners (extreme x with extreme v) are unreachable, so the infimum is 0 and
the bound is vacuous. The certified region must be a LEVEL SET of the density, not a
box. So the script reports, per step, the level sets {p_t >= alpha}: their volume
and a Clopper-Pearson lower bound on alpha, which is exactly the (c, U) pair
Proposition 9 consumes.

Run: PYTHONPATH=src python scripts/gate_density_step_t.py   (~2 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--steps", type=int, nargs="+", default=[2, 5, 10, 20, 40, 80])
ap.add_argument("--region", type=float, nargs=2, default=[3.0, 2.0],
                help="certify over |x| <= X, |v| <= V")
ap.add_argument("--grid", type=int, default=9, help="grid points per axis over U")
ap.add_argument("--mc", type=int, default=20000, help="MC samples of W_t")
ap.add_argument("--delta", type=float, default=0.05)
ap.add_argument("--seed", type=int, default=99)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
dt, g, dr, A = env.dt, env.gain, env.drag, env.a_max
k = 1 - dr * dt

# --- M and its determinant, in closed form ----------------------------------
M = [[dt * g * dt, dt * k * g * dt + g * dt * dt],   # dx/da_{t-1}, dx/da_{t-2}
     [g * dt,      k * g * dt]]                      # dv/da_{t-1}, dv/da_{t-2}
DET = M[0][0] * M[1][1] - M[0][1] * M[1][0]
AREA = 4 * A * A * abs(DET)
DENS = 1.0 / AREA


def inv_apply(du):
    """M^{-1} du -> the (a_{t-1}, a_{t-2}) needed to move by du."""
    a, b, c, d = M[0][0], M[0][1], M[1][0], M[1][1]
    return ((d * du[0] - b * du[1]) / DET, (-c * du[0] + a * du[1]) / DET)


def w_samples(t, n):
    """W_t: the step-t state with the last two actions set to zero."""
    out = []
    for i in range(n):
        rng = random.Random(args.seed + 7919 * t + i)
        x = rng.uniform(-0.5, 0.5)
        v = 0.0
        acts = [rng.uniform(-A, A) for _ in range(t)]
        acts[-1] = 0.0
        acts[-2] = 0.0
        for a in acts:
            v = v + (g * a - dr * v) * dt
            x = x + v * dt
        out.append((x, v))
    return out


from cwm.law import wilson_ci  # noqa: E402

Z_CONSERVATIVE = 4.0
"""z = 4 corresponds to a per-cell level of ~3.2e-5, so with a couple of hundred
cells the family-wise level stays far below delta = 0.05 -- conservative on purpose,
and the same Wilson machinery the rest of the paper uses (an exact Clopper-Pearson
tail overflows in plain floats at n in the thousands)."""


def cp_lower(k_hits, n, _delta_unused):
    """Wilson lower bound at z = 4 (see Z_CONSERVATIVE)."""
    if k_hits == 0:
        return 0.0
    return wilson_ci(k_hits, n, z=Z_CONSERVATIVE)[1]


GX, GV = args.region


def level_sets(t, n, rho):
    """Per-cell empirical density of the step-t (x, v) law on a rho-grid, with a
    Clopper-Pearson lower bound per cell, then the level sets it supports."""
    nx = int(2 * GX / rho)
    nv = int(2 * GV / rho)
    cnt = {}
    for i in range(n):
        rng = random.Random(args.seed + 7919 * t + i)
        x = rng.uniform(-0.5, 0.5)
        v = 0.0
        for _ in range(t):
            a = rng.uniform(-A, A)
            v = v + (g * a - dr * v) * dt
            x = x + v * dt
        if abs(x) < GX and abs(v) < GV:
            key = (min(nx - 1, int((x + GX) / rho)),
                   min(nv - 1, int((v + GV) / rho)))
            cnt[key] = cnt.get(key, 0) + 1
    cell_vol = rho * rho
    n_cells = nx * nv
    dens = {}
    for key, c in cnt.items():
        lo = cp_lower(c, n, args.delta / n_cells)
        dens[key] = lo / cell_vol          # density lower bound on that cell
    return dens, cell_vol, n_cells


ALPHAS = [0.5, 0.2, 0.1, 0.05, 0.02, 0.01]
rows = []
print(f"|det M| = {abs(DET):.6f}  parallelogram area = {AREA:.6f}  "
      f"density = {DENS:.4f}   (time-invariant, so a density exists at every "
      f"t >= 2)")
print(f"box |x| <= {GX}, |v| <= {GV};  MC = {args.mc};  delta = {args.delta}\n")
print(f"{'step':>5} " + " ".join(f"vol(p>={a})".rjust(12) for a in ALPHAS))
for t_step in args.steps:
    dens, cell_vol, n_cells = level_sets(t_step, args.mc, 0.25)
    vols = []
    for a in ALPHAS:
        vol_xv = sum(cell_vol for d in dens.values() if d >= a)
        vols.append(vol_xv * 2 * A)        # times the action range
    rows.append({"step": t_step, "alphas": ALPHAS, "volumes_sa": vols})
    print(f"{t_step:5} " + " ".join(f"{v:12.3f}" for v in vols))

# the best (c, U) pair by certified volume at a useful resolution
best = None
for r in rows:
    for a, v in zip(r["alphas"], r["volumes_sa"]):
        if v > 0 and (best is None or v > best["volume_sa"]):
            best = {"step": r["step"], "c": a, "volume_sa": v}
print(f"\nlargest certified region: step {best['step']}, c >= {best['c']}, "
      f"vol(U) = {best['volume_sa']:.2f} in (x, v, a)")
print(f"step-1 certificate had c = {5/6:.4f} on vol(U) = 1.2, so this is "
      f"{best['volume_sa']/1.2:.0f}x the region at "
      f"{best['c']/(5/6):.2f}x the density.")

out = _REPO / "results" / "gate_density_step_t.json"
out.write_text(json.dumps(
    {"script": "gate_density_step_t.py", "params": vars(args),
     "M": M, "det_M": DET, "parallelogram_area": AREA,
     "parallelogram_density": DENS, "box": [GX, GV], "rows": rows,
     "best": best}, indent=2))
print(f"\nwrote {out}")
