# Beacon — Minimal Provable Deep PO Game (Claim A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Beacon oracle (a minimal deep partially-observable game where competent play reaches a final-round region D that random play almost never reaches) plus a Claim A instrument and experiment driver, demonstrating that a CWM whose `infer_states` is wrong only on D passes a random-trajectory inference gate yet loses at play.

**Architecture:** Beacon reuses the imperfect contract (`observation`/`infer_states`/`initial_states`) and the existing determinized planner, inference gate, and arena. A survival walk (self-inflicted loss: an unsafe move loses immediately) makes random play die at rate 1/2 per step while optimal play reaches the final round deterministically; at the final round each player must guess the opponent's hidden type, which is inferable from the opponent's observed moves. All chance is in the deal (the two hidden types), so `apply_action` is deterministic.

**Tech Stack:** Python 3, pytest, existing `cwm` package. No new dependencies.

## Global Constraints

- State `{"board": list[int], "current_player": int}`, `current_player ∈ {1,2}`; hidden info in `board`. Imperfect-info `returns` are real-valued net chips.
- Two hidden types `t1, t2 ∈ {0,1}` drawn uniformly at the deal. Branching `b = 2`. Parameter `T` = safe steps each player must complete; default `T = 8`.
- Safe action in the walk: `safe(k, t) = (k + t) % 2` (function of the mover's OWN type and their own step index `k`). Playing the non-safe action is an immediate loss (the opponent wins).
- board (length 9): `[step1, step2, t1, t2, last1, last2, guess1, guess2, status]`. `last_i` = the mover's most recent move (public), `-1` if none. `guess_i` ∈ {-1,0,1}. status: 0 walking, 1 final round, 2 P1 wins, 3 P2 wins, 4 draw.
- Final round: each player commits a guess `g ∈ {0,1}`; player `i` scores 1 iff `guess_i == t_{opponent}`; higher score wins, equal scores draw.
- `current_player` is derivable (`_cp_from_board`): walk (`status==0`) → `1 if (step1+step2) % 2 == 0 else 2`; final (`status==1`) → `1 if (#guesses set) % 2 == 0 else 2`.
- `last_i` invariant: once `step_i ≥ 1`, `last_i == (step_i - 1 + t_i) % 2`. Type inversion from observation: `t_opp = (last_opp - step_opp + 1) % 2` when `last_opp != -1`.
- `observation(state, player)` masks ONLY the opponent's type slot (`t2` if player 1, else `t1`) to `-1`; everything else is public.
- Reuses `cwm.determinized` (`determinized_policy`, `imperfect_arena`), `cwm.gap.inference_accuracy`, `cwm.law` (`wilson_ci`, `danger`). Perfect-info games unaffected.
- `results/` is git-ignored.

---

### Task 1: Beacon core dynamics

**Files:**
- Create: `src/cwm/groundtruth/beacon.py`
- Test: `tests/test_beacon.py`

**Interfaces:**
- Produces: `make_beacon(T=8)` returning an object with `T`, `safe(k, t)`, `_cp_from_board(board)`, `initial_state()`, `initial_states()`, `is_terminal(state)`, `legal_actions(state)`, `apply_action(state, action)`, `returns(state)`. (observation/infer_states/registration come in Task 2.)

- [ ] **Step 1: Write the failing tests** — create `tests/test_beacon.py`:

```python
from cwm.groundtruth import beacon as B

G = B.make_beacon(T=3)   # small T for hand-checkable tests

def test_safe_function():
    assert G.safe(0, 0) == 0 and G.safe(0, 1) == 1
    assert G.safe(1, 0) == 1 and G.safe(1, 1) == 0

def test_initial_states_four_deals():
    ss = G.initial_states()
    assert len(ss) == 4                                  # (t1,t2) in {0,1}^2
    seen = set()
    for s in ss:
        b = s["board"]
        assert b[0] == 0 and b[1] == 0                   # steps
        assert b[4] == -1 and b[5] == -1                 # no moves yet
        assert b[6] == -1 and b[7] == -1                 # no guesses
        assert b[8] == 0                                 # walking
        assert s["current_player"] == 1
        seen.add((b[2], b[3]))
    assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}

def test_legal_actions_walk_and_final_and_terminal():
    s = {"board": [0, 0, 1, 0, -1, -1, -1, -1, 0], "current_player": 1}
    assert G.legal_actions(s) == [0, 1]                  # walk
    f = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    assert G.legal_actions(f) == [0, 1]                  # final round
    t = {"board": [3, 3, 1, 0, 1, 0, 1, 0, 2], "current_player": 1}
    assert G.legal_actions(t) == []                      # terminal

def test_unsafe_move_is_immediate_loss():
    # P1 type 0 at step 0: safe = 0; playing 1 loses -> P2 wins (status 3)
    s = {"board": [0, 0, 0, 1, -1, -1, -1, -1, 0], "current_player": 1}
    ns = G.apply_action(s, 1)
    assert ns["board"][8] == 3 and G.is_terminal(ns)
    assert G.returns(ns) == {1: -1.0, 2: 1.0}

def test_safe_move_advances_and_records_last_and_purity():
    s = {"board": [0, 0, 1, 0, -1, -1, -1, -1, 0], "current_player": 1}
    before = list(s["board"])
    ns = G.apply_action(s, 1)                            # P1 type 1 step 0: safe = 1
    assert s["board"] == before                          # input unmutated
    assert ns["board"][0] == 1 and ns["board"][4] == 1   # step1, last1
    assert ns["current_player"] == 2 and ns["board"][8] == 0

def test_full_walk_reaches_final_round():
    # T=3, types t1=1, t2=0. Both play safe each step; after 6 safe moves -> final.
    s = G.initial_state_with(1, 0)
    moves = 0
    while s["board"][8] == 0:
        p = s["current_player"]
        k = s["board"][0] if p == 1 else s["board"][1]
        t = s["board"][2] if p == 1 else s["board"][3]
        s = G.apply_action(s, G.safe(k, t))
        moves += 1
    assert moves == 6 and s["board"][8] == 1             # final round
    assert s["current_player"] == 1                      # P1 guesses first

def test_final_round_scoring_p1_wins():
    # both at T=3; t1=1, t2=0; P1 guesses t2=0 (correct), P2 guesses t1=1... make P2 wrong
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    s = G.apply_action(s, 0)                             # P1 guesses 0 == t2 -> correct
    assert s["current_player"] == 2 and s["board"][8] == 1
    s = G.apply_action(s, 0)                             # P2 guesses 0 != t1(1) -> wrong
    assert s["board"][8] == 2 and G.is_terminal(s)       # P1 wins (score 1 vs 0)
    assert G.returns(s) == {1: 1.0, 2: -1.0}

def test_final_round_draw_when_both_correct():
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    s = G.apply_action(s, 0)                             # P1 guesses t2=0 correct
    s = G.apply_action(s, 1)                             # P2 guesses t1=1 correct
    assert s["board"][8] == 4 and G.returns(s) == {1: 0.0, 2: 0.0}

def test_cp_from_board():
    assert G._cp_from_board([0, 0, 0, 0, -1, -1, -1, -1, 0]) == 1
    assert G._cp_from_board([1, 0, 0, 0, 1, -1, -1, -1, 0]) == 2
    assert G._cp_from_board([3, 3, 0, 0, 1, 1, -1, -1, 1]) == 1   # final, 0 guesses
    assert G._cp_from_board([3, 3, 0, 0, 1, 1, 0, -1, 1]) == 2    # final, 1 guess

def test_returns_nonterminal_zero():
    assert G.returns(G.initial_state()) == {1: 0.0, 2: 0.0}
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon.py -q`
Expected: FAIL (`No module named 'cwm.groundtruth.beacon'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/beacon.py`:

```python
"""Beacon — a minimal deep partially-observable game (Claim A witness).

Two players, each with a hidden type t in {0,1} drawn at the deal. Phase 1 (walk):
each player must complete T "safe" steps; the safe action at own step k is
safe(k,t)=(k+t)%2 (depends on the mover's own type), and any other action is an
immediate loss. Random play survives each step w.p. 1/2 so reaches the final round
w.p. (1/2)^{2T}; optimal play reaches it w.p. 1. Phase 2 (final round): each player
guesses the opponent's hidden type (inferable from the opponent's observed moves);
scoring g==t_opponent. Net-chip returns. All chance is in the deal, so apply_action
is deterministic. observation/infer_states/registration are added in Task 2.

board (len 9): [step1, step2, t1, t2, last1, last2, guess1, guess2, status]
status: 0 walking, 1 final round, 2 P1 wins, 3 P2 wins, 4 draw.
"""


class _Beacon:
    def __init__(self, T: int):
        self.T = T

    def safe(self, k: int, t: int) -> int:
        return (k + t) % 2

    def _cp_from_board(self, board: list) -> int:
        if board[8] == 1:                              # final round
            made = (board[6] != -1) + (board[7] != -1)
            return 1 if made % 2 == 0 else 2
        return 1 if (board[0] + board[1]) % 2 == 0 else 2   # walk

    def initial_states(self) -> list:
        out = []
        for t1 in (0, 1):
            for t2 in (0, 1):
                out.append({"board": [0, 0, t1, t2, -1, -1, -1, -1, 0],
                            "current_player": 1})
        return out

    def initial_state(self) -> dict:
        return self.initial_states()[0]

    def initial_state_with(self, t1: int, t2: int) -> dict:
        return {"board": [0, 0, t1, t2, -1, -1, -1, -1, 0], "current_player": 1}

    def is_terminal(self, state: dict) -> bool:
        return state["board"][8] in (2, 3, 4)

    def legal_actions(self, state: dict) -> list:
        if self.is_terminal(state):
            return []
        return [0, 1]

    def apply_action(self, state: dict, action: int) -> dict:
        b = list(state["board"])
        p = state["current_player"]
        opp = 2 if p == 1 else 1
        if b[8] == 1:                                  # final round: a guess
            b[6 if p == 1 else 7] = action
            if b[6] != -1 and b[7] != -1:              # both guessed -> resolve
                s1 = 1 if b[6] == b[3] else 0          # P1 guesses t2
                s2 = 1 if b[7] == b[2] else 0          # P2 guesses t1
                b[8] = 2 if s1 > s2 else 3 if s2 > s1 else 4
                return {"board": b, "current_player": p}
            return {"board": b, "current_player": opp}
        # walk
        k = b[0] if p == 1 else b[1]
        t = b[2] if p == 1 else b[3]
        if action != self.safe(k, t):                  # unsafe -> immediate loss
            b[8] = 3 if p == 1 else 2                   # opponent wins
            return {"board": b, "current_player": opp}
        if p == 1:
            b[0] += 1; b[4] = action
        else:
            b[1] += 1; b[5] = action
        if b[0] == self.T and b[1] == self.T:          # both done -> final round
            b[8] = 1
        return {"board": b, "current_player": opp}

    def returns(self, state: dict) -> dict:
        st = state["board"][8]
        if st == 2:
            return {1: 1.0, 2: -1.0}
        if st == 3:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}                         # draw or non-terminal


def make_beacon(T: int = 8) -> "_Beacon":
    return _Beacon(T)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
git add src/cwm/groundtruth/beacon.py tests/test_beacon.py
git commit -m "feat(games): Beacon core dynamics (survival walk + hidden-type final guess)"
```

---

### Task 2: Beacon imperfect surface (observation, infer_states) + register

**Files:**
- Modify: `src/cwm/groundtruth/beacon.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_beacon.py`

**Interfaces:**
- Consumes: `make_beacon`, `_Beacon`, `_cp_from_board`, `safe` (Task 1).
- Produces: methods `observation(state, player) -> list[int]`, `infer_states(obs_board, player) -> list[dict]` on `_Beacon`; module attributes `RULES_TEXT`, `POLICY_DESCRIPTION`; registered as `"beacon"` in `GAMES` (using a default `make_beacon()` instance).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_beacon.py`:

```python
def test_observation_masks_only_opponent_type():
    s = {"board": [1, 0, 1, 0, 1, -1, -1, -1, 0], "current_player": 1}
    assert G.observation(s, 1) == [1, 0, 1, -1, 1, -1, -1, -1, 0]   # t2 masked
    assert G.observation(s, 2) == [1, 0, -1, 0, 1, -1, -1, -1, 0]   # t1 masked

def test_infer_states_ambiguous_before_opponent_moved():
    # player 1 to infer t2; opponent (P2) has not moved (last2 == -1)
    s = {"board": [1, 0, 1, 0, 1, -1, -1, -1, 0], "current_player": 2}
    obs = G.observation(s, 1)
    inferred = G.infer_states(obs, 1)
    assert sorted(d["board"][3] for d in inferred) == [0, 1]        # both t2
    for d in inferred:
        assert G.observation(d, 1) == obs                           # round-trip
        assert d["board"][2] == 1                                   # own type kept

def test_infer_states_singleton_after_opponent_moved():
    # P2 type 0 has taken 1 step: last2 = safe(0,0) = 0. From obs, infer t2.
    s = {"board": [1, 1, 1, 0, 1, 0, -1, -1, 0], "current_player": 1}
    obs = G.observation(s, 1)
    inferred = G.infer_states(obs, 1)
    assert len(inferred) == 1 and inferred[0]["board"][3] == 0      # t2 recovered
    assert inferred[0]["board"] == s["board"]                       # true state
    assert G.observation(inferred[0], 1) == obs

def test_infer_states_inversion_nonidentity_step2():
    # P2 type 1 took 2 steps: last2 = safe(1,1) = 0. invert: t=(0-2+1)%2 = 1
    s = {"board": [2, 2, 0, 1, 1, 0, -1, -1, 0], "current_player": 1}
    obs = G.observation(s, 1)
    inferred = G.infer_states(obs, 1)
    assert len(inferred) == 1 and inferred[0]["board"][3] == 1

def test_true_state_always_member():
    g = B.make_beacon(T=4)
    s = g.initial_state_with(1, 1)
    rng_actions = [g.safe(0, 1), g.safe(0, 1)]                      # P1, P2 one step each
    for a in rng_actions:
        s = g.apply_action(s, a)
    for player in (1, 2):
        obs = g.observation(s, player)
        assert any(d["board"] == s["board"] for d in g.infer_states(obs, player))

def test_beacon_registered():
    from cwm.games import GAMES
    assert "beacon" in GAMES["beacon"].rules_text.lower()
    assert GAMES["beacon"].module.T == 8
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon.py -k "observation or infer or member or registered" -q`
Expected: FAIL (`'_Beacon' object has no attribute 'observation'`)

- [ ] **Step 3: Implement** — add these methods to the `_Beacon` class in `src/cwm/groundtruth/beacon.py` (insert after `returns`):

```python
    def observation(self, state: dict, player: int) -> list:
        b = list(state["board"])
        b[3 if player == 1 else 2] = -1            # mask opponent's type
        return b

    def infer_states(self, obs_board: list, player: int) -> list:
        obs = list(obs_board)
        opp_idx = 3 if player == 1 else 2          # opponent type slot
        last_opp = obs[5] if player == 1 else obs[4]
        step_opp = obs[1] if player == 1 else obs[0]
        cp = self._cp_from_board(obs)
        if last_opp == -1:                         # opponent not moved -> ambiguous
            candidates = [0, 1]
        else:                                      # invert safe(step_opp-1, t)=last_opp
            candidates = [(last_opp - step_opp + 1) % 2]
        out = []
        for t in candidates:
            s = list(obs)
            s[opp_idx] = t
            out.append({"board": s, "current_player": cp})
        return out
```

- [ ] **Step 4: Add module-level text and registration.** Append to `src/cwm/groundtruth/beacon.py` (after the `make_beacon` function):

```python
RULES_TEXT = """\
This game is Beacon (2 players), a survival walk followed by a hidden-type guess.
  - Each player has a hidden type t in {0,1}, fixed at the start.
  - board has 9 integers: [step1, step2, t1, t2, last1, last2, guess1, guess2,
    status]. status: 0 walking, 1 final round, 2 player 1 wins, 3 player 2 wins,
    4 draw. last_i is a player's most recent move (-1 if none); guess_i is their
    final guess (-1 if none).
  - Walk: players alternate (player 1 first). On your turn at your own step index k
    (= your completed safe steps), the actions are 0 and 1; the SAFE action is
    (k + your_type) % 2. Playing the safe action advances you by one step and records
    it in last_i. Playing the other action loses immediately (the opponent wins).
  - When both players have completed T safe steps, the game enters the final round.
  - Final round: players alternate (player 1 first) committing a guess in {0,1}.
    You score 1 if your guess equals the OPPONENT's hidden type, else 0. The higher
    score wins; equal scores draw. returns are net chips (+1 win, -1 loss, 0 draw).
  - Imperfect information: you see your own type and every player's public moves
    (last_i) and the full betting/guess state, but NOT the opponent's type label —
    which is recoverable from their observed moves, since a move at step k by a
    player of type t is (k + t) % 2.
"""

POLICY_DESCRIPTION = (
    "You play Beacon. board = [step1, step2, t1, t2, last1, last2, guess1, guess2, "
    "status]. In the walk, play the safe action (k+your_type)%2 to survive. In the "
    "final round, guess the opponent's hidden type (deducible from their moves).")
```

- [ ] **Step 5: Register in `src/cwm/games.py`** — extend the import line and add the entry (match the existing `kuhn`/`leduc` style; `beacon` is registered via a default `make_beacon()` instance):

```python
from .groundtruth import (tictactoe, connect_four, gen_tictactoe, gen_chess,
                          trike, gen_chess_material, kuhn_poker, leduc_poker, beacon)
```

```python
    "beacon": GameSpec(
        name="beacon",
        module=beacon.make_beacon(),
        rules_text=beacon.RULES_TEXT,
        policy_description=beacon.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 6: Run tests to verify pass**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon.py tests/test_games.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
git add src/cwm/groundtruth/beacon.py src/cwm/games.py tests/test_beacon.py
git commit -m "feat(games): Beacon imperfect surface (observation, infer_states) + register"
```

---

### Task 3: Claim A instrument + experiment driver

**Files:**
- Create: `src/cwm/beacon_instrument.py`
- Create: `scripts/beacon_claimA.py`
- Test: `tests/test_beacon_instrument.py`

**Interfaces:**
- Consumes: `cwm.groundtruth.beacon` (`make_beacon`, `_Beacon`), `cwm.determinized` (`determinized_policy`, `imperfect_arena`), `cwm.gap.inference_accuracy`, `cwm.law.danger`.
- Produces:
  - `src/cwm/beacon_instrument.py`: `BeaconWrongInference(T=8)` — delegates the whole contract to a `make_beacon(T)` truth EXCEPT `infer_states`, which at final-round states (`status==1`) returns the FLIPPED opponent type (a singleton inconsistent with the observation); everywhere else it equals the truth. Helpers `infoset_key(model, board, player)`, `random_reach_final_rate(model, n_games, seed)`.
  - `scripts/beacon_claimA.py`: the driver (gate-on-random, play vs fair baseline, danger-vs-T).

- [ ] **Step 1: Write the failing tests** — create `tests/test_beacon_instrument.py`:

```python
from cwm.beacon_instrument import BeaconWrongInference, random_reach_final_rate
from cwm.groundtruth import beacon as B

T = 3
truth = B.make_beacon(T)
inst = BeaconWrongInference(T)

def test_instrument_delegates_dynamics():
    s = truth.initial_state_with(1, 0)
    assert inst.legal_actions(s) == truth.legal_actions(s)
    assert inst.apply_action(s, truth.safe(0, 1)) == truth.apply_action(s, truth.safe(0, 1))
    assert inst.is_terminal(s) == truth.is_terminal(s)
    assert inst.initial_states() == truth.initial_states()
    assert inst.observation(s, 1) == truth.observation(s, 1)

def test_instrument_correct_on_walk_states():
    # walk state (status 0): inference equals the truth
    s = {"board": [1, 1, 1, 0, 1, 0, -1, -1, 0], "current_player": 1}
    obs = inst.observation(s, 1)
    assert inst.infer_states(obs, 1) == truth.infer_states(obs, 1)

def test_instrument_flips_type_on_final_round():
    # final-round state (status 1): P2 type 0 moved (last2=0 at T=3 -> safe(2,0)=0)
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    obs = inst.observation(s, 1)
    truth_inf = truth.infer_states(obs, 1)
    wrong_inf = inst.infer_states(obs, 1)
    assert truth_inf[0]["board"][3] == 0                  # truth: t2 = 0
    assert wrong_inf[0]["board"][3] == 1                  # instrument flips to 1
    assert len(wrong_inf) == 1

def test_random_reach_final_rate_is_tiny():
    # P(random reaches final) = (1/2)^{2T}; at T=3 that's 1/64 ~ 0.0156. Sample loosely.
    rate = random_reach_final_rate(truth, n_games=4000, seed=0)
    assert rate < 0.05
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon_instrument.py -q`
Expected: FAIL (`No module named 'cwm.beacon_instrument'`)

- [ ] **Step 3: Implement the instrument** — create `src/cwm/beacon_instrument.py`:

```python
"""Claim A instrument for Beacon: identical to the true game EXCEPT its inference
function is wrong only at final-round states (status==1) — the deep region D that
competent play reaches but a random-trajectory gate almost never does. There it
returns the FLIPPED opponent type, a singleton inconsistent with the observed
history. On every walk state it equals the truth, so a random-sampled gate (which
dies in the walk) certifies it; yet at the final round the determinized planner acts
on the flipped belief and guesses wrong, losing at play.
"""
import random

from .groundtruth import beacon as B


class BeaconWrongInference:
    def __init__(self, T: int = 8):
        self.T = T
        self._truth = B.make_beacon(T)
        # delegate the deterministic contract surface
        self.safe = self._truth.safe
        self._cp_from_board = self._truth._cp_from_board
        self.initial_state = self._truth.initial_state
        self.initial_states = self._truth.initial_states
        self.initial_state_with = self._truth.initial_state_with
        self.is_terminal = self._truth.is_terminal
        self.legal_actions = self._truth.legal_actions
        self.apply_action = self._truth.apply_action
        self.returns = self._truth.returns
        self.observation = self._truth.observation

    def infer_states(self, obs_board, player):
        inferred = self._truth.infer_states(obs_board, player)
        if obs_board[8] == 1 and len(inferred) == 1:      # final round D: flip
            opp_idx = 3 if player == 1 else 2
            s = list(obs_board)
            s[opp_idx] = 1 - inferred[0]["board"][opp_idx]
            return [{"board": s, "current_player": self._cp_from_board(obs_board)}]
        return inferred


def infoset_key(model, board, player):
    return tuple(model.observation({"board": list(board),
                                    "current_player": player}, player))


def random_reach_final_rate(model, n_games: int, seed: int) -> float:
    rng = random.Random(seed)
    deals = model.initial_states()
    reached = 0
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            if s["board"][8] == 1:                        # entered final round
                reached += 1
                break
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return reached / n_games
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_beacon_instrument.py -q`
Expected: PASS

- [ ] **Step 5: Write the driver** — create `scripts/beacon_claimA.py`:

```python
"""Claim A for imperfect information (Beacon), CPU only. The provable witness:
a CWM whose inference is wrong only on the final-round region D passes a random
inference gate yet loses at play.

(1) Gate: instrument inference matches truth on random-play states (D unreached).
(2) Play: instrument loses vs the fair truth-vs-truth baseline, CI-separated.
(3) Danger vs T: measured gate-miss rate vs the exact (1-(1/2)^{2T})^N.

Run: PYTHONPATH=src python scripts/beacon_claimA.py
"""
import json
import random
from pathlib import Path

from cwm.groundtruth import beacon as B
from cwm.beacon_instrument import BeaconWrongInference, random_reach_final_rate
from cwm.determinized import imperfect_arena
from cwm.law import danger

T = 8
SIMS = 100
N_GAMES = 400
SEEDS = [0, 1, 2]
GATE_GAMES = 2000


def gate_mismatches_on_random(truth, inst, n_games, seed):
    """Fraction of random-play (state,player) inferences where instrument != truth."""
    rng = random.Random(seed)
    deals = truth.initial_states()
    checks = mismatches = 0
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not truth.is_terminal(s):
            for p in (1, 2):
                obs = truth.observation(s, p)
                checks += 1
                if inst.infer_states(obs, p) != truth.infer_states(obs, p):
                    mismatches += 1
            s = truth.apply_action(s, rng.choice(truth.legal_actions(s)))
    return mismatches, checks


def main():
    Path("results").mkdir(exist_ok=True)
    truth = B.make_beacon(T)
    inst = BeaconWrongInference(T)
    out = {"T": T}

    # (1) gate on random-play states
    mm, ch = gate_mismatches_on_random(truth, inst, GATE_GAMES, seed=0)
    reach = random_reach_final_rate(truth, GATE_GAMES, seed=0)
    out["gate"] = {"mismatches": mm, "checks": ch, "random_reach_final_rate": reach}
    print(f"gate: instrument mismatches on random sample = {mm}/{ch}; "
          f"random reaches final at rate {reach:.5f}", flush=True)

    # (2) play vs fair baseline
    fair = imperfect_arena(truth, truth, truth, simulations=SIMS, n_games=N_GAMES,
                           seeds=SEEDS, n_determinizations=2)
    play = imperfect_arena(truth, inst, truth, simulations=SIMS, n_games=N_GAMES,
                           seeds=SEEDS, n_determinizations=2)
    out["play"] = {"fair_winrate": fair["a_winrate"], "fair_ci": [fair["lo"], fair["hi"]],
                   "instrument_winrate": play["a_winrate"],
                   "instrument_ci": [play["lo"], play["hi"]],
                   "instrument_net": play["a_net"], "n": play["n"]}
    print(f"play: fair={fair['a_winrate']:.3f}[{fair['lo']:.3f},{fair['hi']:.3f}] "
          f"instrument={play['a_winrate']:.3f}[{play['lo']:.3f},{play['hi']:.3f}] "
          f"net={play['a_net']:.1f}", flush=True)

    # (3) danger vs T: exact gate-miss factor against measured reach
    cost = max(0.0, fair["a_winrate"] - play["a_winrate"])
    rows = []
    for t in (4, 6, 8, 10):
        eps = (0.5) ** (2 * t)
        miss = (1 - eps) ** GATE_GAMES
        rows.append({"T": t, "eps": eps, "gate_miss_prob": miss,
                     "danger": danger(cost, eps, GATE_GAMES)})
        print(f"danger T={t}: eps={eps:.2e} gate_miss={miss:.3f} "
              f"danger={danger(cost, eps, GATE_GAMES):.4f}", flush=True)
    out["danger_curve"] = {"play_cost": cost, "rows": rows}

    Path("results/beacon_claimA.json").write_text(json.dumps(out, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Smoke-run the driver at tiny settings**

Run:
```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
PYTHONPATH=src python -c "
import scripts.beacon_claimA as D
D.T=4; D.SIMS=20; D.N_GAMES=8; D.SEEDS=[0]; D.GATE_GAMES=200
D.main(); print('SMOKE OK')
" 2>&1 | tail -8
```
Expected: prints gate/play/danger lines, writes `results/beacon_claimA.json`, ends `SMOKE OK`. (Numbers are noisy at this size — this only checks the code path. The instrument's mismatches on the random sample should already be small or zero.)

- [ ] **Step 7: Run the full suite**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
git add src/cwm/beacon_instrument.py scripts/beacon_claimA.py tests/test_beacon_instrument.py
git commit -m "feat: Beacon Claim A instrument + experiment driver"
```

---

## Post-implementation (manual, CPU)

1. Non-triviality: confirm determinized MCTS (competent) survives the walk and beats
   a random agent (which dies in the walk), and that the fair truth-vs-truth baseline
   is ≈ 0.5 (all draws — both guess correctly).
2. Full Claim A run: `PYTHONPATH=src python scripts/beacon_claimA.py` at proper
   settings (T=8, SIMS=100, N_GAMES=400, SEEDS=[0,1,2,3], GATE_GAMES=2000). Expect:
   instrument inference mismatches on the random sample ≈ 0 (gate-blind, since random
   almost never reaches the final round); instrument play winrate well below the fair
   0.5 with a separated Wilson CI (near-deterministic loss). If the planner does not
   convert correct inference into the winning guess (e.g. too few simulations or
   determinizations), raise SIMS / n_determinizations and report honestly.
3. Write results into `docs/EXPERIMENTS.md`; update RESEARCH-DIRECTION and the
   preprint skeleton §6 (the positive imperfect-info result + the instantiated bound).
```
