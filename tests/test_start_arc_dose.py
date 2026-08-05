"""Tests for the coverage dose on PatchField2D's start distribution (`--start-arc`).

Distinct from `tests/test_evidence_dose.py`, which covers the controlled-sample apparatus in
`cwm.continuous.evidence_dose`: that one varies WHICH transitions the synthesizer is shown,
this one varies WHERE the episodes begin, and so the angular coverage of the contacts the
rollouts produce. This is the 2D program's one treatment whose direction was recorded before
the run (docs/paper2/PRESPEC-LEDGER.md, B21).

A dose is only a dose if it moves the thing it claims to move and nothing else. Two tests are
therefore about the intervention rather than the result:

  * the contract text must be IDENTICAL across arms, or the wider start ring would be
    TELLING the synthesizer something rather than SHOWING it something;
  * `start_arc_deg=None` must reproduce the committed box start bit for bit, or every
    already-run campaign silently becomes a different experiment -- which has happened once
    in this instrument's history, through a reworded slab clause.
"""
import json
import math
import pathlib
import random
import subprocess
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D                      # noqa: E402
from cwm.continuous.contract import (build_contract,              # noqa: E402
                                     collect_transitions)

_RES = _REPO / "results"
ARCS = (120.0, 240.0)


def _env(arc=None):
    return PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), start_arc_deg=arc)


# --- the intervention -------------------------------------------------------------- #
@pytest.mark.parametrize("arc", ARCS)
@pytest.mark.parametrize("include_mode", [True, False])
def test_the_dose_does_not_leak_into_the_contract(arc, include_mode):
    """The dose is evidence, not instruction: the rules text cannot depend on it."""
    assert build_contract(_env(arc), include_mode) == \
        build_contract(_env(None), include_mode)


def test_the_default_start_is_unchanged_bit_for_bit():
    old = subprocess.run(["git", "show", "HEAD:src/cwm/continuous/envs.py"],
                         capture_output=True, text=True, cwd=_REPO).stdout
    if not old:
        pytest.skip("no git HEAD to compare against")
    ns = {}
    exec(compile(old.replace("from .shapes import", "from cwm.continuous.shapes import"),
                 "committed", "exec"), ns)                        # noqa: S102 — our own
    committed = ns["PatchField2D"](p1=(3.0, 0.0), p2=(7.0, 0.0))
    for seed in (10_000, 70_000, 200_000):
        a = collect_transitions(committed, 6, seed=seed)
        b = collect_transitions(_env(None), 6, seed=seed)
        assert len(a) == len(b) and a  # non-vacuous
        for ta, tb in zip(a, b):
            assert ta["state"] == tb["state"] and ta["action"] == tb["action"]
            assert ta["next_state"] == tb["next_state"]


@pytest.mark.parametrize("arc", ARCS)
def test_the_ring_start_is_outside_the_patch_and_inside_the_arc(arc):
    """Otherwise episodes would begin already frozen and the sample would show no entry."""
    env = _env(arc)
    rng = random.Random(1234)
    for _ in range(200):
        x, y = env.initial_state(rng)[:2]
        assert not env._inside(x, y, env.p1), "an episode starts inside the near patch"
        assert not env._inside(x, y, env.p2)
        bearing = math.degrees(math.atan2(y - env.p1[1], x - env.p1[0]))
        offset = abs((bearing - 180.0 + 180.0) % 360.0 - 180.0)   # arc centred on 180 deg
        assert offset <= arc / 2 + 1e-6, f"bearing {bearing:.1f} outside the {arc}-deg arc"


# --- the calibration --------------------------------------------------------------- #
def _cal():
    f = _RES / "evidence_dose_calibration.json"
    if not f.exists():
        pytest.skip("run scripts/calibrate_evidence_dose.py")
    return json.loads(f.read_text())


@pytest.mark.parametrize("arc", ARCS)
def test_each_dose_arm_is_admissible_on_every_criterion(arc):
    """Coverage raised, contacts matched, every block firing, and the trap intact."""
    a = _cal()["arms"][f"arc{arc:g}"]
    assert a["admissible"]["all"] is True, a["admissible"]


def test_the_unused_wide_arm_is_recorded_as_inadmissible():
    """Non-vacuity: the criteria have to be able to reject something. The 360-deg arm is
    the one they reject -- its contact count does not match -- and it is not used."""
    cal = _cal()
    if "arc360" not in cal["arms"]:
        pytest.skip("the 360-deg arm was not swept")
    a = cal["arms"]["arc360"]
    assert a["admissible"]["all"] is False
    assert a["admissible"]["contacts_matched"] is False


def test_the_dose_raises_coverage_while_holding_the_contact_count():
    f = _RES / "region_fit_baseline.json"
    if not f.exists():
        pytest.skip("run scripts/region_fit_baseline.py")
    arms = json.loads(f.read_text())["dose_arms"]
    base, wide = arms["default"], arms["arc240"]
    assert abs(base["median_contacts"] - wide["median_contacts"]) <= 3
    assert wide["median_landing_arc_deg"] > base["median_landing_arc_deg"] + 50


# --- the outcome -------------------------------------------------------------------- #
def _abl():
    f = _RES / "arity_evidence_ablations.json"
    if not f.exists():
        pytest.skip("run scripts/arity_evidence_ablations.py")
    return json.loads(f.read_text())["campaigns"]


def test_the_evidence_determines_the_region_on_every_dose_sample():
    """The premise of the null: a three-line fit is exact at this coverage, so the failure
    cannot be charged to the evidence."""
    f = _RES / "region_fit_baseline.json"
    if not f.exists():
        pytest.skip("run scripts/region_fit_baseline.py")
    arms = json.loads(f.read_text())["dose_arms"]
    assert arms["arc240"]["n_recovering_both"] == 20
    # and it is a RESPONSE to the dose, not a fluke of one arm
    assert (arms["default"]["n_recovering_both"]
            <= arms["arc120"]["n_recovering_both"]
            <= arms["arc240"]["n_recovering_both"])


@pytest.mark.parametrize("camp", ["dose_arc240", "dose_arc240_hint", "dose_arc120"])
def test_no_dose_arm_restores_repair(camp):
    c = _abl()
    if camp not in c:
        pytest.skip(f"{camp} has not been analysed")
    per = c[camp]["per_size"]["large"]
    assert per["n_mode_containing"] == 20
    assert per["k_repaired_behavioural"] == 0
    assert per["k_repaired_gate_and_probe"] == 0


def test_the_translation_arm_still_succeeds_on_the_wider_sample():
    """Without this the null would be about the instrument rather than the induction."""
    c = _abl()
    if "dose_arc240" not in c:
        pytest.skip("dose_arc240 has not been analysed")
    per = c["dose_arc240"]["per_size"]["large"]
    if per["n_full"] == 0:
        pytest.skip("the full arm was not run at this arc")
    assert per["n_full"] == per["full_gate_passed"] == 20
    assert per["full_zero_iterations"] == 20 and per["full_mode_encoded"] == 20


def test_the_dose_is_its_own_treatment_in_the_statistics():
    """Third instance of one omission: a sample-changing knob left out of the treatment key
    collapses arms into one cell. The key must separate all five of these."""
    sys.path.insert(0, str(_REPO / "scripts"))
    from paper2_statistics import treatment_key
    base = {"instrument": "patch2d", "knob": {"k1": 3, "k2": 7}, "patch_shape": "disc",
            "prompt_variant": "default", "max_iters": 5, "arm": "incomplete",
            "mode_effect": "freeze", "mode_hint": None, "start_arc": None,
            "n_rollouts": 40}
    keys = {treatment_key(base)}
    for arc in ARCS:
        for hint in (None, "centre"):
            keys.add(treatment_key({**base, "start_arc": arc, "n_rollouts": 15,
                                    "mode_hint": hint}))
    assert len(keys) == 5, keys
