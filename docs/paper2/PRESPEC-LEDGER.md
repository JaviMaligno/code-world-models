# Paper 2 — pre-specified / confirmatory / diagnostic / exploratory / post-hoc ledger

Review point #20. The evidence is the git history, not memory. Every date below
comes from `git log --date=iso` on the file that first states a claim and the
commit that first measures it; where the two are hours apart the times are given,
because a "prediction" recorded 40 minutes before its run and one recorded a day
after are different things.

Read against git `9e4988c` (2026-07-27). `main.tex` line numbers are those of the
**committed** file at that commit (`git show HEAD:docs/paper2/main.tex`), because
the working tree is being edited concurrently.

## The vocabulary, and what earns each label here

| label | test applied |
|---|---|
| **PRE-SPECIFIED** | a dated file states the experiment *and* its expected outcome before any commit contains its result |
| **CONFIRMATORY** | ran as specified; the pre-stated prediction is what was checked |
| **DIAGNOSTIC** | added to explain or repair a failure/error that had already been observed |
| **EXPLORATORY ABLATION** | added after seeing a result, to probe an explanation of it |
| **POST-HOC** | the analysis, statistic or theorem was chosen after the data existed |

## The pre-specification instruments, and their exact dates

1. **`docs/specs/2026-07-06-continuous-hybrid-cwm-design.md`**, created
   `1c9bd05` **2026-07-06 18:09 UTC**. Its own opening line is the strongest
   dating evidence in the repo:

   > Status: design 2026-07-06. … **Nothing in this spec has been run.**

   It contains predictions in three places — §Thesis, the *Contrast arm*
   paragraph, and §Risks:

   > **Expected shape of the result:** the same **threshold law** as paper 1 —
   > harm ≈ 0 while the boundary is commonly crossed by random rollouts, rising
   > as the boundary moves out of the rollout envelope, plateauing at full
   > play_cost — because competent (MPC) reach of the boundary should be
   > knob-insensitive while random reach falls. That reach-mechanism plot … is
   > the first thing to measure.

   > **Contrast arm — smooth localized perturbation** … **Prediction:** to be
   > simultaneously gate-invisible (sub-tolerance off the region) and
   > play-consequential, a smooth perturbation must be large exactly where
   > competent trajectories go — the two requirements fight, so danger stays
   > low. This makes point 2 of the thesis an *experiment*, not just an argument.

   > **Repair may succeed here** (a numeric discontinuity is visible in data in a
   > way a symbolic rule is not). Not a risk to the thesis — either outcome is a
   > finding — but frame the paper so it doesn't depend on repair failing.

   It also sets a **pre-registered decision rule** (§Order of work step 1):
   "**go/no-go: competent reach flat, random reach falling** (if not,
   re-engineer reward)" — and, in §Risks, requires "a documented ε-sensitivity
   sweep" for the loose-ε arm.

   And it **scopes theory out**: "Does NOT transfer: the coverage/enumeration
   results (finite info-sets). Covering-number analogues are open; mention as
   limitation, **do not attempt for paper 2 headline**." (See L4 below.)

2. **The same spec's "Runbook — LLM arms" section**, appended `05412f9`
   **2026-07-07 09:44 UTC**, before any credentialed run was committed
   (`c21ece9`, 2026-07-07 11:22 +0100 = 10:22 UTC — **38 minutes later**). It
   carries an explicit **"Predictions to check against:"** block: full arm
   "gate 1.0 in 0–2 iterations, wall_blindness 0.0, play_cost ≈ 0"; mode-absent
   "gate 1.0 + wall_blindness 1.0 + play_cost ≈ 1 with play_contact_rate 1.0
   (~60% of seeds at the defaults)"; mode-present "translation-not-inference
   predicts the gate cannot reach 1.0 … a numerically-manifested discontinuity
   may be EASIER to induce from data … Either outcome is a finding; if it
   repairs, that is the interesting divergence from paper 1 and becomes its own
   section."

3. **The same spec, amended `e2825e2` 2026-07-07 11:36 UTC** with "Remaining
   credentialed runs": the 20-seed tightening and the Qwen cross-family
   spot-check, with "What to expect … (2) tests whether mode-repair-from-data is
   a GPT-5.x quirk — **either outcome is a finding**". Qwen ran `680b68f`
   2026-07-07 14:48 +0100 (13:48 UTC), **2 h 12 min later**.

4. **`docs/paper2/STRONGER-STATEMENTS.md`**, created `26d45c1`
   **2026-07-25 09:06 +0100**, after five adversarial reviews. Its "Route to the
   strong version" bullets are pre-run relative to `be648f8`
   **2026-07-25 10:28 +0100** (82 minutes) — a real, if short, pre-registration
   window for the 2026-07-25 batch.

**The spec was last touched 2026-07-10** (`704dd57`, one line). It never mentions
mitigation, distrust regions, fences, PatchField2D, the square ablation, guided
prompts or curvature (`grep -ic` over both the original and current versions
returns 0 for all of them). Everything from 2026-07-12 onward is therefore
unspecified in the design doc, whatever its scientific merit.

---

## Ledger

### A. Pre-specified and confirmatory

| # | claim / experiment | first specified (file + date) | first measured (commit + date) | classification |
|---|---|---|---|---|
| A1 | Threshold law: danger ≈ 0 → elbow → plateau at full play_cost (`tab:danger`, `fig:threshold`) | design spec §Thesis "Expected shape of the result", **2026-07-06 18:09** | `992ec0c` **2026-07-06 20:49** (`results/continuous_reach.json`) | PRE-SPECIFIED → CONFIRMATORY (2 h 40 min) |
| A2 | Competent reach flat / random reach falling — the **go/no-go** rule (`fig:reach`) | spec §Order of work step 1, 2026-07-06 | `992ec0c` 2026-07-06, commit subject "mechanism go/no-go **PASSED**" | PRE-SPECIFIED → CONFIRMATORY |
| A3 | Wall position is the rarity knob; sweep it from common to ≈0 | spec §Primary instrument (a), 2026-07-06 | `992ec0c` 2026-07-06 | PRE-SPECIFIED → CONFIRMATORY |
| A4 | Gate-miss exactness: empirical pass@40 = (1−r)^40 within binomial CI (`tab:axes`) | spec §The gate, 2026-07-06 | `05412f9` **2026-07-07 09:44** (`continuous_axes.json`) | PRE-SPECIFIED → CONFIRMATORY |
| A5 | Pervasive-error control arm (δ<ε passes, δ>ε rejected) — the axis separation | spec §The gate, 2026-07-06 | `05412f9` 2026-07-07 | PRE-SPECIFIED → CONFIRMATORY |
| A6 | Smooth-bump contrast: **danger stays low** | spec *Contrast arm* **prediction**, 2026-07-06 | `05412f9` 2026-07-07 (play_cost 0.000 at amp 0.5, −0.745 at amp 1.0) | PRE-SPECIFIED → CONFIRMATORY |
| A7 | Smooth learner cannot localize the mode (`tab:smooth`, `fig:smooth`) | spec §Synthesis arms item 4 (MLP probe, "default: include small"), 2026-07-06 | `8f914f8` **2026-07-07 10:58** (`continuous_smooth_probe.json`) | PRE-SPECIFIED → CONFIRMATORY |
| A8 | Full-spec synthesis passes the tiny-ε pinned-integrator gate | runbook **Predictions**, 2026-07-07 09:44 | `c21ece9` 2026-07-07 10:22 UTC | PRE-SPECIFIED → CONFIRMATORY (38 min) |
| A9 | Mode absent ⇒ gate 1.0, blindness 1.0, play_cost ≈ 1, contact 1.0 | runbook **Predictions** (incl. the "~60% of seeds" rate), 2026-07-07 09:44 | `c21ece9` → tightened `34e74ee` / `680b68f` 2026-07-07 | PRE-SPECIFIED → CONFIRMATORY |
| A10 | Mode present ⇒ **either** gate-refusal **or** repair, "either outcome is a finding; if it repairs … becomes its own section" | runbook **Predictions**, 2026-07-07 09:44 | `c21ece9` 2026-07-07; repair confirmed | PRE-SPECIFIED **CONTINGENCY** → CONFIRMATORY. The repair section is a pre-registered branch, not a post-hoc pivot — the strongest pre-specification claim the paper can make |
| A11 | ε-sensitivity sweep is required and must show ε is a pervasive-error dial (`tab:eps-sweep`) | spec §Risks "needs a documented ε-sensitivity sweep", 2026-07-06 | `d8947b0` **2026-07-10 13:45** | PRE-SPECIFIED → CONFIRMATORY |
| A12 | Second hybrid instrument = pendulum with a hard angular stop (`tab:pendulum`) | spec §Second hybrid instrument ("pendulum with a hard angular stop, or 2D navigation with a sticky patch … pick one"), 2026-07-06 | `e2825e2` **2026-07-07 11:36** | PRE-SPECIFIED → CONFIRMATORY |
| A13 | Qwen cross-family spot-check: is repair-from-data a GPT-5.x quirk? | spec runbook amendment, **2026-07-07 11:36 UTC** | `680b68f` **2026-07-07 13:48 UTC** | PRE-SPECIFIED → CONFIRMATORY (2 h 12 min) |
| A14 | Pendulum **synthesis** arm (`tab:pendulum-synthesis`) | flagged as the open item of the 2026-07-07 pendulum section ("the synthesis arms on the pendulum remain optional future work") | `814a29b` **2026-07-08 11:54** | CONFIRMATORY (specified ~1 day ahead, as an extension of A12) |

### B. Added after the results they respond to

Ordered by date. The five items the review asks about specifically are B5–B9;
each date below is verified from `git log`, not assumed.

| # | experiment | dated record that first specifies it | first measured | gap after the result it responds to | classification |
|---|---|---|---|---|---|
| B1 | **Distrust-region mitigation** (`tab:mitigation`, §Mitigation, `prop:fencecover`) | none — absent from every version of the design spec | `ab66ba3` **2026-07-09 09:35** (`continuous_mitigation.json`) | 3 days after the exploitation result (A1/A9) | EXPLORATORY (prescriptive extension). The paper presents it as a contribution, not as a prediction — correctly |
| B2 | **Second planner family, CEM** (`tab:cem`) | spec names "random shooting / CEM" as the planner *implementation*; no second-family comparison is specified anywhere | `ad3d034` **2026-07-12 20:46** | 5 days | POST-HOC CONFIRMATORY: the theory it tests (`prop:playcost`, query-hit mass) *is* pre-specified (spec §The planner, 2026-07-06); the arm is not |
| B3 | **Claude agent-relay third family** (cart + pendulum) | none | `164bd3c` **2026-07-15 21:43** | 8 days | EXPLORATORY ABLATION |
| B4 | **PatchField2D instrument** (4D, bi-modal; `tab:patch2d`, §PatchField2D) | spec names "2D navigation with a sticky patch" as *one of two options* for the second instrument, with **no predictions**; `docs/EXPERIMENTS.md` states the campaign "closes the two structural gaps **the reviewers flagged** on the 1D instruments" | `3ce5c1b` **2026-07-17 08:06** (mechanism), `dc27f7b` **2026-07-17 09:19** (synthesis) | 11 days; review-driven | DIAGNOSTIC (instrument option pre-named; campaign, hypotheses and knob grid not) |
| B5 | **Square (zero-curvature) ablation** — main.tex L820 "Ablation 2: a zero-curvature square **falsifies** the curvature reading" | none before the result | CPU calibration `b953e97` **2026-07-19 18:19 UTC**; synthesis `64ca1ea` **2026-07-20 08:31 UTC**, `2fba8bf` 2026-07-20 09:24 | **2–3 days after** the 2D repair failure it explains (`dc27f7b` 2026-07-17 09:19) | EXPLORATORY ABLATION. A genuine falsification *of a post-hoc hypothesis*: the curvature reading itself was born of the 07-17/18 result |
| B6 | **Guided-prompt ablation** (`--prompt-variant region`, 15 refine iterations = 3× budget) | none before the result | `cca5406` **2026-07-19 23:02** | **2 days after** `dc27f7b` | EXPLORATORY ABLATION. Also the single most expensive cells in the paper: 320 LLM calls each, 640 of the campaign's 1959 |
| B7 | **Seed-offset disjoint blocks** (`--seed-offset`, the `*_off20` cells) | `STRONGER-STATEMENTS.md` item 2 "Route to the strong version: run the second size on a *disjoint* seed block", `26d45c1` **2026-07-25 09:06** | `be648f8` **2026-07-25 10:28** | 82 min after its own route note; **18 days** after the pooling it repairs (`c21ece9` 2026-07-07) | DIAGNOSTIC (statistical repair of a pooling error a review found: the two sizes share samples, so pooled Wilson bounds were overstated) |
| B8 | **Sharp-plateau reward variant** (`continuous_reach_sharp`, `continuous_pendulum_sharp`, and the asymmetric `sharpphantom`) | `STRONGER-STATEMENTS.md` item 3, `26d45c1` **2026-07-25 09:06** — states cost, payoff and one caveat ("changing the reward shape changes every number") | `be648f8` **2026-07-25 10:28**; asymmetric variant `93aab59` 2026-07-25 13:09 | 82 min after its route note; **19 days** after the "below random at every knob" claim it rescues | EXPLORATORY (added to earn back a statement a review weakened). **See F1: the specific risk main.tex calls "pre-registered" is not in the pre-run text** |
| B9 | **50k dependence re-measurement** (`patch2d_dependence_50k.json`, `rem:bracket`) | the independence error is identified in `26d45c1` **2026-07-25 09:06** ("an independence error becomes a theorem"); no prediction of the *sign* is recorded | `6f3b852` **2026-07-25 17:58** | **8 days** after the 600-rollout table it corrects (`3ce5c1b` 2026-07-17) | POST-HOC re-measurement. The outcome — negative dependence at (2,6) and (3,7), **positive** at (4,6), undecided at (4,7) — was not predicted; the paper says so ("We therefore measured it properly") |
| B10 | **76-artifact behavioural audit** (`patch2d_artifact_audit.json`; main.tex L816 "locates the failure precisely") | none | `89761b7` **2026-07-23 09:57** | 6 days after `dc27f7b` | POST-HOC analysis. **And it shipped wrong once:** the original partial-repair check read `per["p1"]` while the key is `"patch1"`, so the condition never fired (vacuous); corrected `2026-07-24`, and the corrected reading changed the paper's claim from "no artifact covers the seen patch" to **34/76 do** (`docs/EXPERIMENTS.md`, the audit table) |
| B11 | **2D Qwen + 2D Claude relay arms** (Ablation 3) | none | `ea8ca9f` **2026-07-24 22:58** — commit subject "close all 11 **pre-arXiv review** items" | 7 days | DIAGNOSTIC (review-driven) |
| B12 | **PatchField2D ε rows / CEM row / 2D mitigation** | the ε axis is pre-specified (A11), the instrument is not | `05da157` **2026-07-17 20:40**, `0de7645` 20:41, `7b38352` 21:07 | same day as B4 | CONFIRMATORY on a post-hoc instrument (ε), EXPLORATORY (CEM row, 2D mitigation) |
| B13 | **Sample-stream census** (`sample_stream_census.json`: rollout-seed blocks, block-level Wilson) | none — the unit of analysis was changed *because* a review pointed out the pooling was over shared samples | `6f3b852` **2026-07-25 17:58** | 18 days | POST-HOC (choice of the sampling unit after the data) |
| B14 | **Fence separation census** (`fence_separation_census.json`) | none | `6f3b852` **2026-07-25 17:58** | 8 days after the 2D mitigation result | DIAGNOSTIC — it *replaced* the paper's own reading of that result: "boundary-mapping transient" became "a growing fraction of outright failures (0/20, 2/20, 7/20 pinned episodes)" |
| B15 | **Rarity re-measurement at 30k / 20k rollouts** (censored zeros in `tab:pendulum`, `tab:axes`) | `STRONGER-STATEMENTS.md` item 4, `26d45c1` 2026-07-25 09:06 | `be648f8` **2026-07-25 10:28** | 82 min / 18 days | DIAGNOSTIC (removes two censored zeros a review flagged) |

### C. The theory: all of it post-hoc, and one part explicitly out of scope

Every proposition-backing JSON in the paper was produced in the final 40 hours,
after all of the data existed, and in most cases *because a measurement looked
suspiciously exact*. `docs/EXPERIMENTS.md` records the trigger verbatim:
"mencionas varias cosas medidas que salen completamente exactas, me pregunto si
eso es hint de algo más que se puede demostrar."

| # | result | JSON | commit | classification |
|---|---|---|---|---|
| C1 | ε-invariance threshold ε\* (`prop:epsinv`, `tab:epsstar`) | `eps_invariance_threshold.json` | `e71aaa3` 2026-07-25 11:23 | POST-HOC (theorem reverse-engineered from an exact measurement) |
| C2 | gate density constant c = 5/6 (`cor:cartdensity`) | `gate_density_constant.json` | `e71aaa3` 2026-07-25 11:23 | POST-HOC |
| C3 | truth-planner knob-invariance regime (`prop:knobinv`, `prop:ident`) | `truth_planner_knob_regime.json`, `truth_plan_invariance_certificate.json` | `e71aaa3` 11:23, `93aab59` 13:09 | POST-HOC |
| C4 | coverage certificate, packing route (`prop:coverage`) | `gate_coverage_certificate.json`, `circle_covering_number.json` | `fbb6ab7` 2026-07-25 13:51 | POST-HOC — **and see L4** |
| C5 | dependence-exact + validation variants | `gate_coverage_dependent.json`, `gate_coverage_validation.json`, `gate_density_step_t.json` | `b816e8b` 14:17, `44fa512` 14:38 | POST-HOC |
| C6 | certified-region query mass | `certified_region_query_mass.json` | `316c057` 14:59 | POST-HOC |
| C7 | partition certificate + validation (`prop:partition`) | `gate_partition_certificate.json`, `gate_partition_validation.json` | `cb4a13c` **2026-07-26 21:17** | POST-HOC |
| C8 | ε-flatness rate (`prop:epsrate`) | `eps_flatness_rate.json` | `5a17956` 2026-07-26 23:02 | POST-HOC |
| C9 | derived play-cost normalizers (`prop:normalizers`) | `play_cost_proved_bounds.json` | `517142d` 2026-07-26 23:19 | POST-HOC |
| C10 | phantom-targeting probability | `phantom_targeting_probability.json` | `5675a91` 2026-07-26 23:32 | POST-HOC |

**L4 (the unflattering one).** The 2026-07-06 spec said, of exactly this
material: "Covering-number analogues are open; mention as limitation, **do not
attempt for paper 2 headline**." The paper now contains `prop:coverage`,
`prop:partition`, `prop:fencecover` and `cor:fencedim`. They were added in the
last two days, and the first version of the fence bound was **wrong in the
direction that mattered** — a covering number was used where a packing number
was needed, and a hand-computed circle covering number of 13 was really 7 (6 with
free centres). It was caught not by the audit but by a reader's question — "el
número de recubrimiento de un círculo no es 3?" — and fixed the same day
(`fbb6ab7`, 2026-07-25 13:51). The paper's §Mitigation now says the weakening was
"forced by counterexample rather than caution", which is accurate.

---

## F. Every phrase in `main.tex` claiming pre-registration or falsification

Line numbers from `git show HEAD:docs/paper2/main.tex` (`9e4988c`). **No edit to
`main.tex` is made or proposed here** — this is the ledger's verdict only.

| # | line | phrase | ledger verdict |
|---|---|---|---|
| **F1** | **512** | "\textbf{It costs no planner competence}, **the pre-registered risk**: a sharper plateau gives random shooting less gradient to follow, yet $J_\mathrm{truth}$ moves only 17.77→17.76 …" | **NOT SUPPORTED by any dated record in this repository.** Searches, all re-runnable: `grep -rn "less gradient\|gradient to follow\|planner competence" docs scripts src` returns, excluding this ledger, exactly two hits — the `main.tex` sentence itself and `scripts/continuous_sharp_plateau.py:19` — and that script was added in `be648f8` (2026-07-25 10:28), **the same commit as the result the risk is said to have preceded**. `git show 26d45c1:docs/paper2/STRONGER-STATEMENTS.md` (the 09:06 pre-run text, the only one there is) states, for the sharp variant, a cost, a payoff and one caveat — "changing the reward shape changes every number in the mechanism tables" — and nothing about planner competence; `grep -c "gradient\|competence"` on that revision returns 0. This says the risk is not *recorded* in advance, not that it was not *considered*. Supportable rewordings: "a risk recorded with the variant's script", or drop "pre-registered" |
| **F2** | **814** | "\paragraph{**We predicted partial repair**; we measured none.}" | **NOT SUPPORTED as a temporal claim.** Pickaxe: `git log -S"we predicted partial repair"` → first occurrence `60b85cd` **2026-07-18**, one day *after* the measurement (`dc27f7b` 2026-07-17 09:19). The instrumentation that would detect partial repair (`sample_contains_mode_per`, the four-way partition summary) was added in the same commit as the run, so the *expectation* is real and designed-for, but nothing dated states it in advance. "The instrument was built to detect partial repair; none occurred" is the supportable form |
| **F3** | **820** | "Ablation 2: a zero-curvature square **falsifies** the curvature reading." | **SUPPORTED as logic, MISLEADING as chronology.** It is a genuine falsification test, but B5 dates both the hypothesis (born of the 2026-07-17/18 result) and the test (2026-07-19/20) after the finding. "falsifies" is fine; the paragraph does not currently say the ablation was added afterwards |
| **F4** | **139** | "The **falsifiable** content is the dependence itself … We therefore measured it properly, at 50,000 …" | **SUPPORTED.** The paper states the ordering itself (a correction after a review). B9: the sign was not predicted, and the paper does not claim it was |
| **F5** | **375** | "…a Wilson lower bound per cell at level $\delta/K$ over a cell family **fixed in advance** (so selecting a level set afterwards is legitimate)" | **SUPPORTED, as a statistical not a temporal claim.** `scripts/gate_density_step_t.py::apriori_cell_family()` computes the family "WITHOUT looking at the data" and derives the per-cell z from `delta / N_CELLS_APRIORI`, which is exactly the multiplicity discipline the sentence claims. Everything in that script was written in one commit (`44fa512`), so there is no *dated* pre-registration — and none is needed for this claim |
| **F6** | **816** | "A 76-artifact code inspection **locates the failure precisely**." | **SUPPORTED post-hoc, with a caveat the paper does not carry.** B10: the classifier is post-hoc and its partial-repair branch was **vacuous** for a day (`per["p1"]` vs `"patch1"`), and the fix changed the headline reading to 34/76. The audit script now re-derives the corrected numbers |
| **F7** | **295** | "The two hypotheses **are measured, and measured sharply** …" (`prop:knobinv`) | **SUPPORTED as written.** It claims measurement, not prediction. Note for the appendix: C1–C3 record that four propositions were reverse-engineered from measurements that looked exact — post-hoc theory, honestly labelled ("hypotheses either derived or measured to a stated precision") |
| **F8** | **641** | "each **prediction** inside the 300-gate Wilson interval" | **SUPPORTED.** The (1−r)^N exactness check is pre-specified (A4) and the prediction is the theory's, not a fitted quantity |
| **F9** | **182** | "Two things follow about how the threshold may be used, and **an earlier draft of this section violated both**." | **SUPPORTED and to the paper's credit** — it is the paper stating its own post-hoc correction (ε\* compared across streams was replaced by an in-sample identity, `e71aaa3` → `93aab59`) |
| **F10** | **779** | "certified with an invented mode **unfalsifiable by its gate sample**" | **SUPPORTED.** Descriptive of the artifact, not a claim about our process |

## G. Summary counts

* PRE-SPECIFIED with a dated prediction, then CONFIRMATORY: **14** (A1–A14) —
  the whole 1D story: mechanism, axis separation, smooth contrast, ε axis, both
  1D instruments, the GPT-5.x synthesis trichotomy, the Qwen family check.
* Added after the result they respond to: **15** (B1–B15) — DIAGNOSTIC
  (review- or error-driven) **5** (B4, B7, B11, B14, B15); EXPLORATORY /
  EXPLORATORY ABLATION **5** (B1, B3, B5, B6, B8); POST-HOC **3**
  (B9, B10, B13); mixed **2** (B2 post-hoc test of pre-specified theory, B12
  pre-specified measurement on a post-hoc instrument).
* POST-HOC theory: **10** result files (C1–C10), all in the last 40 hours, in a
  domain the design spec had explicitly scoped out.
* `main.tex` phrases claiming pre-registration or falsification: **10** examined
  (F1–F10); **2 not supported** (F1, F2), **1 supported but chronologically
  misleading** (F3), **7 supported**.

## H. How to re-derive every date in this ledger

All read-only. The classifications are judgements; the dates are not.

```bash
# the spec as first committed, with its "Nothing in this spec has been run."
git show 1c9bd05:docs/specs/2026-07-06-continuous-hybrid-cwm-design.md
# the "Predictions to check against" block, and that it precedes the run
git show 05412f9 -- docs/specs/2026-07-06-continuous-hybrid-cwm-design.md
git log -1 --date=iso --format='%h %ad %s' 05412f9   # 2026-07-07 09:44 +0000
git log -1 --date=iso --format='%h %ad %s' c21ece9   # 2026-07-07 11:22 +0100
# first appearance of every results artifact (this is the "first measured" column)
git log --no-renames --date=short --format='COMMIT|%h|%ad|%s' \
    --diff-filter=A --name-only -- results/
# the pre-run version of STRONGER-STATEMENTS.md
git show 26d45c1:docs/paper2/STRONGER-STATEMENTS.md
# F2: first written form of the partial-repair prediction
git log --date=short --format='%h %ad %s' -S"we predicted partial repair" \
    -- docs/EXPERIMENTS.md docs/paper2/
# what the spec never mentions (returns 0 on both revisions)
git show 1c9bd05:docs/specs/2026-07-06-continuous-hybrid-cwm-design.md \
  | grep -ic "mitigat\|distrust\|fence\|patch2d\|square\|curvature"
grep -ic "mitigat\|distrust\|fence\|patch2d\|square\|curvature" \
    docs/specs/2026-07-06-continuous-hybrid-cwm-design.md
# the F-column line numbers are HEAD's, not the working tree's
git show HEAD:docs/paper2/main.tex | grep -n "pre-registered\|falsif\|fixed in advance"
```

Caveat on the "first measured" column: it is the date a result was **committed**,
which is an upper bound on when it was run. Where a prediction and its result land
in the same commit (B5's calibration, F1's script) the ledger says so explicitly
rather than inferring an order the record does not contain.

The honest headline: paper 2's **1D core is genuinely pre-registered**, with
predictions committed 38 minutes to 2 hours before the runs that tested them and
a written go/no-go rule that was met. Everything about the **2D instrument, the
mitigation, the second planner family, the third and fourth model families, both
ablations and all ten theory results is post-specification** — mostly good
science done in response to reviews, but none of it predicted in advance, and two
sentences in the paper currently say otherwise.
