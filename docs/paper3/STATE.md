# Paper 3 — where things stand

Start here when picking the work back up. This file is the pointer layer: the
numbers and the arguments live in the documents it names, and are not copied
here, because a second copy is how `THEORY.md`'s list and its sections came to
contradict each other twice (CAMPAIGN-LOG.md, "Ledger hygiene").

Last updated 2026-08-24 (second session — the audit session, below).

## The state in one paragraph

The theory list is nearly closed, the experimental programme is finished
except for one item that needs designing rather than running, and paper 3's
campaigns are now INSIDE the held-out audit (663/663, the two-factor law
inside Wilson95 at 31/31 campaigns). What is left is mathematical (the second
half of T7) plus the thin-neck design question.

## Open, in the order the work naturally goes

1. **T7 second half — the relative-homology evidence estimator** (`THEORY.md`,
   section "T7 (second half)"). First half closed: R1 (no infinite bars, by
   construction) and R2 (the estimator is a union-find) are proved, and with the
   free evidence entered as PATHS rather than a point cloud the synthetic
   discrimination is 12/12. This is the live mathematical frontier.
2. **Thin-neck ring** — the only unrun item of the v2 programme, and not
   runnable as written: the env has to be designed first and that design is the
   question (where Lemma 2's hypothesis fails, and what the measurement reads
   once it does). See `V2-PROGRAM.md`.
3. **Folding the audit's findings into the tex** when the paper prose is next
   touched: the 31/31 two-factor confirmation, the exact 2x2 on the incomplete
   arm, hidden≡closed carrying into the audit, the inside-start cells'
   globally-wrong-models regime (237/320 off-mode eval exceptions vs 87/343
   outside), and the 2-ULP point-trap gate hack. All in EXPERIMENTS.md,
   "ring2d held-out audit".

RESOLVED since the last update: the rarity decision (r, the firing rarity,
with r_int carried as labelled provenance — reasoning recorded with the
R_SOURCES entries and in EXPERIMENTS.md) and the two heldout branches
(`env_key` / `env_from_params`, plus 21 R_SOURCES entries and the audit's
`--instruments` scope flag).

Everything else in `V2-PROGRAM.md` buckets 1 and 2 has run; the table there
carries each outcome and its file.

## What happened on 2026-08-24, second session

Picked up exactly where the list above pointed: the rarity decision, then the
plumbing it unblocks, then the audit itself. No mathematics attempted (T7
stays for its own session).

- **The rarity decision taken and pinned: r, the firing rarity** — the
  audit's whole event algebra is contact-based, r_int is Lemma 2's curve and
  cannot reveal blindness to a gate; it rides along as `r_interior`,
  drift-checked. A test pins the decision.
- **ring2d audited, completely**: 663/663 artifacts into
  `results/heldout_gate_audit_ring2d.json` (paper 2's committed audit
  untouched — its scope cannot widen by construction now). Headlines: the
  two-factor law inside Wilson95 at **31/31 campaigns**; the 2x2 exact at
  112/112 on the incomplete arm; 88 regressions all mode_only; the
  inside-start cells produce globally wrong models rather than blind
  integrators (237/320 off-mode eval exceptions vs 87/343 outside). Full
  numbers in EXPERIMENTS.md, "ring2d held-out audit".
- **A 2-ULP-wide gate hack found by the reproduction check**: one artifact
  (mini_gap0.6-hid seed 10000) reached its stored in-sample 1.0 by freezing
  on exact `==` equality with its sample's single contact state; this
  platform's libm puts that y 2 ULPs away, so the trap misses here. No
  held-out conclusion moves; pinned as the only tolerated mismatch. Fourth
  portability finding, first one where the fragility is the artifact's own.

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
- `.env` is filled in and **working** (2026-08-24): `gpt-5.4` and `gpt-5.4-mini`
  both answer a live round-trip. Two things to know about it:
  - It points at **`ai-gonvarri-foundry`** (`rg-pharo-gonvarri`, swedencentral),
    which is a **client resource** — usage bills to it. The deployments were
    created there on 2026-08-24 at the default capacity (10) rather than
    something larger, deliberately, since it is not our infrastructure. If the
    campaigns crawl, that capacity is the first thing to raise.
  - The deployment names match the models exactly (`gpt-5.4` -> gpt-5.4
    2026-03-05, `gpt-5.4-mini` -> gpt-5.4-mini 2026-03-17). That is load-bearing
    and not cosmetic: the deployment name is what gets written as `"model"` in
    every results JSON, so a deployment called `gpt-5.4` serving anything else
    would silently mislabel the campaign's provenance.
  - `nano` was never deployed. No campaign has used it, and it is only read when
    a run passes `size=nano`, so it costs nothing to leave out.
- This machine drops work when saturated: keep worker pools small (the rarity
  sweep defaults to 4) and never run two suites at once.
