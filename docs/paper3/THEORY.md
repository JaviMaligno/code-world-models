# Paper 3 — formal statements

Companion to `RESEARCH-DIRECTION.md`.

**Scope of this file.** Mathematical content only: statements, proofs,
refutations, and measured facts with their evidence labels (per
`.claude/skills/paper-claims`: proved / measured / consistent-with, each with
its unit and n). A closed route is mathematical content and stays — *which*
route is closed and *by what* is a fact. The narrative of how the campaign
reached each state — dates, which reading came first, what was believed and
then corrected — belongs in `CAMPAIGN-LOG.md`, not here. Paper prose lives in
`main.tex` and is governed by the same claim contract.
 These are the "is there a theorem here"
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

*Corollary (evidence equivalence of disc and annulus from outside).* From
outside starts, no landing ever falls at d < r_in (the lemma), so the disc
mode ‖p−c‖ ≤ r_out and the annulus mode r_in ≤ ‖p−c‖ ≤ r_out fire on exactly
the same steps of every realization: the contact processes — and hence ALL
evidence any gate, repair loop, or TDA pass extracts — are pathwise
identical. Measured as an exact row-for-row equality of the two contact
clouds in the TDA probe (`results/continuous_ring2d_tda_probe.json`,
ring_out vs disc_out at every N). Paper 2's dimensional reduction is
*rational given the evidence*: outside data cannot even pose the disc-vs-
annulus question.

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
metric crossing. **RESOLVED (T8, 2026-07-25): the upgrade is a DICHOTOMY,
not a bound** — the unconditional query bound is refuted by landing-free
witnesses in every linking class, and what survives is "link ⇒ query ∨
thread-the-clearance-disc" plus the corridor corollary. See the T8 section
below.

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
steps, the limit event is null. Monotone convergence gives continuity.
**RESOLVED quantitatively (T4, 2026-07-25):** the one-step landing law is
EXACTLY uniform on a circle of radius gain·dt² (Lemma S below), giving the
explicit uniform modulus |q(γ) − q(γ′)| ≤ h·√(r_out·|γ−γ′|/(gain·dt²))
(Theorem T4: Hölder-1/2, ≈ 1033·√ε at the defaults; linear in ε off
tangencies with explicit C(m), Theorem T4′, and per-step √ε is attained at
tangency, so Hölder-1/2 is sharp per-state). Corollary: r_int(γ) ≤ 1033·√γ
→ r_int(0) = 0 as γ → 0 — the continuity-at-0 claim, now quantitative. ∎

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
**(KEY) is FALSE — refuted by stress test (2026-07-19, second pass).**
`scripts/ring2d_key_probe.py`, Part 1
(`results/continuous_ring2d_key_probe.json`): at (γ₁, γ₂) = (0.4, 0.6), a
scan of 91 legal divergence configurations of the form "s parked in the
γ₁-corridor near the interior boundary, velocity outward + tangential so the
landing falls in the sliver D" produces **91/91 CI-separated violations** —
h₁(freeze(s), 40) ∈ [0.52, 0.69] against h₂(move(s,a), 40) ∈ [0.00, 0.33]
(n = 2000 per side). Mechanism, now named: **freeze-rescue**. The freeze
re-anchors the narrow-gap chain AT REST at s's position; when s sits in the
corridor 0.05–0.2 from the interior, that parking is privileged, while the
wide-gap chain keeps its outward velocity and is carried away (drag brings
it to rest ~3 units out, a generic exterior position). These configurations
are reachable with positive probability (corridor states are reachable by
Prop-8-style threading; velocities ≤ gain/drag by accumulation), so the
refutation stands for (KEY) both as stated and restricted to the reachable
set. Prop 9 remains a valid reduction — with a false hypothesis: any proof
of M1 must therefore engage the divergence distribution's weighting, not
local comparisons alone.

**Lemma 4 (first-divergence identity).** Under the CRN coupling with
γ₁ < γ₂, let τ = the first step whose landing lies in D, S the state then,
A the action, T = h − τ the remaining budget, and E_pre = {interior entered
before τ}. Then
  r_int(γ₂) − r_int(γ₁)
    = E[ 1{τ ≤ h, ¬E_pre} · ( h₂(move(S, A), T) − h₁(freeze(S), T) ) ].
*Proof.* On {τ > h} the trajectories coincide (Lemma 3): contribution 0. On
{τ ≤ h, E_pre} both entered before τ: contribution 0. On the remaining
event, condition on the history up to τ: each chain individually is Markov,
so its conditional entry probability is h_k of its own state with budget T —
the conditional expectation of the difference of indicators is h₂ − h₁
regardless of the post-τ dependence between the chains. Tower property. ∎

**Numerical self-validation + where M1 lives** (same probe, Part 2). Over
6000 CRN rollouts at (0.4, 0.6): 79 first divergences (no prior entry);
Monte-Carlo of the integrand at each (400/side): negative at only **3/79**
configs, mean +0.162; identity check: measured r_int difference 0.00250 vs
reconstructed E[1_div · Δ] = 0.00213 (agreement within MC noise). So M1 is
true at these parameters *because* the first-divergence distribution puts
~96% of its mass on inward-crossing configurations (where the wide gap wins
by +0.16 on average) and ~4% on freeze-rescue configurations — a fact about
the chain's occupation measure, not about any pointwise comparison.

**Final status of M1/M2 after the second pass.** All local routes are now
CLOSED WITH EVIDENCE: pathwise coupling — refuted (seed 50543, incl. at 2π);
pointwise config comparison (KEY) — refuted (91/91). Two further classical
routes noted and dead: a measure-preserving injection between entering
action-sets is equivalent to the inequality itself (no shortcut), and
"freeze as pure time-delay" is false (freeze re-anchors, it does not delay).
What a genuine proof now requires: an estimate on the first-divergence
occupation measure — e.g. that the freeze-rescue region (corridor × outward
velocities) carries divergence-mass sufficiently below the inward-crossing
mass, uniformly in γ. That is a quantitative statement about a controlled
nonlinear random walk with re-anchoring; we assess it as out of proportion
for this paper and leave M1/M2 as measured regularities with the identity
(Lemma 4) as their exact frame — the same discipline as paper 2's play_cost.

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
| Prop 6 (continuity of r, r_int in γ) | PROVED with explicit modulus (Theorem T4, 2026-07-25): Hölder-1/2 constant h·√(r_out/(gain·dt²)) ≈ 1033; linear off tangencies; per-step sharpness at tangency |
| Prop 7 (direct entries monotone) | proved (pathwise); measured 0 violations |
| Prop 8 (positivity r_int(γ) > 0, facing) | proved (witness tube); machine-checked incl. perturbations |
| Prop 9 (KEY ⇒ M1, simultaneous induction) | proved — but (KEY) is FALSE (91/91 CI-separated violations; freeze-rescue) |
| Lemma 4 (first-divergence identity) | proved; numerically self-validated (0.00250 vs 0.00213) |
| r_int(0) = 0 | theorem (Lemma 2); measured 0.0000 at n=4000 |
| M1, M2 | THEOREMS up to an explicit defect (Thm T3-P″, 2026-07-26): r_int(γ₂) ≥ r_int(γ₁) − [f(γ₁)−f(γ₂)]⁺ via Prop 7 — EXACTLY ZERO wherever f is nondecreasing (6/11 adjacent pairs); certified slack 6.7e-4 vs effect 1.12e-2 (16.9×), exact where f = 0 (γ ≥ 3.2). Earlier routes to the UNCONDITIONAL statement remain closed with evidence (pathwise: seed 50543 — now explained as necessarily a funnel entry; pointwise: (KEY) refuted). Open: an a-priori bound on f |
| hidden-channel positivity | expected (steering witness deferred); grounds the two-grades remark |
| n-dim / non-round / non-separating versions | RESEARCH-DIRECTION §8 program |

**Synthesis-side confirmations (registered open-ring arm, 2026-07-22; EXPERIMENTS.md).**
The arm supplies empirical counterparts to the theory here:
- *Danger relative to reach (the thesis).* The facing-vs-hidden contrast at the
  SAME β₁=0 is the operational form of "position of 𝓡 relative to the operative
  reach, not its topology" (the remark near line 296): facing pc_blind collapses
  over a gap≈0.1 knee (CPU curve 0.999→0.001 by gap 0.15) while hidden holds
  pc 1.116 at gap 0.6 and 1.2. The aligned-channel degeneracy (mechanism grid)
  now has an LLM-synthesis analogue.
- *Prop 1 (gate quotient) empirically load-bearing.* Inside gate-pass ≈ 0 at
  every gap (even Claude's passes are wall_blind=1.0, pc 0.0): certification
  succeeds only where the reachable-equivalent structure meets round,
  guessable parameters — the gauge freedom of Prop 1 is exactly the slack the
  synthesizer cannot pin, so certified ≠ correct except in that corner.
- *Sensor resolution as a new object.* The pre-registered β̂₁ summary (Rips,
  3×median-NN) reports β̂₁=1 for every gap ≤ 1.2 (flip ~1.8) though the true
  β₁=0 for all gap>0; posed artifact topology tracks β̂₁, so the sensor's
  resolution limit — a computable NSW-style density bound (RESEARCH-DIRECTION
  A.1) — is what the certified model's topology inherits. Candidate formal
  statement: repairable topology is bounded by the persistent-homology
  resolution of the contact evidence at the sampling density.

## The measured→provable audit (2026-07-24, with the v2 program)

Sweep of every measured-only claim in papers 2–3 / EXPERIMENTS.md for
statements that are provable with the existing toolkit. Verdicts:

| measured claim | provable? | action |
|---|---|---|
| persistent nerve fence ⇒ truth-equal play (pc 0.999→0.058) | **YES** — Prop 10 below (coverage + margin hypotheses, both checkable) | PROVED |
| freedom patch ⇒ truth-equal play on invented modes (1.769→0.029) | **YES** — Prop 11 below (certificate-coverage hypothesis) | PROVED |
| lie-rate symmetry (80 vs 2 lessons/ep) | trivially — Remark R1 | stated |
| hidden ≡ closed observational identity | YES (Lemma 3 coupling) — Remark R2 | stated |
| Rips flip location (chord vs fill scale) | YES in idealized form via the known VR-complex-of-S¹/arc characterization (Adamaszek–Adams 2017) — gives a γ* formula; our measured flip sits between the naive chord bound and the exact characterization | sketched; formalize at v2 write-up |
| aligned-channel degeneracy (facing pc→0) | bound-grade (corridor-fits-channel ⇒ blind argmax executable ⇒ pc ≤ tail terms) | sketch only |
| r(n) collapse order | concentration-of-measure order bound; constant not worth it | note |
| M1/M2 | still occupation-measure grade | unchanged (out of proportion) |
| dose-independence of parameter guessing | NOT provable (a claim about LLM behavior) | stays measured |

**Proposition 10 (fence sufficiency — the constructive result is
theorem-backed).** Let the planner be deterministic argmax over candidates
𝒞 with imagined steps of length ≤ Δ, truth f the closed ring, model f̂ the
blind model, F the fence set (union of segments), and suppose:

  (COV) every segment of length ≤ Δ that crosses the reachable outer
  boundary arc of A passes within ε of F;
  (RG-west) the best non-crossing candidate's imagined return under the
  pure integrator exceeds every crossing candidate's PRE-crossing return
  plus its flee tie-break advantage (at the defaults: west-lode return ≈ 2
  vs phantom-tail prefix ≤ 0.1 — holds with margin, checkable over the
  visited envelope).

Then for every real state outside the band: (i) every crossing candidate is
truncated at or before its crossing step (by (COV)); (ii) every
non-crossing candidate receives the SAME imagined return under f̂+fences,
under f̂ alone, and under the truth f (all three agree along non-crossing
paths: f̂ = integrator = f off the band, and truth-imagination freezes only
on crossings); (iii) by (RG-west) the argmax is a non-crossing candidate
and is the same candidate under f-imagination and under f̂+fence
imagination. Hence the mitigated planner and the truth planner choose the
same action at every real step: real trajectories are identical,
play_cost = 0 exactly. ∎
*Measured instance:* episodes 2–16 of the persistent-nerve run satisfy
(COV) after episode 1's two lessons (the extended edges span the crossing
corridor) and return-match the truth planner episode-for-episode; pc 0.058
> 0 comes entirely from episode 1 — the learning transient the theorem
does not (and should not) cover.

**Proposition 11 (patch sufficiency — the dual).** Let f̂ be an
invented-mode model (f̂ = f except it freezes on a region B where f moves
freely), K the freedom-certificate set, and suppose (CERT): every point of
B visited by any candidate's imagined path from the current real state lies
within ε of K, and f̂'s freeze prediction at any state within ε of K is
freeze-form. Then the patched model's imagination equals truth imagination
for every candidate (off B they agree; on B∩(ε-neighborhood of K) the patch
substitutes the pinned integrator = f), so the argmax coincides with the
truth planner's and play_cost = 0 exactly. ∎
*Measured instance:* from inside, every step yields a certificate (the model
lies each step — R1), so (CERT) is satisfied within one episode's prefix;
measured near-truth returns from episode 1, pc 0.029 = the prefix cost.

**Remark R1 (lie rates).** The certificate rate is the occupation of the
disagreement region under the operative policy: for the filled model from
inside it is ≈1 per step (the disagreement region contains the start's
whole neighborhood); for the blind model from outside it is r per rollout
(the disagreement region is the band, reached rarely). The measured 80 vs 2
lessons/episode is this occupation gap, not an algorithmic property.

**Remark R2 (hidden ≡ closed, quantified).** By the Lemma-3 coupling with
D = the hidden channel's slivers, any trajectory event's probability
differs between hidden-γ and closed ring by at most P(some landing in D) =
r_int-type mass, which Prop 8's tube argument bounds below by ρ^h > 0 and
measurement bounds above by 0 at n = 400: the observational identity is an
inequality with an exactly-zero left witness, not an exact theorem — the
two grades of impossibility again, now as a statement about the
equivalence itself.

## RESULTS TO PROVE — the v2 target list (2026-07-24, Javier's directive)

Standing decision: everything below is a TARGET to be attacked, in Javier's
order and on his timing (not this session). "Sketch" status is a starting
point, never a resting place; difficulty notes are honest assessments, not
scope exclusions. Superseding the audit table's dispositions above where
they conflict.

- **T1 — Rips flip location.** **CLOSED (2026-07-25) as a two-sided
  sandwich law with explicit constants.** Birth exact (Lemma B, winding
  argument); death sandwiched √3·r_min ≤ death ≤ 2·r_max·sin(θ*/2)
  (Lemma D⁻ + the FILLING LEMMA D⁺, proved 2026-07-25 by an explicit
  spanning-triangle + fan-retraction 2-chain — the key reduction: the
  bar dies when ITS OWN class [z₀] bounds, so no general
  "winding-0 ⇒ boundary" lemma is needed and the Adamaszek–Adams
  machinery is not required). Two-sided corollary: guaranteed β̂₁ ≥ 1
  when √3·r_min − 2·r_max·sin(Δθ_max/2) > τ; guaranteed no persistent
  winding bar when 2·r_max·sin(θ*/2) − 2·r_min·sin(Δθ_max/2) < τ.
  Validation: 78/80 pointwise law (`t1_flip_law_validation.py`, the 2
  misses inside the proved undecided band), sandwich 57/57 winding bars
  + 34 guaranteed-1 and 5 guaranteed-0 rows with 0 violations
  (`scripts/t1_death_sandwich.py`). The class-to-BAR transfer is Lemma P
  (2026-07-25 second pass, prompted by Javier's pairing question): under
  the checkable rank condition r₀ = 1 (exactly one bar spans
  [B⁺, √3·r_min)) the sandwich holds for the bar itself; r₀ = 1 measured
  in 36/36 nonempty-window rows, and r₀ ≥ 2 is the SAME configuration as
  the spurious-class exclusion — one hypothesis, per-sample decidable.
- **T2 — Aligned-channel degeneracy.** **DECOMPOSITION HALF CLOSED
  (2026-07-25):** the clean-step lemma's exact route was closed by the
  hypothesis-emptiness certificate (0/48 clean episodes), and the
  replacement is now an EXACT IDENTITY, not a bound — hybrid
  telescoping gives J_T − J_B = Σ_{dirty steps} A_t with clean steps
  contributing exactly 0 (Lemma T2-I; residual ≤ 4.6·10⁻¹⁴ in 18/18
  episodes, `scripts/t2_percontact_identity.py`). Measured structure:
  the γ-trend lives in the dirty-step RATE (21.2 → 10.5 per episode as
  γ goes 0.3 → 1.2) while the per-contact cost Ā is flat (≈0.12–0.17);
  40% of A_t are NEGATIVE at every γ (blind's action often better under
  the truth continuation — play_cost is a small difference of large
  cancelling terms); and the tail is heavy (max A_t = 11.65 vs mean
  0.13 at γ = 0.3). The freeze-transient explanation of that tail is
  **REFUTED** (0/556 freezes in both continuations: after the dirty step
  both follow π_T, which knows the mode). The tail instead scales with
  remaining horizon (corr +0.325) and concentrates at narrow gaps
  (18/6/3 of the top decile at γ = 0.3/0.6/1.2), pointing at
  route commitment — WHICH WAS THEN REFUTED (2026-07-26): tail events
  split the two routes LESS often than the bulk (0.190 vs 0.299) and
  same-side pairs carry the larger |A|; cut-locus target withdrawn.
  **MECHANISM FOUND (2026-07-26): DELAY COST**, measured not asserted —
  A_t regressed on the basin-dwell difference gives slope 0.9404 against
  the known amp_phantom = 1.0, intercept ≈ 0, R² = 0.9275, and 100% of
  tail events have a nonzero dwell difference (bulk 41%).
  **NEGATIVE RESULT PROVED (Prop T2-D):** every imagination-level
  quantity is a function of (s_t, models, C_t) while A_t also depends on
  C_{t+1..h}, so NO bound from the model's own disagreement can be tight
  — measured with the imagination data pinned, A_t still spans
  [−1.707, +0.602]. Paper 2's play_cost ≤ μ_query is valid here, equals 1,
  and its vacuity is not sharpenable. The replacement (bound the
  planner-averaged value) has a proved reduction (Lemma S caps, measured
  tight) and a proved divergence cap (drag lemma, tight to 3%), but is
  NON-VACUOUS ONLY WITH A MEASURED CONSTANT: pc ≤ 48 with A proved,
  ≤ 1.21 under the competence hypothesis (both vacuous since pc ≤ 1 is
  trivial), ≤ 0.18 with L_v measured. REMAINING: the distribution of the
  angle between the two argmax actions — a planner property, exactly what
  T2-D says a tight bound must characterise.
- **T3 — M1/M2 distributional monotonicity of r_int(γ).** **PARTIALLY
  RESOLVED (2026-07-25): M1 and M2 are now THEOREMS with an explicit,
  measured defect.** Theorem T3-P: r_int(γ₂) ≥ r_int(γ₁) − f(γ₁) for
  γ₁ < γ₂, where f = the funnel component — immediate from Prop 7's
  pathwise inclusion of DIRECT entries, needing no occupation measures.
  Certified slack 6.7·10⁻⁴ vs effect 0.0112 (**16.9×**), Prop 7
  re-verified at 550 000 pathwise comparisons with 0 violations, and
  f = 0 measured throughout γ ≥ 3.2 where T3-P(c) then gives EXACT
  monotonicity. The seed-50543 counterexample is now explained, not just
  recorded: Prop 7 forbids a direct violation, so it must be a funnel
  entry — it lives precisely in the term T3-P isolates. Strongest defect
  bound from Prop 7 is T3-P″ ([f(γ₁)−f(γ₂)]⁺, exactly zero on 6/11
  adjacent pairs). ALL ROUTES TO PROVING M1/M2 ARE CLOSED WITH EVIDENCE:
  pathwise (seed 50543), pointwise (KEY refuted 91/91), the
  velocity-preserving variant (refuted 13/30 764 entering pairs — the
  position block alone breaks pathwise inclusion), and three
  restatements that are logically equivalent to M1/M2 rather than
  reductions (c = r·κ; d-rise ≥ f-drop; f ≤ d(2π) − d(γ)). REMAINING
  an a-priori bound on f(γ) — equivalently f ≤ c·r_int with a
  uniform c < 1. c < 1 IS PROVED (Prop 8's witness tube is freeze-free,
  so d > 0) but with a ρ^h-order margin, wrong by ~96 orders of magnitude
  against the measured d. The route the measurement points to is a LOCAL
  LIMIT THEOREM, not an occupation estimate: d(γ) is a clean power law
  (slope 1.72 over γ ∈ [0.05, 0.4]), i.e. a hitting probability, and a
  local CLT for the joint (angle, radial speed) law at the channel mouth
  would give a polynomial bound.
- **T4 — Prop 6's explicit density constant:** **RESOLVED (2026-07-25).**
  The one-step landing law is EXACTLY circular-uniform (Lemma S), so the
  γ-curves are uniformly Hölder-1/2 with the fully explicit constant
  h·√(r_out/(gain·dt²)) ≈ 1033 (Theorem T4), linear in ε off tangencies
  with explicit C(m) (Theorem T4′), and the per-step √ε rate is ATTAINED
  at tangency (Lemma A(iv)) — so the only route from √ε to ε is an
  occupation bound on the tangency band, the "density constant" the
  sketch anticipated, now isolated — and the MEASUREMENT shows the
  coupling route's quantity P(hit D) genuinely scales sublinearly,
  ε^0.30 over ε ∈ [0.0125, 0.2] (funnel states occupy the tangency band
  and saturate per episode), so the Hölder exponent is not pessimism of
  the method. Validated:
  `scripts/t4_continuity_modulus.py` (exact circle to 4e-15; bounds vs
  analytic/MC; tangency slope exactly 0.5). Section "T4 — the explicit
  continuity modulus" below.
- **T5 — r(n) concentration order with explicit constants.** **ORDER
  RESOLVED (2026-07-25).** The Hoeffding/Azuma route stays refuted; the
  replacement is geometric and needs no concentration inequality:
  reaching the shell forces the displacement into the TANGENT CONE
  (Lemma C), and an exchangeable, sign-symmetric displacement enters a
  fixed cone with probability ≤ 4/(nκ²) (Lemma E), giving the proved
  bound r(n) ≤ 4h/(nκ²), κ² = 1 − (r_out/L)² (Theorem T5-C). Measured
  truth is EXPONENTIAL at exactly the spherical-cap rate
  (r_out/L)ⁿ = 0.4167ⁿ — fitted 0.411, log-linear R² = 0.999 — so the
  dimension effect is the mode's ANGULAR SIZE from the start and nothing
  else. Surprise worth keeping: the cube-uniform thrust is strongly
  diagonal-biased yet matches the isotropic constant to 1.5 %, which
  licenses an isotropic comparison as the route to the sharp theorem.
  **EXPONENTIAL RATE PROVED for the ISOTROPIC action interface
  (2026-07-25):** if the thrust direction is uniform on S^{n−1} then Z is
  spherically symmetric, its direction is EXACTLY uniform, and Lemma G
  (self-contained cap bound) gives r(n) ≤ (h/2)(r_out/L)^{n−2} = 40 ·
  0.4167^{n−2} — the measured law, now a theorem, non-vacuous from n ≈ 7
  against n ≈ 400 for the exchangeability bound. Verified at n = 3…8
  (isotropic decay 0.431 vs predicted 0.4167; cap bound checked to
  n = 30). **INTERFACE TRANSFER largely closed too (Lemma H + Prop
  T5-T):** conditioning on the action's absolute values makes the
  displacement coordinates INDEPENDENT (the norm cap is sign-invariant,
  so the signs are i.i.d. Rademacher — checked bitwise), and a single
  matched-exponent Chernoff bound then returns
  √(e·n/(1+γ²))·(1−κ²)^{(n−1)/2} — the cap rate exactly, losing only √n.
  So the cube route is SHARP, not merely exponential, modulo one
  Berry–Esseen ingredient requiring the conditional weight profile to be
  non-degenerate. Refuted en route: Bernstein-on-Z₁ (computes 2.5e-5 <
  measured 2.4e-3 at n = 8 — the cone event is a small-ball event for
  the perpendicular mass, 0.21× typical at n = 8).
- **T6 — Hidden-channel reachability at γ = 0.6 within h = 80:**
  **RESOLVED (2026-07-24, positive).** A 10-parameter waypoint-controller
  search (400 random + 300 refinement candidates,
  `scripts/t6_hidden06_witness_search.py`) found a controller entering the
  interior **100/100** over the standard start distribution — found at
  candidate 4, so the witness is abundant in the family, not a needle. The
  hand template's failure was control precision, not reachability.
  Machine-checked permanently: `test_t6_hidden06_steering_witness`.
  Consequence for R2: at hidden γ = 0.6 BOTH grades are now witnessed —
  gate-policy rate 0 at n = 400 vs steered rate 1.0.
- **T7 — The relative-homology evidence estimator.** **FIRST HALF
  RESOLVED (2026-07-25):** infinite-bar artifacts characterized (Prop C1:
  they are H₁ of the censor-complement flag complex — per-sample
  DECIDABLE), minimal model proved (Prop C2 quadrilateral), censor
  non-monotonicity established and measured (Prop C3: nested censors →
  0/4/0 infinite-bar cells). Certificate run INVERTED the historical
  note: the never-fillable cycles belong to v1 itself (4/25 cells — the
  3 true gap-0 loops + the single 19/20 specificity failure, now
  diagnosed as structural), not to the margin refinement (rejected for
  bridge restoration, 5/5 finite false loops at γ = 0.6). The
  ambivalence finding (same mechanism carries truth at γ = 0 and the
  false positive at γ = 0.6) is the sharpest argument that edge deletion
  is the wrong primitive. **SECOND HALF LARGELY RESOLVED (2026-07-25):**
  the relative pair estimator is formulated, Props R1 (no infinite bars,
  structural) and R2 (LES reduction to a union-find) proved, the
  point-cloud instantiation REFUTED by measurement (density mismatch)
  and replaced by path input, discrimination 20/20 at γ > 0 against
  plain Rips's 9/20, and the γ = 0 one-sided miss identified as
  Proposition 1's gauge rather than an estimator defect. **T7 CLOSED
  (2026-07-25):** the γ = 0 two-sided miss is NOT a calibration gap but
  Prop R4's shell geometry (freeze zeroes the velocity, so evidence hugs
  the band faces and more data makes it worse), and stability is Prop R5
  (2ε-interleaving of pairs, its path clause shown necessary by an
  ε = 0 counterexample). Nothing open.
- **T8 — Linking-number query lower bound:** **RESOLVED (2026-07-25), in
  two halves.** The UNCONDITIONAL bound is REFUTED with explicit
  landing-free witnesses in BOTH linking classes (even at the dangerous
  offset — a threading plan of trivial extra length exists), so
  "obstruction is path-relative" is now a theorem, not a measurement.
  What survives and is PROVED: the linking dichotomy — a plan that links
  the core either queries the tube or threads the clearance sub-disc D_m
  (Lemmas X/Y); real trajectories never enter the tube and can only link
  through D_m (the hole is the only gate under the true dynamics); and
  the corridor corollary recovers μ_query = 1 exactly when the candidate
  corridor's straight segment clears the core by < ρ_t − Δ/2 (the
  registered offset 1.5 sits AT this boundary: min g = 0.5 exactly).
  thread = linking machine-checked against the Gauss integral
  (`scripts/t8_linking_dichotomy.py`; 1.0006 / 1.0006 / −0.0002).
  Section "T8 — the linking dichotomy" below.

## T1 — the proofs (2026-07-24, second pass: logic, not just validation)

Setting. X = {x₁,…,x_m} ⊂ ℝ², all points star-shaped about the center O
with radii rᵢ = ‖xᵢ − O‖ ∈ [r_min, r_max] and angles θᵢ (our landing
clouds: r ∈ [3.5, ≈3.8]). Sort angles cyclically; let Δθ_max be the largest
cyclic angular gap. For an edge (u, v) write δ(u,v) ∈ (−π, π] for the
minimal angular increment. The winding number of a simplicial 1-cycle z
(integer coefficients) is w(z) = (1/2π) Σ_{edges} δ — an integer, since the
increments telescope mod 2π.

**Lemma B (birth of the winding class — exact).** The smallest VR scale at
which a cycle with w ≠ 0 exists is
  s_w ∈ [ 2 r_min sin(Δθ_max/2), 2 r_max sin(Δθ_max/2) ],
and for points exactly on a circle (r_min = r_max = ρ) it equals
2ρ sin(Δθ_max/2).

*Proof.* (Lower bound.) Let z have w(z) ≠ 0 and let G be the open sector of
the maximal gap. The cumulative angle along z advances by 2πw, so some edge
(u, v) has an increment interval covering G's midpoint; since no sample
point lies in G, both endpoints lie outside G and |δ(u,v)| ≥ Δθ_max. As
|δ| ≤ π, the chord satisfies ‖u − v‖ ≥ 2 r_min sin(|δ|/2) ≥
2 r_min sin(Δθ_max/2) — the planar chord between points at radii ≥ r_min
and angular separation α ≤ π is minimized on the circle of radius r_min.
Hence z requires scale ≥ that chord. (Upper bound.) The consecutive-
neighbors cycle (each point joined to its angular successor) has winding 1
and all its angular increments ≤ Δθ_max, so all its chords ≤
2 r_max sin(Δθ_max/2); it exists at that scale. ∎

**Lemma D⁻ (death lower bound — self-contained, no literature needed).**
At every scale s < √3 · r_min, the winding class is not a boundary; hence
death ≥ √3 r_min.

*Proof.* If s < √3 r_min then every edge has chord < √3 r_min, which forces
|δ| < 2π/3 (a chord between points at radii ≥ r_min with angular
separation ≥ 2π/3 has length ≥ 2 r_min sin(π/3) = √3 r_min). For any
2-simplex all three of whose edges are present at scale s, the boundary's
three increments each lie in (−2π/3, 2π/3) and sum to 2πk with
|sum| < 2π, so k = 0: every triangle boundary has winding 0. Winding is
therefore invariant under adding boundaries at scale s, and a cycle with
w = 1 cannot be null-homologous. ∎

**Corollary (the detector law, proved half).** The bridged bar has
birth = 2ρ̃₁ sin(Δθ_max/2) and death ≥ √3 ρ̃₂ with ρ̃₁, ρ̃₂ ∈
[r_min, r_max]; the measured death/ρ̄ spread [1.70, 1.82] around √3 = 1.732
is exactly the radial thickness of the landing cloud (r ∈ [3.5, ~3.8]:
√3·3.5/3.65 ≈ 1.66 to √3·3.8/3.65 ≈ 1.80). The law
"β̂₁ = 1 iff √3ρ − 2ρ sin(Δθ_max/2) > τ" is therefore proved as a
GUARANTEE in one direction: whenever √3 r_min − 2 r_max sin(Δθ_max/2) > τ,
the bar exists and is persistent (Lemma B upper + Lemma D⁻), so the
detector MUST report β̂₁ ≥ 1.

**Lemma D⁺ (death upper bound — the filling lemma, RESOLVED 2026-07-25).**
Let Δθ_max be the largest angular gap and Δθ₂ the second-largest
(Δθ₂ ≤ Δθ_max). Then the winding bar's death satisfies
  death ≤ 2 r_max · sin(θ*/2),
with θ* given by whichever regime applies (take the smaller when both do):
  (i) if Δθ_max ≤ 2π/3 and Δθ₂ < π/3:  θ* = 2π/3 + Δθ₂;
  (ii) if Δθ₂ < Δθ_max < π:  θ* = max(Δθ_max, (2π − Δθ_max)/2 + Δθ₂/2).
Both θ* ≤ π, so the bound is genuine; and always death ≤ diam(X) ≤ 2 r_max
(cone). KEY REDUCTION: no general "winding-0 ⇒ boundary" filling lemma is
needed — the bar dies as soon as ITS OWN class [z₀] (the
consecutive-neighbors cycle born at Lemma B's scale) becomes a boundary,
and the proof exhibits an explicit 2-chain doing exactly that.

*Proof.* Step 1 (the spanning triangle). Choose three samples x₁, x₂, x₃:
in regime (i), place targets t₁ = G_mid − π/3, t₂ = G_mid + π/3, t₃ =
G_mid + π (G = the largest gap, an open arc of length Δθ_max centered at
G_mid); each target lies outside G (its distance to G's edge is
π/3 − Δθ_max/2 ≥ 0), so its nearest sample sits within Δθ₂/2; the three
arcs of (x₁, x₂, x₃) have lengths 2π/3 ± Δθ₂ < π. In regime (ii), take
x₁ = u, x₂ = v (the samples flanking G) and x₃ = the sample nearest to
G_mid + π (within Δθ₂/2, since that target is not in G when Δθ_max < π);
the arcs are Δθ_max < π and (2π − Δθ_max)/2 ± Δθ₂/2, each < π because
Δθ₂ < Δθ_max. In both regimes every arc is < π and ≤ θ*, so every chord
is ≤ 2 r_max sin(θ*/2) =: s* and the triangle is a 2-simplex of VR(X; s*)
(flag). Its boundary's three angular increments are the arcs (each < π,
sum 2π): winding 1.
Step 2 (fan retraction: [z₀] = [∂triangle] at s*). Let φ map each sample
to the nearest of x₁, x₂, x₃ by angle; φ moves points by ≤ (largest
arc)/2 ≤ θ*/2, so the fan edges (x, φ(x)) have chord ≤ 2 r_max sin(θ*/4)
≤ s*. For each consecutive pair (p, q) of the cycle z₀, the prism
triangles (p, q, φ(p)) and (q, φ(p), φ(q)) lie in VR(X; s*): the only
non-trivial edge is (q, φ(p)), with angular length ≤ (consecutive gap) +
θ*/2. Case (a), the pair flanks G: in regime (ii), p = u, q = v are
themselves vertices and the prism is degenerate; in regime (i), φ(p) is
the x₁-side vertex at angular distance ≤ π/3 + Δθ₂/2 from p, so
(q, φ(p)) has angular length ≤ Δθ_max/2 + π/3 + Δθ₂/2 ≤ 2π/3 + Δθ₂/2
(using Δθ_max ≤ 2π/3), chord ≤ s*. Case (b), any other pair: the gap is
≤ Δθ₂, angular length ≤ θ*/2 + Δθ₂, and the chord comparison
sin(θ*/4 + Δθ₂/2) ≤ sin(θ*/2) holds iff (H): Δθ₂ ≤ θ*/2. (H) is
AUTOMATIC in regime (i), where θ*/2 = π/3 + Δθ₂/2 > Δθ₂ ⟺ Δθ₂ < 2π/3,
already implied; in regime (ii), θ* ≥ (2π − Δθ_max)/2 ≥ π/2, so
Δθ₂ ≤ π/4 suffices — (H) is stated as the lemma's standing hypothesis
and checked numerically per sample.
Under (H), all prisms are present; summing their boundaries telescopes φ
along z₀ (φ is monotone along the angularly-sorted cycle, so the image
cycle is exactly ∂(x₁x₂x₃), degenerate repeats cancelling). Hence
[z₀] = [∂(x₁x₂x₃)] = 0 in H₁(K_{s*}). ∎
NOTE: this kills the CLASS. That the measured BAR dies is a persistence-
pairing statement and needs Lemma P below — the class could in principle
be carried past s* by a winding-0 admixture on a second long bar.

**Lemma P (from class death to bar death — the pairing step).** Suppose
B⁺ < √3 r_min (the persistent regime; otherwise the law predicts no bar)
and let r₀ = rank(ι: H₁(K_{B⁺}) → H₁(K_{√3 r_min − ε})) = the number of
bars containing the window [B⁺, √3 r_min) — computable from the barcode
as #{bars: birth ≤ B⁺, death ≥ √3 r_min}. Then:
  (a) r₀ ≥ 1 always: ι[z₀] ≠ 0 across the window because w(ι z₀) = 1
      and w is defined below √3 r_min (Lemma D⁻'s triangle computation);
  (b) if r₀ = 1, the UNIQUE window-spanning bar has birth ∈ [B⁻, B⁺]
      and death ∈ [√3 r_min, s*] — the sandwich holds for THE BAR.
*Proof of (b).* Fix an interval decomposition V ≅ ⊕ I[bᵢ, dᵢ) of the H₁
persistence module (field coefficients; transition maps act as identity-
or-zero per summand, so a class born by scale x has constant bar
coefficients along s ≥ x). Expand ι[z₀] at s = √3 r_min − ε: only bars
containing [B⁺, s] can carry nonzero coefficients; by r₀ = 1 there is
one, e₁: ι[z₀] = a₁e₁, and applying w gives 1 = a₁·w(e₁), so a₁ ≠ 0 and
w(e₁) ≠ 0. At s*: 0 = ι[z₀] = a₁·ι(e₁) (Lemma D⁺), hence ι(e₁) = 0: the
bar is dead by s*. Its death ≥ √3 r_min since it spans the window; its
birth b₁ ≤ B⁺ by the window, and ≥ B⁻ because its birth class pushes
forward to e₁ with w ≠ 0, so it is a winding cycle and Lemma B applies.∎
  When r₀ ≥ 2 a second long bar coexists with the winding one across the
window; that is exactly the "spurious persistent class" configuration
already recorded as the detector-level exclusion — the hypothesis of
Lemma P and the detector caveat are the SAME per-sample checkable
condition (measured: r₀ = 1 in every factorial row with a nonempty
window, `t1_death_sandwich.json`).

**Corollary (the detector law, now TWO-SIDED).** With B⁻ = 2 r_min
sin(Δθ_max/2), B⁺ = 2 r_max sin(Δθ_max/2) (Lemma B), D⁻ = √3 r_min
(Lemma D⁻), D⁺ = 2 r_max sin(θ*/2) (Lemma D⁺):
  - GUARANTEED β̂₁ ≥ 1 when D⁻ − B⁺ > τ (the bar exists and persists);
  - GUARANTEED no persistent WINDING bar when D⁺ − B⁻ < τ; the detector
    can then only report β̂₁ ≥ 1 through a spurious non-winding class,
    which is the one remaining unproved exclusion (measured: no
    non-winding H1 bar ever cleared τ in the 80-row factorial).
The undecided band D⁻ − B⁺ ≤ persistence-proxy ≤ D⁺ − B⁻ has width
(D⁺ − D⁻) + (B⁺ − B⁻) — radial thickness plus the θ*-slack — and the
measured flip rows (γ = 1.8, N = 160, margin ≈ 0.2) sit inside it, as
they must. Validation: `scripts/t1_death_sandwich.py` — per sensor-
factorial row, the window-uniqueness rank r₀ (Lemma P) and
D⁻ ≤ death ≤ D⁺ for the window-spanning bar.
Status: **T1 CLOSED as a two-sided sandwich law with explicit constants**
(birth exact by Lemma B; death of the class sandwiched by D⁻/D⁺; the
BAR inherits the sandwich under Lemma P's r₀ = 1, which is per-sample
checkable and is the same condition as the spurious-class exclusion —
the caveat structure collapses to one measured-true hypothesis).

## T5 — route refuted (2026-07-24); replaced by a proved cone bound
## (2026-07-25) and an unconditional exponential (2026-07-26, Cor T5-U).
## Only the SHARP CONSTANT on the cube interface rests on measurement.

The worst-case concentration route (Hoeffding/Azuma over the AR(1) weights,
with Chernoff conditioning on ‖a‖ for the norm-cap's n-scaling) computes
NUMERICALLY VACUOUS at the instrument's scales: bound ≈ 0.51 at n = 2–5
versus measured r ≈ 0.013–0.002 (and the conditioning term only bites for
n ≫ 20). Same failure shape as paper 2's envelope-tail attempt: bounded-
difference constants ignore the drag's variance contraction. Recorded as a
refuted route (progress in the (KEY) sense).

**The replacement is geometric, not variance-based** — and it needs no
concentration inequality at all. What kills the hit rate in high dimension
is not the SIZE of the displacement but its DIRECTION: the shell subtends
a fixed solid angle from the start, and an exchangeable displacement
almost never points into a fixed cone.

**Lemma C (tangent cone).** Let x₀ be the start, c the shell centre,
L = ‖c − x₀‖ > r_out, and Z = x_t − x₀. If ‖x_t − c‖ ≤ r_out then
  ⟨Z, e⟩ ≥ κ‖Z‖,  e := (c − x₀)/L,  κ := √(L² − r_out²)/L,
i.e. Z lies in the tangent cone from x₀ to the ball B(c, r_out), whose
half-angle has sine r_out/L.
*Proof.* ‖x_t − c‖² = ‖Z − Le‖² = ‖Z‖² − 2L⟨Z,e⟩ + L² ≤ r_out² gives
⟨Z,e⟩ ≥ (‖Z‖² + L² − r_out²)/(2L) ≥ ‖Z‖·√(L² − r_out²)/L by AM–GM. ∎

**Lemma E (exchangeable cone bound).** Let Z be a random vector in ℝⁿ
whose coordinates are exchangeable and jointly sign-symmetric, and let
e be a unit vector lying in the span of two coordinate axes. Then for
κ ∈ (0, 1],
  P(⟨Z, e⟩ ≥ κ‖Z‖) ≤ 4/(nκ²),
and if e is itself a coordinate axis, P ≤ 1/(2nκ²).
*Proof.* Let S = {i : Z_i² ≥ (κ²/2)‖Z‖²}. Since Σ_i Z_i² = ‖Z‖², we have
|S| ≤ 2/κ² deterministically, so by exchangeability
P(1 ∈ S) = E|S|/n ≤ 2/(nκ²). With e ∈ span(e₁, e₂), Cauchy–Schwarz gives
⟨Z,e⟩ ≤ √(Z₁² + Z₂²), so the event forces Z₁² + Z₂² ≥ κ²‖Z‖², hence
max(Z₁², Z₂²) ≥ (κ²/2)‖Z‖², i.e. 1 ∈ S or 2 ∈ S; union bound. For an
axis-aligned e the event is Z₁ ≥ κ‖Z‖, so 1 ∈ S′ = {i : Z_i² ≥ κ²‖Z‖²}
with |S′| ≤ 1/κ², giving P(|Z₁| ≥ κ‖Z‖) ≤ 1/(nκ²), halved by sign
symmetry. ∎

**Lemma F (the instrument satisfies the hypotheses).** In ShellFieldN the
displacement Z_t = x_t − x₀ = dt²·Σ_s w_{t,s}·T_s, with weights
w_{t,s} = (1 − β^{t−s+1})/(1 − β), β = 1 − drag·dt, and thrusts
T_s = gain·a⃗_s/max(1, ‖a⃗_s‖), a⃗_s ~ U([−1,1]ⁿ) i.i.d. Each T_s has
exchangeable, jointly sign-symmetric coordinates (‖a⃗‖ is invariant under
permutations and sign flips, and the a⃗ coordinates are i.i.d. symmetric);
independent sums of such vectors inherit both properties, so Z_t does.
Moreover c and x₀ lie in the first-two-coordinates plane, so e ∈
span(e₁, e₂). ∎

**Theorem T5-C (explicit dimension bound on the contact rate).** For
ShellFieldN with horizon h,
  r(n) ≤ h · 4/(n κ²),  κ² = (L² − r_out²)/L²,
with L = ‖c − x₀‖ (≈ 12 at the defaults, so κ² = 119/144 ≈ 0.826).
Hence r(n) = O(1/n) with an explicit constant 4h/κ² ≈ 387 — the first
non-vacuous bound for T5, and one that needs no concentration inequality:
only exchangeability and the tangent-cone geometry.
*Proof.* Union bound over t ≤ h of Lemma C ∘ Lemma E, valid by Lemma F. ∎

**What is still open, and why.** The bound is asymptotic in practice: at
the defaults it bites only for n ≳ 400, while the truth at n = 2–6 is
already ~10⁻³. Two named sources of looseness, both now identified rather
than guessed:
  (a) *the union over time* (a factor h = 80) — the h displacement
      vectors are strongly dependent, and a maximal version of Lemma E
      would remove most of it;
  (b) *exchangeability is too weak to see the exponential rate.* Lemma E
      is sharp for exchangeable laws (a Z supported on the coordinate
      axes attains it), but the actual Z is diffuse: for i.i.d.-Gaussian
      coordinates, Z₁²/‖Z‖² ~ Beta(½, (n−1)/2) and the cone probability
      decays like (1 − κ²)^{(n−1)/2} — EXPONENTIALLY. The instrument
      should be at least this fast, since the cube-uniform thrust
      direction has density ∝ (max_i|θ_i|)^{−n} on the sphere, i.e. it
      concentrates near the DIAGONALS and away from the coordinate axes
      where the target sits. Proving the exponential rate therefore needs
      a diffuseness input (an anti-concentration or small-ball estimate
      for Z₁/‖Z‖) that exchangeability alone cannot supply. That is the
      remaining T5 target, now sharply stated.

**The measured law: the rate is the spherical-cap measure**
(`scripts/t5_cone_bound.py`, 10 000 rollouts per n):

| n | cone rate | r measured |
|---|---|---|
| 2 | 0.5120 | 0.0096 |
| 3 | 0.2258 | 0.0049 |
| 4 | 0.0962 | 0.0020 |
| 5 | 0.0383 | 0.0006 |
| 6 | 0.0159 | 0.0002 |
| 7 | 0.0067 | 0.0001 |
| 8 | 0.0024 | 0.0000 |

The decay is **exponential, not polynomial**: log-linear fit R² = 0.999
against log-log R² = 0.952, per-dimension factor **0.411**. The
prediction from treating Z as isotropic is the normalized measure of a
spherical cap of half-angle θ = arcsin(r_out/L), whose leading factor is
sin θ = r_out/L = 5/12 = **0.4167** — agreement to **1.5 %**. So:

  **r(n) ≍ (r_out/L)ⁿ, the tangent cone's angular measure.**

Three consequences worth recording.
(i) The dimension effect is set by the mode's *angular size from the
start* — r_out/L — and by nothing else: not its volume, not its
thickness, not the horizon. "Danger dies with dimension" is a statement
about solid angle.
(ii) Lemma E's 1/n is provably valid but quantitatively the wrong order;
the measurement shows the gap is the whole exponential, so no sharpening
of the union bound (looseness (a)) can rescue it — the missing
ingredient is diffuseness (looseness (b)), as diagnosed.
(iii) A genuine surprise, and a useful one: the cube-uniform thrust
direction has density ∝ (max_i|θ_i|)^{−n} on the sphere and so is
strongly biased toward the diagonals, yet the measured rate matches the
*isotropic* cap constant to 1.5 %. The diagonal bias does not change the
exponential rate — evidence that an isotropic comparison is the right
route to the sharp theorem, not merely the convenient one.

**A refuted route, and the lemma it names (2026-07-25).** The obvious
attack on the exponential upper bound is to write the cone event as
Z₁ ≥ c·R with c = κ/√(1−κ²) = 2.18 and R² = Σ_{i≥2} Z_i², replace R by
its typical value σ√n, and apply Bernstein to Z₁ (bounded by the per-step
displacement, |ΔZ₁| ≤ dt²·W·gain = 1). That computes to ≈ 2.5·10⁻⁵ at
n = 8 — BELOW the measured cone rate 2.4·10⁻³, so the route is invalid,
and the invalidity localizes the error: treating R as concentrated
discards the event's actual mechanism.
*Measured localization* (4000 rollouts, all times): conditional on the
cone event, the perpendicular mass R is **0.41× its typical value at
n = 5 and 0.21× at n = 8**, while the aligned component Z₁ is only 1.18×
typical at n = 5 and, at n = 8, actually *below* typical (1.29 against a
scale of 2.71). So the cone event is **a small-ball event for R, not a
large-deviation event for Z₁**, and the effect strengthens with n.
*Consequence.* The missing ingredient is now a specific, well-posed
lemma rather than "diffuseness": an anti-concentration (small-ball)
estimate P(Σ_{i≥2} Z_i² ≤ t·E[·]) ≤ ρ(t)ⁿ for sums of independent
exchangeable, sign-symmetric vectors. Exchangeability is silent about
R's LOWER tail, which is exactly why Lemma E cannot be improved by any
amount of symmetry — the gap is not looseness, it is the wrong tail.

**The exponential bound, PROVED — for the isotropic action interface
(2026-07-25).** The small-ball lemma is hard because the cube-uniform
thrust is only finitely symmetric. But nothing in the instrument forces
that choice: the action interface is a DESIGN decision (the same point
the n-dim methods note already makes about planner competence). Under
the isotropic interface the obstruction disappears entirely.

**Lemma G (spherical cap bound, self-contained).** For U uniform on
S^{n−1}, n ≥ 3, and κ ∈ [0, 1):
  P(⟨U, e⟩ ≥ κ) ≤ ½ (1 − κ²)^{(n−2)/2}.
*Proof.* The marginal density of U₁ is c_n(1 − u²)^{(n−3)/2} on [−1, 1],
and P(U₁ ≥ 0) = ½, so it suffices to show
∫_κ^1 (1−u²)^{(n−3)/2}du ≤ (1−κ²)^{(n−2)/2} ∫_0^1 (1−y²)^{(n−3)/2}dy.
Substitute u = κ + √(1−κ²)·y, so du = √(1−κ²) dy and y ranges over
[0, √((1−κ)/(1+κ))] ⊆ [0, 1]. Then
  1 − u² = (1−κ²)[1 − 2κy/√(1−κ²) − y²] ≤ (1−κ²)(1 − y²),
and since (n−3)/2 ≥ 0 the map t ↦ t^{(n−3)/2} is nondecreasing, giving
(1−u²)^{(n−3)/2} ≤ (1−κ²)^{(n−3)/2}(1−y²)^{(n−3)/2}. Multiply by
du = √(1−κ²)dy and enlarge the range to [0,1]. ∎
(Machine-checked against the exact cap integral for n = 3…30.)

**Theorem T5-I (exponential rate under the isotropic interface).**
Suppose the per-step thrust T_s is spherically symmetric — direction
uniform on S^{n−1}, norm arbitrary and independent across steps (the
instrument's own norm law is allowed). Then for every t the displacement
Z_t = dt²·Σ_s w_{t,s} T_s is a sum of independent spherically symmetric
vectors, hence spherically symmetric, so Z_t/‖Z_t‖ is EXACTLY uniform on
S^{n−1}. With Lemma C and Lemma G,
  P(reach the shell at step t) ≤ ½(1 − κ²)^{(n−2)/2} = ½ (r_out/L)^{n−2},
and therefore
  **r(n) ≤ (h/2) · (r_out/L)^{n−2}**  — at the defaults, 40 · 0.4167^{n−2}.
*Proof.* Spherical symmetry is preserved by independent sums (a rotation
acts on each summand separately) and by the deterministic weights;
Lemma C makes the tangent cone necessary; Lemma G bounds its measure;
union over t ≤ h. ∎

This is the exponential law itself, no longer a measured regularity: the
rate is exactly the tangent cone's angular measure, and no concentration
or small-ball input is needed because the symmetry is exact rather than
approximate. It is non-vacuous from n ≈ 7 (against n ≈ 400 for the
exchangeability bound). *Verified* (`scripts/t5_isotropic_bound.py`):
the cap bound holds against the exact cap integral at n = 3…30, the
isotropic simulation obeys T5-I at every n = 3…8, and its per-dimension
decay is 0.431 against the predicted sin θ = 0.4167.

## The interface transfer (2026-07-25): the cube case, reduced to one
## Berry–Esseen estimate, with the scheme proved SHARP

The cube-uniform thrust has a finite symmetry group, so no symmetry
argument can reach the exponential rate (Lemma E is sharp for
exchangeable laws). But the cube has a structure the isotropic proof
throws away, and it is exactly the one needed: independence.

**Lemma H (conditional coordinate independence).** The norm cap
M_s = max(1, ‖a_s‖) is a function of the ABSOLUTE values |a_{s,i}|
alone, and the coordinates of a_s are independent and symmetric. Hence,
conditionally on all absolute values B = (|a_{s,i}|), the signs
ε_{s,i} = sgn(a_{s,i}) are i.i.d. Rademacher and
  T_{s,i} = ε_{s,i}·b_{s,i},  b_{s,i} := gain·|a_{s,i}|/M_s
with b B-measurable. Therefore the displacement coordinates
  Z_i = dt²·Σ_s w_{t,s} ε_{s,i} b_{s,i}
are, given B, **INDEPENDENT across i**, each a Rademacher sum with
deterministic weights c_{s,i} = dt² w_{t,s} b_{s,i}. ∎
*Machine-checked EXACTLY, not statistically*
(`scripts/t5_interface_transfer.py`): flipping one sign in column j
changes coordinate j and no other, bitwise, in 1500 checks — and the cap
is sign-invariant, which is the step the lemma turns on.

**Proposition T5-T (transfer scheme; sharp in the exponent).** Write
γ² = (1−κ²)/κ². The cone event implies R² ≤ γ²Z₁² with
R² = Σ_{i≥2}Z_i², so by Lemma H's independence, for any λ > 0 with
2λγ²σ₁² < 1,
  P(cone | B) ≤ E[e^{λγ²Z₁²} | B] · Π_{i≥2} E[e^{−λZ_i²} | B].
If the conditional coordinate laws obey the Gaussian-regime estimates
E[e^{tZ₁²}] ≤ (1−2tσ²)^{−1/2} and E[e^{−λZ_i²}] ≤ (1+2λσ²)^{−1/2}, then
optimizing λ — the optimum is u* = 2λ*σ² = ((n−1) − γ²)/(nγ²) — gives
  P(cone) ≤ √(e·n/(1+γ²)) · (1 − κ²)^{(n−1)/2}.
This is **the spherical-cap rate exactly, losing only a √n factor**: the
scheme is not merely exponential but sharp in the exponent, and it
recovers T5-I's constant without any symmetry.
*Verified*: the closed-form optimum against numerical minimisation, and
the constant against its asymptotic prediction, at n = 3…40 (ratios
2.36/3.18/4.10/5.08/6.62/9.42 versus predicted 2.60/3.35/4.24/5.19/
6.70/9.48).

**The two ingredients.**
(i) *Upper side (Z₁).* Rademacher sums are sub-Gaussian with proxy σ₁²
(Hoeffding), giving E[e^{tZ₁²}] ≤ (1−2tσ₁²)^{−1/2} up to an absolute
constant. STANDARD, no gap.
(ii) *Lower side (each Z_i).* Supplied by Lemma I below — and NOT by the
Berry–Esseen route first anticipated, which would have needed a
weight-profile hypothesis for its VALIDITY. Lemma I needs none.

**A false start worth recording.** The clean statement one wants,
E[e^{−λZ²}] ≤ (1+2λσ²)^{−1/2} for every Rademacher sum, is **FALSE**.
Take equal weights: Z lives on a lattice with an atom at 0, so as λ → ∞
the left side tends to P(Z = 0) ≈ √(2/πh) > 0 while the right side tends
to 0. Any correct version must restrict λ or carry an error term.

**Lemma I (Gaussian domination for Rademacher squares, explicit error).**
Let Z = Σ_s c_s ε_s with i.i.d. Rademacher ε, σ² = Σ_s c_s²,
c_max = max_s|c_s|, ρ := σ/c_max ≥ 1, and u := 2λσ². Then for every
λ > 0:
  E[e^{−λZ²}] ≤ (1 + u)^{−1/2} + 2Φ̄( x₀·ρ/√u ),
with x₀ = 1.7780 the largest x satisfying |cos x| ≤ e^{−x²/2}, and Φ̄ the
standard normal tail. No weight-profile hypothesis is needed for
validity; ρ controls only the error's size.
*Proof.* Since e^{−λz²} = E_g[e^{i√(2λ)gz}] for g ~ N(0,1), Fubini and
independence of the ε_s give
  E[e^{−λZ²}] = E_g[ Π_s cos(√(2λ)·g·c_s) ].
Split on A = {|g| ≤ G}, G := x₀/(√(2λ)·c_max). On A every argument obeys
|√(2λ)gc_s| ≤ √(2λ)·G·c_max = x₀, hence |cos(√(2λ)gc_s)| ≤ e^{−λg²c_s²}
termwise — the ABSOLUTE value is what makes the product step legitimate,
since individual cosines may be negative — so |Π_s cos| ≤ e^{−λg²σ²} on
A. Off A bound the product by 1. Therefore
  E[e^{−λZ²}] ≤ E_g[e^{−λg²σ²}] + P(|g| > G) = (1+2λσ²)^{−1/2} + 2Φ̄(G),
and G = x₀ρ/√u on substituting λ = u/(2σ²). ∎
*Verified* (`scripts/t5_rademacher_ingredient.py`): x₀ is the exact
crossover, and the bound holds on profiles from a single weight (ρ = 1,
where it is valid but loose) through geometric decay to 20 equal weights
(ρ = 4.47), by exact enumeration where feasible and Monte Carlo else.

**Closing the transfer with the instrument's own profile.** At the
scheme's optimum u* ≈ 4.76 the per-coordinate factor is
  q(ρ) = (1+u*)^{−1/2} + 2Φ̄(1.778ρ/2.182) = 0.4167 + 2Φ̄(0.815ρ),
so the sharp cap constant is recovered as soon as ρ is bounded away from
1. The instrument's conditional weights are c_{s,i} = dt²·w_{t,s}·gain·
|a_{s,i}|/M_s: the AR(1) weights spread the mass over ≈ 80 steps and the
|a_{s,i}| are i.i.d. uniform, so no single step can dominate. Measured
over ≈ 8000 coordinate profiles at n = 3…20: ρ has **median 4.0, 5th
percentile 3.4, minimum 2.34**, giving a per-dimension rate of
**0.4177–0.4179** (worst single sample 0.474) against the sharp 0.4167 —
a cost of about 3·10⁻³.

**Lemma I′ (subset refinement).** For ANY subset S of the steps,
  E[e^{−λZ²}] ≤ (1 + 2λσ_S²)^{−1/2} + 2Φ̄( x₀/(√(2λ)·max_{s∈S}|c_s|) ),
σ_S² = Σ_{s∈S}c_s². *Proof.* Z = Z_S + Z_{S^c} with independent parts,
so E[e^{−λZ²}] ≤ sup_t E[e^{−λ(Z_S+t)²}]; the representation gives
E[e^{−λ(Z_S+t)²}] = E_g[e^{i√(2λ)gt}·Π_{s∈S}cos(√(2λ)gc_s)], and the
shift's phase has modulus 1, so taking absolute values reduces to
Lemma I's proof on S. ∎ Useful because a single anomalously large weight
can simply be dropped from S. (Verified on 200 random profiles, half of
them deliberately given a dominant weight: dropping the largest weight
always yields a valid bound.)

**Corollary T5-U (the exponential is UNCONDITIONAL in ρ — 2026-07-26).**
The attempt below tries to prove a lower bound on ρ, having fixed λ at
the error-FREE optimum u* = 4.76. That was the mistake. Re-optimising λ
WITH the error term included changes the picture completely, because
  ρ ≥ 1 always — it is Cauchy–Schwarz: σ² = Σ_s c_s² ≥ c_max².
Substituting ρ = 1 in Lemma I,
  q(u) := (1 + u)^{−1/2} + 2Φ̄(x₀/√u)
satisfies **q(u) < 1 for every u > 0**, with minimum **0.7783 at
u = 1.32**. Both limits approach 1 from below — as u → 0 the first term
→ 1 while the second vanishes super-exponentially; as u → ∞ the first
vanishes and the second ↑ 2Φ̄(0) = 1 — so the supremum is not attained.
(Checked on a grid spanning u ∈ [10⁻⁶, 9·10⁶]: not one point reaches 1.)

**Why this does NOT by itself give a rate.** The value 0.7783
is q at u = 1.32; a single λ makes u_i = 2λσ_i² equal 1.32 for *one*
scale only. Every coordinate does contribute q(u_i) < 1, but a product
of factors each merely below 1 is not exponentially small — an
exponential RATE needs sup_i q(u_i) < 1 uniformly, hence the u_i must lie
in a bounded window, hence the σ_i must be comparable. So the σ_i
comparability is not an optional sharpening; it is load-bearing.

What ρ ≥ 1 genuinely buys is that the window is enormous: q ≤ 0.89 for
σ_i²/m ∈ [0.2, 5] and q ≤ 0.94 for σ_i²/m ∈ [0.1, 10] — a factor 25 to
100. So only very crude control of the spread is needed, which is why
the old requirement (a lower bound on ρ, a max-versus-sum ratio) is
replaced by a much weaker one. But "much weaker" is not "none".

**What the measurement still buys.** With ρ free, the only remaining
requirement is that a single λ serve all coordinates, i.e. that the
per-coordinate scales σ_i be comparable (u_i = 2λσ_i², and q is
minimised at u = 1.32). That is a far milder and more robust condition
than a bound on ρ: since q < 1 at EVERY u, comparability affects only
the constant, and staying within a factor 2 of the optimum costs almost
nothing (q(0.66) = 0.805, q(2.65) = 0.798). Measured spread
τ = max_i σ_i/min_i σ_i over 300 episodes per dimension: median
1.11–1.25, 95th percentile 1.25–1.36 for n = 3…20, giving a
per-dimension rate ≤ **0.789–0.799**.

*Is that comparability provable? I called it "routine"; it is NOT —
tried and failed, 2026-07-26.* The structure is right, and one piece of
it: M_s = max(1,‖a_s‖) is the norm of the WHOLE action, so A_s := (w_s/M_s)² is COMMON to every coordinate, and given
the norms σ_i² = dt⁴gain²·Σ_s A_s a_{s,i}² genuinely is a sum of 80
INDEPENDENT terms. But the constants do not deliver a high-probability
statement at these parameters. For the deviation t = μ/2 (μ = E[σ_i²|
norms], the same for every i by within-step exchangeability): Hoeffding,
whose range term is Σ_s A_s², gives exponent ≈ 2.3–2.9, i.e. 5–10% per
coordinate and a union over the n coordinates that is VACUOUS (0.77 at
n = 8, 1.00 at n = 20); Bernstein, using Var(a²) = 4/45, lifts the
exponent to ≈ 2.9–4.4 but the union is still ≈ 0.4–0.5. Nor does "most
coordinates suffice" rescue it: E[#bad] ≤ 0.03n is only a Markov-level
statement, and making P(#bad > 0.3n) decay in n needs concentration of
the bad-count, whose indicators are exchangeable but DEPENDENT (within a
step the coordinates lie on a sphere-slice). Numbers for each route
tried, at the deviation the wide window permits (σ_i² ≥ 0.2m, i.e.
ζ = 0.2, which still gives q ≤ 0.89):
  • Hoeffding, range term Σ_s A_s²: exponent 2.3–2.9, union VACUOUS.
  • Bernstein, Var(a²) = 4/45: exponent 2.9–4.4, union 0.4–0.5.
  • Multiplicative Chernoff on X_s = A_s a²/A_max ∈ [0,1], exponent
    (1−ζ)²(m/A_max)/2: m/A_max is only 5–12 because m carries a 1/n and
    E[a²] = 1/3, so the exponent caps near 3.
  • Same, after using Lemma I′ to DROP the top-k steps by A_s (which
    shrinks A_max fast and m slowly): m_S/A_max,S rises 5.1 → 10.3 at
    k = 10, exponent → 4.2, union still 0.31.

**What IS proved for the cube interface, floor and all.** Take
λ = 1.32/(2m) with m = (1/n)Σ_iσ_i² (B-measurable, and equal to
E[σ_i²|norms] by within-step exchangeability). Then:
  • DETERMINISTICALLY #{i : σ_i² > 5m} ≤ n/5, since Σ_iσ_i² = nm;
  • by the Chernoff above, E#{i : σ_i² < 0.2m} ≤ 0.04n, so Markov gives
    P(#{i : σ_i² < 0.2m} > 0.3n) ≤ 0.12;
  • off that event at least n/2 coordinates have σ_i²/m ∈ [0.2, 5],
    each contributing q ≤ 0.89.
Hence P(cone) ≤ 0.89^{n/2} + 0.12 — unconditional, but with a constant
floor, from Markov applied to what I took to be a dependent count.

**Lemma K (norm-free sandwich — the floor was self-inflicted,
2026-07-26).** Both defects above dissolve at once. Deterministically
M_s² = max(1,‖a_s‖²) ∈ [1, n], so A_s = w_s²/M_s² ∈ [w_s²/n, w_s²] and
  σ_i² ≥ (1/n)Σ_s w_s² a_{s,i}²,   m = (1/n)Σ_s w_s² min(1,‖a_s‖²) ≤ S/n,
with S := Σ_s w_s². Therefore
  {σ_i² < z·m} ⊆ {Σ_s w_s² a_{s,i}² < z·S},
and the right-hand event **depends only on coordinate i's own variables**
(a_{s,i})_s. Two consequences, each killing one defect:
  (i) the a_{s,i} are i.i.d. U(−1,1) with no conditioning, so the exact
      Chernoff bound applies with the true MGF of a²,
        p(z) = min_θ exp(θzS)·Π_s E[e^{−θ w_s² a²}],
        E[e^{−ca²}] = ½√(π/c)·erf(√c);
      numerically p(0.2) = 9.7·10⁻⁴ against the range-based bound's 0.31
      — a factor 300 — and simulation puts the truth at 1.2·10⁻⁴, so the
      exact bound is only 8× loose;
  (ii) the bad indicators are INDEPENDENT across i (disjoint variable
      sets), so #bad is BINOMIAL and Chernoff replaces Markov:
      P(#bad > αn) ≤ (e·p/α)^{αn} — exponentially small in n.
So negative association is not needed at all: the coupling that seemed to
require it is an artifact of conditioning on the norms.

**Theorem T5-F (cube interface, unconditional and floor-free).** With
λ = 1.32/(2m), a lower cutoff z, an upper cutoff K (deterministic:
#{σ_i² > Km} ≤ n/K since Σ_iσ_i² = nm) and a bad-fraction α,
  P(cone) ≤ q_max^{(1−α−1/K)n} + (e·p(z)/α)^{αn},
  q_max := max(q(1.32z), q(1.32K)).
Optimising over (z, K, α) at the instrument's weights gives
**z = 0.2, K = 10, α = 0.05, hence P(cone) ≤ 2 · 0.9057ⁿ** — a clean
exponential with NO floor and NO measured input. (Previous: 0.9434ⁿ +
0.12.)

Summary for the cube interface: exponential decay PROVED outright,
≤ 2·0.9057ⁿ; the sharper 0.80ⁿ still rests on the measured spread
τ ≤ 1.36, and the sharp 0.4167ⁿ on the measured ρ ≈ 4.

| statement | status |
|---|---|
| r(n) decays exponentially, cube interface | **PROVED outright: ≤ 2·0.9057ⁿ, no floor, no inputs** (Thm T5-F) |
| … with σ_i comparable (measured τ ≤ 1.36) | ≤ 0.80 per dimension, no floor |
| … the sharp rate 0.4167 = r_out/L | measured (ρ ≈ 4) |
| r(n) ≤ (h/2)(r_out/L)^{n−2}, isotropic | PROVED exactly (T5-I) |

**On PROVING ρ — the accounting that led here (superseded above, kept
because it is what forced the re-optimisation).** The
chain is: ρ_i² ≥ (M_min/M_max)²·Σ_s v_s²a_{s,i}², where v_s = w_{t,s}/w_max
is the deterministic AR(1) profile and M_s = max(1,‖a_s‖). For the
instrument's profile Σv_s² = 44.2 and Σv_s⁴ = 32.8, so Hoeffding on the
bounded independent terms v_s²a_{s,i}² gives Σ_s v_s²a_{s,i}² ≥ 4.09
with probability 0.999, i.e. ρ_i ≥ 2.02·(M_min/M_max). The remaining
factor is where the accounting goes badly: M_s ∈ [1, √n] deterministically,
and the concentration ‖a_s‖² ≈ n/3 that would give M_max/M_min ≤ √3
needs a union bound over h = 80 steps, which is vacuous until n ≳ 80.
So the PROVED constants are:
  • n ≳ 80 (concentration bites): ρ ≥ 1.17, rate q ≤ 0.758;
  • M_s effectively constant (n → ∞): ρ ≥ 2.02, q ≤ 0.516;
  • MEASURED at n = 3…20: ρ median 4.0, min 2.34, q ≈ 0.418.
Attempts to remove the M-factor by pigeonholing the steps into dyadic
M-bands, or by restricting to the AR(1) plateau, make the surviving
subset small enough that the loss exceeds the gain (both were tried; the
subset version of the argument lands below the trivial ρ ≥ 1). So a good ρ stays measured — but
Corollary T5-U above makes that moot for the EXISTENCE of the
exponential, which needs no ρ at all.

**Status: T5 CLOSED for the isotropic interface; for the cube interface
the exponential is proved only with a constant floor (below).** The
chain is complete for both:
Lemma C (tangent cone) → Lemma H (conditional independence) →
Prop T5-T (matched-exponent Chernoff) → Lemma I (the Rademacher
ingredient) gives the spherical-cap rate for the cube-uniform action;
Lemma G → Theorem T5-I gives it exactly for the isotropic action. The
residue on the cube interface is TWO things, both quantified above: the
proved bound carries a constant floor 0.12 (Markov on a dependent
count), and the sharp constant 0.4167 rests on the measured spread.
Measured decays agree across all three: cube 0.411, isotropic 0.431,
theory 0.4167.

An irony worth keeping: the isotropic interface is provable because its
symmetry is exact, the cube interface because its coordinates are
independent — the two routes are disjoint, and it is the cube's, the
apparently harder case, that yields the sharp constant.

## T2 — lemma proved, exact route closed by a hypothesis-emptiness certificate (2026-07-24)

**Lemma (clean-step coincidence).** At a fixed real state with the
deterministic candidate enumeration: truth imagination and blind
imagination score every A-free candidate identically (the models agree off
A), so if NO candidate's imagined path touches A, the two argmaxes coincide
exactly; by induction, an episode all of whose steps are candidate-clean is
IDENTICAL under the two planners and contributes 0 to play_cost. (Proof:
strict-> argmax over the same enumeration of equal scores; the weaker
per-step form — blind argmax A-free AND touch-penalties not promoting
another candidate — suffices and is what the checker tests.) ∎

**Certificate (the hypothesis is empirically empty).**
`scripts/t2_aligned_degeneracy.py` replays paired episodes at facing
γ ∈ {0.3, 0.6, 1.2} marking each step clean/dirty: **0/48 episodes are
clean end-to-end** — every episode has at least one step where the blind
argmax clips A in imagination or a touching candidate separates the two
argmaxes. So the aligned-channel degeneracy is NOT explained by exact
coincidence (route closed, in the seed-50543 sense), and the exact-0
conditional theorem, though valid, has empty scope at episode granularity.

**What the data says the true mechanism is (the remaining target).** The
dirty return gaps are SMALL: truth − blind ≈ 0.7 on average (occasionally
negative — random-shooting noise) against a denominator ≈ 40, giving the
measured pc ≈ 0.02. The correct theorem to seek is a PER-CONTACT REGRET
BOUND: each imagination-touch near an open channel costs O(freeze-transient)
because the next replan threads the channel — bounding pc by
(touch rate) × (per-touch cost) / (J_truth − J_random). T2 stays OPEN with
this named target; artifacts: `results/t2_aligned_degeneracy.json`.

## T2 (second pass, 2026-07-25) — the per-contact decomposition is an
## EXACT IDENTITY, not a bound

Setting. Deterministic dynamics f; make the planners MARKOV by seeding
each step's candidate draw with (episode_seed, t) — a per-step-seeded
variant of the harness planner (same candidate family; the identity
needs the policy to be a function of (state, t) alone, which the
sequential-RNG harness is not). Both planners share the per-(episode, t)
candidate set; a step is CLEAN iff the blind argmax action equals the
truth argmax action on that shared set (the clean-step lemma's
condition), DIRTY otherwise.

**Lemma T2-I (hybrid telescoping — exact).** Let π_B, π_T be the blind-
and truth-planner policies, s₀..s_{H−1} the π_B trajectory, and for a
state s and step index t let V_T^t(s) = the return of following π_T from
s for the remaining steps. Then
  J(π_T) − J(π_B) = Σ_{t dirty} A_t,   with
  A_t = [r(s_t, τ_t) + V_T^{t+1}(f(s_t, τ_t))]
      − [r(s_t, b_t) + V_T^{t+1}(f(s_t, b_t))],
τ_t = π_T(s_t, t), b_t = π_B(s_t, t). Clean steps contribute EXACTLY 0.
*Proof.* Hybrid argument: h_t = return of playing π_B for steps < t then
π_T from step t (h_0 = J(π_T)-episode from s₀... precisely h_0 = pure
π_T, h_H = pure π_B, both from the same s₀). h_t and h_{t+1} share the
π_B prefix through s_t; they differ only in the step-t action (τ_t vs
b_t) and the π_T continuation from the resulting state:
h_t − h_{t+1} = A_t. At a clean step τ_t = b_t so A_t = 0. Sum the
telescope. ∎
Corollary (the named per-contact bound, now trivial):
  pc = Σ_{dirty} A_t / (J_T − J_rand) ≤ D̄ · Â / (J_T − J_rand),
D̄ = dirty-step count, Â = max_t A_t. The CONTENT is no longer the
inequality but the measured size of Â — the identity localizes all of
play_cost onto the dirty steps' advantage terms, and A_t can be NEGATIVE
(a blind action that happens to score better under the truth
continuation), which is why dirty return gaps were occasionally negative.

**Measured decomposition** (`scripts/t2_percontact_identity.py`, Markov
planner horizon 40 / 48 samples, 6 episodes × γ ∈ {0.3, 0.6, 1.2}):

| γ | dirty steps / 80 | Ā | max A_t | frac(A_t < 0) |
|---|---|---|---|---|
| 0.3 | 20–23 (mean 21.2) | +0.129 | 11.65 | 0.40 |
| 0.6 | 13–19 (mean 14.7) | +0.169 | 2.70 | 0.40 |
| 1.2 | 8–12 (mean 10.5) | +0.118 | 2.26 | 0.40 |

Identity residual ≤ 4.6·10⁻¹⁴ in 18/18 episodes. Three readings:
(i) **the contact RATE, not the per-contact cost, carries the γ-trend** —
Ā is flat (≈0.12–0.17) while dirty steps fall by half from γ = 0.3 to
1.2, so the danger curve's γ-dependence lives in the first factor of
D̄·Â, exactly where the reachability story predicts it;
(ii) **40% of dirty steps have A_t < 0** at every γ — blind's action is
often BETTER under the truth continuation, so play_cost is a small
difference of large cancelling terms, which is why bounding it by
|A_t| alone must be loose;
(iii) the γ = 0.3 outlier max A_t = 11.65 against a mean of 0.13 is a
heavy tail: any useful a-priori bound must control the tail, not the
mean. *(Planner note: the Markov variant with 48 samples is not the
registered arm's 200-sample sequential planner, so absolute pc here is
not comparable to the paper's 0.02–0.03 — the structure is the claim,
not the level.)*

*Status after this pass:* the decomposition half of T2 is CLOSED as an
identity (machine-checked: per-episode Σ A_t = J_T − J_B to float
precision, 18/18). The a-priori half — a tail bound on A_t — stays open;
the next section refutes the obvious guess about it.

### T2 tail mechanism: the freeze-transient guess is REFUTED (2026-07-25)

The natural conjecture, and the one written into the earlier target, was
that a large A_t is a FREEZE TRANSIENT: the blind action pushes the
trajectory into the mode, costing a freeze the truth action avoids.
`scripts/t2_tail_mechanism.py` records, for all 278 dirty steps, the
freeze counts of BOTH continuations. Result:
  **every continuation freezes exactly 0 times — 0/556.**
The reason is structural and should have been obvious: after the dirty
step both branches follow π_T, and the truth planner knows the mode, so
it never touches it. The advantage term compares two mode-free futures.
Freeze transients cannot be the tail; the guess is dead.

What the tail actually correlates with (same run, top decile
|A| ≥ 1.818, n = 27):
  • **remaining horizon** — tail steps have mean t = 14.3 versus 25.9 in
    the bulk, and corr(remaining horizon, |A|) = +0.325: the damage of a
    wrong first action is proportional to how long it has to compound;
  • **channel narrowness** — 18 / 6 / 3 of the tail at γ = 0.3 / 0.6 /
    1.2, i.e. the tail concentrates where the two routes around the mode
    differ most.
*Route commitment: REFUTED.* The reading under test is that A_t is a
ROUTE-COMMITMENT cost — one bad first action committing the
truth-following continuation to the other way around the annulus, so
that V_T jumps across the CUT LOCUS where the optimal route switches
sense — and named a cut-locus bound as the target. That reading was an
interpretation of two correlations, not a measurement, so I measured it:
`scripts/t2_route_commitment.py` runs both continuations under π_T and
records which side of the ring each passes (sign of y at closest
approach). If route commitment were the mechanism, tail events would be
the opposite-side ones. Result, 215 dirty steps at γ ∈ {0.3, 0.6}:
  P(opposite sides | TAIL) = **0.190**,
  P(opposite sides | bulk) = **0.299**,
  mean |A|: opposite **0.623** vs same-side **0.920**.
The correlation runs BACKWARDS: tail events are *less* likely to split
the routes, and same-side pairs carry the larger advantages. Route
commitment is refuted, and with it the cut-locus target — which was
attractive precisely because it would have tied T2 to the paper's
topology, a reason to distrust it rather than to believe it.

**The third reading — DELAY COST — is CONFIRMED (2026-07-26).** The
surviving facts (|A_t| grows with the remaining horizon, concentrates at
narrow gaps, same route) suggested that a wrong first action simply
loses TIME, and that the return is dominated by time spent in the
phantom basin. Unlike the two refuted readings this one makes a sharp
quantitative prediction, so it was measured rather than asserted. With
  dwell := #steps of a continuation with dist(pos, centre) < r₀,
the prediction is A_t ≈ amp_phantom·(dwell_τ − dwell_blind) — slope
equal to a KNOWN constant, not a fitted one.
`scripts/t2_delay_cost.py`, 215 dirty steps at γ ∈ {0.3, 0.6}:
  **slope 0.9404** against amp_phantom = **1.0** (6% off),
  **intercept 0.0141** (≈ 0), **R² = 0.9275**,
  nonzero dwell difference in **100%** of tail events vs **41%** of the
  bulk.
So the dwell difference explains 93% of the variance in the per-contact
advantage, at the reward amplitude. This is the mechanism.

**The sum telescopes back to ONE number: the arrival delay
(2026-07-26).** Two further measurements collapse the statement.
*(a) Dwell is sticky.* In 9/9 episodes across γ ∈ {0.3, 0.6, 1.2},
neither planner ever leaves the basin once it arrives. So
dwell = h − T_arr exactly, and Δdwell is an ARRIVAL-TIME difference, not
an occupancy pattern.
*(b) The per-step terms telescope.* Comparing the hybrid sum with the
whole-episode dwell difference: J_T − J_B against amp·(Dwell_T −
Dwell_B) gives ratios 0.81–1.66 (mean ≈ 1.07) over the same 9 episodes.
Combining with the identity and the delay regression,
  **pc = amp_phantom · (T_arr^B − T_arr^T) / (J_T − J_rand)** ,
i.e. the entire aligned-channel play-cost IS the blind planner's
lateness at the lure. Measured arrival times: truth 33–36, blind 37–38,
so the delay is **1–5 steps** — and a 1–5 step delay against a
denominator of ≈ 40 is exactly the pc ≈ 0.02–0.1 the arm reports.

**A freeze-based account of the delay: also REFUTED, and replaced.** I
next proposed that the delay is (number of π_B freezes) × (recovery cost
per freeze), since one velocity reset carries an asymptotic distance
deficit of v_∞·dt/(1−β) = 33 units. Measured: in the facing
configuration **π_B freezes 0 times** — the blind trajectory never
touches the band at all. So the delay is not a contact cost, and the
third mechanism in this family dies with the first two.

**What the delay actually is: the AIM POINT (2026-07-26).** The blind
model has no wall, so π_B steers at the straight line to the lure. With
the channel FACING, that line threads it — the aim is nearly right, the
executed path never contacts, and the planner is merely a few steps
sloppier than one that steers for the channel itself. Rotating the
channel off the axis must then break it, and the break is not gradual:
| channel offset | arrival, truth | arrival, blind | π_B freezes |
|---|---|---|---|
| 0.0 (facing) | 34–36 | 37–38 | **0** |
| 0.4 | 39–41 / never | never (2/3) | **49–50** |
| 0.8 | never | never | **48–50** |
So the aligned-channel degeneracy is a knife edge: 0.4 rad of rotation
turns "arrives 1–4 steps late, never touching the mode" into "hammers
the wall fifty times and never arrives". (This also reconciles the arm's
blind contact rate of 1.0, which is measured in a non-facing setting.)

**A quantitative clean-step lemma, with FULL scope (2026-07-26).**
Because the executed blind path is contact-free, π_B's whole loss is
candidate MIS-RANKING. That can be bounded, and the bound is forced by
algebra. Write bc, tc for the blind- and truth-argmax candidates. From
V_B(bc) ≥ V_B(tc),
  V_T(tc) − V_T(bc)
    = [V_T(tc) − V_B(tc)] + [V_B(tc) − V_B(bc)] + [V_B(bc) − V_T(bc)]
    ≤ [V_T(tc) − V_B(tc)]⁺ + Δ_over,   Δ_over := V_B(bc) − V_T(bc).
*Both terms are needed.* Dropping the first — i.e. assuming the truth's own
candidate never touches the mode — leaves a bound that holds only
51–71/106 (the truth planner does plan grazing paths, and a freeze can
RAISE the truth's score by parking the trajectory nearer the lure than
the blind continuation flies). With both terms the chain holds
**106/106**, as it must.

The point is not the inequality but its SCOPE. Both terms are
model-disagreement on the disagreement region E: they vanish identically
when neither candidate's imagined path touches A. So this is the
QUANTITATIVE version of the clean-step lemma whose exact version was
closed by the hypothesis-emptiness certificate (0/48 clean episodes) —
the exact statement had empty scope, this one has full scope and reduces
to it. In paper-2's language both terms are μ_query-type quantities, so
the aligned-channel play-cost is bounded by imagination-side
disagreement, which is the shape that paper's Proposition 3 predicts.

**The replanning link FAILS (2026-07-27).** The chain bounds the
CANDIDATE-level gap V_T(tc) − V_T(bc), whereas the identity's A_t is a
CONTINUATION-level term (both branches then follow π_T). The natural
hope was that the former dominates the latter, which would close a
play-cost bound. Measured: **A_t ≤ candidate gap in only 101/106** dirty
steps, worst violation A_t = +2.62 against a candidate gap of +0.97. So
it is not a theorem, and the failure is intelligible: MPC replanning
moves both branches, usually rescuing the bad first action (mean A_t
0.175 against mean candidate gap 6.26, a factor 36) but occasionally
rescuing the good one more, which reverses the inequality. Open-loop
candidate values simply do not order closed-loop continuations.

**A closed-loop attempt, and the obstruction it exposes (2026-07-27).**
The identity is exactly the performance-difference lemma: since π_T(s) =
τ, one has A^{π_T}(s, τ) = 0 and therefore
  **A_t = −A^{π_T}(s_t, b_t)** ,
the cost of a one-step deviation from π_T. Bounding it needs the value
of the MPC policy, and the one handle MPC gives without any continuity
assumption is that its argmax beats EVERY candidate in its set —
including the constant "straight at the lure" candidate. If MPC
therefore arrived no later than the straight-line policy, the arrival
time would be bounded by a purely geometric quantity and the delay bound
would follow. Measured: **0/30**. MPC arrives at step 28 against the
straight policy's 22, consistently across γ ∈ {0.3, 0.6, 1.2} — it is
optimising a 40-step return, not arrival, and its executed path is a
sequence of first actions from successively replanned candidates, which
is not any single candidate.

**Proposition T2-D (the obstruction, as a theorem rather than a pattern
of failures — 2026-07-27).** Four routes failing the same way is
evidence, not proof; the statement can be proved outright by
construction. Every *imagination-level* quantity at a step — the two
models' returns on every candidate, hence Δ_over, the excess, whether
the step is clean, and μ_query — is a function of the triple (state s_t,
the two models, candidate set C_t). But
  A_t = −A^{π_T}(s_t, b_t)
also depends on the candidate sets C_{t+1}, …, C_h, which are planner
randomness carrying no information about the models. Hence A_t is NOT
measurable with respect to the imagination-level data, and no bound of
the form A_t ≤ g(imagination data) can be tight: any valid g must
dominate the essential supremum over the future planner randomness. ∎

*Measured, at a single step with the imagination data pinned exactly*
(γ = 0.6, t = 14; V_B(bc) = V_T(bc) = 11.0982 — so even Δ_over = 0 —
V_T(tc) = 11.5304, V_B(tc) = 8.3519): varying only the future candidate
seeds moves A_t over **[−1.707, +0.602]**, a spread of **2.309**. That
is an order of magnitude above the mean |A_t| = 0.175 over all dirty
steps. The conditional spread is the irreducible looseness of ANY
imagination-level bound.

*What this does and does not say.* It does not invalidate paper 2's
play_cost ≤ μ_query(E): that bound is correct here, and by Proposition 4
equals 1 — correct and vacuous. It says the vacuity is not an artifact
to be sharpened away. And it identifies the only remaining direction:
bound **E[A_t | s_t, C_t]**, the conditional mean over planner
randomness, rather than A_t. That is a statement about the (model,
planner) PAIR — consistent with the paper's own theme that danger
requires a competent planner and that competence is an interface
property, not a model property.

**The direction T2-D leaves open, carried out (2026-07-27).** Prop T2-D
says a tight bound must condition on the planner. Do that: let W̄ be the
π_T value AVERAGED over the planner's candidate draws. Then, exactly,
  **E[A_t | s_t, C_t] = Δr + W̄(f(s_t, τ)) − W̄(f(s_t, b))** ,
a difference of one function at two states that differ by ONE action
choice. Lemma S caps that difference with no further assumptions: both
landings lie on the same circle of radius R_L = gain·dt² about the same
drift centre, and both velocities on a circle of radius gain·dt, so
  ‖Δposition‖ ≤ 2·gain·dt² = 0.060,  ‖Δvelocity‖ ≤ 2·gain·dt = 0.600.
*Measured, and the caps are tight*: max ‖Δpos‖ = 0.0590, max ‖Δvel‖ =
0.5903 over the dirty steps of three episodes. So
  |E[A_t | s_t, C_t]| ≤ L_p·0.060 + L_v·0.600 + |Δr|,
and everything reduces to the Lipschitz behaviour of the SEED-AVERAGED
value — which, unlike the MPC policy itself, is smoothed by averaging
over candidate draws.

*Measuring L_v needs care.* At K = 10 seeds the estimator's standard
error (≈ 0.38) exceeds the signal, and the ratios it produces are noise
— an apparent L_v = 12.7 at the smallest perturbation. With K = 100 and
CRN pairing:
  smallest perturbation (‖Δv‖ = 0.029): E[A|s,C] = **−0.015 ± 0.078**,
    i.e. statistically zero — the apparent blow-up was noise;
  largest  perturbation (‖Δv‖ = 0.590): E[A|s,C] = **+0.462 ± 0.078**,
    ratio **0.78 ± 0.13**.
Consistent with Lipschitz scaling, at L_v ≈ 0.8.

**Assembling the bound — and what it costs to use proved constants
only (2026-07-27, corrected).** The chain is
  pc ≤ D̄ · (L_v·2·gain·dt + L_p·2·gain·dt² + Δr_max) / (J_T − J_rand),
with L_v itself bounded through the fixed point L_v ≤ A/(1−p). Feeding
each available value of A (D̄ ≈ 15 dirty steps, denominator ≈ 40,
p ≈ 0.5):
| constant A | source | ⇒ L_v ≤ | ⇒ pc ≤ | |
|---|---|---|---|---|
| 107 | PROVED (drag cap × h·Lip r) | 214 | **48.2** | vacuous |
| 2.7 | competence hypothesis (saturation) | 5.4 | **1.21** | vacuous |
| 0.77 | measured | 1.5 | 0.35 | non-vacuous |
| — | measured L_v ≈ 0.8 directly | 0.8 | 0.18 | non-vacuous |

Since pc ≤ 1 holds trivially (play_cost 1 means the blind planner is no
better than random), the proved chain is vacuous by a factor 48 and the
competence-hypothesis chain misses at 1.21: a non-vacuous bound requires a
measured constant.

*Where the remaining factor sits.* Between the hypothesis chain (1.21)
and the measurement (0.18) there is a factor 6.7, and it is two things,
both of which charge worst cases: every dirty step is charged the MAXIMUM
perturbation 2·gain·dt = 0.6, whereas the measured ‖Δv‖ over dirty steps
averages ≈ 0.28; and the fixed point costs 1/(1−p) = 2 at p = 0.5. Both
are averages over the PLANNER's action choices, since
‖Δv‖ = 2·gain·dt·|sin((φ_τ−φ_b)/2)| with φ = πa/a_max.

**Closing the first of the two, and the SCOPE that emerged
(2026-07-27).** The sum, not the max, is what the identity needs:
Σ_dirty A_t ≤ L_v·Σ_dirty ‖Δv_t‖ = L_v·D̄·E‖Δv‖, so a bound on the MEAN
suffices, and with ‖Δv‖ = 2·gain·dt·|sin((φ_τ−φ_b)/2)| the question is
E|sin((φ_τ−φ_b)/2)| against 2/π, the mean of |sin| over a period (its
value for two INDEPENDENT uniform actions).

*Full stochastic dominance is FALSE.* An initial check over 278 dirty
steps at facing γ ∈ {0.3, 0.6, 1.2} found the measured CDF above the
independent-uniform CDF at every quantile. Stress-tested at ~10× the
sample and over a wider grid (`scripts/t2_angle_dominance.py`: 4 gaps ×
{facing, hidden} × 2 planner budgets, 10 105 dirty steps), dominance
fails in **11 of 16 cells**, with worst deficit +0.60. The earlier
zero was again a power/coverage artifact — this time of coverage, since
the failures are concentrated in a configuration the first check did not
sample.

*The mean claim survives, with a sharp scope.* What the bound needs is
only E|sin| ≤ 2/π, and the split is clean:
| configuration | cells | E|sin| | dirty steps/cell |
|---|---|---|---|
| **facing** channel | 8 | 0.409–0.625, **all < 2/π** | 39–277 |
| **hidden** channel | 8 | 0.940–0.941, **all > 2/π** | 1119–1120 |
So the mean bound holds in every facing cell and fails in every hidden
one. The mechanism is transparent and is the R2 remark again: with the
channel hidden the truth model is observationally a CLOSED ring, so the
truth planner heads west to the real lode while the blind planner charges
east at the phantom — the two argmaxes are near-ANTIPODAL (|sin| ≈ 0.94)
and, tellingly, **every single step is dirty** (n = 1120 = 14 episodes ×
80 steps, in all four hidden gap cells, whose numbers are identical
because a hidden channel leaves the truth's behaviour γ-independent).

*The bound, correctly scoped.* With E‖Δv‖ ≤ 2·gain·dt·(2/π) = 0.382,
  **pc ≤ 0.767 for the FACING channel** — non-vacuous, and with no
fitted constant: the measured input is a distributional claim (a mean
inequality), not a number read off a regression. Evidence label
*measured*, unit dirty step, n = 1109 facing dirty steps across 8 cells,
`results/t2_angle_dominance.json`. It does NOT extend to the hidden
channel, where the same chain is vacuous — appropriately, since that is
the configuration in which the blind model is maximally wrong about
direction. Scope matters here rather than being a caveat: the
aligned-channel degeneracy this section is about IS the facing case.
*Still unproved:* the mean inequality itself, a property of the (model,
planner) pair — exactly the object Prop T2-D identifies as unavoidable.

**Can L_v be proved? Half of it can (2026-07-27).**
*Provable half — the drag makes divergence bounded, not exponential.*
With IDENTICAL actions the plant is affine, so δv_t = β^t δv₀ and
δx_t = δx₀ + dt·Σ_{k≤t} δv_k, giving for all t
  **‖δx_t‖ ≤ ‖δx₀‖ + ‖δv₀‖·dt/(1−β) = ‖δx₀‖ + ‖δv₀‖/drag**,
i.e. 0.06 + 0.6/0.3 = **2.06** at the instrument's values — bounded
forever, and without drag it would grow without bound. Verified against
the integrator over 400 random states × 200 steps: worst observed
1.9956 against the cap 2.0600, tight to 3%. This is the structural
reason W̄ can be Lipschitz at all.
*The other half is NOT anti-concentration.* The natural completion would
be that the argmax rarely switches under a
small perturbation. Measured, it switches often: an ε = 0.05 velocity
perturbation already flips the argmax for **10%** of candidate draws,
rising to 66% at ε = 0.8, with no clean C·ε scaling. So the smoothing
does not come from switches being rare.
*Where it does come from.* At a switch the two candidates are TIED in
imagined value, so the loss from switching is not the value gap but the
divergence it creates — two states 0.6 apart in velocity, whose future
value difference is again ≤ L_v·0.6. That yields a self-consistent
bound
  L_v·δ ≤ A·δ + p(δ)·L_v·(2·gain·dt),
with A the identical-actions constant (which the drag cap controls),
closing whenever p(δ)·2·gain·dt < 1 — measured p ≈ 0.5 at δ = 0.6, so
p·0.6 ≈ 0.3 < 1 and the fixed point exists. That is the shape of a
proof of L_v; what remains unproved is A.

*Why A resists, precisely.* Under identical actions the drag lemma caps
the separation at 2.06 for all time, so the crude bound is
A ≤ h·Lip(r)·2.06 = 80 × 0.65 × 2.06 = **107** — against a measured
|ΔW̄| of 0.46, a factor 230. The looseness is entirely the assumption
that every step pays Lip(r): the reward is a pair of sigmoids that
SATURATE, so two trajectories 2.06 apart differ in reward only while one
is inside the transition shell (width w = 0.5) and the other is not.
Charging only those steps gives A·δ ≤ amp_total × (arrival-time offset)
≤ 1.3 × 2.06 = **2.7**, within a factor 6 of the measurement. But that
step needs both trajectories to REACH the basin and stay — a
reachability property of π_T, not of the plant — and reachability of the
lure under the truth planner is exactly what the instrument assumes
rather than proves (it is the (RG)/(C) competence hypothesis of Prop 4
in another guise). So A is bounded by a proved 107 and, under the
competence hypothesis already used elsewhere in the paper, by 2.7.

**T2 status: a non-vacuous bound exists for the FACING channel
(pc ≤ 0.767), resting on one hypothesis already used in the paper plus a
measured mean inequality that holds in the facing configuration and fails
in the hidden one.** The original
question — bound play_cost from the model's own disagreement — is
answered NEGATIVELY and provably (Prop T2-D). The replacement — bound it
from the planner-averaged value — has a proved reduction (Lemma S, with
caps measured tight at 0.0590/0.5903), a proved divergence cap (the drag
lemma, tight to 3%), and an identified source of smoothness (ties at a
switch, not rarity of switches, with a fixed point that closes since
p·2·gain·dt ≈ 0.3 < 1). What it does NOT yet have is a non-vacuous bound
from proved constants: that requires A, and A's proved value is 40×
too large while its hypothesis value is still 20% short of useful. The
missing ingredient is the distribution of the angle between the two
argmax actions — a planner property, as Prop T2-D requires.

So T2 stands at: an exact decomposition (the hybrid identity = PDL), a
validated mechanism (delay/arrival, R² = 0.93), and a proved per-step
inequality with full scope that bounds an object the closed loop does
not respect.

## T4 — the explicit continuity modulus, RESOLVED (2026-07-25)

The structural fact that unlocks everything: the one-step landing law is
not merely absolutely continuous — it is EXACTLY the uniform measure on a
circle whose radius is a constant of the plant.

**Lemma S (one-step landing law).** Fix any state s = (x, y, vx, vy)
(including post-freeze states) and draw a ~ U(−a_max, a_max). The proposed
landing of one `integrate_2d` step is
  L = c(s) + R_L · (cos φ, sin φ),   φ = π a / a_max,
with drift center c(s) = (x + (1 − drag·dt)·vx·dt,
y + (1 − drag·dt)·vy·dt) and radius R_L = gain·dt². Since a ↦ φ is a
linear bijection [−a_max, a_max] → [−π, π] carrying uniform to uniform,
the landing law is exactly the uniform (normalized arc-length) measure on
the circle ∂B(c(s), R_L). At the defaults R_L = 0.03.
*Proof.* Read off `integrate_2d`: x′ = x + v′x·dt = x + (1 − drag·dt)·vx·dt
+ gain·dt²·cos φ, same for y; the pushforward of the uniform angle law
under φ ↦ c(s) + R_L(cos φ, sin φ) is by definition the uniform
arc-length measure. ∎ (The accompanying machine check,
`test_t4_landing_circle_exact`, is a CODE-CONFORMANCE check — that the
repository's integrator is the map this theorem is about — not part of
the mathematics.)

**Lemma A (circle–strip anticoncentration, explicit).** Let U be uniform
on the circle of radius R centered at c, S the closed strip of width w
around a line ℒ, and s = dist(c, ℒ). Set ℓ = w/R. Then:
  (i) [unconditional] P(U ∈ S) ≤ √(ℓ/2) = √(w/(2R));
  (ii) [transversal ⇒ linear] if s ≤ (1 − m)R for some m ∈ (0, 1] and
       w ≤ mR, then P(U ∈ S) ≤ 2w/(π R √(3m));
  (iii) [miss] if s ≥ R + w/2 then P(U ∈ S) = 0;
  (iv) [tangency sharpness] if s = R and ℓ ≤ 2 then P(U ∈ S) ≥ √ℓ/π —
       so (i) is attained up to the factor π/√2 ≈ 2.22, and no per-step
       bound of order better than √w holds without a hypothesis on s.
*Proof.* Choose coordinates with ℒ = {second coord = 0}, c = (0, s),
s ≥ 0; rotating coordinates shifts the uniform ψ, so U ∈ S iff
sin ψ ∈ I := [(−w/2 − s)/R, (w/2 − s)/R], an interval of length ℓ. Over a
period, Leb{ψ : sin ψ ∈ [a, b]} = 2·(arcsin(b ∧ 1) − arcsin(a ∨ (−1))).
  (i) The arcsin increment over intervals of length ℓ is maximized when I
abuts an endpoint: arcsin(1) − arcsin(1 − ℓ) = arccos(1 − ℓ)
= 2 arcsin √(ℓ/2) ≤ π √(ℓ/2) (using arcsin u ≤ (π/2)u); divide by 2π.
  (ii) The endpoints of I satisfy |·| ≤ s/R + ℓ/2 ≤ 1 − m/2, so
arcsin′ = (1 − t²)^{−1/2} ≤ (m − m²/4)^{−1/2} ≤ 2/√(3m) on I (m ≤ 1);
Leb ≤ 4ℓ/√(3m); divide by 2π.
  (iii) I ∩ [−1, 1] = ∅.
  (iv) I = [−1 − ℓ/2, −1 + ℓ/2]; Leb = 2 arccos(1 − ℓ/2)
= 4 arcsin √(ℓ/4) ≥ 4√(ℓ/4) = 2√ℓ (arcsin u ≥ u); divide by 2π. ∎

**Lemma W (sliver-in-strip).** For γ′ = γ + ε ≤ 2π the divergence set
D(γ, γ′) = A(γ) \ A(γ′) is the union of two slivers, each of angular
width ε/2 flanking the channel; each sliver is contained in the strip of
width w_ε = r_out·ε/2 around the line through the ring center along the
sliver's angular bisector.
*Proof.* A sliver point p has |p − c₀| ≤ r_out and angular offset ≤ ε/4
from the bisector, so its distance to the bisector line is
|p − c₀|·sin(offset) ≤ r_out·ε/4 = w_ε/2. ∎
*(Chebyshev ring: identical with w_ε = √2·r_out·ε/2, since d_∞ ≤ r_out ⇒
d₂ ≤ √2·r_out; the gap sector stays angular in both norms.)*

**Theorem T4 (explicit modulus for the γ-curves).** For all
0 ≤ γ ≤ γ′ ≤ 2π with ε = γ′ − γ, and for q = r, q = r_int — indeed for
the probability q of ANY trajectory-determined event —
  |q(γ) − q(γ′)| ≤ P(some landing in D(γ, γ′) within h steps)
                 ≤ h · √( r_out · ε / (gain · dt²) ).
At the defaults (h = 80, r_out = 5, gain = 3, dt = 0.1) the modulus is
80·√(500ε/3) ≈ 1033·√ε: r and r_int are uniformly Hölder-1/2 on [0, 2π]
with a fully explicit constant. Corollary, quantitative continuity at 0:
r_int(γ) = |r_int(γ) − r_int(0)| ≤ 1033·√γ (with r_int(0) = 0 exact).
Prop 6's TODO is closed.
*Proof.* Lemma 3 gives the first inequality. For the second, the coupled
trajectory's state before step t is ℱ_{t−1}-measurable and a_t is an
independent uniform, so by Lemma S the conditional landing law is
circular-uniform with radius R_L = gain·dt²; by Lemmas W and A(i) each
sliver contributes ≤ √(w_ε/(2R_L)), so P(L_t ∈ D | ℱ_{t−1}) ≤
2·√(r_out·ε/(4·gain·dt²)) = √(r_out·ε/(gain·dt²)); union over t ≤ h. ∎

**Theorem T4′ (linear off tangencies — the promised density
decomposition).** Fix m ∈ (0, 1] and let ε satisfy w_ε ≤ m·R_L (i.e.
ε ≤ 2m·gain·dt²/r_out). For step t and sliver line ℒ^± write
s_t^± = dist(c(state_{t−1}), ℒ^±), and call (t, ±) *tangent* if
s_t^± ∈ ((1 − m)·R_L, R_L + w_ε/2]. Then
  P(hit D within h) ≤ h·C(m)·ε + √(w_ε/(2R_L)) · E[#tangent pairs],
with C(m) = 2·r_out / (π·gain·dt²·√(3m)) — at the defaults
C(m) ≈ 106.1/√(3m). *Proof.* Per step and sliver apply Lemma A(ii) when
s_t^± ≤ (1 − m)R_L (contribution 2w_ε/(πR_L√(3m)) = C(m)·ε/2), A(iii)
when s_t^± > R_L + w_ε/2 (zero), and A(i) on the tangent pairs. ∎
  The √ε residue is NOT an artifact of the method: by Lemma A(iv), a state
whose drift center sits at distance exactly R_L from a sliver line with
the tangency arc inside the sliver proper (available at any radius in
[r_in, r_out]: the tangency arc has length ~√(w_ε·R_L) ≪ ring thickness)
has SINGLE-STEP hitting probability ≥ √(w′/R_L)/π with w′ ≥ r_in·ε/2 the
sliver's true width there — the per-step √ε rate is attained, so improving
the modulus to O(ε) requires an occupation bound on the tangency band (a
density constant for the drift-center law along the trajectory), not a
better per-state estimate. That is exactly the "density constant"
anticipated by the Prop-6 sketch, now isolated as the sole remaining gap
between √ε and ε.
  *Measured scaling — the tangency term is REAL, not a technicality*
(`results/t4_continuity_modulus.json`): P(hit D) over ε ∈ [0.0125, 0.2]
at γ = 0.6 fits log-log slope **0.30** (ε ×16 ⇒ P ×2.3) — strictly
sublinear. So a LINEAR bound on the divergence probability — the
intermediate quantity every coupling proof controls — is refuted at the
measured scale, not merely unprovable per-state; whether |Δr_int| itself
is Lipschitz stays open (its increments, 0.0005–0.001, are below CRN
resolution at n = 4000). Mechanism: the funnel states (the same mouth-hovering freeze-re-anchor
population behind seed 50543) sit with drift centers within ~R_L of the
channel-edge ray — inside T4′'s tangency band — and propose MANY
correlated landings per episode, so mouth episodes saturate (hit for
every ε in range) and the marginal growth comes from the thin
non-saturated fringe: slope ≤ 1/2. The coupling inequality
|Δr_int| ≤ P(hit D) was verified sample-exact per ε, with measured slack
≈ 10× (0.0005–0.001 vs 0.005–0.011).

**Honesty note (what the constant is and is not).** 1033·√ε is
astronomically loose at the measured scale (adjacent-γ r_int increments
are ~10⁻³ at ε = 0.2): the union bound counts all h steps while Lemma
A(iii) zeroes all but the near-band ones, and worst-case-state
anticoncentration is far from typical. The theorem's content is
structural: the landing law is EXACTLY circular-uniform (Lemma S), the
modulus is finite and explicit for EVERY trajectory event at once, and the
only obstruction to a linear modulus is tangency occupation — located, not
hidden.

## T3 (partial) — M1 and M2 hold UP TO THE FUNNEL MASS, unconditionally
## (2026-07-25): the conjectures become theorems with a measured slack

The pathwise route to M1/M2 is closed (seed 50543) and the pointwise
(KEY) route is refuted, so both were logged as measured-only. But
Proposition 7 already proves the DIRECT component is pathwise monotone,
and that alone yields a one-sided theorem — no occupation measures
needed. Write, at gap γ, r_int(γ) = d(γ) + f(γ) with d = P(direct entry)
and f = P(funnel-assisted entry: enters, but lands in A(γ) at least once
before its first entry).

**Theorem T3-P (one-sided monotonicity with an explicit defect).** For
all 0 ≤ γ₁ < γ₂ ≤ 2π,
  r_int(γ₂) ≥ r_int(γ₁) − f(γ₁).
Consequently: (a) any violation of M1 at the pair (γ₁, γ₂) is at most
f(γ₁); (b) M2 holds up to the same defect, r_int(2π) ≥ r_int(γ) − f(γ),
and at γ = 2π there is no wall so every entry is direct, r_int(2π) =
d(2π); (c) if f(γ₁) = 0 then M1 holds EXACTLY at that pair.
*Proof.* r_int(γ₂) = d(γ₂) + f(γ₂) ≥ d(γ₂) ≥ d(γ₁) (Proposition 7,
pathwise inclusion direct(γ₁) ⊆ direct(γ₂)) = r_int(γ₁) − f(γ₁). ∎

**Why this is progress and not bookkeeping.** M1/M2 stop being
conjectures and become theorems with a *named, measurable* defect term.
The remaining question is no longer "prove monotonicity" — an abstract
occupation-measure problem — but "bound f(γ)", a single scalar with a
mechanical definition, which the instrument measures directly. And the
seed-50543 certificate is now *explained rather than merely recorded*:
it must be a funnel entry, because Proposition 7 forbids a direct one —
the counterexample lives exactly in the term T3-P isolates.

**Measured defect** (`scripts/t3_funnel_bound.py`, n = 50 000 per gap —
12.5× the original probe):

| γ | direct | funnel | f (95% upper) |
|---|---|---|---|
| 0.0 | 0 | 0 | 7.7·10⁻⁵ |
| 0.2 | 61 | 10 | 3.7·10⁻⁴ |
| 0.6 | 272 | 22 | 6.7·10⁻⁴ |
| 0.9 | 378 | 22 | 6.7·10⁻⁴ |
| 1.8 | 542 | 6 | 2.6·10⁻⁴ |
| ≥3.2 | 562 | 0 | 7.7·10⁻⁵ |

Three things this buys:
(i) **Proposition 7 re-verified at 550 000 pathwise comparisons** (11
adjacent pairs × 50 000 CRN seeds): 0 violations, as proved — the
theorem's engine is machine-confirmed at 12.5× the earlier sample.
(ii) **The certified slack is 6.7·10⁻⁴ against an effect of 0.0112 —
a factor 16.9.** M1 and M2 are therefore established to within a defect
17× smaller than the phenomenon they describe, with 0 empirical
violations at this sample size. They are no longer conjectures.
(iii) **The funnel profile is unimodal and vanishes at both ends** —
0 at γ = 0 (nothing to enter), rising to 22/50 000 at γ ∈ [0.6, 0.9],
back to 0 for γ ≥ 3.2. This is the mechanism the name claims: funnelling
needs BOTH a wall to freeze against and a channel to thread, so it dies
when either disappears. By T3-P(c), M1 holds EXACTLY (defect provably
zero if f = 0) throughout the saturated region γ ≥ 3.2, where the
measurement is 0/50 000.

**Theorem T3-P″ (the defect is the DROP in f, not f — 2026-07-26).**
The derivation of T3-P discards a positive term. Restoring it:
  r_int(γ₂) = d(γ₂) + f(γ₂) ≥ d(γ₁) + f(γ₂) = r_int(γ₁) − f(γ₁) + f(γ₂),
so for γ₁ < γ₂
  **r_int(γ₂) ≥ r_int(γ₁) − [f(γ₁) − f(γ₂)]⁺** ,
strictly stronger than T3-P at no cost, and with a qualitative
consequence: **wherever f is nondecreasing the defect is EXACTLY ZERO**
and M1 holds outright, with no bound on f needed at all. Only a DROP in
the funnel mass can break monotonicity.
*Measured on the grid* (adjacent pairs): the defect is exactly 0 in
**6 of 11** pairs — every pair on which f rises, i.e. the whole range
γ ≤ 0.9 where T3-P′ is vacuous and where the old statement was weakest.
On the remaining pairs the worst defect falls from 4.4·10⁻⁴ to
**2.4·10⁻⁴**, so the separation against the effect size 0.0112 improves
from 25.5× to **46.8×**. The two earlier bounds are subsumed: T3-P′
(f ≤ r) still covers the wall-free end by proof, and the drop form
covers the small-γ end by making the defect vanish identically.
*What this changes about the target.* The open problem is no longer "a
bound on f" but "a bound on how fast f can DECREASE" — and f's decrease
is confined to γ ≳ 0.9, exactly where T3-P′ already proves the defect
≤ r(γ) → 0. So the two halves now overlap rather than leaving a gap; a
uniform statement would follow from f's unimodality, which is measured
(f rises to a peak at γ ∈ [0.6, 0.9] and falls to 0) but not proved.

*Sharpest form of what remains — and why it is NOT a reduction
(2026-07-26, corrected 2026-07-27).* Writing the increment out,
  r_int(γ₂) − r_int(γ₁) = [d(γ₂) − d(γ₁)] + [f(γ₂) − f(γ₁)],
with the first bracket PROVED nonnegative (Prop 7), so M1 can fail only
if f's drop exceeds d's rise. "Prove d's rise beats f's drop" is NOT a
target: that inequality is LOGICALLY EQUIVALENT to M1 itself (r_int(γ₂) ≥ r_int(γ₁) ⟺ d-rise ≥ f-drop), so
it restates the problem rather than reducing it — the same trap as the
c = r·κ factorisation, caught here before it was acted on. And a
pathwise version is impossible: seed 50543 refutes pathwise M1, hence no
injection from lost funnel entries to gained direct entries can exist.

*Conclusion for T3-P″.* Proposition 7 has now been squeezed dry: T3-P″ is
the strongest defect bound it can yield, and it is a bound on the SIZE
of a failure, not a route to excluding one.

## T3 — the original ingredient, and a NON-equivalent route (2026-07-27)

*The local form of the ingredient is already refuted.* Stochastic
domination of the post-divergence states would follow if, at the first
divergence, the γ₂ copy (which continues into the widened channel with
its velocity) dominated the γ₁ copy (which freezes at the previous
position). That pointwise statement is exactly (KEY), and (KEY) was
refuted by the freeze-rescue measurement (91/91 CI-separated
violations). This is a genuine refutation, not a circularity — the route
is closed for a reason, and only the distributional form survives.

*Restatements to avoid.* M2 ⟺ f(γ) ≤ d(2π) − d(γ), and M1 ⟺ d's rise
beats f's drop. Both are equivalences, like c = r·κ before them. Any
route phrased as "bound this quantity" where the quantity's only free
bound is the statement itself is a rename.

**A route that is NOT equivalent: isolate the velocity reset.**
Freeze-rescue is caused by one specific modelling choice — a contact
zeroes the velocity. Consider the VARIANT in which a contact blocks the
POSITION but leaves the velocity updating freely. This is a different
instrument, so proving M1 there is not equivalent to proving it here;
and if M1 becomes pathwise in the variant, freeze-rescue is
demonstrably the sole obstruction. Measured, 20 000 CRN rollouts per
gap over eight gaps:
  instrument (velocity reset):    **3** pathwise violations
  variant (velocity preserved):   **0** pathwise violations
with essentially identical marginals (r_int agrees to ≤ 3·10⁻⁴).

*And the variant has the structural reason a proof would need.* When a
contact preserves the velocity, the velocity process is
**γ-INDEPENDENT** — it is a function of the action sequence alone, since
the mode never touches it. So under CRN both copies share v_t exactly,
positions are x_0 + dt·Σ_{s free} v_s, and at the first divergence the
γ₂ copy is the γ₁ copy TRANSLATED by dt·v (same velocity, one free step
ahead, and that step lands inside the widened channel). The
post-divergence comparison is therefore between two exact translates
evolving under a shared velocity process — a far more tractable object
than two states with different velocities, which is what the reset
creates. That is the handle, and it exists only in the variant.

*Four candidate invariants, and the one that nearly works
(2026-07-27).* Over 24 000 CRN pairs per gap pair, counting pairs with
at least one violation among those that diverge:
| candidate invariant | 0.2→0.6 | 0.6→1.2 | 1.2→2.4 |
|---|---|---|---|
| (a) current distance d₂ ≤ d₁ | 2 | 6 | 13 |
| (b) **running minimum** min d₂ ≤ min d₁ | **0** | **0** | **2** |
| (c) free-step count |free₂| ≥ |free₁| | 5 | 5 | 1 |
| (d) path length L₂ ≥ L₁ | 6 | 4 | 1 |
(divergence occurs in 126 / 119 / 71 pairs.)
The RUNNING MINIMUM is the right shape — it is exactly what decides
entry, and it is strictly weaker than the pointwise ordering. The two
violations at the widest pair are explained by the last remark: the
invariant only has to hold UP TO the γ₁ copy's entry time, since that is
when it is used.

**The conditional invariant, and its REFUTATION by adversarial search
(2026-07-27).** The candidate was: for γ₁ < γ₂ in the velocity-preserving
variant, under CRN,
  min_{s ≤ t} d(x²_s) ≤ min_{s ≤ t} d(x¹_s) for every t ≤ τ₁,
τ₁ the γ₁ copy's first entry time. It would imply pathwise M1 in one
line (copy 1 entering means min d¹ < r_in at τ₁, hence min d² < r_in,
hence copy 2 entered by then). It survived 24 000 CRN pairs at ADJACENT
gap pairs — and adjacency was the flaw in that test. Searching the
widest separations instead (γ₁ ∈ {0.1, 0.3, 0.6, 1.2, 2.4} against
γ₂ = 2π, 15 000 pairs each) finds **2 violations in 90 000 pairs**, at
γ₁ = 0.3 and 0.6. Wilson 95% upper bound on the violation rate
8.1 × 10⁻⁵, unit = CRN pair. So the conditional invariant is refuted
too, and the earlier zero was an artifact of sampling only small
divergences.

**The variant statement itself is REFUTED (2026-07-27).** The invariants
were only routes to pathwise M1 in the variant; the statement can be
tested directly, and the unit matters — only a pair in which the γ₁ copy
ENTERS can falsify it, so the unit is the entering pair, not the
rollout. The first check gave 0 failures in 517 entering pairs, which is
a Wilson 95% upper bound of 7.4 × 10⁻³ and no more: it cannot support a
claim below about one in a hundred. Accumulating units until the interval
is worth quoting (`scripts/t3_variant_pairs.py`, resumable,
3 000 000 CRN pairs at γ₁ ∈ {1.2, 2.4, 3.2} against γ₂ = 2π):

| cell | failures | entering units | rate |
|---|---|---|---|
| 1.2 → 2π | 5 | 9 088 | 5.5·10⁻⁴ |
| 2.4 → 2π | 5 | 10 793 | 4.6·10⁻⁴ |
| 3.2 → 2π | 3 | 10 883 | 2.8·10⁻⁴ |
| **total** | **13** | **30 764** | 4.2·10⁻⁴ [2.5·10⁻⁴, 7.2·10⁻⁴] |

Evidence label *measured*; unit entering pair; n = 30 764;
`results/t3_variant_pairs.json`. So **pathwise M1 fails in the
velocity-preserving variant too**, at a rate of roughly 4 in 10 000
entering pairs, consistently across all three cells.

*What that settles.* Removing the velocity reset does NOT make M1
pathwise; freeze-rescue is therefore **not** the sole obstruction, and
the whole variant route — the isolation argument, the γ-independence
handle, both candidate invariants — is closed. The residual mechanism
must be the position block alone: a blocked copy is re-anchored in
POSITION, which suffices to destroy pathwise inclusion without any
velocity effect.

*What it does not settle.* The distributional statements M1 and M2
remain measured-consistent and are unaffected: they never claimed a
pathwise ordering, and T3-P″ still bounds their defect. What is refuted
is the last route that would have proved them.

**Method note, and the reason to record it.** Both of this section's
zeros — 0/24 000 for the invariant and 0/517 for the statement — were
artifacts of insufficient power, one from sampling only adjacent gap
pairs and one from counting rollouts instead of units. Both fell to a
targeted search. A censored zero is an interval, and its width is set by
the number of experimental UNITS, which here is two orders of magnitude
below the rollout count.

*What survives.* Pathwise M1 in the variant held in **0** of those same
18 000 pairs (on top of the earlier 140 000), so the statement itself is
not in doubt; what is missing is the right invariant. It is weaker than
distance ordering, and it must be a property preserved by the shared
velocity process rather than by the geometry of a single step.

Status: T3's remaining gap is localised to a single modelling feature
(the velocity reset) and to a single missing object (the invariant for
the variant's induction). The target is non-equivalent to M1 for the
instrument, structurally supported by the γ-independence of the velocity
process, and 0/158 000 against it — with the first candidate invariant
now ruled out.

**Corollary T3-P′ (the defect has an A-PRIORI bound too).** A funnel
entry lands in A(γ) at least once before entering, so
funnel(γ) ⊆ fire(γ) and
  f(γ) ≤ r(γ),  hence  r_int(γ₂) ≥ r_int(γ₁) − r(γ₁) for γ₁ < γ₂.
This replaces the measured slack by a quantity the theory already
controls: r is nonincreasing (Prop 5) and r(2π) = 0, so **the M1/M2
defect bound improves monotonically in γ and vanishes at the wall-free
end**. At γ = 2π there is no mode at all, so r(2π) = 0 BY CONSTRUCTION,
hence f(2π) = 0 and M2's defect at the endpoint is exactly zero — proved,
not measured. (At γ = 4.6 the probe also reports r = 0, but that is a
0/4000 measurement, not a proof; the distinction matters and we keep it.)
Checked on the grid: f ≤ r holds at every γ, though loosely — r/f runs
from 24× (γ = 1.2) to 356× (γ = 0.1), because most fires never go on to
enter.

*Where T3-P′ actually bites (2026-07-26 — sharper than "loose").* The
defect bound r(γ) is useful for M1 only where r(γ) < r_int(γ); otherwise
r_int(γ₂) ≥ r_int(γ₁) − r(γ₁) has a negative right-hand side and says
nothing. On the grid, r < r_int exactly for **γ ≥ 1.2**; at every
γ ≤ 0.9 the bound is **VACUOUS for M1**, not merely loose. So T3-P′
proves the monotonicity defect only on the upper half of the range
(including the wall-free end, where f measures 0/50 000 and measurement
could prove nothing), and the lower half rests entirely on the measured
f. The two are complementary, but the split is at γ ≈ 1.0, not
everywhere.

*The target, now stated exactly.* What the small-γ half needs is not "a
bound on f" but a bound of the form
  **f(γ) ≤ c · r_int(γ) with a constant c < 1**,
i.e. *funnel entries are a bounded FRACTION of all entries*. That is
what makes T3-P read r_int(γ₂) ≥ (1−c)·r_int(γ₁), a genuine
monotonicity-up-to-a-factor. Note the two easy bounds sit exactly at the
boundary of usefulness: f ≤ r_int is trivially true (funnel ⊆ enter) and
gives c = 1, which is vacuous; f ≤ r gives c = r/r_int, which exceeds 1
below γ = 1.2. So ANY constant c < 1 proved uniformly would be new.
Measured c = f/r_int: 0.222 / 0.141 / 0.050 / 0.075 / 0.055 at
γ = 0.1 / 0.2 / 0.4 / 0.6 / 0.9 — so even c = 1/4 would cover the
measured range, and c = 1/2 would already halve the defect.

Full closure of T3 = a bound f(γ) ≤ c·r_int(γ) with c < 1 uniform (see
the sharpened statement above). Any such c is new; c = 1/4 would cover
the whole measured range.

**c < 1 is PROVED — and the constant is useless (2026-07-27).** Since
c = f/r_int = 1 − d/r_int, a strict c < 1 is equivalent to d(γ) > 0, and
that is already a theorem: Proposition 8's witness tube is explicitly
FREEZE-FREE (it maintains distance ≥ c(γ) = min(0.8γ, 0.9) from A along
the way), so every trajectory in it is a DIRECT entry, giving
  d(γ) ≥ P(|y₀| ≤ η(γ)) · ρ^h > 0,  ρ = c(γ)/(2L_h).
Hence
  **r_int(γ₂) ≥ (1 − c(γ))·r_int(γ₁) with c(γ) < 1, proved**, and by
Prop 5's chain this is a genuine (if weak) monotonicity-up-to-a-factor.
The catch is the size: ρ^h is 10⁻⁸⁶ at γ = 0.6 and 10⁻⁶⁴ at γ = 1.2, so
1 − c is astronomically small and the statement, while strictly true, is
quantitatively vacuous. The measured c is 0.05–0.22.
*What that isolates.* The obstruction is no longer "is any c < 1
available" — it is that the only proved lower bound on d is an
action-tube probability ρ^h, exponentially small in the horizon because
it forces the entire action sequence into a narrow window. Two transfers
from T5 were computed and do NOT work: the tangent cone from a frozen
position at distance ≈ 4 to a target of radius r_in = 3.5 has half-angle
sine 0.875, so the per-step cone bound is 0.34 and the union over h = 80
is vacuous; and the channel sector sits in a strip of width ≈ r_out·γ = 3
against a landing circle of radius R_L = 0.03, where Lemma A gives
√(w/2R_L) = 7 > 1 per step. Both are recorded so the next attempt does
not repeat them.

**What the right route looks like, measured (2026-07-27).** A tube bound
and a hitting bound differ in a testable way: a tube probability is
exponential in the horizon, whereas hitting a target of angular measure
γ with a density-bounded landing law is POWER-LAW in γ. Measured
(200 000 rollouts per gap, direct entries only):
| γ | d(γ) |
|---|---|
| 0.05 | 9.5·10⁻⁵ |
| 0.10 | 3.4·10⁻⁴ |
| 0.15 | 6.3·10⁻⁴ |
| 0.20 | 1.2·10⁻³ |
| 0.30 | 2.2·10⁻³ |
| 0.40 | 3.3·10⁻³ |
log-log slope **1.72** — a clean power law, not an exponential. And the
scale gap is decisive: at γ = 0.1 the proved tube bound is of order
10⁻¹⁰⁰ while d is 3.4·10⁻⁴, so the tube argument is wrong by ~96 orders
of magnitude. Evidence label *measured*, unit rollout, n = 200 000 per
gap.
*Consequence.* d is a hitting probability, and the ingredient it needs is
not a local CLT after all: something more elementary and fully provable
does the job, because the plant's smoothing makes a SINGLE action move
the endpoint macroscopically.

**Lemma J (two-action steering — the exponent ρ^h is unnecessary).** In
the free-flight (freeze-free) regime the endpoint is a smooth function of
the action sequence with
  ∂x_T/∂a_s = K·W(T−s)·(−sin φ_s, cos φ_s),  K := gain·π·dt²,
  W(m) := Σ_{k<m} β^k = (1−β^m)/(1−β),  β = 1 − drag·dt,
so for any two steps s₁ ≠ s₂ the Jacobian of (a_{s₁}, a_{s₂}) ↦ x_T is
  **|J| = K²·W(T−s₁)·W(T−s₂)·|sin(φ_{s₁} − φ_{s₂})|** ,
bounded above by (K/(1−β))² = 9.87 and bounded below away from the
degenerate coincidence φ_{s₁} = ±φ_{s₂}. Consequently, freeing just TWO
actions and fixing the rest, the map to the endpoint is a local
diffeomorphism onto a region of area up to 4·(K/(1−β))² ≈ 39.5 — larger
than the whole instrument's scale — and the entry probability factorises
as
  d ≥ ¼·inf|J|·area(target) × P(prefix event),
polynomial in the target's measure with NO exponential-in-h factor.
*Proof.* Differentiate the affine free-flight recursion: a change δa_s
alters the thrust by K/dt²·δa_s·(−sin φ_s, cos φ_s), which the velocity
recursion carries forward with weights β^k, and the position accumulates
dt·Σ of those — giving the stated derivative. The Jacobian is the cross
product of the two derivative vectors, whose directions are the two
rotated thrust directions, giving the sine factor. ∎
*Verified numerically to 8·10⁻⁹ relative error* at four (s₁, s₂) pairs
(`recorded in this section`), and the one-action sensitivity separately:
measured |∂x_T/∂a_s| rises from 0.186 at lag 1 to 2.865 at lag 79 against
the analytic 0.094…2.858 — i.e. one early action alone sweeps ≈ 5.7 units
of endpoint displacement, where a single landing moves only R_L = 0.03.
That factor of ~190 between the per-step landing scale and the
per-action endpoint scale is exactly what Prop 8's tube throws away.

*"Bound P(prefix)" is CIRCULAR.* Lemma J
removes the exponential but leaves P(prefix), the probability that the
other h−2 actions bring the trajectory to a state from which two free
ones finish. That is not a target: a launch state is DEFINED as one from
which the remaining actions enter, and entry requires passing through
one, so P(reach a launch state, freeze-free) = d identically. This is the
fourth restatement this section has produced (after c = r·κ, d-rise ≥
f-drop, and f ≤ d(2π) − d(γ)); the pattern is that any decomposition of
the entry event into "get into position" × "finish" recovers the entry
event, because position is defined by the finish.

**A decomposition that is NOT circular (2026-07-27).** Break the entry
event using the RING-FREE dynamics, whose quantities cannot mention entry
at all:
  **d(γ) = R · ∫_channel ρ(θ) dθ · T(γ)**
  R := P(a ring-free rollout ever reaches radius r_out) — γ-INDEPENDENT;
  ρ := density of the FIRST-ARRIVAL angle at r_out, ring-free —
       γ-INDEPENDENT;
  T(γ) := throughput, the fraction of channel-sector arrivals that reach
       the interior — the only γ-dependent factor.
Measured (`scripts/t3_reach_density_throughput.py`, 120 000 ring-free
rollouts and 200 000 per gap):
  **R = 0.03049**, and ρ(π) = **1.0167 per rad** (zero at π/2 and 0 — the
approach is one-sided, which is why the facing channel matters);
| γ | d measured | R·ρ·γ | T (ratio) | T (from counts) |
|---|---|---|---|---|
| 0.05 | 9.5·10⁻⁵ | 1.55·10⁻³ | 0.061 | 0.069 |
| 0.10 | 3.4·10⁻⁴ | 3.10·10⁻³ | 0.110 | 0.115 |
| 0.20 | 1.2·10⁻³ | 6.20·10⁻³ | 0.193 | 0.202 |
| 0.40 | 3.3·10⁻³ | 1.24·10⁻² | 0.264 | 0.280 |
| 0.60 | 5.2·10⁻³ | 1.86·10⁻² | 0.282 | 0.313 |
The two independent estimates of T agree to 10%, and T(γ) has log-log
slope **0.640**, so the decomposition predicts d ∼ γ^{1.64} against the
directly measured **γ^{1.72}** — it closes.

**What that leaves, and why it is the right shape.** The lower bound now
factors into three pieces with different characters:
  (i) R = 3.0% — a Θ(1) hitting probability for the RING-FREE plant,
      which is exactly the object Lemma J's two-action steering bounds
      below, with no γ and no exponential;
  (ii) ρ(π) ≈ 1 per rad — a one-dimensional density for the ring-free
      first-arrival angle. Bounding a marginal density below is the
      tractable form of the local-CLT idea, and it is γ-free;
  (iii) T(γ) ∼ γ^{0.64} — the throughput, which is where the geometry of
      crossing a 1.5-thick band inside an arc of width γ·r lives.
So T3's remaining analytic content is (iii) alone: the other two factors
are γ-independent ring-free quantities. And (iii) is not circular — it
conditions on arrival IN the channel, an event defined by the geometry
rather than by the outcome.

**A γ² lower bound, calibrated (2026-07-27).** Taking T(γ) ≥ c₁γ with
c₁ = min over the grid of T/γ = 0.4695 (T is concave, so the smallest
ratio is the safe one) gives
  **d(γ) ≥ R·ρ(π)·c₁·γ² = 0.01456·γ²**,
which holds at every measured gap with slack 1.0× to 2.6× (exact at
γ = 0.6, where c₁ is attained). This is the first lower bound on d of the
right ORDER — γ² against the measured γ^1.72 — and it is *measured*, not
proved: c₁ is fitted. Evidence label *measured*, unit rollout,
`results/t3_reach_density_throughput.json`.

**The kinematic derivation of c₁, with the constant derived rather than
guessed.** The crossing is BALLISTIC in the tangential direction: the
drag time constant is 1/drag = 33 steps while the crossing takes k ≈ 9
(measured median 8–9 steps, from v_rad ≈ 1.5 and a 1.5-thick band), so
the arrival tangential velocity PERSISTS through the crossing and the
tangential travel is ≈ |v_tan|·k·dt. Survival inside the arc of
half-width r·γ/2 therefore requires
  **|v_tan| ≤ r·γ/(2·k·dt) ≈ 2.2·γ** ,
and since |v_tan|'s density at 0 is bounded below, P(that) ≥ 2.2γ·f(0),
giving T ∝ γ and hence c₁.
*Measured* (200 000 rollouts per gap; unit = channel arrival):
| γ | arrivals | threshold 2.2γ | P(satisfied) | non-freeze fraction | f(0) |
|---|---|---|---|---|---|
| 0.1 | 594 | 0.222 | 0.251 | 0.288 | 1.044 |
| 0.2 | 1184 | 0.444 | 0.498 | 0.473 | 1.157 |
| 0.4 | 2332 | 0.889 | 0.797 | 0.614 | 1.184 |
| 0.6 | 3352 | 1.333 | 0.927 | 0.698 | 1.104 |
The criterion tracks the non-freeze fraction across the range (0.25 vs
0.29, 0.50 vs 0.47, 0.80 vs 0.61, 0.93 vs 0.70 — over-predicting at wide
gaps, where the ballistic approximation degrades as the crossing has room
to turn), and **f(0) ≈ 1.1 independent of γ**, which is what makes the
bound linear in γ.

*A failure mode of the earlier test, for the record.* An initial version
of this criterion used the threshold 6.7γ and appeared refuted: it was
satisfied by 100% of arrivals at γ ≥ 0.4 while T stayed at 0.28. The
threshold was 3× too loose because it used the free-flight speed rather
than the arrival's v_rad ≈ 1.5 to set the crossing time k. With k derived
from the measured v_rad the criterion is informative, so the mechanism was
never the problem.

**How arrivals actually fail** (200 000 rollouts per gap; unit = channel
arrival) — this is what identifies the corridor as the binding constraint:
| γ | entered | froze | turned back | horizon |
|---|---|---|---|---|
| 0.2 | 0.202 | **0.527** | 0.014 | 0.258 |
| 0.6 | 0.313 | **0.302** | 0.023 | 0.362 |
Freezing on the band is the dominant failure and the only strongly
γ-dependent one (0.527 → 0.302), turning back is negligible (1–2%), and
the horizon accounts for a further 26–36% because the crossing needs
≈ 9 of the 80 steps and arrivals are late. The tangential travel during a
successful crossing has median 0.227 against the arc bound 0.400 at
γ = 0.2, and 0.339 against 1.200 at γ = 0.6 — tight at the narrow gap,
slack at the wide one, exactly as the freeze fractions say.

Superseded measurement, kept because its threshold was wrong rather than
its variables:
| γ | arrivals | T | median \|v_tan\| | median v_rad | P(\|v_tan\| ≤ 6.7γ) | T given that |
|---|---|---|---|---|---|---|
| 0.1 | 594 | 0.115 | 0.441 | 1.505 | 0.707 | 0.155 |
| 0.2 | 1184 | 0.202 | 0.445 | 1.497 | 0.956 | 0.211 |
| 0.4 | 2332 | 0.280 | 0.470 | 1.494 | 0.9996 | 0.281 |
| 0.6 | 3352 | 0.313 | 0.514 | 1.474 | 1.000 | 0.313 |
The median tangential speed is ≈ 0.45 regardless of γ, and the 6.7γ
threshold is satisfied by 100% of arrivals at γ ≥ 0.4 — which is why that
threshold carries no information. The variables are right; the constant
was not.

**Lemma D (free-coordinate density lower bound).** Let Y = Y(a_1,…,a_h) be
a function of the actions, a_s ~ U(−a_max, a_max) independent, and fix a
designated step s. On the event that the equation Y = y has a root in a_s
with |a_s| < a_max while the other actions are held fixed,
  **f_Y(y) ≥ (1/(2a_max))·P(a root exists)/ sup|∂Y/∂a_s|** ,
by the change of variables f_Y(y) = E[(2a_max)^{-1}|∂Y/∂a_s|^{-1}] summed
over roots. Both of T3's remaining densities are instances.

*(i) f(0), the density of |v_tan| at 0 — PROVED.* Tangential velocity is
  v_tan = Σ_s w_s·sin(φ_s − θ),  w_s = gain·dt·β^{t−s},
so the LAST step enters with weight w = gain·dt = 0.3 exactly, and its
contribution is gain·dt·sin(φ − θ) with φ uniform: the arcsine law, whose
density 1/(π√(1−x²)) is **bounded below by 1/π on all of (−1,1)** — no
compactness caveat needed. Freeing that step,
  f(0) ≥ (1/(gain·dt))·(1/π)·P(|R| ≤ gain·dt),  R := v_tan − last term.
*Measured*: P(|R| ≤ 0.3) = 0.362 at γ = 0.2 and 0.325 at γ = 0.6, giving
  bound **f(0) ≥ 0.384 / 0.345**  against measured **1.157 / 1.104** —
valid at both gaps, loose by ≈ 3×. Evidence: *proved* (Lemma D with the
arcsine bound), with the range factor P(|R| ≤ 0.3) *measured*, unit
channel arrival, n = 1184 / 3352.

*(ii) ρ(π), the ring-free arrival-angle density — PROVED.* The arrival
angle is steerable by a single early action: measured |∂θ/∂a_0| at first
arrival has median 0.362 and 90th percentile 0.532 (n = 115 steerable
paths, i.e. those whose arrival step is unchanged by the perturbation).
Lemma D with a_max = 1 gives
  ρ(π) ≥ (1/2)/sup|∂θ/∂a_0| ≥ 0.5/0.532 = **0.940**
against measured **1.0167** — valid, and loose by only **1.1×**. The
sensitivity is what makes this work: one early action sweeps the arrival
angle over ≈ 1.1 rad, so the angle has a genuine density rather than
concentrating.

*Status of T3.* The bound d ≥ 0.0146·γ² has the right order, and every
factor now has a derivation:
| factor | value | status |
|---|---|---|
| R = P(ring-free reach) | 0.030 | measured; Θ(1), γ-free — the object Lemma J bounds |
| ρ(π) | 1.02/rad | **PROVED ≥ 0.94** (Lemma D), 1.1× loose |
| f(0) | 1.10–1.16 | **PROVED ≥ 0.35** (Lemma D + arcsine), 3× loose |
| T ≥ 2.2γ·f(0) − P(horizon) | — | derived (ballistic crossing) |
**The horizon term is an artifact of the bookkeeping, and vanishes.** It
appeared because R counts arrivals at any time while the crossing needs
k ≈ 9 further steps. Building the deadline into the reach factor removes
it: define
  **R′ := P(a ring-free rollout reaches r_out within h − k steps)**,
so every counted arrival has at least k steps left and the horizon
condition is satisfied by construction. Measured: R = 0.03020 and
R′ = **0.02118** (70.1% of R), so the correction is a factor 1.4 and the
term disappears rather than being bounded.

**R′ is bounded below by ISOTROPY (no density estimate needed).** For the
2D heading action the thrust is gain·(cos φ, sin φ) with φ = πa/a_max
uniform on [−π, π], so each thrust direction is **uniform on the circle**
and the displacement Z_t = dt²·Σ_s w_{t,s}T_s is a sum of independent
isotropic vectors — hence **isotropic itself** (the same structure as
Theorem T5-I). Two consequences, both exact rather than estimated: the
direction of Z_t is uniform, and it is INDEPENDENT of |Z_t|. Therefore,
with L = ‖c − x₀‖ = 12,
  R′ ≥ P(|Z_t| ∈ [L − r_out, L + r_out]) · min_{r ≤ L+r_out} (arcsin(r_out/r)/π)
     = P(|Z_t| ∈ [7, 17]) · arcsin(5/17)/π
for any single t ≤ h − k, since reaching the ball requires the
displacement to have both the right magnitude range and a direction
within the ball's angular half-width arcsin(r_out/r) of e.
*Measured* (200 000 ring-free rollouts; the angular factor is exact at
0.0950):
| t | median \|Z_t\| | P(\|Z_t\| ∈ [7,17]) | ⇒ R′ ≥ |
|---|---|---|---|
| 20 | 1.17 | 0.0000 | 0 |
| 40 | 2.58 | 0.0051 | 0.00048 |
| 60 | 3.91 | 0.1081 | 0.01027 |
| 71 | 4.59 | 0.2000 | **0.01900** |
against R′ = 0.02118 measured — **valid and loose by only 1.1×**, taking
the single best time t = h − k = 71. (Using several t would only improve
it, at the cost of a union-of-events argument.) The remaining measured
input is one scalar, P(|Z_{71}| ∈ [7, 17]) = 0.20, the magnitude
distribution of an isotropic sum — a one-dimensional radial law, and the
last quantity in the chain.

**Status of T3's lower bound.** Every factor of d ≥ C·γ² is now derived or
proved:
| factor | status |
|---|---|
| R′ (reach within the deadline) | **PROVED ≥ 0.019** by isotropy, 1.1× loose; one measured scalar (the radial law) |
| ρ(π) | **PROVED ≥ 0.94** (Lemma D), 1.1× loose |
| f(0) | **PROVED ≥ 0.35** (Lemma D + arcsine), 3× loose |
| T ≥ 2.2γ·f(0) | derived (ballistic crossing) |
| horizon term | **eliminated** (absorbed into R′) |
So the chain that began as "stochastic domination of post-divergence
occupation measures" has reduced to three elementary ingredients —
isotropy, the arcsine density, and a one-action steering derivative —
plus a single measured radial law. Nothing in it is an occupation
estimate.

**An intuition about that constant, REFUTED (2026-07-26).** The natural
hope was that a freeze HANDICAPS entry — Lemma S says the freeze zeroes
the velocity, so the next landing creeps 0.03 and the trajectory has to
rebuild speed before it can thread the channel; on that reading
P(enter | froze) would be well below P(enter) and c small for kinematic
reasons. Measured (40 000 rollouts per gap) it is the opposite:
  γ = 0.2: P(enter) = 0.00140, P(enter | froze first) = 0.00805 — **5.8×**
  γ = 0.6: 0.00580 vs 0.02130 — **3.7×**
  γ = 1.2: 0.00960 vs 0.04624 — **4.8×**
Freezing does not hinder entry, it SELECTS for it: a trajectory that has
touched the band is one that reached the ring's neighbourhood, which is
a prerequisite for threading the channel. The selection effect dominates
the kinematic handicap by nearly an order of magnitude.

**A factorisation that is CIRCULAR.** By Bayes
  c(γ) = f/r_int = P(froze | entered) = r(γ) · κ(γ),
  κ(γ) := P(enter | froze first)/P(enter)  — the freeze BOOST.
"Prove κ ≤ 32" is not a target: the only free bound on κ is κ ≤ 1/r_int,
which returns c ≤ r/r_int, precisely the bound already available. The
factorisation renames the difficulty rather than reducing it.

**A partial mechanism, measured (2026-07-26).** Where DO funnel entries
freeze? Over 30 000 rollouts per gap, the angular distance |θ − π| from
the first freeze to the channel centre:
  γ = 0.2: funnel entries **0.092** rad vs non-entering freezes 0.272 —
    three times closer to the mouth;
  γ = 0.6: 0.296 vs 0.384;  γ = 1.2: 0.577 vs 0.594 — the gap closes.
Two readings. (i) Funnel entries are trajectories that froze essentially
AT the channel mouth and then threaded it, which is why the freeze
"boosts" entry: it is a proxy for arriving at the right place. (ii) The
non-entering medians track γ/2 (0.1 / 0.3 / 0.6) because a freeze cannot
occur inside the channel, so all freezes pile up against its edge — and
once the channel is wide, "at the edge" and "at the mouth" coincide,
which is why the discriminating power vanishes by γ = 1.2. So mouth
proximity explains the funnel at narrow gaps only. It is a partial
mechanism and we label it as such rather than extrapolating it.

## T7 (first half) — infinite censoring artifacts characterized and made
## DECIDABLE (2026-07-25). Second half and stability: see below; T7 is
## CLOSED.

Setting. Finite cloud X ⊂ ℝ², censor set F of forbidden (unordered) point
pairs — here: edges properly crossed by a certified-free trajectory
segment (`ring2d_censored_filtration.py`, `_crosses` with margin δ ≥ 0).
The censored VR filtration VR_F(X; s) = the flag complex on edges
{‖p−q‖ ≤ s} \ F. It is a filtration in s, and for s ≥ diam(X) it is
CONSTANT, equal to Cl(G_F) := the flag complex of the censor-complement
graph G_F = (X, all pairs ∉ F).

**Proposition C1 (characterization + decidability of infinite bars).**
The infinite H_k bars of VR_F are in bijection with a basis of
H_k(Cl(G_F)). In particular: (a) with F = ∅ the limit is the full
simplex, so the PLAIN Rips filtration has no infinite H₁ bars — the
INFINITUDE of any censored bar is caused by the censor (though the class
it carries may be genuine: see the gap-0 cells below); (b) whether a
given (X, F) has infinite bars is DECIDABLE by one finite computation
(H₁ of Cl(G_F)); "this censored sensor reading has no never-fillable
cycles" is a per-sample machine-checkable CERTIFICATE, not a hope.
*Proof.* The filtration stabilizes at Cl(G_F), so classes alive at all
scales are exactly the classes of the limit complex; F = ∅ gives the
(2·diam)-cone. ∎

**Proposition C2 (the minimal model: a never-fillable cycle).**
Let x₁…x₄ be an allowed 4-cycle (consecutive pairs ∉ F) whose two
diagonals ∈ F, with [x₁x₂x₃x₄] ≠ 0 in H₁(Cl(G_F)) (for the isolated
quadrilateral, Cl(G_F) IS the 4-cycle graph and H₁ = ℤ). Then VR_F has
an infinite H₁ bar born ≤ the longest side.
(Machine-checked: `test_t7_quadrilateral_minimal_model`.)

**Proposition C3 (censor monotonicity gives a bifiltration, NOT
monotone artifacts).** Nested censors F ⊆ F′ give nested limit
complexes Cl(G_{F′}) ⊆ Cl(G_F) — (scale, censor) is a bifiltration —
but H₁ of the limit is NOT monotone in the censor: removing edges can
both create cycles (by removing fills) and destroy them (by removing
the cycle's own edges). So there is no "safe censor-strength" theorem;
each censor needs its own C1 certificate. *Measured directly:* the
three nested censors clearance-0.3 ⊂ v1 ⊂ proximity-0.3 produce
0 / 4 / 0 infinite-bar cells on the same 25 clouds.

**Certificate run — the finding INVERTS the historical note.**
`scripts/t7_infinite_bar_certificate.py` on the committed
censored-filtration cells (γ ∈ {0, 0.6, 1.2, 1.8, 2.4} × seeds
10000–50000, inside evidence):
  - **v1 itself has infinite H₁ bars in 4/25 cells** — the historical
    comment attributing infinite bars to the margin refinement is
    corrected: the margin (clearance-0.3) and proximity-0.3 variants
    have 0/25.
  - The 4 cells are exactly interpretable: the 3 gap-0 cells with an
    infinite bar are precisely the committed run's gap-0 β̂₁ = 1
    readings (the TRUE loop, whose fills cross the certified-free hole
    and are censored — infinite persistence is the estimator saying
    "this loop encloses certified-free space", the correct answer with
    infinite confidence); the 4th is gap 0.6 seed 40000 — the SINGLE
    specificity failure of the 19/20 result, now DIAGNOSED: it is not a
    near-threshold finite bar but a structural C2-type never-fillable
    cycle (the censor missed the closing chord and censored its fills).
  - The margin-0.3 rejection reason is also corrected by measurement:
    it repairs the gap-0 false negatives (5/5) but RESTORES THE BRIDGE
    at γ = 0.6 (5/5 false loops, all finite) — it was rightly rejected,
    for specificity, not for infinite bars.
The two-sided conclusion for the estimator problem: infinite bars under
edge-censoring are (a) per-sample decidable (C1), (b) semantically
AMBIVALENT — the same mechanism encodes the true enclosure at γ = 0 and
the lone false positive at γ = 0.6 — which is the sharpest argument yet
that edge deletion is the wrong primitive and the principled object is
RELATIVE homology of contact w.r.t. certified-free space. That
estimator's formulation and stability theorem remain the OPEN second
half of T7.

## T7 (second half) — the relative estimator: formulated, two structural
## propositions proved, discrimination measured (2026-07-25)

The censoring pathology (infinite bars) came from deleting edges, which
leaves a limit complex that is not a cone. The principled replacement
uses the pair (K, L) = (VR(X ∪ Y; s), VR(Y; s)) with X the contact cloud
and Y the certified-free evidence, and reads the relative group
H₁(K, L). Two structural facts make it the right object.

**Proposition R1 (no infinite bars, by construction).** For s ≥ diam both
K_s and L_s are full simplices, so H₁(K_s, L_s) = 0: every relative bar
is finite. Edge censoring admits infinite bars precisely because its
limit complex is Cl(G_F) ≠ full (Prop C1); the relative construction
removes the pathology rather than certifying its absence per sample.
(Machine-checked in every cell run below and asserted in the estimator.)

**Proposition R2 (the estimator is a union-find).** The long exact
sequence of the pair gives
  H₁(K) → H₁(K, L) → H₀(L) → H₀(K),
so rank H₁(K, L) = rank(im H₁(K)) + rank ker(H₀(L) → H₀(K)); when
H₁(K) = 0 it equals rank ker(H₀(L) → H₀(K)) exactly, and lower-bounds it
otherwise. That kernel rank is
  #components of VR(Y; s) − #components of VR(X ∪ Y; s) that contain a
  point of Y,
i.e. **the number of certified-free components that the contact evidence
glues together** — computable by two incremental union-finds, no matrix
reduction. Implementation: `tda.free_merge_persistence`.

**The free evidence is PATHS, not a cloud (a refuted instantiation).**
Feeding Y as a flat point cloud makes the estimator report separation
almost everywhere, including wide-open channels (measured: rel β̂₁ ≥ 1 at
γ = 1.8, worse than plain Rips). Diagnosis: the contact cloud is dense on
a curve while the free cloud is a sparse 2-D scatter, so contact points
glue free components purely by DENSITY MISMATCH. The fix is not a
parameter but the right object: a free trajectory certifies passage
between its own consecutive samples, so Y enters as polylines whose
consecutive samples are joined at scale 0. (A useful corollary: path
subsampling is lossless for the connectivity certificate, unlike
point-cloud subsampling.) With paths, synthetic discrimination is
perfect: **12/12** — β̂₁^rel = 1 on the closed ring and 0 at
γ ∈ {0.6, 1.2, 1.8}, where plain Rips reports the spurious loop.

**Measured on the instrument** (`scripts/t7_relative_estimator.py`,
5 gaps × 5 seeds × 2 evidence arms):

| γ | plain β̂₁ (correct/5) | rel β̂₁ (correct/5) |
|---|---|---|
| 0.0 | 5/5 | 0/5 (one-sided), 1/5 (two-sided) |
| 0.6 | 0/5 | 5/5 |
| 1.2 | 0/5 | 5/5 |
| 1.8 | 4/5 | 5/5 |
| 2.4 | 5/5 | 5/5 |

At every γ > 0 — the whole regime where the pre-registered detector
fails — the relative estimator is **20/20** against plain Rips's 9/20,
with no infinite bars and no censoring. At γ = 0 it does not fire, for
two different reasons that must not be conflated:
  (a) *one-sided evidence: not a defect but the gauge theorem.* With
inside starts the interior is reach-null, so no free evidence exists
outside the ring. The estimator answers "how many certified-free
components does the contact set separate?", and with one side sampled
the answer is vacuously zero. Proposition 1's quotient says exactly this:
beyond the reachable set there is nothing to identify. Plain β̂₁ scores
5/5 here by answering a DIFFERENT question — the SHAPE of the cloud, not
the SEPARATION it induces — and the two questions come apart precisely
in the gauge region.
  (b) *two-sided evidence: NOT a calibration gap — a structural limit of
freeze evidence.* See Proposition R4.

**Proposition R4 (freeze evidence cannot resolve enclosure, and more of
it makes things worse).** Under freeze-on-entry the contact cloud
concentrates on two thin shells at the band's faces and never samples
its interior. Mechanism — it is Lemma S again: a freeze resets the
velocity to zero, and from rest the next proposed landing moves only
R_L = gain·dt² = 0.03, so after the first contact the trajectory creeps
along the face instead of penetrating. Consequently, writing w =
r_out − r_in for the band thickness and δ for the shell thickness:
  • free-direct connection scale = w exactly (inside free reaches r_in,
    outside free reaches r_out);
  • contact-mediated connection scale ≥ w − 2δ;
so the relative bar has length ≤ 2δ, set by the shells and NOT by the
sample size, while τ = 3 × median contact spacing GROWS with the sample
(more contacts spread the deduped-and-capped cloud over more of each
face). The estimator therefore degrades with more evidence.
*Measured* (γ = 0, two-faced evidence via a start distribution reaching
both faces, 40/120/320 rollouts per arm): shells saturate at
r ∈ [3.50, 3.71] and [4.83, 5.00] (δ ≈ 0.21, 0.17, unchanged from 120 to
320); bar length 0.160 / 0.197 / 0.253 against τ = 0.183 / 0.324 /
0.439. The bar is sub-threshold at every sample size and the gap widens.
*Consequence.* No threshold calibration recovers γ = 0: the obstruction
is in the EVIDENCE, not the rule. What would fix it is evidence that
enters the band at speed on both faces — which freeze semantics
structurally prevents after the first contact. This is a third, sharper
form of the paper's recurring point that the sensor's limits are
mechanical rather than statistical.

Note the pleasing closure: the same one-step landing law (Lemma S) that
made T4's continuity modulus explicit is what caps T7's estimator here.

**Proposition R5 (stability of the relative estimator).** Let (X, Y) and
(X′, Y′) be two evidence sets with d_H(X, X′) ≤ ε and d_H(Y, Y′) ≤ ε
(Hausdorff), and suppose the free evidence is given as point sets (no
path edges) or, for path input, that the paths correspond in pairs with
d_H ≤ ε vertex-wise along matched paths. Then the relative persistence
modules of (VR(X ∪ Y; ·), VR(Y; ·)) and (VR(X′ ∪ Y′; ·), VR(Y′; ·)) are
2ε-interleaved, so their diagrams satisfy
  d_bottleneck ≤ 2ε.
*Proof.* Choose π: X ∪ Y → X′ ∪ Y′ sending each point to a nearest point
of the other set, taking Y into Y′ and X into X′ (possible separately on
each part by the two Hausdorff hypotheses). For p, q at distance ≤ s,
‖π(p) − π(q)‖ ≤ s + 2ε, so π induces simplicial maps VR(X ∪ Y; s) →
VR(X′ ∪ Y′; s + 2ε) that carry VR(Y; s) into VR(Y′; s + 2ε): a map of
PAIRS. With path input, matched path edges (present at scale 0 on both
sides) are preserved because π matches paths, so π stays simplicial on
the augmented complexes. Symmetrically for π′. The composites π′π and
ππ′ are contiguous to the inclusions (any point and its double image lie
within 2ε, so images of a simplex together with the simplex span a
simplex at the shifted scale), hence induce the interleaving identities
on relative homology, which is functorial for maps of pairs. Algebraic
stability for interleaved modules (Chazal et al.) gives the bottleneck
bound. ∎
**Why the path clause is necessary (a counterexample at ε = 0).** The
clause is not a technical convenience; without it R5 is FALSE. Take one
fixed point set Y and two different groupings of it into paths: in P the
coarse samples along a channel traversal form ONE path, in P′ the same
points are singletons. The point sets are IDENTICAL, so d_H = 0 and any
point-set-only hypothesis is satisfied with ε = 0, which would force
d_bottleneck = 0. Measured (`test_r5_path_structure_is_necessary`,
coarse bridge of spacing 1.8): P yields one bar, P′ yields two, and the
unmatched bar puts **d_bottleneck ≥ 0.317 while 2ε = 0**. So the
hypothesis cannot be weakened to Hausdorff closeness of the points.

*Why this is the right situation rather than a defect.* The estimator's
entire job is to decide whether a certified free TRAVERSAL exists — that
is how it separates γ = 0 from γ > 0. Traversal-existence is a property
of the trajectories, not of the point cloud: the same positions,
regrouped, describe either "one path crossed the channel" or "some
points happened to lie near the channel". Any estimator that answers the
question therefore MUST be discontinuous in the point-set metric; a
point-set-stable estimator provably could not do the job (it would have
to give the same answer to both groupings above). R5 accordingly states
stability in the metric the input actually lives in — perturbation of
the trajectories, which are the certificates — and the counterexample is
what shows that choice is forced, not chosen for convenience.

Status: **T7 CLOSED as far as the evidence allows.** Formulation resolved
(relative pair + Props R1/R2; point-cloud input refuted, paths correct),
discrimination established at γ > 0 (20/20 vs 9/20), and the γ = 0 miss
resolved into two proved obstructions rather than an open task: gauge
(Prop 1) for one-sided evidence, and Proposition R4's shell geometry for
two-sided. Stability is Proposition R5 (2ε-interleaving of pairs, with
the honest caveat that the perturbation must respect the path
structure). **T7 is CLOSED.**

## T8 — the linking dichotomy, RESOLVED (2026-07-25): the unconditional
## bound is REFUTED with witnesses, the conditional bound is proved

Setting (TubeField3D). Core circle K = {x = c_x, dyz = R_c} with
dyz(p) = ‖(p_y, p_z) − core_yz‖, defaults c_x = 8, R_c = core_radius = 2,
core_yz = (o, 0). Tube T = {g ≤ ρ_t}, g(p) = dist(p, K) =
hypot(p_x − c_x, dyz(p) − R_c), ρ_t = tube_radius = 1; g is 1-Lipschitz
(distance to a set). Spanning disc D = {x = c_x, dyz ≤ R_c}, oriented by
+x; K = ∂D. Plant: ‖v_{t+1}‖ ≤ (1 − drag·dt)‖v_t‖ + gain·dt with
‖v₀‖ = 0, so every step (real or imagined) has length ≤ Δ := (gain/drag)·dt
= 1.0 — the same step bound as the ring (Lemma 2's hypothesis). Write
m := ρ_t − Δ/2 = 1/2 (the clearance margin).

**Lemma X (discrete clearance — the metric primitive, any dimension, any
core set).** If a polygonal path with steps ≤ Δ has an interpolation point
q with g(q) ≤ ρ_t − Δ/2, then some LANDING lies in the closed tube
{g ≤ ρ_t}.
*Proof.* q lies on a segment of length ≤ Δ, so its nearer endpoint p has
‖p − q‖ ≤ Δ/2; g is 1-Lipschitz, so g(p) ≤ g(q) + Δ/2 ≤ ρ_t. ∎

**Lemma Y (hole gate).** If no landing of the path lies in T, then every
intersection of its interpolation with the spanning disc D lies in the
open clearance sub-disc D_m := {x = c_x, dyz < R_c − m}.
*Proof.* An intersection q ∈ D has x = c_x and dyz(q) ≤ R_c, so
g(q) = R_c − dyz(q). If dyz(q) ≥ R_c − m then g(q) ≤ m = ρ_t − Δ/2 and
Lemma X puts a landing in T — contradiction. ∎

**Definition (threading number = path-level linking).** For a polygonal
path π with endpoints off the plane {x = c_x} that meets D transversally
in finitely many segment-interior points (generic; perturb by < min-gap
otherwise), thread(π) := the signed count of crossings of D (sign = sign
of the x-increment). Closing π by any arc in the far region
{dyz ≥ R_c + ρ_t + 1} ∪ {far x} that avoids D and T yields a loop L with
lk(L, K) = thread(π): D is a Seifert surface for K and the far arc
crosses the plane only outside D. thread is therefore the linking number
of the plan with the mode's core, needing no closure choice.
(Machine-checked against the Gauss linking integral:
`scripts/t8_linking_dichotomy.py`.)

**Theorem T8 (linking dichotomy).**
(a) *Gate:* any plan (imagined path, steps ≤ Δ) with thread ≠ 0 either
has an imagined landing in T — under blind imagination, a QUERY on the
disagreement region E = T × actions — or crosses the clearance disc D_m.
Hence the conditional query bound: μ_query ≥ 1 for every plan with
thread(π) ≠ 0 that avoids D_m. (Proof: thread ≠ 0 forces a D-crossing;
Lemma Y.)
(b) *The unconditional bound is FALSE — witnesses in both classes:* both
linking classes contain landing-free (hence query-free) plans from the
start region to B(c, r₀), at the aligned AND at the offset geometry:
  - thread = 1, aligned (o = 0): the x-axis path (t, 0, 0) has dyz ≡ 0,
    g(t) = hypot(t − 8, 2) ≥ 2 > ρ_t, and crosses D at (8, 0, 0) ∈ D_m;
  - thread = 1, offset (o = 1.5): route (0,0,0) → (0, 1.5, 0) →
    (12, 1.5, 0) → (12, 0, 0); on the east leg dyz ≡ 0 relative to the
    core center, g = hypot(t − 8, 2) ≥ 2; crossing at (8, 1.5, 0) = the
    hole's center, g = 2;
  - thread = 0 (around): (0,0,0) → (0, 6, 0) → (12, 6, 0) → (12, 0, 0);
    at the plane crossing (8, 6, 0), dyz − R_c ≥ 2.5 (offset) so
    g ≥ 2.5, and the crossing is outside D.
  Subdivide each route into steps ≤ Δ: all landings keep g > ρ_t. So NO
  positive lower bound on query mass follows from topology alone —
  "obstruction is path-relative" is now a THEOREM about the instrument,
  not only the measured 0.019-vs-0.898 dichotomy; even at the dangerous
  offset a query-free threading plan of trivial extra length exists, so
  the measured 0.898 is a property of the planner's SEARCH (random
  shooting concentrates near the straight corridor), not of the geometry
  of feasible plans.
(c) *Real dynamics:* real trajectories never land in T (freeze semantics:
a proposed landing in T freezes at the previous position — the same
argument that makes the ring band reach-null in position), and real steps
obey the same Δ; hence by Lemma Y every real trajectory that links the
core threads D_m: under the true dynamics, THE HOLE IS THE ONLY GATE to
the winding class. *Measured non-vacuously* (east-biased action arm, 300
episodes × 80 steps per config): 0 real positions in the tube, 368 plane
crossings all through the clearance disc, and the real linking rate drops
0.507 → 0.283 when the offset moves the hole off the flow — the knob's
mechanism seen directly in the trajectories' homology classes.
(d) *Corridor corollary — where Prop 4 survives:* assume (RG3) + (C3) and
that every candidate's imagined path lies within Hausdorff distance ε of
the straight segment start → phantom. The straight segment (t, 0, 0) has
constant dyz = o, so min_t g = |o − R_c| (attained at t = c_x). If
|o − R_c| < ρ_t − Δ/2 − ε, every candidate — in particular the argmax —
has an interpolation point with g < ρ_t − Δ/2, so by Lemma X it queries:
μ_query = 1. The mechanism run's offset o = 1.5 gives min g = 0.5 =
ρ_t − Δ/2 EXACTLY — the registered configuration sits at the degenerate
boundary of the corollary (planner paths dip below the straight line's
clearance, which is why contact = 0.94 is measured); any o with
|o − R_c| < 0.5, e.g. o = 1.75, satisfies the strict hypothesis for
ε < 0.5 − |o − R_c|.

**What replaces "linking lower-bounds query mass".** The correct
statement has the same shape as the paper's two-grades remark: the metric
crossing (Lemma 2) forced queries because the mode SEPARATED the lure —
for the tube, the winding class is gated by the hole (Lemma Y), and
queries are forced exactly on plans that link WITHOUT threading (T8(a)),
a conditional statement whose unconditional strengthening is refuted by
explicit witnesses (T8(b)). Topology relocates the obstruction from
"reaching the lure" to "which homotopy class the plan uses"; it cannot
force the planner into the dangerous class — that choice is the
planner's, which is the tube row's measured content.
