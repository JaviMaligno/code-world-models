"""Thin-neck ring mechanism sweep (V2-PROGRAM's last unrun item).

The knob: `neck` thins the band FROM OUTSIDE (r_out dips to r_in + neck inside
an angular sector; the hole d < r_in is invariant), which breaks Lemma 2's
metric hypothesis while leaving the topology alone -- beta_1 = 1 and the band
still separates the plane in the continuum at every neck > 0. Interior entry
requires a single step longer than `neck` (local crossing lemma,
`freeze_stays_outside_of_superset` in formal/Paper3Ring), and the max step is
(gain/drag)*dt = 1.0: neck = 1.2 is a theorem-zero control, thinner necks
admit leap-through at speed.

Measured per (neck, placement) cell, all on the truth env:
  - r, r_int          contact rarity / interior-entry rate (Wilson CIs)
  - leap forensics    per FIRST interior entry: the entering step's length,
                      the prior distance, the speed at entry, the entry step
                      index, and whether the rollout had any contact BEFORE
                      the entry (freeze-then-leap vs clean leap)
  - disagree_fill     transition disagreement of the filled model on the
                      first `disagree_rollouts` rollouts (gate-side
                      falsifiability of the wrong topology, as in the grid)
  - pc_blind, pc_fill paired MPC play_cost of the two wrong models

Pre-registered readings: docs/paper3/THIN-NECK-DESIGN.md. Checkpoints per
cell; a completed cell is never recomputed.

Run: PYTHONPATH=src python scripts/ring2d_thin_neck.py
     [--rollouts 30000] [--episodes 16] [--jobs 4]
"""
import argparse
import json
import math
import os
import pathlib
import random
import time
from concurrent.futures import ProcessPoolExecutor

from cwm.continuous.envs import RingField2D, blind_of, filled_of
from cwm.continuous import harness
from cwm.law import wilson_ci

_REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = _REPO / "results" / "ring2d_thin_neck.json"

NECKS = [0.1, 0.2, 0.4, 0.6, 0.8, 1.2]
CENTERS = {"facing": math.pi, "hidden": 0.0}


def knob_of(neck, placement) -> str:
    if neck is None:
        return "closed"
    return f"nk{neck:g}" + ("" if placement == "facing" else "-hid")


def env_of(neck, placement) -> RingField2D:
    if neck is None:
        return RingField2D()
    return RingField2D(neck=neck, neck_center=CENTERS[placement])


def measure(job):
    """Rarity + leap forensics + fill disagreement for one cell."""
    neck, placement, n, seed, n_disagree = job
    truth = env_of(neck, placement)
    filled = filled_of(truth)
    hits = entered = 0
    trans = disagree = 0
    leaps = []
    for i in range(n):
        rng = random.Random(seed + i)
        s = truth.initial_state(rng)
        hit = inside = False
        for t in range(truth.h_episode):
            a = rng.uniform(-truth.a_max, truth.a_max)
            st, _, c = truth.step(s, a)
            if i < n_disagree:
                sf, _, _ = filled.step(s, a)
                trans += 1
                if max(abs(x - y) for x, y in zip(st, sf)) > 1e-12:
                    disagree += 1
            if not inside and truth.in_interior(st[0], st[1]):
                # first interior entry of this rollout: leap forensics;
                # the rollout CONTINUES so r keeps the committed
                # full-rollout convention
                leaps.append({
                    "rollout": i, "t": t,
                    "step": math.hypot(st[0] - s[0], st[1] - s[1]),
                    "d_prev": math.hypot(s[0] - truth.center[0],
                                         s[1] - truth.center[1]),
                    "d_land": math.hypot(st[0] - truth.center[0],
                                         st[1] - truth.center[1]),
                    "speed": math.hypot(st[2], st[3]),
                    "contact_before": hit,
                })
                inside = True
            s = st
            hit = hit or c
        hits += hit
        entered += inside
    r, r_lo, r_hi = wilson_ci(hits, n)
    ri, ri_lo, ri_hi = wilson_ci(entered, n)
    return {
        "neck": neck, "placement": placement if neck is not None else None,
        "knob": knob_of(neck, placement),
        "r": r, "r_ci": [r_lo, r_hi], "contacts": hits,
        "r_interior": ri, "r_interior_ci": [ri_lo, ri_hi],
        "interior_entries": entered, "rollouts": n,
        "disagree_fill": (disagree / trans) if trans else None,
        "disagree_transitions": disagree, "transitions": trans,
        "disagree_rollouts": min(n, n_disagree),
        "leaps": leaps[:200],           # forensic detail, capped
        "n_leaps_recorded": min(len(leaps), 200),
        "leap_step_min": min((l["step"] for l in leaps), default=None),
        "leap_step_median": (sorted(l["step"] for l in leaps)[len(leaps) // 2]
                             if leaps else None),
        "n_clean_leaps": sum(1 for l in leaps if not l["contact_before"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rollouts", type=int, default=30_000)
    ap.add_argument("--episodes", type=int, default=16)
    ap.add_argument("--disagree-rollouts", type=int, default=4000,
                    help="rollouts on which the filled model's transition "
                    "disagreement is also measured (2x step cost)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    cells = [(None, "facing")] + [(nk, pl) for nk in NECKS for pl in CENTERS]
    doc = (json.loads(OUT.read_text()) if OUT.exists()
           else {"script": "ring2d_thin_neck.py", "params": vars(args),
                 "rows": []})
    done = {row["knob"] for row in doc["rows"]}
    todo = [(nk, pl) for nk, pl in cells if knob_of(nk, pl) not in done]
    print(f"{len(todo)} cell(s) to run ({len(done)} done), "
          f"{args.rollouts} rollouts each", flush=True)

    t0 = time.time()
    jobs = [(nk, pl, args.rollouts, args.seed + 50_000,
             args.disagree_rollouts) for nk, pl in todo]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for (nk, pl), row in zip(todo, pool.map(measure, jobs)):
            truth = env_of(nk, pl)
            pc_b = harness.play_cost(truth, blind_of(truth), args.episodes,
                                     seed=args.seed)
            pc_f = harness.play_cost(truth, filled_of(truth), args.episodes,
                                     seed=args.seed)
            row.update({
                "j_truth": pc_b["j_truth"], "j_blind": pc_b["j_blind"],
                "j_filled": pc_f["j_blind"], "j_random": pc_b["j_random"],
                "play_cost_blind": pc_b["play_cost"],
                "play_cost_filled": pc_f["play_cost"],
                "blind_contact_rate": pc_b["blind_contact_rate"],
                "filled_contact_rate": pc_f["blind_contact_rate"],
                "n_episodes": args.episodes,
            })
            doc["rows"].append(row)
            doc["elapsed_s"] = round(time.time() - t0, 1)
            tmp = OUT.with_name(OUT.name + ".tmp")
            tmp.write_text(json.dumps(doc, indent=2))
            os.replace(tmp, OUT)
            print(f"  {row['knob']:>10}  r={row['r']:.5f} "
                  f"r_int={row['r_interior']:.5f} "
                  f"({row['interior_entries']} entries, "
                  f"{row['n_clean_leaps']} clean) "
                  f"dis_fill={row['disagree_fill']:.6f} "
                  f"pc_b={row['play_cost_blind']:.3f} "
                  f"pc_f={row['play_cost_filled']:.3f}", flush=True)
    print(f"wrote {OUT}  [{doc['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
