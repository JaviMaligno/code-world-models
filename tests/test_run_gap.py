from cwm.run_gap import aggregate_gap, _play_performance
from cwm.groundtruth import gen_chess_material, gen_chess

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

def test_aggregate_gap_includes_play_winrate():
    agg = aggregate_gap([
        {"gap": 0.0, "gap_truth": 0.0, "play": {"cwm_winrate": 0.2}},
        {"gap": 0.0, "gap_truth": 0.0, "play": {"cwm_winrate": 0.4}},
        {"seed": 9, "skipped": "gate<1.0"},
    ])
    assert agg["play_n"] == 2
    assert abs(agg["cwm_winrate_mean"] - 0.3) < 1e-9
    assert agg["cwm_winrate_min"] == 0.2 and agg["cwm_winrate_max"] == 0.4

def test_aggregate_gap_no_play_key_when_absent():
    agg = aggregate_gap([{"gap": 0.0, "gap_truth": 0.0}])
    assert "cwm_winrate_mean" not in agg

def test_play_performance_runs_and_reports():
    # truth has the material-at-cap rule; the "CWM" is base army5x5a (omits it).
    # Unit test only checks the metric computes a well-formed result (the
    # directional 'rule-blind agent loses' claim is for the full experiment at
    # proper simulation counts, not a fast unit test).
    res = _play_performance(gen_chess_material, gen_chess, sims=80, n_games=6, seed=0)
    assert set(res) == {"cwm_wins", "truth_wins", "draws", "cwm_illegal", "cwm_winrate"}
    assert res["cwm_wins"] + res["truth_wins"] + res["draws"] == 6
    assert 0.0 <= res["cwm_winrate"] <= 1.0
