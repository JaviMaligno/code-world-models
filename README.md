# Code World Models vs LLM-as-Policy (MVP)

Reproduces, at small scale, the Code World Models result: synthesized verifiable
code + MCTS vs a direct LLM policy. See `docs/specs/` and `docs/plans/`.

## Setup
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env   # then fill in Azure credentials

## Test
    pytest
