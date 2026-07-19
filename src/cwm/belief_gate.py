"""Policy-guided verification for imperfect-information model surfaces.

The original inference gate samples states from uniformly-random play.  This
module keeps the checker independent from the sampling policy so a held-out gate
can mix broad random coverage with states reached by the policy that will
actually use the model.
"""
from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from heapq import heappop, heappush


Policy = Callable[[object, dict, random.Random, int, int], int]


def random_policy(model, state: dict, rng: random.Random, game: int, move: int) -> int:
    """Uniformly sample one legal action."""
    del game, move
    return rng.choice(model.legal_actions(state))


def collect_policy_states(model, n_games: int, policy: Policy, seed: int) -> list[dict]:
    """Collect every non-terminal pre-action state reached by ``policy``.

    Deals are sampled from ``initial_states`` using a local RNG.  The policy is
    evaluated on the reference model, never on the candidate being checked, so
    a wrong candidate cannot steer the gate away from its own error region.
    """
    if n_games < 0:
        raise ValueError("n_games must be non-negative")
    rng = random.Random(seed)
    deals = model.initial_states()
    states: list[dict] = []
    for game in range(n_games):
        deal = deals[rng.randrange(len(deals))]
        state = {"board": list(deal["board"]),
                 "current_player": deal["current_player"]}
        move = 0
        while not model.is_terminal(state):
            states.append({"board": list(state["board"]),
                           "current_player": state["current_player"]})
            action = policy(model, state, rng, game, move)
            legal = model.legal_actions(state)
            if action not in legal:
                raise ValueError(f"gate policy returned illegal action {action}; legal={legal}")
            state = model.apply_action(state, action)
            move += 1
    return states


def _canonical_states(states: Iterable[dict]) -> list[tuple]:
    """Order-insensitive multiset representation of inferred full states."""
    return sorted((tuple(s["board"]), s["current_player"]) for s in states)


def check_beliefs(truth, candidate, states: Iterable[dict]) -> dict:
    """Compare observation and inference outputs on held-out full states.

    Both players are checked at every state.  Inferred states use multiset
    equality, matching the synthesized-CWM inference gate: duplicates or skewed
    support are errors, while output ordering is irrelevant.
    """
    observation_mismatches = inference_mismatches = checks = 0
    observation_errors = inference_errors = 0
    examples: list[str] = []
    n_states = 0
    for state in states:
        n_states += 1
        for player in (1, 2):
            checks += 1
            truth_obs = truth.observation(state, player)
            try:
                candidate_obs = candidate.observation(state, player)
            except Exception as exc:
                observation_errors += 1
                inference_errors += 1
                if len(examples) < 10:
                    examples.append(
                        f"observation error state={state['board']} p={player} "
                        f"error={exc!r}")
                continue
            if candidate_obs != truth_obs:
                observation_mismatches += 1
                if len(examples) < 10:
                    examples.append(
                        f"observation state={state['board']} p={player} got={candidate_obs}")
            truth_inferred = _canonical_states(truth.infer_states(truth_obs, player))
            try:
                candidate_inferred = _canonical_states(
                    candidate.infer_states(candidate_obs, player))
            except Exception as exc:
                inference_errors += 1
                if len(examples) < 10:
                    examples.append(
                        f"inference error state={state['board']} p={player} "
                        f"error={exc!r}")
                continue
            if candidate_inferred != truth_inferred:
                inference_mismatches += 1
                if len(examples) < 10:
                    examples.append(
                        f"inference state={state['board']} p={player} "
                        f"got={candidate_inferred}")
    return {
        "n_states": n_states,
        "checks": checks,
        "observation_mismatches": observation_mismatches,
        "inference_mismatches": inference_mismatches,
        "observation_errors": observation_errors,
        "inference_errors": inference_errors,
        "passes": (observation_mismatches == 0 and inference_mismatches == 0
                   and observation_errors == 0 and inference_errors == 0),
        "examples": examples,
    }


def adversarial_belief_search(truth, candidate, max_expansions: int = 10_000) -> dict:
    """Search the oracle tree for a belief counterexample, deepest states first.

    This is a bounded falsifier.  It returns ``reject`` on a counterexample,
    ``pass`` only after exhausting the reachable non-terminal state space, and
    ``inconclusive`` when the budget is exhausted first.  It checks every state
    it expands and prioritizes depth, which targets survival-style coverage gaps
    without requiring a deployed reference policy.  Terminal children are
    omitted because a planner never queries beliefs after the game has ended.

    The candidate is queried only for verification; oracle transitions determine
    the frontier.  ``max_expansions`` therefore controls oracle/candidate belief
    checks, while the worst-case frontier can still grow exponentially with depth.
    """
    if max_expansions <= 0:
        raise ValueError("max_expansions must be positive")

    frontier: list[tuple[int, int, int, dict]] = []
    queued: set[tuple] = set()
    counter = 0

    def key(state: dict) -> tuple:
        return tuple(state["board"]), state["current_player"]

    def push(state: dict, depth: int) -> None:
        nonlocal counter
        state_key = key(state)
        if state_key in queued:
            return
        queued.add(state_key)
        # Negative depth makes heapq a deepest-first frontier. Counter gives a
        # deterministic ordering without comparing state dictionaries.
        heappush(frontier, (-depth, counter, depth, state))
        counter += 1

    for initial in truth.initial_states():
        push({"board": list(initial["board"]),
              "current_player": initial["current_player"]}, 0)

    expansions = 0
    while frontier and expansions < max_expansions:
        _, _, depth, state = heappop(frontier)
        expansions += 1
        report = check_beliefs(truth, candidate, [state])
        if not report["passes"]:
            return {
                "verdict": "reject",
                "counterexample_found": True,
                "expanded_states": expansions,
                "belief_checks": expansions * 2,
                "counterexample_depth": depth,
                "counterexample_state": state,
                "observation_mismatches": report["observation_mismatches"],
                "inference_mismatches": report["inference_mismatches"],
                "observation_errors": report["observation_errors"],
                "inference_errors": report["inference_errors"],
                "examples": report["examples"],
                "frontier_remaining": len(frontier),
            }
        for action in truth.legal_actions(state):
            child = truth.apply_action(state, action)
            if not truth.is_terminal(child):
                push(child, depth + 1)

    exhausted = not frontier
    return {
        "verdict": "pass" if exhausted else "inconclusive",
        "counterexample_found": False,
        "expanded_states": expansions,
        "belief_checks": expansions * 2,
        "exhausted_reachable_nonterminal_states": exhausted,
        "frontier_remaining": len(frontier),
        "max_expansions": max_expansions,
        "examples": [],
    }
