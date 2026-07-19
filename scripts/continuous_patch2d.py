"""Third hybrid instrument: PatchField2D, the 2D bi-modal instrument
(design doc: docs/superpowers/specs/2026-07-16-patchfield2d-design.md).

Bi-knob mechanism sweep: for each (k1, k2) patch-center cell, measure
per-mode rarity (Wilson CIs), the paired truth/blind/random MPC arena
(play_cost), and the per-mode + joint danger(N=40) law
d@40 = play_cost * (1-r_i)^40 (per mode) and
d@40_joint = play_cost * ((1-r1)*(1-r2))^40.

Run: PYTHONPATH=src python scripts/continuous_patch2d.py   (~1-2h CPU)
"""
import argparse
import json
import pathlib
import random
import time

from cwm.continuous.envs import PatchField2D, blind_of
from cwm.continuous import harness
from cwm.law import wilson_ci

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--k1", type=float, nargs="+", default=[2.0, 3.0, 4.0])
ap.add_argument("--k2", type=float, nargs="+", default=[6.0, 7.0, 8.0])
ap.add_argument("--rollouts", type=int, default=600)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def per_mode_rarity(truth, n_rollouts: int, seed: int) -> tuple[int, int]:
    """Random-action rollouts, tracking per-mode contacts BEFORE stepping
    (mirrors tests/test_patch2d.py::test_rarity_split's loop)."""
    h1 = h2 = 0
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = truth.initial_state(rng)
        c1 = c2 = False
        for _ in range(truth.h_episode):
            a = rng.uniform(-truth.a_max, truth.a_max)
            m1, m2 = truth.contact_modes(s, a)
            c1, c2 = c1 or m1, c2 or m2
            s = truth.step(s, a)[0]
        h1 += c1
        h2 += c2
    return h1, h2


t0 = time.time()
rows = []
print(f"{'k1':>5} {'k2':>5} {'r1':>7} {'r2':>7} {'J_truth':>8} {'J_blind':>8} "
      f"{'cost':>6} {'d40_joint':>10}", flush=True)
for k1 in args.k1:
    for k2 in args.k2:
        truth = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
        blind = blind_of(truth)

        h1, h2 = per_mode_rarity(truth, args.rollouts, seed=args.seed + 50_000)
        r1, r1_lo, r1_hi = wilson_ci(h1, args.rollouts)
        r2, r2_lo, r2_hi = wilson_ci(h2, args.rollouts)

        pc = harness.play_cost(truth, blind, args.episodes, seed=args.seed)

        d40_p1 = pc["play_cost"] * (1 - r1) ** 40
        d40_p2 = pc["play_cost"] * (1 - r2) ** 40
        d40_joint = pc["play_cost"] * ((1 - r1) * (1 - r2)) ** 40

        row = {
            "k1": k1, "k2": k2,
            "r1": r1, "r1_ci": [r1_lo, r1_hi],
            "r2": r2, "r2_ci": [r2_lo, r2_hi],
            "j_truth": pc["j_truth"], "j_blind": pc["j_blind"],
            "j_random": pc["j_random"], "play_cost": pc["play_cost"],
            "blind_contact_rate": pc["blind_contact_rate"],
            "d40_p1": d40_p1, "d40_p2": d40_p2, "d40_joint": d40_joint,
            "n_episodes": pc["n_episodes"],
        }
        rows.append(row)
        print(f"{k1:5.1f} {k2:5.1f} {r1:7.4f} {r2:7.4f} {pc['j_truth']:8.2f} "
              f"{pc['j_blind']:8.2f} {pc['play_cost']:6.3f} {d40_joint:10.4f}",
              flush=True)

out = {"script": "continuous_patch2d.py", "params": vars(args),
       "rows": rows, "elapsed_s": round(time.time() - t0, 1)}
path = pathlib.Path("results/continuous_patch2d.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
