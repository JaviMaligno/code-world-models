# Codex adversarial review of paper 3 (2026-08-27)

Reviewer: OpenAI Codex CLI (gpt-5.6-sol, read-only sandbox over the repo);
brief: adversarial referee calibrated to .claude/skills/paper-claims/SKILL.md
(errors / scope / legibility / related work / consistency / reproducibility;
no style hedging). Findings below verbatim; triage dispositions added inline
as **TRIAGE:** lines by the maintainers.

## Triage (2026-08-27, same session)

Every finding was verified against the tex/JSONs before acting; all
dispositions applied in the same session, linter back at zero, LaTeX green.

| # | verdict | disposition |
|---|---|---|
| 1 | CONFIRMED | `prop:quotient` restated: forward implication + the honest a.e.-converse (acceptance with certainty ⟺ agreement at μ_query-a.e. query), with the one-line (1−q)^N proof added; intro bullet qualified |
| 2 | CONFIRMED | the ×NSW column recomputed on the points the detector RECEIVES (`n_used`, cap 300, from the JSONs); table gains a `used (×NSW)` column, prose rewritten — the honest story (recovery at and below the naive i.i.d. floor) is stronger, and the conjecture sentence now names the consumed density |
| 3 | CONFIRMED | n = 6 inside cell relabeled `proj. only`; prose states the 2-plane diagnostic detects projected circles and is not evidence about β₅ |
| 4 | CONFIRMED | the bolded causal sentence re-scoped to what is measured (posed topology tracks the sensor's report; cross-gap crossover) with the causal reading labeled consistent-with and the isolating intervention (randomized flipped summaries on committed evidence blocks) named as identified-but-not-run |
| 5 | CONFIRMED | stale prose replaced by the caption's own numbers (3/27 vs 2/33, n = 60, directional only) |
| 6 | CONFIRMED (independently found during formalization) | proof step rewritten to the Lean argument: sin θ = \|y₀\|/d ≤ γ/8 < sin(γ/2) by Jordan, both angles in [0, π/2] |
| 7 | CONFIRMED | the transitions bound was the rule-of-three (3/n), mislabeled Wilson; both uppers regenerated as Wilson 95% (1.3e-4, 1.2e-5); EXPERIMENTS.md fixed to match |
| 8 | CONFIRMED | "exactly when" replaced by the sandwich-scoped statement; the mean-radius display labeled as the sandwich's collapse, measured as a pointwise predictor (78/80) |
| 9 | CONFIRMED | heading and intro bullet re-scoped to "none of the three tested families" |
| 10 | CONFIRMED | source lines added: H1 lead-in (open_sweep_summary + unit), mitigation table caption (4 mitigation JSONs + optimism + unit), ShellField table caption (both TDA JSONs + unit) |
| 11 | CONFIRMED (submission-time item remains) | reproducibility section now states what is true and checkable (params/model provenance embedded per JSON; script-emitted numbers enforced by the CI ratchet); URL + archival snapshot + environment lock stay an explicit submission-time TODO |
| 12 | CONFIRMED | ten references added (PHAVer, SpaceEx, Flow*, KeYmaera X, Kearns–Singh, Strehl–Li–Littman, Aswani, Berkenkamp, Perea–Harer, Khasawneh–Munch) and woven into the three related-work paragraphs with the paper's positioning |
| 13 | CONFIRMED | defaults paragraph now gives the calibrated r = 0.0312 (937/30,000) with the 18/400 grid realization labeled and reconciled |
| 14 | CONFIRMED | 1/drag → 1/(drag·dt) ≈ 33 steps |
| 15 | CONFIRMED | h = 80 added to the frozen defaults |
| 16 | CONFIRMED | orphaned (d) label removed |
| 17 | CONFIRMED | intro claim split into proved-vs-measured (isotropic rate proved; box-thrust bound 4h/(nκ²); measured factor 0.411; contacts 1/600 at n = 4, censored zeros at 5, 6) |

On the overall verdict: findings 1 and 2 were real and are repaired above —
the quotient's honest converse is *stronger* than the deleted sentence
(exact a.e. characterization), and the recomputed densities sharpen the
sensor-resolution conjecture rather than weaken the section. The
recommended within-environment randomized-summary intervention is recorded
in the paper as identified-but-not-run.

## Findings (verbatim)

1. **Severity**: `error`  
   **Location**: Theory: the gate quotient — “The set of models accepted with certainty is exactly the extension class \(E(f)=\{\hat f:\hat f|_{\mathcal R}=f|_{\mathcal R}\}\).”  
   **The problem**: The converse is false in continuous spaces. A candidate may differ from \(f\) at a measure-zero point lying in the support \(\mathcal R\) and still be accepted with probability one for every finite \(N\).  
   **Check performed**: Compared Proposition 1 with `docs/paper3/THEORY.md` and `formal/Paper2Props/Paper3Ring/Basic.lean`; Lean’s `prop1_gate_quotient` proves only the forward implication under pointwise agreement and contains no accepted-with-certainty converse.  
   **Suggested repair**: Define the quotient modulo occupation-measure almost-everywhere equality, or add regularity assumptions under which disagreement at a support point implies positive-measure disagreement, and formalize that converse separately.

2. **Severity**: `error`  
   **Location**: Evidence sensor in \(n\) dimensions — “with densities \(10\)–\(2700\times\) the NSW floor.”  
   **The problem**: The reported ratios divide raw, highly duplicated contact counts by the heuristic floor even though only the deduplicated, capped \(n_{\rm used}\le300\) points enter persistence. For inside \(n=5\), the paper reports \(59{,}961/1365.3=43.9\times\), but the detector receives \(300/1365.3=0.22\times\); at \(n=6\), \(10.6\times\) becomes \(0.050\times\).  
   **Check performed**: Cross-referenced `results/continuous_shellfield_tda_inside.json` fields `n_contacts`, `n_used`, and `nsw_points_needed` with `scripts/continuous_shellfield_tda.py`, which passes `used = subsample(..., cap=300)` to the complex.  
   **Suggested repair**: Recompute the table from the actual deduplicated points supplied to persistence, and treat trajectory contacts as dependent samples rather than NSW’s i.i.d. manifold sample.

3. **Severity**: `major`  
   **Location**: Table “Persistent homology of the ShellField-\(n\) contact cloud” — “\(\beta_{n-1}\)? … \(n=6\) … (marginal)” and “2-plane slices at \(n=6\).”  
   **The problem**: An \(H_1\) calculation on 2-D coordinate projections cannot test recovery of \(\beta_5(S^5)\). It can detect projected circles, but that is not evidence that the six-dimensional shell’s defining homology was recovered.  
   **Check performed**: Read `scripts/continuous_shellfield_tda.py`; for \(n=6\), `slices_dominant_vs_second` projects onto four coordinate pairs and runs a 2-D Rips \(H_1\) reducer.  
   **Suggested repair**: Either compute \(H_5\) with a scalable complex/estimator or relabel the \(n=6\) entry as a projection diagnostic and remove it from the \(\beta_{n-1}\)-recovery claim.

4. **Severity**: `major`  
   **Location**: Evidence sensor — “an honest evidence summary with finite resolution causes wrong-topology gate-certified models.”  
   **The problem**: The reported H2 comparison changes \(\gamma\), evidence geometry, and the summary together, and Table 5 counts all terminal artifacts rather than gate-passing artifacts. It establishes a cross-gap association in proposed topology, not that the sensor caused wrong topology in certified models.  
   **Check performed**: Compared Table `tab:sensor`, the H2 paragraph, the inside-start artifacts in `results/continuous_ring2d_open_sweep_summary.json`, and the paper’s admission that the within-\(\gamma=1.8\) contrast is nonsignificant.  
   **Suggested repair**: Randomize correct versus deliberately flipped summaries on the same committed evidence blocks, then report topology and gate passage by intervention at the seed-block level.

5. **Severity**: `error`  
   **Location**: H2 paragraph — “closed structures appear only in the \(\hat\beta_1=1\) subset … though underpowered at \(n=30\).”  
   **The problem**: The immediately preceding caption reports \(3/27\) closed structures for \(\hat\beta_1=1\) and \(2/33\) for \(\hat\beta_1=0\), totaling \(n=60\). Thus they do not appear “only” in the first subset, and the stated sample size is stale.  
   **Check performed**: Cross-checked the paragraph against Table `tab:sensor` in `docs/paper3/main.tex`.  
   **Suggested repair**: Replace the sentence with the actual \(3/27\) versus \(2/33\), \(n=60\), nonsignificant contrast.

6. **Severity**: `error`  
   **Location**: Positivity proposition proof — “their angular offset from \(\pi\) [is] at most \(|y_0|/r_{\mathrm{in}}\).”  
   **The problem**: The offset is \(\arcsin(|y_0|/r)\), which is at least, not at most, \(|y_0|/r\). The theorem may remain true because the chosen margin is stronger than necessary, but the printed proof step is invalid.  
   **Check performed**: Recomputed the line–circle intersection geometry and compared it with `WitnessTube.lean`, which uses the sine characterization and Jordan’s inequality instead of this false bound.  
   **Suggested repair**: Use \(\sin(\gamma/2)\ge \gamma/\pi>\gamma/8\) to show \(|y_0|/r\le\gamma/8<\sin(\gamma/2)\), matching the Lean argument.

7. **Severity**: `error`  
   **Location**: Thin-neck table note — “Wilson uppers \(1.2\times10^{-4}\) (rollouts), \(9.4\times10^{-6}\) (transitions).”  
   **The problem**: Under the two-sided 95% Wilson convention used elsewhere, \(0/30{,}000\) has upper bound \(1.2804\times10^{-4}\), and \(0/320{,}000\) has upper bound \(1.2005\times10^{-5}\), not \(9.4\times10^{-6}\).  
   **Check performed**: Evaluated \(z^2/(n+z^2)\) with \(z=1.96\) and checked `results/ring2d_thin_neck.json`, which stores the \(30{,}000\)-rollout value and confirms `transitions=320000`. The manuscript’s \(0/400\), \(0/32{,}000\), and \(0/16\) bounds are otherwise consistent.  
   **Suggested repair**: Generate both bounds directly from the JSON and print \(1.3\times10^{-4}\) and \(1.2\times10^{-5}\).

8. **Severity**: `major`  
   **Location**: Sensor resolution — “the detector reports \(\hat\beta_1=1\) exactly when \(\sqrt3\rho-2\rho\sin(\Delta\theta_{\max}/2)>\tau\).”  
   **The problem**: What follows is only a two-sided sufficient-condition sandwich involving \(r_{\min}\), \(r_{\max}\), a rank condition, and an undecided band; the paper later reports only \(78/80\) pointwise agreement. The mean-radius display is therefore not an exact iff law.  
   **Check performed**: Compared the quoted sentence with the subsequent guaranteed-presence/guaranteed-absence conditions and the T1 ledger in `docs/paper3/THEORY.md`.  
   **Suggested repair**: State the proved two-sided sandwich as the theorem and place the mean-radius expression as a measured approximation validated on \(78/80\) rows.

9. **Severity**: `major`  
   **Location**: Closed-ring synthesis heading — “No family repairs the ring from outside evidence.”  
   **The problem**: The heading universally quantifies over model families, while the evidence is two GPT sizes with 20 seeds and only three-seed Qwen/Claude spot checks. The limitations section explicitly says those checks establish mechanism, not rates.  
   **Check performed**: Cross-referenced Table `tab:closedring`, the Qwen/Claude descriptions, and “Synthesis cells are modest; one contrast is underpowered.”  
   **Suggested repair**: Either expand independent family-level campaigns or make the heading self-contained: “None of the three tested families repaired the ring from outside evidence,” with JSON, \(n\), and seed block as the unit.

10. **Severity**: `major`  
    **Location**: Multiple measured lead-ins, including “H1 confirmed—with the clincher,” “The failure is a covering law,” and “The same law governs the sensor directly in \(n\) dimensions.”  
    **The problem**: These headline claims do not name their backing JSON or consistently state \(n\) and the experimental unit. Several tables say only “the JSON,” and the mitigation and dimensional tables name no result file at all.  
    **Check performed**: Applied the repository’s mandatory `.claude/skills/paper-claims/SKILL.md` contract and traced the apparent sources to `continuous_ring2d_open_sweep_summary.json`, `continuous_mitigation_ring*.json`, and `continuous_shellfield_tda*.json`.  
    **Suggested repair**: Add a source line to every result-bearing caption/lead-in naming the exact JSON, sample size, and unit—seed block, paired episode, rollout, transition, or artifact.

11. **Severity**: `major`  
    **Location**: Reproducibility — “All experiments, result files, and analysis scripts are in the project repository.”  
    **The problem**: The paper gives no public repository URL, exact commands, environment lock, model deployment/API version, or result-to-script/flag map; the source still contains “TODO: public repo URL at submission time.” `pyproject.toml` specifies only lower bounds, while the only frozen requirements and reproducibility manifest are for paper 2.  
    **Check performed**: Inspected the reproducibility section, `pyproject.toml`, `results/repro_manifest.json`, and synthesis JSON metadata. Exact model names occur in JSON, but the paper narrates only “GPT-5.x mini and large.”  
    **Suggested repair**: Commit a paper-3 manifest containing revision/tag, locked dependencies, exact commands and flags, model/deployment/API metadata, expected outputs/checksums, and a public archival URL.

12. **Severity**: `major`  
    **Location**: Related work — the four paragraphs beginning “Model error in model-based RL,” “Hybrid systems and reachability,” and “Topological data analysis.”  
    **The problem**: The comparison omits the closest literatures needed to position the central claims: formal reachability/certified hybrid analysis, simulation-lemma/PAC model learning, safe model-based control, and topology of dynamical data.  
    **Check performed**: Read all entries in `docs/paper3/references.bib`; it contains S-TaLiRo and a survey, but not these core lines.  
    **Suggested repair**: Compare specifically against PHAVer (Frehse, 2005), SpaceEx (Frehse et al., 2011), Flow* (Chen et al., 2013), KeYmaera X (Fulton et al., 2015), Kearns–Singh’s simulation-lemma/PAC-MDP line, Strehl et al.’s PAC model-based RL, Aswani et al. and Berkenkamp et al. on safe learning-based/model-based control, and Perea–Harer or Khasawneh–Munch on persistence for dynamical/time-series data.

13. **Severity**: `minor`  
    **Location**: Instrument versus synthesis — “the outside contact rarity at the defaults is \(r=0.045\)” versus “\(r=0.0312\) measured at \(30{,}000\) calibration rollouts.”  
    **The problem**: These are two estimates of the same default quantity without immediate sample qualifiers. The \(18/400=0.045\) estimate is statistically compatible with the better \(937/30{,}000=0.03123\) estimate, but the narration makes them look like contradictory constants.  
    **Check performed**: Compared Table `tab:mechanism` with `results/continuous_ring2d_mechanism.json` and `results/ring2d_rarity_sweep.json`.  
    **Suggested repair**: Use \(0.0312\) as the calibrated default and label \(0.045=18/400\) as the lower-powered mechanism-grid realization.

14. **Severity**: `error`  
    **Location**: Honest math ledger — “drag’s time constant is \(1/\mathrm{drag}=33\) steps.”  
    **The problem**: With drag \(0.3\) and \(dt=0.1\), \(1/\mathrm{drag}=3.33\) time units; conversion to steps requires \(1/(\mathrm{drag}\,dt)=33.3\). For the actual discrete multiplier \(0.97\), the e-folding time is \(-1/\log(0.97)=32.8\) steps.  
    **Check performed**: Recomputed from the stated semi-implicit recursion \(v_{t+1}=(1-0.3\cdot0.1)v_t+\cdots\).  
    **Suggested repair**: Print \(1/(\mathrm{drag}\,dt)\approx33\) steps, or the exact discrete value \(32.8\) steps.

15. **Severity**: `minor`  
    **Location**: Continuity proposition — “\(\approx1033\sqrt{\varepsilon}\) at the defaults.”  
    **The problem**: The arithmetic is correct—\(80\sqrt{5/(3\cdot0.1^2)}=1032.8\)—but \(h=80\) has not been stated numerically before this display, so a cold reader cannot reproduce the constant from the instrument section.  
    **Check performed**: Recomputed the constant from gain \(3\), \(dt=0.1\), \(r_{\rm out}=5\), and \(h=80\); searched earlier definitions in `main.tex`.  
    **Suggested repair**: Add \(h=80\) to the frozen instrument defaults.

16. **Severity**: `minor`  
    **Location**: End of the query-lower-bound discussion — “\(\textbf{(d)}\) Under two checkable hypotheses …”  
    **The problem**: There are no preceding items (a)–(c), and the text substantially repeats Proposition `prop:query`; this looks like an orphaned fragment and interrupts the contribution chain for a first-time reader.  
    **Check performed**: Followed the subsection sequentially from Proposition `prop:query` through the steering-witness paragraph.  
    **Suggested repair**: Remove the orphan label and replace the repeated passage with a direct backward reference to Proposition `prop:query`.

17. **Severity**: `minor`  
    **Location**: Dimension contribution — “the contact rarity collapses geometrically (\(r(n)\to0\) by \(n=4\)).”  
    **The problem**: Convergence cannot occur “by” a finite dimension, and the measured \(n=4\) rate is \(1/600=0.00167\), not zero. The asymptotic theorem and the finite experiment are being conflated.  
    **Check performed**: Read `results/continuous_shellfield.json`; \(n=5,6\) are censored \(0/600\), while \(n=4\) has one contact.  
    **Suggested repair**: State the proved asymptotic decay separately from the measurement: \(r(4)=1/600\), with its Wilson interval, and zero observed contacts at \(n=5,6\).

**Overall verdict:** Reject in the current form, with encouragement to resubmit after major revision. The paper contains a strong instrument and several valuable negative results, but its central quotient is stated with a false continuous-space converse, and the sensor/dimensional evidence contains both a serious denominator error and an invalid \(n=6\) homology interpretation. The two highest-value changes are: first, rebuild the gate quotient as an occupation-measure/a.e. theorem with an honest converse and matching Lean statement; second, redo the H2/ShellField analysis using the actual independent points supplied to persistence and a within-environment randomized summary intervention that measures gate-passing artifacts.


---

# Round 2 (2026-08-27, after the round-1 repairs)

Same reviewer, briefed to audit the round-1 repairs and hunt new findings.
Verbatim below; triage:

**Repair audit**: 11 REPAIRED, 5 PARTIAL, 1 NEW DEFECT (the round-1 repair
of #1). All PARTIALs and the defect addressed in the same session:

| finding | verdict | disposition |
|---|---|---|
| A#1 / B1 | CONFIRMED — my round-1 converse proof conflated occupation mass with per-rollout hit probability | prop:quotient rewritten: μ_query DEFINED (query-occupation measure), D the beyond-tolerance disagreement set, the proof now goes p := P(one rollout queries D), (1−p)^N by i.i.d. rollouts, and p = 0 ⟺ μ_query(D) = 0 by nonnegativity of the count; THEORY.md synced with the correction history |
| B2 | CONFIRMED — my pre-registered "net ≥ 8" rule was not a fixed-level test | design doc amended (before any outcome inspected): exact two-sided conditional binomial/McNemar with effect + CI |
| B3 | CONFIRMED — temporal/stochastic confound (historical control, no inference seed) | design doc amended: a CONTEMPORANEOUS honest replicate (same seeds, --out-tag ctrl2, same session/deployment) becomes the primary control; the committed arm demoted to a drift check |
| B4 | CONFIRMED — gate passage is a downstream outcome, not an invariant | design doc amended: secondary causal outcome, invariance null removed |
| B5 (+A#4/A#5 partials) | CONFIRMED | abstract clause and contribution-bullet heading re-scoped to the measured tracking claim; both "vanish" spots now "all but vanish" with the 1/40 visible |
| B6 | CONFIRMED against the JSON — τ GROWS with dose on 4/5 seeds; the flips come from the spurious bar's persistence growing (0.05→0.50, 0.11→0.43) | mechanism sentence rewritten to the per-seed truth, labeled directional/underpowered, JSON + cap named |
| B7 | CONFIRMED | "exactly for γ ≥ 3.2" replaced by the censored-zero bound (Wilson upper 7.7e-5) with exactness stated as conditional on f = 0 |
| B8 | CONFIRMED | "no recalibration recovers γ = 0" scoped to the registered 3× calibration, with the untested-recalibration caveat explicit |
| B9 (+A#6 partial) | CONFIRMED — same domain split as the Lean proof | γ > π case added (θ ≤ π/2 < γ/2) |
| B10 (+A#10 partial) | CONFIRMED | tab:ndim prints 0/600 with Wilson upper 6.4e-3 and its JSON; tab:closedring gains its JSON provenance + unit |
| A#11 partial | acknowledged | environment lock / archival URL / checksum manifest remain the explicit submission-time TODO (Javier's call on the public URL) |

## Round-2 findings (verbatim)

## A. Repair audit

#1: NEW DEFECT — The a.e. converse is plausible only after defining \(\mu_{\mathrm{query}}\), but the proof wrongly equates its disagreement mass \(q\) with the probability that a rollout hits the disagreement set. Within-rollout queries are dependent, so \((1-q)^N\) does not follow. The abstract, practitioner summary, conclusion, `THEORY.md`, and Lean still state/prove only the old pointwise-forward result.

#2: REPAIRED — Recomputed used/NSW ratios are outside \(17.381, 2.500, 0.1824, 0.00806, 0.00249\) and inside \(23.810, 4.6875, 0.9947, 0.2197, 0.04974\), consistent with the displayed rounding. Raw contacts, deduplication, cap, and dependence are now distinguished correctly.

#3: REPAIRED — The \(n=6\) result is clearly labeled a projected-\(H_1\) diagnostic, not evidence for \(\beta_5\).

#4: PARTIAL — The rewritten H2 paragraph and bold sentence are correctly scoped, but the abstract and contribution list still claim that the sensor “propagates” error into gate-certified artifacts and “causes” wrong-topology gate-certified models.

#5: PARTIAL — The \(3/27\) versus \(2/33\), \(n=60\), nonsignificant statement is correct, but the caption and paragraph still say closed structures “vanish” under arc guidance despite reporting one closed structure.

#6: PARTIAL — The Jordan route is sound for \(0<\gamma\le\pi\), but the proposition quantifies over every \(\gamma>0\); the displayed sine comparison is invalid for \(\gamma>\pi\). A trivial second case would complete it.

#7: REPAIRED — \(z^2/(n+z^2)\) gives \(1.2804\times10^{-4}\) for \(0/30{,}000\) and \(1.2005\times10^{-5}\) for \(0/320{,}000\), correctly rounded to \(1.3\times10^{-4}\) and \(1.2\times10^{-5}\).

#8: REPAIRED — The mean-radius expression now has the correct minus sign, is labeled a measured predictor, and is separated from the proved sandwich.

#9: REPAIRED — The heading now quantifies only over the three tested families.

#10: PARTIAL — Sources were added to the specifically repaired H1, mitigation, and ShellField displays, but other result-bearing captions, notably the closed-ring and \(n\)-dimensional tables, still omit exact JSON provenance and/or the independent unit.

#11: PARTIAL — Embedded parameters and model names improve traceability, but there is still no paper-3 environment lock, archival/public URL, checksum manifest, or executable result-to-command map; the source retains the submission-time TODO.

#12: REPAIRED — All ten records have the correct authors, venue, and year: [PHAVer](https://www-verimag.imag.fr/~frehse/phaver_web/frehse_hscc2005.pdf), [SpaceEx](https://researchportal.ip-paris.fr/en/publications/spaceex-scalable-verification-of-hybrid-systems/), [Flow*](https://home.cs.colorado.edu/~srirams/papers/cav2013-flowstar.html), [KeYmaera X](https://logic.kastel.kit.edu/publications/dblp_conf_cade_fultonmqvp15/), [Kearns–Singh](https://www.cis.upenn.edu/~mkearns/papers/KearnsSinghE3.pdf), [Strehl–Li–Littman](https://jmlr.org/papers/v10/strehl09a.html), [Aswani et al.](https://www.sciencedirect.com/science/article/pii/S0005109813000678), [Berkenkamp et al.](https://papers.nips.cc/paper_files/paper/2017/hash/766ebcd59621e305170616ba3d3dac32-Abstract.html), [Perea–Harer](https://scholars.duke.edu/publication/959004), and [Khasawneh–Munch](https://www.sciencedirect.com/science/article/pii/S0888327015004598).

#13: REPAIRED — The calibrated \(937/30{,}000=0.03123\) rate and the lower-powered \(18/400=0.045\) realization are correctly reconciled.

#14: REPAIRED — \(1/(\mathrm{drag}\,dt)\approx33\) steps has the correct units and agrees with the discrete \(32.8\)-step e-folding time.

#15: REPAIRED — \(h=80\) is stated before the \(1033\sqrt{\varepsilon}\) constant.

#16: REPAIRED — The orphaned `(d)` is gone.

#17: REPAIRED — The proved asymptotic/bound and finite measurements \(1/600,0/600,0/600\) are separated correctly in the contribution statement.

## B. New findings

### 1. The repaired quotient proof does not establish its converse

**Severity:** error  
**Location:** [main.tex:283](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:283), [THEORY.md:36](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/THEORY.md:36)  
**Problem:** \(\mu_{\mathrm{query}}\) is never defined. If it is the occupation measure, its mass \(q\) is not the probability that one rollout hits the disagreement set. Moreover, a nonzero gate tolerance identifies equality only modulo that tolerance, not literal equality. The conclusion and practitioner summary still say that a sampling gate certifies the full reachable restriction pointwise.  
**Check performed:** Compared the proposition with the gate definition, theory ledger, and `prop1_gate_quotient`; Lean proves only the forward realization-level implication.  
**Suggested repair:** Define \(p=P(\text{one rollout queries }D_\varepsilon)\), where \(D_\varepsilon=\{\|\hat f-f\|>\varepsilon\}\). Independence across rollouts gives \((1-p)^N\). Separately prove \(p=0\iff\mu_{\rm occ}(D_\varepsilon)=0\), then synchronize the abstract, conclusion, ledger, and formalization.

### 2. The intervention’s preregistered significance rule is mathematically invalid

**Severity:** error  
**Location:** [INTERVENTION-DESIGN.md:37](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/INTERVENTION-DESIGN.md:37)  
**Problem:** “At least 8 net discordant flips” is not a fixed \(p<0.05\) criterion. Exact McNemar/sign significance depends on the total number \(d\) of discordant pairs: \(9{:}1\) has net eight and two-sided \(p=0.0215\), while \(34{:}26\) also has net eight but is nonsignificant.  
**Check performed:** Evaluated the exact conditional binomial test under \(X\sim\mathrm{Binomial}(d,1/2)\).  
**Suggested repair:** Pre-register the exact two-sided McNemar/binomial \(p\)-value as a function of \(d\), plus the paired effect and confidence interval; delete the fixed “net eight” threshold before inspecting outcomes.

### 3. The crossover does not isolate each per-seed difference as claimed

**Severity:** major  
**Location:** [INTERVENTION-DESIGN.md:15](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/INTERVENTION-DESIGN.md:15)  
**Problem:** The old honest arm is always historical and the flipped arm is run later. The LLM request supplies no synthesis seed, so pairing fixes \(D_{\rm train}\), not response randomness. A per-seed difference can therefore arise from stochastic generation or period/deployment drift; it is not attributable to the summary “alone.”  
**Check performed:** Traced `tda`/`tda-flip` through `continuous_danger_synthesis.py` and the Azure provider: evidence seeds are fixed, but no inference seed or randomized treatment order is used.  
**Suggested repair:** Run both arms contemporaneously, randomize order within evidence block, record immutable deployment/API identity, and use repeated synthesis draws if the target is an average causal effect over model randomness.

### 4. H-I3 mistakes a downstream outcome for an invariant

**Severity:** major  
**Location:** [INTERVENTION-DESIGN.md:57](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/INTERVENTION-DESIGN.md:57)  
**Problem:** The gate need not see the prompt for gate passage to move. The prompt changes the synthesized artifact, which the gate directly evaluates; passage is therefore a legitimate treatment outcome. Calling movement a “synthesis-side artifact” would discard precisely one causal pathway of interest.  
**Check performed:** Followed the pipeline summary \(\rightarrow\) synthesized code \(\rightarrow\) gate score.  
**Suggested repair:** Treat paired gate passage and held-out acceptance as secondary causal outcomes, without an invariance null justified by prompt blindness.

### 5. The repaired H2 scope is contradicted by headline claims

**Severity:** major  
**Location:** [main.tex:57](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:57), [main.tex:187](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:187), [main.tex:1508](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:1508)  
**Problem:** The body correctly says causation is not isolated and Table 5 counts terminal artifacts, yet the abstract/contribution list assert propagation into “gate-certified artifacts” and causal production of them. The same section says closed structures “vanish” where the table reports \(1/40\).  
**Check performed:** Compared the abstract, contribution bullet, table caption, and repaired H2 paragraph.  
**Suggested repair:** Until the corrected intervention finishes, make every headline state the measured cross-gap association in posed terminal topology; reserve gate-certified and causal language for treatment-specific gate outcomes.

### 6. The claimed dose mechanism is contradicted by its JSON

**Severity:** error  
**Location:** [main.tex:1417](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:1417)  
**Problem:** The paper explains \(1/5\rightarrow3/5\) false loops by saying the threshold shrinks with density while persistence stays fixed. At \(\gamma=1.8\), cap 90, \(N=40\rightarrow160\), \(\tau\) instead increases for four of five seeds: \(0.1868\to0.2044\), \(0.1697\to0.2239\), \(0.2494\to0.3206\), and \(0.2613\to0.2800\). Bar persistence also changes.  
**Check performed:** Recomputed directly from `results/ring2d_sensor_resolution.json`.  
**Suggested repair:** Report the paired \(1/5\rightarrow3/5\) observation as directional and underpowered, and derive any mechanism from the actual per-seed cap/subsampling behavior.

### 7. A censored funnel zero is promoted to exact monotonicity

**Severity:** error  
**Location:** [main.tex:580](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:580)  
**Problem:** The paper says M1/M2 hold “exactly for \(\gamma\ge3.2\) where the funnel mass measures zero.” Measurement of zero events does not prove \(f=0\); the corollary gives exactness conditional on \(f=0\), not from a censored estimate.  
**Check performed:** Compared the corollary’s algebraic hypothesis with the \(50{,}000\)-rollout measurement and the theory ledger.  
**Suggested repair:** State a confidence upper bound on the funnel mass and the corresponding measured slack, or prove structural vanishing for that range.

### 8. “No recalibration recovers \(\gamma=0\)” is not supported

**Severity:** major  
**Location:** [main.tex:1474](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:1474)  
**Problem:** The reported bars \(0.160/0.197/0.253\) are below the particular thresholds \(0.183/0.324/0.439\), but lowering the threshold factor would make them fire. The data establish failure of the registered \(3\times\) rule as dose increases, not impossibility under every recalibration.  
**Check performed:** Compared each bar directly with the displayed threshold and considered the same detector with a smaller multiplier.  
**Suggested repair:** Either say “more data does not rescue the registered calibration,” or sweep the threshold and demonstrate that no single calibration recovers \(\gamma=0\) while retaining the required open-ring specificity.

### 9. The positivity proof omits half its stated domain

**Severity:** minor  
**Location:** [main.tex:603](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:603)  
**Problem:** Jordan’s inequality and monotonicity of sine are used as though \(\gamma/2\in[0,\pi/2]\), but the proposition says every \(\gamma>0\) and the paper permits widths up to \(2\pi\).  
**Check performed:** Checked the domains of \(\sin x\ge2x/\pi\) and sine monotonicity.  
**Suggested repair:** Prove the displayed case for \(0<\gamma\le\pi\); for \(\gamma>\pi\), use \(\theta\le\pi/2<\gamma/2\) directly.

### 10. The dimensional table regresses to unqualified censored zeros

**Severity:** minor  
**Location:** [main.tex:1723](C:/Users/Usuario/GitHub/code-world-models/docs/paper3/main.tex:1723)  
**Problem:** \(n=5,6\) are printed as \({\sim}0\), without \(0/600\), a Wilson upper, exact JSON source, or unit. This obscures the distinction repaired in contribution #17.  
**Check performed:** Compared the table with `results/continuous_shellfield.json`, where both cells are \(0/600\).  
**Suggested repair:** Print \(0/600\) with the rollout-level Wilson upper and add the exact JSON source to the caption.

**Overall verdict:** No—the paper is not yet acceptable merely modulo the running intervention. Most round-1 empirical repairs are sound, but the central quotient still lacks a valid converse proof, headline H2 claims remain stronger than the repaired body, and the preregistered intervention currently has an invalid test and a temporal/stochastic confound. The single highest-value change is to rebuild Proposition 1 around a defined trajectory-hit probability \(p\), connect it rigorously to occupation-measure a.e. agreement, and synchronize every headline, ledger entry, and Lean claim with that theorem.

# Round 3 (2026-08-28, after the intervention fold and the round-2 repairs)

Same reviewer and brief (adversarial referee over the repo, read-only;
round-3 brief targeted the new material: the intervention fold, the
903/39 audit counts, and the round-2 repairs themselves). Verbatim
findings below; triage inline.

**Reviewer's summary: no BLOCKING defects; two MAJOR and three MINOR
defects not reported in rounds 1–2.** Clean bill (verbatim): the primary
intervention numbers are correct (60 pairs, 11 discordant, 9:2, exact
p = 0.0654296875; gate discordance 0); git history supports genuine
pre-registration (design `181ec28` 22:18, amendments `c0a329b` 22:35,
analysis script `fa92e03` 23:02, outcomes `879b9e5` 00:00); the paper
does not bury the primary null; held-out counts all reproduce (903
artifacts, 39 campaigns, 156/156 over 91 blocks, 214/121, all 121
mode-only, 39/39 Wilson); prop:quotient repaired correctly; every
ShellField `used (×NSW)` entry matches; the dose-mechanism rewrite
matches its JSON; the strict claims audit reports paper 3 clean.

## Round-3 triage (2026-08-28, same session)

| # | severity | verdict | disposition |
|---|---|---|---|
| 1 | MAJOR | CONFIRMED | "any honest summary has *some* flip" (main.tex "The sensor constant is ours") overgeneralized: honesty does not imply finite resolution. Re-scoped: the flip is PROVED for Rips-type detectors (barcode sandwich; below the bridging scale the gap is invisible); the analogous blind width for any fixed-scale sampled summary is stated as an explicit expectation, not an assertion; propagation into posed topology stays measured-for-the-registered-detector-only |
| 2 | MAJOR | CONFIRMED | "The null is not control instability … no deployment drift" exceeded the evidence: the honest controls disagree on 9/60 pairs (4:5); p = 1.0 shows balance, not stability. Rewritten: per-seed classification is stochastic at this cell, the balanced split shows no *directional* drift but cannot rule out generation variability as such, and this seedless generation noise is exactly what the paired binomial's null absorbs |
| 3 | MINOR | CONFIRMED | the registered exact CI for the discordant split was never emitted. `clopper_pearson` added to the analysis script (bisection on the binomial CDF, no new deps), JSON re-emitted (`toward_claim_share_ci95_clopper_pearson` = [0.482, 0.977]), tex reports it spanning 1/2 |
| 4 | MINOR | CONFIRMED | H-I3's original invariance reading contradicted amendment 3. H-I3 annotated [SUPERSEDED by amendment 3] in INTERVENTION-DESIGN.md with the original text kept for the record |
| 5 | MINOR | CONFIRMED | the round-2 Wilson uppers were hand-derived (arithmetically correct, wrong provenance). New `scripts/ring2d_zero_wilson.py` emits them from the sweep's own denominators into `results/ring2d_zero_wilson.json` (1.2804e-4, 1.2005e-5, 0.1936); tex cites the file |

All five repaired in the same session; linter zero, LaTeX green. The full
round-3 transcript (~950 KB) lives outside the repo; the findings above
are the complete list.

# Round 4 (2026-08-28, convergence check on the round-3 repairs)

Same reviewer and brief (round-4 brief targeted the five round-3 repairs
plus one final structural sweep). First attempt was cut off by the Codex
workspace spend cap; re-run complete under a fresh account.

**Reviewer's verdict: no BLOCKING defects, one MAJOR and three MINOR —
all four on the round-3 repairs themselves; "the final structural sweep
found nothing else new."** Clean (verbatim): the Clopper–Pearson
implementation is correct for 9/11 ([0.4822441, 0.9771688], so the tex's
[0.48, 0.98] and "spanning 1/2" are correct); the other Wilson values
match numerically; the "we expect, but do not prove" wording is honest;
the strict claims audit reports paper 3 clean; the H-I3 [SUPERSEDED]
annotation is coherent.

## Round-4 triage (2026-08-28, same session)

| # | severity | verdict | disposition |
|---|---|---|---|
| 1 | MAJOR | CONFIRMED | "for Rips-type detectors the flip is forced by the barcode sandwich" exceeded the sandwich's hypotheses (planar center-star-shaped clouds; class-to-bar rank condition measured, not assumed; non-winding exclusion unproved). Re-scoped to the sandwich's own hypotheses with its explicit condition √3·r_min − 2·r_max·sin(Δθ_max/2) > τ and the rank condition labeled measured |
| 2 | MINOR | CONFIRMED | "balanced, so no *directional* drift" still inferred a population absence from a null; now "no *observed* directional imbalance", with the variability caveat kept |
| 3 | MINOR | CONFIRMED | `ring2d_zero_wilson.py` read `r.get("episodes", 16)` but the rows store `n_episodes` — every lookup silently fell back to the literal 16 (numerically identical, provenance broken). Fixed to `r["n_episodes"]`, JSON re-emitted (same three uppers) |
| 4 | MINOR | CONFIRMED | INTERVENTION-DESIGN.md's RESULT ledger still said "no deployment drift"; aligned with the tex's repaired reading (no observed directional imbalance; generation variability not excluded, absorbed by the paired null) |

All four repaired in the same session; linter zero, LaTeX green.
Reviewer's own closing line: after these repairs, "submission-readiness
would remain only modulo the recorded archival-URL/environment-lock
TODO." Findings across rounds: 17 → 10 → 5 → 4 (this round's four all
against text introduced by round 3's own repairs; the structural sweep
found nothing new). The review cycle CONVERGES here.
