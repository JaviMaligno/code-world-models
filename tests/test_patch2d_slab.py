"""Tests for the rarity-matched 1D-PREDICATE ablation on PatchField2D
(`patch_shape="slab"`, review point #4 / 2026-07-27).

The ablation's whole value is that it changes ONE thing: the mode predicate's
arity (2 landing coordinates -> 1). So these tests are mostly *invariance*
tests:

  * disc/square rollouts must be BIT-identical to the pre-change code (golden
    sha256 over states/rewards/actions/contacts of a fixed seeded batch,
    captured from the code before "slab" existed);
  * the slab env's off-mode dynamics must be bit-identical to the disc's (only
    the trigger differs);
  * the incomplete-arm contract text must be byte-identical to the disc's (the
    ablation must not leak into the arm that omits the mode).

Plus a brute-force oracle for the predicate itself (an independent
reimplementation of the integrator and of the slab in its INTERVAL form
`c - W <= x <= c + W`, which the env writes as `abs(x - c) <= W`), the probe
contract `mode_blindness` relies on, and a FakeProvider smoke test of the whole
synthesis path.
"""
import hashlib
import json
import math
import pathlib
import random
import struct

import pytest

from cwm.continuous import harness
from cwm.continuous.contract import (
    build_contract, collect_transitions, contract_accuracy, mode_blindness,
    sample_contains_mode, synthesize_and_evaluate)
from cwm.continuous.envs import PatchField2D, blind_of
from cwm.continuous.instruments import spec_for
from cwm.llm.provider import FakeProvider

REPO = pathlib.Path(__file__).resolve().parents[1]
CALIB = REPO / "results" / "patch2d_slab_calibration.json"

DISC = PatchField2D()                                   # k=(3,7), R=1, disc
SQUARE = PatchField2D(patch_shape="square")
W_IMPERM = 0.5     # >= half the one-step reach (gain/drag)*dt = 1.0: unjumpable
SLAB = PatchField2D(patch_shape="slab", slab_half_width=W_IMPERM)


# --- 1. the disc/square code paths are untouched ------------------------------
# Digests captured by running this exact loop against src/cwm/continuous/envs.py
# BEFORE patch_shape="slab" / slab_half_width existed. Any change to the disc or
# square membership test, the integrator, the reward or the freeze semantics
# moves them, which would invalidate every committed disc/square result.
GOLDEN = {
    ("disc", "truth"): "d6690d941512771114e1095ac06e65dc24bd29796636a7fb0e907d73f749347a",
    ("disc", "blind"): "da8d4981be128ff656ae8f250271ee1b44eb9c94cb147df0ab55dec926bdf657",
    ("square", "truth"): "c5bf317a5f39ae04a130128366142ecacc8ed7aa979a00d12cc3eea8afb1cb9e",
    ("square", "blind"): "da8d4981be128ff656ae8f250271ee1b44eb9c94cb147df0ab55dec926bdf657",
}


def _rollout_digest(env, n_rollouts=25, seed=777):
    """sha256 over the exact float bytes of a fixed seeded rollout batch, plus
    the contact flags. Returns (digest, n_contacts) so callers can prove the
    batch actually exercised the mode branch."""
    h = hashlib.sha256()
    contacts = 0
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            m1, m2 = env.contact_modes(s, a)
            s2, r, c = env.step(s, a)
            h.update(struct.pack("<6d???", s2[0], s2[1], s2[2], s2[3], r, a,
                                 c, m1, m2))
            contacts += c
            s = s2
    return h.hexdigest(), contacts


def test_disc_and_square_rollouts_are_bit_identical_to_pre_slab_code():
    for shape in ("disc", "square"):
        env = PatchField2D(patch_shape=shape)
        d_truth, n_truth = _rollout_digest(env)
        d_blind, n_blind = _rollout_digest(blind_of(env))
        # non-vacuous: the truth batch really did fire the freeze branch, and
        # the blind batch really did not (so both branches are covered).
        assert n_truth > 0, f"{shape}: golden batch never contacted a patch"
        assert n_blind == 0
        assert d_truth == GOLDEN[(shape, "truth")], f"{shape} truth digest moved"
        assert d_blind == GOLDEN[(shape, "blind")], f"{shape} blind digest moved"


def test_disc_default_and_slab_field_is_inert_for_disc_and_square():
    assert PatchField2D().patch_shape == "disc"
    # the new field must not touch disc/square behaviour at any value
    for shape in ("disc", "square"):
        base = PatchField2D(patch_shape=shape)
        for W in (0.001, 0.5, 3.0):
            assert _rollout_digest(PatchField2D(patch_shape=shape,
                                                slab_half_width=W))[0] == \
                _rollout_digest(base)[0]


# --- 2. the slab predicate: brute-force oracle --------------------------------
def _oracle_landing(state, action, dt=0.1, gain=3.0, drag=0.3, a_max=1.0):
    """Independent reimplementation of the 2D landing point straight from the
    contract text (does NOT call integrate_2d / PatchField2D)."""
    x, y, vx, vy = state
    a = min(a_max, max(-a_max, action))
    phi = math.pi * a / a_max
    nvx = vx + (gain * math.cos(phi) - drag * vx) * dt
    nvy = vy + (gain * math.sin(phi) - drag * vy) * dt
    return x + nvx * dt, y + nvy * dt


def _oracle_in_slab(x, c, W):
    """The slab in the INTERVAL form of the spec, not the env's abs() form."""
    return (c - W) <= x <= (c + W)


@pytest.mark.parametrize("W", [0.03, 0.5, 1.0])
def test_slab_contact_matches_brute_force_oracle(W):
    env = PatchField2D(patch_shape="slab", slab_half_width=W)
    rng = random.Random(20260727)
    n_in = n_out = 0
    for _ in range(20000):
        # states spread over the region the modes live in, at speeds the plant
        # actually reaches, so both branches are hit many times
        s = (rng.uniform(-1.0, 9.0), rng.uniform(-6.0, 6.0),
             rng.uniform(-10.0, 10.0), rng.uniform(-10.0, 10.0))
        a = rng.uniform(-1.5, 1.5)          # includes out-of-range (clamped)
        x2, _y2 = _oracle_landing(s, a)
        want = (_oracle_in_slab(x2, env.p1[0], W),
                _oracle_in_slab(x2, env.p2[0], W))
        assert env.contact_modes(s, a) == want
        n_in += any(want)
        n_out += not any(want)
    assert n_in > 100 and n_out > 100, (n_in, n_out)   # non-vacuous both ways


def test_slab_membership_ignores_y_while_disc_and_square_do_not():
    env = PatchField2D(patch_shape="slab", slab_half_width=0.5)
    rng = random.Random(7)
    differed = 0
    for _ in range(4000):
        s = (rng.uniform(1.0, 5.0), rng.uniform(-6.0, 6.0),
             rng.uniform(-8.0, 8.0), rng.uniform(-8.0, 8.0))
        a = rng.uniform(-1.0, 1.0)
        # reflecting the whole state in y reflects the landing y and leaves the
        # landing x untouched, so a y-blind predicate cannot notice
        mirror = (s[0], -s[1], s[2], -s[3])
        assert env.contact_modes(s, a) == env.contact_modes(mirror, -a)
        differed += (DISC.contact_modes(s, a) != env.contact_modes(s, a))
    assert differed > 50   # the two predicates genuinely disagree somewhere


def test_slab_off_mode_dynamics_are_bit_identical_to_the_disc():
    """Only the trigger changed: whenever neither env freezes, the successor
    states and rewards agree to the last bit."""
    env = PatchField2D(patch_shape="slab", slab_half_width=0.5)
    rng = random.Random(11)
    same, trigger_differed = 0, 0
    for _ in range(8000):
        s = (rng.uniform(-2.0, 9.0), rng.uniform(-4.0, 4.0),
             rng.uniform(-6.0, 6.0), rng.uniform(-6.0, 6.0))
        a = rng.uniform(-1.0, 1.0)
        sd, rd, cd = DISC.step(s, a)
        ss, rs, cs = env.step(s, a)
        if not cd and not cs:
            assert sd == ss and rd == rs
            same += 1
        else:
            trigger_differed += (cd != cs)
    assert same > 1000 and trigger_differed > 20


def test_calibration_scripts_contact_shortcut_equals_contact_modes():
    """scripts/calibrate_patch2d_slab.py reads the landing from `_integrate` and
    the per-mode contacts from `_inside` (one integration instead of two) so it
    can also count center-line crossings for free. That shortcut must be exactly
    `contact_modes`, on every shape."""
    rng = random.Random(4242)
    seen = {True: 0, False: 0}
    for env in (DISC, SQUARE, SLAB,
                PatchField2D(patch_shape="slab", slab_half_width=0.03)):
        for _ in range(3000):
            s = (rng.uniform(-1.0, 9.0), rng.uniform(-3.0, 3.0),
                 rng.uniform(-8.0, 8.0), rng.uniform(-8.0, 8.0))
            a = rng.uniform(-1.0, 1.0)
            x2, y2, _, _ = env._integrate(s, a)
            shortcut = (env._inside(x2, y2, env.p1), env._inside(x2, y2, env.p2))
            assert shortcut == env.contact_modes(s, a)
            seen[any(shortcut)] += 1
    assert seen[True] > 100 and seen[False] > 100, seen


# --- 3. rarity is monotone in W (the calibration's premise) -------------------
def _r1(env, n_rollouts, seed=50_000):
    hits = 0
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        c1 = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            c1 = c1 or env.contact_modes(s, a)[0]
            s = env.step(s, a)[0]
        hits += c1
    return hits / n_rollouts


def test_patch1_rarity_is_monotone_in_the_slab_half_width():
    # same rollout seeds for every W, so the comparison is paired and the
    # monotonicity is a property of the predicate nesting, not of noise
    rs = [_r1(PatchField2D(patch_shape="slab", slab_half_width=W), 300)
          for W in (0.01, 0.05, 0.5)]
    assert 0.0 < rs[0] < rs[1] < rs[2] < 1.0, rs


# --- 4. contract text ---------------------------------------------------------
def test_slab_full_contract_states_the_clause_and_incomplete_arm_is_unchanged():
    full = build_contract(SLAB, include_mode=True)
    assert "sticky vertical slab centered at x = 3.0" in full
    assert "half-width W = 0.5" in full
    assert "if abs(x2 - 3.0) <= 0.5, the mover sticks (whatever y2 is):" in full
    assert "sticky vertical slab centered at x = 7.0" in full
    assert "if abs(x2 - 7.0) <= 0.5" in full
    # the slab must never be mentioned by y, and must not name a radius/half-side
    assert "y2 - 0.0" not in full and "radius" not in full
    assert "half-side" not in full
    # no leak into the arm that omits the mode: byte-identical to the disc's
    assert build_contract(SLAB, include_mode=False) == \
        build_contract(DISC, include_mode=False)


# --- 5. probes ---------------------------------------------------------------
def test_slab_probes_fire_only_their_own_mode_and_span_several_y():
    probes = spec_for(SLAB).mode_probes(SLAB)
    assert set(probes) == {"patch1", "patch2"}
    for name, want in (("patch1", (True, False)), ("patch2", (False, True))):
        ys = set()
        for s, a in probes[name]:
            assert SLAB.contact_modes(s, a) == want, (name, s)
            assert SLAB.step(s, a)[2] is True
            ys.add(s[1])
        assert len(ys) >= 3   # the probes really do vary y


# --- 6. synthesized artifacts -------------------------------------------------
def _slab_code(W: float, centers=("3.0", "7.0")) -> str:
    return f'''\
import math
def step(state, action):
    x, y, vx, vy = state
    a = max(-1.0, min(1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2, y2 = x + vx2 * 0.1, y + vy2 * 0.1
    for cx in ({", ".join(centers)},):
        if abs(x2 - cx) <= {W}:
            return [x, y, 0.0, 0.0]
    return [x2, y2, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x + 6.0, y); d2 = math.hypot(x - 12.0, y)
    return (0.3 / (1.0 + math.exp((d1 - 2.0) / 0.5))
            + 1.0 / (1.0 + math.exp((d2 - 2.0) / 0.5)))
'''


SLAB_FULL_CODE = _slab_code(W_IMPERM)
SLAB_BLIND_CODE = SLAB_FULL_CODE.replace(
    f"    for cx in (3.0, 7.0,):\n        if abs(x2 - cx) <= {W_IMPERM}:\n"
    "            return [x, y, 0.0, 0.0]\n", "")
# the two arity errors a template prior would make on slab evidence: a DISC
# fitted to the contact points, and a slab that also gates on y (the disc/square
# template copied over). Both are correct at y = 0 and wrong off the axis.
SLAB_AS_DISC_CODE = SLAB_FULL_CODE.replace(
    f"if abs(x2 - cx) <= {W_IMPERM}:",
    f"if (x2 - cx) ** 2 + y2 ** 2 <= {W_IMPERM} ** 2:")
SLAB_Y_GATED_CODE = SLAB_FULL_CODE.replace(
    f"if abs(x2 - cx) <= {W_IMPERM}:",
    f"if abs(x2 - cx) <= {W_IMPERM} and abs(y2) <= 1.0:")


def test_slab_full_code_is_float_exact_on_a_mode_containing_gate():
    tr = collect_transitions(SLAB, n_rollouts=3, seed=0)
    assert sample_contains_mode(tr)          # non-vacuous: freezes are in there
    acc, fails = contract_accuracy(SLAB_FULL_CODE, tr, eps=1e-9)
    assert acc == 1.0, fails[:3]


def test_slab_blind_code_passes_iff_the_sample_missed_the_slab():
    tr = collect_transitions(SLAB, n_rollouts=3, seed=0)
    assert sample_contains_mode(tr)
    acc, fails = contract_accuracy(SLAB_BLIND_CODE, tr, eps=1e-9)
    assert acc < 1.0 and fails               # freezes are inexplicable
    # a thin slab at seed 1 is missed by 3 rollouts -> the gate-miss event
    thin = PatchField2D(patch_shape="slab", slab_half_width=0.03)
    tr_miss = collect_transitions(thin, n_rollouts=3, seed=1)
    assert not sample_contains_mode(tr_miss)
    acc2, _ = contract_accuracy(_slab_code(0.03).replace(
        "    for cx in (3.0, 7.0,):\n        if abs(x2 - cx) <= 0.03:\n"
        "            return [x, y, 0.0, 0.0]\n", ""), tr_miss, eps=1e-9)
    assert acc2 == 1.0                       # slab-blind code fully verified


def test_slab_mode_blindness_separates_arity_errors():
    assert mode_blindness(SLAB_FULL_CODE, SLAB) == {"patch1": 0.0, "patch2": 0.0}
    assert mode_blindness(SLAB_BLIND_CODE, SLAB) == {"patch1": 1.0, "patch2": 1.0}
    # both arity errors are right on the axis probe and wrong on the two
    # off-axis ones: exactly 2/3, which is what makes the probes an arity test
    for code in (SLAB_AS_DISC_CODE, SLAB_Y_GATED_CODE):
        mb = mode_blindness(code, SLAB)
        assert mb == {"patch1": 2 / 3, "patch2": 2 / 3}, mb


def test_slab_synthesis_path_end_to_end_with_fake_provider():
    """The exact path scripts/continuous_danger_synthesis.py drives, offline."""
    full = synthesize_and_evaluate(
        FakeProvider([f"```python\n{SLAB_FULL_CODE}```"]), "fake", SLAB,
        include_mode=True, n_rollouts=3, seed=0)
    assert full["gate_passed"] and full["refine_iterations"] == 0
    assert full["mode_blindness"] == {"patch1": 0.0, "patch2": 0.0}
    assert full["wall_blindness"] == 0.0
    # sample_contains_mode_per works and is non-vacuous for patch 1
    assert full["sample_contains_mode_per"] == {"patch1": True, "patch2": False}

    blind = synthesize_and_evaluate(
        FakeProvider([f"```python\n{SLAB_BLIND_CODE}```"] * 8), "fake", SLAB,
        include_mode=False, n_rollouts=3, seed=0)
    # the sample contains the mode, so the all-or-nothing gate must refuse the
    # slab-blind artifact (soundness) rather than certify it
    assert blind["sample_contains_mode_per"]["patch1"] is True
    assert not blind["gate_passed"] and blind["arm"] == "incomplete"


def test_slab_full_arm_contract_text_reaches_the_synthesis_prompt():
    from cwm.continuous.contract import build_synthesis_messages
    tr = collect_transitions(SLAB, n_rollouts=1, seed=0)
    msgs = build_synthesis_messages(build_contract(SLAB, include_mode=True), tr)
    assert "if abs(x2 - 3.0) <= 0.5" in msgs[1]["content"]


# --- 7. the impermeable slab still exhibits the danger -----------------------
def test_impermeable_slab_pins_the_blind_planner_like_the_disc():
    """A half-width of 0.5 is half the one-step reach (gain/drag)*dt = 1.0, so
    no single step can jump the band: the mode-blind planner must freeze exactly
    as it does on the disc. (The thin, rarity-matched slab does NOT have this
    property -- that is the confound the calibration script measures.)"""
    assert (SLAB.gain / SLAB.drag) * SLAB.dt == 1.0
    t = harness.run_episode(SLAB, SLAB, "mpc", seed=0, n_samples=40)
    b = harness.run_episode(SLAB, blind_of(SLAB), "mpc", seed=0, n_samples=40)
    assert b.contact and b.ret < 1.0 and b.final_state[0] < SLAB.p1[0]
    assert t.ret > 10.0 and not t.contact


def test_a_slab_of_half_width_half_the_step_reach_cannot_be_jumped():
    """Brute-force check of the analytic claim the `imperm` arm rests on.

    Claim: |vx| <= gain/drag for every reachable state (vx2 = (1-drag*dt)*vx +
    gain*cos(phi)*dt has fixed point gain/drag and starts at 0), so one step
    moves x by at most (gain/drag)*dt = 1.0; a slab of half-width W >= 0.5
    therefore cannot be stepped over, whatever the actions. This asserts it
    directly over rollouts of the plant instead of trusting the algebra: no step
    ever starts strictly west of slab 1 and lands strictly east of it."""
    env = PatchField2D(patch_shape="slab", slab_half_width=0.5)
    c = env.p1[0]
    rng_seed, near, jumps, max_dx = 90_000, 0, 0, 0.0
    for i in range(300):
        rng = random.Random(rng_seed + i)
        s = env.initial_state(rng)
        # drive east hard for a while so the sample really reaches high speed
        for t in range(env.h_episode):
            a = 0.0 if t < 40 else rng.uniform(-env.a_max, env.a_max)
            x2, _y2, _, _ = env._integrate(s, a)
            max_dx = max(max_dx, abs(x2 - s[0]))
            if s[0] < c - 0.5 and x2 > c + 0.5:
                jumps += 1
            near += (abs(s[0] - c) < 1.5)
            s = env.step(s, a)[0]
    assert (env.gain / env.drag) * env.dt == 1.0
    assert max_dx <= 1.0, max_dx
    assert jumps == 0
    assert near > 1000, near     # non-vacuous: the sample really got to the slab


# --- 8. the shipped default is the ADMISSIBLE calibrated configuration --------
def test_default_slab_half_width_is_the_admissible_calibrated_one():
    """The default must be the configuration the calibration certifies as
    admissible, not merely the one that matches rarity.

    Two configurations match the disc's rarity. `thin` matches it by narrowing the
    slab to half-width 0.0206 and is INADMISSIBLE: at that width the slab is
    permeable, so the phantom corridor is open and play_cost collapses to 0.012 --
    an instrument with no trap to omit. `imperm` matches it by moving the slab
    (k1 = 5.5) at the impermeable half-width 0.5 and preserves the exploitation
    geometry. The env default is the impermeable width; the position knob is
    supplied per campaign, as it is for the disc.
    """
    if not CALIB.exists():
        pytest.skip("results/patch2d_slab_calibration.json not produced yet")
    summary = json.loads(CALIB.read_text()).get("summary")
    if not summary:
        pytest.skip("calibration artifact incomplete (no summary)")
    verdict = summary["verdict"]
    # the calibration must still agree about which arm is usable
    assert verdict["admissible_imperm"] is True, verdict
    assert verdict["admissible_thin"] is False, verdict
    assert PatchField2D().slab_half_width == summary["imperm_slab_half_width"]


def test_the_inadmissible_thin_arm_is_recorded_with_its_reason():
    """Non-vacuity guard: the artifact must actually carry the numbers that make
    `thin` inadmissible, so this decision cannot silently become unsupported."""
    if not CALIB.exists():
        pytest.skip("results/patch2d_slab_calibration.json not produced yet")
    summary = json.loads(CALIB.read_text()).get("summary")
    if not summary:
        pytest.skip("calibration artifact incomplete (no summary)")
    thin, disc, imperm = (summary["arms"]["thin"], summary["arms"]["disc"],
                          summary["arms"]["imperm"])
    # thin is rarity-matched but NOT danger-preserving: that is the whole point
    assert abs(thin["r1"] - disc["r1"]) < 0.02, (thin["r1"], disc["r1"])
    assert thin["play_cost"] < 0.1, thin["play_cost"]
    assert thin["j_truth"] > 2 * disc["j_truth"], (thin["j_truth"], disc["j_truth"])
    # imperm is both
    assert abs(imperm["r1"] - disc["r1"]) < 0.02, (imperm["r1"], disc["r1"])
    assert abs(imperm["play_cost"] - disc["play_cost"]) < 0.05
    assert imperm["blind_contact_rate"] == 1.0


def test_an_arity_one_predicate_screens_the_far_mode():
    """A slab is unbounded in y, so the near slab screens everything behind it and
    the instrument is necessarily SINGLE-mode. This is a structural fact about a
    one-coordinate trigger in this plant, not a calibration failure, and the paper
    states it as the ablation's one unavoidable confound -- so it is pinned here.
    """
    if not CALIB.exists():
        pytest.skip("results/patch2d_slab_calibration.json not produced yet")
    summary = json.loads(CALIB.read_text()).get("summary")
    if not summary:
        pytest.skip("calibration artifact incomplete (no summary)")
    assert summary["verdict"]["p2_reachable_disc"] is True
    assert summary["verdict"]["p2_reachable_imperm"] is False
    assert summary["arms"]["imperm"]["r2"] == 0.0
