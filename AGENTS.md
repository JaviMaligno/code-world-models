# Repository instructions

Research code and papers for Code World Models (CWM): LLM-synthesized, verifiable
world-model code + planning (MCTS / CEM) vs a direct LLM policy. Paper 1 covers discrete
games (`docs/paper/`), paper 2 continuous/hybrid state spaces (`docs/paper2/`), paper 3
in `docs/paper3/`.

**Paper 3 is the active work: read `docs/paper3/STATE.md` first.** It says what
is open, what is decided, and how to run things here — and it is a pointer
layer, so follow it to the document that holds the detail rather than trusting
a restatement.

Paper 2 is published (arXiv:2608.17956). `results/` is shared between the
papers, so anything that globs it states which instruments it covers; do not
widen paper 2's analyses to pick up paper 3's campaigns.

## Layout

- `src/cwm/` — package (`pip install -e ".[dev]"`): games, MCTS/CFR, synthesizer/refiner,
  sandbox, LLM clients (`llm/`), continuous instruments (`continuous/`).
- `scripts/` — experiment, certificate and audit scripts; most are run as
  `PYTHONPATH=src python scripts/<name>.py`.
- `results/` — versioned per-seed JSON artifacts. They are the papers' cited evidence and
  are committed on purpose; do not gitignore or delete them.
- `tests/` — pytest suite (Azure-free; `pythonpath = src` is set in `pyproject.toml`).
- `docs/EXPERIMENTS.md` (results + reproduction commands), `docs/RESEARCH-DIRECTION.md`
  (theorems and narrative), `docs/specs/`, `docs/plans/`.
- `formal/Paper2Props/` — Lean formalization (paper 2 props; paper 3 in `Paper3Ring/`),
  built in CI by `leanprover/lean-action`.

## Setup, test, guards

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    cp .env.example .env                    # Azure credentials for LLM-calling scripts
    pytest -q

Paper guards (also in `.github/workflows/ci.yml`):

    bash scripts/check_latex.sh                                  # all papers: 0 overfull, 0 undefined refs
    python scripts/check_paper_build.py docs/paper/main.tex docs/paper2/main.tex  # after a build
    python scripts/audit_paper2_numbers.py                       # paper-2 table cells vs results/
    PYTHONPATH=src python scripts/sample_stream_census.py        # seed-block recount
    PYTHONPATH=src python scripts/audit_paper_claims.py          # claim-scope audit (not a CI step; run it yourself)

## Paper work

For any review or edit of `docs/paper*/`, read `.claude/skills/paper-claims/SKILL.md` first
(the claim contract, with before/after examples). In particular:

- Every claim carries its quantifier/scope, its experimental unit, and an evidence label
  (*proved* / *measured* with JSON, $n$ and unit / *consistent with*).
- **Strengthen before weakening.** When a claim is vulnerable, try to earn it with a proof,
  experiment, independent unit, or clearer integration first. Every weakening records what
  would earn it back in `docs/paper2/STRONGER-STATEMENTS.md`.
- **Contribution-preservation test.** Preserve coherent contributions. Do not infer that
  length or contribution count is a defect. Remove material only for a demonstrated
  contradiction, duplication, lack of evidential function, or an explicit venue constraint.
- The paper is not a research log: no draft archaeology, debugging narrative,
  self-assessment or operational history. Corrections history goes in
  `docs/paper2/CHANGELOG-corrections.md` (wrong claim, correct claim, what caught it).
  Operational history becomes a statement of the resulting scope; a correction that changes
  a number gets one clause in the paper (the number and its source), never the story.
  Scope, hypotheses, censoring and negative results are claims, not process prose — they stay.
- Run `scripts/audit_paper_claims.py` before calling a paper edit done.
- The latest actionable review for paper 2 is `docs/paper2/REVIEW5-HARDENING.md`.

Paper 3 mathematics is formalized in Lean as it lands: when a THEORY.md item's
proof lands or changes, formalize it in `formal/Paper2Props/Paper3Ring/` in the
same session, or record in `docs/paper3/FORMALIZATION.md` why not. That ledger
maps THEORY.md items to Lean declarations and carries the triage of what is next.

## The sampling unit is the seed block

`collect_transitions` (`src/cwm/continuous/contract.py`) draws `Random(seed + i)`, and
`scripts/continuous_danger_synthesis.py` sets
`rollout_seed = 10_000 * (seed_index + 1 + seed_offset)`. The gate rollout stream depends
only on the seed index — not on the instrument knob, patch shape, or prompt variant.
Consequences:

- Varying knob/shape/prompt adds *treatments*, not *samples*. In any pooled count the unit
  is the (seed index, offset) block; use cluster-level (block) bounds, not per-cell ones.
- To draw genuinely fresh samples for an ablation, use `--seed-offset` (shifts the block).
- `scripts/sample_stream_census.py` recounts every campaign at block level (runs in CI).

## Long-running or money-costing scripts must be resumable

Hard rule for any sweep of expensive units (per-seed LLM synthesis, per-cell episodes,
multi-hour CPU):

- Checkpoint per unit with an atomic write (temp file + `os.replace`), and on start load
  the partial output and skip units already done. A resumed run's JSON must equal a fresh
  run's. Reference implementation: `run_synthesis` in
  `scripts/continuous_danger_synthesis.py`, tested by `tests/test_synthesis_resume.py`.
- Some older sweeps (e.g. `continuous_patch2d.py`, `continuous_cem.py`,
  `continuous_eps_sweep.py`) still write once at the end — make them resumable before
  relaunching them on a costly run.
- Verify a resume path with a test: partial run, kill, re-run, assert done units are
  skipped and the final output equals a from-scratch run.
- Before launching any long run, check the hot loop's complexity: a per-lesson growing
  structure scanned linearly inside a planner's inner loop needs dedup or a spatial index
  first. When a perf/correctness fix lands at one call site, grep for sibling call sites of
  the same pattern and fix them all before the next launch.
