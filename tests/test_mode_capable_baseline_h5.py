"""Focused checks for the H5 learned event-function baseline."""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from mode_capable_baseline_h5 import (  # noqa: E402
    LearnedPatchEventModel, cart_contact_rows, circle_fit, cluster_separated_modes,
    learn_cart_threshold, learn_patch_regions, transition_metrics,
)
from cwm.continuous.contract import collect_transitions  # noqa: E402
from cwm.continuous.envs import CartWall, PatchField2D  # noqa: E402


def test_cart_event_is_unidentified_without_contacts_and_exact_with_one():
    env = CartWall(x_wall=8.0)
    free = collect_transitions(env, 40, seed=10_000)
    containing = collect_transitions(env, 40, seed=20_000)
    assert learn_cart_threshold(free) is None
    first_contact = next(t for t in containing if t["contact"])
    assert learn_cart_threshold([first_contact]) == 8.0
    # The learner reconstructs the event from transition disagreement; it does
    # not consume the internal contact label used by the experimental harness.
    unlabelled = [{k: v for k, v in first_contact.items() if k != "contact"}]
    assert len(cart_contact_rows(unlabelled)) == 1
    assert learn_cart_threshold(unlabelled) == 8.0


def test_exact_circle_is_in_the_fitted_hypothesis_class():
    points = [(4.0, 0.0), (3.0, 1.0), (2.0, 0.0), (3.0, -1.0)]
    cx, cy, radius = circle_fit(points)
    assert cx == pytest.approx(3.0, abs=1e-12)
    assert cy == pytest.approx(0.0, abs=1e-12)
    assert radius == pytest.approx(1.0, abs=1e-12)


def test_spatial_gap_separates_two_event_modes():
    groups = cluster_separated_modes([(2.1, 0.0), (3.8, 0.0),
                                      (6.1, 0.0), (7.8, 0.0)])
    assert [len(g) for g in groups] == [2, 2]


def test_patch_model_is_bit_exact_off_its_learned_modes():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    model = LearnedPatchEventModel(env, ((3.0, 0.0, 1.0), (7.0, 0.0, 1.0)))
    sample = collect_transitions(env, 2, seed=999_000)
    metrics = transition_metrics(env, model, sample)
    assert metrics["exact_transition_fraction"] == 1.0
    assert metrics["off_mode_exact_fraction"] == 1.0


def test_real_patch_sample_produces_a_finite_near_region():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    sample = collect_transitions(env, 40, seed=10_000)
    regions, evidence = learn_patch_regions(env, sample)
    assert evidence["n_contacts"] > 0
    assert regions
    assert all(len(r) == 3 and r[2] > 0 for r in regions)


def test_versioned_result_has_statement_contract_if_present():
    path = REPO / "results" / "mode_capable_baseline_h5.json"
    if not path.exists():
        pytest.skip("run scripts/mode_capable_baseline_h5.py")
    result = json.loads(path.read_text())
    assert result["schema_version"] == 1
    assert result["claim_contract"]["label"] == "measured"
    assert result["claim_contract"]["experimental_unit"] == "training seed block"
    assert result["cart"]["hypothesis_class_contains_truth"] is True
    assert result["patch2d"]["hypothesis_class_contains_truth"] is True
