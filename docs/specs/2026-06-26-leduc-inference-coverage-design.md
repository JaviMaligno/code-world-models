# Leduc Poker + Inference Coverage-Gap (Claim A) — Design

Status: design 2026-06-26. Kuhn validated the imperfect-information pipeline but is
too small to exhibit a gap (12 info-sets, all covered by random play → the gate is
identifying). This builds **Leduc poker** — many more information sets — to
demonstrate **Claim A** for imperfect information: a CWM whose inference function
is *verified on sampled trajectories* still loses at play because the inference is
wrong on the **competent-play distribution** that random sampling under-covers.
This is the imperfect-information analogue of the perfect-info rare-rule result,
now on the hidden-history inference function.

## Why Leduc

Coverage is the only Claim-A avenue once the planner uses the consistent set
(determinized MCTS votes uniformly over `infer_states`, and the ground-truth
inference is the uniform consistent set — there is no posterior-weight to corrupt).
So we need a game where **random-play info-set coverage < competent-play info-set
coverage**. Kuhn has 12 info-sets (100% covered). Leduc has hundreds (private card
× community card × two betting rounds with raises), and competent play (folding
weak hands, raising strong ones) reaches betting/board info-sets that random play
rarely produces. That coverage gap is what makes a verified-but-wrong inference
possible.

## Leduc rules (pinned; standard / OpenSpiel semantics)

- **Deck:** 6 cards, ranks J/Q/K = 0/1/2, two of each (multiset `[0,0,1,1,2,2]`).
  Suit is irrelevant to value; multiplicity matters for inference.
- **Players:** 2, each antes 1. Each dealt one private card.
- **Round 0 (pre-community):** a betting round (bet size **2**). Then one community
  card is revealed from the remaining deck.
- **Round 1 (post-community):** a betting round (bet size **4**). Then showdown.
- **Betting per round:** the actor may, with action codes **0=fold, 1=check/call,
  2=raise**:
  - no bet outstanding → check (1) or raise (2, commits the round's bet size);
  - bet outstanding → fold (0), call (1, matches), or raise (2) if
    `raises_this_round < 2`.
  - A round ends when a bet is called or both check. Max **2 raises per round**.
- **Fold** ends the hand immediately; the other player wins the pot.
- **Showdown:** a private card that **pairs the community card** wins; otherwise the
  higher private rank wins; **equal private ranks split** (tie → 0 net). returns are
  **net chips** (real-valued; positive = that player gains).

## Contract mapping (reuses the imperfect-info contract)

`state = {"board": list[int], "current_player": int}`. Board (fixed length 9):

```
[0] p1_card        rank 0/1/2
[1] p2_card        rank 0/1/2
[2] community      rank 0/1/2 — DEALT at the start but hidden until round 1
[3] round          0 (pre-community) or 1 (post-community)
[4] committed_p1   chips p1 has put in (starts 1 = ante)
[5] committed_p2   chips p2 has put in (starts 1)
[6] raises_round   raises made in the current round (0..2)
[7] acted_round    actions taken in the current round (0 at round start) —
                   distinguishes the opening check from the closing check
[8] status         0 ongoing, 1 = folded (terminal), 2 = showdown (terminal)
```

- `current_player` is tracked in the state dict; P1 acts first each round.
- "bet outstanding" iff `committed_p1 != committed_p2`; amount to call =
  `abs(committed_p1 - committed_p2)` (derivable, no slot).
- Round transition logic (finalized in the plan): a **call** of an outstanding bet
  ends the round; **check then check** (a check with `acted_round >= 1` and no bet
  outstanding) ends the round; a check as the opening action passes the turn; a
  **raise** passes the turn and increments `raises_round` (legal only when
  `raises_round < 2`). When a round ends without a fold: round 0 → set `round=1`,
  reset `raises_round`/`acted_round`, P1 acts first, the community card (already in
  `board[2]`) becomes observable; round 1 ending → `status=2` (showdown).

### Chance handling — all chance is in the deal (no mid-game chance)

The community card is dealt at the start (into `board[2]`) but kept hidden, exactly
like Kuhn's unused card. `apply_action` is therefore **fully deterministic**: the
round-0→1 transition only flips `round` and lets `observation` stop masking the
already-dealt community card. All chance lives in `initial_states()`.

- `initial_states()` enumerates every post-deal outcome: ordered draws of
  (p1_card, p2_card, community) from the deck multiset `[0,0,1,1,2,2]` (so p1≠ the
  same physical card as p2/community; ranks may repeat up to multiplicity 2).
  `round=0`, committeds `1,1`, `raises_round=acted_round=0`, `status=0`, P1 to act.
- `observation(state, player)`: mask the opponent's private card always, and mask
  `community` (to -1) while `round==0`; everything else is public (own card,
  community once `round==1`, round, committeds, raises, acted, status).
- `infer_states(observation, player)`: all full states consistent with the
  observation — in round 0, every assignment of (opponent_card, community) drawn
  from the remaining deck multiset; in round 1, every assignment of opponent_card
  (community already public). Respect the two-of-each-rank deck. Canonical order;
  the true state is a member; round-trip invariant holds.
- `returns(state)`: net chips at terminal per the showdown/fold rules; 0/0 if not
  terminal.

## The experiment

1. **Coverage measurement (CPU, cheap):** enumerate/collect the info-sets a
   competent MCTS-vs-MCTS self-play visits; measure the fraction NOT covered by N
   random-play trajectories (N = the gate's sample size). Expect a substantial
   uncovered competent-tail (unlike Kuhn's 0). `scripts/leduc_coverage.py`.
2. **Claim A instrument (the demonstration):** build an on-manifold CWM equal to
   the truth EXCEPT `infer_states` is **wrong on a competent-tail info-set region**
   (membership-valid on the random-sampled info-sets, wrong on the under-covered
   ones — e.g. drops a consistent opponent-card or adds an inconsistent one only
   when the board shows a competent-only betting line). Show:
   - it **passes** `inference_accuracy` on a random-trajectory sample (gate blind), and
   - it **loses at play** vs the truth in `imperfect_arena` with a Wilson-CI-
     separated deficit (Leduc hands are cheap enough for thousands of games → tight CI).
3. **Danger law (inference axis):** `danger = play_cost × P(info-set absent from N
   random samples)`, swept over N — the same threshold law, now for the inference
   function.
4. **(Optional) LLM synthesis:** synthesize Leduc (large) and report whether its
   inference passes the gate and how it plays — context, not the headline.

## Components

- `src/cwm/groundtruth/leduc_poker.py` — full imperfect-info contract +
  `RULES_TEXT` + `POLICY_DESCRIPTION`; registered as `leduc`.
- `src/cwm/world_model.py` — no change (uses the existing `build_imperfect_contract`).
- Reuse `determinized.py` (`determinized_policy`, `imperfect_arena`), `gap.py`
  (`inference_accuracy`), `law.py` (`wilson_ci`, `danger`).
- `scripts/leduc_coverage.py` — coverage measurement + the Claim A instrument run
  + the danger-vs-N table. (Driver; not unit-tested beyond a smoke.)
- The Claim A "wrong-inference" instrument: a small module/class wrapping the
  truth with a corrupted `infer_states` confined to a competent-tail predicate
  (defined in the driver, on-manifold).

## Testing

Leduc oracle (the correctness-critical part):
- ante/committed bookkeeping; bet sizes 2 (round 0) / 4 (round 1); raise cap 2 per
  round; round transition on call/check-check; community reveal at round 0→1.
- fold ends the hand, folder loses what they committed; showdown: pair-with-
  community beats high card, higher rank wins, equal rank splits (0 net) — on
  hand-checked positions.
- `apply_action` purity; `legal_actions` correct (fold only when facing a bet;
  raise only under the cap); `returns` non-zero only at terminal.
- `observation` masks opponent card (+ community in round 0) and nothing else;
  `infer_states` set-equality respecting the deck multiset, round-trip invariant,
  true-state membership; deck-multiplicity correctness (two of each rank).
- `initial_states` enumerates the correct post-deal multiset of deals.
Harness reuse:
- `determinized_policy` and `imperfect_arena` run on Leduc (legal moves; truth-vs-
  truth fair baseline ≈ 0.5 by symmetry).
- `inference_accuracy` passes on the true Leduc oracle and fails on the corrupted
  instrument when sampled on a covered info-set (sanity that the gate works),
  and PASSES the instrument when sampled only on random-covered info-sets (the
  Claim A blind spot).

## Out of scope

- Claim B (translation-not-inference) — needs a *novel* imperfect-info game
  (Quadranto / Hand of War); separate spec.
- Full ISMCTS (determinized planning suffices; the planner is held fixed across
  the comparison, so its suboptimality cancels).
- Exact game-theoretic optimality of the planner (we measure model-induced
  differences, not absolute strength).
