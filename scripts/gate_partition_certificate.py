"""The coverage certificate by PARTITION instead of packing: twice as strong, and
with no geometric factor to get wrong.

Why this exists. The certificate's probabilistic half was first instantiated with a
maximal-packing argument: bound the packing number of U above, bound each net point's
ball probability below, union-bound. Peer review found two errors in that
instantiation and we then found a third, all of the same kind -- a geometric factor
asserted rather than computed:

  * the cardinality must be the PACKING number, not the covering number;
  * the ball mass must be intersected with U, since the density is hypothesised only
    on U (a corner of an axis-aligned box keeps one orthant: 2^-(d+m));
  * and that orthant factor is NOT shear-invariant, while the cart's U is a sheared
    box -- the true factor is 0.950 * 2^-(d+m).

Each fix made the certificate weaker: rho = 0.615 -> 1.150 -> 1.165, bound 1.57 ->
2.93 -> 2.97. That is the honest direction, but it invites the wrong conclusion,
because the losses are artifacts of the ARGUMENT, not facts about the gate. A
packing bound pays for the covering number twice (once in K, once in the ball mass)
and both payments are geometry that has to be estimated.

A partition argument pays neither, and on this instrument it is exact.

PART (a): EXACT, NO MONTE CARLO. Under the gate policy the step-1 law of (x, v, a) is
uniform on U = {|v| <= V, |x - dt*v| <= 1/2, |a| <= a_max}. In the sheared coordinate
y = x - dt*v that is uniform on a BOX, [-1/2, 1/2] x [-V, V] x [-a_max, a_max], and
the shear has unit Jacobian. So partition the box into n_y * n_v * n_a equal
sub-boxes: each has probability EXACTLY 1/K, K = n_y*n_v*n_a. With M i.i.d. samples,

    P(some cell empty)  <=  K (1 - 1/K)^M,

which needs no density constant, no covering number and no ball geometry. If every
cell holds a sample then the visited set is a rho-net, with rho the cell's sup
diameter measured in the ORIGINAL coordinates -- the one place the shear costs
anything:

    |x - x'| = |(y - y') + dt(v - v')| <= Delta_y + dt*Delta_v,
    rho = max(Delta_y + dt*Delta_v,  Delta_v,  Delta_a).

Maximising over partitions subject to K (1-1/K)^M <= delta gives, at the deployed
M = N = 40 (one step per rollout, so the samples are genuinely independent):
K = 8 with (n_y, n_v, n_a) = (2, 1, 4), rho = 0.600, and a certified bound of 1.534
-- against 2.969 by the packing route. Note what rho is pinned by: Delta_v = 2V, the
full reachable velocity range. At this gate size the certificate simply cannot
resolve velocity, and that is a statement about the gate rather than about the proof.

PART (b): ALL STEPS, STILL WITHOUT ASSUMING THEY ARE INDEPENDENT. Part (a) uses one
step per rollout because steps within a rollout are dependent. The dependence needs
no factorisation argument (see gate_coverage_dependent.py): with
p_C = P(one rollout puts no sample in cell C), which is a plain Bernoulli parameter
whatever happens within a rollout, the i.i.d.-ness of ROLLOUTS gives

    P(C unhit by the gate) = p_C^N   exactly,

and p_C is measured directly, with Hoeffding for the upper bound. This buys a much
finer partition, because a rollout gets 80 chances at U rather than one.

Both parts certify sup_U |f - f_hat| <= eps + 2*L*rho for L-Lipschitz pairs passing
the gate at tolerance eps (Proposition "coverage", part 1, which is untouched by any
of this -- only the sample-size half was ever in question).

Run: PYTHONPATH=src python scripts/gate_partition_certificate.py   (~5 min CPU)
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
ap.add_argument("--n-gate", type=int, default=40, help="the deployed N")
ap.add_argument("--delta", type=float, default=0.05)
ap.add_argument("--eps-gate", type=float, default=0.01)
ap.add_argument("--mc-rollouts", type=int, default=20000,
                help="Monte Carlo budget for part (b)'s p_C")
ap.add_argument("--max-cells", type=int, default=24,
                help="largest partition part (a) searches (K is capped by delta "
                     "long before this)")
ap.add_argument("--max-cells-b", type=int, default=400,
                help="largest partition part (b) searches")
ap.add_argument("--part-a-only", action="store_true",
                help="run only the exact part (a) -- no Monte Carlo -- and VERIFY it "
                     "against the versioned JSON instead of overwriting it. This is "
                     "the CI mode: part (a) needs no sampling, so it can be "
                     "re-derived on every push, while part (b) costs 20k rollouts "
                     "and must not clobber the committed result.")
ap.add_argument("--seed", type=int, default=4242)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
DT, A = env.dt, env.a_max
V = env.gain * env.dt * A          # the one-step reachable |v| bound
Y = 0.5                            # |y| = |x - dt v| bound
L = max(abs(1 - env.drag * DT) + env.gain * DT,
        1.0 + DT * abs(1 - env.drag * DT) + env.gain * DT ** 2)
VOL_U = (2 * V) * (2 * Y) / 2 * 2 * (2 * A) / 2   # = 2V * 2Y * 2A / ... see below
VOL_U = (2 * V) * (2 * Y) * (2 * A)               # 0.6 * 1.0 * 2.0 = 1.2


def net_radius(ny, nv, na):
    """Sup diameter of a cell, in the ORIGINAL (x, v, a) coordinates."""
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    return max(dy + DT * dv, dv, da), (dy, dv, da)


# --- part (a): exact ----------------------------------------------------------
def failure_prob(K, m):
    """K (1 - 1/K)^m, the union bound with EXACT per-cell probability 1/K."""
    return K * (1 - 1.0 / K) ** m


best_a = None
grid_a = []
for ny in range(1, args.max_cells + 1):
    for nv in range(1, args.max_cells + 1):
        for na in range(1, args.max_cells + 1):
            K = ny * nv * na
            if K > args.max_cells:
                continue
            fail = failure_prob(K, args.n_gate)
            if fail > args.delta:
                continue
            rho, deltas = net_radius(ny, nv, na)
            row = {"n_y": ny, "n_v": nv, "n_a": na, "K": K,
                   "failure_prob": fail, "rho": rho,
                   "cell_extents": deltas,
                   "uniform_bound": args.eps_gate + 2 * L * rho}
            grid_a.append(row)
            if best_a is None or rho < best_a["rho"]:
                best_a = row

print(f"U: |v| <= {V}, |x - dt v| <= {Y}, |a| <= {A};  vol(U) = {VOL_U};  "
      f"L = {L:.4f};  eps = {args.eps_gate};  delta = {args.delta}")
K_MAX = max((r["K"] for r in grid_a), default=0)
print(f"\n(a) EXACT partition, M = N = {args.n_gate} independent step-1 samples.")
print(f"    largest admissible K: {K_MAX}  "
      f"(K+1 = {K_MAX+1} would fail: {failure_prob(K_MAX+1, args.n_gate):.4f} "
      f"> {args.delta})")
print(f"    {'n_y':>4} {'n_v':>4} {'n_a':>4} {'K':>4} {'P(fail)':>9} {'rho':>7} "
      f"{'certifies':>10}")
for r in sorted(grid_a, key=lambda r: r["rho"])[:6]:
    print(f"    {r['n_y']:4} {r['n_v']:4} {r['n_a']:4} {r['K']:4} "
          f"{r['failure_prob']:9.4f} {r['rho']:7.3f} {r['uniform_bound']:10.3f}")
print(f"    best: rho = {best_a['rho']:.3f}, certifies "
      f"sup|f - f_hat| <= {best_a['uniform_bound']:.4f}")
print(f"    pinned by Delta_v = {best_a['cell_extents'][1]:.3f} "
      f"(the full reachable velocity range: at this N the certificate cannot "
      f"resolve v at all)")


if args.part_a_only:
    dst = _REPO / "results" / "gate_partition_certificate.json"
    prev = json.loads(dst.read_text())
    ref = prev["exact_best"]
    same = (ref["n_y"], ref["n_v"], ref["n_a"]) == (best_a["n_y"], best_a["n_v"],
                                                    best_a["n_a"]) \
        and abs(ref["rho"] - best_a["rho"]) < 1e-12 \
        and abs(ref["uniform_bound"] - best_a["uniform_bound"]) < 1e-9 \
        and prev["max_admissible_K_exact"] == K_MAX
    print(f"\n[--part-a-only] re-derived exact certificate vs the versioned JSON: "
          f"{'MATCH' if same else 'MISMATCH'}")
    if not same:
        print(f"  versioned: {ref}")
        print(f"  re-derived: {best_a}")
        sys.exit(1)
    print("  (part (b) not re-run and the JSON not touched: it costs 20k rollouts)")
    sys.exit(0)


# --- part (b): all steps, dependence handled by direct measurement -------------
def p_miss_per_cell(ny, nv, na):
    """p_C for every cell: the measured probability that ONE gate rollout puts no
    sample in C. No factorisation, no independence between steps -- only the
    i.i.d.-ness of rollouts, which is a property of the gate's design."""
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    miss = collections.defaultdict(int)
    cells = [(i, j, k) for i in range(ny) for j in range(nv) for k in range(na)]
    for i in range(args.mc_rollouts):
        rng = random.Random(args.seed + i)
        s = env.initial_state(rng)
        hit = set()
        for _ in range(env.h_episode):
            a = rng.uniform(-A, A)
            x, v = s
            y = x - DT * v
            if abs(y) < Y and abs(v) < V and abs(a) < A:
                hit.add((min(ny - 1, int((y + Y) / dy)),
                         min(nv - 1, int((v + V) / dv)),
                         min(na - 1, int((a + A) / da))))
            s = env.step(s, a)[0]
        for c in cells:
            if c not in hit:
                miss[c] += 1
    return {c: miss[c] / args.mc_rollouts for c in cells}, len(cells)


def coarsest_for(rho_target):
    """The partition with the FEWEST cells whose net radius is <= rho_target.

    Choosing candidates by net radius alone is not enough: a partition can be
    needlessly fine on an axis that does not set the radius, paying for cells it does
    not need. Since rho = max(Delta_y + dt*Delta_v, Delta_v, Delta_a), the coarsest
    admissible partition takes each axis to its own ceiling."""
    na = math.ceil(2 * A / rho_target)
    nv = math.ceil(2 * V / rho_target)
    dv = 2 * V / nv
    slack = rho_target - DT * dv
    if slack <= 0:
        return None
    ny = math.ceil(2 * Y / slack)
    rho, _ = net_radius(ny, nv, na)
    if rho > rho_target + 1e-12:
        return None
    return rho, ny, nv, na, ny * nv * na


CANDIDATES_B, _seen = [], set()
_r = 2.0
while _r > 0.08:
    c = coarsest_for(_r)
    if c and (c[1], c[2], c[3]) not in _seen:
        _seen.add((c[1], c[2], c[3]))
        CANDIDATES_B.append(c)
    _r -= 0.01
CANDIDATES_B.sort(reverse=True)

print(f"\n(b) ALL steps, p_C measured directly ({args.mc_rollouts} MC rollouts), "
      f"N = {args.n_gate}.")
print(f"    {'n_y':>4} {'n_v':>4} {'n_a':>4} {'K':>4} {'worst p_C':>10} "
      f"{'p_C UB':>8} {'K*UB^N':>10} {'rho':>7} {'certifies':>10}")
# Search coarse -> fine and stop after a few consecutive failures. Going the other
# way spends the whole MC budget on partitions so fine that no gate could hit every
# cell, which tells us nothing.
best_b, rows_b = None, []
tried, consecutive_fail = 0, 0
for rho, ny, nv, na, K in CANDIDATES_B:
    if best_b is not None and rho >= best_b["rho"]:
        continue                      # only finer partitions can improve
    if tried >= 18 or consecutive_fail >= 4:
        break
    tried += 1
    ps, K = p_miss_per_cell(ny, nv, na)
    worst = max(ps.values())
    # Hoeffding at level delta/3 spread over K cells, then union bound at delta/2
    ub_term = math.sqrt(math.log(3 * K / args.delta) / (2 * args.mc_rollouts))
    worst_ub = min(1.0, worst + ub_term)
    fail = K * worst_ub ** args.n_gate if worst_ub < 1.0 else float("inf")
    ok = fail <= args.delta / 2
    row = {"n_y": ny, "n_v": nv, "n_a": na, "K": K, "rho": rho,
           "worst_p_C": worst, "worst_p_C_ub": worst_ub, "union_failure": fail,
           "certified": bool(ok),
           "uniform_bound": args.eps_gate + 2 * L * rho}
    rows_b.append(row)
    print(f"    {ny:4} {nv:4} {na:4} {K:4} {worst:10.4f} {worst_ub:8.4f} "
          f"{min(fail, 9.9999):10.4f} {rho:7.3f} "
          f"{row['uniform_bound']:10.3f}{'  <= CERTIFIED' if ok else ''}",
          flush=True)
    if ok:
        consecutive_fail = 0
        if best_b is None or rho < best_b["rho"]:
            best_b = row
    else:
        consecutive_fail += 1

if best_b:
    print(f"\n    best: rho = {best_b['rho']:.3f}, certifies "
          f"sup|f - f_hat| <= {best_b['uniform_bound']:.4f}")
else:
    print("\n    no partition finer than part (a)'s is certified at this budget")

print("\nSummary against the packing route (results/gate_coverage_certificate.json):")
print(f"  packing + ball geometry, 1 step/rollout : rho = 1.165, bound 2.969")
print(f"  EXACT partition,         1 step/rollout : rho = {best_a['rho']:.3f}, "
      f"bound {best_a['uniform_bound']:.3f}")
if best_b:
    print(f"  measured partition,      all steps      : rho = {best_b['rho']:.3f}, "
          f"bound {best_b['uniform_bound']:.3f}")
print("The gain is entirely in the argument: a partition pays for neither the "
      "covering")
print("number nor the ball's boundary, and on this instrument its cell "
      "probabilities are")
print("exact. Nothing about the gate changed.")

out = _REPO / "results" / "gate_partition_certificate.json"
out.write_text(json.dumps(
    {"script": "gate_partition_certificate.py", "params": vars(args),
     "U": {"V": V, "Y": Y, "a_max": A, "vol": VOL_U}, "L_plant": L,
     "max_admissible_K_exact": K_MAX,
     "exact_grid": sorted(grid_a, key=lambda r: r["rho"]),
     "exact_best": best_a,
     "measured_rows": rows_b, "measured_best": best_b}, indent=2))
print(f"\nwrote {out}")
