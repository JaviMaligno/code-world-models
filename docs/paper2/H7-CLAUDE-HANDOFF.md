# H7 bounded-observation-noise handoff

## Provenance

Claude Code was requested with exactly `claude-fable-5`, but the workspace reported that it was
out of credits before the model could perform the implementation. The final implementation and
verification were therefore completed locally by Codex, without network access. This note is an
engineering provenance record, not manuscript prose.

## Pre-specified strong claim and statement contract

**Proposed claim.** Under known independent observation noise bounded coordinatewise by
\(\eta\), replacing exact equality by support compatibility preserves the rare-mode gate's
acceptance law on the fixed CartWall panel through \(\eta=0.1\), and produces a measured masking
boundary at the first pre-specified noise level where the blind-model acceptance probability rises
by at least 0.05.

- **Quantifier and scope:** the seven pre-specified values
  \(\eta\in\{0,0.01,0.03,0.1,0.3,1,3\}\), `CartWall(x_wall=4)`, the truth model and its analytic
  mode-blind proxy, and iid coordinatewise Uniform\([-\eta,\eta]\) noise on observed next state
  and reward. It is not a claim about unknown, heavy-tailed or process noise.
- **Experimental unit:** one disjoint block of 20 rollout seeds. There are 200 blocks; neither
  their 4,000 rollouts nor their 320,000 transitions are treated as independent inferential units.
- **Evidence labels:** **proved** for the conditional support-overlap formula
  \(q(\delta,\eta)=\max(0,1-|\delta|/(2\eta))\) under the stated uniform-noise hypothesis (with
  the \(\eta=0\) equality limit); **measured** for its evaluation on the fixed 200-block panel and
  the independent simulated block verdicts in
  `results/h7_noisy_observation_gate_v1.json`. The result does not identify prevalence on external
  systems.

The design, critical event, unit, thresholds and seed mapping were frozen separately in
`results/h7_noisy_gate_prespec_v1.json`. The result records the SHA-256 hash of that canonical
pre-specification.

## What was implemented

`scripts/h7_noisy_observation_gate.py` replays identical latent truth states and actions at every
noise level. For each scalar output, a candidate passes when the noisy observation lies in the
candidate's bounded support. For the truth candidate this occurs with probability one. For the
blind candidate the exact scalar support-overlap probability is multiplied over output coordinates
and transitions to obtain a conditional block-pass probability. Independent noise then supplies
one empirical Bernoulli verdict per block and level. Reported binomial intervals are exact
two-sided 95% Clopper--Pearson intervals over the 200 blocks.

The pre-specified primary criterion is an analytic blind-pass increase no larger than 0.01 at
\(\eta=0.1\) relative to \(\eta=0\). The boundary is the first listed \(\eta\) whose increase is at
least 0.05. The fixed panel contains the mode in 189/200 blocks (1,816 contact transitions total).
The generated results are:

| \(\eta\) | truth passes | blind passes (empirical) | exact CP95 | analytic conditional blind-pass probability |
|---:|---:|---:|---:|---:|
| 0 | 200/200 | 11/200 (0.055) | [0.02777, 0.09628] | 0.05500 |
| 0.01 | 200/200 | 11/200 (0.055) | [0.02777, 0.09628] | 0.05500 |
| 0.03 | 200/200 | 11/200 (0.055) | [0.02777, 0.09628] | 0.05500 |
| 0.1 | 200/200 | 11/200 (0.055) | [0.02777, 0.09628] | 0.05500 |
| 0.3 | 200/200 | 11/200 (0.055) | [0.02777, 0.09628] | 0.05558 |
| 1 | 200/200 | 32/200 (0.160) | [0.11209, 0.21830] | 0.15819 |
| 3 | 200/200 | 106/200 (0.530) | [0.45833, 0.60077] | 0.50287 |

The primary analytic increase is exactly 0 on this panel, satisfying the 0.01 margin. The first
pre-specified level exceeding the +0.05 boundary is \(\eta=1\). These probabilities are conditional
evaluations on the fixed latent panel, not population-prevalence estimates.

## Manuscript-ready integration template

> **Bounded observation noise preserves the gate law up to a measured masking boundary.** We
> replaced exact matching by support compatibility under independently added coordinatewise
> Uniform\([-\eta,\eta]\) observation noise. On 200 disjoint 20-rollout seed blocks of the
> CartWall@4 panel, the correct model passed every block at every pre-specified noise level. The
> exact conditional support-overlap calculation in
> `results/h7_noisy_observation_gate_v1.json` gives blind-model acceptance probabilities of 0.055
> at \(\eta=0\), 0.055 at the primary \(\eta=0.1\), and first exceeds the pre-specified +0.05
> boundary at \(\eta=1\), where it is 0.1582 (the independent noise realization accepts 32/200
> blocks, exact CP95 [0.1121, 0.2183]). Thus the noiseless equality
> statement becomes a support-probability statement: bounded noise through the primary level does
> not mask an additional block on this fixed panel, while sufficiently wide support measurably
> hides mode discrepancies. The unit is the seed block, not a rollout or transition.

The numbers and Clopper--Pearson intervals above are generated in `levels` and
`prespecified_decisions`; none is inferred from a rounded manuscript display.

## Licensed inference and blockers

This earns a non-asymptotic noisy-gate result and a measured robustness boundary for one designed
instrument. It does **not** complete the full H7 acceptance criterion:

1. only observation noise was added; process noise and an unknown noise law remain open;
2. truth and mode-blind analytic proxies were evaluated, not a new LLM synthesis campaign;
3. planning loss was not rerun because noise was confined to gate observations;
4. CartWall remains a designed instrument, not an externally specified contact benchmark.

The cheapest decisive external follow-up is to freeze a benchmark adapter and analysis before any
outcome is inspected: use a dependency-pinned, externally authored saturation/contact environment;
define the contact event from its own termination/contact signal; select disjoint training, gate and
held-out seed blocks; run the unchanged synthesis/gate/planner chain; and report mode exposure,
support-aware acceptance, held-out mode error and paired planning return for every attempted draw,
including refusals and failures. Until that run exists, the broader external-dynamics claim is not
earned.

## Reproduction

```bash
PYTHONPATH=src .venv/bin/python scripts/h7_noisy_observation_gate.py
PYTHONPATH=src .venv/bin/python scripts/h7_noisy_observation_gate.py --check
PYTHONPATH=src .venv/bin/pytest -q tests/test_h7_noisy_observation_gate.py
```
