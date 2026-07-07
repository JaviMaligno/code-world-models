"""Synthesis contract + pipeline for the continuous instrument (LLM arms).

The integrator is PINNED as part of the contract (design doc): the spec text
states the exact update equations and their order, so a correct synthesis
matches the truth to float precision and the gate can run at eps ~ 1e-9 —
effectively exact-match, sidestepping the tolerance axis. The rules text is
generated from the CartWall instance so spec constants can never drift from
the ground truth.

Arms:
  full        — the wall clause is in the spec (control: translation works)
  incomplete  — the wall clause is omitted (headline: passes the gate iff the
                sample missed the wall; the planner is then exploited)

The pipeline (synthesize -> refine on the SAME sample, which doubles as the
gate, as in paper 1's sweep) is pure-function so tests drive it offline with
FakeProvider; scripts/continuous_danger_synthesis.py is a thin wrapper.
"""
import json
import random
from dataclasses import dataclass

from ..sandbox import run_in_sandbox
from ..synthesizer import extract_code
from .envs import CartWall

CONTINUOUS_CONTRACT_API = """\
Implement a deterministic 1D control world model as Python module-level
functions (pure, no I/O, no globals, only the `math` standard-library module).

State is a list [x, v] of two floats (position, velocity). Action is a float.

Functions to implement EXACTLY these signatures:
  def step(state: list, action: float) -> list   # next [x, v]
  def reward(state: list) -> float               # reward of a state

The integrator is FIXED and part of the contract. step() must compute, in
exactly this order, with plain Python floats:
  1. a = min(a_max, max(-a_max, action))         # clamp the action
  2. v2 = v + (gain * a - drag * v) * dt
  3. x2 = x + v2 * dt
then apply any additional dynamics rules given below, and return [x2, v2].
"""


def rules_text(env: CartWall, include_wall: bool) -> str:
    lines = [
        "Physical constants:",
        f"  dt = {env.dt}",
        f"  gain = {env.gain}",
        f"  drag = {env.drag}",
        f"  a_max = {env.a_max}",
        "",
        "Reward (a function of the state [x, v] alone):",
        f"  left  = {env.a_left} / (1.0 + math.exp(-(({env.x_left} - x) / {env.width})))",
        f"  right = {env.a_right} / (1.0 + math.exp(-((x - {env.x_right}) / {env.width})))",
        "  reward = left + right",
    ]
    if include_wall:
        if env.x_wall is None:
            raise ValueError("env has no wall; cannot write the wall clause")
        lines += [
            "",
            "Additional dynamics rule:",
            f"  There is an immovable wall at x = {env.x_wall}. After computing",
            f"  x2 and v2 as above, if x2 >= {env.x_wall}, the cart stops at the",
            f"  wall inelastically: the next state is exactly [{env.x_wall}, 0.0].",
        ]
    return "\n".join(lines)


def build_contract(env: CartWall, include_wall: bool) -> str:
    return CONTINUOUS_CONTRACT_API + "\n" + rules_text(env, include_wall)


def collect_transitions(env: CartWall, n_rollouts: int, seed: int = 0) -> list[dict]:
    """N i.i.d. uniform-random rollouts on `env` (the truth). This sample is
    both the training data and the gate, as in the paper-1 sweep; `n_rollouts`
    is the danger-law N. Each transition records whether the wall fired, so
    the identifiability event (wall absent from the sample) is logged."""
    out = []
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            s2, r, contact = env.step(s, a)
            out.append({"state": list(s), "action": a, "next_state": list(s2),
                        "reward": r, "contact": contact})
            s = s2
    return out


def sample_contains_wall(transitions: list[dict]) -> bool:
    return any(t["contact"] for t in transitions)


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
                             max_examples: int = 30) -> list[dict]:
    system = ("You are an expert Python programmer. You write deterministic, "
              "pure code that exactly implements a specified physics world "
              "model. Output ONLY a single Python code block, no prose.")
    user = (f"{contract}\n\n"
            f"Here are observed transitions (ground truth) to match exactly:\n"
            f"{_example_lines(transitions, max_examples)}\n\n"
            f"Write the Python module implementing the contract. "
            f"Output only one ```python code block.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def contract_accuracy(code: str, transitions: list[dict], eps: float,
                      timeout: float = 30.0) -> tuple[float, list[str]]:
    """Fraction of transitions where the synthesized step() and reward()
    match within eps (sup-norm over x, v, reward), via the sandbox."""
    if not transitions:
        return 0.0, ["no transitions provided"]
    cases = [{"s": t["state"], "a": t["action"]} for t in transitions]
    call = (
        "import json\n"
        f"_cases = json.loads({json.dumps(json.dumps(cases))})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    try:\n"
        "        _ns = step(list(_c['s']), _c['a'])\n"
        "        _r = reward(list(_ns))\n"
        "        _out.append({'ns': [float(_ns[0]), float(_ns[1])], 'r': float(_r)})\n"
        "    except Exception as e:\n"
        "        _out.append({'error': repr(e)})\n"
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
    correct, failures = 0, []
    for t, got in zip(transitions, produced):
        if "error" in got:
            failures.append(f"step({t['state']!r}, {t['action']!r}) raised {got['error']}")
            continue
        err = max(abs(got["ns"][0] - t["next_state"][0]),
                  abs(got["ns"][1] - t["next_state"][1]),
                  abs(got["r"] - t["reward"]))
        if err <= eps:
            correct += 1
        else:
            failures.append(
                f"step({t['state']!r}, {t['action']!r}): expected "
                f"{t['next_state']!r} r={t['reward']!r}, got {got['ns']!r} "
                f"r={got['r']!r} (err {err:.3g})")
    return correct / len(transitions), failures


@dataclass
class RefineResult:
    code: str
    accuracy: float
    iterations: int
    usages: list


def refine_continuous(provider, model: str, contract: str, code: str,
                      transitions: list[dict], eps: float,
                      max_iters: int = 5) -> RefineResult:
    """Refine until the sample matches at eps (mirrors cwm.refiner.refine_cwm:
    the SAME sample is re-checked each iteration — it is the gate)."""
    usages = []
    acc, failures = contract_accuracy(code, transitions, eps)
    iterations = 0
    while acc < 1.0 and iterations < max_iters:
        msg = (f"{contract}\n\nThe current implementation is below. It fails "
               f"some transitions. Fix it so every transition matches to "
               f"within {eps} in x, v and reward. Output only one ```python "
               f"code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
               f"FAILURES (expected vs got):\n" + "\n".join(failures[:20]))
        completion = provider.complete([{"role": "user", "content": msg}],
                                       model=model)
        usages.append(completion.usage)
        code = extract_code(completion.text)
        acc, failures = contract_accuracy(code, transitions, eps)
        iterations += 1
    return RefineResult(code=code, accuracy=acc, iterations=iterations,
                        usages=usages)


class SynthesizedModel:
    """In-process adapter exposing the CartWall step interface, so mpc.plan
    and harness.run_episode drive a synthesized model directly. Only run this
    on gate-accepted code (the gate executes in the sandbox first)."""

    def __init__(self, code: str, base_env: CartWall):
        ns: dict = {}
        exec(code, ns)  # noqa: S102 — gate-accepted synthesized code
        self._step, self._reward = ns["step"], ns["reward"]
        self.a_max = base_env.a_max
        self.h_episode = base_env.h_episode

    def step(self, state, action):
        s2 = self._step(list(state), action)
        return (s2[0], s2[1]), self._reward(list(s2)), False

    def initial_state(self, rng):  # pragma: no cover — parity with CartWall
        return (rng.uniform(-0.5, 0.5), 0.0)


def wall_blindness(code: str, env: CartWall, eps: float = 1e-6) -> float:
    """Fraction of wall-region probe transitions the synthesized model gets
    WRONG (1.0 = fully wall-blind, 0.0 = wall encoded correctly). Probes are
    states just below the wall moving right under full thrust — every one
    fires the clamp in truth."""
    if env.x_wall is None:
        raise ValueError("truth env must have a wall")
    probes = [((env.x_wall - 0.1, v), env.a_max) for v in (1.0, 2.0, 4.0)]
    model = SynthesizedModel(code, env)
    blind = 0
    for s, a in probes:
        st, rt, contact = env.step(s, a)
        assert contact, "probe must fire the wall in truth"
        sm, rm, _ = model.step(s, a)
        err = max(abs(st[0] - sm[0]), abs(st[1] - sm[1]), abs(rt - rm))
        if err > eps:
            blind += 1
    return blind / len(probes)


def synthesize_and_evaluate(provider, model_name: str, env: CartWall,
                            include_wall: bool, n_rollouts: int, seed: int,
                            eps: float = 1e-9, max_iters: int = 5,
                            max_examples: int = 30) -> dict:
    """One cell of the synthesis experiment: collect the sample, synthesize,
    refine on the sample (the gate), then classify the artifact. Returns a
    JSON-ready dict; play evaluation is done by the caller (it needs the
    truth-planner baseline shared across seeds)."""
    transitions = collect_transitions(env, n_rollouts, seed=seed)
    contract = build_contract(env, include_wall)
    msgs = build_synthesis_messages(contract, transitions, max_examples)
    completion = provider.complete(msgs, model=model_name)
    code = extract_code(completion.text)
    refined = refine_continuous(provider, model_name, contract, code,
                                transitions, eps, max_iters=max_iters)
    return {
        "arm": "full" if include_wall else "incomplete",
        "seed": seed,
        "n_rollouts": n_rollouts,
        "eps": eps,
        "sample_contains_wall": sample_contains_wall(transitions),
        "gate_accuracy": refined.accuracy,
        "gate_passed": refined.accuracy == 1.0,
        "refine_iterations": refined.iterations,
        "wall_blindness": wall_blindness(refined.code, env)
        if refined.accuracy == 1.0 else None,
        "code": refined.code,
    }
