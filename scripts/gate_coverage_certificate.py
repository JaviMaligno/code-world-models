"""The continuous coverage certificate: what the deployed gate DOES certify.

Paper 1's coverage guarantee enumerates information sets, and paper 2's
Limitations list its continuous analogue as open. This closes it on the gate side,
using the two pieces the paper now has: the guaranteed disagreement ball
(smoothness forbids exactly localized error) and the gate's visitation density as
a volume ratio.

The certificate has two halves.

(a) DETERMINISTIC. If f and f_hat are L-Lipschitz on U in the sup-metric, f_hat
    passes the gate at tolerance eps on every visited transition, and the visited
    set is a rho-net of U, then for any u in U with nearest visited point v:
        |f(u) - f_hat(u)| <= |f(v) - f_hat(v)| + 2 L rho <= eps + 2 L rho.
    A covering number replaces the enumeration: a gate that rho-covers certifies
    a UNIFORM bound, not just agreement where it looked.

(b) PROBABILISTIC. How many gate samples give a rho-net? Take a minimal
    rho/2-net of U with K = N_cov(U, rho/2) points. If the gate's per-step
    visitation density is at least c on U, each net point's rho/2-ball has
    probability p >= c*vol(B_{rho/2}), so after M independent samples the chance
    some net ball is empty is at most K(1-p)^M <= K exp(-pM); setting that to
    delta gives
        M >= ln(K/delta) / (c * vol(B_{rho/2})).
    Every point of U is then within rho/2 of a net point holding a sample, hence
    within rho of a visited point.

Independence caveat, taken seriously: steps WITHIN a rollout are dependent, so the
rigorous instantiation uses one step per rollout (M = N = 40 for the deployed
gate). The all-steps figure (M = N*T = 3200) is reported too, flagged as assuming
approximate independence across steps -- it is the optimistic end.

Run: PYTHONPATH=src python scripts/gate_coverage_certificate.py   (instant)
"""
import argparse
import json
import math
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--delta", type=float, default=0.05, help="failure probability")
ap.add_argument("--eps-gate", type=float, default=0.01, help="gate tolerance")
ap.add_argument("--n-rollouts", type=int, default=40, help="the deployed N")
ap.add_argument("--horizon", type=int, default=80, help="steps per rollout")
args = ap.parse_args()

env = CartWall(x_wall=8.0)
DIM = 3                                   # (x, v, a)
VOL_U = (2 * env.gain * env.dt * env.a_max) * 1.0 * (2 * env.a_max)
C = 1.0 / VOL_U                           # uniform step-1 law => density 1/vol
# plant Lipschitz constant in the sup-metric (exact for this affine map)
L = max(abs(1 - env.drag * env.dt) + env.gain * env.dt,
        1.0 + env.dt * abs(1 - env.drag * env.dt) + env.gain * env.dt ** 2)


def vol_U_grown(s):
    """vol(U + B_s) for U = {|v|<V, |x - dt*v|<1/2, |a|<a_max}, exactly: growing
    by s in the sup-metric relaxes each constraint, and the slanted slab's area
    is (width in v) x (width in x at fixed v)."""
    V = env.gain * env.dt * env.a_max
    return (2 * (V + s)) * (1.0 + 2 * s * (1 + env.dt)) * (2 * (env.a_max + s))


def n_cover_bound(r):
    """N_cov(U, r) <= |maximal r-packing| <= vol(U + B_{r/2}) / vol(B_{r/2}).
    (A maximal r-packing is an r-cover; its r/2-balls are disjoint and sit inside
    U + B_{r/2}.) Sup-balls: vol(B_t) = (2t)^DIM."""
    return vol_U_grown(r / 2) / ((r) ** DIM)


def ball_mass_fraction(rho):
    """inf_{u in U} vol(B(u, rho/2) INTERSECT U) / vol(B_{rho/2}), computed rather
    than asserted.

    The tempting shortcut is 2^-DIM: for an AXIS-ALIGNED box whose extents all
    exceed rho/2, a corner keeps exactly one orthant of its sup-ball. But this U is
    a SHEARED box, {|v| < V, |x - dt v| < 1/2, |a| < a_max}, and the ratio is not
    shear-invariant --- the sup-ball is axis-aligned while the region is not, so the
    slanted constraint clips the corner cap a little further. Measured here it is
    0.950 * 2^-DIM at the certified rho, i.e. asserting 2^-DIM would have left the
    certificate 5% optimistic. That is small, and it is exactly the size of error
    that hand-asserted geometry produces, so it is computed.

    The infimum is attained at a corner (the scan below re-checks that), and the cap
    volume factorises as (action interval) x (area of the clipped (x, v) slab)."""
    r = rho / 2
    V = env.gain * env.dt * env.a_max

    def cap(ux, uv, ua, n=400):
        la = min(env.a_max, ua + r) - max(-env.a_max, ua - r)
        if la <= 0:
            return 0.0
        lo, hi = max(-V, uv - r), min(V, uv + r)
        if hi <= lo:
            return 0.0
        tot, dv = 0.0, (hi - lo) / n
        for i in range(n):
            v = lo + (i + 0.5) * dv
            xlo = max(env.dt * v - 0.5, ux - r)
            xhi = min(env.dt * v + 0.5, ux + r)
            if xhi > xlo:
                tot += (xhi - xlo) * dv
        return tot * la

    vol_ball = rho ** DIM
    corners = [(env.dt * sv * V + sx * 0.5, sv * V, sa * env.a_max)
               for sv in (-1, 1) for sx in (-1, 1) for sa in (-1, 1)]
    best = min(cap(*c) for c in corners) / vol_ball
    # self-check: no interior point beats the worst corner (coarse scan)
    for i in range(9):
        for j in range(9):
            uv = -V + 2 * V * j / 8
            ux = env.dt * uv - 0.5 + i / 8
            for k in range(9):
                ua = -env.a_max + 2 * env.a_max * k / 8
                best = min(best, cap(ux, uv, ua, n=120) / vol_ball)
    return best


def samples_needed(rho):
    """A rho-net needs every point of a rho/2-net to be hit. K is bounded above
    by n_cover_bound(rho/2) -- an UPPER bound matters here, since a bigger K
    demands more samples (using vol(U)/vol(B) instead, a packing LOWER bound,
    understates it by a factor 2^DIM; corrected 2026-07-25).

    BOUNDARY. The density c is hypothesised only ON U, so a net point p sitting on
    dU gets P(B(p, rho/2)) >= c * vol(B(p, rho/2) INTERSECT U), not c * vol(B).
    The factor is computed by ball_mass_fraction(), not asserted: for this SHEARED
    U it is 0.950 * 2^-DIM rather than the 2^-DIM an axis-aligned box would give
    (caught in peer review, 2026-07-25 -- the same 2^DIM class as the packing slip
    above -- and the residual 5% caught on re-reading our own correction)."""
    vol_ball = rho ** DIM                     # vol(B_{rho/2}), side rho
    K = max(1.0, n_cover_bound(rho / 2))
    p = C * vol_ball * ball_mass_fraction(rho)   # computed, not asserted
    return math.log(K / args.delta) / p


def best_rho(m_available):
    rho = 0.005
    while rho < 4.0:
        if samples_needed(rho) <= m_available:
            return rho
        rho += 0.005
    return None


rows = []
for label, m in (("one step per rollout (rigorous)", args.n_rollouts),
                 ("all steps (assumes approximate independence)",
                  args.n_rollouts * args.horizon)):
    rho = best_rho(m)
    bound = args.eps_gate + 2 * L * rho
    rows.append({"regime": label, "m_samples": m, "rho": rho,
                 "uniform_bound": bound})

grid = [{"rho": r, "m_needed": samples_needed(r),
         "uniform_bound": args.eps_gate + 2 * L * r}
        for r in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8)]

WALL_PROBE_ERROR = 4.2                    # Section "smooth learners", probe err

print(f"cart gate: vol(U) = {VOL_U}, c = {C:.6f}, L_plant = {L:.4f}, "
      f"dim = {DIM}, eps = {args.eps_gate}, delta = {args.delta}")
print(f"\n{'rho':>6} {'M needed':>10} {'certifies |f-fhat| <=':>22}")
for g in grid:
    print(f"{g['rho']:6.2f} {g['m_needed']:10.0f} {g['uniform_bound']:22.3f}")
print()
for r in rows:
    print(f"{r['regime']:>44}: M={r['m_samples']:5} -> rho={r['rho']:.3f}, "
          f"certifies sup|f-fhat| <= {r['uniform_bound']:.3f}")
rig = rows[0]
L_MAX_EXCLUDED = (WALL_PROBE_ERROR - args.eps_gate) / (2 * rig["rho"])
print(f"\nThe hard mode's own disagreement is {WALL_PROBE_ERROR} (the wall-region "
      f"probe error), which exceeds")
print(f"the rigorous bound {rig['uniform_bound']:.3f} -- but only for pairs smooth "
      f"enough. Since eps + 2*L*rho")
print(f"GROWS with L, the certificate excludes an error of {WALL_PROBE_ERROR} exactly "
      f"for pairs with")
print(f"L = max(Lip f, Lip f_hat) <= {L_MAX_EXCLUDED:.3f} (the plant itself is "
      f"{L:.2f}-Lipschitz, so this is")
print("a real but narrow class: a smoother-than-the-plant model cannot carry the")
print("wall's error past this gate, a 2x-rougher one can). The wall itself escapes by")
print("not being Lipschitz at all: that is the boundary of what coverage can buy.")

out = _REPO / "results" / "gate_coverage_certificate.json"
out.write_text(json.dumps(
    {"script": "gate_coverage_certificate.py", "params": vars(args),
     "vol_U": VOL_U, "c": C, "L_plant": L, "dim": DIM,
     "grid": grid, "regimes": rows,
     "wall_probe_error": WALL_PROBE_ERROR,
     "max_L_excluding_wall_error": L_MAX_EXCLUDED}, indent=2))
print(f"\nwrote {out}")
