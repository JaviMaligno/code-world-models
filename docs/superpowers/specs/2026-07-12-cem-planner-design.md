# Design: second planner family (CEM) — play_cost is planner-dependent, as Proposition 3 prescribes

Date: 2026-07-12
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved (user-approved reframing after controller prototype)

## Problem

§9 admits "one base planner family" and the external (Codex) review flags it:
the paper's exploitation claims rest on random-shooting MPC alone. The naive
goal ("show CEM is exploited too") was **falsified by a controller prototype**
(2026-07-12): CEM with per-step Gaussians and iterative elite concentration is
**not** exploited — pc_blind ≈ 0.000, zero contact — while remaining
competent on truth (cart ≈ 97% of MPC-truth).

## The finding to publish (reframing)

This is the *other branch of Proposition 3*, measured. play_cost ≤ μ_query(E)
(times the range factor): exploitation requires the planner's imagination to
hit the critical region. Random shooting **with constant candidates** reaches
the distant phantom plateau in imagination (high query-hit mass on E) → lured,
pinned, play_cost ≈ 1. CEM's local search concentrates on the nearer TRUE
plateau from the first elite iteration and never discovers the phantom (≈0
query-hit mass) → play_cost ≈ 0. The certified-blind model is a landmine
whose detonation depends on the planner's reach — planner-mediated danger,
exactly as the theory prescribes, now measured on both branches. (This also
connects to §2.3's design lesson iii: i.i.d. per-step candidates are
diffusive and "the wall never enters imagination" — CEM is the principled
version of that observation.)

Honest caveats to report: CEM occasionally lands in local optima on the
pendulum truth (prototype: 14.3 vs 20.1 at one seed); the claim is about the
blind-arm geometry, not CEM's optimality. And the result does NOT license "use
CEM and you are safe": a planner blind to the phantom is also blind to real
distant reward; the safety is an artifact of limited reach, not of knowledge.

## Mechanism (prototype-validated hyperparameters)

New module `src/cwm/continuous/cem.py` (additive; no existing module touched):
- `plan_cem(model, state, rng, horizon=40, n_iters=5, n_samples=64,
  elite_frac=0.125, min_std=0.05) -> float`: per-step Gaussians initialized
  (mean 0, std a_max), samples clipped to [−a_max, a_max], elites = top
  n_samples·elite_frac by imagined return, mean/std refit per timestep, std
  floored at min_std; returns the final elite-mean first action.
  Deterministic given rng.
- `run_episode(truth, model, seed, boundary=None, **plan_kw)` mirroring the
  harness episode loop; when `boundary` is given (the mode position), it also
  accumulates the per-step fraction of CEM samples whose imagined trajectory
  crosses the boundary — the measured query-hit proxy.
- The measurement script also computes the same imagined-crossing fraction
  for the random-shooting MPC candidates (locally, via `mpc._candidates`) so
  the two planners' query-hit masses are compared apples-to-apples.

## Measurement

`scripts/continuous_cem.py` (CPU, ~30–60 min): both instruments, the usual
knob grids (cart x_wall {2,4,6,8,10}; pendulum th_stop {0.8,1.0,1.2,1.4,1.6,
2.0}); arms per knob on paired seeds × 20 episodes: truth-CEM, blind-CEM,
random (harness), plus the MPC imagined-crossing diagnostic on the blind
model. Report per knob: J_truth_cem, J_blind_cem, J_random, play_cost_blind
(CEM), blind contact rate, imagined-crossing fraction for CEM-blind and
MPC-blind. Output `results/continuous_cem.json`.

Expected: play_cost_blind(CEM) ≈ 0 knob-invariantly with ≈0 contact and ≈0
imagined-crossing, vs MPC-blind's high crossing fraction. Deviations are
findings, not failures — report as measured.

## Tests (offline, fast; new `tests/test_cem.py`)

1. Determinism: same seed → identical first action.
2. Competence on truth (cart@8, seed 0/3, prototype-validated): CEM-truth
   return ≥ 0.9 × MPC-truth return.
3. Non-exploitation (cart@8): blind-CEM episode has contact False, final
   position < x_wall − 1, return within 5% of CEM-truth (prototype: identical
   to 2 decimals).
4. Pendulum blind-CEM: contact False, no pinning at th_stop.

## Paper integration

- New subsection in the mechanism section (§4.x): "A second planner family:
  play_cost is planner-dependent, as Proposition 3 prescribes" — table (knob ×
  {pc_blind MPC (existing), pc_blind CEM, crossing fraction MPC/CEM}) or
  compact form; the landmine framing; the honest caveats.
- §9: the "one base planner family" limitation is rewritten — two families
  measured, one on each branch of Prop 3; remaining scope: no gradient-based
  or tree planners, and CEM's safety-by-limited-reach is not a mitigation.
- Abstract: one clause ONLY if it fits within 1920 chars (currently 1720);
  e.g. "; a second planner family whose search never reaches the phantom
  region is, as the play-cost bound prescribes, not exploited at all".
- EXPERIMENTS.md dated entry with the full table.
- `main.tex` recompiles clean under the guard.

## Out of scope (YAGNI)

- Gradient-based shooting, tree search, other planner families.
- CEM hyperparameter sweeps (one prototype-validated setting, stated).
- Mitigation × CEM interaction (the mitigation is defined for the exploited
  planner; CEM has nothing to mitigate here).
