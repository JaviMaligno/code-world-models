"""T7 (first half): the infinite-bar certificate for the censored sensor
(docs/paper3/THEORY.md, "T7 (first half)": Propositions C1-C3).

By Proposition C1, an infinite H1 bar of the censored Rips filtration can
only come from the censor (the plain filtration has none), and whether a
given (cloud, censor) has one is a finite computation. This script runs
that computation on the committed censored-filtration cells (gamma x
seeds 10000-50000, inside evidence). MEASURED FINDING (2026-07-25, the
inversion of the historical note): v1 ITSELF has infinite bars in 4/25
cells — the 3 gap-0 cells whose beta1=1 readings are the TRUE loop made
never-fillable (its fills cross the certified-free hole), plus gap-0.6
seed 40000, the single 19/20 specificity failure, now diagnosed as a
structural C2-type never-fillable cycle. The clearance-0.3 and
proximity-0.3 variants have 0/25 (their false loops are finite bridge
bars); the nested censors' 0 / 4 / 0 pattern is Proposition C3's
non-monotonicity measured directly.

Run: PYTHONPATH=src python scripts/t7_infinite_bar_certificate.py (~9 min)
"""
import importlib.util
import json
import math
import os
import pathlib
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D
from cwm.continuous.tda import dedupe, rips_persistence, subsample

# reuse the sensor's evidence + censor implementation verbatim
_spec = importlib.util.spec_from_file_location(
    "rcf", os.path.join(_REPO, "scripts", "ring2d_censored_filtration.py"))
rcf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcf)

t0 = time.time()
GAPS = [0.0, 0.6, 1.2, 1.8, 2.4]
SEEDS = [10000, 20000, 30000, 40000, 50000]   # the committed run's cells


def infinite_h1(points, free_segments):
    def edge_ok(p, q):
        return not any(rcf._crosses(p, q, a, b) for a, b in free_segments)
    bars = rips_persistence(points, edge_filter=edge_ok)["h1"]
    return sum(1 for b in bars if b[1] is None)


def _seg_dist(p1, p2, q1, q2):
    """Distance between two segments (0 if they intersect)."""
    from cwm.continuous.mitigation import _segments_intersect
    if _segments_intersect(p1, p2, q1, q2):
        return 0.0

    def pt_seg(p, a, b):
        ax, ay = b[0] - a[0], b[1] - a[1]
        L2 = ax * ax + ay * ay
        t = 0.0 if L2 == 0 else max(0.0, min(
            1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
        return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)
    return min(pt_seg(p1, q1, q2), pt_seg(p2, q1, q2),
               pt_seg(q1, p1, p2), pt_seg(q2, p1, p2))


def infinite_h1_proximity(points, free_segments, margin):
    def edge_ok(p, q):
        return not any(_seg_dist(p, q, a, b) < margin
                       for a, b in free_segments)
    bars = rips_persistence(points, edge_filter=edge_ok)["h1"]
    return sum(1 for b in bars if b[1] is None)


rows = []
v1_clean = m3_dirty = px_dirty = 0
for gap in GAPS:
    env = RingField2D(gap=gap, gap_center=math.pi,
                      x0_center=RingField2D().center)
    for seed in SEEDS:
        landings, free = rcf.evidence(env, seed)
        pts = subsample(dedupe(landings, 0.05), 90, 0)
        rcf.MARGIN = 0.0
        inf_v1 = infinite_h1(pts, free)
        rcf.MARGIN = 0.3
        inf_m3 = infinite_h1(pts, free)
        rcf.MARGIN = 0.0
        inf_px = infinite_h1_proximity(pts, free, 0.3)
        v1_clean += (inf_v1 == 0)
        m3_dirty += (inf_m3 > 0)
        px_dirty += (inf_px > 0)
        rows.append({"gap": gap, "seed": seed, "n_points": len(pts),
                     "inf_bars_v1": inf_v1, "inf_bars_margin03": inf_m3,
                     "inf_bars_proximity03": inf_px})
        print(f"gap={gap} seed={seed}: v1 = {inf_v1}, "
              f"clearance-0.3 = {inf_m3}, proximity-0.3 = {inf_px}",
              flush=True)
print(f"\ncertificate: v1 artifact-free in {v1_clean}/{len(rows)} cells; "
      f"clearance-0.3 infinite bars in {m3_dirty}/{len(rows)}; "
      f"proximity-0.3 infinite bars in {px_dirty}/{len(rows)}")
path = pathlib.Path("results/t7_infinite_bar_certificate.json")
path.write_text(json.dumps({"v1_clean_cells": v1_clean,
                            "clearance03_dirty_cells": m3_dirty,
                            "proximity03_dirty_cells": px_dirty,
                            "cells": len(rows), "rows": rows}, indent=1))
print(f"wrote {path}  ({time.time() - t0:.0f}s)")
