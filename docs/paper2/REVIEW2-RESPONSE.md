# Paper 2 — response to the second external review (2026-07-30)

Same discipline as the first round: every point gets a verdict verified against the text or
the data before anything is edited, a strengthen-before-weaken pass, and evidence per row.
Process commentary goes here and to `CHANGELOG-corrections.md`, never into `main.tex`.

**Reviewer's overall position:** major revision — no longer for missing experiments but for
(1) two central propositions false as stated, (2) a third proof that mishandles the clamp,
(3) causal overinterpretation of the ablations, (4) pseudo-replicated inference in the
held-out audit, (5) contradictions between abstract, expanded results and conclusion.

## Verdicts and actions

| # | Point | Verdict after verification | Action | Status |
|---|---|---|---|---|
| 1.1 | `prop:risk`: "X constant on G" is not sufficient for the factored form | **Reviewer RIGHT.** Their counterexample checks: X=1_G, P(G)=1/2 gives D_N=1/2 vs E[X]P(G)=1/4, Cov=1/4. Constant-on-G gives the CONDITIONAL form D_N = E[X\|G]P(G) = c·P(G), not the E[X] form. The parenthetical "(a single fixed blind model)" is the globally-constant case, which does work | Restate: "in particular it holds when X is almost surely constant". Add the P(G)>0 convention for E[X\|G]. Add the salvage the reviewer's own logic implies, which is a STRENGTHENING: if X is constant on G with value c, then D_N = c·P(G) exactly via the conditional form — and c = the accepted-artifact cost is what the paper already reports | DONE |
| 1.2 | `prop:twofactor` false under its hypotheses: (i) is one-directional, so P(blind shipped) = (1−r)^{N_tr+N_g} does not follow | **Reviewer RIGHT.** The proof itself says the blind event *contains* the train-miss event, then asserts equality. Correct statements: P(train misses R ∧ shipped) = (1−r)^{N_tr+N_g} exactly under (i)+(ii); P(blind shipped) = (1−r)^{N_tr+N_g} + P(blind ∧ train hits R)·(1−r)^{N_g} ≥ the law, equality iff (i) is an iff — which 2D refutes (blind with the mode in sample) and 1D violates in 6 of 111 blocks | Conclusion restated as the exact probability of the specific event; general case given as a displayed decomposition with the lower-bound reading; the excess term named and tied to the measured 105/111 and the 2D campaigns. The empirical two-factor test already measured the *event* (train-miss ∧ gate-miss), so the data needs no change — the theorem now says what the test tested | DONE |
| 1.3 | `prop:epsrate` proof: conditional law of θ_t has an atom at the stop, not uniform; ess-inf part needs clamp-free accessibility | **Reviewer RIGHT on both flaws, and right that the bound survives.** The strip [θ_stop−εdt, θ_stop) is disjoint from the atom {θ_stop}, so the density bound holds on the no-clamp branch, which is the only branch meeting the strip; but the proof asserted "the law is uniform", which is false (it is censored-uniform). The ess-inf step used the unclamped two-action Jacobian without guaranteeing a clamp-free two-step history | Proof rewritten by explicit branches (clamp-at-t gives the atom, clamp-at-(t−1) gives a 1-D null set in the plane, clamp-free branch carries the density); approachability hypothesis strengthened to require a positive-probability clamp-free two-step window, stated checkably; the measured 0.0018 stays as the empirical check | DONE |
| 1.4 | "an independent gate is free" too strong | **Reviewer RIGHT.** Only the miss exponent of the specific event depends on N_tr+N_g; nothing is claimed about synthesis quality at fixed total budget, total risk D_N, or compute — and the experiment compared 40 vs 40+40, not a fixed-budget redistribution | All three sites replaced by the exponent statement with the explicit non-implications; the 40 vs 80 design stated where the experiment is described | DONE |
| 2.1 | "below random at every rarity knob" contradicts the 100-episode section | **Reviewer RIGHT.** The paper's own §100-episodes says cart favours blind in 86/100 seeds and pendulum is false; only PatchField2D is unequivocal | Abstract, conclusion and related-work rewritten around the robust claim: planner exploitation with near-total regret and persistent boundary pinning; "below random" scoped to the heavy-tailed mean where measured | DONE |
| 2.2 | "whenever the sample revealed contacts" and "single phantom-mode exception" contradict the audit | **Reviewer RIGHT.** 105/111, four GPT phantom stops, plus Claude's (outside the held-out audit) | Abstract quantified (105 of 111); conclusion's "single exception" replaced by the full accounting | DONE |
| 2.3 | "programs, not smooth function classes" reintroduces the corrected overclaim | **Reviewer RIGHT.** The body's own §smooth keeps C∞ compactly-supported errors alive; the conclusion slogan denies it | Conclusion restated as the bounded-Lipschitz claim the paper proves | DONE |
| 3.1 | The arity ablation does not exclude arity | **Reviewer RIGHT — and the paper already knows it** (tab:ablations row 4 "excludes nothing"); abstract and the mechanism paragraph contradicted the table | Abstract and mechanism paragraph now list arity as *not answerable on this instrument* rather than excluded | DONE |
| 3.2 | Template prior not causally identified as THE mechanism | **Reviewer RIGHT.** The interventions exclude named alternatives; they do not exhaust the space (textual-fitting incapacity, memoryless refinement, prompt representation, absent sysid objective all remain compatible) | "What remains as the mechanism" → the description that survives every intervention tried, with the uneliminated alternatives named; causal language removed | DONE |
| 3.3 | "The form is what is not induced" too clean: with the form GIVEN (hint-centre, and at 185°), still 0/20 | **Reviewer RIGHT.** The failure is the conversion of contacts into a *located* parameterized rule; form alone does not rescue it, form+location does | Slogan replaced everywhere by the two-sided statement (reviewer's proposed sentence, essentially) | DONE |
| 4 | Identifiability should be relative to a hypothesis class | **Reviewer RIGHT** (their §4 arrived garbled, but the recoverable point is this one and it is correct: finitely many contacts never determine an arbitrary region) | `sec:arity`'s identifiability paragraph now states the class (regions from the paper's template library / the circle-fit class) and "identified" is defined relative to it | DONE |
| 5.1 | Wilson/CP intervals over 647/610 draws are pseudo-replication | **Reviewer RIGHT.** Draws share rollout-seed blocks across campaigns and treatments — the same unit error the first review caught elsewhere | Inferential intervals removed from the draw-level counts; counts kept as descriptive; block-level accounting stated alongside | DONE |
| 5.2 | "exact outside the mode" overstates: exactness is on D_eval under the eval distribution | **Reviewer RIGHT** | Wording scoped: "exact on the 100-rollout evaluation sample outside the mode"; the CP bound removed with the intervals (5.1) | DONE |
| 5.3 | 647 − 40 = 607 ≠ 610: explain | **Reviewer RIGHT, and their guess is exactly the recorded cause**: `n_reverse_regressions = 3` in the audit JSON — three artifacts below 1.000 in-sample pass the independent gate | Sentence added with the count, read from the JSON; audit claim pins it | DONE |
| 5.4 | "Both hypotheses hold" too global: (i) checked 30/30 on the cart headline cell only, and known false in 2D | **Reviewer RIGHT** | Paragraph heading and text scoped to the cell where it was checked | DONE |
| 6.1 | "two independent modes" misleading | RIGHT — the paper itself later measures dependence | → "two distinct modes" | DONE |
| 6.2 | Conformal sentence in related work | RIGHT — conformal yields calibrated sets a planner could treat as uncertainty | Restated: the marginal guarantee is over the calibration distribution and does not control the planner's query distribution | DONE |
| 6.3 | "invisible to all three anchors" false for model-independent safety automata | RIGHT | Qualified: a safety monitor specified independently of the learned model does catch it; what fails is monitors derived from the model or its training sample | DONE |
| 6.4 | "certifies nothing in the CEGIS sense" | RIGHT to qualify: it certifies absence of counterexamples in a sample | Qualified | DONE |
| 6.5 | "sample coverage is the whole game" contradicts 2D | RIGHT | Scoped to the measured 1D/GPT regime | DONE |
| 6.6 | "strict gate soundness" vs the paper's own reserved use of "sound" | RIGHT | → sample consistency | DONE |
| 7.1 | Reduce the main paper | **Declined with reasons, as in round 1 (#22):** every body section now carries measured weight (13/13 numbered results back a measurement, CI-checked); cutting to reviewer length buries the answers to their own points | — | DECLINED (argued) |
| 7.2 | Homogenize identified/recovered/accepted/sample-consistent/exact-on-eval/globally-exact | RIGHT | Terminology pass done with the fixes above; the claims linter's soundness-scope rule already polices "certify/sound" | DONE |
| 7.3 | Per-seed distribution figure for the three 100-episode experiments | RIGHT — the data is per-seed in results/ | Figure added (`make_paper2_figures.py`), referenced from the 100-episode section | DONE |
| 7.4 | Anonymous version + DOI | Author's call (account needed); recorded, not blocking | — | OPEN (author) |
| 7.5 | Separate confirmatory / exploratory / post-hoc findings | Already the pre-specification appendix's job | Every campaign carries a dated classification in the ledger (`sup:prespec`, B1–B21, C1–C10); nothing new needed | DONE (pre-existing) |

## The strengthen-before-weaken ledger for this round

* 1.1 — the correct salvage is *stronger for practice* than the broken clause: constancy on
  G gives exactness of the **conditional** product, and the conditional mean is what the
  paper reports. Nothing weakened; a false sufficient condition replaced by a true one.
* 1.2 — the theorem now asserts an **exact** probability for the event the empirical test
  already measured, plus an honest decomposition whose excess term the paper *measures*
  (6/111 on 1D, gross in 2D). The law survives as exact-for-the-event and lower-bound-for-
  blind-shipped.
* 5.3 — a suspected accounting error turned into a verified, recorded quantity.
* 2.1/2.2 — weakenings, and correct ones: the measured distributions decide.
