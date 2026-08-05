"""Tests for Proposition prop:entryclass (freeze semantics censor the region's interior).

The proposition has three parts and each is checkable directly against the instruments:

  (i)   every state a truth rollout visits lies outside the mode region;
  (ii)  therefore a predicate agreeing with membership on the reachable set is exactly
        equal to the truth on every rollout -- no sample distinguishes them;
  (iii) a planner rolling such a model forward also never enters the region, so the
        disagreement region has query-hit probability zero.

These are oracle tests: (i) and (iii) are checked by direct enumeration of rollouts, and
(ii) by constructing an entry-detector model here and comparing it against the truth
transition by transition, rather than by trusting any campaign artifact.
"""
import math
import pathlib
import random
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D  # noqa: E402
from cwm.continuous.contract import collect_transitions  # noqa: E402

INSTRUMENTS = [
    pytest.param({"p1": (3.0, 0.0), "p2": (7.0, 0.0), "patch_shape": "disc"}, id="disc"),
    pytest.param({"p1": (3.0, 0.0), "p2": (7.0, 0.0), "patch_shape": "square"},
                 id="square"),
    pytest.param({"p1": (5.5, 0.0), "p2": (7.0, 0.0), "patch_shape": "slab",
                  "slab_half_width": 0.5}, id="slab"),
]


def _inside(env, x, y):
    return env._inside(x, y, env.p1) or env._inside(x, y, env.p2)


@pytest.mark.parametrize("kw", INSTRUMENTS)
def test_part_i_no_visited_state_is_inside_the_region(kw):
    """(i) The freeze resets to the PREVIOUS position, so the region's interior is never
    occupied. This is the premise the whole proposition rests on."""
    env = PatchField2D(**kw)
    visited = inside = contacts = 0
    for r in range(60):
        rng = random.Random(4242 + r)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            visited += 1
            if _inside(env, s[0], s[1]):
                inside += 1
            a = rng.uniform(-env.a_max, env.a_max)
            s2, _, contact = env.step(s, a)
            contacts += bool(contact)
            s = s2
    assert inside == 0, f"{inside} of {visited} visited states were inside the region"
    assert contacts > 0, "vacuous: this sample never fired the mode"


@pytest.mark.parametrize("kw", INSTRUMENTS)
def test_part_i_every_contact_is_an_entry_from_outside(kw):
    """The same fact stated the way the evidence sees it: a sample witnesses only
    entries, never a step taken from inside."""
    env = PatchField2D(**kw)
    tr = collect_transitions(env, 40, seed=10_000)
    contacts = [t for t in tr if t["contact"]]
    assert contacts, "vacuous: no contacts in this sample"
    from_inside = [t for t in contacts if _inside(env, t["state"][0], t["state"][1])]
    assert not from_inside, f"{len(from_inside)} contacts started inside the region"


def _entry_detector_model(env):
    """A model that freezes when the step CROSSES the slab's west face instead of when
    the landing lies in the slab. On the reachable set the two are equivalent; strictly
    inside the slab they are not."""
    west = env.p1[0] - env.slab_half_width

    def step(s, a):
        x, y, vx, vy = s
        a = max(-env.a_max, min(env.a_max, a))
        phi = math.pi * a / env.a_max
        vx2 = vx + (env.gain * math.cos(phi) - env.drag * vx) * env.dt
        vy2 = vy + (env.gain * math.sin(phi) - env.drag * vy) * env.dt
        x2, y2 = x + vx2 * env.dt, y + vy2 * env.dt
        if (x2 - west) * (x - west) <= 0.0:
            return (x, y, 0.0, 0.0)
        return (x2, y2, vx2, vy2)

    return step


def test_part_ii_an_entry_detector_is_exact_on_every_sampled_transition():
    """(ii) No sample distinguishes it -- checked on three disjoint blocks, one of them
    2.5x the gate's size."""
    env = PatchField2D(p1=(5.5, 0.0), p2=(7.0, 0.0), patch_shape="slab",
                       slab_half_width=0.5)
    model = _entry_detector_model(env)
    total = contacts = 0
    for seed, n in ((10_000, 40), (5_010_000, 40), (7_010_000, 100)):
        tr = collect_transitions(env, n, seed=seed)
        for t in tr:
            total += 1
            contacts += bool(t["contact"])
            got = model(tuple(t["state"]), t["action"])
            assert max(abs(g - e) for g, e in zip(got, t["next_state"])) <= 1e-9, (
                f"seed {seed}: the entry detector differs from the truth on a SAMPLED "
                f"transition, which contradicts part (ii)")
    assert contacts > 0, "vacuous: no contacts across the three blocks"
    assert total > 10_000


def test_part_ii_is_not_vacuous_the_two_rules_do_differ_off_sample():
    """The pair must actually be a pair: equal on every sample, unequal inside."""
    env = PatchField2D(p1=(5.5, 0.0), p2=(7.0, 0.0), patch_shape="slab",
                       slab_half_width=0.5)
    model = _entry_detector_model(env)
    s = (5.4, 0.0, 0.0, 0.0)          # already inside the slab [5, 6]
    a = 0.0                            # thrust east: the landing is also inside
    truth, _, contact = env.step(s, a)
    got = model(s, a)
    assert contact, "the probe state must fire the mode in truth"
    assert max(abs(g - e) for g, e in zip(got, truth)) > 1e-6, (
        "the entry detector must DISAGREE with the truth strictly inside the region")


def test_part_iii_the_models_own_rollouts_never_enter_the_region():
    """(iii) hence q_hit(E) = 0 and prop:playcost forces play_cost = 0."""
    env = PatchField2D(p1=(5.5, 0.0), p2=(7.0, 0.0), patch_shape="slab",
                       slab_half_width=0.5)
    model = _entry_detector_model(env)
    inside = steps = froze = 0
    for r in range(40):
        rng = random.Random(900_000 + r)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s = model(s, a)
            steps += 1
            if _inside(env, s[0], s[1]):
                inside += 1
            if s[2] == 0.0 and s[3] == 0.0:
                froze += 1
    assert inside == 0, f"{inside} of {steps} model-rolled states were inside the region"
    assert froze > 0, "vacuous: the model never froze, so nothing was tested"
