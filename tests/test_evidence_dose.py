import random

from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.evidence_dose import build_dose_sample, is_evidence_capped_failure


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


def test_capped_failure_uses_source_indices():
    assert is_evidence_capped_failure(failure_source_indices={311, 512}, allowed_source_indices={7, 8, 9}) is True
    assert is_evidence_capped_failure(failure_source_indices={8, 512}, allowed_source_indices={7, 8, 9}) is False
