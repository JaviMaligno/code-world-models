# Imperfect-Information CWM Round — Design (Kuhn poker, generalizable)

Status: design 2026-06-26. Extends the Code World Models study to imperfect
information: the synthesized model must provide not only transition dynamics but a
**hidden-history inference function**, and planning runs over information sets.
Built first for **Kuhn poker** (tiny, fully solved) but with a generic contract so
Leduc / Quadranto / Hand of War follow without redesign.

## Research question

Does sampling-based verification give false adequacy when the model has a hidden
state? There are now **two** synthesized artifacts to verify — the transition
dynamics (as before) and the **inference function** (which full states are
consistent with a player's observation). Hypothesis, by analogy to the
perfect-information result: a CWM can pass a sampling gate (transitions correct +
inference sets contain the truth) yet plan badly because the inference
*distribution/shape* is wrong where search relies on it — the same
accuracy-vs-play theme, now on the hidden-information axis.

## The contract (extends the existing one)

State stays `{"board": list[int], "current_player": int}`, but `board` now encodes
the **full** state including hidden parts. Two new functions are added; the rest
are unchanged in spirit:

- `initial_state() -> dict` — full state (with hidden info), `current_player` set.
- `legal_actions(state) -> list[int]`
- `apply_action(state, action) -> dict` — new state, no mutation.
- `is_terminal(state) -> bool`
- `returns(state) -> dict` — `{1: r1, 2: r2}`, 0.0 unless terminal.
- **`observation(state, player) -> list[int]`** — what `player` sees: the public
  parts plus that player's own private parts, with the opponent's hidden parts
  masked (a sentinel, e.g. `-1`). Pure.
- **`infer_states(observation, player) -> list[dict]`** — the full states
  consistent with that observation (the determinizations / hidden-history set).
  For the ground truth this is the exact consistent set; a synthesized CWM may get
  it wrong. Each returned state must satisfy `observation(s, player) == observation`.

Generality: nothing here is Kuhn-specific. Leduc adds a community card and a second
betting round inside `board`; Quadranto/Hand of War encode their hidden tiles/cards
in `board`. The two new functions are the only new surface.

## Kuhn poker concretely

- 3 cards J/Q/K = 0/1/2. Each player dealt one; one card unused (also hidden).
- `board` layout (fixed length): `[p1_card, p2_card, unused_card, pot_p1, pot_p2,
  h0, h1]` where `h0,h1` are the betting-history slots (action codes; `-1` = not
  yet played). current_player ∈ {1,2}, P1 acts first. Actions: `0 = check/call`,
  `1 = bet/raise` (Kuhn has one bet size). Standard Kuhn betting tree (check-check;
  check-bet-fold/call; bet-fold/call), antes of 1 each.
- `observation(state, 1)` = board with `p2_card` and `unused_card` set to `-1`
  (P1 sees own card + pot + history); symmetric for P2.
- `infer_states(obs, p)` = the full states assigning the two unseen cards to the
  two masked slots (2 permutations for Kuhn), all else equal. Ground truth returns
  exactly those; order canonical.
- `returns`: showdown by card rank or fold, scaled to the pot, mapped to
  `{-1.0,0.0,1.0}`-style net (use net chips sign → win/lose/tie; document the
  exact mapping in the ground truth).

## Planner: determinized MCTS

Reuse the existing perfect-information `mcts_policy`. To choose a move from an
information set:
1. `obs = observation(state, current_player)`.
2. `dets = infer_states(obs, current_player)` (optionally sample K if large; for
   Kuhn use all).
3. For each determinization, run `mcts_policy` treating it as the true state;
   collect the chosen action.
4. Aggregate: majority/visit-weighted vote → the move.

This is valid for the research question and far simpler than full ISMCTS; the
contract leaves room to swap in ISMCTS later if Kuhn demands it. New module
`src/cwm/ismcts.py` (or `determinized.py`) with
`determinized_policy(model, state, n_determinizations, simulations, seed) -> int`.

## Verification, metric, experiment

- **Gate (sampling):** extend the refiner's accuracy check to also verify
  `observation` and `infer_states` on sampled states: for each sampled full state
  `s` and player `p`, the synthesized `observation(s,p)` matches the truth, and
  `infer_states(observation(s,p), p)` equals the truth's consistent set (as a set).
  Transition/terminal/returns checks stay as they are.
- **Inference-fidelity diagnostic:** beyond set-membership, record where the
  synthesized inference set differs from the truth's (extra/missing states) — the
  imperfect-info analogue of the perfect-info divergence diagnostics.
- **Play metric (the adequacy lens):** CWM + determinized-MCTS vs ground-truth +
  determinized-MCTS, refereed by the true game (reuse arena/`_play_performance`
  shape, generalized to imperfect-info agents). Fair baseline = truth-vs-truth ≈
  the game-theoretic value; report it.
- **Experiment:** synthesize the Kuhn CWM (mini) with rules given; confirm it
  passes the gate; measure play vs the true game. Then probe the new failure
  surface: does a CWM with a subtly wrong `infer_states` (e.g. a biased or
  incomplete set) still pass the gate yet lose at play? (the imperfect-info
  verified-but-wrong case).

## Components

- `src/cwm/groundtruth/kuhn_poker.py` — full contract + `observation` +
  `infer_states` + `RULES_TEXT` + `POLICY_DESCRIPTION`; registered in `games.py`.
- `src/cwm/world_model.py` — extend `CONTRACT_API` with the `observation` and
  `infer_states` signatures (a separate `IMPERFECT_CONTRACT_API` or an additive
  section, so perfect-info games are unaffected).
- `src/cwm/ismcts.py` — `determinized_policy(...)`.
- Refiner/gap: add `observation`/`infer_states` checks (guarded so perfect-info
  games skip them — e.g. only when the module defines `infer_states`).
- `src/cwm/games.py` — register `kuhn`.
- Tests: oracle correctness (deal/observation masking, inference set exactness,
  betting tree, returns), determinized planner returns legal moves and beats a
  random imperfect-info agent, gate checks for observation/inference.

## Out of scope (later, once the pipeline is proven on Kuhn)

- Leduc poker (community card, 2 rounds), Quadranto (H.8), Hand of War (H.9).
- Full ISMCTS (only if determinized planning proves inadequate on Kuhn).
- The quantitative danger law on imperfect-info (after the basic result holds).
