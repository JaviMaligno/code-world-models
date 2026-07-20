import random

from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.evidence_dose import (
    build_dose_sample, is_evidence_capped_failure, refine_capped)
from cwm.llm.provider import FakeProvider


def test_transitions_carry_source_index():
    tr = collect_transitions(ShapeField2D(shape=Circle(3.0, 0.0, 1.0)), n_rollouts=5, seed=0)
    assert [t["source_index"] for t in tr] == list(range(len(tr)))  # stable original order


def test_fixed_size_and_distinct_negatives():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    tr = collect_transitions(env, n_rollouts=60, seed=0)
    ex, allowed, meta = build_dose_sample(env, tr, m=8, span="large", rng=random.Random(0))
    assert len(ex) == 40 and meta["n_positive"] == 8 and meta["n_negative"] == 8
    neg_src = [e["source_index"] for e in ex if not e["contact"]]
    assert len(set(neg_src)) == len(neg_src)  # no negative reused
    assert allowed <= {t["source_index"] for t in tr}  # allowed refers to original indices


def test_background_excludes_all_positives():
    # Circle offset/radius calibrated to ~15% per-episode rarity (see
    # results/shape2d_calibration.json, cell "contrast_circle": rarity=0.15).
    # Before the fix, `bg_pool` only excluded `used_source_indices` (the
    # chosen positives + matched negatives), so an UNCHOSEN positive
    # (contact=True) transition could land in the background block --
    # contradicting the docstring ("background: neither positive nor a
    # matched near-miss") and the meta["n_positive"] == m guarantee. seed=4
    # is a known repro for the old bug (one positive leaked into background).
    env = ShapeField2D(shape=Circle(cx=3.9042205810546875, cy=0.0, R=1.5))
    tr = collect_transitions(env, n_rollouts=200, seed=0)
    m = 8
    for seed in (0, 4, 14, 16, 33):
        ex, allowed, meta = build_dose_sample(env, tr, m=m, span="large", rng=random.Random(seed))
        assert len(ex) == 40
        n_positive_total = sum(1 for e in ex if e["contact"])
        assert n_positive_total == m == meta["n_positive"]
        background = ex[2 * m:]
        assert len(background) == meta["n_background"] == 40 - 2 * m
        assert all(not e["contact"] for e in background)  # no positive leaks into background


def test_capped_failure_uses_source_indices():
    assert is_evidence_capped_failure(failure_source_indices={311, 512}, allowed_source_indices={7, 8, 9}) is True
    assert is_evidence_capped_failure(failure_source_indices={8, 512}, allowed_source_indices={7, 8, 9}) is False


def test_infra_failure_is_not_reported_as_evidence_capped():
    # A syntactically-invalid artifact causes `contract_accuracy_indexed` to
    # hit the GLOBAL sandbox-failure path (produced is None), which reports a
    # single failure with source_index=None -- unattributable to any
    # transition, and therefore never a member of `allowed_source_indices`.
    # Before the fix this made `capped` empty on the very first iteration and
    # mislabeled the run `evidence_capped_failure=True`. It must instead be
    # treated like the uncapped baseline: fed back to the model and refined
    # up to max_iters, with evidence_capped_failure staying False throughout.
    transitions = [
        {"state": [0.0], "action": 0.0, "next_state": [0.0], "reward": 0.0,
         "contact": False, "source_index": i}
        for i in range(5)
    ]
    allowed_source_indices = {0, 1}  # irrelevant to an infra failure
    broken_code = "this is not ) valid ( python $$$"
    provider = FakeProvider([f"```python\n{broken_code}\n```"] * 3)
    result = refine_capped(
        provider, "fake", contract="contract text", code=broken_code,
        gate_transitions=transitions, controlled_examples=transitions,
        allowed_source_indices=allowed_source_indices, eps=1e-9, max_iters=3)
    assert result.evidence_capped_failure is False
    assert result.iterations == 3
    assert result.accuracy == 0.0
