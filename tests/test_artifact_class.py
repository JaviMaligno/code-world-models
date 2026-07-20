"""Sandboxed triple-classification of artifacts + sandboxed dynamic mask.

`invalid` (unparseable / missing step-reward / raises on a trivial call) must
be distinguished from `gate_failing` (runs, but the gate sample doesn't match
to eps) -- both are checked entirely inside the sandbox, never via an
in-process exec of non-accepted code.
"""
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.artifact_class import classify_artifact, dynamic_metrics_sandboxed


def _sample(seed=0):
    return collect_transitions(ShapeField2D(shape=Circle(3.0, 0.0, 1.0)), n_rollouts=5, seed=seed)


def test_missing_step_is_invalid_not_gate_failing():
    assert classify_artifact("def reward(s):\n    return 0.0\n", _sample(), 1e-9)["class"] == "invalid"


def test_valid_wrong_artifact_is_exactly_gate_failing():
    bad = "def step(s,a):\n    return list(s)\ndef reward(s):\n    return 0.0\n"
    assert classify_artifact(bad, _sample(), 1e-9)["class"] == "gate_failing"


def test_dynamic_mask_from_sandbox():
    circ = ("import math\n"
            "def step(s,a):\n"
            "    x2=s[0]+ (s[2]+ (3.0*math.cos(math.pi*max(-1,min(1,a))/1.0)-0.3*s[2])*0.1)*0.1\n"
            "    return list(s)\n"
            "def reward(s):\n"
            "    return 0.0\n")
    mask = dynamic_metrics_sandboxed(circ, ((-8.0, 14.0), (-6.0, 6.0)), grid_n=32,
                                     velocity_samples=[(3.0, 0.0)])
    assert mask.shape == (32, 32)
