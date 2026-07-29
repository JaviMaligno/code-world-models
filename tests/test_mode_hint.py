"""Tests for the graded mode hints — the positive control for the 2D negative results.

A negative result is only as strong as the guarantee that its target is learnable by the
pipeline at all. The hints state the rule's FORM and EFFECT while withholding constants, so
if the pipeline cannot fit them the 2D failure is upstream of region induction.

That makes the leak checks load-bearing: a hint that named a withheld constant would turn
the control into the translation exercise the full arm already covers, and the campaign
would silently confirm nothing.
"""
import pathlib
import subprocess
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D                        # noqa: E402
from cwm.continuous.contract import build_contract                  # noqa: E402
from cwm.continuous.instruments import (_patch2d_rules_text,        # noqa: E402
                                        patch2d_hint_lines)

LEVELS = ("radius", "centre")
# the truth's constants at the campaign's knob, in every textual form they could leak as
R_FORMS = ("R = 1.0", "R=1.0", "1.0 ** 2", "1.0**2", "<= 1.0,", "radius = 1.0",
           "radius R = 1.0", "R ** 2 = 1.0")
CENTRE_FORMS = ("(3.0, 0.0)", "(7.0, 0.0)", "x2 - 3.0", "x2 - 7.0")


def _env():
    return PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))


def test_no_hint_reproduces_the_committed_contract_byte_for_byte():
    old = subprocess.run(["git", "show", "HEAD:src/cwm/continuous/instruments.py"],
                         capture_output=True, text=True, cwd=_REPO).stdout
    if not old:
        pytest.skip("no git HEAD to compare against")
    src = (old.replace("from .envs import", "from cwm.continuous.envs import")
              .replace("from .shapes import", "from cwm.continuous.shapes import"))
    ns = {}
    exec(compile(src, "committed", "exec"), ns)  # noqa: S102 — our own file
    env = _env()
    for include in (True, False):
        assert ns["_patch2d_rules_text"](env, include) == \
            _patch2d_rules_text(env, include)


@pytest.mark.parametrize("level", LEVELS)
def test_the_hint_never_names_the_withheld_radius(level):
    text = build_contract(_env(), False, hint=level)
    for form in R_FORMS:
        assert form not in text, f"{level}: the hint leaks the radius as {form!r}"


def test_the_centre_level_withholds_the_centres_too():
    text = build_contract(_env(), False, hint="centre")
    for form in CENTRE_FORMS:
        assert form not in text, f"the 'centre' hint leaks a centre as {form!r}"


def test_the_radius_level_DOES_give_the_centres():
    """Non-vacuity in the other direction: the 'radius' level is supposed to be the easier
    one, so it must actually supply the centres."""
    text = build_contract(_env(), False, hint="radius")
    assert "(3.0, 0.0)" in text and "(7.0, 0.0)" in text


@pytest.mark.parametrize("level", LEVELS)
def test_the_hint_states_the_form_and_the_effect(level):
    """What the control gives, as against what it withholds."""
    text = build_contract(_env(), False, hint=level)
    assert "circular" in text
    assert "PREVIOUS position" in text          # the effect
    assert "infer" in text                       # and it says what to infer


@pytest.mark.parametrize("level", LEVELS)
def test_the_hint_is_strictly_more_than_the_incomplete_arm(level):
    inc = build_contract(_env(), False)
    hinted = build_contract(_env(), False, hint=level)
    assert len(hinted) > len(inc)
    # every line of the plain incomplete arm survives: the hint ADDS a partial clause
    for line in inc.split("\n"):
        assert line in hinted.split("\n")


@pytest.mark.parametrize("level", LEVELS)
def test_the_hint_is_strictly_less_than_the_full_arm(level):
    full = build_contract(_env(), True)
    hinted = build_contract(_env(), False, hint=level)
    assert hinted != full
    # the full arm's own membership line, with the radius in it, must be absent
    assert "<= 1.0," in full and "<= 1.0," not in hinted


def test_a_hint_with_include_mode_is_refused():
    """The hint REPLACES the full clause; combining them would state the rule twice, once
    completely, and quietly make the control a translation exercise."""
    with pytest.raises(ValueError, match="include_mode must be False"):
        build_contract(_env(), True, hint="radius")


def test_an_unknown_level_is_refused():
    with pytest.raises(ValueError, match="unknown hint level"):
        patch2d_hint_lines(_env(), "nonsense")


@pytest.mark.parametrize("level", LEVELS)
def test_the_hint_survives_the_synthesis_message_builder(level):
    """The hint has to reach the prompt, not just the contract object."""
    from cwm.continuous.contract import (build_synthesis_messages,
                                         collect_transitions)
    env = _env()
    tr = collect_transitions(env, 40, seed=10_000)
    assert any(t["contact"] for t in tr), "vacuous: no contacts to infer from"
    msgs = build_synthesis_messages(build_contract(env, False, hint=level), tr)
    user = msgs[-1]["content"]
    assert "constants withheld" in user
    for form in R_FORMS:
        assert form not in user, f"{level}: the radius leaks into the prompt as {form!r}"


# --- the control's own results, pinned ---------------------------------------------
_RES = _REPO / "results"


def _campaign(level):
    import json
    f = _RES / f"continuous_synthesis_patch2d_large_k3_7_hint-{level}.json"
    if not f.exists():
        pytest.skip(f"the hint-{level} campaign has not been run")
    return json.loads(f.read_text())


def test_the_radius_control_succeeded_and_the_centre_control_did_not():
    """The paper's sharpest claim rests on this dichotomy, so it is asserted from the
    committed artifacts rather than from prose."""
    import json
    rep = _RES / "arity_evidence_ablations.json"
    if not rep.exists():
        pytest.skip("run scripts/arity_evidence_ablations.py")
    camps = json.loads(rep.read_text())["campaigns"]
    if "hint_radius" not in camps or "hint_centre" not in camps:
        pytest.skip("the hint campaigns are not in the analysis yet")
    rad = camps["hint_radius"]["per_size"]["large"]
    cen = camps["hint_centre"]["per_size"]["large"]
    assert rad["n_mode_containing"] == cen["n_mode_containing"] == 20
    # given the form AND the centres: every seed, exactly
    assert rad["k_repaired_behavioural"] == 20
    assert rad["best_iou"] == 1.0
    # given the form alone: none
    assert cen["k_repaired_behavioural"] == 0
    assert cen["best_iou"] < 0.2


def test_every_radius_control_artifact_is_exact_not_merely_probe_clean():
    """The distinction the slab campaign forced: a probe pass is not a repair."""
    import json
    rep = _RES / "arity_evidence_ablations.json"
    if not rep.exists():
        pytest.skip("run scripts/arity_evidence_ablations.py")
    camps = json.loads(rep.read_text())["campaigns"]
    if "hint_radius" not in camps:
        pytest.skip("the hint-radius campaign is not in the analysis yet")
    arts = camps["hint_radius"]["artifacts"]
    assert len(arts) == 20
    for a in arts:
        assert a["iou_truth"] == 1.0, a
        assert a["grid_exact"] is True and a["grid_mismatch"] == 0, a
        assert a["grid_n"] == 9020, a


def test_the_trivial_baseline_beats_the_form_only_arm():
    """What makes the negative an induction failure: a three-line fit recovers the region
    on samples where the synthesizer given the form does not."""
    import json
    f = _RES / "region_fit_baseline.json"
    if not f.exists():
        pytest.skip("run scripts/region_fit_baseline.py")
    d = json.loads(f.read_text())
    assert d["n_seeds"] == 20
    assert d["n_recovering_both"] >= 10, d["n_recovering_both"]
    assert d["n_recovering_centre"] >= d["n_recovering_both"]
    # and the arc really is partial -- neither a thin crescent nor full coverage
    assert 60.0 < d["median_landing_arc_deg"] < 200.0, d["median_landing_arc_deg"]
