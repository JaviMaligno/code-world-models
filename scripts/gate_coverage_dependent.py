"""Coverage certificate WITHOUT any independence assumption across steps.

The first version of the certificate had two instantiations: a rigorous one using
one step per rollout (N = 40 samples) and an optimistic one pretending all N*T =
3200 steps were independent. The gap between them (rho 0.615 vs 0.165) was left to
"a mixing argument would buy the optimistic figure honestly". This script settles
that, and the answer is a NEGATIVE result worth having.

No mixing argument is needed, because of a better structure: under the gate policy
the action a_t is drawn i.i.d. and independently of the state s_t. For a product
cell C = C_s x C_a, condition on the ENTIRE state trajectory of a rollout; the
action indicators at the visiting times are then independent Bernoulli(q_a), so

    P(rollout never puts a sample in C | state trajectory) = (1 - q_a)^O,
    O = #{t : s_t in C_s},

which is exact, not a bound, and uses no independence between steps. Rollouts ARE
i.i.d., so the expectation factorises exactly:

    P(C unhit by the whole gate) = ( E[(1 - q_a)^O] )^N  =  phi^N.

phi is a per-rollout expectation of a [0,1] variable, so Monte Carlo plus Hoeffding
gives a rigorous upper bound on it, and the cell is covered with probability
1 - delta/K as soon as phi^N <= delta/(2K).

What it buys: at rho = 0.6, phi <= 0.835 and N >= 39 suffices -- the deployed gate
has exactly 40, so it certifies sup|f - f_hat| <= eps + 2*L*rho = 1.53, against
1.57 for the one-step-per-rollout version. A 2% improvement, not a factor of four.

Why: the binding constraint is not within-rollout dependence at all. It is that the
WORST cell must be visited by a decent fraction of rollouts, and with N = 40 the
tail cells are not. So the optimistic 0.43 was not merely un-rigorous, it was
unreachable at this gate size: certifying finer rho needs a much larger gate, and
the N-vs-rho trade-off measured here is a quantitative statement of how weak a
40-rollout sampling gate is.

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
                default=[0.8, 0.7, 0.6, 0.5, 0.4, 0.3])
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
    """phi_C = E[(1-q_a)^{O_C}] for every state cell, by Monte Carlo over i.i.d.
    rollouts of the gate policy."""
    nx = max(1, int(2 * R / rho))
    q = rho / (2 * A)
    acc = collections.defaultdict(float)
    cells = [(i, j) for i in range(nx) for j in range(nx)]
    for i in range(args.mc_rollouts):
        rng = random.Random(args.seed + i)
        s = env.initial_state(rng)
        loc = collections.Counter()
        for _ in range(T):
            a = rng.uniform(-A, A)
            x, v = s
            if abs(x) < R and abs(v) < R:
                loc[(min(nx - 1, int((x + R) / rho)),
                     min(nx - 1, int((v + R) / rho)))] += 1
            s = env.step(s, a)[0]
        for c in cells:
            acc[c] += (1 - q) ** loc.get(c, 0)
    phis = {c: acc[c] / args.mc_rollouts for c in cells}
    n_action_cells = max(1, int(2 * A / rho))
    return phis, len(cells) * n_action_cells, q


rows = []
print(f"region |x|,|v| <= {R};  L = {L:.4f};  eps = {args.eps_gate};  "
      f"delta = {args.delta};  MC = {args.mc_rollouts} rollouts")
print(f"{'rho':>6} {'K':>6} {'q_a':>6} {'worst phi':>10} {'phi UB':>8} "
      f"{'N needed (rig)':>15} {'N needed (est)':>15} {'certifies':>10}")
for rho in args.rhos:
    phis, K, q = phi_per_cell(rho)
    worst = max(phis.values())
    ub_term = math.sqrt(math.log(3 * K / args.delta) / (2 * args.mc_rollouts))
    worst_ub = min(1.0, worst + ub_term)
    target = args.delta / (2 * K)
    n_rig = (math.ceil(math.log(target) / math.log(worst_ub))
             if worst_ub < 1.0 else None)
    n_est = (math.ceil(math.log(target) / math.log(worst))
             if worst < 1.0 else None)
    bound = args.eps_gate + 2 * L * rho
    rows.append({"rho": rho, "n_cells": K, "q_a": q, "worst_phi": worst,
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
print("one step per rollout gave rho = 0.615 -> 1.572, so handling the dependence "
      "buys ~2%,")
print("not the factor of four the 'all steps independent' reading suggested: the "
      "binding")
print("constraint is how many ROLLOUTS reach the worst cell, not how the steps "
      "correlate.")

out = _REPO / "results" / "gate_coverage_dependent.json"
out.write_text(json.dumps({"script": "gate_coverage_dependent.py",
                           "params": vars(args), "L_plant": L, "rows": rows},
                          indent=2))
print(f"\nwrote {out}")
