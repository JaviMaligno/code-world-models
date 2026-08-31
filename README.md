# Code World Models vs LLM-as-Policy (MVP)

Reproduces, at small scale, the Code World Models result: synthesized verifiable
code + MCTS vs a direct LLM policy. See `docs/specs/` and `docs/plans/`.

## 📄 Papers

### Paper 1 — discrete games (published)

**When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models** — Javier Aguilar Martín (AGILabs).

- **arXiv:** [arXiv:2607.14169](https://arxiv.org/abs/2607.14169) (v2)
- **PDF:** [`docs/paper/main.pdf`](docs/paper/main.pdf) (43 pp)
- **LaTeX source:** [`docs/paper/main.tex`](docs/paper/main.tex) · bibliography [`docs/paper/references.bib`](docs/paper/references.bib)
- **Markdown draft:** [`docs/paper/preprint-draft.md`](docs/paper/preprint-draft.md)
- **arXiv bundle & revision runbook:** [`docs/paper/ARXIV-SUBMISSION.md`](docs/paper/ARXIV-SUBMISSION.md)

### Paper 2 — continuous / hybrid state spaces (published)

**An Omitted Mode Is a Rare Rule: The Sampling-Verification Danger Law in Continuous Code World Models** — Javier Aguilar Martín (AGILabs).

The danger law transfers to continuous state spaces (its ingredients are
measure-theoretic), a smooth truth/model pair provably cannot realize the
localized verified-but-wrong geometry, and repair-from-data turns out to be
geometry-dependent: exact on 1D clamps, absent on 2D regions via a template
prior over low-complexity region forms.

- **arXiv:** [arXiv:2608.17956](https://arxiv.org/abs/2608.17956)
- **PDF:** [`docs/paper2/main.pdf`](docs/paper2/main.pdf) (92 pp)
- **LaTeX source:** [`docs/paper2/main.tex`](docs/paper2/main.tex) · bibliography [`docs/paper2/references.bib`](docs/paper2/references.bib)
- **arXiv bundle, guide & form-ready abstract:** [`docs/paper2/ARXIV-SUBMISSION.md`](docs/paper2/ARXIV-SUBMISSION.md) · [`docs/paper2/abstract-arxiv.txt`](docs/paper2/abstract-arxiv.txt)

### Paper 3 — enclosed modes, and topology relative to reach (published)

**An Enclosed Mode Is a Gauge Choice: Topology Relative to Reach in Certified Code World Models** — Javier Aguilar Martín (AGILabs).

Acceptance-with-certainty determines a model only on the reachable query set, so
beyond reach its content is gauge: on a closed ring the wrong-topology
filled-disc artifact is unfalsifiable by *any* sampling gate and bitwise
harmless at play. What makes an omission dangerous is not its shape but whether
a competent planner's path crosses it — an equally wide channel collapses the
exploitation when it faces the start and leaves it untouched when hidden —
while repair is parameter- and sensor-bound, and the mitigation that works has
to match both the dimension and the direction of the model's error.

- **arXiv:** [arXiv:2608.28541](https://arxiv.org/abs/2608.28541)
- **PDF:** [`docs/paper3/main.pdf`](docs/paper3/main.pdf) (33 pp)
- **LaTeX source:** [`docs/paper3/main.tex`](docs/paper3/main.tex) · bibliography [`docs/paper3/references.bib`](docs/paper3/references.bib)
- **arXiv bundle, guide & form-ready abstract:** [`docs/paper3/ARXIV-SUBMISSION.md`](docs/paper3/ARXIV-SUBMISSION.md) · [`docs/paper3/abstract-arxiv.txt`](docs/paper3/abstract-arxiv.txt)
- **Lean formalization:** [`formal/Paper2Props/Paper3Ring/`](formal/Paper2Props/Paper3Ring) · ledger [`docs/paper3/FORMALIZATION.md`](docs/paper3/FORMALIZATION.md)
- **Where things stand:** [`docs/paper3/STATE.md`](docs/paper3/STATE.md) · corrections [`docs/paper3/CHANGELOG-corrections.md`](docs/paper3/CHANGELOG-corrections.md)

### Shared

- **Results & reproduction commands:** [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) · theorems & narrative [`docs/RESEARCH-DIRECTION.md`](docs/RESEARCH-DIRECTION.md)
- **Per-seed artifacts** (including every synthesized program and every relayed
  transcript) are versioned under `results/`.

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # then fill in Azure credentials

## Test
    pytest

## Paper guards

Both run in CI and locally, so a regression fails before a preprint does:

    bash scripts/check_latex.sh            # compile both papers: 0 overfull, 0 undefined refs
    python scripts/audit_paper2_numbers.py # every paper-2 table cell re-derived from results/
    python scripts/audit_paper3_numbers.py # same, for paper 3's tables and counted claims
    python scripts/audit_paper_claims.py   # the claims contract (scope, units, evidence labels)
