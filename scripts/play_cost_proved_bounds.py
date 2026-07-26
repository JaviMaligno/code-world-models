"""The play-cost corollary with no measured supremum left in it.

Corollary "playcost saturation" normalises by $J_max$ and $J_min$, the essential
supremum and infimum of the realized return. Both were MEASURED: $J_max$ as the best
constant policy's return from the most favourable start, $J_min$ as the smallest
return observed. A supremum estimated over a policy class is not a supremum, and the
corollary's headline -- that the measurement sits at 98.7% of its bound -- rested on
it. This derives both, so the ceiling is a theorem and the only measured quantity
left in the corollary is the thing being bounded.

THE UPPER BOUND. Two facts about this instrument multiply.

  * The reward is r(x) = a_left*sigmoid((x_left - x)/w) + a_right*sigmoid((x -
    x_right)/w): a small plateau far to the LEFT (amplitude 0.3 at x_left = -6) and a
    large one far to the RIGHT (amplitude 1.0 at x_right = 12). The first term is
    decreasing in x, the second increasing, so over any interval the sum is at most
    the left term at the left end plus the right term at the right end.

  * The truth clamps x <= x_wall <= 10 < x_right, so the right plateau is
    unreachable and its term is bounded by a_right*sigmoid((x_wall - x_right)/w)
    uniformly -- 3.4e-4 at x_wall = 8, and smaller at every nearer wall.

  * The leftmost position reachable at step t is attained by pushing left
    throughout. That is not an assumption: x_t is affine in (a_0, ..., a_{t-1}) with
    all coefficients positive (each action enters through gain*dt^2 times a positive
    sum of powers of 1 - drag*dt), so x_t is minimised at a_s = -a_max for all s.

Together, for ANY policy and any admissible x_0,

    J = sum_t r(x_t) <= sum_t [ a_left*sigmoid((x_left - x_min(t))/w)
                                + a_right*sigmoid((x_wall - x_right)/w) ],

with x_min(t) the push-left trajectory from x_0 = -x0_range. On the paper's constants
this gives 18.0359 against a measured best of 18.0091 -- 0.15% slack, because the
optimal policy really is "push left and stay", so the reachability envelope is nearly
attained rather than merely valid.

THE LOWER BOUND. r > 0 everywhere, so J_min >= T * min_{x reachable} r(x), an
explicit positive number (1.3e-6 at x_wall = 8, attained near x = 2.7 where the left
plateau's tail has died and the right one has not begun). That is what makes "the
blind planner is pinned at the realizable floor" a statement with a floor in it.

The oracle test searches policies -- random, bang-bang, and switching -- and confirms
none exceeds the derived ceiling, which is the check that would catch a sign error in
the monotonicity argument.

Run: PYTHONPATH=src python scripts/play_cost_proved_bounds.py   (~3 min CPU)
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
ap.add_argument("--walls", type=float, nargs="+",
                default=[2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0])
ap.add_argument("--oracle-policies", type=int, default=4000,
                help="random policies per knob, to try to beat the derived ceiling")
ap.add_argument("--verify", action="store_true",
                help="recompute and CHECK against the versioned JSON instead of "
                     "overwriting it. The CI mode: the bounds are closed-form given "
                     "the instrument constants, so they can be re-derived on every "
                     "push -- but a cheap CI variant of a script that WRITES results "
                     "clobbers them, which is a mistake we already made once with "
                     "gate_partition_certificate.py.")
ap.add_argument("--seed", type=int, default=31337)
args = ap.parse_args()


def leftmost_trajectory(env):
    """x_min(t): the leftmost position reachable at each step. Pushing left
    throughout is optimal because x_t is affine in the actions with all
    coefficients positive -- see the module docstring."""
    x, v = -env.x0_range, 0.0
    out = [x]
    for _ in range(env.h_episode):
        v = v + (-env.gain * env.a_max - env.drag * v) * env.dt
        x = x + v * env.dt
        out.append(x)
    return out


def proved_upper(env):
    """A ceiling on the realized return of ANY policy from ANY admissible x_0."""
    xs = leftmost_trajectory(env)
    right_cap = env.a_right / (1 + math.exp((env.x_right - env.x_wall) / env.width))
    total = 0.0
    for t in range(1, env.h_episode + 1):
        left = env.a_left / (1 + math.exp((xs[t] - env.x_left) / env.width))
        total += left + right_cap
    return total, right_cap, xs[env.h_episode]


def proved_lower(env, grid=200_000):
    """T * min r over the reachable range: an explicit positive floor."""
    lo, hi = leftmost_trajectory(env)[-1], env.x_wall
    best, argbest = float("inf"), None
    for i in range(grid + 1):
        x = lo + (hi - lo) * i / grid
        r = env.reward((x, 0.0))
        if r < best:
            best, argbest = r, x
    return env.h_episode * best, best, argbest


def oracle_best(env, n):
    """Try hard to beat the ceiling: bang-bang, constants, single switches, and
    random block policies. A violation here means the monotonicity argument is
    wrong, which is exactly the failure a derivation like this invites."""
    rng = random.Random(args.seed)
    best = -float("inf")

    def run(actions, x0):
        s, tot = (x0, 0.0), 0.0
        for a in actions:
            s, r, _ = env.step(s, a)
            tot += r
        return tot

    T, A = env.h_episode, env.a_max
    x0s = [-env.x0_range, -env.x0_range / 2, 0.0, env.x0_range]
    cands = [[-A] * T, [A] * T, [0.0] * T]
    for k in range(0, T + 1, 4):                      # single switch
        cands.append([A] * k + [-A] * (T - k))
        cands.append([-A] * k + [A] * (T - k))
    for _ in range(n):                                 # random blocks
        blk = rng.choice([1, 2, 5, 10, 20])
        seq = []
        while len(seq) < T:
            seq += [rng.uniform(-A, A)] * blk
        cands.append(seq[:T])
    for acts in cands:
        for x0 in x0s:
            best = max(best, run(acts, x0))
    return best


rows = []
print(f"{'x_wall':>7} {'J_max proved':>13} {'oracle best':>12} {'slack':>7} "
      f"{'right cap':>10} {'J_min proved':>13} {'argmin x':>9}")
for xw in args.walls:
    env = CartWall(x_wall=xw)
    ub, right_cap, xend = proved_upper(env)
    lb, rmin, xstar = proved_lower(env)
    ob = oracle_best(env, args.oracle_policies)
    ok = ob <= ub + 1e-9
    rows.append({"x_wall": xw, "J_max_proved": ub, "oracle_best": ob,
                 "oracle_within_bound": bool(ok), "slack_ratio": ub / ob,
                 "right_plateau_cap": right_cap, "leftmost_reachable": xend,
                 "J_min_proved": lb, "min_reward": rmin, "argmin_x": xstar})
    print(f"{xw:7.1f} {ub:13.4f} {ob:12.4f} {ub/ob:7.4f} {right_cap:10.3g} "
          f"{lb:13.4g} {xstar:9.2f}"
          f"{'' if ok else '   <-- ORACLE BEATS THE BOUND'}")

# the corollary, with nothing measured in the ceiling
J_TRUTH, J_RAND = 17.7722, 0.5343
_r8 = [r for r in rows if r["x_wall"] == 8.0]
if _r8:
    r8 = _r8[0]
    proved = (r8["J_max_proved"] - r8["J_min_proved"]) / (J_TRUTH - J_RAND)
    print(f"\nplay_cost ceiling at x_wall = 8, with both normalisers DERIVED:")
    print(f"  (J_max - J_min)/(J_truth - J_rand) = "
          f"({r8['J_max_proved']:.4f} - {r8['J_min_proved']:.3g})/"
          f"({J_TRUTH} - {J_RAND}) = {proved:.4f}")
    print(f"  measured play_cost 1.0310 sits at {100*1.0310/proved:.1f}% of it")
    print(f"  (the measured-supremum version of the same ceiling was 1.0445; the")
    print(f"   derived one is only {proved/1.0445:.4f}x weaker, so proving it costs")
    print(f"   almost nothing)")

print(f"\nOracle: {sum(r['oracle_within_bound'] for r in rows)}/{len(rows)} knobs "
      f"with no policy exceeding the derived ceiling.")

# --- what CAN be derived about the pinning, and what cannot -------------------
# contact = 1.00 at every knob is measured. Two of the three things it rests on are
# structural and computed here; the third is not derivable and we say so.
def pinning_structure(env):
    """(i) steps to reach the wall under full right thrust -- x_t is affine in the
    actions with positive coefficients, so pushing right is optimal and this is the
    EARLIEST possible contact from the least favourable start; (ii) the imagined
    returns the blind model offers for going right versus left over the planning
    horizon, which is the asymmetry that makes right the argmax."""
    from cwm.continuous.envs import blind_of
    x, v, reach = env.x0_range, 0.0, None          # least favourable start is +x0
    x, v = -env.x0_range, 0.0
    for t in range(1, env.h_episode + 1):
        v = v + (env.gain * env.a_max - env.drag * v) * env.dt
        x = x + v * env.dt
        if reach is None and x >= env.x_wall:
            reach = t
    blind = blind_of(env)
    H = 40
    out = {}
    for label, a in (("right", env.a_max), ("left", -env.a_max)):
        s, tot = (0.0, 0.0), 0.0
        for _ in range(H):
            s, r, _ = blind.step(s, a)
            tot += r
        out[label] = tot
    return reach, out["right"], out["left"]


print("\nWhat is derivable about the pinning (contact = 1.00 is measured):")
print(f"{'x_wall':>7} {'steps to wall':>14} {'imagined right':>15} "
      f"{'imagined left':>14} {'ratio':>7}")
pin = []
for xw in args.walls:
    env = CartWall(x_wall=xw)
    k, jr, jl = pinning_structure(env)
    pin.append({"x_wall": xw, "steps_to_wall_full_thrust": k,
                "imagined_return_right": jr, "imagined_return_left": jl,
                "asymmetry_ratio": jr / jl})
    print(f"{xw:7.1f} {k:14} {jr:15.3f} {jl:14.3f} {jr/jl:7.2f}")
print("Derivable: the wall is reachable in a small fraction of the horizon, and the")
print("blind model offers a large-plateau return for going right against a small-")
print("plateau return for going left. NOT derivable: that the argmax over 200 random")
print("block candidates executes a positive first action. A candidate set containing")
print("an all-positive-block sequence has probability 1 - (1 - 2^-B)^n_samples, which")
print("is ~1 here, but the argmax's FIRST action is not forced positive by any")
print("argument we have -- a trajectory may go left before turning. So pinning stays")
print("measured, with these two facts explaining rather than proving it.")

out = _REPO / "results" / "play_cost_proved_bounds.json"
if args.verify:
    prev = json.loads(out.read_text())
    ref = {r["x_wall"]: r for r in prev["rows"]}
    bad = [r["x_wall"] for r in rows
           if abs(ref[r["x_wall"]]["J_max_proved"] - r["J_max_proved"]) > 1e-9
           or abs(ref[r["x_wall"]]["J_min_proved"] - r["J_min_proved"]) > 1e-15
           or not r["oracle_within_bound"]]
    print(f"\n[--verify] derived bounds vs the versioned JSON: "
          f"{'MATCH' if not bad else 'MISMATCH at ' + str(bad)}")
    sys.exit(1 if bad else 0)
out.write_text(json.dumps({"script": "play_cost_proved_bounds.py",
                           "params": vars(args), "J_truth": J_TRUTH,
                           "J_rand": J_RAND, "rows": rows,
                           "pinning_structure": pin}, indent=2))
print(f"\nwrote {out}")
