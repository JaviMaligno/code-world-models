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
plane) as one more paper-2 arm. Decision (2026-07-19): **no — the annulus opens
paper 3.** Rationale, recorded so it isn't relitigated:

- Paper 2's negative result is already saturated: 0/76 on the *contractible*
  disc. A harder geometry cannot strengthen a floor of zero, and the submission
  (tex/PDF/tarball/figures) is finished; reopening it buys nothing.
- The disc is topologically trivial. The annulus's payoff is not "repair also
  fails here" — it is a set of phenomena that paper 2's measure-theoretic frame
  cannot even state: exact (not just exponentially likely) unidentifiability of
  enclosed content, topological lower bounds on query-hit mass, and
  topology-informed repair. These need their own frame.
- Paper 2 already climbed the first rung silently: two disjoint patches means
  β₀ = 2, with per-mode identifiability and partial-repair machinery built. The
  annulus is the β₁ rung. Paper 3 makes the ladder explicit and keeps climbing.

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
| 2 | **annulus (RingField2D)** | **β₁ = 1** | paper 3 opening instrument |
| 2' | C-shape (ring with gap) | contractible, non-convex | the *topological knob*: gap→0 |
| 3 | shells/tori in d ≥ 3 | β_{d−1}, codimension | paper 3 multidimensional arm |

## 3. The opening instrument: RingField2D

Same 4D state and heading integrator as PatchField2D (reuse the class shape,
the frozen-default discipline, and the n-component machinery). The mode region
is an annulus centered on the phantom lode:

- mode: freeze-at-previous-position if `R_in ≤ dist((x',y'), c) ≤ R_out`,
  with the phantom lode strictly inside the inner disc.
- knobs: **thickness** `R_out − R_in` (the rarity knob, as before); **gap
  angle** `γ` (an angular sector removed from the ring — the topological knob:
  `γ = 0` gives β₁ = 1, any `γ > 0` is contractible); **start placement**
  (outside / inside the ring — inside makes the inner boundary reachable).

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
   both boundary components. Key question: does any family ever write a region
   with a hole from boundary-crossing data alone?
3. **Topology-informed repair (the constructive arm).** Persistent homology /
   clustering on the sample's *contact set* (the revealed boundary points)
   yields a topological summary ("contact points lie on a closed curve
   enclosing the target; β₁ = 1"). Feed the summary — not the answer — into the
   refine prompt. Does repair recover, the way 1D repair worked without help?
   This is TDA earning its keep inside the loop, and it is the natural fix for
   paper 2's probe limitation (probes only where the *true* mode fires; invented
   modes needed code inspection): probe placement itself becomes
   topology-driven.
4. **Multidimensional arm (the "heavy" part, scoped last).** Spherical shells
   S^{d−1} in d = 3..6 (state (x⃗, v⃗), same freeze semantics), solid torus in
   d = 3. Hypotheses to test, not assume: repair difficulty and artifact
   reduction track **codimension and Betti profile**, with "dimensional
   reduction" as the general failure mode (the synthesizer projects the region
   to lower descriptive complexity); the gate-quotient volume grows with
   enclosure. Keep cells small; this arm exists to show the invariants organize
   the results, not to sweep every d.

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
- **TDA at N = 40 is data-starved.** The contact set from 40 rollouts may be a
  handful of points on the outer boundary only. The TDA arm may need contact
  points pooled across refine iterations, or a larger-N sensor pass framed as
  deployment monitoring (which is legitimate: mitigation already watches every
  real step).
- **Don't burn LLM cells before the mechanism arm freezes the design** —
  paper 2's discipline (prototype-validated frozen defaults) applies verbatim.
- **Scope creep is the known failure mode of "more topology".** The ladder ends
  at rung 3 for this paper; sheaves, configuration spaces, and moving
  boundaries are explicitly out.

## 7. Next steps

1. Land paper 2 (its branch merges; the continuous stack becomes available
   here). Blocked on that.
2. Prototype `RingField2D` + calibration (rarity vs thickness, γ sweep,
   truth-MPC navigates, blind-MPC pins) — the analogue of the 2026-07-16
   PatchField2D controller prototype. Freeze defaults.
3. Write the mechanism-arm plan (docs/superpowers style) with the three-way
   split table as the deliverable.
4. Draft the gate-quotient proposition and the crossing bound properly; they
   are cheap and de-risk the "is there a theorem here" question early.

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
