"""Coverage certificate WITHOUT any independence assumption across steps.

The first version of the certificate had two instantiations: a rigorous one using
one step per rollout (N = 40 samples) and an optimistic one pretending all N*T =
3200 steps were independent. The gap between them (rho 0.615 vs 0.165) was left to
"a mixing argument would buy the optimistic figure honestly". This settles that, and
the answer is a NEGATIVE result worth having.

WHAT THIS SCRIPT USED TO DO, AND WHY IT WAS WRONG. It modelled the per-rollout unhit
probability as phi_C = E[(1 - q_a)^{O_C}], claiming this was EXACT by conditioning on
the rollout's entire state trajectory and calling the action indicators at the
visiting times independent Bernoulli(q_a). That argument is invalid: under this plant
the action is recoverable from consecutive states (a_t = ((v_{t+1}-v_t)/dt + drag*v_t)
/gain), so conditioning on the whole state trajectory determines every action -- the
conditional indicator law is degenerate, not Bernoulli. a_t is independent of s_t, not
of the trajectory. Peer review caught this (2026-07-25) and measured the damage: at
rho = 0.6 the model gave 0.802 against a true 0.812 at the binding cell, i.e.
ANTI-conservative, and up to 11.6% off elsewhere.

WHAT IT DOES NOW. The factorisation was never needed. Only ONE independence fact is
used, and it is a fact of the design rather than of the dynamics: the N gate rollouts
are i.i.d. So, with p_C = P(a single rollout puts no sample in cell C) -- a plain
Bernoulli parameter, whatever the within-rollout dependence --

    P(C unhit by the whole gate) = p_C^N,   exactly.

p_C is estimated by Monte Carlo directly (count rollouts that miss C) and bounded
above by Hoeffding; the cell is covered with probability 1 - delta/K as soon as
p_C^N <= delta/(2K). Nothing is assumed about how steps within a rollout correlate,
because nothing needs to be.

The grid is honest too: ceil, so every cell is at most rho wide (see phi_per_cell).

Run: PYTHONPATH=src python scripts/gate_coverage_dependent.py   (~6 min CPU)
"""
import argparse
import collections
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--region", type=float, default=1.0,
                help="certify over |x| <= R, |v| <= R (interior of the reachable set)")
ap.add_argument("--rhos", type=float, nargs="+",
                default=[2.0, 1.0, 0.8, 0.667, 0.5, 0.4, 0.3])
ap.add_argument("--mc-rollouts", type=int, default=8000,
                help="Monte Carlo budget for phi (bigger = tighter upper bound)")
ap.add_argument("--n-gate", type=int, default=40)
ap.add_argument("--delta", type=float, default=0.05)
ap.add_argument("--eps-gate", type=float, default=0.01)
ap.add_argument("--seed", type=int, default=4242)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
T, A, R = env.h_episode, env.a_max, args.region
L = max(abs(1 - env.drag * env.dt) + env.gain * env.dt,
        1.0 + env.dt * abs(1 - env.drag * env.dt) + env.gain * env.dt ** 2)


def phi_per_cell(rho):
    """p_C = P(one gate rollout puts no sample in cell C), measured directly for
    every product cell of the (x, v, a) grid.

    The grid must be HONEST: every cell no wider than rho, and every point of the
    region in some cell. `int(2R/rho)` cells of nominal width rho plus index
    clamping does neither -- at rho = 0.6 it makes the top cell 0.8 wide, so
    hitting all cells certifies only a 0.8-net, and the action sliver [0.8, 1.0]
    lands in no cell at all while being charged q_a = rho/2A. That bug (caught in
    peer review, 2026-07-25) turned the whole rho-vs-N table into a grid artifact.
    So: ceil, and cell width 2R/nx <= rho exactly."""
    nx = max(1, math.ceil(2 * R / rho))
    wx = 2 * R / nx                                # <= rho by construction
    na = max(1, math.ceil(2 * A / rho))
    wa = 2 * A / na                                # <= rho
    q = wa / (2 * A)                               # exact per-step action-cell mass
    miss = collections.defaultdict(int)
    cells = [(i, j, k) for i in range(nx) for j in range(nx) for k in range(na)]
    for i in range(args.mc_rollouts):
        rng = random.Random(args.seed + i)
        s = env.initial_state(rng)
        hit = set()
        for _ in range(T):
            a = rng.uniform(-A, A)
            x, v = s
            if abs(x) < R and abs(v) < R:
                hit.add((min(nx - 1, int((x + R) / wx)),
                         min(nx - 1, int((v + R) / wx)),
                         min(na - 1, int((a + A) / wa))))
            s = env.step(s, a)[0]
        for c in cells:
            if c not in hit:
                miss[c] += 1
    # p_C: the DIRECTLY measured per-rollout probability of missing cell C.
    ps = {c: miss[c] / args.mc_rollouts for c in cells}
    return ps, len(cells), q, max(wx, wa)


rows = []
print(f"region |x|,|v| <= {R};  L = {L:.4f};  eps = {args.eps_gate};  "
      f"delta = {args.delta};  MC = {args.mc_rollouts} rollouts")
print(f"{'rho':>6} {'K':>6} {'q_a':>6} {'worst phi':>10} {'phi UB':>8} "
      f"{'N needed (rig)':>15} {'N needed (est)':>15} {'certifies':>10}")
for rho in args.rhos:
    ps, K, q, w_eff = phi_per_cell(rho)
    worst = max(ps.values())
    ub_term = math.sqrt(math.log(3 * K / args.delta) / (2 * args.mc_rollouts))
    worst_ub = min(1.0, worst + ub_term)
    target = args.delta / (2 * K)
    # worst == 0 means every cell is hit by every rollout in the MC sample, so a
    # single rollout suffices on the point estimate; the rigorous bound still has
    # to pay the Hoeffding term, which is why n_rig can be finite when n_est is 1.
    n_rig = (math.ceil(math.log(target) / math.log(worst_ub))
             if 0.0 < worst_ub < 1.0 else (1 if worst_ub == 0.0 else None))
    n_est = (math.ceil(math.log(target) / math.log(worst))
             if 0.0 < worst < 1.0 else (1 if worst == 0.0 else None))
    bound = args.eps_gate + 2 * L * w_eff
    rows.append({"rho": rho, "cell_width": w_eff, "n_cells": K, "q_a": q,
                 "worst_phi": worst,
                 "worst_phi_ub": worst_ub, "n_needed_rigorous": n_rig,
                 "n_needed_estimated": n_est, "uniform_bound": bound,
                 "certified_at_deployed_N": bool(n_rig and n_rig <= args.n_gate)})
    print(f"{rho:6.2f} {K:6} {q:6.3f} {worst:10.4f} {worst_ub:8.4f} "
          f"{str(n_rig):>15} {str(n_est):>15} {bound:10.3f}")

ok = [r for r in rows if r["certified_at_deployed_N"]]
best = min(ok, key=lambda r: r["rho"]) if ok else None
print()
if best:
    print(f"deployed gate (N = {args.n_gate}) certifies at rho = {best['rho']}: "
          f"sup|f - f_hat| <= {best['uniform_bound']:.3f} "
          f"(needs N >= {best['n_needed_rigorous']})")
print("Reading: the binding constraint is not within-rollout dependence at all -- it")
print("is how many ROLLOUTS reach the worst cell. Handling the dependence honestly")
print("(direct p_C, no factorisation) and gridding honestly (every cell <= rho) makes")
print("the deployed 40-rollout gate WEAKER than the first version claimed, not")
print("stronger: the 'all steps independent' reading was not merely un-rigorous, its")
print("resolution was unreachable at this gate size by a wide margin.")

out = _REPO / "results" / "gate_coverage_dependent.json"
out.write_text(json.dumps({"script": "gate_coverage_dependent.py",
                           "params": vars(args), "L_plant": L, "rows": rows},
                          indent=2))
print(f"\nwrote {out}")
