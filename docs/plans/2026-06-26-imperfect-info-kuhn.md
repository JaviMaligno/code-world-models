# Imperfect-Information CWM (Kuhn poker) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an imperfect-information pipeline (extended contract with `observation` + `infer_states` + `initial_states`, a determinized-MCTS planner, gate verification of the inference function, and an imperfect-info arena) validated on Kuhn poker.

**Architecture:** Keep state as `{"board": list[int], "current_player": int}` with hidden info encoded in `board`. The Kuhn oracle adds `observation`/`infer_states`/`initial_states`. A determinized planner reuses perfect-info `mcts_policy` over the inferred full states. Verification and the arena are guarded so perfect-info games are unaffected.

**Tech Stack:** Python 3, pytest, existing `cwm` package (`mcts`, `arena`, `law.wilson_ci`, sandbox). No new dependencies.

## Global Constraints

- State is `{"board": list[int], "current_player": int}`, `current_player ∈ {1,2}`; Action is `int`. Hidden info lives in `board`.
- Imperfect-info contract adds: `initial_states() -> list[dict]` (all post-deal chance outcomes), `observation(state, player) -> list[int]` (board as the player sees it; hidden entries set to `-1`, pure), `infer_states(observation, player) -> list[dict]` (all full states consistent with the observation, canonical order).
- **Invariant:** for every `s'` in `infer_states(observation(s, p), p)`, `observation(s', p) == observation(s, p)`, and the true `s` is always a member.
- Imperfect-info `returns` may be real-valued net payoffs (NOT restricted to {-1,0,1}); positive = that player gains. Perfect-info games keep {-1.0,0.0,1.0}.
- `current_player` is publicly derivable from `board` (betting-history length): `cp = 1 if (#played actions) even else 2`.
- Kuhn: 3 cards J/Q/K = 0/1/2 distinct; actions `0 = pass` (check if no bet pending, else fold), `1 = bet` (bet if none pending, else call); antes 1 each, one bet size 1.
- Determinized planner and arena reuse `cwm.mcts.mcts_policy` and `cwm.law.wilson_ci`. Perfect-info games skip the new checks (guarded by `hasattr(module, "infer_states")`).
- `results/` is git-ignored. Inherit sandbox guards where synthesized code is run (later, in experiments).

---

### Task 1: Kuhn poker oracle + imperfect contract API

**Files:**
- Create: `src/cwm/groundtruth/kuhn_poker.py`
- Modify: `src/cwm/world_model.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_kuhn_poker.py`

**Interfaces:**
- Produces: a module with `initial_state()`, `initial_states()`, `legal_actions(state)`, `apply_action(state, action)`, `is_terminal(state)`, `returns(state)`, `observation(state, player)`, `infer_states(observation, player)`, `RULES_TEXT`, `POLICY_DESCRIPTION`. In `world_model`: `IMPERFECT_CONTRACT_API` and `build_imperfect_contract(rules_text)`. Registered as `"kuhn"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_kuhn_poker.py`:

```python
from cwm.groundtruth import kuhn_poker as k

def test_initial_states_enumerates_six_deals():
    ss = k.initial_states()
    assert len(ss) == 6
    for s in ss:
        b = s["board"]
        assert sorted(b[:3]) == [0, 1, 2]        # three distinct cards
        assert b[3:] == [-1, -1, -1]             # empty history
        assert s["current_player"] == 1
    assert k.initial_state() == ss[0]

def test_legal_actions_two_until_terminal():
    s = k.initial_state()
    assert k.legal_actions(s) == [0, 1]

def test_apply_action_is_pure_and_toggles_player():
    s = k.initial_state()
    before = list(s["board"])
    ns = k.apply_action(s, 1)
    assert s["board"] == before                  # input unmutated
    assert ns["board"][3] == 1                   # first history slot filled
    assert ns["current_player"] == 2

def test_check_check_showdown_higher_card_wins():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}  # P1=K, P2=J
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 0)   # P2 check -> showdown pot 2
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 1.0, 2: -1.0}

def test_bet_fold_betting_player_wins_ante():
    s = {"board": [0, 2, 1, -1, -1, -1], "current_player": 1}  # P1=J, P2=K
    s = k.apply_action(s, 1)   # P1 bet
    s = k.apply_action(s, 0)   # P2 fold
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 1.0, 2: -1.0}     # P2 folded -> loses ante 1

def test_check_bet_call_showdown_pot4():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}  # P1=K, P2=J
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 1)   # P2 bet
    s = k.apply_action(s, 1)   # P1 call -> showdown pot 4
    assert k.is_terminal(s)
    assert k.returns(s) == {1: 2.0, 2: -2.0}

def test_check_bet_fold_p1_folds():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}
    s = k.apply_action(s, 0)   # P1 check
    s = k.apply_action(s, 1)   # P2 bet
    s = k.apply_action(s, 0)   # P1 fold -> P2 wins ante
    assert k.is_terminal(s)
    assert k.returns(s) == {1: -1.0, 2: 1.0}

def test_returns_nonterminal_zero():
    assert k.returns(k.initial_state()) == {1: 0.0, 2: 0.0}

def test_observation_masks_opponent_and_unused():
    s = {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}
    o1 = k.observation(s, 1)
    assert o1 == [2, -1, -1, 1, -1, -1]          # P1 sees own card + history
    o2 = k.observation(s, 2)
    assert o2 == [-1, 0, -1, 1, -1, -1]          # P2 sees own card + history

def test_infer_states_exact_and_roundtrip():
    s = {"board": [2, 0, 1, -1, -1, -1], "current_player": 1}
    obs = k.observation(s, 1)                     # [2,-1,-1,-1,-1,-1]
    inferred = k.infer_states(obs, 1)
    assert len(inferred) == 2
    # the true state is a member
    assert any(d["board"] == s["board"] for d in inferred)
    # round-trip invariant + current_player recovered
    for d in inferred:
        assert k.observation(d, 1) == obs
        assert d["current_player"] == 1
        assert sorted(d["board"][:3]) == [0, 1, 2]

def test_infer_states_for_player2_midgame():
    s = {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}   # after P1 bet
    obs = k.observation(s, 2)
    inferred = k.infer_states(obs, 2)
    assert len(inferred) == 2
    for d in inferred:
        assert k.observation(d, 2) == obs
        assert d["current_player"] == 2          # history len 1 -> P2 to act
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_kuhn_poker.py -q`
Expected: FAIL (`No module named 'cwm.groundtruth.kuhn_poker'`)

- [ ] **Step 3: Implement the oracle** — create `src/cwm/groundtruth/kuhn_poker.py`:

```python
"""Kuhn poker oracle — imperfect-information contract.

board = [p1_card, p2_card, unused_card, h0, h1, h2]:
  cards 0=J,1=Q,2=K (all distinct); unused_card is dealt to neither player.
  h0,h1,h2 = betting actions in order (-1 = not played). Action 0 = pass
  (check if no bet pending, else fold); action 1 = bet (bet if none pending,
  else call). Antes 1 each; one bet size 1.
state = {"board": board, "current_player": cp}; P1 acts first.
Hidden from player p: the opponent's card and the unused card.
returns are NET CHIPS (real-valued), positive = that player gains.
"""
CARDS = (0, 1, 2)


def initial_states() -> list:
    out = []
    for p1 in CARDS:
        for p2 in CARDS:
            if p2 == p1:
                continue
            unused = (set(CARDS) - {p1, p2}).pop()
            out.append({"board": [p1, p2, unused, -1, -1, -1], "current_player": 1})
    return out


def initial_state() -> dict:
    return initial_states()[0]


def _history(board: list) -> list:
    return [a for a in board[3:6] if a != -1]


def _cp_from_board(board: list) -> int:
    return 1 if len(_history(board)) % 2 == 0 else 2


def _terminal_kind(board: list):
    h = _history(board)
    if h == [0, 0]:
        return "showdown1"          # check-check, pot 2
    if h == [1, 0]:
        return "fold"               # bet-fold (P2 folds)
    if h == [1, 1]:
        return "showdown2"          # bet-call, pot 4
    if h == [0, 1, 0]:
        return "fold"               # check-bet-fold (P1 folds)
    if h == [0, 1, 1]:
        return "showdown2"          # check-bet-call, pot 4
    return None


def is_terminal(state: dict) -> bool:
    return _terminal_kind(state["board"]) is not None


def legal_actions(state: dict) -> list:
    if is_terminal(state):
        return []
    return [0, 1]


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    for i in (3, 4, 5):
        if board[i] == -1:
            board[i] = action
            break
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}


def returns(state: dict) -> dict:
    board = state["board"]
    kind = _terminal_kind(board)
    if kind is None:
        return {1: 0.0, 2: 0.0}
    h = _history(board)
    if kind == "fold":
        folder = 1 if len(h) % 2 == 1 else 2      # [1,0]->P2 folds; [0,1,0]->P1 folds
        winner = 2 if folder == 1 else 1
        amt = 1.0
    else:
        winner = 1 if board[0] > board[1] else 2  # higher card; cards always distinct
        amt = 1.0 if kind == "showdown1" else 2.0
    loser = 2 if winner == 1 else 1
    return {winner: amt, loser: -amt}


def observation(state: dict, player: int) -> list:
    board = list(state["board"])
    if player == 1:
        board[1] = -1      # hide P2 card
    else:
        board[0] = -1      # hide P1 card
    board[2] = -1          # unused card hidden from both
    return board


def infer_states(observation: list, player: int) -> list:
    obs = list(observation)
    own = obs[0] if player == 1 else obs[1]
    unknown = [c for c in CARDS if c != own]      # the two cards not held by `player`
    cp = _cp_from_board(obs)
    out = []
    for a, b in (unknown, unknown[::-1]):
        s = list(obs)
        if player == 1:
            s[1], s[2] = a, b      # opponent card, unused
        else:
            s[0], s[2] = a, b
        out.append({"board": s, "current_player": cp})
    return out


RULES_TEXT = """\
This game is Kuhn poker (2 players).
  - board has 6 integers: [p1_card, p2_card, unused_card, h0, h1, h2].
    Cards are 0,1,2 (all three distinct); unused_card belongs to neither player.
    h0,h1,h2 are betting actions in order, -1 meaning not yet played.
  - current_player is 1 or 2; P1 acts first; players alternate.
  - Each player antes 1. Action 0 = pass (a check if no bet is pending, a fold if a
    bet is pending). Action 1 = bet (a bet of 1 if none pending, a call if pending).
  - Betting lines and outcomes:
      pass,pass            -> showdown for pot 2 (each anted 1)
      bet,pass             -> the passing player folds, the bettor wins their ante (net +1)
      bet,bet              -> showdown for pot 4
      pass,bet,pass        -> the second passing player folds (net -1 for them)
      pass,bet,bet         -> showdown for pot 4
  - At a showdown the higher card wins. returns are net chips: showdown pot 2 ->
    +1/-1; showdown pot 4 -> +2/-2; fold -> +1/-1.
  - This is imperfect information: each player sees only their own card and the
    public betting history, not the opponent's card or the unused card.
"""

POLICY_DESCRIPTION = (
    "You play Kuhn poker. board = [p1_card, p2_card, unused_card, h0, h1, h2]; you "
    "see only your own card and the betting history (others are -1). Action 0 = "
    "pass (check/fold), 1 = bet (bet/call).")
```

- [ ] **Step 4: Add the imperfect contract API** — in `src/cwm/world_model.py`, after `build_contract`, append:

```python
IMPERFECT_CONTRACT_API = CONTRACT_API + """

This is an IMPERFECT-INFORMATION game. The board encodes hidden information.
Additionally implement EXACTLY these signatures:
  def initial_states() -> list[dict]   # every possible initial (post-deal) state
  def observation(state: dict, player: int) -> list[int]   # board as `player` sees it; hidden entries are -1
  def infer_states(observation: list[int], player: int) -> list[dict]  # all full states consistent with the observation

returns may be real-valued NET payoffs (not limited to {-1.0,0.0,1.0}); a positive
value means that player gains that many chips. current_player is derivable from the
public betting history. Every state in infer_states(observation(s,p),p) must map
back to the same observation, and the true state must be included.
"""


def build_imperfect_contract(rules_text: str) -> str:
    return IMPERFECT_CONTRACT_API + "\n\n" + rules_text
```

- [ ] **Step 5: Register in `src/cwm/games.py`** — extend the import and add the entry:

```python
from .groundtruth import (tictactoe, connect_four, gen_tictactoe, gen_chess,
                          trike, gen_chess_material, kuhn_poker)
```

```python
    "kuhn": GameSpec(
        name="kuhn",
        module=kuhn_poker,
        rules_text=kuhn_poker.RULES_TEXT,
        policy_description=kuhn_poker.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 6: Run tests to verify pass**

Run: `python -m pytest tests/test_kuhn_poker.py tests/test_games.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/cwm/groundtruth/kuhn_poker.py src/cwm/world_model.py src/cwm/games.py tests/test_kuhn_poker.py
git commit -m "feat(games): Kuhn poker oracle + imperfect-information contract API"
```

---

### Task 2: Determinized-MCTS planner

**Files:**
- Create: `src/cwm/determinized.py`
- Test: `tests/test_determinized.py`

**Interfaces:**
- Consumes: `cwm.mcts.mcts_policy`.
- Produces: `determinized_policy(model, state, n_determinizations=None, simulations=200, seed=0) -> int` — plans from the current player's information set: derive `obs = model.observation(state, p)`, infer the consistent full states, run `mcts_policy` on each (capped/sampled at `n_determinizations` if given), and return the visit/vote-winning action.

- [ ] **Step 1: Write the failing tests** — create `tests/test_determinized.py`:

```python
import random
from cwm.determinized import determinized_policy
from cwm.groundtruth import kuhn_poker as k

def test_returns_legal_action():
    s = k.initial_state()
    a = determinized_policy(k, s, simulations=50, seed=1)
    assert a in k.legal_actions(s)

def test_beats_random_at_kuhn():
    # determinized planner (both as P1 and P2, alternating) vs a random agent,
    # refereed by the true game; the planner should not lose money on net.
    rng = random.Random(0)
    net = 0.0
    deals = k.initial_states()
    for i in range(60):
        s = dict(deals[i % len(deals)])
        s = {"board": list(s["board"]), "current_player": 1}
        planner_is_p1 = (i % 2 == 0)
        while not k.is_terminal(s):
            p = s["current_player"]
            if (p == 1) == planner_is_p1:
                a = determinized_policy(k, s, simulations=80, seed=1 + i)
            else:
                a = rng.choice(k.legal_actions(s))
            s = k.apply_action(s, a)
        r = k.returns(s)
        net += r[1] if planner_is_p1 else r[2]
    assert net > 0      # a planner should beat a random opponent on net chips
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_determinized.py -q`
Expected: FAIL (`No module named 'cwm.determinized'`)

- [ ] **Step 3: Implement** — create `src/cwm/determinized.py`:

```python
"""Determinized MCTS for imperfect-information games.

To act from an information set, derive the current player's observation, infer the
full states consistent with it, run perfect-information MCTS on each (treating it
as the true state), and vote. Known caveat: determinization suffers strategy
fusion and is not game-theoretic-optimal; it is a valid, simple planner for
measuring model-induced differences (both sides use the same planner)."""
import random

from .mcts import mcts_policy


def determinized_policy(model, state: dict, n_determinizations=None,
                        simulations: int = 200, seed: int = 0) -> int:
    player = state["current_player"]
    obs = model.observation(state, player)
    dets = model.infer_states(obs, player)
    if n_determinizations is not None and len(dets) > n_determinizations:
        rng = random.Random(seed)
        dets = rng.sample(dets, n_determinizations)
    votes: dict = {}
    for i, d in enumerate(dets):
        a = mcts_policy(model, d, n_simulations=simulations, seed=seed + i)
        votes[a] = votes.get(a, 0) + 1
    # deterministic tie-break: highest votes, then smallest action
    return max(sorted(votes), key=lambda a: votes[a])
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_determinized.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cwm/determinized.py tests/test_determinized.py
git commit -m "feat: determinized-MCTS planner for imperfect-information games"
```

---

### Task 3: Inference-function verification (gate)

**Files:**
- Modify: `src/cwm/gap.py`
- Test: `tests/test_gap.py`

**Interfaces:**
- Consumes: `cwm.sandbox.run_in_sandbox` (same pattern as `contract_divergence`).
- Produces: `inference_accuracy(cwm_code: str, states: list, truth_module, timeout: float = 10.0) -> dict` with keys `n`, `observation_rate`, `inference_rate`, `n_exec_errors`, `examples`. For each sampled full state `s` and player `p ∈ {1,2}`: the synthesized `observation(s,p)` must equal the truth's, and `set(map(tuple-of-board, infer_states(observation(s,p),p)))` must equal the truth's consistent set. Errors on either side count as a mismatch (not silently 1.0). Excludes exec-errored states from denominators.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_gap.py`:

```python
def test_inference_accuracy_perfect_oracle():
    import inspect
    from cwm.gap import inference_accuracy
    from cwm.groundtruth import kuhn_poker
    src = inspect.getsource(kuhn_poker)
    states = [kuhn_poker.initial_state(),
              {"board": [2, 0, 1, 1, -1, -1], "current_player": 2}]
    rep = inference_accuracy(src, states, kuhn_poker)
    assert rep["observation_rate"] == 1.0
    assert rep["inference_rate"] == 1.0
    assert rep["n_exec_errors"] == 0

def test_inference_accuracy_detects_wrong_infer():
    import inspect
    from cwm.gap import inference_accuracy
    from cwm.groundtruth import kuhn_poker
    src = inspect.getsource(kuhn_poker)
    # corrupt infer_states to drop one consistent state (return only the first)
    bad = src.replace("    return out\n\n\nRULES_TEXT",
                      "    return out[:1]\n\n\nRULES_TEXT")
    assert bad != src
    states = [{"board": [2, 0, 1, -1, -1, -1], "current_player": 1}]
    rep = inference_accuracy(bad, states, kuhn_poker)
    assert rep["inference_rate"] < 1.0
    assert rep["examples"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gap.py -k inference -q`
Expected: FAIL (`cannot import name 'inference_accuracy'`)

- [ ] **Step 3: Implement** — add to `src/cwm/gap.py`:

```python
def inference_accuracy(cwm_code: str, states: list, truth_module,
                       timeout: float = 10.0) -> dict:
    """Verify a synthesized imperfect-info CWM's observation() and infer_states()
    against the truth on sampled full states, for both players. Set-equality on the
    inferred consistent states; errors count as mismatches, not silent passes."""
    if not states:
        return {"n": 0, "observation_rate": 1.0, "inference_rate": 1.0,
                "n_exec_errors": 0, "examples": []}
    # truth expectations (in-process)
    def _canon(stlist):
        return sorted(tuple(s["board"]) for s in stlist)
    truth = []
    for s in states:
        row = {}
        for p in (1, 2):
            o = truth_module.observation(s, p)
            row[p] = {"obs": o, "infer": _canon(truth_module.infer_states(o, p))}
        truth.append(row)
    cases = [{"state": s} for s in states]
    payload = json.dumps(json.dumps(cases))
    call = (
        "import json\n"
        f"_cases = json.loads({payload})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    _s = _c['state']\n"
        "    _r = {}\n"
        "    for _p in (1, 2):\n"
        "        _e = {}\n"
        "        try:\n"
        "            _o = observation(_s, _p)\n"
        "            _e['obs'] = _o\n"
        "        except Exception as ex:\n"
        "            _e['obs'] = {'__error__': repr(ex)}; _o = None\n"
        "        try:\n"
        "            _inf = infer_states(_o, _p) if _o is not None else None\n"
        "            _e['infer'] = sorted([tuple(x['board']) for x in _inf]) if _inf is not None else {'__error__': 'no obs'}\n"
        "        except Exception as ex:\n"
        "            _e['infer'] = {'__error__': repr(ex)}\n"
        "        _r[str(_p)] = _e\n"
        "    _out.append(_r)\n"
        "print(json.dumps(_out))\n"
    )
    res = run_in_sandbox(cwm_code, call, timeout=timeout)
    lines = res.stdout.strip().splitlines() if res.ok else []
    try:
        produced = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        produced = None
    if not isinstance(produced, list) or len(produced) != len(states):
        return {"n": 0, "observation_rate": 0.0, "inference_rate": 0.0,
                "n_exec_errors": len(states),
                "examples": [(res.stderr or "malformed output")[-200:]]}

    obs_ok = inf_ok = measured = 0
    examples = []
    for st, tr, got in zip(states, truth, produced):
        for p in (1, 2):
            measured += 1
            g = got.get(str(p), {})
            # observation: JSON round-trips lists fine; compare directly
            if g.get("obs") == tr[p]["obs"]:
                obs_ok += 1
            elif len(examples) < 10:
                examples.append(f"obs mismatch state={st['board']} p={p} got={g.get('obs')}")
            # inference: truth infer is list[tuple]; sandbox gives list[list]
            got_inf = g.get("infer")
            norm = sorted(tuple(x) for x in got_inf) if isinstance(got_inf, list) else got_inf
            if norm == tr[p]["infer"]:
                inf_ok += 1
            elif len(examples) < 10:
                examples.append(f"infer mismatch state={st['board']} p={p} got={got_inf}")
    n = measured
    return {"n": n, "observation_rate": obs_ok / n, "inference_rate": inf_ok / n,
            "n_exec_errors": 0, "examples": examples}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_gap.py -k inference -q`
Expected: PASS

- [ ] **Step 5: Run the gap suite**

Run: `python -m pytest tests/test_gap.py -q`
Expected: PASS (existing gap tests unaffected)

- [ ] **Step 6: Commit**

```bash
git add src/cwm/gap.py tests/test_gap.py
git commit -m "feat(gap): inference_accuracy — verify observation + infer_states"
```

---

### Task 4: Imperfect-information arena

**Files:**
- Modify: `src/cwm/determinized.py`
- Test: `tests/test_determinized.py`

**Interfaces:**
- Consumes: `cwm.determinized.determinized_policy`, `cwm.law.wilson_ci`.
- Produces: `imperfect_arena(truth, model_a, model_b, simulations, n_games, seeds, n_determinizations=None) -> dict` with keys `a_winrate`, `lo`, `hi`, `n`, `a_wins`, `b_wins`, `ties`, `a_net`. Per game: sample a deal from `truth.initial_states()`, alternate which seat model_a controls, both agents act via `determinized_policy` on their OWN model, referee with `truth`. Win/tie/lose by net-chip sign for the Wilson CI; also accumulate net chips (`a_net`).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_determinized.py`:

```python
def test_imperfect_arena_fair_baseline_truth_vs_truth():
    from cwm.determinized import imperfect_arena
    from cwm.groundtruth import kuhn_poker as k
    res = imperfect_arena(k, k, k, simulations=60, n_games=40, seeds=[0, 1])
    assert res["n"] == 80
    assert res["a_wins"] + res["b_wins"] + res["ties"] == 80
    assert 0.0 <= res["lo"] <= res["a_winrate"] <= res["hi"] <= 1.0
    # symmetric self-play with alternating deals -> roughly even
    assert 0.30 < res["a_winrate"] < 0.70
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_determinized.py -k arena -q`
Expected: FAIL (`cannot import name 'imperfect_arena'`)

- [ ] **Step 3: Implement** — add to `src/cwm/determinized.py` (and add `from .law import wilson_ci` to the imports):

```python
def imperfect_arena(truth, model_a, model_b, simulations: int, n_games: int,
                    seeds: list, n_determinizations=None) -> dict:
    """model_a vs model_b, each planning via determinized_policy on its OWN model,
    refereed by `truth`. Deals sampled from truth.initial_states(); seats alternate.
    Win/tie/lose by net-chip sign (Wilson CI); a_net accumulates net chips."""
    deals = truth.initial_states()
    a_wins = b_wins = ties = 0
    a_net = 0.0
    g = 0
    for sd in seeds:
        rng = random.Random(sd)
        for i in range(n_games):
            deal = deals[rng.randrange(len(deals))]
            s = {"board": list(deal["board"]), "current_player": deal["current_player"]}
            a_is_p1 = (i % 2 == 0)
            move = 0
            while not truth.is_terminal(s):
                p = s["current_player"]
                model = model_a if ((p == 1) == a_is_p1) else model_b
                a = determinized_policy(model, s, n_determinizations=n_determinizations,
                                        simulations=simulations, seed=sd + g * 1000 + move)
                if a not in truth.legal_actions(s):
                    a = truth.legal_actions(s)[0]
                s = truth.apply_action(s, a)
                move += 1
            r = truth.returns(s)
            a_payoff = r[1] if a_is_p1 else r[2]
            a_net += a_payoff
            if a_payoff > 0:
                a_wins += 1
            elif a_payoff < 0:
                b_wins += 1
            else:
                ties += 1
            g += 1
    n = a_wins + b_wins + ties
    point, lo, hi = wilson_ci(a_wins + 0.5 * ties, n)
    return {"a_winrate": point, "lo": lo, "hi": hi, "n": n,
            "a_wins": a_wins, "b_wins": b_wins, "ties": ties, "a_net": a_net}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_determinized.py -q`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green)

- [ ] **Step 6: Commit**

```bash
git add src/cwm/determinized.py tests/test_determinized.py
git commit -m "feat: imperfect-information arena (determinized agents, Wilson CI, net chips)"
```

---

## Post-implementation (manual, needs Azure)

Run after merge. These are the actual experiments (synthesized code → inherit the
per-seed try/except + chunking guards from run_gap when wiring synthesis):

1. **Pipeline validation:** synthesize Kuhn (mini) with `build_imperfect_contract`;
   confirm it passes the transition gate AND `inference_accuracy` (expect ~1.0 by
   recall); measure `imperfect_arena(truth=kuhn, cwm, truth)` play ≈ fair baseline.
   A near-zero gap here is expected (recall), not the result.
2. **Claim A (verified-but-wrong inference):** take an on-manifold CWM whose
   `infer_states` is subtly wrong (e.g. drops a rarely-reached consistent history
   or returns a membership-valid but skewed set) that still passes the gate;
   measure `imperfect_arena` play vs truth. A Wilson-CI-separated loss is the
   result. Kuhn is cheap → run thousands of games for a tight CI.
3. **Claim B (translation-not-inference):** synthesize with rules withheld; check
   whether `observation`/`infer_states` can be inferred at all.
4. Write results (with CIs) into `docs/EXPERIMENTS.md`; update RESEARCH-DIRECTION.
```
