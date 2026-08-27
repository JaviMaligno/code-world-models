# H2 summary intervention — design (2026-08-27, pre-registered)

The Codex review (REVIEW-CODEX.md, finding 4) and the paper itself now
state the gap: H2's evidence that the sensor's report steers posed topology
is a cross-gap association (environment and summary vary together), and the
within-gap contrast at γ = 1.8 is directional only. This experiment is the
isolating intervention, committed before the run.

## Design

**Paired crossover on the committed evidence blocks.** The committed arm
`continuous_synthesis_ring2d_mini_gap1.8-in_pv-tda.json` (γ = 1.8, inside
start, mini, 60 seeds 10000..600000, prompt variant `tda`) is the CONTROL:
each seed's prompt carries the honest topological summary of its own
evidence. The new arm runs the SAME 60 seeds — bit-identical D_train by the
seed convention — under a new variant `tda-flip`, identical in every byte
except the summary's topology CLAIM, which is negated:

- the counts, cluster count, and bounding box lines stay truthful;
- the `beta_1 = k` line and its one interpretive sentence are replaced by
  the OPPOSITE report (detector says ≥ 1 → the prompt says 0 with the
  open-arc sentence; detector says 0 → the prompt says 1 with the
  closed-loop sentence).

Every seed receives both treatments (full crossover — stronger than
randomizing assignment), and the environment, evidence, gate, and every
other prompt byte are held fixed, so any per-seed difference in outcome is
attributable to the summary's claim alone.

**Outcomes, per seed (paired):**

1. posed topology class of the terminal artifact — closed
   (disc/loop/complement) vs arc vs none, by the same classifier the H2
   table used;
2. gate passage (in-sample), and held-out acceptance once the audit
   re-runs.

**Analysis** (`scripts/ring2d_summary_intervention.py` →
`results/ring2d_summary_intervention.json`): the paired 2×2 of posed-closed
against summary-claims-closed, per seed. The test is the exact two-sided
McNemar/binomial: with `d` discordant pairs of which `k` flip in the
claimed direction, `p = P(|Binomial(d, 1/2) − d/2| ≥ |k − d/2|)`,
significance at `p < 0.05`; the report carries the paired effect (the
discordant split) and its exact binomial confidence interval, not only the
verdict.

**AMENDMENTS (2026-08-27, before any outcome was inspected; prompted by
the round-2 review, REVIEW-CODEX.md B2–B4):**

1. *Test corrected.* The original text pre-registered "≥ 8 net discordant
   flips" as the criterion — invalid, since significance depends on the
   total discordant count `d` (9:1 is significant, 34:26 is not). Replaced
   by the exact conditional binomial above. No outcome had been generated,
   let alone read, when this was corrected.
2. *Temporal control added.* The committed honest arm is historical; the
   flipped arm runs today, and the LLM call carries no inference seed, so a
   naive pairing confounds the summary's effect with generation randomness
   and possible deployment drift. A CONTEMPORANEOUS honest replicate
   (variant `tda`, same 60 seeds, `--out-tag ctrl2`, run in the same
   session and against the same deployment as the flipped arm) becomes the
   PRIMARY control; the committed arm is demoted to a drift check
   (honest-then vs honest-now). The primary contrast is flip-now vs
   honest-now, paired per seed; residual generation stochasticity is what
   the paired binomial's null absorbs.
3. *Gate passage re-classified.* H-I3 wrongly treated gate passage as an
   invariance check "because the gate never sees the prompt" — but the
   prompt changes the artifact and the gate scores the artifact, so
   passage is a downstream causal OUTCOME. It is now a secondary outcome
   (paired, reported with the same exact test), with no invariance null.

## Pre-registered readings

- **H-I1 (steering).** Posed topology follows the CLAIM, not the evidence:
  seeds whose honest summary said closed and whose flipped prompt says arc
  pose closed structures less often under the flip, and symmetrically. If
  the paired contrast is significant, H2's causal sentence is EARNED and
  the paper's consistent-with label upgrades to measured-causal
  (within-environment, γ = 1.8 inside, mini).
- **H-I2 (null).** If posed topology is unchanged under the flip, the
  summary's claim line is inert at this cell and the cross-gap crossover
  must be attributed to the rest of the evidence channel — the paper's
  causal reading is then WRONG as stated and the sensor section's
  conclusion weakens to the association, permanently.
- **H-I3 (gate invariance).** Gate passage should NOT move (the gate never
  sees the prompt): any drift is a synthesis-side artifact and is reported
  as such, not as a sensor effect.

Either outcome is publishable content; the design is committed before the
first flipped token is sampled.

## Cost

Azure mini, 60 cells, ~1.5–2 h; the control arm is already committed. The
audit absorbs the new campaign under the existing `ring2d_gap1.8-in`
rarity entry (prompt variant is not part of the stream key, by
construction).
