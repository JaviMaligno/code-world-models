#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs the LaTeX toolchain (pdflatex + bibtex) needed to build docs/paper/main.tex
# and the Python dev dependencies needed to run the test suite.
#
# Runs only in remote/web sessions ($CLAUDE_CODE_REMOTE == "true"); on your local
# machine it exits immediately, since these tools are already installed there.
set -euo pipefail

# Local sessions: no-op. Everything is already installed on your laptop.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- LaTeX (for building docs/paper/main.tex with pdflatex + bibtex) ---
# The paper uses: geometry, amsmath/amssymb/amsthm, booktabs, graphicx, xcolor,
# natbib, hyperref. These live across the base/recommended/extra TeXLive bundles.
if ! command -v pdflatex >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended
fi

# --- Python dependencies (for pytest) ---
# Use `python -m pip` so the install targets the same interpreter that runs the
# tests (`python -m pytest`), avoiding PATH mismatches between pip/python/pytest.
python -m pip install -e ".[dev]"
