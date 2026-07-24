# Design: PatchField2D — the 2D bi-modal instrument (paper 2)

Date: 2026-07-16
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved (brainstorming; user chose 2D + two patches, FULL apparatus
including 2D mitigation)

## Problem

§9 and the external review flag the remaining structural limitation: "both
modes are single stationary boundaries in a 2-dimensional state". This
instrument closes BOTH halves at once — higher-dimensional state (4D) and
multiple boundaries (two independent modes) — and unlocks genuinely new
science: the identifiability event becomes per-mode, the danger law composes,
and PARTIAL REPAIR (an artifact repaired on the seen mode, blind on the
unseen one) becomes measurable.

## The instrument (`PatchField2D`, in `cwm.continuous.envs`)

- State `[x, y, vx, vy]`. **Scalar action** `a ∈ [−a_max, a_max]` mapped to a
  heading: thrust vector `gain·(cos(π·a/a_max), sin(π·a/a_max))`. This
  preserves ALL planner machinery unchanged (mpc, cem, harness,
  collect_transitions consume scalar actions).
- Semi-implicit Euler, 4 variables (pinned in the contract):
  1. `phi = pi * clamp(a)/a_max`
  2. `vx2 = vx + (gain*cos(phi) − drag*vx)*dt`; `vy2` analogous with sin
  3. `x2 = x + vx2*dt`; `y2 = y + vy2*dt`
- **Modes**: two circular sticky patches `P_i = disc(c_i, R)`, each with its
  own field (`patch1`, `patch2`; `None` disables — `blind_of` variants per
  mode and both). Hard rule mirroring the wall: if `(x2, y2) ∈ P_i`, the
  next state is `[x, y, 0, 0]` — the probe stops inelastically at the edge
  (PREVIOUS position, zero velocity). This semantics is load-bearing for the
  2D mitigation (see below).
- **Reward**: radial sigmoid lodes — small real lode near the start, large
  phantom lode behind the patches (`amp/(1+exp((dist(p, lode)−r0)/w))`).
  The blind planner aims straight at the phantom and freezes at a patch edge.
- **Knobs**: the two patch centers' distances along/off the start→lode
  corridor. Target calibration: r₁ ≈ 0.15 (near patch), r₂ ≈ 0.02 (far
  patch) so that at N=40 the partition {miss both, see 1 miss 2, see both}
  has usable mass (P(see 1, miss 2) ≈ 0.45). PROVISIONAL until the
  calibration prototype; adjust globally, never per-cell.

## New science

- Per-mode identifiability: P(sample misses both) = (1−r₁)^N (1−r₂)^N — the
  law composes mode-wise. Report per-mode and joint.
- **Partial repair** (the headline measurement): an artifact from a sample
  that contains patch-1 contacts but no patch-2 contacts should repair P₁
  and stay blind to P₂ — certified at gate 1.000, exploited exactly at the
  mode its sample was silent on. Per-mode blindness makes this measurable.
- Repair difficulty vs mode geometry: the circular-patch condition
  (`(x2−cx)² + (y2−cy)² ≤ R²`) is harder to induce than a half-line clamp;
  §9 anticipates repair may weaken — either outcome is a finding.

## Machinery generalization (minimal, golden-protected)

1. Error comparisons that assume 2 state components generalize to all
   components (`max over i of |st[i]−sm[i]|`, plus reward):
   `gate.transition_error`, `contract.contract_accuracy`'s sandbox
   comparison, `contract.SynthesizedModel.step` (return `tuple(s2)`),
   `mitigation.run_mitigated_episode`'s violation check. Backward-compatible;
   the cart golden test must still pass byte-identically.
2. `InstrumentSpec.mode_probes(env)` returns a dict `{mode_name: [(state,
   action), ...]}`; `mode_blindness` returns per-mode values. For cart and
   pendulum: a single mode (`"wall"`/`"stop"`), and the EMITTED JSON keys
   (`wall_blindness` scalar, `sample_contains_wall` bool) stay unchanged for
   them. The 2D instrument emits per-mode dicts under new keys
   (`mode_blindness: {patch1: .., patch2: ..}`, `sample_contains_mode:
   {patch1: .., patch2: ..}`) alongside a conservative scalar
   `wall_blindness` (mean) for schema compatibility.
3. New `PATCH2D` InstrumentSpec: 4-variable api_text (with the heading
   mapping stated), rules_text with one clause per patch (each omittable
   independently: arms full / omit-P2 / omit-both), per-mode probes (states
   just outside each patch moving inward).
4. `mpc.py`, `cem.py`, `harness.py` are NOT modified. mpc's constant
   candidates give east/west; piecewise-constant blocks give turning paths —
   whether the truth planner can route around patches is PROTOTYPE-GATED
   (see risks). `n_samples` may be raised per-call (a plan() argument, not a
   code change).

## 2D mitigation (design, prototype-gated)

The 1D one-sided-fence argument SURVIVES with the stay-at-previous-position
semantics: a violation means the model predicted a position inside a patch
while truth kept the probe outside — so refuted predictions lie INSIDE the
patch, a region unreachable in truth. Fencing them cannot cut off any real
trajectory. Design: fences = 2D positions of refuted predictions; a candidate
rollout truncates when an imagined STEP SEGMENT passes within ε of any fence
(segment-to-point distance — leap-proof); flee tie-break = final imagined
position's euclidean distance to the nearest fence. `eps` fixed per
instrument (order of the patch radius).

Honest prediction to measure (not a failure): the 1D single-violation
sufficiency becomes a BOUNDARY-MAPPING transient in 2D — the planner can
skirt one fence disc and re-contact the patch edge elsewhere, accreting
fences along the probed arc. Report violations-per-episode and the transient
length; compare to 1D's mean_violations = 1.0.

## Experiments

1. **Calibration prototype (controller, before the SDD plan)**: (a) truth
   planner navigates around patches to the real lode with unmodified mpc at
   feasible n_samples; (b) blind planner freezes at a patch (play_cost ≈ 1);
   (c) rarity knobs give the target r₁/r₂ split. Iterate lure/patch geometry
   here — this is where the design doc says the time goes. Only then write
   the plan.
2. **Mechanism (CPU)**: bi-knob sweep (~3×3 grid), per-mode rarity, per-mode
   and joint danger law, knob-invariant play_cost.
3. **LLM synthesis** (Azure GPT-5.x mini + large, 20 seeds/cell, N=40,
   eps=1e-9, same pipeline): headline bi-knob cell; classify per-seed by the
   partition {miss both → doubly blind; see 1 miss 2 → PARTIAL repair
   expected; see both → full repair expected}; per-mode blindness recorded;
   play on gate-passing artifacts. Repair-vs-geometry finding either way.
4. **Cheap rows**: eps-sweep row (mode-arm rarity flat in ε on the 2D
   instrument) and CEM row (not exploited, near-zero crossing) — mirroring
   the existing tables.
5. **Mitigation 2D sweep**: knob grid × {truth, blind-both, mitigated},
   paired seeds; violations-per-episode, boundary-mapping transient,
   play_cost collapse.

## Paper integration

- New instrument section (placement by flow: likely a subsection in the
  mechanism section + rows/paragraphs in synthesis, axis/eps, CEM and
  mitigation sections; the partial-repair result gets its own paragraph in
  the synthesis section).
- §9: "one dimension, single stationary boundary" limitation FALLS; the
  honest residue becomes contact-rich manipulation / moving boundaries /
  the 2D mitigation's boundary-mapping transient scope.
- Abstract: one clause (2D bi-modal instrument; per-mode identifiability;
  partial repair). Keep ≤1920 chars rendered.
- EXPERIMENTS.md dated entries per experiment; guard clean on both papers.

## Out of scope (YAGNI)

- Moving boundaries, 3+ modes, contact-rich manipulation (stay future work).
- Vector actions or changes to mpc/cem/harness.
- Cross-family (Qwen/Claude relay) on the 2D instrument — the three-family
  picture is established on two instruments; 2D cross-family only if the
  user asks later.
- Per-cell tuning of eps/tol/knobs after calibration freezes them.

## Risks

- Truth-planner navigation with scalar-heading MPC (prototype gate a).
- Lure calibration with two knobs (prototype gate c; known time sink).
- LLM repair of circular geometry may stall more — that is a finding, but
  budget max-iters stays at 5 (no protocol inflation to force repairs).
- 4D synthesis prompts are longer (30 examples × 4-component states); if
  token pressure appears, examples stay at 30 (protocol constant) and we
  note the cost.
