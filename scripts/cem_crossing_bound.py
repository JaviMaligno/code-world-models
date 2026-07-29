"""Review point #7: the CEM "crossing = 0.0000" cells are CENSORED zeros.

Table tab:cem reports the CEM planner's imagined boundary-crossing fraction on
20 plans per row (one plan per episode seed from the paired initial state) =
20 x 5 iterations x 64 samples = 6400 imagined trajectories per row. Two cart
rows (x_wall = 8, 10) print 0.0000 there, and the paper then reads that as an
EXACT zero ("mu_query = 0 forces play_cost = 0"), which its own censored-zero
convention forbids. This script replaces the reading with a measurement: the
same planner, the same crossing definition, two orders of magnitude more
sampled imagined trajectories, and an interval instead of a point.

Two scopes are measured, both reusing `cwm.continuous.cem.plan_cem` unmodified
(so the planner configuration is by construction the one tab:cem used):

  scope "initial_state" -- tab:cem's own definition, extended. Plan p uses
      rng = random.Random(1000*p), draws the initial state from it, then plans
      once. Plans p = 0..19 are BIT-IDENTICAL to the 20 plans behind the
      published column (scripts/continuous_cem.py uses the same seeds
      sd = 1000*i and the same rng discipline), which is checked against
      results/continuous_cem.json and recorded under "validation".

  scope "episode" -- the whole episode's planning, which is what mu_query(E) is
      actually about. A full CEM episode on the blind model in truth makes
      h_episode = 80 plans, so 80 x 320 = 25600 imagined trajectories, and the
      episode either does or does not contain at least one crossing. That gives
      a DIRECT Clopper-Pearson bound on mu_query(E) with no independence
      assumption at all, alongside the per-trajectory bound.

Reported per row: trajectories examined, crossings observed, a one-sided
Clopper-Pearson 95% UPPER bound on the per-trajectory crossing probability p
(Wilson upper reported alongside for reference), and the implied upper bound on
mu_query(E) for one episode. x_wall = 6 is the resolved control: its crossing
probability is nonzero and small, so it shows the estimator can see rare
crossings at this sample size.

Resumable: every unit (one initial-state chunk, or one episode) is checkpointed
into results/cem_crossing_bound.json by atomic replace, and a rerun skips the
units already there. --deadline-s stops cleanly and keeps everything finished
so far; rerun to extend.

Run: PYTHONPATH=src python scripts/cem_crossing_bound.py \
         --workers 4 --deadline-s 5400
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import time

from cwm.continuous import cem
from cwm.continuous.envs import CartWall, blind_of

OUT = pathlib.Path("results/cem_crossing_bound.json")
PUBLISHED = pathlib.Path("results/continuous_cem.json")

# tab:cem's sample: 20 plans/row in the "initial_state" scope.
PUBLISHED_PLANS_PER_ROW = 20

# ----------------------------------------------------------------------------
# exact binomial interval helpers (no scipy in this environment)
# ----------------------------------------------------------------------------


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Bin(n, p), summed in log space (n here is millions)."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    ln_n1 = math.lgamma(n + 1)
    total = 0.0
    for i in range(k + 1):
        lt = (ln_n1 - math.lgamma(i + 1) - math.lgamma(n - i + 1)
              + i * lp + (n - i) * lq)
        if lt > -745.0:
            total += math.exp(lt)
    return min(1.0, total)


def _bisect(f, lo: float, hi: float, iters: int = 200) -> float:
    """Root of a monotone f on [lo, hi] (f(lo) and f(hi) straddle 0)."""
    flo = f(lo)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0.0) == (flo > 0.0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact (Clopper-Pearson) 100(1-alpha)% UPPER bound on p.

    Solves P(X <= k | n, p) = alpha. For k = 0 this is the closed form
    1 - alpha**(1/n); the test suite checks the bisection against it.
    """
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    return _bisect(lambda p: binom_cdf(k, n, p) - alpha, k / n, 1.0)


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact 100(1-alpha)% LOWER bound: solves P(X >= k) = alpha."""
    if k <= 0:
        return 0.0
    return _bisect(lambda p: (1.0 - binom_cdf(k - 1, n, p)) - alpha, 0.0, k / n)


def clopper_pearson_interval(k: int, n: int, conf: float = 0.95) -> dict:
    """Two-sided exact 100*conf% interval (equal-tailed)."""
    a = (1.0 - conf) / 2.0
    return {"k": k, "n": n, "point": (k / n) if n else None,
            "lo": clopper_pearson_lower(k, n, a),
            "hi": clopper_pearson_upper(k, n, a),
            "conf": conf, "method": "Clopper-Pearson (exact, equal-tailed)"}


def wilson_upper(k: int, n: int, z: float = 1.959963984540054) -> float:
    """Upper end of the two-sided Wilson score interval (for reference)."""
    if n <= 0:
        return 1.0
    ph = k / n
    d = 1.0 + z * z / n
    c = ph + z * z / (2 * n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return min(1.0, (c + h) / d)


# ----------------------------------------------------------------------------
# rows, planner config, units
# ----------------------------------------------------------------------------


def row_key(x_wall: float) -> str:
    return f"cart_xwall{x_wall:g}"


def make_row(x_wall: float):
    """(truth, blind, boundary) exactly as scripts/continuous_cem.py builds
    them for a cart row: boundary is the float x_wall (crossing means x >=)."""
    truth = CartWall(x_wall=x_wall)
    return truth, blind_of(truth), x_wall


def planner_config() -> dict:
    """The default plan_cem signature -- read, not restated, so this record
    cannot drift from the planner tab:cem used."""
    import inspect
    sig = inspect.signature(cem.plan_cem)
    cfg = {name: prm.default for name, prm in sig.parameters.items()
           if prm.default is not inspect.Parameter.empty and name != "boundary"}
    cfg["n_trajectories_per_plan"] = cfg["n_iters"] * cfg["n_samples"]
    return cfg


def _count_from_frac(frac: float, n_traj: int) -> int:
    """plan_cem returns crossed/total_samples with total_samples exactly
    n_iters*n_samples, so the integer count is recoverable exactly."""
    k = round(frac * n_traj)
    assert abs(frac * n_traj - k) < 1e-6, (frac, n_traj)
    return k


def initial_scope_counts(truth, blind, boundary, p_lo: int, p_hi: int,
                         n_per_plan: int) -> dict:
    """tab:cem's own scope: one plan per seed from that seed's initial state.
    Plan p uses rng = random.Random(1000*p) and draws the initial state from it
    -- the rng discipline of scripts/continuous_cem.py, so p = 0..19 are the
    published 20 plans."""
    crossings = plans = 0
    per_plan = []
    for p in range(p_lo, p_hi):
        rng = random.Random(1000 * p)
        s0 = truth.initial_state(rng)
        _, frac = cem.plan_cem(blind, s0, rng, boundary=boundary)
        k = _count_from_frac(frac, n_per_plan)
        crossings += k
        plans += 1
        per_plan.append(k)
    return {"plans": plans, "trajectories": plans * n_per_plan,
            "crossings": crossings,
            "plans_with_crossing": sum(1 for k in per_plan if k),
            # which plan seeds crossed: what makes a "0.0000" cell's few
            # crossings locatable and reproducible instead of anecdotal
            "crossing_plan_seeds": [1000 * (p_lo + j)
                                    for j, k in enumerate(per_plan) if k],
            "crossing_plan_counts": [k for k in per_plan if k],
            "first_plan_fracs": [k / n_per_plan for k in per_plan[:20]]}


def episode_scope_counts(truth, blind, boundary, seed: int,
                         n_per_plan: int) -> dict:
    """One full blind-model CEM episode in `truth`, with INTEGER crossing
    counts over every plan of the episode. Mirrors cem.run_episode exactly
    (which returns only the mean fraction); `replay_check` asserts that."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    crossings = plans = 0
    fracs = []
    ret, contact = 0.0, False
    for _ in range(truth.h_episode):
        a, frac = cem.plan_cem(blind, s, rng, boundary=boundary)
        fracs.append(frac)
        crossings += _count_from_frac(frac, n_per_plan)
        plans += 1
        s, r, c = truth.step(s, a)
        ret += r
        contact = contact or c
    return {"plans": plans, "trajectories": plans * n_per_plan,
            "crossings": crossings, "episode_has_crossing": crossings > 0,
            "crossing_frac_mean_over_plans": sum(fracs) / len(fracs),
            "ret": ret, "contact": contact, "seed": seed}


def replay_check(truth, blind, boundary, out: dict) -> dict:
    """Independent replay through the committed episode driver: our loop must
    reproduce cem.run_episode bit-for-bit, or the counts are not counts of the
    published quantity."""
    ep = cem.run_episode(truth, blind, seed=out["seed"], boundary=boundary)
    return {"ret_matches": ep.ret == out["ret"],
            "contact_matches": ep.contact == out["contact"],
            "crossing_frac_matches":
                ep.crossing_frac == out["crossing_frac_mean_over_plans"],
            "run_episode_ret": ep.ret,
            "run_episode_crossing_frac": ep.crossing_frac}


def run_unit(unit: dict) -> dict:
    """Execute one unit. Pure function of `unit` (spawn-safe, order-free)."""
    t0 = time.time()
    x_wall = unit["x_wall"]
    truth, blind, boundary = make_row(x_wall)
    cfg = planner_config()
    n_per_plan = cfg["n_trajectories_per_plan"]

    if unit["scope"] == "initial_state":
        out = initial_scope_counts(truth, blind, boundary, unit["p_lo"],
                                   unit["p_hi"], n_per_plan)
    else:
        out = episode_scope_counts(truth, blind, boundary,
                                   1000 * unit["episode"], n_per_plan)
        out["episode"] = unit["episode"]
        if unit.get("validate_against_run_episode"):
            out["validation_run_episode"] = replay_check(
                truth, blind, boundary, out)
            assert all(out["validation_run_episode"][k] for k in
                       ("ret_matches", "contact_matches",
                        "crossing_frac_matches")), out["validation_run_episode"]

    out.update({"key": unit["key"], "scope": unit["scope"],
                "x_wall": x_wall, "elapsed_s": round(time.time() - t0, 2)})
    return out


def build_units(walls, n_plans: int, chunk: int, n_episodes: int) -> list:
    """Round-robin over rows and scopes so a deadline cut leaves every row
    with a comparable sample instead of finishing row 1 only."""
    n_chunks = (n_plans + chunk - 1) // chunk
    units = []
    for i in range(max(n_chunks, n_episodes)):
        for w in walls:
            rk = row_key(w)
            if i < n_episodes:
                units.append({"key": f"{rk}|episode|{i}", "scope": "episode",
                              "x_wall": w, "episode": i,
                              "validate_against_run_episode": i == 0})
            if i < n_chunks:
                lo = i * chunk
                units.append({"key": f"{rk}|initial_state|{i}",
                              "scope": "initial_state", "x_wall": w,
                              "p_lo": lo, "p_hi": min(lo + chunk, n_plans)})
    return units


# ----------------------------------------------------------------------------
# aggregation
# ----------------------------------------------------------------------------


_PUB_CACHE: dict = {}


def _published_row(x_wall: float) -> dict | None:
    if not PUBLISHED.exists():
        return None
    if "d" not in _PUB_CACHE:
        _PUB_CACHE["d"] = json.loads(PUBLISHED.read_text())
    d = _PUB_CACHE["d"]
    for r in d.get("rows", []):
        if r.get("instrument") == "cart" and r.get("knob") == x_wall:
            return r
    return None


def aggregate(units: dict, walls, cfg: dict) -> dict:
    n_per_plan = cfg["n_trajectories_per_plan"]
    rows = []
    for w in walls:
        rk = row_key(w)
        mine = [u for u in units.values() if u["x_wall"] == w]
        init = [u for u in mine if u["scope"] == "initial_state"]
        eps = [u for u in mine if u["scope"] == "episode"]
        truth, _, _ = make_row(w)
        n_traj_per_episode = truth.h_episode * n_per_plan
        row = {
            "instrument": "cart", "x_wall": w, "row_key": rk,
            "published_crossing_cem_table_cell":
                (_published_row(w) or {}).get("crossing_frac_cem_blind"),
            "published_n_trajectories":
                PUBLISHED_PLANS_PER_ROW * n_per_plan,
            "n_imagined_trajectories_per_episode": n_traj_per_episode,
            "n_imagined_trajectories_per_episode_derivation":
                (f"h_episode({truth.h_episode}) * n_iters({cfg['n_iters']}) "
                 f"* n_samples({cfg['n_samples']}) = {n_traj_per_episode}"),
        }
        for name, group in (("initial_state", init), ("episode", eps)):
            n_traj = sum(u["trajectories"] for u in group)
            k = sum(u["crossings"] for u in group)
            n_plans = sum(u["plans"] for u in group)
            blk = {
                "n_units_done": len(group),
                "n_plans": n_plans,
                "n_trajectories_examined": n_traj,
                "crossings_observed": k,
                "crossing_frac_point": (k / n_traj) if n_traj else None,
                "p_upper_cp95_onesided":
                    clopper_pearson_upper(k, n_traj) if n_traj else None,
                "p_upper_wilson95_twosided":
                    wilson_upper(k, n_traj) if n_traj else None,
                "sample_multiple_of_published":
                    (n_traj / (PUBLISHED_PLANS_PER_ROW * n_per_plan))
                    if n_traj else 0.0,
            }
            if blk["p_upper_cp95_onesided"] is not None:
                ph = blk["p_upper_cp95_onesided"]
                blk["mu_query_upper_from_p_union_bound"] = min(
                    1.0, n_traj_per_episode * ph)
                blk["mu_query_upper_from_p_independence"] = (
                    1.0 - (1.0 - ph) ** n_traj_per_episode)
            if name == "episode":
                n_ep = len(group)
                k_ep = sum(1 for u in group if u["episode_has_crossing"])
                blk["n_episodes"] = n_ep
                blk["episodes_with_any_crossing"] = k_ep
                blk["mu_query_point_direct"] = (k_ep / n_ep) if n_ep else None
                blk["mu_query_upper_cp95_direct"] = (
                    clopper_pearson_upper(k_ep, n_ep) if n_ep else None)
                blk["episodes_with_true_mode_contact"] = sum(
                    1 for u in group if u["contact"])
            row[name] = blk
        # A LOWER confidence bound on mu_query(E), which the censored-zero
        # reading cannot supply. An initial-state-scope plan IS the first plan
        # of the episode with that seed (continuous_cem.py draws the initial
        # state from random.Random(sd) and then plans, exactly as
        # cem.run_episode does), and "the first plan contains a crossing"
        # implies "some query in the episode lands in the disagreement region".
        # So P(first plan crosses) <= mu_query(E), and a one-sided
        # Clopper-Pearson lower bound on the former is one for the latter.
        n_plans_i = row["initial_state"]["n_plans"]
        k_plans_i = sum(u["plans_with_crossing"] for u in init)
        if n_plans_i:
            row["mu_query_lower_bound_from_first_plan"] = {
                "plans_with_at_least_one_crossing": k_plans_i,
                "n_plans": n_plans_i,
                "point": k_plans_i / n_plans_i,
                "lower_cp95_onesided": clopper_pearson_lower(
                    k_plans_i, n_plans_i, 0.05),
                "argument": "an initial-state-scope plan is the episode's "
                            "first plan; {first plan crosses} implies "
                            "{mu_query event}, so this is a valid lower "
                            "confidence bound on mu_query(E)"}
        row["crossing_plan_seeds_initial_scope"] = sorted(
            s for u in init for s in u.get("crossing_plan_seeds", []))
        row["crossing_episode_seeds"] = sorted(
            u["seed"] for u in eps if u["episode_has_crossing"])
        row["total_trajectories_examined"] = (
            row["initial_state"]["n_trajectories_examined"]
            + row["episode"]["n_trajectories_examined"])
        row["total_crossings_observed"] = (
            row["initial_state"]["crossings_observed"]
            + row["episode"]["crossings_observed"])
        # The two scopes sample DIFFERENT state distributions (episode-start
        # states vs all states the blind-CEM episode visits), so the pooled
        # count is reported for scale only; every mu_query bound below is
        # derived from the episode scope, which is the distribution the
        # quantity is defined on.
        # headline: the tightest defensible upper bound on mu_query(E)
        cands = [(row["episode"].get("mu_query_upper_cp95_direct"),
                  "direct episode-level Clopper-Pearson (no independence "
                  "assumption)"),
                 (row["episode"].get("mu_query_upper_from_p_union_bound"),
                  "union bound over the episode's imagined trajectories from "
                  "the per-trajectory Clopper-Pearson upper bound")]
        cands = [(v, s) for v, s in cands if v is not None]
        if cands:
            v, s = min(cands)
            row["mu_query_upper_best"] = v
            row["mu_query_upper_best_source"] = s
            row["play_cost_upper_implied_by_prop_playcost"] = v
        rows.append(row)
    return {"rows": rows}


def validate(units: dict, walls, cfg: dict) -> dict:
    """The published cells must be recovered exactly by the first 20 units of
    each scope; otherwise this script is not measuring the paper's quantity."""
    n_per_plan = cfg["n_trajectories_per_plan"]
    checks = []
    for w in walls:
        pub = _published_row(w)
        if pub is None:
            continue
        # initial_state: plans p = 0..19 (contained in the first chunks)
        fr = []
        for u in sorted((u for u in units.values()
                         if u["x_wall"] == w and u["scope"] == "initial_state"),
                        key=lambda u: int(u["key"].rsplit("|", 1)[1])):
            fr.extend(u.get("first_plan_fracs", []))
            if len(fr) >= PUBLISHED_PLANS_PER_ROW:
                break
        if len(fr) >= PUBLISHED_PLANS_PER_ROW:
            mine = sum(fr[:PUBLISHED_PLANS_PER_ROW]) / PUBLISHED_PLANS_PER_ROW
            checks.append({
                "x_wall": w, "scope": "initial_state",
                "published": pub["crossing_frac_cem_blind"], "recomputed": mine,
                "match": math.isclose(mine, pub["crossing_frac_cem_blind"],
                                      rel_tol=0.0, abs_tol=1e-15)})
        # episode: episodes 0..19
        ep = [u for u in units.values()
              if u["x_wall"] == w and u["scope"] == "episode"
              and u["episode"] < PUBLISHED_PLANS_PER_ROW]
        if len(ep) == PUBLISHED_PLANS_PER_ROW:
            mine = sum(u["crossing_frac_mean_over_plans"]
                       for u in ep) / PUBLISHED_PLANS_PER_ROW
            checks.append({
                "x_wall": w, "scope": "episode",
                "published": pub["crossing_frac_cem_episode_blind"],
                "recomputed": mine,
                "match": math.isclose(
                    mine, pub["crossing_frac_cem_episode_blind"],
                    rel_tol=1e-12, abs_tol=1e-15)})
        ok = [u for u in units.values()
              if u["x_wall"] == w and u["scope"] == "episode"
              and "validation_run_episode" in u]
        for u in ok:
            checks.append({"x_wall": w, "scope": "episode_driver_replay",
                           "episode": u["episode"],
                           "match": all(u["validation_run_episode"][k] for k in
                                        ("ret_matches", "contact_matches",
                                         "crossing_frac_matches"))})
    return {"checks": checks,
            "all_match": all(c["match"] for c in checks) if checks else None,
            "n_per_plan": n_per_plan}


def write_json(payload: dict) -> None:
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False))
    os.replace(tmp, OUT)


def build_payload(args, cfg, units: dict, elapsed: float,
                  truncated: bool, n_units_total: int) -> dict:
    walls = args.walls
    payload = {
        "script": "cem_crossing_bound.py",
        "review_point": 7,
        "params": vars(args),
        "planner_config": cfg,
        "planner_source": "cwm.continuous.cem.plan_cem (reused unmodified)",
        "crossing_definition":
            "an imagined trajectory 'crosses' iff some imagined state has "
            "x >= x_wall during the planner's horizon-40 rollout on the "
            "blind model; identical to scripts/continuous_cem.py",
        "interval_method": "Clopper-Pearson (exact binomial); Wilson two-sided "
                           "upper reported alongside for reference",
        "units_done": len(units),
        "units_total": n_units_total,
        "truncated": truncated,
        "elapsed_s": round(elapsed, 1),
    }
    payload.update(aggregate(units, walls, cfg))
    payload["validation"] = validate(units, walls, cfg)
    payload["units"] = units
    return payload


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--walls", type=float, nargs="+", default=[6.0, 8.0, 10.0],
                    help="6.0 is the resolved control")
    ap.add_argument("--plans", type=int, default=4000,
                    help="initial-state-scope plans per row "
                         "(4000 x 320 = 1.28M trajectories = 200x tab:cem)")
    ap.add_argument("--chunk", type=int, default=100, help="plans per unit")
    ap.add_argument("--episodes", type=int, default=100,
                    help="episode-scope CEM episodes per row")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--deadline-s", type=float, default=5400.0)
    ap.add_argument("--drill-walls", type=float, nargs="*", default=[],
                    help="re-run, at per-plan granularity, the initial-state "
                         "chunks of these rows that recorded a crossing but no "
                         "plan-seed detail (cheap provenance backfill)")
    ap.add_argument("--out", default=str(OUT),
                    help="checkpoint path (override only for smoke tests)")
    args = ap.parse_args()

    OUT = pathlib.Path(args.out)
    cfg = planner_config()
    units: dict = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
            units = prev.get("units", {}) or {}
            print(f"resuming: {len(units)} units already done", flush=True)
        except json.JSONDecodeError:
            print("existing JSON unreadable; starting fresh", flush=True)

    all_units = build_units(args.walls, args.plans, args.chunk, args.episodes)
    pending = [u for u in all_units if u["key"] not in units]
    print(f"planner: {cfg}", flush=True)
    print(f"{len(all_units)} units total, {len(pending)} pending, "
          f"{args.workers} workers, deadline {args.deadline_s}s", flush=True)

    t0 = time.time()
    truncated = False
    if pending:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(args.workers) as pool:
            for res in pool.imap_unordered(run_unit, pending):
                units[res["key"]] = res
                write_json(build_payload(args, cfg, units, time.time() - t0,
                                         True, len(all_units)))
                print(f"  {res['key']:>34}  traj={res['trajectories']:>7} "
                      f"crossings={res['crossings']:>5} "
                      f"[{res['elapsed_s']:.1f}s] "
                      f"({len(units)}/{len(all_units)})", flush=True)
                if time.time() - t0 > args.deadline_s:
                    truncated = True
                    print("deadline reached; stopping cleanly", flush=True)
                    break
            pool.terminate()

    # Backfill per-plan provenance for the rows whose published cell reads
    # 0.0000: if a crossing was found there we want its plan seed, not just a
    # count. Chunks already recorded with per-plan detail are skipped.
    for w in args.drill_walls:
        truth, blind, boundary = make_row(w)
        n_per_plan = cfg["n_trajectories_per_plan"]
        for key, u in list(units.items()):
            if (u["x_wall"] != w or u["scope"] != "initial_state"
                    or not u["crossings"] or "crossing_plan_seeds" in u):
                continue
            i = int(key.rsplit("|", 1)[1])
            lo = i * args.chunk
            hi = min(lo + args.chunk, args.plans)
            print(f"  drill {key}: plans {lo}..{hi - 1}", flush=True)
            fresh = initial_scope_counts(truth, blind, boundary, lo, hi,
                                         n_per_plan)
            assert fresh["crossings"] == u["crossings"], (key, fresh, u)
            u.update(fresh)
            write_json(build_payload(args, cfg, units, time.time() - t0,
                                     True, len(all_units)))

    payload = build_payload(args, cfg, units, time.time() - t0,
                            truncated or len(units) < len(all_units),
                            len(all_units))
    write_json(payload)
    print(f"\nwrote {OUT}  [{payload['elapsed_s']}s] "
          f"truncated={payload['truncated']}", flush=True)
    for r in payload["rows"]:
        for scope in ("initial_state", "episode"):
            b = r[scope]
            if not b["n_trajectories_examined"]:
                continue
            print(f"x_wall={r['x_wall']:>4} {scope:>13}: "
                  f"traj={b['n_trajectories_examined']:>9} "
                  f"({b['sample_multiple_of_published']:.0f}x tab:cem) "
                  f"crossings={b['crossings_observed']:>6} "
                  f"p<={b['p_upper_cp95_onesided']:.3e} "
                  f"mu_query<={b.get('mu_query_upper_from_p_union_bound', 0):.4f}"
                  + (f"  direct mu_query<="
                     f"{b['mu_query_upper_cp95_direct']:.4f} "
                     f"({b['episodes_with_any_crossing']}/{b['n_episodes']} "
                     f"episodes)" if scope == "episode" else ""), flush=True)
    print(f"validation all_match={payload['validation']['all_match']}",
          flush=True)
    for r in payload["rows"]:
        k = r["episode"]["crossings_observed"] + \
            r["initial_state"]["crossings_observed"]
        if r["x_wall"] in (8.0, 10.0) and k > 0:
            print(f"*** FINDING: {k} imagined crossing(s) OBSERVED at "
                  f"x_wall={r['x_wall']} -- the published 0.0000 cell is not "
                  f"an exact zero ***", flush=True)


if __name__ == "__main__":
    main()
