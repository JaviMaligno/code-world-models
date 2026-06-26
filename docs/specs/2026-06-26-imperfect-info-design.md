# Imperfect-Information CWM Round — Design (Kuhn poker, generalizable)

Status: design 2026-06-26 (revised with the perfect-information round's lessons,
testing, and preprint-minimum criteria). Extends the Code World Models study to
imperfect information: the synthesized model must provide not only transition
dynamics but a **hidden-history inference function**, and planning runs over
information sets. Built first for **Kuhn poker** (tiny, fully solved) with a
generic contract so Leduc / Quadranto / Hand of War follow without redesign.

## Lessons carried over from the perfect-information round (binding)

1. **Famous games are recalled, not inferred → trivial.** Tic-tac-toe and
   Connect Four synthesized perfectly in 0 refinements (recall) → gap ≈ 0.
   **Kuhn poker is canonical in game theory and almost certainly in training
   data**, so the model will recall it and pass any gate. Therefore **Kuhn is
   pipeline validation, NOT the result.** The non-trivial result must come from
   (a) the verified-but-wrong-inference instrument below, and/or (b) inference
   under no/withheld rules (translation-vs-inference), exactly as the rare-rule
   instrument and `--no-rules` carried the perfect-info result.
2. **Accuracy/membership is the wrong adequacy lens (dilution).** A rare but
   pivotal error does not move a sampled accuracy/membership rate. **Play
   performance is primary; inference set-membership is a secondary diagnostic.**
3. **Repair/probe data must be on-manifold.** Artificial unreachable states
   corrupted synthesis (large model → acc 0.004). Any wrong-inference probe and
   any verification sampling uses reachable states only.
4. **MCTS in pure Python is the bottleneck.** Determinized MCTS is K× a normal
   MCTS per move, so it is *more* expensive. Kuhn's depth is ~3–4 plies and Kuhn
   has only 2 determinizations, so a full game is cheap — **exploit this**: run
   thousands of games for tight Wilson CIs (the rigor army5x5a could not afford).
   Keep drivers observable (per-row print + incremental JSON, fair baseline by
   symmetry) per the law-sweep fixes.
5. **Inherit the harness guards:** sandbox chunking + `n_exec_errors` excluded
   from denominators, per-seed `try/except` around running synthesized code, skip
   a seed whose distribution is unmeasured. `infer_states` returns a *list* of
   states (larger sandbox output) — size the chunking accordingly.

## Research question and what makes it preprint-worthy

The new failure surface is the **inference function**. The contribution extends
the perfect-info thesis to hidden information:

- **Claim A (verified-but-wrong inference):** a CWM can pass a sampling gate —
  transitions correct AND every sampled `infer_states` set contains the true
  state — yet **lose at play** because the inference *distribution/shape* is wrong
  where search relies on it (e.g. a posterior that over/under-weights, or omits a
  rarely-reached consistent history). Set-membership is necessary, not sufficient.
- **Claim B (translation-not-inference, hidden-info version):** with rules
  withheld, the model cannot infer a correct inference function from trajectories
  (analogue of the perfect-info `--no-rules` collapse).

Minimum bar to claim either: a **play-performance gap with Wilson CIs that
exclude 0**, plus a paired control where the gate *would* catch the error if it
weren't diluted, plus reproducibility across seeds. Kuhn's cheapness makes tight
CIs attainable. If neither claim produces a CI-separated gap, the honest result
is a null that strengthens "sampling verification is identifying for small games"
— still reportable, but we pursue a novel imperfect-info game next (Leduc/
Quadranto) rather than over-claim.

## The contract (extends the existing one)

State stays `{"board": list[int], "current_player": int}`; `board` now encodes the
**full** state including hidden parts. Two new functions; the rest unchanged:

- `initial_state() -> dict`, `legal_actions(state) -> list[int]`,
  `apply_action(state, action) -> dict` (new state, no mutation),
  `is_terminal(state) -> bool`, `returns(state) -> dict` (`{1: r1, 2: r2}`, 0.0
  unless terminal).
- **`observation(state, player) -> list[int]`** — what `player` sees: public parts
  + that player's own private parts, opponent's hidden parts masked to `-1`. Pure.
- **`infer_states(observation, player) -> list[dict]`** — the full states
  consistent with that observation (determinizations / hidden-history set). Ground
  truth returns the exact consistent set in canonical order. **Invariant:** every
  returned `s` satisfies `observation(s, player) == observation`.

Generality: nothing is Kuhn-specific. Leduc encodes a community card + 2nd round
in `board`; Quadranto/Hand of War encode hidden tiles/cards. The two new functions
are the only new surface, and they are detected at runtime (a module either
defines `infer_states` or it is a perfect-info game — see the gate guard).

## Kuhn poker concretely

- 3 cards J/Q/K = 0/1/2. Each player dealt one; one card unused (hidden).
- `board` (fixed length 7): `[p1_card, p2_card, unused_card, ante_done, h0, h1, h2]`
  — `h*` are betting-action slots (`-1` = not played; `0` = check/call, `1` =
  bet/raise). Kuhn's tree: P1 {check,bet}; if check, P2 {check→showdown,
  bet→P1{fold,call}}; if bet, P2 {fold,call→showdown}. Antes 1 each; one bet size 1.
- `observation(state, 1)` = board with `p2_card` and `unused_card` set to `-1`;
  symmetric for P2.
- `infer_states(obs, p)` = the full states assigning the two unseen cards to the
  two masked slots (2 permutations for Kuhn), all else equal, canonical order.
- `returns`: net chips at terminal, sign-mapped to `{1: +1/0/-1, 2: ∓}` (win/tie/
  lose by net chips). The exact pot/ante arithmetic is documented in the oracle;
  the win/lose/tie *sign* is what the arena and `returns`-contract use.

## Planner: determinized MCTS

Reuse perfect-information `mcts_policy`. To choose a move from an info set:
1. `obs = observation(state, current_player)`;
2. `dets = infer_states(obs, current_player)` (all of them for Kuhn; sample K if a
   later game's set is large);
3. run `mcts_policy` on each determinization (as if it were the true state),
   collect the chosen action;
4. aggregate by visit/vote → the move.

New module `src/cwm/determinized.py`:
`determinized_policy(model, state, n_determinizations, simulations, seed) -> int`.

**Known caveat (documented, not a bug):** determinized MCTS suffers strategy
fusion and is not game-theoretic-optimal for imperfect info. This does NOT
invalidate the experiment: the **fair baseline is truth-vs-truth with the same
planner and alternating deals → ~0.5 by symmetry**, and the blind-vs-aware
comparison changes only the *model*, holding the planner fixed, so the planner's
suboptimality cancels in the contrast. We measure the baseline empirically and
report it; we do not claim absolute strength, only the model-induced difference.
ISMCTS is a later option only if determinized planning cannot resolve the effect.

## Verification, metric, experiment

- **Gate (sampling), guarded:** when a module defines `infer_states`, the
  refiner/gap additionally checks, on sampled reachable full states `s` and each
  player `p`: synthesized `observation(s,p)` == truth, and
  `set(infer_states(observation(s,p),p))` == truth's consistent set. Perfect-info
  games (no `infer_states`) skip these checks. Transition/terminal/returns checks
  unchanged. Inherit chunking, `n_exec_errors`, and the per-seed try/except.
- **Inference-fidelity diagnostic (secondary):** record extra/missing inferred
  states vs truth — the imperfect-info analogue of the perfect-info divergence
  diagnostics. Reported, but NOT the headline (dilution).
- **Play metric (primary, the adequacy lens):** CWM + determinized-MCTS vs
  ground-truth + determinized-MCTS, refereed by the true game, alternating deals,
  pooled over seeds, **Wilson CI**. Reuse the `law.arena_winrate` shape,
  generalized so the agents call `determinized_policy`. Run enough games (Kuhn is
  cheap → thousands) that the CI half-width ≪ the effect.
- **Experiment sequence:**
  1. *Pipeline validation:* synthesize Kuhn (mini, rules given); expect gate-pass
     and play ≈ baseline (recall). This validates plumbing; a near-zero gap here
     is expected, not the result.
  2. *Claim A instrument:* construct an on-manifold CWM whose `infer_states` is
     subtly wrong (e.g. drops/duplicates a consistent history, or returns a
     non-uniform-but-membership-valid set) that still passes the gate; measure its
     play vs truth. A CI-separated loss is the verified-but-wrong-inference result.
  3. *Claim B:* synthesize with rules withheld (`--no-rules`-style) and see whether
     the inference function can be inferred at all.

## Components

- `src/cwm/groundtruth/kuhn_poker.py` — full contract + `observation` +
  `infer_states` + `RULES_TEXT` + `POLICY_DESCRIPTION`; registered as `kuhn`.
- `src/cwm/world_model.py` — add an `IMPERFECT_CONTRACT_API` section (observation
  + infer_states signatures) appended for games that need it; perfect-info
  `CONTRACT_API` unchanged.
- `src/cwm/determinized.py` — `determinized_policy(...)`.
- `src/cwm/refiner.py` / `src/cwm/gap.py` — `infer_states`/`observation` checks,
  guarded by `hasattr(module, "infer_states")`; inherit existing guards.
- `src/cwm/games.py` — register `kuhn` (and mark it imperfect-info).

## Testing (oracle + harness; expanded per the lessons)

Kuhn oracle:
- deal correctness; `observation` masks exactly the opponent + unused card and
  nothing else; **round-trip invariant**: for every `s'` in
  `infer_states(observation(s,p),p)`, `observation(s',p) == observation(s,p)`.
- `infer_states` returns exactly the consistent set (set-equality, canonical
  order), size 2 for Kuhn; the true state is always a member.
- betting tree: every Kuhn line reaches a terminal; `legal_actions` correct at
  each node; `apply_action` purity; `returns` non-zero only at terminal and
  sign-correct on hand-checked showdowns and folds.
Planner:
- `determinized_policy` returns a legal action; beats a random imperfect-info
  agent over N games by a wide margin (non-triviality).
Gate/harness:
- with the Kuhn oracle fed as its own "CWM", `infer_states`/`observation` checks
  pass (gap 0); with a deliberately wrong `infer_states` (drops a state) the
  check fails and the diagnostic surfaces the missing state.
- guards inherited: a synthesized module that omits `infer_states` is handled; a
  crashing module is contained per-seed.

## Out of scope (later, once Kuhn validates the pipeline)

- Leduc poker (community card, 2 rounds), Quadranto (H.8), Hand of War (H.9) —
  the latter two are the *novel* imperfect-info games that would carry Claim B
  most convincingly (no recall).
- Full ISMCTS (only if determinized planning cannot resolve the effect on Kuhn).
- The quantitative danger law on the inference axis (after Claim A holds).
