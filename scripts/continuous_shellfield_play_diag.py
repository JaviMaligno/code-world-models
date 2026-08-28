"""Diagnostic: is ShellFieldN's play-arm collapse (n=2: play_cost~=0.162,
blind_contact~=0.15) caused by the ACTION INTERFACE, not the geometry?

The puzzle: RingField2D (2D, gap=0, scalar-heading action a in [-a_max,a_max]
mapped to phi = pi*a/a_max) gives play_cost_blind ~= 0.998, blind_contact ~=
1.0 -- the blind planner pins on the shell. ShellFieldN n=2 has the SAME
center (12, 0), SAME closed shell, SAME distance -- but a thrust-VECTOR
action a-vec in [-1,1]^n (norm-capped, mpc._candidates' per-component-
uniform sampling) gives play_cost ~= 0.162, blind_contact ~= 0.15.

Suspected cause: a=0 in the scalar interface gives phi=0, thrust exactly
EAST -- the blind planner's own "aim at the phantom" candidate is baked into
the three constant candidates {-1,0,1}*a_max. The vector interface's
analogous constants (mpc._candidates' `neg=(-1,)*n`, `pos=(1,)*n`,
`zero=(0,)*n`) are (-1,-1), (1,1), (0,0) for n=2 -- (1,1)/sqrt(2) points at
the CUBE DIAGONAL (45 deg), never at the phantom's axial direction (1,0).
And the n_samples per-component-uniform candidates are ALSO diagonal-biased
(direction of a uniform-in-box vector concentrates away from the axes), so
east is rarely, if ever, proposed to the blind planner.

This script does NOT modify cwm.continuous.mpc or cwm.continuous.envs (hard
constraint: the committed ShellFieldN/planner behavior is golden). It
re-implements a LOCAL, parametrized candidate sampler + planner + episode
loop (mirroring mpc.plan / mpc._candidates / harness.run_episode exactly for
the "percomponent" variant, so that variant reproduces the committed
n=2 row from results/continuous_shellfield_play.json as a control), and adds
two alternative samplings:

  (A) percomponent   -- the current interface, unmodified (the control;
                         expect play_cost~=0.162, blind_contact~=0.15).
  (B) direction_uniform -- sample a direction uniformly on S^{n-1} (normalized
                         Gaussian) times a magnitude in [0,1]; every direction,
                         including axial, is equally likely. Applied to BOTH
                         the MPC candidates' per-step draws AND the random
                         baseline (it is a wholesale change of the action-
                         generating distribution, same role "percomponent"
                         plays in (A)).
  (C) percomponent_axial -- (A)'s exact candidate set PLUS 2n explicit axial
                         unit-vector constant candidates +-e_i (the vector
                         analogue of the scalar interface's constant
                         candidates giving an exact east/west direction).
                         The random baseline is UNCHANGED from (A) -- the
                         axial candidates are a planner-side addition (like
                         (A)'s own diagonal constants), not a change to the
                         behavior policy.

Hypothesis (to confirm or refute): (B) and/or (C) restore blind exploitation
(blind_contact -> ~1, play_cost -> ~1, like RingField2D) while (A) stays
~0.16 -- pinning the cause on the per-component direction bias, not the
mode geometry/distance.

Also prints a direction-bias sanity anchor, independent of any planner: for
100000 per-component a-vec in [-1,1]^2 samples, the fraction whose direction
(a / ||a||) lands within ~10 deg of the +x axis (east, toward the phantom),
vs the same fraction under direction-uniform sampling (~5.6% analytically:
a 20-degree wide wedge out of 360).

RESUMABLE (project convention): writes results/continuous_shellfield_play_diag.json
atomically after EVERY variant; a restart skips variants already present.

Run: PYTHONPATH=src python scripts/continuous_shellfield_play_diag.py
(n=2 only, 3 variants; --episodes 20 by default -- drop to 10 with
--episodes 10 if too slow for a foreground run.)
"""
import argparse
import json
import math
import os
import pathlib
import random
import time
from dataclasses import dataclass

from cwm.continuous.envs import ShellFieldN, blind_of

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--n", type=int, default=2,
                help="ShellFieldN dimension (directly comparable to "
                     "RingField2D at n=2, the puzzle's control)")
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--horizon", type=int, default=40)
ap.add_argument("--n-samples", type=int, default=200, dest="n_samples")
ap.add_argument("--block", type=int, default=10)
ap.add_argument("--bias-samples", type=int, default=100_000, dest="bias_samples")
ap.add_argument("--out", type=str,
                default="results/continuous_shellfield_play_diag.json")
args = ap.parse_args()

VARIANTS = ("percomponent", "direction_uniform", "percomponent_axial")


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Same discipline as every other continuous_shellfield*.py script: write
    to a temp file in the same directory, then os.replace() -- a kill
    mid-write never corrupts the previous checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Action samplers (local; mpc.py / envs.py are untouched)
# --------------------------------------------------------------------------

def sample_percomponent(rng: random.Random, n: int) -> tuple:
    """The CURRENT interface's per-step draw -- byte-identical to
    mpc._candidates' `rng.uniform(-1.0, 1.0)` per component and to
    continuous_shellfield_play.py's run_random_episode_nd."""
    return tuple(rng.uniform(-1.0, 1.0) for _ in range(n))


def sample_direction_uniform(rng: random.Random, n: int) -> tuple:
    """A direction uniform on S^{n-1} (normalized isotropic Gaussian -- the
    standard construction; for n=2 this is exactly a uniform angle) times a
    magnitude uniform in [0,1], so the sampled vector's norm is <= 1 and it
    passes through thrust_vector_nd's clamp/normalize unchanged, with every
    direction -- including axial -- equally likely."""
    g = [rng.gauss(0.0, 1.0) for _ in range(n)]
    norm = math.sqrt(sum(gi * gi for gi in g))
    if norm == 0.0:
        return tuple(0.0 for _ in range(n))
    mag = rng.uniform(0.0, 1.0)
    return tuple(mag * gi / norm for gi in g)


SAMPLERS = {
    "percomponent": sample_percomponent,
    "direction_uniform": sample_direction_uniform,
    "percomponent_axial": sample_percomponent,  # random baseline unchanged
}


def _candidates_variant(rng: random.Random, horizon: int, n_samples: int,
                        block: int, n: int, variant: str):
    """mpc._candidates' action_dim>1 branch, reproduced locally so the
    committed mpc.py stays untouched, parametrized by `variant`:

    - "percomponent": IDENTICAL to mpc._candidates(action_dim=n) -- the
      3 constant candidates {(-1,)*n, (1,)*n, (0,)*n} plus n_samples
      per-component-uniform blocks. This is the control; it must reproduce
      results/continuous_shellfield_play.json's n=2 row.
    - "direction_uniform": the SAME 3 constant candidates (unchanged --
      those are the interface's existing constants, not what is being
      tested), but the n_samples blocks are drawn direction-uniform.
    - "percomponent_axial": "percomponent"'s exact candidate set, PLUS 2n
      explicit axial unit-vector constant candidates +-e_i -- the vector
      analogue of the scalar interface's constant candidates landing
      exactly on phi=0 (east).
    """
    neg = (-1.0,) * n
    pos = (1.0,) * n
    zero = (0.0,) * n
    yield [neg] * horizon
    yield [pos] * horizon
    yield [zero] * horizon
    if variant == "percomponent_axial":
        for i in range(n):
            e = tuple(1.0 if j == i else 0.0 for j in range(n))
            yield [e] * horizon
            yield [tuple(-c for c in e)] * horizon
    sampler = sample_direction_uniform if variant == "direction_uniform" \
        else sample_percomponent
    for _ in range(n_samples):
        acts = []
        while len(acts) < horizon:
            a = sampler(rng, n)
            acts.extend([a] * block)
        yield acts[:horizon]


def plan_variant(model, state, rng: random.Random, horizon: int,
                 n_samples: int, block: int, n: int, variant: str) -> tuple:
    """mpc.plan, reproduced locally for the tuple-action (n>1) path so the
    candidate generator can be swapped per variant without touching mpc.py."""
    best, best_a0 = -float("inf"), (0.0,) * n
    for acts in _candidates_variant(rng, horizon, n_samples, block, n, variant):
        s, total = state, 0.0
        for a in acts:
            s, r, _ = model.step(s, a)
            total += r
        if total > best:
            best, best_a0 = total, acts[0]
    return best, best_a0


@dataclass
class Episode:
    ret: float
    contact: bool
    final_state: tuple


def run_episode_variant(truth: ShellFieldN, model: ShellFieldN, policy: str,
                        seed: int, horizon: int, n_samples: int, block: int,
                        n: int, variant: str) -> Episode:
    """harness.run_episode, reproduced locally so the random branch can use
    the n-dim, variant-dependent sampler (harness.run_episode's own random
    branch is scalar-only -- see continuous_shellfield_play.py's docstring
    for why that loop cannot be reused for ShellFieldN)."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact = 0.0, False
    sampler = SAMPLERS[variant]
    for _ in range(truth.h_episode):
        if policy == "mpc":
            _, a = plan_variant(model, s, rng, horizon, n_samples, block, n,
                                variant)
        else:
            a = sampler(rng, n)
        s, r, c = truth.step(s, a)
        total += r
        contact = contact or c
    return Episode(ret=total, contact=contact, final_state=s)


def play_cost_variant(truth: ShellFieldN, blind: ShellFieldN, variant: str,
                      n_episodes: int, seed: int, horizon: int,
                      n_samples: int, block: int) -> dict:
    """harness.play_cost's exact formula and paired-seed protocol, all three
    arms (truth-MPC, blind-MPC, random) using the SAME variant's sampling, so
    each row is a self-consistent, controlled measurement."""
    n = truth.n
    t_eps, b_eps, r_eps = [], [], []
    for i in range(n_episodes):
        sd = seed + 1000 * i
        t_eps.append(run_episode_variant(truth, truth, "mpc", sd, horizon,
                                         n_samples, block, n, variant))
        b_eps.append(run_episode_variant(truth, blind, "mpc", sd, horizon,
                                         n_samples, block, n, variant))
        r_eps.append(run_episode_variant(truth, truth, "random", sd, horizon,
                                         n_samples, block, n, variant))
    j_t = sum(e.ret for e in t_eps) / n_episodes
    j_b = sum(e.ret for e in b_eps) / n_episodes
    j_r = sum(e.ret for e in r_eps) / n_episodes
    denom = j_t - j_r
    return {
        "variant": variant,
        "j_truth": j_t, "j_blind": j_b, "j_random": j_r,
        "play_cost": (j_t - j_b) / denom if denom > 0 else 0.0,
        "blind_contact_rate": sum(e.contact for e in b_eps) / n_episodes,
        "truth_contact_rate": sum(e.contact for e in t_eps) / n_episodes,
        "n_episodes": n_episodes,
    }


# --------------------------------------------------------------------------
# Bias sanity anchor (planner-independent)
# --------------------------------------------------------------------------

def east_fraction(rng: random.Random, n_samples: int, sampler, deg: float = 10.0) -> float:
    """Fraction of sampled 2D vectors whose direction a/||a|| lands within
    `deg` degrees of the +x axis (east, toward the phantom at (12,0))."""
    cos_thresh = math.cos(math.radians(deg))
    within = 0
    counted = 0
    for _ in range(n_samples):
        a = sampler(rng, 2)
        norm = math.hypot(a[0], a[1])
        if norm == 0.0:
            continue
        counted += 1
        if a[0] / norm >= cos_thresh:
            within += 1
    return within / counted if counted else 0.0


def main() -> None:
    if args.n != 2:
        print(f"warning: --n={args.n} != 2; the puzzle's control is n=2 "
              f"(directly comparable to RingField2D 2D)", flush=True)

    out_path = pathlib.Path(args.out)
    config_keys = ("n", "episodes", "seed", "horizon", "n_samples", "block")
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
        out = {"script": "continuous_shellfield_play_diag.py",
               "params": vars(args), "rows": [], "bias": {}}

    # bias sanity anchor -- planner-independent, cheap, run first
    bias_rng = random.Random(args.seed)
    frac_percomponent = east_fraction(bias_rng, args.bias_samples,
                                      sample_percomponent)
    frac_direction_uniform = east_fraction(bias_rng, args.bias_samples,
                                           sample_direction_uniform)
    out["bias"] = {
        "n_samples": args.bias_samples,
        "deg": 10.0,
        "east_fraction_percomponent": frac_percomponent,
        "east_fraction_direction_uniform": frac_direction_uniform,
        "east_fraction_direction_uniform_analytic": 20.0 / 360.0,
    }
    print(f"bias anchor ({args.bias_samples} samples, within 10 deg of east):"
          f"  percomponent={frac_percomponent:.4f}"
          f"  direction_uniform={frac_direction_uniform:.4f}"
          f"  (analytic uniform = {20.0 / 360.0:.4f})", flush=True)

    done = {row["variant"] for row in out["rows"]}
    t0 = time.time()
    header = (f"{'variant':>20} {'play_cost':>10} {'j_truth':>10} "
              f"{'j_blind':>10} {'j_random':>10} {'blind_contact':>13}")
    print(header, flush=True)
    for row in out["rows"]:
        print(f"{row['variant']:>20} {row['play_cost']:10.4f} "
              f"{row['j_truth']:10.4f} {row['j_blind']:10.4f} "
              f"{row['j_random']:10.4f} {row['blind_contact_rate']:13.4f}"
              f"  [cached]", flush=True)

    truth = ShellFieldN(n=args.n)
    blind = blind_of(truth)
    for variant in VARIANTS:
        if variant in done:
            continue
        pc = play_cost_variant(truth, blind, variant, args.episodes,
                               args.seed, args.horizon, args.n_samples,
                               args.block)
        out["rows"].append(pc)
        out["elapsed_s"] = round(time.time() - t0, 1)
        _atomic_write_json(out_path, out)   # per-variant checkpoint
        print(f"{variant:>20} {pc['play_cost']:10.4f} {pc['j_truth']:10.4f} "
              f"{pc['j_blind']:10.4f} {pc['j_random']:10.4f} "
              f"{pc['blind_contact_rate']:13.4f}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, out)
    print(f"wrote {out_path}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
