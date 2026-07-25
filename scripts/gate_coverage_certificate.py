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


def samples_needed(rho):
    """A rho-net needs every point of a rho/2-net to be hit. K is bounded above
    by n_cover_bound(rho/2) -- an UPPER bound matters here, since a bigger K
    demands more samples (using vol(U)/vol(B) instead, a packing LOWER bound,
    understates it by a factor 2^DIM; corrected 2026-07-25)."""
    vol_ball = rho ** DIM                     # vol(B_{rho/2}), side rho
    K = max(1.0, n_cover_bound(rho / 2))
    p = C * vol_ball
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
print(f"\nThe hard mode's own disagreement is {WALL_PROBE_ERROR} (the wall-region "
      f"probe error), which exceeds")
print("both bounds -- so the certificate EXCLUDES any Lipschitz model with the")
print("wall's error magnitude. The wall escapes it only by not being Lipschitz:")
print("that is the exact boundary of what a continuous coverage guarantee can buy.")

out = _REPO / "results" / "gate_coverage_certificate.json"
out.write_text(json.dumps(
    {"script": "gate_coverage_certificate.py", "params": vars(args),
     "vol_U": VOL_U, "c": C, "L_plant": L, "dim": DIM,
     "grid": grid, "regimes": rows,
     "wall_probe_error": WALL_PROBE_ERROR}, indent=2))
print(f"\nwrote {out}")
