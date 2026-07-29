"""Rarity-matched 1D-PREDICATE ablation for PatchField2D (review point #4).

The paper reads 109/111 repaired 1D clamps vs 0/156 repaired 2D regions as
"repair is geometry-dependent". That contrast changed a dozen things at once
(state dimension, action parametrization, mode count, dynamics, contact
distribution, predicate complexity), so "geometry" is not identified. This
script builds and measures the decisive cheap ablation: keep PatchField2D
EXACTLY as it is -- 4D state, scalar action mapped to a heading, two modes, the
same lodes, the same one-sided contact evidence, the same freeze-at-previous-
position semantics -- and change ONLY the mode predicate's arity, from the
2-coordinate disc  (x2-c)^2 + (y2-c)^2 <= R^2  to the 1-coordinate slab
 |x2 - c| <= W  (`patch_shape="slab"`), with W calibrated so patch-1 contact
rarity under the gate's own random-rollout policy matches the disc's.

Four arms, all at k = (3, 7) unless stated, all measured with the SAME
protocols the disc used (scripts/continuous_patch2d.py):

  disc       reference: patch_shape="disc", R = 1.0, k = (3, 7).
  thin       the literal ablation: k = (3, 7), W calibrated to match the disc's
             patch-1 rarity.
  xmatched   W = R = 1.0, k = (3, 7): the slab whose x-extent is IDENTICAL to
             the disc's, rarity NOT matched (an upper reference point).
  imperm     W = 0.5 (the smallest half-width no single step can jump over,
             since sup|dx| = (gain/drag)*dt = 1.0 = 2W), with k1 calibrated to
             match the disc's patch-1 rarity instead.

Why three slab arms rather than one: a 1-coordinate predicate is a codimension-1
band, so its rarity and its *permeability* are the same knob. Matching rarity at
k1 = 3 forces a thin band that a single integrator step jumps over, and a mode
the planner can step over cannot be exploited -- so `thin` also measures
J_truth/J_blind/J_random/play_cost, exactly so the paper can check (not assume)
that the ablation preserved the exploitation geometry. `imperm` is the opposite
corner: rarity matched with an unjumpable band, at the price that patch 2
becomes unreachable behind it. Each arm additionally reports a direct
permeability measurement (`axis_leak_rate`: the fraction of center-line
crossings that landed with |y2| <= R and yet did NOT trigger the mode).

Every number the paper could quote is written to the output JSON. The run is
checkpointed per unit (atomic temp-file + os.replace) and re-running skips
finished units, so it can be interrupted freely.

No LLM/network calls anywhere: everything is measured against the truth env and
its blind_of() counterpart.

Sampling units, for anyone quoting a number out of this file: every rarity is
over i.i.d. RANDOM ROLLOUTS (n = --rollouts, Wilson 95% intervals; a printed 0 is
a censored zero and its content is the interval), and every play quantity is over
paired MPC EPISODES (n = --episodes, paired seeds across truth/blind/random).
Each arm's calibrated knob is re-measured on a disjoint rollout stream
(`validate`) so the quoted rarity is not the statistic the knob was tuned to.

Run: PYTHONPATH=src python scripts/calibrate_patch2d_slab.py
     [--rollouts 30000] [--search-rollouts 4000] [--episodes 20]
     [--out results/patch2d_slab_calibration.json] [--only UNIT ...]
"""
import argparse
import json
import math
import os
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cwm.continuous import harness                       # noqa: E402
from cwm.continuous.envs import PatchField2D, blind_of   # noqa: E402
from cwm.law import wilson_ci                            # noqa: E402

K1_DISC, K2 = 3.0, 7.0
R_DISC = 1.0
# sup |dx| over one integrator step: velocity is driven to the drag terminal
# speed gain/drag, so |dx| < (gain/drag)*dt; a slab of half-width >= half that
# cannot be jumped over by any single step.
def _step_reach(env) -> float:
    return (env.gain / env.drag) * env.dt


ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--rollouts", type=int, default=30_000,
                help="rollouts for every FINAL rarity measurement")
ap.add_argument("--search-rollouts", type=int, default=4_000,
                help="rollouts per search evaluation (common seed stream, so "
                     "r1(knob) is a deterministic monotone function of the knob "
                     "and the bisection is exact w.r.t. this sample)")
ap.add_argument("--episodes", type=int, default=20,
                help="MPC episodes per play measurement (matches "
                     "scripts/continuous_patch2d.py)")
ap.add_argument("--seed", type=int, default=0, help="play-episode seed base")
ap.add_argument("--eval-seed", type=int, default=200_000,
                help="rollout seed stream for rarity (disjoint from the 50_000 "
                     "stream the committed disc sweep used)")
ap.add_argument("--validate-seed-offset", type=int, default=1_000_000,
                help="offset of the disjoint stream every arm's FINAL knob is "
                     "re-measured on, so the quoted rarity is not the statistic "
                     "the knob was tuned against")
ap.add_argument("--polish-tol", type=float, default=0.006,
                help="if the final |r1 - target| exceeds this, take up to "
                     "--polish-steps secant corrections at full sample size")
ap.add_argument("--polish-steps", type=int, default=2)
ap.add_argument("--out", type=pathlib.Path,
                default=pathlib.Path("results/patch2d_slab_calibration.json"))
ap.add_argument("--only", nargs="*", default=None,
                help="run only these unit names (debugging)")
args = ap.parse_args()


# --- measurement primitives ---------------------------------------------------
def measure(env, n_rollouts: int, seed: int) -> dict:
    """Per-mode contact rarity under the gate's own policy (i.i.d. uniform
    random actions), plus a direct permeability measurement.

    The contact loop mirrors scripts/continuous_patch2d.py::per_mode_rarity
    exactly (contacts read BEFORE stepping, per-rollout booleans), so the disc
    numbers are comparable to the committed sweep. It reads the landing point
    from `env._integrate` and the per-mode contacts from `env._inside` --- which
    is verbatim what `env.contact_modes` computes, just without integrating a
    third time --- so nothing here reimplements the dynamics or the predicate.

    On top of the rarity it counts, per STEP, center-line crossings of each
    patch: a crossing is a step whose integrator landing x lands on the far side
    of the patch's center x from where it started. A crossing that did not
    trigger the mode is a leak; the leak rate restricted to landings with
    |y2| <= R (`axis_leak_rate`) is the quantity that decides whether a mode can
    be walked through by a planner heading straight along the axis."""
    h1 = h2 = h_either = h_both = 0
    cross = [0, 0]
    cross_leak = [0, 0]
    axis_cross = [0, 0]
    axis_leak = [0, 0]
    max_abs_dx = 0.0
    p1, p2 = env.p1, env.p2
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        c1 = c2 = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            x2, y2, _, _ = env._integrate(s, a)
            m1 = env._inside(x2, y2, p1)
            m2 = env._inside(x2, y2, p2)
            dx = x2 - s[0]
            if abs(dx) > max_abs_dx:
                max_abs_dx = abs(dx)
            if p1 is not None and (s[0] - p1[0]) * (x2 - p1[0]) <= 0.0:
                cross[0] += 1
                cross_leak[0] += (not m1)
                if abs(y2 - p1[1]) <= R_DISC:
                    axis_cross[0] += 1
                    axis_leak[0] += (not m1)
            if p2 is not None and (s[0] - p2[0]) * (x2 - p2[0]) <= 0.0:
                cross[1] += 1
                cross_leak[1] += (not m2)
                if abs(y2 - p2[1]) <= R_DISC:
                    axis_cross[1] += 1
                    axis_leak[1] += (not m2)
            c1, c2 = c1 or m1, c2 or m2
            s = env.step(s, a)[0]
        h1 += c1
        h2 += c2
        h_either += (c1 or c2)
        h_both += (c1 and c2)
    r1, r1_lo, r1_hi = wilson_ci(h1, n_rollouts)
    r2, r2_lo, r2_hi = wilson_ci(h2, n_rollouts)
    ru, ru_lo, ru_hi = wilson_ci(h_either, n_rollouts)
    return {
        "n_rollouts": n_rollouts, "seed": seed,
        "hits_p1": h1, "hits_p2": h2, "hits_union": h_either, "hits_both": h_both,
        "r1": r1, "r1_ci": [r1_lo, r1_hi],
        "r2": r2, "r2_ci": [r2_lo, r2_hi],
        "r_union": ru, "r_union_ci": [ru_lo, ru_hi],
        "r_both": h_both / n_rollouts,
        "r_union_indep_approx": 1.0 - (1.0 - r1) * (1.0 - r2),
        "crossings_p1": cross[0], "crossings_p2": cross[1],
        "crossing_leaks_p1": cross_leak[0], "crossing_leaks_p2": cross_leak[1],
        "axis_crossings_p1": axis_cross[0], "axis_crossings_p2": axis_cross[1],
        "axis_leaks_p1": axis_leak[0], "axis_leaks_p2": axis_leak[1],
        "leak_rate_p1": (cross_leak[0] / cross[0]) if cross[0] else None,
        "axis_leak_rate_p1": (axis_leak[0] / axis_cross[0]) if axis_cross[0] else None,
        "axis_leak_rate_p2": (axis_leak[1] / axis_cross[1]) if axis_cross[1] else None,
        "max_abs_dx": max_abs_dx,
        "step_reach_bound": _step_reach(env),
    }


COMMITTED_DISC_PLAY_COST = 1.0058514013550737   # results/continuous_patch2d.json, k=(3,7)


def play(env, n_episodes: int, seed: int) -> dict:
    """The paired truth/blind/random MPC arena.

    This is `harness.play_cost` unrolled over the same `harness.run_episode`
    helper with the same seed schedule (sd = seed + 1000*i) and the same
    planner defaults, so it returns the identical aggregate numbers -- the disc
    arm must reproduce the committed play_cost bit-for-bit, which is asserted in
    the summary (`disc_play_cost_matches_committed`). It is unrolled only so the
    per-episode returns / contacts / final x can be recorded: for a slab thin
    enough to match the disc's rarity, WHERE the blind planner ends up (pinned
    at the mode, or through it and on the phantom lode) is the whole question."""
    blind = blind_of(env)
    t, b, r = [], [], []
    for i in range(n_episodes):
        sd = seed + 1000 * i
        t.append(harness.run_episode(env, env, "mpc", sd))
        b.append(harness.run_episode(env, blind, "mpc", sd))
        r.append(harness.run_episode(env, policy="random", seed=sd))
    j_t, j_b, j_r = (harness.mean_return(t), harness.mean_return(b),
                     harness.mean_return(r))
    denom = j_t - j_r
    out = {
        "j_truth": j_t, "j_blind": j_b, "j_random": j_r,
        "play_cost": (j_t - j_b) / denom if denom > 0 else 0.0,
        "blind_contact_rate": sum(e.contact for e in b) / n_episodes,
        "truth_contact_rate": sum(e.contact for e in t) / n_episodes,
        "n_episodes": n_episodes,
    }
    for tag, eps in (("truth", t), ("blind", b), ("random", r)):
        out[f"episodes_{tag}"] = [
            {"ret": e.ret, "contact": e.contact, "final_x": e.final_state[0],
             "final_y": e.final_state[1]} for e in eps]
    # how often the blind planner ended up east of the mode it does not model
    # (i.e. walked through it) rather than pinned at/behind it
    c1 = env.p1[0] if env.p1 is not None else float("inf")
    out["blind_frac_ended_east_of_p1"] = (
        sum(e.final_state[0] > c1 for e in b) / n_episodes)
    out["truth_frac_ended_east_of_p1"] = (
        sum(e.final_state[0] > c1 for e in t) / n_episodes)
    return out


# --- env factory --------------------------------------------------------------
def env_for(arm: str, knobs: dict):
    if arm == "disc":
        return PatchField2D(p1=(K1_DISC, 0.0), p2=(K2, 0.0), patch_shape="disc")
    if arm == "thin":
        return PatchField2D(p1=(K1_DISC, 0.0), p2=(K2, 0.0), patch_shape="slab",
                            slab_half_width=knobs["W_thin"])
    if arm == "xmatched":
        return PatchField2D(p1=(K1_DISC, 0.0), p2=(K2, 0.0), patch_shape="slab",
                            slab_half_width=R_DISC)
    if arm == "imperm":
        return PatchField2D(p1=(knobs["k1_imperm"], 0.0), p2=(K2, 0.0),
                            patch_shape="slab",
                            slab_half_width=knobs["W_imperm"])
    raise ValueError(arm)


# --- checkpointing ------------------------------------------------------------
def load() -> dict:
    if args.out.exists():
        try:
            return json.loads(args.out.read_text())
        except json.JSONDecodeError:
            print(f"warning: {args.out} unparseable; starting fresh", flush=True)
    return {"script": "calibrate_patch2d_slab.py", "params": {}, "units": {}}


def save(state: dict) -> None:
    state["params"] = {k: (str(v) if isinstance(v, pathlib.Path) else v)
                       for k, v in vars(args).items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(args.out.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=False))
    os.replace(tmp, args.out)


state = load()
UNITS: dict = {}


def unit(name):
    def deco(fn):
        UNITS[name] = fn
        return fn
    return deco


# --- units --------------------------------------------------------------------
@unit("target_search")
def _target_search(st):
    """The matching target, measured on the SEARCH seed stream so the search is
    paired with the reference (identical rollout seeds, so the calibration is
    not chasing the disc's own sampling noise)."""
    env = env_for("disc", {})
    m = measure(env, args.search_rollouts, args.eval_seed)
    return {"arm": "disc", "r1_target_search": m["r1"], "measure": m,
            "committed_disc_r1_at_k37": 0.14166666666666666}


def _search_monotone(eval_r1, grid, target, decreasing: bool, tol=1e-4,
                     max_bisect=20):
    """Grid-then-bisect on a knob whose r1 is monotone. Records every
    evaluation. `decreasing` says whether r1 falls as the knob grows."""
    trace = []

    def ev(v):
        for t in trace:
            if t["knob"] == v:
                return t["r1"]
        r1 = eval_r1(v)
        trace.append({"knob": v, "r1": r1, "stage": _search_monotone.stage})
        print(f"    knob={v:.6f} r1={r1:.4f} (target {target:.4f})", flush=True)
        return r1

    _search_monotone.stage = "grid"
    vals = [(v, ev(v)) for v in grid]
    # bracket: the adjacent grid pair straddling the target
    lo = hi = None
    for (va, ra), (vb, rb) in zip(vals, vals[1:]):
        if (ra - target) * (rb - target) <= 0.0:
            lo, hi = (va, ra), (vb, rb)
            break
    if lo is None:
        best = min(vals, key=lambda t: abs(t[1] - target))
        return {"knob": best[0], "r1_search": best[1], "bracketed": False,
                "trace": trace}
    _search_monotone.stage = "bisect"
    a, b = lo[0], hi[0]
    for _ in range(max_bisect):
        if abs(b - a) <= tol:
            break
        mid = 0.5 * (a + b)
        rm = ev(mid)
        above = (rm > target)
        # want to keep the sub-interval straddling the target
        if decreasing:
            if above:
                a = mid
            else:
                b = mid
        else:
            if above:
                b = mid
            else:
                a = mid
    cand = [t for t in trace if t["stage"] == "bisect"] or trace
    best = min(cand, key=lambda t: abs(t["r1"] - target))
    return {"knob": best["knob"], "r1_search": best["r1"], "bracketed": True,
            "bracket": [a, b], "trace": trace}


@unit("search_thin")
def _search_thin(st):
    """W at k1 = 3.0 matching the disc's patch-1 rarity (r1 is increasing in W:
    the slab of half-width W contains the slab of any smaller half-width)."""
    target = st["units"]["target_search"]["r1_target_search"]
    grid = [0.005, 0.01, 0.02, 0.03, 0.05, 0.12, 0.5, 1.0]

    def eval_r1(W):
        env = PatchField2D(p1=(K1_DISC, 0.0), p2=(K2, 0.0), patch_shape="slab",
                           slab_half_width=W)
        return measure(env, args.search_rollouts, args.eval_seed)["r1"]

    # tol 2e-4 in W is ~8e-4 in r1 near the bracket (slope ~4 per unit W), far
    # below the final 30k-rollout Wilson half-width, so bisecting further only
    # chases the search sample's own noise; the `polish` stage corrects the
    # residual transfer error at full sample size instead.
    res = _search_monotone(eval_r1, grid, target, decreasing=False, tol=2e-4)
    res["W_thin"] = res.pop("knob")
    res["target"] = target
    return res


@unit("search_imperm")
def _search_imperm(st):
    """k1 at W = 0.5 (the smallest unjumpable half-width) matching the disc's
    patch-1 rarity (r1 is decreasing in k1: the slab moves away from the start).
    k1 is capped so slab 1 and slab 2 stay disjoint."""
    target = st["units"]["target_search"]["r1_target_search"]
    W = 0.5 * _step_reach(PatchField2D())
    grid = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5]

    def eval_r1(k1):
        env = PatchField2D(p1=(k1, 0.0), p2=(K2, 0.0), patch_shape="slab",
                           slab_half_width=W)
        return measure(env, args.search_rollouts, args.eval_seed)["r1"]

    # tol 5e-3 in k1 is ~4e-4 in r1 (slope ~0.08 per unit k1) — see search_thin
    res = _search_monotone(eval_r1, grid, target, decreasing=True, tol=5e-3)
    res["k1_imperm"] = res.pop("knob")
    res["W_imperm"] = W
    res["target"] = target
    res["k1_max_disjoint"] = K2 - 2 * W
    return res


def _knobs(st) -> dict:
    """Knobs from whichever searches have finished. Tolerant of a truncated run
    so the arms are independent: `thin`/`xmatched` never need search_imperm and
    vice versa."""
    u = st["units"]
    k = {}
    if "search_thin" in u:
        k["W_thin"] = u["search_thin"]["W_thin"]
    if "search_imperm" in u:
        k["W_imperm"] = u["search_imperm"]["W_imperm"]
        k["k1_imperm"] = u["search_imperm"]["k1_imperm"]
    return k


def _match_target(st) -> tuple:
    """(target r1, where it came from). The like-for-like target is the disc's
    OWN r1 on the full evaluation stream, so both arms are compared at the same
    sample size on the same seeds; the small paired search sample is only the
    fallback for a run that has not measured the disc yet."""
    u = st["units"]
    if "rarity_disc" in u:
        return u["rarity_disc"]["measure"]["r1"], "rarity_disc.measure.r1"
    return (u["target_search"]["r1_target_search"],
            "target_search.r1_target_search")


def _rarity_unit(st, arm, polish_knob=None):
    knobs = _knobs(st)
    target, target_src = _match_target(st)
    env = env_for(arm, knobs)
    m = measure(env, args.rollouts, args.eval_seed)
    out = {"arm": arm, "knobs": dict(knobs), "measure": m, "polish": [],
           "match_target": target, "match_target_source": target_src}
    if polish_knob is None:
        out["validate"] = measure(env, args.rollouts,
                                  args.eval_seed + args.validate_seed_offset)
        return out
    # secant polish at full sample size: only the knob moves, and every attempt
    # (with its own full-size measurement) is recorded.
    prev = (knobs[polish_knob], m["r1"])
    search = st["units"]["search_thin" if polish_knob == "W_thin"
                          else "search_imperm"]
    best = (knobs[polish_knob], m)
    for _ in range(args.polish_steps):
        if abs(best[1]["r1"] - target) <= args.polish_tol:
            break
        tr = sorted(search["trace"], key=lambda t: t["knob"])
        slope = None
        for ta, tb in zip(tr, tr[1:]):
            if (ta["r1"] - target) * (tb["r1"] - target) <= 0.0 and tb["knob"] != ta["knob"]:
                slope = (tb["r1"] - ta["r1"]) / (tb["knob"] - ta["knob"])
                break
        if not slope:
            break
        nxt = prev[0] + (target - prev[1]) / slope
        if nxt <= 0.0 or not math.isfinite(nxt):
            break
        knobs[polish_knob] = nxt
        m2 = measure(env_for(arm, knobs), args.rollouts, args.eval_seed)
        out["polish"].append({"knob": nxt, "r1": m2["r1"]})
        print(f"    polish {polish_knob}={nxt:.6f} r1={m2['r1']:.4f}", flush=True)
        if abs(m2["r1"] - target) < abs(best[1]["r1"] - target):
            best = (nxt, m2)
        prev = (nxt, m2["r1"])
    knobs[polish_knob] = best[0]
    out["knobs"] = dict(knobs)
    out["measure"] = best[1]
    out["knob_final"] = best[0]
    # The knob was tuned against r1 on the evaluation stream, so `measure.r1` is
    # an optimized-on statistic. `validate` re-measures the SAME knob on a
    # disjoint rollout stream at the same size: that is the number to quote when
    # the question is "what is this arm's rarity", while `measure` is the number
    # the matching was done against.
    out["validate"] = measure(env_for(arm, knobs), args.rollouts,
                              args.eval_seed + args.validate_seed_offset)
    return out


def _final_knobs(st) -> dict:
    """The knobs actually used by the final rarity measurements (post-polish)."""
    k = _knobs(st)
    rt = st["units"].get("rarity_thin")
    if rt and "knob_final" in rt:
        k["W_thin"] = rt["knob_final"]
    ri = st["units"].get("rarity_imperm")
    if ri and "knob_final" in ri:
        k["k1_imperm"] = ri["knob_final"]
    return k


def _play_unit(st, arm):
    env = env_for(arm, _final_knobs(st))
    p = play(env, args.episodes, args.seed)
    r = st["units"].get(f"rarity_{arm}", {}).get("measure", {})
    if r:
        p["d40_p1"] = p["play_cost"] * (1 - r["r1"]) ** 40
        p["d40_p2"] = p["play_cost"] * (1 - r["r2"]) ** 40
        p["d40_joint"] = p["play_cost"] * (1 - r["r_union"]) ** 40
    p["arm"] = arm
    p["knobs"] = _final_knobs(st)
    return p


@unit("rarity_disc")
def _rarity_disc(st):
    return _rarity_unit(st, "disc")


@unit("rarity_thin")
def _rarity_thin(st):
    return _rarity_unit(st, "thin", polish_knob="W_thin")


@unit("rarity_xmatched")
def _rarity_xmatched(st):
    return _rarity_unit(st, "xmatched")


@unit("rarity_imperm")
def _rarity_imperm(st):
    return _rarity_unit(st, "imperm", polish_knob="k1_imperm")


@unit("play_disc")
def _play_disc(st):
    return _play_unit(st, "disc")


@unit("play_thin")
def _play_thin(st):
    return _play_unit(st, "thin")


@unit("play_imperm")
def _play_imperm(st):
    return _play_unit(st, "imperm")


@unit("play_xmatched")
def _play_xmatched(st):
    return _play_unit(st, "xmatched")


# Execution order, by DECREASING importance rather than by arm, so a run cut
# short by wall clock still leaves a usable artifact: the disc reference and the
# literal (thin) ablation first -- that pair alone decides whether the ablation
# is admissible -- then the impermeable alternative, then the x-extent-matched
# reference point. Every unit only depends on units listed before it, and the
# summary is built from whatever finished (`units_missing` names the rest).
ORDER = ["target_search", "search_thin",
         "rarity_disc", "rarity_thin", "play_disc", "play_thin",
         "search_imperm", "rarity_imperm", "play_imperm",
         "rarity_xmatched", "play_xmatched"]
assert set(ORDER) == set(UNITS), (set(ORDER) ^ set(UNITS))


# --- driver -------------------------------------------------------------------
t_all = time.time()
for name in ORDER:
    if args.only and name not in args.only:
        continue
    if name in state["units"]:
        print(f"[skip] {name}", flush=True)
        continue
    print(f"[run ] {name}", flush=True)
    t0 = time.time()
    res = UNITS[name](state)
    res["elapsed_s"] = round(time.time() - t0, 1)
    state["units"][name] = res
    save(state)
    print(f"[done] {name}  [{res['elapsed_s']}s]", flush=True)


def _summarize(state: dict) -> dict:
    """The numbers the paper quotes, over whatever arms completed."""
    u = state["units"]
    knobs = _final_knobs(state)
    target, target_src = _match_target(state)
    summary = {
        "k1_disc": K1_DISC, "k2": K2, "R_disc": R_DISC,
        "committed_disc_r1_at_k37": 0.14166666666666666,
        "committed_disc_play_cost": COMMITTED_DISC_PLAY_COST,
        "r1_match_target": target, "r1_match_target_source": target_src,
        "r1_target_paired_search_sample":
            u["target_search"]["r1_target_search"],
        "search_rollouts": args.search_rollouts,
        "final_rollouts": args.rollouts,
        "episodes": args.episodes,
        "calibrated_slab_half_width": knobs.get("W_thin"),
        "imperm_slab_half_width": knobs.get("W_imperm"),
        "imperm_k1": knobs.get("k1_imperm"),
        "step_reach_bound": _step_reach(PatchField2D()),
        "units_done": [n for n in ORDER if n in u],
        "units_missing": [n for n in ORDER if n not in u],
        "arms": {},
    }
    for arm in ("disc", "thin", "xmatched", "imperm"):
        if f"rarity_{arm}" not in u or f"play_{arm}" not in u:
            continue
        m = u[f"rarity_{arm}"]["measure"]
        v = u[f"rarity_{arm}"].get("validate") or {}
        p = u[f"play_{arm}"]
        summary["arms"][arm] = {
            "r1": m["r1"], "r1_ci": m["r1_ci"],
            "r2": m["r2"], "r2_ci": m["r2_ci"],
            "r_union": m["r_union"], "r_union_ci": m["r_union_ci"],
            "r1_validate": v.get("r1"), "r1_validate_ci": v.get("r1_ci"),
            "r2_validate": v.get("r2"), "r2_validate_ci": v.get("r2_ci"),
            "r_union_validate": v.get("r_union"),
            "r_union_validate_ci": v.get("r_union_ci"),
            "r1_minus_target": m["r1"] - target,
            "axis_leak_rate_p1": m["axis_leak_rate_p1"],
            "leak_rate_p1": m["leak_rate_p1"],
            "max_abs_dx": m["max_abs_dx"],
            "j_truth": p["j_truth"], "j_blind": p["j_blind"],
            "j_random": p["j_random"], "play_cost": p["play_cost"],
            "blind_contact_rate": p["blind_contact_rate"],
            "truth_contact_rate": p["truth_contact_rate"],
            "d40_p1": p.get("d40_p1"), "d40_joint": p.get("d40_joint"),
            "blind_frac_ended_east_of_p1": p["blind_frac_ended_east_of_p1"],
            "truth_frac_ended_east_of_p1": p["truth_frac_ended_east_of_p1"],
        }
    a = summary["arms"]
    if "disc" in a:
        summary["disc_play_cost_matches_committed"] = (
            a["disc"]["play_cost"] == COMMITTED_DISC_PLAY_COST)
    def _r1_for_verdict(arm):
        """Judge the match on the DISJOINT validation stream when it exists: the
        tuned arms' `r1` there is not the statistic their knob was fitted to."""
        return a[arm]["r1_validate"] if a[arm].get("r1_validate") is not None \
            else a[arm]["r1"]

    verdict = {"basis": ("r1_validate (disjoint stream)"
                         if a and "disc" in a
                         and a["disc"].get("r1_validate") is not None
                         else "r1 (tuning stream)")}
    for arm in ("thin", "imperm", "xmatched"):
        if arm in a and "disc" in a:
            # "admissible" = the ablation changed the predicate's arity WITHOUT
            # changing what makes the instrument dangerous: rarity within one
            # point of the disc's AND at least half its normalized regret.
            verdict[f"rarity_matched_{arm}"] = \
                abs(_r1_for_verdict(arm) - _r1_for_verdict("disc")) <= 0.01
            verdict[f"danger_preserved_{arm}"] = \
                a[arm]["play_cost"] >= 0.5 * a["disc"]["play_cost"]
            verdict[f"admissible_{arm}"] = (
                verdict[f"rarity_matched_{arm}"]
                and verdict[f"danger_preserved_{arm}"])
        if arm in a:
            verdict[f"p2_reachable_{arm}"] = a[arm]["r2"] > 0.0
    if "disc" in a:
        verdict["p2_reachable_disc"] = a["disc"]["r2"] > 0.0
    summary["verdict"] = verdict
    return summary


if "target_search" in state["units"]:
    state["summary"] = _summarize(state)
    state["elapsed_s"] = round(time.time() - t_all, 1)
    save(state)
    print(json.dumps(state["summary"], indent=2))
print(f"wrote {args.out}", flush=True)
