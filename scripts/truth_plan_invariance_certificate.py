"""Certificate: the truth planner's plan is knob-independent over the sweep.

Proposition 8 (play_cost's knob-invariance is an identity) has two hypotheses,
one of which is that the truth planner's return does not depend on the rarity
knob. The paper's evidence for it was bit-identity of J_truth across the sweep.
Bit-identity is strong evidence but it is an observation; this script upgrades it
to a machine-checked certificate over the planner's own candidate set.

The certificate. At a replanning step, a candidate's imagined return under the
truth model depends on the knob ONLY IF its imagined trajectory reaches the
clamp. So if at every knob k and every replanning step

  (C1) the argmax candidate's imagined trajectory stays strictly below the
       SMALLEST wall in the sweep (so its return is the same at every knob), and
  (C2) every candidate that reaches the wall at knob k scores strictly below
       that argmax,

then the argmax is the same candidate at every knob -- it is the maximiser over a
knob-free subset, and every knob-dependent candidate loses -- hence the chosen
action, the realised trajectory and J_truth are identical across knobs. That is a
proof for this instrument and this candidate set, not a regularity.

The same check locates the boundary of the regime: it fails exactly when some
clamping candidate starts winning, which is what happens once the wall no longer
blocks the far plateau.

Run: PYTHONPATH=src python scripts/truth_plan_invariance_certificate.py  (~4 min)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous import mpc                      # noqa: E402
from cwm.continuous.envs import CartWall            # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--walls", type=float, nargs="+",
                default=[2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0],
                help="the sweep; C1 is checked against min(walls)")
ap.add_argument("--extra-walls", type=float, nargs="+",
                default=[11.0, 12.0, 12.5, 13.0],
                help="past the sweep, to locate where the certificate fails")
ap.add_argument("--episodes", type=int, default=20,
                help="match the harness (20), so the certificate covers the runs the\n                     paper reports rather than a 2-episode subset")
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--n-samples", type=int, default=200)
ap.add_argument("--block", type=int, default=10)
args = ap.parse_args()

ALL_WALLS = list(args.walls) + list(args.extra_walls)
WALL_MIN = min(args.walls)


def step_certificate(env, state, rng_seed):
    """(C1, C2, C3, argmax_return, argmax_max_x) at one replanning step.

C1 pins the argmax VALUE to a knob-free subset, but the executed action comes from
    the argmax CANDIDATE, so peer review asked what happens on a tie (2026-07-25).
    We measure it: ties DO occur (the reward saturates to 1.0 on the plateau in
    floating point, so many candidates score identically), which is why the gap is
    not closed by assuming uniqueness. It is closed by the tie-break instead. The
    planner keeps the FIRST maximiser (`if total > best`), the candidate enumeration
    `mpc._candidates(a_max, rng, horizon, n_samples, block)` does not depend on the
    knob, and C2 keeps every clamping candidate strictly below the top --- so the
    first maximiser is the same knob-free candidate at every knob, ties or not.
    C3 is therefore reported as a DIAGNOSTIC (does uniqueness happen to hold?), not
    as a hypothesis the certificate needs."""
    rng = random.Random(rng_seed)
    best, best_maxx, best_clamped = -float("inf"), None, None
    second = -float("inf")
    worst_clamping = -float("inf")
    for acts in mpc._candidates(env.a_max, rng, args.horizon, args.n_samples,
                                args.block):
        s, total, maxx, clamped = state, 0.0, state[0], False
        for a in acts:
            s, r, contact = env.step(s, a)
            total += r
            maxx = max(maxx, s[0])
            clamped |= contact
        if total > best:
            second = best
            best, best_maxx, best_clamped = total, maxx, clamped
        elif total > second:
            second = total
        if clamped:
            worst_clamping = max(worst_clamping, total)
    c1 = (not best_clamped) and best_maxx < WALL_MIN
    c2 = worst_clamping < best          # -inf if nothing clamped: vacuously true
    c3 = second < best                  # the argmax is attained uniquely
    return c1, c2, c3, best, best_maxx, worst_clamping, best - second


rows = []
for xw in ALL_WALLS:
    env = CartWall(x_wall=xw)
    ok_c1 = ok_c2 = ok_c3 = True
    worst_margin = float("inf")
    worst_gap = float("inf")
    argmax_maxx = -float("inf")
    for e in range(args.episodes):
        # replay the truth planner's own realised run, certifying every step
        seed = 1000 * e
        rng = random.Random(seed)
        s = env.initial_state(rng)
        for step in range(env.h_episode):
            c1, c2, c3, best, maxx, worst_clamp, gap = step_certificate(
                env, s, rng_seed=seed * 100_000 + step)
            ok_c1 &= c1
            ok_c2 &= c2
            ok_c3 &= c3
            worst_gap = min(worst_gap, gap)
            argmax_maxx = max(argmax_maxx, maxx)
            if worst_clamp > -float("inf"):
                worst_margin = min(worst_margin, best - worst_clamp)
            a = mpc.plan(env, s, random.Random(seed * 100_000 + step),
                         horizon=args.horizon, n_samples=args.n_samples,
                         block=args.block)
            s, _, _ = env.step(s, a)
    rows.append({"x_wall": xw, "in_sweep": xw in args.walls,
                 "C1_argmax_never_reaches_min_wall": ok_c1,
                 "C2_clamping_candidates_always_lose": ok_c2,
                 "C3_argmax_unique": ok_c3,
                 "min_top_two_gap": (None if worst_gap == float("inf")
                                     else worst_gap),
                 "certificate": bool(ok_c1 and ok_c2),
                 "note_C3": "diagnostic only: ties are broken by the "
                            "knob-independent enumeration order",
                 "argmax_max_x_over_run": argmax_maxx,
                 "min_margin_argmax_minus_best_clamping": (
                     None if worst_margin == float("inf") else worst_margin)})
    print(f"x_wall={xw:5.1f} {'[sweep]' if xw in args.walls else '       '} "
          f"C1={ok_c1!s:5} C2={ok_c2!s:5} C3(diag)={ok_c3!s:5} -> certificate="
          f"{bool(ok_c1 and ok_c2)!s:5}  argmax max x={argmax_maxx:7.3f}  "
          f"margin={rows[-1]['min_margin_argmax_minus_best_clamping']}",
          flush=True)

certified = [r["x_wall"] for r in rows if r["in_sweep"] and r["certificate"]]
failed = [r["x_wall"] for r in rows if not r["certificate"]]
print(f"\ncertified over the sweep: {certified}")
print(f"certificate fails at: {failed or 'nowhere tested'}")
out = _REPO / "results" / "truth_plan_invariance_certificate.json"
out.write_text(json.dumps({"script": "truth_plan_invariance_certificate.py",
                           "params": vars(args), "wall_min": WALL_MIN,
                           "rows": rows}, indent=2))
print(f"wrote {out}")
