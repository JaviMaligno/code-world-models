# CWM Rare-Rule Gap Instrument — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `army5x5a + material-at-cap` ground truth and the `gap_truth`
metric so the gap experiment can be run in paired incomplete/complete-rules
conditions (the instrument that broke the rarity↔consequence tension).

**Architecture:** The material rule only changes terminal *scoring* at the ply
cap (`is_terminal`, `legal_actions`, `apply_action` are identical to base
army5x5a), so the new ground truth reuses `gen_chess` and overrides only
`returns`. Two registry entries on that one module supply the complete and
incomplete rule specs. `run_gap` gains `gap_truth = agreement(D_gate) −
agreement(D_truth)` alongside the existing `gap` (= gate − cwm).

**Tech Stack:** Python 3, pytest, existing `cwm` package. No new dependencies.

## Global Constraints

- State is `{"board": list[int], "current_player": int}`, `current_player ∈ {1,2}`; Action is an `int`. army5x5a `board` has 26 ints (cells 0..24 + ply counter at index 25).
- Contract functions: `initial_state`, `legal_actions`, `apply_action` (returns a NEW state, never mutates), `is_terminal`, `returns` (`{1,2}`→`{-1.0,0.0,1.0}`, all 0.0 unless terminal; winner +1, loser −1, draw 0/0).
- The material rule R: at `board[25] >= MAX_PLIES` (100) with both generals alive, the player with more pieces among cells 0..24 wins; equal piece counts is a draw. A captured general still wins/loses as in base army5x5a, and R never changes `is_terminal`/`legal_actions`/`apply_action` — only `returns`.
- Material count: player 1 owns values {1,2,3}; player 2 owns {4,5,6}.
- Registry keys: `"army5x5a_material"` (complete rules) and `"army5x5a_material_incomplete"` (base rules), both on the material module.
- New game modules follow the style of existing `groundtruth/*.py` and expose `RULES_TEXT` + `POLICY_DESCRIPTION`.
- `run_gap` stays game-agnostic; `results/` is git-ignored.

---

### Task 1: `army5x5a + material-at-cap` ground truth

**Files:**
- Create: `src/cwm/groundtruth/gen_chess_material.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_gen_chess_material.py`

**Interfaces:**
- Consumes: `cwm.groundtruth.gen_chess` (`initial_state`, `legal_actions`, `apply_action`, `is_terminal`, `N`, `MAX_PLIES`, `_general_alive`, `RULES_TEXT`).
- Produces: a contract module exposing `initial_state`, `legal_actions`, `apply_action`, `is_terminal`, `returns`, `_material(board) -> tuple[int,int]`, `RULES_TEXT`, `POLICY_DESCRIPTION`; registered as `"army5x5a_material"` and `"army5x5a_material_incomplete"`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_gen_chess_material.py`:

```python
from cwm.groundtruth import gen_chess_material as m
from cwm.groundtruth import gen_chess as base

def _cap_state(board_cells, current_player=1):
    # board_cells: 25 cell values; ply counter set to the cap.
    return {"board": list(board_cells) + [base.MAX_PLIES], "current_player": current_player}

def test_initial_state_matches_base():
    assert m.initial_state() == base.initial_state()

def test_legal_and_apply_match_base_midgame():
    s = base.initial_state()
    assert m.legal_actions(s) == base.legal_actions(s)
    a = m.legal_actions(s)[0]
    assert m.apply_action(s, a) == base.apply_action(s, a)

def test_material_counts():
    cells = [0] * 25
    cells[0] = 1; cells[1] = 2; cells[2] = 3   # P1: 3 pieces
    cells[20] = 4; cells[21] = 5               # P2: 2 pieces
    assert m._material(cells) == (3, 2)

def test_cap_material_winner():
    cells = [0] * 25
    cells[2] = 1; cells[5] = 2; cells[6] = 3   # P1 general + 2 pieces = 3
    cells[22] = 4                              # P2 general only = 1
    s = _cap_state(cells)
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 1.0, 2: -1.0}

def test_cap_equal_material_is_draw():
    cells = [0] * 25
    cells[2] = 1; cells[5] = 2                 # P1: 2
    cells[22] = 4; cells[23] = 5               # P2: 2
    s = _cap_state(cells)
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 0.0, 2: 0.0}

def test_capture_win_unchanged():
    cells = [0] * 25
    cells[2] = 1                               # only P1 general alive (P2 general captured)
    s = {"board": cells + [10], "current_player": 1}
    assert m.is_terminal(s) is True
    assert m.returns(s) == {1: 1.0, 2: -1.0}

def test_nonterminal_returns_zero():
    s = base.initial_state()
    assert m.is_terminal(s) is False
    assert m.returns(s) == {1: 0.0, 2: 0.0}

def test_rules_text_variants_registered():
    from cwm.games import GAMES
    assert GAMES["army5x5a_material"].module is m
    assert GAMES["army5x5a_material_incomplete"].module is m
    # complete spec mentions material/pieces at the cap; incomplete keeps base "draw"
    assert "more pieces" in GAMES["army5x5a_material"].rules_text.lower()
    assert GAMES["army5x5a_material_incomplete"].rules_text == base.RULES_TEXT
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gen_chess_material.py -v`
Expected: FAIL (`No module named 'cwm.groundtruth.gen_chess_material'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/gen_chess_material.py`:

```python
"""army5x5a with a deep-tail 'material-at-cap' rule (rare-rule gap instrument).

Identical to gen_chess (army5x5a) EXCEPT terminal scoring at the ply cap: when the
ply counter reaches MAX_PLIES with both generals alive, instead of a draw the
player with more pieces on the board (cells 0..24) wins; equal counts is a draw.
is_terminal / legal_actions / apply_action are unchanged from base, so only
`returns` differs. This rule is rare under random play (~1% of games) but central
to competent play (~50%), exposing the gate's coverage blind spot.
"""
from . import gen_chess as base
from .gen_chess import (  # re-export the unchanged contract surface
    initial_state, legal_actions, apply_action, is_terminal,
    N, MAX_PLIES, _general_alive,
)


def _material(board: list) -> tuple:
    p1 = sum(1 for v in board[:N] if v in (1, 2, 3))
    p2 = sum(1 for v in board[:N] if v in (4, 5, 6))
    return p1, p2


def returns(state: dict) -> dict:
    board = state["board"]
    a1, a2 = _general_alive(board, 1), _general_alive(board, 2)
    if not a1 or not a2:                      # a general was captured: as in base
        if a1 and not a2:
            return {1: 1.0, 2: -1.0}
        if a2 and not a1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}
    if board[N] >= MAX_PLIES:                 # deep-tail rule: more material wins
        p1, p2 = _material(board)
        if p1 > p2:
            return {1: 1.0, 2: -1.0}
        if p2 > p1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}
    return {1: 0.0, 2: 0.0}                   # non-terminal


# Complete spec: base rules with the cap clause rewritten to state the rule.
RULES_TEXT = base.RULES_TEXT.replace(
    "  - Capturing the opponent's general wins. If the ply counter reaches 100 with both\n"
    "    generals alive, the game is a draw.",
    "  - Capturing the opponent's general wins. If the ply counter reaches 100 with both\n"
    "    generals alive, the player with MORE pieces on the board (cells 0..24) wins;\n"
    "    equal piece counts is a draw.",
)

POLICY_DESCRIPTION = base.POLICY_DESCRIPTION
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — extend the import line and add two entries:

```python
from .groundtruth import tictactoe, connect_four, gen_tictactoe, gen_chess, trike, gen_chess_material
```

Add to the `GAMES` dict:

```python
    "army5x5a_material": GameSpec(
        name="army5x5a_material",
        module=gen_chess_material,
        rules_text=gen_chess_material.RULES_TEXT,
        policy_description=gen_chess_material.POLICY_DESCRIPTION,
    ),
    "army5x5a_material_incomplete": GameSpec(
        name="army5x5a_material_incomplete",
        module=gen_chess_material,
        rules_text=gen_chess.RULES_TEXT,
        policy_description=gen_chess_material.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Verify the RULES_TEXT replacement actually fired** (the `.replace` is a no-op if the base text drifts). Run:

```bash
python -c "from cwm.groundtruth import gen_chess_material as m, gen_chess as b; assert m.RULES_TEXT != b.RULES_TEXT, 'replace did not fire'; assert 'more pieces' in m.RULES_TEXT.lower(); print('RULES_TEXT OK')"
```
Expected: `RULES_TEXT OK`

- [ ] **Step 6: Run tests to verify pass**

Run: `python -m pytest tests/test_gen_chess_material.py tests/test_games.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/cwm/groundtruth/gen_chess_material.py src/cwm/games.py tests/test_gen_chess_material.py
git commit -m "feat(games): army5x5a + material-at-cap (rare-rule gap instrument)"
```

---

### Task 2: `gap_truth` metric in `run_gap`

**Files:**
- Modify: `src/cwm/run_gap.py`
- Test: `tests/test_run_gap.py`

**Interfaces:**
- Consumes: existing per-seed dict with `gate`/`cwm`/`truth` = `state_agreement_rate` of D_gate/D_cwm/D_truth.
- Produces: each scored per-seed entry also carries `gap_truth = gate − truth`; `aggregate_gap` returns `gap_truth_mean/min/max` alongside the existing `gap_*`.

- [ ] **Step 1: Write the failing tests** — replace the body of `tests/test_run_gap.py` with:

```python
from cwm.run_gap import aggregate_gap

def test_aggregate_gap_math():
    agg = aggregate_gap([
        {"gap": 0.1, "gap_truth": 0.5},
        {"gap": 0.3, "gap_truth": 0.7},
        {"gap": 0.2, "gap_truth": 0.6},
    ])
    assert agg["n_seeds"] == 3
    assert abs(agg["gap_mean"] - 0.2) < 1e-9
    assert agg["gap_min"] == 0.1 and agg["gap_max"] == 0.3
    assert abs(agg["gap_truth_mean"] - 0.6) < 1e-9
    assert agg["gap_truth_min"] == 0.5 and agg["gap_truth_max"] == 0.7

def test_aggregate_gap_empty():
    agg = aggregate_gap([])
    assert agg["n_seeds"] == 0
    assert agg["gap_mean"] == 0.0
    assert agg["gap_truth_mean"] == 0.0

def test_aggregate_gap_skips_entries_without_gap():
    agg = aggregate_gap([
        {"gap": 0.2, "gap_truth": 0.4},
        {"seed": 3, "skipped": "gate<1.0", "accuracy": 0.97},
        {"gap": 0.4, "gap_truth": 0.8},
    ])
    assert agg["n_seeds"] == 2
    assert abs(agg["gap_mean"] - 0.3) < 1e-9
    assert abs(agg["gap_truth_mean"] - 0.6) < 1e-9
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_run_gap.py -v`
Expected: FAIL (`KeyError: 'gap_truth_mean'`)

- [ ] **Step 3: Update `aggregate_gap`** in `src/cwm/run_gap.py` — replace the function with:

```python
def aggregate_gap(per_seed: list) -> dict:
    def _agg(key):
        vals = [r[key] for r in per_seed if key in r]
        n = len(vals)
        return n, (sum(vals) / n if n else 0.0), (min(vals) if n else 0.0), (max(vals) if n else 0.0)

    n, gmean, gmin, gmax = _agg("gap")
    _, tmean, tmin, tmax = _agg("gap_truth")
    return {"n_seeds": n,
            "gap_mean": gmean, "gap_min": gmin, "gap_max": gmax,
            "gap_truth_mean": tmean, "gap_truth_min": tmin, "gap_truth_max": tmax}
```

- [ ] **Step 4: Add `gap_truth` to the per-seed entry** in `src/cwm/run_gap.py` — in the scored-seed `per_seed.append({...})`, add the `gap_truth` key right after `gap`:

```python
        per_seed.append({
            "seed": seed,
            "gap": d_gate.state_agreement_rate - d_cwm.state_agreement_rate,
            "gap_truth": d_gate.state_agreement_rate - d_truth.state_agreement_rate,
            "gate": d_gate.state_agreement_rate,
            "cwm": d_cwm.state_agreement_rate,
            "truth": d_truth.state_agreement_rate,
            "refinement_iterations": refined.iterations,
            "d_gate": asdict(d_gate),
            "d_cwm": asdict(d_cwm),
            "d_truth": asdict(d_truth),
        })
```

- [ ] **Step 5: Run tests to verify pass**

Run: `python -m pytest tests/test_run_gap.py -v`
Expected: PASS

- [ ] **Step 6: Sanity-check the module still imports and the games are runnable**

Run: `python -c "import cwm.run_gap; from cwm.games import GAMES; assert 'army5x5a_material' in GAMES and 'army5x5a_material_incomplete' in GAMES; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 8: Commit**

```bash
git add src/cwm/run_gap.py tests/test_run_gap.py
git commit -m "feat(run_gap): gap_truth metric (gate vs D_truth) for the rare-rule experiment"
```

---

## Post-implementation (manual, needs Azure)

Run after merge:

1. **Treatment + control grid:**
   ```bash
   for cond in army5x5a_material_incomplete army5x5a_material; do
     for sz in mini nano; do
       PYTHONPATH=src python -m cwm.run_gap --game $cond --synth-size $sz \
         --synth-seeds 5 --selfplay-games 20 --simulations 300 --train-games 40 --seed 0
     done
   done
   ```
2. Read `gap_truth_mean` and per-seed `gap_truth` from `results/gap_army5x5a_material*_*.json`.
   Expect: **incomplete** → `gap_truth > 0`, bimodal across seeds; **complete** (control)
   → `gap_truth ≈ 0`. The contrast is the result.
3. Append a summary table (gap_truth per condition × size, plus the per-seed
   spread) to `docs/EXPERIMENTS.md`. If the treatment gap is confirmed, that
   motivates the separate search-guided-synthesis spec.
