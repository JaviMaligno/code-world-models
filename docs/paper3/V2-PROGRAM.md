# Paper 3 v2 + paper-4 seeds: the two-bucket program (2026-07-24)

Decision recorded with Javier: the trilogy closes the original program;
remaining work splits into two buckets. Bucket 1 extends paper 3 (same
thesis, harder settings → v2 of the same preprint). Bucket 2 holds the only
genuine paper-4 seeds; each is prototyped CHEAPLY first, and the outcome
decides (positive & substantial → paper 4 candidate; negative or
incremental → folds into paper 3 v2 as honest scope). After the experiments
settle: a **measured→provable audit** (sweep every measured-only claim in
papers 2–3 / THEORY.md / EXPERIMENTS.md for statements that are actually
provable now — e.g. the persistent-fence planner-equivalence, the
aligned-channel degeneracy, the Rips flip location via birth/death radii,
hidden≡closed observational identity, r(n) concentration order).

## Bucket 1 — paper 3 v2 extensions (same thesis, run and fold as measured)

| # | experiment | cost | status |
|---|---|---|---|
| 1c | **Synthesis-side dose curve**: D-cell (closed ring, inside+tda), evidence N ∈ {40, 80, 160, 320}, 20 seeds mini. Note the pipeline couples evidence and gate (the gate IS the sample) — pre-registered reading: the deployed pipeline's dose curve. H: gate-pass stays ≈0 (parameter identifiability is not dose-limited; the sensor factorial already showed β̂₁ isn't). | Azure mini ~2h | **launching** |
| 1a | **Square ring** (Chebyshev annulus, zero curvature, corners): mechanism grid + synthesis cells A/D. Pairs with paper 2's square ablation: do models write ROUND rings on square-ring evidence (template prior on the separator)? Honest note: Chebyshev distance is 1-Lipschitz, so Lemma 2 SURVIVES — this is still the metric side; it ablates curvature-of-the-separator, not the metric proof. | env + CPU + Azure | queued |
| 1d | **Smooth learners on the ring** (paper 2's probe, ring evidence, inside and outside starts). | CPU minutes | queued |
| 1b | **Multi-chamber** (nested annuli; gauge structure is nested; D-cell from the middle chamber). Needs design. | design + all arms | second wave |
| — | thin-neck ring (thickness < Δ locally: where Lemma 2's hypothesis fails, leap-through becomes possible and measurable) | env + CPU | second wave |

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
| 2c | **Active boundary learning** (pay the covering cost optimally by seeking violations) | after 2a/2b | — |
| 2d | **TubeField-3 + linking** (non-separating mode; Prop 4's homological upgrade — the only genuinely new math) | new instrument + math | phenomenon differs from separating case ⇒ paper-4 co-thesis |

Rule (Javier, 2026-07-23/24): a paper 4 exists only if bucket 2 matures into
a thesis ("the defenses that work" and/or "non-separating modes"); anything
incremental folds into paper 3 v2. No half-baked preprints.
