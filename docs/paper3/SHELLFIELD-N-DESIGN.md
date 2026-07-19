# ShellField-n — design note (decision record, 2026-07-19)

Scope: the §8.1 first step. DECISIONS ONLY — no implementation yet; the
n-dim arm starts after the 2D mechanism/TDA/synthesis story is frozen.

## State and dynamics

State (x⃗, v⃗) ∈ ℝ²ⁿ; semi-implicit Euler with the same gain/drag/dt; freeze-
at-previous-position semantics unchanged. Mode = spherical shell
r_in ≤ ‖x⃗′ − c‖ ≤ r_out (later: tubular neighborhoods of S¹ ⊂ ℝ³ for
TubeField-3). All 2D theory that is metric transfers verbatim (Lemma 2,
Props 1, 3, 5–9 analogues — distance to c is 1-Lipschitz in every ℝⁿ).

## The action interface (the one real decision)

The 2D scalar-heading action (φ = π·a/a_max) does not generalize. Options:

(a) n−1 spherical angles as an action vector — awkward parameterization,
    coordinate singularities at the poles, biased sampling.
(b) Keep a scalar action indexing a fixed direction codebook — preserves
    the planner API but discretizes the action space and changes the
    problem class. Rejected.
(c) **CHOSEN: thrust-vector action** a⃗ ∈ [−1, 1]ⁿ, thrust =
    gain · a⃗ / max(1, ‖a⃗‖) (norm-capped, so the max thrust magnitude equals
    the 2D instruments'). Uniform per-component sampling for the random
    policy and for MPC/CEM candidates.

Planner impact: `mpc._candidates` / CEM sample scalars from
[−a_max, a_max]. Extension is ADDITIVE: a new `action_dim: int = 1` spec
threaded through candidate generation (tuple actions when > 1), with the
scalar path byte-identical when `action_dim == 1` (golden-protected — the
committed 1D/2D results must not move). The 2D instruments KEEP the scalar
heading interface; ShellField-n is a new class, no retrofit.

## Geometry normalization across n

Keep the *metric* situation constant so n is the only knob: start-to-shell
distance, r_in/r_out (thickness 1.5 > max step 1.0 — Lemma 2's margin),
lode geometry, h_episode all fixed at the 2D values, embedded in the first
two coordinates (c = (12, 0, 0, …)). Then r(n) and r_int(n) measure the
dimension effect purely (concentration: a drift-free random walk loses the
2-plane, so reach collapses with n).

## First measurements (in order, all CPU)

1. r(n), r_int(n) for n = 2..6 at the normalized geometry — the "n as the
   rarity knob" mini-law (§8.2): expect ~geometric collapse; report against
   (1−r)^N to show the danger regime becoming automatic.
2. Truth-MPC navigation check per n (does random-shooting MPC still reach
   the real lode at n = 4–6 with vector actions? if not, that is a planner
   scaling finding, recorded, and the play arm caps at the largest working n).
3. Contact-cloud TDA in n dims: β_{n−1} needs Rips in ℝⁿ up to dim n−1
   simplices — the pure-Python reducer stops being viable at n ≥ 3
   (β₂ needs tetrahedra). Decision: the n-dim TDA arm reports the NSW
   density threshold and the H₁ of 2-plane SLICES only, or brings in a
   dependency (gudhi/ripser) — defer, record as an open tooling decision.

## Non-goals (scope guard, same as §8.4)

No knotted tubes, no products, no moving boundaries in this paper; TubeField-3
enters only if the linking-number bound (§8.3-2) lands as a theorem first.
