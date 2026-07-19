# Paper 3 — formal statements (working draft, 2026-07-19)

Companion to `RESEARCH-DIRECTION.md`. These are the "is there a theorem here"
de-risk items (§7.4 there). Discipline as in papers 1–2: provable vs measured
kept explicit; every hypothesis checked at its use-site. Instrument:
`RingField2D` (`src/cwm/continuous/envs.py`), tests in `tests/test_ring2d.py`.

## Setup

Deterministic dynamics f : S×A → S on S ⊆ ℝᵈ, initial distribution μ₀, episode
horizon h. A *gate policy* ρ selects actions (uniform-random in our gates,
but nothing below needs that). The **reachable query set** is

  𝓡(f, μ₀, ρ, h) = { (s, a) : some length-≤h trajectory under (f, μ₀, ρ)
                      queries f at (s, a) with positive probability },

and in continuous spaces we take the support of the induced occupation
measure (the closure convention changes nothing below: two models that agree
on a set agree on any set it is dense in only if both are continuous there —
we only ever use agreement ON 𝓡 itself, defined as the support).

A **sampling gate** of any size N draws trajectories under (f, μ₀, ρ) and
accepts a candidate f̂ iff f̂ reproduces every queried transition (within any
tolerance, including exactly).

## Proposition 1 (gate quotient — certifiable content is f restricted to 𝓡)

Let f̂ be any model with f̂|𝓡 = f|𝓡. Then for every N, the gate accepts f̂
with probability 1, and the trajectory law of ANY policy π whose queries stay
in 𝓡 is identical under f and f̂. Consequently the set of models accepted
with certainty is exactly the extension class E(f) = { f̂ : f̂|𝓡 = f|𝓡 }, and
no gate statistic distinguishes two members of E(f). The complement
𝓖 = (S×A) \ 𝓡 is **gauge freedom**: model content on 𝓖 is chosen by the
synthesizer's prior and is unfalsifiable by any sample drawn from ρ.

*Proof.* By induction on the step index, a trajectory under (f, μ₀, π) with
queries in 𝓡 is a trajectory under (f̂, μ₀, π) with the same realizations:
the state after step t is a function of μ₀, the action sequence, and the
queried values of f, which agree with f̂'s on 𝓡. Gate draws use π = ρ, whose
queries lie in 𝓡 by definition (up to a null set), so acceptance statistics
coincide; f itself is in E(f) and is accepted a.s., hence so is every member. ∎

*Relation to paper 2's Proposition 2 (identifiability).* That proposition
conditions on the finite-sample event "the mode region was missed"
(probability (1−r)^N → 0 as N grows when r > 0). Proposition 1 is its
structural, N-independent limit: on 𝓖 the miss probability is 1 for EVERY N.
The prior caveat of paper 2 ("a prior or the specification could still supply
the mode") is exactly the statement that E(f) is not a singleton.

*Use-site (RingField2D, gap = 0, start outside).* Lemma 2 below shows the
open inner disc × all actions ⊆ 𝓖. So the entire interior behavior of an
accepted artifact — including whether it freezes there (filled disc) or not
(true annulus) — is gauge. Measured: `test_interior_is_reach_null_at_gap_zero`
(200 rollouts, 0 interior states visited, ring itself reached).

## Lemma 2 (metric crossing / no jump-over)

Let positions move in discrete steps p₀, p₁, … ∈ ℝ² with ‖p_{t+1} − p_t‖ ≤ Δ,
and let A = { p : r_in ≤ ‖p − c‖ ≤ r_out } with thickness w = r_out − r_in > Δ.
If ‖p₀ − c‖ > r_out and ‖p_T − c‖ < r_in for some T, then some intermediate
p_t ∈ A. Moreover under RingField2D's freeze semantics (a step landing in A
returns the previous position), no trajectory started outside ever produces a
position with ‖p − c‖ < r_in: the interior is unreachable, not merely rare.

*Proof.* g(t) = ‖p_t − c‖ changes by at most Δ per step (‖·−c‖ is
1-Lipschitz). Let t* be the first index with g(t*) < r_out. If g(t*) < r_in
then g(t*−1) ≥ r_out forces a step > w > Δ, contradiction; so
g(t*) ∈ [r_in, r_out), i.e. p_{t*} ∈ A. For the freeze dynamics: the first
landing in A is replaced by the previous (outside) position with zero
velocity, so g never drops below r_in; induct. ∎

*Constants at the frozen defaults.* Speed obeys ‖v_{t+1}‖ ≤ (1 − drag·dt)‖v_t‖
+ gain·dt, so from rest ‖v‖ ≤ gain/drag = 10 and Δ = ‖v‖·dt ≤ 1.0 < w = 1.5.
Hypothesis holds with margin for real AND imagined rollouts (planners use the
same integrator and action clamp).

*Honesty note — this is metric, not topological.* The lemma uses only that
distance-to-center is 1-Lipschitz; it works verbatim in ℝⁿ for round shells
(S^{n−1} of any dimension) and needs NO homology. Genuine algebraic topology
is *earned* only where this proof dies — non-round separators
(Jordan–Brouwer / Alexander duality to even define "inside"), and
non-separating modes (winding/linking obstructions). See
RESEARCH-DIRECTION §8: this is the boundary of "topología algebraica de
verdad", and rung 2 (the round ring) deliberately sits on the metric side of
it — the topology enters through *what the gauge region and its boundary
class organize*, not through the crossing proof.

## Proposition 3 (wrong topology: unfalsifiable AND harmless at gap = 0)

Let f be the true ring dynamics (gap = 0), f̂_fill the filled-disc model
(freeze on the whole disc ‖p − c‖ ≤ r_out), and let the planner be any
deterministic function of model responses and a seed whose imagined rollouts
start at real (outside) states and use the contract integrator (step bound Δ
< w, Lemma 2). Then:

(i) *(unfalsifiable)* f̂_fill ∈ E(f): it disagrees with f only on next-states
in the open interior, which by Lemma 2 lie outside 𝓡 — every sampling gate
accepts it with probability 1.

(ii) *(harmless)* The planner's real trajectories under model f̂_fill and
under the true model f are identical realization-by-realization; play_cost
of the wrong-topology model is exactly 0.

*Proof.* (i) is Proposition 1 + Lemma 2. (ii) Imagined rollouts from an
outside state under either model freeze at the same first-annulus-landing
(the two models agree on A and outside; by Lemma 2 imagination never
produces an interior query where they differ), so every candidate action
sequence receives the same imagined return under both models; a deterministic
planner therefore selects the same action at every real step, and the real
environment does the rest. ∎

*Measured (bitwise, as designed):* `test_wrong_topology_is_planner_equivalent
_at_gap_zero` — identical episodes (return, final state, contact) on paired
seeds, MPC on f vs f̂_fill. The γ-knob then makes the same wrong artifact
consequential: with gap > 0 a channel trajectory enters the interior, where
f̂_fill freezes and f does not — E(f) shrinks and f̂_fill exits it.

*Why this matters for the paper.* This is the cleanest statement of the
"certifiability ≠ correctness, and BOTH ≠ consequence" triad: at γ = 0 the
artifact is wrong, certified, and costless; γ > 0 continuously converts the
same wrongness into (1−r(γ))^N-gated danger. One knob walks the artifact
through all three regimes — the three-way split of the mechanism arm.

## Proposition 4 (crossing lower bound on query-hit mass — sketch, to tighten)

For the mode-blind model f̂_blind and any planner whose real trajectory
enters the closed disc ‖p − c‖ ≤ r_in at some step (e.g. because the phantom
lode at c lures it), Lemma 2 applied to the REAL path under blind planning
(the blind model never freezes, so the real path is the integrator path until
truth's first freeze) gives: the trajectory has a step landing in A, i.e. the
episode queries/realizes the disagreement region with probability ≥ P(planner
commits to the interior). At the defaults the blind MPC commits on every
episode (measured: blind_contact_rate 1.0), so μ_query(E) = 1 and paper 2's
Proposition 3 bound is tight here — play_cost ≈ its upper bound. TO TIGHTEN:
state "commits to the interior" as a reward-gap condition on the planner
(the phantom's imagined return dominates every non-crossing alternative) so
the bound has no behavioral hypothesis; this is where a genuinely topological
version will replace the metric one for non-round/non-separating geometry
(linking number of the realized path with the mode's core submanifold).

## Remark (r(γ): the identifiability knob is continuous)

r(γ) = P(a random rollout fires the mode) and r_int(γ) = P(a random rollout
enters the interior) satisfy: r_int(0) = 0 exactly (Lemma 2), r_int is
nondecreasing in γ (mode region shrinks with γ, so freezes can only be
delayed; a coupling argument per realization), and the danger law applies
verbatim at each γ with its own r(γ). The calibration script
(`scripts/continuous_ring2d.py`) measures both curves; the γ = 0 column is a
theorem, the rest is measurement.

## Status ledger

| statement | status |
|---|---|
| Prop 1 (gate quotient) | proved (elementary); instantiated by reach-null test |
| Lemma 2 (crossing) | proved, constants checked at defaults |
| Prop 3 (unfalsifiable+harmless, bitwise) | proved; confirmed bitwise on 3 seeds |
| Prop 4 (query lower bound) | sketch — behavioral hypothesis to be replaced |
| r(γ) continuity/monotonicity | coupling argument to write out; measured |
| n-dim / non-round / non-separating versions | RESEARCH-DIRECTION §8 program |
