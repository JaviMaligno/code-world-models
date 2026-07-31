"""Emit T2's load-bearing measurements that had no committed artifact.

Every number here was quoted in docs/paper3/THEORY.md with no script and no
results/*.json behind it, so a reader could not re-derive it. That is the same
failure class as a hand-computed constant, one level up: the constants emitter
(scripts/t_campaign_constants.py) closed it for CONSTANTS, and this closes it
for the T2 MEASUREMENTS. Emitted here, in one pass over the same MPC harness
`scripts/t2_percontact_identity.py` uses:

  (a) the clean-step chain, both terms:  V_T(tc) - V_T(bc)
        <= [V_T(tc) - V_B(tc)]^+ + Delta_over,  Delta_over := V_B(bc) - V_T(bc)
      and the same chain with the FIRST term dropped, which is the version that
      fails -- so the count for both is reported side by side;
  (b) A_t <= candidate gap, the replanning link that FAILS, with its worst
      violation;
  (c) the straight-at-the-lure arrival comparison: does MPC arrive no later
      than the constant "straight" candidate it beats in value?
  (d) dwell stickiness: does either planner ever leave the basin after
      arriving? A zero here is CENSORED, so its Wilson interval is emitted
      beside it -- a printed 0 is not a guarantee;
  (e) the conditional spread of A_t at ONE step with the imagination data
      pinned exactly, over future planner seeds -- the quantity Prop T2-D says
      no imagination-level bound can beat;
  (f) L_v, the value's Lipschitz constant in velocity, by CRN pairing over K
      future-candidate seeds, with the standard error at each K so that the
      K = 10 estimate's noise (which produced a spurious blow-up) is visible
      rather than asserted.

Resumable: every cell is keyed by (measurement, gap, planner config) and
written as it finishes, so an interrupted run continues where it stopped.
Changing the planner config invalidates old rows rather than silently reusing
them.

  PYTHONPATH=src python scripts/t2_unrecorded_measurements.py
"""
import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys
import time

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

from cwm.continuous.envs import RingField2D, blind_of            # noqa: E402
from cwm.continuous import mpc                                   # noqa: E402

OUT = _REPO / "results" / "t2_unrecorded_measurements.json"

# Same planner as t2_percontact_identity.py: horizon 40 is required for
# imagined paths to reach the phantom at all.
HOR, NS, BLOCK = 40, 48, 10
EPISODES = 6
GAPS = (0.3, 0.6, 1.2)
PLANNER = {"horizon": HOR, "n_samples": NS, "block": BLOCK,
           "seeding": "per (episode, step)"}
t0 = time.time()


def candidates(a_max, ep_seed, t, shift=0):
    """Per-(episode, step) seeded candidate set.

    `shift` perturbs ONLY the planner's future randomness, leaving the
    imagination data at the current step untouched -- that separation is what
    measurement (e) needs.
    """
    rng = random.Random(ep_seed * 100_003 + t + 7_919 * shift)
    return list(mpc._candidates(a_max, rng, HOR, NS, BLOCK, 1))


def rollout_value(env, state, acts):
    s, tot = state, 0.0
    for a in acts:
        s, r, _ = env.step(s, a)
        tot += r
    return tot, s


def argmax_over(env, state, cands):
    """(best value, first action) for `env` over a shared candidate set."""
    best, a0 = -float("inf"), 0.0
    for acts in cands:
        v, _ = rollout_value(env, state, acts)
        if v > best:
            best, a0 = v, acts[0]
    return best, a0


def v_truth(truth, state, ep_seed, t_from, H, shift=0):
    """Return of following pi_T from `state`, with future seeds shifted."""
    s, tot = state, 0.0
    for t in range(t_from, H):
        _, a = argmax_over(truth, s, candidates(truth.a_max, ep_seed, t, shift))
        s, r, _ = truth.step(s, a)
        tot += r
    return tot


def wilson(k, n, z=1.96):
    """(lo, hi) -- a printed 0/n means the interval, not a guarantee."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / den), min(1.0, (c + h) / den))


def dirty_steps(truth, blind, ep_seed, H):
    """Blind-executed trajectory, recording every mis-ranked step.

    Returns (dirty, arrival_step, left_basin) where dirty holds one record per
    step at which the blind and truth argmaxes differ, with BOTH models' values
    on BOTH argmax candidates -- so the chain in (a) can be evaluated without a
    second pass.
    """
    s = truth.initial_state(random.Random(ep_seed))
    dirty, arrival, left = [], None, False
    inside = False
    for t in range(H):
        cands = candidates(truth.a_max, ep_seed, t)
        vb_bc, b_t = argmax_over(blind, s, cands)
        vt_tc, tau_t = argmax_over(truth, s, cands)
        if b_t != tau_t:
            # the two models' values on the OTHER's argmax candidate
            bc = next(c for c in cands if c[0] == b_t)
            tc = next(c for c in cands if c[0] == tau_t)
            vt_bc, _ = rollout_value(truth, s, bc)
            vb_tc, _ = rollout_value(blind, s, tc)
            dirty.append({"t": t, "state": list(s), "b": b_t, "tau": tau_t,
                          "V_T_tc": vt_tc, "V_B_tc": vb_tc,
                          "V_B_bc": vb_bc, "V_T_bc": vt_bc})
        s, _, _ = truth.step(s, b_t)
        in_now = truth.in_interior(s[0], s[1])
        if in_now and arrival is None:
            arrival = t
        if inside and not in_now:
            left = True
        inside = in_now
    return dirty, arrival, left


def straight_arrival(truth, ep_seed, H):
    """Arrival step of the constant 'straight at the lure' policy.

    MPC's argmax beats every candidate in its set INCLUDING this one, so if
    value dominance implied arrival dominance, MPC would arrive no later.
    """
    s = truth.initial_state(random.Random(ep_seed))
    cx, cy = truth.center
    for t in range(H):
        # aim the heading straight at the lure: phi = pi*a/a_max
        phi = math.atan2(cy - s[1], cx - s[0])
        a = max(-truth.a_max, min(truth.a_max, phi / math.pi * truth.a_max))
        s, _, _ = truth.step(s, a)
        if truth.in_interior(s[0], s[1]):
            return t
    return None


def measure_gap(gap):
    """Every per-gap measurement in one pass over the episodes."""
    truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    H = truth.h_episode
    both_ok = first_dropped_ok = n_dirty = 0
    link_ok, link_worst = 0, None
    a_terms, mpc_arr, straight_arr, no_later, left_any = [], [], [], 0, 0
    episodes = 0

    for i in range(EPISODES):
        ep_seed = 4000 + 1000 * i
        dirty, arrival, left = dirty_steps(truth, blind, ep_seed, H)
        episodes += 1
        left_any += bool(left)
        s_arr = straight_arrival(truth, ep_seed, H)
        mpc_arr.append(arrival)
        straight_arr.append(s_arr)
        if arrival is not None and s_arr is not None:
            no_later += (arrival <= s_arr)

        for rec in dirty:
            n_dirty += 1
            st = tuple(rec["state"])
            # (a) the chain, with and without the first term
            lhs = rec["V_T_tc"] - rec["V_T_bc"]
            over = rec["V_B_bc"] - rec["V_T_bc"]
            first = max(0.0, rec["V_T_tc"] - rec["V_B_tc"])
            both_ok += (lhs <= first + over + 1e-9)
            first_dropped_ok += (lhs <= over + 1e-9)
            # (b) A_t against the candidate gap
            s_tau, r_tau, _ = truth.step(st, rec["tau"])
            s_b, r_b, _ = truth.step(st, rec["b"])
            a_t = ((r_tau + v_truth(truth, s_tau, ep_seed, rec["t"] + 1, H))
                   - (r_b + v_truth(truth, s_b, ep_seed, rec["t"] + 1, H)))
            a_terms.append(a_t)
            if a_t <= lhs + 1e-9:
                link_ok += 1
            elif link_worst is None or (a_t - lhs) > link_worst["excess"]:
                link_worst = {"gap": gap, "t": rec["t"], "A_t": a_t,
                              "candidate_gap": lhs, "excess": a_t - lhs}
        print(f"  gap={gap} ep={i}: dirty {len(dirty)}, "
              f"mpc arrives {arrival}, straight {s_arr}",
              flush=True)

    return {
        "gap": gap, "episodes": episodes, "planner": PLANNER,
        "n_dirty": n_dirty,
        "chain_both_terms_ok": both_ok,
        "chain_first_term_dropped_ok": first_dropped_ok,
        "replanning_link_ok": link_ok,
        "replanning_link_worst_violation": link_worst,
        "A_t": {"n": len(a_terms),
                "mean": statistics.fmean(a_terms) if a_terms else None,
                "min": min(a_terms, default=None),
                "max": max(a_terms, default=None)},
        "mpc_arrival": mpc_arr, "straight_arrival": straight_arr,
        "mpc_no_later_than_straight": no_later,
        "left_basin_after_arriving": left_any,
    }


def conditional_spread(gap, t_star, n_shifts):
    """(e) A_t's spread over FUTURE planner seeds, imagination data pinned.

    Prop T2-D says A_t is not measurable with respect to the imagination-level
    data; this measures how much room that leaves. The step is chosen as the
    dirty step with Delta_over closest to 0, so that even the bound's slack
    term vanishes and the spread cannot be attributed to it.
    """
    truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    H = truth.h_episode
    best = None
    for i in range(EPISODES):
        ep_seed = 4000 + 1000 * i
        dirty, _, _ = dirty_steps(truth, blind, ep_seed, H)
        for rec in dirty:
            over = abs(rec["V_B_bc"] - rec["V_T_bc"])
            if best is None or over < best[0]:
                best = (over, ep_seed, rec)
    if best is None:
        return None
    over, ep_seed, rec = best
    st = tuple(rec["state"])
    s_tau, r_tau, _ = truth.step(st, rec["tau"])
    s_b, r_b, _ = truth.step(st, rec["b"])
    vals = []
    for k in range(n_shifts):
        a_t = ((r_tau + v_truth(truth, s_tau, ep_seed, rec["t"] + 1, H, k))
               - (r_b + v_truth(truth, s_b, ep_seed, rec["t"] + 1, H, k)))
        vals.append(a_t)
    return {"gap": gap, "t": rec["t"], "ep_seed": ep_seed,
            "n_future_seeds": n_shifts,
            "Delta_over": rec["V_B_bc"] - rec["V_T_bc"],
            "V_T_tc": rec["V_T_tc"], "V_B_tc": rec["V_B_tc"],
            "V_B_bc": rec["V_B_bc"], "V_T_bc": rec["V_T_bc"],
            "A_t_min": min(vals), "A_t_max": max(vals),
            "A_t_spread": max(vals) - min(vals),
            "A_t_mean": statistics.fmean(vals)}


def lipschitz_velocity(gap, Ks):
    """(f) L_v by CRN pairing, reported at each K with its standard error.

    The estimand is E[A_t | s_t, C_t] / ||Delta v||: the two successor states of
    a dirty step differ ONLY in velocity, by gain*dt*|tau - b|, so A_t is a
    value difference across a known velocity separation. Reported at the
    smallest and largest separation available, because the whole point is how
    the ratio behaves as the separation shrinks -- and at K = 10 the standard
    error swamps it, which is why the K = 10 numbers must not be quoted.
    """
    truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
    blind = blind_of(truth)
    H = truth.h_episode
    recs = []
    for i in range(EPISODES):
        ep_seed = 4000 + 1000 * i
        dirty, _, _ = dirty_steps(truth, blind, ep_seed, H)
        for rec in dirty:
            rec["ep_seed"] = ep_seed
            rec["dv"] = truth.gain * truth.dt * abs(rec["tau"] - rec["b"])
            recs.append(rec)
    if not recs:
        return None
    recs.sort(key=lambda r: r["dv"])
    out = []
    for label, rec in (("smallest", recs[0]), ("largest", recs[-1])):
        st = tuple(rec["state"])
        s_tau, r_tau, _ = truth.step(st, rec["tau"])
        s_b, r_b, _ = truth.step(st, rec["b"])
        # CRN: the SAME future seed drives both branches at each k.
        vals = []
        for k in range(max(Ks)):
            a_t = ((r_tau + v_truth(truth, s_tau, rec["ep_seed"],
                                    rec["t"] + 1, H, k))
                   - (r_b + v_truth(truth, s_b, rec["ep_seed"],
                                    rec["t"] + 1, H, k)))
            vals.append(a_t)
        for K in Ks:
            v = vals[:K]
            mean = statistics.fmean(v)
            sd = statistics.stdev(v) if len(v) > 1 else float("nan")
            se = sd / math.sqrt(len(v)) if len(v) > 1 else float("nan")
            out.append({"which": label, "gap": gap, "t": rec["t"],
                        "dv": rec["dv"], "K": K,
                        "E_A_given_s_C": mean, "stderr": se,
                        "L_v_estimate": mean / rec["dv"] if rec["dv"] else None,
                        "L_v_stderr": se / rec["dv"] if rec["dv"] else None})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--future-seeds", type=int, default=40,
                    help="planner seeds for the conditional-spread cell")
    ap.add_argument("--lv-K", type=int, nargs="*", default=[10, 40, 100],
                    help="CRN sample sizes to report L_v at")
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {}
    # Changing the planner invalidates cached cells rather than reusing them.
    if state.get("planner") != PLANNER:
        state = {"planner": PLANNER}
    cells = state.setdefault("cells", {})

    for gap in GAPS:
        key = f"per_gap|{gap}"
        if key not in cells:
            print(f"per-gap measurements, gap={gap}", flush=True)
            cells[key] = measure_gap(gap)
            OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    key = f"conditional_spread|0.6|{args.future_seeds}"
    if key not in cells:
        print(f"conditional spread at gap=0.6 over {args.future_seeds} "
              f"future seeds", flush=True)
        cells[key] = conditional_spread(0.6, None, args.future_seeds)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    key = f"L_v|0.6|{'-'.join(map(str, args.lv_K))}"
    if key not in cells:
        print(f"L_v by CRN pairing at K={args.lv_K}", flush=True)
        cells[key] = lipschitz_velocity(0.6, args.lv_K)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    # Pool the per-gap counts: the unit is the DIRTY STEP for (a)/(b) and the
    # EPISODE for (c)/(d), and mixing them is how a count gets inflated.
    per_gap = [v for k, v in cells.items() if k.startswith("per_gap|")]
    nd = sum(r["n_dirty"] for r in per_gap)
    ne = sum(r["episodes"] for r in per_gap)
    n_pairs = sum(sum(1 for a, b in zip(r["mpc_arrival"], r["straight_arrival"])
                      if a is not None and b is not None) for r in per_gap)
    left = sum(r["left_basin_after_arriving"] for r in per_gap)
    summary = {
        "unit_for_chain_and_link": "dirty step",
        "unit_for_arrival_and_stickiness": "episode",
        "n_dirty_steps": nd, "n_episodes": ne,
        "chain_both_terms": f"{sum(r['chain_both_terms_ok'] for r in per_gap)}/{nd}",
        "chain_first_term_dropped":
            f"{sum(r['chain_first_term_dropped_ok'] for r in per_gap)}/{nd}",
        "replanning_link": f"{sum(r['replanning_link_ok'] for r in per_gap)}/{nd}",
        "replanning_link_worst": max(
            (r["replanning_link_worst_violation"] for r in per_gap
             if r["replanning_link_worst_violation"]),
            key=lambda w: w["excess"], default=None),
        "mpc_no_later_than_straight":
            f"{sum(r['mpc_no_later_than_straight'] for r in per_gap)}/{n_pairs}",
        "left_basin_after_arriving": f"{left}/{ne}",
        # A censored zero's content is its interval, not the zero.
        "left_basin_wilson_95": wilson(left, ne),
        "mpc_no_later_wilson_95": wilson(
            sum(r["mpc_no_later_than_straight"] for r in per_gap), n_pairs),
    }
    state["summary"] = summary
    OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    print(f"\n--- summary ({time.time() - t0:.0f}s) ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
