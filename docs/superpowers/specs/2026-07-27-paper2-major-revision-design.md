# Paper 2 major revision — design

**Date:** 2026-07-27. **Branch:** `paper2-major-revision`. **Trigger:** an external review of
`docs/paper2/main.tex` (26 numbered points plus ~20 minor ones) recommending *major
revision / reject and resubmit*. Item-by-item status lives in
`docs/paper2/REVIEW-RESPONSE.md`; this file records the design decisions.

## The governing rule (agreed with the author)

When a claim is too strong, **the first move is to look for the experiment or the proof
that earns the strong version.** Weakening the wording is the fallback, and a weakening
must record what would earn it back. This is why the design below spends compute on #1,
#4, #7, #9 and #12 rather than rewriting their sentences.

The second governing rule: **the paper states what is true, not how we got there.** All
draft archaeology, debugging narrative and self-assessment leaves the manuscript.

Both rules are made mechanical (not memory-dependent) by `.claude/skills/paper-claims/`
and `scripts/audit_paper_claims.py` in CI.

## Workstreams

### W1 — Independent gate and the risk estimand (#1, #2, #6)

The review's fatal-if-true point: the N=40 rollouts are simultaneously synthesis examples,
refinement feedback and acceptance gate, so "gate 1.000" is training-set consistency.

The fix costs nothing: **all 625 synthesized artifacts are versioned with their source**
(`results/continuous_synthesis_*.json`, `cells[].code`), so each can be scored on rollout
blocks it never saw. Refine-on-`D_train`, accept-on-`D_gate` *is* the prospective
protocol; evaluating it after the fact changes nothing about its validity.

- `src/cwm/continuous/heldout.py`, `scripts/heldout_gate_audit.py` → three disjoint blocks
  per artifact (`D_train` reproduced, `D_gate` at +5e6, `D_eval` at +7e6), per-artifact
  held-out accuracy, acceptance, mode presence per block, and a failure breakdown
  (mode contact vs off-mode arithmetic).
- Theory: **risk estimand.** `D_N = E[PC(A(D_train)) · 1{accepted ∧ play-inadequate}]`,
  with the identity `D_N = E[PC | ·] P(·)`, the exact conditions under which it factorizes,
  and bounds when the conditional cost varies. `play_cost × (1-r)^N` is retained as the
  fixed-blind-model identity, not as a general law. "Exact" is reserved for the gate-miss
  factor.
- Theory: **two-factor gate miss.** With `D_train ⫫ D_gate` and the *measured* premise
  "mode absent from `D_train` ⇒ artifact mode-blind", `P(blind ∧ accepted) =
  (1-r)^{N_train}(1-r)^{N_gate}`.
- Vocabulary: the in-sample notion is renamed a **sample-consistency gate** throughout;
  "sound" is reserved for the stated logical property.

### W2 — Measurements that keep claims strong (#4, #7, #9)

- **`patch_shape="slab"`** in `PatchField2D`, half-width calibrated so patch-1 rarity
  matches the disc's `r1 = 0.1417`: same 4D state, same scalar-heading action, same two
  modes, same lodes, same one-sided evidence — only the trigger's *arity* changes (one
  landing coordinate instead of two). This is what makes "geometry-dependent" an
  identified axis rather than a confounded contrast. Either outcome is publishable:
  repair ⇒ the axis is trigger arity; no repair ⇒ the axis is the evidence structure and
  the template-prior reading is falsified.
- **`landing` prompt variant**: the paper's own audit found 36/40 artifacts conditioning on
  the current rather than the landing state. The variant states the variable (never the
  shape), isolating variable-identification from region-induction.
- **CEM censored zeros** (#7): the two `crossing = 0.0000` rows get a Clopper-Pearson upper
  bound at ≥200× the sampling, converted correctly to a `q_hit` bound. The claim becomes
  `play_cost ≤ bound`, never "forces zero".
- **Play inference** (#9): 100 paired episodes on the headline rows, paired bootstrap CIs,
  a paired randomization test, raw return and raw regret reported beside the normalized
  play_cost, per-seed values for ECDFs, and a Clopper-Pearson interval for the 7/20 lock-in.

### W3 — Theory: correct, and generalize where possible (#2, #3, #11–#16)

- #11 the joint-bracket sharpness remark needs `r1 + r2 ≤ 1`; above it the lower end is
  `P(R1 ∪ R2) = 1` with minimal intersection `r1 + r2 - 1`, not disjointness. (Real error.)
- #12 **generalize instead of scoping down**: prove the quadratic ε-flatness rate for the
  whole semi-implicit family with additive `gain·a` in the velocity update and a clamp on
  the integrated coordinate, reusing the already-proved universal two-action Jacobian. The
  cart *and* the pendulum then follow from a theorem, and the measured exponents become
  confirmation rather than the only evidence for the pendulum.
- #3 the Lipschitz claim is restated as **bounded-Lipschitz models cannot realize
  arbitrarily sharp localization at fixed error amplitude**, with the volume form
  `vol(E_ε) ≥ ((η-ε)/L)^{d+m}`, and representability / finite-sample learnability /
  1e-9 exactness / the h=8 probe are separated. Headings and the conclusion follow.
  (Our own compactly-supported `C^∞` bump falsifies the current wording.)
- #13 `cor:playcost` is restated with the *proved bounds* `J̄`, `J̲` rather than essential
  extremes, plus a table separating proved bound / attained / numerically approached.
- #14 an explicit simultaneity ledger for the coverage certificate (partition fixed before
  the Monte Carlo? δ split? K selected on the same sample? level sets?), with a union
  correction if the audit finds selection, and relabelling if it is calibrated rather than
  rigorous.
- #15 formal definitions of **trigger arity** (landing coordinates entering the predicate)
  and **mode-boundary dimension**, used consistently and reconciled with `cor:fencedim`.
- #16 the ten propositions are regrouped into four families (gate miss and identifiability;
  Lipschitz localization and detectability; coverage; mitigation packing); algebraic
  identities become lemmas or remarks.

### W4 — Statistics by experimental unit (#5, minors)

`scripts/paper2_statistics.py`: primary unit = gate-sample block `(seed index, offset)`;
secondary = synthesis draw; treatment = (instrument, knob, shape, prompt variant, budget).
Per-treatment tables replace pooled counts; block-level bounds replace draw-level Wilson;
`0/156` is presented as *156 synthesis attempts over N distinct blocks across these
treatments* with a per-block upper bound; `109/111` is reported per instrument/knob/size.
Censored zeros carry their interval in the row; over-precise digits are truncated to the
resolution the sample supports; figures get uncertainty bands.

### W5 — Structure, narrative, apparatus (#17–#26)

Main article ≈16 pp: problem and estimand → minimal theory → the instruments → the LLM
experiment with an independent gate → 1D vs 2D → limitations. Everything else moves to
clearly labelled **Supplementary Material** in the same PDF (coverage certificates, CEM,
mitigation, ε-flatness, normalizers, artifact audit, exhaustive tables). New appendices:
the complete LLM protocol; reproducibility (versions, frozen deps, commit/tag, hardware,
runtimes, LLM cost, JSON→table manifest, licence, `env.example`); and a
pre-specified/confirmatory/diagnostic/exploratory ledger dated from git. Related work is
expanded across twelve literatures with CEGIS treated as the direct analogue and its
difference named precisely. The abstract is rewritten to five pieces. Headings are
de-escalated. Process prose moves to `docs/paper2/CHANGELOG-corrections.md`.

### W6 — The durable rule

`.claude/skills/paper-claims/SKILL.md` (statement contract + strengthen-first rule +
narrative contract, with before/after examples from the real text) and
`scripts/audit_paper_claims.py` in CI (self-referential register, unquantified modals in
headings and bold lead-ins, unscoped soundness vocabulary, pooled-inference smell, printed
zeros without intervals, prose constants absent from `results/`), plus two memories.

## Execution

The mechanical-but-substantial half (W1 infrastructure, W2 instruments/scripts, W4, W6,
and the fact-gathering for W5) runs as a parallel agent workflow with disjoint file
ownership, no paid API calls, and adversarial verification on the six riskiest
deliverables. The theory (W3), the risk-estimand propositions (W1), the manuscript surgery
(W5) and the final integration are done in the main session.

Verification before completion: `pytest` green, `scripts/audit_paper2_numbers.py` green,
`scripts/audit_paper_claims.py` at or below its ratchet, LaTeX compiling with no undefined
references, main-article page count in range, and every row of
`docs/paper2/REVIEW-RESPONSE.md` closed with its evidence.
