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
