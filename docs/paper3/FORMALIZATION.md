# Paper 3 — Lean formalization ledger

The formalization lives in `formal/Paper2Props/Paper3Ring/` (same Lake package
as paper 2's `Paper2Props` so the two share one mathlib build and one CI job —
`lean_proofs` in `.github/workflows/ci.yml` builds both default targets with
the mathlib binary cache). THEORY.md stays the statement of record; this file
maps its items to Lean declarations and says exactly what is and is not
machine-checked.

## The standing rule (2026-08-24, Javier's directive)

**From now on, when a THEORY.md item's proof lands (or changes), it gets
formalized in `Paper3Ring` in the same working session, or this ledger records
explicitly why not** (typical reasons: needs measure-theoretic infrastructure
we have not built; needs persistent homology, which mathlib does not have).
"Formalized" means the mathematical content at the level the proof actually
operates — for pathwise/realization arguments that IS the whole proof; for
probabilistic statements the realization core is formalized and the a.s.
wrapper is noted. The same strengthen-before-weaken discipline applies: a
statement that cannot be formalized as written should first be re-examined,
not silently weakened.

## Status (2026-08-24, first tranche)

| THEORY.md item | Lean declaration(s) | status |
|---|---|---|
| Lemma 2, crossing half | `lemma2_crossing` | **PROVED** (any pseudometric space; discrete IVT on the 1-Lipschitz distance) |
| Lemma 2, freeze half ("interior unreachable, not merely rare") | `freeze_stays_outside`, `lemma2_interior_unreachable` | **PROVED** (abstract state space with position projection; freeze preserves position) |
| Lemma 2, corollary (disc ≡ annulus evidence equivalence from outside) | `disc_annulus_traj_eq`, `disc_annulus_contact_iff` | **PROVED** (pathwise identity of trajectories AND contact processes) |
| "Constants at the frozen defaults" (Δ = 1.0 < w = 1.5) | `speed_invariant`, `ringF_step_dist` via `ring_interior_unreachable`, `ring2d_frozen_defaults_step_lt_thickness` | **PROVED**, including the integrator's speed invariant `‖v‖ ≤ gain/drag` through freeze events |
| r_int(0) = 0 (pathwise, at the defaults) | `ring2d_interior_unreachable_at_defaults` | **PROVED** for the RingField2D-shaped dynamics (semi-implicit integrator, `‖u‖ ≤ 1` heading, freeze on annulus landing) |
| Prop 1 (gate quotient) | `prop1_traj_eq`, `prop1_gate_quotient`, `prop1_no_statistic_distinguishes` | **PROVED at realization level** — the induction that IS the proof; the measure wrapper (a.s. over seeds) adds only quantification and is not formalized |
| Prop 3(i) (unfalsifiable), composed | `prop3_unfalsifiable_loop`, `prop3_no_statistic_distinguishes_loop` (`PlannerLoop.lean`, second tranche) | **PROVED**, upgraded past the plan: the loop version quantifies over ARBITRARY (state, time)-policies, so gate rollouts (state-independent policies) and closed-loop play are one statement — swapping the annulus for the filled disc changes no rollout of any policy from outside |
| Local crossing lemma (thin neck, 2026-08-24) | `freeze_stays_outside_of_superset`, `neck_interior_unreachable` | **PROVED** the same session the design landed (the standing rule's first exercise): a mode set CONTAINING the thin annulus `[r_in, r_in+w]` with `w > Δ` seals the hole, whatever its shape — interior entry requires a single step longer than the neck. The deterministic leap witness at neck = 0.5 (`tests/test_ring2d_thin_neck.py`) is the measured complement |
| Prop 3(ii) (harmless / planner equivalence) | `disc_annulus_same_return` (engine) + `plannerPolicy`, `planner_actions_agree`, `prop3_harmless_loop`, `prop3_play_cost_zero` (`PlannerLoop.lean`, second tranche) | **PROVED, loop included**: the planner is any deterministic function of (state, time, the model's imagined rollouts over a candidate family with the contract step bound) — MPC/CEM are instances — and the real closed-loop trajectories under the two models' planners coincide realization-by-realization, so every return functional (play_cost included) is equal |
| Lemma T2-I (hybrid telescoping — exact) | `polRet`/`polTraj`/`prefixRet`/`advantage`/`hybrid`, `t2i_hybrid_telescoping`, `clean_step_advantage_zero`, `t2i_sum_over_dirty` (`Advantage.lean`, second tranche) | **PROVED**: J(π_T) − J(π_B) = Σ_{t<H} A_t exactly, clean steps contribute definitionally 0, and the sum restricts to the dirty steps — the identity that localizes all of play_cost on the dirty steps' advantage terms. Realization level (deterministic dynamics, Markov policies), exactly the setting THEORY.md states it in |
| Theorems T3-P and T3-P″ (defect monotonicity) | `t3p_defect`, `t3p_exact_of_no_funnel`, `t3p_double_prime`, `t3p_double_prime_exact_of_nondecreasing` (`Advantage.lean`, second tranche) | **PROVED from the named hypotheses** `hsplit` (r_int = d + f, the exclusive event split) and `hdirect` (Prop 7's conclusion d(γ₁) ≤ d(γ₂)): the defect bound, its exactness at f(γ₁) = 0, the sharper drop form [f(γ₁) − f(γ₂)]⁺, and exactness wherever f is nondecreasing. These theorems machine-check the step from Prop 7 to M1/M2-with-defect, where THEORY.md records two earlier wrong routes; Prop 7's own pathwise engine is now proved too (next row), and `hdirect` remains a hypothesis only through the measure wrapper (inclusion ⟹ inequality of measured d-values) |
| Prop 7 (direct entries pathwise monotone) | `freezeTraj_eq_of_avoid` (the engine), `entersDirectlyAt`, `prop7_direct_monotone`, `prop7_first_entry_preserved`, `direct_entry_traj_is_free`, `no_wall_every_entry_direct`, `channelMode_antitone`, `prop7_channel` (`DirectEntries.lean`, third tranche) | **PROVED at realization level**, and slightly past the paper's statement: the engine (freeze-free prefixes are mode-set monotone) holds for ANY mode sets `M₂ ⊆ M₁`; Prop 7 is transport along it, minimality of the first entry transports too, a direct trajectory is proved equal to the FREE trajectory through its entry (the `M₂ = ∅` case), the no-wall endpoint d(2π) = r_int(2π) is the vacuous-avoidance corollary, and the knob instantiation A(γ) = annulus \ S(γ) is antitone for any monotone sector family `S` (the sector's shape is never used, as the paper says). The measure wrapper (pathwise inclusion ⟹ d(γ₁) ≤ d(γ₂) over seeds) adds only monotonicity of a measure under inclusion and is noted, not formalized. THEORY.md's seed-50543 counterexample is visible in the formalization: no theorem here mentions full entries — the induction has no invariant without `havoid` |
| Prop 10 (fence sufficiency) | `loopTraj_eq_of_policy_agree` (the loop engine), `maximizers`, `maximizers_transport`, `prop10_fence_sufficiency`, `prop10_play_cost_zero` (`Mitigation.lean`, fourth tranche) | **PROVED from the named hypotheses**: at every state of the reachable envelope, mitigated and truth imagined returns agree on the non-crossing candidates, and every crossing candidate is strictly dominated under both (the dominance form of (COV)+(RG-west), the latter a measured margin, like T3-P's `hdirect`). Conclusion machine-checked: the maximizer SETS coincide — so any deterministic tie-break picks the same candidate — and the real trajectories are identical, play_cost exactly 0. The geometric step (COV ⟹ truncation of crossing candidates) stays with the mitigation module's semantics |
| Prop 11 (patch sufficiency) | `freezeTraj_eq_of_landing_mem_iff` (the coupling engine — Remark R2's "Lemma-3 coupling", generalized), `prop11_patch_sufficiency`, `prop11_play_cost_zero` (`Mitigation.lean`, fourth tranche) | **PROVED**: the patched mode set is `Mt ∪ (B \ N)` (truth mode plus the invented region minus the certified neighborhood); with (CERT) distilled — no queried landing in the residue `B \ N` from any reachable state — patched imagination equals truth imagination for every candidate (the coupling engine: mode sets agreeing on membership at every queried landing give identical trajectories), the planner picks the same action, and play_cost is exactly 0. The engine also subsumes `DirectEntries.freezeTraj_eq_of_avoid` as the `M₂ ⊆ M₁` special case |
| Prop 8, 1-D reduction (witness tube) | `prop8_witness_stays_on_axis` (`WitnessTube.lean`, fourth tranche) | **PROVED, the structural half**: for the instrument's own `ringF`/`ringFreeze` dynamics, axis-aligned heading inputs and initial velocity keep every state — freeze events included, any mode set — on the line `p₀ + ℝ·e`. The triage's feared "interval arithmetic over cos/sin" dissolves for the paper's witness (action ≡ 0 ⟹ heading exactly (1,0)) |
| Prop 8, in-horizon entry (numeric tail) | `vSeq`/`bSeq`, `vSeq_le_ten`, `vSeq_lower`, `vSeq_ge_five`, `bSeq_growth`, `prop8_scalar_window`, `prop8_window_is_interior`, `prop8_free_witness_follows_scalar` (`WitnessTube.lean`, fifth tranche) | **PROVED**: the witness's scalar recursion (the exact frozen-defaults integrator, from rest) reaches speed ≥ 5 by step 34 (ratchet: below 5 each step gains ≥ 0.15), the offset then gains ≥ 0.5 per step, and the first crossing of the window `[9.5, 10.5)` happens by step 53 < h = 80 without overshoot (no step exceeds 1); any window landing is strictly inside the hole in the instrument's own metric (`hypot < 3.5`, from the start box); and a freeze-free witness trajectory is proved to FOLLOW that scalar recursion exactly |
| Prop 8, channel membership + composed core | `hyp`, `sectorSin`, `ringModeSin`, `div_eight_le_sin_half` (Jordan for the η-margin), `witness_line_avoids_wall`, `prop8_positivity_core` (`WitnessTube.lean`, fifth tranche) | **PROVED, closing Prop 8 up to the measure wrapper**: the sector is modeled by its sine characterization on the west half-plane (`\|y\| ≤ d·sin(γ/2)` — the faithful model of `_in_gap_sector` there for γ ∈ (0, π], where every witness landing lives; larger γ has a smaller wall). Jordan's inequality (`Real.mul_le_sin`) with 8 > π turns the η(γ) = 3.5γ/8 margin into channel membership at every band radius, so the witness line avoids the wall outright, and `prop8_positivity_core` composes: from the start box, the constant-thrust witness reaches `hyp < r_in` within 53 < 80 steps against the γ-channel wall. What remains of THEORY.md's Prop 8 is ONLY the measure wrapper (the start box has positive probability) |
| Prop 5 (r nonincreasing in γ), realization core | `prop5_fire_monotone` (`Mitigation.lean`, seventh tranche) | **PROVED** from the coupling engine, unifying THEORY.md's two cases into one: take the first step at which the smaller-wall trajectory's landing is in the LARGER wall; before it the landings are in neither set, so the trajectories agree, and the larger-wall system fires there or earlier — fire(γ₂) ⊆ fire(γ₁) pathwise. The measure wrapper (⟹ r(γ₂) ≤ r(γ₁)) is noted as everywhere |
| T4's Lemma W (sliver-in-strip), geometric core | `lemmaW_sliver_in_strip` (`CapBound.lean`, seventh tranche) | **PROVED**: a point at radius ≤ r_out and angular offset `\|φ\| ≤ ε/4` from a line through the center is within `r_out·ε/4` of that line (via `\|sin\| ≤ \|·\|`) — each γ-sliver lies in its bisector strip. T4's remaining pieces: Lemma A's arcsin computations and the circle-measure preimage, Lemma S's exactly-uniform landing direction (a pushforward), and the h-step union bound — the measure assembly |
| T1's foundation layer (Lemma D⁻'s content; Lemma B's chord step) | `chordSq_eq` (law of cosines), `chordSq_comm`, `wrap`/`cos_wrap` (increments in `(−π, π]` via `Real.Angle`), `wrap_lt_of_chordSq_lt` (edge–angle bound), `wrap_triangle_sum`/`triangle_wrap_sum_eq_zero` (the triangle telescope, exact), `winding`/`triangleBoundary`/`winding_notin_boundaries`, `lemmaDminus_core` (`RipsCircle.lean`, seventh tranche) | **PROVED — Lemma D⁻'s mathematical content with the persistence bookkeeping stripped** (as the paper's own proof strips it): 1-chains as `Finsupp` ℤ-combinations of oriented edges, winding as the induced additive functional, and: below `√3·r_min` every edge's wrapped increment is inside `(−2π/3, 2π/3)` (cos > −1/2 + antitonicity), every triangle boundary has winding EXACTLY 0 (the 2π-multiple from the `Real.Angle` telescope is forced to 0), so a chain with nonzero winding is not in the subgroup generated by scale-s triangle boundaries. Remaining for the full T1 sandwich: the Rips/persistence language (birth/death of the BAR, Lemma P's class-to-bar transfer), Lemma B's existence half (the consecutive-neighbors cycle), and D⁺'s explicit filling 2-chain — a program, with this file as its foundation |
| T5's Lemma G, analytic core | `lemmaG_integral_core` (`CapBound.lean`, sixth tranche) | **PROVED**, generalized to any real exponent p ≥ 0 (Lemma G takes p = (n−3)/2): `∫_κ¹ (1−u²)^p ≤ (1−κ²)^{p+1/2}·∫_0¹ (1−y²)^p` — the substitution u = κ + √(1−κ²)·y (its Jacobian is the extra 1/2 in the exponent), the pointwise bound 1−u² ≤ (1−κ²)(1−y²), and the range enlargement, i.e. the entire computation Lemma G's proof runs on. NOT formalized (the genuinely probabilistic part, per the triage): the reduction from the uniform sphere measure to the 1-D marginal density, and Theorem T5-I's spherical-symmetry-of-sums step. Measured complement: the cap bound checked against the exact cap integral at n = 3…30 |

### Modelling notes (what the Lean statements quantify over)

- The abstract half runs over any `PseudoMetricSpace`; nothing uses ℝ² — the
  paper's honesty note ("metric, not topological; works verbatim for round
  shells in ℝⁿ") is visible in the generality of the formal statement.
- `freezeTraj` is the instrument's semantics abstracted: free step `F t`, mode
  set on the LANDING position, freeze-on-contact preserving position. The
  capstone instantiates it with the concrete semi-implicit integrator over any
  real normed space (`V = ℝ²` in the instrument; the proof needs nothing of
  the dimension), heading input of norm ≤ 1, and the frozen defaults as
  numerals checked by `norm_num`.
- Determinism: trajectories are functions of an action stream `ℕ → A`; "with
  the same realizations" in THEORY.md is exactly this parametrization.

## Status (2026-08-25, second tranche)

`PlannerLoop.lean` (Prop 3 composed: the closed loop, both halves) and
`Advantage.lean` (T2-I exact telescoping; T3-P/T3-P″ defect theorems) —
0 sorries, `lake build Paper3Ring` green (1674 jobs). Local build note: this
machine intermittently fails parallel from-source mathlib builds ("failed to
read file" on files that exist, exit 0xC0000409 — the saturation failure
mode this box is known for, lake has no jobs flag). `lake exe cache get`
fixes it: with the binary cache in place the library builds in seconds.

## Status (2026-08-25, third tranche)

`DirectEntries.lean` (Prop 7 and its engine) — 0 sorries, both default
targets green (8703 jobs). The engine turned out to need no coupling
machinery at all: the "coupled-trajectory setup" the earlier triage
predicted collapses to one induction on freeze-free prefixes, because a
direct trajectory never queries either mode set before its entry.

## Status (2026-08-25, fourth tranche)

`Mitigation.lean` (Props 10 and 11: the loop engine, the argmax-set
transport, the coupling engine) and `WitnessTube.lean` (Prop 8's 1-D
reduction) — 0 sorries, both default targets green (8705 jobs). Two
structural finds: the deterministic tie-break needs no least-index
machinery (any function of the maximizer SET transports, because the sets
themselves coincide); and Prop 8's witness needs no trigonometry at all —
constant action 0 makes the heading exactly (1, 0), so the tube reduction
is pure linear algebra (`module`).

## Status (2026-08-25, fifth tranche)

Prop 8 CLOSED up to the measure wrapper, all in `WitnessTube.lean` —
0 sorries, both default targets green (8705 jobs). The numeric tail (the
scalar window by step 53, the hypot bound into the hole, the freeze-free
linkage) and the channel membership both landed: the sector's sine
characterization on the west half-plane needs no angle API, and Jordan's
inequality (`Real.mul_le_sin`, with 8 > π) is exactly the η(γ) margin.
With this, every deterministic/realization-level item of THEORY.md's list
is machine-checked; what the triage below holds is genuinely
probabilistic or needs persistence theory mathlib does not have.

## Status (2026-08-25, sixth tranche)

One bite out of the probabilistic tail: Lemma G's analytic core landed in
`CapBound.lean` (0 sorries, both targets green, 8706 jobs) — the interval
integral inequality its proof runs on, generalized to any real exponent.
The frontier of the triage is now purely measure-theoretic assembly.

## Status (2026-08-25, seventh tranche)

Both remaining programs are STARTED, with their first machine-checked
layers (0 sorries, both targets green, 8707 jobs). On the measure side:
Prop 5's realization core turned out to be pathwise (one application of
the coupling engine — mis-triaged as probabilistic), and T4's Lemma W
landed. On the Rips side: `RipsCircle.lean` proves Lemma D⁻'s
mathematical content with the persistence bookkeeping stripped, exactly
as the paper's own proof strips it — no Rips complex machinery needed
for the mathematics that carries the result.

## Not yet formalized — triage

Ordered by (value × feasibility), highest first:

1. **T4/Prop 6 measure assembly** — Lemma A's arcsin computations and the
   circle-measure preimage `Leb{ψ : sin ψ ∈ I}`, Lemma S's exactly-uniform
   landing direction (pushforward of the uniform action), and the h-step
   union bound. Lemma W and Prop 5 are done; the rest is genuine measure
   work with mathlib ingredients.
2. **T5 measure assembly** — the sphere-measure reduction to the 1-D
   marginal density and T5-I's spherical-symmetry-of-sums step (Lemma G's
   analytic core is done); the Berry–Esseen transfer stays out of
   reasonable reach.
3. **T1's remaining floors** — on the `RipsCircle.lean` foundation: the
   Rips/persistence language (birth/death of the BAR, Lemma P's
   class-to-bar transfer), Lemma B's existence half (the
   consecutive-neighbors cycle), D⁺'s explicit filling 2-chain. T7's
   relative estimator sits above all of that. A program; the foundation
   layer exists now.

## Building locally

`formal/Paper2Props/` is the package root; `lake build` builds both libraries.
In a network-restricted environment the mathlib binary cache host
(`lakecache.blob.core.windows.net`) may be blocked — `Paper3Ring` deliberately
imports narrow mathlib modules (not `import Mathlib`) so `lake build
Paper3Ring` from source stays feasible; `Paper2Props` imports all of Mathlib
and effectively needs the cache. CI has the cache and builds everything.
