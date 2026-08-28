"""RingField2D calibration + mechanism sweep (paper 3, rung 2).

Per gap value: per-rollout mode rarity r(gamma) and interior-entry rate
r_int(gamma) (THEORY.md Remark: r_int(0) = 0 is a theorem — Lemma 2 — so the
gamma = 0 row is a check, not a measurement), the paired truth/blind/random
MPC arena (play_cost, as in continuous_patch2d.py), and the wrong-topology
column: play_cost of the FILLED-disc model (Prop 3: exactly 0 at gamma = 0,
consequential once the channel opens).

Run: PYTHONPATH=src python scripts/continuous_ring2d.py   (~5 min CPU)
"""
import argparse
import json
import pathlib
import random
import time

from cwm.continuous.envs import RingField2D, blind_of, filled_of
from cwm.continuous import harness
from cwm.law import wilson_ci

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--gaps", type=float, nargs="+", default=[0.0, 0.6, 1.2])
ap.add_argument("--rollouts", type=int, default=600)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def rarity_and_interior(truth, n_rollouts: int, seed: int) -> tuple[int, int]:
    """Random rollouts; per-rollout (mode fired, interior entered) counts."""
    hits = entered = 0
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = truth.initial_state(rng)
        hit = inside = False
        for _ in range(truth.h_episode):
            a = rng.uniform(-truth.a_max, truth.a_max)
            s, _, c = truth.step(s, a)
            hit = hit or c
            inside = inside or truth.in_interior(s[0], s[1])
        hits += hit
        entered += inside
    return hits, entered


t0 = time.time()
rows = []
print(f"{'gap':>5} {'r':>7} {'r_int':>7} {'J_truth':>8} {'J_blind':>8} "
      f"{'pc_blind':>8} {'pc_fill':>8}", flush=True)
for gap in args.gaps:
    truth = RingField2D(gap=gap)
    h, e = rarity_and_interior(truth, args.rollouts, seed=args.seed + 50_000)
    r, r_lo, r_hi = wilson_ci(h, args.rollouts)
    ri, ri_lo, ri_hi = wilson_ci(e, args.rollouts)

    pc_blind = harness.play_cost(truth, blind_of(truth), args.episodes,
                                 seed=args.seed)
    pc_fill = harness.play_cost(truth, filled_of(truth), args.episodes,
                                seed=args.seed)

    row = {
        "gap": gap,
        "r": r, "r_ci": [r_lo, r_hi],
        "r_interior": ri, "r_interior_ci": [ri_lo, ri_hi],
        "interior_entries": e, "rollouts": args.rollouts,
        "j_truth": pc_blind["j_truth"], "j_blind": pc_blind["j_blind"],
        "j_random": pc_blind["j_random"],
        "play_cost_blind": pc_blind["play_cost"],
        "blind_contact_rate": pc_blind["blind_contact_rate"],
        "j_filled": pc_fill["j_blind"],
        "play_cost_filled": pc_fill["play_cost"],
        "filled_contact_rate": pc_fill["blind_contact_rate"],
        "n_episodes": args.episodes,
    }
    rows.append(row)
    print(f"{gap:5.2f} {r:7.4f} {ri:7.4f} {row['j_truth']:8.2f} "
          f"{row['j_blind']:8.2f} {row['play_cost_blind']:8.3f} "
          f"{row['play_cost_filled']:8.3f}", flush=True)

out = {"script": "continuous_ring2d.py", "params": vars(args),
       "rows": rows, "elapsed_s": round(time.time() - t0, 1)}
path = pathlib.Path("results/continuous_ring2d.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
