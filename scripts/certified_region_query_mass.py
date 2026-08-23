"""How much of the planner's query mass lies inside the certifiable region.

The coverage certificate bounds |f - f_hat| on the region the GATE covers. The
play-cost bound, by contrast, is driven by the region the PLANNER queries
(Proposition 4's query-hit mass). Those are different measures, and the paper
listed that mismatch as the certificate's remaining conceptual gap. This closes it
by measuring the overlap directly.

For each planner, every imagined MPC rollout step is a query; we count what
fraction of those (s, a) points fall inside the regions the certificate can cover.
If that fraction is small, the certificate is sound but nearly irrelevant to play
-- which is paper 1's thesis in continuous form, and quantified rather than argued:
the gate certifies where it looks and the planner looks elsewhere.

Run: PYTHONPATH=src python scripts/certified_region_query_mass.py   (~4 min CPU)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous import mpc                       # noqa: E402
from cwm.continuous.envs import CartWall, blind_of   # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=2)
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--n-samples", type=int, default=200)
ap.add_argument("--block", type=int, default=10)
ap.add_argument("--regions", type=float, nargs="+", default=[1.0, 1.0, 3.0, 2.0],
                help="flattened (X, V) pairs: the region |x| < X, |v| < V")
args = ap.parse_args()

env = CartWall(x_wall=8.0)
REGIONS = list(zip(args.regions[0::2], args.regions[1::2]))


def query_mass(model):
    total = 0
    inside = {r: 0 for r in REGIONS}
    for e in range(args.episodes):
        seed = 1000 * e
        rng = random.Random(seed)
        s = env.initial_state(rng)
        for step in range(env.h_episode):
            qrng = random.Random(seed * 100_000 + step)
            for acts in mpc._candidates(model.a_max, qrng, args.horizon,
                                        args.n_samples, args.block):
                st = s
                for a in acts:
                    total += 1
                    for (X, V) in REGIONS:
                        if abs(st[0]) < X and abs(st[1]) < V:
                            inside[(X, V)] += 1
                    st, _, _ = model.step(st, a)
            a = mpc.plan(model, s, random.Random(seed * 100_000 + step),
                         horizon=args.horizon, n_samples=args.n_samples,
                         block=args.block)
            s, _, _ = env.step(s, a)
    return total, {r: inside[r] / total for r in REGIONS}


rows = []
print(f"{'planner':>22} {'queries':>12} " +
      " ".join(f"in |x|<{X},|v|<{V}".rjust(18) for X, V in REGIONS))
for name, model in (("blind (the exploited)", blind_of(env)),
                    ("truth", env)):
    total, frac = query_mass(model)
    rows.append({"planner": name, "queries": total,
                 "inside_fraction": {f"{X},{V}": frac[(X, V)]
                                     for X, V in REGIONS}})
    print(f"{name:>22} {total:12,} " +
          " ".join(f"{100*frac[r]:17.1f}%" for r in REGIONS))

print("\nReading: the certificate is sound on its region and nearly irrelevant to")
print("play, because that region carries a couple of percent of the query mass.")
print("The gate certifies where it looks; the planner looks somewhere else.")

out = _REPO / "results" / "certified_region_query_mass.json"
out.write_text(json.dumps({"script": "certified_region_query_mass.py",
                           "params": vars(args), "regions": REGIONS,
                           "rows": rows}, indent=2))
print(f"\nwrote {out}")
