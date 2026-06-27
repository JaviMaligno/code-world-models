# Beacon — a minimal provable deep partially-observable game (Claim A) — Design

Status: design 2026-06-27. Kuhn validated the imperfect-info pipeline; Leduc proved
(and a depth sweep confirmed) that shallow betting games have **no inference
coverage gap** — competent poker play is *shallower* than random, so competent
info-sets ⊆ random-covered. The coverage bound (RESEARCH-DIRECTION) shows a gap
needs `b^{d_max} ≫ N` with **depth = survival** (competent reaches a deep region
random misses). Beacon is the minimal game engineered to have exactly that
property, so the imperfect-info Claim A is **provable**, with the experiment as
instantiation — matching the standard set for the danger law (the `(1−r)^N` factor
is exact, not fitted).

## What Beacon must demonstrate

A CWM whose inference function (`infer_states`) is wrong **only on a deep region D**
that competent play reaches but an N-trajectory random gate does not:
1. **passes** the inference gate (the gate samples only shallow states, where the
   CWM's inference is correct), yet
2. **loses at play** against a planner with correct inference, because at D it acts
   on a wrong belief.

This is the imperfect-information analogue of the perfect-info rare-rule gap, now on
the inference half of the contract.

## The game (minimal "survival walk + hidden-type final guess")

Two players. Each has a hidden **type** `t ∈ {0,1}` drawn uniformly at the deal.
Parameter `T` = safe steps each player must complete (branching `b = 2`).

**Phase 1 — the walk (depth generator; loss is self-inflicted).** Players alternate
(P1, P2, P1, …). On the mover's turn at their own step index `k` (= how many safe
steps they have completed), the legal actions are `{0,1}` and the **safe** action is
`safe(k, t) = (k + t) mod 2` — a function of the mover's *own* type (which they
know). Playing the safe action advances that player by one step; playing the other
action is an **immediate loss** (the opponent wins). When **both** players have
completed `T` safe steps, the game enters the final round.

- Random play survives each step with probability `1/b = 1/2`, independently, so
  `P(random reaches the final round) = (1/2)^{2T}`.
- Optimal play knows its own safe action, so it reaches the final round with
  probability 1.

**Phase 2 — the final guess (where inference decides).** Reached only if both
survived. P1 then P2 each commit a guess `g ∈ {0,1}`. Player `i` **scores 1** iff
`g_i == t_{opponent}` (name the opponent's hidden type), else 0. Higher score wins;
equal scores draw. Net chips ±1 (win/lose), 0 (draw).

**Why the type is inferable.** A player's safe moves are a deterministic function of
their type, so their *observed move history* pins it down: from a move `a` observed
at step `k`, `t = (a − k) mod 2`. Inference is a genuine inversion of `safe`, not a
lookup — and it is naturally ambiguous early (no move seen → `{0,1}`) and resolved
later (one move seen → singleton).

## Contract encoding

`state = {"board": list[int], "current_player": int}`. Board (length 9):

```
[0] step1    safe steps completed by player 1 (0..T)
[1] step2    safe steps completed by player 2 (0..T)
[2] t1       player 1 hidden type (0/1)            — latent, masked for the opponent
[3] t2       player 2 hidden type (0/1)            — latent, masked
[4] last1    player 1's most recent move, public   — -1 if none, else 0/1
[5] last2    player 2's most recent move, public   — -1 if none, else 0/1
[6] guess1   player 1's final guess                — -1 none, else 0/1
[7] guess2   player 2's final guess                — -1 none, else 0/1
[8] status   0 walking, 1 final round, 2 P1 wins, 3 P2 wins, 4 draw
```

- `last_i` is the public shadow of the latent: `last_i = (step_i − 1 + t_i) mod 2`
  once `step_i ≥ 1` (the opponent's observed last move), else -1. Stored so
  `observation`/`infer_states` need not recompute it from the masked latent.
- **current_player is derivable** (helper `_cp_from_board`): in the walk
  (`status==0`), `cp = 1 if (step1+step2) even else 2` (P1 starts); in the final
  round (`status==1`), `cp = 1 if (#guesses made) even else 2`.

Core dynamics:
- `initial_states()`: the 4 deals `(t1,t2) ∈ {0,1}²`; board
  `[0,0,t1,t2,-1,-1,-1,-1,0]`, `current_player=1`.
- `legal_actions(state)`: `[]` if terminal; else `[0,1]` (walk action or final
  guess).
- `apply_action(state, a)` (pure):
  - walk: `p=current_player`, `k=step_p`, `s = (k + t_p) mod 2`. If `a != s` →
    `status` set so the **opponent** wins (3 if p==1 else 2). If `a == s` →
    `step_p += 1`, `last_p = a`, turn passes. If now `step1==T and step2==T` →
    `status=1` (final round).
  - final: set `guess_p = a`, turn passes; once both guesses set, resolve: `score_i
    = 1 if guess_i == t_{other} else 0`; `status = 2/3/4` by higher score / tie.
- `is_terminal`: `status ∈ {2,3,4}`.
- `returns`: 2→`{1:1.0,2:-1.0}`, 3→`{1:-1.0,2:1.0}`, 4→`{1:0.0,2:0.0}`, else 0/0.

Imperfect surface:
- `observation(state, player)`: copy board; set the **opponent's** type slot (`t2`
  if player==1 else `t1`) to -1. Everything else (own type, both `last`, steps,
  guesses, status) is public.
- `infer_states(obs_board, player)`: let the opponent index be `t2`(/`t1`). If the
  opponent's `last` is -1 (not moved) → candidates `{0,1}`. Else the unique `t` with
  `(step_opp − 1 + t) mod 2 == last_opp` → singleton. Return full states with the
  opponent slot filled by each candidate, `current_player = _cp_from_board(obs)`.
  The true state is a member; round-trip `observation(s,player)==obs` holds.

Defined via a factory `make_beacon(T)` (default `T=8`, giving `P(random reaches
final) = 2^{-16} ≈ 1.5e-5`, so a gate of N≈2000 misses D with probability
`(1−ε)^N ≈ 0.97`). Registered as `beacon`.

## The Claim A instrument

`BeaconWrongInference(T)` delegates the whole contract to the truth **except**
`infer_states`, which is corrupted **only at final-round states** (`status==1`):
there it returns the *flipped* opponent type (`1 − true_t`), a singleton
inconsistent with the observed history. Everywhere else (all walk states) it equals
the truth. Because random play almost never reaches `status==1`, the gate samples
only states where the instrument is correct.

## The experiment (`scripts/beacon_claimA.py`)

1. **Gate (random-sampled):** `inference_accuracy` over the instrument on N
   random-play states → expect inference_rate ≈ 1.0 (instrument passes; it is
   wrong only on the unreached final-round region).
2. **Play:** `imperfect_arena(truth, instrument, truth, …)` vs the fair baseline
   `imperfect_arena(truth, truth, truth, …)` → expect a Wilson-CI-separated (indeed
   near-deterministic) deficit for the instrument, because at the final round it
   guesses the flipped type and scores 0 against the correct planner's 1.
3. **Danger curve:** sweep `T` → measured gate-miss rate vs `(1−(1/2)^{2T})^N`, and
   play_cost ≈ constant → the danger law on the inference axis.

## What is proven vs measured

**Proven (exact / computed):**
- `P(random reaches D) = (1/2)^{2T}` exactly (2T i.i.d. safe steps) ⟹ for
  `N·(1/2)^{2T} ≪ 1` the gate misses D with probability `(1−(1/2)^{2T})^N` (the
  danger-law gate-miss factor, here exact in `T`).
- Optimal play reaches D with probability 1 (the safe action is known).
- At D, correct inference ⟹ winning guess; flipped inference ⟹ losing guess (by the
  win condition `g==t_opp` and `f=identity`). The instrument therefore passes the
  gate w.h.p. and loses every reached-final game vs a correct planner.

**Measured (instantiation):** the actual gate pass (0 mismatches on the random
sample w.h.p.), the actual arena deficit with Wilson CI, and the danger curve over
`T`. `play_cost`'s magnitude is the only empirical quantity.

## Testing

Oracle: walk survival and self-inflicted loss (unsafe move → opponent wins); turn
alternation; both-reach-T → final round; final-round scoring (`g==t_opp`), all three
terminal outcomes incl. draw; `apply_action` purity; `returns` non-zero only at
terminal; `_cp_from_board` in both phases; `initial_states` = 4 deals.
Imperfect surface: `observation` masks only the opponent type; `infer_states` =
`{0,1}` pre-move and the correct singleton post-move; round-trip invariant;
true-state membership; the inversion `t=(last−step+1) mod 2` is correct.
Instrument: equals truth on walk states; returns the flipped singleton at
final-round states; the flip is inconsistent with the observation (a real error).
Integration: `determinized_policy` and `imperfect_arena` run on Beacon; fair
baseline truth-vs-truth ≈ 0.5; the instrument loses with separated CI; MCTS-vs-random
non-triviality (competent survives + guesses right; random dies in the walk).

## Out of scope

- Claim B (synthesis with rules withheld) on Beacon — a later spec; Beacon is the
  provable Claim-A witness, not a synthesis benchmark, and is intentionally trivial
  in strategy (the walk is a reflex depth-generator).
- Strategic depth in the walk (a richer variant is a possible follow-up; here the
  minimal reflex walk is what makes the four properties provable).
- ISMCTS / posterior weighting — the determinized planner over the consistent set is
  held fixed across truth and instrument, so it cancels.
