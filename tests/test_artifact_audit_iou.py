"""Oracle tests for the behavioural audit's shape-independent correctness metric.

`scripts/patch2d_artifact_audit.py` classifies an artifact's freeze set by SHAPE, which
is the right instrument for the disc campaign and the wrong one for the trigger-arity
ablation: a CORRECT slab is unbounded in y, so the shape classifier calls it `halfplane`
-- the same label the disc campaign's dimensional-reduction failure earns. The IoU of the
artifact's freeze set against the truth's separates them, and these tests pin that.

They are oracle tests in the sense the repo requires: the expected value is known by
construction (the truth scored against itself must be exactly 1) and the discriminating
case is built here rather than taken from any campaign, so the test cannot inherit an
error from the code path it checks.
"""
import importlib.util
import pathlib
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D  # noqa: E402


def _audit_module():
    spec = importlib.util.spec_from_file_location(
        "patch2d_artifact_audit", _REPO / "scripts" / "patch2d_artifact_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = _audit_module()

_INTEGRATOR = """
import math
def step(s, a):
    x, y, vx, vy = s
    a = max(-1.0, min(1.0, a)); phi = math.pi * a / 1.0
    vx2 = vx + (3.0*math.cos(phi) - 0.3*vx)*0.1
    vy2 = vy + (3.0*math.sin(phi) - 0.3*vy)*0.1
    x2 = x + vx2*0.1; y2 = y + vy2*0.1
    {rule}
    return [x2, y2, vx2, vy2]
def reward(s): return 0.0
"""


def _artifact(rule: str) -> str:
    return _INTEGRATOR.format(rule=rule)


@pytest.mark.parametrize("shape,k1,kw", [
    ("disc", 3.0, {}),
    ("square", 3.0, {}),
    ("slab", 5.5, {"slab_half_width": 0.5}),
])
def test_truth_against_itself_is_exactly_one(shape, k1, kw):
    env = PatchField2D(p1=(k1, 0.0), p2=(7.0, 0.0), patch_shape=shape, **kw)
    t = A.truth_mask(env)
    ag = A.mask_agreement(t, t)
    assert ag["iou_truth"] == 1.0
    assert ag["missed_frac"] == 0.0
    assert ag["excess_cells"] == 0
    # non-vacuity: the truth really does freeze somewhere on the probe grid
    assert ag["truth_cells"] > 50, ag


def test_a_correct_slab_scores_near_one_despite_being_classed_halfplane():
    """The whole reason this metric exists."""
    env = PatchField2D(p1=(5.5, 0.0), p2=(7.0, 0.0), patch_shape="slab",
                       slab_half_width=0.5)
    code = _artifact("if abs(x2 - 5.5) <= 0.5 or abs(x2 - 7.0) <= 0.5:\n"
                     "        return [x, y, 0.0, 0.0]")
    r = A.audit_code(code, env)
    assert r["iou_truth"] > 0.99, r
    # and the shape classifier does call it unbounded, which is the trap
    assert r["class"] == "halfplane", r


def test_a_halfplane_substituted_for_a_disc_scores_low_while_covering_the_patch():
    """The disc campaign's dominant failure: full coverage, vast excess."""
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    r = A.audit_code(_artifact("if x2 >= 2.0:\n        return [x, y, 0.0, 0.0]"), env)
    assert r["iou_truth"] < 0.10, r
    assert r["missed_frac"] == 0.0, r          # it does cover the patch
    assert r["excess_cells"] > 1000, r        # by freezing most of the box
    assert r["cover_p1"] == 1.0, r


def test_a_blind_artifact_scores_zero():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    r = A.audit_code(_artifact("pass"), env)
    assert r["class"] == "blind", r
    assert r["iou_truth"] == 0.0 and r["missed_frac"] == 1.0, r


def test_the_metric_is_shape_aware_not_position_blind():
    """A slab at the WRONG centre must not pass: otherwise the ablation would count a
    template placed anywhere as a repair."""
    env = PatchField2D(p1=(5.5, 0.0), p2=(7.0, 0.0), patch_shape="slab",
                       slab_half_width=0.5)
    right = A.audit_code(_artifact(
        "if abs(x2 - 5.5) <= 0.5 or abs(x2 - 7.0) <= 0.5:\n"
        "        return [x, y, 0.0, 0.0]"), env)
    wrong = A.audit_code(_artifact(
        "if abs(x2 - 2.0) <= 0.5:\n        return [x, y, 0.0, 0.0]"), env)
    assert right["iou_truth"] > 0.99 > wrong["iou_truth"], (right, wrong)
    assert wrong["iou_truth"] < 0.05, wrong
