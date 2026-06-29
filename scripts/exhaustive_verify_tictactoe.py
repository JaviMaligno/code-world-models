"""Upgrade the §3.2 null from "no observed divergence" to a proof-by-exhaustion,
on the one game small enough to enumerate fully: tic-tac-toe.

Synthesize a tic-tac-toe CWM (Azure), confirm it passes the random gate, then
enumerate EVERY reachable state of the true game (BFS from the initial state) and
check the synthesized code against the truth on the entire reachable transition
relation: legal_actions, is_terminal, returns on each state, and apply_action on
every (state, legal action). Zero mismatches over the full reachable set ⇒ the
gate-passing CWM is *globally correct on reachable states*, proven, not sampled.

This is the transition-function analogue of the coverage bound (Theorem 1): when
the check covers the whole reachable relation, passing it certifies global
correctness by exhaustion.

Run: PYTHONPATH=src python3.12 scripts/exhaustive_verify_tictactoe.py [mini|large]
"""
import os, sys, random, json
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import tictactoe as truth
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.run_gap import _load_module_from_code

SIZE = sys.argv[1] if len(sys.argv) > 1 else "mini"
MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[SIZE]]


def all_reachable_states(model):
    """BFS over the TRUE game from the initial state; return every reachable state
    (keyed by its board+player), in discovery order."""
    start = model.initial_state()
    seen = {}
    order = []
    frontier = [start]
    while frontier:
        s = frontier.pop()
        key = (tuple(s["board"]), s["current_player"])
        if key in seen:
            continue
        seen[key] = s
        order.append(s)
        if model.is_terminal(s):
            continue
        for a in model.legal_actions(s):
            frontier.append(model.apply_action(s, a))
    return order


def exhaustive_check(cwm, states):
    """Compare the synthesized cwm against the truth on EVERY reachable state and
    every (state, legal action). Search-relevant mismatches (the ones a planner can
    ever query) are separated from the documented terminal-legal convention artifact:
    a planner never calls legal_actions on a terminal state, so a divergence there is
    behaviourally irrelevant (the paper's `legal_terminal_divergences`). Returns
    (n_states, n_transitions, real_mismatches[], terminal_legal_artifacts)."""
    real = []
    terminal_legal = 0
    n_trans = 0
    for s in states:
        st = {"board": list(s["board"]), "current_player": s["current_player"]}
        terminal = truth.is_terminal(s)
        try:
            if cwm.legal_actions(st) != truth.legal_actions(s):
                if terminal:
                    terminal_legal += 1            # convention artifact, excluded
                else:
                    real.append(("legal_actions", s["board"]))
            if cwm.is_terminal(st) != terminal:
                real.append(("is_terminal", s["board"]))
            if cwm.returns(st) != truth.returns(s):
                real.append(("returns", s["board"]))
            for a in truth.legal_actions(s):       # truth.legal_actions([] on terminals)
                n_trans += 1
                if cwm.apply_action({"board": list(s["board"]),
                                     "current_player": s["current_player"]}, a) != truth.apply_action(s, a):
                    real.append(("apply_action", s["board"], a))
        except Exception as e:
            real.append(("exception", s["board"], repr(e)[:120]))
    return len(states), n_trans, real, terminal_legal


def main():
    print(f"synth size = {SIZE}", flush=True)
    contract = build_contract(truth.RULES_TEXT)
    traj = collect_trajectories(truth, n_games=15, seed=7)
    code, _ = synthesize_cwm(provider, MODEL, contract, traj)
    refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=5)
    print(f"random gate: accuracy={refined.accuracy:.4f} iters={refined.iterations}", flush=True)
    cwm = _load_module_from_code(refined.code)

    states = all_reachable_states(truth)
    n_states, n_trans, real, terminal_legal = exhaustive_check(cwm, states)
    print(f"reachable states (exhaustive BFS) = {n_states}", flush=True)
    print(f"transitions checked = {n_trans}", flush=True)
    print(f"terminal-legal convention artifacts (excluded, planner never queries) = {terminal_legal}", flush=True)
    print(f"SEARCH-RELEVANT mismatches over the full reachable relation = {len(real)}", flush=True)
    if real:
        print("examples:", real[:5], flush=True)
    verdict = ("PROVEN globally correct on the entire reachable search-relevant relation"
               if refined.accuracy >= 1.0 and not real
               else "NOT globally correct / gate not passed")
    print(f"VERDICT: {verdict}", flush=True)
    from pathlib import Path
    Path("results").mkdir(exist_ok=True)
    Path("results/exhaustive_tictactoe.json").write_text(json.dumps({
        "size": SIZE, "gate_accuracy": refined.accuracy, "gate_iters": refined.iterations,
        "reachable_states": n_states, "transitions_checked": n_trans,
        "terminal_legal_artifacts": terminal_legal,
        "search_relevant_mismatches": len(real), "verdict": verdict}, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    main()
