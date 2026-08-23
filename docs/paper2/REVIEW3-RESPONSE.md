# Paper 2 — response to the third external review (2026-07-30)

Reviewer's position: major revision, now for "un bloqueante teórico y un conjunto de
inconsistencias localizadas"; after these, "minor revision / weak accept". Same protocol as
rounds 1–2: verdict verified against text or data before editing.

## Verdicts and actions

| # | Point | Verdict after verification | Action | Status |
|---|---|---|---|---|
| 1 | The clamp-free-window hypothesis does not prove ess-inf 0: one point θ*<θ_stop at positive distance leaves V∩strip empty for small ε | **Reviewer RIGHT — and the re-derivation found a second gap they did not flag**: D is a *maximum* over the rollout's contacts, so the constructed soft contact must be the rollout's only one; an earlier or later coarse contact pushes D past ε even with the strip fixed | Hypothesis replaced by *slow approachability at the horizon's end*: a boundary state (θ_stop, ω★) with two-sided margin \|ω★+F·dt\| < gain·dt·a_max that clamp-free, contact-free histories approach within every δ at step T−1, with the window's two actions open. Proof rewritten: δ < min(δ₀, ε·dt, κ·dt), density bounded below on image∩ball via the two-action Jacobian (only invocable on the clamp-free branch), the final fresh action lands the only contact of the rollout in (0, ε] | DONE |
| 1b | "M bounds the density of the clamped coordinate" — the law has an atom | RIGHT | → density of the absolutely continuous part below the stop, atom noted | DONE |
| 1c | 0.0018 does not "witness" a for-every-ε property | RIGHT | → "remains an assumption; the data supply consistency, with nothing suggesting a positive floor" | DONE |
| 2 | The four GPT phantoms are mis-placed in the held-out section as (i) violations | **Reviewer RIGHT; the wrong sentence was OURS from round 2.** Verified: all four have the true mode in the training block (one contact transition each) — they are inside the 111, not (i) violations. Moreover (i) has **no** violation in the audited arms: all 60 mode-free-train draws are probe-blind | Sentence replaced by the measured 60/60 statement; the phantoms moved to the claim they actually bound (eval-exactness) | DONE |
| 3 | "One accepted artifact known to be wrong off-sample" false; need per-artifact accounting | **RIGHT, and the data are worse than the reviewer suspected**: 3 of the 4 phantoms are accepted by the independent gate at eval 1.000 (no rollout visits the invented stop's region); the 4th drew samples that do visit it and is rejected (11 off-mode gate failures, 13 on eval). Chance decided which. **Bonus finding**: the regressions' "one exception is a Qwen artifact" was stale from the 625-era snapshot — the only off-mode regression among the 40 is the fourth phantom | Scope notes rewritten with the full accounting; the exception's identity corrected; six new audit claims pin everything (mode-in-train, 3-in-610, the 131–280 grid mismatches, the 60/60, the exception identity) | DONE |
| 4 | Conclusion says "repairs it exactly"; "the gate catches the superstitious patch" too strong | RIGHT — the gate caught the two superstitious patches and none of the four phantoms | Conclusion now: 105 of 111; two caught by the gate; four invented stops no sampling check caught and the behavioural grid did | DONE |
| 5 | Abstract: "confining it exactly requires a discontinuity" false (C∞ bump) | RIGHT | → fixed-amplitude/uniform-L budget statement; "smooth compactly supported errors satisfy the budget by occupying it, not by evading it" | DONE |
| 6 | Not "eight single-variable interventions" | RIGHT — the guided arm changes ≥4 things, landing/clamp change semantics+dwell+evidence, dose changes start distribution+rollout count | → "eight targeted interventions, each aimed at one candidate explanation", with the induced side-changes enumerated in the section paragraph | DONE |
| 7 | "Excludes prompting and budget" too strong | RIGHT — one prompt at 3× budget did not suffice; memory, tools, other prompts untried | Table header → "what did not suffice, as tested"; mechanism paragraph names the untried variants | DONE |
| 8 | "The evidence determines the region" mixes population reach with sample identification | RIGHT | Three-way split now explicit: population identifiability (2000-rollout measurement), finite-sample recoverability in the circle class (12/20 baseline, 20/20 at 185°, with the charge assigned per sample), template-library identifiability **not proven and not relied on** | DONE |
| 9 | The universal density constant is not a global lower bound (missing coverage fraction) | RIGHT | Scoped: the Jacobian gives the conditional density on clamp-free two-action images; the marginal needs the history-coverage fraction, established by erosion+measurement on the cart and **not** for the pendulum; "verified where used, not inherited from the family" | DONE |
| 10 | The fencing corollary bounds new-coverage fences, not deployment cost or convergence | RIGHT — duplicates unlimited, an episode with 24 observed | → "caps a count; not a completion guarantee", with the non-guarantees listed | DONE |
| m1 | Two-factor equality-iff needs r<1 | RIGHT | Degenerate case excluded in the statement; vacuity test added to the falsification suite (20 tests now) | DONE |
| m2 | "danger still lives exactly in the joint-miss event" needs scope | RIGHT — D_N also collects other accepted artifacts' costs (the invented-stop class among them) | Scoped | DONE |
| m3 | ":602 the form is what is not induced" recurrence | RIGHT — third site missed in round 2 | → located-rule phrasing | DONE |
| m4 | Review-response length figures inconsistent (35 vs 29 vs 86/38) | RIGHT | Measured from main.aux: 87 pp total, conclusion p38, supplement from p39; the stale row now says page counts are measured, not tracked in that table | DONE |
| m5 | Bookmark warnings (math in titles) | RIGHT | \texorpdfstring on the three ε titles; 0 warnings | DONE |

## Notes

* Point 1's repair makes the hypothesis *stronger* (accumulation at the boundary through
  contact-free histories, two-sided margin, horizon's-end placement) and the proof correct;
  the paper says plainly the hypothesis is an assumption the data are only consistent with.
* Point 3's accounting strengthens the paper's own thesis: the independent gate and the
  100-rollout evaluation caught one phantom in four, and which one was chance — Proposition
  prop:ident operating on the checks themselves. The grid is what convicts the other three.
* 706 audited values agree; claims linter clean on all six rules; structural guard clean;
  87 pp, zero overfull, zero bookmark warnings; falsification suite 20/20.
