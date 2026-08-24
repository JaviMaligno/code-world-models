"""Tests for the held-out (three-way split) gate audit — paper 2 review #1.

Two things are load-bearing here and both get an INDEPENDENT check:

1. The split's disjointness.  ``collect_transitions`` seeds rollout *i* with
   ``random.Random(seed + i)``, so the claim "no held-out rollout was ever a
   training rollout" is a statement about integer blocks.  It is proved twice:
   once by brute-force set intersection over every block any committed campaign
   uses, and once by an independent pairwise interval oracle that does not call
   the module under test.  A negative control (a deliberately colliding offset)
   proves the detector is not vacuously True, and a data-level check proves the
   realized rollouts differ, not just the seeds.

2. The scoring.  ``score_transitions`` must return exactly what the paper's own
   ``contract_accuracy`` returns (it exists only to additionally report WHICH
   transitions failed and whether they were mode contacts), and its accuracy is
   also checked against a brute-force in-process oracle that never touches the
   sandbox path or ``_compare_transitions``.

No test here makes a network call.
"""
import importlib.util
import json
import math
import pathlib

import pytest

from cwm.continuous.contract import (collect_transitions, contract_accuracy,
                                     sample_contains_mode)
from cwm.continuous.envs import CartWall, PatchField2D, PendulumStop
from cwm.continuous.heldout import (
    EVAL_SEED_OFFSET, GATE_SEED_OFFSET, N_EVAL_DEFAULT, N_GATE, R_SOURCES,
    TRAIN_N_ROLLOUTS, blind_from_cell, contingency, disjointness_report,
    env_from_params, env_key, failure_class, independence_surrogate,
    mode_presence, score_transitions, seed_block, split_for_cell,
    train_rollout_seeds, wilson)

_REPO = pathlib.Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "heldout_gate_audit.py"
_spec = importlib.util.spec_from_file_location("heldout_gate_audit_mod", _SCRIPT)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


# --- fixture artifacts (hand-written, byte-identical plant to the truth) ------
ENV = CartWall(x_wall=8.0)

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
BLIND_CODE = FULL_CODE.replace(
    "    if x2 >= 8.0:\n        return [8.0, 0.0]\n", "")
# pervasive-error control: drag mis-scaled, wall intact -> failures EVERYWHERE,
# which is the off-mode failure class the audit must distinguish from the mode.
BIASED_CODE = FULL_CODE.replace("0.3 * v", "0.6 * v")


def _wall_sample(n_rollouts=40, seed=GATE_SEED_OFFSET + 10_000):
    """A sample that really contains wall contacts (asserted by the callers, so
    every test that depends on the interesting branch says so out loud)."""
    return collect_transitions(ENV, n_rollouts, seed=seed)


# --- 1. the split is disjoint -------------------------------------------------
def test_seed_block_matches_collect_transitions_seeding():
    """seed_block must be the set of integers collect_transitions really uses:
    rollout i of collect_transitions(env, n, seed) is random.Random(seed + i)."""
    import random
    seed, n = 12_345, 7
    got = collect_transitions(ENV, n, seed=seed)
    h = ENV.h_episode
    assert len(got) == n * h
    for i in range(n):
        rng = random.Random(seed + i)
        assert got[i * h]["state"][0] == pytest.approx(
            ENV.initial_state(rng)[0], abs=0.0)
    assert seed_block(seed, n) == {seed + i for i in range(n)}


def _pairwise_interval_oracle(n_train, n_gate, n_eval):
    """Independent oracle: enumerate every (train, gate, eval) block as a
    half-open interval and count overlaps with max/min arithmetic only.  Does
    not import disjointness_report or seed_block."""
    seeds = [10_000 * (i + 1 + off) for off in (0, 20) for i in range(20)]
    blocks = ([("train", s, s + n_train) for s in seeds]
              + [("gate", s + 5_000_000, s + 5_000_000 + n_gate) for s in seeds]
              + [("eval", s + 7_000_000, s + 7_000_000 + n_eval) for s in seeds])
    overlaps = []
    for i in range(len(blocks)):
        ki, ai, bi = blocks[i]
        for j in range(i + 1, len(blocks)):
            kj, aj, bj = blocks[j]
            if max(ai, aj) < min(bi, bj):
                overlaps.append((ki, kj, ai, aj))
    return overlaps


def test_heldout_blocks_are_disjoint_from_every_train_block():
    rep = disjointness_report(n_train=TRAIN_N_ROLLOUTS, n_gate=N_GATE,
                              n_eval=N_EVAL_DEFAULT)
    # non-vacuity: the report really covered 40 campaign seeds and full blocks
    assert rep["n_train_seeds"] == 40
    assert rep["train_seed_min"] == 10_000 and rep["train_seed_max"] == 400_000
    assert rep["train_union_size"] == 40 * TRAIN_N_ROLLOUTS
    assert rep["gate_union_size"] == 40 * N_GATE
    assert rep["eval_union_size"] == 40 * N_EVAL_DEFAULT
    assert rep["train_gate_overlap"] == []
    assert rep["train_eval_overlap"] == []
    assert rep["gate_eval_overlap"] == []
    assert rep["gate_within_family_overlap_seeds"] == []
    assert rep["eval_within_family_overlap_seeds"] == []
    assert rep["all_disjoint"] is True
    # independent oracle agrees there is no overlap at all
    assert _pairwise_interval_oracle(TRAIN_N_ROLLOUTS, N_GATE,
                                     N_EVAL_DEFAULT) == []


def test_disjointness_detector_is_not_vacuous():
    """Negative control: with a colliding offset the SAME function must report
    an overlap, so the True above is a measurement and not a tautology."""
    bad = disjointness_report(n_train=TRAIN_N_ROLLOUTS, n_gate=N_GATE,
                             n_eval=N_EVAL_DEFAULT, gate_offset=0)
    assert bad["all_disjoint"] is False
    assert bad["train_gate_overlap"]
    # and a within-family collision is detectable too (stride 10_000 < n_eval)
    crowded = disjointness_report(n_eval=20_000)
    assert crowded["eval_within_family_overlap_seeds"]
    assert crowded["all_disjoint"] is False


def test_realized_heldout_rollouts_are_not_training_rollouts():
    """Data-level check: the initial states of the held-out rollouts never
    coincide with any training rollout's initial state, for every committed
    train seed of the cart instrument."""
    h = ENV.h_episode
    train_starts, gate_starts, eval_starts = set(), set(), set()
    for s in train_rollout_seeds():
        for name, off, n, bag in (("train", 0, TRAIN_N_ROLLOUTS, train_starts),
                                  ("gate", GATE_SEED_OFFSET, N_GATE, gate_starts),
                                  ("eval", EVAL_SEED_OFFSET, 8, eval_starts)):
            ts = collect_transitions(ENV, n, seed=s + off)
            for i in range(n):
                bag.add(ts[i * h]["state"][0])
    assert len(train_starts) == 40 * TRAIN_N_ROLLOUTS      # no accidental dupes
    assert not (train_starts & gate_starts)
    assert not (train_starts & eval_starts)
    assert not (gate_starts & eval_starts)


def test_split_for_cell_reproduces_the_three_blocks():
    cell = {"seed": 10_000, "n_rollouts": 40, "eps": 1e-9}
    d_train, d_gate, d_eval = split_for_cell(ENV, cell, n_eval=5)
    assert d_train == collect_transitions(ENV, 40, seed=10_000)
    assert d_gate == collect_transitions(ENV, 40, seed=10_000 + GATE_SEED_OFFSET)
    assert d_eval == collect_transitions(ENV, 5, seed=10_000 + EVAL_SEED_OFFSET)
    assert d_train != d_gate != d_eval


# --- 2. scoring ---------------------------------------------------------------
def _oracle_score(code: str, transitions, eps: float):
    """Brute-force in-process oracle: exec the artifact here, call its step /
    reward directly and count matches.  Deliberately avoids the sandbox path,
    _run_contract_cases and _compare_transitions, so it can contradict them."""
    ns: dict = {}
    exec(code, ns)  # noqa: S102 — hand-written fixture code, not LLM output
    n_ok = 0
    fails_contact, fails_off = 0, 0
    for t in transitions:
        s2 = ns["step"](list(t["state"]), t["action"])
        r = ns["reward"](list(s2))
        err = max(max(abs(a - b) for a, b in zip(s2, t["next_state"])),
                  abs(r - t["reward"]))
        if err <= eps:
            n_ok += 1
        elif t["contact"]:
            fails_contact += 1
        else:
            fails_off += 1
    return n_ok / len(transitions), fails_contact, fails_off


def test_score_transitions_equals_contract_accuracy_on_a_passing_artifact():
    sample = _wall_sample()
    assert sample_contains_mode(sample), "fixture must exercise the mode branch"
    res = score_transitions(FULL_CODE, sample, eps=1e-9)
    acc, _ = contract_accuracy(FULL_CODE, sample, eps=1e-9)
    assert res.accuracy == acc == 1.0
    assert res.n_mode_contact > 0
    assert res.n_fail == 0 and res.exact_outside_mode is True


def test_score_transitions_equals_contract_accuracy_on_a_failing_artifact():
    sample = _wall_sample()
    assert sample_contains_mode(sample)
    res = score_transitions(BLIND_CODE, sample, eps=1e-9)
    acc, _ = contract_accuracy(BLIND_CODE, sample, eps=1e-9)
    assert res.accuracy == acc < 1.0
    # the interesting branch: the blind artifact fails ONLY on mode contacts
    assert res.n_fail > 0
    assert res.n_fail_mode_contact == res.n_fail
    assert res.n_fail_off_mode == 0
    assert res.exact_outside_mode is True
    assert res.max_err_off_mode_fail is None


def test_score_transitions_matches_the_bruteforce_oracle():
    sample = _wall_sample()
    assert sample_contains_mode(sample)
    for code in (FULL_CODE, BLIND_CODE, BIASED_CODE):
        res = score_transitions(code, sample, eps=1e-9)
        o_acc, o_contact, o_off = _oracle_score(code, sample, eps=1e-9)
        assert res.accuracy == pytest.approx(o_acc, abs=0.0), code[:40]
        assert res.n_fail_mode_contact == o_contact
        assert res.n_fail_off_mode == o_off


def test_off_mode_failures_are_separated_from_mode_failures():
    """The load-bearing distinction: a pervasive (off-mode) error must NOT be
    reported as a mode failure, and must set exact_outside_mode False."""
    sample = _wall_sample()
    res = score_transitions(BIASED_CODE, sample, eps=1e-9)
    assert res.n_fail_off_mode > 0, "the biased control must fail off-mode"
    assert res.exact_outside_mode is False
    assert res.max_err_off_mode_fail is not None
    assert res.max_err_off_mode_fail > 1e-9
    assert failure_class(res.to_json()) in ("off_mode_only", "mixed")


def test_score_transitions_reports_infra_failure_like_contract_accuracy():
    broken = "def step(state, action):\n    raise SystemExit(3)\n"
    sample = collect_transitions(ENV, 2, seed=1)
    res = score_transitions(broken, sample, eps=1e-9)
    acc, _ = contract_accuracy(broken, sample, eps=1e-9)
    assert res.accuracy == acc == 0.0
    assert res.infra_error


def test_failure_class_labels():
    base = {"infra_error": None, "n_fail": 0, "n_fail_off_mode": 0,
            "n_fail_mode_contact": 0}
    assert failure_class(base) == "no_failures"
    assert failure_class({**base, "n_fail": 3, "n_fail_mode_contact": 3}) \
        == "mode_only"
    assert failure_class({**base, "n_fail": 3, "n_fail_off_mode": 3}) \
        == "off_mode_only"
    assert failure_class({**base, "n_fail": 3, "n_fail_off_mode": 1,
                          "n_fail_mode_contact": 2}) == "mixed"
    assert failure_class({**base, "infra_error": "boom"}) == "infra_error"


# --- 3. env reconstruction against the committed campaigns --------------------
@pytest.mark.parametrize("fname,expect_key", [
    ("continuous_synthesis_large_xwall8.json", "cart_xwall8"),
    ("continuous_synthesis_mini_xwall4.json", "cart_xwall4"),
    ("continuous_synthesis_pendulum_large_thstop1.4.json",
     "pendulum_thstop1.4"),
    ("continuous_synthesis_pendulum_large_thstop1.json", "pendulum_thstop1"),
    ("continuous_synthesis_patch2d_large_k3_7.json", "patch2d_k3_7"),
    ("continuous_synthesis_patch2d_mini_k5_9.json", "patch2d_k5_9"),
    ("continuous_synthesis_patch2dsq_large_k3_7.json", "patch2dsq_k3_7"),
    # the campaigns added in the major revision, each of which changes the stream
    ("continuous_synthesis_patch2dslab_large_k5.5_7.json", "patch2dslab_k5.5_7"),
    ("continuous_synthesis_patch2dlanding_large_k3_7.json", "patch2d_k3_7_landing"),
    ("continuous_synthesis_patch2dclamp_large_k3_7.json", "patch2d_k3_7_clamp"),
    ("continuous_synthesis_patch2d_large_k3_7_arc240.json",
     "patch2d_k3_7_arc240_n15"),
    ("continuous_synthesis_patch2d_large_k3_7_arc120.json",
     "patch2d_k3_7_arc120_n15"),
])
def test_env_key_and_type_match_the_filename(fname, expect_key):
    d = json.loads((_REPO / "results" / fname).read_text())
    assert env_key(d["params"]) == expect_key
    env = env_from_params(d["params"])
    if expect_key.startswith("cart"):
        assert isinstance(env, CartWall) and env.x_wall is not None
    elif expect_key.startswith("pendulum"):
        assert isinstance(env, PendulumStop) and env.th_stop is not None
    else:
        assert isinstance(env, PatchField2D)
        # read the shape from the params, not by substring-matching the key: guessing
        # the instrument from the key's spelling is the bug this file now pins
        assert env.patch_shape == d["params"].get("patch_shape", "disc")
        assert env.mode_effect == d["params"].get("mode_effect", "freeze")
        assert env.start_arc_deg == d["params"].get("start_arc")


@pytest.mark.parametrize("fname", [
    "continuous_synthesis_large_xwall8.json",
    "continuous_synthesis_pendulum_large_thstop1.4.json",
    "continuous_synthesis_patch2d_large_k3_7.json",
])
def test_reproduced_training_sample_reproduces_the_stored_gate_score(fname):
    """The strongest available check that env_from_params + the seed convention
    rebuild the ORIGINAL training sample: re-scoring the committed artifact on
    the reproduced D_train must return the accuracy the original run stored,
    and the stored sample_contains_wall flag must come back out."""
    d = json.loads((_REPO / "results" / fname).read_text())
    env = env_from_params(d["params"])
    cell = d["cells"][0]
    d_train, _, _ = split_for_cell(env, cell, n_eval=1)
    assert mode_presence(env, d_train)["any"] == cell["sample_contains_wall"]
    acc, _ = contract_accuracy(cell["code"], d_train, eps=cell["eps"],
                              timeout=300.0)
    assert acc == cell["gate_accuracy"]


def test_env_from_params_defaults_match_the_synthesis_script():
    """Older committed files predate the instrument/patch_shape flags, so the
    defaults must be the synthesis script's argparse defaults."""
    assert env_from_params({"x_wall": 8.0}) == CartWall(x_wall=8.0)
    assert env_from_params({"instrument": "pendulum", "x_wall": 8.0}) \
        == PendulumStop(th_stop=1.4)
    assert env_from_params({"instrument": "patch2d", "x_wall": 8.0}) \
        == PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), patch_shape="disc")
    with pytest.raises(ValueError):
        env_from_params({"instrument": "shape2d"})


# --- 4. mode presence --------------------------------------------------------
def test_mode_presence_counts_rollouts_and_transitions():
    sample = _wall_sample()
    mp = mode_presence(ENV, sample)
    assert mp["any"] is True and mp["per"] is None
    assert mp["n_rollouts"] == N_GATE
    assert 0 < mp["n_rollouts_with_contact"] <= N_GATE
    assert mp["n_contact_transitions"] >= mp["n_rollouts_with_contact"]
    # the miss event is reachable too (a 2-rollout far-wall sample)
    tiny = collect_transitions(ENV, 2, seed=0)
    assert mode_presence(ENV, tiny)["any"] is False


def test_mode_presence_per_mode_for_patch2d():
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    sample = collect_transitions(env, 40, seed=GATE_SEED_OFFSET + 10_000)
    mp = mode_presence(env, sample)
    assert set(mp["per"]) == {"patch1", "patch2"}
    # non-vacuous: the common patch really does fire in this held-out block
    assert mp["per"]["patch1"] is True
    assert mp["any"] is True


def test_blind_from_cell():
    assert blind_from_cell({"wall_blindness": 1.0}) is True
    assert blind_from_cell({"wall_blindness": 0.0}) is False
    assert blind_from_cell({"wall_blindness": None}) is None
    assert blind_from_cell({"mode_blindness": {"patch1": 1.0, "patch2": 1.0},
                            "wall_blindness": 1.0}) is True
    assert blind_from_cell({"mode_blindness": {"patch1": 0.0, "patch2": 1.0},
                            "wall_blindness": 0.5}) is False


# --- 5. aggregation ----------------------------------------------------------
def _rec(gate_mode, accepted, arm="incomplete", seed=10_000, off=0, mode=0):
    return {"file": "f.json", "arm": arm, "seed": seed,
            "mode_in_gate": {"any": gate_mode},
            "accepted_heldout": accepted,
            "gate": {"accuracy": 1.0 if accepted else 0.5,
                     "n_fail_mode_contact": mode, "n_fail_off_mode": off}}


def test_contingency_table_and_coincidence():
    recs = [_rec(False, True), _rec(False, True), _rec(True, False)]
    c = contingency(recs, row_key=lambda r: r["mode_in_gate"]["any"],
                    col_key=lambda r: r["accepted_heldout"])
    assert c["table"]["gate_mode_absent"]["accepted"] == 2
    assert c["table"]["gate_mode_present"]["rejected"] == 1
    assert c["coincides_exactly"] is True and c["n_disagree"] == 0
    assert c["off_diagonal"] == []
    # one disagreement must be caught AND identified
    recs.append(_rec(True, True, seed=20_000))
    c2 = contingency(recs, row_key=lambda r: r["mode_in_gate"]["any"],
                     col_key=lambda r: r["accepted_heldout"])
    assert c2["coincides_exactly"] is False and c2["n_disagree"] == 1
    assert c2["off_diagonal"][0]["seed"] == 20_000


def test_wilson_wrapper():
    assert wilson(0, 0) is None
    lo, hi = wilson(20, 20)
    assert 0.8 < lo < 0.9 and hi == 1.0


def test_independence_surrogate():
    assert independence_surrogate(0.0, 0.0) == 0.0
    assert independence_surrogate(0.2, 0.5) == pytest.approx(0.6)
    assert independence_surrogate(1.0, 0.3) == 1.0


# --- 6. the script: rarity provenance, resume, idempotence -------------------
def test_verify_r_sources_rederives_every_constant():
    """Every rarity used for the two-factor prediction is re-read from the JSON
    that produced it; the test re-reads them a third time, here."""
    got = audit.verify_r_sources()
    reach = json.loads((_REPO / "results" / "continuous_reach.json").read_text())
    pend = json.loads((_REPO / "results" / "continuous_pendulum.json").read_text())
    p2d = json.loads((_REPO / "results" / "continuous_patch2d.json").read_text())
    r8 = next(r for r in reach["rows"] if r["x_wall"] == 8.0)["rarity"]
    r14 = next(r for r in pend["rows"] if r["th_stop"] == 1.4)["rarity"]
    r10 = next(r for r in pend["rows"] if r["th_stop"] == 1.0)["rarity"]
    ru = next(r for r in p2d["rows"]
              if r["k1"] == 3.0 and r["k2"] == 7.0)["r_either"]
    assert got["cart_xwall8"]["r"] == r8
    assert got["pendulum_thstop1.4"]["r"] == r14
    assert got["pendulum_thstop1"]["r"] == r10
    assert got["patch2d_k3_7"]["r"] == ru
    # the uncalibrated cells are reported as such, never silently filled in
    assert got["patch2d_k5_9"]["r"] is None
    assert got["patch2dsq_k3_7"]["r"] is None
    assert "r_union_independence_surrogate" in got["patch2dsq_k3_7"]
    assert "DERIVED" in got["patch2dsq_k3_7"][
        "r_union_independence_surrogate_note"]


def test_verify_r_sources_detects_drift(monkeypatch):
    """Negative control for the provenance guard."""
    patched = {k: dict(v) for k, v in R_SOURCES.items()}
    patched["cart_xwall8"]["r"] = 0.99
    monkeypatch.setattr(audit, "R_SOURCES", patched)
    with pytest.raises(SystemExit):
        audit.verify_r_sources()


def _write_fake_campaign(tmp_path: pathlib.Path) -> pathlib.Path:
    """A synthesis-shaped file with two hand-written artifacts: one correct
    (accepted on any sample) and one wall-blind (accepted iff the sample misses
    the wall).  Seed 10_000's D_gate DOES contain the wall (asserted below), so
    the blind artifact must be REJECTED by the independent gate — the exact
    regression the audit exists to find."""
    doc = {"script": "continuous_danger_synthesis.py", "model": "fake-model",
           "size": "mini", "tag": "mini",
           "params": {"instrument": "cart", "x_wall": 8.0, "n_rollouts": 4,
                      "eps": 1e-9},
           "cells": []}
    for arm, code in (("full", FULL_CODE), ("incomplete", BLIND_CODE)):
        train = collect_transitions(ENV, 4, seed=10_000)
        acc, _ = contract_accuracy(code, train, eps=1e-9)
        doc["cells"].append({
            "arm": arm, "seed": 10_000, "n_rollouts": 4, "eps": 1e-9,
            "sample_contains_wall": sample_contains_mode(train),
            "gate_accuracy": acc, "gate_passed": acc == 1.0,
            "refine_iterations": 0,
            "wall_blindness": 0.0 if arm == "full" else 1.0,
            "code": code})
    out = tmp_path / "continuous_synthesis_fake_xwall8.json"
    out.write_text(json.dumps(doc))
    return out


def test_script_end_to_end_is_resumable_and_idempotent(tmp_path):
    _write_fake_campaign(tmp_path)
    out = tmp_path / "audit.json"
    # a small n_eval keeps the test fast; n_gate stays at the mandated 40
    argv = ["--results-dir", str(tmp_path), "--out", str(out),
            "--n-eval", "4", "--validate-train-per-file", "2"]

    # phase 1: --limit 1 leaves the run deliberately incomplete
    assert audit.main(argv + ["--limit", "1"]) == 0
    doc1 = json.loads(out.read_text())
    assert len(doc1["artifacts"]) == 1 and doc1["complete"] is False

    # phase 2: resume finishes it without redoing the first artifact
    assert audit.main(argv) == 0
    doc2 = json.loads(out.read_text())
    assert len(doc2["artifacts"]) == 2 and doc2["complete"] is True
    keys = [(a["file"], a["arm"], a["seed"]) for a in doc2["artifacts"]]
    assert len(set(keys)) == 2
    assert doc2["artifacts"][0] == doc1["artifacts"][0]   # untouched on resume

    # phase 3: re-running a complete audit is a no-op
    assert audit.main(argv) == 0
    doc3 = json.loads(out.read_text())
    assert [(a["file"], a["arm"], a["seed"]) for a in doc3["artifacts"]] == keys

    # the interesting branch really was exercised
    by_arm = {a["arm"]: a for a in doc3["artifacts"]}
    assert by_arm["full"]["mode_in_train"]["any"] is False       # rare mode
    assert by_arm["full"]["in_sample_gate_passed"] is True
    assert by_arm["incomplete"]["in_sample_gate_passed"] is True
    assert by_arm["incomplete"]["mode_in_gate"]["any"] is True, \
        "the held-out gate block must contain the wall for this to be a test"
    assert by_arm["full"]["accepted_heldout"] is True
    assert by_arm["incomplete"]["accepted_heldout"] is False
    agg = doc3["aggregates"]
    assert agg["totals"]["n_regressions"] == 1
    assert agg["c_regressions"]["by_failure_class"] == {"mode_only": 1}
    assert agg["train_reproduction_check"]["n_checked"] == 2
    assert agg["train_reproduction_check"]["n_accuracy_matches"] == 2
    assert agg["train_reproduction_check"]["mismatches"] == []
    # (a): on the train-miss subset of the incomplete arm, acceptance coincides
    # with "the gate block also missed the mode" -- here 0 accepted / 1 rejected
    inc = agg["a_contingency"]["incomplete_arm"]
    assert inc["n"] == 1 and inc["coincides_exactly"] is True
    # (d): the blind artifact's D_eval failures are all mode contacts
    assert agg["d_out_of_sample_exactness"]["n_exceptions"] == 0
    assert doc3["split"]["all_disjoint"] is True


def test_script_finds_the_reverse_regression(tmp_path):
    """The other side of the same coin: an artifact the in-sample gate REFUSED
    that an independent gate ACCEPTS.  Cart seed 120000's training block
    contains the wall (so the blind artifact is refused in-sample) while its
    held-out gate block does not (so the blind artifact passes it) -- asserted
    below, so this is a real branch and not a lucky fixture."""
    train = collect_transitions(ENV, 40, seed=120_000)
    gate = collect_transitions(ENV, 40, seed=120_000 + GATE_SEED_OFFSET)
    assert sample_contains_mode(train) and not sample_contains_mode(gate)
    acc_train, _ = contract_accuracy(BLIND_CODE, train, eps=1e-9)
    assert acc_train < 1.0
    doc = {"script": "continuous_danger_synthesis.py", "model": "fake-model",
           "size": "mini", "tag": "mini",
           "params": {"instrument": "cart", "x_wall": 8.0, "n_rollouts": 40,
                      "eps": 1e-9},
           "cells": [{"arm": "incomplete", "seed": 120_000, "n_rollouts": 40,
                      "eps": 1e-9, "sample_contains_wall": True,
                      "gate_accuracy": acc_train, "gate_passed": False,
                      "refine_iterations": 5, "wall_blindness": 1.0,
                      "code": BLIND_CODE}]}
    (tmp_path / "continuous_synthesis_rev_xwall8.json").write_text(
        json.dumps(doc))
    out = tmp_path / "audit.json"
    assert audit.main(["--results-dir", str(tmp_path), "--out", str(out),
                       "--n-eval", "4", "--validate-train-per-file", "1"]) == 0
    got = json.loads(out.read_text())
    a = got["artifacts"][0]
    assert a["in_sample_gate_passed"] is False
    assert a["accepted_heldout"] is True
    agg = got["aggregates"]
    assert agg["totals"]["n_reverse_regressions"] == 1
    assert agg["totals"]["n_regressions"] == 0
    assert agg["c_regressions"]["reverse_detail"][0]["seed"] == 120_000
    assert agg["train_reproduction_check"]["n_accuracy_matches"] == 1


def test_aggregate_rejects_an_uncatalogued_env_key():
    """A campaign whose instrument cell has no rarity entry must hard-error
    rather than silently produce a null prediction."""
    rec = {"file": "f.json", "campaign": "f", "env_key": "cart_xwall99",
           "arm": "incomplete", "seed": 10_000, "n_train_rollouts": 40,
           "model": "m", "block_key": "cart_xwall99@10000",
           "in_sample_gate_passed": True, "accepted_heldout": True,
           "probe_blind_all_modes": True,
           "mode_in_train": {"any": False}, "mode_in_gate": {"any": False},
           "mode_in_eval": {"any": False, "n_rollouts_with_contact": 0,
                            "n_rollouts": 100, "n_contact_transitions": 0},
           "gate": {"accuracy": 1.0, "n_fail_mode_contact": 0,
                    "n_fail_off_mode": 0, "n_fail": 0, "infra_error": None},
           "eval": {"accuracy": 1.0, "n_fail_mode_contact": 0,
                    "n_fail_off_mode": 0, "n_fail": 0, "infra_error": None},
           "gate_failure_class": "no_failures",
           "eval_failure_class": "no_failures"}
    rec["mode_in_gate"].update({"n_rollouts_with_contact": 0, "n_rollouts": 40,
                                "n_contact_transitions": 0})
    with pytest.raises(SystemExit):
        audit.aggregate([rec], 40, 100)


def test_script_refuses_a_resume_with_a_different_split(tmp_path):
    _write_fake_campaign(tmp_path)
    out = tmp_path / "audit.json"
    argv = ["--results-dir", str(tmp_path), "--out", str(out),
            "--n-eval", "4", "--validate-train-per-file", "0"]
    assert audit.main(argv) == 0
    with pytest.raises(SystemExit):
        audit.main(["--results-dir", str(tmp_path), "--out", str(out),
                    "--n-eval", "6", "--validate-train-per-file", "0"])


def test_script_refuses_to_shrink_the_gate_below_40(tmp_path):
    with pytest.raises(SystemExit):
        audit.main(["--results-dir", str(tmp_path), "--n-gate", "20"])


# --- 7. the committed audit output, if present --------------------------------
def test_committed_audit_json_is_self_consistent():
    path = _REPO / "results" / "heldout_gate_audit.json"
    if not path.exists():
        pytest.skip("results/heldout_gate_audit.json not produced yet")
    doc = json.loads(path.read_text())
    assert doc["split"]["all_disjoint"] is True
    assert doc["params"]["n_gate"] >= N_GATE
    arts = doc["artifacts"]
    keys = [(a["file"], a["arm"], a["seed"]) for a in arts]
    assert len(set(keys)) == len(keys), "duplicate artifacts in the audit"
    agg = doc["aggregates"]
    assert agg["totals"]["n_artifacts"] == len(arts)
    # every recomputable total must match a recount of the artifact list
    assert agg["totals"]["n_heldout_accepted"] == sum(
        1 for a in arts if a["accepted_heldout"])
    assert agg["totals"]["n_regressions"] == sum(
        1 for a in arts if a["in_sample_gate_passed"]
        and not a["accepted_heldout"])
    assert agg["d_out_of_sample_exactness"]["n_exceptions"] == sum(
        1 for a in arts if not a["eval"]["infra_error"]
        and a["eval"]["n_fail_off_mode"] > 0)
    # acceptance is exactly "held-out gate accuracy == 1.0"
    for a in arts:
        assert a["accepted_heldout"] == (a["gate"]["accuracy"] == 1.0)
        assert a["gate"]["n"] == doc["params"]["n_gate"] * 80
        assert a["eval"]["n"] == doc["params"]["n_eval"] * 80
        assert math.isclose(
            a["gate"]["accuracy"],
            a["gate"]["n_correct"] / a["gate"]["n"], rel_tol=0, abs_tol=0)
        assert (a["gate"]["n_fail_mode_contact"]
                + a["gate"]["n_fail_off_mode"] == a["gate"]["n_fail"])
    if doc.get("complete"):
        # DERIVED, not typed: the count was hardcoded to 625 and went stale the moment the
        # revision's campaigns landed. What the test is for is COMPLETENESS -- every cell
        # of every committed campaign was re-scored -- so it counts them.
        # Counted over the audit's OWN scope: results/ is shared with paper 3, and a
        # ring2d campaign is not an artifact this audit failed to cover, it is one it
        # does not claim (audit.AUDITED_INSTRUMENTS says why).
        import glob
        expected = 0
        for f in glob.glob(str(_REPO / "results" / "continuous_synthesis_*.json")):
            d = json.loads(pathlib.Path(f).read_text())
            instrument = d.get("params", {}).get("instrument", "cart")
            if instrument not in audit.AUDITED_INSTRUMENTS:
                continue
            expected += len(d.get("cells", []))
        assert agg["totals"]["n_artifacts"] == expected, (
            f"the audit covers {agg['totals']['n_artifacts']} artifacts but the committed "
            f"campaigns hold {expected}: re-run scripts/heldout_gate_audit.py")
        assert agg["train_reproduction_check"]["mismatches"] == []


def test_env_key_separates_the_slab_from_the_square():
    """The bug this pins: env_key mapped every non-disc shape to "sq", so a slab and a
    square at the same knob collapsed onto ONE key -- and the key is what the audit
    deduplicates samples on and looks the rarity up by. At a shared knob the slab would
    silently have been scored against the square's rarity. It surfaced only because the
    slab's calibrated knob (5.5) had no R_SOURCES entry and the guard refused to run,
    which is luck rather than design."""
    base = {"instrument": "patch2d", "k1": 3.0, "k2": 7.0}
    keys = {env_key({**base, "patch_shape": sh})
            for sh in ("disc", "square", "slab")}
    assert len(keys) == 3, keys


def test_env_key_separates_every_field_the_rollout_stream_depends_on():
    """The stream depends on the post-state, the start distribution and the rollout
    count as well as the shape and the knob. Two artifacts sharing an env_key and a seed
    are asserted elsewhere to share their samples bit-for-bit, so any of these missing
    from the key makes that assertion false."""
    base = {"instrument": "patch2d", "k1": 3.0, "k2": 7.0}
    variants = [
        base,
        {**base, "mode_effect": "landing"},
        {**base, "mode_effect": "clamp"},
        {**base, "start_arc": 120.0, "n_rollouts": 15},
        {**base, "start_arc": 240.0, "n_rollouts": 15},
        {**base, "n_rollouts": 15},
        {**base, "patch_shape": "slab", "k1": 5.5},
    ]
    keys = [env_key(v) for v in variants]
    assert len(set(keys)) == len(keys), keys


def test_the_committed_defaults_keep_their_original_keys():
    """625 artifacts were audited under the pre-fix keys; the fix must not rename them."""
    assert env_key({"instrument": "patch2d", "k1": 3.0, "k2": 7.0}) == "patch2d_k3_7"
    assert env_key({"instrument": "patch2d", "k1": 3.0, "k2": 7.0,
                    "patch_shape": "square"}) == "patch2dsq_k3_7"
    # explicit defaults must be indistinguishable from absent ones
    assert env_key({"instrument": "patch2d", "k1": 3.0, "k2": 7.0,
                    "mode_effect": "freeze", "start_arc": None,
                    "n_rollouts": 40}) == "patch2d_k3_7"


def test_every_committed_campaign_has_a_rarity_entry():
    """The guard that caught the collision only fires at audit time, on the campaign it
    reaches. This makes it fire in CI, for all of them, before any scoring runs."""
    import glob
    from cwm.continuous.heldout import R_SOURCES
    missing = set()
    for f in glob.glob(str(_REPO / "results" / "continuous_synthesis_*.json")):
        d = json.loads(pathlib.Path(f).read_text())
        params = d.get("params") or {}
        if not params.get("instrument") and "x_wall" not in params:
            continue
        try:
            k = env_key(params)
        except Exception:
            continue
        if k not in R_SOURCES:
            missing.add((pathlib.Path(f).name, k))
    assert not missing, f"campaigns with no R_SOURCES entry: {sorted(missing)}"


def test_a_surrogate_is_never_built_from_a_missing_rarity():
    """The slab's patch-2 rarity was never measured. A surrogate built from it would be
    a fabrication dressed as a derivation, so it must be absent, not filled in."""
    from cwm.continuous.heldout import R_SOURCES
    slab = R_SOURCES["patch2dslab_k5.5_7"]
    assert slab["r"] is None
    assert slab["per_mode"]["patch2"] is None
    assert slab["per_mode"]["patch1"] is not None


# --- 9. ring2d (paper 3) enters the audit -------------------------------------
_RING_SWEEP = _REPO / "scripts" / "ring2d_rarity_sweep.py"
_ring_spec = importlib.util.spec_from_file_location("ring2d_rarity_sweep_mod",
                                                    _RING_SWEEP)
ring_sweep = importlib.util.module_from_spec(_ring_spec)
_ring_spec.loader.exec_module(ring_sweep)


def _ring2d_campaign_files():
    return sorted((_REPO / "results").glob("continuous_synthesis_ring2d_*.json"))


def test_env_key_ring2d_separates_every_stream_field():
    """All five stream-defining fields (gap, channel, start, ring_norm, multi)
    plus n_rollouts must each change the key: leaving one out is the
    slab-vs-square collision on a sixth instrument."""
    base = {"instrument": "ring2d"}
    variants = [
        base,
        {**base, "gap": 0.6},
        {**base, "gap": 0.6, "channel": "hidden"},
        {**base, "start": "inside"},
        {**base, "ring_norm": "cheby"},
        {**base, "multi": True, "start": "middle"},
        {**base, "start": "inside", "n_rollouts": 80},
    ]
    keys = [env_key(v) for v in variants]
    assert len(set(keys)) == len(keys), keys


def test_env_key_ring2d_defaults_are_indistinguishable_from_absent():
    """A campaign that serialised the explicit defaults must key identically to
    an old file that predates the flags (this is what keeps committed keys
    stable when a flag is added)."""
    assert env_key({"instrument": "ring2d"}) == "ring2d_gap0"
    assert env_key({"instrument": "ring2d", "gap": 0.0, "channel": "facing",
                    "start": "outside", "ring_norm": "euclid", "multi": False,
                    "n_rollouts": 40,
                    # other instruments' defaults ride along in the namespace
                    # and must not touch the key
                    "x_wall": 8.0, "k1": 3.0, "k2": 7.0,
                    "patch_shape": "disc"}) == "ring2d_gap0"


def test_env_key_ring2d_matches_the_campaigns_own_knob():
    """The key must be ring2d_<KNOB> with the synthesis script's own knob
    string (mirrored by the sweep's knob_of), plus the _n suffix exactly when
    the campaign overrode --n-rollouts."""
    files = _ring2d_campaign_files()
    assert files, "no committed ring2d campaigns found"
    for f in files:
        params = json.loads(f.read_text())["params"]
        knob = ring_sweep.knob_of(ring_sweep.config_of(params))
        expect = f"ring2d_{knob}"
        n = params.get("n_rollouts", 40)
        if n != 40:
            expect += f"_n{n}"
        assert env_key(params) == expect, f.name


def test_env_from_params_ring2d_matches_the_sweep_mirror():
    """env_from_params and the sweep script's env_of are two mirrors of the
    same synthesis-script block; they must rebuild the SAME env for every
    committed campaign, field for field."""
    import dataclasses
    for f in _ring2d_campaign_files():
        params = json.loads(f.read_text())["params"]
        a = env_from_params(params)
        b = ring_sweep.env_of(ring_sweep.config_of(params))
        assert dataclasses.asdict(a) == dataclasses.asdict(b), f.name


@pytest.mark.parametrize("fname", [
    # closed ring, outside start (the headline configuration)
    "continuous_synthesis_ring2d_compat-qwen3-coder-30b-a3b-instruct_gap0.json",
])
def test_reproduced_training_sample_reproduces_the_stored_gate_score_ring2d(fname):
    """Same strongest-available check as for the paper-2 instruments: the
    reproduced D_train must give back the committed artifact's stored gate
    accuracy and mode-presence flag exactly."""
    d = json.loads((_REPO / "results" / fname).read_text())
    env = env_from_params(d["params"])
    cell = d["cells"][0]
    d_train, _, _ = split_for_cell(env, cell, n_eval=1)
    assert mode_presence(env, d_train)["any"] == cell["sample_contains_wall"]
    acc, _ = contract_accuracy(cell["code"], d_train, eps=cell["eps"],
                               timeout=300.0)
    assert acc == cell["gate_accuracy"]


def test_ring2d_rarity_entries_use_the_firing_rarity():
    """The r-vs-r_int decision, pinned: every ring2d entry's prediction
    argument is the mode-FIRING rarity (kind 'firing', the event the audit's
    contingency counts), r_interior is carried alongside as provenance with
    its own source path, and both values match the sweep JSON exactly."""
    sweep = json.loads((_REPO / "results" / "ring2d_rarity_sweep.json")
                       .read_text())
    rows = {r["knob"]: r for r in sweep["rows"]}
    ring_keys = {k: v for k, v in R_SOURCES.items() if k.startswith("ring2d_")}
    assert ring_keys, "no ring2d entries in R_SOURCES"
    for key, meta in ring_keys.items():
        knob = key[len("ring2d_"):].split("_n")[0]
        assert meta["kind"] == "firing", key
        assert meta["r"] == rows[knob]["r"], key
        assert meta["r_interior"] == rows[knob]["r_interior"], key
        assert meta["source"] == "results/ring2d_rarity_sweep.json", key
        assert "r_interior_path" in meta, key


def test_committed_ring2d_audit_json_is_self_consistent():
    """The ring2d audit's own output file, held to the same recount checks as
    paper 2's -- and completeness judged against the ring2d campaigns only
    (its scope), never against paper 2's."""
    path = _REPO / "results" / "heldout_gate_audit_ring2d.json"
    if not path.exists():
        pytest.skip("results/heldout_gate_audit_ring2d.json not produced yet")
    doc = json.loads(path.read_text())
    assert doc["split"]["all_disjoint"] is True
    assert doc["params"]["n_gate"] >= N_GATE
    assert doc["params"].get("instruments") == ["ring2d"]
    arts = doc["artifacts"]
    keys = [(a["file"], a["arm"], a["seed"]) for a in arts]
    assert len(set(keys)) == len(keys), "duplicate artifacts in the audit"
    agg = doc["aggregates"]
    assert agg["totals"]["n_artifacts"] == len(arts)
    assert agg["totals"]["n_heldout_accepted"] == sum(
        1 for a in arts if a["accepted_heldout"])
    assert agg["totals"]["n_regressions"] == sum(
        1 for a in arts if a["in_sample_gate_passed"]
        and not a["accepted_heldout"])
    for a in arts:
        assert a["accepted_heldout"] == (a["gate"]["accuracy"] == 1.0)
        assert a["gate"]["n"] == doc["params"]["n_gate"] * 80
    if doc.get("complete"):
        expected = sum(
            len(json.loads(f.read_text()).get("cells", []))
            for f in _ring2d_campaign_files())
        assert agg["totals"]["n_artifacts"] == expected, (
            f"the ring2d audit covers {agg['totals']['n_artifacts']} artifacts "
            f"but the committed ring2d campaigns hold {expected}: re-run "
            f"scripts/heldout_gate_audit.py --instruments ring2d")
        # ONE reproduction mismatch is known and pinned rather than allowed
        # away: mini_gap0.6-hid seed 10000 hacked the in-sample gate with an
        # exact-equality point trap on the contact state's floats, and its
        # hardcoded y is 2 ULPs from what this platform's libm produces along
        # the same trajectory -- so the stored 1.0 is platform-contingent and
        # the recomputed score is 3199/3200. Held-out conclusions are
        # unaffected (D_gate's contact states are different floats entirely,
        # so the trap misses them on EVERY platform). Any OTHER mismatch is a
        # real reproduction failure and must fail here.
        mm = agg["train_reproduction_check"]["mismatches"]
        assert [(m["file"], m["seed"], m["recomputed_train_accuracy"])
                for m in mm] in (
            [],  # a run on the original platform reproduces even the trap
            [("continuous_synthesis_ring2d_mini_gap0.6-hid.json", 10000,
              0.9996875)],
        ), mm
