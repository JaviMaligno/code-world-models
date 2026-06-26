# Quantitative Law of Sampling-Verification Harm — Design

Status: design 2026-06-26. Gives the breadth/generality the play-vs-accuracy
result needs for a preprint. A CPU spike (`scratchpad/law_sweep.py`) validated the
core relationship; this formalizes it into tested, reproducible repo code + a
rigorous run.

## Claim

The expected planning harm from accepting an LLM-synthesized world model on
**transition accuracy over random trajectories** is

    danger(rule, N) = play_cost(rule) × P(rule absent from N random games)
                    ≈ consequence × (1 − rarity)^N

where `rarity` = fraction of random games whose result the rule determines,
`play_cost` = how much a rule-blind planner loses to a rule-aware one in the true
game, and `N` = number of training/verification trajectories. A rule is dangerous
**iff it is rare enough to escape the gate AND consequential enough to matter** —
the two trade off, so `danger` is an inverted-U in `rarity`, peaking at
intermediate rarity. Whether a game *admits* a high-danger rule depends on its
structure (deep tails reachable by competent but not random play).

The spike already showed the ordering this predicts: army5x5a deep-tail rules
(rarity ~0–0.01, danger ~0.08–0.11) dominate every Connect Four rule
(rarity 0.12–0.38, danger ≤0.003) despite CF rules having *higher* raw play_cost.

## What we measure (all CPU-only; the rule-blind hand-written base is the exact
on-manifold proxy for a CWM that omits the rule — validated 2026-06-26)

For each (base game, rule, knob value):
- **rarity**: fraction of `R` random games (played under the true rule-on game)
  whose terminal result is determined by the rule. Report with a binomial CI.
- **play_cost**: `fair_baseline − blind_winrate`, where `blind_winrate` is the
  win rate (wins + 0.5·draws)/games of a rule-blind MCTS agent (planning on the
  hand-written base game) vs a rule-aware MCTS agent (planning on the true game),
  refereed by the true game, alternating starts. `fair_baseline` is measured per
  game as truth-vs-truth (expected ≈0.5; report it, do not assume).
- **danger(N)** for N ∈ {20, 40, 80}: `play_cost × (1−rarity)^N`.

Statistics: `S` arena seeds per point; report blind_winrate mean and a binomial
95% CI (Wilson) over the pooled games. Rarity over `R` random games with its CI.

## The rarity knob (continuous curve, not a few points)

**Primary — army5x5a material-at-cap, sweep the cap length `MAX_PLIES`.** Lower
cap → games reach the cap more often → the rule fires more often → less rare;
higher cap → rarer. Sweep `MAX_PLIES ∈ {30, 40, 50, 60, 80, 100, 140}` (×, and
optionally lead threshold `k ∈ {1,2}`). This traces `rarity` from high→~0 and
thus `danger` across the inverted-U. army5x5a is the high-divergence base that
admits the danger zone.

**Contrast — Connect Four**, low divergence. Its consequential rules (topcenter,
vthree, square) are all common (rarity 0.12–0.38) → high play_cost but ~0 danger
at N=40. Include them as fixed points showing CF cannot reach the danger peak. (No
clean continuous knob needed for the contrast; the three points suffice.)

## LLM confirmation (closes the loop: proxy → real pipeline)

At 2–3 knob values spanning the curve (e.g. a high-danger cap=100 point and a
low-danger cap=40 point), synthesize the CWM for real with **incomplete rules**
(mini), confirm it (a) passes the gate when the rule is absent from its sample and
(b) plays at the winrate the hand-written base proxy predicts (within CI). This
validates that the CPU proxy stands in for the real LLM-synthesized model. Reuse
`run_gap --play-games` / `_play_performance`.

## Components

- **`src/cwm/groundtruth/gen_chess_material.py`** — make `MAX_PLIES` and the lead
  threshold `K` parameters the law sweep can vary without editing the module.
  Add a factory `make_material(max_plies=100, lead=1)` returning an object exposing
  the contract (`initial_state`/`legal_actions`/`apply_action`/`is_terminal`/
  `returns`) + `outcome(state) -> (winner, reason)` where reason ∈
  {"capture","material","draw","none"}. The existing module-level functions stay
  (default 100/1) for the registry.
- **`src/cwm/law.py`** *(new)* — pure measurement:
  - `rarity(game, rule_reason, n_games, seed) -> (rate, lo, hi)` (Wilson CI).
  - `arena_winrate(truth, blind, sims, n_games, seeds) -> (winrate, lo, hi, n)`
    pooled over seeds with a Wilson CI; alternating starts; illegal→loss.
  - `danger(play_cost, rarity, N) -> float`.
- **`scripts/law_sweep.py`** — run the army cap-sweep + CF contrast, print/save a
  table (rarity±CI, fair_baseline, blind_winrate±CI, play_cost, danger@{20,40,80})
  to `results/law_sweep.json` and a markdown table to stdout.
- **Tests** `tests/test_law.py`: Wilson CI bounds sane (0≤lo≤rate≤hi≤1; wider for
  small n); `danger` monotone decreasing in rarity and increasing in play_cost;
  `arena_winrate` on truth-vs-truth ≈0.5 within CI on a tiny fast config;
  `make_material` matches the registered module at defaults and changes rarity
  with the knob (shorter cap → more "material"/"capture"-ended random games).

## Protocol

1. truth-vs-truth fair baseline per game (confirm ≈0.5).
2. army cap-sweep (7 points) + CF (3 points): rarity (R=400), arena
   (sims=400, n_games=80, seeds=3 → 240 pooled games/point), danger@N.
3. Tabulate; the headline is the **danger-vs-rarity curve** (army inverted-U)
   with CF points far below the peak.
4. LLM confirmation at 2–3 points.
5. Write results to `docs/EXPERIMENTS.md`.

## Out of scope

- Imperfect-information round (separate).
- Search-guided repair (already shown to fail by examples; spec completeness is
  the fix).
