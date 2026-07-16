"""Offline tests for the continuous synthesis pipeline (FakeProvider — no
Azure needed). These exercise the exact code path scripts/
continuous_danger_synthesis.py runs, including the sandboxed exact-match gate
and the play adapter, so the LLM arms are validated end-to-end before any
credentialed run."""
from cwm.continuous.envs import CartWall
from cwm.continuous import harness
from cwm.continuous.contract import (
    SynthesizedModel, build_contract, collect_transitions, contract_accuracy,
    refine_continuous, sample_contains_wall, synthesize_and_evaluate,
    wall_blindness)
from cwm.llm.provider import FakeProvider

import pathlib as _pathlib
_FIX = _pathlib.Path(__file__).parent / "fixtures"


def test_build_contract_cart_matches_golden():
    from cwm.continuous.contract import build_contract
    env = CartWall(x_wall=8.0)
    assert build_contract(env, include_mode=True) == (_FIX / "cart_contract_full.txt").read_text()
    assert build_contract(env, include_mode=False) == (_FIX / "cart_contract_incomplete.txt").read_text()


# Hand-written "synthesized" modules: the correct full-spec artifact and the
# wall-omitting artifact. Same update expressions as CartWall.step, so the
# full one must match to float precision (the pinned-integrator premise).
FULL_CODE = '''\
import math
def step(state, action):
    x, v = state
    a = max(-1.0, min(1.0, action))
    v2 = v + (3.0 * a - 0.3 * v) * 0.1
    x2 = x + v2 * 0.1
    if x2 >= 8.0:
        return [8.0, 0.0]
    return [x2, v2]
def reward(state):
    x = state[0]
    left = 0.3 / (1.0 + math.exp(-((-6.0 - x) / 0.5)))
    right = 1.0 / (1.0 + math.exp(-((x - 12.0) / 0.5)))
    return left + right
'''
INCOMPLETE_CODE = FULL_CODE.replace(
    "    if x2 >= 8.0:\n        return [8.0, 0.0]\n", "")

ENV = CartWall(x_wall=8.0)


def test_full_code_is_float_exact_on_the_gate():
    transitions = collect_transitions(ENV, n_rollouts=5, seed=0)
    acc, failures = contract_accuracy(FULL_CODE, transitions, eps=1e-9)
    assert acc == 1.0, failures[:3]


def test_incomplete_code_passes_iff_sample_missed_the_wall():
    # wall@8: 5 rollouts almost surely miss it (r ~ 0.013/rollout)
    far = collect_transitions(ENV, n_rollouts=5, seed=0)
    assert not sample_contains_wall(far)
    acc, _ = contract_accuracy(INCOMPLETE_CODE, far, eps=1e-9)
    assert acc == 1.0  # the gate-miss event: wall-blind code fully verified
    # wall@0.5: 20 rollouts hit it with overwhelming probability
    near_env = CartWall(x_wall=0.5)
    near = collect_transitions(near_env, n_rollouts=20, seed=0)
    assert sample_contains_wall(near)
    acc, failures = contract_accuracy(INCOMPLETE_CODE.replace("8.0]", "0.5]"),
                                      near, eps=1e-9)
    assert acc < 1.0 and failures  # wall transitions are inexplicable


def test_wall_blindness_classifier():
    assert wall_blindness(FULL_CODE, ENV) == 0.0
    assert wall_blindness(INCOMPLETE_CODE, ENV) == 1.0


def test_refine_loop_consumes_provider_until_fixed():
    transitions = collect_transitions(ENV, n_rollouts=3, seed=0)
    provider = FakeProvider([f"```python\n{FULL_CODE}```"])
    contract = build_contract(ENV, include_mode=True)
    res = refine_continuous(provider, "fake", contract,
                            "def step(s, a):\n    return s\n"
                            "def reward(s):\n    return 0.0\n",
                            transitions, eps=1e-9)
    assert res.accuracy == 1.0 and res.iterations == 1


def test_synthesize_and_evaluate_offline_both_arms():
    full = synthesize_and_evaluate(
        FakeProvider([f"```python\n{FULL_CODE}```"]), "fake", ENV,
        include_mode=True, n_rollouts=3, seed=0)
    assert full["gate_passed"] and full["wall_blindness"] == 0.0
    assert full["refine_iterations"] == 0 and not full["sample_contains_wall"]

    inc = synthesize_and_evaluate(
        FakeProvider([f"```python\n{INCOMPLETE_CODE}```"]), "fake", ENV,
        include_mode=False, n_rollouts=3, seed=0)
    assert inc["gate_passed"] and inc["wall_blindness"] == 1.0
    assert inc["arm"] == "incomplete"


def test_synthesized_blind_model_is_exploited_at_play():
    """The play path end-to-end on a synthesized artifact: MPC planning on the
    wall-blind module drives into the wall and stays pinned."""
    model = SynthesizedModel(INCOMPLETE_CODE, ENV)
    ep = harness.run_episode(ENV, model, "mpc", seed=3, n_samples=40)
    assert ep.contact and ep.final_state[0] == ENV.x_wall
    truth_ep = harness.run_episode(ENV, ENV, "mpc", seed=3, n_samples=40)
    assert truth_ep.ret > 10 * max(ep.ret, 0.1)


from cwm.continuous.envs import PendulumStop
from cwm.continuous.contract import mode_blindness, sample_contains_mode

# Hand-written pendulum artifacts: same update expressions as PendulumStop.step
# (nonlinear plant), so the full one must match to float precision.
PEND_FULL_CODE = '''\
import math
def step(state, action):
    th, om = state
    a = max(-1.0, min(1.0, action))
    om2 = om + (3.0 * a - 2.0 * math.sin(th) - 0.3 * om) * 0.1
    th2 = th + om2 * 0.1
    if th2 >= 1.4:
        return [1.4, 0.0]
    return [th2, om2]
def reward(state):
    th = state[0]
    left = 0.3 / (1.0 + math.exp(-((-2.0 - th) / 0.25)))
    right = 1.0 / (1.0 + math.exp(-((th - 3.0) / 0.25)))
    return left + right
'''
PEND_INCOMPLETE_CODE = PEND_FULL_CODE.replace(
    "    if th2 >= 1.4:\n        return [1.4, 0.0]\n", "")

PEND_ENV = PendulumStop(th_stop=1.4)


def test_pendulum_full_code_is_float_exact_on_the_gate():
    transitions = collect_transitions(PEND_ENV, n_rollouts=5, seed=0)
    acc, failures = contract_accuracy(PEND_FULL_CODE, transitions, eps=1e-9)
    assert acc == 1.0, failures[:3]


def test_pendulum_incomplete_passes_iff_sample_missed_the_stop():
    far = collect_transitions(PEND_ENV, n_rollouts=5, seed=0)
    assert not sample_contains_mode(far)  # th_stop=1.4 rarely hit in 5 rollouts
    acc, _ = contract_accuracy(PEND_INCOMPLETE_CODE, far, eps=1e-9)
    assert acc == 1.0  # gate-miss event: stop-blind code fully verified
    near_env = PendulumStop(th_stop=0.5)
    near = collect_transitions(near_env, n_rollouts=20, seed=0)
    assert sample_contains_mode(near)
    acc2, failures = contract_accuracy(
        PEND_INCOMPLETE_CODE.replace("1.4", "0.5"), near, eps=1e-9)
    assert acc2 < 1.0 and failures  # stop transitions are inexplicable


def test_pendulum_mode_blindness_classifier():
    assert mode_blindness(PEND_FULL_CODE, PEND_ENV) == 0.0
    assert mode_blindness(PEND_INCOMPLETE_CODE, PEND_ENV) == 1.0


def test_pendulum_synthesize_and_evaluate_offline_both_arms():
    full = synthesize_and_evaluate(
        FakeProvider([f"```python\n{PEND_FULL_CODE}```"]), "fake", PEND_ENV,
        include_mode=True, n_rollouts=3, seed=0)
    assert full["gate_passed"] and full["wall_blindness"] == 0.0
    assert full["refine_iterations"] == 0 and not full["sample_contains_wall"]

    inc = synthesize_and_evaluate(
        FakeProvider([f"```python\n{PEND_INCOMPLETE_CODE}```"]), "fake", PEND_ENV,
        include_mode=False, n_rollouts=3, seed=0)
    assert inc["gate_passed"] and inc["wall_blindness"] == 1.0
    assert inc["arm"] == "incomplete"


def test_pendulum_blind_model_is_exploited_at_play():
    model = SynthesizedModel(PEND_INCOMPLETE_CODE, PEND_ENV)
    ep = harness.run_episode(PEND_ENV, model, "mpc", seed=3, n_samples=40)
    assert ep.contact and ep.final_state[0] == PEND_ENV.th_stop
    truth_ep = harness.run_episode(PEND_ENV, PEND_ENV, "mpc", seed=3, n_samples=40)
    assert truth_ep.ret > 10 * max(ep.ret, 0.1)


from cwm.continuous.envs import PatchField2D

P2D = PatchField2D()
P2D_FULL_CODE = '''\
import math
def step(state, action):
    x, y, vx, vy = state
    a = max(-1.0, min(1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2, y2 = x + vx2 * 0.1, y + vy2 * 0.1
    for cx, cy in ((3.0, 0.0), (7.0, 0.0)):
        if (x2 - cx) ** 2 + (y2 - cy) ** 2 <= 1.0:
            return [x, y, 0.0, 0.0]
    return [x2, y2, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x + 6.0, y); d2 = math.hypot(x - 12.0, y)
    return (0.3 / (1.0 + math.exp((d1 - 2.0) / 0.5))
            + 1.0 / (1.0 + math.exp((d2 - 2.0) / 0.5)))
'''
P2D_OMIT_P2_CODE = P2D_FULL_CODE.replace("((3.0, 0.0), (7.0, 0.0))",
                                         "((3.0, 0.0),)")


def test_patch2d_full_code_float_exact():
    tr = collect_transitions(P2D, n_rollouts=5, seed=0)
    acc, fails = contract_accuracy(P2D_FULL_CODE, tr, eps=1e-9)
    assert acc == 1.0, fails[:3]


def test_patch2d_per_mode_blindness():
    mb = mode_blindness(P2D_OMIT_P2_CODE, P2D)
    assert mb == {"patch1": 0.0, "patch2": 1.0}   # partial blindness!


def test_patch2d_synthesize_and_evaluate_keys():
    cell = synthesize_and_evaluate(
        FakeProvider([f"```python\n{P2D_OMIT_P2_CODE}```"]), "fake", P2D,
        include_mode=False, n_rollouts=3, seed=0)
    assert "mode_blindness" in cell and "sample_contains_mode_per" in cell
    assert isinstance(cell["wall_blindness"], float) or cell["wall_blindness"] is None


# Same integrator as P2D_FULL_CODE but returning 3-component states (vy2
# dropped): the arity guard must reject it — zip() truncation previously let
# such an artifact pass the gate at accuracy 1.0.
P2D_WRONG_ARITY_CODE = P2D_FULL_CODE.replace(
    "return [x, y, 0.0, 0.0]", "return [x, y, 0.0]").replace(
    "return [x2, y2, vx2, vy2]", "return [x2, y2, vx2]")


def test_patch2d_wrong_arity_is_a_hard_failure():
    from cwm.continuous.gate import run_gate
    tr = collect_transitions(P2D, n_rollouts=3, seed=0)
    acc, fails = contract_accuracy(P2D_WRONG_ARITY_CODE, tr, eps=1e-9)
    assert acc < 1.0
    assert any("wrong state arity" in f for f in fails)
    model = SynthesizedModel(P2D_WRONG_ARITY_CODE, P2D)
    assert not run_gate(P2D, model, n_rollouts=1, eps=1e-9).passed
