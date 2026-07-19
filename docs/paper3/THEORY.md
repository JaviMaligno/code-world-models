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

## Proposition 4 (crossing lower bound on query-hit mass)

*Hypotheses.* f̂_blind the mode-blind model; the planner selects, at each real
step, the first action of a candidate action sequence maximizing imagined
return under f̂_blind over a candidate set 𝒞 (random-shooting MPC, CEM elites,
etc. — any deterministic argmax over 𝒞 given the seed). Assume:

  (RG) *reward gap:* every sequence in 𝒞 whose imagined path (under f̂_blind,
  from the current real state) enters B(c, r₀) has imagined return strictly
  greater than every sequence in 𝒞 whose imagined path stays outside
  B(c, r_out);
  (C) *candidate coverage:* 𝒞 contains at least one sequence whose imagined
  path enters B(c, r₀).

Then the selected sequence's imagined path crosses the annulus A (Lemma 2,
applied to the imagined path: blind imagination never freezes, steps ≤ Δ), so
the planner **queries f̂_blind on the disagreement region E = A × queried
actions during planning**: μ_query(E) = 1 conditional on (RG) ∧ (C). Paper 2's
Proposition 3 (play_cost ≤ μ_query(E)) is therefore tight-side-active on this
instrument: nothing in the upper bound is slack by failure to query.

*Proof.* By (C) an entering candidate exists; by (RG) no non-entering
candidate can be the argmax, so the selected imagined path enters B(c, r₀).
Since r₀ < r_in at the defaults (2.0 < 3.5), that path passes from
‖p − c‖ > r_out to ‖p − c‖ < r_in, and Lemma 2 places one of its steps in A.
That step is a model query on E. ∎

*(RG) is checkable, not behavioral.* At the frozen defaults it holds with
margin for every start state we use: a non-entering imagined path collects
phantom reward ≤ amp/(1+e^{(r_out−r₀)/width}) = 1/(1+e⁶) ≈ 0.0025 per step
plus at most the real lode's plateau (0.3/step reached after ≥ 6 units of
travel), while an entering path collects ≈ 1.0/step once inside — at horizon
40 the entering return dominates (≈35 vs ≈9 from the start region, larger
margin near the ring). A pre-registered check per instrument variant (as with
non-triviality in paper 1): verify (RG) numerically over the visited-state
envelope before running the arm. (C) holds for random shooting with
probability → 1 in the sample count and is logged (contact implies it fired).

*Measured.* blind_contact_rate = 1.0 at every gap in the calibration — the
real path realizes the crossing every episode, matching μ_query = 1.

*Topological upgrade slot (n-dim program §8.3-2).* For non-separating modes
(TubeField-3) the same proposition's conclusion must be re-derived with the
linking number of the imagined path and the mode's core replacing the
metric crossing — that is the genuinely homological version of this bound.

## The γ-curves: r(γ) and r_int(γ) (second pass, 2026-07-19)

r(γ) = P(a random rollout fires the mode), r_int(γ) = P(a random rollout
enters the interior). Fix the probability space: one i.i.d. action sequence
(a_t) and initial state drive the dynamics at EVERY γ (common random
numbers); write A(γ) for the mode region, so γ₁ < γ₂ ⇒ A(γ₂) ⊆ A(γ₁), and
D = A(γ₁) \ A(γ₂) (the two flanking slivers of the wider channel).

**Lemma 3 (divergence localization).** Under the coupling, the γ₁- and
γ₂-trajectories coincide up to (and excluding) the first step whose landing
falls in D. Hence any event determined by the trajectory has
|P_γ₁(·) − P_γ₂(·)| ≤ P(some landing in D).
*Proof.* Before that step every landing is either outside A(γ₁) (both free,
same next state) or in A(γ₂) (both freeze at the same previous position);
induction. The bound is the coupling inequality. ∎

**Proposition 5 (r is nonincreasing in γ — the coupling DOES work here).**
fire(γ₂) ⊆ fire(γ₁) pathwise, so r(γ₂) ≤ r(γ₁).
*Proof.* Take a realization where the γ₂-trajectory fires, first at step t.
Case 1: no D-landing before t. By Lemma 3 the trajectories agree through t,
and the step-t landing is in A(γ₂) ⊆ A(γ₁), so γ₁ fires at t. Case 2: some
D-landing at s < t (or s = t). A landing in D IS a landing in A(γ₁): γ₁
fires at s. ∎ (Measured, consistent: 0.0417 / 0.0283 / 0.0150.)

**Proposition 6 (continuity of r and r_int in γ).** Both curves are
continuous on [0, 2π].
*Proof sketch (to finalize).* By Lemma 3, |r_int(γ) − r_int(γ′)| ≤ P(some
landing in D(γ, γ′)). As γ′ → γ the slivers D(γ, γ′) shrink to the two
boundary rays; the events decrease to {some landing exactly on a boundary
ray}. For fixed state, the landing position is a non-constant real-analytic
curve of the action a, so the a-preimage of the (measure-zero) rays is
finite per step; integrating over the i.i.d. action law and summing over h
steps, the limit event is null. Monotone convergence gives continuity. The
quantitative version (P(landing in a width-ε sector) ≤ h·C·ε off tangencies,
Hölder-1/2 at tangencies of the landing curve to the rays) is the explicit-
constant TODO. Corollary: r_int(γ) → r_int(0) = 0 as γ → 0 — the
continuity-at-0 claim, now by a named argument. ∎(mod the TODO)

**Proposition 7 (direct entries are pathwise monotone).** Call an interior
entry *direct* (at gap γ) if the trajectory never lands in A(γ) before its
first entry, and *funnel-assisted* otherwise. Then for γ₁ < γ₂,
direct(γ₁) ⊆ direct(γ₂) pathwise, so the direct component d(γ) of r_int is
nondecreasing, with d(2π) = r_int(2π) (no wall ⇒ every entry direct).
*Proof.* A direct-at-γ₁ trajectory's landings before entry avoid A(γ₁) ⊇
A(γ₂); by the Lemma-3 induction it is unchanged under γ₂ and still avoids
A(γ₂): same entry, still direct. ∎
Consequently r_int(γ) ≥ d(γ) with d nondecreasing: ALL non-monotone risk
lives in the funnel component.

**Counterexample (pathwise inclusion for full entry is FALSE).** Probe
`scripts/ring2d_rint_probe.py` (4000 CRN rollouts, γ grid to 2π,
`results/continuous_ring2d_rint_probe.json`): seed **50543** enters the
interior at γ = 0.4 but NOT at γ = 0.6 — a funnel-assisted entry (freeze
near the mouth re-anchors, then the narrower-gap geometry funnels it in)
that widening the channel destroys. So the full-monotonicity statement can
have NO pathwise/coupling proof; only distributional arguments (stochastic
domination of post-divergence conditionals) remain admissible. This
certificate is the reason the conjecture below is stated distributionally.

**Measured verdict (same probe).** r_int is monotone nondecreasing across
the full grid — 0.0000 / 0.0008 / 0.0020 / 0.0040 / 0.0067 / 0.0080 /
0.0097 / 0.0105 / 0.0110, then EXACTLY constant at 0.0110 for γ ≥ 2.4 (the
entering seed set is literally identical from there: the wall no longer
intersects any entering trajectory — saturation at the free-walk limit,
reached while r(γ) > 0 still). Decomposition: direct entries 3 → 44
(monotone, Prop 7 — 0 violations observed, as proved), funnel entries ≤ 2
per gap at the defaults. Fire-violations 0 everywhere (Prop 5 sanity,
exact). Pathwise entry violations: 1 in 44,000 adjacent-pair comparisons
(the certificate above); gains 3–12 per pair.

**Refined conjectures (both distributional, both measured-consistent):**
  (M1) r_int is nondecreasing on [0, 2π];
  (M2) r_int(γ) ≤ r_int(2π): the wall never helps NET interior entry.
(Seed 50543 also fails to enter at γ = 2π — checked directly — so M2's
pathwise version is refuted by the same certificate as M1's.)

**Proposition 8 (positivity: r_int(γ) > 0 for every γ > 0, facing channel).**
For the defaults with `gap_center = π` and any γ > 0, r_int(γ) > 0.
*Proof.* (Witness tube.) Condition on |y₀| ≤ η(γ) := (3.5/8)·γ ∧ 0.4 — an
event of probability η/0.5 > 0 under y₀ ~ U(−0.5, 0.5). Take the constant
action sequence a_t ≡ 0. Then φ = 0, v_y stays 0, and the trajectory runs
east along the line y = y₀ with speed increasing toward gain/drag = 10;
within ≤ 40 < h steps its landings pass x = 7 … 8.5 and beyond
(machine-checked witness: `test_positivity_witness_tube`). Every landing at
radius d(x, y₀) ∈ [r_in, r_out] from the ring center has angular offset from
π at most |y₀|/r_in ≤ γ/8 < γ/2, i.e. lies in the channel; landings at
radius > r_out are outside the band. Hence the witness path is freeze-free,
its distance to A(γ) along the way is ≥ c(γ) := min(0.8·γ, 0.9) > 0 (chord
bound from angular clearance 3γ/8 at radius ≥ 3.5), and its first landing
past the band has depth d < 2.6 < r_in − c. On the freeze-free tube the
h-step flow map is Lipschitz in the action sequence with an explicit
constant L_h (per-step sensitivity |∂v′/∂a| ≤ gain·π·dt, compounded through
the linear drag recursion; finite by induction). Choose ρ = c(γ)/(2·L_h):
every action sequence with ‖a − 0‖_∞ ≤ ρ yields a trajectory staying within
c/2 of the witness, hence still freeze-free (never closer than c/2 to A) and
still landing at depth < 2.6 + c/2 < r_in: it enters. The probability of
that action tube is ρ^h > 0 (uniform density 1/2 per step, interval width
2ρ). Multiply by P(|y₀| ≤ η). ∎

**Corollary (the knob statement is now fully theorem-backed).** r_int(0) = 0
exactly (Lemma 2); r_int is continuous in γ (Prop 6); r_int(γ) > 0 for every
γ > 0 (Prop 8). The γ-knob re-opens identifiability continuously from an
exact zero — the paper's claim about the instrument needs nothing from M1/M2;
monotonicity is structure, not load-bearing.

**Remark (two grades of invisibility — gap_center selects them).** With the
HIDDEN channel (`gap_center = 0`) the mechanism grid measures r_int = 0 at
n = 400 and the filled model's disagreement rate = 0 — observationally
identical to the closed ring — yet a Prop-8-style steering construction
(around the ring, then in through the far channel; witness deferred) gives
r_int > 0 strictly. So the instrument realizes BOTH impossibility grades of
paper 1's split, selected by one knob: γ = 0 → *exact* unidentifiability (no
gate at any N; a theorem), hidden γ > 0 → r_int > 0 but of tube order ρ^h,
so (1 − r)^N ≈ 1 at every feasible N (practical unidentifiability, the
danger-law grade). The topological change (connectivity restored) is real in
both hidden and facing variants; only its position relative to the operative
reach differs — the thesis, again.

**Proposition 9 (reduction: M1 follows from one two-state estimate).** For
kernel K_k (gap γ_k, γ₁ < γ₂) let h_k(s, t) = P(the K_k-chain from state s
enters the interior within t steps). Suppose

  (KEY) for every state s and action a whose landing lies in
  D = A(γ₁) \ A(γ₂):  h₁(freeze(s), t) ≤ h₂(move(s, a), t) for all t < h,

where freeze(s) = (position of s, zero velocity) and move(s, a) = the
integrator successor. Then h₁(s, t) ≤ h₂(s, t) for ALL s, t — in particular
M1 for every initial distribution.
*Proof.* Induction on t. t = 0: both indicators of s ∈ I. Step: condition on
the first action a. If the landing is outside A(γ₁) or inside A(γ₂), both
kernels move to the same state s′ and the inductive hypothesis applies to
(s′, t−1). If the landing is in D, (KEY) applies verbatim. Integrate over a.
∎
*Why (KEY) is genuinely open, not merely unwritten.* (a) The natural split
h₁(freeze(s), t) ≤ h₂(freeze(s), t) ≤ h₂(move(s,a), t) re-introduces the
full conclusion in its first half (circular) and a same-kernel state-
monotonicity in its second — so (KEY) must be attacked directly as a
two-chain, two-state estimate. (b) Coupling the two continuations by common
actions fails quantitatively, not just formally: under identical actions the
velocity gap contracts by (1 − drag·dt) per step but the position offset
converges to Δp_∞ = Δp₀ + Δv₀·dt/(drag·dt) — at the defaults up to ≈
|Δv₀|·3.3 + |Δp₀| units, an order of magnitude larger than the channel and
band scales, so entry events of the coupled paths do not align. (c) What
would suffice: a hitting-probability monotonicity for the frozen chain along
a radial-position/inward-momentum order — an honest estimate about a
controlled nonlinear random walk with re-anchoring, with no symmetry to
lean on. Recorded as the sharp open problem; M1/M2 stay conjectures.

- The danger law applies verbatim at each γ with its own r(γ) — theorem
  (unchanged from paper 1/2; nothing ring-specific).

## Status ledger

| statement | status |
|---|---|
| Prop 1 (gate quotient) | proved (elementary); instantiated by reach-null test |
| Lemma 2 (crossing) | proved, constants checked at defaults |
| Prop 3 (unfalsifiable+harmless, bitwise) | proved; confirmed bitwise on 3 seeds |
| Prop 4 (query lower bound) | proved under (RG)+(C); (RG) checkable per instrument, check to pre-register |
| Lemma 3 (divergence localization) | proved |
| Prop 5 (r nonincreasing in γ) | proved (pathwise); 0 violations in 44k CRN checks |
| Prop 6 (continuity of r, r_int in γ) | proved mod explicit density constant |
| Prop 7 (direct entries monotone) | proved (pathwise); measured 0 violations |
| Prop 8 (positivity r_int(γ) > 0, facing) | proved (witness tube); machine-checked incl. perturbations |
| Prop 9 (KEY ⇒ M1, simultaneous induction) | proved; (KEY) is the isolated open estimate |
| r_int(0) = 0 | theorem (Lemma 2); measured 0.0000 at n=4000 |
| M1, M2 | CONJECTURES — pathwise routes REFUTED (seed 50543, incl. at 2π); reduction to (KEY) rigorous; coupling obstruction quantified (offset ≈ 3.3·|Δv₀| ≫ channel scale) |
| hidden-channel positivity | expected (steering witness deferred); grounds the two-grades remark |
| n-dim / non-round / non-separating versions | RESEARCH-DIRECTION §8 program |
