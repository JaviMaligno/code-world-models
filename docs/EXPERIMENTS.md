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

## Pure-inference variant — `--no-rules` (2026-06-24)

To test whether the gap is hidden by *giving* the model the rules (translation,
not inference), we reran the grid withholding `RULES_TEXT` — synthesizing from
trajectories alone (generic `CONTRACT_API` only). `cwm/run_gap.py --no-rules`,
results suffixed `_norules`.

| Game | Regime | Synth | gate-pass | gaps (scored) | skip accuracies |
|------|--------|-------|-----------|---------------|-----------------|
| gen_tictactoe | correct prior | mini | 2/5 | [0.0, 0.0] | [0.61, 0.62, 0.96] |
| gen_tictactoe | correct prior | nano | 2/5 | [0.0, 0.0] | [0.0, 0.50, 0.63] |
| army5x5a | no prior | mini | 0/5 | – | all 0.0 |
| army5x5a | no prior | nano | 0/5 | – | all 0.0 |
| trike | wrong prior | mini | 0/5 | – | all 0.0 |
| trike | wrong prior | nano | 0/5 | – | all 0.0 |

**Findings:**
- Where the gate is reached, gap is still **0** — only gen_tictactoe passes
  (2/5), driven by recall, and those CWMs are correct (gap 0).
- For genuinely novel games (army5x5a, trike) pure inference **fails the gate
  entirely** (0% accuracy): the model cannot infer the dynamics from trajectories
  alone, especially the opaque action encodings (`from*25+to`; disc/pawn value
  scheme). It does not produce a wrong-but-gate-passing CWM — it produces nothing.

**Decisive conclusion.** Across with-rules and no-rules, in all three regimes,
there is **no "passes the gate but wrong on the search distribution" case**.
Either the model gets it right (gap 0) or it fails the gate. The coverage gap
does not materialize here. Diagnosis: for these games the random-trajectory
sample **identifies** the dynamics — there is no compact wrong hypothesis
consistent with 40 random games that diverges elsewhere (no under-determination).
The gate is not weak; it is identifying.

**Implication (pivot).** A real gap needs **sample under-determination**: a rule
that random play almost never exercises but optimal play seeks out (a rarely-
triggered tactic). That is the next instrument — see RESEARCH-DIRECTION.md.

## Rarity↔consequence tension (rule search, 2026-06-24/25)

Before building an instrument we searched for a rule that is **rare under random
play** (so the gate misses it) yet **consequential in competent play** (so a
planner exploits it). Validated empirically (`scratchpad` spikes): rarity =
fraction of random games the rule decides; consequence = R-aware-MCTS vs
R-blind-MCTS in the true game.

| Base | Rule | Rarity (random) | Consequence |
|------|------|-----------------|-------------|
| Connect Four | last-placer-on-full-board wins | 0% | none |
| Connect Four | corner 4-in-a-row is poison | 3% | weak |
| Connect Four | top-centre fill wins | 12% | strong |
| Connect Four | vertical-3 in centre wins | 23% | strong |
| Connect Four | 2×2 square wins | 38% | strong |
| army5x5a | infantry breakthrough wins | 75% | strong |

Six rules across two games lie on a **rarity↔consequence anti-correlation curve**:
anything a planner can force, random play also stumbles into. Connect Four
admits no rare-AND-consequential rule. **Diagnosis:** the gap requires a game
where random-play and competent-play state distributions diverge. A
random-vs-MCTS divergence measurement (`scripts/divergence.py`) ranked the games
by game-length divergence (competent − random median plies): **army5x5a** stands
out (random 23, competent 58, routinely hitting the 100-ply cap), while trike and
gen_tictactoe are Connect-Four-like (low divergence).

## The instrument: army5x5a + material-at-cap (2026-06-25)

In army5x5a's deep tail (competent play maneuvers there; random rarely reaches
it) a **material-at-cap** rule lands in the rare∧consequential quadrant: at the
ply cap with both generals alive, the player with more pieces wins (instead of a
draw). Validated: it *changes the outcome* in only **~1%** of random games (cap
reached 5.3%, mostly equal-material draws) yet decides **~50%** of competent
games. Implemented as `groundtruth/gen_chess_material.py` with paired specs:
`army5x5a_material` (complete rules) and `army5x5a_material_incomplete` (base
rules, omitting the rule). `run_gap.py --game <spec> --play-games N`.

### State-agreement is the wrong lens (dilution)

| Condition (mini, 5 seeds) | gate-pass | gap_truth | note |
|---------------------------|-----------|-----------|------|
| incomplete (omits rule) | 2–3/5 | **0.000** | skipped seeds failed gate at acc 0.998 — the rule WAS in their 40 training trajectories, so the base CWM mismatched it and the gate caught it |
| complete (control) | 5/5 | **0.000** | — |

`gap_truth` ≈ 0 in both conditions. The divergence region (cap+unequal-material)
is <1% of visited states, and symmetric MCTS self-play ties on material → the
states where the rule-blind CWM is wrong are barely visited. **A rare-but-pivotal
rule error does not move the state-agreement rate** (it is diluted), and the gate
is actually *sensitive* when the rule appears in the training sample (it then
fails the gate). nano fails the gate entirely on army5x5a (representational
complexity), as before.

### Play performance IS the lens (the result)

Adequacy for planning must be measured by **play**, not prediction accuracy. The
rule-omitting CWM is, for play, equivalent to hand-written base army5x5a (differs
only at the rare cap+material states), so its play cost is measured exactly and
Azure-free (`scripts/play_cost.py`, 600 sims, 240 games):

| Arena (true game = army5x5a + material) | win rate |
|-----------------------------------------|----------|
| truth-vs-truth (fairness baseline) | 0.479, 0.529 → **0.504** |
| **rule-blind vs truth** (base/incomplete-CWM) | 0.383, 0.383 → **0.383** |

The LLM-synthesized incomplete CWMs (gate-passing, gap_truth = 0) play at
**0.28–0.37** win rate vs a truth agent; the complete-rules CWMs at **0.38–0.45**
(non-overlapping) — and the hand-written rule-blind oracle, measured at scale,
sits at a reproducible **0.383** against a calibrated **0.504** baseline. Losing
~2:1 (≈63L/35W of 120).

**Headline finding.** A world model can pass transition-accuracy verification
(gate 1.0) and be **≥99% state-accurate on the search distribution** (gap_truth
= 0) yet **systematically lose at play** because the <1% it gets wrong is exactly
the pivotal tactic. Transition/state accuracy is the wrong adequacy criterion for
planning — play performance is. Complete rules close it (control plays near
baseline); an incomplete spec leaves a rare branch that sampling-based
verification cannot see but a planner punishes.

### Commands

```bash
# state-agreement grid, treatment + control, with play performance:
for c in army5x5a_material_incomplete army5x5a_material; do
  PYTHONPATH=src python -m cwm.run_gap --game $c --synth-size mini \
    --synth-seeds 5 --selfplay-games 20 --simulations 400 --train-games 40 --play-games 30
done
PYTHONPATH=src python scripts/play_cost.py   # Azure-free play-cost + fairness baseline
```

## Can the gap be repaired? — translation vs inference (2026-06-26)

Spikes on army5x5a + material-at-cap, INCOMPLETE rules unless noted. Play winrate
vs the true game (40 games/400 sims; baseline 0.28, fair truth-vs-truth 0.50).

| Repair attempt | discriminating examples | gate acc | rule learned | winrate |
|----------------|-------------------------|----------|--------------|---------|
| none (random trajectories) | 0 | 1.000 (false security) | no | 0.28 |
| naive DAgger (dump competent traj) | ~2 | 0.9996 | no | 0.28 |
| proper DAgger (flawed model's game path, iterated) | 4–5/round | 0.993 | no | 0.28–0.33 |
| targeted, **artificial** states | 120 | mini 0.916 / **large 0.004** | no | mini 0.35 / **large 0.05** |
| targeted, **real** (harvested on-manifold) | 54 | mini 0.959 / large 0.959 | no | mini 0.35 / **large 0.42** |
| **COMPLETE rules** + targeted (control) | 120 | **1.000 (0 iters)** | **yes** | **0.53** |

**Findings:**
1. **Detection works, repair-by-examples does not.** Verifying on the play/search
   distribution makes the gate drop below 1.0 (it *detects* the inadequacy that
   random-trajectory verification missed). But neither mini nor large can *infer*
   the rare rule from examples — even 54 real discriminating transitions with 12
   refinement iters leave the gate at 0.959 and the rule unlearned.
2. **Spec completeness is decisive.** Given the rule in RULES_TEXT, the model
   encodes it instantly (0 refinement iters) and plays at parity (0.53 ≈ 0.50).
3. **Scale helps only marginally.** large (0.42) > mini (0.35) on real data, both
   far below the complete-rules 0.53. The inference ceiling is general, not a
   mini-only artifact.
4. **Repair data must be on-manifold.** Artificial (unreachable) discriminating
   states *corrupt* synthesis — the large model collapsed to acc 0.004 / winrate
   0.05 trying to fit them. Harvested reachable states (flawed self-play ends at
   cap+unequal-material 6/20, 3× competent's 2/20) are sane but still
   insufficient to teach the rule.

**Unified thesis.** LLM code-world-model synthesis is rule **translation**, not
rule **inference**: it is correct iff the rules are specified. Sampling-based
verification gives false adequacy precisely because the model translates what it
was given — and the gate cannot surface a rule that was never specified and is
too rare to appear in samples. The actionable fix is **spec completeness +
verification on the play distribution** (which detects incompleteness); repairing
by feeding examples does not work at this model scale.

```bash
# repair spikes (Azure). The .env path is hard-coded; adjust if relocated.
PYTHONPATH=src python scripts/repair_spikes/spike_dagger2.py     # proper iterative DAgger
PYTHONPATH=src python scripts/repair_spikes/spike_harvest.py     # on-manifold real data, mini + large
PYTHONPATH=src python scripts/repair_spikes/spike_targeted2.py   # dose-response + complete-rules control
```
