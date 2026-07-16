"""Mechanism tests for the 2D bi-modal instrument (prototype-validated
expectations, 2026-07-16: r1~0.14, r2~0.008; truth-MPC reaches the real lode
with unmodified mpc.plan; blind-MPC freezes at patch 1, pc=1.000)."""
import random

from cwm.continuous.envs import PatchField2D, blind_of, blind_of_modes
from cwm.continuous import harness

ENV = PatchField2D()


def test_step_integrator_and_patch_semantics():
    # free step from rest heading east (a=0 -> phi=0)
    s2, r, c = ENV.step((0.0, 0.0, 0.0, 0.0), 0.0)
    assert not c and abs(s2[0] - 0.03) < 1e-12 and s2[1] == 0.0
    # a step that would enter patch 1 freezes at the PREVIOUS position
    s = (1.95, 0.0, 3.0, 0.0)   # next x2 ~ 2.24 -> inside disc((3,0),1)
    s2, r, c = ENV.step(s, 0.0)
    assert c and s2 == (1.95, 0.0, 0.0, 0.0)
    assert ENV.contact_modes(s, 0.0) == (True, False)


def test_blind_variants():
    b = blind_of(ENV)
    assert b.p1 is None and b.p2 is None
    s = (1.95, 0.0, 3.0, 0.0)
    s2, _, c = b.step(s, 0.0)
    assert not c and s2[0] > 2.0          # sails through the phantom patch
    b2 = blind_of_modes(ENV, ("p2",))
    assert b2.p1 == ENV.p1 and b2.p2 is None


def test_rarity_split():
    h1 = h2 = 0
    n = 200
    for i in range(n):
        rng = random.Random(50_000 + i)
        s = ENV.initial_state(rng)
        c1 = c2 = False
        for _ in range(ENV.h_episode):
            a = rng.uniform(-ENV.a_max, ENV.a_max)
            m1, m2 = ENV.contact_modes(s, a)
            c1, c2 = c1 or m1, c2 or m2
            s = ENV.step(s, a)[0]
        h1 += c1
        h2 += c2
    assert 0.08 < h1 / n < 0.22            # r1 ~ 0.14
    assert h2 / n < 0.05                   # r2 ~ 0.008


def test_truth_navigates_and_blind_is_pinned():
    t = harness.run_episode(ENV, ENV, "mpc", seed=0, n_samples=40)
    b = harness.run_episode(ENV, blind_of(ENV), "mpc", seed=0, n_samples=40)
    assert t.ret > 10.0                    # sits on the real lode
    assert abs(t.final_state[0] - ENV.lode_real[0]) < 2.5
    assert b.contact and b.ret < 1.0       # frozen at a patch edge
    assert b.final_state[0] < 3.0
