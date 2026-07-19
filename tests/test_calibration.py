import json, subprocess, sys, math
from cwm.continuous.calibration import validate_calibration_artifact, EXPECTED_CELL_IDS

def _full_cells():
    return [{"id": cid, "family": "circle", "R": 1.0, "offset": 3.0, "rarity": 0.15,
             "rarity_ci": [0.12, 0.18], "n_rollouts": 400, "n_episodes": 30, "play_cost_blind": 0.99,
             "grid_delta_256_512": 0.004, "provenance": "measured"} for cid in EXPECTED_CELL_IDS]

def _good_artifact():
    return {"box": [[-8,14],[-6,6]], "grid_n": 256, "rarity_target": 0.15, "rarity_tol": 0.05,
            "frac_planner_outside_box": 0.01, "frac_outside_box_bound": 0.05,
            "cal_seed_stream": 1, "val_seed_stream": 2, "delta": 0.12, "delta_provenance": "median_normal_bracket",
            "sufficiency": {"certified": False, "tau_s": None, "reason": "conservative upper bound deferred to Phase B"},
            "repaired_threshold": {"band_disagreement": 0.05, "fpr": 0.05, "source": "truth_oracle_fullarm_griderror"},
            "provenance": {"box": "fixed", "grid_n": "fixed", "rarity_target": "fixed", "delta": "measured",
                           "repaired_threshold": "truth_oracle_fullarm_griderror", "frac_planner_outside_box": "measured"},
            "cells": _full_cells()}

def test_validator_rejects_placeholder():
    placeholder = {"box": [[-8,14],[-6,6]], "grid_n": 256, "delta": None, "cells": [],
                   "sufficiency": {"certified": False, "tau_s": 0.1, "reason": ""},  # tau_s must be null
                   "repaired_threshold": {"source": "incomplete_anchor"}, "frac_planner_outside_box": 0.0}
    problems = validate_calibration_artifact(placeholder)
    assert any("cell" in p.lower() for p in problems)      # manifest mismatch (empty)
    assert any("delta" in p.lower() for p in problems)     # None
    assert any("source" in p.lower() for p in problems)    # bad provenance
    assert any("tau" in p.lower() or "sufficiency" in p.lower() for p in problems)  # tau_s not null

def test_validator_rejects_missing_one_cell():
    art = _good_artifact(); art["cells"] = art["cells"][:-1]  # drop a manifest cell
    assert any("cell" in p.lower() for p in validate_calibration_artifact(art))

def test_validator_rejects_equal_seed_streams():
    art = _good_artifact(); art["val_seed_stream"] = art["cal_seed_stream"]
    assert any("seed" in p.lower() for p in validate_calibration_artifact(art))

def test_validator_accepts_full_artifact():
    assert validate_calibration_artifact(_good_artifact()) == []

# --- SMOKE test: --quick fills the schema; scientific validation is only for the full artifact ---
def test_calibration_quick_smoke_schema(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, "scripts/calibrate_shape2d.py", "--quick", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    art = json.loads(out.read_text())
    assert set(c["id"] for c in art["cells"]) == EXPECTED_CELL_IDS  # schema/manifest present
    assert art["sufficiency"]["tau_s"] is None
    # NOTE: --quick may not meet rarity/play_cost tolerances with few episodes; strict
    # validate_calibration_artifact is asserted only on the FULL run, below.

def test_validator_rejects_non_numeric_numeric_field():
    # A non-numeric string in a numeric field must not silently skip its
    # threshold check -- it must be flagged as a type problem instead.
    art = _good_artifact()
    art["cells"][0]["n_rollouts"] = "big"
    problems = validate_calibration_artifact(art)
    assert any("n_rollouts" in p and "numeric" in p.lower() for p in problems)

def test_validator_rejects_bool_in_numeric_field():
    # bool is a subclass of int in Python -- it must still be rejected as
    # non-numeric for a field like n_rollouts, not silently accepted.
    art = _good_artifact()
    art["cells"][0]["n_rollouts"] = True
    problems = validate_calibration_artifact(art)
    assert any("n_rollouts" in p and "numeric" in p.lower() for p in problems)

def test_full_calibration_passes_strict_validation():
    import os, pytest
    path = "results/shape2d_calibration.json"
    if not os.path.exists(path):
        pytest.skip("full calibration artifact not generated yet (run scripts/calibrate_shape2d.py)")
    assert validate_calibration_artifact(json.load(open(path))) == []  # the scientific gate on the committed artifact
