"""LLM-as-policy baseline agent (game-agnostic)."""
import re
from cwm.llm.provider import Usage

def build_policy_messages(state: dict, legal: list[int], policy_description: str) -> list[dict]:
    system = policy_description + " Reply with ONLY the integer of your chosen legal move."
    user = (f"Board: {state['board']}\nYou are player {state['current_player']}.\n"
            f"Legal moves: {legal}\nReply with one integer from the legal moves.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]

def parse_action(text: str) -> int | None:
    m = re.search(r"\d+", text)   # multi-digit: works for tic-tac-toe (0..8) and Connect Four (0..6) and beyond
    return int(m.group()) if m else None

def baseline_policy(provider, model, state: dict, legal: list[int],
                    policy_description: str) -> tuple[int | None, "Usage"]:
    completion = provider.complete(build_policy_messages(state, legal, policy_description), model=model)
    action = parse_action(completion.text)
    if action not in legal:
        return None, completion.usage
    return action, completion.usage
