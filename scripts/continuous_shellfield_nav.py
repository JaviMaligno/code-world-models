"""ShellFieldN truth-MPC navigation check (paper 3, n-dim arm,
docs/paper3/SHELLFIELD-N-DESIGN.md SS"first measurements", item 2).

Per n in {2..6}, at the SAME normalized geometry as continuous_shellfield.py
(only n varies), run truth-MPC (random-shooting, mpc.plan reading
ShellFieldN.action_dim == n so candidates are n-dim thrust vectors -- design
note, "the action interface") from the normalized start, same horizon/
n_samples/block as the 2D instruments (harness.play_cost's defaults: horizon
40, n_samples 200, block 10). Measures whether vector-action random-shooting
still navigates to the real lode as n grows, against a uniform per-component
random-policy baseline (same sampling as continuous_shellfield.py's rarity
sweep). This is NOT a rarity/contact measurement -- it is a REWARD/reach
measurement: J_truth_mpc (mean return under truth-MPC) vs J_random (mean
return under the random baseline), plus the mean final-state distance to the
real lode, whose comparison to r0 gives `reached`.

If MPC stops reaching the real lode at some n, that is a recorded
planner-scaling finding (the design note says the play arm then caps at the
largest working n) -- this script only measures and records, it does not
retune candidates to force a reach.

RESUMABLE (hard project rule): writes results/continuous_shellfield_nav.json
atomically after EVERY n; a restart skips any n already present. Resuming
with different --episodes/--seed/--horizon/--n-samples/--block than the
stored file is a hard error (numbers would silently mix configurations).

Run: PYTHONPATH=src python scripts/continuous_shellfield_nav.py   (a few min CPU)
"""
import argparse
import json
import os
import pathlib
import random
import time

from cwm.continuous.envs import ShellFieldN
from cwm.continuous import harness

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--ns", type=int, nargs="+", default=[2, 3, 4, 5, 6])
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--n-samples", type=int, default=200, dest="n_samples")
ap.add_argument("--block", type=int, default=10)
ap.add_argument("--out", type=str,
                default="results/continuous_shellfield_nav.json")
args = ap.parse_args()


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Serialize to a temp file in the same directory, then os.replace() it
    over the destination -- a single atomic rename, so a kill mid-write
    never corrupts the previous checkpoint (same discipline as
    continuous_shellfield.py)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def _dist_to_lode(env: ShellFieldN, state: tuple) -> float:
    return env._dist(state[: env.n], env.lode_real())


def run_truth_mpc_episode(env: ShellFieldN, seed: int, horizon: int,
                          n_samples: int, block: int) -> tuple[float, float]:
    """mpc.plan reads env.action_dim == n automatically (mpc.py, "the action
    interface"), so this is harness.run_episode's ordinary mpc branch --
    unmodified. Returns (return, final distance to the real lode)."""
    ep = harness.run_episode(env, env, "mpc", seed=seed, horizon=horizon,
                             n_samples=n_samples, block=block)
    return ep.ret, _dist_to_lode(env, ep.final_state)


def run_random_episode(env: ShellFieldN, seed: int) -> tuple[float, float]:
    """Uniform per-component thrust-vector random policy (same sampling as
    continuous_shellfield.py's rarity rollouts) -- harness.run_episode's
    random branch samples a SCALAR and cannot be reused for the n-dim action
    interface, hence this dedicated loop."""
    rng = random.Random(seed)
    s = env.initial_state(rng)
    total = 0.0
    for _ in range(env.h_episode):
        a = tuple(rng.uniform(-1.0, 1.0) for _ in range(env.n))
        s, r, _ = env.step(s, a)
        total += r
    return total, _dist_to_lode(env, s)


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
        out = {"script": "continuous_shellfield_nav.py", "params": vars(args),
               "rows": []}

    done = {row["n"] for row in out["rows"]}
    t0 = time.time()
    header = (f"{'n':>3} {'J_truth_mpc':>12} {'J_random':>10} "
              f"{'d_mpc':>7} {'d_random':>9} {'reached':>8}")
    print(header, flush=True)
    for row in sorted(out["rows"], key=lambda r: r["n"]):
        print(f"{row['n']:3d} {row['j_truth_mpc']:12.4f} "
              f"{row['j_random']:10.4f} {row['dist_mpc']:7.3f} "
              f"{row['dist_random']:9.3f} {str(row['reached']):>8}  [cached]",
              flush=True)

    for n in args.ns:
        if n in done:
            continue
        env = ShellFieldN(n=n)
        mpc_rets, mpc_dists = [], []
        rand_rets, rand_dists = [], []
        for i in range(args.episodes):
            sd = args.seed + 1000 * i
            ret, dist = run_truth_mpc_episode(env, sd, args.horizon,
                                              args.n_samples, args.block)
            mpc_rets.append(ret)
            mpc_dists.append(dist)
            ret_r, dist_r = run_random_episode(env, sd)
            rand_rets.append(ret_r)
            rand_dists.append(dist_r)
        j_truth_mpc = sum(mpc_rets) / len(mpc_rets)
        j_random = sum(rand_rets) / len(rand_rets)
        dist_mpc = sum(mpc_dists) / len(mpc_dists)
        dist_random = sum(rand_dists) / len(rand_dists)
        # reached: truth-MPC's mean final position ends up inside the real
        # lode's basin (distance < r0, the same radius the reward sigmoid
        # uses) -- a clean, env-native criterion, not a tuned threshold.
        reached = dist_mpc < env.r0
        row = {
            "n": n,
            "j_truth_mpc": j_truth_mpc,
            "j_random": j_random,
            "dist_mpc": dist_mpc,
            "dist_random": dist_random,
            "reached": reached,
            "episodes": args.episodes,
        }
        out["rows"].append(row)
        out["elapsed_s"] = round(time.time() - t0, 1)
        _atomic_write_json(out_path, out)   # per-n checkpoint
        print(f"{n:3d} {j_truth_mpc:12.4f} {j_random:10.4f} {dist_mpc:7.3f} "
              f"{dist_random:9.3f} {str(reached):>8}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, out)
    print(f"wrote {out_path}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
