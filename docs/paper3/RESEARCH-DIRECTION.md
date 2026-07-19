# Paper 3 — The topology of the critical region (research direction)

Status: **shaping** (started 2026-07-19). This document is the canonical note for
the third paper; earlier fragments of this idea lived only in conversation/agent
memory, never in the repo. Branch: `claude/paper-tres-topology-4w813y`.

**Dependency.** Paper 3 builds directly on paper 2's continuous stack
(`src/cwm/continuous/` — envs, contract, gate, MPC/CEM, mitigation, synthesis
harness), which lives on the unmerged branch
`claude/continuous-setting-feasibility-wktp6b`. Paper-3 experiments start after
that branch lands; until then this document is design-only. Nothing here
modifies paper 1 or paper 2.

## 1. Where the ring idea comes from — and why it is NOT paper 2's

Paper 2 ends on a geometry-dependence finding: LLM repair-from-data collapses
when the omitted hybrid mode's boundary goes from a 1D flat clamp (82/82
repaired) to a 2D *circular* disc (0/76; the synthesizer reduces the disc to a
half-plane — dimensional reduction). Its §10 leaves "other geometries" open.

The tempting move is to add an **annulus mode** (a ring: non-trivial H₁ in the
plane) as one more paper-2 arm. Decision (2026-07-19, re-reviewed the same day
on content grounds after Appendix A landed): **no — the annulus opens paper 3.**
Rationale, recorded so it isn't relitigated. The criterion is CONTENT — does the
result test/sharpen paper 2's claims, or state new ones? — never the state of
paper 2's files (PDFs/tarballs are regenerated continuously and certify nothing):

- **The annulus does not test paper 2's claims; it states new ones.** Paper 2's
  geometry-dependence claim is already carried by the minimal contrast — flat 1D
  clamp (82/82 repaired) vs curved 2D disc (0/76), *both contractible* — and a
  0/N floor cannot be strengthened by a harder region. At γ = 0 the annulus
  exits paper 2's frame entirely: the enclosed region has r = 0 exactly, the
  danger law's endpoint degenerates, and the operative statements (gate
  quotient, crossing lower bounds, reach-null unidentifiability,
  topology-informed repair) are new propositions, not instances of paper 2's.
  New claims ⇒ new paper.
- **The annulus is also the wrong *ablation* for paper 2's own open question.**
  What would isolate the cause of the 0/76 *inside* paper 2 is a fixed-topology
  contrast — e.g. an axis-aligned square patch (flat edges, contractible, lower
  descriptive complexity than a circle), separating curvature from descriptive
  complexity (the two-axes note of Appendix A.2). The annulus varies curvature
  AND topology at once: useless as a paper-2 ablation, exactly right as paper
  3's opening subject.
- Paper 2 already climbed the first rung silently: two disjoint patches means
  β₀ = 2, with per-mode identifiability and partial-repair machinery built. The
  annulus is the β₁ rung. Paper 3 makes the ladder explicit and keeps climbing.
- **Content-based dependency that DOES belong to paper 2:** paper 3's rung-1
  datum is the 0/76, and paper 2's §10 leaves its two obvious confounds open
  (richer prompting, larger iteration budgets). Closing those cells is paper-2
  content and should happen there, before paper 3's synthesis arm runs — see
  the §6 risk entry.

## 2. The reframe: from geometry to topology of the critical region

Papers 1–2 treat the critical region R ⊂ S×A purely as a *measurable set*: the
danger law `play_cost × (1−r)^N` sees only its sampling mass r and its
consequence. Paper 2's synthesis arms revealed that what the *repair loop* can
do depends on R's **shape**. Paper 3's thesis candidate:

> What a sample-driven synthesis-and-verification loop can learn, certify, and
> repair about a hybrid mode is governed by the **topology of the mode region
> relative to reachability** — its Betti numbers, its codimension, and which of
> its boundary components the reachable set actually touches — not by its
> measure alone.

The ladder (each rung is an instrument class, first three already exist):

| rung | region | invariant | status |
|------|--------|-----------|--------|
| 0 | half-space (CartWall, PendStop) | contractible, flat | paper 2: repaired 82/82 |
| 1 | disc (PatchField2D) | contractible, curved | paper 2: repaired 0/76 |
| 1' | two discs | β₀ = 2 | paper 2: partial-repair machinery, 0/66 |
| 2 | **annulus (RingField2D)** | **β₁ = 1** | **implemented 2026-07-19** (`envs.py`; Props 1–3 in `THEORY.md`; mechanism tests + calibration) |
| 2' | C-shape (ring with gap) | contractible, non-convex | the *topological knob*: the same class, `gap > 0` |
| 3 | shells/tori in d ≥ 3 | β_{d−1}, codimension | paper 3 multidimensional arm — full n-dim program in §8 |

## 3. The opening instrument: RingField2D

**Status: implemented (2026-07-19)** — `src/cwm/continuous/envs.py`
(`RingField2D`, `filled_of`, `blind_of`), mechanism tests in
`tests/test_ring2d.py` (reach-null and the bitwise Prop-3 equivalence pass),
formal statements in `docs/paper3/THEORY.md`, calibration in
`scripts/continuous_ring2d.py`. The working branch carries the paper-2
continuous stack by merge, so nothing here waits for the paper-2 → main merge.

Same 4D state and heading integrator as PatchField2D (reuse the class shape,
the frozen-default discipline, and the n-component machinery). The mode region
is an annulus centered on the phantom lode:

- mode: freeze-at-previous-position if `R_in ≤ dist((x',y'), c) ≤ R_out`,
  with the phantom lode strictly inside the inner disc.
- knobs: **thickness** `R_out − R_in` (the rarity knob, as before); **gap
  angle** `γ` (an angular sector removed from the ring — the topological knob:
  `γ = 0` gives β₁ = 1, any `γ > 0` is contractible); **start placement**
  (outside / inside the ring — inside makes the inner boundary reachable).

**Calibration (2026-07-19, `results/continuous_ring2d.json`, 600 rollouts +
20 paired MPC episodes per gap):**

| gap | r | r_int | J_truth | J_blind | pc_blind | pc_filled |
|-----|--------|--------|---------|---------|----------|-----------|
| 0.0 | 0.0417 | 0.0000 | 17.32 | 0.14 | 0.998 | 0.000 |
| 0.6 | 0.0283 | 0.0067 | 42.32 | 41.37 | 0.023 | 0.340 |
| 1.2 | 0.0150 | 0.0100 | 41.65 | 41.37 | 0.007 | 0.222 |

Both theorem checks land exactly: r_int(0) = 0 (Lemma 2) and
play_cost(filled) = 0.000 at gap 0 → 0.34 once the channel opens (Prop 3's
knob-through-the-regimes, measured). **Design finding (recorded, defaults not
silently changed):** with the channel FACING the start (`gap_center = π`),
the blind planner's straight-line approach threads the channel by
construction, so pc_blind collapses at gap > 0 (0.023) and the middle
"rare ∧ dangerous" regime degenerates. The mechanism arm needs the hidden
channel — `gap_center = 0` (east, away from the start): truth navigates
around; the blind planner still hits the west wall. Whether wrongness is
dangerous depends on whether the topology forces the error ONTO the
planner's path — itself a mechanism datum, keep it in the paper. Also note
r(0) = 0.042 ⇒ (1−r)^40 ≈ 0.18: at N = 40 the identifiability event fires in
~18% of seeds — a workable synthesis regime without retuning.

Why this instrument is qualitatively new, not just harder:

**(a) The interior is reach-null, not reach-rare.** With `γ = 0` and start
outside, no trajectory of the *true* dynamics ever enters the inner disc: every
approach freezes at the outer boundary. The inner boundary and the interior have
sampling probability exactly **0** under every policy — not `(1−r)^N` small,
zero. Whatever a certified model says about the enclosed region is **pure
prior**, unfalsifiable by any gate of any size. Paper 2 met this as an anecdote
(Claude's phantom pendulum stop, certified because its sample was silent at
θ < −1.4); the annulus makes it *structural and designed-in*: an entire region,
with its own homology class of boundary, about which the sample says nothing in
principle.

**(b) Crossing arguments give topological lower bounds.** Any continuous
trajectory from the start component to the phantom lode must cross the ring
(Jordan/linking argument). So conditional on the planner steering toward the
phantom, the query-hit mass of the mode region is bounded below by a *crossing*
event, not estimated from measure. This complements paper 2's Proposition 3
(play_cost ≤ μ_query, an upper bound) with a topological route to **lower**
bounds on exploitation — the first provable piece that needs topology rather
than measure.

**(c) The gate quotient.** Candidate proposition, formalizing (a): fix the true
dynamics f and the reachable set 𝓡 of the gate policy from the initial
distribution. Any model f̂ agreeing with f on 𝓡 passes every sampling gate with
probability 1; the set of accepted-with-certainty models is exactly the set of
extensions of f|_𝓡, i.e. the gate certifies content only up to the quotient "=
on 𝓡". The unreachable complement is **gauge freedom**, and its size/topology is
an invariant of the instrument. On RingField2D the gauge region is an open disc
whose boundary circle carries the non-trivial class — the prior caveat of paper
2's Proposition 2 upgraded from a caveat to a measured, designed object. (Proof
core is easy; the value is the definition + the instrument that makes it
non-vacuous + the measurement of what different model families *put* there.)

**(d) The gap knob interpolates identifiability.** As γ > 0 opens, the interior
becomes reachable through a channel of tunable width: sampling mass of the
inner region moves continuously from 0, and the danger law should reappear as
the γ-parametrized limit. Prediction: the (1−r)^N phenomenology is the γ > 0
regime, and the γ = 0 endpoint is its degenerate, provably-blind limit. One
instrument, both worlds, one knob.

## 4. Experimental arms (design sketch, order matters)

1. **Mechanism arm (no LLM).** Hand-written truth + mode-blind and
   *wrong-topology* models (annulus-blind; annulus→disc, i.e. the model that
   also freezes the interior — the paper-2 "dimensional/topological reduction"
   written by hand). Measure: gate acceptance, play_cost, mitigation behavior.
   Note the disc-model twist: with γ = 0 and start outside, annulus vs disc is
   *play-equivalent* (the interior is never visited) — the wrong topology is
   both unfalsifiable AND harmless. With γ > 0 or start-inside episodes it
   becomes consequential. That three-way split (unfalsifiable+harmless /
   rare+dangerous / revealed+repairable) as a function of (γ, start) is the
   mechanism table of the paper.
2. **Synthesis arm.** Same protocol as paper 2 (N = 40, ε = 10⁻⁹, ≤5 refine
   iters, 20 seeds/cell, mini+large, cross-family spot-checks). Classification
   now includes *topological* type of the artifact's mode region (blind /
   half-plane / disc / annulus / other), by code inspection + probes seeded on
   both boundary components, logging **both** complexity axes per artifact —
   geometric (shape/curvature) and descriptive (AST) — since paper 2's
   "dimensional reduction" is a descriptive-complexity collapse, not a
   geometric one (Appendix A.2). Key question: does any family ever write a
   region with a hole from boundary-crossing data alone?
3. **Topology-informed repair (the constructive arm).** Persistent homology /
   clustering on the sample's *contact set* (the revealed boundary points)
   yields a topological summary ("contact points lie on a closed curve
   enclosing the target; β₁ = 1"). Feed the summary — not the answer — into the
   refine prompt. Does repair recover, the way 1D repair worked without help?
   This is TDA earning its keep inside the loop, and it is the natural fix for
   paper 2's probe limitation (probes only where the *true* mode fires; invented
   modes needed code inspection): probe placement itself becomes
   topology-driven.
   **Status 2026-07-19 — measurement half DONE:** from-scratch Rips
   persistence module (`src/cwm/continuous/tda.py`, ground-truth-tested) +
   contact-cloud probe. Finding (EXPERIMENTS.md): the contact set carries the
   topology of the REACHABLE boundary, not of the mode — from outside, ring
   and disc evidence are pathwise IDENTICAL (Lemma 2 corollary; paper 2's
   dimensional reduction is rational given its evidence) and β̂₁ stays 0 at
   any N; from inside, β̂₁ = 1 already at N = 40. So the summary the repair
   prompt can honestly receive is about ∂𝓡, and the LLM half of this arm
   (still gated on the paper-2 confound cells) should test BOTH summaries:
   the arc summary from outside (does it at least stop the half-plane
   reduction?) and the loop summary from inside.
4. **Multidimensional arm (the "heavy" part, scoped last).** Spherical shells
   S^{d−1} in d = 3..6 (state (x⃗, v⃗), same freeze semantics), solid torus in
   d = 3. Hypotheses to test, not assume: repair difficulty and artifact
   reduction track **codimension and Betti profile**, with "dimensional
   reduction" as the general failure mode (the synthesizer projects the region
   to lower descriptive complexity); the gate-quotient volume grows with
   enclosure. Boundary metrics normalized by **reach** τ(M) (Federer; Appendix
   A.1) rather than a single curvature scalar — the correct d ≥ 3
   generalization, and the scale that decides whether a sample can resolve
   inner vs outer boundary at all. Keep cells small; this arm exists to show
   the invariants organize the results, not to sweep every d.

## 5. What would be provable vs measured (paper-1/2 discipline)

- **Provable:** the gate quotient (§3c); crossing lower bounds on query-hit
  mass (§3b); exact reach-nullity of enclosed regions at γ = 0 and its
  γ-parametrized relaxation (continuity of r(γ), limits); transfer of the
  danger law verbatim (it is measure-theoretic — nothing to redo).
- **Measured:** everything about what synthesizers actually write in the gauge
  region and on the ladder (repair rates by rung, artifact topology classes,
  TDA-informed recovery, family differences). Keep the split explicit from day
  one, as in papers 1–2.

## 6. Honest risks, recorded before starting

- **The γ = 0 headline could be deflating:** unfalsifiable-but-harmless is a
  cute point, not a paper. The paper needs the *consequential* regimes (γ > 0
  channel, start-inside, multi-chamber navigation) to carry the danger story;
  design instruments so topology changes *play*, not only certifiability.
- **~~The 0/76 confounds~~ RESOLVED (2026-07-19, run locally on the paper-2
  branch):** 0/40 repair under the strongest joint treatment (region guidance
  + 3× budget, large+mini). The rung-1 datum stands UNCONDITIONED — and the
  mechanism sharpened in paper 3's favor: the guidance eliminated the
  half-plane reduction (artifacts now fit bounded 2D regions — rotated
  ellipses, rectangles, micro-disc unions) yet 0/40 write the true disc; they
  fit the hull of the observed pre-freeze crescent and 36/40 condition on the
  wrong variable (current position, not the landing). This is the
  evidence-equivalence corollary made empirical on the synthesis side:
  hull-fitting is the rational response to reachable-boundary-only evidence —
  the §4.3 arc/loop-summary experiment is now the directly indicated
  treatment. (Analysis in paper-2 EXPERIMENTS.md, 2026-07-19 entry.)
- **TDA at N = 40 is data-starved.** The contact set from 40 rollouts may be a
  handful of points on the outer boundary only. The TDA arm may need contact
  points pooled across refine iterations, or a larger-N sensor pass framed as
  deployment monitoring (which is legitimate: mitigation already watches every
  real step). Appendix A.1's Niyogi–Smale–Weinberger threshold makes this
  worry *computable* (a sample-density bound in units of reach below which β₁
  is unrecoverable), and A.2's active-boundary-learning direction is the
  designed answer to it.
- **Don't burn LLM cells before the mechanism arm freezes the design** —
  paper 2's discipline (prototype-validated frozen defaults) applies verbatim.
- **Scope creep is the known failure mode of "more topology".** The ladder ends
  at rung 3 for this paper; sheaves, configuration spaces, and moving
  boundaries are explicitly out.

## 7. Next steps

1. ~~Wait for the continuous stack~~ DONE another way (2026-07-19): the
   paper-2 branch is merged INTO this working branch, so prototyping runs
   here; the paper-2 → main merge remains paper 2's own step. Still pending
   on the paper-2 side and still gating THIS paper's LLM arm: the two §10
   confound cells + square-patch ablation
   (`docs/superpowers/plans/2026-07-19-disc-confounds-square-ablation.md`,
   LLM cells ready to run locally).
2. ~~Prototype RingField2D + calibration~~ DONE (2026-07-19): instrument,
   tests (reach-null, bitwise Prop-3), calibration script; frozen defaults
   center (12,0), r_in 3.5, r_out 5.0 (thickness 1.5 > max step 1.0 —
   Lemma 2's hypothesis with margin), gap_center π.
3. ~~Draft gate quotient + crossing bound~~ DONE (2026-07-19):
   `docs/paper3/THEORY.md` — Prop 1 (gate quotient), Lemma 2 (metric
   crossing), Prop 3 (unfalsifiable+harmless, proved AND confirmed bitwise),
   Prop 4 sketch (query lower bound; behavioral hypothesis to replace),
   r(γ) remark. The "is there a theorem here" question is answered yes.
4. ~~Mechanism arm~~ DONE (2026-07-19, ran directly — no plan doc needed):
   grid + readings in EXPERIMENTS.md "Paper 3" section. Landed: the
   three-regime walk; phantom-obstruction exploitation BELOW random
   (pc_fill 1.769 from inside); policy-relative reachability (hidden
   channel observationally identical to the closed ring); the
   aligned-channel degeneracy quantified.
5. ~~Tighten Prop 4 / r(γ)~~ DONE (2026-07-19): Prop 4 under (RG)+(C);
   γ-curves resolved into Props 5–9 + certificate (seed 50543) + scoped
   conjectures M1/M2 with the open estimate (KEY) isolated (THEORY.md).
   Open math, in order of value: (KEY); the hidden-channel steering
   witness; Prop 6's explicit density constant.
6. n-dimensional program: §8. First concrete step there: ShellField-n design
   note (action-interface decision) + the r(n) collapse measurement.
7. LLM synthesis arm: WAITS for the paper-2 confound cells (§6 first risk).

---

## 8. The n-dimensional program — and where algebraic topology is EARNED

*(Recorded 2026-07-19 from Javier's direction — this part of the paper-3 idea
("ir a más dimensiones — no solo 3 sino n en general; ver qué generaliza y
dónde tiene sentido empezar a usar topología algebraica de verdad") was
previously undocumented. Revisit and refine on every pass.)*

### 8.1 The instrument family in general n

State (x⃗, v⃗) ∈ ℝ²ⁿ, same drag/thrust integrator and freeze-at-previous
semantics. Modes are **tubular neighborhoods of thickness w around compact
embedded submanifolds M^k ⊂ ℝⁿ**; the 2D ladder is the special case n = 2
(half-line, point-disc, circle-annulus). The two structured rungs:

- **ShellField-n**: M = S^{n−1} (round sphere, k = n−1, separating). The
  direct generalization of RingField2D; everything in THEORY.md holds
  verbatim (Lemma 2 is dimension-free).
- **TubeField-3**: M = a circle (or a knot) in ℝ³, k = 1, codimension 2,
  NON-separating. The first rung whose analysis cannot be metric — see 8.3.

Knobs per rung: (n, k, embedding class [M], thickness w, gap γ where a
separating M gets a channel, start placement).

**Infrastructure cost to flag early:** the scalar heading action (one angle)
is 2D-specific. In ℝⁿ the action must parameterize a direction in S^{n−1}
(n−1 angles or an n-vector, renormalized). That touches the planner API
(mpc/cem sample scalar actions today) — an additive `action_dim` extension,
to be designed once and reused; do NOT bolt on per-instrument hacks.

### 8.2 What generalizes for free, and what changes quantitatively

Free (dimension-independent): the measure-theoretic core (danger law,
identifiability, gate quotient Prop 1), Lemma 2 for round shells (distance is
1-Lipschitz in every ℝⁿ), Prop 3's bitwise equivalence (same proof).

Changes with n (each a measurable mini-law, not an assumption):
- **Rarity collapses with n.** A random rollout's chance of reaching a far
  shell drops fast with dimension (drift-free directions multiply). Measure
  r(n) at fixed geometry: the danger regime becomes *automatic* in high n —
  the paper-1/2 threshold story gets an "n as the rarity knob" corollary.
- **TDA sample complexity blows up.** Niyogi–Smale–Weinberger density scales
  like (1/τ)^Θ(n); persistent-homology computation (Rips) grows steeply.
  Consequence: experiments live at n ≤ ~6; statements are for general n; the
  TDA-repair arm needs the NSW threshold *reported next to* each cell so
  "TDA failed" is never claimed where recovery was information-theoretically
  impossible (A.1).
- **Synthesizer artifact classes vs n.** Paper 2's dimensional reduction
  (disc → half-plane) presumably worsens; log the geometric + AST complexity
  axes per artifact (as in the 2D arms) and the *codimension* of the written
  region vs the true one.

### 8.3 Where algebraic topology is EARNED (the gating criterion — keep)

**Criterion (record, apply at every use):** a piece of algebraic-topology
machinery enters the paper only if it yields (a) a hypothesis or step in a
theorem that a bound actually uses, or (b) a measurement that organizes
experimental data. Otherwise it is notation. (THEORY.md's Lemma-2 honesty
note is the model: the round crossing bound is METRIC — raising n alone does
NOT earn homology; round shells in ℝ¹⁰⁰ are still a 1-Lipschitz argument.)

Ordered by how soon each is genuinely forced:

1. **Non-round separators (Jordan–Brouwer / Alexander duality).** The moment
   the separating mode is a topological (n−1)-sphere that is not a metric
   sphere — bent, star-shaped, wild — "inside" stops being definable by a
   distance and Lemma 2's proof dies. Jordan–Brouwer (or Alexander duality
   for general compact separators) is then the *existence statement for the
   gauge region itself*: Prop 1's 𝓖 is nonempty because H̃₀(complement) ≠ 0.
   First genuinely topological theorem slot: "crossing lemma for topological
   spheres with a step-size/reach condition" (reach τ(M) replaces thickness —
   A.1 Federer).
2. **Non-separating modes (linking/winding).** TubeField-3: the complement is
   connected — no trapped interior, Prop 1's gauge region is (essentially)
   empty, certifiability is NOT the story. The obstruction moves to
   *homotopy classes of trajectories*: a path from start to lode either
   crosses the tube or links the core circle (H₁(ℝ³ \ M) = ℤ). Theorem slot
   for Prop 4's true generalization: a lower bound on query-hit mass in
   terms of the **linking number** of the planner's realized/imagined path
   with M — consequence forced by topology, not by measure or metric. This
   is the cleanest candidate for "topología algebraica de verdad" doing
   irreplaceable work in a bound.
3. **Nerve/Čech certificates for boundary knowledge.** Contact sets (samples)
   and mitigation fences are covers of the mode boundary; the nerve theorem
   turns "fence complex" into a certificate of the boundary's homotopy type
   when the cover is good (radius < τ again). Upgrades both the TDA-repair
   arm (A.1) and the 2D-mitigation decay finding of paper 2 §6.1 into one
   statement: mitigation IS incremental boundary estimation, and its
   certificate is topological.
4. **Gauge-region classification.** H_*(∂𝓡) as the invariant that organizes
   what different model families' priors deposit in unfalsifiable regions
   (the phantom-mode taxonomy of paper 2, made systematic). This is a
   *measurement organizer* (criterion (b)), not a bound.

### 8.4 Scope guard for the n-dim arm

Same rule as §6: rungs beyond (ShellField-n, TubeField-3) — knotted M,
products with richer Betti profiles, moving boundaries — are recorded here
and stay OUT of paper 3 unless one of the four slots above lands a theorem
that needs them. "Heavy and multidimensional" means n as a swept knob and
one honest topological theorem, not a zoo.

---

## Appendix A — Literature anchors + extra directions (added by Claude, 2026-07-19)

> **Provenance note (read this).** Sections 1–7 above were written by the paper-3
> shaping session from Javier's recollection of earlier conversations. THIS
> APPENDIX is added by Claude directly from the agent-memory notes those
> conversations produced — the bibliographic anchors and side-directions that
> "other people couldn't find" because they lived only in memory. It is kept
> separate, and nothing above is edited, so the two sources stay distinguishable:
> §1–7 = the shaping session; Appendix A = the recovered memory notes.

### A.1 Literature anchors (each mapped to the section it de-risks)

§1–7 already lean on "reach", "crossing", "persistent homology", and
"topological recovery" informally. Each is an established result — cite them so
the *provable* claims rest on named theorems, not intuition:

- **Reach — §2 invariant, §3c gauge region, §4.4 multidim.** Federer, "Curvature
  Measures," *Trans. AMS* 1959, doi:10.1090/s0002-9947-1959-0110078-1. The reach
  τ(M) folds curvature and feature-separation into one scale; use it to
  *normalize* boundary metrics and to state when a sample can resolve the ring's
  inner vs outer boundary (needs sampling radius < τ). It is also the correct
  d ≥ 3 generalization of paper 2's single κ: principal curvatures + second
  fundamental form + reach, not one scalar.
- **Homology from random samples — §4.3 TDA arm.** Niyogi, Smale & Weinberger,
  "Finding the homology of submanifolds with high confidence from random
  samples," *DCG* 2008, doi:10.1007/s00454-008-9053-2. Gives the sample density
  (in units of reach) at which balls around sampled points recover the true
  homology w.h.p. — exactly the guarantee the "does the contact set reveal
  β₁ = 1?" arm needs, and it turns the §6 "TDA at N = 40 is data-starved" worry
  into a *computable* threshold N below which β₁ is unrecoverable.
- **Stability of persistence — §4.3.** Cohen-Steiner, Edelsbrunner & Harer,
  "Stability of Persistence Diagrams," *DCG* 2007, doi:10.1007/s00454-006-1276-5.
  The bottleneck-stability bound is what distinguishes a *real* hole from a
  sampling-induced one, and it is stable under the geometric perturbations the
  contact set carries — the principled version of "is this β₁ signal real."

### A.2 Directions from memory not yet in §1–7

- **Active boundary learning — the direct answer to the §6 data-starvation
  risk.** Rather than wait for random contacts, place the next query where the
  candidate hypotheses *disagree* (version-space / boundary-fragment view).
  Mammen & Tsybakov, "Smooth discrimination analysis," *Ann. Statist.* 1999,
  doi:10.1214/aos/1017939240, is the optimal-rate statistical frame for
  estimating a region's boundary — a better lens for the TDA/repair arm than a
  purely geometric curve, and it composes with mitigation (which already queries
  every real deployment step).
- **A sample-complexity theorem for semialgebraic guards.** Bound the samples
  (or the version-space diameter) needed to *identify* a guard as a function of
  dimension, polynomial degree, number of inequalities, and margin — the
  quantitative companion to the qualitative gate-quotient (§3c), and the bridge
  back to paper 2's "code / predicate-complexity" story.
- **Geometric vs descriptive (AST) complexity are distinct axes.** A circle is
  geometrically curved yet programmatically simpler than an 8-gon; the artifact
  classification (§4.2) should log BOTH, because "dimensional reduction" is a
  descriptive-complexity collapse, not a geometric one.
- **Guard geometry vs reset-map complexity — an orthogonal knob.** Hold the
  guard region fixed and vary the reset map: bounce / stick / friction /
  hysteresis / velocity-dependent reset. Paper 2 found "non-positional guards"
  (velocity-dependent freezes); this axis makes that a *designed* dimension,
  independent of the Betti ladder.
- **Explicit local-indistinguishability experiment.** Two modes identical over
  the *entire observed* region but globally distinct — the gate-quotient (§3c)
  turned into a controlled A/B. The cleanest possible demonstration that the
  prior, not the data, fixes the enclosed content; unifies phantom modes, the
  Proposition-2 caveat, and the impossibility of global extrapolation in one
  measurement.
- **Explicitly out of scope (recorded, not reopened):** moving / time-dependent
  guards, memory/hysteresis, contact-rich manipulation — same boundary as §6.
