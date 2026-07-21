"""Driver tests: naming must match the harness's real files; resume must
skip complete cells; --dry-run must plan without spending money."""
import json
import pathlib
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

import continuous_ring2d_open_sweep as drv


def test_target_path_matches_existing_harness_files():
    # These two files exist in results/ — produced by the harness itself.
    assert drv.target_path("mini", 0.6, "facing", "inside", "tda") == \
        "results/continuous_synthesis_ring2d_mini_gap0.6-in_pv-tda.json"
    assert drv.target_path("mini", 0.6, "facing", "outside", "default") == \
        "results/continuous_synthesis_ring2d_mini_gap0.6.json"
    assert drv.target_path("large", 1.2, "hidden", "outside", "default") == \
        "results/continuous_synthesis_ring2d_large_gap1.2-hid.json"


def test_phase_grids_match_spec():
    p0 = plan_index(drv.plan_for_phase(0))
    assert p0 == {("mini", 1.8, "facing", "inside", "tda", 3),
                  ("mini", 0.2, "facing", "outside", "default", 3)}
    p1 = plan_index(drv.plan_for_phase(1))
    assert ("mini", 0.05, "facing", "outside", "default", 20) in p1
    assert ("mini", 1.8, "facing", "inside", "tda", 30) in p1
    assert ("mini", 0.6, "hidden", "outside", "default", 10) in p1
    assert len([c for c in p1 if c[2] == "hidden"]) == 2
    p2 = plan_index(drv.plan_for_phase(2))
    assert p2 == {("large", 0.1, "facing", "outside", "default", 20),
                  ("large", 0.6, "facing", "outside", "default", 20),
                  ("large", 0.6, "facing", "inside", "tda", 20),
                  ("large", 2.4, "facing", "inside", "tda", 20)}


def plan_index(plan):
    return {(c["size"], c["gap"], c["channel"], c["start"], c["variant"],
             c["n_seeds"]) for c in plan}


def test_seeds_missing_skips_complete_files(tmp_path):
    f = tmp_path / "cells.json"
    cells = [{"arm": "incomplete", "seed": 10_000 * (i + 1)} for i in range(3)]
    f.write_text(json.dumps({"cells": cells}))
    assert drv.seeds_missing(str(f), 3) is False      # complete -> skip
    assert drv.seeds_missing(str(f), 5) is True       # top-up needed
    assert drv.seeds_missing(str(tmp_path / "nope.json"), 1) is True


def test_dry_run_spends_nothing():
    out = subprocess.run(
        [sys.executable, "scripts/continuous_ring2d_open_sweep.py",
         "--phase", "1", "--dry-run"],
        cwd=_REPO, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0
    # every planned cell appears as RUN or SKIP with its target file
    assert "continuous_synthesis_ring2d_mini_gap0.05.json" in out.stdout
    assert "RUN" in out.stdout and "gap1.8-in_pv-tda" in out.stdout
