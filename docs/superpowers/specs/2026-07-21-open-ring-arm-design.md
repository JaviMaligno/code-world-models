# Open-ring registered arm: danger collapse & topology-tracking across the detector flip

**Status:** approved design (2026-07-21). Successor to the exploratory open-ring
2×2 (EXPERIMENTS.md "Exploratory control: OPEN ring") and built on the
per-artifact behavioral audit (EXPERIMENTS.md "Per-artifact behavioral audit",
`scripts/ring2d_artifact_audit.py`, commit ece9aea).

## 1. Context and motivation

The closed-ring synthesis arm (gap 0, β₁=1) established: identifiability event
family-independent; no repair from outside; from inside, models pose geometric
structure but fail exact parameter identification (audit F2); the one passer
used the gauge-free complement form with a round guessable radius (F3); the
pre-registered topological summary has a resolution limit — its Rips detector
reports β̂₁=1 for every gap ≤ 1.2, flips (seed-dependently) at gap ≈ 1.8, and
is clean β̂₁=0 at 2.4 (F5). The exploratory open-ring 2×2 showed the danger
(play_cost) collapses 1.12 → 0.029 when a facing channel opens (aligned-channel
degeneracy), while the identifiability event is unchanged.

The registered arm characterizes two curves and one attribution:

- **Danger curve** pc(gap): where does the blind model's exploitation collapse
  as the facing channel opens, and does it persist with a hidden channel
  (same β₁, unreachable channel)?
- **Topology-tracking attribution**: when the synthesizer poses a mode
  structure from inside evidence, does it follow **(a) the guidance's β̂₁**,
  **(b) the raw evidence**, or **(c) a template prior**? The detector flip
  makes these separable: for 0 < gap ≤ 1.2 guidance (loop) contradicts truth
  (arc); at gap 1.8 guidance varies BETWEEN seeds of the same gap; at 2.4
  guidance agrees with truth (arc).
- **Parameter-identifiability boundary**: gate-pass from inside requires
  reachable-equivalent structure × exactly-guessable parameters (F3). The
  channel edge angles (π ± gap/2) are NOT round numbers, so the arm predicts
  gate-pass ≈ 0 at open gaps even when the posed structure is correct — a
  falsifiable sharpening of F3.

## 2. Pre-registered hypotheses

- **H1 (danger = topology relative to reach).** pc(gap) for the blind model,
  facing channel, collapses from ≈1.12 (gap 0) to ≈0 somewhere in (0, 0.6);
  with the hidden channel pc stays ≈1 at every tested gap. β₁ alone does not
  predict danger; obstruction of the competent planner's path does.
- **H2 (attribution).** Artifact structure classes from inside evidence track
  the GUIDANCE topology, not the truth: loop/disc-type structures dominate
  while guidance says β̂₁=1 (gap ≤ 1.2), arc-type structures rise where
  guidance says β̂₁=0 (gap 2.4). At gap 1.8 the within-gap contrast holds:
  cells whose own guidance said 1 pose closed structures more often than
  cells whose guidance said 0. (Alternative outcomes: classes independent of
  guidance and dominated by disc/half-plane → prior; classes tracking truth
  even against guidance → evidence-driven.)
- **H3 (parameter identifiability).** Gate-pass rate from inside stays ≈0 at
  every open gap (channel edges not round-guessable), including for Claude
  (the strongest gap-0 repairer): at gap 2.4 Claude poses an arc (honest
  guidance) but fails the exact edge parameters.

## 3. Design grid

Instrument: `RingField2D` (unchanged). Protocol: N=40 rollouts, ε=1e-9,
≤5 refines, incomplete arm — identical to the closed-ring arm. All runs
resumable per seed (existing harness checkpointing).

| component | gaps | seeds × size | prompt/start/channel |
|---|---|---|---|
| A-facing (danger) | 0.05, 0.1, 0.2, 0.4, 0.6*, 1.2 | 20 mini | default / outside / facing |
| A-hidden (control) | 0.6, 1.2 | 10 mini | default / outside / hidden |
| D-facing (synthesis) | 0.2, 0.6*, 1.2, 1.8, 2.4 | 20 mini (30 at 1.8) | tda / inside / facing |
| large robustness | D at {0.6, 2.4}; A at {0.1, 0.6} | 20 large | as above |
| Claude relay spots | D at 2.4; A at the CPU-curve knee rounded to the nearest A-facing grid gap | 3 each | relay harness (already supports --gap/--channel) |
| CPU dense danger curve | 0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.9, 1.2 | no LLM | pc_blind(gap) via paired MPC episodes (mechanism-grid method), locates the knee densely |

*gap 0.6 mini cells already exist (exploratory run, 5 seeds) — the arm tops
them up to 20 seeds; the harness resume logic must SKIP the existing 5 seeds,
not recompute them.

Gap 0 endpoints are reused from the committed closed-ring arm (no re-runs).

## 4. Pre-registered metrics and analyses

Per cell (all emitted by the audit/aggregator, extending
`scripts/ring2d_artifact_audit.py`):

1. `gate_accuracy` (terminal) AND `blind_ref_gate` (canonical blind on the
   cell's exact evidence) — terminal gates are only interpreted against the
   blind reference (audit F6 bands).
2. Freeze-mask class with the FIXED taxonomy and thresholds (pre-registered,
   as committed in `ring2d_artifact_audit.py`): blind / vdep / point / arc /
   loop / disc / complement / fill-unbounded; angular-coverage cutoffs 0.04
   and 0.97; inner-fill cutoff 0.5; far-field cutoff 0.2; 81×81 grid on
   [4,20]×[−8,8]; velocity slices (0,0) and (1.5,0.5).
3. `guidance_beta1` parsed from the recorded `guidance_text` (per-cell).
4. `sample_contains_wall` (identifiability axis) and the per-gap mode-absent
   rate with Wilson CI; r(gap) is REPORTED so danger-collapse is not
   conflated with rarity change.
5. play_cost for gate-passing cells; J_truth(gap), J_random(gap) baselines
   reported alongside (the truth baseline itself changes as the phantom
   becomes reachable — part of the mechanism, not a nuisance).
6. Refine HISTORY (new, see §5): per-iteration (code, gate) so the structure
   trajectory across refines is data (the Claude relay showed oscillation
   blind → wrong-structure → right-structure-wrong-parameter → blind that
   terminal-only recording erases).

Headline analyses:

- pc(gap) facing vs hidden (H1), on the CPU dense curve + LLM-arm
  confirmations; knee location reported with the corridor-width geometry
  (channel arc-width ≈ gap × r_in).
- Class distribution per gap × guidance β̂₁ × truth β₁ (H2), including the
  gap-1.8 within-gap contingency (cells split by their own guidance).
- Gate-pass rate per gap from inside (H3) + per-artifact parameter extraction
  for posed structures: fitted freeze-boundary radii/angles vs truth
  (r_in 3.5, edges π ± gap/2) — measures HOW CLOSE the failed attempts were.

## 5. Components to build

1. **Refine history recording** (`src/cwm/continuous/contract.py`):
   `refine_continuous(..., keep_history=False)`; when True, RefineResult
   carries `history: list[(code, accuracy)]` (one entry per iteration,
   including the initial synthesis) and `synthesize_and_evaluate` stores it
   in the cell as `"history"`. Default False → existing outputs byte-identical
   (golden-safe). The sweep driver turns it on.
2. **Sweep driver** (`scripts/continuous_ring2d_open_sweep.py`): iterates the
   §3 grid SHELLING OUT to `scripts/continuous_danger_synthesis.py` (one
   subprocess per cell) — reusing its provider handling, checkpoint/resume,
   and file naming untouched. Driver-level resume = skip cells whose result
   file already holds all requested seeds. A `--phase {0,1,2}` flag runs the
   validation subset / mini sweep / large additions. The CPU dense danger
   curve lives in the same driver behind `--cpu-curve` (no LLM calls).
3. **Aggregator** (`scripts/ring2d_open_aggregate.py`): globs the sweep result
   files + gap-0 legacy files, runs the audit instruments (import from
   `ring2d_artifact_audit.py` — refactor its per-cell core into an importable
   function), emits `results/continuous_ring2d_open_sweep_summary.json` with
   the three headline analyses' tables.
4. **Claude relay spots**: manual protocol via `scripts/continuous_claude_step.py`
   (already supports `--gap/--channel/--start/--prompt-variant`) — no code.

## 6. Guardrails (binding)

- ε=1e-9, N=40, ≤5 refines, incomplete arm: UNCHANGED from the closed arm.
- The topological summary's wording and detector (dedup 0.05, cap 90,
  3×median-NN Rips) are pre-registered instruments: DO NOT tune them. Their
  resolution limit is a measured object (the flip), not a bug to fix.
- `RingField2D` is not modified.
- The cart golden test suite must stay byte-identical (369 tests green);
  `keep_history=False` default guarantees the existing pipeline's outputs.
- Every run resumable per seed; the driver additionally resumes per cell.
  Long-running/money-costing runs MUST be interruptible without loss
  (standing rule).
- gap-0.6 exploratory cells are reused, never recomputed.
- No changes to pc/gate definitions; r(gap) always reported next to pc(gap).

## 7. Phases and budget

- **Phase 0 (validation, ~15 min Azure):** D-facing at gap 1.8 × 3 seeds mini
  (the within-gap-contrast cell) + A-facing at gap 0.2 × 3 seeds mini, both
  with history recording on; then the aggregator end-to-end on those cells +
  the existing gap-0/0.6 files. Gate: artifacts classified, per-cell guidance
  β̂₁ recorded (and varying at 1.8 if the seeds happen to straddle the flip),
  history recorded, resume works (re-running the same command is a no-op).
- **Phase 1 (mini sweep, ~2–3 h Azure):** full §3 mini grid + CPU dense curve.
- **Phase 2 (large + Claude, ~2 h Azure + manual relay):** large robustness
  cells; Claude spots (D at 2.4; A at the knee from the CPU curve).
- **Phase 3 (folds):** EXPERIMENTS.md fold; RESEARCH-DIRECTION/THEORY updates
  (the flip as "sensor resolution" instrument; H1 as the paper-3 thesis
  statement); paper-3 section notes.

Estimated Azure volume: ≈250 mini cells (~17 s A / ~46 s D per seed) +
80 large cells; well under prior arm budgets.

## 8. Outcome interpretation (pre-registered)

- H1 confirmed → the danger law's reachability axis is demonstrated on the
  synthesis side with a knob (gap) that leaves the synthesis failure intact:
  the headline paper-3 figure.
- H2 "guidance-following" → the TDA summary is a load-bearing part of the
  repair loop AND its resolution limit propagates into the artifact: honest
  summaries with finite resolution CAUSE wrong-topology models. H2 "prior" →
  strengthens paper 2's template-prior mechanism on a new instrument. H2
  "evidence-driven" → models read raw coordinates past the summary (would be
  the surprising branch; per-iteration history adjudicates HOW).
- H3 confirmed → gate-pass measures parameter guessability, sharpening the
  gate-quotient story (Prop 1): certification succeeds only where gauge
  freedom + round parameters align. H3 refuted (Claude passes at 2.4) →
  repair-from-inside is stronger than parameter-roundness; family-dependent
  rate again.
