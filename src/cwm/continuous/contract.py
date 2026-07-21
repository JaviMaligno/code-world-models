"""Synthesis contract + pipeline for the continuous instrument (LLM arms).

The integrator is PINNED as part of the contract (design doc): the spec text
states the exact update equations and their order, so a correct synthesis
matches the truth to float precision and the gate can run at eps ~ 1e-9 —
effectively exact-match, sidestepping the tolerance axis. The instrument-
specific contract text (integrator, rules, mode probes) comes from an
InstrumentSpec (see instruments.py, selected by spec_for(env)), so this
pipeline is env-generic across the cart and pendulum instruments; spec
constants are generated from the truth env instance so they can never drift
from the ground truth.

Arms:
  full        — the mode clause (wall / stop) is in the spec (control:
                translation works)
  incomplete  — the mode clause is omitted (headline: passes the gate iff the
                sample missed the mode; the planner is then exploited)

The pipeline (synthesize -> refine on the SAME sample, which doubles as the
gate, as in paper 1's sweep) is pure-function so tests drive it offline with
FakeProvider; scripts/continuous_danger_synthesis.py is a thin wrapper.
"""
import json
import random
from dataclasses import dataclass

from ..sandbox import run_in_sandbox
from ..synthesizer import extract_code
from .instruments import spec_for


def build_contract(env, include_mode: bool, omit: tuple = ()) -> str:
    spec = spec_for(env)
    return spec.api_text + "\n" + spec.rules_text(env, include_mode, omit=omit)


def collect_transitions(env, n_rollouts: int, seed: int = 0) -> list[dict]:
    """N i.i.d. uniform-random rollouts on `env` (the truth). This sample is
    both the training data and the gate, as in the paper-1 sweep; `n_rollouts`
    is the danger-law N. Each transition records whether the wall fired, so
    the identifiability event (wall absent from the sample) is logged. Each
    transition also carries a stable `source_index` -- its 0-based position
    in THIS original order -- so downstream consumers (evidence_dose.py) can
    refer back to a transition after it has been reshuffled/subsampled into a
    smaller controlled set."""
    out = []
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s2, r, contact = env.step(s, a)
            out.append({"state": list(s), "action": a, "next_state": list(s2),
                        "reward": r, "contact": contact,
                        "source_index": len(out)})
            s = s2
    return out


def sample_contains_mode(transitions: list[dict]) -> bool:
    return any(t["contact"] for t in transitions)


sample_contains_wall = sample_contains_mode  # back-compat alias


def _example_lines(transitions: list[dict], max_examples: int) -> str:
    # Spread examples across the sample rather than taking a prefix (a prefix
    # would come from a single rollout). repr() keeps full float precision.
    n = len(transitions)
    idx = sorted({(i * n) // max_examples for i in range(min(max_examples, n))})
    return "\n".join(
        f"step({transitions[i]['state']!r}, {transitions[i]['action']!r}) "
        f"-> {transitions[i]['next_state']!r}   "
        f"reward(next) = {transitions[i]['reward']!r}"
        for i in idx)


def build_synthesis_messages(contract: str, transitions: list[dict],
                             max_examples: int = 30,
                             guidance: str = "") -> list[dict]:
    """`guidance` is the confound-closure knob (2026-07-19): extra
    methodological text inserted before the final instruction. Empty (the
    default) reproduces the original prompt byte-for-byte (tested), so all
    committed runs stay valid; non-empty is the "richer prompting" arm that
    paper 2 §10 leaves open."""
    system = ("You are an expert Python programmer. You write deterministic, "
              "pure code that exactly implements a specified physics world "
              "model. Output ONLY a single Python code block, no prose.")
    extra = f"{guidance}\n\n" if guidance else ""
    user = (f"{contract}\n\n"
            f"Here are observed transitions (ground truth) to match exactly:\n"
            f"{_example_lines(transitions, max_examples)}\n\n"
            f"{extra}"
            f"Write the Python module implementing the contract. "
            f"Output only one ```python code block.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def _run_contract_cases(code: str, transitions: list[dict], timeout: float = 30.0):
    """Sandbox-execute `step`/`reward` over every transition's (state, action)
    and return the raw per-case results aligned 1:1 with `transitions`, or
    (None, error_message) on any infra failure. Comparing the results against
    the expected values is left to the caller so both `contract_accuracy` and
    evidence_dose.py's source-indexed variant can independently derive
    pass/fail (and, for the latter, which transitions failed)."""
    cases = [{"s": t["state"], "a": t["action"]} for t in transitions]
    call = (
        "import json\n"
        f"_cases = json.loads({json.dumps(json.dumps(cases))})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    try:\n"
        "        _ns = step(list(_c['s']), _c['a'])\n"
        "        _r = reward(list(_ns))\n"
        "        _out.append({'ns': [float(v) for v in _ns], 'r': float(_r)})\n"
        "    except Exception as e:\n"
        "        _out.append({'error': repr(e)})\n"
        "print(json.dumps(_out))\n"
    )
    res = run_in_sandbox(code, call, timeout=timeout)
    if not res.ok:
        return None, res.stderr.strip()[-300:] or "execution failed"
    lines = res.stdout.strip().splitlines()
    if not lines:
        return None, "sandbox produced no output"
    try:
        produced = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None, f"bad JSON output: {lines[-1][:200]}"
    return produced, None


def _compare_transitions(transitions: list[dict], produced: list[dict],
                         eps: float) -> tuple[int, list[str], list[int]]:
    """Compare sandbox output to expected values. Returns (n_correct,
    failure_messages, failed_positions) where failed_positions are 0-based
    positions into `transitions` (parallel to failure_messages), for callers
    that need to identify which particular transitions failed."""
    correct, failures, failed_positions = 0, [], []
    for i, (t, got) in enumerate(zip(transitions, produced)):
        if "error" in got:
            failures.append(f"step({t['state']!r}, {t['action']!r}) raised {got['error']}")
            failed_positions.append(i)
            continue
        if len(got["ns"]) != len(t["next_state"]):
            failures.append(
                f"step({t['state']!r}, {t['action']!r}): wrong state arity: "
                f"expected {len(t['next_state'])} components, got "
                f"{len(got['ns'])}")
            failed_positions.append(i)
            continue
        err = max(max(abs(g - e) for g, e in zip(got["ns"], t["next_state"])),
                  abs(got["r"] - t["reward"]))
        if err <= eps:
            correct += 1
        else:
            failures.append(
                f"step({t['state']!r}, {t['action']!r}): expected "
                f"{t['next_state']!r} r={t['reward']!r}, got {got['ns']!r} "
                f"r={got['r']!r} (err {err:.3g})")
            failed_positions.append(i)
    return correct, failures, failed_positions


def contract_accuracy(code: str, transitions: list[dict], eps: float,
                      timeout: float = 30.0) -> tuple[float, list[str]]:
    """Fraction of transitions where the synthesized step() and reward()
    match within eps (sup-norm over x, v, reward), via the sandbox."""
    if not transitions:
        return 0.0, ["no transitions provided"]
    produced, err = _run_contract_cases(code, transitions, timeout=timeout)
    if produced is None:
        return 0.0, [err]
    correct, failures, _ = _compare_transitions(transitions, produced, eps)
    return correct / len(transitions), failures


@dataclass
class RefineResult:
    code: str
    accuracy: float
    iterations: int
    usages: list
    history: list | None = None   # [(code, accuracy)] when keep_history


def refine_continuous(provider, model: str, contract: str, code: str,
                      transitions: list[dict], eps: float,
                      max_iters: int = 5, guidance: str = "",
                      max_failures: int = 20,
                      keep_history: bool = False) -> RefineResult:
    """Refine until the sample matches at eps (mirrors cwm.refiner.refine_cwm:
    the SAME sample is re-checked each iteration — it is the gate).
    `guidance`/`max_failures` are the confound-closure knobs (2026-07-19);
    the defaults reproduce the original refine message byte-for-byte.
    `keep_history` (opt-in, default off) records (code, accuracy) for the
    initial synthesis and every refine iteration; off by default so existing
    outputs are unchanged."""
    usages = []
    acc, failures = contract_accuracy(code, transitions, eps)
    history = [(code, acc)] if keep_history else None
    iterations = 0
    while acc < 1.0 and iterations < max_iters:
        msg = (f"{contract}\n\nThe current implementation is below. It fails "
               f"some transitions. Fix it so every transition matches to "
               f"within {eps} in x, v and reward. Output only one ```python "
               f"code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
               f"FAILURES (expected vs got):\n"
               + "\n".join(failures[:max_failures])
               + (f"\n\n{guidance}" if guidance else ""))
        completion = provider.complete([{"role": "user", "content": msg}],
                                       model=model)
        usages.append(completion.usage)
        code = extract_code(completion.text)
        acc, failures = contract_accuracy(code, transitions, eps)
        if keep_history:
            history.append((code, acc))
        iterations += 1
    return RefineResult(code=code, accuracy=acc, iterations=iterations,
                        usages=usages, history=history)


class SynthesizedModel:
    """In-process adapter exposing the instrument step interface (cart or
    pendulum), so mpc.plan and harness.run_episode drive a synthesized model
    directly. Only run this on gate-accepted code (the gate executes in the
    sandbox first)."""

    def __init__(self, code: str, base_env):
        ns: dict = {}
        exec(code, ns)  # noqa: S102 — gate-accepted synthesized code
        self._step, self._reward = ns["step"], ns["reward"]
        self.a_max = base_env.a_max
        self.h_episode = base_env.h_episode

    def step(self, state, action):
        s2 = self._step(list(state), action)
        return tuple(s2), self._reward(list(s2)), False

    def initial_state(self, rng):  # pragma: no cover — parity with the env
        return (rng.uniform(-0.5, 0.5), 0.0)


def mode_blindness(code: str, env, eps: float = 1e-6):
    """Fraction of mode-region probe transitions the synthesized model gets
    WRONG per mode (1.0 = fully mode-blind, 0.0 = mode encoded correctly).
    Probes fire their mode in truth by construction. Returns a scalar when the
    instrument has exactly one mode (numerically identical to the original
    single-mode behavior; key stays `wall_blindness` in emitted JSON for
    backward compatibility there), else a dict keyed by mode name."""
    spec = spec_for(env)
    probes_by_mode = spec.mode_probes(env)
    model = SynthesizedModel(code, env)
    result = {}
    for name, probes in probes_by_mode.items():
        blind = 0
        for s, a in probes:
            st, rt, contact = env.step(s, a)
            assert contact, "probe must fire the mode in truth"
            sm, rm, _ = model.step(s, a)
            if len(st) != len(sm):
                err = float("inf")  # wrong arity counts as blind
            else:
                err = max(max(abs(a_ - b_) for a_, b_ in zip(st, sm)),
                          abs(rt - rm))
            if err > eps:
                blind += 1
        result[name] = blind / len(probes)
    if len(result) == 1:
        return next(iter(result.values()))
    return result


wall_blindness = mode_blindness  # back-compat alias


def synthesize_and_evaluate(provider, model_name, env,
                            include_mode: bool, n_rollouts: int, seed: int,
                            eps: float = 1e-9, max_iters: int = 5,
                            max_examples: int = 30, omit: tuple = (),
                            guidance: str = "",
                            max_failures: int = 20,
                            keep_history: bool = False) -> dict:
    """One cell of the synthesis experiment: collect the sample, synthesize,
    refine on the sample (the gate), then classify the artifact. Returns a
    JSON-ready dict; play evaluation is done by the caller (it needs the
    truth-planner baseline shared across seeds). Single-mode instruments
    (cart, pendulum) emit exactly the original schema; multi-mode instruments
    (patch2d) additionally emit "mode_blindness" (dict) and
    "sample_contains_mode_per" (dict), while "wall_blindness" becomes the mean
    of the mode_blindness dict (or None when the gate failed)."""
    transitions = collect_transitions(env, n_rollouts, seed=seed)
    if callable(guidance):
        # per-seed dynamic guidance (paper 3 TDA arm): the guidance text is
        # computed FROM this seed's own sample (e.g. a topological summary of
        # its contact evidence), so it must be resolved after collection.
        guidance = guidance(env, transitions)
    contract = build_contract(env, include_mode, omit=omit)
    msgs = build_synthesis_messages(contract, transitions, max_examples,
                                    guidance=guidance)
    completion = provider.complete(msgs, model=model_name)
    code = extract_code(completion.text)
    refined = refine_continuous(provider, model_name, contract, code,
                                transitions, eps, max_iters=max_iters,
                                guidance=guidance, max_failures=max_failures,
                                keep_history=keep_history)
    spec = spec_for(env)
    mb = mode_blindness(refined.code, env) if refined.accuracy == 1.0 else None
    cell = {
        "arm": "full" if include_mode else "incomplete",
        "seed": seed,
        "n_rollouts": n_rollouts,
        "eps": eps,
        "sample_contains_wall": sample_contains_mode(transitions),
        "gate_accuracy": refined.accuracy,
        "gate_passed": refined.accuracy == 1.0,
        "refine_iterations": refined.iterations,
        "wall_blindness": (mb if not isinstance(mb, dict)
                          else (sum(mb.values()) / len(mb) if mb else None)),
        "code": refined.code,
    }
    if keep_history:
        cell["history"] = [{"code": c, "gate_accuracy": a}
                           for c, a in refined.history]
    if spec.sample_modes is not None:
        cell["mode_blindness"] = mb
        cell["sample_contains_mode_per"] = spec.sample_modes(env, transitions)
    if guidance:
        cell["guidance_text"] = guidance   # audit trail for dynamic guidance
    return cell
