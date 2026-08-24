"""Per-rollout rarity r and interior-entry rate r_int for EVERY ring2d
configuration that a committed synthesis campaign actually used.

Why this exists. `heldout_gate_audit.py` refuses to audit a campaign whose
env_key has no calibrated entry in `heldout.R_SOURCES`, and when this was
written no ring2d configuration had one -- so paper 3's 31 campaigns (663
artifacts) sat outside the held-out audit. (RESOLVED 2026-08-24: the entries
exist now, built from this file's output with r -- the FIRING rarity -- as
the prediction's argument and r_int carried as labelled provenance; the
reasoning is with the entries in heldout.py.) The existing calibration
(`results/continuous_ring2d.json`) does not close that: it covers 3 gap values
of the ~14 configurations in use, at 600 rollouts against the 30k that paper
2's own rarities were measured with (see the `note` fields in R_SOURCES).

What this script does and does NOT do. It MEASURES, at the campaigns' own
configurations and at matching precision, and writes both quantities with
Wilson intervals. It does not write R_SOURCES, because which quantity belongs
there is a question about the paper, not about the data: paper 3 treats r and
r_int as two different curves ("the gamma-curves ARE r(gamma) and
r_int(gamma)", THEORY.md), r is the firing rarity the danger law takes as its
argument, and r_int is the interior-entry rate that Lemma 2 says is 0 at
gap = 0. Picking one is a modelling decision; this file is its input.

Configurations are DISCOVERED from results/, not typed: whatever the campaigns
ran is what gets measured, so a config added later cannot be silently missed.

Run: PYTHONPATH=src python scripts/ring2d_rarity_sweep.py [--rollouts 30000]
     [--jobs 4]   (~5 h at the defaults on 4 workers; --rollouts 600 for a
     smoke run in ~2 min)
"""
import argparse
import json
import math
import pathlib
import random
import time
from concurrent.futures import ProcessPoolExecutor

from cwm.continuous.envs import RingField2D
from cwm.law import wilson_ci

_REPO = pathlib.Path(__file__).resolve().parents[1]
RESULTS = _REPO / "results"
OUT = RESULTS / "ring2d_rarity_sweep.json"

# The fields of `params` that define a ring2d ROLLOUT STREAM. Kept as an
# explicit list because that is what the eventual env_key branch has to key on:
# the slab/square collision (tests/test_heldout_gate.py) happened by leaving a
# stream-defining field out of the key, and ring2d has five of them.
STREAM_FIELDS = ("gap", "channel", "start", "ring_norm", "multi")


def config_of(params: dict) -> dict:
    """The stream-defining subset, with the synthesis script's own defaults."""
    return {
        "gap": float(params.get("gap", 0.0)),
        "channel": params.get("channel", "facing"),
        "start": params.get("start", "outside"),
        "ring_norm": params.get("ring_norm", "euclid"),
        "multi": bool(params.get("multi", False)),
    }


def env_of(cfg: dict) -> RingField2D:
    """Rebuild the truth env EXACTLY as scripts/continuous_danger_synthesis.py
    does for --instrument ring2d (that block is the definition; any drift here
    would calibrate a different instrument from the one that was run)."""
    c = RingField2D().center
    x0 = {"outside": (0.0, 0.0), "inside": c,
          "middle": (c[0] - 6.25, c[1])}[cfg["start"]]
    return RingField2D(
        gap=cfg["gap"],
        gap_center=math.pi if cfg["channel"] == "facing" else 0.0,
        x0_center=x0,
        norm=cfg["ring_norm"],
        r_in2=7.5 if cfg["multi"] else None,
        r_out2=9.0 if cfg["multi"] else None)


def knob_of(cfg: dict) -> str:
    """The campaign's own KNOB string, so a row can be matched to its files."""
    return (("sq" if cfg["ring_norm"] == "cheby" else "")
            + f"gap{cfg['gap']:g}"
            + ("-m2" if cfg["multi"] else "")
            + ("" if cfg["channel"] == "facing" else "-hid")
            + {"outside": "", "inside": "-in", "middle": "-mid"}[cfg["start"]])


def discover() -> dict:
    """Every distinct ring2d configuration in results/, with its files."""
    found = {}
    for path in sorted(RESULTS.glob("continuous_synthesis_ring2d_*.json")):
        params = json.loads(path.read_text()).get("params", {})
        if params.get("instrument") != "ring2d":
            continue
        cfg = config_of(params)
        key = json.dumps(cfg, sort_keys=True)
        found.setdefault(key, {"config": cfg, "files": [], "cells": 0})
        found[key]["files"].append(path.name)
        found[key]["cells"] += len(json.loads(path.read_text()).get("cells", []))
    return found


def measure(job: tuple) -> dict:
    """(mode fired, interior entered) over n random rollouts.

    Identical loop to continuous_ring2d.py's rarity_and_interior, including the
    +50_000 seed offset, so a shared configuration reproduces that file's
    number instead of merely resembling it."""
    cfg, n, seed = job
    truth = env_of(cfg)
    hits = entered = 0
    for i in range(n):
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
    r, r_lo, r_hi = wilson_ci(hits, n)
    ri, ri_lo, ri_hi = wilson_ci(entered, n)
    return {"config": cfg, "knob": knob_of(cfg),
            "r": r, "r_ci": [r_lo, r_hi], "mode_firings": hits,
            "r_interior": ri, "r_interior_ci": [ri_lo, ri_hi],
            "interior_entries": entered, "rollouts": n}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rollouts", type=int, default=30_000,
                    help="matches the 30k the R_SOURCES entries were measured with")
    ap.add_argument("--jobs", type=int, default=4,
                    help="worker processes; kept low on purpose, this machine "
                         "drops work when saturated")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    found = discover()
    if not found:
        raise SystemExit("no ring2d synthesis campaigns in results/")
    print(f"{len(found)} distinct configurations, "
          f"{sum(v['cells'] for v in found.values())} artifacts, "
          f"{args.rollouts} rollouts each, {args.jobs} workers", flush=True)

    t0 = time.time()
    jobs = [(v["config"], args.rollouts, args.seed + 50_000)
            for v in found.values()]
    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(measure, jobs):
            key = json.dumps(row["config"], sort_keys=True)
            row["files"] = found[key]["files"]
            row["n_artifacts"] = found[key]["cells"]
            rows.append(row)
            print(f"  {row['knob']:>16}  r={row['r']:.5f} "
                  f"[{row['r_ci'][0]:.5f},{row['r_ci'][1]:.5f}]  "
                  f"r_int={row['r_interior']:.5f} "
                  f"({row['interior_entries']} entries)", flush=True)

    rows.sort(key=lambda d: d["knob"])
    out = {"script": "ring2d_rarity_sweep.py",
           "params": vars(args),
           "stream_fields": list(STREAM_FIELDS),
           "rows": rows,
           "elapsed_s": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
