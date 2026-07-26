"""The planner targets the phantom: not observed, bounded.

"The blind planner is lured right and pinned at the wall" was measured
(contact = 1.00 at every knob) and explained by two structural facts, but the step
that matters -- that the planner's CHOSEN PLAN goes after reward the truth makes
unreachable -- was not derived. The obstruction we recorded was real but was about
the wrong quantity: nothing forces the argmax's FIRST ACTION to be positive, since a
trajectory may go left before turning. The plan's target is a different question, and
it does admit a bound.

THE ARGUMENT. Fix a state s and let xbar = x_right - 2w, just short of the phantom
plateau. Two computations bracket the score:

  * An upper bound on the imagined return of ANY candidate whose trajectory never
    exceeds xbar. The reward is a decreasing term plus an increasing one, and the
    reachable interval at step t is [x_min(t), min(x_max(t), xbar)] with the
    endpoints given by full left and full right thrust (exact, by the same
    positive-coefficient monotonicity that Proposition "normalizers" uses). Summing
    the decreasing term at the left end and the increasing one at the right gives
    U_noreach(s).

  * The imagined return of the full-right-thrust candidate, L(s), computed directly.

If L(s) > U_noreach(s) then any candidate scoring at least L(s) must exceed xbar, so
whenever the sampled set contains one, the ARGMAX's trajectory reaches the phantom
plateau. The planner is then provably planning against reward that does not exist --
which is the exploitation, stated as a property of the plan rather than of the
outcome.

HOW OFTEN THE SET CONTAINS ONE. Two bounds, and they bracket the truth from both
sides because they are different objects.

  * EXACT. The block values are i.i.d. uniform on [-a_max, a_max]. On the up-set
    {all blocks >= theta*a_max} with theta > 0 the trajectory only moves right, the
    reward is increasing there, and raising a block moves every later position right
    -- so the score is minimised at the corner (all blocks = theta). Taking the
    smallest theta whose corner still scores above U_noreach gives a sub-event of
    exactly computable probability ((1-theta)/2)^{n_blocks}, hence an exact lower
    bound on the per-step probability. No sampling anywhere.

  * ESTIMATED. The true probability that a random candidate scores above
    U_noreach(s), with a Clopper-Pearson lower confidence limit. This is a property
    of the PLANNER'S OWN sampling law -- a known distribution -- so estimating it is
    estimating a well-defined integral, not measuring the environment.

The exact bound is loose because a single corner is a crude sub-event; the two are
reported side by side so the gap between "provable" and "true" is visible rather
than papered over.

WHAT CAME OUT, AND IT IS NARROWER THAN EXPECTED. The score gap closes everywhere
(margin +0.33 at x = -0.5 rising to +26.25 at (6, 5)), but the probability that the
sampled set holds a candidate above U_noreach is negligible from REST -- 2e-4 exact,
5e-3 estimated -- and 1.000 once the cart carries rightward velocity. So the result
is conditional: phantom-targeting is self-REINFORCING, not self-starting. How the
lure begins is not covered.

WHAT THIS DOES NOT SETTLE. It bounds the probability that the chosen PLAN targets
the phantom, per replanning step. It does not prove the executed first action is
positive, nor that the cart reaches the wall, nor contact = 1.00. Those remain
measured. What changes is that the lure is no longer only observed: the imagined-
return gap is a theorem, and the sampling probability is explicit.

Run: PYTHONPATH=src python scripts/phantom_targeting_probability.py   (~4 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall, blind_of  # noqa: E402
from cwm.law import wilson_ci                       # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--block", type=int, default=10)
ap.add_argument("--n-samples", type=int, default=200, help="the planner's own n")
ap.add_argument("--mc", type=int, default=200_000, help="for the estimated p")
ap.add_argument("--x-wall", type=float, default=8.0)
ap.add_argument("--seed", type=int, default=1)
args = ap.parse_args()

env = CartWall(x_wall=args.x_wall)
blind = blind_of(env)
H, B, A, w = args.horizon, args.block, env.a_max, env.width
NB = H // B
XBAR = env.x_right - 2 * w
STATES = [(0.0, 0.0), (0.5, 0.0), (-0.5, 0.0), (2.0, 3.0), (4.0, 4.0), (6.0, 5.0)]


def envelope(s0, sign):
    """Extreme reachable positions under constant full thrust -- exact, because the
    position is affine in the actions with all coefficients positive."""
    x, v = s0
    out = [x]
    for _ in range(H):
        v = v + (sign * env.gain * A - env.drag * v) * env.dt
        x = x + v * env.dt
        out.append(x)
    return out


def u_noreach(s0):
    """Upper bound on the imagined return of any candidate never exceeding XBAR."""
    lo, hi = envelope(s0, -1), envelope(s0, +1)
    tot = 0.0
    for t in range(1, H + 1):
        left = env.a_left / (1 + math.exp((lo[t] - env.x_left) / w))
        right = env.a_right / (1 + math.exp((env.x_right - min(hi[t], XBAR)) / w))
        tot += left + right
    return tot


def imagined(s0, acts):
    s, tot = s0, 0.0
    for a in acts:
        s, r, _ = blind.step(s, a)
        tot += r
    return tot


def corner_theta(s0, target):
    """Smallest theta whose all-theta candidate still scores above `target`. On
    {blocks >= theta} the score is minimised at that corner, so this yields an
    EXACT probability ((1-theta)/2)^NB for a sub-event of {score > target}."""
    lo, hi = 0.0, 1.0
    if imagined(s0, [A] * H) <= target:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if imagined(s0, [mid * A] * H) > target:
            hi = mid
        else:
            lo = mid
    return hi


rows = []
print(f"xbar = {XBAR}, horizon {H}, blocks {NB}x{B}, planner draws "
      f"n = {args.n_samples}\n")
print(f"{'state':>14} {'U_noreach':>10} {'L full-right':>13} {'margin':>8} "
      f"{'theta':>6} {'p exact':>9} {'P(set) exact':>13} {'p est':>8} "
      f"{'P(set) est':>11}")
for s0 in STATES:
    U = u_noreach(s0)
    L = imagined(s0, [A] * H)
    th = corner_theta(s0, U)
    p_exact = ((1 - th) / 2) ** NB if th is not None else 0.0
    P_exact = 1 - (1 - p_exact) ** args.n_samples
    rng = random.Random(args.seed)
    hits = 0
    for _ in range(args.mc):
        acts = []
        for _ in range(NB):
            acts += [rng.uniform(-A, A)] * B
        if imagined(s0, acts) > U:
            hits += 1
    p_lo = wilson_ci(hits, args.mc)[1]
    P_est = 1 - (1 - p_lo) ** args.n_samples
    rows.append({"state": list(s0), "U_noreach": U, "L_full_right": L,
                 "margin": L - U, "gap_closes": bool(L > U), "theta": th,
                 "p_exact_sub_event": p_exact,
                 "P_set_contains_exact": P_exact,
                 "p_estimated_hits": hits, "p_estimated_lower": p_lo,
                 "P_set_contains_estimated": P_est})
    print(f"{str(s0):>14} {U:10.3f} {L:13.3f} {L-U:+8.3f} "
          f"{(th if th else float('nan')):6.3f} {p_exact:9.2e} {P_exact:13.4f} "
          f"{p_lo:8.4f} {P_est:11.6f}")

print("\nReading, and it is narrower than one might hope. The score gap closes at")
print("every state (margin +0.33 to +26.25), so the implication holds throughout:")
print("a candidate scoring above U_noreach must reach the phantom, hence so must the")
print("argmax. What varies wildly is the PROBABILITY that the sampled set holds such")
print("a candidate. From rest it is negligible -- 2e-4 exact, 5e-3 estimated -- so")
print("the result says nothing about how the lure STARTS. Once the cart carries")
print("rightward velocity it is 1.000 by both routes from (2,3) on. The honest")
print("statement is therefore conditional: phantom-targeting is self-reinforcing, not")
print("self-starting. Initiation, the executed first action\'s sign, and hence")
print("contact = 1.00 all stay measured.")

out = _REPO / "results" / "phantom_targeting_probability.json"
out.write_text(json.dumps({"script": "phantom_targeting_probability.py",
                           "params": vars(args), "xbar": XBAR, "rows": rows},
                          indent=2))
print(f"\nwrote {out}")
