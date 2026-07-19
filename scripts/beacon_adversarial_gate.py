"""Close Beacon's random-coverage hole with targeted belief gates.

The experiment compares three held-out checks:

* random: 2000 uniformly-random games (the paper's original gate);
* mixed: 1999 random games plus one reference-policy game;
* adversarial: bounded deepest-first search over non-terminal oracle states.

The candidate is never used to generate gate states.  The reference policy runs
on the oracle, so the candidate cannot steer verification away from its error.
In Beacon one competent trajectory reaches the deep final region D with
probability one, whereas one random trajectory reaches it with probability
2^(-2T).  Thus the single targeted trajectory should reject the flipped-belief
instrument while preserving essentially the whole random-coverage budget. The
policy-free falsifier should find the same region by prioritizing depth, without
assuming a particular reference policy.

Run: PYTHONPATH=src python scripts/beacon_adversarial_gate.py
"""
import json
from pathlib import Path

from cwm.beacon_instrument import BeaconWrongInference
from cwm.belief_gate import (adversarial_belief_search, check_beliefs,
                             collect_policy_states, random_policy)
from cwm.determinized import determinized_policy
from cwm.groundtruth import beacon as B


T = 8
GATE_GAMES = 2000
SIMULATIONS = 100


def reference_policy(model, state, rng, game, move):
    """The deployed planner family, evaluated only on the trusted oracle."""
    del rng
    return determinized_policy(
        model,
        state,
        n_determinizations=2,
        simulations=SIMULATIONS,
        seed=10_000 + game * 1000 + move,
    )


def _arm(truth, candidate, random_games, reference_games, seed):
    random_states = collect_policy_states(
        truth, n_games=random_games, policy=random_policy, seed=seed)
    reference_states = collect_policy_states(
        truth, n_games=reference_games, policy=reference_policy, seed=seed + 1)
    report = check_beliefs(truth, candidate, random_states + reference_states)
    report.update({
        "random_games": random_games,
        "reference_games": reference_games,
        "reference_final_states": sum(s["board"][8] == 1 for s in reference_states),
    })
    return report


def main():
    truth = B.make_beacon(T)
    candidate = BeaconWrongInference(T)
    random_only = _arm(truth, candidate, GATE_GAMES, 0, seed=0)
    mixed = _arm(truth, candidate, GATE_GAMES - 1, 1, seed=0)
    adversarial = adversarial_belief_search(
        truth, candidate, max_expansions=GATE_GAMES)

    assert random_only["passes"], random_only
    assert not mixed["passes"], mixed
    assert mixed["reference_final_states"] == 2, mixed
    assert adversarial["verdict"] == "reject", adversarial
    assert adversarial["counterexample_depth"] == 2 * T, adversarial

    result = {
        "T": T,
        "gate_games": GATE_GAMES,
        "simulations": SIMULATIONS,
        "random_only": random_only,
        "mixed_one_reference": mixed,
        "bounded_adversarial_search": adversarial,
        "analytic": {
            "random_reach_D_per_game": 0.5 ** (2 * T),
            "reference_reach_D_per_game": 1.0,
            "random_gate_miss_probability": (1 - 0.5 ** (2 * T)) ** GATE_GAMES,
        },
    }
    Path("results").mkdir(exist_ok=True)
    Path("results/beacon_adversarial_gate.json").write_text(
        json.dumps(result, indent=2) + "\n")

    for name, report in (("random-only", random_only),
                         ("mixed (1999 random + 1 reference)", mixed)):
        verdict = "PASS" if report["passes"] else "REJECT"
        print(
            f"{name}: {verdict}; inference mismatches "
            f"{report['inference_mismatches']}/{report['checks']}; "
            f"reference final states={report['reference_final_states']}",
            flush=True,
        )
    print(
        f"bounded adversarial search: REJECT after "
        f"{adversarial['expanded_states']} expanded states / "
        f"{adversarial['belief_checks']} belief checks; "
        f"counterexample depth={adversarial['counterexample_depth']}",
        flush=True,
    )
    print(
        f"analytic random-only miss probability="
        f"{result['analytic']['random_gate_miss_probability']:.6f}",
        flush=True,
    )
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
