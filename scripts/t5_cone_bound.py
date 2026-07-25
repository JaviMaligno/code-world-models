"""T5: measure the cone event that Theorem T5-C bounds
(docs/paper3/THEORY.md, "T5 ... proved cone bound").

Theorem T5-C: r(n) <= h * 4/(n*kappa^2) with kappa the cosine of the
tangent-cone half-angle from the start to the ball B(c, r_out). The
bound is a union over time of an exchangeability estimate, and both
steps are loose. This script measures, per dimension n:

  - cone_rate: P(exists t <= h with <Z_t, e> >= kappa*||Z_t||), the
    EXACT quantity the union bound targets — so cone_rate vs the bound
    isolates looseness (b) (exchangeability), and cone_rate vs the
    single-time rate isolates looseness (a) (the union over time);
  - t_rate: the per-time average P(<Z_t,e> >= kappa||Z_t||), whose
    h-multiple is the union bound's own estimate;
  - r_measured: the realized contact rate (rollouts that fire the mode),
    the object of T5 itself.

Reported with Wilson CIs, plus log-log and log-linear slope fits of
cone_rate vs n — polynomial (Lemma E's 1/n) versus the exponential rate
the Beta heuristic predicts.

Resumable per n. CPU; ~5 min at the defaults.

Run: PYTHONPATH=src python scripts/t5_cone_bound.py [--rollouts N]
"""
import argparse
import json
import math
import os
import pathlib
import random
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import ShellFieldN                     # noqa: E402
from cwm.law import wilson_ci                                   # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
# grid stops at n = 8: a pilot puts the cone rate near 1e-3 there, so
# larger n returns 0 hits at any affordable sample and adds no slope
# information (the fit needs resolved points, not zeros)
ap.add_argument("--dims", type=int, nargs="+",
                default=[2, 3, 4, 5, 6, 7, 8])
ap.add_argument("--rollouts", type=int, default=10_000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--smallball", action="store_true",
                help="run the refuted-route localization instead of the sweep")
args = ap.parse_args()

OUT = "results/t5_cone_bound.json"
t0 = time.time()


def run_dim(n, n_roll, seed0):
    env = ShellFieldN(n=n)
    c = env.center()
    h = env.h_episode
    cone_hits = fired = 0
    t_hits = t_total = 0
    for i in range(n_roll):
        rng = random.Random(seed0 + 90_000 + i)
        s = env.initial_state(rng)
        x0 = s[:n]
        d = [c[k] - x0[k] for k in range(n)]
        L = math.sqrt(sum(v * v for v in d))
        kappa = math.sqrt(max(0.0, L * L - env.r_out ** 2)) / L
        e = [v / L for v in d]
        in_cone = contact_any = False
        for _ in range(h):
            a = tuple(rng.uniform(-env.a_max, env.a_max) for _ in range(n))
            s, _, contact = env.step(s, a)
            contact_any = contact_any or contact
            z = [s[k] - x0[k] for k in range(n)]
            nz = math.sqrt(sum(v * v for v in z))
            if nz > 0.0:
                t_total += 1
                if sum(z[k] * e[k] for k in range(n)) >= kappa * nz:
                    t_hits += 1
                    in_cone = True
        cone_hits += in_cone
        fired += contact_any
    kappa2 = (L * L - env.r_out ** 2) / (L * L)     # last rollout's; ~const
    return {"n": n, "rollouts": n_roll, "h": h,
            "kappa2_last": kappa2,
            "cone_hits": cone_hits, "fired": fired,
            "per_time_rate": t_hits / max(1, t_total),
            "bound_T5C": min(1.0, h * 4.0 / (n * kappa2))}


def main():
    store = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if store.get("rollouts") != args.rollouts:
        store = {"rollouts": args.rollouts, "seed": args.seed, "rows": []}
    done = {r["n"] for r in store["rows"]}
    for n in args.dims:
        if n in done:
            continue
        row = run_dim(n, args.rollouts, args.seed)
        p, lo, hi = wilson_ci(row["cone_hits"], args.rollouts)
        row.update({"cone_rate": p, "cone_ci": [lo, hi]})
        rp, rlo, rhi = wilson_ci(row["fired"], args.rollouts)
        row.update({"r_measured": rp, "r_ci": [rlo, rhi]})
        store["rows"].append(row)
        tmp = OUT + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(store, fh, indent=1)
        os.replace(tmp, OUT)
        print(f"n={n:3d}: cone_rate={p:.5f} (bound {row['bound_T5C']:.3f}), "
              f"per-time={row['per_time_rate']:.5f}, "
              f"r={rp:.5f} [{rlo:.5f},{rhi:.5f}]", flush=True)

    rows = sorted(store["rows"], key=lambda r: r["n"])
    pos = [r for r in rows if r["cone_rate"] > 0]
    if len(pos) >= 3:
        xs_log = [math.log(r["n"]) for r in pos]
        xs_lin = [float(r["n"]) for r in pos]
        ys = [math.log(r["cone_rate"]) for r in pos]

        def slope(xs, ys):
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            return (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
                    / sum((x - mx) ** 2 for x in xs))

        def r2(xs, ys):
            b = slope(xs, ys)
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            a = my - b * mx
            ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
            ss_tot = sum((y - my) ** 2 for y in ys)
            return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        fit = {"loglog_slope": slope(xs_log, ys), "loglog_r2": r2(xs_log, ys),
               "loglin_slope": slope(xs_lin, ys),
               "loglin_r2": r2(xs_lin, ys)}
        store["fit"] = fit
        print(f"\ncone_rate vs n: log-log slope {fit['loglog_slope']:.2f} "
              f"(R2 {fit['loglog_r2']:.3f})  [Lemma E predicts -1]")
        print(f"                log-linear slope {fit['loglin_slope']:.3f} "
              f"(R2 {fit['loglin_r2']:.3f})  [exponential if this fits "
              f"better]")
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(store, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"wrote {OUT}  ({time.time() - t0:.0f}s)")




def small_ball_arm():
    """The refuted-route localization (THEORY.md, T5 'A refuted route'):
    conditional on the cone event, is the PERPENDICULAR mass R small or
    is the aligned component Z1 large? Answer decides which tail a sharp
    bound must control.
    Run: PYTHONPATH=src python scripts/t5_cone_bound.py --smallball
    """
    import statistics as st
    out = []
    for n in (5, 8):
        env = ShellFieldN(n=n)
        c = env.center()
        z1s, rs, all_r = [], [], []
        for i in range(args.rollouts):
            rng = random.Random(args.seed + 90_000 + i)
            s = env.initial_state(rng)
            x0 = s[:n]
            d = [c[k] - x0[k] for k in range(n)]
            L = math.sqrt(sum(v * v for v in d))
            kappa = math.sqrt(max(0.0, L * L - env.r_out ** 2)) / L
            e = [v / L for v in d]
            for _ in range(env.h_episode):
                a = tuple(rng.uniform(-env.a_max, env.a_max)
                          for _ in range(n))
                s, _, _ = env.step(s, a)
                z = [s[k] - x0[k] for k in range(n)]
                nz = math.sqrt(sum(v * v for v in z))
                if nz == 0.0:
                    continue
                z1 = sum(z[k] * e[k] for k in range(n))
                r = math.sqrt(max(0.0, nz * nz - z1 * z1))
                all_r.append(r)
                if z1 >= kappa * nz:
                    z1s.append(z1)
                    rs.append(r)
        mean_r = st.mean(all_r)
        row = {"n": n, "cone_events": len(z1s), "mean_R_overall": mean_r,
               "mean_R_given_cone": st.mean(rs) if rs else None,
               "R_ratio": (st.mean(rs) / mean_r) if rs else None,
               "mean_Z1_given_cone": st.mean(z1s) if z1s else None}
        out.append(row)
        print(f"n={n}: cone events {len(z1s)}; R|cone = "
              f"{row['R_ratio']:.2f}x typical; Z1|cone = "
              f"{row['mean_Z1_given_cone']:.2f} vs R scale {mean_r:.2f}",
              flush=True)
    assert all(r["R_ratio"] < 0.6 for r in out), \
        "the cone event should be carried by SMALL perpendicular mass"
    print("\nThe cone event is a SMALL-BALL event for the perpendicular "
          "mass, not a large deviation of the aligned component: a sharp "
          "bound must control R's lower tail.")
    p = pathlib.Path("results/t5_small_ball.json")
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    if args.smallball:
        small_ball_arm()
    else:
        main()
