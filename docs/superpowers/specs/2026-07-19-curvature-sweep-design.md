# Design: Repair-vs-geometry — capacity frontier of the synthesizer (paper 2)

Date: 2026-07-19 (rev. 3 after second expert review of 454a8c2)
Branch: `claude/continuous-setting-feasibility-wktp6b`
Worktree: `cwm-wt-paper2`
Status: implementation-ready target. rev. 3 closes the factorization and
evidence-definition blockers and pins the geometric, interface, sandbox, and
statistical details.

## Problem and the correct decomposition

Paper 2 found repair-from-data is geometry-dependent (1D clamp 82/82 pooled; 2D
disc 0/76, collapsed to a half-plane) and currently *documents* it. We *close*
it by measuring the synthesizer's **effective capacity frontier** over boundary
geometry, separating three factors: visibility, evidence sufficiency, and
representation.

**Full law (all branches — nothing is an "exception"):**

```
P(R) = P(R|¬V)·P(¬V)                         # repair without visibility: prior / phantom mode
     + P(V)·[ P(R|V,¬S)·P(¬S|V)              # accidental hit on insufficient evidence
            + P(R|V, S)·P(S |V) ]            # the causal path we isolate
```

The clean **causal path we aim to characterize** is the single joint term

```
P(V ∧ S ∧ R) = P(V) · P(S|V) · P(R|V,S).
```

`P(R|¬V) > 0` (repair without seeing the mode) and `P(R|V,¬S) > 0` (repair on
insufficient evidence) are then *interesting results about the prior* — not
framework exceptions. The phantom-mode failure is the `¬V`/`¬S` branch made
visible. We report all branches; the sweep conditions on `V ∧ S` to read factor
3 (representation).

## What the synthesizer actually sees (measured from the code)

Evidence is not "the sample." The pipeline (`contract.py`) is:

- **initial prompt:** 30 spaced transitions (`max_examples = 30`).
- **gate:** all `N·h = 40·80 = 3200` transitions.
- **each refinement prompt:** only the **first 20 failures** (`failures[:20]`),
  which depend on the previous artifact and the transition order.

So "mode visible" must be split, and logged per seed:

- **V_gate:** a contact exists among the 3200 (what rarity `r` controls).
- **V_initial:** a contact appears in the 30 spaced initial examples.
- **V_transcript:** a mode contact/failure reaches *any* prompt across
  refinement (the union of what the LLM was actually shown).
- plus the **count and geometry** of the contact examples effectively shown.

### Three oracles (this is how factors 2 and 3 are separated)

A per-family shape fit (circle / parabola / polygon), fit on **labeled proposed
endpoints (inside/outside), not on positive contacts** — contacts penetrate the
region and do not reveal the exact boundary point. Three information budgets:

- **oracle_initial:** the same 30 initial observations.
- **oracle_transcript:** the union of examples actually shown to the LLM.
- **oracle_full:** all 3200 (the information ceiling).

**Primary attribution comparison: LLM vs `oracle_transcript`.** If
`oracle_transcript` reconstructs and the LLM does not → representation/prior
(factor 3). If `oracle_transcript` also fails → the bottleneck is information
(factor 2). `oracle_full` bounds what is knowable at all.

## Instruments

Single-mode (second patch disabled), evaluated on a **common reachable box**
(the box belongs to the experiment, not the shape), each calibrated to matched
rarity with a CI, each confirmed to give a genuine hazard (mode-blind planner
exploited).

### Anchor — 2D half-plane, mono-mode, identically calibrated
`x ≥ c`. The linear predicate and the limit of both sweeps. Fresh 2D anchor —
1D results and the earlier bi-modal disc are not comparable.

### Sweep 0 (highest value) — evidence dose
Directly identifies factor 2 vs factor 3. Fixed geometry (intermediate parabola,
circle, square only — does not multiply the budget), condition on visibility,
and **vary the number of contact examples shown** `m ∈ {1,2,4,8,16}`, crossed
with **small vs large geometric span**, with **matched nearby negatives**. This
is the most important single addition for paper 2.

### Sweep 1 — local curvature (graph boundaries)
Guard `x ≥ c + y²/(2R)`, limit `R→∞` = half-plane, same reachable window for all
`R`. Curvature of this parabola is **not** globally `1/R`:
`κ(y) = (1/R)/(1+(y/R)²)^{3/2}`. We use **κ local at the arc center** as the axis
value and also log its **range over the observed arc**. Cells chosen so the
dimensionless resolution (below) spans the transition.

### Sweep 2 — compositional complexity (oriented polytopes)
Half-plane, strip, wedge, triangle, square, hexagon. **Not a clean 1-D axis** —
treat the geometry as separate logged variables, not a scalar: **#facets**,
**closed/open**, **intersection angle**, **face-on vs vertex-on incidence**
(several rotations per shape), **#facets actually observed**. Total curvature of
any convex closed curve is 2π (Gauss–Bonnet), so this axis is composition, not
curvature.

### Contrast — global closure at matched local jet
Parabola vs circle sharing position, tangent, and local curvature on the contact
arc (matched 1- and 2-jet). Isolates global closure / extrapolation with the
local geometry held fixed.

### Baselines
- **Tangent baseline:** best half-plane fit to the shown contacts → quantifies
  "collapses to the tangent."
- **Per-family oracle** (three budgets, above).

### The geometric variable
`κ·L_obs` (or `κ·L_obs²/δ`), dimensionless: `L_obs` = observed **arc length /
tangential extent** (defined per family — arc length for the parabola/circle,
not "angular span"), `δ` = the uncertainty with which the contacts bound the
boundary. The sagitta `κL²/8` is meaningful only against this resolution.

### Dropped from core: ellipse
Eccentricity fixes neither scale, orientation, nor local curvature — confusion
over identification.

## Metrics (hierarchy)

1. **Primary — symmetric disagreement on the common box**, over **stratified
   labeled state–action proposals**: in-`M` positives, out negatives, a narrow
   band on both sides of the boundary, a uniform draw, and the planner's own
   distribution. Report balanced accuracy, precision, recall, FPR; **IoU
   mandatory**.
2. **Boundary — symmetric Hausdorff / robust p95 and symmetric mean distance**,
   normalized by box diameter or a reach-based scale.
3. **Dynamic — transition-disagreement rate in a tube around the guard**, in
   **state–action space** (the mode's home is the preimage of contact, not
   `M ⊂ ℝ²`).
4. **Program — automated AST/MDL vector**: #comparisons, boolean depth,
   #literals, polynomial degree, hypot/sqrt, conjunction/disjunction/auxiliary
   regions, AST length / approx MDL, invented/superset/subset flags. Automate
   AST; manually audit a sample.

### Extracting the synthesized boundary (for metrics 1–2)
Evaluate the artifact as a **black box on the common grid + marching squares**,
with a **convergence check** (metrics stable under grid refinement). Do NOT
in-process `exec` non-accepted code: `SynthesizedModel` execs accepted artifacts
only. Classify every artifact into **{invalid/non-executable, executable but
gate-failing, gate-passing}**; AST is always extractable; **dynamic metrics for
gate-failing artifacts run in the sandbox**, recorded separately.

## Statistics and budget

- **Continuous per-seed score** (metric 1/2) is primary; binary "repaired" is a
  thresholded secondary (threshold fixed in the plan).
- Models: **beta regression / logit-normal** for bounded IoU/disagreement;
  **logistic only for `repaired`**; **random intercept per seed/sample** to
  exploit the pairing across geometries and sizes; **model×geometry
  interaction**.
- **Pre-registered adaptive rule** (may depend on observed results *because* it
  is pre-registered — only improvised decisions are barred):
  1. 10 seeds in every cell.
  2. → 20 where the crossover CI crosses the cell.
  3. → 30 if its width still exceeds a fixed threshold.
  4. Adjust inference for the sequential design.
- Report a **crossover interval**, not a point `R*`.
- Record **exact model version, temperature, any inference seed** per call.
- ≥ 20 seeds at the anchor and transition region.

## Interfaces (must exist before code)

Shapes are possibly unbounded, so the rev. 2 interface is fixed:

```
contains(p)               # boolean
implicit_value(p)         # signed level-set value (cheap; not exact euclidean dist)
boundary_points(window,n) # arc-length uniform WITHIN the given window
project_to_boundary(p)    # nearest boundary point (parabola projection is non-trivial → numeric)
normal_or_cone(p)         # normal, or the normal cone at a vertex (multi-valued)
```

The **bounding box is the experiment's**, not the shape's. Implement for
half-plane, parabola(R), regular polygon(k, orientation), circle (contrast).

Other machinery that must be defined in the plan: common reachable box + grid
resolution/convergence; probes built from **feasible integrated endpoints**
labeled by stratum (not abstract boundary points); vertex handling via the
normal cone; per-family calibration offset with an **independent-sample CI for
`r`**; mandatory per-seed covariates (rollouts-with-contact, contact
transitions, unique contact points, `L_obs`, facets observed, penetration depth,
and V_initial/V_transcript/#examples-shown); exact score→"repaired" criterion;
JSON schema, checkpoint/resume, regression tests; cart golden test byte-identical.

## Implementation order (from the review)

1. Corrected factorization + V_initial/V_transcript + three oracles (definitions
   and logging).
2. `Shape` interface (unbounded-safe) + common box/grid + sandbox classification.
3. Metrics 1–2 + tangent/oracle baselines; κ, L_obs, δ, oracle-fit spec.
4. **Half-plane + parabolas + evidence-dose sweep (Sweep 0/1)** — first science.
5. Composition (Sweep 2).
6. Closure contrast and the small topological enrichment — only if budget and
   paper length allow.

## Paper integration

Replace "0/76 on a disc" with: the capacity frontier over `κ·L_obs` and over
compositional complexity (both sizes); the evidence-dose identification of
factor 2 vs 3; the closure contrast; tangent + three-oracle baselines; crossover
interval; AST/MDL breakdown. The representation claim (factor 3) is licensed only
where `oracle_transcript` shows factor 2 satisfied. Re-scope "geometry-dependent"
from caveat to a mechanism separating information from representation.
EXPERIMENTS.md dated entry; guard clean on both papers.

## Out of scope (YAGNI) and noted-but-separate

- Ellipse in core; mitigation / CEM / eps per geometry; cross-family on the
  sweep; a formal repair theorem and deep topology (paper 3,
  [[paper3-geometry-topology-directions]]).
- **Small 2D-topology enrichment (candidate paper-2 add-on, its own mini-plan,
  inspiration not gospel):** 3 cells — disc (b₀,b₁)=(1,0), annulus (1,1), two
  discs same mode (2,0); matched total rarity; evidence from every
  component/boundary; a topological oracle; measure (b₀,b₁) of the synthesized
  set in the box AND IoU/FPR (a program can get Betti numbers right with wrong
  geometry). Frame as "global-structure enrichment," not a topological law, not
  part of the curvature crossover.

## Risks

- **Evidence sufficiency still stochastic** — stratify/condition on `L_obs` and
  the V-distinctions; the oracle is the anchor, not averaging.
- **Vertex normals / tube ambiguity** — normal-cone interface, sample audit.
- **Parabola projection / marching-squares convergence** — numeric, with a
  convergence test in the metric.
- **Calibration time sink** per family; independent-sample CI to avoid
  over-fitting `r`.
- **Sequential-design inference** — pre-registered rule + design-aware analysis.
- **Azure cost** for ≥20-seed cells with refinement → crash-safe checkpoint.
