# Paper 2 — response to the fourth external review (2026-08-01)

Reviewer's position: focused major revision (two reproducibility/interpretation problems and
one technical precision), then minor revision. Same protocol as rounds 1–3.

## Verdicts and actions

| # | Point | Verdict after verification | Action | Status |
|---|---|---|---|---|
| 1 | The Qwen 2D contrast is confounded with the serving backend (full = HF router, incomplete = vLLM; mixed file's metadata misdescribes; no per-cell provenance) | **Reviewer RIGHT.** The reviewer offered two remedies; we took the solid one | **The matched campaign was run**: both arms × 3 seeds on ONE pinned backend (vLLM 0.26.0 on an H100, bf16 checkpoint at a recorded Hub revision sha, the checkpoint's own `generation_config` applied to both arms; `results/qwen_vllm_provenance.json`). Result: full 3/3 at gate 1.000 zero iterations, incomplete refused 3/3 at 0.993–0.997 — and the mixed first pass's incomplete cells reproduce these accuracies to three decimals, seed by seed (pinned by an audit claim). The mixed file is demoted to an exploratory unmatched spot-check, its metadata quirks documented in REPRO-FACTS; the paper's ablation-3 paragraph now cites the matched contrast and states n=3 as an exploratory diagnostic, not a replication. A `--out-tag` (filename-only, never a treatment key) prevents future mixed-provenance resumes | DONE |
| 2 | 105/111 are draws, not blocks (called "blocks" at :35, :52, :679) | **RIGHT on the defect; the count differs**: under the audit's own block key (mini and large share their samples; cart and pendulum do not) the 111 draws span **70** distinct blocks, not 36, with **64/70** exact on every draw and the six failures in six distinct blocks | All three sites now say draws, with the block accounting alongside; an audit claim derives 111/105/70/64/6 from the records | DONE |
| 3a | The essential-infimum event ignores the position component of the sup-norm disagreement: D = max(ω′, position excess) ≤ ω′·max(1,dt) | **RIGHT** — the reviewer's bound is exactly what the transition carries | Target interval is now ω′ ∈ [(θstop−θ)/dt, ε/max(1,dt)], δ < min(δ₀, ε·dt/max(1,dt), κ·dt), and the proof displays both components with the max(1,dt) factor | DONE |
| 3b | ε\*=0 asserted "on these instruments" while the approachability hypothesis is admitted to be an assumption | RIGHT | Conditional statement: ε\*=0 under the hypothesis, "an assumption the data are consistent with, not a theorem about them"; the O(ε²) bound stays unconditional (it never used the hypothesis) | DONE |
| 4 | Contribution :50 still says "unsatisfiable at finite Lipschitz constant" | RIGHT — a compactly supported smooth error is the counterexample to the general reading | Restated at fixed amplitude/tolerance on vanishing volume, with the diverging-constant reading and the occupies-not-evades parenthesis | DONE |
| 5 | Supplement regressions to causal language (:1214 "excludes the curvature reading", :1229 "one-variable comparison") | RIGHT | Headers and sentences moved to did-not-suffice / targets-the-post-state phrasing; the reviewer's ":1235 not the reason / survives as mechanism" strings do not occur in the current source (searched), so the two real sites are the fixes | DONE |
| 6 | Stale phrases: :45 "vanishes"+"one accepted artifact"; :679 "no sampling check caught"; "danger law is everything"; "each excluded by measurement"; "a second family" | RIGHT on all five | "nearly vanishes ... in 105 of 111 draws"; five known invented-mode artifacts (four GPT — three of them held-out-accepted — plus Claude's); "their own acceptance samples could not catch --- the independent gate caught one of the four, by the luck of its draw"; "dominant --- near-exhaustive for the shipment of mode-blind artifacts"; "each shown insufficient by measurement"; "two further model-family spot-checks at tiny n" | DONE |
| 7 | preprint-draft.md dangerously stale | RIGHT | Prominent OBSOLETE-HISTORICAL warning banner listing exactly which of its claims were later corrected, pointing at main.tex + the CI audit as authoritative | DONE |
| 8 | REVIEW-RESPONSE row 5 still says 109/111 and 34/36; Qwen row overstated | RIGHT | Row 5 annotated as the round-1 record with the superseding numbers; row 18 already carried the mixed-backend note and now the matched campaign supersedes it | DONE |
| 9 | REPRO-FACTS does not record the mixed provenance | RIGHT | Split-provenance note added naming both files, the metadata quirks and the provenance JSON | DONE |
| 10 | Lean build not certifiable by the reviewer (90 s no output) | Expected — the first build compiles Mathlib stragglers; subsequent builds are minutes | `formal/README.md` documents this; `lake build` completed on this machine (8697 jobs) and the CI job is listed as future work | NOTED |

## Count movements this round (all derived, none typed)

The matched campaign adds 6 cells: 1028 → **1034** artifacts over 34 campaign files; in-sample
passed 647 → **650**; held-out accepted 610 → **613** (the three new full cells); train
reproduction 99 → **102**; full-arm 434 → **437**; calls 3901 → **3922**. Regressions (40 over
25 blocks), reverse regressions (3), the 60/60, and every 1D number are unchanged. 712 audited
values agree at printed precision.
