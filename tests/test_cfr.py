"""MCCFR validation on Kuhn poker, where the equilibrium is analytic:
game value for player 1 is -1/18, and exploitability -> 0."""
import pytest

from cwm.groundtruth import kuhn_poker as K
from cwm.cfr import (MCCFR, VanillaCFRPlus, expected_value,
                     best_response_value, exploitability)

KUHN_VALUE = -1.0 / 18.0


@pytest.fixture(scope="module")
def kuhn_avg_strategy():
    solver = MCCFR(K, seed=0)
    solver.iterate(60_000)
    return solver.average_strategy()


def test_kuhn_game_value(kuhn_avg_strategy):
    v = expected_value(K, kuhn_avg_strategy)
    assert abs(v - KUHN_VALUE) < 0.01


def test_kuhn_exploitability(kuhn_avg_strategy):
    assert exploitability(K, kuhn_avg_strategy) < 0.03


def test_best_response_beats_uniform():
    # Against the uniform profile, P1's best response must earn strictly more
    # than the equilibrium value (uniform is exploitable).
    br1 = best_response_value(K, {}, 1)
    assert br1 > KUHN_VALUE + 0.05


def test_exploitability_nonnegative_uniform():
    assert exploitability(K, {}) > 0.0


def test_cfr_plus_kuhn_tight():
    # Full-tree CFR+ should reach a much tighter equilibrium than sampling,
    # in few iterations.
    solver = VanillaCFRPlus(K)
    solver.iterate(2000)
    avg = solver.average_strategy()
    assert abs(expected_value(K, avg) - KUHN_VALUE) < 0.002
    assert exploitability(K, avg) < 0.01
