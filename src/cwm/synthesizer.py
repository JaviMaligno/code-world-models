# src/cwm/synthesizer.py
"""Synthesize a Code World Model from the contract + trajectories."""
import re

_SYSTEM = (
    "You are an expert Python programmer. You write deterministic, pure code "
    "that exactly implements a specified game world model. Output ONLY a single "
    "Python code block, no prose."
)

def _example_line(t) -> str:
    return (f"state={t.state} action={t.action} -> next_state={t.next_state} "
            f"terminal={t.terminal} returns={t.reward}")

def build_synthesis_messages(contract: str, trajectories: list,
                             max_examples: int = 30) -> list[dict]:
    examples = "\n".join(_example_line(t) for t in trajectories[:max_examples])
    user = (
        f"{contract}\n\n"
        f"Here are observed transitions (ground truth) to match exactly:\n"
        f"{examples}\n\n"
        f"Write the Python module implementing the contract. "
        f"Output only one ```python code block."
    )
    return [{"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user}]

def extract_code(text: str) -> str:
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).rstrip("\n")
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).rstrip("\n")
    return text.strip()

def synthesize_cwm(provider, model: str, contract: str, trajectories: list):
    msgs = build_synthesis_messages(contract, trajectories)
    completion = provider.complete(msgs, model=model)
    return extract_code(completion.text), completion.usage
