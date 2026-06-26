# Quantitative Law of Sampling-Verification Harm — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build tested, reproducible code to measure `danger(rule, N) = play_cost × (1−rarity)^N` across a continuous rarity sweep (army5x5a cap length) and a low-divergence contrast (Connect Four), with Wilson confidence intervals.

**Architecture:** A parameterizable army5x5a-material factory provides the rarity knob (cap length / lead threshold); a pure `law.py` measures rarity, arena win rate (rule-blind vs rule-aware, refereed by the true game), and the danger metric, all with Wilson CIs; a driver script runs the sweep and saves a table.

**Tech Stack:** Python 3, pytest, existing `cwm` package (`mcts`, `arena`, `groundtruth.gen_chess`). No new dependencies (Wilson CI uses `math`).

## Global Constraints

- State is `{"board": list[int], "current_player": int}`, `current_player ∈ {1,2}`; Action is `int`. army5x5a `board` = 26 ints (cells 0..24 + ply counter at index 25).
- Contract: `initial_state`, `legal_actions`, `apply_action` (new state, no mutation), `is_terminal`, `returns` (`{1,2}`→`{-1.0,0.0,1.0}`, all 0.0 unless terminal).
- Material: player 1 owns piece values {1,2,3}, player 2 owns {4,5,6}; count over cells 0..24 only (exclude the ply counter at index 25).
- Material-at-cap rule with lead `L`: at `board[25] >= max_plies` with both generals alive, the side whose material lead ≥ `L` wins; otherwise draw. A captured general wins/loses exactly as in base army5x5a and takes precedence over the cap rule.
- `danger(play_cost, rarity, N) = play_cost * (1 - rarity) ** N`.
- The arena uses the existing `cwm.arena.run_arena(referee, cwm_agent, baseline_agent, n_games, seed) -> ArenaResult(games, cwm_wins, baseline_wins, draws, baseline_illegal, cwm_illegal)`; it alternates starts and forfeits illegal moves.
- `results/` is git-ignored.

---

### Task 1: Parameterizable material-game factory

**Files:**
- Modify: `src/cwm/groundtruth/gen_chess_material.py`
- Test: `tests/test_gen_chess_material.py`

**Interfaces:**
- Consumes: `gen_chess` internals `N`, `PASS`, `_OWNER`, `_piece_dests`, `_general_alive`, `initial_state`, `apply_action`, `RULES_TEXT`.
- Produces: `make_material(max_plies: int = 100, lead: int = 1) -> _MaterialGame` where `_MaterialGame` exposes `initial_state()`, `legal_actions(state)`, `apply_action(state, action)`, `is_terminal(state)`, `returns(state)`, and `outcome(state) -> tuple[int, str]` with reason ∈ {"capture","material","draw","none"}. Existing module-level functions are unchanged.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_gen_chess_material.py`:

```python
def test_factory_defaults_match_module():
    from cwm.groundtruth import gen_chess_material as gm
    g = gm.make_material()  # defaults 100 / 1
    s = g.initial_state()
    assert s == gm.initial_state()
    assert g.legal_actions(s) == gm.legal_actions(s)
    # a cap state with unequal material: same returns as the module
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[22] = 4
    cap = {"board": cells + [gm.MAX_PLIES], "current_player": 1}
    assert g.returns(cap) == gm.returns(cap)
    assert g.outcome(cap) == (1, "material")

def test_factory_lead_threshold():
    from cwm.groundtruth import gen_chess_material as gm
    g2 = gm.make_material(lead=2)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[22] = 4   # P1 lead = 1
    cap = {"board": cells + [100], "current_player": 1}
    assert g2.outcome(cap) == (0, "draw")        # lead 1 < 2 -> draw
    cells2 = [0] * 25; cells2[2] = 1; cells2[5] = 2; cells2[6] = 3; cells2[22] = 4  # P1 lead = 2
    cap2 = {"board": cells2 + [100], "current_player": 1}
    assert g2.outcome(cap2) == (1, "material")

def test_factory_short_cap_is_terminal_earlier():
    from cwm.groundtruth import gen_chess_material as gm
    g = gm.make_material(max_plies=40)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[22] = 4
    s = {"board": cells + [40], "current_player": 1}
    assert g.is_terminal(s) is True              # at the shorter cap
    assert g.legal_actions(s) == []
    s2 = {"board": cells + [39], "current_player": 1}
    assert g.is_terminal(s2) is False
    assert g.legal_actions(s2)                    # moves available below the cap

def test_factory_long_cap_not_gated_by_base_100():
    from cwm.groundtruth import gen_chess_material as gm
    g = gm.make_material(max_plies=140)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[22] = 4
    s = {"board": cells + [120], "current_player": 1}   # past base 100, below 140
    assert g.is_terminal(s) is False
    assert g.legal_actions(s)                     # must still generate moves (not base-gated)

def test_factory_capture_precedence():
    from cwm.groundtruth import gen_chess_material as gm
    g = gm.make_material(max_plies=40)
    cells = [0] * 25; cells[2] = 1                # only P1 general (P2 captured)
    s = {"board": cells + [40], "current_player": 1}
    assert g.outcome(s) == (1, "capture")
    assert g.returns(s) == {1: 1.0, 2: -1.0}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gen_chess_material.py -k factory -v`
Expected: FAIL (`module 'cwm.groundtruth.gen_chess_material' has no attribute 'make_material'`)

- [ ] **Step 3: Implement the factory** — append to `src/cwm/groundtruth/gen_chess_material.py`:

```python
def _moves(board: list, player: int) -> list:
    """Legal piece moves for `player`, independent of any cap (base.legal_actions
    is gated by base.is_terminal at the fixed cap 100, which is wrong for other
    cap lengths, so generate moves directly)."""
    actions = []
    for idx in range(N):
        v = board[idx]
        if v != 0 and base._OWNER[v] == player:
            for tgt in base._piece_dests(board, idx):
                actions.append(idx * N + tgt)
    if not actions:
        actions.append(base.PASS)
    return actions


class _MaterialGame:
    """army5x5a + material-at-cap, parameterized by cap length and lead threshold."""

    def __init__(self, max_plies: int, lead: int):
        self.max_plies = max_plies
        self.lead = lead

    def initial_state(self) -> dict:
        return initial_state()

    def apply_action(self, state: dict, action: int) -> dict:
        return apply_action(state, action)

    def outcome(self, state: dict) -> tuple[int, str]:
        b = state["board"]
        a1, a2 = _general_alive(b, 1), _general_alive(b, 2)
        if not a1 or not a2:
            return (1 if a1 else 2), "capture"
        if b[N] >= self.max_plies:
            p1, p2 = _material(b)
            if p1 - p2 >= self.lead:
                return 1, "material"
            if p2 - p1 >= self.lead:
                return 2, "material"
            return 0, "draw"
        return 0, "none"

    def is_terminal(self, state: dict) -> bool:
        return self.outcome(state)[1] != "none"

    def legal_actions(self, state: dict) -> list:
        if self.is_terminal(state):
            return []
        return _moves(state["board"], state["current_player"])

    def returns(self, state: dict) -> dict:
        w, reason = self.outcome(state)
        if reason == "none":
            return {1: 0.0, 2: 0.0}
        if w == 1:
            return {1: 1.0, 2: -1.0}
        if w == 2:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}


def make_material(max_plies: int = 100, lead: int = 1) -> "_MaterialGame":
    return _MaterialGame(max_plies, lead)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_gen_chess_material.py -v`
Expected: PASS (factory tests + the existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/cwm/groundtruth/gen_chess_material.py tests/test_gen_chess_material.py
git commit -m "feat(games): parameterizable material-game factory (cap/lead rarity knob)"
```

---

### Task 2: `law.py` — rarity, arena win rate, danger (with Wilson CIs)

**Files:**
- Create: `src/cwm/law.py`
- Test: `tests/test_law.py`

**Interfaces:**
- Consumes: `cwm.mcts.mcts_policy`, `cwm.arena.run_arena`.
- Produces:
  - `wilson_ci(successes: float, n: int, z: float = 1.96) -> tuple[float, float, float]` → `(point, lo, hi)` (point = successes/n; `(0.0, 0.0, 1.0)` if n==0).
  - `rarity(game, rule_reason: str, n_games: int, seed: int) -> tuple[float, float, float]` → fraction of random games whose `game.outcome(terminal)[1] == rule_reason`, with Wilson CI.
  - `arena_winrate(truth, blind, sims: int, n_games: int, seeds: list[int]) -> dict` with keys `winrate`, `lo`, `hi`, `n`, `wins`, `draws`, `losses` (blind agent vs truth agent, refereed by `truth`, pooled over seeds).
  - `danger(play_cost: float, rarity_rate: float, n: int) -> float` = `play_cost * (1 - rarity_rate) ** n`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_law.py`:

```python
import math
from cwm.law import wilson_ci, rarity, arena_winrate, danger
from cwm.groundtruth import gen_chess_material as gm

def test_wilson_ci_bounds():
    p, lo, hi = wilson_ci(5, 10)
    assert p == 0.5 and 0.0 <= lo < 0.5 < hi <= 1.0
    p0, lo0, hi0 = wilson_ci(0, 0)
    assert (p0, lo0, hi0) == (0.0, 0.0, 1.0)
    # more data -> tighter interval
    _, lo_small, hi_small = wilson_ci(5, 10)
    _, lo_big, hi_big = wilson_ci(50, 100)
    assert (hi_big - lo_big) < (hi_small - lo_small)

def test_danger_monotonicity():
    # (1-rarity)^N shrinks as rarity rises, so danger decreases with rarity
    assert danger(0.3, 0.01, 40) > danger(0.3, 0.20, 40)
    # increasing in play_cost
    assert danger(0.4, 0.05, 40) > danger(0.2, 0.05, 40)
    # exact value
    assert abs(danger(0.5, 0.0, 40) - 0.5) < 1e-12

def test_rarity_counts_rule_reason():
    g = gm.make_material(max_plies=40)        # short cap -> rule fires often-ish
    rate, lo, hi = rarity(g, "material", n_games=60, seed=1)
    assert 0.0 <= lo <= rate <= hi <= 1.0

def test_arena_winrate_fair_baseline():
    # truth vs itself -> ~0.5, and counts are consistent
    g = gm.make_material(max_plies=40)
    res = arena_winrate(g, g, sims=60, n_games=10, seeds=[0, 1])
    assert res["n"] == 20
    assert res["wins"] + res["draws"] + res["losses"] == 20
    assert 0.0 <= res["lo"] <= res["winrate"] <= res["hi"] <= 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_law.py -v`
Expected: FAIL (`No module named 'cwm.law'`)

- [ ] **Step 3: Implement** — create `src/cwm/law.py`:

```python
"""Quantitative law of sampling-verification harm.

danger(rule, N) = play_cost(rule) * P(rule absent from N random games)
                = play_cost * (1 - rarity) ** N
A rule harms a sampling-verified planner iff it is rare enough to escape an
N-trajectory gate AND consequential enough to matter. All measurement is pure
(no LLM): the rule-blind hand-written base game is the on-manifold proxy for a
CWM that omits the rule.
"""
import math
import random

from .mcts import mcts_policy
from .arena import run_arena


def wilson_ci(successes: float, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(point, lo, hi) Wilson score interval. successes may be fractional (draws
    counted as 0.5); point = successes/n. n==0 -> (0.0, 0.0, 1.0)."""
    if n == 0:
        return (0.0, 0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (p, max(0.0, center - half), min(1.0, center + half))


def rarity(game, rule_reason: str, n_games: int, seed: int) -> tuple[float, float, float]:
    """Fraction of random games whose terminal outcome is decided by `rule_reason`
    (per game.outcome), with a Wilson CI."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_games):
        s = game.initial_state()
        while not game.is_terminal(s):
            s = game.apply_action(s, rng.choice(game.legal_actions(s)))
        if game.outcome(s)[1] == rule_reason:
            hits += 1
    return wilson_ci(hits, n_games)


def _mcts_agent(model, sims: int, base_seed: int):
    counter = {"n": 0}
    def agent(state, legal):
        counter["n"] += 1
        return mcts_policy(model, state, n_simulations=sims, seed=base_seed + counter["n"])
    return agent


def arena_winrate(truth, blind, sims: int, n_games: int, seeds: list) -> dict:
    """Win rate (wins + 0.5*draws)/n of a `blind`-planning MCTS agent vs a
    `truth`-planning MCTS agent, refereed by `truth`, pooled over `seeds`."""
    wins = draws = losses = 0
    for sd in seeds:
        a_blind = _mcts_agent(blind, sims, sd + 1)
        a_truth = _mcts_agent(truth, sims, sd + 100_000)
        # run_arena treats arg1 as "cwm_agent" -> our blind agent
        res = run_arena(truth, cwm_agent=a_blind, baseline_agent=a_truth,
                        n_games=n_games, seed=sd + 2000)
        wins += res.cwm_wins
        draws += res.draws
        losses += res.baseline_wins
    n = wins + draws + losses
    point, lo, hi = wilson_ci(wins + 0.5 * draws, n)
    return {"winrate": point, "lo": lo, "hi": hi, "n": n,
            "wins": wins, "draws": draws, "losses": losses}


def danger(play_cost: float, rarity_rate: float, n: int) -> float:
    return play_cost * (1 - rarity_rate) ** n
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_law.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/law.py tests/test_law.py
git commit -m "feat(law): rarity, arena win rate, danger metric with Wilson CIs"
```

---

### Task 3: `law_sweep.py` driver

**Files:**
- Create: `scripts/law_sweep.py`

**Interfaces:**
- Consumes: `cwm.law` (`rarity`, `arena_winrate`, `danger`), `cwm.groundtruth.gen_chess_material.make_material`, `cwm.groundtruth.connect_four`, and a Connect-Four rule wrapper defined inline.

- [ ] **Step 1: Write the driver** — create `scripts/law_sweep.py`:

```python
"""Run the quantitative-law sweep: army5x5a cap-length rarity knob (the
inverted-U danger curve) + Connect Four low-divergence contrast. CPU only.

Run: PYTHONPATH=src python scripts/law_sweep.py
"""
import json
from pathlib import Path

from cwm.law import rarity, arena_winrate, danger
from cwm.groundtruth import gen_chess_material as gm, connect_four as base_cf

SIMS = 400
N_GAMES = 80
SEEDS = [0, 1, 2]
RARITY_GAMES = 400
N_TRAJ = [20, 40, 80]          # gate sizes for the danger metric

ROWS, COLS = 6, 7
def _i(r, c):
    return r * COLS + c


class CFRule:
    """Connect Four + one extra instant-win shape (low-divergence contrast)."""
    def __init__(self, rule):
        self.rule = rule

    def initial_state(self):
        return base_cf.initial_state()

    def apply_action(self, s, a):
        return base_cf.apply_action(s, a)

    def legal_actions(self, s):
        if self.is_terminal(s):
            return []
        return [c for c in range(COLS) if s["board"][_i(0, c)] == 0]

    def _vthree(self, b):
        for r in range(ROWS - 2):
            p = b[_i(r, 3)]
            if p and b[_i(r + 1, 3)] == p and b[_i(r + 2, 3)] == p:
                return p
        return 0

    def _square(self, b):
        for r in range(ROWS - 1):
            for c in range(COLS - 1):
                p = b[_i(r, c)]
                if p and b[_i(r, c + 1)] == p and b[_i(r + 1, c)] == p and b[_i(r + 1, c + 1)] == p:
                    return p
        return 0

    def outcome(self, s):
        b = s["board"]
        if self.rule == "topcenter" and b[_i(0, 3)] != 0 and base_cf.winner(s) == 0:
            return b[_i(0, 3)], "rule"
        if self.rule == "vthree":
            x = self._vthree(b)
            if x:
                return x, "rule"
        if self.rule == "square":
            x = self._square(b)
            if x:
                return x, "rule"
        w = base_cf.winner(s)
        if w:
            return w, "line"
        if all(v != 0 for v in b):
            return 0, "draw"
        return 0, "none"

    def is_terminal(self, s):
        return self.outcome(s)[1] != "none"

    def returns(self, s):
        w, reason = self.outcome(s)
        if reason == "none":
            return {1: 0.0, 2: 0.0}
        return {1: 1.0, 2: -1.0} if w == 1 else {1: -1.0, 2: 1.0} if w == 2 else {1: 0.0, 2: 0.0}


def row(name, truth, blind, reason):
    rar, rlo, rhi = rarity(truth, reason, RARITY_GAMES, seed=1)
    fair = arena_winrate(truth, truth, SIMS, N_GAMES, SEEDS)        # fairness baseline
    blind_res = arena_winrate(truth, blind, SIMS, N_GAMES, SEEDS)
    play_cost = fair["winrate"] - blind_res["winrate"]
    dangers = {n: danger(play_cost, rar, n) for n in N_TRAJ}
    return {"config": name, "rarity": rar, "rarity_ci": [rlo, rhi],
            "fair_winrate": fair["winrate"],
            "blind_winrate": blind_res["winrate"],
            "blind_ci": [blind_res["lo"], blind_res["hi"]],
            "play_cost": play_cost, "danger": dangers}


from cwm.groundtruth import gen_chess as base_army


class BaseArmyCap:
    """Rule-blind army at a given cap: cap is a DRAW (omits material rule)."""
    def __init__(self, max_plies):
        self.max_plies = max_plies
    def initial_state(self):
        return base_army.initial_state()
    def apply_action(self, s, a):
        return base_army.apply_action(s, a)
    def _term(self, b):
        return (not base_army._general_alive(b, 1)) or (not base_army._general_alive(b, 2)) or b[base_army.N] >= self.max_plies
    def is_terminal(self, s):
        return self._term(s["board"])
    def legal_actions(self, s):
        from cwm.groundtruth.gen_chess_material import _moves
        return [] if self.is_terminal(s) else _moves(s["board"], s["current_player"])
    def returns(self, s):
        b = s["board"]; a1 = base_army._general_alive(b, 1); a2 = base_army._general_alive(b, 2)
        if a1 and not a2:
            return {1: 1.0, 2: -1.0}
        if a2 and not a1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}


def main():
    rows = []
    for mp in (30, 40, 50, 60, 80, 100, 140):
        truth = gm.make_material(max_plies=mp)
        blind = BaseArmyCap(mp)
        rows.append(row(f"army cap={mp}", truth, blind, "material"))
    for rule in ("topcenter", "vthree", "square"):
        truth = CFRule(rule)
        rows.append(row(f"cf {rule}", truth, base_cf, "rule"))

    Path("results").mkdir(exist_ok=True)
    Path("results/law_sweep.json").write_text(json.dumps(rows, indent=2))
    print(f"{'config':14s} {'rarity':>8s} {'fair':>6s} {'blind':>6s} {'cost':>6s} "
          f"{'dgr@20':>7s} {'dgr@40':>7s} {'dgr@80':>7s}")
    for r in rows:
        d = r["danger"]
        print(f"{r['config']:14s} {r['rarity']:8.3f} {r['fair_winrate']:6.3f} "
              f"{r['blind_winrate']:6.3f} {r['play_cost']:6.3f} "
              f"{d['20']:7.3f} {d['40']:7.3f} {d['80']:7.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run the driver at tiny settings to confirm it executes** (edit not needed — override via a quick inline check):

Run:
```bash
PYTHONPATH=src python -c "
import scripts.law_sweep as L
L.SIMS=30; L.N_GAMES=4; L.SEEDS=[0]; L.RARITY_GAMES=30
L.main()
print('SMOKE OK')
" 2>&1 | tail -5
```
Expected: a table prints, ends with `SMOKE OK`, and `results/law_sweep.json` exists. (Numbers are noise at this size — this only checks the code path.)

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 4: Commit**

```bash
git add scripts/law_sweep.py
git commit -m "feat(law): sweep driver — army cap-length curve + Connect Four contrast"
```

---

## Post-implementation (manual)

1. Full sweep: `PYTHONPATH=src python scripts/law_sweep.py` (CPU; minutes). Read
   `results/law_sweep.json`. Expect the army `danger` column to trace an
   inverted-U over the cap sweep (peaking at intermediate rarity) and every CF row
   to have `danger ≈ 0` at N≥40 despite high `play_cost`.
2. Confirm the fair baseline (`fair_winrate`) is ≈0.5 for every row; if a row is
   far off, raise `SIMS`/`N_GAMES`.
3. LLM confirmation (Azure): at 2–3 cap values, synthesize the CWM with INCOMPLETE
   rules (`run_gap --game army5x5a_material_incomplete --play-games`) and check its
   play winrate matches the `blind_winrate` proxy within CI.
4. Write the danger-vs-rarity curve + CF contrast into `docs/EXPERIMENTS.md`.
