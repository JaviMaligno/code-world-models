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
| Lemma A's analytic cores, complete | `arccos_one_sub_eq` (the half-angle identity via `abs_sin_half`), `arcsin_le_pi_div_two_mul` (inverse Jordan), `le_arcsin`, `lemmaA_endpoint_bound` (arccos(1−ℓ) ≤ π√(ℓ/2)), `lemmaA_tangency_bound` (√ℓ ≤ arccos(1−ℓ/2)), `lemmaA_transversal_bound` (arcsin increment ≤ (2/√(3m))·length on intervals m/2-away from ±1, mean value inequality), `arcsin_increment_le_arccos` (the endpoint-maximality: over ANY [a,b] ⊆ [−1,1], arcsin b − arcsin a ≤ arccos(1−(b−a)) — proved by elementary trigonometry, no convexity: sum-to-product plus sin((β−α)/2) ≤ cos((α+β)/2) from (β−α)+\|β+α\| ≤ π) (`CapBound.lean`, eighth tranche) | **PROVED — every analytic step of Lemma A's four parts** |
| Lemma A(i), end to end | `volume_sin_mem_Icc` (the circle-measure preimage: over the period `[−π/2, 3π/2]`, `Leb{ψ : sin ψ ∈ [a,b]} = 2·(arcsin b − arcsin a)` — one interval per monotone branch of sin, meeting in at most the point π/2), `lemmaA_part_i` (`CapBound.lean`, eighth tranche) | **PROVED as a genuine measure statement** — the package's first: the strip event's measure over the full period is ≤ 2π·√(ℓ/2), i.e. the uniform-angle probability is ≤ √(ℓ/2), composed from the preimage, the endpoint-maximality and the arccos bound. Lemma A's parts (ii)/(iii)/(iv) now need only the same preimage plumbing if their measure forms are ever wanted; the analytic content is all machine-checked |
| Lemma B's gap-jump core (the birth lower bound) | `wrap_eq_add_int`, `exists_lift_above`, `exists_big_step_of_climb` (the upcrossing lemma), `lemmaB_gap_jump` (`RipsCircle.lean`, eighth tranche) | **PROVED**: a walk whose wrapped increments sum to 2πw, w ≠ 0, on vertices all keeping distance ≥ Δ/2 from every lift of the gap midpoint (no vertex in the open gap arc), has a step with \|wrapped increment\| ≥ Δ. The proof lifts the walk (no wrapping needed at all): the lift climbs 2πw, crosses a lift of the gap midpoint, and both crossing endpoints are ≥ Δ/2 away — the negative-winding case by NEGATING the lift, which sidesteps the wrap-reversal pathology at ±π. With the chord–angle bound this is Lemma B's `s_w ≥ 2·r_min·sin(Δθ_max/2)`. Remaining for full Lemma B: the existence half (the consecutive-neighbors cycle at the upper scale) |
| Lemma S (one-step landing law) | `lemmaS_landing_eq` (`WitnessTube.lean`: the read-off half — one integrator step from ANY state lands at drift-center + `gain·dt²`·heading, one `module`), `lemmaS_heading_uniform` (`CapBound.lean`: the measure half — the heading map `a ↦ π·a` carries the uniform action law on [−1,1] to `(1/π)`·Lebesgue on [−π,π], via `Real.map_volume_mul_left` and `restrict_map`) (eighth tranche) | **PROVED, both halves**: the landing law is exactly the uniform arc-length measure on the circle of radius `gain·dt²` about the drift center, state-independent |
| The per-step T4 ingredient, composed | `volume_sin_window_shift` (the period-window glue: split at the shared part, translate the tail by 2π with null endpoints), `lemmaA_part_i'` (`CapBound.lean`, eighth tranche) | **PROVED**: the strip bound `≤ 2π·√(ℓ/2)` holds over the heading's ACTUAL window `[−π, π]` — Lemma A(i) transported to where Lemma S delivers the uniform angle |
| T4's union-bound skeleton | `prod_slice_bound` / `prod_slice_bound'` (the Fubini conditioning step in both factor orders, via `Measure.prod_apply`/`prod_apply_symm` + `lintegral_mono`), `union_bound_le` (h events ≤ B each ⟹ union ≤ h·B) (`CapBound.lean`, eighth tranche) | **PROVED** — the two measure steps of T4's h-step argument, in both conditioning orders |
| T4's process wiring | `pi_union_slice_bound` (`CapBound.lean`, eighth tranche) | **PROVED**: for the (n+1)-fold product of the per-step action law, coordinate-`t` slice bounds uniform in the other coordinates give `μ(⋃ E_t) ≤ (n+1)·B·mass^n` — the `piFinSuccAbove` split composed with `prod_slice_bound'` per step and the finite union bound. Normalized, this is T4's `P(⋃) ≤ h·(B/mass)`. What now remains of the fully composed concrete T4 is ONLY the instrument side of the hypotheses: measurability of the freeze-trajectory map in the action sequence (an `ite`-induction) and the slice computation `landing ∈ sliver ⟹ rotated-strip event` through `lemmaS_landing_eq` + `lemmaW` + `lemmaA_part_i_rotated` — every measure-theoretic step is done |
| **Theorem T4's modulus, composed** | `t4_slice_bound` (the per-slice bound in final form: any rotated sin-interval event of length ℓ has action mass ≤ 2√(ℓ/2), composed from `lemmaS_heading_uniform` + `lemmaA_part_i_rotated`), `t4_modulus` (`CapBound.lean`, ninth tranche) | **PROVED**: for events whose coordinate slices all have the rotated sin-interval form of length ≤ ℓ, the h-step union has action-process mass ≤ h·2√(ℓ/2)·2^{h−1} — normalized, `P(some landing in the sliver within h steps) ≤ h·√(ℓ/2)`, THEORY.md's Hölder-1/2 modulus with ℓ = w_ε/R_L. The single remaining per-instrument input is the `hform` hypothesis (each sliver-landing slice reduces to the sin form via `lemmaS_landing_eq` + `lemmaW_sliver_in_strip` — the coordinate-choice computation, instantiated per application) |
| Trajectory measurability (T4's hypothesis (a)) | `measurable_freezeTraj_param`, `measurable_landing_param`, `measurableSet_landing_event` (`ProcessWiring.lean`, ninth tranche) | **PROVED**: the freeze trajectory driven through an action-indexed tentative step is a measurable function of the action sequence (an induction over the freeze branches with `Measurable.ite`), and so are the landing map and every landing event — exactly the measurability `pi_union_slice_bound` consumes. T4's ONLY remaining gap is the per-slice computation: landing ∈ sliver ⟹ rotated-strip event, chaining `lemmaS_landing_eq` + `lemmaW_sliver_in_strip` + `lemmaA_part_i_rotated` — geometry already proved, one composition left |
| Rotation invariance: Lemma A for arbitrary strips | `volume_Icc_inter_eq_Ioc_inter`, `volume_sin_Ioc_translate` (whole-window 2πk-translation), `volume_sin_window_rep` (split-and-translate at a representative), `volume_sin_window_any` (ANY length-2π window carries the same sin-strip mass), `volume_sin_rotate` ("rotating coordinates shifts the uniform ψ" — the rotated strip event has the same measure for every φ₀), `lemmaA_part_i_rotated` (`CapBound.lean`, eighth tranche) | **PROVED**: the per-step strip bound `≤ 2π√(ℓ/2)` holds for strips in EVERY orientation — the step Lemma A's proof opens with. With this, the per-step conditional bound is fully orientation-free, exactly what the slice bound consumes |
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

## Status (2026-08-25, eighth tranche)

Two more floors (0 sorries, 8707 jobs): Lemma A's parts-(i)/(iv) analytic
cores (`CapBound.lean` — the half-angle identity, inverse Jordan, and both
the endpoint and tangency bounds), and Lemma B's gap-jump core
(`RipsCircle.lean` — the upcrossing lemma on the lifted walk; the
negative-winding case by negating the lift, which sidesteps the
wrap-reversal pathology). T1's birth lower bound and D⁻ are now both
machine-checked at the level the paper proves them.

## Not yet formalized — triage

Ordered by (value × feasibility), highest first:

1. **T4's `hform` instantiation** — the modulus itself is composed
   (`t4_modulus`); what remains is the per-instrument coordinate-choice
   computation feeding it: expressing each concrete sliver-landing slice in
   the rotated sin-interval form (inner-product expansion of the strip
   membership through `lemmaS_landing_eq` and `lemmaW_sliver_in_strip`,
   with interval clamping). Mechanical trigonometry; no measure or
   measurability step remains anywhere in T4.
2. **T5 measure assembly** — the sphere-measure reduction to the 1-D
   marginal density and T5-I's spherical-symmetry-of-sums step (Lemma G's
   analytic core is done); the Berry–Esseen transfer stays out of
   reasonable reach.
3. **T1's remaining floors** — on the `RipsCircle.lean` foundation: the
   Rips/persistence language (birth/death of the BAR, Lemma P's
   class-to-bar transfer), Lemma B's existence half (the
   consecutive-neighbors cycle), D⁺'s explicit filling 2-chain. T7's
   relative estimator sits above all of that.

## Building locally

`formal/Paper2Props/` is the package root; `lake build` builds both libraries.
In a network-restricted environment the mathlib binary cache host
(`lakecache.blob.core.windows.net`) may be blocked — `Paper3Ring` deliberately
imports narrow mathlib modules (not `import Mathlib`) so `lake build
Paper3Ring` from source stays feasible; `Paper2Props` imports all of Mathlib
and effectively needs the cache. CI has the cache and builds everything.
