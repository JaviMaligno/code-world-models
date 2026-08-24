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
| Prop 3(i) (unfalsifiable) | composition of `prop1_gate_quotient` + `lemma2_interior_unreachable` | components proved; the composed statement is next-tranche mechanical work |
| Local crossing lemma (thin neck, 2026-08-24) | `freeze_stays_outside_of_superset`, `neck_interior_unreachable` | **PROVED** the same session the design landed (the standing rule's first exercise): a mode set CONTAINING the thin annulus `[r_in, r_in+w]` with `w > Δ` seals the hole, whatever its shape — interior entry requires a single step longer than the neck. The deterministic leap witness at neck = 0.5 (`tests/test_ring2d_thin_neck.py`) is the measured complement |
| Prop 3(ii) (harmless / planner equivalence) | `disc_annulus_same_return` | **engine PROVED** (any return functional coincides); the planner/environment loop wrapper is next-tranche mechanical work |

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

## Not yet formalized — triage

Ordered by (value × feasibility), highest first:

1. **Prop 3 composed statement + planner loop** — mechanical from the proved
   pieces; do in the next tranche.
2. **T2's Lemma T2-I (hybrid telescoping) and the T3-P / T3-P″ defect
   theorems** — exact pathwise identities and one-sided inequalities over
   trajectories; the same realization-level style as Prop 1. No measure
   theory needed for the identities themselves.
3. **Prop 7 (direct entries pathwise monotone)** — pathwise, needs the
   coupled-trajectory setup (two gap values, shared stream).
4. **Prop 10/11 (fence/patch sufficiency)** — metric covering arguments.
5. **Prop 8 (positivity via witness tube)** — constructive; the honest form
   exhibits one explicit action stream entering at γ > 0, which needs interval
   arithmetic over cos/sin (fiddly, not deep).
6. **Prop 5/6, T4 (coupling monotonicity of r; Hölder modulus)** —
   probabilistic: needs the uniform action measure and the anticoncentration
   Lemma A; mathlib has the ingredients (circle measure, Lipschitz), real
   work to assemble.
7. **T5 (cone bounds, spherical caps, Cor T5-U)** — probability with explicit
   constants (Lemma G is a clean self-contained target; the Berry–Esseen
   transfer is out of reasonable reach).
8. **T1 (Rips birth/death lemmas), T7 (relative estimator)** — mathlib has no
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
