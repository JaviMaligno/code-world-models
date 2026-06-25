from cwm.run_gap import aggregate_gap

def test_aggregate_gap_math():
    agg = aggregate_gap([
        {"gap": 0.1, "gap_truth": 0.5},
        {"gap": 0.3, "gap_truth": 0.7},
        {"gap": 0.2, "gap_truth": 0.6},
    ])
    assert agg["n_seeds"] == 3
    assert abs(agg["gap_mean"] - 0.2) < 1e-9
    assert agg["gap_min"] == 0.1 and agg["gap_max"] == 0.3
    assert abs(agg["gap_truth_mean"] - 0.6) < 1e-9
    assert agg["gap_truth_min"] == 0.5 and agg["gap_truth_max"] == 0.7

def test_aggregate_gap_empty():
    agg = aggregate_gap([])
    assert agg["n_seeds"] == 0
    assert agg["gap_mean"] == 0.0
    assert agg["gap_truth_mean"] == 0.0

def test_aggregate_gap_skips_entries_without_gap():
    agg = aggregate_gap([
        {"gap": 0.2, "gap_truth": 0.4},
        {"seed": 3, "skipped": "gate<1.0", "accuracy": 0.97},
        {"gap": 0.4, "gap_truth": 0.8},
    ])
    assert agg["n_seeds"] == 2
    assert abs(agg["gap_mean"] - 0.3) < 1e-9
    assert abs(agg["gap_truth_mean"] - 0.6) < 1e-9
