# Connect Four + Multi-Game Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Generalize the tic-tac-toe MVP to support multiple games via a registry, then add Connect Four (hand-written ground truth) so the same loop (synthesize → refine → MCTS → arena → cost) runs on it. Connect Four is where win-rate genuinely discriminates.

**Architecture:** The pure-logic modules (mcts, sandbox, refiner, trajectories, arena, cost_meter, provider, synthesizer) are already game-agnostic — they take the contract/model/contract-text as parameters. Only three places are hardcoded to tic-tac-toe: `world_model.CONTRACT_TEXT`, `baseline._SYSTEM`, and `run_experiment` (imports tictactoe). We split the contract into a generic API part + per-game rules, introduce a game registry, generalize the baseline prompt, add a Connect Four ground truth, and parameterize the runner with `--game`.

**Tech Stack:** Python 3.11+, pytest. No new dependencies (Connect Four is hand-written; OpenSpiel is deferred to the poker/imperfect-information milestone).

## Global Constraints

- Python 3.11+. TDD throughout (failing test first), frequent commits, `pytest` with `pythonpath=["src"]`.
- State stays `{"board": list[int], "current_player": int}` (1 or 2); `Action = int`. `returns` → `{1: r1, 2: r2}` int keys, values in {-1.0, 0.0, 1.0}, all-zero unless terminal.
- Connect Four representation (FIXED): board is 6 rows × 7 columns = 42 cells, row-major, `index = row*7 + col`, **row 0 = top, row 5 = bottom**. `Action` = column `0..6`; the disc falls to the lowest empty row in that column. Win = 4 in a row horizontally, vertically, or diagonally.
- Synthesized code is executed ONLY in the sandbox during refinement (unchanged).
- Tests never hit a real API (FakeProvider).
- Do not break the existing 47 tests; update the ones that reference `CONTRACT_TEXT` as part of the refactor.

## File Structure

```
src/cwm/
├── world_model.py        # MODIFY: CONTRACT_API (generic) + build_contract(rules) helper; keep State/Action/serialization
├── games.py              # CREATE: GameSpec dataclass + GAMES registry
├── groundtruth/
│   ├── tictactoe.py      # MODIFY: add RULES_TEXT + POLICY_DESCRIPTION
│   └── connect_four.py   # CREATE: contract impl + winner + RULES_TEXT + POLICY_DESCRIPTION
├── baseline.py           # MODIFY: build_policy_messages(state, legal, policy_description); parse_action -> \d+
└── run_experiment.py     # MODIFY: --game {tictactoe,connect4}; load GameSpec from registry
tests/
├── test_tictactoe.py     # unchanged behavior (still implements contract)
├── test_connect_four.py  # CREATE
├── test_games.py         # CREATE: registry wiring
├── test_baseline.py      # MODIFY: pass policy_description; multi-digit parse
├── test_synthesizer.py   # MODIFY: build contract via world_model.build_contract
└── test_refiner.py       # MODIFY: build contract via world_model.build_contract
```

---

## Task 1: Generic contract API + game registry (refactor)

**Files:**
- Modify: `src/cwm/world_model.py`, `src/cwm/groundtruth/tictactoe.py`
- Create: `src/cwm/games.py`, `tests/test_games.py`
- Modify (keep green): `tests/test_synthesizer.py`, `tests/test_refiner.py`

**Interfaces:**
- Produces:
  - `world_model.CONTRACT_API: str` — the generic API contract (functions + State/Action format), no game rules.
  - `world_model.build_contract(rules_text: str) -> str` — returns `CONTRACT_API + "\n\n" + rules_text`.
  - `tictactoe.RULES_TEXT: str`, `tictactoe.POLICY_DESCRIPTION: str`.
  - `games.GameSpec` (frozen dataclass: `name: str`, `module`, `rules_text: str`, `policy_description: str`).
  - `games.GAMES: dict[str, GameSpec]` (initially just `"tictactoe"`).
- Consumes: existing tictactoe contract functions.

- [ ] **Step 1: Write failing tests** `tests/test_games.py`

```python
from cwm.games import GAMES, GameSpec
from cwm.world_model import CONTRACT_API, build_contract

def test_registry_has_tictactoe():
    assert "tictactoe" in GAMES
    spec = GAMES["tictactoe"]
    assert isinstance(spec, GameSpec)
    assert spec.name == "tictactoe"

def test_spec_module_implements_contract():
    m = GAMES["tictactoe"].module
    s = m.initial_state()
    assert s == {"board": [0]*9, "current_player": 1}
    assert m.legal_actions(s) == list(range(9))

def test_build_contract_combines_api_and_rules():
    c = build_contract(GAMES["tictactoe"].rules_text)
    assert "initial_state" in c            # from API
    assert "tic-tac-toe" in c.lower()      # from rules
    assert c.startswith(CONTRACT_API[:20])

def test_policy_description_present():
    assert "tic-tac-toe" in GAMES["tictactoe"].policy_description.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_games.py -v`
Expected: FAIL (cwm.games undefined, CONTRACT_API undefined).

- [ ] **Step 3: Refactor `world_model.py`**

Replace the `CONTRACT_TEXT = """..."""` block with a generic API constant + builder. Keep `State`, `Action`, `state_to_json`, `state_from_json` exactly as they are.

```python
CONTRACT_API = """\
Implement a deterministic turn-based game world model as Python module-level
functions (pure, no I/O, no globals).

State is a dict: {"board": list[int], "current_player": int} (current_player is 1 or 2).
Action is an int.

Functions to implement EXACTLY these signatures:
  def initial_state() -> dict
  def legal_actions(state: dict) -> list[int]
  def apply_action(state: dict, action: int) -> dict   # returns a NEW state; do not mutate input
  def is_terminal(state: dict) -> bool
  def returns(state: dict) -> dict                       # {1: r1, 2: r2}, each in {-1.0,0.0,1.0}; all 0.0 unless terminal

returns gives +1.0 to the winner, -1.0 to the loser, 0.0/0.0 for a draw or any
non-terminal state. Players are 1 and 2 and alternate.
"""

def build_contract(rules_text: str) -> str:
    return CONTRACT_API + "\n\n" + rules_text
```

- [ ] **Step 4: Add rules + policy text to `tictactoe.py`**

Append at the bottom of `src/cwm/groundtruth/tictactoe.py` (keep all existing functions):

```python
RULES_TEXT = """\
This game is tic-tac-toe.
  - board has 9 cells (indices 0..8, row-major over a 3x3 grid): 0 empty, 1 = X, 2 = O.
  - Action is the cell index 0..8 to place the current player's mark.
  - A player wins with 3 of their marks in a row, column, or diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play tic-tac-toe. The board is a list of 9 cells (0 empty, 1=X, 2=O), "
    "indices 0..8 row-major. A move is the cell index 0..8 to play."
)
```

- [ ] **Step 5: Create `src/cwm/games.py`**

```python
"""Registry of supported games."""
from dataclasses import dataclass

from .groundtruth import tictactoe

@dataclass(frozen=True)
class GameSpec:
    name: str
    module: object          # exposes the world-model contract functions
    rules_text: str
    policy_description: str

GAMES = {
    "tictactoe": GameSpec(
        name="tictactoe",
        module=tictactoe,
        rules_text=tictactoe.RULES_TEXT,
        policy_description=tictactoe.POLICY_DESCRIPTION,
    ),
}
```

- [ ] **Step 6: Update tests that imported `CONTRACT_TEXT`**

In `tests/test_synthesizer.py` and `tests/test_refiner.py`, replace `from cwm.world_model import CONTRACT_TEXT` with:
```python
from cwm.world_model import build_contract
from cwm.games import GAMES
```
and replace each use of `CONTRACT_TEXT` with `build_contract(GAMES["tictactoe"].rules_text)`. (Define a module-level `CONTRACT_TEXT = build_contract(GAMES["tictactoe"].rules_text)` at the top of each test file if that minimizes edits — either is fine, as long as the synthesized perfect-code tests still pass.)

- [ ] **Step 7: Run the full suite**

Run: `pytest -q`
Expected: all pass (the 4 new test_games tests + existing suite, with the two test files updated). If the perfect-code refiner test fails, confirm the contract text still describes the tic-tac-toe rules via `build_contract`.

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "refactor: split contract into generic API + per-game rules; add game registry"
```

---

## Task 2: Generalize the baseline agent

**Files:**
- Modify: `src/cwm/baseline.py`, `tests/test_baseline.py`

**Interfaces:**
- Produces: `build_policy_messages(state, legal, policy_description) -> list[dict]`; `parse_action(text) -> int | None` (now `\d+`); `baseline_policy(provider, model, state, legal, policy_description) -> tuple[int | None, Usage]`.
- Consumes: `games.GameSpec.policy_description`.

- [ ] **Step 1: Update failing tests** `tests/test_baseline.py`

Adjust calls to pass a `policy_description` and add a multi-digit parse test:

```python
from cwm.baseline import build_policy_messages, parse_action, baseline_policy
from cwm.llm.provider import FakeProvider

DESC = "You play a test game. A move is an integer."

def test_parse_plain_int():
    assert parse_action("4") == 4

def test_parse_multi_digit():
    assert parse_action("I'll play column 12") == 12

def test_parse_from_sentence():
    assert parse_action("cell 7 please") == 7

def test_parse_none_when_absent():
    assert parse_action("no number here") is None

def test_messages_include_description_and_legal():
    msgs = build_policy_messages({"board": [0]*9, "current_player": 1}, [0, 1, 2], DESC)
    blob = " ".join(m["content"] for m in msgs)
    assert "[0, 1, 2]" in blob
    assert "test game" in blob

def test_baseline_returns_action_and_usage():
    fake = FakeProvider(["I choose 3"])
    action, usage = baseline_policy(fake, "large",
                                    {"board": [0]*9, "current_player": 1}, [3, 4], DESC)
    assert action == 3 and usage.completion_tokens > 0

def test_baseline_illegal_returns_none():
    fake = FakeProvider(["I choose 8"])
    action, _ = baseline_policy(fake, "large",
                                {"board": [0]*9, "current_player": 1}, [3, 4], DESC)
    assert action is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_baseline.py -v`
Expected: FAIL (signature mismatch / multi-digit).

- [ ] **Step 3: Update `baseline.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_baseline.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: make baseline agent game-agnostic (policy_description, multi-digit parse)"
```

---

## Task 3: Connect Four ground truth

**Files:**
- Create: `src/cwm/groundtruth/connect_four.py`, `tests/test_connect_four.py`

**Interfaces:**
- Produces: module-level `initial_state`, `legal_actions`, `apply_action`, `is_terminal`, `returns`, `winner` matching the contract; plus `RULES_TEXT` and `POLICY_DESCRIPTION`.

- [ ] **Step 1: Write failing tests** `tests/test_connect_four.py`

```python
from cwm.groundtruth import connect_four as c

def test_initial_state():
    s = c.initial_state()
    assert s == {"board": [0]*42, "current_player": 1}

def test_legal_actions_all_columns():
    assert c.legal_actions(c.initial_state()) == [0, 1, 2, 3, 4, 5, 6]

def test_gravity_drop_to_bottom():
    s = c.apply_action(c.initial_state(), 3)
    # bottom row is row 5 -> index 5*7+3 = 38
    assert s["board"][38] == 1
    assert s["current_player"] == 2

def test_stacking_in_column():
    s = c.initial_state()
    s = c.apply_action(s, 3)   # P1 -> row5 col3 (idx38)
    s = c.apply_action(s, 3)   # P2 -> row4 col3 (idx31)
    assert s["board"][38] == 1 and s["board"][31] == 2

def test_apply_action_is_pure():
    s = c.initial_state()
    c.apply_action(s, 0)
    assert s["board"] == [0]*42

def test_vertical_win():
    s = c.initial_state()
    # P1 stacks col0 four times; P2 plays col1 between
    for col in [0, 1, 0, 1, 0, 1, 0]:
        s = c.apply_action(s, col)
    assert c.winner(s) == 1
    assert c.is_terminal(s) is True
    assert c.returns(s) == {1: 1.0, 2: -1.0}

def test_horizontal_win():
    s = c.initial_state()
    # P1 plays cols 0,1,2,3 on bottom row; P2 plays col6 area on bottom (won't make 4)
    for col in [0, 6, 1, 6, 2, 5, 3]:
        s = c.apply_action(s, col)
    assert c.winner(s) == 1

def test_diagonal_win():
    s = c.initial_state()
    # Build an ascending diagonal for P1: (r5,c0),(r4,c1),(r3,c2),(r2,c3)
    # Move sequence engineered so P1 occupies the diagonal; verify winner==1.
    moves = [0,   # P1 r5c0
             1,   # P2 r5c1
             1,   # P1 r4c1
             2,   # P2 r5c2
             3,   # P1 r5c3 (filler, not diagonal yet)
             2,   # P2 r4c2
             2,   # P1 r3c2
             3,   # P2 r4c3
             6,   # P1 filler r5c6
             3,   # P2 r3c3
             3]   # P1 r2c3  -> completes diagonal (r5c0,r4c1,r3c2,r2c3)
    for m in moves:
        s = c.apply_action(s, m)
    assert c.winner(s) == 1

def test_legal_excludes_full_column():
    s = c.initial_state()
    for _ in range(6):           # fill column 0 (6 rows)
        s = c.apply_action(s, 0)
    assert 0 not in c.legal_actions(s)

def test_returns_nonterminal_is_zero():
    assert c.returns(c.initial_state()) == {1: 0.0, 2: 0.0}
```

> Note for the implementer: the win-sequence tests are hand-constructed. If any sequence does not actually produce the claimed win (verify by running), FIX the move sequence so the test genuinely asserts that win type — do NOT weaken the assertion or the implementation to match a wrong sequence.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_connect_four.py -v`
Expected: FAIL (module undefined).

- [ ] **Step 3: Implement `connect_four.py`**

```python
"""Hand-written Connect Four oracle implementing the world_model contract.

board: list[int] length 42, row-major, index = row*7 + col, row 0 = top, row 5 = bottom.
0 empty, 1 and 2 are the players. Action = column 0..6; disc falls to lowest empty row.
"""

ROWS, COLS = 6, 7

def _idx(r: int, c: int) -> int:
    return r * COLS + c

def initial_state() -> dict:
    return {"board": [0] * (ROWS * COLS), "current_player": 1}

def _drop_row(board: list, col: int):
    for r in range(ROWS - 1, -1, -1):      # bottom (row 5) upward
        if board[_idx(r, col)] == 0:
            return r
    return None

def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    return [col for col in range(COLS) if state["board"][_idx(0, col)] == 0]

def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    r = _drop_row(board, action)
    board[_idx(r, action)] = state["current_player"]
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}

def winner(state: dict) -> int:
    b = state["board"]
    for r in range(ROWS):
        for col in range(COLS):
            p = b[_idx(r, col)]
            if p == 0:
                continue
            # horizontal →
            if col + 3 < COLS and all(b[_idx(r, col + k)] == p for k in range(4)):
                return p
            # vertical ↓
            if r + 3 < ROWS and all(b[_idx(r + k, col)] == p for k in range(4)):
                return p
            # diagonal ↘
            if r + 3 < ROWS and col + 3 < COLS and all(b[_idx(r + k, col + k)] == p for k in range(4)):
                return p
            # diagonal ↙
            if r + 3 < ROWS and col - 3 >= 0 and all(b[_idx(r + k, col - k)] == p for k in range(4)):
                return p
    return 0

def is_terminal(state: dict) -> bool:
    return winner(state) != 0 or all(cell != 0 for cell in state["board"])

def returns(state: dict) -> dict:
    w = winner(state)
    if w == 1:
        return {1: 1.0, 2: -1.0}
    if w == 2:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}

RULES_TEXT = """\
This game is Connect Four.
  - board has 42 cells representing a 6-row x 7-column grid, row-major:
    index = row*7 + col, with row 0 the TOP row and row 5 the BOTTOM row.
    0 empty, 1 and 2 are the two players' discs.
  - Action is a COLUMN index 0..6. The disc falls to the LOWEST empty row in
    that column (gravity). A column is a legal move only if its top cell
    (row 0) is empty.
  - A player wins with 4 of their discs in a line: horizontal, vertical, or
    either diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play Connect Four on a 6-row by 7-column board (42 cells, row-major, "
    "0 empty, 1 and 2 are the players). A move is a COLUMN number 0..6; your "
    "disc falls to the lowest empty row in that column."
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_connect_four.py -v`
Expected: PASS (10 tests). If a win-sequence test fails, first verify the sequence is correct by hand; fix the SEQUENCE, not the oracle (unless the oracle has a genuine bug).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Connect Four ground truth (gravity, 4-in-a-row, rules text)"
```

---

## Task 4: Register Connect Four + parameterize the runner

**Files:**
- Modify: `src/cwm/games.py`, `tests/test_games.py`, `src/cwm/run_experiment.py`

**Interfaces:**
- Produces: `GAMES["connect4"]`; runner `--game {tictactoe,connect4}` selecting the GameSpec and using its module (referee), `build_contract(rules_text)` (synthesis), and `policy_description` (baseline).

- [ ] **Step 1: Add failing registry test** to `tests/test_games.py`

```python
def test_registry_has_connect4():
    from cwm.games import GAMES
    spec = GAMES["connect4"]
    assert spec.name == "connect4"
    s = spec.module.initial_state()
    assert s == {"board": [0]*42, "current_player": 1}
    assert "connect four" in spec.policy_description.lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_games.py::test_registry_has_connect4 -v`
Expected: FAIL (KeyError 'connect4').

- [ ] **Step 3: Register Connect Four** in `src/cwm/games.py`

```python
from .groundtruth import tictactoe, connect_four
```
and add to `GAMES`:
```python
    "connect4": GameSpec(
        name="connect4",
        module=connect_four,
        rules_text=connect_four.RULES_TEXT,
        policy_description=connect_four.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 4: Parameterize `run_experiment.py`**

Replace the hardcoded `from .groundtruth import tictactoe as g` and `CONTRACT_TEXT` usage with registry-driven selection:
- Add import: `from .games import GAMES` and `from .world_model import build_contract`.
- Add CLI arg: `ap.add_argument("--game", default="tictactoe", choices=list(GAMES))`.
- After parsing: `spec = GAMES[args.game]`, `g = spec.module`, `contract = build_contract(spec.rules_text)`.
- Pass `contract` to `synthesize_cwm(...)` and `refine_cwm(...)` (instead of `CONTRACT_TEXT`).
- The baseline agent must pass the description:
```python
    def baseline_agent(state, legal):
        action, u = baseline_policy(provider, baseline_model, state, legal, spec.policy_description)
        meter.add(args.baseline_size, u)
        return action
```
- Include `"game": args.game` in the report dict, and write results to `results/{args.game}_{synth}_vs_{baseline}.json`.

- [ ] **Step 5: Verify (no full run)**

Run: `pytest -q` (expect all green) and:
`python -c "import cwm.run_experiment as r; print('ok')"` and
`python -m cwm.run_experiment --help` (confirm `--game` with choices tictactoe, connect4).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: register Connect Four and add --game selector to the runner"
```

---

## Self-Review

**1. Spec coverage:** Multi-game registry (Task 1), generic contract split (Task 1), generalized baseline (Task 2), Connect Four ground truth (Task 3), runner `--game` (Task 4). Pure-logic modules unchanged (synthesizer/refiner already take contract as a parameter; mcts/arena/sandbox/cost_meter game-agnostic). ✅
**2. Placeholder scan:** No TBD/TODO; all code is concrete. ✅
**3. Type consistency:** `build_contract(rules_text)->str`, `GameSpec(name, module, rules_text, policy_description)`, `build_policy_messages(state, legal, policy_description)`, `baseline_policy(..., policy_description)` consistent across tasks and the runner wiring. ✅

## Post-build: evaluation runs (not code tasks)

After Task 4, run on Connect Four (controller executes; needs `.env`):
- `python -m cwm.run_experiment --game connect4 --games 30 --synth-size mini --baseline-size large --simulations 400 --seed 7`
- `python -m cwm.run_experiment --game connect4 --games 30 --synth-size nano --baseline-size large --simulations 400 --seed 7`
Connect Four needs deeper search than tic-tac-toe; start at `--simulations 400` and raise if CWM play looks weak. Capture win/draw/loss, baseline illegal rate, refinement iterations, and real cost.
