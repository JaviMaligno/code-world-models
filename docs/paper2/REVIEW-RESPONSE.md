# Paper 2 — point-by-point response to the external review (2026-07-27)

Every numbered point and every minor point of the review, with the fix, where it landed,
and how it was verified. **No row may be marked DONE without evidence in its last column.**
Status vocabulary: `OPEN` · `IN PROGRESS` · `DONE` · `DECLINED` (with a stated reason).

Governing rule for this revision: where a claim was too strong, we first looked for the
experiment or the proof that earns the strong version; wording was weakened only when that
failed, and each weakening records what would earn it back.

## Critical points

| # | Review point | Fix | Status | Evidence |
|---|---|---|---|---|
| 1 | Synthesis/refinement sample doubles as the gate — "verification" is training-set consistency | Held-out three-way split `D_train`/`D_gate`/`D_eval` scored over all 625 versioned artifacts (no new LLM spend); acceptance redefined on `D_gate`; in-sample notion renamed *sample-consistency gate* | DONE | `scripts/heldout_gate_audit.py` + `heldout_gate_paper_numbers.py` over all 625 artifacts; §sec:heldout. Blocks verified disjoint; train sample reproduced 60/60. **36 of 463** in-sample-accepted artifacts are rejected by an independent gate (7.8%, [0.057,0.106]), 35 of 36 failing only on mode contacts |
| 2 | `danger = play_cost·(1-r)^N` is not defined as a probabilistic estimand | New risk estimand `D_N = E[PC(A(D))·1{accepted ∧ play-inadequate}]`, factorization conditions proved, bounds when the conditional cost varies; "exact" reserved for the gate-miss factor | DONE | `prop:risk` (risk estimand + factorization iff Cov = 0 + two-sided bounds) and `prop:twofactor` (exponents add) in §sec:estimand; both hypotheses measured: (i) 30/30, (ii) 60/60 exact; two-factor 0.399 inside [0.142,0.402] |
| 3 | "Smooth learners cannot localize" is too strong (a `C^∞` bump has compact support — our own arm) | Restated as bounded-Lipschitz / fixed-amplitude / arbitrarily-sharp; volume form added; representability vs learnability vs 1e-9 exactness vs the h=8 probe separated; headings and conclusion rewritten | DONE | `cor:locbudget` (volume price) + `rem:fourstatements` (representability / detectability / tolerance / learnability separated); §smooth and the conclusion retitled; our own $C^\infty$ bump named as the counterexample to the old wording |
| 4 | "Geometry-dependent via a template prior" is not causally identified | Rarity-matched **slab** ablation (trigger arity varied alone, inside the same 4D bi-modal plant) + `landing` prompt variant; claim stated at whatever the ablations identify | DONE | **Both campaigns run** (2026-07-29). The result is not the one the ablations were built to get, and is stronger: four candidate causes are now measured negatives (curvature, prompting/budget, trigger arity, variable identification), and the obstruction is located in the evidence by `prop:entryclass` — the freeze semantics keep every visited state outside the region, so a rule agreeing with the truth on the reachable set is exactly consistent with *every* sample and harmless by the same argument. Whether the target is identifiable is measurable in advance (`scripts/mode_identifiability.py`): the disc's far side is visited 4695 times, a slab's never. On the slab `gpt-5.4` passes the paper's repair criterion on 19/20 and recovers the rule in 0/20; on the disc the landing arm is 0/40. §sec:arity |
| 5 | Experimental unit unclear; `0/156` and `109/111` carry invalid binomial inference | `scripts/paper2_statistics.py`: unit hierarchy declared, per-treatment tables, block-level bounds, pooled comparator explicitly labelled invalid | DONE | `scripts/paper2_statistics.py`; 0/156 restated as 156 draws over **20 blocks** with an exact per-block upper bound 0.168; 109/111 restated at block level; the cart's 0.851 was **wrong at block level** and is now 0.708/0.772 with the estimand named. *(Superseded twice since this row was written: the grid-exactness audit moved 109 to **105/111 draws**, and the fourth review fixed the unit vocabulary — the current accounting is 105/111 draws over **70 distinct blocks, 64/70 exact on every draw**, pinned by `audit_paper2_numbers.py`; this row is kept as the round-1 record.)* |
| 6 | "Certification stayed sound" uses too weak a definition of sound | Vocabulary split: *sample-consistent* / *no observed false acceptance on the gate sample* vs *sound* for the stated logical property | DONE | *sample-consistency gate* vs *held-out gate* defined in §sec:theory; 'certified' in the acceptance sense replaced by 'accepted' throughout; linter rule `soundness-scope` at 0 |
| 7 | CEM result reads an observed zero as a zero query probability | `scripts/cem_crossing_bound.py`: ≥200× sampling, Clopper-Pearson upper bound, correct conversion to a `q_hit` bound; claim becomes `≤` | DONE | `scripts/cem_crossing_bound.py` at 200× the sample: at $x_\mathrm{wall}=8$ the zero was censoring **18 crossings in 1.28M** and $q_\mathrm{hit}\geq0.0029$, so the 'forces play_cost = 0' claim is refuted; at 10 the zero survives with $q_\mathrm{hit}\leq0.058$. Claim is now an inequality on all rows |
| 8 | `play_cost` depends on a small unstable random baseline | Raw return, raw regret, normalized regret, difference from random and paired intervals reported together; cross-instrument comparisons qualified | DONE | `scripts/play_cost_intervals.py`, 100 paired episodes on the three headline rows: raw return, raw regret, normalized play_cost, $J_\mathrm{rand}-J_\mathrm{blind}$ and paired bootstrap intervals now reported together. **The strong form was tested and failed**: on the cart the blind planner beats random in 86/100 seeds, so 'below random' there is a heavy-tailed-mean claim; the paper now says so and drops the rhetoric |
| 9 | 20 episodes/cell too few for several conclusions | 100 paired episodes on headline rows; paired bootstrap + randomization test; per-seed values and ECDFs; Clopper-Pearson for 7/20 | DONE | 100 paired episodes, 20{,}000-resample paired bootstrap, sign-flip randomization test and an exact sign test per row; per-seed values versioned for ECDFs; distribution shape (sd, median, IQR, skew) reported where it matters — PatchField2D's $J_\mathrm{truth}$ has sd 7.9. Clopper–Pearson for the 7/20 lock-in in `play_cost_intervals.json::mitigation_lockin_2d`, with the caveat that the census threshold is estimated from the same 20 episodes |
| 10 | "Deployment-realistic ε=0.01" unjustified; `N=40` inherited | Renamed *representative tolerance* and justified against state scale/simulator resolution, with the ε-sweep as the invariance argument; `N=40` motivated explicitly as inherited-for-comparability | DONE | renamed *representative tolerance*, justified against the instrument's two scales and the reward span, with the 8-order $\varepsilon$-sweep as the invariance argument; $N=40$ stated as inherited-for-comparability, with d@$N$ at three $N$ |

## Concrete theoretical points

| # | Review point | Fix | Status | Evidence |
|---|---|---|---|---|
| 11 | Joint-bracket sharpness needs `r1+r2 ≤ 1` | Condition added; the `r1+r2 > 1` case stated (lower end is `P(R1∪R2)=1`, minimal intersection `r1+r2-1`) | DONE | `rem:bracket`: the lower end is the Fréchet–Hoeffding minimal intersection $\max(0,r_1+r_2-1)$, which is disjointness only when $r_1+r_2\leq1$; our knobs are in that regime |
| 12 | ε-flatness proposition stated more generally than its proof | **Generalized**: proved for the semi-implicit family with additive `gain·a` and a clamp on the integrated coordinate, so cart and pendulum are both theorems | DONE | **generalized instead of scoped down**: `prop:epsrate` now proves the quadratic rate for the whole semi-implicit family with additive `gain·a` and a clamp on the integrated coordinate, with an approachability hypothesis for the ess-inf half. Cart and pendulum are both theorems; $C=T\,dt\,c$ ties the constant to the universal density constant |
| 13 | "Normalizers derived" are bounds, not the extremes | Corollary restated with `J̄`, `J̲`; table separating proved bound / attained / numerically approached | DONE | `cor:playcost` restated with the proved bounds $\bar J,\underline J$ and a computable second inequality; three statuses (proved bound / attained / numerically approached) separated in the text |
| 14 | Monte-Carlo coverage certificate not rigorous without a simultaneity account | Simultaneity ledger (partition fixed before MC? δ split? K selection? level sets?), union correction if selection occurred, relabelled if calibrated | DONE | `docs/paper2/CERTIFICATE-AUDIT.md` + `scripts/certificate_simultaneity.py`. Verdict: rigorous modulo a level the code accounts for. Disclosure added; selection survives Bonferroni over the whole 9674-test family and Clopper–Pearson. **Two real defects fixed**: the step-$t$ Wilson level was a hand-picked $z=4$ (now derived, $z=4.4129$ over 9806 cells; three volumes 3.09→3.02, 6.13→5.77, 6.21→5.27) and the validation sampled the step-0 law (fixed; 385→384/400) |
| 15 | "Boundary dimension" not well defined | Formal definitions of *trigger arity* and *mode-boundary dimension*; used consistently; reconciled with the fencing corollary | DONE | `def:arity` + `rem:twodims`: trigger arity $p$ and entry-barrier dimension $b$ defined and reconciled with `cor:fencedim`; the paper no longer claims either is the joint-space boundary dimension |
| 16 | Theorem inflation ("ten propositions are new") | Regrouped into four families; algebraic identities demoted to lemmas/remarks | DONE | contributions regrouped into four families; supporting identities named as such and moved to the supplement |

## Design and reproducibility

| # | Review point | Fix | Status | Evidence |
|---|---|---|---|---|
| 17 | No compact, complete LLM protocol specification | New appendix from `docs/paper2/PROTOCOL-FACTS.md` (system/synthesis/refine messages verbatim, budgets, parsing, retries, sampling params, deployments, calls per seed, classification rules) | DONE | `docs/paper2/appendix-protocol.tex` from `PROTOCOL-FACTS.md`: verbatim messages, budgets, parsing, retry policy (SDK-level only), sampling params actually sent, deployments, calls per seed, and the operational classification rules |
| 18 | Closed models hinder reproduction | Per-artifact hashes and versioned transcripts recorded; call/token accounting; open-weight arm complete on all instruments | DONE | call counts exact (`results/repro_manifest.json`, synced by `scripts/sync_repro_facts.py`); transcripts versioned; token usage recorded as absent with the reason. The open-weight 2D arm was completed on 2026-07-31: the three `incomplete` cells ran against the SAME weights (`Qwen/Qwen3-Coder-30B-A3B-Instruct`, bf16 from the Hub) served by a self-hosted vLLM on Modal (`scripts/modal_qwen3coder_vllm.py`) after every HF Inference Providers token 402'd; the committed results file's top-level `compat_base_url` still names the HF router because the resume guard treats the URL as provenance, not treatment --- the mixed serving path is recorded HERE and in the paper's ablation-3 paragraph. Result: full arm 3/3 clean at gate 1.000; incomplete arm refused 3/3 (0.993--0.997), mode in every training block, none accepted held-out --- the family's 1D stall-and-refuse class, reproduced on 2D. One further provenance fact, true of the WHOLE compat arm and not just these cells: the client pins only `max_tokens`, so sampling parameters were server-default on both serving paths (each HF-router provider has its own; vLLM reads the model's generation_config) --- the compat arm was never sampling-pinned, which is consistent with its role as a spot-check and is stated here rather than discovered later. |
| 19 | Reproducibility appendix incomplete | Python version, frozen dependency list, commit/tag, hardware, per-campaign runtime, LLM cost, master command, JSON→table manifest, licence, `env.example` | DONE | `docs/paper2/appendix-repro.tex`: platform, the one-machine gap stated, frozen deps + the missing release tag, the JSON→table manifest with three checking tiers and one gap, runtime as a lower bound, cost as a range with the reason, licence (Apache-2.0 + CC-BY-4.0), `env.example` |
| 20 | Post-hoc analysis and researcher degrees of freedom | Dated ledger: PRE-SPECIFIED / CONFIRMATORY / DIAGNOSTIC / EXPLORATORY ABLATION / POST-HOC, from git history; "pre-registered", "falsified", "pins the mechanism" audited against it | DONE | `docs/paper2/appendix-prespec.tex` from git dates. **Two claims were unsupported and are corrected in the text**: 'the pre-registered risk' and 'we predicted partial repair'; a third now states its chronology |
| 21 | Related work too brief; CEGIS not discussed | Twelve literatures added with verified references; CEGIS treated as the direct analogue with the difference named (a CEGIS oracle is complete relative to a specification; a sampling gate is not); companion-paper dependence removed from the argumentative load-bearing path | DONE | `docs/paper2/related-work.tex`, 12 literatures, ~2300 words, CEGIS first with the oracle difference named. All **59** new bib entries verified (54 via Crossref/arXiv, 5 by hand); `results/bib_verification.json`, checked by the audit |

## Narrative and presentation

| # | Review point | Fix | Status | Evidence |
|---|---|---|---|---|
| 22 | 50 pages, no hierarchy, too many contributions | Hierarchy: main article + labelled Supplementary Material. Contributions: audited by content, not by length. | PARTIAL on length, DONE on the other two | The review makes three complaints and only one is about size. **Hierarchy** is fixed: `scripts/restructure_paper2.py` split the manuscript at a labelled divider and moved thirteen blocks behind it. **Too many contributions** was made mechanical rather than argued: a numbered result earns body space if a *measurement* leans on it. Measured, the body was 11/13; the two exceptions were scope qualifiers sitting seven pages from the numbers they qualify, now cited at the measurement, so it is **13/13**, checked in CI by `scripts/check_paper_build.py`. That audit also found five results stated and never cited, a label defined twice (a cross-reference in Limitations resolved to the appendix instead of the body) and two empty headings left by the restructuring --- all fixed, none of them findable by counting pages. **Length** is not met: the main article is ~38 pp of an 87-page compilation (Supplementary Material from p. 39), not the 12--16 asked for. We state the reason rather than working around it: point #21 asked related work to *grow* (one paragraph to twelve literatures, ~4 pp), and answering the review added four propositions, an independent re-scoring of all 1025 artifacts and eight campaigns. Cutting to 16 would require moving the independent-gate section and half the theory behind the divider --- burying the answers to points #11 and #13 to satisfy a page count. Every body section is now shown to carry weight; we submit that as the response to "too many contributions" and accept the length as stated. |
| 23 | Too much self-referential prose | Register purged; history to `docs/paper2/CHANGELOG-corrections.md`; enforced by `scripts/audit_paper_claims.py` | DONE | 48 flagged passages removed to `docs/paper2/CHANGELOG-corrections.md`; linter rule `process-prose` at 0 |
| 24 | Immediate textual contradiction (covering-number analogue "left open", then presented) | Residual sentence deleted | DONE | the residual sentence is deleted |
| 25 | Titles and headings overclaim | Four flagged headings and their siblings de-escalated to their actual scope | DONE | four headings de-escalated; linter rule `modal-scope` at 0 |
| 26 | Abstract overloaded | Rewritten to problem / main theory result / main empirical result / 2D limitation / implication | DONE | rewritten to problem / theory / empirical / 2D limitation / implication; no pooled counts |

## Minor points

| # | Review point | Fix | Status | Evidence |
|---|---|---|---|---|
| m1 | "Two independent modes" — distinct but dependent | Wording corrected everywhere; the measured dependence cited | DONE | wording corrected; the measured dependence is cited where the modes are introduced |
| m2 | "Zero-curvature square" | → "axis-aligned square with flat edges" (corners are not differentiable) | DONE | all occurrences → 'axis-aligned square with flat edges' |
| m3 | "Below random" needs the raw return beside it | Raw returns added at every such claim | DONE | raw returns beside every normalized figure; the planner section points at the measured decomposition instead of asserting 'below random' |
| m4 | Printed zeros should carry `<` or an interval in the table | Table cells carry their bound; global convention no longer load-bearing | DONE | `scripts/apply_table_bounds.py` (idempotent, values read from `results/` at runtime): 43 cells across 7 tables now distinguish censored zero / rounded-away positive / demonstrated zero; the convention paragraph is no longer load-bearing; linter rule `printed-zero` at 0 |
| m5 | Four-decimal 2D rarities exceed the resolution | Truncated to the resolution the sample supports | DONE | `tab:patch2d` truncated to the 3 decimals 600 rollouts resolve |
| m6 | `d@40` quoted without an interval | Interval propagated or the figure withdrawn | DONE | `d@N` bands are the rarity interval propagated through $\mathrm{play\_cost}\cdot(1-r)^N$ (monotone, so the corner pair) — stated in the figure captions; table cells that would round to zero print in exponent form |
| m7 | Figures lack uncertainty bands | Bands added where the data supports them | DONE | `scripts/make_paper2_figures.py` now draws the propagated rarity band on `fig:threshold`, Wilson bars on `fig:reach` with the truth planner's censored zero as an upper bound, and paired intervals on `fig:axes`; all three captions say what the bands are |
| m8 | Unclear whether episode seeds are reused across knobs and planners | Stated from the code | DONE | stated from the code in §sec:planner: episode seeds are $900{,}000+1000i$ (synthesis) and $1000i$ (sweeps), so they recur across knobs, instruments and both planner families, and the three arms of a row share them |
| m9 | Seed pairing must enter the statistical analysis | Paired bootstrap/randomization used throughout the play claims | DONE | same paragraph states that every play interval is paired (bootstrap or randomization over seed triples), which is what makes $10^{-4}$ differences meaningful at 20 episodes |
| m10 | `J_truth` sometimes called "optimal" | Removed; MPC-with-true-model is not proved optimal | DONE | 'optimal' removed where it implied MPC optimality |
| m11 | "Truth planner" needs emphasis that it is the true-model planner, not an optimal policy | Stated at first use and in the definition | DONE | at first use: the truth planner is the *same* random-shooting MPC given the true dynamics, a reference and not a proved optimal policy |
| m12 | "Almost-everywhere exact" is misleading (small measure, not zero) | → "exact outside the mode region" | DONE | → 'exact outside the mode region' everywhere including the abstract |
| m13 | "Rarity" is a rollout-level probability, not a region volume | Reminded in the definition | DONE | the definition now says rarity is the probability that a whole gate *rollout* contains a contact, not the region's volume |
| m14 | `μ_query` is not a measure | Renamed `q_hit(E)` consistently, including in propositions and proofs | DONE | renamed `q_hit(E)` in all 13 sites; the not-a-measure caveat is now in the definition |
| m15 | Funding, conflicts of interest, data availability, AI-use declaration | Added | DONE | new `\section*{Declarations}`: funding, competing interests, data/code availability with both licences and the missing DOI release, and a use-of-AI declaration |
| m16 | Anonymization | Author/affiliation/URL/repo occurrences listed; venue policy decision left to the author | DONE | the same section lists the four identifiers and the nine companion-paper citations a double-blind version must change; the venue decision is left to the author |
| m17 | The 2026 CWM citation and the companion paper must be publicly available at submission | Availability status of each recorded; no argument left resting on an unavailable work | DONE | both checked; no argument rests on an unavailable work |

## Verification of this revision

Run from the repository root; all four were green at the time of writing.

| check | command | result |
|---|---|---|
| tests | `.venv/bin/python -m pytest -q` | **578 passed** |
| numbers | `PYTHONPATH=src .venv/bin/python scripts/audit_paper2_numbers.py` | **657 values, all agree** |
| claims | `.venv/bin/python scripts/audit_paper_claims.py docs/paper2/main.tex` | **0 errors, 0 warnings** across all six rules |
| build | `pdflatex` ×2 + `bibtex` in `docs/paper2/` | 0 overfull boxes, 0 undefined references; page counts move with each revision and are NOT tracked here --- the current split is measured from `main.aux` (conclusion page vs first `sup:` label), not from this table |

## What remains open, and why

* **Review point 4 is now DONE, and the answer changed the paper.** Both campaigns ran on
  2026-07-29. The slab ablation could not answer the arity question — its target is not
  identifiable, which the reachability measurement establishes rather than assumes — but it
  produced Proposition `prop:entryclass` and, with the landing arm, the contrast that bounds
  what an independent gate buys: on the disc it rejects 4 of the 4 artifacts that passed
  their own gate; on the slab, 0 of 19, because there is nothing to reject. Two corrections
  followed, both lowering a headline: the mode probe is not a sufficient repair criterion,
  and the 1D count is 105 of 111, block-level 30/36 [0.672, 0.936].
* **That decisive experiment was run, and it refuted the hypothesis behind it.** Two
  instruments lift `prop:entryclass`'s premise — the mover stops inside the region
  (`landing`) or is projected onto its boundary (`clamp`) — with rarity identical, the trap
  intact, and the premise verifiably broken (4614 and 233 separating transitions against
  freeze's zero). Repair does not return: 0 of 40 each, no artifact passing the gate at all,
  the same half-plane template at the same constant. The two confounds are complementary and
  both covered: `landing` gives 11× more mode evidence and fails; `clamp` matches freeze's
  evidence quantity and fails. So the censoring is **not** why region induction fails, and
  the region-template prior survives as a mechanism after seven ablations rather than as a
  description. `prop:entryclass` keeps its two jobs: explaining the slab's nineteen
  accepted-but-wrong artifacts, and bounding what an independent gate can catch.
* **That positive control was run too, and it locates the frontier.** Two levels, 20 seeds
  each: given the region's form AND its centres, the withheld radius is inferred **exactly in
  20 of 20** (IoU 1.000, exact on all 9020 grid points, all 20 accepted by an independent
  gate); given the form alone, **0 of 20**, with 16 writing a point. A second control from
  outside the pipeline — a plain least-squares circle fit on the same evidence — recovers both
  constants on **12 of 20** samples. So the failure is not the evidence, not an inability to
  fit constants, and not representational: what is not induced is the region's **form**, and
  once the form and its location are given the constants follow to float precision. On the 8
  samples where the trivial fit also fails, the negative is not attributed to the synthesizer.
* **Open**: nothing experimental. The evidence-dose experiment ran (ablation 8): raising the
  contacts' angular coverage to where a three-line least-squares fit recovers the region on
  20 of 20 samples leaves the synthesizer at 0 of 20, so the prior does not yield to
  coverage. The only open item is a DOI deposit, below.
* **Review point 18 (closed-model reproduction) is now DONE.** Call counts and transcripts are
  exact; the open-weight 2D arm was completed via a self-hosted vLLM serving the same weights
  (see row 18 for the provenance note).* **An archived release.** The git tags `paper2-v1.0-review-response` and
  `paper2-v1.1-evidence-dose` exist and are pushed, so a citable revision identifies the
  code behind each table. A **DOI** over a tag does not exist. To be accurate about where
  that item came from: the review asked (m15) for a *data-availability statement*, not for
  a DOI; the DOI is this response's own addition, arXiv does not require one, and an
  earlier draft of this file wrongly called it "required before submission". It is a
  nice-to-have that needs a Zenodo/figshare account, and it is the author's call.
