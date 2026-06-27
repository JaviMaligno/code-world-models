# Masked Tic-Tac-Toe — Claim B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a partially-observable tic-tac-toe oracle (standard dynamics + a fixed hidden center cell) and a synthesis probe demonstrating Claim B: a CWM's belief model (`observation`/`infer_states`) is invisible to a transition-accuracy gate — synthesizing with the masking rule withheld still passes the transition gate but fails the inference gate.

**Architecture:** The oracle reuses `tictactoe` dynamics unchanged and adds the imperfect surface (`observation` masks the center; `infer_states` enumerates count-consistent center values). The probe (Azure GPT-5.4) synthesizes the contract with the masking rule present vs withheld and gates each on transitions AND inference. No arena/play — Claim B is a verification-blindness result.

**Tech Stack:** Python 3, pytest, existing `cwm` package, Azure OpenAI (probe only). No new dependencies.

## Global Constraints

- State `{"board": list[int] (len 9, values 0 empty / 1 X / 2 O), "current_player": 1|2}`. Hidden entries in an observation are `-1` (the contract's convention).
- Dynamics are standard tic-tac-toe, re-exported unchanged from `src/cwm/groundtruth/tictactoe.py` (`initial_state`, `legal_actions`, `apply_action`, `winner`, `is_terminal`, `returns`).
- `HIDDEN = 4` (the center cell). `observation(state, player)` masks ONLY cell 4 to `-1`, identically for both players.
- `infer_states(obs_board, player)` enumerates center v ∈ {0,1,2} keeping boards with legal counts (`#1 == #2` or `#1 == #2 + 1`); rebuilt `current_player = 1 if #1==#2 else 2`. The gate compares inferred **boards** only (ignores current_player). The true state is always a member; round-trip `observation(s,p)==obs` holds.
- Registered as `"masked_tictactoe"` in `src/cwm/games.py` via the module (re-exports + the two functions are module-level).
- The inference gate `inference_accuracy(code, states, truth_module)` calls `observation(s,p)`/`infer_states(o,p)` for both players and compares boards (multiset). The probe also uses `build_imperfect_contract`, `synthesize_cwm`, `refine_cwm`, `collect_trajectories`-style transitions, `AzureOpenAIProvider` (see `scripts/run_kuhn_validation.py` for the established pattern).
- No arena/play in this round. `results/` is git-ignored.

---

### Task 1: Masked tic-tac-toe oracle + register

**Files:**
- Create: `src/cwm/groundtruth/masked_tictactoe.py`
- Modify: `src/cwm/games.py`
- Test: `tests/test_masked_tictactoe.py`

**Interfaces:**
- Consumes: `tictactoe` dynamics (`initial_state`, `legal_actions`, `apply_action`, `winner`, `is_terminal`, `returns`, `RULES_TEXT`).
- Produces: module `masked_tictactoe` with the re-exported dynamics + `HIDDEN`, `observation(state, player) -> list[int]`, `infer_states(obs_board, player) -> list[dict]`, `RULES_TEXT`, `POLICY_DESCRIPTION`; registered as `"masked_tictactoe"` in `GAMES`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_masked_tictactoe.py`:

```python
from cwm.groundtruth import masked_tictactoe as M
from cwm.groundtruth import tictactoe as T

def test_dynamics_delegated_to_tictactoe():
    s = M.initial_state()
    assert s == T.initial_state()
    assert M.legal_actions(s) == T.legal_actions(s)
    assert M.apply_action(s, 0) == T.apply_action(s, 0)
    assert M.is_terminal(s) == T.is_terminal(s)
    assert M.returns(s) == T.returns(s)

def test_observation_masks_only_center_both_players():
    s = {"board": [1, 2, 1, 0, 2, 0, 0, 0, 0], "current_player": 1}
    assert M.observation(s, 1) == [1, 2, 1, 0, -1, 0, 0, 0, 0]
    assert M.observation(s, 2) == [1, 2, 1, 0, -1, 0, 0, 0, 0]   # symmetric mask
    # only the center changed
    assert M.observation(s, 1)[:4] == s["board"][:4]
    assert M.observation(s, 1)[5:] == s["board"][5:]

def test_observation_initial_state_masks_empty_center():
    assert M.observation(M.initial_state(), 1) == [0, 0, 0, 0, -1, 0, 0, 0, 0]

def test_infer_states_enumerates_count_consistent_centers():
    # visible: two X (0,2), one O (1); center hidden. a=#X_vis=2, b=#O_vis=1.
    s = {"board": [1, 2, 1, 0, 0, 0, 0, 0, 0], "current_player": 1}  # true center empty
    obs = M.observation(s, 1)
    boards = sorted(tuple(d["board"]) for d in M.infer_states(obs, 1))
    # v=0: #X=2,#O=1 -> 2==1+1 legal; v=1: #X=3,#O=1 -> illegal; v=2: #X=2,#O=2 -> legal
    assert boards == sorted([(1,2,1,0,0,0,0,0,0), (1,2,1,0,2,0,0,0,0)])
    assert any(d["board"] == s["board"] for d in M.infer_states(obs, 1))  # true member

def test_infer_states_roundtrip_and_legal_current_player():
    s = {"board": [1, 2, 1, 0, 0, 0, 0, 0, 0], "current_player": 1}
    obs = M.observation(s, 1)
    for d in M.infer_states(obs, 1):
        assert M.observation(d, 1) == obs                       # round-trip
        x = d["board"].count(1); o = d["board"].count(2)
        assert d["current_player"] == (1 if x == o else 2)      # parity-derived

def test_infer_states_filters_illegal_center_and_keeps_true():
    # 8 visible filled (4 X, 4 O), true center empty.
    s = {"board": [1, 2, 1, 2, 0, 1, 2, 1, 2], "current_player": 1}
    obs = M.observation(s, 1)
    boards = sorted(tuple(d["board"]) for d in M.infer_states(obs, 1))
    # v=0 -> 4X,4O legal; v=1 -> 5X,4O legal; v=2 -> 4X,5O ILLEGAL (filtered out)
    assert boards == sorted([(1,2,1,2,0,1,2,1,2), (1,2,1,2,1,1,2,1,2)])
    assert (1,2,1,2,0,1,2,1,2) in boards                        # true (empty center) kept

def test_registered():
    from cwm.games import GAMES
    assert "tic-tac-toe" in GAMES["masked_tictactoe"].rules_text.lower()
    assert GAMES["masked_tictactoe"].module is M
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_masked_tictactoe.py -q`
Expected: FAIL (`No module named 'cwm.groundtruth.masked_tictactoe'`)

- [ ] **Step 3: Implement** — create `src/cwm/groundtruth/masked_tictactoe.py`:

```python
"""Masked tic-tac-toe — Claim B witness (belief model orthogonal to transitions).

Standard tic-tac-toe dynamics (re-exported unchanged from `tictactoe`) plus an
arbitrary, non-recallable observation rule: the center cell (index 4) is hidden
from both players (shown as -1), even after it is played. infer_states enumerates
the count-consistent values of the hidden center. The dynamics synthesize at
transition-gate 1.0 (recall); the masking is the withholdable, dynamics-independent
rule whose omission a transition gate cannot detect.
"""
from . import tictactoe as _t
from .tictactoe import (  # re-export the unchanged dynamics surface
    initial_state, legal_actions, apply_action, winner, is_terminal, returns,
)

HIDDEN = 4


def observation(state: dict, player: int) -> list:
    b = list(state["board"])
    b[HIDDEN] = -1
    return b


def infer_states(obs_board: list, player: int) -> list:
    out = []
    for v in (0, 1, 2):
        board = list(obs_board)
        board[HIDDEN] = v
        x = board.count(1)
        o = board.count(2)
        if x == o or x == o + 1:                 # legal tic-tac-toe counts
            out.append({"board": board, "current_player": 1 if x == o else 2})
    return out


RULES_TEXT = _t.RULES_TEXT.rstrip() + """
  - Imperfect information: the center cell (index 4) is hidden from BOTH players —
    observation shows it as -1, even after a mark has been placed there. All other
    cells are public. infer_states must enumerate every value (0, 1, 2) of the
    hidden center that yields a legal position (X starts, so the count of 1s equals
    the count of 2s, or exceeds it by exactly one); the true state is always among
    them.
"""

POLICY_DESCRIPTION = _t.POLICY_DESCRIPTION + (
    " The center cell (index 4) is hidden from you (shown as -1); infer its value "
    "from the visible board and turn parity.")
```

- [ ] **Step 4: Register in `src/cwm/games.py`** — extend the import line and add the entry (match existing `kuhn`/`leduc`/`beacon` style):

```python
from .groundtruth import (tictactoe, connect_four, gen_tictactoe, gen_chess,
                          trike, gen_chess_material, kuhn_poker, leduc_poker, beacon,
                          masked_tictactoe)
```

```python
    "masked_tictactoe": GameSpec(
        name="masked_tictactoe",
        module=masked_tictactoe,
        rules_text=masked_tictactoe.RULES_TEXT,
        policy_description=masked_tictactoe.POLICY_DESCRIPTION,
    ),
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_masked_tictactoe.py tests/test_games.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
git add src/cwm/groundtruth/masked_tictactoe.py src/cwm/games.py tests/test_masked_tictactoe.py
git commit -m "feat(games): masked tic-tac-toe (PO; center hidden) + register"
```

---

### Task 2: Claim B synthesis probe

**Files:**
- Create: `scripts/mtt_claimB_probe.py`
- Test: `tests/test_mtt_probe.py`

**Interfaces:**
- Consumes: `cwm.groundtruth.masked_tictactoe`, `cwm.world_model.build_imperfect_contract`, `cwm.llm.azure_openai.AzureOpenAIProvider`, `cwm.synthesizer.synthesize_cwm`, `cwm.refiner.refine_cwm`, `cwm.gap.inference_accuracy`, `cwm.run_gap._load_module_from_code`, `cwm.trajectories.Trajectory`.
- Produces: `scripts/mtt_claimB_probe.py` with `RULES_FULL`, `RULES_WITHHELD` (the masking sentence removed), `collect_transitions(model, n_games, seed)`, `random_states(model, n, seed)`, `main()`. The masking-removal is unit-tested in `tests/test_mtt_probe.py`.

- [ ] **Step 1: Write the failing test** — create `tests/test_mtt_probe.py`:

```python
import importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "mtt_claimB_probe",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "mtt_claimB_probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

def test_withheld_removes_masking_rule_no_op_guard():
    assert probe.RULES_WITHHELD != probe.RULES_FULL          # not a silent no-op
    assert "hidden from BOTH players" in probe.RULES_FULL
    assert "hidden from BOTH players" not in probe.RULES_WITHHELD
    assert "index 4" not in probe.RULES_WITHHELD             # masking detail gone
    # the tic-tac-toe dynamics text survives in both
    assert "3 of their marks in a row" in probe.RULES_WITHHELD
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_mtt_probe.py -q`
Expected: FAIL (`No such file or directory: .../scripts/mtt_claimB_probe.py`)

- [ ] **Step 3: Implement** — create `scripts/mtt_claimB_probe.py`:

```python
"""Claim B probe (imperfect-info, real LLM synthesis on masked tic-tac-toe).

Demonstrates that a CWM's belief model is invisible to a transition gate.
Synthesize masked tic-tac-toe two ways:
  (full)     rules include the masking rule (the center cell is hidden);
  (withheld) the masking sentence is removed (rules describe tic-tac-toe + that this
             is an imperfect-info variant, but NOT what is hidden).
For each: transition gate (accuracy on random transitions) AND inference gate
(observation_rate / inference_rate). Expected: transition gate ~1.0 in BOTH (the
dynamics are recall, blind to masking); inference gate passes full, fails withheld
(the synthesized observation does not mask the center -> observation_rate drops).

Run: PYTHONPATH=src python3.12 scripts/mtt_claimB_probe.py [large|mini|nano]
"""
import os
import sys
import random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import masked_tictactoe as M
from cwm.world_model import build_imperfect_contract
from cwm.trajectories import Trajectory
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.gap import inference_accuracy

# Remove exactly the masking paragraph for the withheld variant.
_MASK_SENTENCE = (
    "  - Imperfect information: the center cell (index 4) is hidden from BOTH players —\n"
    "    observation shows it as -1, even after a mark has been placed there. All other\n"
    "    cells are public. infer_states must enumerate every value (0, 1, 2) of the\n"
    "    hidden center that yields a legal position (X starts, so the count of 1s equals\n"
    "    the count of 2s, or exceeds it by exactly one); the true state is always among\n"
    "    them.\n")
RULES_FULL = M.RULES_TEXT
RULES_WITHHELD = RULES_FULL.replace(
    _MASK_SENTENCE,
    "  - Imperfect information: this is a partially-observable variant; provide the\n"
    "    contract's observation and infer_states functions.\n")
assert RULES_WITHHELD != RULES_FULL, "masking-rule replace was a no-op — check _MASK_SENTENCE"


def collect_transitions(model, n_games, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n_games):
        s = model.initial_state()
        while not model.is_terminal(s):
            legal = model.legal_actions(s)
            a = rng.choice(legal)
            nxt = model.apply_action(s, a)
            out.append(Trajectory(state=s, action=a, next_state=nxt,
                                  reward=model.returns(nxt), terminal=model.is_terminal(nxt),
                                  legal_actions=legal))
            s = nxt
    return out


def random_states(model, n, seed):
    """Reachable full states (mid-game, where the center may be filled or empty)."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        s = model.initial_state()
        while not model.is_terminal(s):
            out.append({"board": list(s["board"]), "current_player": s["current_player"]})
            s = model.apply_action(s, rng.choice(model.legal_actions(s)))
    return out[:n]


def run(label, rules, provider, model_name):
    print(f"\n=== {label} ===", flush=True)
    contract = build_imperfect_contract(rules)
    traj = collect_transitions(M, n_games=60, seed=1)
    code, _ = synthesize_cwm(provider, model_name, contract, traj)
    refined = refine_cwm(provider, model_name, contract, code, traj, max_iters=8)
    print(f"transition gate: accuracy={refined.accuracy:.4f} iters={refined.iterations}",
          flush=True)
    sample = random_states(M, 50, seed=2)
    inf = inference_accuracy(refined.code, sample, M)
    print(f"inference gate: observation_rate={inf['observation_rate']:.3f} "
          f"inference_rate={inf['inference_rate']:.3f} n={inf['n']} exec_err={inf['n_exec_errors']}",
          flush=True)
    if inf["examples"]:
        print("  examples:", inf["examples"][:2], flush=True)
    return {"label": label, "transition_acc": refined.accuracy,
            "observation_rate": inf["observation_rate"], "inference_rate": inf["inference_rate"]}


def main():
    size = sys.argv[1] if len(sys.argv) > 1 else "large"
    model_name = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI", "large": "AZURE_DEPLOYMENT_LARGE",
                             "nano": "AZURE_DEPLOYMENT_NANO"}[size]]
    provider = AzureOpenAIProvider(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"])
    print(f"Claim B probe on masked tic-tac-toe, synth size={size}", flush=True)
    r_full = run("FULL rules", RULES_FULL, provider, model_name)
    r_wh = run("WITHHELD masking rule", RULES_WITHHELD, provider, model_name)
    print("\n=== SUMMARY ===", flush=True)
    for r in (r_full, r_wh):
        print(f"{r['label']:24s} transition_acc={r['transition_acc']:.3f} "
              f"observation_rate={r['observation_rate']:.3f} "
              f"inference_rate={r['inference_rate']:.3f}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify pass**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest tests/test_mtt_probe.py -q`
Expected: PASS (the module imports and the withheld-rules construction removes the masking rule)

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `cd /Users/javieraguilarmartin1/Documents/repos/code-world-models && python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/javieraguilarmartin1/Documents/repos/code-world-models
git add scripts/mtt_claimB_probe.py tests/test_mtt_probe.py
git commit -m "feat: Claim B synthesis probe (masked tic-tac-toe, full vs withheld masking)"
```

---

## Post-implementation (manual, Azure)

1. Run the probe: `PYTHONPATH=src python3.12 scripts/mtt_claimB_probe.py large`.
   Expected (the demonstrable triangle): transition gate ≈ 1.0 for BOTH full and
   withheld (tic-tac-toe is recall, blind to masking); inference gate passes for full
   (observation_rate ≈ 1.0, inference_rate high) and FAILS for withheld
   (observation_rate drops — the synthesized observation does not mask the center).
2. If full does NOT reach transition gate 1.0, that is itself a finding (even
   tic-tac-toe + an imperfect contract confounds synthesis) — report honestly and
   try `mini`/`nano` or simplify the contract framing. If withheld accidentally still
   masks the center (recall of the imperfect contract from the full run is impossible
   — separate synthesis calls — but the model might guess), report the observation_rate
   and note the residual.
3. Document results in `docs/EXPERIMENTS.md`; fold the Proposition + result into
   RESEARCH-DIRECTION and the preprint skeleton/draft §6 (Claim B).
```
