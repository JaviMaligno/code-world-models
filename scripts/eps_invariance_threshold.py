"""The exact threshold below which the mode arm's reveal-rarity is eps-invariant.

The eps-sweep (scripts/continuous_eps_sweep.py) measures a mode arm's
reveal-rarity as FLAT in the gate tolerance, and the paper leans on that
flatness to write one symbol r for both "the rollout fires the mode" and "the
rollout reveals a disagreement". Flatness is not an accident and not merely
measured: for a rollout w let

    D(w) = max over w's mode contacts of ||truth - blind||_inf   (0 if none),

so reveal-rarity at tolerance eps is exactly P(D > eps) -- a non-increasing step
function whose steps are the observed values of D. Hence

    reveal-rarity(eps) = mode-firing rarity   for every eps < eps*,
    eps* = min{ D(w) : D(w) > 0 },

and the flatness breaks exactly above eps*. Note eps* is a per-ROLLOUT minimum of
a per-contact maximum: a pinned rollout contacts the mode many times, so it is
enough that ONE of its contacts is coarse, which is why eps* is far above the
smallest single-contact disagreement.

TWO THINGS THIS SCRIPT GETS RIGHT ONLY SINCE 2026-07-25, both caught in peer review.

(1) SAME SAMPLE. eps* is a property of a SAMPLE, not of the instrument: it is the
    minimum of D over the rollouts that fired. Comparing an eps* computed on one
    rollout stream against dips measured on another is not a prediction, and it
    failed on 2 of 4 arms when we did that (the sweep draws Random(10000+i); this
    script used Random(0+i)). It now defaults to the sweep's own stream, where the
    relation reveal-rarity(eps) = firing-rarity for eps < eps* is an identity and
    the first grid point at or above eps* is exactly where the sweep dips.

(2) A MINIMUM IS AN UNSTABLE STATISTIC. It is upward-biased for the population
    essential infimum and decreases monotonically in n, so "eps* = 0.3855, hence
    flat throughout a grid topping out at 0.3" is not safe. The script therefore
    reports the number of firing rollouts behind each eps*, the first two order
    statistics of D, and eps* recomputed on independent blocks and on a 10x sample,
    so the reader sees the resolution rather than a false decimal.

Run: PYTHONPATH=src python scripts/eps_invariance_threshold.py   (~2 min CPU)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall, PendulumStop, blind_of  # noqa: E402

GRID = [1e-9, 1e-6, 1e-4, 1e-3, 1e-2, 3e-2, 0.1, 0.3]
ARMS = (("cart wall@4", lambda: CartWall(x_wall=4.0)),
        ("cart wall@8", lambda: CartWall(x_wall=8.0)),
        ("pendulum stop@1.0", lambda: PendulumStop(th_stop=1.0)),
        ("pendulum stop@1.4", lambda: PendulumStop(th_stop=1.4)))

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--rollouts", type=int, default=2000,
                help="gate-policy rollouts per arm (the sweep's own sample size)")
ap.add_argument("--seed", type=int, default=10_000,
                help="MUST match the sweep's reveal-rarity stream (seed + 10_000 "
                     "there, with --seed 0) for the grid claim to be in-sample")
ap.add_argument("--blocks", type=int, nargs="+", default=[500_000, 900_000],
                help="extra independent streams, to show eps*'s sample variability")
ap.add_argument("--big", type=int, default=20_000,
                help="a 10x sample per arm, since min decreases in n (0 to skip)")
args = ap.parse_args()


def per_rollout_disagreement(env, n, seed):
    """D(w) for every rollout that contacts the mode, under the gate policy
    (uniform random actions from the initial-state distribution)."""
    blind = blind_of(env)
    out = []
    for i in range(n):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        worst, hit = 0.0, False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            st, _, contact = env.step(s, a)
            sb, _, _ = blind.step(s, a)
            if contact:
                hit = True
                worst = max(worst, max(abs(x - y) for x, y in zip(st, sb)))
            s = st
        if hit:
            out.append(worst)
    return out


def all_contact_disagreements(env, n, seed):
    """Every single-contact disagreement, to show how far above them eps* sits:
    eps* is a per-rollout MAX over contacts, so it is much larger than the
    smallest individual contact error, and that gap is the point of the remark."""
    blind = blind_of(env)
    out = []
    for i in range(n):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            st, _, contact = env.step(s, a)
            sb, _, _ = blind.step(s, a)
            if contact:
                out.append(max(abs(x - y) for x, y in zip(st, sb)))
            s = st
    return out


rows = []
print(f"{'arm':>18} {'firing':>7} {'eps*':>9} {'2nd D':>9} {'breaks at':>10}   "
      f"reveal/rarity over the grid")
for name, mk in ARMS:
    env = mk()
    ds = sorted(per_rollout_disagreement(env, args.rollouts, args.seed))
    eps_star = ds[0]
    second = ds[1] if len(ds) > 1 else None
    ratios = [sum(d > e for d in ds) / len(ds) for e in GRID]
    breaks = next((e for e in GRID if e >= eps_star), None)
    # eps* on independent streams, and on a 10x sample: how much is it a decimal?
    others = []
    for b in args.blocks:
        db = sorted(per_rollout_disagreement(env, args.rollouts, b))
        others.append({"seed": b, "n_firing": len(db), "eps_star": db[0]})
    big = None
    if args.big:
        dbig = sorted(per_rollout_disagreement(env, args.big, args.seed))
        big = {"rollouts": args.big, "n_firing": len(dbig), "eps_star": dbig[0]}
    singles = all_contact_disagreements(env, args.rollouts, args.seed)
    rows.append({"arm": name, "n_firing": len(ds), "eps_star": eps_star,
                 "second_order_statistic": second,
                 "first_grid_eps_above_eps_star": breaks,
                 "grid": GRID, "reveal_over_firing": ratios,
                 "eps_star_other_streams": others,
                 "eps_star_big_sample": big,
                 "n_contacts": len(singles),
                 "min_single_contact_disagreement": min(singles) if singles else None})
    print(f"{name:>18} {len(ds):7} {eps_star:9.4f} "
          f"{(second if second is not None else float('nan')):9.4f} {str(breaks):>10}   "
          + " ".join(f"{r:.3f}" for r in ratios))

print("\neps* is a sample minimum -- here is how much it moves:")
for r in rows:
    alt = ", ".join(f"{o['eps_star']:.4f} (n={o['n_firing']})"
                    for o in r["eps_star_other_streams"])
    bg = (f";  at {r['eps_star_big_sample']['rollouts']} rollouts: "
          f"{r['eps_star_big_sample']['eps_star']:.4f} "
          f"(n={r['eps_star_big_sample']['n_firing']})"
          if r["eps_star_big_sample"] else "")
    print(f"  {r['arm']:>18}: {r['eps_star']:.4f} (n={r['n_firing']})  "
          f"other streams: {alt}{bg}")
    print(f"{'':>20}  smallest SINGLE-contact disagreement: "
          f"{r['min_single_contact_disagreement']:.4g} over {r['n_contacts']} contacts")

out = _REPO / "results" / "eps_invariance_threshold.json"
out.write_text(json.dumps({"script": "eps_invariance_threshold.py",
                           "params": vars(args), "grid": GRID,
                           "rows": rows}, indent=2))
print(f"\nwrote {out}")
print("Reading: on THIS sample reveal/rarity is exactly 1.000 for every grid eps")
print("below eps*, and the first grid point at or above eps* is where the sweep dips")
print("-- an identity in-sample, not a cross-sample prediction. The block-to-block")
print("spread above is the honest uncertainty on the threshold itself.")
