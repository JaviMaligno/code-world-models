from cwm.run_gap import aggregate_gap

def test_aggregate_gap_math():
    agg = aggregate_gap([
        {"gap": 0.1}, {"gap": 0.3}, {"gap": 0.2},
    ])
    assert agg["n_seeds"] == 3
    assert abs(agg["gap_mean"] - 0.2) < 1e-9
    assert agg["gap_min"] == 0.1
    assert agg["gap_max"] == 0.3

def test_aggregate_gap_empty():
    agg = aggregate_gap([])
    assert agg["n_seeds"] == 0
    assert agg["gap_mean"] == 0.0

def test_aggregate_gap_skips_entries_without_gap():
    # Skipped seeds (gate<1.0) are recorded without a "gap" key and must be
    # excluded from the aggregate, not crash or skew it.
    agg = aggregate_gap([
        {"gap": 0.2}, {"seed": 3, "skipped": "gate<1.0", "accuracy": 0.97},
        {"gap": 0.4},
    ])
    assert agg["n_seeds"] == 2
    assert abs(agg["gap_mean"] - 0.3) < 1e-9
    assert agg["gap_min"] == 0.2
    assert agg["gap_max"] == 0.4
