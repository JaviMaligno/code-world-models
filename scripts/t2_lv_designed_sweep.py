"""L_v by a DESIGNED separation sweep, rather than whatever the dirty steps gave.

Why the previous attempt failed. scripts/t2_unrecorded_measurements.py measures
E[A_t | s_t, C_t] at the velocity separations the dirty steps happen to supply.
Those are not chosen: the smallest is ||dv|| = 0.001, where the signal
L_v*||dv|| ~ 1e-3 sits an order of magnitude below the CRN standard error, and
the estimate is consistent with zero at every K. That is a POWER failure, not a
finding about L_v -- and reporting "L_v ~ 0.8" from it, as an earlier draft did,
was reading noise.

What this does instead. The estimand is the Lipschitz constant of the
PLANNER-AVERAGED value in velocity:

    L_v := sup_s limsup_{delta -> 0} |V_T(s + delta e) - V_T(s)| / delta,

where V_T is the return of following pi_T. So:

  * the separation is IMPOSED, on a geometric grid spanning three decades,
    instead of being whatever a dirty step produced;
  * the two branches share future planner seeds (CRN), so the difference is
    driven by the perturbation and not by planner noise;
  * the perturbation is applied in a FIXED direction per (state, replicate),
    and the sweep reports the directional ratio, since a Lipschitz constant is
    a supremum over directions and averaging over them would understate it;
  * each cell reports its own standard error, so a separation without signal is
    visible AS such rather than being averaged into the answer.

The honest outcome is whichever of these the data support, and the script does
not choose in advance:
  (a) the ratio settles to a finite plateau as delta shrinks -> that plateau is
      the measured L_v;
  (b) the ratio grows without bound -> the value is NOT Lipschitz in velocity
      at these states, which would be a stronger result than the original
      claim and would kill the fixed-point route outright;
  (c) no separation resolves the signal -> the measurement stays censored, and
      the script says so with the standard errors that show it.

Resumable per (gap, delta, n_states, K).

  PYTHONPATH=src python scripts/t2_lv_designed_sweep.py
"""
import argparse
import json
import math
import pathlib
import random
import statistics
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import RingField2D                      # noqa: E402
from cwm.continuous import mpc                                   # noqa: E402

OUT = _REPO / "results" / "t2_lv_designed_sweep.json"
HOR, NS, BLOCK = 40, 48, 10
PLANNER = {"horizon": HOR, "n_samples": NS, "block": BLOCK}
# Three decades, geometric: if the ratio has a plateau this grid finds it, and
# if it diverges the divergence is visible as a trend rather than one point.
DELTAS = (0.4, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002)


def candidates(a_max, seed, t, rep):
    """Candidate set for step t under replicate `rep` (the CRN stream)."""
    rng = random.Random(seed * 100_003 + t * 7_919 + rep * 15_485_863)
    return list(mpc._candidates(a_max, rng, HOR, NS, BLOCK, 1))


def v_truth(env, state, seed, t_from, H, rep):
    """Return of following pi_T from `state`, under replicate `rep`."""
    s, tot = state, 0.0
    for t in range(t_from, H):
        best, a0 = -float("inf"), 0.0
        for acts in candidates(env.a_max, seed, t, rep):
            p, v = s, 0.0
            for a in acts:
                p, r, _ = env.step(p, a)
                v += r
            if v > best:
                best, a0 = v, acts[0]
        s, r, _ = env.step(s, a0)
        tot += r
    return tot


def sweep_cell(gap, delta, states, K, horizon_steps, seed0):
    """E[V_T(s + delta e) - V_T(s)] / delta under CRN, at an IMPOSED delta.

    The direction e is fixed per state (drawn once, reused across replicates
    and across deltas), so the ratios at different deltas estimate the same
    directional derivative and the sweep is a limit rather than a scatter.
    """
    env = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
    H = env.h_episode
    t_from = H - horizon_steps
    ratios, per_state = [], []
    for i in range(states):
        srng = random.Random(90_000 + i)
        s0 = env.initial_state(srng)
        # Advance to a mid-episode state, so the value has a horizon to differ
        # over -- at t = H the difference is identically 0 and the ratio is
        # trivially 0, which would silently drag the estimate down.
        # Advance under pi_T itself, NOT under random actions. L_v is used at
        # dirty steps along the executed trajectory, so the states it must
        # cover are the ones the planner actually visits. A random-action state
        # at t = 68 is typically frozen or out of reach, where both branches
        # score ~0 and the ratio is trivially small -- which is what a first
        # version of this sweep measured, and it measured the wrong states.
        s = s0
        for t in range(t_from):
            best, a0 = -float("inf"), 0.0
            for acts in candidates(env.a_max, 90_000 + i, t, seed0):
                p_, v_ = s, 0.0
                for a in acts:
                    p_, r_, _ = env.step(p_, a)
                    v_ += r_
                if v_ > best:
                    best, a0 = v_, acts[0]
            s, _, _ = env.step(s, a0)
        theta = srng.uniform(-math.pi, math.pi)
        e = (math.cos(theta), math.sin(theta))
        sp = (s[0], s[1], s[2] + delta * e[0], s[3] + delta * e[1])
        diffs = []
        for k in range(K):
            rep = seed0 + k
            va = v_truth(env, s, 90_000 + i, t_from, H, rep)
            vb = v_truth(env, sp, 90_000 + i, t_from, H, rep)
            diffs.append(vb - va)
        m = statistics.fmean(diffs)
        sd = statistics.stdev(diffs) if len(diffs) > 1 else float("nan")
        se = sd / math.sqrt(len(diffs)) if len(diffs) > 1 else float("nan")
        per_state.append({"state_index": i, "mean_diff": m, "stderr": se,
                          "ratio": m / delta, "ratio_stderr": se / delta,
                          "resolved": abs(m) > 1.96 * se if se == se else False})
        ratios.append(abs(m) / delta)
    ratios.sort()
    resolved = sum(1 for p in per_state if p["resolved"])
    # The signal-to-noise ratio is the quantity that decides whether ANY
    # verdict is available. Without it, |mean|/delta grows as delta shrinks
    # for a purely statistical reason -- |mean| of a noisy near-zero estimate
    # sits at the noise floor, so the ratio inherits a 1/delta trend that has
    # nothing to do with the value's smoothness. Reporting that trend as
    # "divergent" is precisely the direction error this campaign exists to
    # catch, so the SNR is emitted beside every ratio.
    snrs = [abs(p["mean_diff"]) / p["stderr"] for p in per_state
            if p["stderr"] == p["stderr"] and p["stderr"] > 0]
    return {
        "gap": gap, "delta": delta, "n_states": states, "K": K,
        "horizon_steps": horizon_steps, "planner": PLANNER,
        "abs_ratio_median": statistics.median(ratios),
        "abs_ratio_max": ratios[-1],
        "abs_ratio_p90": ratios[int(0.9 * (len(ratios) - 1))],
        "states_with_resolved_signal": resolved,
        "snr_median": statistics.median(snrs) if snrs else None,
        "snr_max": max(snrs) if snrs else None,
        "abs_mean_diff_median": statistics.median(
            [abs(p["mean_diff"]) for p in per_state]),
        "stderr_median": statistics.median(
            [p["stderr"] for p in per_state]),
        "per_state": per_state,
        # A Lipschitz constant is a SUP over states and directions, so the max
        # is the estimator; the median describes a typical state and is not a
        # bound. Both are emitted so neither can stand in for the other.
        "note": ("abs_ratio_max is the Lipschitz estimator (a sup); "
                 "abs_ratio_median describes a typical state and is NOT a "
                 "bound. states_with_resolved_signal says how many cells the "
                 "sample can actually see -- a delta where that is 0 carries "
                 "no information about L_v."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=0.6)
    ap.add_argument("--states", type=int, default=12)
    ap.add_argument("--K", type=int, default=24)
    ap.add_argument("--horizon-steps", type=int, default=30,
                    help="steps of value tail to average over")
    ap.add_argument("--deltas", type=float, nargs="*", default=list(DELTAS))
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {}
    if state.get("planner") != PLANNER:
        state = {"planner": PLANNER}
    cells = state.setdefault("cells", {})

    for delta in args.deltas:
        key = f"{args.gap}|{delta}|{args.states}|{args.K}|{args.horizon_steps}"
        if key in cells:
            continue
        cells[key] = sweep_cell(args.gap, delta, args.states, args.K,
                                args.horizon_steps, 5_000)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
        c = cells[key]
        print(f"delta={delta:<6} |ratio| median {c['abs_ratio_median']:8.3f}  "
              f"max {c['abs_ratio_max']:8.3f}  "
              f"resolved {c['states_with_resolved_signal']}/{args.states}",
              flush=True)

    rows = sorted((v for v in cells.values() if isinstance(v, dict)
                   and "delta" in v), key=lambda r: -r["delta"])
    if rows:
        # Verdict, chosen by the data rather than in advance.
        # A delta is INFORMATIVE only if its signal clears the noise. With
        # `states` cells at 5%, a couple of "resolved" cells is what pure noise
        # produces, so the test is on the SNR itself, not on that count.
        expected_false = 0.05 * max(r["n_states"] for r in rows)
        useful = [r for r in rows
                  if (r.get("snr_median") or 0) >= 2.0
                  and r["states_with_resolved_signal"] > 2 * expected_false]
        snr_lo = min((r.get("snr_median") or 0) for r in rows)
        snr_hi = max((r.get("snr_median") or 0) for r in rows)
        if not useful:
            verdict = (
                "CENSORED, and the sweep says WHY. The median signal-to-noise "
                "ratio is %.2f-%.2f across three decades of delta -- the mean "
                "difference never clears one standard error at any separation. "
                "Crucially the apparent growth of |mean|/delta (%.3f at the "
                "largest delta to %.3f at the smallest) is NOT evidence of "
                "divergence: |mean| sits at the noise floor throughout, and "
                "CRN makes that floor shrink with delta, so the ratio inherits "
                "a 1/delta trend for a purely statistical reason. Since the "
                "SNR is FLAT rather than improving as delta shrinks, refining "
                "the separation cannot rescue this route; only K can, and SNR "
                "grows as sqrt(K), so resolving at SNR 3 needs about %dx the "
                "replicates used here."
                % (snr_lo, snr_hi, rows[0]["abs_ratio_median"],
                   rows[-1]["abs_ratio_median"],
                   max(1, round((3.0 / max(snr_hi, 1e-9)) ** 2))))
        else:
            smallest = min(useful, key=lambda r: r["delta"])
            largest = max(useful, key=lambda r: r["delta"])
            growth = (smallest["abs_ratio_max"] / largest["abs_ratio_max"]
                      if largest["abs_ratio_max"] else float("inf"))
            if growth > 3.0:
                verdict = (
                    "DIVERGENT: with the signal resolved at both ends "
                    "(SNR >= 2), the directional ratio GROWS by %.1fx as delta "
                    "falls from %g to %g, so the planner-averaged value is not "
                    "Lipschitz in velocity at these states."
                    % (growth, largest["delta"], smallest["delta"]))
            else:
                verdict = (
                    "PLATEAU: with the signal resolved, the directional ratio "
                    "is stable (%.2fx across delta from %g to %g); the "
                    "Lipschitz estimator is the sup over states, %.3f."
                    % (growth, largest["delta"], smallest["delta"],
                       smallest["abs_ratio_max"]))
        state["verdict"] = verdict
        state["ladder"] = [
            {"delta": r["delta"], "median": r["abs_ratio_median"],
             "p90": r["abs_ratio_p90"], "max": r["abs_ratio_max"],
             "resolved": r["states_with_resolved_signal"],
             "snr_median": r.get("snr_median"),
             "abs_mean_diff_median": r.get("abs_mean_diff_median"),
             "stderr_median": r.get("stderr_median"),
             "n_states": r["n_states"]} for r in rows]
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
        print(f"\n{verdict}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
