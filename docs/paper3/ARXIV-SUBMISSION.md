# arXiv submission guide — "An Enclosed Mode Is a Gauge Choice"

Paper 3 of the trilogy. Companions: paper 1 **arXiv:2607.14169**
(`aguilar2026verified`), paper 2 **arXiv:2608.17956** (`aguilar2026omitted`).

Status: **ANNOUNCED 2026-08-31 as [arXiv:2608.28541](https://arxiv.org/abs/2608.28541)**
(submitted 2026-08-28 as `submit/8006768`; unsubmitted, corrected and
resubmitted the same day — see `CHANGELOG-corrections.md`). The announced v1
carries the correction. The ID is in the README, `STATE.md` and here.

The entry for anyone citing this paper:

```bibtex
@misc{aguilar2026enclosed,
  title         = {An Enclosed Mode Is a Gauge Choice: Topology Relative to Reach in Certified Code World Models},
  author        = {Aguilar Mart\'in, Javier},
  year          = {2026},
  eprint        = {2608.28541},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  note          = {Paper 3 of the series. arXiv:2608.28541, \url{https://arxiv.org/abs/2608.28541}; repository: \url{https://github.com/JaviMaligno/code-world-models}},
}
```

What was submitted, for the record:

- Primary **cs.LG**, cross-list **cs.AI** at submission time; **eess.SY
  added afterwards** (announced 2026-09-01) once the account's `eess` group
  was enabled — the v1.5 dropdowns only offer archives from your registered
  groups, which is why it could not go in with the paper.
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

1. ~~Add the arXiv ID to the README and to `docs/paper3/STATE.md`.~~ Done.
2. ~~Update this repo's citations of paper 3 anywhere they say
   "in preparation".~~ Nothing inside this repo cites paper 3.
3. ~~eess.SY cross-list.~~ Done — requested 2026-08-31 (`submit/8015233`)
   and announced 2026-09-01 00:00 UTC. Subjects now read cs.LG (primary);
   cs.AI; eess.SY. For next time: the v1.5 forms only offer archives from
   the account's registered groups, so enable the group under *Change User
   Information* BEFORE submitting and the cross-list can go in with the
   paper instead of afterwards.
4. Companion blog post, if the trilogy pattern continues (paper 2's is
   scheduled for 2026-08-30 from the `personal-website` repo).
