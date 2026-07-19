# Design: Repair-vs-geometry — capacity frontier of the synthesizer (paper 2)

Date: 2026-07-19 (rev. 2 after expert review of 3ca6456)
Branch: `claude/continuous-setting-feasibility-wktp6b`
Worktree: `cwm-wt-paper2`
Status: redesigned per expert review. Supersedes rev. 1, which confounded
curvature, logical complexity, and geometric evidence sufficiency.

## Problem and the factorization that governs the whole design

Paper 2 found repair-from-data is geometry-dependent (1D clamp 82/82 pooled; 2D
disc 0/76, collapsed to a half-plane) and currently *documents* it. We *close*
it by measuring the synthesizer's **effective capacity frontier** over boundary
geometry. The central hazard is attributing to "curvature" an effect that is
really logical complexity or evidence sufficiency. The design is organized
around the correct factorization of a repair event:

```
P(repair) = P(mode visible)
          · P(evidence geometrically sufficient | visible)
          · P(synthesizer represents it | sufficient)
```

- Factor 1 (visibility) is what rarity `r` controls. Rev. 1 controlled ~only
  this and wrongly treated the rest as covariates.
- Factor 2 (sufficiency) is a **central explanatory variable**, not a covariate:
  same `r` can give a tight contact arc or contacts spread over half the
  boundary, one normal direction or many facets — radically different geometric
  information. We measure and stratify it, and use a per-family **oracle** to
  isolate it.
- Factor 3 (representation) is the scientific target: the synthesizer's prior /
  hypothesis class. It is only interpretable once factors 1–2 are pinned.

## What we are NOT doing / not confusing

- **Curvature ≠ logical complexity ≠ evidence sufficiency.** Separate axes for
  each; no single axis stands in for another.
- **No global-closure confound in the curvature axis.** A disc of growing `R`
  does not interpolate to a half-plane under a reproduce-the-whole-boundary
  metric (a half-plane never reproduces a closed circle). We use graph
  boundaries for the local axis and treat closure as its own contrast.
- **Topology note (corrected).** Non-trivial homology already exists in 2D: an
  annulus is planar with H₁(M)=ℤ; disconnected components give b₀>1; nested
  boundaries. Distinguish H₁(∂disc)=ℤ, H₁(disc region)=0, H₁(annulus region)=ℤ.
  What is not natural in a planar subset is "higher genus" (closed surfaces).
  This *curvature/complexity* plan does not run topology, but a 2D-topology
  experiment (annulus / disconnected modes; recover b₀,b₁) is a legitimate
  **candidate for paper 2** as a separate plan — noted, not scoped here. Deeper
  topological theory → paper 3 (`[[paper3-geometry-topology-directions]]`).

## Instruments: two clean sweeps + contrast + baselines + anchor

All modes are single-mode (second patch disabled), evaluated on a **common
reachable box**, each calibrated to the same rarity `r` (with a CI, see below)
and each confirmed to produce a genuine hazard (mode-blind planner exploited).

### Anchor — 2D half-plane (mono-mode, calibrated identically)
`x ≥ c`. The linear predicate, trivially repairable, and the R→∞ / k-side limit
of both sweeps. The 1D results and the earlier bi-modal disc are **not**
comparable anchors; this is a fresh, identically-calibrated 2D anchor.

### Sweep 1 — local curvature (graph boundaries)
Guard `x ≥ c + y²/(2R)` (a parabola), limit `R→∞` = half-plane, evaluated in the
**same reachable window** for all `R`. Interpolates curvature cleanly with no
global closure, no area, no "back side." Cells across `R` chosen so the
dimensionless resolution (below) spans the transition, not `R` on a round grid.

### Sweep 2 — linear composition (oriented polytopes)
Half-plane → strip/wedge → triangle → square → hexagon. This axis is
**compositional complexity** (#facets, boolean depth, #linear regions), NOT
curvature — total curvature of any convex closed curve is 2π (Gauss–Bonnet), so
`k` is not monotone in curvature. **Orientation is controlled**: at least
`face-on` and `vertex-on` incidence per shape (several rotations), because
hitting a face vs a vertex yields radically different evidence.

### Contrast — global closure at matched local jet
Parabola vs circle sharing position, tangent, and local curvature on the contact
arc (same 1-jet, matched 2-jet). Isolates the effect of *global closure /
extrapolation* holding the local geometry fixed — the one thing Sweep 1 cannot
see.

### Baselines (cheap, high-value)
- **Tangent baseline:** best half-plane fit to the sampled contacts. Lets us say
  quantitatively "the LLM artifact collapses to the tangent."
- **Per-family oracle:** circle/parabola/polygon fit *knowing the family*. If the
  oracle also fails to reconstruct from the sample → the bottleneck is
  information (factor 2). If the oracle succeeds and the LLM fails → it is
  representation/prior (factor 3). This is what separates the factors.

### Dropped from the core: ellipse
Eccentricity alone fixes neither scale, orientation, nor local curvature; it adds
confusion rather than identification. Excluded from the core sweep (may return
only if a specific question needs it).

## The geometric variable

Not `κ` alone but a **dimensionless resolution** `κ·L_obs` (or `κ·L_obs²/δ`),
where `L_obs` is the observed contact-arc span and `δ` the uncertainty with which
the contacts bound the boundary. The sagitta `κL²/8` is meaningful only against a
resolution scale. Repairability is modeled against this variable, per model size.

## Metrics (hierarchy; the old boundary-recall metric is demoted)

Rev. 1's boundary-point probe measured ~recall and missed oversized half-planes,
invented modes, extra forbidden regions, partial-overlap shifts — the same
`mode_blindness` blind spot paper 2 already hit with Claude's phantom mode.

1. **Primary — symmetric disagreement on the common reachable box.** Evaluate
   truth and synthesized code on **stratified** state–action proposals:
   in-`M` positives, out negatives, a narrow band on both sides of the boundary,
   a uniform draw, and the planner's own distribution. Report balanced accuracy,
   precision, recall, FPR. **IoU is mandatory, not optional.**
2. **Boundary — symmetric Hausdorff (or robust p95) and symmetric mean distance**,
   normalized by the box diameter / a reach-based common scale (Federer reach
   combines curvature and feature separation).
3. **Dynamic — transition-disagreement rate inside a tube around the guard**,
   because the observable is the state–action preimage whose integrated endpoint
   enters `M`, not `M ⊂ ℝ²` directly. The mode's real home is state–action space.
4. **Program characterization — automated AST/MDL vector**, not a 3-way label:
   #comparisons, boolean depth, #literals/constants, polynomial degree,
   hypot/sqrt use, conjunction/disjunction/auxiliary regions, AST length / approx
   MDL, and invented/superset/subset flags. Automate the AST extraction; manually
   audit a sample.

## Statistics and budget

- **Continuous per-seed score** (from metric 1/2) is the primary outcome; a
  binary "repaired" is a thresholded secondary (threshold defined in the spec,
  see machinery). A 0/10 cell is NOT zero-variance (Wilson upper ≈ 0.28).
- **≥ 20 seeds** at the anchor and in the transition region; fewer only in cells
  already saturated on the continuous score.
- **Logistic / mixed model** with a model×geometry interaction for the capacity
  frontier and the size effect.
- **Pre-registered adaptive rule:** densification depends on crossover
  uncertainty or a fixed prior rule, NOT on the observed result (no selecting
  cells to add seeds by outcome — that biases the estimate).
- **Report an interval for the crossover**, not a point `R*`.
- **Record exact model version, temperature, and any inference seed** per call.

## Machinery / interfaces (must exist before code)

- **`Shape` interface:** `contains(p)`, `signed_distance(p)`, `boundary_points(n)`
  (arc-length uniform), `bbox()`, `normals(p)` — implemented for half-plane,
  parabola(R), regular polygon(k, orientation), (circle for the contrast).
  Vertices: `normals` returns the normal cone / is multi-valued; boundary/tube
  metrics handle non-unique normals explicitly.
- **Common reachable box** and grid resolution with a convergence check (metrics
  stable under refinement).
- **Probes built from feasible integrated endpoints**, not abstract boundary
  points: a probe is a (state, action) whose one-step integrated endpoint lands
  in the intended stratum. This is what the gate and planner actually see.
- **Per-family calibration offset** stated exactly, with an **independent sample
  and a CI for `r`** (calibrate on one seed stream, measure on another).
- **Mandatory covariates logged per seed:** rollouts-with-contact, contact
  transitions, unique contact points, angular span `L_obs`, facets observed,
  penetration depth — AND how many contact transitions actually reach the prompt
  (initial 30 spaced examples) vs the gate/refinement (all up to 3200).
- **Exact score→"repaired" criterion** and the **behavior/classification when the
  gate does not pass** (a non-passing artifact still gets metric/AST records).
- **Full-arm controls** (geometry described in the prompt) at the extremes of
  each family, to confirm translation works when the rule is given.
- **JSON schema, checkpoint/resume** (reuse the crash-safe synthesis harness),
  and **regression tests**; the cart golden test stays byte-identical.

## Paper integration

- Replace the single "0/76 on a disc" point with: the capacity frontier over
  `κ·L_obs` (Sweep 1) and over compositional complexity (Sweep 2), both model
  sizes; the closure contrast (parabola vs circle at matched jet); the tangent
  and oracle baselines; the crossover interval; the AST/MDL breakdown.
- State the characterization as a falsifiable prediction confronted with the
  data, with the factor-3 (representation) claim licensed only where the oracle
  shows factor-2 (information) is satisfied.
- Re-scope "repair is geometry-dependent" from caveat to a mechanism separating
  information from representation.
- EXPERIMENTS.md dated entry; guard clean on both papers.

## Out of scope (YAGNI)

- Ellipse in the core sweep; mitigation / CEM / eps per geometry; cross-family on
  the sweep; a formal repair theorem and deep topology (paper 3).
- **Noted but separate:** a 2D-topology paper-2 experiment (annulus /
  disconnected modes, recover b₀,b₁) — its own plan if pursued.

## Risks

- **Evidence-sufficiency still leaks.** Even with the oracle, `L_obs` is
  stochastic per seed; we stratify/condition on it, not average over it.
- **Vertex normals / tube metric ambiguity** at polygon corners — handled by the
  normal-cone interface; audited on a sample.
- **Calibration time sink** per family (the known bottleneck); budget controller
  time and use the independent-sample CI to avoid over-fitting `r`.
- **Crossover outside the grid** → the pre-registered rule extends the grid, not
  re-tunes a cell.
- **Azure cost/throughput** for ≥20-seed cells with refinement loops → crash-safe
  checkpoint/resume.
