# Paper 2 — corrections history

The manuscript states what is true; this file records how it got there. Everything below
was previously narrated inside `main.tex` and was moved here in the 2026-07-27 revision
(external review point #23: a paper is not a research log). Each entry names the wrong
claim, the correct one, and what caught it, so the record survives without the paper
reading like a lab notebook.

Kept because it is genuinely useful: the pattern across these entries is that **every
error was in a number or a geometric factor computed by hand in prose**, never in a value
`scripts/audit_paper2_numbers.py` re-derives from `results/`.

### The disc/slab contrast: right argument, wrong campaign and wrong range

The sentence bounding what an independent acceptance sample buys read "on the disc, four of
the twenty large-model artifacts reach gate 1.000 ... an independent acceptance sample rejects
4 of 4 (accuracies 0.9944 to 0.9950)". Two errors, found 2026-07-29 because **no audit claim
covered that sentence** -- it was prose-only, which is the same exposure every other
correction in this file had.

* The four artifacts are in the **guided landing-prompt arm**, not the default disc arm. The
  default disc arm's incomplete artifacts reach 1.000 on *none*, so there was never anything
  there for a second sample to catch. "On the disc" was true of the instrument and misleading
  about the campaign.
* The accuracy range's upper end is **0.9997**, not 0.9950.

The corrected version is stronger than the wrong one, which is why it is worth stating rather
than trimming: across the disc instrument, **every** incomplete artifact reaching in-sample
1.000 is rejected -- 8 of 8 draws over **6 distinct rollout-seed blocks** (the two sizes at
k = (5,9) share their blocks, so 8 draws are not 8 samples; pooling them would repeat the
error review point #11 caught). And the gate is shown not to be merely strict: on the positive
control, where the artifacts are exactly right, it accepts 20 of 20. Four claims in
`scripts/audit_paper2_numbers.py` now derive all of it.

## The reconstruction layer: enumerated fields, three separate omissions

Found 2026-07-29 while extending the held-out re-scoring from the 625 artifacts that
existed when it was first run to all 1025. Three functions rebuilt an experiment's
identity by **enumerating** the fields they cared about, and each one silently dropped a
knob added later. None of these reached the manuscript --- the published held-out numbers
(625 artifacts, 430 accepted, the disc's 4/4 and the slab's 0/19) were computed before the
new campaigns existed, so they were never contaminated --- but two of the three would have
corrupted the extension, and one of them did until a test caught it.

* **`heldout.env_from_params` dropped `mode_effect` and `start_arc`.** It rebuilt the
  landing, clamp and evidence-dose campaigns as plain freeze discs, i.e. scored 240
  artifacts against the wrong truth. This is a wrong answer rather than a missing one, and
  it is the reason the extension was re-run from scratch for those campaigns. The param is
  named `start_arc` while the field is `start_arc_deg`, so a by-name pass-through would
  have missed it too: the fix carries every field, maps the aliases explicitly, and
  **raises** on any param it cannot classify, rather than dropping it.
* **`heldout.env_key` mapped every non-disc shape to `"sq"`**, so the slab collided with
  the square. Since the key is what the audit deduplicates samples on and looks the rarity
  up by, at a shared knob the slab would have been scored against the square's rarity in
  silence. It surfaced only because the slab's calibrated knob (5.5) had no `R_SOURCES`
  entry and that guard refuses to run --- luck, not design, so there is now a test that
  fails in CI when any committed campaign lacks an entry. The key also had to gain
  `mode_effect`, `start_arc` and `n_rollouts`, all of which change the rollout stream.
* **`paper2_statistics.treatment_key` omitted the same class of field three times**
  (`mode_effect`, then `mode_hint`, then `start_arc`/`n_rollouts`), each time collapsing
  distinct arms into one cell. Each was caught by that module's own one-draw-per-block
  invariant, which is what it is for.

The pattern is the one this file already records for hand-computed constants, in a
different layer: an enumerated list of fields is a hand-maintained constant. Where a list
could be derived from the type, it now is; where it cannot, an unrecognised entry is an
error rather than a default.

## Theory and certificates

| # | Wrong claim | Correct claim | Caught by |
|---|---|---|---|
| 1 | The joint gate-miss factor is $(1-r_1)^N(1-r_2)^N$ | The two per-mode contact events are dependent within a rollout; the joint factor is $(1-r_\cup)^N$, with a sharp distribution-free bracket and a sign rule for the product's error | Measuring $P(\text{both})$ at 50k rollouts: the dependence changes sign across the knob grid |
| 2 | The bracket's lower end is attained at disjointness | Attained at the Fréchet–Hoeffding minimal intersection $\max(0, r_1+r_2-1)$, which is disjointness only when $r_1+r_2\le 1$ | External review (2026-07-27) |
| 3 | $\varepsilon^\ast$ is a constant of the instrument | It is a property of a sample; the population threshold is $0$ and what stands in its place is a quadratic rate | The running minimum falls monotonically with $n$ ($0.420 \to 0.041$) |
| 4 | A diagnostic showed $\varepsilon^\ast$ hitting a hard floor | The diagnostic took the minimum over a *sorted* prefix, which is the global minimum by construction | Re-reading the diagnostic |
| 5 | The $\varepsilon$-flatness rate is a cart result, with the pendulum exponent as evidence | It holds for the whole semi-implicit family with additive `gain·a` and a clamp on the integrated coordinate; both instruments are theorems | External review (2026-07-27); the constant $C = T\,dt\,c$ was already generic in the script |
| 6 | Smooth learners cannot localize error | Bounded-Lipschitz pairs cannot localize *arbitrarily sharply at fixed amplitude*; the volume price is $((\eta-\varepsilon)/L)^{d+m}$. A compactly supported $C^\infty$ error is not excluded — the paper uses one | External review (2026-07-27) |
| 7 | Covering number 13 for the fence bound | 7 (a half-width had been used as a full width), then **12**, because the bound needs a *packing* number, not a covering one | Peer review 2026-07-25, then a counterexample: the planner is an adversary, not an optimal coverer |
| 8 | The step-$t$ certificate's $\rho$ and bound were 1.44 / 3.67 | Those numbers existed only in prose; the script certifies nothing at $N=40$ on any step-$t$ level set | The numeric audit, once extended to that block |
| 9 | A 2-D density fed into a 3-D hypothesis | $p_{3D} = p_{2D}/(2a_{\max})$ | Peer review 2026-07-25 |
| 10 | A per-cell *average* density used where the hypothesis wants an *infimum* | Minkowski erosion of $P$-shaped cells gives a genuine pointwise infimum | Peer review 2026-07-25 |
| 11 | `int(2R/rho)` with index clamping produced cells wider than $\rho$ — and the falsification test shared the bug, so it validated it | Every cell must be no wider than $\rho$, and the validation must not import the code path it falsifies | Peer review 2026-07-25 |
| 12 | A packing-ball probability that ignored $\partial U$ (factor $2^{d+m}$) | The ball mass must be intersected with $U$ | Peer review 2026-07-25 |
| 13 | $J_{\max}$ defined as a supremum of *expected* return | It must be a pointwise extremum; the earlier definition came out *below* the measured $J_{\mathrm{truth}}$ | Peer review 2026-07-25 |
| 14 | Conditioning on a rollout's whole trajectory leaves the action indicators independent Bernoulli | False: the action is recoverable from consecutive states, so the conditional law is degenerate. No factorization is needed — rollouts are i.i.d. | Internal check, 2026-07 |
| 15 | Handling the within-rollout dependence is worth 2% | It is worth a factor of $1.6$; the 2% came from a broken grid | The grid bug (#11) |
| 16 | The step-$t$ per-cell Wilson bounds hold at level $\delta/K$ | They were taken at a fixed $z = 4$, simultaneous only up to 1578 cells against a family of 9806. The level is now *derived* ($z = 4.4129$), and three quoted volumes shrink: $3.09 \to 3.02$, $6.13 \to 5.77$, $6.21 \to 5.27$ | `scripts/certificate_simultaneity.py`, external review point #14 |
| 17 | The $K=8$ validation sampled the step-1 law | It broke out of the loop after step 0, where $v_0 = 0$ exactly. Benign at the certified $n_v = 1$ (same joint law in the coordinates the partition sees) but 0/400 for a sound certificate at any $n_v \geq 2$. Fixed; the count moves $385/400 \to 384/400$ | `scripts/certificate_simultaneity.py` |
| 18 | The validation declared the bound violated whenever the point estimate exceeded it | A bound on a probability is falsified only if the whole interval lies above it. For a bound that is nearly an equality the point estimate lands above about half the time | This revision |

## Experiments and statistics

| # | Wrong claim | Correct claim | Caught by |
|---|---|---|---|
| 19 | Pooled Wilson bounds over both model sizes (0.84 cart, 0.824 pendulum) | The gate sample depends on the seed index alone, so the two sizes share samples: pooling doubles the synthesis draws, not the independent samples. Per-size bounds are 0.72 and 0.70 | Peer review 2026-07-25 |
| 20 | (recovered) Those pooled bounds are legitimate again | `--seed-offset` gives the second size a disjoint sample block, so the pooled $n$ is honest and 0.84 is restored | Re-running the large arm at offset 20 |
| 21 | The 2D mitigation's fences probe 17% / 43% / 68% of the circle | Those were violation counts divided by the budget — saturation assumed and restated as a percentage. Measured directly, the median probed arc is 0% / 0% / 87% | Peer review 2026-07-25 |
| 22 | The 2D mitigation degrades with distance as a longer transient | It fails outright in 7 of 20 episodes at the farthest knob; the distributions are skewed, not shifted | Per-episode census |
| 23 | The distinct fence count is about two thirds of the budget | At most a quarter; the raw counts are dominated by duplicate fences | Per-episode census |
| 24 | pass@40 marginally falsified the closed-form prediction on `wall@8` | A point estimate had been compared against an interval with its own interval unquoted; propagating the rarity's Wilson interval contains the measurement | Peer review 2026-07-25 |
| 25 | The gate-miss prediction is 0.6046 | That came from a superseded 2000-rollout rarity; at 30,000 rollouts it is 0.63 | Re-measuring the rarity |
| 26 | `0/156` supports "never" | It supports a per-block upper bound; the sampling unit is the (seed index, offset) block, and varying knob/shape/prompt adds treatments, not samples | Peer review 2026-07-25, sharpened by external review point #5 |
| 27 | The repair collapse is caused by a template prior over region forms | Consistent with one; not identified. The 1D-vs-2D contrast moves the trigger arity and the entry-barrier dimension together, along with the state dimension, the action parametrization, the mode count and the evidence structure | External review point #4 |
| 28 | The two CEM rows with `crossing = 0.0000` instantiate the bound's zero-reach branch | An observed zero is censored; the rows carry an upper bound on the crossing probability, and the play-cost claim is an inequality | External review point #7 |
| 29 | Certification "stayed sound" | It was *sample-consistent*: no accepted artifact contradicted a transition of the sample it was scored on. Soundness is reserved for a stated logical property | External review point #6 |
| 30 | The acceptance gate verifies the artifact | It scores the artifact on the sample it was refined against. An independent acceptance sample is a different test, and it is now run over all 625 versioned artifacts | External review point #1 |

## Instrument design

- The first cart calibration had a drag time constant of $10$ s against a $3$ s planning
  horizon, and nothing moved. The constraint is recorded in the paper as a design
  condition rather than as a history.
- I.i.d. per-step candidate sampling makes imagined displacement diffusive, so the truth
  and blind models rank all candidates identically and the mode never enters imagination.
  Piecewise-constant blocks plus constant candidates fix it.
- Point (Gaussian) reward lodes demand braking finesse random shooting lacks; sigmoid
  plateaus remove the parking problem.
- Three earlier mitigation designs (pre-state flee-balls, full-state point fences) were
  each defeated by the argmax planner probing around the fence. Only the one-sided
  refuted-prediction fence with segment truncation survived.
