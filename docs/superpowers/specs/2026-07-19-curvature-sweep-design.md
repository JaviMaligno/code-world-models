# Design: Repair-vs-geometry — capacity frontier of the synthesizer (paper 2)

Date: 2026-07-19 (rev. 4 after third expert review of 538c076)
Branch: `claude/continuous-setting-feasibility-wktp6b`
Worktree: `cwm-wt-paper2`
Status: implementation-ready. rev. 4 closes V=V_transcript, version-space `S`,
transcript-controlled evidence dose, non-positional guards, and pins numeric
cells/metrics/thresholds/budget. A calibration prototype (plan Task 1) fixes the
values marked *(calibrated)* before the synthesis runs, exactly as the original
disc did.

## Decomposition (V is V_transcript)

The visibility that matters to the synthesizer is **V_transcript** (a mode
contact/failure actually reached some prompt), NOT V_gate. Full law:

```
P(R) = P(R|¬V)·P(¬V) + P(V)·[ P(R|V,¬S)·P(¬S|V) + P(R|V,S)·P(S|V) ],   V ≡ V_transcript
```

Isolated causal path: `P(V∧S∧R) = P(V)·P(S|V)·P(R|V,S)`.

**Outcome is not binary.** A repair attempt is classified into:
1. **correct repair** — reproduces the true mode, no phantom region;
2. **true-mode + phantom** — reproduces the true mode but adds a false-positive
   region (the Claude phantom-mode failure; a false positive, NOT "repair
   without visibility");
3. **wrong** — neither.
`P(R|¬V)>0` (prior-based repair) and `P(R|V,¬S)>0` (accidental hit on thin
evidence) are results about the prior, not exceptions.

## Evidence the synthesizer sees (verified in contract.py)

initial prompt = 30 spaced examples (`max_examples=30`); gate = all
`N·h = 40·80 = 3200` transitions; each refinement prompt = first 20 failures
(`failures[:20]`), artifact- and order-dependent. Logged per seed: **V_gate,
V_initial, V_transcript**, and the count/geometry of contact examples shown.

## `S` (sufficiency) via version space — NOT via the oracle alone

The oracle succeeding may be prior; failing may be poor optimization. So define
sufficiency independently:

> `S` holds iff every shape in the family consistent with the shown evidence
> differs from every other by less than a threshold `τ_S` (in IoU/Hausdorff) on
> the evaluation box — i.e. the **version-space diameter** is small.

- small diameter ⇒ identifying evidence (`S`);
- large diameter ⇒ insufficient evidence (`¬S`);
- **LLM fails with small diameter ⇒ clear representational failure.**

The per-family oracle (three information budgets below) is the **operational**
estimator of reconstructability; the version-space diameter is what licenses the
strong information claim. If the version-space computation proves too heavy,
keep the oracle but label it *operational oracle* and drop the strong
identification wording. `τ_S` *(calibrated)*.

Oracles fit on **labeled proposed endpoints (inside/outside)**, not positive
contacts (contacts penetrate; they don't reveal the boundary point):
`oracle_initial` (30), `oracle_transcript` (union shown to LLM), `oracle_full`
(3200) — **the operational ceiling for that family and those 3200 observations**,
not "what is knowable at all". Primary attribution = **LLM vs oracle_transcript**.

## Metrics (primary is in state–action space)

The artifact need not induce a unique planar set `M ⊂ ℝ²` (it can gate on
velocity/action/previous state). Therefore:

1. **Primary — symmetric transition-disagreement in state–action space**, in a
   tube around the guard, over **stratified labeled (state,action) proposals**.
   Report three separate balanced-disagreement scores — **uniform-box**,
   **boundary-band** (PRIMARY), **planner-distribution** — never aggregated into
   one weighted score without pre-registered weights.
2. **Boundary — symmetric Hausdorff / robust p95 + symmetric mean**, normalized
   by box diameter / reach.
3. **2D region IoU — only after a preimage-invariance check**: IoU/marching-
   squares is reported *iff* the artifact's forbidden set is invariant across
   several (state,action) preimages producing the same endpoint. If not
   invariant, classify the artifact as a **non-positional guard** and report the
   inter-preimage discrepancy (itself a finding about the effective program
   class). IoU takes exact 0 and 1 → model with **zero/one-inflated beta** (or
   regularized logit-normal), not ordinary beta.
4. **Program — automated AST/MDL vector** (#comparisons, boolean depth,
   #literals, poly degree, hypot/sqrt, conj/disj/aux regions, AST length/MDL,
   invented/superset/subset). Automate AST; audit a sample.

Synthesized-set extraction: **black-box grid + marching squares + convergence
check**. Never in-process `exec` non-accepted code — `SynthesizedModel` execs
accepted artifacts only; **gate-failing artifacts run in the sandbox**, and every
artifact is classed **{invalid, gate-failing, gate-passing}**.

## Numeric cells, metrics, thresholds

Common reachable box: **`[-8,14]×[-6,6]`** (envelope of the start→lure corridor;
*calibrated* to the empirical p99 of rollouts). Grid **256²** initial, converged
if the metric shifts `<1%` at 512². Mode offset `c` near the old patch band
(`x≈3`). `δ` = **median normal-bracket width between the nearest shown
inside/outside pair** (fallback: local version-space diameter). "repaired" =
**boundary-band disagreement ≤ 0.05 AND FPR ≤ 0.05** on the primary score
*(threshold calibrated on the anchor)*.

| Sweep | Cells (geometry × config) | Value |
|-------|---------------------------|-------|
| Anchor | half-plane `x≥c` | 1 |
| 0 · Evidence dose | **one** geometry (intermediate parabola OR circle) × `m∈{1,2,4,8,16}` × span{small,large} | 10 |
| 1 · Curvature | parabola `x≥c+y²/2R`, `R∈{8,4,2,1}` (κ_center=1/R; half-plane=R→∞ is the anchor) | 4 |
| 2 · Composition | {strip, wedge, triangle, square, hexagon} × {face-on(0), vertex-on(π/k)} (strip face-on only) | ~9 |
| Contrast | parabola vs circle at matched 1&2-jet, one curvature | 2 |

Add square to Sweep 0 only if an interaction appears (review's advice).
`R`, `τ_S`, `r`/offset, box, threshold are *(calibrated)* in Task 1.

### Evidence dose must control the WHOLE transcript
Varying `m` initial contacts is void if refinement then feeds up to 20 more
failures. So: **cap the entire transcript (initial + every refinement prompt) to
exactly `m` positive contacts plus matched nearby negatives**, holding the total
example count and token budget constant by substituting background transitions
for contacts. `m` is then the only intervention. (Alternative kept in reserve:
run evidence-dose with refinement disabled, or a small `m_initial×m_refinement`
factorial.)

### Shape interface (unbounded-safe; covers strip/wedge)
```
contains(p)               # bool
implicit_value(p)         # signed level set: NEGATIVE inside, POSITIVE outside
boundary_points(window,n) # arc-length uniform within the window
project_to_boundary(p)    # nearest point; ties → deterministic pick + multi flag (or list)
normal_or_cone(p)         # normal, or normal cone at a vertex
```
Implement for half-plane, parabola(R), strip, wedge, regular polygon(k,orient),
circle. Bounding box belongs to the experiment, not the shape.

## Statistics and budget

- Continuous per-seed score primary; binary "repaired" secondary (threshold
  above). Bounded scores → zero/one-inflated beta / regularized logit-normal;
  logistic only for `repaired`; **random intercept per seed/sample** (pairing
  across geometries/sizes); model×geometry interaction.
- **Pre-registered adaptive rule** (observed-result-dependent is fine *because*
  pre-registered): 10 seeds all cells → 20 where the crossover CI crosses a cell
  → 30 if its width still exceeds a fixed bound; design-aware inference.
- Report a **crossover interval**, not a point.
- Record exact model version, temperature, inference seed per call.

**Budget (real):** cells above, both sizes (×2). Anchor 1, Sweep 0 10, Sweep 1
4, Sweep 2 ~9, Contrast 2 → **~26 geometry configs × 2 sizes = ~52 cells**. At 10
initial seeds and ~2–7 LLM calls/synthesis → **~520 syntheses, ~1.5–3.6k LLM
calls** before densification (to 20–30 at anchor+transition). **Stopping order:**
Task-1 calibration → anchor + Sweep 1 + evidence-dose (first science) → decide
continue → Sweep 2 → contrast + topology add-on only if budget/paper-length
allow. Evidence-dose is prototyped on ONE geometry first.

## Implementation order

1. **Calibration prototype (Task 1):** fix `R`, `τ_S`, `r`/offset, box, grid
   convergence, `δ`, repaired-threshold; confirm the mode-blind planner is
   exploited per cell; CI for `r` on an independent sample.
2. Shape interface (unbounded-safe) + common box/grid + sandbox classification.
3. Metrics 1–2 + version-space `S` + tangent/three-oracle baselines.
4. Anchor + parabolas + evidence-dose — first science.
5. Composition (Sweep 2).
6. Closure contrast; 2D-topology add-on only if budget/length allow.

## Paper integration

Replace "0/76 on a disc" with the capacity frontier over `κ·L_obs` and over
compositional complexity (both sizes); the evidence-dose factor-2-vs-3
identification licensed by version-space `S`; the closure contrast; tangent +
three-oracle baselines; crossover interval; AST/MDL breakdown; and the outcome
taxonomy (correct / true+phantom / wrong). Representation claims only where `S`
holds. Re-scope "geometry-dependent" to a mechanism separating information from
representation. EXPERIMENTS.md dated entry; guard clean on both papers.

## Out of scope / noted-but-separate

- Ellipse in core; mitigation / CEM / eps per geometry; cross-family on the
  sweep; formal repair theorem and deep topology (paper 3,
  [[paper3-geometry-topology-directions]]).
- **2D-topology enrichment (candidate paper-2 add-on, its own mini-plan):** disc
  (1,0), annulus (1,1), two discs same mode (2,0); matched total rarity; evidence
  from every component/boundary; topological oracle; measure (b₀,b₁) of the
  synthesized set in the box AND IoU/FPR (Betti-correct with wrong geometry is
  possible). "Global-structure enrichment," not a topological law.

## Risks

- Version-space computation cost → fallback to operational-oracle wording.
- Non-positional guards → primary metric is state–action; preimage-invariance
  gate before any 2D claim.
- Evidence-dose leakage via refinement → whole-transcript cap.
- Calibration time sink; independent-sample CI for `r`.
- Sequential-design inference → pre-registered rule + design-aware analysis.
- Azure cost (~520+ syntheses) → crash-safe checkpoint/resume; phased stopping.
