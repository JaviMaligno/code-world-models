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
