"""Declarative recall probe — persist the literal question & answer behind the
paper's two recall claims, so they are auditable rather than asserted:

  1. army5x5a (arXiv:2510.04542, App. H.5): claimed NOT recalled ("no prior").
  2. Trike (Erickson, 2020): claimed name-recalled but mechanics confabulated
     ("wrong prior").
  3. Kuhn poker: positive control — a game the model certainly knows, showing
     the model does declare knowledge when it has it (so a "we don't know"
     answer on army5x5a is informative, not a generic hedge).

Each question asks the model to state the rules precisely OR to say explicitly
that it does not know them, and to label its answer RECALL vs GUESS. Full
responses are persisted verbatim to results/declarative_recall_probe.json;
the paper cites that file. Ground truths to compare against:
army5x5a movesets in src/cwm/groundtruth/gen_chess.py; Trike rules in
src/cwm/groundtruth/trike.py.

Run: PYTHONPATH=src python3.12 scripts/declarative_recall_probe.py [large|mini]
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.llm.azure_openai import AzureOpenAIProvider

SIZE = sys.argv[1] if len(sys.argv) > 1 else "large"
MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                    "nano": "AZURE_DEPLOYMENT_NANO"}[SIZE]]

SYSTEM = ("You are being probed for factual recall of specific game rules. "
          "Answer precisely. If you do not reliably know something, say "
          "'I do not know' explicitly instead of guessing. End your answer "
          "with exactly one of the labels: [RECALL] if you are reporting "
          "rules you actually know from training, or [GUESS] if any part of "
          "your description is invented or inferred.")

PROBES = [
    {
        "id": "army5x5a",
        "claim_in_paper": "no prior: the model does not know the detailed movesets",
        "question": (
            "The DeepMind paper 'Code World Models for General Game Playing' "
            "(arXiv:2510.04542) defines a two-player board game called "
            "'army5x5a' in its Appendix H.5. Do you know this specific game? "
            "If yes, state precisely: (a) the board size, (b) the piece types "
            "each player has and how many of each, (c) the exact movement "
            "offsets of every piece type, (d) the win condition, and (e) the "
            "starting position. If you do not know the game or any of these "
            "details, say so explicitly for each part rather than guessing."
        ),
    },
    {
        "id": "trike",
        "claim_in_paper": "wrong prior: the model knows the name but confabulates the mechanics",
        "question": (
            "Do you know the abstract combinatorial board game 'Trike', "
            "designed by Alek Erickson in 2020? If yes, state precisely: "
            "(a) the board shape and size, (b) what pieces exist and who owns "
            "them, (c) what a turn consists of, (d) how the game ends, and "
            "(e) how the winner is determined. If you do not reliably know "
            "any of these, say so explicitly for that part rather than "
            "guessing."
        ),
    },
    {
        "id": "kuhn_poker_control",
        "claim_in_paper": "positive control: a game the model certainly knows",
        "question": (
            "Do you know Kuhn poker? If yes, state precisely: (a) the deck, "
            "(b) the betting structure, (c) the payoffs, and (d) the number "
            "of information sets for the first player. If you do not know "
            "any of these, say so explicitly."
        ),
    },
]


def main():
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    out = {"model_size": SIZE, "deployment": MODEL, "date": date.today().isoformat(),
           "system_prompt": SYSTEM, "probes": []}
    for p in PROBES:
        print(f"=== {p['id']} ===", flush=True)
        comp = provider.complete(
            [{"role": "system", "content": SYSTEM},
             {"role": "user", "content": p["question"]}], MODEL)
        print(comp.text, flush=True)
        print("", flush=True)
        out["probes"].append({**p, "response": comp.text,
                              "usage": {"prompt_tokens": comp.usage.prompt_tokens,
                                        "completion_tokens": comp.usage.completion_tokens}})
    Path("results").mkdir(exist_ok=True)
    dest = Path("results/declarative_recall_probe.json")
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
