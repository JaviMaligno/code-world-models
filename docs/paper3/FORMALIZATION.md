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

## Not yet formalized — triage

Ordered by (value × feasibility), highest first:

1. **Prop 10/11 (fence/patch sufficiency)** — metric covering arguments.
2. **Prop 8 (positivity via witness tube)** — constructive; the honest form
   exhibits one explicit action stream entering at γ > 0, which needs interval
   arithmetic over cos/sin (fiddly, not deep).
3. **Prop 5/6, T4 (coupling monotonicity of r; Hölder modulus)** —
   probabilistic: needs the uniform action measure and the anticoncentration
   Lemma A; mathlib has the ingredients (circle measure, Lipschitz), real
   work to assemble.
4. **T5 (cone bounds, spherical caps, Cor T5-U)** — probability with explicit
   constants (Lemma G is a clean self-contained target; the Berry–Esseen
   transfer is out of reasonable reach).
5. **T1 (Rips birth/death lemmas), T7 (relative estimator)** — mathlib has no
   Vietoris–Rips persistence; formalizing these means building that theory
   first. Out of scope until that changes; recorded here so the gap is a
   stated fact rather than an omission.

## Building locally

`formal/Paper2Props/` is the package root; `lake build` builds both libraries.
In a network-restricted environment the mathlib binary cache host
(`lakecache.blob.core.windows.net`) may be blocked — `Paper3Ring` deliberately
imports narrow mathlib modules (not `import Mathlib`) so `lake build
Paper3Ring` from source stays feasible; `Paper2Props` imports all of Mathlib
and effectively needs the cache. CI has the cache and builds everything.
