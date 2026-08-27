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
