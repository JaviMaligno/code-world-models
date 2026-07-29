"""Review point #9: honest inference for the headline play_cost rows.

The play tables are 20 paired episodes per cell with visibly skewed per-episode
distributions (the random arm is near zero on most seeds and occasionally large,
which is the play_cost DENOMINATOR), and on some cells a single seed dominates
the reported interval. 20 episodes plus a t-interval is not the right inference
for that. This script re-runs the three HEADLINE rows

    cart      x_wall  = 8      (tab:danger)
    pendulum  th_stop = 1.4    (tab:pendulum)
    patch2d   k       = (3,7)  (tab:patch2d)

with 100 PAIRED episodes instead of 20 -- same episode seed across the truth /
blind / random arms, the same pairing convention as the committed runs
(scripts/continuous_reach.py -> cwm.continuous.harness.play_cost pairs
sd = seed + 1000*i, seed = 0, and this script reuses harness.run_episode with
its default MPC settings), so episodes 0..19 REPRODUCE the committed cell
exactly. That reproduction is asserted and recorded under "validation".

Reported per row:
  * raw J_truth / J_blind / J_random means and the raw regret J_truth - J_blind;
  * normalized play_cost (ratio of means, the published estimator);
  * a PAIRED bootstrap 95% CI (20000 resamples of the seed triples, the ratio
    recomputed inside each resample, so denominator uncertainty is carried);
  * a paired sign-flip randomization test for "blind is worse than random",
    plus the exact paired sign test as a distribution-free companion;
  * distribution shape (median, IQR, min/max, skew) and a leave-one-seed-out
    jackknife range of play_cost, which is what makes "one seed dominates"
    checkable rather than asserted;
  * every per-seed triple, so an ECDF can be plotted from this JSON alone.

Also (no new episodes needed): an exact Clopper-Pearson 95% interval for the
2D mitigation lock-in count 7/20 at knob (4,8), recounted from the per-episode
returns already versioned in results/fence_separation_census.json.

Resumable: one unit = one (row, episode); every unit is checkpointed into
results/play_cost_intervals.json by atomic replace and a rerun skips what is
already there. Units are ordered cart/pendulum first, then patch2d, so a
deadline cut leaves the first two rows complete.

Run: PYTHONPATH=src python scripts/play_cost_intervals.py \
         --episodes 100 --workers 4 --deadline-s 7200
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cem_crossing_bound import (binom_cdf, clopper_pearson_interval)  # noqa: E402
from cwm.continuous import harness  # noqa: E402
from cwm.continuous.envs import (CartWall, PatchField2D, PendulumStop,  # noqa: E402
                                 blind_of)

OUT = pathlib.Path("results/play_cost_intervals.json")
CENSUS = pathlib.Path("results/fence_separation_census.json")
MITIGATION = pathlib.Path("results/continuous_mitigation_patch2d.json")

# The committed cells these 100-episode reruns must contain as their first 20.
ROWS = [
    {"key": "cart_xwall8", "kind": "cart", "knob": 8.0,
     "label": "cart x_wall = 8", "table": "tab:danger",
     "published_json": "results/continuous_reach.json",
     "published_match": {"x_wall": 8.0}},
    {"key": "pend_thstop1.4", "kind": "pend", "knob": 1.4,
     "label": "pendulum th_stop = 1.4", "table": "tab:pendulum",
     "published_json": "results/continuous_pendulum.json",
     "published_match": {"th_stop": 1.4}},
    {"key": "patch2d_k3_7", "kind": "patch2d", "knob": [3.0, 7.0],
     "label": "patch2d k = (3,7)", "table": "tab:patch2d",
     "published_json": "results/continuous_patch2d.json",
     "published_match": {"k1": 3.0, "k2": 7.0}},
]
PUBLISHED_EPISODES = 20
PAIRING_SEED = 0          # harness.play_cost(..., seed=0)
PAIRING_STRIDE = 1000     # sd = seed + 1000*i


def make_truth(kind: str, knob):
    if kind == "cart":
        return CartWall(x_wall=knob)
    if kind == "pend":
        return PendulumStop(th_stop=knob)
    if kind == "patch2d":
        return PatchField2D(p1=(knob[0], 0.0), p2=(knob[1], 0.0))
    raise ValueError(kind)


def episode_seed(i: int) -> int:
    return PAIRING_SEED + PAIRING_STRIDE * i


# ----------------------------------------------------------------------------
# one unit = one paired episode triple
# ----------------------------------------------------------------------------


def run_unit(unit: dict) -> dict:
    t0 = time.time()
    truth = make_truth(unit["kind"], unit["knob"])
    blind = blind_of(truth)
    sd = episode_seed(unit["episode"])
    # Same calls, same order, same defaults as harness.play_cost.
    t = harness.run_episode(truth, truth, "mpc", sd)
    b = harness.run_episode(truth, blind, "mpc", sd)
    r = harness.run_episode(truth, policy="random", seed=sd)
    return {"key": unit["key"], "row": unit["row"], "episode": unit["episode"],
            "seed": sd,
            "j_truth": t.ret, "j_blind": b.ret, "j_random": r.ret,
            "truth_contact": t.contact, "blind_contact": b.contact,
            "random_contact": r.contact,
            "elapsed_s": round(time.time() - t0, 2)}


def build_units(n_episodes: int) -> list:
    """cart and pendulum interleaved first (so a deadline cut completes them),
    patch2d afterwards."""
    units = []
    for group in (ROWS[:2], ROWS[2:]):
        for i in range(n_episodes):
            for row in group:
                units.append({"key": f"{row['key']}|{i}", "row": row["key"],
                              "kind": row["kind"], "knob": row["knob"],
                              "episode": i})
    return units


# ----------------------------------------------------------------------------
# inference
# ----------------------------------------------------------------------------


def _ratio_play_cost(t: list, b: list, r: list):
    mt, mb, mr = (sum(t) / len(t), sum(b) / len(b), sum(r) / len(r))
    den = mt - mr
    return ((mt - mb) / den if den > 0 else 0.0), mt, mb, mr, den


def paired_bootstrap(t: list, b: list, r: list, n_boot: int, seed: int) -> dict:
    """Resample the SEED TRIPLES with replacement (so the pairing is preserved)
    and recompute the ratio-of-means play_cost inside each resample."""
    n = len(t)
    rng = random.Random(seed)
    pc, regret, dnr = [], [], []
    bad_denominator = 0
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        tt = [t[i] for i in idx]
        bb = [b[i] for i in idx]
        rr = [r[i] for i in idx]
        mt, mb, mr = (sum(tt) / n, sum(bb) / n, sum(rr) / n)
        den = mt - mr
        if den <= 0:
            bad_denominator += 1
            continue
        pc.append((mt - mb) / den)
        regret.append(mt - mb)
        dnr.append(mr - mb)

    def ci(v):
        if not v:
            return None
        s = sorted(v)
        lo = s[max(0, int(math.floor(0.025 * len(s))))]
        hi = s[min(len(s) - 1, int(math.ceil(0.975 * len(s))) - 1)]
        return {"lo": lo, "hi": hi, "mean": statistics.mean(s),
                "sd": statistics.pstdev(s) if len(s) > 1 else 0.0}
    return {"n_boot": n_boot, "n_used": len(pc),
            "n_nonpositive_denominator": bad_denominator,
            "method": "paired (seed-triple) nonparametric bootstrap, "
                      "percentile 95% CI, ratio-of-means recomputed per resample",
            "play_cost_ci95": ci(pc),
            "regret_ci95": ci(regret),
            "j_random_minus_j_blind_ci95": ci(dnr)}


def signflip_test(b: list, r: list, n_perm: int, seed: int) -> dict:
    """Paired randomization test of H0: the per-seed difference
    d = J_random - J_blind is symmetric about 0 (i.e. blind is not worse than
    random), against the one-sided alternative mean(d) > 0. The permutation
    group is the sign flips, which is the exact group for paired data."""
    d = [ri - bi for ri, bi in zip(r, b)]
    n = len(d)
    obs = sum(d) / n
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        s = sum(x if rng.getrandbits(1) else -x for x in d)
        if s / n >= obs:
            ge += 1
    k = sum(1 for x in d if x > 0)
    n_eff = sum(1 for x in d if x != 0)
    sign_p = (1.0 - binom_cdf(k - 1, n_eff, 0.5)) if n_eff else 1.0
    return {"per_seed_d_random_minus_blind": d,
            "observed_mean_d": obs,
            "n_perm": n_perm,
            "p_onesided_signflip": (1 + ge) / (n_perm + 1),
            "alternative": "mean(J_random - J_blind) > 0, i.e. blind is worse "
                           "than random",
            "exact_sign_test": {"k_seeds_random_beats_blind": k,
                                "n_effective": n_eff,
                                "p_onesided": sign_p}}


def shape(v: list) -> dict:
    n = len(v)
    s = sorted(v)
    m = statistics.mean(v)
    sd = statistics.stdev(v) if n > 1 else 0.0
    skew = (sum((x - m) ** 3 for x in v) / n / sd ** 3) if sd > 0 else 0.0
    return {"n": n, "mean": m, "sd": sd, "median": statistics.median(v),
            "q25": s[int(0.25 * (n - 1))], "q75": s[int(0.75 * (n - 1))],
            "min": s[0], "max": s[-1], "skew_g1": skew}


def jackknife(t: list, b: list, r: list, seeds: list) -> dict:
    """Leave-one-seed-out play_cost: the direct check on 'one outlier seed
    dominates this cell'."""
    n = len(t)
    if n < 2:
        return {"play_cost_min": None, "play_cost_max": None,
                "most_influential_seed": None, "most_influential_delta": None,
                "per_seed_leave_one_out": []}
    vals = []
    for j in range(n):
        tt = [t[i] for i in range(n) if i != j]
        bb = [b[i] for i in range(n) if i != j]
        rr = [r[i] for i in range(n) if i != j]
        vals.append(_ratio_play_cost(tt, bb, rr)[0])
    full = _ratio_play_cost(t, b, r)[0]
    infl = [abs(v - full) for v in vals]
    jmax = max(range(n), key=lambda j: infl[j])
    return {"play_cost_min": min(vals), "play_cost_max": max(vals),
            "most_influential_seed": seeds[jmax],
            "most_influential_delta": vals[jmax] - full,
            "per_seed_leave_one_out": vals}


def _published(row: dict) -> dict | None:
    p = pathlib.Path(row["published_json"])
    if not p.exists():
        return None
    for rec in json.loads(p.read_text()).get("rows", []):
        if all(rec.get(k) == v for k, v in row["published_match"].items()):
            return rec
    return None


def summarize(units: dict, n_boot: int, n_perm: int) -> dict:
    rows_out, checks = [], []
    for row in ROWS:
        mine = sorted((u for u in units.values() if u["row"] == row["key"]),
                      key=lambda u: u["episode"])
        if not mine:
            rows_out.append({**{k: row[k] for k in
                                ("key", "label", "table", "knob")},
                             "n_episodes": 0, "complete": False})
            continue
        seeds = [u["seed"] for u in mine]
        t = [u["j_truth"] for u in mine]
        b = [u["j_blind"] for u in mine]
        r = [u["j_random"] for u in mine]
        pc, mt, mb, mr, den = _ratio_play_cost(t, b, r)
        per_seed_pc = [(ti - bi) / den if den > 0 else 0.0
                       for ti, bi in zip(t, b)]
        out = {
            **{k: row[k] for k in ("key", "label", "table", "knob")},
            "n_episodes": len(mine),
            "pairing": f"sd = {PAIRING_SEED} + {PAIRING_STRIDE}*i, "
                       f"i = 0..{len(mine) - 1}; same sd in all three arms",
            "j_truth": mt, "j_blind": mb, "j_random": mr,
            "regret_raw": mt - mb,
            "denominator_j_truth_minus_j_random": den,
            "play_cost": pc,
            "play_cost_estimator": "ratio of means (the published estimator)",
            "per_seed_play_cost_fixed_denominator": per_seed_pc,
            "per_seed_play_cost_note":
                "per-seed play_cost uses the COMMON aggregate denominator "
                "J_truth_bar - J_random_bar, so its mean equals the published "
                "ratio-of-means play_cost exactly (same convention as "
                "scripts/continuous_cem.py:paired_play_cost_ci)",
            "bootstrap": paired_bootstrap(t, b, r, n_boot, seed=20260727),
            "randomization_blind_worse_than_random":
                signflip_test(b, r, n_perm, seed=920260727),
            "shape": {"j_truth": shape(t), "j_blind": shape(b),
                      "j_random": shape(r),
                      "per_seed_play_cost": shape(per_seed_pc)},
            "jackknife": jackknife(t, b, r, seeds),
            "contact_rates": {
                "truth": sum(u["truth_contact"] for u in mine) / len(mine),
                "blind": sum(u["blind_contact"] for u in mine) / len(mine)},
            "per_seed": [{"seed": u["seed"], "j_truth": u["j_truth"],
                          "j_blind": u["j_blind"], "j_random": u["j_random"],
                          "play_cost_fixed_denominator": p}
                         for u, p in zip(mine, per_seed_pc)],
        }
        assert math.isclose(out["play_cost"],
                            statistics.mean(per_seed_pc), abs_tol=1e-12)
        # validation: the first 20 paired episodes must BE the committed cell
        pub = _published(row)
        if pub is not None and len(mine) >= PUBLISHED_EPISODES:
            head = mine[:PUBLISHED_EPISODES]
            got = {"j_truth": statistics.mean(u["j_truth"] for u in head),
                   "j_blind": statistics.mean(u["j_blind"] for u in head),
                   "j_random": statistics.mean(u["j_random"] for u in head)}
            got["play_cost"] = ((got["j_truth"] - got["j_blind"])
                                / (got["j_truth"] - got["j_random"]))
            for field in ("j_truth", "j_blind", "j_random", "play_cost"):
                checks.append({
                    "row": row["key"], "field": field,
                    "published": pub[field], "recomputed_first20": got[field],
                    "match": math.isclose(got[field], pub[field],
                                          rel_tol=1e-12, abs_tol=1e-15)})
            out["published_first20"] = {"published": {
                f: pub[f] for f in ("j_truth", "j_blind", "j_random",
                                    "play_cost")}, "recomputed": got}
        out["complete"] = None
        rows_out.append(out)
    return {"rows": rows_out,
            "validation": {"checks": checks,
                           "all_match": (all(c["match"] for c in checks)
                                         if checks else None),
                           "meaning": "episodes 0..19 of each 100-episode rerun "
                                      "reproduce the committed table cell "
                                      "exactly, which is what makes the "
                                      "100-episode inference a statement about "
                                      "the SAME quantity"}}


# ----------------------------------------------------------------------------
# (B2) the 2D mitigation lock-in count, from already-versioned per-episode data
# ----------------------------------------------------------------------------


def lockin_intervals() -> dict:
    if not CENSUS.exists():
        return {"available": False,
                "reason": f"{CENSUS} missing: the per-episode outcomes behind "
                          f"the 7/20 count are not versioned"}
    census = json.loads(CENSUS.read_text())["patch2d_episode_census"]
    mit_rows = (json.loads(MITIGATION.read_text())["rows"]
                if MITIGATION.exists() else [])
    out = {"available": True,
           "source": str(CENSUS),
           "pinned_definition_in_census":
               "ret < 0.1 * max(ret over the 20 mitigated episodes of that "
               "knob) -- scripts/fence_separation_census.py",
           "caveat":
               "the census threshold is estimated from the same 20 episodes "
               "(it is 0.1 x the sample MAX), so the exact binomial interval "
               "below treats as fixed a threshold that is not; the "
               "fixed-threshold variants are given beside it",
           "knobs": []}
    for c in census:
        rets = [e["ret"] for e in c["episodes"]]
        n = len(rets)
        thr_sample = 0.1 * max(rets)
        k_sample = sum(1 for x in rets if x < thr_sample)
        rec = {"knob": c["knob"], "n_episodes": n,
               "census_pinned_episodes": c["pinned_episodes"],
               "recount_matches_census": k_sample == c["pinned_episodes"],
               "sample_threshold": thr_sample,
               "as_published": clopper_pearson_interval(k_sample, n)}
        mit = next((m for m in mit_rows
                    if m.get("k1") == c["knob"][0] and m.get("k2") == c["knob"][1]),
                   None)
        if mit is not None:
            thr_fix = 0.1 * mit["j_truth"]
            k_fix = sum(1 for x in rets if x < thr_fix)
            rec["fixed_threshold_0.1_x_j_truth"] = {
                "j_truth": mit["j_truth"], "threshold": thr_fix,
                "k": k_fix, "interval": clopper_pearson_interval(k_fix, n)}
            thr_blind = 10.0 * mit["j_blind"]
            k_blind = sum(1 for x in rets if x < thr_blind)
            rec["strict_blind_level_threshold_10_x_j_blind"] = {
                "j_blind": mit["j_blind"], "threshold": thr_blind,
                "k": k_blind, "interval": clopper_pearson_interval(k_blind, n)}
        rec["returns_sorted"] = sorted(rets)
        out["knobs"].append(rec)
    return out


# ----------------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------------


def write_json(payload: dict) -> None:
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, OUT)


def build_payload(args, units: dict, elapsed: float, n_total: int,
                  full_stats: bool) -> dict:
    payload = {
        "script": "play_cost_intervals.py",
        "review_point": 9,
        "params": vars(args),
        "harness": "cwm.continuous.harness.run_episode (MPC defaults: "
                   "horizon 40, n_samples 200, block 10) -- the same calls, in "
                   "the same order, as harness.play_cost",
        "units_done": len(units), "units_total": n_total,
        "truncated": len(units) < n_total,
        "elapsed_s": round(elapsed, 1),
    }
    if full_stats:
        payload.update(summarize(units, args.n_boot, args.n_perm))
        payload["mitigation_lockin_2d"] = lockin_intervals()
        for r in payload["rows"]:
            r["complete"] = r["n_episodes"] >= args.episodes
    payload["units"] = units
    return payload


def main() -> None:
    global OUT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--deadline-s", type=float, default=7200.0)
    ap.add_argument("--n-boot", type=int, default=20000)
    ap.add_argument("--n-perm", type=int, default=20000)
    ap.add_argument("--out", default=str(OUT),
                    help="checkpoint path (override only for smoke tests)")
    args = ap.parse_args()
    OUT = pathlib.Path(args.out)

    units: dict = {}
    if OUT.exists():
        try:
            units = json.loads(OUT.read_text()).get("units", {}) or {}
            print(f"resuming: {len(units)} units already done", flush=True)
        except json.JSONDecodeError:
            print("existing JSON unreadable; starting fresh", flush=True)

    all_units = build_units(args.episodes)
    pending = [u for u in all_units if u["key"] not in units]
    print(f"{len(all_units)} units total, {len(pending)} pending, "
          f"{args.workers} workers, deadline {args.deadline_s}s", flush=True)

    t0 = time.time()
    if pending:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")
        with ctx.Pool(args.workers) as pool:
            for res in pool.imap_unordered(run_unit, pending):
                units[res["key"]] = res
                # cheap checkpoint (no bootstrap) after every episode
                write_json(build_payload(args, units, time.time() - t0,
                                         len(all_units), full_stats=False))
                print(f"  {res['key']:>20}  J_t={res['j_truth']:8.3f} "
                      f"J_b={res['j_blind']:8.3f} J_r={res['j_random']:7.3f} "
                      f"[{res['elapsed_s']:.0f}s] "
                      f"({len(units)}/{len(all_units)})", flush=True)
                if time.time() - t0 > args.deadline_s:
                    print("deadline reached; stopping cleanly", flush=True)
                    break
            pool.terminate()

    payload = build_payload(args, units, time.time() - t0, len(all_units),
                            full_stats=True)
    write_json(payload)
    print(f"\nwrote {OUT}  [{payload['elapsed_s']}s] "
          f"truncated={payload['truncated']}", flush=True)
    for r in payload["rows"]:
        if not r["n_episodes"]:
            print(f"{r['label']:>24}: NO EPISODES", flush=True)
            continue
        bs = r["bootstrap"]["play_cost_ci95"]
        print(f"{r['label']:>24}: n={r['n_episodes']:>3} "
              f"J_t={r['j_truth']:.3f} J_b={r['j_blind']:.4f} "
              f"J_r={r['j_random']:.4f} regret={r['regret_raw']:.3f} "
              f"play_cost={r['play_cost']:.4f} "
              f"boot95=[{bs['lo']:.4f},{bs['hi']:.4f}] "
              f"p_signflip="
              f"{r['randomization_blind_worse_than_random']['p_onesided_signflip']:.2e} "
              f"jack=[{r['jackknife']['play_cost_min']:.4f},"
              f"{r['jackknife']['play_cost_max']:.4f}]", flush=True)
    print(f"validation all_match={payload['validation']['all_match']}",
          flush=True)
    lk = payload.get("mitigation_lockin_2d", {})
    for k in lk.get("knobs", []):
        ap_ = k["as_published"]
        print(f"lock-in knob {k['knob']}: {ap_['k']}/{ap_['n']} "
              f"CP95=[{ap_['lo']:.3f},{ap_['hi']:.3f}] "
              f"recount_ok={k['recount_matches_census']}", flush=True)


if __name__ == "__main__":
    main()
