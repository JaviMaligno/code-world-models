# Paper 3 — where things stand

Start here when picking the work back up. This file is the pointer layer: the
numbers and the arguments live in the documents it names, and are not copied
here, because a second copy is how `THEORY.md`'s list and its sections came to
contradict each other twice (CAMPAIGN-LOG.md, "Ledger hygiene").

Last updated 2026-08-27 (review-hardening session — Codex rounds 1–2
triaged and repaired; the pre-registered H2 flipped-summary intervention
RUN and folded: directional 9:2 but p = 0.065, the causal reading stays
unearned).

## The state in one paragraph

The theory list is CLOSED (T1–T8 all resolved in `THEORY.md` — the earlier
version of this file called T7's second half open, but its section and its
ledger entry both end "T7 is CLOSED", 2026-07-25; the residuals THEORY.md
itself records as out of scope are T2's argmax-angle distribution, a planner
property, and T3's final factor being the instrument's own rarity r, which
the series treats as an input). The experimental programme is FINISHED —
the thin-neck LLM synthesis, the last open item, ran on 2026-08-24 (third
session, both sizes) — and paper 3's campaigns are all INSIDE the held-out
audit (903/903, the two-factor law inside Wilson95 at 39/39 campaigns,
the two intervention arms included).
The synthesis result is folded into the tex (Section "The metric
converse"), which builds clean at linter zero. The Lean tranches two through eight are
DONE (2026-08-25): Prop 3 composed with the planner loop, T2-I exact,
T3-P/T3-P″, Prop 7's pathwise engine, Props 10/11 (fence and patch
sufficiency, with the coupling engine that also carries Remark R2),
Prop 8 CLOSED up to the measure wrapper, Prop 5's pathwise core,
Lemma G's analytic core, Lemma A's (i)/(iv) cores, T4's Lemma W, and —
on the Rips side — Lemma D⁻'s content AND Lemma B's gap-jump core
(T1's birth lower bound), both at the level the paper proves them —
0 sorries throughout. FORMALIZATION.md's remaining triage is the
measure assembly (circle-measure preimage, Lemma S, union bound;
sphere-marginal reduction) and T1's upper floors (persistence
language, Lemma B's existence half, D⁺'s filling chain). None of it
blocking.

## Open, in the order the work naturally goes

1. **Lean, remaining triage** (FORMALIZATION.md): **Theorem T4's modulus
   is now COMPOSED end to end** (`t4_modulus`, ninth tranche) — Lemma A
   complete with rotation invariance, Lemma S both halves, Lemma W,
   trajectory measurability, the Fubini slice bound and the union bound,
   all machine-checked; only the per-instrument `hform` coordinate
   computation remains. Elsewhere: T5's sphere-marginal reduction, and
   T1's upper floors (Lemma B's existence half, D⁺'s filling chain,
   persistence language) on the `RipsCircle.lean` foundation. Nothing
   blocks on any of it.
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
  ledger and triage updated in FORMALIZATION.md. Local builds need
  `lake exe cache get` first — this machine's saturation kills parallel
  from-source mathlib builds.
- **And the third tranche too** (`DirectEntries.lean`): Prop 7 proved at
  realization level from one induction — freeze-free prefixes are
  mode-set monotone — with first-entry preservation, the
  direct-trajectory-is-free corollary, the no-wall endpoint, and the
  channel-family antitonicity for any monotone sector family. The
  predicted "coupled-trajectory setup" was unnecessary: a direct
  trajectory never queries either mode set before entry. 0 sorries,
  8703 jobs green.
- **And the fourth** (`Mitigation.lean`, `WitnessTube.lean`): Props 10
  and 11 — the loop engine (policy agreement on an invariant ⟹ identical
  closed loops), the argmax-set transport (any deterministic tie-break
  picks the same candidate because the maximizer SETS coincide), the
  coupling engine (mode sets agreeing at every queried landing ⟹
  identical trajectories — Remark R2's Lemma-3 coupling, subsuming
  DirectEntries' avoid-form), and both play_cost-exactly-0 conclusions
  from the named coverage/dominance hypotheses. Plus Prop 8's 1-D
  reduction: the witness tube is pure linear algebra (action ≡ 0 makes
  the heading exactly (1,0) — the feared cos/sin interval arithmetic
  dissolves); its numeric tail stays with the Python witness. 0 sorries,
  8705 jobs green.
- **And the fifth closes Prop 8** (still `WitnessTube.lean`): the scalar
  window (speed ≥ 5 by step 34 by ratchet, window [9.5, 10.5) by step
  53 < 80 without overshoot), the hypot bound into the hole, the
  freeze-free linkage to the instrument's trajectory, and the channel
  membership itself — the sector sine-modeled on the west half-plane (no
  angle API) and the η(γ) margin discharged by Jordan's inequality with
  8 > π. `prop8_positivity_core` composes it all: the witness enters the
  hole against the γ-channel wall within 53 steps. Only the measure
  wrapper (positive probability of the start box) remains, as everywhere
  in the package. With this, NOTHING mechanical is left in the triage.
- **And a sixth takes the first bite of the probabilistic tail**
  (`CapBound.lean`): Lemma G's analytic core — the interval-integral
  inequality its proof runs on (substitution with the Jacobian giving
  the exponent's extra 1/2, pointwise bound, range enlargement),
  generalized to any real exponent p ≥ 0. The sphere-measure reduction
  and T5-I's symmetry-of-sums step remain, honestly probabilistic.
- **And the seventh opens both remaining programs.** Prop 5's core
  turned out to be PATHWISE (mis-triaged as probabilistic): one
  application of the coupling engine, unifying the paper's two cases
  (`prop5_fire_monotone`). T4 gains Lemma W's geometric core. And
  `RipsCircle.lean` lays T1's foundation with no persistence machinery:
  the law of cosines, the edge–angle bound below √3·r_min, the exact
  triangle telescope over `Real.Angle`, and winding as an additive
  functional on `Finsupp` chains that vanishes on scale-s triangle
  boundaries — Lemma D⁻'s content, "the winding class is not a boundary
  below √3·r_min", machine-checked. 0 sorries, 8707 jobs green.
- **The eighth (continued) closes Lemma A(i) end to end as a MEASURE
  statement** — the package's first genuinely probabilistic result:
  `volume_sin_mem_Icc` computes the circle-measure preimage over the
  period (one interval per monotone branch of sin, null overlap at π/2)
  and `lemmaA_part_i` composes it with the endpoint-maximality (proved
  by elementary trigonometry, no convexity needed) and the arccos bound
  into `P(strip) ≤ √(ℓ/2)` for the uniform angle. What remains of T4's
  assembly: Lemma S's pushforward and the h-step union bound.
- **The eighth adds Lemma A's analytic cores and Lemma B's gap jump.**
  `CapBound.lean`: arccos(1−ℓ) = 2·arcsin√(ℓ/2) (via `abs_sin_half`),
  the inverse Jordan bound arcsin u ≤ (π/2)u, and Lemma A's (i) endpoint
  and (iv) tangency bounds. `RipsCircle.lean`: the upcrossing lemma — a
  lifted walk that climbs 2πw while its vertices avoid the open gap arc
  must take a single step ≥ Δ (negative winding by negating the lift,
  sidestepping the wrap-reversal pathology at ±π) — which with the
  chord–angle bound is Lemma B's birth lower bound
  s_w ≥ 2·r_min·sin(Δθ_max/2). T1's two proved halves (B-lower, D⁻) are
  now machine-checked at the paper's own level.

Picked up exactly where the list above pointed: the rarity decision, then the
plumbing it unblocks, then the audit itself. No mathematics attempted (T7
stays for its own session).

## What happened on 2026-08-26/27 — review hardening

Two adversarial Codex review rounds (`codex exec -s read-only`,
gpt-5.6-sol) run against the full tex; findings verbatim + triage in
`REVIEW-CODEX.md`. Round 1: 17/17 confirmed and repaired (headline: the
"exactly E(f)" converse was FALSE at μ_query-null disagreements — Prop
quotient rebuilt on the per-rollout hit probability; the NSW table
recomputed on n_used). Round 2 found round 1's own quotient repair
invalid (occupation mass vs per-rollout probability) — rebuilt again; 11
REPAIRED, 5 PARTIAL, 10 new findings triaged. Linter zero and LaTeX
green after each round.

**The H2 intervention ran** (design pre-registered in
`INTERVENTION-DESIGN.md`, amendments dated before any outcome existed;
analysis `scripts/ring2d_summary_intervention.py` committed before the
arms finished): full paired crossover at γ=1.8 inside, mini, 60 seeds —
flipped summary vs a CONTEMPORANEOUS honest replicate (`ctrl2`) as
primary control. Result (`results/ring2d_summary_intervention.json`):
11 discordant pairs, 9 toward the claim / 2 against, exact two-sided
p = 0.065 — directionally consistent with steering, NOT significant at
the pre-registered 0.05. Per H-I2 the tex's causal sentence is
permanently downgraded to the measured association (contributions
bullet + Section "The evidence sensor" both updated). Drift check
honest-then vs honest-now 4:5 (p = 1.0, no deployment drift); gate
passage 0 discordant.

The ring2d audit re-ran absorbing the two intervention arms: 903/903
artifacts over 39 campaigns, 39/39 inside Wilson95, contingency still
156/156 exact over 91 blocks, 214 in-sample passes / 121 regressions
unchanged (both new arms: 0 gate passes). Tex counts updated.

Codex round 3 ran after the fold (2026-08-28): NO blocking defects, a
clean bill on the intervention numbers, the pre-registration (verified
via git history), the audit counts, and every round-2 repair; 2 MAJOR
(both wording-scope: the "any honest summary has some flip"
overgeneralization, the drift sentence claiming stability) + 3 MINOR
(registered CI never emitted; H-I3 vs amendment 3; Wilson uppers
hand-derived) — all five repaired same session (REVIEW-CODEX.md round-3
triage). Findings are converging: 17 → 10 → 5, none blocking.

Round 4 (convergence check) ran complete after Javier switched Codex
accounts (first attempt hit the workspace spend cap): NO blocking, 1
MAJOR + 3 MINOR, all four against text round 3's own repairs introduced,
and "the final structural sweep found nothing else new" — all four
repaired same session (REVIEW-CODEX.md round-4 triage). Round 5 (final
verification, 2026-08-28) came back **CLEAN — zero defects of any
severity**, all four round-4 repairs verified exact (Wilson values
recomputed independently), verdict verbatim: "submission-ready modulo
the explicitly recorded public archival URL/environment lock TODO."
Findings across rounds: 17 → 10 → 5 → 4-on-own-repairs → 0. **The
review cycle is CLOSED.**

A#11 RESOLVED (2026-08-28, on Javier's go): the repo is public at
https://github.com/JaviMaligno/code-world-models; `env-lock.txt` (pip
freeze, Python 3.13.7) and `MANIFEST.sha256`
(`scripts/emit_manifest.py`, SHA-256 over every tracked results JSON
and paper-3 source) are committed; the tex's reproducibility section
names the URL and the archival tag `paper3-v1` (the merge of the
review-hardening branch into main). Secret scan before anything: no
.env ever tracked, no key patterns in the tree.

Nothing stands between the paper and submission.

## Editorial cycle (2026-08-28, after the mathematical one closed)

A separate writing-quality review cycle (legibility, flow,
paper-vs-process; ledger `docs/paper3/REVIEW-EDITORIAL.md`) ran to
convergence on Javier's ask: E1 24 findings (14 MAJOR) → E2 10 (all on
E1's repairs) → E3 clean bill + 3 mechanical copy-edits. Verdict
verbatim: "Submission-ready after these three mechanical copy-edits" —
applied same session. No claim's quantifier, scope, or evidence label
moved; no scientific content deleted. The `paper3-v1` archival tag was
moved to the post-editorial state (it is the snapshot the tex itself
cites).

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
    created there on 2026-08-24 at the default capacity (10); on 2026-08-27
    Javier authorized raising `gpt-5.4-mini` to **capacity 100**
    (GlobalStandard — the capacity is a rate ceiling only, billing stays
    per-token), which is what let the tda-variant campaigns run without
    429 crawl. `gpt-5.4` (large) remains at 10.
  - The deployment names match the models exactly (`gpt-5.4` -> gpt-5.4
    2026-03-05, `gpt-5.4-mini` -> gpt-5.4-mini 2026-03-17). That is load-bearing
    and not cosmetic: the deployment name is what gets written as `"model"` in
    every results JSON, so a deployment called `gpt-5.4` serving anything else
    would silently mislabel the campaign's provenance.
  - `nano` was never deployed. No campaign has used it, and it is only read when
    a run passes `size=nano`, so it costs nothing to leave out.
- This machine drops work when saturated: keep worker pools small (the rarity
  sweep defaults to 4) and never run two suites at once.
