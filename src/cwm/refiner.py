"""Measure contract accuracy of synthesized code and refine it to 1.0."""
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
    n_samples: int = 0   # total DISTINCT trajectories seen (synth + any resamples)

def contract_accuracy(code: str, trajectories: list, timeout: float = 5.0):
    if not trajectories:
        return 0.0, ["no trajectories provided"]
    # Batch program: for each (state, action) compute all four contract properties.
    cases = [{"state": t.state, "action": t.action} for t in trajectories]
    call = (
        "import json\n"
        f"_cases = json.loads({json.dumps(json.dumps(cases))})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    _r = {}\n"
        "    try:\n"
        "        _ns = apply_action(_c['state'], _c['action'])\n"
        "        _r['next_state'] = _ns\n"
        "    except Exception as e:\n"
        "        _r['next_state'] = {'__error__': repr(e)}\n"
        "        _ns = None\n"
        "    try:\n"
        "        _r['legal'] = legal_actions(_c['state'])\n"
        "    except Exception as e:\n"
        "        _r['legal'] = {'__error__': repr(e)}\n"
        "    if _ns is not None:\n"
        "        try:\n"
        "            _r['terminal'] = is_terminal(_ns)\n"
        "        except Exception as e:\n"
        "            _r['terminal'] = {'__error__': repr(e)}\n"
        "        try:\n"
        "            _r['reward'] = returns(_ns)\n"
        "        except Exception as e:\n"
        "            _r['reward'] = {'__error__': repr(e)}\n"
        "    else:\n"
        "        _r['terminal'] = {'__error__': 'next_state failed'}\n"
        "        _r['reward'] = {'__error__': 'next_state failed'}\n"
        "    _out.append(_r)\n"
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
        # Normalize reward keys: JSON round-trip turns int keys to str; trajectory has int keys.
        expected_reward = {str(k): v for k, v in t.reward.items()}
        mismatches = []
        if got.get("next_state") != t.next_state:
            mismatches.append("next_state")
        if got.get("legal") != t.legal_actions:
            mismatches.append("legal_actions")
        if got.get("terminal") != t.terminal:
            mismatches.append("is_terminal")
        if got.get("reward") != expected_reward:
            mismatches.append("returns")
        if mismatches:
            # Show expected AND got for each mismatched field, and only for
            # those fields — maximal signal per character. (An earlier version
            # cut the whole line at 200 chars with no expected= at all, so the
            # feedback header said "expected vs got" while the body carried
            # neither: a model cannot learn an omitted rule from feedback that
            # only names the failing states.)
            exp = {"next_state": t.next_state, "legal_actions": t.legal_actions,
                   "is_terminal": t.terminal, "returns": expected_reward}
            got_key = {"next_state": "next_state", "legal_actions": "legal",
                       "is_terminal": "terminal", "returns": "reward"}
            detail = "; ".join(
                f"{m}: expected={exp[m]} got={got.get(got_key[m])}"
                for m in mismatches)
            msg = (f"state={t.state} action={t.action} {detail}")[:800]
            failures.append(msg)
        else:
            correct += 1
    return correct / len(trajectories), failures

def refine_cwm(provider, model, contract, code, trajectories, max_iters=5,
               resample_fn=None):
    """Refine `code` until it matches the contract on the trajectories.

    By default the SAME `trajectories` are re-checked each iteration (the original
    behavior). If `resample_fn` is given, it is called as `resample_fn(iteration)`
    to draw a FRESH, independent trajectory set before each accuracy check — a
    genuine validation loop in which refinement sees new random play-throughs, so
    the total number of distinct samples (and the chance a rare rule is observed)
    grows with the iteration count rather than overfitting one fixed set.
    `n_samples` reports the total distinct trajectories seen across synthesis +
    refinement.
    """
    usages = []
    n_samples = len(trajectories)
    acc, failures = contract_accuracy(code, trajectories)
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
        if resample_fn is not None:
            trajectories = resample_fn(iterations)
            n_samples += len(trajectories)
        acc, failures = contract_accuracy(code, trajectories)
    return RefineResult(code=code, accuracy=acc, iterations=iterations,
                        usages=usages, n_samples=n_samples)
