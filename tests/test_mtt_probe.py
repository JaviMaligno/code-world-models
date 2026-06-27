import importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "mtt_claimB_probe",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "mtt_claimB_probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

def test_withheld_removes_masking_rule_no_op_guard():
    assert probe.RULES_WITHHELD != probe.RULES_FULL          # not a silent no-op
    assert "hidden from BOTH players" in probe.RULES_FULL
    assert "hidden from BOTH players" not in probe.RULES_WITHHELD
    assert "index 4" not in probe.RULES_WITHHELD             # masking detail gone
    # the tic-tac-toe dynamics text survives in both
    assert "3 of their marks in a row" in probe.RULES_WITHHELD
