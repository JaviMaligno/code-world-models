import random

import pytest

from cwm.beacon_instrument import BeaconWrongInference
from cwm.belief_gate import (adversarial_belief_search, check_beliefs,
                             collect_policy_states, random_policy)
from cwm.groundtruth import beacon as B


def safe_beacon_policy(model, state, rng, game, move):
    del rng, game, move
    board = state["board"]
    player = state["current_player"]
    if board[8] == 1:
        obs = model.observation(state, player)
        inferred = model.infer_states(obs, player)
        return inferred[0]["board"][3 if player == 1 else 2]
    step = board[0] if player == 1 else board[1]
    own_type = board[2] if player == 1 else board[3]
    return model.safe(step, own_type)


def test_random_gate_misses_beacon_deep_error_at_reported_seed():
    truth = B.make_beacon(T=8)
    candidate = BeaconWrongInference(T=8)
    states = collect_policy_states(truth, n_games=2000, policy=random_policy, seed=0)

    report = check_beliefs(truth, candidate, states)

    assert report["passes"]
    assert report["checks"] == 8156
    assert report["inference_mismatches"] == 0


def test_one_competent_trajectory_rejects_beacon_instrument():
    truth = B.make_beacon(T=8)
    candidate = BeaconWrongInference(T=8)
    states = collect_policy_states(truth, n_games=1, policy=safe_beacon_policy, seed=0)

    report = check_beliefs(truth, candidate, states)

    assert not report["passes"]
    assert report["observation_mismatches"] == 0
    assert report["inference_mismatches"] == 4
    assert sum(state["board"][8] == 1 for state in states) == 2


def test_mixed_gate_keeps_budget_and_rejects_with_one_competent_game():
    truth = B.make_beacon(T=8)
    candidate = BeaconWrongInference(T=8)
    random_states = collect_policy_states(
        truth, n_games=1999, policy=random_policy, seed=0)
    competent_states = collect_policy_states(
        truth, n_games=1, policy=safe_beacon_policy, seed=1)

    report = check_beliefs(truth, candidate, random_states + competent_states)

    assert not report["passes"]
    assert report["inference_mismatches"] == 4


def test_adversarial_search_finds_beacon_deep_error_without_reference_policy():
    truth = B.make_beacon(T=8)
    candidate = BeaconWrongInference(T=8)

    report = adversarial_belief_search(truth, candidate, max_expansions=100)

    assert report["verdict"] == "reject"
    assert report["counterexample_found"]
    assert report["counterexample_depth"] == 16
    assert report["counterexample_state"]["board"][8] == 1
    assert report["inference_mismatches"] == 2
    assert report["expanded_states"] <= 20


def test_adversarial_search_budget_is_explicit_when_no_error_found():
    truth = B.make_beacon(T=8)

    report = adversarial_belief_search(truth, truth, max_expansions=5)

    assert report["verdict"] == "inconclusive"
    assert not report["counterexample_found"]
    assert not report["exhausted_reachable_nonterminal_states"]
    assert report["expanded_states"] == 5


def test_adversarial_search_pass_requires_exhaustive_search():
    truth = B.make_beacon(T=2)

    report = adversarial_belief_search(truth, truth, max_expansions=1000)

    assert report["verdict"] == "pass"
    assert not report["counterexample_found"]
    assert report["exhausted_reachable_nonterminal_states"]


def test_belief_gate_rejects_candidate_execution_errors():
    truth = B.make_beacon(T=2)

    class CrashingCandidate:
        observation = truth.observation

        @staticmethod
        def infer_states(obs, player):
            raise RuntimeError("boom")

    report = check_beliefs(truth, CrashingCandidate(), [truth.initial_state()])

    assert not report["passes"]
    assert report["inference_errors"] == 2
    assert report["inference_mismatches"] == 0


def test_collect_policy_states_rejects_illegal_policy_action():
    truth = B.make_beacon(T=2)

    with pytest.raises(ValueError, match="illegal action"):
        collect_policy_states(
            truth, n_games=1,
            policy=lambda model, state, rng, game, move: 99,
            seed=0,
        )


def test_adversarial_search_rejects_nonpositive_budget():
    truth = B.make_beacon(T=2)

    with pytest.raises(ValueError, match="positive"):
        adversarial_belief_search(truth, truth, max_expansions=0)


def test_random_policy_only_returns_legal_actions():
    truth = B.make_beacon(T=2)
    state = truth.initial_state_with(0, 1)

    assert random_policy(truth, state, random.Random(0), 0, 0) in (0, 1)
