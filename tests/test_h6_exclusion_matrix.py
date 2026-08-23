import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("h6", ROOT / "scripts/h6_exclusion_matrix.py")
H6 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H6)


def test_matrix_is_complete_and_ordered():
    data = H6.build()
    assert [r["id"] for r in data["rows"]] == list(range(1, 9))
    required = {"target_hypothesis", "changed_variables", "unavoidable_cochanges",
                "prediction_status", "experimental_unit", "positive_control", "result",
                "licensed_inference", "not_licensed"}
    assert all(required <= set(row) for row in data["rows"])


def test_unidentifiable_arity_is_not_counted_as_exclusion():
    row = H6.build()["rows"][3]
    assert "none about arity" in row["licensed_inference"]
    assert any("observationally non-identifiable" in item
               for item in row["unavoidable_cochanges"])


def test_only_coverage_direction_was_recorded_before_run():
    rows = H6.build()["rows"]
    assert [r["id"] for r in rows if "B21" in r["prediction_status"]] == [8]
    assert "not preregistered" in rows[7]["prediction_status"]


def test_key_controls_and_negatives_are_derived():
    rows = H6.build()["rows"]
    assert "0/40 behavioural repairs" in rows[5]["result"]
    assert "0/40 behavioural repairs" in rows[6]["result"]
    assert "0/40 behavioural repairs" in rows[7]["result"]
    assert "20/20" in rows[7]["positive_control"]


def test_committed_result_is_fresh():
    expected = json.dumps(H6.build(), indent=2, sort_keys=True) + "\n"
    assert H6.RESULT.read_text() == expected


def test_followups_separate_all_material_confound_pairs():
    text = json.dumps(H6.build()["factorial_followups"])
    for term in ("prompt guidance", "mode-evidence quantity", "start distribution",
                 "identifiability"):
        assert term in text
