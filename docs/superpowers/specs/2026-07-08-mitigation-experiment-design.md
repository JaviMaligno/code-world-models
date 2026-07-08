# Design: mitigation experiment — distrust-region replanning (paper 2)

Date: 2026-07-08
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved (brainstorming), pending implementation plan

## Problem

Paper 2's §9 admits "one planner family" and makes an unmeasured claim: *"a
planner with online model-error feedback (e.g., replanning on
prediction-violation) would break the loop — that is a mitigation claim
consistent with our thesis (verify on the deployment distribution), not
against it."* This project turns that claim into a measured result.

The exploitation loop today: at each of the episode's 80 steps, random-shooting
MPC plans on the mode-blind model, which imagines coasting through the phantom
region toward the large plateau; truth clamps the state at the wall/stop; the
planner stays pinned for the whole episode at play_cost ≈ 1 (below random),
knob-invariantly. Crucially, at every step the planner already holds the
information needed to detect the failure — it predicted `ŝ = model.step(s, a)`
and observed `s' ≠ ŝ` — and discards it.

## Framing (formal vs empirical — keep these separate)

- The mitigation does NOT contradict the danger law. The gate still certified a
  wrong model; nothing about (1−r)^N changes. What the experiment shows is that
  the *exploitation* is planner-mediated, and that deployment-time feedback
  (prediction-vs-observation, free to the planner) recovers performance.
  "Verify on the deployment distribution", operationalized at runtime.
- Theoretical tie-in: the mitigated planner must touch the mode ONCE to learn it
  exists — consistent with identifiability (you cannot avoid what you have never
  seen). The residual play_cost ≈ the cost of that first contact plus the escape
  transient. Report it as such; do not claim the mitigation is free.
- The zero-cost control is exact, not empirical: with a correct model no
  violation ever fires, so the mitigated planner is bit-identical to plain MPC
  by construction (asserted in tests).

## Mechanism (planner-side only; the model is never touched)

New module `src/cwm/continuous/mitigation.py`:

- **Violation detection** (real steps): after executing `a` from `s` and
  observing `s'`, compare with the model's prediction `ŝ = model.step(s, a)`.
  If `max(|ŝ₀−s'₀|, |ŝ₁−s'₁|) > tol` with `tol = 1e-6`, record the
  **pre-state** `s` as a violation point. (Pinned-integrator world: a correct
  model matches to float precision, and any real mode mismatch is orders of
  magnitude above 1e-6 — the threshold is not delicate.)
- **Distrust-region truncation** (imagination): while scoring a candidate
  action sequence, the first time the imagined state comes within ε of any
  violation point — distance measured on the position coordinate `state[0]`
  only — the rollout is TRUNCATED: reward accumulated so far is kept, all
  subsequent imagined reward is dropped. Rationale: once the imagined
  trajectory reaches a place where the model was observed wrong, nothing
  downstream of it is trustworthy. (A reward-only mask inside the ball would
  NOT work: the phantom lure lies beyond the wall, and a trajectory could cross
  the ball and still collect the phantom plateau on the far side.)
- **Tie-break when everything truncates**: if the current state is already
  inside a distrust ball (the pinned situation), every candidate truncates
  immediately and scores ~equal. Principled tie-break: after truncation the
  rollout keeps stepping the model WITHOUT accumulating reward, and the
  candidate whose FINAL imagined state maximizes distance to the nearest
  violation point wins — "flee the distrusted region when nothing is
  trustworthy", with full-horizon lookahead. (Design delta 2026-07-08, from
  implementation: the original first-imagined-state metric was myopic — when
  two violation balls overlap, the one-step flee gets trapped at the local
  distance-maximum between them, the midpoint. The final-state metric clears
  merged balls and also breaks the previously-exact tie at the resting pinned
  state — the away-from-lure direction wins strictly. Using the model's
  kinematics beyond the truncation point for DIRECTION only is weaker trust
  than believing its reward claims; no reward is ever accumulated there.)
  Deterministic; no dependence on candidate enumeration order.
- **ε per instrument**, fixed across knobs (not tuned per knob): cart ε = 0.25,
  pendulum ε = 0.1 (the scale of each instrument's reward sigmoid width). If
  calibration shows these are bad defaults, adjust once, globally, and record
  the change.
- The episode loop lives in `mitigation.py` (`run_mitigated_episode(truth,
  model, seed, ...)`), mirroring `harness.run_episode`'s signature and Episode
  return, plus violation metadata (count, first-contact step).

## Measurement

`scripts/continuous_mitigation.py` (CPU-only, ~10–15 min):

- Instruments and knob grids — PROVISIONAL, mirroring the paper's existing
  sweep tables for the exploitation side; adjust after a first calibration run
  if any knob is degenerate:
  - cart: `x_wall ∈ {2, 4, 6, 8, 10}` (danger-curve grid)
  - pendulum: `th_stop ∈ {0.8, 1.0, 1.2, 1.4, 1.6, 2.0}` (§4.1 grid)
- Three arms, paired seeds, 20 episodes/knob: truth-MPC, blind-MPC (existing
  behavior), blind-MPC + mitigation.
- Per knob report: `play_cost_blind`, `play_cost_mitigated` (same normalized
  regret), blind/mitigated contact rates, mean violations per episode, mean
  first-contact step.
- Output: `results/continuous_mitigation.json` + printed table (one row per
  knob per instrument).
- Expected: play_cost drops from ~1.03 (cart) / ~1.0 (pendulum) to ≈ 0–0.1,
  knob-invariantly; mitigated contact rate ≈ 1 (the single unavoidable first
  contact) but contacts per episode collapse from ~all-steps to ~1.

## Tests (offline, no LLM; extend `tests/test_continuous.py` or a new
`tests/test_mitigation.py`)

1. Violation detection fires on a clamped transition and never on the truth
   model.
2. Bit-identity control: `run_mitigated_episode(truth, truth, seed)` returns
   exactly the same return/final state as `harness.run_episode(truth, truth,
   "mpc", seed)` on the same seed (no violations → identical action sequence).
3. Escape: on the blind model (cart x_wall=8), the mitigated episode (a) records
   ≥1 violation, (b) ends with final position off the wall, (c) return within a
   modest margin of the truth planner's and far above the pinned blind return.
4. Same escape test on the pendulum (th_stop=1.4).

## Paper integration

- New short subsection with the sweep table — placed after the synthesis
  result (end of §6) or as its own section before Related Work; decide by
  flow at writing time.
- §9: rewrite the "one planner family" limitation — the mitigation claim is
  now measured; the remaining honest scope is that random-shooting MPC is
  still the only BASE planner family.
- Abstract: one clause (the exploitation is planner-mediated and cheap
  deployment-time feedback removes it at the cost of one contact).
- EXPERIMENTS.md: dated entry with the table.
- `main.tex` recompiles clean (0 overfull >2pt, 0 undefined), committed
  `main.bbl` untouched.

## Out of scope (YAGNI)

- Online model patching (that is repair — covered by the LLM arms) and
  conservative-fallback policies.
- Mitigation on LLM-synthesized artifacts (the hand-written blind proxy is the
  same code path; adds Azure cost, no information).
- Per-knob tuning of ε/tol; alternative distrust metrics (full-state balls,
  Mahalanobis, etc.).
- Changes to `mpc.plan`'s candidate scheme.
