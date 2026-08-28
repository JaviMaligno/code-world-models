"""Offline tests for the paper-3 ring2d synthesis arm (FakeProvider — no
Azure): contract text, float-exact full artifact, blindness classifier,
probes under both channel orientations, per-seed dynamic (TDA) guidance, and
the topological summary's loop/arc wording."""
import math

from cwm.continuous.envs import PatchField2D, RingField2D, blind_of
from cwm.continuous.contract import (
    build_contract, collect_transitions, contract_accuracy, mode_blindness,
    sample_contains_mode, synthesize_and_evaluate)
from cwm.continuous.tda import topological_summary
from cwm.llm.provider import FakeProvider

RING = RingField2D()
RING_IN = RingField2D(x0_center=RingField2D().center)   # contact-rich mu0

RING_FULL_CODE = '''\
import math
def step(state, action):
    x, y, vx, vy = state
    a = max(-1.0, min(1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2, y2 = x + vx2 * 0.1, y + vy2 * 0.1
    d = math.hypot(x2 - 12.0, y2 - 0.0)
    if 3.5 <= d <= 5.0:
        return [x, y, 0.0, 0.0]
    return [x2, y2, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x + 6.0, y); d2 = math.hypot(x - 12.0, y)
    return (0.3 / (1.0 + math.exp((d1 - 2.0) / 0.5))
            + 1.0 / (1.0 + math.exp((d2 - 2.0) / 0.5)))
'''
RING_BLIND_CODE = RING_FULL_CODE.replace(
    "    if 3.5 <= d <= 5.0:\n        return [x, y, 0.0, 0.0]\n", "")


def test_ring_contract_text_and_incomplete_equals_patch2d():
    full = build_contract(RING, include_mode=True)
    assert "sticky ring (annulus)" in full
    assert "inner radius r_in = 3.5 and outer radius r_out = 5.0" in full
    assert "Exception (channel)" not in full          # gap = 0: no channel text
    gapped = build_contract(RingField2D(gap=0.6), include_mode=True)
    assert "Exception (channel)" in gapped and "width 0.6" in gapped
    # the incomplete ring contract is byte-identical to patch2d's (same plant,
    # same lodes) — no leak, and the two instruments pose the same base task
    assert build_contract(RING, include_mode=False) == \
        build_contract(PatchField2D(), include_mode=False)


def test_ring_full_code_float_exact_on_contact_rich_sample():
    tr = collect_transitions(RING_IN, n_rollouts=5, seed=0)
    assert sample_contains_mode(tr)                   # inside start: r ~ 0.73
    acc, fails = contract_accuracy(RING_FULL_CODE, tr, eps=1e-9)
    assert acc == 1.0, fails[:3]


def test_ring_blindness_classifier_and_probes_fire_both_orientations():
    assert mode_blindness(RING_FULL_CODE, RING) == 0.0
    assert mode_blindness(RING_BLIND_CODE, RING) == 1.0
    # the north-approach probes fire in truth for facing AND hidden channels
    from cwm.continuous.instruments import spec_for
    for env in (RING, RingField2D(gap=0.6),
                RingField2D(gap=0.6, gap_center=0.0)):
        for s, a in spec_for(env).mode_probes(env)["ring"]:
            assert env.step(s, a)[2], (env.gap, env.gap_center, s)


def test_dynamic_guidance_resolves_from_the_seeds_own_sample():
    calls = []

    class Capturing:
        def __init__(self):
            self._inner = FakeProvider([f"```python\n{RING_FULL_CODE}```"])

        def complete(self, messages, model):
            calls.append(messages)
            return self._inner.complete(messages, model=model)

    def fn(env, transitions):
        n = sum(t["contact"] for t in transitions)
        return f"DYNAMIC-SUMMARY contacts={n}"

    cell = synthesize_and_evaluate(
        Capturing(), "fake", RING_IN, include_mode=True, n_rollouts=3,
        seed=0, guidance=fn)
    assert cell["gate_passed"]
    assert "DYNAMIC-SUMMARY contacts=" in calls[0][1]["content"]
    assert cell["guidance_text"].startswith("DYNAMIC-SUMMARY")


def test_topological_summary_wording_loop_vs_arc():
    loop = [(12 + 4 * math.cos(2 * math.pi * k / 50),
             4 * math.sin(2 * math.pi * k / 50)) for k in range(50)]
    s = topological_summary(loop)
    assert "beta_1 = 1" in s and "CLOSED LOOP" in s
    arc = [(12 + 4 * math.cos(a), 4 * math.sin(a))
           for a in [2.2 + 1.8 * k / 40 for k in range(41)]]
    s2 = topological_summary(arc)
    assert "beta_1 = 0" in s2 and "open arc" in s2
    assert "REACHABLE side" in s2                     # the mechanical note
    tiny = topological_summary([(0.0, 0.0), (1.0, 1.0)])
    assert "too few" in tiny
