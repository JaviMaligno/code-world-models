# arXiv submission guide — "An Omitted Mode Is a Rare Rule"

Paper 2 of the trilogy. Companion paper 1 is **arXiv:2607.14169** (currently v2),
cited as `aguilar2026verified`; paper 3 is unpublished and is NOT referenced.

Status: **ready to submit** (new submission, not a replacement).

## 1. What is ready

- `main.tex` — the paper (article class; amsthm, booktabs, natbib/plainnat,
  hyperref, geometry, amssymb, graphicx, xcolor — all standard TeXLive).
- `references.bib` — 21 entries, all citation keys resolved (checked: no
  undefined citations, no uncited entries).
- `main.bbl` — pre-generated bibliography so arXiv does not need to run bibtex.
- `figures/*.pdf` — 4 vector figures (`danger_threshold`, `reach_mechanism`,
  `axis_separation`, `smooth_localization`), regenerated from the result JSONs by
  `scripts/make_paper2_figures.py`.
- `abstract-arxiv.txt` — **the abstract for the submission form**: plain ASCII,
  1865 characters, under arXiv's hard 1920-character limit. Paste this, not the
  LaTeX abstract (which carries `\citep`, math mode and em dashes the metadata
  field will not take).

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
  main.tex references.bib main.bbl \
  figures/danger_threshold.pdf figures/reach_mechanism.pdf \
  figures/axis_separation.pdf figures/smooth_localization.pdf
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
6. After announcement: add the arXiv ID to the README, and update paper 3's
   `references.bib` entry for this paper from "in preparation" to the real ID.

## 4. Verification done before submission (2026-07-24)

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
- **Numbers spot-checked against the JSONs**: the d@N columns, the CEM paired
  t-intervals, the Wilson bounds, and the artifact-audit class counts.

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
