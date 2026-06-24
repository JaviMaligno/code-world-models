"""Measure transition accuracy of synthesized code and refine it to 1.0."""
import json
from dataclasses import dataclass
from .sandbox import run_in_sandbox
from .synthesizer import extract_code

@dataclass
class RefineResult:
    code: str
    accuracy: float
    iterations: int
    usages: list

def transition_accuracy(code: str, trajectories: list, timeout: float = 5.0):
    if not trajectories:
        return 0.0, ["no trajectories provided"]
    # Build one batch program: apply each action, print the resulting states as JSON.
    cases = [{"state": t.state, "action": t.action} for t in trajectories]
    call = (
        "import json\n"
        f"_cases = json.loads({json.dumps(json.dumps(cases))})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    try:\n"
        "        _out.append(apply_action(_c['state'], _c['action']))\n"
        "    except Exception as e:\n"
        "        _out.append({'__error__': repr(e)})\n"
        "print(json.dumps(_out))\n"
    )
    res = run_in_sandbox(code, call, timeout=timeout)
    if not res.ok:
        return 0.0, [res.stderr.strip()[-300:] or "execution failed"]
    lines = res.stdout.strip().splitlines()
    if not lines:
        return 0.0, ["sandbox produced no output"]
    try:
        produced = json.loads(lines[-1])
    except json.JSONDecodeError:
        return 0.0, [f"bad JSON output: {lines[-1][:200]}"]
    failures = []
    correct = 0
    for t, got in zip(trajectories, produced):
        if got == t.next_state:
            correct += 1
        else:
            failures.append((f"state={t.state} action={t.action} "
                             f"expected={t.next_state} got={got}")[:200])
    return correct / len(trajectories), failures

def refine_cwm(provider, model, contract, code, trajectories, max_iters=5):
    usages = []
    acc, failures = transition_accuracy(code, trajectories)
    iterations = 0
    while acc < 1.0 and iterations < max_iters:
        msg = (
            f"{contract}\n\nThe current implementation is below. It fails some "
            f"transitions. Fix it so every transition matches. Output only one "
            f"```python code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
            f"FAILURES (expected vs got):\n" + "\n".join(failures[:20])
        )
        completion = provider.complete(
            [{"role": "user", "content": msg}], model=model)
        usages.append(completion.usage)
        code = extract_code(completion.text)
        iterations += 1
        acc, failures = transition_accuracy(code, trajectories)
    return RefineResult(code=code, accuracy=acc, iterations=iterations, usages=usages)
