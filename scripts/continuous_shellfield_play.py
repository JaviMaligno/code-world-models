"""ShellFieldN play-cost measurement (paper 3, n-dim arm, step 3 of the
"first measurements" sequence in docs/paper3/SHELLFIELD-N-DESIGN.md, after
r(n) calibration [continuous_shellfield.py] and the truth-MPC navigation
check [continuous_shellfield_nav.py] confirmed vector MPC reaches the real
lode at every n = 2..6).

Measures whether the BLIND model (shell disabled, `blind_of`) is exploited
by its own planner across n -- the danger mechanism (paper 1's play_cost)
becoming automatic as r(n) collapses (continuous_shellfield.py's finding).

play_cost is `harness.play_cost`'s own formula, UNCHANGED:

    play_cost = (J_truth - J_blind) / (J_truth - J_random)

with all three arms measured on paired seeds in the TRUE environment
(truth-MPC, blind-MPC, and a random baseline). We cannot call
`harness.play_cost(...)` directly, though: its `run_episode`'s "random"
branch samples a SCALAR action (`rng.uniform(-truth.a_max, truth.a_max)`),
which is the 1D/2D instruments' interface, not ShellFieldN's thrust-VECTOR
action (`action_dim == n`) -- feeding it a scalar crashes in
`thrust_vector_nd` (`for ai in action` over a float). This is exactly the
n-dim/random-baseline gap `continuous_shellfield_nav.py` already hit and
solved with a dedicated `run_random_episode` loop (uniform per-component
thrust, the same sampling `continuous_shellfield.py`'s rarity sweep uses).
So: the truth-MPC and blind-MPC arms go through `harness.run_episode`
UNMODIFIED (mpc.plan already reads `action_dim` off the model), and only
the random arm uses that dedicated n-dim loop; the three means are then
combined with `harness.play_cost`'s exact formula above (no new formula
invented). `blind_contact_rate` is `harness.run_episode`'s own `contact`
flag (truth-env wall/shell clamp fired at least once), averaged over the
blind-MPC episodes -- identical definition to `harness.play_cost`'s.

Same horizon/n_samples/block/episodes as the nav check (harness.play_cost's
defaults: horizon 40, n_samples 200, block 10, episodes 20), so this is
mpc-cost-comparable to continuous_shellfield_nav.py but roughly 2x its
wall-clock (truth-MPC AND blind-MPC per episode, instead of just truth-MPC).

RESUMABLE (hard project rule): writes results/continuous_shellfield_play.json
atomically after EVERY n; a restart skips any n already present. Resuming
with different --episodes/--seed/--horizon/--n-samples/--block than the
stored file is a hard error (numbers would silently mix configurations).

Run: PYTHONPATH=src python scripts/continuous_shellfield_play.py   (CPU;
truth-MPC + blind-MPC roughly doubles continuous_shellfield_nav.py's
per-n wall-clock, so budget accordingly -- it is resumable per n if
interrupted.)
"""
import argparse
import json
import os
import pathlib
import random
import time

from cwm.continuous.envs import ShellFieldN, blind_of
from cwm.continuous import harness

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--ns", type=int, nargs="+", default=[2, 3, 4, 5, 6])
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--n-samples", type=int, default=200, dest="n_samples")
ap.add_argument("--block", type=int, default=10)
ap.add_argument("--out", type=str,
                default="results/continuous_shellfield_play.json")
args = ap.parse_args()


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Serialize to a temp file in the same directory, then os.replace() it
    over the destination -- a single atomic rename, so a kill mid-write
    never corrupts the previous checkpoint (same discipline as
    continuous_shellfield.py / continuous_shellfield_nav.py)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def run_random_episode_nd(env: ShellFieldN, seed: int) -> float:
    """Uniform per-component thrust-vector random policy (same sampling as
    continuous_shellfield.py's rarity rollouts and
    continuous_shellfield_nav.py's run_random_episode) -- the n-dim
    counterpart of harness.run_episode's scalar random branch, which cannot
    be reused here (ShellFieldN's action is a length-n tuple, not a
    scalar). Returns the episode return only; harness.play_cost's formula
    only needs J_random, not the random arm's contact/final-state."""
    rng = random.Random(seed)
    s = env.initial_state(rng)
    total = 0.0
    for _ in range(env.h_episode):
        a = tuple(rng.uniform(-1.0, 1.0) for _ in range(env.n))
        s, r, _ = env.step(s, a)
        total += r
    return total


def play_cost_nd(truth: ShellFieldN, blind: ShellFieldN, n_episodes: int,
                 seed: int, horizon: int, n_samples: int, block: int) -> dict:
    """harness.play_cost's exact formula and paired-seed protocol, with the
    random arm swapped for the n-dim-safe loop above (harness.play_cost's
    own random branch is scalar-only, see module docstring). truth-MPC and
    blind-MPC both go through harness.run_episode UNMODIFIED."""
    t_eps, b_eps, r_rets = [], [], []
    for i in range(n_episodes):
        sd = seed + 1000 * i
        t_eps.append(harness.run_episode(truth, truth, "mpc", sd, horizon,
                                          n_samples, block))
        b_eps.append(harness.run_episode(truth, blind, "mpc", sd, horizon,
                                          n_samples, block))
        r_rets.append(run_random_episode_nd(truth, sd))
    j_t = harness.mean_return(t_eps)
    j_b = harness.mean_return(b_eps)
    j_r = sum(r_rets) / len(r_rets)
    denom = j_t - j_r
    return {
        "j_truth": j_t, "j_blind": j_b, "j_random": j_r,
        "play_cost": (j_t - j_b) / denom if denom > 0 else 0.0,
        "blind_contact_rate": sum(e.contact for e in b_eps) / n_episodes,
        "n_episodes": n_episodes,
    }


def main() -> None:
    out_path = pathlib.Path(args.out)
    config_keys = ("episodes", "seed", "horizon", "n_samples", "block")
    if out_path.exists():
        out = json.loads(out_path.read_text())
        out.setdefault("rows", [])
        stored_p = out.get("params", {}) or {}
        current_p = vars(args)
        mismatch = {k: (stored_p[k], current_p[k]) for k in config_keys
                    if k in stored_p and stored_p[k] != current_p[k]}
        if mismatch:
            raise ValueError(
                f"refusing to resume {out_path}: it was produced under a "
                f"different configuration {mismatch}; rerun with matching "
                f"flags or move the file aside")
    else:
        out = {"script": "continuous_shellfield_play.py", "params": vars(args),
               "rows": []}

    done = {row["n"] for row in out["rows"]}
    t0 = time.time()
    header = (f"{'n':>3} {'play_cost':>10} {'j_truth':>10} {'j_blind':>10} "
              f"{'j_random':>10} {'blind_contact':>13}")
    print(header, flush=True)
    for row in sorted(out["rows"], key=lambda r: r["n"]):
        print(f"{row['n']:3d} {row['play_cost']:10.4f} {row['j_truth']:10.4f} "
              f"{row['j_blind']:10.4f} {row['j_random']:10.4f} "
              f"{row['blind_contact_rate']:13.4f}  [cached]", flush=True)

    for n in args.ns:
        if n in done:
            continue
        truth = ShellFieldN(n=n)
        blind = blind_of(truth)
        pc = play_cost_nd(truth, blind, args.episodes, args.seed,
                          args.horizon, args.n_samples, args.block)
        row = {"n": n, **pc}
        out["rows"].append(row)
        out["elapsed_s"] = round(time.time() - t0, 1)
        _atomic_write_json(out_path, out)   # per-n checkpoint
        print(f"{n:3d} {pc['play_cost']:10.4f} {pc['j_truth']:10.4f} "
              f"{pc['j_blind']:10.4f} {pc['j_random']:10.4f} "
              f"{pc['blind_contact_rate']:13.4f}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, out)
    print(f"wrote {out_path}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
