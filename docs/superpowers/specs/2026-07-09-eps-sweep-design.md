# Design: ε-sensitivity sweep of the deployment-realistic gate (paper 2)

Date: 2026-07-09
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved (brainstorming, user-approved inline with pendulum added)

## Problem

The design doc lists an open risk: *"ε/integrator confounds: killed by the
pinned-integrator contract, but the deployment-realistic loose-ε arm needs a
documented ε-sensitivity sweep."* The axis-separation experiment (§5) runs the
deployment-realistic tolerance gate at a single ε = 0.01. This project
documents the full ε axis, killing the confound.

## Claim to document

**The tolerance axis is orthogonal to the identifiability hole.**

- **Mode-omitted arms** (cart wall@4/wall@8; pendulum stop@1.0/stop@1.4): the
  model's error is a discontinuity — it jumps from 0 to O(1) at the mode — so
  reveal-rarity (and hence pass@N = (1−r)^N) must be **ε-independent** across
  ~7 orders of magnitude (1e-9 → ~0.3, i.e. from float-noise scale to the
  error's own scale). Tightening the tolerance cannot catch the mode;
  loosening it does not widen the hole.
- **Pervasive-bias arms** (drag ×1.03, ×2.0 — on BOTH instruments; `biased_of`
  is a drag rescale and both plants have drag): reveal-rarity switches 1 → 0
  as ε crosses the arm's error scale — the tolerance axis polices pervasive
  error and only pervasive error.
- **Smooth-bump arms** (cart only — the bump is a CartWall field; N/A on the
  pendulum, noted): amplitude-dependent transition, analogous to bias.

## How

New `scripts/continuous_eps_sweep.py` reusing the existing gate machinery
(`gate.reveal_rarity`, `gate.gate_pass_rate` — same functions
`continuous_axes.py` uses):

- ε grid (log): {1e-9, 1e-6, 1e-4, 1e-3, 1e-2, 3e-2, 0.1, 0.3}.
- Arms: cart — wall@4, wall@8, bias×1.03, bias×2.0, bump amp0.5, bump amp1.0
  (the six axis-separation arms); pendulum — stop@1.0, stop@1.4, bias×1.03,
  bias×2.0.
- Per (arm, ε): reveal-rarity with 2000 rollouts (Wilson CI). For the
  mode-omitted arms additionally the empirical gate pass@40 with 300
  independent gates, to exhibit pass@40 ≈ (1−r)^40 holding at every ε.
- No play re-measurement: the model does not change with ε, so play_cost is
  ε-independent by construction (state this, don't measure it).
- Output: `results/continuous_eps_sweep.json` + printed table. ~10–25 min CPU
  (pendulum roughly doubles the cart cost).

## Tests (offline, fast)

- The wall arm's reveal-rarity is IDENTICAL at ε=1e-6 and ε=1e-2 (same seed,
  small rollout count) — the ε-flatness property in miniature.
- The supra-bias arm's reveal-rarity is 1.0 at ε=1e-6 and 0.0 at ε=0.3 (the
  switching property).

## Paper integration

- §5 (axis separation), both `preprint-draft.md` and `main.tex`: short
  paragraph + mini-table (reveal-rarity vs ε for the headline mode arm and
  the two bias arms; note the pendulum replicates) — "the (1−r)^N hole is
  flat in ε; bias policing switches at ε = the error scale".
- EXPERIMENTS.md: dated section with the full table (all arms × all ε).
- Design doc: annotate the ε-confound risk as RESOLVED (pointer to this
  spec + results).
- `main.tex` recompiles clean (0 overfull >2pt, 0 undefined), committed
  `main.bbl` untouched.

## Out of scope (YAGNI)

- Re-measuring play_cost per ε (ε-independent by construction).
- Smooth-bump arms on the pendulum (no bump field; a pendulum bump instrument
  would be new engineering for no new claim).
- Any change to `gate.py` / the ε=0.01 default of `continuous_axes.py`.
