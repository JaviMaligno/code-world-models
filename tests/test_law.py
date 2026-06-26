from cwm.law import wilson_ci, rarity, arena_winrate, danger
from cwm.groundtruth import gen_chess_material as gm

def test_wilson_ci_bounds():
    p, lo, hi = wilson_ci(5, 10)
    assert p == 0.5 and 0.0 <= lo < 0.5 < hi <= 1.0
    p0, lo0, hi0 = wilson_ci(0, 0)
    assert (p0, lo0, hi0) == (0.0, 0.0, 1.0)
    # more data -> tighter interval
    _, lo_small, hi_small = wilson_ci(5, 10)
    _, lo_big, hi_big = wilson_ci(50, 100)
    assert (hi_big - lo_big) < (hi_small - lo_small)

def test_danger_monotonicity():
    # (1-rarity)^N shrinks as rarity rises, so danger decreases with rarity
    assert danger(0.3, 0.01, 40) > danger(0.3, 0.20, 40)
    # increasing in play_cost
    assert danger(0.4, 0.05, 40) > danger(0.2, 0.05, 40)
    # exact value
    assert abs(danger(0.5, 0.0, 40) - 0.5) < 1e-12

def test_rarity_counts_rule_reason():
    g = gm.make_material(max_plies=40)        # short cap -> rule fires often-ish
    rate, lo, hi = rarity(g, "material", n_games=60, seed=1)
    assert 0.0 <= lo <= rate <= hi <= 1.0

def test_arena_winrate_fair_baseline():
    # truth vs itself -> ~0.5, and counts are consistent
    g = gm.make_material(max_plies=40)
    res = arena_winrate(g, g, sims=60, n_games=10, seeds=[0, 1])
    assert res["n"] == 20
    assert res["wins"] + res["draws"] + res["losses"] == 20
    assert 0.0 <= res["lo"] <= res["winrate"] <= res["hi"] <= 1.0
