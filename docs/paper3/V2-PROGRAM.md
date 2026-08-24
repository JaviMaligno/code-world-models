# Paper 3 v2 + paper-4 seeds: the two-bucket program (2026-07-24)

Decision recorded with Javier: the trilogy closes the original program;
remaining work splits into two buckets. Bucket 1 extends paper 3 (same
thesis, harder settings → v2 of the same preprint). Bucket 2 holds the only
genuine paper-4 seeds; each is prototyped CHEAPLY first, and the outcome
decides (positive & substantial → paper 4 candidate; negative or
incremental → folds into paper 3 v2 as honest scope). After the experiments
settle: the audit ran 2026-07-24 (THEORY.md) and its residue is now the
standing **RESULTS-TO-PROVE list (T1–T8, THEORY.md)** — attacked in
Javier's order, on his timing; nothing on it is scoped out. Original note:
a **measured→provable audit** (sweep every measured-only claim in
papers 2–3 / THEORY.md / EXPERIMENTS.md for statements that are actually
provable now — e.g. the persistent-fence planner-equivalence, the
aligned-channel degeneracy, the Rips flip location via birth/death radii,
hidden≡closed observational identity, r(n) concentration order).

## Bucket 1 — paper 3 v2 extensions (same thesis, run and fold as measured)

STATUS 2026-08-24 (second session): **everything in this bucket has now
RUN**, the thin-neck included. The rows carry each outcome and its file,
checked against `results/` and the EXPERIMENTS.md sections named in each row.

| # | experiment | cost | status |
|---|---|---|---|
| 1c | **Synthesis-side dose curve**: D-cell (closed ring, inside+tda), evidence N ∈ {40, 80, 160, 320}, 20 seeds mini. Note the pipeline couples evidence and gate (the gate IS the sample) — pre-registered reading: the deployed pipeline's dose curve. H: gate-pass stays ≈0 (parameter identifiability is not dose-limited; the sensor factorial already showed β̂₁ isn't). | Azure mini ~2h | **DONE** — H confirmed: 0/20 at every dose, and the sharp reading is that the median artifact poses r = 4.0 (a round number) whether it saw 40 or 320 rollouts. Files `..._N{80,160,320}.json`; EXPERIMENTS.md "Dose curve". |
| 1a | **Square ring** (Chebyshev annulus, zero curvature, corners): mechanism grid + synthesis cells A/D. Pairs with paper 2's square ablation: do models write ROUND rings on square-ring evidence (template prior on the separator)? Honest note: Chebyshev distance is 1-Lipschitz, so Lemma 2 SURVIVES — this is still the metric side; it ablates curvature-of-the-separator, not the metric proof. | env + CPU + Azure | **DONE** — models write ROUND rings on SQUARE evidence (11/12 posed structures at corner ratio ≈1.0, 12/12 written with hypot). Everything else norm-invariant. Files `..._mini_sqgap0{,-in_pv-tda}.json`; EXPERIMENTS.md "Square ring". |
| 1d | **Smooth learners on the ring** — DEPRIORITIZED (2026-07-24): paper 2's smoothness-forbids-localized-error proposition is geometry-independent and already covers the ring in principle; the probe code is 1D-hardcoded and porting it buys a foregone confirmation. Revisit only if a reviewer asks. | — | deprioritized |
| 1b | **Multi-chamber** (nested annuli; gauge structure is nested; D-cell from the middle chamber). | design + all arms | **DONE** — three mutually reach-null chambers verified; D-cell from the middle chamber 0/20, and ZERO nested artifacts: the loop does not even pose layer two. The true two-circle cloud draws a detector lottery {0:9, 1:10, 2:1}. File `..._mini_gap0-m2-mid_pv-tda.json`; EXPERIMENTS.md "Second wave". |
| — | thin-neck ring (thickness < Δ locally: where Lemma 2's hypothesis fails, leap-through becomes possible and measurable) | env + CPU | **DONE (2026-08-24)** — designed (`THIN-NECK-DESIGN.md`, pre-registered, committed before the run), proved (local crossing lemma in Lean: entry needs a step > neck), witnessed (deterministic leap at neck 0.5), and swept at 30k. Headlines: planner leak only at neck 0.1 (pc_blind 0.451); **certified-and-costly at neck 0.2–0.4** (fill: 0 disagreements in 320k transitions, pc 0.57/0.50); hidden necks bit-identical to closed at all six thicknesses. `results/ring2d_thin_neck.json`; EXPERIMENTS.md "Thin-neck ring". LLM synthesis ran too (2026-08-24, Azure mini, neck 0.1/0.2/0.4, incomplete arm): 0/60 artifacts write any angular structure — even the two seeds whose evidence contained leaps answered with a reward threshold and free flight; audit absorbs the cells at 34/34. Files `..._mini_gap0-nk{0.1,0.2,0.4}.json`; EXPERIMENTS.md "Thin-neck LLM synthesis". |

## Bucket 2 — paper-4 seeds (prototype-first; outcomes decide)

STATUS 2026-07-24: 2a PASSED (pc 1.769 -> 0.029; lie-rate symmetry). 2b
STRONG SIGNAL + open research problem (censored Rips 22/25 vs plain 8/25;
naive edge deletion creates infinite-bar artifacts; the right object is
relative homology). 1c DONE (dose cannot buy repair; parameters are guessed
round numbers). The constructive thesis for a paper 4 now has two working
legs + one identified research problem — the strongest configuration for a
genuine fourth paper so far.

| # | seed | prototype | decision gate |
|---|---|---|---|
| 2a | **Trust-inversion / optimism defense** (the dual of distrust: the invented-mode cell where every fence variant is inert at pc 1.769). Freedom fences: where the model predicted freeze and the truth MOVED, patch imagination locally with the pinned integrator (the contract's own integrator — legitimately known). | CPU, mitigation.py | pc 1.769 → small ⇒ the constructive program has its second leg |
| 2b | **Trajectory-censored filtration** (the sensor that works): drop Rips edges that cross certified-free space (free trajectory segments). H: censored β̂₁ = 0 at γ = 0.6 where plain Rips says 1 at any density. | CPU, tda.py variant | works ⇒ third leg; then "defenses matched to failures" is a paper-4 thesis (constructive, with the persistent nerve fence as leg one) |
| 2c | **Active boundary learning** (pay the covering cost optimally by seeking violations) | after 2a/2b | **DONE** — three routes to Prop 10's (COV), ranked by lesson-efficiency: geometry (2 lessons) > exploration (50+11) > passivity (9, with regressions). PERSISTENCE is the necessary ingredient in all three. `results/ring2d_active_boundary.json`. |
| 2d | **TubeField-3 + linking** (non-separating mode; Prop 4's homological upgrade — the only genuinely new math) | new instrument + math | **DONE, and it did differ** — same rarity, same trivial topology, pc_blind 0.019 aligned vs 0.898 offset: the danger dichotomy is purely PATH-relative, and separation contributes only the exact-gauge side. The ring conflated the two. `results/tubefield_mechanism.json`; T8 is the math it opened (RESOLVED). |

Rule (Javier, 2026-07-23/24): a paper 4 exists only if bucket 2 matures into
a thesis ("the defenses that work" and/or "non-separating modes"); anything
incremental folds into paper 3 v2. No half-baked preprints.

## Off-programme — DONE 2026-08-24 (second session)

**ring2d is inside the held-out audit.** The decision went to **r, the firing
rarity** (the audit's events are contacts; r_int is Lemma 2's curve and rides
along as labelled provenance), both heldout branches exist with 21 R_SOURCES
entries, and `heldout_gate_audit.py --instruments ring2d` ran to completion:
663/663 artifacts, two-factor law inside Wilson95 at 31/31 campaigns, the 2x2
exact on the incomplete arm, and one 2-ULP-wide point-trap gate hack exposed
by the reproduction check. `results/heldout_gate_audit_ring2d.json`;
EXPERIMENTS.md "ring2d held-out audit" has the numbers and the decision's
reasoning.

Three measured results worth folding in wherever the ring's phenomenology is
written up: a HIDDEN channel gives the closed ring's rarity to five decimals
with the same interval (reach, not topology) — and its campaigns audit
correctly under that r; interior entry at small gaps is nonzero — the
600-rollout calibration read it as zero, which is a theorem only at gap = 0;
and the inside-start cells produce globally wrong models rather than blind
integrators (237/320 off-mode eval exceptions vs 87/343 outside).
