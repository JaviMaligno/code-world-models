# Paper 3 — corrections after submission

One entry per factual correction to `main.tex` made after the arXiv
submission of 2026-08-28 (`submit/8006768`), so the record of what changed
and why lives outside the paper (the paper states what is true, not its own
history — `.claude/skills/paper-claims/SKILL.md`, narrative contract).

## 2026-08-28 — `tab:ndim`: $r(6)$ was printed as a censored zero, and is not one

**Found** while cross-checking the blog post's numbers against the result
JSONs (the article quoting the table, not the table itself).

**What was wrong.** `tab:ndim` printed
`$r(n)$ & 0.0133 & 0.0033 & 0.0017 & $0^{\dagger}$ & $0^{\dagger}$`, i.e. a
censored zero at both $n = 5$ and $n = 6$, and the contributions bullet said
"censored zeros at $n = 5, 6$". But `results/continuous_shellfield.json` —
the file the caption cites, single-commit and never re-run — records
**1 contact in 600 rollouts at $n = 6$** ($r = 0.001\overline{6}$, the same
as $n = 4$). Only $n = 5$ is a genuine $0/600$.

This inverts the claims contract's own rule about censored zeros: the paper
must not state a censored zero as a zero, and equally must not state an
observed count as a censored zero.

**Why it survived.** Five adversarial mathematical rounds and three
editorial rounds (REVIEW-CODEX.md, REVIEW-EDITORIAL.md) all read the table
against the *prose*, never against the JSON. The claims linter checks the
*form* of a printed zero — dagger present, Wilson upper given — not whether
the count behind it is really zero. Paper 2 had `audit_paper2_numbers.py`
for exactly this; paper 3 had no equivalent.

**Fixed.**

1. The cell now reads `0.0017` at $n = 6$; the dagger stays only on $n = 5$.
2. The contributions bullet reads "contacts $1/600$ at $n = 4$ and at
   $n = 6$, a censored zero at $n = 5$", and says plainly that the
   $600$-rollout calibration is at its own resolution floor from $n = 4$ on
   — the collapse rate ($0.411$ per dimension) is measured on the
   $10{,}000$-rollout cone sweep, which is unaffected.
3. The caption's provenance was wrong by omission and is now per row: $r(n)$
   from `continuous_shellfield.json`, the two $J$ rows from
   `continuous_shellfield_nav.json`, play cost and contact rate from
   `continuous_shellfield_play.json`. (Those three sources were always
   correct in the numbers; only the citation was incomplete.)
4. **New guard:** `scripts/audit_paper3_numbers.py` parses the tabulars by
   label and compares every sourceable cell against its JSON at the paper's
   printed precision, with censored cells required to have a zero count. It
   reproduces this exact failure when the old cell is re-injected, and
   passes on the corrected tex. Run it with the claims linter.

**Effect on the paper's claims.** None of the headline claims move: the
rarity collapse is carried by the $10{,}000$-rollout measurement and its
two proofs, the independence-of-axes result is carried by the play row
(unchanged, $\mathrm{pc} \approx 1.0$ at every $n \le 6$), and the
$n$-dimensional section's argument is unchanged. What changes is one table
cell, one parenthetical, and a caption's provenance.

**Submission status — RESOLVED 2026-08-28.** Javier chose unsubmit-and-replace
over a v2. Executed the same day, before announcement:

1. `submit/8006768` unsubmitted ("Submission status set to 'incomplete'").
   It had been queued for **Sun 30 Aug 2026 20:00 US Eastern**; unsubmitting
   removed it from that batch.
2. The stale `main.tex` deleted and the corrected one uploaded (it is the only
   file that changed: no citation moved, so `main.bbl` is untouched and was
   again **retained** against arXiv's suggestion to drop it).
3. Re-checked and recompiled by arXiv: pdflatex on TeX Live 2025, `main.tex =>
   main.pdf [SUCCEEDED]`, top-level and compiler auto-selections unchanged.
   The corrected row is verified *in the rendered PDF*, not just the source:
   the page's text stream reads `r(n) 0.0133 0.0033 0.0017 0† 0.0017`.
4. Metadata survived the round trip intact (title, author, the 1918-character
   abstract, comments) and so did the categories (cs.LG primary, cs.AI
   cross-list) and the CC BY 4.0 licence. PDF re-previewed as arXiv requires.
5. **Resubmitted**: status back to `submitted`. The announcement slot moves to
   the next cycle after this one, so expect the ID roughly a day later than
   the original Sunday slot.

The only cosmetic casualty: the preview page's HTML-rendering widget reported
"Unauthorized. Your session may be expired" instead of showing the HTML
version. The PDF path is what gates announcement and it was green; the HTML
version is generated server-side after announcement anyway.
