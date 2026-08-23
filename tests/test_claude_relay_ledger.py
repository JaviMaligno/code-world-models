"""The relay ledger's rule classifier, against constructed artifacts.

The classifier names the template an artifact wrote (paper 2's PatchField2D
cross-family arm). It is the only piece of judgement in the ledger, so it is
pinned here on one artifact per class, including the two that matter most for
the paper's claim: the TRUE form (a disc on the landing position) must never be
confused with the dominant error (the same disc on the CURRENT position).
"""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "claude_relay_ledger.py"
_spec = importlib.util.spec_from_file_location("claude_relay_ledger_mod", _SCRIPT)
ledger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ledger)


def _module(rule: str) -> str:
    """A synthesized-artifact module whose step() carries `rule` as its extra
    dynamics, with the pinned integrator and a reward() the classifier must
    ignore (reward always mentions the lodes, so a classifier that read it
    would call everything reward-anchored)."""
    return f'''import math

def step(state, action):
    x, y, vx, vy = state
    a = min(1.0, max(-1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2 = x + vx2 * 0.1
    y2 = y + vy2 * 0.1
{rule}
    return [x2, y2, vx2, vy2]

def reward(state):
    x, y, vx, vy = state
    d1 = math.hypot(x - (-6.0), y - 0.0)
    d2 = math.hypot(x - 12.0, y - 0.0)
    return 0.3 / (1.0 + math.exp((d1 - 2.0) / 0.5)) + \\
        1.0 / (1.0 + math.exp((d2 - 2.0) / 0.5))
'''


FREEZE = "        return [x, y, 0.0, 0.0]"

CASES = {
    # no extra dynamics at all
    "blind": "",
    # the TRUE rule: radial predicate on the landing position
    "disc-landing": f"    if (x2 - 3.0) ** 2 + (y2 - 0.0) ** 2 <= 1.0:\n{FREEZE}",
    "disc-landing-hypot": f"    if math.hypot(x2 - 3.0, y2) <= 1.0:\n{FREEZE}",
    # the wrong-causal-variable error: same disc, current position
    "disc-current": f"    if math.hypot(x - 3.0, y - 0.0) < 1.0:\n{FREEZE}",
    # dimensional reduction
    "halfplane": f"    if x2 > 2.0:\n{FREEZE}",
    "halfplane-y": f"    if y2 <= -1.5:\n{FREEZE}",
    # band on one coordinate
    "strip": f"    if abs(y) < 0.6:\n{FREEZE}",
    # the true square's form: bands on both coordinates
    "box": f"    if abs(x2 - 3.0) <= 1.0 and abs(y2 - 0.0) <= 1.0:\n{FREEZE}",
    # anchored on the reward landmarks / on reward itself
    "reward-zone-lode": f"    if math.hypot(x - (-6.0), y) <= 2.0:\n{FREEZE}",
    "reward-zone-thresh": f"    if reward(state) < 2e-06:\n{FREEZE}",
}

EXPECTED = {
    "blind": "blind",
    "disc-landing": "disc-landing",
    "disc-landing-hypot": "disc-landing",
    "disc-current": "disc-current",
    "halfplane": "halfplane",
    "halfplane-y": "halfplane",
    "strip": "strip",
    "box": "box",
    "reward-zone-lode": "reward-zone",
    "reward-zone-thresh": "reward-zone",
}


def test_classifier_on_one_artifact_per_class():
    got = {name: ledger.classify(_module(rule)) for name, rule in CASES.items()}
    assert got == EXPECTED, got


def test_landing_and_current_discs_are_never_confused():
    """The paper's claim rests on this distinction: the same radial predicate is
    correct on (x2, y2) and wrong on (x, y)."""
    landing = ledger.classify(_module(CASES["disc-landing"]))
    current = ledger.classify(_module(CASES["disc-current"]))
    assert landing == "disc-landing"
    assert current == "disc-current"
    assert landing != current


def test_reward_body_alone_does_not_make_an_artifact_non_blind():
    """reward() always mentions the lodes; only step()'s extra rule counts."""
    assert ledger.classify(_module("")) == "blind"
