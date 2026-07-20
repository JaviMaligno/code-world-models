# Paper 3 — RingField2D LLM synthesis arm (ready to run locally)

**Goal:** the paper-3 synthesis experiment on rung 2 (the annulus): does any
synthesizer family recover a mode region with a hole from data, and does the
TDA-informed prompt (arc/loop summary of the seed's OWN contact evidence)
change what gets written? Ungated as of 2026-07-20: the paper-2 confound
cells closed 0/156 with the template-prior mechanism, and the square ablation
falsified curvature — topology (this arm) is the surviving distinct axis.

**Infrastructure (this commit, offline-tested):** `RING2D_SPEC`
(instruments.py — annulus clause + channel-exception text, north-approach
probes firing under both channel orientations), `--instrument ring2d` with
`--gap/--channel/--start` knobs, prompt variant `tda` (region guidance + a
per-seed `topological_summary` of the contact landings — computed from the
sample alone, wording pre-registered in `src/cwm/continuous/tda.py`, never
names a shape), per-seed dynamic guidance resolved inside
`synthesize_and_evaluate` and recorded as `cell["guidance_text"]`, resume
guards extended to the ring knobs. The incomplete ring contract is
byte-identical to patch2d's (tested) — same plant, same lodes, no leak.

## Reading guide — TWO structural traps, know them before looking at results

1. **A filled-disc artifact at gap 0 passes EVERYTHING.** Gate (interior
   never sampled from outside — reach-null), blindness probes (they only
   test the annulus band), and play (Prop 3: planner-equivalent bitwise).
   If a synthesizer writes `d <= 5.0` instead of `3.5 <= d <= 5.0`, every
   metric reads "correct". That outcome — a CERTIFIED wrong-topology
   artifact from a real synthesis loop — is not a failure of the harness,
   it is the paper-3 headline if it occurs. Classification therefore
   REQUIRES code inspection of every gate-passing artifact: record the
   written predicate (annulus / filled disc / other) explicitly.
2. **Blindness 0.0 ≠ correct region** for the same reason (probe scope =
   the true mode's band only; paper 2 §10's probe limitation, structural
   here).

## Cells (pre-registered order; large first, mini twins after direction)

- **A — baseline:** `large 20 --instrument ring2d --arm both`
  → `results/continuous_synthesis_ring2d_large_gap0.json`
  Predictions: full 20/20 clean (annulus clause translates; watch it —
  first curved TWO-boundary clause). Incomplete: ring in-sample w.p.
  ≈ 0.82/seed (r = 0.042, N = 40) → ~16 mode-containing seeds refused with
  template-prior artifacts; ~4 mode-absent seeds certified blind and
  exploited at play (pc ≈ 1) — the identifiability event on rung 2.
- **B — region control:** same + `--prompt-variant region`
  → `..._gap0_pv-region.json`. Expected: evidence-hull class (arcs/thin
  shells hugging the west outer boundary), per the disc/square campaigns.
- **C — TDA (headline treatment):** same + `--prompt-variant tda`
  → `..._gap0_pv-tda.json`. Outside evidence ⇒ arc summary + the
  reachable-face note. Questions, in order: does the note kill the
  thin-shell/hull error (regions extended beyond the evidence)? does any
  seed write a SOLID region (filled disc — see trap 1)? does any write the
  true annulus (it cannot be inferred from outside evidence — Lemma 2
  evidence-equivalence — so an annulus here would mean prior injection,
  also a finding)?
- **D — TDA, inside start:** `large 20 --instrument ring2d --arm both
  --start inside --prompt-variant tda` → `..._gap0-in_pv-tda.json`.
  Inside μ0: r ≈ 0.73, every sample mode-containing, evidence = the INNER
  circle, summary reports beta_1 = 1 + closed-loop sentence. The
  constructive question: with loop evidence and the loop summary, does the
  synthesizer write a region with a hole (any enclosing boundary), where
  outside evidence provably cannot pose the question?
- Mini twins of whichever cells carry the paper numbers.

Costs mirror the patch2d cells (~1+≤5 calls/seed, play-eval-dominated,
~30–40 min/cell). All runs resumable: rerun the exact same command.

## After the runs

Per gate-passing artifact: predicate class (annulus / filled disc / other,
by code inspection — trap 1), plus the usual conditionals. Per refused
artifact: template class (1D threshold / radial ball / hull-shell / other)
and the variable tested (landing vs current). Fold into EXPERIMENTS.md
(paper-3 section), then RESEARCH-DIRECTION §4.2/§4.3 status; the D-cell
result decides whether the TDA-repair claim is stated positively or as a
measured negative with the evidence-equivalence explanation.
