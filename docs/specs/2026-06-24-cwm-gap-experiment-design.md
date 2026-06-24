# CWM "Verified vs Correct" Gap Experiment — Design

Status: design approved 2026-06-24. Scope: **measurement only** (the
search-guided-synthesis fix is a separate, contingent spec).

## Purpose

The synthesis loop accepts a world model when it reaches **transition accuracy
1.0 on random-policy trajectories** (the *gate*). But MCTS plans over a
different distribution — search-promising states, often out-of-distribution
relative to random play. A world model can pass the gate at 100% and still be
wrong exactly where planning needs it. The paper (arXiv:2510.04542) never
measured this.

This experiment **measures that gap** across three knowledge regimes and reports
whether sampled-trajectory verification gives false security. It is publishable
either way: a gap confirms the concern; no gap is an honest null result that
still motivates the verification-distribution question.

Thematic tie-in: validating on the wrong distribution = false security — the
spine of the companion blog article on cognitive debt.

## The three knowledge regimes

Established empirically via a cold declarative probe of gpt-5.4 (ran 2026-06-24):

| Regime | Game | gpt-5.4's prior | Expectation |
|--------|------|-----------------|-------------|
| Correct prior | Generalized Tic-Tac-Toe 6×6 win-4 | knows it (m,n,k family) | gap ≈ 0 (recall, not inference) |
| No prior | Generalized Chess `army5x5a` | does NOT know the movesets | gap may appear (genuine translation) |
| Wrong prior | Trike (Erickson 2020) | confabulates the mechanics | gap should bite hardest |

The CWM setup always supplies the rules text **and** trajectories; "inference"
here means *translate given rules + examples into globally correct code*, not
guess rules from nothing. The sharpest case is Trike, where a strong **wrong**
prior may leak into the code in ways random trajectories never expose.

## Architecture

Game-agnostic measurement harness on top of the existing synth → refine loop.
No baseline LLM is needed (the gap is intrinsic to the world model), so runs are
cheaper than the arena.

For each synthesized CWM that passed the gate (accuracy 1.0), gather three state
distributions and compare the CWM (run in the sandbox) against the ground-truth
module (run in-process) on each:

- **D_gate** — the random-policy trajectory states the refiner already used.
  Expected agreement ≈ 1.0 by construction (the control).
- **D_cwm** *(headline)* — states MCTS expands while planning **on the CWM**,
  collected over CWM-vs-CWM self-play. This is the distribution the agent's own
  decisions depend on; a "verified-but-wrong" model bites here.
- **D_truth** — states MCTS expands while planning **on the ground truth**, over
  self-play on the true game. The distribution a competent player visits.

### Divergence metric

For a set of states `S`, comparing CWM vs ground truth, per state `s`:

- `legal_actions(s)` — compared as sets.
- `is_terminal(s)` — compared.
- `returns(s)` — compared (dict `{1: r1, 2: r2}`).
- `apply_action(s, a)` for **each `a` in `truth.legal_actions(s)`** — next states
  compared.

If a state in D_cwm is unreachable/ill-formed under the truth and the truth
function raises, that counts as a **mismatch** — it is exactly a gap symptom (the
CWM invented an impossible position). The CWM may likewise raise; caught and
counted as a mismatch for that property.

Reported per distribution:

- per-property agreement rates: `legal`, `terminal`, `returns` (per state);
  `transition` (per `(s, a)` pair).
- **`state_agreement_rate`** — fraction of states with **zero** mismatches across
  all properties. This is the headline per-distribution number.

**Headline gap = `state_agreement(D_gate) − state_agreement(D_cwm)`.** Also report
the D_truth figure. Per regime, per synth model, aggregated over synthesis seeds.

## Components / files

### Harness

- **`src/cwm/mcts.py`** — add an optional `visited: set | None = None` parameter to
  `mcts_policy`. When provided, insert `state_to_json(state)` for the root state
  and every expanded child node into the set (tree nodes only — not rollout
  states, which are random noise). Backward-compatible: default `None` changes
  nothing. Import `state_to_json` from `.world_model`.

- **`src/cwm/gap.py`** *(new)* —
  - `collect_visited_states(model, n_games, simulations, seed, cap=20000) -> list[dict]`
    Drive `model`-vs-`model` self-play with `mcts_policy(..., visited=acc)`,
    accumulate a deduped set of serialized states, deserialize to a list. If the
    cap is hit, stop and `log` how many states were dropped (no silent
    truncation). Used for both D_cwm (model = CWM) and D_truth (model = truth).
  - `contract_divergence(cwm_code: str, states: list[dict], truth_module, timeout=10.0) -> DivergenceReport`
    Compute truth outputs in-process; build one batch program (same sandbox
    pattern as `refiner.contract_accuracy`) that, for each state, returns
    `legal_actions`, `is_terminal`, `returns`, and `apply_action` for every
    truth-legal action; compare; tally the rates above. Errors on either side →
    mismatch for that property.
  - `DivergenceReport` dataclass: `n_states`, `legal_rate`, `terminal_rate`,
    `returns_rate`, `transition_rate`, `n_pairs`, `state_agreement_rate`,
    plus a short list of example mismatches (capped, for the write-up).

- **`src/cwm/run_gap.py`** *(new)* — orchestrator. Flags: `--game`,
  `--synth-size {mini,nano}`, `--synth-seeds N` (default 5), `--selfplay-games`
  (default 20), `--simulations` (default 300), `--seed`. For each synthesis seed:
  collect oracle trajectories, synthesize + refine to gate 1.0 (reuse existing
  code; skip & record the seed if it fails to reach 1.0), build D_gate / D_cwm /
  D_truth, run `contract_divergence` on each, emit a per-seed JSON. Aggregate
  mean and min/max of the headline gap across seeds. Write
  `results/gap_{game}_{synth_size}.json`. `load_dotenv(override=True)` as in
  `run_experiment.py`.

### Ground-truth games (each: module + `RULES_TEXT` + `POLICY_DESCRIPTION`, registered in `games.py`)

All use the existing contract: `State = {"board": list[int], "current_player": int}`
with `current_player ∈ {1, 2}`; `Action = int`; functions `initial_state`,
`legal_actions`, `apply_action` (returns a new state, no mutation), `is_terminal`,
`returns` (`{1: r1, 2: r2}`, each in `{-1.0, 0.0, 1.0}`, all `0.0` unless terminal).

#### `src/cwm/groundtruth/gen_tictactoe.py` — Gen-TTT 6×6 win-4 (correct prior)

- m,n,k generalization (m=6, n=6, k=4) of the existing tic-tac-toe oracle.
  Parameters as module constants `ROWS=6`, `COLS=6`, `K=4`.
- board = 36 ints, 0 empty / 1 / 2; index = row*COLS + col.
- Action = empty cell index (0..35). legal_actions = empty cells.
- Win = any K-in-a-row (horizontal, vertical, both diagonals). Draw = full board,
  no winner. Terminal = win or full.

#### `src/cwm/groundtruth/gen_chess.py` — army5x5a (no prior)

- Board: 5×5, 25 cells, `index = row*5 + col`. row 0 = rank A (top) … row 4 = E
  (bottom); col 0 = file 1 (left).
- Piece encoding: `0` empty; P1: `1` general / `2` infantry / `3` cavalry;
  P2: `4` general / `5` infantry / `6` cavalry.
- Move offsets `(Δrow, Δcol)` (from the paper's Appendix H.5):
  - general: `[(1,0),(-1,0),(0,1),(0,-1),(0,-2),(0,2)]`
  - infantry: `[(1,0),(2,0),(1,-1),(1,1),(-1,0)]`
  - cavalry: `[(0,3),(1,2),(2,1),(3,0)]`
- **Mirroring:** module constant `MIRROR_PLAYER2 = True`. When true, Player 2's
  pieces use **negated row offsets** (`(-Δrow, Δcol)`), so the pawn-like infantry
  advances toward the opponent for both sides. (The appendix lists one moveset and
  is silent on orientation; with no mirroring one side's infantry is nearly
  immobile and the game degenerates. The constant lets us flip it if the
  non-triviality sweep disagrees.) The `RULES_TEXT` states the chosen convention
  explicitly so the synthesizer has complete rules.
- Movement: jump by offset (no sliding / no intermediate-cell blocking). A move is
  legal if the target is on-board and not occupied by a own piece; landing on an
  opponent piece captures it.
- Action int: `from_idx * 25 + to_idx` (0..624); `PASS = 625`. `legal_actions`
  returns only offset-legal moves; `PASS` is legal **only when the player has no
  piece move** (prevents trivial stalling).
- Initial position (`current_player = 1`):
  - rank E (P1, indices 20–24): `cavalry, infantry, general, infantry, cavalry`
    → `[3,2,1,2,3]`.
  - rank A (P2, indices 0–4): `cavalry, infantry, general, infantry, cavalry`
    → `[6,5,4,5,6]`.
  - ranks B–D empty.
- Terminal: a side's general no longer on the board → the other side wins; OR the
  ply cap is reached → draw. **Ply cap** module constant `MAX_PLIES = 100`
  guarantees termination (generals could otherwise shuffle forever).
- returns: winner `+1.0`, loser `-1.0`; draw `0.0/0.0`.

#### `src/cwm/groundtruth/trike.py` — Trike (wrong prior)

Implements the **real** Trike mechanics (NOT gpt-5.4's confabulation).

- Triangular hex board, side `SIDE = 6` (module constant) → `SIDE*(SIDE+1)/2 = 21`
  cells. Row `r ∈ [0, SIDE)` has `r+1` cells, `c ∈ [0, r]`;
  `index(r,c) = r*(r+1)//2 + c`.
- The 3 movement axes (and the 6 neighbor offsets in `(Δr, Δc)`):
  axis A `(0,±1)`, axis B `(±1 same sign on Δr and Δc)` → `(+1,+1)/(-1,-1)`,
  axis C `(±1,0)` → `(+1,0)/(-1,0)`. Neighbors = those six offsets that stay in
  the triangle.
- Cell values: `0` empty; `1` P1 disc; `2` P2 disc; `3` P1 disc **with pawn**;
  `4` P2 disc with pawn; `5` neutral pawn (start cell only); `6` blocked-neutral
  (vacated start). "Occupied" = any non-zero value. Exactly one cell holds the
  pawn (value 3, 4, or 5).
- `initial_state`: neutral pawn (`5`) on a fixed central start cell, all others
  `0`, `current_player = 1`. Start cell = the cell nearest the triangle centroid;
  for SIDE=6 this is `index(4,2) = 12` (documented constant `START_CELL`). Using a
  neutral start avoids the free-color asymmetry of Trike's special first
  placement while keeping a deterministic fixed initial state.
- A turn: the current player slides the pawn from its cell along one axis over
  consecutive **empty (`0`)** cells (cannot pass over or land on occupied) to an
  empty destination. The vacated cell keeps its disc color (`3→1`, `4→2`) or
  becomes blocked-neutral (`5→6`); the destination becomes the current player's
  color-with-pawn (`3` if P1 else `4`).
- Action int = **destination cell index** (0..20). The pawn's current cell is read
  from the board, so the destination uniquely identifies the slide. `legal_actions`
  = reachable empty cells along the three axes.
- Terminal: the current player has **no legal slide** (pawn surrounded — every
  axis blocked). Termination is guaranteed: one cell becomes permanently occupied
  each turn.
- Scoring at terminal: among the pawn's cell **and its neighbors**, count P1 cells
  (`1` or `3`) and P2 cells (`2` or `4`). Majority wins (`+1/-1`); equal counts →
  draw (`0.0/0.0`). The pawn's own cell counts for its color; with a full interior
  neighborhood this is 7 cells (odd) so draws are rare but permitted at edges.

### Non-triviality validation (every new game)

- `src/cwm/selfplay_sweep.py` *(new, or extend an existing sweep helper)* —
  MCTS-vs-random win rate (skill must beat random by a wide margin) and
  MCTS-vs-MCTS with alternating starts (no obvious forced first-player win).
  Run as a check before trusting a game as a skill discriminator; results noted
  in `docs/EXPERIMENTS.md`. Expose board-size / mirror constants so a degenerate
  result can be retuned on the fly.

## Experimental protocol

- Grid: `game ∈ {gen_tictactoe, army5x5a, trike}` × `synth-size ∈ {mini, nano}`.
- **5 synthesis seeds** per cell (synthesis is stochastic → distinct CWMs).
- Per CWM: gate to accuracy 1.0; build D_gate, D_cwm, D_truth (20 self-play
  games each, simulations 300; tune per game).
- Report mean and min/max of the headline gap per cell; per-property breakdown;
  example mismatches for the write-up.
- Outputs: per-seed JSON in `results/` (git-ignored) + a summary table appended to
  `docs/EXPERIMENTS.md`.

## Testing

- **Per ground truth:** oracle correctness on hand-checked positions; `apply_action`
  purity (input unmutated); determinism; guaranteed termination; `returns` only
  non-zero at terminal; a non-triviality smoke test (MCTS beats random over a few
  games).
- **Harness:**
  - `mcts_policy` visit-log: populated, deduped, contains the root; `None` default
    leaves behavior unchanged.
  - `contract_divergence`: with the ground truth fed as its own "CWM", agreement =
    1.0 on every distribution (gap 0). With a deliberately corrupted CWM (e.g. a
    one-line wrong win check), it reports < 1.0 and surfaces the mismatch — proving
    the harness can actually detect a gap.
  - `collect_visited_states`: respects the cap and logs the drop.

## Out of scope (separate, contingent specs)

- Search-guided synthesis (the DAgger-style fix) — only if a gap is found.
- Imperfect-information round (poker, Quadranto, Hand of War) with an inference
  function + ISMCTS.
