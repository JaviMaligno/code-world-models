"""RingField2D mechanism arm: the three-regime table (paper 3, rung 2).

Grid: gap x channel orientation x start placement, two wrong models each:
  - blind  (no ring): the mode-omission axis, as in papers 1-2
  - filled (disc):    the wrong-TOPOLOGY axis, new here
Measured per cell:
  - r, r_int          per-rollout mode rarity / interior-entry rate
  - disagree_fill     fraction of random-rollout transitions where the filled
                      model's step() differs from truth (sup-norm > 1e-12) —
                      the gate-side falsifiability of the wrong topology:
                      0.0 means every sampling gate certifies it (Prop 1),
                      > 0 means a size-N gate refutes it w.p. 1-(1-hit)^N
  - pc_blind, pc_fill paired MPC play_cost of each wrong model

The expected structure (docs/paper3/RESEARCH-DIRECTION.md §4.1): the filled
model walks through unfalsifiable+harmless (gap 0, outside) ->
falsifiable+costly (gap > 0 hidden channel) -> instantly-falsified (inside
start); the blind model stays exploited except when the channel faces the
start (the aligned-channel degeneracy, a mechanism datum in itself).

Run: PYTHONPATH=src python scripts/continuous_ring2d_mechanism.py  (~20 min)
"""
import argparse
import itertools
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import RingField2D, blind_of, filled_of
from cwm.continuous import harness
from cwm.law import wilson_ci

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--gaps", type=float, nargs="+", default=[0.0, 0.6, 1.2])
ap.add_argument("--rollouts", type=int, default=400)
ap.add_argument("--episodes", type=int, default=16)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

BASE = RingField2D()
STARTS = {"outside": (0.0, 0.0), "inside": BASE.center}
CENTERS = {"facing": math.pi, "hidden": 0.0}


def sweep_rollouts(truth, filled, n, seed):
    """One pass of random rollouts measuring rarity, interior entry, and the
    filled model's transition disagreement rate on the same trajectories."""
    hits = entered = 0
    trans = disagree = 0
    for i in range(n):
        rng = random.Random(seed + i)
        s = truth.initial_state(rng)
        hit = inside = False
        for _ in range(truth.h_episode):
            a = rng.uniform(-truth.a_max, truth.a_max)
            st, _, c = truth.step(s, a)
            sf, _, _ = filled.step(s, a)
            trans += 1
            if max(abs(x - y) for x, y in zip(st, sf)) > 1e-12:
                disagree += 1
            s = st
            hit = hit or c
            inside = inside or truth.in_interior(s[0], s[1])
        hits += hit
        entered += inside
    return hits, entered, disagree, trans


t0 = time.time()
rows = []
print(f"{'gap':>5} {'chan':>7} {'start':>8} {'r':>7} {'r_int':>7} "
      f"{'dis_fill':>9} {'pc_blind':>8} {'pc_fill':>8}", flush=True)
for gap, (cname, gcenter), (sname, x0c) in itertools.product(
        args.gaps, CENTERS.items(), STARTS.items()):
    if gap == 0.0 and cname == "hidden":
        continue    # gap 0 has no channel; one orientation row suffices
    truth = RingField2D(gap=gap, gap_center=gcenter, x0_center=x0c)
    h, e, dis, ntr = sweep_rollouts(truth, filled_of(truth),
                                    args.rollouts, args.seed + 50_000)
    r, r_lo, r_hi = wilson_ci(h, args.rollouts)
    ri, _, _ = wilson_ci(e, args.rollouts)

    pc_b = harness.play_cost(truth, blind_of(truth), args.episodes,
                             seed=args.seed)
    pc_f = harness.play_cost(truth, filled_of(truth), args.episodes,
                             seed=args.seed)
    row = {
        "gap": gap, "channel": cname, "start": sname,
        "r": r, "r_ci": [r_lo, r_hi], "r_interior": ri,
        "disagree_fill": dis / ntr, "disagree_transitions": dis,
        "transitions": ntr,
        "j_truth": pc_b["j_truth"], "j_blind": pc_b["j_blind"],
        "j_filled": pc_f["j_blind"], "j_random": pc_b["j_random"],
        "play_cost_blind": pc_b["play_cost"],
        "play_cost_filled": pc_f["play_cost"],
        "blind_contact_rate": pc_b["blind_contact_rate"],
        "filled_contact_rate": pc_f["blind_contact_rate"],
        "n_episodes": args.episodes, "rollouts": args.rollouts,
    }
    rows.append(row)
    print(f"{gap:5.2f} {cname:>7} {sname:>8} {r:7.4f} {ri:7.4f} "
          f"{row['disagree_fill']:9.6f} {row['play_cost_blind']:8.3f} "
          f"{row['play_cost_filled']:8.3f}", flush=True)

out = {"script": "continuous_ring2d_mechanism.py", "params": vars(args),
       "rows": rows, "elapsed_s": round(time.time() - t0, 1)}
path = pathlib.Path("results/continuous_ring2d_mechanism.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
