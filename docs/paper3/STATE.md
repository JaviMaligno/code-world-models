# Paper 3 — where things stand

Start here when picking the work back up. This file is the pointer layer: the
numbers and the arguments live in the documents it names, and are not copied
here, because a second copy is how `THEORY.md`'s list and its sections came to
contradict each other twice (CAMPAIGN-LOG.md, "Ledger hygiene").

Last updated 2026-08-24 (third session — the thin-neck synthesis campaign).

## The state in one paragraph

The theory list is CLOSED (T1–T8 all resolved in `THEORY.md` — the earlier
version of this file called T7's second half open, but its section and its
ledger entry both end "T7 is CLOSED", 2026-07-25; the residuals THEORY.md
itself records as out of scope are T2's argmax-angle distribution, a planner
property, and T3's final factor being the instrument's own rarity r, which
the series treats as an input). The experimental programme is FINISHED —
the thin-neck LLM synthesis, the last open item, ran on 2026-08-24 (third
session, both sizes) — and paper 3's campaigns are all INSIDE the held-out
audit (783/783, the two-factor law inside Wilson95 at 37/37 campaigns).
The synthesis result is folded into the tex (Section "The metric
converse"), which builds clean at linter zero. The Lean second tranche is
DONE (2026-08-25): Prop 3 composed with the planner loop, T2-I exact,
T3-P/T3-P″ — 0 sorries. What is left is FORMALIZATION.md's remaining
triage (Prop 7's pathwise engine first), none of it blocking.

## Open, in the order the work naturally goes

1. **Lean, remaining triage** (FORMALIZATION.md): Prop 7's pathwise
   coupled-trajectory engine is next — it would also discharge the T3-P
   theorems' `hdirect` hypothesis. Nothing blocks on it.
2. **Paper 1's linter debt** (22 soundness-scope, 20 printed-zero,
   3 process-prose at baseline) if that paper is ever revised. The
   baseline is READ correctly on Windows now (the linter's lookup
   normalized path separators on 2026-08-24; before that every recorded
   count silently read as 0 here and the run always reported false
   regressions).

RESOLVED since the last update: the rarity decision (r, firing) + heldout
branches + 663/663 audit; the Lean first tranche and the standing
formalize-as-it-lands rule; the tex caught up (audit, 30k rarity,
positivity note, machine-checked remark) and reached linter zero; and the
THIN-NECK ring — designed (pre-registered, committed before the run),
proved (local crossing lemma in Lean), witnessed (deterministic leap at
neck 0.5), swept at 30k, and folded into the tex
(Section "The metric converse"). The v2 programme's bucket 1 is now
fully run. Headlines: planner leak only at neck 0.1 (pc_blind 0.451);
certified-and-costly at neck 0.2–0.4 (0 disagreements in 320k sampled
transitions, pc_fill 0.57/0.50); hidden necks bit-identical to closed at
all six thicknesses.

Everything else in `V2-PROGRAM.md` buckets 1 and 2 has run; the table there
carries each outcome and its file.

## What happened on 2026-08-24, third session

The thin-neck LLM synthesis — the one decision that was waiting on Javier
(Azure bills to the client resource) — authorized and run. Also: the two
paper-3 branches unified (`claude/paper-tres-topology-4w813y` was strictly
contained in `claude/paper-3-experiments-bc45nn` and was deleted, local and
origin; this branch is the only one).

- **The neck knob entered the synthesis pipeline** (`--neck/--neck-channel`,
  KNOB `-nk{...}` matching `env_key`; `env_from_params` and the rarity
  sweep's three mirrors carry it, omitted-when-None so no committed key
  moves; three R_SOURCES entries read `results/ring2d_thin_neck.json`; the
  full arm is refused at `--neck` until the rules text can describe a dip).
- **Six campaigns, both sizes, 20 seeds, incomplete arm** (neck
  0.1/0.2/0.4 facing; mini first, large as the family control on Javier's
  go). The campaign's answer: **0/120 artifacts write any angular
  structure** — not the neck, not even the uniform band
  (`results/ring2d_neck_synthesis_scan.json` carries the counts); the two
  seed blocks whose evidence contained leaps (shared by both sizes) were
  answered with a reward threshold and free flight. A second
  exact-equality gate hack (mini seed 140000, all four floats of the
  sample's single contact state) passed in-sample and fell held-out as
  mode_only; two more point traps stalled at 0.999.
- **The audit re-run absorbed the cells**: 783/783 artifacts, 37/37
  campaigns inside Wilson95, incomplete-arm contingency 156/156 exact
  over 91 blocks.
- **The result is folded into the tex**: new paragraph "The loop does not
  write the neck" in Section "The metric converse"; the held-out
  paragraph's counts updated (783/37/156/91/214/121). Claims linter at
  zero for paper 3, `check_latex.sh` green (30 pages, 0 overfull, 0
  dangling refs). Fixed on the way: the linter's baseline lookup broke on
  Windows path separators (every recorded count read as 0).
- **The Lean second tranche landed** (2026-08-25, continuation of the same
  session): `PlannerLoop.lean` — Prop 3 COMPOSED, closed loop included
  (unfalsifiable over arbitrary policies; the planner as any deterministic
  function of the model's imagined rollouts, and play_cost exactly 0) —
  and `Advantage.lean` — T2-I as an exact telescoping identity with
  clean-steps-contribute-0 and the dirty-step restriction, plus
  T3-P/T3-P″ from the named split-and-Prop-7 hypotheses. 0 sorries;
  ledger and triage updated in FORMALIZATION.md (Prop 7's pathwise engine
  is now triage item 1). Local builds need `lake exe cache get` first —
  this machine's saturation kills parallel from-source mathlib builds.

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
- **The Lean formalization started, and it is now a standing rule** (Javier:
  "me gustaría formalizar lo que llevamos hasta ahora en lean... y lo que
  siga a partir de ahora también"). First tranche PROVED, 0 sorries, builds
  clean: Lemma 2 (both halves), the disc≡annulus evidence-equivalence
  corollary, Prop 1 at realization level, Prop 3(ii)'s engine, the
  integrator speed invariant, and the capstone "interior unreachable at the
  frozen defaults". Lives in `formal/Paper2Props/Paper3Ring/` (same package
  and CI job as paper 2's `Paper2Props`); the item-by-item map, the
  modelling notes and the triage of what is next are in
  `docs/paper3/FORMALIZATION.md`, and the going-forward rule is in
  CLAUDE.md: new THEORY.md proofs get formalized in the same session or the
  ledger records why not.

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
