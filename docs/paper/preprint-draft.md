# When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models

**Author:** Javier Aguilar Martin — AGILabs (javieraguilar.ai)
**Status:** First draft, 2026-06-27. Numbers from `docs/EXPERIMENTS.md` — re-verify against the log before submission.

---

## Abstract

Large language models (LLMs) can synthesize the rules of a game as executable code — a *Code World Model* (CWM) — which a classical planner then searches over. The synthesized model is typically accepted when it reaches high *transition accuracy* on sampled trajectories. We argue that this acceptance criterion is the wrong notion of adequacy for planning.

Across perfect- and imperfect-information games we find: (1) A CWM can pass a sampling gate at 100% transition accuracy and be ≥99% state-accurate on the distribution a planner actually visits, yet lose systematically at play — because the less than 1% it gets wrong is exactly the pivotal dynamics. We call this the *verified-vs-correct gap*. (2) The expected harm follows a quantitative law, `danger = play_cost × (1 − rarity)^N`, where `rarity` is the probability a random play-through triggers the omitted rule and `N` is the gate size. The `(1 − rarity)^N` factor is *proven exact* (i.i.d. Bernoulli); `play_cost` is measured empirically. This law predicts when sampling verification is blind: harm is negligible while the rule is common enough for the gate to catch, then rises through a threshold as it becomes rare, and saturates at the full `play_cost` once it almost always escapes. (3) The failure is not repaired by more data. LLM CWM synthesis is *rule translation*, not *rule inference*: it correctly encodes rules it was given and cannot infer rules that were omitted, regardless of model scale or the quantity of on-manifold example transitions. (4) The same failure mechanism recurs on the *inference* function of imperfect-information CWMs. We prove a coverage bound: a size-N random gate is identifying for the inference function when `N ≳ b^{d_max}`, which explains why shallow games (Kuhn poker, Leduc poker) show no inference gap. We also construct a minimal game, Beacon, that escapes this bound — a verified-but-wrong `infer_states` function passes the inference gate (0/8156 mismatches) yet loses every game (0.000 vs fair baseline 0.500), with the danger law recurring on this new axis.

Taken together, these results suggest that adequacy for LLM-synthesized world models used in planning should be measured on the search distribution or by play directly, not by prediction accuracy on sampled transitions, and that making the specification complete is more effective than attempting repair by example.

---

## 1. Introduction

### 1.1 The Code World Model paradigm

The observation that a small language model plus a well-specified world model plus classical search can outperform a much larger model used as a direct policy is central to recent work on LLMs for game playing. The *Code World Model* (CWM) paradigm makes this concrete: an LLM is prompted with a game's rules and some sampled trajectories, and asked to synthesize a fully executable implementation of the game's transition dynamics. A classical planner — typically Monte Carlo Tree Search (MCTS) — then searches over the synthesized world model, interacts with a referee (the true game), and is evaluated in an arena.

We reproduce this baseline on tic-tac-toe and Connect Four (§3.1): LLM-synthesized CWMs refined to transition accuracy 1.0 paired with UCT-MCTS dominate the same LLM used as a direct policy by wide margins (e.g., 29–1 in Connect Four). This reproduces the direction of the result in arXiv:2510.04542 (Lehrach et al., 2025) on known games. The synthesis is also trivially cheap: total API cost across all runs in this paper is approximately $2, with roughly $0.001–0.005 per arena game for the LLM-as-policy baseline and synthesis a one-off cost.

### 1.2 The implicit trust step

Accepting a synthesized world model involves a gatekeeping step: the CWM is refined in a sandbox until it achieves transition accuracy 1.0 on a set of randomly sampled trajectories. This gate is computationally cheap and serves as the only barrier between synthesis and deployment in the planner.

Our central question is: **does passing this gate certify that the CWM is adequate for planning?**

The concern is structural. A planner does not play randomly — it concentrates search on states it deems strategically significant. If the random-trajectory gate and the planner's search distribution diverge in a systematic way, there could exist a CWM that passes the gate yet is wrong precisely on the states that matter for competent play. We call this the *verified-vs-correct gap*.

### 1.3 A first look: when the gate is identifying

Our first experiments across three game families and two knowledge regimes (rules given / rules withheld) found that the feared gap does not appear on small, fully-specified games (§3.2). Whenever a CWM passes the random-trajectory gate, it is also correct on the MCTS-visited distribution; whenever it is wrong on the search distribution, it also fails the gate. For these games, the random sample is *identifying* — no compact wrong hypothesis fits all training trajectories yet diverges elsewhere. This is an honest null result; we report it as such, because understanding *when* the gate is identifying is necessary to understand when it is not.

### 1.4 When the gate fails: rare rules and the danger law

The null result on small games points to the condition under which the gate can be fooled: a rule that random play almost never triggers but competent play reliably seeks out. We engineered a minimal instrument satisfying this condition (§3.3): a variant of the game army5x5a augmented with a *material-at-cap* tiebreak rule that triggers in roughly 1% of random games but decides roughly 50% of competent games.

A CWM that omits this rule passes the gate at transition accuracy 1.0, is ≥99% state-accurate on the search distribution — yet loses approximately 2:1 in play (win rate 0.383 vs calibrated baseline 0.504). State accuracy is blind to the omission (dilution); play is not.

We then quantify when this can happen via a law that relates harm to gate size and rule rarity (§4), and show that the gap cannot be repaired by providing more example transitions (§5).

### 1.5 Extension to imperfect information

The same mechanism appears on the *inference* half of an imperfect-information CWM. An imperfect-information world model must also implement an `infer_states` function — given a sequence of observations, reconstruct the set of possible hidden states — and this function is gated separately. We prove (§6) that the inference gate is identifying when the game is shallow enough, explain why poker games fall below this threshold, and construct a minimal game (Beacon) where a verified-but-wrong `infer_states` passes the inference gate yet loses every game.

### 1.6 Contributions

This paper makes five contributions:

1. **The verified-vs-correct gap (§3.3):** A gate-passing, ≥99%-state-accurate CWM that loses ~2:1 in play. The gap arises from a rare-but-pivotal rule omitted from the specification and invisible to random-trajectory sampling. We also document the honest null — small fully-specified games show no gap — which clarifies the boundary conditions.

2. **A quantitative danger law (§4):** `danger = play_cost × (1 − rarity)^N`. The `(1 − rarity)^N` gate-miss factor is proven exact under i.i.d. Bernoulli sampling (Proposition 1); `play_cost` is empirical. The law predicts a threshold below which verification is safe and above which harm saturates at the full play cost.

3. **Translation, not inference (§5):** LLM CWM synthesis is rule translation. The omitted rule cannot be recovered from example transitions regardless of model scale (mini, large) or data regime (naive DAgger, proper DAgger, targeted on-manifold examples). Artificial off-manifold repair data actively corrupts synthesis.

4. **The coverage bound (§6, Theorem 1) and Beacon (§6.4):** We prove that a size-N random inference gate is identifying when `N ≳ b^{d_max} · p_chance^{-1} · log|𝓘|`, which explains the absence of an inference gap in Kuhn and Leduc. We then construct Beacon, the minimal game that escapes this bound, obtaining 0/8156 gate mismatches alongside 0.000 play win rate.

5. **Claim B — the belief model is invisible to a transition gate (§6.6):** We prove (Proposition 2) that the information partition encoded by `observation`/`infer_states` appears in no transition tuple, so a transition-accuracy gate cannot detect a wrong belief model. We demonstrate it on masked tic-tac-toe: withholding the masking rule yields a transition-gate-perfect (1.000) but belief-wrong (`observation_rate` 0.020) synthesis. With Beacon, this gives both faces of belief-model verification — a wrong belief loses at play *and* is invisible to a transition gate.

6. **Unification (§6, §7):** The verified-vs-correct gap and the inference gap are one mechanism on two halves of the CWM contract. A size-N random gate fails exactly on events of random-reach probability ≲ 1/N that competent play nonetheless reaches; the harm is `(consequence) × P(gate miss)`, with `P(gate miss) ≈ e^{−Nr}` for transition rules and `≈ e^{−N·b^{−d_max}}` for inference info-sets.

---

## 2. Setup and Methods

### 2.1 The CWM contract

A Code World Model is a Python module implementing the following interface (the *contract*):

- `initial_state() → state` — returns the starting game state.
- `legal_actions(state) → list[action]` — returns the list of legal actions.
- `apply_action(state, action) → state` — returns the next state.
- `is_terminal(state) → bool` — returns True if the game is over.
- `returns(state) → list[float]` — returns the utility vector (only valid on terminal states).

Each state is a Python dictionary containing at minimum `board` and `current_player` fields. For imperfect-information games (§6) the contract is extended with:

- `observation(state, player) → obs` — returns the observation available to a player at a state.
- `initial_states(obs, player) → list[state]` — returns all states consistent with a first observation.
- `infer_states(history_obs, player) → list[state]` — returns all states consistent with a sequence of observations.

This contract mirrors the minimal interface required by UCT-MCTS for perfect-information games and determinized MCTS for imperfect-information games.

### 2.2 Synthesis and the gate

An LLM (Azure OpenAI Global Standard deployments `gpt-5.4`, `gpt-5.4-mini`, `gpt-5-nano`; snapshot `gpt-5.4-2026-03-05`) is prompted with the game's `RULES_TEXT` and a set of random-policy trajectories. The prompt asks the model to synthesize a complete Python module implementing the contract.

The synthesized module is then refined in a sandbox: a referee plays a fresh set of random trajectories through both the synthesized CWM and the ground-truth oracle, and any discrepancy produces an error message fed back to the LLM for correction. Refinement continues until the synthesized CWM achieves *transition accuracy 1.0* on the random-trajectory sample, or until a refinement budget is exhausted. Passing this test is called *passing the gate*.

The transition accuracy metric is the fraction of (state, action, next-state) tuples from randomly sampled play-throughs on which the synthesized CWM agrees with the ground truth. Note that this is the gate's own lens; §3 and §4 argue it is the wrong lens for planning.

For imperfect-information games, an analogous *inference gate* measures accuracy on the `infer_states` function over the observations generated by random play.

### 2.3 Planning

For perfect-information games, planning uses UCT-MCTS with a configurable simulation budget (200–600 per move, depending on the experiment; see individual sections). The planner operates entirely on the synthesized CWM and never queries the true game during search; only the arena referee is the true game.

For imperfect-information games, planning uses determinized MCTS: at each decision point, the planner samples a set of possible hidden-state completions from `infer_states`, runs UCT-MCTS on each determinization, and aggregates votes (Cowling et al., 2012; Long et al., 2010). The planner is hardened to tolerate a faulty `infer_states` (raising exceptions, returning empty lists) via a legal-fallback mechanism, ensuring arena runs do not abort when the CWM is deliberately instrumented to be wrong.

### 2.4 Metrics

We distinguish two families of metrics throughout the paper:

**The gate's lens (prediction accuracy):**
- *Transition accuracy* — agreement rate on (state, action, next-state) under random play.
- *State accuracy* — fraction of states in a distribution where the CWM agrees with the ground truth on all contract outputs.
- *gap_truth* — difference in state agreement between the gate's random-trajectory distribution and the MCTS-visited distribution on the ground truth.

**The right lens (play performance):**
- *Win rate* — fraction of games won by the CWM+MCTS agent versus a ground-truth+MCTS opponent in an arena refereed by the true game, with Wilson score 95% confidence intervals.

Fairness baselines are established by running truth-vs-truth arenas (ground-truth+MCTS against itself), which should produce win rates near 0.5 for balanced games. Deviations from 0.5 in the fairness baseline indicate start-order imbalance or search-budget asymmetry; we report them alongside each play result.

### 2.5 Games

We use the following games, selected to span known, novel, and partially-known regimes:

- **Tic-tac-toe** — well-known; used to verify the CWM paradigm.
- **Connect Four** — well-known; used to verify the paradigm and as a negative control for the danger law.
- **Generalized tic-tac-toe 6×6 win-4** — a parameterized variant (m,n,k game with m=n=6, k=4); model has some prior knowledge.
- **army5x5a** — a generalized chess game from the DeepMind CWM paper (arXiv:2510.04542, Appendix H.5): a 5×5 board with infantry, cavalry, and general pieces, win by capturing the opponent's general. The paper's public release (arXiv, 2025-10-06) post-dates the GPT-5.4 knowledge cutoff (2025-08-31), so army5x5a falls outside the training window; a declarative probe independently confirmed the model does not know the detailed movesets — making it a genuine translation target.
- **army5x5a + material-at-cap** — the above, with an added tiebreak rule: if the game reaches the ply cap (100 plies by default) with both generals alive, the player with more material wins. This is the primary instrument for the rare-rule gap.
- **Trike** (Erickson, 2020) — an abstract combinatorial game; the model knows the name but confabulates the mechanics (wrong-prior regime). Real rules: place a disc on an empty cell on the shared pawn's line, then move the pawn to that disc; game ends when the pawn is surrounded; score = discs adjacent to the pawn.
- **Kuhn poker** — a minimal imperfect-information game; used to validate the imperfect-information pipeline.
- **Leduc poker** — a slightly larger poker game (6-card deck, community card, two betting rounds); used for the coverage-bound corollary.
- **Beacon** — a minimal game constructed specifically to instantiate the positive imperfect-information gap; described in §6.

Non-triviality of the novel games is confirmed empirically: MCTS beats random play from both sides on generalized tic-tac-toe 6×6, army5x5a, and Trike with zero losses (§3.2).

### 2.6 Cost

API synthesis is trivially cheap: approximately $0.043–$0.135 per game family for the known-game runs; roughly $0.81 total for the gap-grid across three games and ten seeds. The CPU bottleneck is MCTS. For the danger law (§4) we exploit the fact that `play_cost` is approximately constant by measuring it precisely once at scale (240 games, 600 simulations) and sweeping `rarity` cheaply (3000 random games per cap setting, no MCTS required). All results and reproduction commands are in `docs/EXPERIMENTS.md`.

---

## 3. The Gap: Accuracy ≠ Play-Adequacy

### 3.1 Known games reproduce the paradigm but do not stress the gate

LLM-synthesized CWMs on tic-tac-toe and Connect Four pass the transition gate in 0 refinement iterations and play at well above baseline performance. For completeness:

| Game | Synthesizer | Refinement iters | Transition accuracy | CWM W / D / L | Baseline illegal moves | CWM illegal | Total cost |
|------|-------------|------------------|---------------------|---------------|------------------------|-------------|------------|
| Tic-tac-toe | gpt-5.4-mini | 0 | 1.0 | 18 / 10 / 2 | 6 | 0 | $0.043 |
| Tic-tac-toe | gpt-5-nano | 0 | 1.0 | 21 / 8 / 1 | 5 | 0 | $0.043 |
| Connect Four | gpt-5.4-mini | 0 | 1.0 | 29 / 0 / 1 | 0 | 0 | $0.135 |
| Connect Four | gpt-5-nano | 0 | 1.0 | 30 / 0 / 0 | 2 | 0 | $0.132 |

(30 games each, seed 7; CWM agent = synthesized model + MCTS; baseline = direct LLM policy.)

The CWM+MCTS agents dominate the direct LLM policy, replicating the paradigm's core claim. However, the fact that these models reach transition accuracy 1.0 in zero refinements is itself revealing: on well-known games, the model is almost certainly *recalling* the rules rather than inferring them from trajectories. "Accuracy 1.0 on sampled trajectories" likely coincides with global correctness here for the right reason — but that coincidence has nothing to say about whether the gate is reliable in general.

### 3.2 The state-agreement gap does not appear on small complete-rules games

To measure the gap properly, we ran a grid across three knowledge regimes and two model sizes (5 synthesis seeds each, 20 self-play games, 300 simulations, train-games 40):

| Game | Regime | Synth | gap mean | gap max | gate-pass | median refine iters | exec-err |
|------|--------|-------|----------|---------|-----------|---------------------|----------|
| gen_tictactoe | correct prior | mini | 0.000 | 0.001 | 5/5 | 0 | 0 |
| gen_tictactoe | correct prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |
| army5x5a | no prior | mini | 0.002 | 0.008 | 4/5 | 0 | 0 |
| army5x5a | no prior | nano | n/a | n/a | 0/5 | – | 0 |
| trike | wrong prior | mini | 0.000 | 0.000 | 4/5 | 1 | 0 |
| trike | wrong prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |

We report this as an honest null. In every regime, the outcome is binary: either the CWM is globally correct (gap ≈ 0) or it fails the gate entirely. There is no case of a CWM that passes the gate yet is wrong on the MCTS-visited distribution. The same pattern holds in a `--no-rules` variant (synthesis from trajectories alone, with `RULES_TEXT` withheld): gen_tictactoe passes in 2/5 seeds via recall, with gap 0; army5x5a and Trike fail the gate entirely (0/5).

The diagnosis: for small, fully-specified games, the random-trajectory sample is *identifying* — no compact wrong hypothesis fits 40 random trajectories yet diverges on the search distribution. The gate is not weak; it is identifying. This makes it harder, not easier, to construct the gap: we need a game where random and competent play genuinely diverge.

The null is informative in a second way: it shows that the binding constraint on small games is *gate-attainability*, not gap size. nano fails army5x5a outright (0/5 gate passes) because the action encoding (`from*25+to` integer, plus a ply counter) is representationally complex; mini handles it (4/5). The knowledge regime matters less than model scale and encoding complexity. This is consistent with the translation hypothesis (§5).

### 3.3 The rare-rule instrument: verified but wrong at play (headline result)

The null result on fully-specified games points to the necessary condition for a gap: a rule whose random-play incidence is near zero but whose competent-play incidence is high. We searched for such rules systematically.

**The rarity↔consequence frontier.** We tested six rules across Connect Four and army5x5a (rarity = fraction of random games the rule decides; consequence = performance change from rule-aware vs rule-blind MCTS on the true game):

| Base | Rule | Rarity (random) | Consequence |
|------|------|-----------------|-------------|
| Connect Four | last-placer-on-full-board wins | 0% | none |
| Connect Four | corner 4-in-a-row is poison | 3% | weak |
| Connect Four | top-centre fill wins | 12% | strong |
| Connect Four | vertical-3 in centre wins | 23% | strong |
| Connect Four | 2×2 square wins | 38% | strong |
| army5x5a | infantry breakthrough wins | 75% | strong |

These six rules lie on a *rarity↔consequence anti-correlation curve*: anything a planner can force, random play also stumbles into. Connect Four admits no rule in the rare-and-consequential quadrant. The diagnosis is confirmed by a random-vs-MCTS game-length divergence measurement: army5x5a stands out with median game length 23 plies under random play vs 58 plies under competent play (routinely hitting the 100-ply cap), while Trike and generalized tic-tac-toe behave like Connect Four (low divergence). A game where random and competent play visit very different parts of the state space is the necessary substrate.

**The instrument.** We constructed a variant of army5x5a with a *material-at-cap* tiebreak rule: if the game reaches the ply cap (100 plies) with both generals alive, the player with more pieces wins (rather than drawing). This rule triggers in approximately 1% of random games (the cap is reached in 5.3% of random games, mostly as equal-material draws) yet decides approximately 50% of competent games. Implementations: `groundtruth/gen_chess_material.py` with paired specifications `army5x5a_material` (complete rules) and `army5x5a_material_incomplete` (base rules, omitting the material-at-cap tiebreak).

**State accuracy is the wrong lens.** A CWM that omits the material-at-cap rule passes the gate (transition accuracy 1.0), and the gap_truth is approximately 0 across all seeds:

| Condition (mini, 5 seeds) | gate-pass | gap_truth | note |
|---------------------------|-----------|-----------|------|
| incomplete (omits rule) | 2–3/5 | 0.000 | seeds that fail the gate do so because the rule appeared in their 40 training trajectories |
| complete (control) | 5/5 | 0.000 | — |

The divergence region (ply-cap states with unequal material) is less than 1% of visited states, and symmetric MCTS self-play tends toward equal material, so the states where the rule-blind CWM is wrong are barely sampled. State accuracy is diluted.

**Play performance is the right lens.** Measuring play directly (true game = army5x5a + material, arena refereed by truth, play_cost measured via `scripts/play_cost.py` at 240 games, 600 simulations):

| Arena (true game = army5x5a + material) | win rate |
|-----------------------------------------|----------|
| truth-vs-truth (fairness baseline) | 0.479, 0.529 → **0.504** |
| rule-blind vs truth (base/incomplete-CWM) | 0.383, 0.383 → **0.383** |

The fairness baseline is well-calibrated (0.504, consistent with no start-order bias). The rule-blind CWM loses approximately 2:1 (roughly 63 losses and 35 wins per 120 games) — a systematic, reproducible deficit. The LLM-synthesized incomplete CWMs play at 0.28–0.37 win rate (across seeds) vs truth; the complete-rules CWMs at 0.38–0.45 (non-overlapping).

**Summary.** A world model can pass transition-accuracy verification (gate 1.0), be ≥99% state-accurate on the search distribution (gap_truth = 0), and yet lose systematically at play — because the less-than-1% it gets wrong is exactly the pivotal tactic. Transition and state accuracy are the wrong adequacy criteria for planning. Play performance is the right criterion.

---

## 4. A Quantitative Law of Sampling-Verification Harm

We now characterize *when* the harm from a sampling gate is large. The key observation is that a gate of N random play-throughs fails to observe a rule that fires with probability r per play-through with exact probability `(1 − r)^N`. We formalize this and measure the remaining empirical component.

### 4.1 The gate-miss proposition

**Proposition 1 (gate-miss probability).** *A sampling gate draws N i.i.d. uniform-random play-throughs and accepts the CWM if none of them triggers a discrepancy on the rule in question. Since each play-through triggers the rule independently with probability r (the "rarity"), the probability the gate never observes the rule is exactly:*
$$P(\text{miss}) = (1 - r)^N \approx e^{-Nr}.$$
*Proof.* Each play-through is a Bernoulli(r) event (rule fires / does not fire), and the N plays are i.i.d. (uniform-random policy is memoryless). The probability all N draws are non-firing is $\prod_{i=1}^{N}(1-r) = (1-r)^N$. ∎

The approximation $e^{-Nr}$ is useful for intuition but the exact expression $(1-r)^N$ is what the table below uses.

**Corollary (danger law).** *Let $\kappa = \text{play\_cost}$ be the expected play deficit of a planner whose CWM omits the rule, conditional on the omission surviving the gate. The expected harm from a gate of size N is:*
$$\text{danger}(N) = \kappa \cdot (1 - r)^N.$$
The $(1-r)^N$ factor is exact (Proposition 1); $\kappa$ is the empirically-measured, game- and planner-specific consequence magnitude.

**Remark (what stays empirical).** The measured regularity that $\kappa$ is approximately constant across rarity values is structural but not analytically forced. It holds here because competent MCTS reaches the ply-cap region regardless of how the rarity knob tunes r — i.e., the consequence of omitting the rule is roughly the same whether the rule is common or rare, as long as it escapes the gate. This invariance requires the planner to consistently reach the rule region, a property of the game and search budget, not of the sampling model.

### 4.2 Measured danger curve

We measure `play_cost` precisely once (play_cost ≈ 0.12, from independent runs: `play_cost.py` returns 0.117–0.121 at cap=100, n=240, 600 sims; `law_sweep` returns 0.112 at cap=30) and sweep `rarity` cheaply by varying the ply cap (a lower cap makes the cap-and-equal-material event more common, hence larger rarity; a higher cap makes it rarer). Rarity per cap is measured over 3000 random games. Results:

| cap | rarity | (1−r)^40 | danger@N=20 | danger@N=40 | danger@N=80 |
|----:|-------:|---------:|----------:|----------:|----------:|
|  25 | 0.337  | 0.0000   | 0.000 | 0.000 | 0.000 |
|  40 | 0.208  | 0.0001   | 0.001 | 0.000 | 0.000 |
|  60 | 0.107  | 0.0107   | 0.012 | 0.001 | 0.000 |
|  80 | 0.056  | 0.0997   | 0.038 | 0.012 | 0.001 |
| 100 | 0.025  | 0.3583   | 0.072 | 0.043 | 0.015 |
| 120 | 0.011  | 0.6339   | 0.096 | 0.076 | 0.048 |
| 140 | 0.007  | 0.7652   | 0.105 | 0.092 | 0.070 |

The result is a threshold law, not an inverted-U. Danger is approximately zero while the rule is common enough for a size-N gate to catch (cap ≤ 50), rises through a threshold as the rule becomes rare (cap 60–100), and plateaus at approximately the full play_cost once the rule almost always escapes the gate (cap ≥ 120). The gate size N shifts the threshold: larger N pushes it toward rarer rules.

### 4.3 Why Connect Four lies safely below the threshold

Six rules across Connect Four and army5x5a were tested (§3.3). All of Connect Four's consequential rules have rarity 0.12–0.38, giving $(1-r)^{40} \approx 0$ — they are caught by even a modest gate. army5x5a's material-at-cap rule at cap=100 has rarity 0.025, giving $(1-r)^{40} \approx 0.36$ — deep in the danger zone. The structural reason is the same: in Connect Four, any rule that a planner can force also appears regularly under random play (the rarity↔consequence tension); in army5x5a, competent play drives the game to the deep-ply-cap region that random play almost never reaches.

---

## 5. Repairing the Gap: Translation, Not Inference

If the gap is caused by a missing rule, can it be repaired by providing example transitions that demonstrate the rule? We ran a systematic set of repair attempts on army5x5a + material-at-cap with incomplete rules.

### 5.1 Repair experiments

All conditions use the mini synthesizer unless noted; play winrate is vs the true game, 40 games at 400 simulations; baseline 0.28, fair truth-vs-truth 0.50. Discriminating examples are transitions that involve the material-at-cap rule.

| Repair attempt | discriminating examples | gate acc | rule learned | winrate |
|----------------|-------------------------|----------|--------------|---------|
| none (random trajectories) | 0 | 1.000 (false security) | no | 0.28 |
| naive DAgger (dump competent trajectories) | ~2 | 0.9996 | no | 0.28 |
| proper DAgger (flawed model's game path, iterated) | 4–5/round | 0.993 | no | 0.28–0.33 |
| targeted, **artificial** states | 120 | mini 0.916 / large 0.004 | no | mini 0.35 / large 0.05 |
| targeted, **real** (harvested on-manifold) | 54 | mini 0.959 / large 0.959 | no | mini 0.35 / **large 0.42** |
| **COMPLETE rules** + targeted (control) | 120 | **1.000 (0 iters)** | **yes** | **0.53** |

### 5.2 Findings

**Detection works, repair does not.** Verifying on the play/search distribution — rather than random trajectories — drops the gate below 1.0, detecting the inadequacy that random-trajectory verification missed. But neither mini nor large can *infer* the missing rule from examples. Even 54 real, on-manifold discriminating transitions with 12 refinement iterations leave the gate at 0.959 and the rule unlearned.

**Spec completeness is decisive.** Given the rule in `RULES_TEXT`, the model encodes it correctly in 0 refinement iterations and plays at parity with the baseline (0.53 ≈ 0.50). The complete-rules control leaves no doubt: the limitation is not the synthesizer's code-writing ability but the absence of the rule from the specification.

**Scale helps marginally but not sufficiently.** The large model (0.42) exceeds mini (0.35) on real on-manifold data, but both remain far below the complete-rules baseline (0.53). The inference ceiling is not a mini-specific artifact.

**Off-manifold repair data corrupts synthesis.** Artificial (unreachable) discriminating states cause catastrophic failure in the large model (accuracy collapses to 0.004, win rate 0.05). The synthesizer attempts to fit transitions that cannot arise in real play and damages the parts of the CWM it had already learned correctly.

### 5.3 Conclusion: translation, not inference

LLM CWM synthesis is *rule translation*: it correctly encodes rules it was given and cannot reliably infer rules that were omitted, even when those rules are demonstrated by example transitions. The actionable implication is that the specification must be complete before synthesis, and that verification on the play distribution detects (but does not repair) incompleteness. Attempting repair by feeding example transitions is not a reliable substitute for a complete specification.

---

## 6. Imperfect Information: The Inference Function as a New Failure Surface

The danger law applies not just to the transition function (the CWM's model of how states evolve) but also to the inference function (the CWM's model of how to reconstruct hidden state from observations). We extend the contract, prove a coverage bound that explains when the inference gate is provably safe, and construct a minimal game where it is not.

### 6.1 Pipeline validation: Kuhn poker

Before constructing a gap, we validate the imperfect-information pipeline on Kuhn poker, a well-understood minimal game (3-card deck, 1 betting round per player, net-chip payoff).

| Synth | transition gate | inference gate (obs / infer) | CWM-vs-truth play | fair baseline |
|-------|-----------------|------------------------------|-------------------|---------------|
| large | 1.000 (0 iters) | 1.000 / 1.000 | 0.470 [0.422, 0.519] | 0.470 [0.422, 0.519] |
| mini | 0.845 (12 iters, fails gate) | 1.000 / 0.000 (infer_states crashes) | — | — |

The large model recalls Kuhn poker; both transition and inference gates pass; the CWM+determinized-MCTS agent plays at 0.470 [0.422, 0.519], overlapping with the truth-vs-truth baseline — consistent with a near-zero gap, as expected when the model has recalled the game correctly. The mini model fails: the transition gate stalls at 0.845 and the synthesized `infer_states` raises a runtime error (`'list' object is not callable`). This scale/representation dependence is consistent with the translation-not-inference finding of §5.

### 6.2 When the inference gate is provably sufficient: a coverage bound

We now formalize when the inference gate sampled on random play is *identifying* — i.e., when every competent-play-relevant inference error would be caught by the random-trajectory gate.

**Setup.** Consider a finite two-player extensive-form game with chance (the deal) and imperfect information. Let: $b$ = maximum branching over player decision nodes; $d(I)$ = number of player-action edges on a shortest history reaching information set $I$; $d_{\max} = \max_I d(I)$; $p_{\text{chance}}$ = minimum probability of a deal consistent with any reachable info-set; $\mathcal{I}$ = set of reachable info-sets. The uniform-random policy $\rho$ plays every legal action with probability $1/|A| \geq 1/b$.

**Lemma 1 (inclusion).** *For any policy profile $\sigma$, $\text{reach}(\sigma) \subseteq \text{reach}(\rho)$.*

*Proof.* Every player edge has $\rho$-probability $\geq 1/b > 0$ and chance edges are shared, so any history with $\pi^\sigma(h) > 0$ has $\pi^\rho(h) > 0$. ∎

**Lemma 2 (reach lower bound under $\rho$).** *Every reachable info-set $I$ has $\pi^\rho(I) \geq p_{\text{chance}} \cdot b^{-d(I)} \geq p_{\text{chance}} \cdot b^{-d_{\max}}$.*

*Proof.* Take any history $h \in I$; $\pi^\rho(h) = \pi_{\text{chance}}(h) \cdot \prod_{\text{edges}} 1/|A| \geq p_{\text{chance}} \cdot b^{-d(h)}$, and $\pi^\rho(I) \geq \pi^\rho(h)$. ∎

**Theorem 1 (the inference gate is identifying when $N \gtrsim b^{d_{\max}}$).** *Draw $N$ i.i.d. games under $\rho$. The probability that some reachable info-set is never visited is at most $|\mathcal{I}| \cdot \exp(-N \cdot p_{\text{chance}} \cdot b^{-d_{\max}})$ (union bound over info-sets plus Lemma 2). Hence for $N \gtrsim b^{d_{\max}} \cdot p_{\text{chance}}^{-1} \cdot \log |\mathcal{I}|$, the random sample covers every reachable info-set with high probability — and by Lemma 1, every info-set any policy (including a competent planner) relies on. An inference function whose error is confined to reachable info-sets is then detected with high probability, so no gate-passing inference function can be play-inadequate through a coverage gap.* ∎

**Corollary (Kuhn, Leduc).** Kuhn: $b=2$, $d_{\max} \approx 2$, so the gate is identifying at any $N$. Leduc: $b=3$, $d_{\max} \approx 8$, so $b^{d_{\max}} \approx 6561$; at $N = 8000$ the gate already covers everything. This prediction is directly confirmed by measurement: with N=8000 random games, 0/1259 of the competent player's inference-relevant info-set visits are on info-sets that random play missed.

**Design corollary (when a gap is possible).** A coverage gap requires $b^{d_{\max}} \gg N$ at feasible $N$ — large branching and/or large depth — with a competent policy that concentrates reach on a deep region of $\rho$-measure $\ll 1/N$. This is the imperfect-information analogue of the rare-rule condition: a region that random play almost never samples but competent play reliably visits.

### 6.3 Leduc depth probe: poker depth does not create an inference gap

To confirm that poker cannot supply the necessary depth, we swept Leduc's per-round raise cap to artificially deepen the betting tree:

| raise cap | random info-sets (max depth) | competent info-sets (max depth) | uncovered inference-relevant |
|-----------|------------------------------|--------------------------------|------------------------------|
| 2 | 574 (8) | 120 (6) | 0 / 418 = 0.0000 |
| 4 | 1090 (11) | 128 (7) | 0 / 400 = 0.0000 |
| 6 | 1210 (12) | 127 (9) | 5 / 396 = 0.0126 |

A coverage gap appears only at cap 6, and is marginal (1.26% of competent visits, 5 info-sets) — insufficient for a CI-separated play deficit. The mechanism is fundamental: in poker, betting depth comes from aggression, and competent play minimizes aggression (it calls or folds dominated hands). Competent info-sets are always a strict subset of random-covered ones — the opposite of the structure needed for a coverage gap. Poker is the wrong family.

### 6.4 Beacon: a minimal positive imperfect-information gap

A positive gap requires a game where depth comes from *survival*: optimal play reaches a deep region by staying alive, while random play blunders out early. This is the exact imperfect-information analogue of the rare-rule gap in army5x5a, where competent play reaches the ply cap (the deep region) while random play ends much earlier.

**Game construction.** Beacon is a two-player game with the following structure:

1. *Setup.* Each player is assigned a hidden type (0 or 1) uniformly at random. The game has T rounds.
2. *Survival walk (rounds 1 to T).* Each round, each player must choose a move; for player $i$ in round $t$, the move is *safe* iff $(k_i + t) \mod 2 = 0$ (where $k_i$ is some information known to the player but determined by the hidden type). An unsafe move loses immediately. The probability that a uniformly-random player survives all T rounds is $(1/2)^T$; a player who knows their type plays safely always and survives with probability 1.
3. *Final round (round T+1).* Each player must guess the opponent's hidden type, which is inferable from the opponent's observed moves during the survival walk. The player who correctly identifies the opponent wins; both correct guesses draw.

The region "game reaches the final round" is called D (the deep region). Random play reaches D with probability $(1/2)^{2T}$ (both players must survive); optimal play reaches D with probability 1.

**The instrument.** A CWM whose `infer_states` is *correct* except that it flips the inferred opponent type at final-round states (`status == 1`) — wrong only on D. Random play almost never samples D, so the inference gate almost never sees the error. The correct inference function enables the determinized MCTS planner to make the right guess; the flipped inference function causes the planner to guess wrong.

**Result (T=8, GATE_GAMES=2000, arena N=400×3 seeds, 100 simulations, 2 determinizations):**

| metric | value |
|--------|-------|
| random reaches final round | 0.00000 |
| instrument inference mismatches on random gate sample | **0 / 8156** (passes the gate) |
| fair baseline (truth vs truth) win rate | 0.500 [0.472, 0.528] (all draws) |
| instrument win rate vs truth | **0.000 [0.000, 0.003]**, net −1200/1200 |

The instrument passes the inference gate perfectly — 0 mismatches on 8156 sampled observations — yet loses every game. This is the imperfect-information analogue of the rare-rule gap: a verified-but-wrong inference function that is play-inadequate.

What is proven vs measured: the reach bound $(1/2)^{2T}$, the fact that optimal play reaches D with probability 1, and the logical implication that flipping the inference on D causes the planner to guess wrong are all analytic properties of the Beacon construction. The play win rate 0.000 [0.000, 0.003] and the 0/8156 gate mismatch count are measured. The determinized planner's conversion of correct inference into the winning guess was verified by a whole-branch code review.

*Caveat.* Beacon is a minimal, strategically trivial witness. Its purpose is to prove that the coverage gap can exist and can have the exact form predicted by the coverage-bound design corollary, not to model a realistic game. The reach-probability structure is engineered specifically to satisfy $b^{d_{\max}} \gg N$; natural games with this structure would involve hidden information in genuinely complex board games.

### 6.5 The danger law on the inference axis

The danger law from §4 applies directly to the inference gap. Sweeping $T$ (so $\varepsilon = (1/2)^{2T}$, the probability that a random game reaches D) against a fixed gate $N = 2000$ and $\text{play\_cost} = 0.5$:

| T | ε | gate-miss $(1−ε)^N$ | danger |
|---|---|---------------------|--------|
| 4 | 3.9×10⁻³ | 0.000 | 0.000 |
| 6 | 2.4×10⁻⁴ | 0.614 | 0.307 |
| 8 | 1.5×10⁻⁵ | 0.970 | 0.485 |
| 10 | 9.5×10⁻⁷ | 0.998 | 0.499 |

At T=4, the deep region is frequent enough that a gate of N=2000 catches the inference error (danger ≈ 0); by T ≥ 8, the gate is blind and harm saturates near play_cost/2 (the maximum possible given the game structure). The same threshold law, the same $(1−\varepsilon)^N$ factor, now instantiated on the inference half of the contract.

### 6.6 Claim B: the belief model is invisible to a transition gate

Beacon (§6.4) shows a verified-but-wrong belief model *loses at play*. The complementary verification question is whether a transition-accuracy gate could have *caught* the wrong belief model in the first place. It cannot, and for a structural reason.

**Proposition 2 (belief–transition orthogonality).** A transition dataset is a set of tuples $(s, a, s', r)$ over *full* ground-truth states. The functions `observation(s, p)` and `infer_states(o, p)` encode the information partition — what player $p$ can distinguish — which appears in no $(s, a, s', r)$ tuple. Therefore (i) no transition dataset constrains the masking convention; (ii) a gate that scores transition accuracy cannot detect an incorrect `observation`/`infer_states`; (iii) the belief model must be specified and is verifiable only by a separate inference gate. $\blacksquare$

**Demonstration (masked tic-tac-toe).** We take standard tic-tac-toe dynamics (which GPT-5.4 synthesizes at transition gate 1.000 by recall) and overlay an arbitrary, non-recallable masking rule: the center cell is hidden from both players (shown as $-1$), even after it is played. We synthesize the contract two ways — with the masking rule present (*full*) and with it removed (*withheld*, leaving tic-tac-toe + an imperfect-information framing that still demands `observation`/`infer_states` but does not say what is hidden) — and gate each on transitions and on inference:

| variant | transition gate | observation_rate | inference_rate |
|---------|-----------------|------------------|----------------|
| full rules | **1.000** (0 iters) | **1.000** | 0.000 (infer_states crashes) |
| withheld masking rule | **1.000** | **0.020** | 0.180 |

The transition gate is **1.000 in both arms** — the dynamics are recall, unaffected by the masking rule, and the gate (which calls only `apply_action`/`legal_actions`/`is_terminal`/`returns`) never invokes the belief functions. With the rule, the model masks the center correctly (`observation_rate` 1.000); without it, the synthesized `observation` does not mask the center (`observation_rate` 0.020) — a wrong belief model that the transition gate nonetheless certifies at 1.000. This is Proposition 2 instantiated: a wrong belief model is invisible to a transition gate.

The clean discriminator is `observation_rate`, not `inference_rate`: GPT-5.4's synthesized `infer_states` raises `'list' object is not callable` across three distinct games (Kuhn-mini, Beacon, masked tic-tac-toe), so `inference_rate` is confounded by a synthesis-robustness failure in both arms. That recurring crash is itself a secondary finding — the belief surface is not only un-gateable by transition data but also hard to synthesize at all.

Together, Beacon (Claim A) and masked tic-tac-toe (Claim B) are the two faces of belief-model verification: a wrong belief both **loses at play** and is **invisible to a transition gate**.

---

## 7. Related Work

### 7.1 Objective mismatch in model-based reinforcement learning

The closest conceptual antecedent is the *objective mismatch* problem in model-based reinforcement learning identified by Lambert et al. (2020): prediction accuracy of a learned world model and the downstream control performance of a planner using that model can diverge substantially, because they optimize different objectives. Our work is in the same spirit but differs in setting and mechanism. We work in the LLM-code-synthesis regime (the world model is a synthesized program, not a learned neural model), the verification step is a discrete sampling gate (not a continuous loss), and the failure mode we characterize is a *rule-coverage blind spot* in that gate rather than a model-capacity or distribution-shift issue. We also provide a closed-form danger law and a proof that the gate-miss probability is exact under i.i.d. Bernoulli sampling — not just an empirical observation.

The broader literature on model-based RL world-model quality (e.g., Dreamer, Hafner et al., 2020; MBPO, Janner et al., 2019) largely focuses on learned continuous-state models where world model error is pervasive rather than localized. Our rare-rule gap is a localized, discrete failure that state-accuracy metrics mask by dilution — a point that may be worth revisiting in continuous settings as well.

### 7.2 Code World Models and LLMs for game playing

The Code World Models for General Game Playing paper (Lehrach et al., arXiv:2510.04542, 2025) introduces the paradigm we build on: an LLM synthesizes an executable world model from rules and trajectories, which a classical planner (in their case, MCTS) then uses. Their results on a set of novel DeepMind board games show that CWM+MCTS outperforms direct LLM policy. We reproduce this result on tic-tac-toe and Connect Four (§3.1) and extend the paradigm to ask whether the gate they use — transition accuracy on random trajectories — certifies play-adequacy. Our contribution is essentially a rigorous negative answer on that question, together with the mechanisms that explain it.

Related work on code-as-policy (e.g., Liang et al., 2023; Gao et al., 2023) uses LLMs to synthesize executable plans or robot controllers, typically verified by execution rather than by sampling. The distinction between what the LLM was told and what it can infer is implicit in much of this work but has not, to our knowledge, been studied with a controlled rare-rule instrument.

The gg-bench effort (arXiv:2505.07215) generates novel games procedurally specifically to avoid LLM contamination. Our army5x5a instrument is chosen partly for the same reason (verified non-recall of movesets, §2.4) and the gg-bench approach is an attractive complement for future scaling.

### 7.3 DAgger and dataset aggregation

Our §5 repair experiments are directly inspired by the DAgger framework of Ross, Gordon, and Bagnell (2011): iteratively label states visited by the current learned policy under the oracle, and retrain. In DAgger's original imitation-learning setting, this reduces covariate shift. Our finding — that DAgger fails to teach the rare rule — is consistent with the translation hypothesis: DAgger addresses *distribution mismatch* between training and test, but the bottleneck here is not distribution mismatch. The model receives discriminating examples of the rule; it simply cannot infer the rule from them. This is a different failure mode from the one DAgger was designed to address.

### 7.4 Imperfect-information planning and determinization

Determinized MCTS (also called single-observer MCTS, SOMCTS, or information-set MCTS in some formulations; Cowling et al., 2012; Whitehouse et al., 2011; determinization analysis, Long et al., 2010) resolves imperfect information by sampling a consistent complete-information game at each decision point. It is not game-theoretically optimal — it is subject to the strategy-fusion problem — but it is a practical planner for moderate-sized imperfect-information games. We use it as the planner in §6, holding the planner fixed across conditions (the baseline is truth-vs-truth under the same determinized MCTS) so that the contrast isolates the CWM inference function rather than planner quality.

Counterfactual regret minimization (CFR; Zinkevich et al., 2007) and its variants are the standard for Nash-equilibrium-optimal play in imperfect-information games but require exact game structure and are not CWM-compatible without further adaptation; we leave that direction to future work.

---

## 8. Limitations and Honest Assessment

**Single model family.** All synthesis experiments use Azure OpenAI GPT-5.x (mini, nano, large). Whether the translation-not-inference finding generalizes to other LLM families — especially open models or post-training variants with stronger code-reasoning abilities — is untested. The rare-rule instrument (§3.3) is carefully constructed to require true rule inference, not recall, so we believe the finding is likely to persist at similar scales, but this is a claim rather than a measurement.

**The rare-rule instrument is engineered.** The material-at-cap rule was selected specifically because it falls in the rare-and-consequential quadrant. We do not claim that all or even most rules in arbitrary games will produce this kind of gap; the rarity↔consequence anti-correlation found in Connect Four (§3.3) shows that the gap requires a specific structural condition. The point is that the gap *can* exist and *does* exist in a game where random and competent play diverge — which is itself informative about when the sampling gate is unsafe.

**Pure-Python MCTS limits arena size.** Our MCTS implementation is a pure Python reference. This limits the number of simulations and arena games that are computationally tractable, which in turn limits the tightness of confidence intervals for some conditions. We mitigate this with the cheap/expensive separation in the danger law (§4) — rarity is swept cheaply, play_cost is measured precisely once at scale — and with Kuhn poker's small game size (tight CIs). The headline play result (0.383 vs 0.504) is reproducible across seeds and CI-separated.

**Determinized MCTS is not game-theoretically optimal.** As noted in §7.4, determinized MCTS is subject to strategy fusion and is not a Nash-equilibrium strategy. The baseline for the imperfect-information experiments is truth-vs-truth under the same determinized MCTS (not an equilibrium baseline), so the contrast is internally consistent but not a statement about how a game-theoretically optimal player would interact with the gap.

**Beacon is a minimal, strategically trivial witness.** Beacon was designed to satisfy the coverage-bound design corollary in the smallest possible game, not to model a realistic scenario. Its survival-walk structure is artificial. The experiment establishes existence and confirms the danger law on the inference axis; it does not demonstrate that natural imperfect-information games with the same structure produce an equally clean gap. Building such a game (e.g., a partially-observable variant of army5x5a) is a natural next step.

**Scope of Claim B.** Claim B (§6.6) establishes that a transition gate is blind to a wrong belief model, demonstrated by withholding an *observation* (masking) rule that is genuinely independent of the dynamics. It does not establish the stronger claim that the belief model could never be inferred from any richer, observation-bearing signal — only that transition data cannot constrain it (Proposition 2) and that withholding the rule yields a wrong, transition-certified belief model. The recurring `infer_states` synthesis crash also means our cleanest signal is `observation_rate`; a study isolating the inference-enumeration failure from the masking failure is future work.

**Knowledge cutoff and contamination.** GPT-5.4's training cutoff is approximately 2025-08-31, and the army5x5a paper (arXiv:2510.04542) was released 2025-10-06 — after the cutoff — so the game falls outside the training window. We additionally confirmed via a declarative probe that the model does not recall the specific movesets (§2.4), and the gate-attainability difficulty (nano fails 5/5) is further evidence of genuine translation rather than recall. Even so, the "post-cutoff = uncontaminated" argument is not a hard guarantee (cutoff dates are approximate and corpora leak); readers should interpret the "no prior" label as "no detectable recall" rather than "strictly novel."

---

## 9. Conclusion

The central finding of this paper is that transition accuracy on randomly sampled play-throughs is the wrong adequacy criterion for an LLM-synthesized world model used in planning. A model can pass this gate at 100% accuracy and remain ≥99% state-accurate on the distribution the planner actually visits, yet lose systematically at play — because the less than 1% it gets wrong is exactly the pivotal dynamics.

The failure follows a quantitative law: `danger = play_cost × (1 − rarity)^N`. The gate-miss factor is proven exact under i.i.d. Bernoulli sampling; play_cost is empirical. This law identifies the condition under which sampling verification is unsafe: a rule whose random-play incidence is small enough to escape a size-N gate but whose competent-play incidence is high enough to matter.

The gap is not repaired by providing example transitions. LLM CWM synthesis is rule translation: it encodes rules it was given and does not infer rules that were omitted, regardless of model scale or the form of the repair data. Off-manifold repair data actively corrupts synthesis. The actionable fix is specification completeness plus verification on the play distribution; the latter detects but does not repair incompleteness.

The same mechanism appears on the inference half of imperfect-information CWMs. We prove a coverage bound that explains why shallow poker games are safe (their inference gate is provably identifying), and construct a minimal game (Beacon) where a verified-but-wrong `infer_states` passes the gate yet loses every game, with the danger law recurring on the inference axis. Perfect-information board games (transition rules, rarity r) and imperfect-information games (inference info-sets, depth T) are the same statement on two faces of the CWM contract.

These results suggest two concrete practices. First, verify on the distribution that planning visits — or measure play directly — rather than on randomly sampled transitions. Second, ensure the specification is complete before synthesis; the model will translate what it is given, and gaps in the specification become invisible to sampling-based verification.

---

## Appendix A: Reproducibility

All experimental results and exact reproduction commands are in `docs/EXPERIMENTS.md`. All code is on the `main` branch (`cwm/` package, `scripts/`). Research narrative and formal theorem statements are in `docs/RESEARCH-DIRECTION.md`.

Key scripts:
- `scripts/nontriviality_sweep.py` — confirms game non-triviality
- `scripts/gap_grid.py` — state-agreement gap across regimes
- `scripts/play_cost.py` — play_cost measurement at scale
- `scripts/law_curve.py` — danger law curve (rarity sweep + cost probes)
- `scripts/repair_spikes/` — DAgger and repair experiments
- `scripts/run_kuhn_validation.py` — imperfect-information pipeline validation
- `scripts/leduc_coverage_diagnostic.py` — Leduc coverage-gap measurement
- `scripts/leduc_depth_probe.py` — Leduc depth sweep
- `scripts/beacon_claimA.py` — Beacon Claim A result and danger law sweep
- `scripts/mtt_claimB_probe.py` — masked tic-tac-toe Claim B probe (full vs withheld masking)

All runs use the Azure OpenAI Global Standard deployments configured in `.env`. Per-run JSON results are in `results/` (git-ignored). Total API cost across all experiments: approximately $2.

---

## References

- Cowling, P. I., Powley, E. J., & Whitehouse, D. (2012). Information Set Monte Carlo Tree Search. *IEEE Transactions on Computational Intelligence and AI in Games*, 4(2), 120–143.
- Gao, L., Madaan, A., Zhou, S., Alon, U., Liu, P., Yang, Y., Callan, J., & Neubig, G. (2023). PAL: Program-aided Language Models. *ICML 2023*.
- gg-bench (2025). A procedurally generated game benchmark for LLMs. arXiv:2505.07215 (repo: `vivek3141/gg-bench`).
- Hafner, D., Lillicrap, T., Ba, J., & Norouzi, M. (2020). Dream to Control: Learning Behaviors by Latent Imagination. *ICLR 2020*.
- Janner, M., Fu, J., Zhang, M., & Levine, S. (2019). When to Trust Your Model: Model-Based Policy Optimization (MBPO). *NeurIPS 2019*.
- Lambert, N. O., Amos, B., Yadan, O., & Calandra, R. (2020). Objective Mismatch in Model-based Reinforcement Learning. *L4DC 2020*, PMLR 120, 761–770. arXiv:2002.04523.
- Lehrach, W., Hennes, D., Lazaro-Gredilla, M., Lou, X., Wendelken, C., Li, Z., Dedieu, A., Grau-Moya, J., Lanctot, M., Iscen, A., Schultz, J., Chiam, M., Gemp, I., Zielinski, P., Singh, S., & Murphy, K. P. (2025). Code World Models for General Game Playing. arXiv:2510.04542.
- Liang, J., Huang, W., Xia, F., Xu, P., Hausman, K., Ichter, B., Florence, P., & Zeng, A. (2023). Code as Policies: Language Model Programs for Embodied Control. *ICRA 2023*.
- Long, J. R., Sturtevant, N. R., Buro, M., & Furtak, T. (2010). Understanding the Success of Perfect Information Monte Carlo Sampling in Game Tree Search. *AAAI 2010*.
- Ross, S., Gordon, G. J., & Bagnell, J. A. (2011). A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning (DAgger). *AISTATS 2011*, PMLR 15, 627–635.
- Whitehouse, D., Powley, E. J., & Cowling, P. I. (2011). Determinization and Information Set Monte Carlo Tree Search for the Card Game Dou Di Zhu. *IEEE CIG 2011*.
- Zinkevich, M., Johanson, M., Bowling, M., & Piccione, C. (2007). Regret Minimization in Games with Incomplete Information (CFR). *NeurIPS 2007*.

*Bibliographic note: Lehrach et al. (2025) and Lambert et al. (2020) were verified against arXiv; the remaining entries are standard references filled from established venues and warrant a final citation-manager pass before submission. The gg-bench author list is not yet confirmed (cited by arXiv id).*

---

*All figures and tables are sourced from `docs/EXPERIMENTS.md` (runs of 2026-06-24 to 2026-06-27); the two theorems and their proofs are stated in `docs/RESEARCH-DIRECTION.md`. Numbers were cross-checked against EXPERIMENTS.md on 2026-06-27 (Kuhn CI, Beacon 0/8156 and 0.000/0.500, Claim-B observation_rate, deployment strings).*
