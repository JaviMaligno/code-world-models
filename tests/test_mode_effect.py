"""Tests for the mode-effect variants that test Proposition prop:entryclass.

The proposition's premise is that the mover never occupies the mode region, which is what
makes an ENTRY rule indistinguishable from the true MEMBERSHIP rule on any sample. Two
variants break it: `landing` (stop where you entered, inside the region) and `clamp`
(project onto the boundary). `freeze` is the committed default.

Three things have to hold for a campaign on a variant to mean anything, and each is a test
here rather than an assumption:
  1. `freeze` is byte-identical to the committed code, in dynamics AND in contract text --
     otherwise the campaigns already run become unreproducible;
  2. the variant really does break the premise, and really does make the two rules
     distinguishable on a sample (the premise could break without the evidence separating
     them, which is what nearly happened with `clamp`);
  3. the contract's full arm states the variant's OWN rule -- a contract still saying "the
     PREVIOUS position" would make the full arm a control for a rule the truth does not
     implement, voiding the comparison.
"""
import math
import pathlib
import random
import subprocess
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D                      # noqa: E402
from cwm.continuous.contract import (build_contract,               # noqa: E402
                                     collect_transitions, mode_blindness)
from cwm.continuous.instruments import _patch2d_rules_text        # noqa: E402

SHAPES = [("disc", {}), ("square", {}), ("slab", {"slab_half_width": 0.5})]
BREAKING = ("landing", "clamp")


def _env(effect="freeze", shape="disc", **kw):
    return PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), patch_shape=shape,
                        mode_effect=effect, **kw)


def test_freeze_is_the_default():
    assert PatchField2D().mode_effect == "freeze"


@pytest.mark.parametrize("shape,kw", SHAPES)
def test_freeze_dynamics_are_unchanged_from_the_committed_code(shape, kw):
    """The committed campaigns must stay reproducible: same transitions, bit for bit."""
    old_src = subprocess.run(
        ["git", "show", "HEAD:src/cwm/continuous/envs.py"],
        capture_output=True, text=True, cwd=_REPO).stdout
    if not old_src:
        pytest.skip("no git HEAD to compare against")
    ns = {}
    exec(compile(old_src, "committed_envs", "exec"), ns)  # noqa: S102 — our own file
    Old = ns["PatchField2D"]
    old = Old(p1=(3.0, 0.0), p2=(7.0, 0.0), patch_shape=shape, **kw)
    new = _env("freeze", shape, **kw)
    contacts = 0
    for r in range(40):
        rng_o, rng_n = random.Random(10_000 + r), random.Random(10_000 + r)
        so, sn = old.initial_state(rng_o), new.initial_state(rng_n)
        assert so == sn
        for _ in range(new.h_episode):
            a = rng_n.uniform(-new.a_max, new.a_max)
            rng_o.uniform(-old.a_max, old.a_max)
            to, tn = old.step(so, a), new.step(sn, a)
            assert to[0] == tn[0] and to[1] == tn[1] and to[2] == tn[2], (
                f"{shape}: freeze dynamics changed")
            contacts += bool(tn[2])
            so, sn = to[0], tn[0]
    assert contacts > 0, "vacuous: the mode never fired in this sample"


@pytest.mark.parametrize("shape,kw", SHAPES)
def test_freeze_contract_text_is_unchanged_from_the_committed_code(shape, kw):
    old_src = subprocess.run(
        ["git", "show", "HEAD:src/cwm/continuous/instruments.py"],
        capture_output=True, text=True, cwd=_REPO).stdout
    if not old_src:
        pytest.skip("no git HEAD to compare against")
    src = (old_src.replace("from .envs import", "from cwm.continuous.envs import")
                  .replace("from .shapes import", "from cwm.continuous.shapes import"))
    ns = {}
    exec(compile(src, "committed_instruments", "exec"), ns)  # noqa: S102
    env = _env("freeze", shape, **kw)
    for include in (True, False):
        assert ns["_patch2d_rules_text"](env, include) == \
            _patch2d_rules_text(env, include), (
                f"{shape} include_mode={include}: the committed contract text changed")


@pytest.mark.parametrize("effect", BREAKING)
def test_the_variant_breaks_the_premise_and_separates_the_two_rules(effect):
    """(2) Both halves, on a sample the size a campaign actually draws."""
    env = _env(effect)
    tr = collect_transitions(env, 40, seed=10_000)

    def inside(x, y):
        return env._inside(x, y, env.p1) or env._inside(x, y, env.p2)

    from_inside = sum(1 for t in tr if inside(t["state"][0], t["state"][1]))
    separating = 0
    for t in tr:
        lx, ly = env._integrate(tuple(t["state"]), t["action"])[:2]
        memb = inside(lx, ly)
        entry = memb and not inside(t["state"][0], t["state"][1])
        separating += (memb != entry)
    assert from_inside > 0, f"{effect}: the premise is not broken on a 40-rollout sample"
    assert separating > 0, (
        f"{effect}: the premise breaks but no sampled transition separates the membership "
        f"rule from the entry rule, so the campaign would test nothing")


def test_freeze_does_NOT_break_the_premise():
    """The control: if this ever fails, prop:entryclass is wrong about this instrument."""
    env = _env("freeze")
    tr = collect_transitions(env, 40, seed=10_000)
    from_inside = [t for t in tr
                   if env._inside(t["state"][0], t["state"][1], env.p1)
                   or env._inside(t["state"][0], t["state"][1], env.p2)]
    assert not from_inside
    assert any(t["contact"] for t in tr), "vacuous: no contacts in this sample"


@pytest.mark.parametrize("effect", ["freeze", "landing", "clamp"])
def test_the_contract_states_the_variant_s_own_rule(effect):
    """(3) The full arm must describe what the truth does, and only the full arm."""
    env = _env(effect)
    full, incomplete = build_contract(env, True), build_contract(env, False)
    delta = "\n".join(l for l in full.split("\n")
                      if l not in incomplete.split("\n"))
    expected = {"freeze": "PREVIOUS position",
                "landing": "LANDING position",
                "clamp": "nearest the landing"}[effect]
    assert expected in delta, f"{effect}: contract does not state its own post-state"
    for other, phrase in (("freeze", "PREVIOUS position"),
                          ("landing", "LANDING position")):
        if other != effect:
            assert phrase not in delta, (
                f"{effect}: contract also claims {other}'s post-state")
    # and the incomplete arm must not leak the mode at all
    for token in ("sticky", "patch centered", "PREVIOUS", "LANDING", "nearest"):
        assert token not in incomplete, f"{effect}: incomplete arm leaks {token!r}"


@pytest.mark.parametrize("effect", ["freeze", "landing", "clamp"])
def test_the_mode_probes_still_fire_in_truth(effect):
    """mode_blindness asserts its probes fire; a fully blind model must score 1.0 on
    every mode under every variant, or the repair criterion is measuring nothing."""
    env = _env(effect)
    blind = """
import math
def step(s, a):
    x, y, vx, vy = s
    a = max(-1.0, min(1.0, a)); phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    return [x + vx2 * 0.1, y + vy2 * 0.1, vx2, vy2]
def reward(s):
    return 0.0
"""
    assert mode_blindness(blind, env) == {"patch1": 1.0, "patch2": 1.0}


def test_clamp_lands_exactly_on_the_boundary():
    env = _env("clamp")
    hit = 0
    for r in range(30):
        rng = random.Random(1234 + r)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            s2, _, contact = env.step(s, rng.uniform(-env.a_max, env.a_max))
            if contact:
                hit += 1
                d = min(math.hypot(s2[0] - c[0], s2[1] - c[1])
                        for c in (env.p1, env.p2))
                assert abs(d - env.R) < 1e-9, f"clamp did not land on the boundary: {d}"
                assert s2[2] == 0.0 and s2[3] == 0.0
            s = s2
    assert hit > 0, "vacuous: the mode never fired"


def test_landing_lands_strictly_inside():
    env = _env("landing")
    hit = 0
    for r in range(30):
        rng = random.Random(1234 + r)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            lx, ly = env._integrate(s, a)[:2]
            s2, _, contact = env.step(s, a)
            if contact:
                hit += 1
                assert (s2[0], s2[1]) == (lx, ly), "landing variant moved the mover"
                assert env._inside(s2[0], s2[1], env.p1) or \
                    env._inside(s2[0], s2[1], env.p2)
            s = s2
    assert hit > 0, "vacuous: the mode never fired"


def test_rarity_is_identical_across_variants():
    """The firing PREDICATE is untouched, so the rarity knob needs no recalibration --
    which is what makes this a one-variable comparison."""
    rar = {}
    for effect in ("freeze", "landing", "clamp"):
        env = _env(effect)
        n = 0
        for r in range(400):
            rng = random.Random(7000 + r)
            s = env.initial_state(rng)
            for _ in range(env.h_episode):
                s, _, c = env.step(s, rng.uniform(-env.a_max, env.a_max))
                if c:
                    n += 1
                    break
        rar[effect] = n / 400
    assert rar["freeze"] > 0.05, f"vacuous: rarity too low {rar}"
    # freeze and landing cannot diverge: the first contact ends the count, and up to the
    # first contact the trajectories are identical. clamp may differ only after it.
    assert rar["freeze"] == rar["landing"] == rar["clamp"], rar


# --- the repair criterion for these variants ---------------------------------------
def _analyzer():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "arity_evidence_ablations", _REPO / "scripts" / "arity_evidence_ablations.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CORRECT = {
    "freeze": "return [x, y, 0.0, 0.0]",
    "landing": "return [x2, y2, 0.0, 0.0]",
    "clamp": ("d = math.hypot(x2 - cx, y2 - cy)\n"
              "        if d == 0.0:\n"
              "            dx2, dy2 = x2 - x, y2 - y\n"
              "            d = math.hypot(dx2, dy2)\n"
              "            if d == 0.0:\n"
              "                dx2, dy2, d = 1.0, 0.0, 1.0\n"
              "            return [cx + 1.0 * dx2 / d, cy + 1.0 * dy2 / d, 0.0, 0.0]\n"
              "        return [cx + 1.0 * (x2 - cx) / d, cy + 1.0 * (y2 - cy) / d, "
              "0.0, 0.0]"),
}

_ARTIFACT = """
import math
def step(s, a):
    x, y, vx, vy = s
    a = max(-1.0, min(1.0, a)); phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2 = x + vx2 * 0.1; y2 = y + vy2 * 0.1
    for cx, cy in ((3.0, 0.0), (7.0, 0.0)):
        if (x2 - cx) ** 2 + (y2 - cy) ** 2 <= 1.0:
        {POST}
    return [x2, y2, vx2, vy2]
def reward(s):
    return 0.0
"""


def _correct_artifact(effect):
    post = _CORRECT[effect].replace("\n", "\n    ")
    return _ARTIFACT.replace("        {POST}", "            " + post)


@pytest.mark.parametrize("effect", ["freeze", "landing", "clamp"])
def test_grid_exactness_accepts_the_correct_rule_for_each_variant(effect):
    """Oracle test for the criterion the campaigns are scored by: hand-write the correct
    rule for the variant and require the criterion to pass it, with the mode actually
    firing on the grid (a criterion that fires nowhere would 'pass' vacuously)."""
    A = _analyzer()
    env = _env(effect)
    r = A.grid_exact(_correct_artifact(effect), env)
    assert r["grid_exact"] is True, (effect, r)
    assert r["grid_mode_firings"] > 100, f"{effect}: criterion is vacuous, {r}"


@pytest.mark.parametrize("effect", ["landing", "clamp"])
def test_grid_exactness_REJECTS_the_right_region_with_the_wrong_post_state(effect):
    """The whole reason the grid criterion exists: an artifact that gets the region right
    and the post-state wrong deviates from the integrator in exactly the same cells, so
    the IoU cannot see it."""
    A = _analyzer()
    env = _env(effect)
    wrong = _correct_artifact("freeze")        # right region, freeze post-state
    r = A.grid_exact(wrong, env)
    assert r["grid_exact"] is False, (effect, r)
    assert r["grid_mismatch"] > 100, r
    # and confirm the IoU really is blind to it, which is the claim being relied on
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "patch2d_artifact_audit", _REPO / "scripts" / "patch2d_artifact_audit.py")
    aud = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aud)
    assert aud.audit_code(wrong, env)["iou_truth"] > 0.99, (
        "the IoU was expected to be blind to a post-state error")
