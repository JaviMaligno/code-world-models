# Continuous/Hybrid CWM — Rare-Mode Danger Law — Design

Status: design 2026-07-06. Direction spec for the **follow-up paper** (paper 2),
to be developed in this repo. Not part of the frozen arXiv submission; paper 1
points here conceptually via Remark "continuous settings" (`main.tex`,
`rem:continuous`), which states exactly which parts of the analysis transfer.
Nothing in this spec has been run.

## Thesis (what paper 2 claims)

The danger law `danger = play_cost × (1−rarity)^N` transfers to
continuous-state control when the critical event is a **hybrid mode boundary**
(contact, hard stop, saturation, regime switch). Concretely:

1. **The law is measure-theoretic.** Replace "rule fires" by "trajectory
   intersects a critical region R" with `r = P_ρ(R)` under the verification
   distribution; the gate-miss probability is `(1−r)^N` verbatim, dimension-free.
   Identifiability (a sample that never intersects R carries no evidence about
   the dynamics on R) and the play-cost upper bound via query-hit mass
   (coupling argument, planner-agnostic) transfer with only notational change.
2. **The localization premise requires hybrid dynamics.** In smooth systems the
   characteristic model failure is pervasive compounding error (the classic
   MBRL story — Lambert et al. 2020, Janner et al. 2019); a failure that is
   *exact off a small region and categorically wrong on it* needs a
   discontinuity in the true dynamics. Hybrid systems provide it: an **omitted
   mode is precisely a rare rule**.
3. **Code synthesis makes the localization realizable.** A synthesized program
   has exact branches: omitting a guard yields a model bit-exact off the
   omitted mode and wrong on it — something a smooth learned model (MLP/GP)
   cannot represent cleanly. This is the new argument paper 2 adds over paper 1
   (not a repetition): the CWM paradigm *creates* in continuous control the
   localized failure class that the learned-model literature says doesn't
   dominate there.
4. **The planner exploits the omission.** MPC planning on the mode-blind model
   plans *through* the missing mode (phantom dynamics); truth stops it. This is
   model exploitation in its most literal form.

Expected shape of the result: the same **threshold law** as paper 1 — harm ≈ 0
while the boundary is commonly crossed by random rollouts, rising as the
boundary moves out of the rollout envelope, plateauing at full play_cost —
because competent (MPC) reach of the boundary should be knob-insensitive while
random reach falls. That reach-mechanism plot (`play_cost_reach.py` analogue)
is the first thing to measure.

## Primary instrument — cart-with-wall (1D double integrator + inelastic stop)

State `(x, v)`, action `a ∈ [−1, 1]`, dt fixed, dynamics
`v' = v + (a − c·v)·dt`, `x' = x + v'·dt`, **wall at `x_w`**: if `x' ≥ x_w`
then `x' = x_w, v' = 0` (inelastic; restitution `v' = −e·v` is a variant knob).
Task: maximize reward for holding position in a target band **at or just
beyond the approach to the wall** (e.g. reward peak near `x_w`), horizon `H`,
episodic return in `[0, 1]` after normalization.

Design requirements, mirroring army5x5a/material-at-cap:

- **(a) Random rollouts rarely reach the mode.** Initial states near the
  origin; random actions diffuse — `P(rollout hits wall)` falls quickly with
  `x_w`. This is the rarity knob: **sweep `x_w`** to trace `r` from common to
  ≈ 0 (the exact analogue of the `MAX_PLIES` cap sweep).
- **(b) Competent play concentrates on the mode.** The optimal controller
  drives at the wall at speed and *uses* the stop (brake-free arrival), or must
  brake precisely because the wall does NOT hold it — pick the reward so the
  wall's presence/absence changes the optimal plan qualitatively.
- **(c) Omission is exploited, not just mispredicted.** The wall-blind model
  predicts coasting through `x_w` into (phantom) high-reward territory; MPC on
  the blind model overshoots/never brakes; truth pins it at the wall with
  `v = 0` away from the plan. play_cost = normalized return deficit.

**Contrast arm — smooth localized perturbation** (the Connect-Four analogue):
replace the wall with a `C^∞` bump in drag centered at `x_w` of comparable
"size". Prediction: to be simultaneously gate-invisible (sub-tolerance off the
region) and play-consequential, a smooth perturbation must be large exactly
where competent trajectories go — the two requirements fight, so danger stays
low. This makes point 2 of the thesis an *experiment*, not just an argument.

**Second hybrid instrument (robustness, pick one):** pendulum with a hard
angular stop, or 2D navigation with a sticky patch. Same knob logic. Only
needed once the 1D result is clean.

## The gate

`N` i.i.d. rollouts: initial state ~ D₀, random action sequence (i.i.d.
uniform; OU-correlated as a variant), horizon `H`. Check every visited
transition: `‖f̂(s,a) − f(s,a)‖∞ ≤ ε`.

- **Pinned integrator (key design decision).** The synthesis contract pins the
  discretization (explicit Euler, given dt) so truth and synthesized model
  share it. Then the full-spec model can match to float precision and the gate
  can run at tiny ε — recovering an effectively *exact-match* gate and cleanly
  separating the localized axis (ours) from the sub-tolerance axis (classic
  MBRL). A loose-ε "deployment-realistic" variant is a secondary arm, not the
  headline.
- **Rarity is measured, and the law is checked for exactness**: `r` = fraction
  of rollouts hitting the wall (Wilson CI over R rollouts); observed gate-miss
  frequency across many gate draws must match `(1−r)^N` (paper 1's exactness
  proposition, re-verified in the continuous harness).
- **Pervasive-error control arm:** a model with a small global bias
  (δ < ε passes, δ > ε fails) shows the gate *does* police pervasive error
  while staying blind to the omitted mode — the axis separation, measured.

## The planner

MPC by random shooting / CEM (pure numpy): sample K action sequences over
horizon `H_p`, roll out on the model, take the best first action, replan.
Single-agent, so play_cost becomes **regret**:
`play_cost = (J(truth-model MPC) − J(blind-model MPC)) / (J(truth-model MPC) − J(random))`,
all evaluated in the true environment, seeds paired. No opponent confound —
cleaner than the two-player arena, and much cheaper than MCTS (2-dim state,
no game tree). The query-hit upper bound transfers: MPC queries its model on
imagined states, and the coupling argument in paper 1's Proposition
(play-cost bound) is already stated for any planner that is a deterministic
function of model responses + seed.

## Synthesis arms (the LLM loop)

Contract: `step(state, action) -> state`, `reward(state, action)`,
`is_terminal(state)` as pure Python over tuples/floats; spec = plain-text
physics description; pipeline structure reused from `cwm.synthesis`
(same refinement loop, gate as accept test).

1. **Full spec** (wall included) — must pass the tiny-ε gate; validates the
   pinned-integrator contract.
2. **Mode omitted from spec** — the headline arm: passes the gate whenever the
   sample misses the wall; MPC then exploits the phantom region.
3. **Repair arms** — wall never described, but demonstrated: (i) boundary-
   crossing transitions included in the training sample; (ii) targeted dose at
   the boundary. Tests whether translation-not-inference holds in the
   continuous regime (a numerically-manifested discontinuity may be *easier*
   to induce from data than a symbolic game rule — a real chance the finding
   is different here, which is informative either way).
4. **(Scope decision, default: include small)** an MLP dynamics arm trained on
   the same N rollouts: shows the smooth learner smears the boundary (errors
   are non-local), substantiating thesis point 3 and pre-empting the obvious
   reviewer demand. Keep it a probe, not a sweep; explicitly scope out
   Dreamer/MBPO-scale baselines.

Cheap/expensive split as in paper 1: a **hand-written wall-blind model** is the
exact on-manifold proxy (validated once against a real synthesis, then used
for all sweeps CPU-only).

## What transfers vs. what must be new (theory section of paper 2)

- Verbatim (restated measure-theoretically): gate-miss `(1−r)^N`;
  identifiability; danger law; play-cost upper bound via query mass.
- New: formalize "localization needs discontinuity" — e.g., if true dynamics
  and model are both L-Lipschitz and the model errs by η at a point, the error
  region has measure bounded below (ball of radius ~η/2L), so gate-invisible
  ⇒ small η ⇒ small play effect under smooth value functions; the wall breaks
  the Lipschitz premise. Even a clean toy proposition here is the paper's
  theoretical anchor.
- Does NOT transfer: the coverage/enumeration results (finite info-sets).
  Covering-number analogues are open; mention as limitation, do not attempt
  for paper 2 headline.

## Components

- `src/cwm/continuous/` — `envs.py` (cart-wall + smooth-bump contrast +
  pendulum-stop), `gate.py` (rollout gate, ε, miss-frequency check),
  `mpc.py` (CEM/random shooting), `contract.py` (synthesis contract text +
  function-loading harness, mirroring the games contract).
- `scripts/continuous_reach.py` — the mechanism plot first (competent vs
  random wall-reach across `x_w`), it predicts whether the threshold law will
  appear before anything expensive is run.
- `scripts/continuous_rarity_sweep.py`, `scripts/continuous_play_cost.py`,
  `scripts/continuous_danger_synthesis.py` — direct analogues of `law_sweep`,
  `play_cost_ci`, `danger_synthesis_sweep`.
- Reuse: Wilson/CI helpers, sweep+JSON-reporting patterns, Azure synthesis
  client, EXPERIMENTS.md logging discipline.

## Tests

- Env unit tests: wall handling (no tunneling at any `dt·v`), energy/sign
  sanity, smooth-bump arm is genuinely `C^∞` at the patch edges (finite-diff
  check).
- Gate exactness: empirical miss frequency vs `(1−r)^N` within binomial CI.
- MPC sanity: truth-model MPC on a no-wall instance ≈ analytic optimum of the
  double integrator (LQR-comparable check); random-policy baseline pinned.
- Proxy validation: hand-written blind model vs one real blind synthesis play
  at parity (the 2026-06-26 validation, repeated here).
- Pinned-integrator check: full-spec synthesis matches truth to float ε on 10⁵
  random transitions.

## Risks / open questions

- **Reward placement is the instrument-engineering crux** (the analogue of
  finding material-at-cap): the wall must be *useful* to the optimal policy or
  *fatal* to the blind plan, not incidental. Budget iteration time here.
- **ε/integrator confounds**: killed by the pinned-integrator contract, but
  the deployment-realistic loose-ε arm needs a documented ε-sensitivity sweep.
- **Repair may succeed here** (a numeric discontinuity is visible in data in a
  way a symbolic rule is not). Not a risk to the thesis — either outcome is a
  finding — but frame the paper so it doesn't depend on repair failing.
- **Reviewer pull toward learned-model baselines**: pre-empt with the small
  MLP probe + explicit scoping to synthesized-code world models.
- Effort: CPU core (env + gate + MPC + reach/rarity sweeps) ≈ 1–2 weeks
  part-time; synthesis arms on top of the existing pipeline; total well under
  paper 1's cost (no game tree, no arena, 2-dim state).

## Runbook — LLM arms (run in an environment with Azure credentials)

Everything below is implemented and validated offline (FakeProvider drives
the identical code path in `tests/test_continuous_contract.py`); only the
credentialed run remains.

**Prerequisites.** `<repo-root>/.env` with the same variables as paper 1:
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`,
and `AZURE_DEPLOYMENT_MINI` / `AZURE_DEPLOYMENT_LARGE` (/ `_NANO`).
`pip install -e .` (needs `python-dotenv`, `openai` — already in
pyproject).

**Commands** (from the repo root):

```bash
# Headline cell: x_wall=8 (gate misses the wall in ~60% of seeds at N=40)
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5
# Caught cell for contrast: x_wall=4 (gate nearly always sees the wall)
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5 --x-wall 4
# Repeat with `large` when mini's behavior is understood
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 5
```

Cost/time: ~2–7 LLM calls per seed (1 synthesis + refinement iterations),
1–2k prompt tokens each — comparable per-seed to paper 1's danger-sweep
cells (cents). Wall-clock is dominated by the CPU play evaluation
(~1–2 min/seed). Output: `results/continuous_synthesis_<size>_xwall<N>.json` (parametrized by
x_wall so multiple cells do not overwrite each other) +
a printed per-seed line and a cell summary with the identifiability
conditional.

**What each seed logs** (improving on paper 1, which could not condition
post hoc): `sample_contains_wall` (the identifiability event), gate
accuracy/iterations at eps=1e-9 (pinned integrator: correct code matches to
float precision — validated offline), `wall_blindness` (wall-region probe,
1.0 = clamp absent), and play (`play_cost`, `play_contact_rate`).

**Predictions to check against:**
- `full` arm: gate 1.0 in 0–2 iterations, wall_blindness 0.0, play_cost ≈ 0.
  If gate fails ONLY on float noise (max err ~1e-12 in the failures list),
  rerun with `--eps 1e-6` and record it — that is a pinned-integrator
  contract finding, not a synthesis failure.
- `incomplete` arm, wall absent from sample (~60% of seeds at the defaults):
  gate 1.0 + wall_blindness 1.0 + play_cost ≈ 1 with play_contact_rate 1.0
  (pinned at the wall) — the full paper-1 headline, synthesized.
- `incomplete` arm, wall present in sample: translation-not-inference
  predicts the gate cannot reach 1.0 (wall transitions are inexplicable to a
  wall-less program). Watch refinement here: a numerically-manifested
  discontinuity may be EASIER to induce from data than a symbolic game rule
  (the model may well invent the clamp from the failing transitions). Either
  outcome is a finding; if it repairs, that is the interesting divergence
  from paper 1 and becomes its own section.

**Troubleshooting.** Synthesized code import/exec errors surface in the
failures list via the sandbox (`'error': repr(e)`) and count as accuracy 0
— the refine loop feeds them back. If a deployment name differs, the env
var mapping is at the top of the script. The script is restartable: each
run overwrites its own JSON only.

## Order of work (resume here)

1. `envs.py` cart-wall + tests; `continuous_reach.py` mechanism plot — **go/no-go:
   competent reach flat, random reach falling** (if not, re-engineer reward).
2. Rarity sweep + hand-written blind proxy + MPC play_cost → danger curve
   (CPU-only paper skeleton).

> **Update (2026-07-06): steps 1–2 DONE, go/no-go PASSED.** Code:
> `src/cwm/continuous/` (envs, mpc, harness) + `tests/test_continuous.py` +
> `scripts/continuous_reach.py`; results in EXPERIMENTS.md §"PAPER 2 —
> Continuous/hybrid instrument" and `results/continuous_reach.json`. Rarity
> sweeps 0.331→0.002 over `x_wall ∈ [2,10]`; play_cost ≈ 1.03 knob-invariant
> (blind planner scores below random — pinned at the wall all episode, every
> knob); danger threshold law reproduced with the full (1−r)^N elbow inside
> the sweep. Design deltas vs this spec, from calibration: (i) reward is two
> sigmoid *plateaus* (not a Gaussian band near the wall) — point lodes demand
> braking finesse random shooting lacks; (ii) the far lode at x=12 with walls
> swept in [2,10] decouples the lure from the knob and keeps play_cost flat;
> (iii) MPC candidates must be piecewise-constant + constant {−1,0,+1} — with
> i.i.d. per-step candidates, imagination is diffusive, truth/blind rank
> candidates identically and the wall never enters imagination; (iv) play_cost
> is normalized regret and can exceed 1 (blind < random) — report unclamped.
3. Pinned-integrator synthesis contract + full-spec/omitted arms (mini first).
4. Exactness + pervasive-error control + smooth-bump contrast.
5. Repair arms + MLP probe + second hybrid instrument as robustness.
6. Draft paper 2 (`docs/paper2/`), reusing paper 1's theory section structure.

> **Update (2026-07-06): step 4 DONE (CPU), step 3 READY (awaiting a
> credentialed run — see the Runbook above).** Axis separation measured
> (`scripts/continuous_axes.py`, EXPERIMENTS.md §"Axis separation"): the
> tolerance gate polices pervasive error (supra-eps rejected always,
> sub-eps passes and is harmless), is blind exactly (1−r)^N to the hard
> mode (empirical pass rate matches the prediction in both wall rows), and
> the smooth bump has wall-like rarity with zero (amp 0.5) or *negative*
> (amp 1.0 — model optimism beats horizon-pessimistic truth planning)
> play_cost. Synthesis pipeline (`cwm.continuous.contract` +
> `scripts/continuous_danger_synthesis.py`) validated end-to-end offline
> with FakeProvider, including float-exactness of the pinned-integrator
> gate at eps=1e-9 through the sandbox.

> **Update (2026-07-07): step 3 RUN (credentialed, 3 cells) and step 5's
> probes largely resolved.** Results in EXPERIMENTS.md ("LLM synthesis arms
> executed" + "Smooth-learner probe"). Key outcomes vs this spec: (i) the
> wall-absent identifiability cell reproduces paper 1's headline end-to-end
> synthesized (4/4 across mini+large: gate 1.000, blind 1.0, play_cost
> 0.999); (ii) the anticipated divergence HAPPENED — with the wall in the
> sample the LLM repairs the mode (large: 3/3 in 1 iter, exact global rule;
> mini: most seeds, with stalls being superstitious local patches the gate
> correctly rejects), so the dedicated repair arms (item 5.i/ii) are RESOLVED
> organically: repair-from-data works in this regime and the danger collapses
> to the pure (1−r)^N event; (iii) the smooth-learner probe shows
> identifiability is learner-independent (a wall-free linear fit passes both
> gates, fully blind) and that smooth learners cannot localize the mode
> (4 contact rows tilt the linear fit 12 orders of magnitude off-mode).
> Remaining from item 5: only the optional second hybrid instrument.
> Next: item 6 — draft paper 2 (`docs/paper2/`).

> **Update (2026-07-07, later): item 6 STARTED.** First full prose draft at
> `docs/paper2/preprint-draft.md` (abstract, instrument + the three design
> lessons, theory transfer incl. the new Proposition 4 "smoothness forbids
> localized error" with proof, Tables 1–3 from the measured runs, the
> synthesis three-way result, smooth-learner probe, related work,
> limitations, reproduction appendix). Numbers cross-checked against
> EXPERIMENTS.md; re-verify before submission as usual.
