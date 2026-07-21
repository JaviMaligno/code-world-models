"""ShellFieldN calibration (paper 3, n-dim arm step 1,
docs/paper3/SHELLFIELD-N-DESIGN.md SS"first measurements", item 1).

Per n in {2..6}, at the SAME normalized geometry (only n varies: r_in/r_out/
lode constants/h_episode pinned at the 2D values, c and the real lode
embedded in the fixed first-two-coordinates 2-plane): per-rollout shell
rarity r(n) (mode contact) and interior-entry rate r_int(n)
(`ShellFieldN.in_interior`) under the uniform per-component random-vector
policy, a_i ~ U(-1, 1) independently (the thrust-vector action's
random-shooting baseline; the integrator norm-caps ||thrust|| regardless of
||a|| > 1 -- design note, "the action interface").

This is the "n as the rarity knob" mini-law (design note SS8.2): a
drift-free random-thrust walk in R^n loses the fixed 2-plane containing the
shell as n grows (concentration of measure), so reach collapses -- expect
~geometric-ish collapse in r(n). Alongside r(n) we print (1-r)^40: the
probability that a sample of 40 independent rollouts (the synthesis-sample
size used elsewhere in this project, e.g. continuous_danger_synthesis.py's
mode-blind-sample story) contains ZERO shell contacts. As r(n) shrinks with
n this approaches 1 -- the danger regime silently becoming automatic rather
than an occasional miss.

RESUMABLE (hard project rule: any long-running CPU sweep must checkpoint
and resume): writes results/continuous_shellfield.json atomically after
EVERY n. A restart loads the existing file, skips any n already present,
and only computes the missing ones -- a killed run never redoes finished
n's. Resuming with different --rollouts/--seed than the stored file is a
hard error (the numbers would silently mix configurations).

Run: PYTHONPATH=src python scripts/continuous_shellfield.py   (a few min CPU)
"""
import argparse
import json
import os
import pathlib
import random
import time

from cwm.continuous.envs import ShellFieldN
from cwm.law import wilson_ci

N_SAMPLE = 40   # reference sample size for the (1-r)^N "missed entirely" column

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--ns", type=int, nargs="+", default=[2, 3, 4, 5, 6])
ap.add_argument("--rollouts", type=int, default=600)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", type=str, default="results/continuous_shellfield.json")
args = ap.parse_args()


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Serialize to a temp file in the same directory, then os.replace() it
    over the destination -- a single atomic rename, so a kill mid-write
    never corrupts the previous checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def rarity_and_interior(env: ShellFieldN, n_rollouts: int, seed: int) -> tuple[int, int]:
    """Random rollouts under the uniform per-component thrust policy;
    per-rollout (shell contacted, interior reached) counts."""
    hits = entered = 0
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        hit = inside = False
        for _ in range(env.h_episode):
            a = tuple(rng.uniform(-1.0, 1.0) for _ in range(env.n))
            s, _, c = env.step(s, a)
            hit = hit or c
            inside = inside or env.in_interior(s[: env.n])
        hits += hit
        entered += inside
    return hits, entered


def main() -> None:
    out_path = pathlib.Path(args.out)
    if out_path.exists():
        out = json.loads(out_path.read_text())
        out.setdefault("rows", [])
        stored_p = out.get("params", {}) or {}
        current_p = vars(args)
        mismatch = {k: (stored_p[k], current_p[k]) for k in ("rollouts", "seed")
                    if k in stored_p and stored_p[k] != current_p[k]}
        if mismatch:
            raise ValueError(
                f"refusing to resume {out_path}: it was produced under a "
                f"different configuration {mismatch}; rerun with matching "
                f"flags or move the file aside")
    else:
        out = {"script": "continuous_shellfield.py", "params": vars(args),
               "rows": []}

    done = {row["n"] for row in out["rows"]}
    t0 = time.time()
    header = f"{'n':>3} {'r':>8} {'r_int':>8} {'(1-r)^' + str(N_SAMPLE):>10}"
    print(header, flush=True)
    for row in sorted(out["rows"], key=lambda r: r["n"]):
        r = row["r"]
        print(f"{row['n']:3d} {r:8.4f} {row['r_int']:8.4f} "
              f"{(1 - r) ** N_SAMPLE:10.4f}  [cached]", flush=True)

    for n in args.ns:
        if n in done:
            continue
        env = ShellFieldN(n=n)
        h, e = rarity_and_interior(env, args.rollouts, seed=args.seed + 50_000)
        r, r_lo, r_hi = wilson_ci(h, args.rollouts)
        ri, ri_lo, ri_hi = wilson_ci(e, args.rollouts)
        row = {
            "n": n, "r": r, "r_ci": [r_lo, r_hi],
            "r_int": ri, "r_int_ci": [ri_lo, ri_hi],
            "contacts": h, "interior_entries": e, "rollouts": args.rollouts,
        }
        out["rows"].append(row)
        out["elapsed_s"] = round(time.time() - t0, 1)
        _atomic_write_json(out_path, out)   # per-n checkpoint
        print(f"{n:3d} {r:8.4f} {ri:8.4f} {(1 - r) ** N_SAMPLE:10.4f}",
              flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, out)
    print(f"wrote {out_path}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
