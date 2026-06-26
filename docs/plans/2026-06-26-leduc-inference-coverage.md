# Leduc Poker + Inference Coverage-Gap (Claim A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Leduc poker oracle (imperfect-info contract) and an experiment driver that demonstrates Claim A: a CWM whose inference function passes a random-trajectory gate still loses at play because its inference is wrong on the competent-play info-sets random sampling under-covers.

**Architecture:** Leduc oracle reuses the imperfect contract (`observation`/`infer_states`/`initial_states`); cards are physical ids 0..5 with rank=id//2 so deck multiplicity is automatic. All chance is in the deal (community pre-dealt, hidden until round 1) so `apply_action` is deterministic. The experiment reuses `determinized_policy`/`imperfect_arena`/`inference_accuracy`/`wilson_ci`/`danger`; the Claim A "instrument" is the truth wrapped with an inference error confined to a competent-tail predicate (CPU only — no LLM needed for the core result).

**Tech Stack:** Python 3, pytest, existing `cwm` package. No new dependencies.

## Global Constraints

- State `{"board": list[int], "current_player": int}`, `current_player ∈ {1,2}`; hidden info in `board`. Imperfect-info `returns` are real-valued net chips.
- Cards are physical ids `0..5`; **rank(id) = id // 2** (ids 0,1=J; 2,3=Q; 4,5=K; value J<Q<K). Deck = ids `0..5` (two per rank automatically).
- board (length 9): `[p1_id, p2_id, community_id, round, committed_p1, committed_p2, raises_round, acted_round, status]`. community is dealt at start but hidden until round 1. status: 0 ongoing, 1 folded, 2 showdown.
- Antes 1 each (committeds start 1,1). Bet size **2** in round 0, **4** in round 1. Max **2 raises per round**. Actions: **0=fold, 1=check/call, 2=raise**. Fold legal only when facing a bet.
- `current_player` for a non-terminal state is derivable: `1 if acted_round % 2 == 0 else 2` (turns alternate within a round; P1 acts first each round).
- On a fold, `apply_action` sets `current_player` to the WINNER (the non-folder); `returns` reads it to identify the folder.
- Showdown: a private card pairing the community (rank equal) beats a non-pair; else higher private rank wins; equal private rank splits (0/0). At showdown committeds are equal.
- Reuses `cwm.determinized` (`determinized_policy`, `imperfect_arena`), `cwm.gap.inference_accuracy`, `cwm.law` (`wilson_ci`, `danger`). Perfect-info games unaffected.
- `results/` is git-ignored.

---

### Task 1: Leduc core dynamics

**Files:**
- Create: `src/cwm/groundtruth/leduc_poker.py`
- Test: `tests/test_leduc_poker.py`

**Interfaces:**
- Produces: `DECK`, `_rank(card)`, `_bet_size(round)`, `_other(p)`, `_cp_from_board(board)`, `initial_state()`, `initial_states()`, `is_terminal(state)`, `legal_actions(state)`, `apply_action(state, action)`, `_showdown_winner(board)`, `returns(state)`. (observation/infer_states/RULES_TEXT come in Task 2.)

- [ ] **Step 1: Write the failing tests** — create `tests/test_leduc_poker.py`:

```python
from cwm.groundtruth import leduc_poker as L

def test_initial_states_distinct_deals():
    ss = L.initial_states()
    assert len(ss) == 6 * 5 * 4                      # ordered (p1,p2,comm) distinct ids
    for s in ss:
        b = s["board"]
        assert len({b[0], b[1], b[2]}) == 3          # three distinct physical cards
        assert b[3] == 0 and b[4] == 1 and b[5] == 1 # round 0, antes
        assert b[6] == 0 and b[7] == 0 and b[8] == 0
        assert s["current_player"] == 1

def test_legal_actions_opening_no_fold():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    assert L.legal_actions(s) == [1, 2]              # check or raise; no fold with no bet

def test_legal_actions_facing_bet():
    # P1 raised in round 0: committed 3 vs 1, P2 to act
    s = {"board": [0, 2, 4, 0, 3, 1, 1, 1, 0], "current_player": 2}
    assert L.legal_actions(s) == [0, 1, 2]           # fold, call, raise

def test_raise_cap():
    s = {"board": [0, 2, 4, 0, 5, 3, 2, 2, 0], "current_player": 2}  # 2 raises done
    assert L.legal_actions(s) == [0, 1]              # no further raise

def test_apply_action_pure_and_raise_bookkeeping():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    before = list(s["board"])
    ns = L.apply_action(s, 2)                        # P1 raises (bet 2)
    assert s["board"] == before                      # input unmutated
    assert ns["board"][4] == 3 and ns["board"][6] == 1 and ns["board"][7] == 1
    assert ns["current_player"] == 2

def test_check_check_advances_to_round1():
    s = {"board": [0, 2, 4, 0, 1, 1, 0, 0, 0], "current_player": 1}
    s = L.apply_action(s, 1)                          # P1 check
    assert s["current_player"] == 2 and s["board"][3] == 0
    s = L.apply_action(s, 1)                          # P2 check -> round 1
    assert s["board"][3] == 1 and s["board"][6] == 0 and s["board"][7] == 0
    assert s["current_player"] == 1 and not L.is_terminal(s)

def test_call_closes_round0_then_round1_showdown():
    s = {"board": [4, 0, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}  # P1=K id4, P2=J id0, comm=Q id2
    s = L.apply_action(s, 2)                          # P1 raise
    s = L.apply_action(s, 1)                          # P2 call -> round 1, committeds 3,3
    assert s["board"][3] == 1 and s["board"][4] == 3 and s["board"][5] == 3
    s = L.apply_action(s, 1)                          # P1 check
    s = L.apply_action(s, 1)                          # P2 check -> showdown
    assert s["board"][8] == 2 and L.is_terminal(s)
    assert L.returns(s) == {1: 3.0, 2: -3.0}         # K beats J, no pair, winner +3

def test_fold_returns():
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}  # P1=J id0
    s = L.apply_action(s, 2)                          # P1 raise -> committed 3
    assert s["current_player"] == 2
    s = L.apply_action(s, 0)                          # P2 folds
    assert s["board"][8] == 1 and L.is_terminal(s)
    assert s["current_player"] == 1                  # winner = P1
    assert L.returns(s) == {1: 1.0, 2: -1.0}         # P2 folded, committed 1

def test_showdown_pair_beats_high_card():
    # P1=J(id0), community=J(id1) -> P1 pairs; P2=K(id4)
    b = [0, 4, 1, 1, 3, 3, 0, 2, 2]                   # round1 showdown, committeds 3,3
    s = {"board": b, "current_player": 1}
    assert L.returns(s) == {1: 3.0, 2: -3.0}         # pair beats high card

def test_showdown_equal_rank_splits():
    # P1=J(id0), P2=J(id1), community=K(id4) -> equal rank, no pair -> split
    b = [0, 1, 4, 1, 3, 3, 0, 2, 2]
    s = {"board": b, "current_player": 1}
    assert L.returns(s) == {1: 0.0, 2: 0.0}

def test_returns_nonterminal_zero():
    assert L.returns(L.initial_state()) == {1: 0.0, 2: 0.0}

def test_cp_from_board():
    assert L._cp_from_board([0, 2, 4, 0, 1, 1, 0, 0, 0]) == 1
    assert L._cp_from_board([0, 2, 4, 0, 3, 1, 1, 1, 0]) == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_leduc_poker.py -q`
Expected: FAIL (`No module named 'cwm.groundtruth.leduc_poker'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/leduc_poker.py`:

```python
"""Leduc poker oracle — imperfect-information contract (core dynamics).

Cards are physical ids 0..5; rank(id)=id//2 (0,1=J;2,3=Q;4,5=K), value J<Q<K.
board (len 9): [p1_id, p2_id, community_id, round, committed_p1, committed_p2,
raises_round, acted_round, status]. community is dealt at start but hidden until
round 1. status: 0 ongoing, 1 folded, 2 showdown. Antes 1; bet 2 (round 0)/4
(round 1); max 2 raises/round. Actions: 0 fold, 1 check/call, 2 raise. returns are
NET CHIPS. observation/infer_states are added in the imperfect surface (same file).
"""
DECK = (0, 1, 2, 3, 4, 5)


def _rank(card: int) -> int:
    return card // 2


def _bet_size(rnd: int) -> int:
    return 2 if rnd == 0 else 4


def _other(p: int) -> int:
    return 2 if p == 1 else 1


def _cp_from_board(board: list) -> int:
    return 1 if board[7] % 2 == 0 else 2


def initial_states() -> list:
    out = []
    for p1 in DECK:
        for p2 in DECK:
            if p2 == p1:
                continue
            for comm in DECK:
                if comm == p1 or comm == p2:
                    continue
                out.append({"board": [p1, p2, comm, 0, 1, 1, 0, 0, 0],
                            "current_player": 1})
    return out


def initial_state() -> dict:
    return initial_states()[0]


def is_terminal(state: dict) -> bool:
    return state["board"][8] != 0


def legal_actions(state: dict) -> list:
    if is_terminal(state):
        return []
    b = state["board"]
    outstanding = b[4] != b[5]
    acts = [0, 1] if outstanding else [1]     # fold only when facing a bet
    if b[6] < 2:
        acts.append(2)
    return acts


def apply_action(state: dict, action: int) -> dict:
    b = list(state["board"])
    p = state["current_player"]
    opp = _other(p)
    rnd = b[3]
    bet = _bet_size(rnd)
    ci, oi = (4, 5) if p == 1 else (5, 4)     # committed indices for p, opp
    pre_acted = b[7]
    b[7] = pre_acted + 1
    if action == 0:                            # fold
        b[8] = 1
        return {"board": b, "current_player": opp}   # current_player = winner
    if action == 2:                            # raise: match then add bet
        b[ci] = b[oi] + bet
        b[6] += 1
        return {"board": b, "current_player": opp}   # round continues
    # action == 1: check or call
    outstanding = b[4] != b[5]
    if outstanding:                            # call closes the round
        b[ci] = b[oi]
        round_ends = True
    else:                                      # check; closes only if not the opener
        round_ends = pre_acted >= 1
    if not round_ends:
        return {"board": b, "current_player": opp}
    if rnd == 0:                               # advance to round 1
        b[3] = 1
        b[6] = 0
        b[7] = 0
        return {"board": b, "current_player": 1}
    b[8] = 2                                    # round 1 ended -> showdown
    return {"board": b, "current_player": opp}


def _showdown_winner(board: list) -> int:
    r1, r2, rc = _rank(board[0]), _rank(board[1]), _rank(board[2])
    p1pair, p2pair = (r1 == rc), (r2 == rc)
    if p1pair and not p2pair:
        return 1
    if p2pair and not p1pair:
        return 2
    if r1 > r2:
        return 1
    if r2 > r1:
        return 2
    return 0                                    # equal rank (incl. both pair) -> split


def returns(state: dict) -> dict:
    b = state["board"]
    if b[8] == 0:
        return {1: 0.0, 2: 0.0}
    if b[8] == 1:                               # fold: current_player is the winner
        winner = state["current_player"]
        folder = _other(winner)
        amt = float(b[4] if folder == 1 else b[5])
        return {winner: amt, folder: -amt}
    w = _showdown_winner(b)                      # showdown: committeds equal
    if w == 0:
        return {1: 0.0, 2: 0.0}
    amt = float(b[4])
    return {w: amt, _other(w): -amt}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leduc_poker.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/groundtruth/leduc_poker.py tests/test_leduc_poker.py
git commit -m "feat(games): Leduc poker core dynamics (betting tree + showdown)"
```

---

### Task 2: Leduc imperfect surface (observation, infer_states) + register

**Files:**
- Modify: `src/cwm/groundtruth/leduc_poker.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_leduc_poker.py`

**Interfaces:**
- Consumes: `DECK`, `_cp_from_board` (Task 1).
- Produces: `observation(state, player) -> list[int]`, `infer_states(obs_board, player) -> list[dict]`, `RULES_TEXT`, `POLICY_DESCRIPTION`; registered as `"leduc"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_leduc_poker.py`:

```python
def test_observation_masks_opponent_and_round0_community():
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}
    assert L.observation(s, 1) == [0, -1, -1, 0, 1, 1, 0, 0, 0]   # P2 + community hidden
    assert L.observation(s, 2) == [-1, 4, -1, 0, 1, 1, 0, 0, 0]

def test_observation_reveals_community_in_round1():
    s = {"board": [0, 4, 2, 1, 3, 3, 0, 0, 0], "current_player": 1}
    assert L.observation(s, 1) == [0, -1, 2, 1, 3, 3, 0, 0, 0]    # community visible

def test_infer_states_round0_spans_opponent_and_community():
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}
    obs = L.observation(s, 1)
    inferred = L.infer_states(obs, 1)
    # remaining ids = {1,2,3,4,5}; ordered (opp,comm) distinct = 5*4 = 20
    assert len(inferred) == 20
    assert any(d["board"] == s["board"] for d in inferred)        # true state member
    for d in inferred:
        assert L.observation(d, 1) == obs                          # round-trip
        assert d["board"][0] == 0                                  # own card kept
        assert len({d["board"][0], d["board"][1], d["board"][2]}) == 3
        assert d["current_player"] == 1

def test_infer_states_round1_spans_opponent_only():
    s = {"board": [0, 4, 2, 1, 3, 3, 0, 0, 0], "current_player": 1}
    obs = L.observation(s, 1)
    inferred = L.infer_states(obs, 1)
    # remaining ids = {1,3,5} (exclude own 0 and community 2) -> 3 opponents
    assert len(inferred) == 3
    for d in inferred:
        assert d["board"][2] == 2                                  # community fixed
        assert L.observation(d, 1) == obs

def test_leduc_registered():
    from cwm.games import GAMES
    assert GAMES["leduc"].module is L
    assert "leduc" in GAMES["leduc"].rules_text.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_leduc_poker.py -k "observation or infer or registered" -q`
Expected: FAIL (`module 'cwm.groundtruth.leduc_poker' has no attribute 'observation'`)

- [ ] **Step 3: Implement** — append to `src/cwm/groundtruth/leduc_poker.py`:

```python
def observation(state: dict, player: int) -> list:
    b = list(state["board"])
    if player == 1:
        b[1] = -1                              # hide opponent's card
    else:
        b[0] = -1
    if b[3] == 0:                              # community hidden until round 1
        b[2] = -1
    return b


def infer_states(obs_board: list, player: int) -> list:
    obs = list(obs_board)
    own = obs[0] if player == 1 else obs[1]
    visible = {own}
    if obs[2] != -1:                           # community already public (round 1)
        visible.add(obs[2])
    remaining = [c for c in DECK if c not in visible]
    cp = _cp_from_board(obs)
    out = []
    opp_idx = 1 if player == 1 else 0
    if obs[2] == -1:                           # round 0: hidden = opponent + community
        for opp in remaining:
            for comm in remaining:
                if comm == opp:
                    continue
                s = list(obs)
                s[opp_idx] = opp
                s[2] = comm
                out.append({"board": s, "current_player": cp})
    else:                                      # round 1: hidden = opponent only
        for opp in remaining:
            s = list(obs)
            s[opp_idx] = opp
            out.append({"board": s, "current_player": cp})
    return out


RULES_TEXT = """\
This game is Leduc poker (2 players).
  - Cards are physical ids 0..5; the rank is id//2 (ids 0,1 = J, 2,3 = Q, 4,5 = K),
    with J < Q < K. The deck is the six ids 0..5 (two cards per rank).
  - board has 9 integers: [p1_id, p2_id, community_id, round, committed_p1,
    committed_p2, raises_round, acted_round, status]. The community card is dealt at
    the start but is hidden until round 1. status: 0 ongoing, 1 a player folded,
    2 showdown.
  - Each player antes 1. There are two betting rounds: round 0 (bet size 2), then
    the community card becomes visible, then round 1 (bet size 4). Max 2 raises per
    round. Actions: 0 = fold, 1 = check/call, 2 = raise. Fold is legal only when
    facing a bet (committeds unequal).
  - A round ends when a bet is called or both players check; the round-0 end reveals
    the community card and starts round 1; the round-1 end is a showdown.
  - Showdown: a private card whose rank equals the community rank (a pair) beats a
    non-pair; otherwise the higher private rank wins; equal private ranks split.
  - returns are net chips: the winner gains the loser's committed amount; a split is
    0/0. On a fold the folder loses what they committed.
  - Imperfect information: a player sees only their own card, the public betting
    state, and the community card once round 1 has begun.
"""

POLICY_DESCRIPTION = (
    "You play Leduc poker. board = [p1_id, p2_id, community_id, round, committed_p1, "
    "committed_p2, raises_round, acted_round, status]; rank = id//2 (J<Q<K). You see "
    "only your own card, the betting state, and the community card from round 1. "
    "Actions: 0 fold, 1 check/call, 2 raise.")
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — extend the import line and add the entry:

```python
from .groundtruth import (tictactoe, connect_four, gen_tictactoe, gen_chess,
                          trike, gen_chess_material, kuhn_poker, leduc_poker)
```

```python
    "leduc": GameSpec(
        name="leduc",
        module=leduc_poker,
        rules_text=leduc_poker.RULES_TEXT,
        policy_description=leduc_poker.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Run tests to verify pass**

Run: `python -m pytest tests/test_leduc_poker.py tests/test_games.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/cwm/groundtruth/leduc_poker.py src/cwm/games.py tests/test_leduc_poker.py
git commit -m "feat(games): Leduc imperfect surface (observation, infer_states) + register"
```

---

### Task 3: Coverage-gap experiment driver (Claim A)

**Files:**
- Create: `src/cwm/leduc_instrument.py`
- Create: `scripts/leduc_coverage.py`
- Test: `tests/test_leduc_instrument.py`

**Interfaces:**
- Consumes: `cwm.groundtruth.leduc_poker`, `cwm.determinized` (`determinized_policy`, `imperfect_arena`), `cwm.gap.inference_accuracy`, `cwm.mcts.mcts_policy`.
- Produces:
  - `src/cwm/leduc_instrument.py`: `WrongInference` — a model equal to `leduc_poker` except `infer_states` drops one consistent opponent assignment **only on a competent-tail predicate** (`_is_tail(board)` = round 1 with committeds above the ante, i.e. a line that involved a raise). It exposes the full contract by delegating to `leduc_poker`.
  - helpers `competent_infosets(model, n_games, sims, seed) -> set`, `random_infoset_coverage(model, n_games, seed) -> set`, `infoset_key(board, player)`.
- The driver `scripts/leduc_coverage.py` runs: coverage gap, the instrument's gate pass on random-sampled states, its play loss vs truth, and the danger-vs-N table.

- [ ] **Step 1: Write the failing tests** — create `tests/test_leduc_instrument.py`:

```python
from cwm.leduc_instrument import WrongInference, _is_tail
from cwm.groundtruth import leduc_poker as L

def test_wronginference_delegates_dynamics():
    w = WrongInference()
    s = L.initial_state()
    assert w.legal_actions(s) == L.legal_actions(s)
    assert w.apply_action(s, 1) == L.apply_action(s, 1)
    assert w.is_terminal(s) == L.is_terminal(s)
    assert w.initial_states() == L.initial_states()

def test_wronginference_correct_off_tail_round0():
    # round 0 (no tail): inference equals the truth
    w = WrongInference()
    s = {"board": [0, 4, 2, 0, 1, 1, 0, 0, 0], "current_player": 1}
    obs = w.observation(s, 1)
    assert w.infer_states(obs, 1) == L.infer_states(obs, 1)

def test_wronginference_wrong_on_tail():
    # round 1 with a raise (committeds 7,7 > ante) -> tail -> drops one state
    w = WrongInference()
    board = [0, 4, 2, 1, 7, 7, 0, 0, 0]
    assert _is_tail(board) is True
    obs = w.observation({"board": board, "current_player": 1}, 1)
    truth_inf = L.infer_states(obs, 1)
    wrong_inf = w.infer_states(obs, 1)
    assert len(wrong_inf) == len(truth_inf) - 1          # one consistent state dropped
    assert all(d in truth_inf for d in wrong_inf)         # remaining are still valid

def test_tail_predicate_excludes_cheap_lines():
    assert _is_tail([0, 4, 2, 1, 1, 1, 0, 0, 0]) is False   # round 1 but only antes
    assert _is_tail([0, 4, 2, 0, 7, 7, 0, 0, 0]) is False   # round 0 never tail
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_leduc_instrument.py -q`
Expected: FAIL (`No module named 'cwm.leduc_instrument'`)

- [ ] **Step 3: Implement the instrument** — create `src/cwm/leduc_instrument.py`:

```python
"""Claim A instrument for Leduc: a model identical to the true game EXCEPT its
inference function is wrong on a competent-play tail (states reached only after a
raise in round 1) that random-play sampling rarely covers. It is membership-correct
where the random gate looks, so it passes the gate, yet misplans where competent
play actually goes — the imperfect-info analogue of the rare-rule instrument.
"""
import random

from .groundtruth import leduc_poker as L
from .mcts import mcts_policy
from .determinized import determinized_policy


def _is_tail(board: list) -> bool:
    """A competent-only info-set: round 1 reached via a raise (committeds above the
    ante of 1). Random play rarely raises into round 1, so the gate under-covers it."""
    return board[3] == 1 and (board[4] > 1 or board[5] > 1)


class WrongInference:
    """Delegates the whole contract to leduc_poker, but corrupts infer_states on
    tail info-sets by dropping one consistent opponent assignment."""
    initial_state = staticmethod(L.initial_state)
    initial_states = staticmethod(L.initial_states)
    legal_actions = staticmethod(L.legal_actions)
    apply_action = staticmethod(L.apply_action)
    is_terminal = staticmethod(L.is_terminal)
    returns = staticmethod(L.returns)
    observation = staticmethod(L.observation)

    @staticmethod
    def infer_states(obs_board, player):
        inferred = L.infer_states(obs_board, player)
        if _is_tail(obs_board) and len(inferred) > 1:
            return inferred[:-1]              # drop one consistent state on the tail
        return inferred


def infoset_key(board: list, player: int):
    return tuple(L.observation({"board": list(board), "current_player": player}, player))


def random_infoset_coverage(model, n_games: int, seed: int) -> set:
    rng = random.Random(seed)
    deals = model.initial_states()
    covered = set()
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            covered.add(infoset_key(s["board"], s["current_player"]))
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return covered


def competent_infosets(model, n_games: int, sims: int, seed: int) -> set:
    rng = random.Random(seed)
    deals = model.initial_states()
    visited = set()
    for i in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not model.is_terminal(s):
            visited.add(infoset_key(s["board"], s["current_player"]))
            a = determinized_policy(model, s, n_determinizations=8,
                                    simulations=sims, seed=seed + i * 1000)
            if a not in model.legal_actions(s):
                a = model.legal_actions(s)[0]
            s = model.apply_action(s, a)
    return visited
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leduc_instrument.py -q`
Expected: PASS

- [ ] **Step 5: Write the driver** — create `scripts/leduc_coverage.py`:

```python
"""Claim A for imperfect information (Leduc). CPU only.

(1) Coverage gap: competent-play info-sets not covered by N random-play trajectories.
(2) The WrongInference instrument passes the random-sampled inference gate yet
    loses at play vs the truth (Wilson-CI-separated).
(3) Danger vs N: play_cost x P(tail info-set absent from N random samples).

Run: PYTHONPATH=src python scripts/leduc_coverage.py
"""
import inspect
import json
import random
from pathlib import Path

from cwm.groundtruth import leduc_poker as L
from cwm.leduc_instrument import (WrongInference, _is_tail, infoset_key,
                                  random_infoset_coverage, competent_infosets)
from cwm.gap import inference_accuracy
from cwm.determinized import imperfect_arena

SIMS = 200
N_GAMES = 400
SEEDS = [0, 1, 2]


def main():
    Path("results").mkdir(exist_ok=True)
    out = {}

    # (1) coverage gap
    comp = competent_infosets(L, n_games=80, sims=SIMS, seed=0)
    rand = random_infoset_coverage(L, n_games=4000, seed=0)
    comp_tail = {k for k in comp if _is_tail(list(k))}
    uncovered_tail = {k for k in comp_tail if k not in rand}
    out["coverage"] = {"competent_infosets": len(comp), "competent_tail": len(comp_tail),
                       "random_covered": len(rand),
                       "tail_uncovered_by_random": len(uncovered_tail)}
    print(f"coverage: competent={len(comp)} tail={len(comp_tail)} "
          f"random_covered={len(rand)} tail_uncovered={len(uncovered_tail)}", flush=True)

    # (2) instrument: gate (random-sampled states) vs play
    w = WrongInference()
    rng = random.Random(1)
    deals = L.initial_states()
    sample = []
    for _ in range(400):                       # random-play states = what the gate sees
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not L.is_terminal(s):
            sample.append({"board": list(s["board"]), "current_player": s["current_player"]})
            s = L.apply_action(s, rng.choice(L.legal_actions(s)))
    gate = inference_accuracy(inspect.getsource(L), sample, L)  # truth passes (sanity)
    # the instrument is a live object, not code; check its inference on the sample directly
    inst_mismatch = sum(1 for st in sample
                        for p in (1, 2)
                        if w.infer_states(L.observation(st, p), p) != L.infer_states(L.observation(st, p), p))
    out["instrument_gate"] = {"truth_inference_rate": gate["inference_rate"],
                              "instrument_mismatches_on_random_sample": inst_mismatch,
                              "n_checks": len(sample) * 2}
    print(f"instrument gate: truth_inference_rate={gate['inference_rate']:.3f} "
          f"instrument mismatches on random sample={inst_mismatch}/{len(sample)*2}", flush=True)

    fair = imperfect_arena(L, L, L, simulations=SIMS, n_games=N_GAMES, seeds=SEEDS,
                           n_determinizations=8)
    play = imperfect_arena(L, w, L, simulations=SIMS, n_games=N_GAMES, seeds=SEEDS,
                           n_determinizations=8)
    out["play"] = {"fair_winrate": fair["a_winrate"], "fair_ci": [fair["lo"], fair["hi"]],
                   "instrument_winrate": play["a_winrate"], "instrument_ci": [play["lo"], play["hi"]],
                   "instrument_net": play["a_net"], "n": play["n"]}
    print(f"play: fair={fair['a_winrate']:.3f}[{fair['lo']:.3f},{fair['hi']:.3f}] "
          f"instrument={play['a_winrate']:.3f}[{play['lo']:.3f},{play['hi']:.3f}] "
          f"net={play['a_net']:.1f}", flush=True)

    # (3) danger vs N: play_cost x P(tail info-set absent from N random samples)
    play_cost = max(0.0, fair["a_winrate"] - play["a_winrate"])
    p_tail = (len(comp_tail) and len(uncovered_tail) / len(comp_tail)) or 0.0
    out["danger"] = {"play_cost": play_cost,
                     "frac_tail_uncovered_at_4000": p_tail}
    print(f"danger: play_cost={play_cost:.3f} tail_uncovered_frac={p_tail:.3f}", flush=True)

    Path("results/leduc_coverage.json").write_text(json.dumps(out, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Smoke-run the driver at tiny settings**

Run:
```bash
PYTHONPATH=src python -c "
import scripts.leduc_coverage as D
D.SIMS=20; D.N_GAMES=6; D.SEEDS=[0]
D.main(); print('SMOKE OK')
" 2>&1 | tail -8
```
Expected: prints coverage/instrument/play/danger lines, `results/leduc_coverage.json` written, ends `SMOKE OK`. (Numbers are noise at this size — this only checks the code path.)

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 8: Commit**

```bash
git add src/cwm/leduc_instrument.py scripts/leduc_coverage.py tests/test_leduc_instrument.py
git commit -m "feat: Leduc coverage-gap experiment + Claim A inference instrument"
```

---

## Post-implementation (manual, CPU)

1. Non-triviality / validation: confirm `imperfect_arena(L, L, L)` fair baseline ≈ 0.5
   and that determinized MCTS beats random at Leduc.
2. Full Claim A run: `PYTHONPATH=src python scripts/leduc_coverage.py` at proper
   settings (e.g. SIMS=300, N_GAMES=2000, SEEDS=[0,1,2,3] for a tight CI). Expect:
   a substantial competent-tail uncovered by random sampling; the instrument's
   inference matching the truth on the random sample (gate-blind) yet losing at play
   with a CI below the fair baseline. If the instrument does NOT separate, widen the
   tail definition or increase games; report honestly.
3. (Optional, Azure) synthesize Leduc (large) and report gate + play as context.
4. Write results into `docs/EXPERIMENTS.md`; update RESEARCH-DIRECTION and the
   preprint skeleton §6.
```
