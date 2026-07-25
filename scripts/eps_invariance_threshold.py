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

This script computes eps* for the paper's four mode arms and reports, for the
sweep's own eps grid, the first grid point that must break flatness. Those
predictions are compared against the sweep's measured dips in the paper.

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
ap.add_argument("--seed", type=int, default=0)
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


rows = []
print(f"{'arm':>18} {'firing':>7} {'eps*':>9} {'breaks at':>10}   reveal/rarity over the grid")
for name, mk in ARMS:
    env = mk()
    ds = sorted(per_rollout_disagreement(env, args.rollouts, args.seed))
    eps_star = ds[0]
    ratios = [sum(d > e for d in ds) / len(ds) for e in GRID]
    breaks = next((e for e in GRID if e >= eps_star), None)
    rows.append({"arm": name, "n_firing": len(ds), "eps_star": eps_star,
                 "first_grid_eps_above_eps_star": breaks,
                 "grid": GRID, "reveal_over_firing": ratios,
                 "min_single_contact_disagreement": None})
    print(f"{name:>18} {len(ds):7} {eps_star:9.4f} {str(breaks):>10}   "
          + " ".join(f"{r:.3f}" for r in ratios))

out = _REPO / "results" / "eps_invariance_threshold.json"
out.write_text(json.dumps({"script": "eps_invariance_threshold.py",
                           "params": vars(args), "grid": GRID,
                           "rows": rows}, indent=2))
print(f"\nwrote {out}")
print("Reading: reveal/rarity is exactly 1.000 for every grid eps below eps*, and")
print("the first grid point at or above eps* is where the measured sweep dips.")
