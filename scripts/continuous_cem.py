"""Second planner family: CEM vs the certified-blind model.

Measures the other branch of Proposition 3: play_cost <= query-hit mass.
Random shooting (constant candidates) reaches the phantom in imagination and
is exploited (the paper's Tables); CEM's local search never discovers it.
Per knob we report CEM's blind-arm play_cost (expected ~0, knob-invariant),
contact rate, and the imagined boundary-crossing fraction for BOTH planners
on the blind model -- the measured query-hit proxy.

Run: PYTHONPATH=src python scripts/continuous_cem.py   (~30-60 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import statistics
import time

from cwm.continuous.envs import CartWall, PendulumStop, PatchField2D, blind_of
from cwm.continuous import cem, harness, mpc
from cwm.law import t_crit_95

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cart-walls", type=float, nargs="+",
                default=[2.0, 4.0, 6.0, 8.0, 10.0])
ap.add_argument("--pend-stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
ap.add_argument("--instrument", choices=["default", "patch2d"],
                default="default",
                help="'default' reproduces the cart/pendulum CEM rows "
                     "byte-identically; 'patch2d' runs the 2D bi-modal "
                     "instrument's knob pairs into a sibling JSON")
ap.add_argument("--patch2d-knobs", type=float, nargs="+",
                default=[2.0, 6.0, 3.0, 7.0, 4.0, 8.0],
                help="flattened (p1_x, p2_x) pairs, e.g. 2 6 3 7 4 8")
args = ap.parse_args()


def _crossed(s, boundary):
    """boundary is a float (1D instruments: x >= boundary) or a callable
    state -> bool (the 2D instrument's per-patch predicate)."""
    return boundary(s) if callable(boundary) else s[0] >= boundary


def mpc_crossing_frac(model, state, rng, boundary, horizon=40,
                      n_samples=200, block=10):
    """Fraction of random-shooting candidates whose imagined trajectory
    crosses `boundary` (read-only reuse of mpc's candidate generator)."""
    crossed = total = 0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, hit = state, False
        for a in acts:
            s, _, _ = model.step(s, a)
            if _crossed(s, boundary):
                hit = True
        crossed += hit
        total += 1
    return crossed / total


def paired_play_cost_ci(truth_returns, blind_returns, denom):
    """Seed-paired t95 for normalized return loss.

    The common aggregate denominator makes the interval center exactly equal
    to the published ratio-of-means play_cost.
    """
    normalized = [(t - b) / denom for t, b in zip(truth_returns, blind_returns)]
    mean = statistics.mean(normalized)
    if len(normalized) < 2:
        return {"per_seed": normalized, "mean": mean, "t95": None,
                "excludes_zero": None}
    sd = statistics.stdev(normalized)
    se = sd / math.sqrt(len(normalized))
    margin = t_crit_95(len(normalized) - 1) * se
    return {"per_seed": normalized, "mean": mean, "sd": sd, "se": se,
            "t95": [mean - margin, mean + margin],
            "excludes_zero": mean - margin > 0 or mean + margin < 0}


def run_cem_row(inst, knob_repr, truth, blind, boundary, episodes, seed):
    """One CEM/MPC/random row for a (truth, blind) pair, paired over seeds.
    `boundary` is the float or callable predicate passed straight through to
    cem.run_episode / cem.plan_cem / mpc_crossing_frac."""
    t, b, r, xc, xm, per_seed = [], [], [], [], [], []
    for i in range(episodes):
        sd = seed + 1000 * i
        t_ep = cem.run_episode(truth, truth, seed=sd)
        b_ep = cem.run_episode(truth, blind, seed=sd, boundary=boundary)
        r_ep = harness.run_episode(truth, policy="random", seed=sd)
        t.append(t_ep)
        b.append(b_ep)
        r.append(r_ep)

        # Apples-to-apples crossing diagnostic: one plan for each planner
        # from the same paired initial state, with each planner receiving
        # the RNG state immediately after that initial-state draw.
        cem_rng = random.Random(sd)
        cem_s0 = truth.initial_state(cem_rng)
        _, cem_cross = cem.plan_cem(blind, cem_s0, cem_rng, boundary=boundary)
        mpc_rng = random.Random(sd)
        mpc_s0 = truth.initial_state(mpc_rng)
        assert cem_s0 == mpc_s0
        mpc_cross = mpc_crossing_frac(blind, mpc_s0, mpc_rng, boundary)
        xc.append(cem_cross)
        xm.append(mpc_cross)
        per_seed.append({
            "seed": sd,
            "j_truth_cem": t_ep.ret,
            "j_blind_cem": b_ep.ret,
            "j_random": r_ep.ret,
            "blind_contact": b_ep.contact,
            "crossing_frac_cem_initial": cem_cross,
            "crossing_frac_mpc_initial": mpc_cross,
            "crossing_frac_cem_episode": b_ep.crossing_frac,
        })
    j_t, j_b = harness.mean_return(t), harness.mean_return(b)
    j_r = harness.mean_return(r)
    denom = j_t - j_r
    ci = paired_play_cost_ci([e.ret for e in t], [e.ret for e in b], denom)
    point = (j_t - j_b) / denom if denom > 0 else 0.0
    assert math.isclose(point, ci["mean"], abs_tol=1e-12)
    return {
        "instrument": inst, "knob": knob_repr,
        "j_truth_cem": j_t, "j_blind_cem": j_b, "j_random": j_r,
        "play_cost_blind_cem": point,
        "play_cost_blind_cem_paired": ci,
        "blind_contact_rate": sum(e.contact for e in b) / episodes,
        "crossing_scope": "paired_initial_state",
        "crossing_frac_cem_blind": sum(xc) / len(xc),
        "crossing_frac_mpc_blind": sum(xm) / len(xm),
        "crossing_frac_cem_episode_blind":
            sum(e.crossing_frac for e in b) / episodes,
        "n_episodes": episodes,
        "per_seed": per_seed,
    }


def patch2d_predicate(env):
    """Crossing predicate for the 2D bi-modal instrument: True if the
    imagined state falls inside either of TRUTH's patches (env is the truth
    instance, so this still detects the phantom for a blind model whose own
    p1/p2 are None)."""
    return lambda s: env._inside(s[0], s[1], env.p1) or env._inside(s[0], s[1], env.p2)


t0 = time.time()
rows = []
print(f"{'inst':>4} {'knob':>5} {'J_tru':>7} {'J_bli':>7} {'J_rnd':>6} "
      f"{'pc_bli':>7} {'c_bli':>5} {'xing_cem':>8} {'xing_mpc':>8}", flush=True)

if args.instrument == "patch2d":
    ks = args.patch2d_knobs
    knob_pairs = list(zip(ks[0::2], ks[1::2]))
    for k1, k2 in knob_pairs:
        truth = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
        blind = blind_of(truth)
        boundary = patch2d_predicate(truth)
        row = run_cem_row("patch2d", [k1, k2], truth, blind, boundary,
                          args.episodes, args.seed)
        rows.append(row)
        knob_label = f"{k1:.0f}/{k2:.0f}"
        print(f"{'patch2d':>4} {knob_label:>5} {row['j_truth_cem']:7.2f} "
              f"{row['j_blind_cem']:7.2f} {row['j_random']:6.2f} "
              f"{row['play_cost_blind_cem']:7.3f} "
              f"{row['blind_contact_rate']:5.2f} "
              f"{row['crossing_frac_cem_blind']:8.4f} "
              f"{row['crossing_frac_mpc_blind']:8.4f}", flush=True)
    out = pathlib.Path("results/continuous_cem_patch2d.json")
else:
    for inst, knobs, mk in (
            ("cart", args.cart_walls, lambda k: CartWall(x_wall=k)),
            ("pend", args.pend_stops, lambda k: PendulumStop(th_stop=k))):
        for k in knobs:
            truth = mk(k)
            blind = blind_of(truth)
            row = run_cem_row(inst, k, truth, blind, k, args.episodes,
                              args.seed)
            rows.append(row)
            print(f"{inst:>4} {k:5.1f} {row['j_truth_cem']:7.2f} "
                  f"{row['j_blind_cem']:7.2f} {row['j_random']:6.2f} "
                  f"{row['play_cost_blind_cem']:7.3f} "
                  f"{row['blind_contact_rate']:5.2f} "
                  f"{row['crossing_frac_cem_blind']:8.4f} "
                  f"{row['crossing_frac_mpc_blind']:8.4f}", flush=True)
    out = pathlib.Path("results/continuous_cem.json")

out.write_text(json.dumps({"script": "continuous_cem.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
