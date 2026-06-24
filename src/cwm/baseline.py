"""LLM-as-policy baseline agent."""
import re

_SYSTEM = ("You play tic-tac-toe. Board is a list of 9 cells (0 empty, 1=X, "
           "2=O), indices 0..8 row-major. Reply with ONLY the index you play.")

def build_policy_messages(state: dict, legal: list[int]) -> list[dict]:
    user = (f"Board: {state['board']}\nYou are player {state['current_player']}.\n"
            f"Legal moves: {legal}\nReply with one index from the legal moves.")
    return [{"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user}]

def parse_action(text: str):
    m = re.search(r"\d", text)
    return int(m.group()) if m else None

def baseline_policy(provider, model, state: dict, legal: list[int]):
    completion = provider.complete(build_policy_messages(state, legal), model=model)
    action = parse_action(completion.text)
    if action not in legal:
        return None, completion.usage   # illegal/unparseable -> arena handles it
    return action, completion.usage
