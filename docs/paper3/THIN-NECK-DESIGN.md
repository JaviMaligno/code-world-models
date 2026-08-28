# Thin-neck ring — design (2026-08-24)

V2-PROGRAM's last unrun item, whose design was the open question: where does
Lemma 2's hypothesis fail, and what does the measurement read once it does?
This file records the design decisions with their reasons and the
pre-registered readings, written BEFORE the 30k sweep ran (the smoke run at
400 rollouts informed the predictions and is disclosed below).

## The question the instrument isolates

Every reopening of the interior so far has been TOPOLOGICAL: the γ-channel
cuts the band (β₁ 1 → 0, the interior becomes continuum-reachable). The
thin neck reopens the interior METRICALLY: the band keeps β₁ = 1 and still
separates the plane in the continuum at every neck > 0, but where its local
thickness drops below the step bound Δ, a DISCRETE trajectory can leap it.
The γ-knob and the neck knob are therefore orthogonal reopenings — one
changes what the continuum allows, the other what the discrete dynamics
allow, and the paper's thesis (danger is reach-relative) predicts that only
the second matters wherever they disagree.

## Design decisions

1. **Thin from OUTSIDE** (`r_out` dips to `r_in + neck` inside the sector;
   the hole `d < r_in` is invariant). The alternative (raise `r_in`) bulges
   the hole outward at the neck, which changes what `r_int` counts and
   breaks comparability with every committed arm. With the hole invariant,
   `r_int` means the same event across the γ-sweep, the hidden arm and this
   one.
2. **The knob is the neck THICKNESS**, swept across the step bound:
   neck ∈ {0.1, 0.2, 0.4, 0.6, 0.8, 1.2} × {facing, hidden} + the closed
   control. The design carries its own threshold theorem (the LOCAL crossing
   lemma, formalized as `freeze_stays_outside_of_superset` /
   `neck_interior_unreachable` in `formal/Paper3Ring`): the mode set
   contains the thin annulus `[r_in, r_in + neck]` at every angle, so
   interior entry requires a single step longer than `neck`; the integrator's
   max step is `(gain/drag)·dt = 1.0`, hence **neck = 1.2 is an exact-zero
   control** and thinner necks admit leap-through only at speed
   `> 10·neck`.
3. **Angular half-width fixed at 0.3 rad** (arc ≈ 1.2 units at the dipped
   radius, comparable to the studied channel arcs). It is a field, not a
   swept knob: sweeping two geometric knobs at once would confound thickness
   with exposure.
4. **Deterministic existence witness, not only a sampled rate.** A scripted
   constant-thrust trajectory (start (0.20, 0), action ≡ 0) leaps the 0.5
   neck at t = 25 with step 0.547 from d = 4.034 — machine-checked in
   `tests/test_ring2d_thin_neck.py`, with the same 40-witness family blocked
   at neck ≥ 1.0. Existence does not ride on the sweep's sample.
5. **`neck=None` is bit-identical to the committed instrument** (the guard
   does no arithmetic; full-thickness neck is geometrically the uniform
   band — both tested). `env_key` carries `-nk{...}` if a campaign ever
   uses the knob.

## Pre-registered readings (before the 30k sweep)

- **H-T1 (existence and threshold).** Leap-through entries exist below the
  step bound and are impossible above it: r_int > 0 requires neck < 1.0
  (theorem for ≥ 1.0 side; the measured side is the rate). Every recorded
  entry must have `step > neck` and `d_prev > r_in + neck` — a per-event
  arithmetic check of the local lemma, not only a rate.
- **H-T2 (the gate's measure barely sees the neck).** r(neck) ≈ r(closed)
  at every neck (the sector is 2·0.3 rad of 2π and the dip narrows the
  band's outer face), and the RANDOM-rollout leap rate is small or zero
  even at thin necks: a leap needs speed > 10·neck at the right angle, and
  random-gate arrivals carry median tangential/radial speeds ≈ 0.45/1.5
  (T3's measurements). The 400-rollout smoke saw 0 entries in every cell,
  consistent with this. If 30k still measures 0 at neck ≤ 0.2, that zero is
  a censored zero and is reported as such.
- **H-T3 (the planner side is the live question).** MPC accelerates along
  the corridor and arrives FAST (up to ≈ 8-9 near the band), so a facing
  neck may admit planner leap-through that the random gate essentially
  never samples. Two outcomes, both informative, neither assumed:
  (a) pc_blind collapses at thin facing necks — the metric hole behaves
  like the topological channel for play, the thesis's sharpest form
  (danger tracks DISCRETE reach; topology unchanged); (b) pc_blind
  persists ≈ 1 — the planner's realized approach speeds or entry angles
  don't meet the leap condition, and the neck is a gauge-preserving
  perturbation. The smoke (2 episodes) read pc_blind ≈ 0.95-0.99 at facing
  necks: directionally (b), underpowered; 16 paired episodes decide.
- **H-T4 (hidden neck is inert).** With the neck on the far side nothing
  changes on any measured axis (the reach argument, as for the hidden
  channel): pc_blind ≈ 1.0, r = closed-ring r, r_int = 0-or-censored.
- **H-T5 (the wrong topology stays unfalsifiable at the gate's measure but
  its harmlessness is now conditional).** disagree_fill counts transitions
  where the filled model differs from truth: nonzero only on interior
  landings, so it tracks the leap rate — 0 wherever H-T2's zeros hold, and
  the filled model stays certified by any sampling gate there. If planner
  leap-through occurs (H-T3a), Prop 3(ii)'s hypothesis fails through the
  neck and pc_fill can move at facing necks, with the topology untouched —
  certification and consequence separating along the METRIC axis this time.

## What would refute the design

If leaps recorded at 30k violate `step > neck` (an event-level arithmetic
failure), the env or the lemma is wrong — halt and fix before any reading.
If the closed control drifts from the committed r = 0.03123 (30k, Wilson
[0.0293, 0.0333]), the harness is not measuring the committed instrument.

## Costs

CPU only (~2 h at 30k × 13 cells on 4 workers, checkpointed per cell).
LLM synthesis campaigns on the neck (does a model ever WRITE a
variable-thickness band?) are a separate decision — Azure bills to the
client resource — and are NOT part of this run.
