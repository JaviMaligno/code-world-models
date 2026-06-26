import random
from cwm.determinized import determinized_policy
from cwm.groundtruth import kuhn_poker as k

def test_returns_legal_action():
    s = k.initial_state()
    a = determinized_policy(k, s, simulations=50, seed=1)
    assert a in k.legal_actions(s)

def test_beats_random_at_kuhn():
    # determinized planner (both as P1 and P2, alternating) vs a random agent,
    # refereed by the true game; the planner should not lose money on net.
    rng = random.Random(0)
    net = 0.0
    deals = k.initial_states()
    for i in range(60):
        s = dict(deals[i % len(deals)])
        s = {"board": list(s["board"]), "current_player": 1}
        planner_is_p1 = (i % 2 == 0)
        while not k.is_terminal(s):
            p = s["current_player"]
            if (p == 1) == planner_is_p1:
                a = determinized_policy(k, s, simulations=80, seed=1 + i)
            else:
                a = rng.choice(k.legal_actions(s))
            s = k.apply_action(s, a)
        r = k.returns(s)
        net += r[1] if planner_is_p1 else r[2]
    assert net > 0      # a planner should beat a random opponent on net chips


def test_imperfect_arena_fair_baseline_truth_vs_truth():
    from cwm.determinized import imperfect_arena
    from cwm.groundtruth import kuhn_poker as k
    res = imperfect_arena(k, k, k, simulations=60, n_games=40, seeds=[0, 1])
    assert res["n"] == 80
    assert res["a_wins"] + res["b_wins"] + res["ties"] == 80
    assert 0.0 <= res["lo"] <= res["a_winrate"] <= res["hi"] <= 1.0
    # symmetric self-play with alternating deals -> roughly even
    assert 0.30 < res["a_winrate"] < 0.70
