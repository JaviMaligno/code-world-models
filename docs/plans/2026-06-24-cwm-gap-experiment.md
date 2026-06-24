# CWM Verified-vs-Correct Gap Experiment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a game-agnostic harness that measures the gap between a world
model's gate accuracy (random-trajectory transitions) and its correctness on the
distribution MCTS actually visits, then run it across three knowledge regimes.

**Architecture:** Add a visited-state hook to MCTS; add `gap.py` (state collection
+ CWM-vs-ground-truth divergence in the sandbox); add three ground-truth games
(Gen-TTT 6×6, army5x5a, Trike); add a non-triviality sweep; add a `run_gap.py`
orchestrator that synthesizes + refines a CWM and reports the gap per regime.

**Tech Stack:** Python 3, pytest, existing `cwm` package (sandbox subprocess,
Azure OpenAI provider), no new dependencies.

## Global Constraints

- State is a dict `{"board": list[int], "current_player": int}`, `current_player ∈ {1, 2}`. Action is an `int`.
- World-model contract functions: `initial_state()`, `legal_actions(state)`, `apply_action(state, action)` (returns a NEW state, never mutates input), `is_terminal(state)`, `returns(state)`.
- `returns(state)` is `{1: r1, 2: r2}`, each in `{-1.0, 0.0, 1.0}`; all `0.0` unless terminal; winner `+1.0`, loser `-1.0`, draw `0.0/0.0`.
- Generated/untrusted code that is only inspected (not planned on) runs in the subprocess sandbox via `cwm.sandbox.run_in_sandbox`. Embed input data with the hardened pattern `json.loads({json.dumps(json.dumps(data))})`.
- Each new game module exposes the contract functions plus `RULES_TEXT` and `POLICY_DESCRIPTION`, and is registered in `src/cwm/games.py`.
- New games follow the style of `src/cwm/groundtruth/connect_four.py` (module-level constants, `_idx`/helpers, pure functions).
- `results/` is git-ignored; the orchestrator writes JSON reports there.
- Any runner that reads Azure env vars calls `load_dotenv(override=True)` first (the experiment's `.env` must beat inherited shell `AZURE_*` vars).

---

### Task 1: MCTS visited-state hook

**Files:**
- Modify: `src/cwm/mcts.py`
- Test: `tests/test_mcts.py`

**Interfaces:**
- Consumes: existing `cwm.world_model.state_to_json`.
- Produces: `mcts_policy(model, state, n_simulations=200, seed=0, visited=None)` — when `visited` is a `set`, it receives `state_to_json` of the root and every expanded child node. Default `None` leaves behavior unchanged.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_mcts.py`:

```python
def test_visited_collects_tree_states():
    from cwm.mcts import mcts_policy
    from cwm.groundtruth import tictactoe as g
    visited = set()
    mcts_policy(g, g.initial_state(), n_simulations=50, seed=1, visited=visited)
    assert len(visited) > 1  # root plus expanded children

def test_visited_default_none_unchanged():
    from cwm.mcts import mcts_policy
    from cwm.groundtruth import tictactoe as g
    a = mcts_policy(g, g.initial_state(), n_simulations=50, seed=1)
    assert a in g.legal_actions(g.initial_state())
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mcts.py::test_visited_collects_tree_states -v`
Expected: FAIL (`mcts_policy() got an unexpected keyword argument 'visited'`)

- [ ] **Step 3: Implement the hook** — edit `src/cwm/mcts.py`. Add the import near the top:

```python
from .world_model import state_to_json
```

Change the `mcts_policy` signature and add the two `visited.add(...)` calls:

```python
def mcts_policy(model, state: dict, n_simulations: int = 200, seed: int = 0,
                visited: set | None = None) -> int:
    rng = random.Random(seed)
    root = _Node(model, state)
    if visited is not None:
        visited.add(state_to_json(state))
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
            if visited is not None:
                visited.add(state_to_json(child.state))
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

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mcts.py -v`
Expected: PASS (all tests, old and new)

- [ ] **Step 5: Commit**

```bash
git add src/cwm/mcts.py tests/test_mcts.py
git commit -m "feat(mcts): optional visited-state hook for gap measurement"
```

---

### Task 2: Divergence comparison (`contract_divergence`)

**Files:**
- Create: `src/cwm/gap.py`
- Test: `tests/test_gap.py`

**Interfaces:**
- Consumes: `cwm.sandbox.run_in_sandbox`.
- Produces:
  - `DivergenceReport` dataclass: fields `n_states:int`, `n_pairs:int`, `legal_rate:float`, `terminal_rate:float`, `returns_rate:float`, `transition_rate:float`, `state_agreement_rate:float`, `examples:list[str]`.
  - `contract_divergence(cwm_code: str, states: list[dict], truth_module, timeout: float = 10.0) -> DivergenceReport` — compares the sandboxed CWM against `truth_module` (run in-process) on `states`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_gap.py`:

```python
import inspect
from cwm.gap import contract_divergence
from cwm.groundtruth import tictactoe

_STATES = [
    tictactoe.initial_state(),
    {"board": [1, 1, 0, 2, 2, 0, 0, 0, 0], "current_player": 1},
    {"board": [1, 1, 1, 2, 2, 0, 0, 0, 0], "current_player": 2},  # terminal, P1 wins
]

def test_identical_module_has_no_gap():
    src = inspect.getsource(tictactoe)
    rep = contract_divergence(src, _STATES, tictactoe)
    assert rep.state_agreement_rate == 1.0
    assert rep.legal_rate == 1.0
    assert rep.transition_rate == 1.0

def test_corrupted_module_is_detected():
    src = inspect.getsource(tictactoe)
    bad = src.replace("b[x] == b[y] == b[z]", "False")  # never detects a win
    rep = contract_divergence(bad, _STATES, tictactoe)
    assert rep.state_agreement_rate < 1.0
    assert rep.examples  # at least one mismatch surfaced

def test_empty_states_is_safe():
    src = inspect.getsource(tictactoe)
    rep = contract_divergence(src, [], tictactoe)
    assert rep.n_states == 0
    assert rep.state_agreement_rate == 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gap.py -v`
Expected: FAIL (`No module named 'cwm.gap'`)

- [ ] **Step 3: Implement `contract_divergence`** — create `src/cwm/gap.py`:

```python
"""Measure where a synthesized world model diverges from the ground truth.

contract_divergence compares the sandboxed CWM against the ground-truth module on
a set of states, across legal_actions / is_terminal / returns / apply_action.
collect_visited_states gathers the states MCTS expands while planning on a model.
"""
import json
from dataclasses import dataclass, field

from .sandbox import run_in_sandbox


@dataclass
class DivergenceReport:
    n_states: int
    n_pairs: int
    legal_rate: float
    terminal_rate: float
    returns_rate: float
    transition_rate: float
    state_agreement_rate: float
    examples: list = field(default_factory=list)


def _truth_expectations(states, truth_module):
    """Compute ground-truth outputs in-process. Returns (truth_list, cases)."""
    truth, cases = [], []
    for s in states:
        try:
            legal = sorted(truth_module.legal_actions(s))
        except Exception as e:
            legal = {"__error__": repr(e)}
        term = _safe(lambda: truth_module.is_terminal(s))
        ret = _safe(lambda: {str(k): v for k, v in truth_module.returns(s).items()})
        nexts = {}
        if isinstance(legal, list):
            for a in legal:
                nexts[str(a)] = _safe(lambda a=a: truth_module.apply_action(s, a))
        truth.append({"legal": legal, "terminal": term, "returns": ret, "nexts": nexts})
        cases.append({"state": s, "actions": legal if isinstance(legal, list) else []})
    return truth, cases


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # truth raising on an impossible state is itself a signal
        return {"__error__": repr(e)}


_CALL = (
    "import json\n"
    "_cases = json.loads({payload})\n"
    "_out = []\n"
    "for _c in _cases:\n"
    "    _s = _c['state']\n"
    "    _r = {{}}\n"
    "    try:\n"
    "        _r['legal'] = sorted(legal_actions(_s))\n"
    "    except Exception as e:\n"
    "        _r['legal'] = {{'__error__': repr(e)}}\n"
    "    try:\n"
    "        _r['terminal'] = is_terminal(_s)\n"
    "    except Exception as e:\n"
    "        _r['terminal'] = {{'__error__': repr(e)}}\n"
    "    try:\n"
    "        _r['returns'] = returns(_s)\n"
    "    except Exception as e:\n"
    "        _r['returns'] = {{'__error__': repr(e)}}\n"
    "    _nx = {{}}\n"
    "    for _a in _c['actions']:\n"
    "        try:\n"
    "            _nx[str(_a)] = apply_action(_s, _a)\n"
    "        except Exception as e:\n"
    "            _nx[str(_a)] = {{'__error__': repr(e)}}\n"
    "    _r['nexts'] = _nx\n"
    "    _out.append(_r)\n"
    "print(json.dumps(_out))\n"
)


def contract_divergence(cwm_code: str, states: list, truth_module,
                        timeout: float = 10.0) -> DivergenceReport:
    if not states:
        return DivergenceReport(0, 0, 1.0, 1.0, 1.0, 1.0, 1.0, [])
    truth, cases = _truth_expectations(states, truth_module)
    payload = json.dumps(json.dumps(cases))
    res = run_in_sandbox(cwm_code, _CALL.format(payload=payload), timeout=timeout)
    if not res.ok:
        return DivergenceReport(len(states), 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                [res.stderr.strip()[-300:] or "sandbox failed"])
    lines = res.stdout.strip().splitlines()
    try:
        produced = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        produced = None
    if not isinstance(produced, list) or len(produced) != len(states):
        return DivergenceReport(len(states), 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                ["malformed sandbox output"])

    legal_ok = term_ok = ret_ok = states_ok = 0
    pairs = pairs_ok = 0
    examples = []
    for st, tr, got in zip(states, truth, produced):
        l_ok = got.get("legal") == tr["legal"]
        t_ok = got.get("terminal") == tr["terminal"]
        r_ok = got.get("returns") == tr["returns"]
        trans_ok = True
        for a_str, exp in tr["nexts"].items():
            pairs += 1
            if got.get("nexts", {}).get(a_str) == exp:
                pairs_ok += 1
            else:
                trans_ok = False
        legal_ok += l_ok
        term_ok += t_ok
        ret_ok += r_ok
        if l_ok and t_ok and r_ok and trans_ok:
            states_ok += 1
        elif len(examples) < 10:
            examples.append(
                f"state={st} legal_ok={l_ok} terminal_ok={t_ok} "
                f"returns_ok={r_ok} transitions_ok={trans_ok}")
    n = len(states)
    return DivergenceReport(
        n_states=n, n_pairs=pairs,
        legal_rate=legal_ok / n, terminal_rate=term_ok / n,
        returns_rate=ret_ok / n,
        transition_rate=(pairs_ok / pairs) if pairs else 1.0,
        state_agreement_rate=states_ok / n, examples=examples)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_gap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/gap.py tests/test_gap.py
git commit -m "feat(gap): CWM-vs-ground-truth divergence in the sandbox"
```

---

### Task 3: Visited-state collection (`collect_visited_states`)

**Files:**
- Modify: `src/cwm/gap.py`
- Test: `tests/test_gap.py`

**Interfaces:**
- Consumes: `cwm.mcts.mcts_policy(..., visited=...)` (Task 1); `cwm.world_model.state_to_json` / `state_from_json`.
- Produces: `collect_visited_states(model, n_games, simulations, seed, cap=20000) -> list[dict]` — self-plays `model` vs itself with MCTS, accumulating a deduped set of the states MCTS expands; returns them as a list, truncated at `cap`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_gap.py`:

```python
def test_collect_visited_states_basic():
    from cwm.gap import collect_visited_states
    from cwm.groundtruth import tictactoe
    states = collect_visited_states(tictactoe, n_games=2, simulations=30, seed=1)
    assert len(states) > 1
    assert all(set(s.keys()) == {"board", "current_player"} for s in states)

def test_collect_visited_states_respects_cap():
    from cwm.gap import collect_visited_states
    from cwm.groundtruth import tictactoe
    states = collect_visited_states(tictactoe, n_games=5, simulations=80, seed=1, cap=10)
    assert len(states) <= 10
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gap.py::test_collect_visited_states_basic -v`
Expected: FAIL (`cannot import name 'collect_visited_states'`)

- [ ] **Step 3: Implement** — add to the top imports of `src/cwm/gap.py`:

```python
import random
import sys

from .mcts import mcts_policy
from .world_model import state_from_json
```

Append the function to `src/cwm/gap.py`:

```python
def collect_visited_states(model, n_games: int, simulations: int, seed: int,
                           cap: int = 20000) -> list:
    """States MCTS expands while self-playing `model` against itself."""
    visited: set = set()
    for g in range(n_games):
        state = model.initial_state()
        move = 0
        while not model.is_terminal(state):
            a = mcts_policy(model, state, n_simulations=simulations,
                            seed=seed + g * 1000 + move, visited=visited)
            state = model.apply_action(state, a)
            move += 1
            if len(visited) >= cap:
                break
        if len(visited) >= cap:
            print(f"collect_visited_states: hit cap {cap}; stopping early",
                  file=sys.stderr)
            break
    return [state_from_json(s) for s in list(visited)[:cap]]
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_gap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/gap.py tests/test_gap.py
git commit -m "feat(gap): collect MCTS-visited states via self-play"
```

---

### Task 4: Gen-TTT 6×6 win-4 ground truth (correct-prior regime)

**Files:**
- Create: `src/cwm/groundtruth/gen_tictactoe.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_gen_tictactoe.py`

**Interfaces:**
- Produces: a contract module with constants `ROWS=6`, `COLS=6`, `K=4`, plus `RULES_TEXT`/`POLICY_DESCRIPTION`; registered as `"gen_tictactoe"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_gen_tictactoe.py`:

```python
from cwm.groundtruth import gen_tictactoe as g

def test_initial_state():
    assert g.initial_state() == {"board": [0] * 36, "current_player": 1}

def test_legal_actions_all_empty():
    assert g.legal_actions(g.initial_state()) == list(range(36))

def test_apply_action_is_pure():
    s = g.initial_state()
    g.apply_action(s, 0)
    assert s["board"] == [0] * 36

def test_horizontal_win_needs_four():
    b = [0] * 36
    for c in range(4):
        b[c] = 1  # row 0, cols 0..3
    assert g.winner({"board": b, "current_player": 2}) == 1

def test_three_in_a_row_does_not_win():
    b = [0] * 36
    for c in range(3):
        b[c] = 1
    assert g.winner({"board": b, "current_player": 2}) == 0

def test_vertical_win():
    b = [0] * 36
    for r in range(4):
        b[r * 6] = 2  # col 0, rows 0..3
    assert g.winner({"board": b, "current_player": 1}) == 2

def test_diagonal_win():
    b = [0] * 36
    for k in range(4):
        b[k * 6 + k] = 1  # (0,0),(1,1),(2,2),(3,3)
    s = {"board": b, "current_player": 2}
    assert g.winner(s) == 1
    assert g.is_terminal(s) is True
    assert g.returns(s) == {1: 1.0, 2: -1.0}

def test_anti_diagonal_win():
    b = [0] * 36
    for k in range(4):
        b[k * 6 + (3 - k)] = 1  # (0,3),(1,2),(2,1),(3,0)
    assert g.winner({"board": b, "current_player": 2}) == 1

def test_returns_nonterminal_is_zero():
    assert g.returns(g.initial_state()) == {1: 0.0, 2: 0.0}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gen_tictactoe.py -v`
Expected: FAIL (`No module named 'cwm.groundtruth.gen_tictactoe'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/gen_tictactoe.py`:

```python
"""Generalized tic-tac-toe (m,n,k) oracle: 6x6 board, 4-in-a-row.

board: list[int] length ROWS*COLS, row-major, index = row*COLS + col.
0 empty, 1 and 2 are the players. Action = empty cell index.
"""

ROWS, COLS, K = 6, 6, 4
_DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))


def _idx(r: int, c: int) -> int:
    return r * COLS + c


def initial_state() -> dict:
    return {"board": [0] * (ROWS * COLS), "current_player": 1}


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
    for r in range(ROWS):
        for c in range(COLS):
            p = b[_idx(r, c)]
            if p == 0:
                continue
            for dr, dc in _DIRS:
                rr, cc = r + (K - 1) * dr, c + (K - 1) * dc
                if 0 <= rr < ROWS and 0 <= cc < COLS and all(
                        b[_idx(r + k * dr, c + k * dc)] == p for k in range(K)):
                    return p
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


RULES_TEXT = """\
This game is generalized tic-tac-toe on a 6x6 board, win with 4 in a row.
  - board has 36 cells (indices 0..35, row-major over a 6x6 grid,
    index = row*6 + col): 0 empty, 1 and 2 are the two players.
  - current_player is 1 or 2; players alternate, placing their own mark in any
    empty cell.
  - Action is the cell index 0..35 to place the current player's mark.
  - A player wins with 4 of their marks in a row, column, or either diagonal.
  - The board full with no winner is a draw.
"""

POLICY_DESCRIPTION = (
    "You play generalized tic-tac-toe on a 6x6 board (36 cells, row-major, "
    "0 empty, 1 and 2 are the players), winning with 4 in a row. A move is an "
    "empty cell index 0..35.")
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — change the import line and add the entry:

```python
from .groundtruth import tictactoe, connect_four, gen_tictactoe
```

Add to the `GAMES` dict:

```python
    "gen_tictactoe": GameSpec(
        name="gen_tictactoe",
        module=gen_tictactoe,
        rules_text=gen_tictactoe.RULES_TEXT,
        policy_description=gen_tictactoe.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_gen_tictactoe.py tests/test_games.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cwm/groundtruth/gen_tictactoe.py src/cwm/games.py tests/test_gen_tictactoe.py
git commit -m "feat(games): generalized tic-tac-toe 6x6 win-4 (correct-prior regime)"
```

---

### Task 5: army5x5a ground truth (no-prior regime)

**Files:**
- Create: `src/cwm/groundtruth/gen_chess.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_gen_chess.py`

**Interfaces:**
- Produces: a contract module. `board` is **26** ints (cells 0..24 + ply counter at index 25). Constants `SIZE=5`, `N=25`, `PASS=625`, `MAX_PLIES=100`, `MIRROR_PLAYER2=True`. Registered as `"army5x5a"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_gen_chess.py`:

```python
from cwm.groundtruth import gen_chess as g

def test_initial_state_layout():
    s = g.initial_state()
    assert len(s["board"]) == 26
    assert s["board"][0:5] == [3, 2, 1, 2, 3]      # rank A: P1
    assert s["board"][20:25] == [6, 5, 4, 5, 6]    # rank E: P2
    assert s["board"][25] == 0                      # ply counter
    assert s["current_player"] == 1

def test_p1_infantry_move_present():
    # infantry at index 1 (row0,col1): (1,0)->idx6 => action 1*25+6 = 31
    assert 31 in g.legal_actions(g.initial_state())

def test_apply_action_is_pure_and_increments_plies():
    s = g.initial_state()
    before = list(s["board"])
    ns = g.apply_action(s, 31)
    assert s["board"] == before            # input unchanged
    assert ns["board"][25] == 1            # ply incremented
    assert ns["current_player"] == 2

def test_capture_general_wins():
    board = [0] * 25 + [0]
    board[12] = 1   # P1 general at (2,2)
    board[13] = 4   # P2 general at (2,3)
    s = {"board": board, "current_player": 1}
    assert g.is_terminal(s) is False
    action = 12 * 25 + 13            # general (0,1): (2,2)->(2,3) captures
    assert action in g.legal_actions(s)
    ns = g.apply_action(s, action)
    assert ns["board"][13] == 1 and ns["board"][12] == 0
    assert g.is_terminal(ns) is True
    assert g.returns(ns) == {1: 1.0, 2: -1.0}

def test_mirrored_player2_infantry_moves_up():
    # P2 infantry at idx22 (row4,col2); mirrored (-1,0)->(3,2)=idx17 => 22*25+17=567
    board = [0] * 25 + [0]
    board[0] = 1     # P1 general
    board[24] = 4    # P2 general
    board[22] = 5    # P2 infantry
    s = {"board": board, "current_player": 2}
    assert 567 in g.legal_actions(s)

def test_ply_cap_is_a_draw():
    board = [0] * 25 + [99]
    board[2] = 1     # P1 general (so both generals alive)
    board[22] = 4    # P2 general
    s = {"board": board, "current_player": 1}
    legal = g.legal_actions(s)
    assert legal  # at least one move exists
    ns = g.apply_action(s, legal[0])
    assert ns["board"][25] == 100
    assert g.is_terminal(ns) is True
    assert g.returns(ns) == {1: 0.0, 2: 0.0}

def test_pass_not_offered_when_moves_exist():
    # A lone general always has at least one move on a 5x5 board, so PASS (625)
    # must NOT be offered. PASS is only added when a side has no piece move.
    board = [0] * 25 + [0]
    board[0] = 1     # P1 general at (0,0)
    board[24] = 4    # P2 general
    s = {"board": board, "current_player": 1}
    legal = g.legal_actions(s)
    assert legal and g.PASS not in legal
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gen_chess.py -v`
Expected: FAIL (`No module named 'cwm.groundtruth.gen_chess'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/gen_chess.py`:

```python
"""army5x5a generalized-chess oracle (DeepMind arXiv:2510.04542, Appendix H.5).

board: list[int] length 26. Indices 0..24 are the 5x5 cells (index = row*5 + col,
row 0 = rank A top .. row 4 = rank E bottom, col 0 = file 1 left). Index 25 is the
ply counter (half-moves played, starts at 0). Cell values: 0 empty; player 1:
1 general, 2 infantry, 3 cavalry; player 2: 4 general, 5 infantry, 6 cavalry.
Win by capturing the opponent's general. Action = from*25 + to, or PASS = 625.
"""

SIZE = 5
N = SIZE * SIZE          # 25 cells
PASS = N * N             # 625
MAX_PLIES = 100
MIRROR_PLAYER2 = True

_MOVES = {
    "general":  [(1, 0), (-1, 0), (0, 1), (0, -1), (0, -2), (0, 2)],
    "infantry": [(1, 0), (2, 0), (1, -1), (1, 1), (-1, 0)],
    "cavalry":  [(0, 3), (1, 2), (2, 1), (3, 0)],
}
_KIND = {1: "general", 2: "infantry", 3: "cavalry",
         4: "general", 5: "infantry", 6: "cavalry"}
_OWNER = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2}
_GENERAL_VAL = {1: 1, 2: 4}


def _offsets(value: int):
    offs = _MOVES[_KIND[value]]
    if MIRROR_PLAYER2 and _OWNER[value] == 2:
        return [(-dr, dc) for dr, dc in offs]
    return offs


def initial_state() -> dict:
    board = [0] * N + [0]
    board[0:5] = [3, 2, 1, 2, 3]      # rank A (row 0): player 1
    board[20:25] = [6, 5, 4, 5, 6]    # rank E (row 4): player 2
    return {"board": board, "current_player": 1}


def _piece_dests(board: list, idx: int) -> list:
    value = board[idx]
    r, c = divmod(idx, SIZE)
    dests = []
    for dr, dc in _offsets(value):
        rr, cc = r + dr, c + dc
        if 0 <= rr < SIZE and 0 <= cc < SIZE:
            tgt = rr * SIZE + cc
            if board[tgt] == 0 or _OWNER[board[tgt]] != _OWNER[value]:
                dests.append(tgt)
    return dests


def legal_actions(state: dict) -> list[int]:
    if is_terminal(state):
        return []
    board = state["board"]
    player = state["current_player"]
    actions = []
    for idx in range(N):
        v = board[idx]
        if v != 0 and _OWNER[v] == player:
            for tgt in _piece_dests(board, idx):
                actions.append(idx * N + tgt)
    if not actions:
        actions.append(PASS)
    return actions


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    player = state["current_player"]
    if action != PASS:
        frm, to = divmod(action, N)
        board[to] = board[frm]
        board[frm] = 0
    board[N] += 1
    return {"board": board, "current_player": 2 if player == 1 else 1}


def _general_alive(board: list, player: int) -> bool:
    return _GENERAL_VAL[player] in board[:N]


def is_terminal(state: dict) -> bool:
    board = state["board"]
    if not _general_alive(board, 1) or not _general_alive(board, 2):
        return True
    return board[N] >= MAX_PLIES


def returns(state: dict) -> dict:
    if not is_terminal(state):
        return {1: 0.0, 2: 0.0}
    board = state["board"]
    a1, a2 = _general_alive(board, 1), _general_alive(board, 2)
    if a1 and not a2:
        return {1: 1.0, 2: -1.0}
    if a2 and not a1:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}


RULES_TEXT = """\
This game is 'army5x5a', a generalized-chess variant on a 5x5 board.
  - board has 26 integers: indices 0..24 are the 25 cells (index = row*5 + col,
    row 0 = top rank, row 4 = bottom rank, col 0 = left file); index 25 is the
    number of plies (half-moves) played so far, starting at 0.
  - Cell values: 0 empty; player 1: 1 general, 2 infantry, 3 cavalry;
    player 2: 4 general, 5 infantry, 6 cavalry. current_player is 1 or 2.
  - Each piece type moves by fixed (row, col) offsets (a single jump; intervening
    pieces do not block the path):
      general:  (1,0),(-1,0),(0,1),(0,-1),(0,-2),(0,2)
      infantry: (1,0),(2,0),(1,-1),(1,1),(-1,0)
      cavalry:  (0,3),(1,2),(2,1),(3,0)
    Player 2's pieces use the same offsets with the ROW component negated, so
    infantry advances toward the opponent for both sides.
  - A move must land on the board and not on a friendly piece. Landing on an
    opponent piece captures it (removes it).
  - Action encodes a move as from_index*25 + to_index (0..624). If a player has no
    piece move, the only legal action is PASS = 625.
  - Capturing the opponent's general wins. If the ply counter reaches 100 with both
    generals alive, the game is a draw.
  - Player 1 starts on the top rank (cells 0..4 = 3,2,1,2,3) and player 2 on the
    bottom rank (cells 20..24 = 6,5,4,5,6). current_player starts at 1.
"""

POLICY_DESCRIPTION = (
    "You play 'army5x5a' generalized chess on a 5x5 board. board has 26 ints: "
    "cells 0..24 (0 empty; you may be player 1 with pieces 1/2/3 or player 2 with "
    "4/5/6) and a ply counter at index 25. A move is from_index*25 + to_index, or "
    "625 to pass. Capture the opponent's general (1 for player 1, 4 for player 2).")
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — extend the import and `GAMES`:

```python
from .groundtruth import tictactoe, connect_four, gen_tictactoe, gen_chess
```

```python
    "army5x5a": GameSpec(
        name="army5x5a",
        module=gen_chess,
        rules_text=gen_chess.RULES_TEXT,
        policy_description=gen_chess.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_gen_chess.py tests/test_games.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cwm/groundtruth/gen_chess.py src/cwm/games.py tests/test_gen_chess.py
git commit -m "feat(games): army5x5a generalized chess (no-prior regime)"
```

---

### Task 6: Trike ground truth (wrong-prior regime)

**Files:**
- Create: `src/cwm/groundtruth/trike.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_trike.py`

**Interfaces:**
- Produces: a contract module for Trike side-6 (21 cells). Constants `SIDE=6`, `NCELLS=21`, `START_CELL=12`. Cell values: 0 empty, 1/2 discs, 3/4 disc-with-pawn, 5 neutral pawn, 6 blocked-neutral. Action = destination cell index. Registered as `"trike"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_trike.py`:

```python
from cwm.groundtruth import trike as t

def test_initial_state():
    s = t.initial_state()
    assert len(s["board"]) == 21
    assert s["board"][12] == 5           # neutral pawn on the central start cell
    assert sum(1 for v in s["board"] if v != 0) == 1
    assert s["current_player"] == 1

def test_initial_legal_actions_exact():
    # Slides from (4,2)=idx12 over the empty board along all three axes.
    assert t.legal_actions(t.initial_state()) == [3, 5, 7, 8, 10, 11, 13, 14, 17, 18]

def test_apply_action_places_disc_and_vacates_start():
    s = t.apply_action(t.initial_state(), 13)
    assert s["board"][12] == 6           # vacated neutral start -> blocked-neutral
    assert s["board"][13] == 3           # P1 disc with pawn
    assert s["current_player"] == 2

def test_apply_action_is_pure():
    s = t.initial_state()
    t.apply_action(s, 13)
    assert s["board"][12] == 5 and s["board"][13] == 0

def test_slide_cannot_pass_occupied():
    s = t.initial_state()
    board = list(s["board"])
    board[13] = 1                        # block (4,3), one step along (0,+1)
    s2 = {"board": board, "current_player": 1}
    assert 13 not in t.legal_actions(s2)  # occupied, cannot land
    assert 14 not in t.legal_actions(s2)  # cannot pass over 13 to reach 14

def test_terminal_scoring_majority():
    # Pawn (P1, value 3) at idx12 with all six neighbors occupied -> trapped.
    board = [0] * 21
    board[12] = 3                        # pawn + P1 disc
    board[13] = 1; board[18] = 1; board[17] = 1   # P1 neighbors
    board[11] = 2; board[7] = 2; board[8] = 2     # P2 neighbors
    s = {"board": board, "current_player": 2}
    assert t.is_terminal(s) is True
    # pawn cell + 6 neighbors: P1 = 3,13,18,17 = 4 ; P2 = 11,7,8 = 3
    assert t.returns(s) == {1: 1.0, 2: -1.0}

def test_returns_nonterminal_is_zero():
    assert t.returns(t.initial_state()) == {1: 0.0, 2: 0.0}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_trike.py -v`
Expected: FAIL (`No module named 'cwm.groundtruth.trike'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/trike.py`:

```python
"""Trike oracle (Alek Erickson, 2020) on a triangular board, side 6 (21 cells).

Cells are numbered row by row from the top: row r (0..SIDE-1) has r+1 cells; cell
(r,c) with 0<=c<=r has index r*(r+1)//2 + c. Cell values: 0 empty; 1 player-1
disc; 2 player-2 disc; 3 player-1 disc with the pawn; 4 player-2 disc with the
pawn; 5 the neutral pawn on its start cell; 6 a blocked, uncolored cell. Action is
the destination cell index for the shared pawn's slide.
"""

SIDE = 6
_CELLS = [(r, c) for r in range(SIDE) for c in range(r + 1)]
_INDEX = {rc: i for i, rc in enumerate(_CELLS)}
NCELLS = len(_CELLS)            # 21
START_CELL = _INDEX[(4, 2)]    # 12
_DIRS = [(0, 1), (0, -1), (1, 1), (-1, -1), (1, 0), (-1, 0)]


def _in_board(r: int, c: int) -> bool:
    return 0 <= r < SIDE and 0 <= c <= r


def _pawn_cell(board: list) -> int:
    for i, v in enumerate(board):
        if v in (3, 4, 5):
            return i
    return -1


def initial_state() -> dict:
    board = [0] * NCELLS
    board[START_CELL] = 5
    return {"board": board, "current_player": 1}


def _legal_dests(board: list) -> list:
    pawn = _pawn_cell(board)
    r, c = _CELLS[pawn]
    dests = []
    for dr, dc in _DIRS:
        rr, cc = r + dr, c + dc
        while _in_board(rr, cc) and board[_INDEX[(rr, cc)]] == 0:
            dests.append(_INDEX[(rr, cc)])
            rr, cc = rr + dr, cc + dc
    return sorted(dests)


def legal_actions(state: dict) -> list[int]:
    return _legal_dests(state["board"])


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    player = state["current_player"]
    pawn = _pawn_cell(board)
    board[pawn] = {3: 1, 4: 2, 5: 6}[board[pawn]]
    board[action] = 3 if player == 1 else 4
    return {"board": board, "current_player": 2 if player == 1 else 1}


def is_terminal(state: dict) -> bool:
    return len(_legal_dests(state["board"])) == 0


def _neighbors(idx: int) -> list:
    r, c = _CELLS[idx]
    out = []
    for dr, dc in _DIRS:
        rr, cc = r + dr, c + dc
        if _in_board(rr, cc):
            out.append(_INDEX[(rr, cc)])
    return out


def returns(state: dict) -> dict:
    if not is_terminal(state):
        return {1: 0.0, 2: 0.0}
    board = state["board"]
    pawn = _pawn_cell(board)
    cells = [pawn] + _neighbors(pawn)
    p1 = sum(1 for i in cells if board[i] in (1, 3))
    p2 = sum(1 for i in cells if board[i] in (2, 4))
    if p1 > p2:
        return {1: 1.0, 2: -1.0}
    if p2 > p1:
        return {1: -1.0, 2: 1.0}
    return {1: 0.0, 2: 0.0}


RULES_TEXT = """\
This game is Trike, on a triangular board with side 6 (21 cells).
  - Cells are numbered row by row from the top: row r (0..5) has r+1 cells; cell
    (r,c) with 0<=c<=r has index r*(r+1)//2 + c. board has 21 integers.
  - Cell values: 0 empty; 1 player-1 disc; 2 player-2 disc; 3 player-1 disc with
    the pawn on it; 4 player-2 disc with the pawn; 5 the neutral pawn on its
    (uncolored) start cell; 6 a blocked, uncolored cell. A cell is occupied if its
    value is not 0. Exactly one cell holds the pawn (value 3, 4, or 5).
  - There is one shared pawn. It starts (value 5) on the central cell, index 12
    (cell (4,2)). current_player is 1 or 2 and starts at 1.
  - Each cell has up to 6 neighbors along three axes, given by the (row,col)
    offsets (0,+1),(0,-1),(+1,+1),(-1,-1),(+1,0),(-1,0) that stay in the triangle.
  - A turn: slide the pawn from its current cell along ONE axis over consecutive
    EMPTY cells (it cannot pass over or stop on an occupied cell) and stop on any
    empty cell reached. The vacated cell keeps its disc color (3->1, 4->2) or
    becomes blocked-uncolored if it was the neutral start (5->6); the destination
    becomes the current player's disc-with-pawn (3 if player 1, else 4).
  - Action is the destination cell index. legal_actions lists every empty cell
    reachable from the pawn along the three axes.
  - The game ends when the player to move has no legal slide (the pawn is
    surrounded). The winner has the majority of their discs among the pawn's cell
    and its neighbors (player-1 cells are 1 or 3, player-2 cells are 2 or 4);
    equal counts is a draw.
"""

POLICY_DESCRIPTION = (
    "You play Trike on a triangular board of 21 cells (side 6). A shared pawn "
    "slides in a straight line over empty cells; you color the destination. A "
    "move is the destination cell index. When the pawn is trapped, the majority "
    "of discs touching it (and the pawn's own cell) wins.")
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — extend the import and `GAMES`:

```python
from .groundtruth import tictactoe, connect_four, gen_tictactoe, gen_chess, trike
```

```python
    "trike": GameSpec(
        name="trike",
        module=trike,
        rules_text=trike.RULES_TEXT,
        policy_description=trike.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_trike.py tests/test_games.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cwm/groundtruth/trike.py src/cwm/games.py tests/test_trike.py
git commit -m "feat(games): Trike side-6 with real mechanics (wrong-prior regime)"
```

---

### Task 7: Non-triviality sweep

**Files:**
- Create: `src/cwm/selfplay_sweep.py`
- Test: `tests/test_selfplay_sweep.py`

**Interfaces:**
- Consumes: `cwm.mcts.mcts_policy`.
- Produces: `mcts_vs_random(model, n_games, simulations, seed) -> dict` with keys `games`, `mcts_wins`, `draws`, `mcts_losses`, `mcts_winrate` (where `mcts_winrate = (wins + 0.5*draws)/games`). MCTS alternates which player it controls across games.

- [ ] **Step 1: Write the failing test** — create `tests/test_selfplay_sweep.py`:

```python
from cwm.selfplay_sweep import mcts_vs_random
from cwm.groundtruth import tictactoe as g

def test_mcts_beats_random_at_tictactoe():
    res = mcts_vs_random(g, n_games=10, simulations=100, seed=0)
    assert res["games"] == 10
    assert res["mcts_losses"] <= 1          # MCTS should essentially never lose to random
    assert res["mcts_winrate"] >= 0.7
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_selfplay_sweep.py -v`
Expected: FAIL (`No module named 'cwm.selfplay_sweep'`)

- [ ] **Step 3: Implement** — create `src/cwm/selfplay_sweep.py`:

```python
"""Non-triviality check: does MCTS skill beat random play on this game?

A game is a useful skill discriminator only if a searcher reliably beats random.
Run this on each new ground truth before trusting it. (No forced first-player win
is checked by eyeballing MCTS-vs-MCTS results separately.)
"""
import random

from .mcts import mcts_policy


def mcts_vs_random(model, n_games: int, simulations: int, seed: int) -> dict:
    rng = random.Random(seed)
    wins = draws = losses = 0
    for i in range(n_games):
        mcts_player = 1 if i % 2 == 0 else 2     # alternate sides
        state = model.initial_state()
        move = 0
        while not model.is_terminal(state):
            p = state["current_player"]
            if p == mcts_player:
                a = mcts_policy(model, state, n_simulations=simulations,
                                seed=seed + i * 1000 + move)
            else:
                a = rng.choice(model.legal_actions(state))
            state = model.apply_action(state, a)
            move += 1
        r = model.returns(state)
        if r[mcts_player] > 0.5:
            wins += 1
        elif r[mcts_player] < -0.5:
            losses += 1
        else:
            draws += 1
    return {"games": n_games, "mcts_wins": wins, "draws": draws,
            "mcts_losses": losses,
            "mcts_winrate": (wins + 0.5 * draws) / n_games}
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_selfplay_sweep.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/selfplay_sweep.py tests/test_selfplay_sweep.py
git commit -m "feat: MCTS-vs-random non-triviality sweep"
```

---

### Task 8: Gap orchestrator (`run_gap.py`)

**Files:**
- Create: `src/cwm/run_gap.py`
- Test: `tests/test_run_gap.py`

**Interfaces:**
- Consumes: `GAMES`, `build_contract`, `collect_trajectories`, `AzureOpenAIProvider`, `synthesize_cwm`, `refine_cwm`, `collect_visited_states`, `contract_divergence`, `CostMeter`.
- Produces: `aggregate_gap(per_seed: list[dict]) -> dict` (pure; keys `n_seeds`, `gap_mean`, `gap_min`, `gap_max`) and a `main(argv=None)` CLI.

- [ ] **Step 1: Write the failing test** — create `tests/test_run_gap.py`:

```python
from cwm.run_gap import aggregate_gap

def test_aggregate_gap_math():
    agg = aggregate_gap([
        {"gap": 0.1}, {"gap": 0.3}, {"gap": 0.2},
    ])
    assert agg["n_seeds"] == 3
    assert abs(agg["gap_mean"] - 0.2) < 1e-9
    assert agg["gap_min"] == 0.1
    assert agg["gap_max"] == 0.3

def test_aggregate_gap_empty():
    agg = aggregate_gap([])
    assert agg["n_seeds"] == 0
    assert agg["gap_mean"] == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_run_gap.py -v`
Expected: FAIL (`No module named 'cwm.run_gap'`)

- [ ] **Step 3: Implement** — create `src/cwm/run_gap.py`:

```python
# src/cwm/run_gap.py
"""Measure the verified-vs-correct gap. For each synthesis seed: synthesize +
refine a CWM to gate accuracy 1.0, then compare it against the ground truth on
three state distributions — D_gate (random-trajectory states the gate used),
D_cwm (states MCTS expands planning on the CWM), and D_truth (states MCTS expands
planning on the ground truth). Headline gap = agreement(D_gate) - agreement(D_cwm).

Usage:
    python -m cwm.run_gap --game army5x5a --synth-size mini --synth-seeds 5
"""
import argparse
import json
import os
import sys
import types
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .games import GAMES
from .world_model import build_contract
from .trajectories import collect_trajectories
from .llm.azure_openai import AzureOpenAIProvider
from .synthesizer import synthesize_cwm
from .refiner import refine_cwm
from .gap import collect_visited_states, contract_divergence
from .cost_meter import CostMeter

_DEPLOY_ENV = {"large": "AZURE_DEPLOYMENT_LARGE",
               "mini": "AZURE_DEPLOYMENT_MINI",
               "nano": "AZURE_DEPLOYMENT_NANO"}


def _load_module_from_code(code: str) -> types.ModuleType:
    mod = types.ModuleType("synth_cwm")
    exec(compile(code, "<synth_cwm>", "exec"), mod.__dict__)
    return mod


def aggregate_gap(per_seed: list) -> dict:
    gaps = [r["gap"] for r in per_seed if "gap" in r]
    n = len(gaps)
    return {"n_seeds": n,
            "gap_mean": sum(gaps) / n if n else 0.0,
            "gap_min": min(gaps) if n else 0.0,
            "gap_max": max(gaps) if n else 0.0}


def main(argv=None):
    load_dotenv(override=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="gen_tictactoe", choices=list(GAMES))
    ap.add_argument("--synth-size", default="mini", choices=list(_DEPLOY_ENV))
    ap.add_argument("--synth-seeds", type=int, default=5)
    ap.add_argument("--selfplay-games", type=int, default=20)
    ap.add_argument("--simulations", type=int, default=300)
    ap.add_argument("--train-games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )
    synth_model = os.environ[_DEPLOY_ENV[args.synth_size]]
    spec = GAMES[args.game]
    g = spec.module
    contract = build_contract(spec.rules_text)
    meter = CostMeter()

    # D_truth depends only on the ground truth; compute once and reuse.
    truth_states = collect_visited_states(
        g, n_games=args.selfplay_games, simulations=args.simulations, seed=args.seed)

    per_seed = []
    for s in range(args.synth_seeds):
        seed = args.seed + s
        traj = collect_trajectories(g, n_games=args.train_games, seed=seed)
        code, usage = synthesize_cwm(provider, synth_model, contract, traj)
        meter.add(args.synth_size, usage)
        refined = refine_cwm(provider, synth_model, contract, code, traj)
        for u in refined.usages:
            meter.add(args.synth_size, u)
        if refined.accuracy < 1.0:
            per_seed.append({"seed": seed, "skipped": "gate<1.0",
                             "accuracy": refined.accuracy})
            continue
        cwm = _load_module_from_code(refined.code)
        gate_states = [t.state for t in traj]
        cwm_states = collect_visited_states(
            cwm, n_games=args.selfplay_games, simulations=args.simulations, seed=seed)
        d_gate = contract_divergence(refined.code, gate_states, g)
        d_cwm = contract_divergence(refined.code, cwm_states, g)
        d_truth = contract_divergence(refined.code, truth_states, g)
        per_seed.append({
            "seed": seed,
            "gap": d_gate.state_agreement_rate - d_cwm.state_agreement_rate,
            "gate": d_gate.state_agreement_rate,
            "cwm": d_cwm.state_agreement_rate,
            "truth": d_truth.state_agreement_rate,
            "refinement_iterations": refined.iterations,
            "d_gate": asdict(d_gate),
            "d_cwm": asdict(d_cwm),
            "d_truth": asdict(d_truth),
        })

    report = {"game": args.game, "synth_size": args.synth_size,
              "summary": aggregate_gap(per_seed),
              "per_seed": per_seed,
              "cost_usd_total": meter.total_usd()}
    out = json.dumps(report, indent=2)
    print(out)
    Path("results").mkdir(exist_ok=True)
    Path(f"results/gap_{args.game}_{args.synth_size}.json").write_text(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_run_gap.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 6: Commit**

```bash
git add src/cwm/run_gap.py tests/test_run_gap.py
git commit -m "feat: gap-measurement orchestrator across three regimes"
```

---

## Post-implementation (manual, not part of subagent execution)

These require Azure API calls and judgment; run them after the branch merges.

1. **Non-triviality validation:** run `mcts_vs_random` for `gen_tictactoe`,
   `army5x5a`, `trike` (e.g. 20 games, 400 sims). Confirm MCTS winrate ≫ random.
   If `army5x5a` is one-sided, flip `MIRROR_PLAYER2` or adjust the start; if
   `trike` games are too short/long, retune `SIDE`. Record findings in
   `docs/EXPERIMENTS.md`.
2. **Gap runs:** `python -m cwm.run_gap --game <g> --synth-size <mini|nano>` for
   the 3 games × 2 sizes. Append the summary table (gap mean / min / max per
   regime, with per-property breakdown) to `docs/EXPERIMENTS.md`.
3. Interpret: gap ≈ 0 on `gen_tictactoe` (recall), gap > 0 expected on `army5x5a`
   / `trike`. If a gap is confirmed, that motivates the separate search-guided
   synthesis spec.
