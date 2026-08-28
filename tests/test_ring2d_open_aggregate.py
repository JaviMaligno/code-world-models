"""Oracle tests for the freeze-mask classifier and boundary-parameter
extraction, plus an end-to-end aggregate smoke test on a fixture file."""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

from ring2d_artifact_audit import freeze_mask_class
import ring2d_open_aggregate as agg

_INTEGRATOR = '''
import math
def step(state, action):
    x, y, vx, vy = state
    a = min(1.0, max(-1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0*math.cos(phi) - 0.3*vx)*0.1
    vy2 = vy + (3.0*math.sin(phi) - 0.3*vy)*0.1
    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]
def reward(state):
    return 0.0
'''


def _with_freeze(condition):
    """Integrator + freeze when `condition` (an expression in x, y) holds."""
    return _INTEGRATOR.replace(
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
        f"    if {condition}:\n"
        f"        return [x, y, 0.0, 0.0]\n"
        f"    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]")


def test_classifier_oracle_classes():
    cases = {
        "blind": _INTEGRATOR,
        "loop": _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1"),
        "disc": _with_freeze("math.hypot(x-12.0, y) <= 5.1"),
        "complement": _with_freeze("math.hypot(x-12.0, y) >= 3.5"),
        "fill-unbounded": _with_freeze("x >= 7.0"),
        "arc": _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1 "
                            "and abs(math.atan2(y, x-12.0)) <= 1.0"),
    }
    for expected, code in cases.items():
        got, _ = freeze_mask_class(code)
        assert got == expected, f"{expected}: classifier said {got}"


def test_classifier_vdep_velocity_superstition():
    code = _INTEGRATOR.replace(
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
        "    if math.hypot(vx2, vy2) > 1.0:\n"
        "        return [x, y, 0.0, 0.0]\n"
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]")
    got, _ = freeze_mask_class(code)
    assert got == "vdep"


def test_boundary_params_recover_the_annulus():
    p = agg.freeze_boundary_params(
        _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1"))
    assert abs(p["r_lo"] - 3.4) < 0.25 and abs(p["r_hi"] - 5.1) < 0.25
    assert p["ang_cov"] >= 0.97 and p["max_ang_gap_rad"] < 0.4


def test_boundary_params_see_the_arc_gap():
    p = agg.freeze_boundary_params(
        _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1 "
                     "and not (abs(math.atan2(y, x-12.0) - math.pi) < 0.6 "
                     "or abs(math.atan2(y, x-12.0) + math.pi) < 0.6)"))
    # a 1.2-rad channel centered at pi must show up as the largest gap
    assert p["max_ang_gap_rad"] > 0.8


def test_aggregate_smoke(tmp_path, monkeypatch):
    fixture = {
        "params": {"gap": 0.2, "channel": "facing", "start": "inside",
                   "prompt_variant": "tda"},
        "size": "mini", "model": "gpt-test",
        "j_truth": 10.0, "j_random": 1.0,
        "cells": [
            {"arm": "incomplete", "seed": 10000, "n_rollouts": 40,
             "eps": 1e-9, "sample_contains_wall": True,
             "gate_accuracy": 0.5, "gate_passed": False,
             "wall_blindness": None,
             "code": agg.BLIND_CODE,
             "guidance_text": "- persistent-homology check: beta_1 = 1.",
             "history": [{"code": agg.BLIND_CODE, "gate_accuracy": 0.5}]},
        ],
    }
    f = tmp_path / "continuous_synthesis_ring2d_mini_gap0.2-in_pv-tda.json"
    f.write_text(json.dumps(fixture))
    summary = agg.build_summary([str(f)], curve_path=None)
    row = summary["synthesis"]["0.2"]
    assert row["n"] == 1 and row["gate_pass"] == 0
    art = summary["artifacts"][0]
    assert art["class"] == "blind" and art["guidance_beta1"] == 1
    assert art["history_classes"] == ["blind"]


def _outside_cell(seed, mode_absent):
    """A minimal outside-start danger cell (env-determined identifiability)."""
    return {"arm": "incomplete", "seed": seed, "n_rollouts": 40, "eps": 1e-9,
            "sample_contains_wall": not mode_absent,
            "gate_accuracy": 1.0 if mode_absent else 0.9997,
            "gate_passed": mode_absent, "wall_blindness": 1.0 if mode_absent else None,
            "play_cost": 0.35 if mode_absent else None,
            "code": agg.BLIND_CODE}


def test_danger_dedups_seed_identical_samples_across_sizes(tmp_path):
    """mini and large files at the same (gap, channel) share seeds and draw
    byte-identical samples (sample_contains_wall is env-determined). The danger
    Wilson CI must count each unique seed ONCE (n = unique seeds), not pool the
    files as independent — else n and the CI are pseudo-replicated. play_cost is
    model-dependent, so pc_values keeps every artifact."""
    seeds_absent = {10000: True, 20000: True, 30000: False}  # 2/3 mode-absent
    files = []
    for size in ("mini", "large"):
        fx = {"params": {"gap": 0.1, "channel": "facing", "start": "outside",
                         "prompt_variant": "default"},
              "size": size, "model": f"gpt-{size}", "j_truth": 10.0,
              "j_random": 1.0,
              "cells": [_outside_cell(s, a) for s, a in seeds_absent.items()]}
        p = tmp_path / f"continuous_synthesis_ring2d_{size}_gap0.1.json"
        p.write_text(json.dumps(fx))
        files.append(str(p))
    d = agg.build_summary(files, curve_path=None)["danger"]["0.1|facing"]
    assert d["n"] == 3            # unique seeds, NOT 6 (two files pooled)
    assert d["mode_absent"] == 2  # deduped, NOT 4
    assert d["n_artifacts"] == 6  # every artifact still counted for context
    assert len(d["pc_values"]) == 4   # model-dependent: 2 absent x 2 sizes
    assert "_seeds" not in d       # helper set stripped before serialization
    lo, hi = d["wilson"][1], d["wilson"][2]
    assert 0.0 <= lo <= hi <= 1.0
