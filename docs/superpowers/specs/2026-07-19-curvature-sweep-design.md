# Design: Curvature sweep — characterizing repair-from-sample vs mode geometry (paper 2)

Date: 2026-07-19
Branch: `claude/continuous-setting-feasibility-wktp6b`
Worktree: `cwm-wt-paper2`
Status: approved in brainstorming (rarity-fixed control, three geometry axes,
three metrics, symmetric mini+large at 10 seeds/cell, adaptive densification)

## Problem

Paper 2's PatchField2D arm found that repair-from-data is geometry-dependent:
GPT-5.x repairs a 1D clamp (82/82 pooled) but collapses a 2D circular disc to a
half-plane (0/76). The current paper *documents* this as a scoped limitation.
This experiment *closes* it by measuring the transition: how repairability
varies as the mode boundary is deformed from a flat clamp toward curved and
composite shapes. It turns a binary "geometry-dependent" caveat into an
empirical curve `repairability(geometry)` that a geometric characterization must
reproduce.

The scientific hazard is confounding **curvature** with **rarity** `r` (the
probability a random rollout contacts the mode, which sets how much evidence of
the mode enters the synthesis sample). The design fixes `r` and lets geometry be
the only free variable.

## What we are NOT doing (and why)

- **Not going topological.** In 2D every simple closed boundary is a Jordan
  curve: ∂M ≅ S¹, H₁ = ℤ, complement in two components. Topology is *constant*
  across disc/ellipse/k-gon, so it cannot discriminate here. Non-trivial
  homology (annulus, higher-genus) requires higher-dimensional state and is
  reserved for a future multidimensional generalization (paper 3). The
  discriminating axis in 2D is the **complexity of the semialgebraic predicate**
  the code class must express, not topology.

## The reframe: two axes that interpolate half-plane → disc

Both axes start at the trivially-repaired half-plane (linear predicate,
curvature 0) and end at the never-repaired disc (quadratic predicate), by
different routes:

- **Axis 1 — smooth curvature.** Disc of radius `R`, curvature `κ = 1/R`. One
  quadratic predicate; curvature → 0 as `R` → ∞.
- **Axis 2 — linear composition.** Regular `k`-gon: boundary = conjunction of
  `k` linear half-plane predicates (`AND` of half-planes), locally flat with
  curvature concentrated at `k` vertices. `k = 1` → half-plane; `k` → ∞ → disc.
- **Axis 3 (enrichment) — variable curvature.** Ellipse of eccentricity `e`:
  same topology, curvature varying along ∂M (maximal at the major-axis
  vertices). Refines but does not discriminate the two formalizations.

The deliverable is the synthesizer's **effective hypothesis class**: up to what
curvature `1/R` (axis 1) and how many composed half-planes `k` (axis 2) it
repairs before collapsing. Curvature is the geometric proxy; semialgebraic
predicate degree is the computational proxy that fits "code."

Falsifiable prediction: `repairability(1/R)` is decreasing; as `R` → ∞ repair
reappears (the half-plane becomes correct on the reachable region); there is a
crossover `R*`. The quantitative bridge is the arc sagitta `≈ ℓ²/8R`.

## Cells (≈11 geometry cells)

Each cell recalibrates its geometry so the empirical rarity `r ≈ 0.15`
(measured as P(random rollout contacts the mode) under the fixed sampler).
Everything else is held constant: `N = 40`, the start→lure corridor, `x0_range`,
the pinned-integrator gate `ε = 10⁻⁹`. A **single** mode per instrument (the
second patch disabled) so geometry is the only thing that varies.

| Axis | Values | What varies | Cells |
|------|--------|-------------|-------|
| 1 · Disc R | `R ∈ {1, 2, 4, 8}` | `κ = 1/R`: 1 → 0.125 | 4 |
| 2 · k-gon | `k ∈ {3, 4, 6, 8}` | composed half-planes; `k`→∞ ≈ disc | 4 |
| 3 · Ellipse e | `e ∈ {0.6, 0.85, 0.95}` | curvature variable, max at vertices | 3 |

Known contrast anchors (already measured, not re-run): 1D half-plane clamp
(repairs 82/82) and the original bi-modal disc (0/76). `R = 1` mono-mode is
re-anchored here in the single-mode configuration for consistency.

### Rarity control and covariates (the rigor point)

`r ≈ 0.15` with `N = 40` gives ≈ 6 expected contacts per sample and
P(sample misses the mode) = `0.85⁴⁰ ≈ 0.0015` — so essentially every seed is
mode-present, and the sweep measures **pure repair** (given the mode's contacts,
is the geometry recovered?), which is the question. The identifiability event
(miss → blind) is already established in 1D/2D and is not the focus here.

Calibration adjusts a designated geometric offset (the mode's placement relative
to the corridor / global scale of the polygon or ellipse) to hit `r ≈ 0.15`,
following the same calibration-prototype step the original disc used. Because
`r` is the theoretically-relevant control (it is what the danger law and
identifiability condition on), it is the **primary** control; anything that
co-varies when the shape changes (e.g. sampled contact-arc length, mode offset)
is **reported as a covariate**, not eliminated — eliminating every covariate
while changing the shape is impossible, so we fix the canonical one and disclose
the rest. Per-cell sanity check: the mode-blind planner must be exploited
(`play_cost ≈ 1`) so there is a genuine hazard to repair.

## Three repair metrics (not exclusive — each gives different information)

- **A · Boundary reproduction (primary, drives the curve).** Uniform probes on
  the *true* boundary ∂M_true; metric = fraction reproduced to tolerance,
  generalizing the existing `mode_blindness`. Continuous, comparable across
  geometries, and immune to the half-plane being unbounded. The per-cell repair
  rate (fraction of seeds whose artifact reproduces the full boundary) is the
  `repairability(geometry)` curve.
- **B · Area overlap (IoU).** Execute the synthesized code on a grid, IoU of its
  forbidden region with M_true **bounded to the reachable box** (required — the
  collapsed half-plane is unbounded). Geometric and good for figures; more
  machinery (grid eval + bounding).
- **C · Predicate class (characterization).** Classify the generated code as
  linear / `k`-linear conjunction / quadratic. Measures the effective hypothesis
  class directly (the theory axis); semi-manual (parsing/inspection over the
  gate-passing artifacts).

A is automatic and danger-law-relevant; C is the theory layer; B is optional
figure support.

## Models and budget (symmetric, adaptive)

Both **GPT-5.x mini and large**, the same seeds on the same cells — symmetric.
Rationale: mini also repairs the 1D clamp (10/10, in 0–5 iterations vs large's
0–1; the "82/82" is pooled mini+large), so mini is equally a repair-in-1D model
whose 2D collapse is part of the phenomenon. Measuring mini less would be unfair
*and* would bias the mini-vs-large comparison; and mini is the cheaper model, so
cost argues the opposite way. The iteration-count asymmetry in 1D motivates a
measured hypothesis: **the effective capacity frontier scales with model size**
(large collapses at higher curvature / more sides than mini).

- Start: **10 seeds/cell × 11 cells × 2 sizes = ≈ 220 syntheses.** Extreme cells
  are 0/n or n/n (no variance), so resolution is spent where it matters.
- Also report **refinement iterations per cell** (mini takes more → proximity to
  its capacity limit) as fine-grained signal at no extra cost.
- **Adaptive:** densify cells near the crossover, or raise to 20 seeds only on
  cells where the mini and large curves nearly coincide.

## Machinery generalization (minimal, golden-protected)

1. Generalize `PatchField2D`'s mode region from the hard-coded disc
   (`(x−cx)²+(y−cy)² ≤ R²`) to a parameterized shape predicate covering
   disc(R) / regular k-gon(k) / ellipse(e), single-mode (second patch disabled).
   `contact_modes`, `step`, and `mode_blindness` consume the shape predicate;
   the freeze-at-previous-position semantics is unchanged.
2. Boundary probes (`mode_probes`) must sample the **whole** ∂M_true uniformly
   (arc length), so partial collapse (a half-plane matching only the sampled
   arc) is detected on the unsampled boundary. This generalizes the current
   single-region probe.
3. The synthesis prompt for the **incomplete** arm stays geometry-agnostic — it
   omits the mode clause; the geometry lives only in the truth env and the
   sampled contacts, so the synthesizer must infer it from data (this is the
   repair phenomenon). No per-geometry prompt text is needed for the sweep.
   (A full-arm control that *describes* the geometry is optional, anchors only.)
4. A calibration-prototype step per geometry (controller, before the synthesis
   runs) that finds the offset/scale hitting `r ≈ 0.15` and confirms the
   mode-blind planner is exploited. Mirrors the original disc calibration.
5. `mpc.py`, `cem.py`, `harness.py` unchanged. The cart golden test must still
   pass byte-identically.

## Paper integration

- Extend the PatchField2D synthesis section: replace the single "0/76 on a disc"
  point with the `repairability(geometry)` curve(s) over both axes and both model
  sizes, the crossover `R*`, and the predicate-class breakdown (metric C).
- State the characterization as a **falsifiable prediction** (repairability
  decreasing in curvature; half-plane→disc collapse is the tangent
  approximation; capacity frontier ∝ model size) confronted with the measured
  curve. A formal theorem (and hard topology) is explicitly future work / paper
  3 — this section is the empirical anchor, not the proof.
- Re-scope the "repair is geometry-dependent" paragraph from a caveat to a
  measured law with a mechanism.
- EXPERIMENTS.md dated entry; guard clean on both papers.

## Out of scope (YAGNI)

- Mitigation, CEM, and eps sweeps per geometry — the sweep is about *synthesis
  repair*; those axes are already covered on the disc and do not inform the
  curvature curve.
- Bi-modal / partial-repair cells — single mode isolates geometry.
- Cross-family (Qwen/Claude) on the sweep — the three-family picture is
  established; add only if asked.
- A formal repair-characterization theorem and non-trivial topology — paper 3.
- Per-cell tuning of anything other than the r-calibration offset.

## Risks

- **r-vs-offset coupling.** Fixing `r` by moving the mode offset slightly couples
  geometry with placement; mitigated by holding the corridor/N/gate constant and
  reporting covariates (contact-arc length, offset). `r` is the canonical
  control; perfect isolation of a single scalar is impossible when the shape
  itself changes.
- **Calibration time sink.** Per-geometry r-calibration is the known bottleneck
  (as with the original disc); budget controller time for it before the synthesis
  runs.
- **Crossover outside the grid.** If `R*` falls beyond `R = 8` or below `R = 1`,
  the adaptive step extends the grid rather than re-tuning within a cell.
- **mini/large curves coincident.** If the capacity frontiers overlap, raise to
  20 seeds on the overlapping cells to resolve (or report "no size effect
  detected" honestly).
- **Azure cost/throughput.** 220 syntheses with refinement loops; reuse the
  crash-safe checkpoint/resume harness from the existing synthesis scripts.
