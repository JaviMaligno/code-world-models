# Pendulum Synthesis Arm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the paper-2 LLM synthesis arm on the second instrument (pendulum-with-stop) by making the contract machinery env-agnostic, then produce the credentialed results and fold them into the paper.

**Architecture:** Introduce an `InstrumentSpec` abstraction (`src/cwm/continuous/instruments.py`) that owns the only instrument-specific parts of the synthesis contract — the integrator API text, the rules text (constants + reward + mode rule), and the mode-region probes. `contract.py` becomes generic and dispatches via `spec_for(env)` (same pattern as `blind_of` in `envs.py`). The cart's contract prompt stays byte-identical (golden test), so the committed §6 results remain valid. The pendulum is then run through the identical pipeline.

**Tech Stack:** Python 3.12, pytest, the repo's `.venv` (`/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python`), `PYTHONPATH=src`. LLM providers: `AzureOpenAIProvider` (Azure GPT-5.x) and `OpenAICompatProvider` (HF router). Offline tests use `FakeProvider`.

## Global Constraints

- Work entirely in the worktree `/private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2` on branch `claude/continuous-setting-feasibility-wktp6b`. Do NOT touch the main checkout (`main`/paper 1).
- Run Python via `.venv/bin/python` with `PYTHONPATH=src` (the worktree has no `.venv`; use the main repo's).
- Credentials live in the worktree's `.env` (Azure vars + `HF_TOKEN`); already present.
- The cart's contract prompt MUST stay byte-identical after the refactor (golden test). Emitted JSON keys `wall_blindness` and `sample_contains_wall` MUST stay stable (backward-compat with `make_paper2_figures.py` and committed cart JSONs).
- Pinned-integrator params for all runs: ε=1e-9, N=40 rollouts, 6 MPC play-episodes/seed, max 5 refine iters.
- Commit after each task. End commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- `main.tex` must recompile with 0 overfull hbox >2pt and 0 undefined refs/cites; use the committed `main.bbl` (do NOT re-run bibtex — no citation changes).

---

### Task 1: `InstrumentSpec` abstraction + cart/pendulum specs (paridad byte-idéntica del cart)

**Files:**
- Create: `src/cwm/continuous/instruments.py`
- Create: `tests/fixtures/cart_contract_full.txt` (captured from current code)
- Create: `tests/fixtures/cart_contract_incomplete.txt` (captured from current code)
- Create: `tests/test_instruments.py`

**Interfaces:**
- Consumes: `CartWall`, `PendulumStop` from `cwm.continuous.envs`; the current `CONTINUOUS_CONTRACT_API` and `rules_text` from `cwm.continuous.contract` (copied verbatim for the cart).
- Produces:
  - `InstrumentSpec` dataclass (frozen) with fields:
    - `api_text: str`
    - `rules_text: Callable[[object, bool], str]` — `(env, include_mode) -> str`
    - `mode_probes: Callable[[object], list]` — `(env) -> list[tuple[tuple[float, float], float]]` (each `(state, action)` fires the mode in truth)
    - `mode_attr: str` — `"x_wall"` | `"th_stop"`
  - `CART_SPEC: InstrumentSpec`, `PENDULUM_SPEC: InstrumentSpec`
  - `spec_for(env) -> InstrumentSpec` — dispatch by `isinstance` (`PendulumStop` → `PENDULUM_SPEC`, else `CART_SPEC`)

- [ ] **Step 1: Capture the current cart prompt as golden fixtures**

Run (from the worktree root):
```bash
mkdir -p tests/fixtures
PYTHONPATH=src .venv/bin/python -c "
from cwm.continuous.envs import CartWall
from cwm.continuous.contract import build_contract
e = CartWall(x_wall=8.0)
open('tests/fixtures/cart_contract_full.txt','w').write(build_contract(e, include_wall=True))
open('tests/fixtures/cart_contract_incomplete.txt','w').write(build_contract(e, include_wall=False))
"
```
Expected: two files created. Sanity check (must match the captured baseline):
```bash
shasum -a 256 tests/fixtures/cart_contract_full.txt tests/fixtures/cart_contract_incomplete.txt
```
Expected: full begins `03feb7919265aa59...` (len 1192), incomplete begins `f506394c078d45d9...` (len 990).

- [ ] **Step 2: Write the failing test**

Create `tests/test_instruments.py`:
```python
"""InstrumentSpec: the env-specific parts of the synthesis contract. The cart
spec must reproduce the pre-refactor prompt byte-for-byte (golden fixtures) so
the committed §6 cart results stay reproducible."""
import pathlib

from cwm.continuous.envs import CartWall, PendulumStop
from cwm.continuous.instruments import CART_SPEC, PENDULUM_SPEC, spec_for

FIX = pathlib.Path(__file__).parent / "fixtures"


def _contract(spec, env, include_mode):
    return spec.api_text + "\n" + spec.rules_text(env, include_mode)


def test_cart_spec_is_byte_identical_to_golden():
    env = CartWall(x_wall=8.0)
    assert _contract(CART_SPEC, env, True) == (FIX / "cart_contract_full.txt").read_text()
    assert _contract(CART_SPEC, env, False) == (FIX / "cart_contract_incomplete.txt").read_text()


def test_spec_for_dispatches_by_type():
    assert spec_for(CartWall(x_wall=8.0)) is CART_SPEC
    assert spec_for(PendulumStop(th_stop=1.4)) is PENDULUM_SPEC


def test_pendulum_rules_text_has_gravity_and_stop():
    env = PendulumStop(th_stop=1.4)
    full = _contract(PENDULUM_SPEC, env, True)
    assert "grav = 2.0" in full
    assert "math.sin(th)" in full
    assert "th_stop" in full or "1.4" in full
    incomplete = _contract(PENDULUM_SPEC, env, False)
    assert "1.4" not in incomplete.split("Reward")[0] or "stop" not in incomplete.lower()


def test_pendulum_mode_probes_fire_the_stop_in_truth():
    env = PendulumStop(th_stop=1.4)
    probes = PENDULUM_SPEC.mode_probes(env)
    assert probes
    for state, action in probes:
        _s2, _r, contact = env.step(state, action)
        assert contact, f"probe {state},{action} must fire the stop in truth"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_instruments.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cwm.continuous.instruments'`.

- [ ] **Step 4: Implement `src/cwm/continuous/instruments.py`**

```python
"""Instrument-specific pieces of the synthesis contract (paper 2 LLM arms).

The contract machinery in `contract.py` is otherwise env-generic; this module
holds the ONLY parts that differ per instrument — the integrator API text, the
rules text (constants + reward + mode rule), and the mode-region probes — behind
an `InstrumentSpec` selected by `spec_for(env)`. The cart spec reproduces the
pre-refactor prompt byte-for-byte (golden test) so committed results stay valid.
"""
from dataclasses import dataclass
from typing import Callable

from .envs import CartWall, PendulumStop

# --- cart (linear plant) -----------------------------------------------------
CART_API_TEXT = """\
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


def _cart_rules_text(env: CartWall, include_mode: bool) -> str:
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
    if include_mode:
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


def _cart_mode_probes(env: CartWall):
    # states just below the wall moving right under full thrust — each fires
    # the clamp in truth.
    return [((env.x_wall - 0.1, v), env.a_max) for v in (1.0, 2.0, 4.0)]


# --- pendulum (nonlinear plant) ----------------------------------------------
PENDULUM_API_TEXT = """\
Implement a deterministic 1D control world model as Python module-level
functions (pure, no I/O, no globals, only the `math` standard-library module).

State is a list [th, om] of two floats (angle, angular velocity). Action is a
float.

Functions to implement EXACTLY these signatures:
  def step(state: list, action: float) -> list   # next [th, om]
  def reward(state: list) -> float               # reward of a state

The integrator is FIXED and part of the contract. step() must compute, in
exactly this order, with plain Python floats:
  1. a = min(a_max, max(-a_max, action))                  # clamp the action
  2. om2 = om + (gain * a - grav * math.sin(th) - drag * om) * dt
  3. th2 = th + om2 * dt
then apply any additional dynamics rules given below, and return [th2, om2].
"""


def _pendulum_rules_text(env: PendulumStop, include_mode: bool) -> str:
    lines = [
        "Physical constants:",
        f"  dt = {env.dt}",
        f"  gain = {env.gain}",
        f"  grav = {env.grav}",
        f"  drag = {env.drag}",
        f"  a_max = {env.a_max}",
        "",
        "Reward (a function of the state [th, om] alone):",
        f"  left  = {env.a_left} / (1.0 + math.exp(-(({env.th_left} - th) / {env.width})))",
        f"  right = {env.a_right} / (1.0 + math.exp(-((th - {env.th_right}) / {env.width})))",
        "  reward = left + right",
    ]
    if include_mode:
        if env.th_stop is None:
            raise ValueError("env has no stop; cannot write the stop clause")
        lines += [
            "",
            "Additional dynamics rule:",
            f"  There is an immovable angular stop at th = {env.th_stop}. After",
            f"  computing th2 and om2 as above, if th2 >= {env.th_stop}, the",
            f"  pendulum stops inelastically: the next state is exactly "
            f"[{env.th_stop}, 0.0].",
        ]
    return "\n".join(lines)


def _pendulum_mode_probes(env: PendulumStop):
    # states just below the stop swinging up under full torque — each fires the
    # stop in truth.
    return [((env.th_stop - 0.1, om), env.a_max) for om in (1.0, 2.0, 4.0)]


@dataclass(frozen=True)
class InstrumentSpec:
    api_text: str
    rules_text: Callable[[object, bool], str]
    mode_probes: Callable[[object], list]
    mode_attr: str


CART_SPEC = InstrumentSpec(
    api_text=CART_API_TEXT, rules_text=_cart_rules_text,
    mode_probes=_cart_mode_probes, mode_attr="x_wall")
PENDULUM_SPEC = InstrumentSpec(
    api_text=PENDULUM_API_TEXT, rules_text=_pendulum_rules_text,
    mode_probes=_pendulum_mode_probes, mode_attr="th_stop")


def spec_for(env) -> InstrumentSpec:
    if isinstance(env, PendulumStop):
        return PENDULUM_SPEC
    return CART_SPEC
```

Note: `CART_API_TEXT` must equal the current `CONTINUOUS_CONTRACT_API` string in `contract.py` character-for-character (the golden test enforces the full-prompt equality, and `build_contract` currently joins `API + "\n" + rules`). `_cart_rules_text` is the current `rules_text` verbatim.

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_instruments.py -v`
Expected: 4 passed. If `test_cart_spec_is_byte_identical_to_golden` fails, `CART_API_TEXT` differs from the original `CONTINUOUS_CONTRACT_API` — diff and fix whitespace/trailing newline until identical.

- [ ] **Step 6: Commit**

```bash
git add src/cwm/continuous/instruments.py tests/test_instruments.py tests/fixtures/cart_contract_full.txt tests/fixtures/cart_contract_incomplete.txt
git commit -m "feat: InstrumentSpec abstraction for cart+pendulum synthesis contracts

Env-specific contract pieces (API text, rules text, mode probes) behind
spec_for(env). Cart spec is byte-identical to the pre-refactor prompt (golden
fixtures). Pendulum spec adds the gravity term and angular-stop rule.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Make `contract.py` env-generic (consume `spec_for`)

**Files:**
- Modify: `src/cwm/continuous/contract.py`
- Test: `tests/test_continuous_contract.py` (existing cart tests must stay green), `tests/test_instruments.py`

**Interfaces:**
- Consumes: `spec_for`, `InstrumentSpec` from `cwm.continuous.instruments`.
- Produces (signatures other tasks rely on):
  - `build_contract(env, include_mode: bool) -> str` (param renamed `include_wall` → `include_mode`; behavior identical for the cart)
  - `mode_blindness(code: str, env, eps: float = 1e-6) -> float` (was `wall_blindness`)
  - `sample_contains_mode(transitions: list[dict]) -> bool` (was `sample_contains_wall`)
  - `synthesize_and_evaluate(provider, model_name, env, include_mode: bool, n_rollouts, seed, eps=1e-9, max_iters=5, max_examples=30) -> dict` — dict still contains keys `"sample_contains_wall"` and `"wall_blindness"` (stable), plus `"arm"`, `"seed"`, `"gate_accuracy"`, `"gate_passed"`, `"refine_iterations"`, `"code"`.
  - Back-compat aliases kept so existing imports/tests do not break: `wall_blindness = mode_blindness`, `sample_contains_wall = sample_contains_mode`.

- [ ] **Step 1: Add a golden regression test for `build_contract` (cart)**

Add to `tests/test_continuous_contract.py`:
```python
import pathlib as _pathlib
_FIX = _pathlib.Path(__file__).parent / "fixtures"


def test_build_contract_cart_matches_golden():
    from cwm.continuous.contract import build_contract
    env = CartWall(x_wall=8.0)
    assert build_contract(env, include_mode=True) == (_FIX / "cart_contract_full.txt").read_text()
    assert build_contract(env, include_mode=False) == (_FIX / "cart_contract_incomplete.txt").read_text()
```

- [ ] **Step 2: Run it to confirm the current signature fails**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_continuous_contract.py::test_build_contract_cart_matches_golden -v`
Expected: FAIL — `build_contract()` currently takes `include_wall`, so `include_mode=` raises `TypeError`.

- [ ] **Step 3: Refactor `contract.py` to consume the spec**

In `src/cwm/continuous/contract.py`:

1. Replace the import and drop the inlined API/rules:
```python
from .instruments import spec_for
```
Remove the `CONTINUOUS_CONTRACT_API` constant and the `rules_text` function (now in `instruments.py`). Keep the `from .envs import CartWall` import only if still referenced by type hints; otherwise remove it.

2. Rewrite `build_contract`:
```python
def build_contract(env, include_mode: bool) -> str:
    spec = spec_for(env)
    return spec.api_text + "\n" + spec.rules_text(env, include_mode)
```

3. Rename `sample_contains_wall` → `sample_contains_mode` (body unchanged — it reads the `contact` flag), and add an alias at the bottom of the file:
```python
sample_contains_wall = sample_contains_mode  # back-compat alias
```

4. Rewrite `wall_blindness` as `mode_blindness` using the spec's probes:
```python
def mode_blindness(code: str, env, eps: float = 1e-6) -> float:
    """Fraction of mode-region probe transitions the synthesized model gets
    WRONG (1.0 = fully mode-blind, 0.0 = mode encoded correctly). Probes fire
    the mode in truth by construction. (Key stays `wall_blindness` in emitted
    JSON for backward compatibility.)"""
    spec = spec_for(env)
    probes = spec.mode_probes(env)
    model = SynthesizedModel(code, env)
    blind = 0
    for s, a in probes:
        st, rt, contact = env.step(s, a)
        assert contact, "probe must fire the mode in truth"
        sm, rm, _ = model.step(s, a)
        err = max(abs(st[0] - sm[0]), abs(st[1] - sm[1]), abs(rt - rm))
        if err > eps:
            blind += 1
    return blind / len(probes)


wall_blindness = mode_blindness  # back-compat alias
```

5. Update `synthesize_and_evaluate`'s signature param `include_wall` → `include_mode`, its call `build_contract(env, include_mode)`, and its returned dict to keep the stable keys while using the generic helpers:
```python
def synthesize_and_evaluate(provider, model_name, env,
                            include_mode: bool, n_rollouts: int, seed: int,
                            eps: float = 1e-9, max_iters: int = 5,
                            max_examples: int = 30) -> dict:
    transitions = collect_transitions(env, n_rollouts, seed=seed)
    contract = build_contract(env, include_mode)
    msgs = build_synthesis_messages(contract, transitions, max_examples)
    completion = provider.complete(msgs, model=model_name)
    code = extract_code(completion.text)
    refined = refine_continuous(provider, model_name, contract, code,
                                transitions, eps, max_iters=max_iters)
    return {
        "arm": "full" if include_mode else "incomplete",
        "seed": seed,
        "n_rollouts": n_rollouts,
        "eps": eps,
        "sample_contains_wall": sample_contains_mode(transitions),
        "gate_accuracy": refined.accuracy,
        "gate_passed": refined.accuracy == 1.0,
        "refine_iterations": refined.iterations,
        "wall_blindness": mode_blindness(refined.code, env)
        if refined.accuracy == 1.0 else None,
        "code": refined.code,
    }
```

6. `collect_transitions`, `contract_accuracy`, `refine_continuous`, `build_synthesis_messages`, `SynthesizedModel` are unchanged except: change type hints `CartWall` → `env` (drop the annotation or use `object`) where they appear, so nothing forces a cart. Do not change their bodies.

- [ ] **Step 4: Update the existing cart tests to the new names (keep them green)**

In `tests/test_continuous_contract.py`, the existing tests import `sample_contains_wall`, `wall_blindness`, and call `synthesize_and_evaluate(..., include_wall=...)`. Because aliases exist for the first two, only the keyword arg must change. Update the two `synthesize_and_evaluate(...)` calls: `include_wall=True` → `include_mode=True`, `include_wall=False` → `include_mode=False`. Leave everything else (they assert on dict keys `wall_blindness`/`sample_contains_wall`, which are preserved).

- [ ] **Step 5: Run the full continuous test suite**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_continuous_contract.py tests/test_instruments.py tests/test_continuous.py -v`
Expected: all pass, including `test_build_contract_cart_matches_golden` and the existing cart battery.

- [ ] **Step 6: Commit**

```bash
git add src/cwm/continuous/contract.py tests/test_continuous_contract.py
git commit -m "refactor: make continuous contract machinery env-generic via spec_for

build_contract/mode_blindness/sample_contains_mode now dispatch through
InstrumentSpec; cart prompt byte-identical (golden test). JSON keys
wall_blindness/sample_contains_wall and back-compat aliases preserved.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Offline pendulum battery (FakeProvider)

**Files:**
- Modify: `tests/test_continuous_contract.py`

**Interfaces:**
- Consumes: `PendulumStop` from `cwm.continuous.envs`; `synthesize_and_evaluate`, `contract_accuracy`, `collect_transitions`, `sample_contains_mode`, `mode_blindness`, `SynthesizedModel`, `build_contract` from `cwm.continuous.contract`; `FakeProvider`; `harness`.
- Produces: pendulum coverage mirroring the cart battery.

- [ ] **Step 1: Add the pendulum offline tests**

Append to `tests/test_continuous_contract.py`:
```python
from cwm.continuous.envs import PendulumStop
from cwm.continuous.contract import mode_blindness, sample_contains_mode

# Hand-written pendulum artifacts: same update expressions as PendulumStop.step
# (nonlinear plant), so the full one must match to float precision.
PEND_FULL_CODE = '''\
import math
def step(state, action):
    th, om = state
    a = max(-1.0, min(1.0, action))
    om2 = om + (3.0 * a - 2.0 * math.sin(th) - 0.3 * om) * 0.1
    th2 = th + om2 * 0.1
    if th2 >= 1.4:
        return [1.4, 0.0]
    return [th2, om2]
def reward(state):
    th = state[0]
    left = 0.3 / (1.0 + math.exp(-((-2.0 - th) / 0.25)))
    right = 1.0 / (1.0 + math.exp(-((th - 3.0) / 0.25)))
    return left + right
'''
PEND_INCOMPLETE_CODE = PEND_FULL_CODE.replace(
    "    if th2 >= 1.4:\n        return [1.4, 0.0]\n", "")

PEND_ENV = PendulumStop(th_stop=1.4)


def test_pendulum_full_code_is_float_exact_on_the_gate():
    transitions = collect_transitions(PEND_ENV, n_rollouts=5, seed=0)
    acc, failures = contract_accuracy(PEND_FULL_CODE, transitions, eps=1e-9)
    assert acc == 1.0, failures[:3]


def test_pendulum_incomplete_passes_iff_sample_missed_the_stop():
    far = collect_transitions(PEND_ENV, n_rollouts=5, seed=0)
    assert not sample_contains_mode(far)  # th_stop=1.4 rarely hit in 5 rollouts
    acc, _ = contract_accuracy(PEND_INCOMPLETE_CODE, far, eps=1e-9)
    assert acc == 1.0  # gate-miss event: stop-blind code fully verified
    near_env = PendulumStop(th_stop=0.5)
    near = collect_transitions(near_env, n_rollouts=20, seed=0)
    assert sample_contains_mode(near)
    acc2, failures = contract_accuracy(
        PEND_INCOMPLETE_CODE.replace("1.4", "0.5"), near, eps=1e-9)
    assert acc2 < 1.0 and failures  # stop transitions are inexplicable


def test_pendulum_mode_blindness_classifier():
    assert mode_blindness(PEND_FULL_CODE, PEND_ENV) == 0.0
    assert mode_blindness(PEND_INCOMPLETE_CODE, PEND_ENV) == 1.0


def test_pendulum_synthesize_and_evaluate_offline_both_arms():
    full = synthesize_and_evaluate(
        FakeProvider([f"```python\n{PEND_FULL_CODE}```"]), "fake", PEND_ENV,
        include_mode=True, n_rollouts=3, seed=0)
    assert full["gate_passed"] and full["wall_blindness"] == 0.0
    assert full["refine_iterations"] == 0 and not full["sample_contains_wall"]

    inc = synthesize_and_evaluate(
        FakeProvider([f"```python\n{PEND_INCOMPLETE_CODE}```"]), "fake", PEND_ENV,
        include_mode=False, n_rollouts=3, seed=0)
    assert inc["gate_passed"] and inc["wall_blindness"] == 1.0
    assert inc["arm"] == "incomplete"


def test_pendulum_blind_model_is_exploited_at_play():
    model = SynthesizedModel(PEND_INCOMPLETE_CODE, PEND_ENV)
    ep = harness.run_episode(PEND_ENV, model, "mpc", seed=3, n_samples=40)
    assert ep.contact and ep.final_state[0] == PEND_ENV.th_stop
    truth_ep = harness.run_episode(PEND_ENV, PEND_ENV, "mpc", seed=3, n_samples=40)
    assert truth_ep.ret > 10 * max(ep.ret, 0.1)
```

- [ ] **Step 2: Run the pendulum battery**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_continuous_contract.py -v -k pendulum`
Expected: 5 passed.

If `test_pendulum_incomplete_passes_iff_sample_missed_the_stop` fails on the `near_env` assertion (`sample_contains_mode(near)` False), raise the near-stop knob is too high — lower `th_stop` (e.g. `0.4`) until 20 rollouts hit it, and adjust the `.replace("1.4", "0.5")` string to match. If `test_pendulum_blind_model_is_exploited_at_play` fails the `ep.contact` assertion, the blind planner is not being lured — verify `PEND_ENV` uses defaults (th_right=3.0 beyond the stop) so the large plateau is blocked.

- [ ] **Step 3: Run the whole suite to confirm nothing regressed**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_continuous_contract.py
git commit -m "test: offline pendulum synthesis battery (FakeProvider)

Mirrors the cart battery on PendulumStop: full-spec float-exact on the gate,
stop-omitting artifact passes iff the sample missed the stop and probes fully
mode-blind, MPC on the blind artifact exploited (pinned at the stop).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Generalize the run script (`--instrument`, `--th-stop`)

**Files:**
- Modify: `scripts/continuous_danger_synthesis.py`

**Interfaces:**
- Consumes: `CartWall`, `PendulumStop` from `cwm.continuous.envs`; `synthesize_and_evaluate` (with `include_mode=`).
- Produces: CLI `--instrument {cart,pendulum}` (default `cart`), `--th-stop` (pendulum mode knob, default 1.4); output filename tagged with instrument + knob. Cart invocation and output filename UNCHANGED by default.

- [ ] **Step 1: Add the instrument switch**

In `scripts/continuous_danger_synthesis.py`:

1. Add imports: `from cwm.continuous.envs import CartWall, PendulumStop`.
2. Add args (after `--x-wall`):
```python
ap.add_argument("--instrument", choices=["cart", "pendulum"], default="cart")
ap.add_argument("--th-stop", type=float, default=1.4,
                help="pendulum mode knob (1.4 headline ~balanced; 1.0 caught)")
```
3. Build the env and a filename knob tag by instrument (replace the `ENV = CartWall(...)` line):
```python
if args.instrument == "pendulum":
    ENV = PendulumStop(th_stop=args.th_stop)
    KNOB = f"thstop{args.th_stop:g}"
    INSTR_TAG = "pendulum_"
else:
    ENV = CartWall(x_wall=args.x_wall)
    KNOB = f"xwall{args.x_wall:g}"
    INSTR_TAG = ""
```
4. Change the two `synthesize_and_evaluate(..., include_wall=(arm == "full"), ...)` calls to `include_mode=(arm == "full")`.
5. Change the incomplete-arm summary print: it currently says "wall ABSENT" — make it read the mode generically, e.g. replace `"wall "` with `"mode "` in the two summary strings (cosmetic; the JSON keys stay the same).
6. Change the output path (replace the `out = pathlib.Path(...)` line):
```python
out = pathlib.Path(
    f"results/continuous_synthesis_{INSTR_TAG}{TAG}_{KNOB}.json")
```
Note: for the cart with defaults this yields `results/continuous_synthesis_{TAG}_xwall8.json` — identical to today (INSTR_TAG empty). Confirm the f-string produces exactly that.

- [ ] **Step 2: Smoke-test the script wiring offline (no LLM) — cart filename unchanged**

Run:
```bash
PYTHONPATH=src .venv/bin/python -c "
import subprocess, sys
# argparse dry check: the cart default output path must be unchanged
import importlib.util, pathlib
# emulate the path expression
TAG='mini'; INSTR_TAG=''; KNOB='xwall8'
print(pathlib.Path(f'results/continuous_synthesis_{INSTR_TAG}{TAG}_{KNOB}.json'))
"
```
Expected: `results/continuous_synthesis_mini_xwall8.json` (matches the committed cart filename).

- [ ] **Step 3: Verify `--help` shows the new flags and parses**

Run: `PYTHONPATH=src .venv/bin/python scripts/continuous_danger_synthesis.py --help`
Expected: help text lists `--instrument {cart,pendulum}` and `--th-stop`.

- [ ] **Step 4: Commit**

```bash
git add scripts/continuous_danger_synthesis.py
git commit -m "feat: --instrument/--th-stop in synthesis script (cart default unchanged)

Selects CartWall or PendulumStop; output filename tagged with instrument +
mode knob. Cart default invocation and filename are byte-identical to before.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Credentialed pendulum runs (headline + caught, 20 seeds mini+large, + Qwen)

**Files:**
- Create (runtime output): `results/continuous_synthesis_pendulum_{mini,large}_thstop1.4.json`, `results/continuous_synthesis_pendulum_{mini,large}_thstop1.json`, `results/continuous_synthesis_pendulum_compat-qwen3-coder-30b-a3b-instruct_thstop1.4.json`
- Create (logs): `results/continuous_synthesis_pendulum_*.log`

**Interfaces:**
- Consumes: the Task 4 script; `.env` credentials in the worktree.

- [ ] **Step 1: One-seed live smoke test (headline mini) before the long runs**

Run:
```bash
PYTHONPATH=src .venv/bin/python scripts/continuous_danger_synthesis.py \
    mini 1 --instrument pendulum --th-stop 1.4
```
Expected: baselines print (`J_truth`>0, `J_random`≈small), one `[full seed=0]` and one `[incomplete seed=0]` line, and `wrote results/continuous_synthesis_pendulum_mini_thstop1.4.json`. This confirms Azure creds + the pendulum path end-to-end. Delete the 1-seed file afterward (`rm results/continuous_synthesis_pendulum_mini_thstop1.4.json`) so the real run isn't confused.

- [ ] **Step 2: Launch the four Azure cells sequentially in the background**

Run (background job; ~3 h total). Single-quoted `bash -c` so `$1/$2/$V/$?/$(date)` expand inside; `cd` uses the worktree's absolute path so cwd is unambiguous:
```bash
nohup bash -c '
  cd /private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2
  export PYTHONPATH=src
  V=/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python
  for cell in "mini 1.4" "large 1.4" "mini 1.0" "large 1.0"; do
    set -- $cell
    echo "=== $1 thstop$2 START $(date) ==="
    $V -u scripts/continuous_danger_synthesis.py $1 20 --instrument pendulum --th-stop $2
    echo "=== $1 thstop$2 DONE rc=$? $(date) ==="
  done
' > results/continuous_synthesis_pendulum_azure.log 2>&1 &
echo "PID $!"
```

- [ ] **Step 3: Monitor to completion**

Use the Monitor tool (or poll) on `results/continuous_synthesis_pendulum_azure.log` for lines matching `seed=|DONE|Error|Traceback|402|wrote `. Wait until all four `DONE rc=0` appear. Watch for: rc≠0, `Traceback`, `402` (HF only — not expected on Azure). If a cell dies, diagnose before continuing (do not silently skip).

- [ ] **Step 4: Launch the Qwen cross-family cell (headline th_stop=1.4, 3 seeds)**

Run:
```bash
nohup bash -c '
  cd /private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2
  export PYTHONPATH=src
  V=/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python
  echo "=== QWEN pendulum START $(date) ==="
  $V -u scripts/continuous_danger_synthesis.py mini 3 --instrument pendulum \
     --th-stop 1.4 --compat-model "Qwen/Qwen3-Coder-30B-A3B-Instruct"
  echo "=== QWEN pendulum DONE rc=$? $(date) ==="
' > results/continuous_synthesis_pendulum_qwen.log 2>&1 &
echo "PID $!"
```
Monitor for `DONE rc=0` and the `wrote ...` line. If it 402s, the HF account is out of credits (per the credentials memo) — surface to the user, do not retry blindly.

- [ ] **Step 5: Verify all five JSONs are well-formed and summarize**

Run:
```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import json, glob
for f in sorted(glob.glob("results/continuous_synthesis_pendulum_*.json")):
    d = json.load(open(f))
    inc = [c for c in d["cells"] if c["arm"] == "incomplete"]
    absent = [c for c in inc if not c["sample_contains_wall"]]
    present = [c for c in inc if c["sample_contains_wall"]]
    blind = [c for c in absent if c["gate_passed"] and c["wall_blindness"] == 1.0]
    rep = [c for c in present if c["gate_passed"] and c["wall_blindness"] == 0.0]
    stall = [c for c in present if not c["gate_passed"]]
    full = [c for c in d["cells"] if c["arm"] == "full"]
    print(f"{f}\n  model={d['model']} seeds={d['params']['n_seeds']} "
          f"th_stop={d['params'].get('th_stop')}\n"
          f"  full {sum(c['gate_accuracy']>=0.9995 for c in full)}/{len(full)} clean | "
          f"incomplete: absent={len(absent)} (blind&exploited={len(blind)}) "
          f"present={len(present)} (repaired={len(rep)} stalled={len(stall)})")
PY
```
Expected: full arms all clean; headline th_stop=1.4 has a mix of absent/present (~50/50); caught th_stop=1.0 has almost all present. Record the exact numbers for Task 6.

- [ ] **Step 6: Commit the result JSONs (not the logs)**

```bash
git add results/continuous_synthesis_pendulum_*.json
git commit -m "results: pendulum synthesis arm — headline+caught 20 seeds + Qwen

Second-instrument (PendulumStop, nonlinear plant) LLM synthesis: headline
th_stop=1.4 and caught th_stop=1.0 at 20 seeds mini+large, plus a Qwen
cross-family spot-check (3 seeds, th_stop=1.4).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Fold the pendulum results into the paper

**Files:**
- Modify: `docs/EXPERIMENTS.md`
- Modify: `docs/paper2/preprint-draft.md`
- Modify: `docs/paper2/main.tex`
- Regenerate: `docs/paper2/main.pdf`

**Interfaces:**
- Consumes: the summarized numbers from Task 5 Step 5.

- [ ] **Step 1: Add a dated EXPERIMENTS.md subsection**

Add a new section after the existing pendulum mechanism section:
`## PAPER 2 — Pendulum synthesis arm: repair-from-data on a nonlinear plant (2026-07-07, later)`
with per-cell tables (headline th_stop=1.4 and caught th_stop=1.0, both sizes; Qwen), using the EXACT numbers from Task 5 Step 5 (do not invent — copy from the summary). State whether repair-from-data reproduces (GPT-5.x) and how the cross-family (Qwen) behaves, mirroring the cart's section structure.

- [ ] **Step 2: Add the §6 second-instrument robustness paragraph (draft + tex)**

In `docs/paper2/preprint-draft.md` §6 and `docs/paper2/main.tex` §6 (`sec:synthesis`), add a short paragraph after the cross-family paragraph: the synthesis arm now runs on the pendulum too; report headline (identifiability event reproduces / play_cost≈1) and caught (repair-from-data reproduces or not) with the exact numbers. Keep the framing: mechanism was already two-instrument; now synthesis is too, so the repair finding is not a cart artifact / a nonlinear plant + angular clamp behaves the same.

- [ ] **Step 3: Update §9 limitations (draft + tex)**

Remove/replace the clause "the synthesis arms have run only on the cart" (draft `preprint-draft.md` and tex `main.tex`): synthesis now runs on both instruments; the remaining honest scope is one dimension / two stationary single-boundary modes (keep that part).

- [ ] **Step 4: Recompile the PDF and check presentation**

Run (uses the committed `main.bbl`; no bibtex):
```bash
cd docs/paper2
rm -f main.aux main.out main.log
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null 2>&1
echo "overfull>2pt:"; grep "^Overfull \\\\hbox" main.log | grep -oE "[0-9]+\.[0-9]+pt" | awk '$1+0>2.0' | wc -l | tr -d ' '
echo "undefined:"; grep -c "undefined" main.log
grep -oE "Output written on main.pdf \([0-9]+ pages" main.log
rm -f main.aux main.out main.log
cd ../..
```
Expected: `overfull>2pt: 0`, `undefined: 0`, page count printed. If overfull >0, tighten the offending sentence/table until 0.

- [ ] **Step 5: Commit**

```bash
git add docs/EXPERIMENTS.md docs/paper2/preprint-draft.md docs/paper2/main.tex docs/paper2/main.pdf
git commit -m "paper2+docs: fold pendulum synthesis arm into §6/§9 + EXPERIMENTS

Second-instrument synthesis results (headline+caught, both sizes, + Qwen).
Removes the 'synthesis only on the cart' limitation. main.tex recompiles clean.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Push the branch**

```bash
git push origin claude/continuous-setting-feasibility-wktp6b
```

---

## Notes for the executor

- If any pendulum calibration assumption breaks at run time (e.g. th_stop=1.4 turns out lopsided at 20 seeds), that is a finding, not a failure — record the actual absent/present split; do not force a rerun to hit 50/50.
- The cart is never re-run; its committed JSONs and the golden test guarantee §6's cart numbers still hold.
- Keep everything in the worktree; never switch the main checkout's branch.
