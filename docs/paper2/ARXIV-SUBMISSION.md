# arXiv submission guide — "An Omitted Mode Is a Rare Rule"

Paper 2 of the trilogy. Companion paper 1 is **arXiv:2607.14169** (currently v2),
cited as `aguilar2026verified`; paper 3 is unpublished and is NOT referenced.

Status: **announced as arXiv:2608.17956** (<https://arxiv.org/abs/2608.17956>),
submitted 2026-08-18 as `submit/7965524`. The README carries the ID, and paper 3's
`references.bib` now cites the real preprint instead of "in preparation" — it lives
in *this* repository after all, on branch `claude/paper-tres-topology-4w813y`
(`docs/paper3/`), not in one of its own. What stays open is §3 step 7: the blog post
is scheduled, not yet out.

The entry paper 3 should use (mirroring how this paper cites paper 1 as
`aguilar2026verified` in `references.bib`):

```bibtex
@misc{aguilar2026omitted,
  title         = {An Omitted Mode Is a Rare Rule: The Sampling-Verification Danger Law in Continuous Code World Models},
  author        = {Aguilar Mart\'in, Javier},
  year          = {2026},
  eprint        = {2608.17956},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  note          = {Companion paper (paper 2). arXiv:2608.17956, \url{https://arxiv.org/abs/2608.17956}; repository: \url{https://github.com/JaviMaligno/code-world-models}},
}
```

What was submitted, for the record: primary **cs.LG**, cross-lists **cs.AI** and
**eess.SY**, licence **CC BY 4.0** (matching paper 1), author `Javier Aguilar Mart\'in`
(arXiv stores the accent in TeX encoding), comments `92 pages, 5 figures` plus the
public repository URL. arXiv compiled the bundle with pdflatex on TeX Live 2025 to
**92 pages** — the same page count as the local build — with 0 undefined references,
0 undefined citations and 0 overfull boxes. `main.bbl` was kept: arXiv's scan suggests
deleting it in favour of `references.bib`, and this bundle is verified to compile
without bibtex, so the suggestion is declined on purpose.

One upload note for next time: macOS `tar` writes AppleDouble `._*` members for
extended attributes even with `--exclude='._*'`. arXiv strips them automatically and
reports each removal; the 12 real files are unaffected.

## 1. What is ready

- `main.tex` — the paper (article class; amsthm, booktabs, natbib/plainnat,
  hyperref, geometry, amssymb, graphicx, xcolor — all standard TeXLive), plus its
  four `\input` files: `related-work.tex`, `appendix-protocol.tex`,
  `appendix-repro.tex`, `appendix-prespec.tex` (all in the tarball; arXiv fails
  without them).
- `references.bib` — all citation keys resolved (0 undefined, checked in CI).
- `main.bbl` — pre-generated bibliography so arXiv does not need to run bibtex.
- `figures/*.pdf` — **5** vector figures (`danger_threshold`, `reach_mechanism`,
  `axis_separation`, `smooth_localization`, `per_seed_distributions`),
  regenerated from the result JSONs by `scripts/make_paper2_figures.py`.
- `abstract-arxiv.txt` — **the abstract for the submission form**: plain ASCII,
  1915 characters, under arXiv's hard 1920-character limit, condensed from the
  post-hardening abstract (105/111 draws, 50/56 blocks, 0/156, targeted
  interventions, located rule, 1034 artifacts). Paste this, not the LaTeX
  abstract.

## 2. The submission bundle (upload this)

A ready tarball is at `docs/paper2/arxiv-submission.tar.gz`, containing
`main.tex`, `main.bbl`, `references.bib` and `figures/*.pdf` (the figures are
required — arXiv will not compile without them).

To regenerate after any edit:

```bash
cd docs/paper2
python ../../scripts/make_paper2_figures.py     # refresh figures if data changed
pdflatex -interaction=nonstopmode main.tex && bibtex main && \
  pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
tar --exclude='._*' -czf arxiv-submission.tar.gz \
  main.tex main.bbl references.bib \
  related-work.tex appendix-protocol.tex appendix-repro.tex appendix-prespec.tex \
  figures/danger_threshold.pdf figures/reach_mechanism.pdf \
  figures/axis_separation.pdf figures/smooth_localization.pdf \
  figures/per_seed_distributions.pdf
rm -f main.aux main.log main.out main.blg main.toc
```

Keep `main.bbl` in the tarball (arXiv uses it) and keep `references.bib` too,
for consistency with paper 1's bundle and so the source is self-contained.

## 3. Steps on arXiv that cannot be automated

1. New submission (paper 1's endorsement covers cs.LG; no new endorsement needed).
2. Primary category **cs.LG**; cross-list **cs.AI** and **eess.SY** (the
   instruments are hybrid control systems and the mitigation is a planner).
3. Paste the abstract from `abstract-arxiv.txt` (ASCII, under the char limit).
4. Upload the tarball from §2 and let arXiv compile; check its PDF against
   `main.pdf` (page count, tables, the 4 figures, cross-references, bibliography).
5. Comments field: page count and that code/data are public.
6. After announcement: add the arXiv ID to the README (**done** — arXiv:2608.17956),
   and update paper 3's `references.bib` entry for this paper from "in preparation"
   to the real ID (**done** — `docs/paper3/references.bib` on branch
   `claude/paper-tres-topology-4w813y`, i.e. this repository, not a separate one as
   this guide previously said). Paper 3's `main.bbl` is stale until the next LaTeX
   run, so the citation still renders the old note in the committed `main.pdf`.
7. After announcement, in the **`personal-website` repo**: the companion blog post
   is written and waiting on branch `blog/infer-the-rule-in-one-dimension` (EN+ES,
   hero image done, LinkedIn body hand-written, X thread drafted). **Scheduled for
   2026-08-30** via `scheduled-publish-infer-the-rule-in-one-dimension.yml`, with the
   real arXiv ID and a matching `pubDate` already committed to the branch. That date
   is the first free slot in both the article calendar and the legacy LinkedIn one.
   The merge publishes blog, Dev.to and LinkedIn in one go and is done by the cron —
   nothing to do by hand except the X thread afterwards.

## 3b. Verification of the CURRENT bundle (2026-08-09, post-review v1.6)

- Rebuilt after the four review rounds: 12 files, compiles from a fresh extract
  of the tarball with pdflatex alone (no bibtex): **87 pages, 0 undefined
  references/citations, 0 overfull boxes** (one benign font-shape warning).
- 712 audited values agree; claims linter and structural guard clean; suite 697.
- Everything below this line describes the 2026-07-24 pre-review bundle and is
  kept as the historical record; where it conflicts (357 values, 4 figures,
  82/82, 0/76, the Qwen credits note), the current state supersedes it.

## 4. Verification done before submission (2026-07-24, HISTORICAL)

- **Compiles clean**: 0 errors, 0 overfull hboxes, 0 undefined references or
  citations, 0 bibtex warnings.
- **Bundle matches source**: the tarball's `main.tex` is byte-identical to
  `docs/paper2/main.tex`.
- **Every script cited in the paper exists** and is tracked, including the two
  PatchField2D entry points (`continuous_cem_patch2d.py`,
  `continuous_eps_sweep_patch2d.py`) and `claude_relay_ledger.py`.
- **Re-run validation**: both PatchField2D CPU experiments were re-executed
  from a clean invocation of their entry points and produced results
  byte-identical to the committed JSONs (`continuous_cem_patch2d.json`,
  `continuous_eps_sweep_patch2d.json`), so the paper's §5 CEM row and the
  per-mode eps-flatness numbers reproduce.
- **Numbers mechanically audited, not spot-checked**:
  `scripts/audit_paper2_numbers.py` parses every `tabular` in `main.tex`, looks up
  the row in the JSON the experiment wrote, and compares each cell at the paper's
  own printed precision (derived columns such as the d@N danger products are
  recomputed, not trusted). It also re-checks the counted prose claims (82/82,
  20/20, 62/62, 4/80 at play_cost 1.095, 0/156, the mitigation single-violation
  rows, the CEM paired t-intervals, 0/76 encoded patches). 357 values, all
  agreeing. Wired into CI as the `paper_numbers` job, so a stale transcription
  fails there instead of in a preprint. Two last-digit errors it caught before
  submission: d@80 at x_wall=8 (0.372 -> 0.371) and d@40 at theta_stop=1.6
  (0.737 -> 0.738).

## 5. Honest residual scope (disclosed in the paper, §11)

- Three instruments; two base planner families at one fixed configuration each.
- Repair-from-data collapses on 2D regions: 0/156 mode-containing seeds for
  GPT-5.x (78 distinct samples × 2 sizes) plus a 3-seed Claude cross-family arm
  that fails in the same classes. A Qwen arm on the same cell aborted after its
  3 full-arm cells (HF Inference credits exhausted): it contributes a clean
  translation control (3/3 gate 1.000, both discs exact, blindness 0.0) and no
  induction data. Recorded as exactly that, not papered over.
- mini and large share their gate samples by construction, so pooled "both
  sizes" counts are n samples × 2 synthesis draws; per-size Wilson bounds are
  the ones the paper relies on.
- The Claude arm is agent-relayed over a subscription transport, small-n, with
  the relayed instances instructed not to use tools; the framing is recorded
  verbatim with the transcripts.
