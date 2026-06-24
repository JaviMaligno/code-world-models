# Experiments Log

Reproducible record of evaluation runs. All runs use the Azure OpenAI Global
Standard deployments (`gpt-5.4`, `gpt-5.4-mini`, `gpt-5-nano`) configured in
`.env`, baseline = `gpt-5.4` as a direct LLM policy.

Pricing in cost figures is real Azure list price (USD/1M tokens, in/out) as of
2026-06-24: gpt-5.4 = 2.5/15, gpt-5.4-mini = 0.75/4.5, gpt-5.4-nano = 0.2/1.25
(the nano deployment used is `gpt-5-nano`; cost approximated with 5.4-nano list
price). See `src/cwm/cost_meter.py`.

## Known-game results (30 games each, seed 7)

| Game | Synthesizer | Refinement iters | Transition accuracy | CWM W / D / L | Baseline illegal moves | CWM illegal | Total cost |
|------|-------------|------------------|---------------------|---------------|------------------------|-------------|------------|
| Tic-tac-toe | gpt-5.4-mini | 0 | 1.0 | 18 / 10 / 2 | 6 | 0 | $0.043 |
| Tic-tac-toe | gpt-5-nano | 0 | 1.0 | 21 / 8 / 1 | 5 | 0 | $0.043 |
| Connect Four | gpt-5.4-mini | 0 | 1.0 | 29 / 0 / 1 | 0 | 0 | $0.135 |
| Connect Four | gpt-5-nano | 0 | 1.0 | 30 / 0 / 0 | 2 | 0 | $0.132 |

CWM agent = synthesized world model + MCTS. Baseline = same prompt every turn,
model picks a move directly. Starts alternate each game.

### Commands

```bash
# Tic-tac-toe (30 games)
python -m cwm.run_experiment --game tictactoe --games 30 --synth-size mini --baseline-size large --simulations 200 --train-games 15 --seed 7
python -m cwm.run_experiment --game tictactoe --games 30 --synth-size nano --baseline-size large --simulations 200 --train-games 15 --seed 7

# Connect Four (30 games)
python -m cwm.run_experiment --game connect4 --games 30 --synth-size mini --baseline-size large --simulations 400 --train-games 40 --seed 7
python -m cwm.run_experiment --game connect4 --games 30 --synth-size nano --baseline-size large --simulations 400 --train-games 40 --seed 7
```

## Cost-gate conclusion

Running the experiment via API is trivially cheap. The synthesizer is a one-off
(~$0.005–0.01 per game built); the baseline (one call per turn) is the only
cost that scales, at ~$0.001–0.005 per game depending on game length. A
thousand-game study costs a few dollars. **No need for a subscription/Codex
fallback for the baseline.**

## Observations feeding the research direction

- Both tic-tac-toe and Connect Four synthesize to a perfect world model
  (transition accuracy 1.0, full contract) in **0 refinement iterations**, even
  though random trajectories cover a tiny fraction of Connect Four's state space.
  Interpretation: the model **recalls** these well-known games rather than
  inferring their rules from trajectories — so "accuracy 1.0 on sampled
  trajectories" likely coincides with global correctness *here* for the wrong
  reason. The coverage gap (sampled-verification vs correctness on the
  MCTS-visited distribution) is expected to surface on **novel** games where the
  model must genuinely infer rules. That is the planned next experiment.
- The same model encodes the rules perfectly as code (synthesizer) yet commits
  illegal moves as a direct policy (baseline) — code > intuition.

## Gap experiment — verified vs correct (2026-06-24)

Harness: `cwm/gap.py` + `cwm/run_gap.py` (spec/plan dated 2026-06-24). For each
synthesis seed we synthesize+refine a CWM to gate accuracy 1.0, then compare it
against the ground truth on three state distributions — D_gate (random-trajectory
states the gate used), D_cwm (states MCTS expands planning on the CWM), D_truth
(states MCTS expands planning on the ground truth). Headline **gap =
state_agreement(D_gate) − state_agreement(D_cwm)**, search-relevant variant
(legal_actions on truth-terminal states excluded — undefined and never queried by
MCTS; tracked separately as `legal_terminal_divergences`).

Protocol: 5 synthesis seeds × {mini, nano}, 20 self-play games, 300 simulations,
visited-cap 4000, train-games 40, seed 0. Baseline LLM not used (the gap is
intrinsic to the world model).

### Non-triviality sweep (MCTS vs random, CPU-only)

| Game | W/D/L | winrate |
|------|-------|---------|
| gen_tictactoe 6×6 win-4 | 20/0/0 | 1.00 |
| army5x5a | 16/0/0 | 1.00 |
| trike side-6 | 14/2/0 | 0.94 |

All three discriminate skill (MCTS beats random from both sides, zero losses).
army5x5a is balanced under strong search (MCTS-vs-MCTS at 800 sims: ~P1 2 / P2 3
/ 5 draws over 10), so the fast decisive games at low sims are weak-play blunders,
not a forced first-player win.

### Gap results

| Game | Regime | Synth | gap mean | gap max | gate-pass | median refine iters | exec-err |
|------|--------|-------|----------|---------|-----------|---------------------|----------|
| gen_tictactoe | correct prior | mini | 0.000 | 0.001 | 5/5 | 0 | 0 |
| gen_tictactoe | correct prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |
| army5x5a | no prior | mini | 0.002 | 0.008 | 4/5 | 0 | 0 |
| army5x5a | no prior | nano | n/a | n/a | 0/5 | – | 0 |
| trike | wrong prior | mini | 0.000 | 0.000 | 4/5 | 1 | 0 |
| trike | wrong prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |

### Findings

1. **The verified-vs-correct gap is ≈ 0 in all three regimes.** Whenever a CWM
   passes the random-trajectory gate (accuracy 1.0), it is also correct on the
   MCTS-visited distribution (D_cwm and D_truth agreement ≈ 1.0). The feared
   coverage gap did not materialize. **Honest null result** for the planned
   contribution as stated.
2. **The binding constraint is gate-attainability, not the gap.** What varies
   across regimes/sizes is whether a model can synthesize a gate-passing world
   model at all:
   - gen_tictactoe: trivial, 0 refinements, both sizes (recall).
   - army5x5a (no prior, complex action encoding `from*25+to` + ply counter):
     **mini gets it right first try (0 refinements, 4/5); nano fails 5/5**, stuck
     at ~1–2% accuracy even after refinement.
   - trike (wrong prior): **needs refinement** (0–5 iters) — the confabulated
     mechanics produce initially-wrong code that refinement corrects — but once
     gate-passed, gap 0. nano passes trike (5/5), so the army5x5a failure is
     representational complexity, not the knowledge regime.
3. Once the gate is passed, the synthesized code is **globally correct**. For
   small, fully-specified games, random-trajectory transition accuracy is a
   *sufficient* correctness gate — no wrong-but-verified CWM was observed.
4. `legal_terminal_divergences` is high for gen_tictactoe / army5x5a (the
   synthesized code omits the is_terminal guard in legal_actions) but 0 for trike
   (its terminal = "no legal slide" makes legal_actions=[] on terminal by
   construction). This is a convention artifact, correctly excluded from the gap.

### Harness bug found and fixed mid-run

The first grid run reported a spurious gap of ~0.6–0.8 on gen_tictactoe. Cause:
`contract_divergence` evaluated ~20k visited states in one sandbox call with a
10s timeout; slower (but correct) CWMs timed out and the report counted that as
state_agreement 0.0 → spurious gap 1.0. Fixed by chunking (1000/chunk, 60s, one
retry at 3×), an `n_exec_errors` field excluded from rate denominators, and a
visited-cap (4000). After the fix, exec-errors are 0 across the grid.

### Interpretation / implications

The planned "coverage gap" contribution does not reproduce on these small,
fully-specified games — likely because a CWM wrong anywhere also fails the random
gate here (the gate is a strong filter when the state space is small and rules are
complete). A real gap would need bigger or under-specified dynamics where the gate
is genuinely weak. The richer signal is **gate-attainability vs game complexity ×
model scale**, and the recall-vs-translate-vs-correct-confabulation distinction
across regimes. See RESEARCH-DIRECTION.md for the pivot options.

### Commands

```bash
PYTHONPATH=src python scripts/nontriviality_sweep.py
PYTHONPATH=src python scripts/gap_grid.py   # 3 games × {mini,nano}, 5 seeds each
```

Total grid cost ≈ $0.81 (army5x5a/nano alone $0.43 — wasted refinement loops on
unreachable gate). Per-run JSON in `results/` (git-ignored).
