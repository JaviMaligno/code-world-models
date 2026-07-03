# Code World Models vs LLM-as-Policy (MVP)

Reproduces, at small scale, the Code World Models result: synthesized verifiable
code + MCTS vs a direct LLM policy. See `docs/specs/` and `docs/plans/`.

## 📄 Preprint

**When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models** — Javier Aguilar Martín (AGILabs).

- **PDF:** [`docs/paper/main.pdf`](docs/paper/main.pdf) (40 pp)
- **LaTeX source:** [`docs/paper/main.tex`](docs/paper/main.tex) · bibliography [`docs/paper/references.bib`](docs/paper/references.bib)
- **Markdown draft:** [`docs/paper/preprint-draft.md`](docs/paper/preprint-draft.md)
- **arXiv submission bundle & guide:** [`docs/paper/ARXIV-SUBMISSION.md`](docs/paper/ARXIV-SUBMISSION.md)
- **Results & reproduction commands:** [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) · theorems & narrative [`docs/RESEARCH-DIRECTION.md`](docs/RESEARCH-DIRECTION.md)

*(arXiv ID to be added once posted.)*

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # then fill in Azure credentials

## Test
    pytest
