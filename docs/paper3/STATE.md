# Paper 3 — where things stand

Start here when picking the work back up. This file is the pointer layer: the
numbers and the arguments live in the documents it names, and are not copied
here, because a second copy is how `THEORY.md`'s list and its sections came to
contradict each other twice (CAMPAIGN-LOG.md, "Ledger hygiene").

Last updated 2026-08-24.

## The state in one paragraph

The theory list is nearly closed and the experimental programme is finished
except for one item that needs designing rather than running. What is left is
mathematical: the second half of T7. Everything below that is either a decision
for you or a piece of plumbing that a decision unblocks.

## Open, in the order the work naturally goes

1. **T7 second half — the relative-homology evidence estimator** (`THEORY.md`,
   section "T7 (second half)"). First half closed: R1 (no infinite bars, by
   construction) and R2 (the estimator is a union-find) are proved, and with the
   free evidence entered as PATHS rather than a point cloud the synthetic
   discrimination is 12/12. This is the live mathematical frontier.
2. **The rarity decision: is it `r` or `r_int`?** Needed before ring2d can enter
   the held-out audit. The data is measured and waiting
   (`results/ring2d_rarity_sweep.json`); see EXPERIMENTS.md, "ring2d rarity
   sweep", whose reading 2 is the reason this is not mechanical — the answer may
   differ between the outside cells and the inside ones.
3. **Two branches, once (2) is decided**: `heldout.env_from_params` and
   `heldout.env_key` have no ring2d case. `env_key` now RAISES instead of
   silently returning a cart key; `env_of` in `scripts/ring2d_rarity_sweep.py`
   is the mirror `env_from_params` needs.
4. **Thin-neck ring** — the only unrun item of the v2 programme, and not
   runnable as written: the env has to be designed first and that design is the
   question (where Lemma 2's hypothesis fails, and what the measurement reads
   once it does). See `V2-PROGRAM.md`.

Everything else in `V2-PROGRAM.md` buckets 1 and 2 has run; the table there
carries each outcome and its file.

## What happened on 2026-08-24

Session with Opus 5. No mathematics was attempted — that was deliberate, the
maths is done in a separate session.

- **`main` merged in** (`9ed060d`), three weeks of paper 2 plus two portability
  test fixes. Seven conflicts, all "both sides added something different in the
  same place", resolved by keeping both. The one worth knowing about: this
  branch added the `ring2d` instrument to `continuous_claude_step.py` while main
  added `patch2d`, and main's cell dict reads a `KNOB` this branch only defined
  for ring2d — a plain merge left `cart` and `pendulum` raising NameError.
- **Paper 2's two analyses now declare their scope** (`add5303`).
  `results/` is shared, so `paper2_statistics` and `heldout_gate_audit` had
  quietly widened to include paper 3. Narrowed rather than extended, because
  paper 2 is published (arXiv:2608.17956) and its report has to keep
  reproducing the announced numbers — which `test_committed_json_is_current`
  confirms it does.
- **A real portability bug fixed** (`74b289f`): `run_in_sandbox` wrote its temp
  file in the locale encoding, so on a non-UTF-8 machine any artifact whose code
  contained a non-ASCII character died with `SyntaxError: Non-UTF-8 code` before
  running — scored as the artifact being wrong. It judged artifacts by whether
  their comments happened to be ASCII. Third of this family, after the slab
  digests and the H4/H7 freshness comparisons.
- **The v2 ledger corrected** (`1cb7e7f`): it said "launching"/"queued" for 1a,
  1b, 1c, 2c and 2d, all of which ran a month ago. Each row now carries its
  outcome and file, checked against `results/`.
- **ring2d rarity measured** (`a709164`), and `env_key`'s silent cart
  fall-through closed. Details in EXPERIMENTS.md, "ring2d rarity sweep".

## Running things here

- `.venv` at the repo root, package installed editable with the `dev` and `tda`
  extras (gudhi included — paper 3's TDA needs it).
  `./.venv/Scripts/python.exe -m pytest -q` runs the suite: **895 pass, 1
  skipped, ~5.5 min**. If it ever takes hours instead, that is the environment,
  not the code — it happened once on a freshly cloned tree.
- `.env` exists but still holds the template values. **Anything that calls Azure
  will not run until the keys are filled in.** CPU-only work is unaffected.
- This machine drops work when saturated: keep worker pools small (the rarity
  sweep defaults to 4) and never run two suites at once.
