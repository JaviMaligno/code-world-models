"""Claim B probe (imperfect-info, real LLM synthesis on masked tic-tac-toe).

Demonstrates that a CWM's belief model is invisible to a transition gate.
Synthesize masked tic-tac-toe two ways:
  (full)     rules include the masking rule (the center cell is hidden);
  (withheld) the masking sentence is removed (rules describe tic-tac-toe + that this
             is an imperfect-info variant, but NOT what is hidden).
For each: transition gate (accuracy on random transitions) AND inference gate
(observation_rate / inference_rate). Expected: transition gate ~1.0 in BOTH (the
dynamics are recall, blind to masking); inference gate passes full, fails withheld
(the synthesized observation does not mask the center -> observation_rate drops).

Run: PYTHONPATH=src python3.12 scripts/mtt_claimB_probe.py [large|mini|nano]
"""
import os
import sys
import random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import masked_tictactoe as M
from cwm.world_model import build_imperfect_contract
from cwm.trajectories import Trajectory
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.gap import inference_accuracy

# Remove exactly the masking paragraph for the withheld variant.
_MASK_SENTENCE = (
    "  - Imperfect information: the center cell (index 4) is hidden from BOTH players —\n"
    "    observation shows it as -1, even after a mark has been placed there. All other\n"
    "    cells are public. infer_states must enumerate every value (0, 1, 2) of the\n"
    "    hidden center that yields a legal position (X starts, so the count of 1s equals\n"
    "    the count of 2s, or exceeds it by exactly one); the true state is always among\n"
    "    them.\n")
RULES_FULL = M.RULES_TEXT
RULES_WITHHELD = RULES_FULL.replace(
    _MASK_SENTENCE,
    "  - Imperfect information: this is a partially-observable variant; provide the\n"
    "    contract's observation and infer_states functions.\n")
assert RULES_WITHHELD != RULES_FULL, "masking-rule replace was a no-op — check _MASK_SENTENCE"


def collect_transitions(model, n_games, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n_games):
        s = model.initial_state()
        while not model.is_terminal(s):
            legal = model.legal_actions(s)
            a = rng.choice(legal)
            nxt = model.apply_action(s, a)
            out.append(Trajectory(state=s, action=a, next_state=nxt,
                                  reward=model.returns(nxt), terminal=model.is_terminal(nxt),
                                  legal_actions=legal))
            s = nxt
    return out


def random_states(model, n, seed):
    """Reachable full states (mid-game, where the center may be filled or empty)."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        s = model.initial_state()
        while not model.is_terminal(s):
            out.append({"board": list(s["board"]), "current_player": s["current_player"]})
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return out[:n]


def run(label, rules, provider, model_name):
    print(f"\n=== {label} ===", flush=True)
    contract = build_imperfect_contract(rules)
    traj = collect_transitions(M, n_games=60, seed=1)
    code, _ = synthesize_cwm(provider, model_name, contract, traj)
    refined = refine_cwm(provider, model_name, contract, code, traj, max_iters=8)
    print(f"transition gate: accuracy={refined.accuracy:.4f} iters={refined.iterations}",
          flush=True)
    sample = random_states(M, 50, seed=2)
    inf = inference_accuracy(refined.code, sample, M)
    print(f"inference gate: observation_rate={inf['observation_rate']:.3f} "
          f"inference_rate={inf['inference_rate']:.3f} n={inf['n']} exec_err={inf['n_exec_errors']}",
          flush=True)
    if inf["examples"]:
        print("  examples:", inf["examples"][:2], flush=True)
    return {"label": label, "transition_acc": refined.accuracy,
            "observation_rate": inf["observation_rate"], "inference_rate": inf["inference_rate"]}


def main():
    size = sys.argv[1] if len(sys.argv) > 1 else "large"
    model_name = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                             "nano": "AZURE_DEPLOYMENT_NANO"}[size]]
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    print(f"Claim B probe on masked tic-tac-toe, synth size={size}", flush=True)
    r_full = run("FULL rules", RULES_FULL, provider, model_name)
    r_wh = run("WITHHELD masking rule", RULES_WITHHELD, provider, model_name)
    print("\n=== SUMMARY ===", flush=True)
    for r in (r_full, r_wh):
        print(f"{r['label']:24s} transition_acc={r['transition_acc']:.3f} "
              f"observation_rate={r['observation_rate']:.3f} "
              f"inference_rate={r['inference_rate']:.3f}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
