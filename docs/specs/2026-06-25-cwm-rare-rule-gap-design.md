# CWM Rare-Rule Gap — Design (the instrument that breaks the tension)

Status: design 2026-06-25. Follows the null result of the first gap experiment
(EXPERIMENTS.md): with complete rules the model is correct (gap 0); with no rules
novel games fail the gate entirely. A rarity↔consequence tension blocked any
rule in Connect Four (6 rules tested). The divergence measurement singled out
**army5x5a** as the high-divergence base, and a **deep-tail rule** there is the
first to land in the rare-AND-consequential quadrant.

## What we are demonstrating (and the integrity framing)

The acceptance gate is *transition accuracy on random-policy trajectories*. We
show it has a **coverage blind spot for rarely-triggered dynamics**: a rule the
random sample almost never exercises is absent from both the trajectories and the
verification set, so a synthesized CWM omits it, **passes the gate**, yet a
competent planner exploits it — divergence on the competent-play distribution.

This is NOT a claim that the CWM method "fails." It is a claim about the *gate's
coverage*, and it is made rigorous by a **paired control**:

| Condition | RULES_TEXT given to the model | Expected `gap_truth` |
|-----------|-------------------------------|----------------------|
| **Incomplete** | base army5x5a (omits the rare rule) | **> 0** (bimodal by seed) |
| **Complete** (control) | base + the rare rule | **≈ 0** |

The contrast isolates the effect: complete specs close the gap; the gate alone
does not. Withholding the rule is necessary to isolate the *trajectory/gate*
channel from the *rules* channel — not to manufacture a failure. We report both.

## The instrument: army5x5a + "material-at-cap"

Base game: `army5x5a` (existing `gen_chess`). Added rule **R**: when the ply
counter reaches `MAX_PLIES` (100), instead of a draw the player with **more
material** (pieces on board, cells 0..24) wins; equal material is still a draw.

Validated empirically (`scratchpad/validate_deeptail.py`, 2026-06-25):
- **Rare under random:** R *changes the outcome* (draw→win) in only **~1%** of
  random games (3/300; cap reached 5.3%, but most cap games have equal material →
  draw either way). So in 40 training games ≈ 0.4 expected → ~67% of seeds never
  see a rule-distinguishing transition → the gate cannot verify R.
- **Consequential under competent play:** R decides **~50%** of MCTS-vs-MCTS
  games (12/24); an R-aware MCTS beats an R-blind MCTS (plans on base army5x5a)
  **15–3** in the true game. The true planner steers to the cap to play for
  material; the R-blind CWM, valuing the cap as a draw, does not.

This is the rare∧consequential quadrant Connect Four lacked (see EXPERIMENTS.md:
6 CF/army rules all on the rarity↔consequence anti-correlation curve).

Why it works here and not in CF: army5x5a has high random-vs-competent
**distributional divergence** (random games median 23 plies; competent median 58,
routinely hitting the 100 cap), so the deep tail is a region competent play
inhabits but random play rarely reaches.

## Metric

Headline **`gap_truth = state_agreement(D_gate) − state_agreement(D_truth)`** —
because a CWM that omits R does not explore R's region itself, so D_cwm
under-shows it; the correct-planner distribution D_truth exposes the omission.
Report `gap_cwm` (the existing `gate − cwm`) too — the contrast `gap_truth ≫
gap_cwm` is itself evidence that the blind spot is on the *competent* distribution.

Expect **bimodality** across seeds in the incomplete condition: seeds whose 40
training trajectories happened to include a cap+unequal-material transition
(~33%) have R verified → `gap_truth ≈ 0`; the rest omit R → `gap_truth > 0`.
Per-seed reporting; also report how many seeds saw R in training.

## Components

- **`src/cwm/groundtruth/gen_chess_material.py`** *(new)* — imports `gen_chess`
  and reuses `initial_state`/`apply_action`/`legal_actions`/`_general_alive`/
  `_material`-style helpers; overrides `is_terminal`/`returns` to add R. Exposes:
  - `RULES_TEXT` = `gen_chess.RULES_TEXT` + an explicit material-at-cap clause
    (the **complete** spec).
  - `POLICY_DESCRIPTION`.
- **`src/cwm/games.py`** — register two specs on the SAME module:
  - `"army5x5a_material"` → rules_text = the complete RULES_TEXT (control).
  - `"army5x5a_material_incomplete"` → module = the material variant, but
    rules_text = `gen_chess.RULES_TEXT` (base, omits R).
- **`src/cwm/run_gap.py`** — add `gap_truth` (and keep `gap`=gap_cwm) to each
  per-seed entry and to `aggregate_gap` (mean/min/max over `gap_truth`). Add a
  per-seed flag `r_seen_in_training` (whether any training trajectory reached a
  cap+unequal-material state).
- **`scripts/gap_grid.py`** — already passes through flags; the two conditions are
  two `--game` values.
- **Tests:** `tests/test_gen_chess_material.py` — R fires at cap with unequal
  material (winner = more material), equal material → draw, capture-win unchanged,
  non-cap non-terminal unchanged, `apply_action` purity; plus a non-triviality /
  rarity smoke (R rare under random, MCTS-vs-random still skill-discriminating).
  `tests/test_run_gap.py` — extend `aggregate_gap` for `gap_truth`.

## Protocol

- Conditions: `army5x5a_material_incomplete` (treatment) and `army5x5a_material`
  (control) × synth-size {mini, nano} × 5 synth seeds.
- 20 self-play games, 300 simulations, visited-cap 4000, train-games 40.
- Headline `gap_truth` per condition; expect treatment > 0 (bimodal), control ≈ 0.
- Save JSON to `results/`; summary table to `docs/EXPERIMENTS.md`.

## Out of scope (separate, contingent)

- Search-guided synthesis (DAgger over the world model) to close the gap — only if
  the treatment gap is confirmed.
- Imperfect-information round.
