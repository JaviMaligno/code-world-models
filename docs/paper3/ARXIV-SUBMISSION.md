# arXiv submission guide — "An Enclosed Mode Is a Gauge Choice"

Paper 3 of the trilogy. Companions: paper 1 **arXiv:2607.14169**
(`aguilar2026verified`), paper 2 **arXiv:2608.17956** (`aguilar2026omitted`).

Status: **SUBMITTED 2026-08-28** as `submit/8006768` (status at submission
time: processing; Javier pressed Submit after reviewing the preview and
the compiled PDF). Awaiting announcement — when the ID arrives, add it to
the README and to this file.

What was submitted, for the record:

- Primary **cs.LG**, cross-list **cs.AI**. **eess.SY could NOT be
  cross-listed** (unlike paper 2): the submitter account's registered
  groups are cs and math only, and the v1.5 cross-list dropdown offers
  only those archives. If wanted, request the eess.SY cross-list after
  announcement (or extend the account's groups first next time).
- Licence **CC BY 4.0** (matching papers 1 and 2). Author
  `Javier Aguilar Mart\'in` (TeX encoding in the form; renders with the
  accent). Comments: `33 pages, 2 figures. Paper 3 of a series
  (companion papers: arXiv:2607.14169, arXiv:2608.17956). Code, data,
  and Lean formalization:
  https://github.com/JaviMaligno/code-world-models`.
- Abstract: `abstract-arxiv.txt` (plain ASCII, 1918 characters, under
  the 1920 hard limit), condensed from the paper's post-editorial
  abstract; paste that file, not the LaTeX abstract.
- Bundle: `arxiv-submission-paper3.tar.gz` = `main.tex`, `main.bbl`,
  `references.bib`, `figures/gamma_curves.pdf`,
  `figures/danger_curve.pdf`. No `\input` files — the tex is
  self-contained. **`main.bbl` kept against the scan's suggestion**, as
  with paper 2: the bundle is verified to compile with pdflatex alone
  (33 pages, only the benign `OMS/cmtt` font-shape warning), and arXiv
  compiled it with pdflatex on TeX Live 2025: SUCCEEDED, HTML conversion
  Success, page count matching the local build.
- The source state is the archival tag `paper3-v1` (both review cycles
  closed: mathematical 17→10→5→4→0, editorial 24→10→3-mechanical).

To regenerate the bundle after any edit:

```bash
cd docs/paper3
pdflatex -interaction=nonstopmode main.tex && bibtex main && \
  pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
tar --exclude='._*' -czf arxiv-submission-paper3.tar.gz \
  main.tex main.bbl references.bib \
  figures/gamma_curves.pdf figures/danger_curve.pdf
```

After announcement:

1. Add the arXiv ID to the README and to `docs/paper3/STATE.md`.
2. Update this repo's citations of paper 3 anywhere they say
   "in preparation".
3. Decide on the eess.SY cross-list request.
4. Companion blog post, if the trilogy pattern continues (paper 2's is
   scheduled for 2026-08-30 from the `personal-website` repo).
