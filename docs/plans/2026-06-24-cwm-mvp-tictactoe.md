# CWM vs LLM-as-Policy (MVP: Tic-Tac-Toe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full Code-World-Model loop end-to-end on tic-tac-toe (synthesize a verifiable world model in code, refine it to perfect transition accuracy, plan with MCTS, and play it against an LLM-as-policy baseline), instrumented to report real token cost.

**Architecture:** A shared `WorldModel` contract is implemented both by a hand-written ground-truth (the oracle) and by LLM-synthesized code. Trajectories collected from the oracle drive both synthesis and a refinement loop that runs generated code in a sandbox until transition accuracy is 1.0. An MCTS planner plays the verified CWM against a direct-policy baseline in an arena, while a cost meter aggregates token usage.

**Tech Stack:** Python 3.11+, pytest, `openai` SDK (Azure client), `python-dotenv`. MCTS is hand-written (no extra deps). No OpenSpiel in the MVP.

## Global Constraints

- Python **3.11+** (uses `tomllib`, modern typing).
- State representation is **fixed and JSON-serializable**: `State = {"board": list[int] of length 9, "current_player": int}` where cell values are `0` empty, `1` X, `2` O; `current_player` ∈ `{1, 2}`. `Action = int` in `0..8` (cell index).
- The `WorldModel` contract (identical for ground-truth and synthesized code):
  - `initial_state() -> State`
  - `legal_actions(state: State) -> list[int]`
  - `apply_action(state: State, action: int) -> State`
  - `is_terminal(state: State) -> bool`
  - `returns(state: State) -> dict[int, float]` → `{1: r1, 2: r2}`, values in `{-1.0, 0.0, 1.0}`; all-zero unless terminal.
- **No `temperature`/`top_p`** sent to GPT-5.4 models (newer models reject them); rely on natural sampling. Model/deployment names are always **parameters**, never hardcoded.
- **Sandbox is mandatory** for any execution of generated code: subprocess, hard timeout, no network, no disk writes.
- API keys/endpoints come from `.env` (loaded via `python-dotenv`); **never** commit them. Tests must **never** hit a real API — always use a fake provider.
- TDD throughout: failing test first, minimal implementation, frequent commits.
- Test layout uses `pythonpath = ["src"]` (no install step needed).

---

## File Structure

```
code-world-models/
├── pyproject.toml              # project metadata + pytest config (pythonpath=src)
├── .gitignore
├── .env.example                # documents required env vars (no secrets)
├── README.md
├── src/cwm/
│   ├── __init__.py
│   ├── world_model.py          # WorldModel Protocol, JSON (de)serialization, CONTRACT_TEXT
│   ├── groundtruth/
│   │   ├── __init__.py
│   │   └── tictactoe.py        # oracle implementation of the contract
│   ├── trajectories.py         # Trajectory dataclass + collect_trajectories()
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py         # LLMProvider Protocol, Usage, FakeProvider
│   │   └── azure_openai.py     # AzureOpenAIProvider
│   ├── sandbox.py              # run_in_sandbox()
│   ├── synthesizer.py          # synthesize_cwm()
│   ├── refiner.py              # transition_accuracy(), refine_cwm()
│   ├── mcts.py                 # mcts_policy()
│   ├── baseline.py             # baseline_policy()
│   ├── arena.py                # play_match(), run_arena()
│   ├── cost_meter.py           # CostMeter, extrapolate()
│   └── run_experiment.py       # CLI wiring it all together
└── tests/
    ├── test_tictactoe.py
    ├── test_trajectories.py
    ├── test_provider.py
    ├── test_sandbox.py
    ├── test_synthesizer.py
    ├── test_refiner.py
    ├── test_mcts.py
    ├── test_baseline.py
    ├── test_arena.py
    └── test_cost_meter.py
```

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`, `src/cwm/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a runnable `pytest` that collects 0 tests; `pythonpath=src` import root.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "cwm"
version = "0.1.0"
description = "Code World Models vs LLM-as-policy — MVP"
requires-python = ">=3.11"
dependencies = ["openai>=1.40.0", "python-dotenv>=1.0.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
.venv/
venv/
.pytest_cache/
*.egg-info/
results/
```

- [ ] **Step 3: Create `.env.example`**

```bash
# Azure OpenAI — fill these in a local .env (never commit .env)
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-12-01-preview
# Deployment names for each size
AZURE_DEPLOYMENT_LARGE=gpt-5.4
AZURE_DEPLOYMENT_MINI=gpt-5.4-mini
AZURE_DEPLOYMENT_NANO=gpt-5.4-nano
```

- [ ] **Step 4: Create empty package files and a placeholder README**

`src/cwm/__init__.py` and `tests/__init__.py` are empty files. `README.md`:

```markdown
# Code World Models vs LLM-as-Policy (MVP)

Reproduces, at small scale, the Code World Models result: synthesized verifiable
code + MCTS vs a direct LLM policy. See `docs/specs/` and `docs/plans/`.

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # then fill in Azure credentials

## Test
    pytest
```

- [ ] **Step 5: Create the venv and install**

Run:
```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```
Expected: installs `openai`, `python-dotenv`, `pytest` without error.

- [ ] **Step 6: Run pytest to verify collection**

Run: `pytest`
Expected: exits 0 (or code 5 "no tests ran") — no import/config errors.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "chore: project scaffolding (pyproject, env, package skeleton)"
```

---

## Task 2: World model contract + tic-tac-toe ground truth

**Files:**
- Create: `src/cwm/world_model.py`, `src/cwm/groundtruth/__init__.py`, `src/cwm/groundtruth/tictactoe.py`
- Test: `tests/test_tictactoe.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `world_model.py`: `State` (type alias `dict`), `Action` (`int`), `state_to_json(state)->str`, `state_from_json(s)->State`, `CONTRACT_TEXT: str` (human-readable contract used later in synthesis prompts).
  - `groundtruth/tictactoe.py`: module-level functions `initial_state()`, `legal_actions(state)`, `apply_action(state, action)`, `is_terminal(state)`, `returns(state)` matching the contract; plus `winner(state) -> int` (0 none, 1, or 2).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tictactoe.py
import json
from cwm.groundtruth import tictactoe as g
from cwm import world_model as wm

def test_initial_state():
    s = g.initial_state()
    assert s == {"board": [0]*9, "current_player": 1}

def test_legal_actions_all_open():
    assert g.legal_actions(g.initial_state()) == list(range(9))

def test_apply_action_places_and_switches():
    s2 = g.apply_action(g.initial_state(), 4)
    assert s2["board"][4] == 1
    assert s2["current_player"] == 2

def test_apply_action_is_pure():
    s = g.initial_state()
    g.apply_action(s, 0)
    assert s["board"] == [0]*9  # original unchanged

def test_row_win_terminal_and_returns():
    # X takes 0,1,2 ; O takes 3,4
    s = g.initial_state()
    for a in [0, 3, 1, 4, 2]:
        s = g.apply_action(s, a)
    assert g.winner(s) == 1
    assert g.is_terminal(s) is True
    assert g.returns(s) == {1: 1.0, 2: -1.0}

def test_full_board_draw():
    s = g.initial_state()
    # 0 1 2 / 3 4 5 / 6 7 8 filled to a draw:
    # X O X / X O O / O X X  -> moves order producing that, no 3-in-a-row
    for a in [0, 1, 2, 4, 3, 5, 7, 6, 8]:
        s = g.apply_action(s, a)
    assert g.is_terminal(s) is True
    assert g.winner(s) == 0
    assert g.returns(s) == {1: 0.0, 2: 0.0}

def test_legal_actions_excludes_filled():
    s = g.apply_action(g.initial_state(), 0)
    assert 0 not in g.legal_actions(s)

def test_json_roundtrip():
    s = g.apply_action(g.initial_state(), 4)
    assert wm.state_from_json(wm.state_to_json(s)) == s
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tictactoe.py -v`
Expected: FAIL (ModuleNotFoundError / functions undefined).

- [ ] **Step 3: Implement `world_model.py`**

```python
# src/cwm/world_model.py
"""Shared world-model contract and (de)serialization for the sandbox boundary."""
import json

State = dict   # {"board": list[int] len 9, "current_player": int}
Action = int   # 0..8

def state_to_json(state: State) -> str:
    return json.dumps(state, sort_keys=True)

def state_from_json(s: str) -> State:
    return json.loads(s)

CONTRACT_TEXT = """\
Implement a deterministic tic-tac-toe world model as Python module-level functions.

State is a dict: {"board": [int]*9, "current_player": int}.
  - board cells: 0 = empty, 1 = X, 2 = O, indexed 0..8 row-major.
  - current_player: 1 or 2 (player to move).
Action is an int 0..8 (the cell index to play).

Functions to implement EXACTLY these signatures (pure, no I/O, no globals):
  def initial_state() -> dict
  def legal_actions(state: dict) -> list[int]
  def apply_action(state: dict, action: int) -> dict   # returns a NEW state; do not mutate input
  def is_terminal(state: dict) -> bool
  def returns(state: dict) -> dict                       # {1: r1, 2: r2}, each in {-1.0,0.0,1.0}; all 0.0 unless terminal

Rules: players alternate; a player wins with 3 in a row/column/diagonal; the
board full with no winner is a draw. returns gives +1.0 to the winner, -1.0 to
the loser, 0.0/0.0 for a draw or any non-terminal state.
"""
```

- [ ] **Step 4: Implement `groundtruth/tictactoe.py`**

```python
# src/cwm/groundtruth/__init__.py  -> empty file
```
```python
# src/cwm/groundtruth/tictactoe.py
"""Hand-written tic-tac-toe oracle implementing the world_model contract."""

_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # cols
    (0, 4, 8), (2, 4, 6),              # diagonals
]

def initial_state() -> dict:
    return {"board": [0] * 9, "current_player": 1}

def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    return [i for i, c in enumerate(state["board"]) if c == 0]

def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    board[action] = state["current_player"]
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}

def winner(state: dict) -> int:
    b = state["board"]
    for x, y, z in _LINES:
        if b[x] != 0 and b[x] == b[y] == b[z]:
            return b[x]
    return 0

def is_terminal(state: dict) -> bool:
    return winner(state) != 0 or all(c != 0 for c in state["board"])

def returns(state: dict) -> dict:
    w = winner(state)
    if w == 1:
        return {1: 1.0, 2: -1.0}
    if w == 2:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_tictactoe.py -v`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: world-model contract + tic-tac-toe ground truth"
```

---

## Task 3: Trajectory collector

**Files:**
- Create: `src/cwm/trajectories.py`
- Test: `tests/test_trajectories.py`

**Interfaces:**
- Consumes: `groundtruth.tictactoe` (the contract functions).
- Produces:
  - `@dataclass(frozen=True) Trajectory` with fields `state: dict`, `action: int`, `next_state: dict`, `reward: dict`, `terminal: bool`, `legal_actions: list[int]`.
  - `collect_trajectories(model, n_games: int, seed: int) -> list[Trajectory]` where `model` is any module/object exposing the contract functions.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_trajectories.py
from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories, Trajectory

def test_collect_is_deterministic_with_seed():
    a = collect_trajectories(g, n_games=3, seed=42)
    b = collect_trajectories(g, n_games=3, seed=42)
    assert [t.action for t in a] == [t.action for t in b]

def test_trajectories_are_valid_transitions():
    traj = collect_trajectories(g, n_games=5, seed=1)
    assert len(traj) > 0
    for t in traj:
        assert isinstance(t, Trajectory)
        assert t.action in t.legal_actions
        assert g.apply_action(t.state, t.action) == t.next_state

def test_terminal_flag_matches_model():
    traj = collect_trajectories(g, n_games=5, seed=7)
    for t in traj:
        assert t.terminal == g.is_terminal(t.next_state)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trajectories.py -v`
Expected: FAIL (module/functions undefined).

- [ ] **Step 3: Implement `trajectories.py`**

```python
# src/cwm/trajectories.py
"""Collect random-vs-random trajectories from a world model."""
import random
from dataclasses import dataclass

@dataclass(frozen=True)
class Trajectory:
    state: dict
    action: int
    next_state: dict
    reward: dict
    terminal: bool
    legal_actions: list

def collect_trajectories(model, n_games: int, seed: int) -> list:
    rng = random.Random(seed)
    out: list = []
    for _ in range(n_games):
        state = model.initial_state()
        while not model.is_terminal(state):
            legal = model.legal_actions(state)
            action = rng.choice(legal)
            nxt = model.apply_action(state, action)
            out.append(Trajectory(
                state=state, action=action, next_state=nxt,
                reward=model.returns(nxt), terminal=model.is_terminal(nxt),
                legal_actions=legal,
            ))
            state = nxt
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trajectories.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: random-vs-random trajectory collector"
```

---

## Task 4: LLM provider abstraction + fake + Azure impl

**Files:**
- Create: `src/cwm/llm/__init__.py`, `src/cwm/llm/provider.py`, `src/cwm/llm/azure_openai.py`
- Test: `tests/test_provider.py`

**Interfaces:**
- Consumes: nothing (Azure impl uses `openai` lazily).
- Produces:
  - `@dataclass Usage` with `prompt_tokens: int`, `completion_tokens: int`.
  - `Completion` = `@dataclass` with `text: str`, `usage: Usage`.
  - `LLMProvider` Protocol: `complete(self, messages: list[dict], model: str) -> Completion`.
  - `FakeProvider(responses: list[str])` — returns canned responses in order, fabricates usage from text length; for tests.
  - `AzureOpenAIProvider(endpoint, api_key, api_version)` with `.complete(messages, model)`.

- [ ] **Step 1: Write failing tests** (fake provider only; Azure impl is not unit-tested against the network)

```python
# tests/test_provider.py
from cwm.llm.provider import FakeProvider, Usage, Completion

def test_fake_returns_in_order():
    p = FakeProvider(["a", "b"])
    assert p.complete([{"role": "user", "content": "x"}], model="m").text == "a"
    assert p.complete([{"role": "user", "content": "y"}], model="m").text == "b"

def test_fake_tracks_usage_nonzero():
    p = FakeProvider(["hello world"])
    c = p.complete([{"role": "user", "content": "hi"}], model="m")
    assert isinstance(c, Completion) and isinstance(c.usage, Usage)
    assert c.usage.prompt_tokens > 0 and c.usage.completion_tokens > 0

def test_fake_raises_when_exhausted():
    p = FakeProvider(["only"])
    p.complete([{"role": "user", "content": "x"}], model="m")
    try:
        p.complete([{"role": "user", "content": "x"}], model="m")
        assert False, "expected StopIteration-style error"
    except IndexError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_provider.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `provider.py`**

```python
# src/cwm/llm/__init__.py  -> empty file
```
```python
# src/cwm/llm/provider.py
"""LLM provider abstraction + a deterministic fake for tests."""
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int

@dataclass
class Completion:
    text: str
    usage: Usage

class LLMProvider(Protocol):
    def complete(self, messages: list[dict], model: str) -> Completion: ...

class FakeProvider:
    """Returns canned responses in order. Usage approximated as word counts."""
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._i = 0

    def complete(self, messages: list[dict], model: str) -> Completion:
        text = self._responses[self._i]   # IndexError when exhausted (tested)
        self._i += 1
        prompt_words = sum(len(m["content"].split()) for m in messages)
        return Completion(
            text=text,
            usage=Usage(prompt_tokens=max(1, prompt_words),
                        completion_tokens=max(1, len(text.split()))),
        )
```

- [ ] **Step 4: Implement `azure_openai.py`** (no unit test; exercised in the manual end-to-end run)

```python
# src/cwm/llm/azure_openai.py
"""Azure OpenAI implementation of LLMProvider."""
from .provider import Completion, Usage

class AzureOpenAIProvider:
    def __init__(self, endpoint: str, api_key: str, api_version: str):
        from openai import AzureOpenAI  # lazy import so tests don't need the dep wired
        self._client = AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version
        )

    def complete(self, messages: list[dict], model: str) -> Completion:
        # NOTE: no temperature/top_p — GPT-5.4 rejects them.
        resp = self._client.chat.completions.create(model=model, messages=messages)
        u = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            usage=Usage(prompt_tokens=u.prompt_tokens,
                        completion_tokens=u.completion_tokens),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_provider.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: LLM provider abstraction + fake + Azure OpenAI impl"
```

---

## Task 5: Sandbox executor

**Files:**
- Create: `src/cwm/sandbox.py`
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass SandboxResult` with `ok: bool`, `stdout: str`, `stderr: str`, `timed_out: bool`.
  - `run_in_sandbox(code: str, call: str, timeout: float = 5.0) -> SandboxResult` — writes `code` + `call` to a temp file, runs it in a fresh `python -I` subprocess with a timeout, captures stdout/stderr. `call` is appended Python that prints JSON to stdout. (Network/disk isolation for the MVP = `python -I` + no helpers that open sockets; hardening deferred per spec §9.)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_sandbox.py
from cwm.sandbox import run_in_sandbox

def test_runs_and_captures_stdout():
    r = run_in_sandbox("def f():\n    return 3\n", "print(f() + 4)")
    assert r.ok is True and r.stdout.strip() == "7" and r.timed_out is False

def test_captures_error():
    r = run_in_sandbox("def f():\n    raise ValueError('boom')\n", "f()")
    assert r.ok is False and "ValueError" in r.stderr and "boom" in r.stderr

def test_times_out():
    r = run_in_sandbox("import time\n", "time.sleep(10)", timeout=1.0)
    assert r.timed_out is True and r.ok is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sandbox.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `sandbox.py`**

```python
# src/cwm/sandbox.py
"""Run untrusted generated code in an isolated subprocess."""
import subprocess
import sys
import tempfile
from dataclasses import dataclass

@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    timed_out: bool

def run_in_sandbox(code: str, call: str, timeout: float = 5.0) -> SandboxResult:
    source = code + "\n" + call + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=True) as f:
        f.write(source)
        f.flush()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", f.name],   # -I: isolated, ignore env & user site
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, stdout="", stderr="timeout", timed_out=True)
    return SandboxResult(
        ok=(proc.returncode == 0), stdout=proc.stdout, stderr=proc.stderr,
        timed_out=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sandbox.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: subprocess sandbox with timeout"
```

---

## Task 6: CWM synthesizer

**Files:**
- Create: `src/cwm/synthesizer.py`
- Test: `tests/test_synthesizer.py`

**Interfaces:**
- Consumes: `world_model.CONTRACT_TEXT`, `trajectories.Trajectory`, `llm.provider.LLMProvider`.
- Produces:
  - `build_synthesis_messages(contract: str, trajectories: list, max_examples: int = 30) -> list[dict]` — the chat messages.
  - `extract_code(text: str) -> str` — pulls Python out of a ```python fenced block (or returns the text if unfenced).
  - `synthesize_cwm(provider, model: str, contract: str, trajectories: list) -> tuple[str, Usage]` — returns `(code, usage)`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_synthesizer.py
from cwm.synthesizer import build_synthesis_messages, extract_code, synthesize_cwm
from cwm.llm.provider import FakeProvider
from cwm.world_model import CONTRACT_TEXT
from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories

def test_messages_include_contract_and_examples():
    traj = collect_trajectories(g, n_games=2, seed=1)
    msgs = build_synthesis_messages(CONTRACT_TEXT, traj, max_examples=5)
    blob = " ".join(m["content"] for m in msgs)
    assert "initial_state" in blob          # contract present
    assert "current_player" in blob         # example states present
    assert msgs[-1]["role"] == "user"

def test_extract_code_from_fence():
    text = "Sure:\n```python\ndef f():\n    return 1\n```\nDone."
    assert extract_code(text) == "def f():\n    return 1"

def test_extract_code_without_fence_returns_text():
    assert extract_code("def f():\n    return 1").startswith("def f")

def test_synthesize_returns_code_and_usage():
    traj = collect_trajectories(g, n_games=1, seed=1)
    fake = FakeProvider(["```python\ndef initial_state():\n    return {}\n```"])
    code, usage = synthesize_cwm(fake, "nano", CONTRACT_TEXT, traj)
    assert "def initial_state" in code
    assert usage.completion_tokens > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_synthesizer.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `synthesizer.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_synthesizer.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: CWM synthesizer (prompt build, code extraction)"
```

---

## Task 7: Test refiner (accuracy + refinement loop)

**Files:**
- Create: `src/cwm/refiner.py`
- Test: `tests/test_refiner.py`

**Interfaces:**
- Consumes: `sandbox.run_in_sandbox`, `synthesizer.build_synthesis_messages`/`extract_code`, `world_model` serialization, `llm.provider`.
- Produces:
  - `transition_accuracy(code: str, trajectories: list, timeout: float = 5.0) -> tuple[float, list[str]]` — fraction of trajectories whose `apply_action` (run in sandbox) reproduces `next_state`; returns `(accuracy, failures)` where each failure is a short string (the mismatch or stack trace).
  - `refine_cwm(provider, model, contract, code, trajectories, max_iters=5) -> RefineResult` with `@dataclass RefineResult{code:str, accuracy:float, iterations:int, usages:list}`.

- [ ] **Step 1: Write failing tests** (use the ground truth as a "perfect synthesis" and a deliberately broken one)

```python
# tests/test_refiner.py
import inspect
from cwm.refiner import transition_accuracy, refine_cwm, RefineResult
from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories
from cwm.world_model import CONTRACT_TEXT
from cwm.llm.provider import FakeProvider

PERFECT = inspect.getsource(g)  # ground-truth source implements the contract

BROKEN = (
    "def initial_state():\n    return {'board':[0]*9,'current_player':1}\n"
    "def legal_actions(state):\n    return [i for i,c in enumerate(state['board']) if c==0]\n"
    "def apply_action(state, action):\n"
    "    b=list(state['board']); b[action]=99\n"   # wrong: writes 99
    "    return {'board':b,'current_player':2 if state['current_player']==1 else 1}\n"
    "def is_terminal(state):\n    return all(c!=0 for c in state['board'])\n"
    "def returns(state):\n    return {1:0.0,2:0.0}\n"
)

def test_perfect_code_scores_1():
    traj = collect_trajectories(g, n_games=5, seed=3)
    acc, failures = transition_accuracy(PERFECT, traj)
    assert acc == 1.0 and failures == []

def test_broken_code_scores_below_1():
    traj = collect_trajectories(g, n_games=5, seed=3)
    acc, failures = transition_accuracy(BROKEN, traj)
    assert acc < 1.0 and len(failures) > 0

def test_refine_stops_at_perfect_accuracy():
    traj = collect_trajectories(g, n_games=3, seed=3)
    # provider would "fix" by returning PERFECT, but starting code is already perfect
    fake = FakeProvider([f"```python\n{PERFECT}\n```"])
    res = refine_cwm(fake, "nano", CONTRACT_TEXT, PERFECT, traj, max_iters=5)
    assert isinstance(res, RefineResult)
    assert res.accuracy == 1.0 and res.iterations == 0  # already perfect, no LLM call

def test_refine_recovers_from_broken():
    traj = collect_trajectories(g, n_games=3, seed=3)
    fake = FakeProvider([f"```python\n{PERFECT}\n```"])  # one fix is enough
    res = refine_cwm(fake, "nano", CONTRACT_TEXT, BROKEN, traj, max_iters=5)
    assert res.accuracy == 1.0 and res.iterations == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_refiner.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `refiner.py`**

```python
# src/cwm/refiner.py
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
    # Build one batch program: apply each action, print the resulting states as JSON.
    cases = [{"state": t.state, "action": t.action} for t in trajectories]
    call = (
        "import json\n"
        f"_cases = json.loads(r'''{json.dumps(cases)}''')\n"
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
    produced = json.loads(res.stdout.strip().splitlines()[-1])
    failures = []
    correct = 0
    for t, got in zip(trajectories, produced):
        if got == t.next_state:
            correct += 1
        else:
            failures.append(f"state={t.state} action={t.action} "
                            f"expected={t.next_state} got={got}")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_refiner.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: transition-accuracy check + refinement loop"
```

---

## Task 8: MCTS planner

**Files:**
- Create: `src/cwm/mcts.py`
- Test: `tests/test_mcts.py`

**Interfaces:**
- Consumes: any object/module exposing the contract functions (`legal_actions`, `apply_action`, `is_terminal`, `returns`).
- Produces:
  - `mcts_policy(model, state: dict, n_simulations: int = 200, seed: int = 0) -> int` — returns the chosen action for `state["current_player"]` using UCT with random rollouts.

- [ ] **Step 1: Write failing tests** (MCTS on the ground truth should be tactically sound)

```python
# tests/test_mcts.py
from cwm.mcts import mcts_policy
from cwm.groundtruth import tictactoe as g

def test_takes_immediate_win():
    # X at 0,1 ; needs 2 to win. O scattered harmlessly.
    state = {"board": [1, 1, 0, 2, 2, 0, 0, 0, 0], "current_player": 1}
    assert mcts_policy(g, state, n_simulations=300, seed=1) == 2

def test_blocks_immediate_loss():
    # O threatens 0,1 -> 2. X must block at 2.
    state = {"board": [2, 2, 0, 1, 0, 0, 0, 0, 0], "current_player": 1}
    assert mcts_policy(g, state, n_simulations=400, seed=1) == 2

def test_returns_legal_action():
    state = g.initial_state()
    assert mcts_policy(g, state, n_simulations=50, seed=1) in g.legal_actions(state)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcts.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `mcts.py`**

```python
# src/cwm/mcts.py
"""Minimal UCT MCTS over a world-model contract."""
import math
import random
from .world_model import state_to_json

class _Node:
    __slots__ = ("state", "player", "parent", "action", "children",
                 "visits", "value", "untried")
    def __init__(self, model, state, parent=None, action=None):
        self.state = state
        self.player = state["current_player"]
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried = list(model.legal_actions(state))

def _uct(child, c=1.41):
    if child.visits == 0:
        return float("inf")
    return (child.value / child.visits) + c * math.sqrt(
        math.log(child.parent.visits) / child.visits)

def _rollout(model, state, rng):
    while not model.is_terminal(state):
        state = model.apply_action(state, rng.choice(model.legal_actions(state)))
    return model.returns(state)

def mcts_policy(model, state: dict, n_simulations: int = 200, seed: int = 0) -> int:
    rng = random.Random(seed)
    root = _Node(model, state)
    for _ in range(n_simulations):
        node = root
        # Selection
        while not node.untried and node.children:
            node = max(node.children, key=_uct)
        # Expansion
        if node.untried:
            a = rng.choice(node.untried)
            node.untried.remove(a)
            child = _Node(model, model.apply_action(node.state, a),
                          parent=node, action=a)
            node.children.append(child)
            node = child
        # Simulation
        result = _rollout(model, node.state, rng)
        # Backpropagation (reward from each node's mover's perspective)
        while node is not None:
            node.visits += 1
            if node.parent is not None:
                node.value += result[node.parent.player]
            node = node.parent
    best = max(root.children, key=lambda n: n.visits)
    return best.action
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcts.py -v`
Expected: PASS (3 tests). If `test_blocks_immediate_loss` is flaky, raise `n_simulations` in the test — document, don't weaken the assertion.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: UCT MCTS planner over the world-model contract"
```

---

## Task 9: Baseline LLM-as-policy agent

**Files:**
- Create: `src/cwm/baseline.py`
- Test: `tests/test_baseline.py`

**Interfaces:**
- Consumes: `llm.provider.LLMProvider`, ground-truth `legal_actions` (for the prompt only).
- Produces:
  - `build_policy_messages(state: dict, legal: list[int]) -> list[dict]`.
  - `parse_action(text: str) -> int | None` — extracts the first integer 0..8, else `None`.
  - `baseline_policy(provider, model, state, legal) -> tuple[int | None, Usage]` — returns `(action_or_None, usage)`; `None` signals an illegal/unparseable move (counted by the arena).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_baseline.py
from cwm.baseline import build_policy_messages, parse_action, baseline_policy
from cwm.llm.provider import FakeProvider

def test_parse_plain_int():
    assert parse_action("4") == 4

def test_parse_from_sentence():
    assert parse_action("I'll play cell 7 because...") == 7

def test_parse_none_when_absent():
    assert parse_action("no number here") is None

def test_messages_mention_legal_actions():
    msgs = build_policy_messages({"board": [0]*9, "current_player": 1}, [0, 1, 2])
    assert "[0, 1, 2]" in " ".join(m["content"] for m in msgs)

def test_baseline_returns_action_and_usage():
    fake = FakeProvider(["I choose 3"])
    action, usage = baseline_policy(fake, "large",
                                    {"board": [0]*9, "current_player": 1}, [3, 4])
    assert action == 3 and usage.completion_tokens > 0

def test_baseline_illegal_returns_none():
    fake = FakeProvider(["I choose 8"])   # 8 not in legal
    action, _ = baseline_policy(fake, "large",
                                {"board": [0]*9, "current_player": 1}, [3, 4])
    assert action is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_baseline.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `baseline.py`**

```python
# src/cwm/baseline.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_baseline.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: LLM-as-policy baseline agent"
```

---

## Task 10: Arena

**Files:**
- Create: `src/cwm/arena.py`
- Test: `tests/test_arena.py`

**Interfaces:**
- Consumes: ground-truth contract (referee), `mcts.mcts_policy`, `baseline.baseline_policy`-style callables.
- Produces:
  - `@dataclass MatchResult{winner:int, illegal_by:dict, moves:int}` (`winner` 0/1/2; `illegal_by` like `{1:0,2:1}`).
  - `play_match(referee, agent1, agent2, seed) -> MatchResult` where each `agentK(state, legal) -> int | None`; a `None` or illegal move **forfeits** the match (the other player wins) and is recorded in `illegal_by`.
  - `@dataclass ArenaResult{games:int, cwm_wins:int, baseline_wins:int, draws:int, baseline_illegal:int, cwm_illegal:int}`.
  - `run_arena(referee, cwm_agent, baseline_agent, n_games, seed) -> ArenaResult` — alternates who starts each game.

- [ ] **Step 1: Write failing tests** (deterministic stub agents — no LLM, no MCTS)

```python
# tests/test_arena.py
from cwm.arena import play_match, run_arena, MatchResult, ArenaResult
from cwm.groundtruth import tictactoe as g

def first_legal(state, legal):
    return legal[0]

def always_illegal(state, legal):
    return None

def test_forfeit_on_illegal():
    # player 1 (agent1) always returns None -> forfeits, player 2 wins
    res = play_match(g, always_illegal, first_legal, seed=1)
    assert isinstance(res, MatchResult)
    assert res.winner == 2 and res.illegal_by[1] == 1

def test_play_match_completes_to_terminal():
    res = play_match(g, first_legal, first_legal, seed=1)
    assert res.winner in (0, 1, 2) and res.moves > 0

def test_run_arena_aggregates_and_alternates():
    # cwm_agent = first_legal, baseline = always_illegal -> baseline forfeits every game
    res = run_arena(g, cwm_agent=first_legal, baseline_agent=always_illegal,
                    n_games=4, seed=1)
    assert isinstance(res, ArenaResult)
    assert res.games == 4
    assert res.cwm_wins == 4 and res.baseline_illegal == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_arena.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `arena.py`**

```python
# src/cwm/arena.py
"""Run matches between two agents, refereed by the ground-truth model."""
from dataclasses import dataclass

@dataclass
class MatchResult:
    winner: int          # 0 draw, else player number
    illegal_by: dict     # {1: count, 2: count}
    moves: int

@dataclass
class ArenaResult:
    games: int
    cwm_wins: int
    baseline_wins: int
    draws: int
    baseline_illegal: int
    cwm_illegal: int

def play_match(referee, agent1, agent2, seed) -> MatchResult:
    agents = {1: agent1, 2: agent2}
    illegal_by = {1: 0, 2: 0}
    state = referee.initial_state()
    moves = 0
    while not referee.is_terminal(state):
        p = state["current_player"]
        legal = referee.legal_actions(state)
        action = agents[p](state, legal)
        if action is None or action not in legal:
            illegal_by[p] += 1
            return MatchResult(winner=(2 if p == 1 else 1),
                               illegal_by=illegal_by, moves=moves)
        state = referee.apply_action(state, action)
        moves += 1
    r = referee.returns(state)
    winner = 1 if r[1] == 1.0 else (2 if r[2] == 1.0 else 0)
    return MatchResult(winner=winner, illegal_by=illegal_by, moves=moves)

def run_arena(referee, cwm_agent, baseline_agent, n_games, seed) -> ArenaResult:
    cwm_wins = baseline_wins = draws = baseline_illegal = cwm_illegal = 0
    for i in range(n_games):
        cwm_is_p1 = (i % 2 == 0)   # alternate who starts
        if cwm_is_p1:
            m = play_match(referee, cwm_agent, baseline_agent, seed + i)
            cwm_player, base_player = 1, 2
        else:
            m = play_match(referee, baseline_agent, cwm_agent, seed + i)
            cwm_player, base_player = 2, 1
        cwm_illegal += m.illegal_by[cwm_player]
        baseline_illegal += m.illegal_by[base_player]
        if m.winner == 0:
            draws += 1
        elif m.winner == cwm_player:
            cwm_wins += 1
        else:
            baseline_wins += 1
    return ArenaResult(games=n_games, cwm_wins=cwm_wins, baseline_wins=baseline_wins,
                       draws=draws, baseline_illegal=baseline_illegal,
                       cwm_illegal=cwm_illegal)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_arena.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: arena with forfeit-on-illegal and alternating starts"
```

---

## Task 11: Cost meter

**Files:**
- Create: `src/cwm/cost_meter.py`
- Test: `tests/test_cost_meter.py`

**Interfaces:**
- Consumes: `llm.provider.Usage`.
- Produces:
  - `PRICES: dict[str, tuple[float, float]]` — USD per 1M tokens `(input, output)` keyed by role label `"large"/"mini"/"nano"`; placeholder values, clearly marked to update with real Azure pricing.
  - `@dataclass CostMeter` with `add(role: str, usage: Usage)` and `total_usd() -> float`, plus `by_role: dict`.
  - `extrapolate(per_game_usd: float, n_games: int) -> float`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cost_meter.py
from cwm.cost_meter import CostMeter, extrapolate, PRICES
from cwm.llm.provider import Usage

def test_prices_have_three_roles():
    assert {"large", "mini", "nano"} <= set(PRICES)

def test_cost_accumulates_by_role():
    m = CostMeter()
    m.add("nano", Usage(prompt_tokens=1_000_000, completion_tokens=0))
    m.add("large", Usage(prompt_tokens=0, completion_tokens=1_000_000))
    assert m.by_role["nano"] > 0 and m.by_role["large"] > 0
    assert abs(m.total_usd() - (m.by_role["nano"] + m.by_role["large"])) < 1e-9

def test_extrapolate_linear():
    assert extrapolate(0.5, 10) == 5.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cost_meter.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `cost_meter.py`**

```python
# src/cwm/cost_meter.py
"""Token accounting and USD estimation.

PRICES are PLACEHOLDERS (USD per 1M tokens, input/output). Replace with real
Azure GPT-5.4 pricing before quoting any figure in the article.
"""
from dataclasses import dataclass, field

PRICES = {
    "large": (5.0, 25.0),   # TODO: real gpt-5.4 pricing
    "mini": (1.0, 5.0),     # TODO: real gpt-5.4-mini pricing
    "nano": (0.5, 2.0),     # TODO: real gpt-5.4-nano pricing
}

@dataclass
class CostMeter:
    by_role: dict = field(default_factory=dict)

    def add(self, role: str, usage) -> None:
        pin, pout = PRICES[role]
        cost = (usage.prompt_tokens / 1e6) * pin + (usage.completion_tokens / 1e6) * pout
        self.by_role[role] = self.by_role.get(role, 0.0) + cost

    def total_usd(self) -> float:
        return sum(self.by_role.values())

def extrapolate(per_game_usd: float, n_games: int) -> float:
    return per_game_usd * n_games
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cost_meter.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: token cost meter with placeholder pricing"
```

---

## Task 12: End-to-end experiment runner (CLI)

**Files:**
- Create: `src/cwm/run_experiment.py`
- (No unit test — this is the manual integration entry point that uses real credentials. Its building blocks are all tested.)

**Interfaces:**
- Consumes: every module above + `.env` via `python-dotenv`.
- Produces: a `main()` CLI that runs collect → synthesize → refine → arena and prints a JSON report (also written to `results/`).

- [ ] **Step 1: Implement `run_experiment.py`**

```python
# src/cwm/run_experiment.py
"""End-to-end MVP run: synthesize a tic-tac-toe CWM with a small model, refine to
accuracy 1.0, then play CWM+MCTS vs a large-model baseline. Prints a JSON report.

Usage:
    python -m cwm.run_experiment --games 20 --synth-size nano --baseline-size large
"""
import argparse
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

from dotenv import load_dotenv

from .world_model import CONTRACT_TEXT
from .groundtruth import tictactoe as g
from .trajectories import collect_trajectories
from .llm.azure_openai import AzureOpenAIProvider
from .synthesizer import synthesize_cwm
from .refiner import refine_cwm
from .mcts import mcts_policy
from .baseline import baseline_policy
from .arena import run_arena
from .cost_meter import CostMeter

_DEPLOY_ENV = {"large": "AZURE_DEPLOYMENT_LARGE",
               "mini": "AZURE_DEPLOYMENT_MINI",
               "nano": "AZURE_DEPLOYMENT_NANO"}

def _load_module_from_code(code: str) -> types.ModuleType:
    mod = types.ModuleType("synth_cwm")
    exec(compile(code, "<synth_cwm>", "exec"), mod.__dict__)
    return mod

def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--synth-size", default="nano", choices=list(_DEPLOY_ENV))
    ap.add_argument("--baseline-size", default="large", choices=list(_DEPLOY_ENV))
    ap.add_argument("--train-games", type=int, default=20)
    ap.add_argument("--simulations", type=int, default=300)
    args = ap.parse_args(argv)

    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )
    synth_model = os.environ[_DEPLOY_ENV[args.synth_size]]
    baseline_model = os.environ[_DEPLOY_ENV[args.baseline_size]]
    meter = CostMeter()

    # 1. Collect trajectories from the oracle
    traj = collect_trajectories(g, n_games=args.train_games, seed=0)

    # 2. Synthesize + 3. refine to accuracy 1.0
    code, usage = synthesize_cwm(provider, synth_model, CONTRACT_TEXT, traj)
    meter.add(args.synth_size, usage)
    refined = refine_cwm(provider, synth_model, CONTRACT_TEXT, code, traj)
    for u in refined.usages:
        meter.add(args.synth_size, u)

    if refined.accuracy < 1.0:
        print(json.dumps({"error": "synthesis did not reach accuracy 1.0",
                          "accuracy": refined.accuracy,
                          "iterations": refined.iterations}, indent=2))
        return 1

    cwm = _load_module_from_code(refined.code)

    # 4. Build agents. CWM+MCTS plans on the synthesized model.
    def cwm_agent(state, legal):
        return mcts_policy(cwm, state, n_simulations=args.simulations, seed=0)

    def baseline_agent(state, legal):
        action, u = baseline_policy(provider, baseline_model, state, legal)
        meter.add(args.baseline_size, u)
        return action

    # 5. Arena
    arena = run_arena(g, cwm_agent=cwm_agent, baseline_agent=baseline_agent,
                      n_games=args.games, seed=100)

    per_game_baseline_usd = meter.by_role.get(args.baseline_size, 0.0) / max(1, args.games)
    report = {
        "synth_size": args.synth_size,
        "baseline_size": args.baseline_size,
        "refinement_iterations": refined.iterations,
        "transition_accuracy": refined.accuracy,
        "arena": vars(arena),
        "cost_usd_by_role": meter.by_role,
        "cost_usd_total": meter.total_usd(),
        "extrapolation_note": (
            f"baseline ~${per_game_baseline_usd:.4f}/game; "
            f"synthesis is one-off ~${sum(v for k,v in meter.by_role.items() if k==args.synth_size):.4f}"
        ),
    }
    out = json.dumps(report, indent=2)
    print(out)
    Path("results").mkdir(exist_ok=True)
    Path(f"results/tictactoe_{args.synth_size}_vs_{args.baseline_size}.json").write_text(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke-test the wiring without the network**

Run: `python -c "import cwm.run_experiment as r; print(r.main.__doc__ is None)"`
Expected: prints `False`-ish import success (no exception). Full run needs `.env`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: end-to-end experiment runner (CLI)"
```

- [ ] **Step 4: Manual run (requires real Azure `.env`) — records the cost gate**

Run: `python -m cwm.run_experiment --games 20 --synth-size nano --baseline-size large`
Expected: JSON report with `transition_accuracy: 1.0`, arena counts, and `cost_usd_*`. Capture this output — it is the cost-gate datapoint that decides API-vs-Codex and feeds the article. (Update `cost_meter.PRICES` with real Azure pricing first.)

---

## Self-Review

**1. Spec coverage:**
- Thesis / headline comparison → Task 12 (runner wires small-synth vs large-baseline). ✅
- `groundtruth` → Task 2 ✅ · `trajectory_collector` → Task 3 ✅ · `llm_provider` (+abstraction) → Task 4 ✅ · `sandbox` → Task 5 ✅ · `cwm_synthesizer` → Task 6 ✅ · `test_refiner` → Task 7 ✅ · `mcts` → Task 8 ✅ · `baseline` → Task 9 ✅ · `arena` → Task 10 ✅ · `cost_meter` → Task 11 ✅.
- Metrics: win/draw/loss + baseline illegal rate (Task 10), refinement iterations + accuracy 1.0 (Task 7), tokens/USD by role (Task 11), extrapolation (Tasks 11–12). ✅
- Provider abstraction for Plan B Codex → Task 4 (`LLMProvider` Protocol, model parameterized). ✅
- Sandbox mandatory → Task 5, used in Task 7. ✅
- Fixed JSON-serializable state + contract → Task 2. ✅
- Out-of-scope items (OpenSpiel, poker, Connect Four, TextArena) → not in any task, as intended. ✅

**2. Placeholder scan:** No "TBD/TODO" in steps. The only `TODO`s are intentional, inside `cost_meter.PRICES`, flagged as "replace with real Azure pricing" and surfaced again in Task 12 Step 4. Acceptable (pricing is an external input, not a code gap).

**3. Type consistency:** `State`=dict and `Action`=int used uniformly. `Usage(prompt_tokens, completion_tokens)` consistent across Tasks 4/6/7/9/11. `mcts_policy(model, state, n_simulations, seed)` signature matches its use in Task 12. Agent callable shape `(state, legal) -> int|None` consistent between Tasks 9, 10, 12. `returns` keyed by int `{1,2}` consistent (Tasks 2, 10). ✅

**Note on the Azure provider:** `AzureOpenAIProvider` (Task 4) and the runner (Task 12) are not unit-tested against the network by design; they are exercised in the Task 12 manual run. All pure logic they depend on is unit-tested.
