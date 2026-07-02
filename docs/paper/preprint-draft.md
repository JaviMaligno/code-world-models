
# When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models

**Author:** Javier Aguilar Martín — AGILabs (javieraguilar.ai)
**Status:** First draft, 2026-06-27. Numbers from `docs/EXPERIMENTS.md` — re-verify against the log before submission.

---

## Abstract

Large language models (LLMs) can synthesize the rules of a game as executable code — a *Code World Model* (CWM) — which a classical planner then searches over. The synthesized model is typically accepted when it reaches high *transition accuracy* on sampled trajectories. We argue that this acceptance criterion is the wrong notion of adequacy for planning.

Our perfect-information existence results are on LLM-synthesized CWMs. We isolate the precise causal magnitude with a hand-instrumented agent that is budget-matched and play-equivalent to the incomplete synthesized CWM; the synthesized runs corroborate the direction. Our imperfect-information results pair an LLM-synthesis pipeline validation (Kuhn poker) with hand-instrumented witnesses that isolate the belief-function failure.

We find four things. (1) An LLM-synthesized CWM can pass a sampling gate at 100% transition accuracy and be ≥99% state-accurate on the distribution the planner actually visits, yet lose systematically at play — because the less than 1% it gets wrong is exactly the pivotal dynamics; the play cost of the omitted rule, isolated with the play-equivalent instrument, is 0.131 (95% CIs separated; seed-clustered 95% CI [0.083, 0.179], n=600). We call this the *verified-vs-correct gap*. (2) The harm from *sampling-gate blindness* follows a quantitative law, `danger = play_cost × (1 − rarity)^N`, where `rarity` is the probability a random play-through triggers the omitted rule and `N` is the gate size (the number of sampled play-throughs the gate checks). This law isolates one channel — the gate failing to *observe* a rule; it does not model the distinct, empirical synthesis-residual channel in which the rule is present in the sample yet the LLM still fails to encode it (finding (3)). The `(1 − rarity)^N` gate-miss factor is *proven exact* (i.i.d. Bernoulli); `play_cost` is measured empirically — with a provable upper bound (the planner's query-hit mass of the error region), a witness-certified lower bound, and an exact, provable value (½) on the Beacon witness. This law predicts when sampling verification is blind: harm is negligible while the rule is common enough for the gate to catch it, rises through a threshold as the rule becomes rare, and saturates at the full `play_cost` once it almost always escapes.

(3) The failure is not repaired by more data. LLM CWM synthesis behaves as *rule translation* rather than *rule inference*: it correctly encodes rules it was given and, across the regimes we tested, did not infer the omitted rule — under the GPT-5.x family (mini and large) and across the §5 data regimes (rules-given, no-rules, naive DAgger, proper DAgger, targeted on-manifold examples), independent of the quantity of on-manifold example transitions. (4) The same mechanism recurs on the *inference* function of imperfect-information CWMs. We prove a coverage bound — a size-N random gate is identifying for the inference function (under a detectability hypothesis) when `N ≳ b^{d_max}` — which explains why shallow games show no inference gap: Kuhn poker is provably covered at the deployed gate, and for Leduc poker the bound certifies the competent-relevant subset of information sets (info-sets) we sampled — not all reachable info-sets, which the deployed gate is too small to guarantee. A companion enumeration-free bound certifies the undetected-error mass of any gate-passing inference function (≤ ln(1/δ)/N under the gate's sampling distribution), extending the certificate to games too large to enumerate. We then hand-construct a minimal witness, Beacon (not a synthesized CWM), that escapes the coverage bound: a verified-but-wrong `infer_states` function passes the inference gate (0/8156 mismatches) yet loses every game (0.000 vs fair baseline 0.500), with the danger law recurring on this new axis.

Taken together, these results suggest that adequacy for LLM-synthesized world models used in planning should be measured on the search distribution or by play directly, not by prediction accuracy on sampled transitions, and that completing the specification is more effective than attempting repair by example.

---

## 1. Introduction

### 1.1 The Code World Model paradigm

A central observation in recent work on LLMs for game playing is that a small language model plus a well-specified world model plus classical search can outperform a much larger model used as a direct policy. The *Code World Model* (CWM) paradigm makes this concrete: an LLM is prompted with a game's rules and some sampled trajectories and asked to synthesize a fully executable implementation of the game's transition dynamics. A classical planner — typically Monte Carlo Tree Search (MCTS) — then searches over the synthesized world model, interacts with a referee (the true game), and is evaluated in an arena.

We reproduce this baseline on tic-tac-toe and Connect Four (§3.1): LLM-synthesized CWMs refined to transition accuracy 1.0 and paired with UCT-MCTS dominate the same LLM used as a direct policy by wide margins (e.g., 29–1 in Connect Four), reproducing the direction of the result in Lehrach et al. (2025) on known games. Synthesis is trivially cheap: total API cost across all runs in this paper is approximately $2, with roughly $0.001–0.005 per arena game for the LLM-as-policy baseline and synthesis a one-off cost.

### 1.2 The implicit trust step

Accepting a synthesized world model involves a gatekeeping step: the CWM is refined in a sandbox until it achieves transition accuracy 1.0 on a set of randomly sampled trajectories. This gate is computationally cheap and is the only barrier between synthesis and deployment in the planner.

Our central question is: **does passing this gate certify that the CWM is adequate for planning?**

The concern is structural — it arises from the setup itself, not from any particular model or random draw (Figure 1). A planner does not play randomly — it concentrates search on states it deems strategically significant. If the random-trajectory gate and the planner's search distribution diverge systematically, there could exist a CWM that passes the gate yet is wrong precisely on the states that matter for competent play. We call this the *verified-vs-correct gap*.

![The structural diagnosis underlying every gap in this paper](figures/reach_divergence.png)

*Figure 1. The structural diagnosis underlying every gap in this paper, schematically. The verification policy ρ (uniform-random gate) places its mass on shallow, common histories; the deployment policy Π (competent planner) places its mass on deep, rare histories. A rare-but-pivotal region — where an omitted transition rule (§3.3) or a wrong belief function (§6.4) lives — is reached by Π but almost never sampled by ρ, so the gate is structurally blind there. This is the same situation as beliefs about rarely-reached game positions being unconstrained in classical game theory (off-equilibrium-path beliefs in extensive-form games); a sampling gate has no analogous refinement to pin down that region. (Schematic, not data.)*

### 1.3 A first look: when the gate is identifying

Our first experiments, across three game families and two knowledge regimes (rules given / rules withheld), find that the feared gap does not appear on small, fully-specified games (§3.2). Whenever a CWM passes the random-trajectory gate, it is also correct on the MCTS-visited distribution; whenever it is wrong on the search distribution, it also fails the gate. For these games the random sample is *identifying* — no compact wrong hypothesis fits all training trajectories yet diverges elsewhere. This is an honest null result, and we report it as such, because understanding *when* the gate is identifying is necessary to understand when it is not.

### 1.4 When the gate fails: rare rules and the danger law

The null result on small games points to the condition under which the gate can be fooled: a rule that random play almost never triggers but competent play reliably seeks out. We engineered a minimal instrument satisfying this condition (§3.3): a variant of the game army5x5a augmented with a *material-at-cap* tiebreak rule whose material-terminal rarity under random play is 2.5% (the rate at which the rule decides the game) yet which decides roughly 50% of competent games.

A CWM that omits this rule passes the gate at transition accuracy 1.0 and is ≥99% state-accurate on the search distribution, yet loses approximately 2:1 in play (win rate 0.376 [0.338, 0.415] vs fair baseline 0.507 [0.467, 0.547], Wilson 95% intervals, n=600). State accuracy is blind to the omission (_dilution_: the handful of wrong states is averaged into a large pool of correct ones, so the aggregate barely moves); play is not.

We then quantify when this can happen via a law that relates harm to gate size and rule rarity (§4), and show that the gap cannot be repaired by providing more example transitions (§5).

### 1.5 Extension to imperfect information

The same mechanism appears on the *inference* half of an imperfect-information CWM. Such a model must also implement an `infer_states` function — given a sequence of observations, reconstruct the set of possible hidden states — and this function is gated separately. We prove (§6) that the inference gate is identifying when the game is shallow enough, explain why poker games fall below this threshold, and construct a minimal game (Beacon) in which a verified-but-wrong `infer_states` passes the inference gate yet loses every game.

### 1.6 Contributions

This paper makes six contributions. The first three establish the perfect-information story — the gap, the quantitative law that governs it, and why it cannot be repaired by example — and the last three carry the same mechanism onto imperfect-information CWMs and unify the two halves of the contract:

1. **The verified-vs-correct gap (§3.3):** A gate-passing, ≥99%-state-accurate CWM that loses ~2:1 in play (win rate 0.376 [0.338, 0.415] vs fair baseline 0.507 [0.467, 0.547], Wilson 95% intervals that do not overlap, n=600). The gap arises from a rare-but-pivotal rule omitted from the specification and invisible to random-trajectory sampling. We also document the honest null — small fully-specified games show no gap — which clarifies the boundary conditions.
2. **A quantitative danger law (§4):** `danger = play_cost × (1 − rarity)^N`. The `(1 − rarity)^N` gate-miss factor is proven exact under i.i.d. Bernoulli sampling (Proposition 1); `play_cost` is empirical — but not opaquely so: we prove the upper bound `play_cost` ≤ $\mu_{\mathrm{query}}(E)$, the planner's query-hit mass of the error region (Proposition 2), certify a lower bound by witness (≥ 0.083 at seed-clustered 95%), and prove the exact value ½ on Beacon (Proposition 4), leaving only the exact constant at scale empirical. The law predicts a threshold below which verification is safe and above which harm saturates at the full play cost.
3. **Translation, not inference (§5):** LLM CWM synthesis behaves as rule translation under the tested regimes. Across the two model sizes tested (mini, large) and every data regime we ran (naive DAgger, proper DAgger, targeted on-manifold examples), the omitted rule was not recovered from example transitions. Artificial off-manifold repair data actively corrupts synthesis.
4. **The coverage bound (§6.2, Theorem 1) and Beacon (§6.4):** We prove that a size-N random inference gate is identifying when `N ≳ b^{d_max} · p_chance^{-1} · log|𝓘|` — where `b` is the per-info-set branching factor, `d_max` the maximum player-action depth, `p_chance` the smallest deal probability, and `|𝓘|` the number of reachable info-sets (all defined in §6.2) — which explains the absence of an inference gap in Kuhn and Leduc. We complement it with an enumeration-free certificate (Theorem 2): any gate-passing inference function has undetected-error hit mass ≤ ln(1/δ)/N under the gate's sampling distribution — a bound whose constants involve no enumeration of info-sets, hence apply to games of arbitrary size, at the price of certifying bounded error mass rather than full coverage. We then construct Beacon, the minimal game that escapes the coverage bound (and realizes the reach-ratio blow-up that makes the error-mass certificate's transfer to play vacuous), obtaining 0/8156 gate mismatches alongside 0.000 play win rate.
5. **The belief model is invisible to a transition gate (§6.6):** We prove (Proposition 5) that the information partition encoded by `observation`/`infer_states` appears in no transition tuple, so a transition-accuracy gate cannot detect a wrong belief model. We demonstrate it on masked tic-tac-toe: withholding the masking rule yields a transition-gate-perfect (1.000) but belief-wrong (`observation_rate` 0.020, `inference_rate` 0.180) synthesis, with a synthesized single-seed corroboration on Beacon (transition gate 1.000, `inference_rate` 0.000). With Beacon, this gives both faces of belief-model verification — a wrong belief can lose at play *and* is invisible to a transition gate.
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

This contract mirrors the minimal interface required by UCT-MCTS (Monte Carlo tree search with the UCT — upper confidence bounds applied to trees — selection rule) for perfect-information games and determinized MCTS for imperfect-information games.

### 2.2 Synthesis and the gate

An LLM (Azure OpenAI Global Standard deployments `gpt-5.4`, `gpt-5.4-mini`, `gpt-5-nano`; snapshot `gpt-5.4-2026-03-05`) is prompted with the game's `RULES_TEXT` and a set of random-policy trajectories. The prompt asks the model to synthesize a complete Python module implementing the contract.

The synthesized module is then refined in a sandbox: a referee evaluates the sampled trajectories through both the synthesized CWM and the ground-truth oracle, and any discrepancy produces an error message fed back to the LLM for correction. Unless otherwise stated, refinement re-uses the same trajectory sample each iteration (the synthesis-pipeline study of §5.2 is the exception — there refinement draws a fresh batch each iteration). Refinement continues until the synthesized CWM achieves *transition accuracy 1.0* on the trajectory sample, or until a refinement budget is exhausted. Passing this test we call *passing the gate*.

Transition accuracy is the fraction of (state, action, next-state) tuples from randomly sampled play-throughs on which the synthesized CWM agrees with the ground truth. This is the gate's own lens; §3 and §4 argue it is the wrong lens for play-adequacy.

For imperfect-information games, an analogous *inference gate* measures accuracy on the `infer_states` function over the observations generated by random play.

### 2.3 Planning

For perfect-information games, planning uses UCT-MCTS with a configurable simulation budget (200–600 per move, depending on the experiment; see individual sections). The planner operates entirely on the synthesized CWM and never queries the true game during search; only the arena referee is the true game.

For imperfect-information games, planning uses determinized MCTS: at each decision point, the planner samples a set of possible hidden-state completions from `infer_states`, runs UCT-MCTS on each determinization, and aggregates votes (Cowling et al., 2012; Long et al., 2010). The planner is hardened to tolerate a faulty `infer_states` (raising exceptions, returning empty lists) via a legal-fallback mechanism, ensuring arena runs do not abort when the CWM is deliberately instrumented to be wrong.

Throughout the paper, **competent play** denotes play under the deployed planner $\Pi$ (UCT-MCTS for perfect information, determinized MCTS for imperfect information, at the stated simulation budget). It is a heuristic proxy for skilled play, *not* an equilibrium strategy: "competent" should be read as "what the deployed planner does," never as "optimal." All gap, danger, and reach statements below are made with respect to this deployed-planner distribution unless we explicitly say "equilibrium."

### 2.4 Metrics

We distinguish two families of metrics throughout the paper:

**The gate's lens (prediction accuracy):**

- *Transition accuracy* — agreement rate on (state, action, next-state) under random play.
- *State accuracy* — fraction of states in a distribution where the CWM agrees with the ground truth on all contract outputs. Write $\mathrm{agree}(D)$ for state accuracy measured on distribution $D$; below, $D_\text{gate}$ is the random-trajectory (gate) distribution, $D_\text{cwm}$ the distribution the synthesized CWM's own planner visits, and $D_\text{truth}$ the distribution the ground-truth planner visits.
- *gap* (a.k.a. *gap_cwm*) — $\mathrm{agree}(D_\text{gate}) - \mathrm{agree}(D_\text{cwm})$: how much more the CWM agrees with the truth where it was verified than where it actually plays. This is the quantity the verified-vs-correct gap is about.
- *gap_truth* — $\mathrm{agree}(D_\text{gate}) - \mathrm{agree}(D_\text{truth})$: the same difference but against the *ground-truth* planner's visited distribution rather than the CWM's own.
- *gap_max* — the maximum of *gap* across the synthesis seeds of a condition (its worst-case value, used when we report "gap ≈ 0, gap_max 0.016").
- *observation_rate* — fraction of sampled (state, player) pairs on which the synthesized `observation` returns the ground-truth observation; the discriminator for a correct belief model (§6.6).
- *inference_rate* — fraction of sampled observation histories on which the synthesized `infer_states` returns exactly the ground-truth set of consistent states. For both belief-surface rates, a *crashing* synthesized function is a synthesis-robustness failure, not a wrong belief: execution errors are excluded from the rate denominators and reported separately, so a rate scores only the cases that actually ran (a wrong-but-running output still counts as a mismatch).

**The decision-relevant lens (play performance):**

- *Win rate* — fraction of games won by the CWM+MCTS agent versus a ground-truth+MCTS opponent in an arena refereed by the true game, with Wilson score 95% confidence intervals.

Fairness baselines are established by running truth-vs-truth arenas (ground-truth+MCTS against itself), which should produce win rates near 0.5 for balanced games. Deviations from 0.5 in the fairness baseline indicate start-order imbalance or search-budget asymmetry; we report them alongside each play result.

### 2.5 Experimental configuration

The table below collects the fixed components of the pipeline so the experiments are reproducible from the paper alone; per-experiment quantities (simulation budget, gate size N, game) are stated in each section, and the full harness is in `docs/EXPERIMENTS.md` and the cited scripts.

| Component | Setting |
|---|---|
| Synthesizer LLM | Azure OpenAI `gpt-5.4` / `-mini` / `-nano`, snapshot `gpt-5.4-2026-03-05` |
| Synthesis prompt | `RULES_TEXT` + a set of random-policy trajectories; asks for a full contract module |
| Gate sampler | uniform-random policy (`rng.choice(legal_actions)`), seeded per run |
| Gate criterion | transition accuracy = 1.0 on the sampled (state, action, next-state) tuples |
| Refinement | re-uses the same sample each iteration (fresh batch only in §5); budget ≤ 5 iters |
| Held-out gate | none separate — the training trajectories *are* the gate (§4) |
| Planner (perfect info) | UCT-MCTS, exploration constant c = 1.41 ≈ √2 (see note), uniform-random rollout to terminal |
| Planner (imperfect info) | determinized MCTS (Cowling et al. 2012; Long et al. 2010) with legal-fallback hardening |
| Selection tie-break | first argmax of UCT; move chosen = most-visited child (first on ties) |
| Simulation budget | 200–600 per move (stated per experiment) |
| Arena | start side alternated every game (i mod 2); distinct RNG seeds per agent and arena |
| State accuracy | agreement with ground truth on *all* contract outputs at a state |
| Terminal-legal convention | `legal_actions` on terminal states excluded (planner never queries it) |

*Note on the exploration constant.* We use c = 1.41 ≈ √2, the canonical UCT
value (Kocsis & Szepesvári 2006), as a fixed convention rather than a tuned
hyperparameter — search strength is set by the simulation budget, and the
planner serves only as a reproducible fixed-strength instrument. The √2 constant
is derived for rewards in [0, 1]; our `returns` lie in {−1, 0, +1}, so a strictly
range-calibrated value would be ≈ 2√2. We verified that this does not affect the
reported quantities: across the perfect-information games, c = 1.41 and c = 2√2
yield identical win/draw/loss outcomes against fixed opponents (uniform-random
and, on tic-tac-toe, a perfect minimax solver) at 200–600 simulations, and on
Beacon — the adversarial instrument for the coverage gap — the planner follows an
identical forced line under both constants. Trajectories on the open games
diverge only by selecting among equally-optimal moves, leaving play strength and
gap measurements unchanged, so no re-run with a recalibrated constant is needed.

### 2.6 Games

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

### 2.7 Cost

API synthesis is trivially cheap: approximately $0.043–$0.135 per game family for the known-game runs; roughly $0.81 total for the gap-grid across three games and ten seeds. The CPU bottleneck is MCTS. For the danger law (§4) we exploit the fact that `play_cost` is approximately constant by measuring it precisely once at scale (240 games, 600 simulations) and sweeping `rarity` cheaply (3000 random games per cap setting, no MCTS required). All results and reproduction commands are in `docs/EXPERIMENTS.md`.

---

## 3. The Gap: Accuracy ≠ Play-Adequacy

### 3.1 Known games reproduce the paradigm but do not stress the gate

LLM-synthesized CWMs on tic-tac-toe and Connect Four pass the transition gate in 0 refinement iterations and play at well above baseline performance. For completeness:

| Game         | Synthesizer  | Refinement iters | Transition accuracy | CWM W / D / L | Baseline illegal moves | CWM illegal | Total cost |
| ------------ | ------------ | ---------------- | ------------------- | ------------- | ---------------------- | ----------- | ---------- |
| Tic-tac-toe  | gpt-5.4-mini | 0                | 1.0                 | 18 / 10 / 2   | 6                      | 0           | $0.043     |
| Tic-tac-toe  | gpt-5-nano   | 0                | 1.0                 | 21 / 8 / 1    | 5                      | 0           | $0.043     |
| Connect Four | gpt-5.4-mini | 0                | 1.0                 | 29 / 0 / 1    | 0                      | 0           | $0.135     |
| Connect Four | gpt-5-nano   | 0                | 1.0                 | 30 / 0 / 0    | 2                      | 0           | $0.132     |

(30 games each, seed 7; CWM agent = synthesized model + MCTS; baseline = direct LLM policy.)

The CWM+MCTS agents dominate the direct LLM policy, replicating the paradigm's core claim. That these models reach transition accuracy 1.0 in zero refinements is itself revealing: on well-known games, the model is almost certainly *recalling* the rules rather than inferring them from trajectories. Here "accuracy 1.0 on sampled trajectories" likely coincides with global correctness for the right reason — but that coincidence says nothing about whether the gate is reliable in general.

### 3.2 The state-agreement gap does not appear on small complete-rules games

To measure the gap properly, we ran a grid across three knowledge regimes and two model sizes (5 synthesis seeds each, 20 self-play games, 300 simulations, train-games 40):

| Game          | Regime        | Synth | gap mean | gap max | gate-pass | median refine iters | exec-err |
| ------------- | ------------- | ----- | -------- | ------- | --------- | ------------------- | -------- |
| gen_tictactoe | correct prior | mini  | 0.000    | 0.001   | 5/5       | 0                   | 0        |
| gen_tictactoe | correct prior | nano  | 0.000    | 0.000   | 5/5       | 0                   | 0        |
| army5x5a      | no prior      | mini  | 0.002    | 0.008   | 4/5       | 0                   | 0        |
| army5x5a      | no prior      | nano  | n/a      | n/a     | 0/5       | –                  | 0        |
| trike         | wrong prior   | mini  | 0.000    | 0.000   | 4/5       | 1                   | 0        |
| trike         | wrong prior   | nano  | 0.000    | 0.000   | 5/5       | 0                   | 0        |

We report this as an honest null. In every regime the outcome is binary: either the CWM is correct on every evaluated state (no observed divergence on the gate, search, and truth-search distributions), with gap ≈ 0, or it fails the gate entirely. No CWM passes the gate yet is wrong on the MCTS-visited distribution. The same pattern holds in a `--no-rules` variant (synthesis from trajectories alone, with `RULES_TEXT` withheld): gen_tictactoe passes in 2/5 seeds via recall, with gap 0; army5x5a and Trike fail the gate entirely (0/5).

For the one game small enough to enumerate, gate-passing certifies *global* correctness on reachable states — a *proof*, not just an observation. On tic-tac-toe we synthesize a CWM, confirm it passes the random gate (accuracy 1.0), then check it against the truth over the **entire reachable state space** by breadth-first enumeration (5478 reachable states, 16167 transitions): **zero mismatches on the search-relevant relation** — `legal_actions` on non-terminal states, `apply_action` on every (state, legal action), `is_terminal`, and `returns` (`scripts/exhaustive_verify_tictactoe.py`). (The enumeration also surfaces 880 `legal_actions`-on-terminal-state divergences — the synthesized code omits the `is_terminal` guard — but a planner never queries `legal_actions` on a terminal state, so these are a behaviourally-irrelevant convention artifact, excluded exactly as the gap measurement does.) This is the transition-function analogue of the inference-side *coverage bound* we prove later (§6.2): when the check covers the whole reachable relation, passing it certifies global correctness by exhaustion. For the larger games the reachable space is too large to enumerate cheaply — Trike side-6 alone exceeds 3 million reachable states (measured), and army5x5a and generalized tic-tac-toe 6×6 are far larger — so there the null is a statement about the evaluated distributions, not a proof; consistently, army5x5a (the largest) is the one game with a tiny residual (gap 0.002).

The diagnosis: for small, fully-specified games, the random-trajectory sample *appears identifying on the evaluated distributions* — no compact wrong hypothesis we observed fits 40 random trajectories yet diverges on the search distribution (proven by exhaustion for tic-tac-toe; an empirical statement on the evaluated distributions for the larger games above). The gate is not weak in these regimes; it is identifying. This makes the gap harder, not easier, to construct: we need a game where random and competent play genuinely diverge.

The null is informative in a second way: it shows that the binding constraint on small games is *gate-attainability*, not gap size. nano fails army5x5a outright (0/5 gate passes) because the action encoding (a `from*25+to` integer plus a ply counter) is representationally complex; mini handles it (4/5). The knowledge regime matters less than model scale and encoding complexity — consistent with the translation hypothesis (§5).

### 3.3 The rare-rule instrument: verified but wrong at play (headline result)

The null result on fully-specified games points to the necessary condition for a gap: a rule whose random-play incidence is near zero but whose competent-play incidence is high. We searched for such rules systematically.

**The rarity↔consequence frontier.** We tested six rules across Connect Four and army5x5a (rarity = fraction of random games the rule decides; consequence = performance change between rule-aware and rule-blind MCTS on the true game):

| Base         | Rule                           | Rarity (random) | Consequence |
| ------------ | ------------------------------ | --------------- | ----------- |
| Connect Four | last-placer-on-full-board wins | 0%              | none        |
| Connect Four | corner 4-in-a-row is poison    | 3%              | weak        |
| Connect Four | top-centre fill wins           | 12%             | strong      |
| Connect Four | vertical-3 in centre wins      | 23%             | strong      |
| Connect Four | 2×2 square wins               | 38%             | strong      |
| army5x5a     | infantry breakthrough wins     | 75%             | strong      |

Across our six-rule probe set, the pattern is that anything a planner can force, random play also stumbles into. Connect Four admits no rule in the rare-and-consequential quadrant. A random-vs-MCTS game-length measurement confirms the diagnosis: army5x5a stands out with median game length 23 plies under random play vs 58 plies under competent play (routinely hitting the 100-ply cap), while Trike and generalized tic-tac-toe behave like Connect Four (low divergence). A game where random and competent play visit very different parts of the state space is the necessary substrate.

**The instrument.** We constructed a variant of army5x5a with a *material-at-cap* tiebreak rule: if the game reaches the ply cap (100 plies) with both generals alive, the player with more pieces wins (rather than drawing). Two rates matter and we keep them distinct. The cap is reached in 5.2% of random games (most are equal-material draws the rule leaves unchanged); the rule's **material-terminal rarity** — the rate at which the material-at-cap branch produces a decisive, gate-observable result — is $r = 2.5\%$ (measured over 3000 random games). The danger law (§4) uses this material-terminal rarity. The same rule decides approximately 50% of competent games. Implementations: `groundtruth/gen_chess_material.py` with paired specifications `army5x5a_material` (complete rules) and `army5x5a_material_incomplete` (base rules, omitting the material-at-cap tiebreak).

**State accuracy is the wrong lens for play-adequacy.** A CWM that omits the material-at-cap rule passes the gate (transition accuracy 1.0), and the gap_truth is approximately 0 across all seeds:

| Condition (mini, 5 seeds) | gate-pass | gap_truth | note                                                                                       |
| ------------------------- | --------- | --------- | ------------------------------------------------------------------------------------------ |
| incomplete (omits rule)   | 2–3/5    | 0.000     | seeds that fail the gate do so because the rule appeared in their 40 training trajectories |
| complete (control)        | 5/5       | 0.000     | —                                                                                         |

The gate-passing-but-rule-blind seeds correspond to the event that the rule is *absent* from the $N \approx 40$ training trajectories, which has probability $(1-r)^N$ (Proposition 1, §4). Here the training sample doubles as the gate, so the proposition is instantiated at $N \approx 40$. On this event the sample is consistent with both the rule-bearing and the rule-omitting world model, so by the sample-identifiability argument (§5) the rule is unidentifiable and the rule-blind CWM is admissible. When the rule *does* appear in the sample — probability $1-(1-r)^N$ — synthesis is *not* guaranteed to encode it (§5 shows examples do not reliably teach the rule); the observed seeds are consistent with the same Bernoulli miss mechanism. Here $N$ is the training sample rather than a separate validation gate.

The divergence region (ply-cap states with unequal material) is less than 1% of visited states, and symmetric MCTS self-play tends toward equal material, so the states where the rule-blind CWM is wrong are barely sampled — they are too small a fraction of visited states to move the aggregate state-accuracy number.

**Play performance is the decision-relevant lens.** We report play in two clearly separated panels: a budget-matched, instrumented, CI'd headline (Panel A) and an LLM-synthesized corroboration (Panel B). We deliberately do not pool instrumented and synthesized evidence into one number.

**Panel A — budget-matched, instrumented, CPU-only (the headline causal claim).** Identical budget across arms (n = 600 = 5 seeds × 120 games, 600 simulations), arena refereed by the true game (army5x5a + material-at-cap), measured via `scripts/play_cost_ci.py` / `scripts/play_cost_blind3.py`:

| Arena (true game = army5x5a + material-at-cap) | win rate [Wilson 95%]          |
| ---------------------------------------------- | ------------------------------ |
| truth-vs-truth (fair baseline)                 | **0.507** [0.467, 0.547] |
| rule-blind vs truth (play cost)                | **0.376** [0.338, 0.415] |

(Panel A: budget-matched, instrumented headline. The Wilson 95% intervals do not overlap.)

![The headline play result](figures/headline_play.png)

*Figure 2. The headline result of the Panel A table: a gate-passing, ≥99% state-accurate, rule-blind CWM (right) loses to the fair baseline (left) at play. The Wilson 95% intervals are visibly separated (fair lower bound 0.467 > rule-blind upper bound 0.415), so the 0.131 play cost is not a sampling artifact.*

play_cost = 0.131 (the fair-baseline win rate minus the rule-blind win rate). The Wilson 95% intervals **do not overlap** (fair lower bound 0.467 > rule-blind upper bound 0.415): the two intervals are _CI-separated_ — they share no common value, so the gap is not a sampling artifact. We use "CI-separated" throughout for this non-overlap of 95% confidence intervals.

**Seed-clustered inference (the seed, not the game, as the unit).** The Wilson intervals above pool games and so treat each game as independent. Because games within a seed share a synthesis/instrument draw and an RNG stream, we also report a more conservative analysis that takes the *seed* as the independent unit. The per-seed win rates are rock-steady (table below), and the paired-by-seed difference (which cancels start-side and budget effects, identical across arms) has mean 0.131 with a Student-t 95% interval of [0.083, 0.179] over the five seeds (sd = 0.039, df = 4), **excluding zero**. The clustered interval is wider than the pooled one, as expected with only five clusters, but the effect survives it. (At n=360, the earlier 3-seed subset gave fair 0.493 and rule-blind 0.376; adding two seeds leaves the rule-blind point unchanged and moves the baseline by 0.014, well within the interval.)

| seed                   | 1     | 2     | 3     | 4     | 5     | paired diff. |
| ---------------------- | ----- | ----- | ----- | ----- | ----- | ------------ |
| fair (truth-vs-truth)  | 0.479 | 0.529 | 0.471 | 0.529 | 0.525 | —            |
| rule-blind vs truth    | 0.383 | 0.383 | 0.362 | 0.417 | 0.333 | —            |
| difference (play cost) | 0.096 | 0.146 | 0.108 | 0.112 | 0.192 | **0.131**    |

*Per-seed win rates underlying the seed-clustered interval (120 games/seed). The paired difference has mean 0.131, Student-t 95% CI [0.083, 0.179], excluding zero.*

The rule-blind agent is hand-written base army5x5a. Two distinct equivalences are at work and we keep them separate. (i) Base-vs-truth isolates the *rule's* play cost *by construction*: both arms are exact hand-written games that differ only in the material-at-cap rule, so the contrast is exact at any budget without invoking the LLM. (ii) The bridge to the synthesized pipeline is *empirical*, not proven: base is play-equivalent to the incomplete synthesized CWM only up to the measured gap_cwm ≈ 0 (a tiny residual — gap_max 0.016 on one seed, §3.2), not by a proof of functional equivalence outside the rare region. This is why the headline causal claim rests on an instrumented, budget-matched, CI'd comparison rather than on the synthesized runs, with the synthesized runs corroborating the direction (Panel B).

**Panel B — LLM-synthesized corroboration (Azure, smaller per-seed budget, ranges only).** Reported as ranges, *not* budget-matched, and clearly labeled as corroboration rather than the headline:

| Synthesized CWM (vs truth) | win rate (range across seeds) |
| -------------------------- | ----------------------------- |
| incomplete-rules CWM       | 0.28–0.37                    |
| complete-rules CWM         | 0.38–0.45                    |

These synthesized runs use a smaller per-seed budget (120 games) and are reported as ranges; they corroborate Panel A's direction (incomplete < complete) but are not the basis of the causal claim.

**Summary.** A world model can pass transition-accuracy verification (gate 1.0), be ≥99% state-accurate on the search distribution (gap_truth = 0), and yet lose systematically at play — because the less than 1% it gets wrong is exactly the pivotal tactic. Transition and state accuracy are the wrong adequacy criteria for planning; play performance is the right one.

---

## 4. A Quantitative Law of Sampling-Verification Harm

We now characterize *when* the harm from a sampling gate is large. The key observation is that a gate of N random play-throughs fails to observe a rule that fires with probability r per play-through with exact probability `(1 − r)^N`. We formalize this gate-miss probability and measure the remaining empirical component.

It is worth stating up front exactly which channel of harm this law captures, since the paper documents three and only one is governed by the law. (a) The *gate-miss* channel: the gate never observes the rule, with probability `(1 − r)^N` — proven exact below. (b) The *play-cost* channel: conditional on the rule being absent from the synthesized model, how much a competent opponent can exploit the omission — measured empirically (`play_cost`). The danger law is the product of channels (a) and (b): the gate-miss probability times the play-cost. (c) A distinct *synthesis-residual* channel, which the law does *not* model: even when the rule *does* appear in the gate sample, the LLM may still fail to encode it (§5 shows this is the common case under repair-by-example). The law is therefore a lower bound on total harm under an idealized synthesizer that always encodes what it observes; the synthesis-residual channel is reported separately and empirically.

### 4.1 The gate-miss proposition

**Proposition 1 (gate-miss probability).** *A sampling gate draws N i.i.d. uniform-random play-throughs and accepts the CWM if none of them triggers the rule in question (and so reveals a discrepancy between the CWM and the true game). Since each play-through triggers the rule independently with probability r (the "rarity"), the probability the gate never observes the rule is exactly:*

$$
P(\text{miss}) = (1 - r)^N \approx e^{-Nr}.
$$

*Proof.* Each play-through is a Bernoulli(r) event (rule fires / does not fire), and the N plays are i.i.d. (uniform-random policy is memoryless). The probability all N draws are non-firing is $\prod_{i=1}^{N}(1-r) = (1-r)^N$. ∎

The approximation $e^{-Nr}$ is useful for intuition but the exact expression $(1-r)^N$ is what the table below uses.

**What $N$ counts.** $N$ is the number of *distinct, independent* i.i.d. uniform-random play-throughs the verification pipeline actually draws that could reveal the rule. The proposition is agnostic to which pipeline stage a draw belongs to, but only *fresh* draws count — re-using the same trajectories does not increase $N$. In our synthesis pipeline the draw is a single set of training trajectories that doubles as the gate: refinement re-checks the *same* trajectories (it collects no new games and so contributes nothing to $N$), and we run no separate held-out validation gate. We verified this against the implementation. The numerical instances therefore are: in the §3.2/§3.3 gap grid $N \approx 40$ (the training trajectories *are* the gate, refinement reuses them); Beacon (§6.4) draws a separate gate of $N = 2000$; the danger-curve sweep below reports $N \in \{20, 40, 80\}$.

**Corollary (danger law).** *Let $\kappa = \text{play\_cost}$ be the expected play deficit of a planner whose CWM omits the rule, conditional on the omission surviving the gate. The expected harm from a gate of size N is:*

$$
\text{danger}(N) = \kappa \cdot (1 - r)^N.
$$

The $(1-r)^N$ factor is exact (Proposition 1); $\kappa$ is the empirically-measured, game- and planner-specific consequence magnitude.

**Remark (what stays empirical).** We treat $\kappa = \text{play\_cost}$ as roughly constant across rarity values. This is an empirical regularity, not something the math forces. It holds here because competent MCTS reaches the ply-cap region regardless of how the rarity knob tunes r, so the consequence of omitting the rule is about the same whether the rule is common or rare — as long as it escapes the gate. The invariance therefore depends on the planner consistently reaching the rule region (a property of the game and the search budget), not on anything about the sampling model. "Empirical" is not all-or-nothing, however: an upper bound on `play_cost` is provable in general, its exact value is provable on solvable witnesses, and lower bounds are certifiable by witness — see Proposition 2 and the remark on how much of `play_cost` is provable, below.

**Remark (why play_cost can be measured once: the cheap/expensive split).** The rarity-invariance of $\kappa$ is what lets us measure it just *once* — expensively, with MCTS — and reuse that single value at every rarity, while sweeping rarity *cheaply* with random games (no MCTS). We call this cost-saving the *cheap/expensive split*: rarity is cheap to sweep, `play_cost` is expensive but need only be paid once. A direct measurement shows *why* the two factors separate this way (`scripts/play_cost_reach.py`, MCTS 300 simulations, 40 games per cap; Figure 3). As the cap knob is varied, the probability that *competent* play reaches the cap region stays roughly flat (0.200, 0.200, 0.225 at caps 30 / 60 / 100), whereas the probability that *random* play reaches it falls sharply (0.375, 0.200, 0.075). So `play_cost` rides the knob-insensitive *competent* reach — which is exactly why it is approximately rarity-invariant — while rarity rides the knob-dependent *random* reach. With only 40 games and 300 simulations per point this is a suggestive mechanism, not a proof; `play_cost`-constancy remains an empirical regularity.

![A measured mechanistic correlate of the cheap/expensive split](figures/play_cost_mechanism.png)

*Figure 3. A measured mechanistic correlate of the cheap/expensive split (`scripts/play_cost_reach.py`, 40 games/point, 300 simulations — suggestive, not a proof). Competent (MCTS) reach of the cap region is roughly flat as the cap knob varies, so `play_cost` is approximately rarity-invariant; random reach falls steeply, which is what drives the rarity knob. The two factors of the danger law thus ride two different reach distributions.*

**Remark (reading the two factors, and which reference distribution).** The danger law factorizes cleanly into a *verification-distribution* term and a *play-distribution* term: $(1-r)^N$ is the probability the verification distribution (N i.i.d. uniform-random plays) misses the rule — and $r$ here is a *random*-play rate, measured on the gate's own uniform-random sampling rather than on the planner's distribution — while $\kappa = \text{play\_cost}$ is the consequence measured on the *deployment* distribution, the reach of the deployed planner $\Pi$. The normatively correct reference for play-adequacy is arguably neither of these but *equilibrium / best-response reach*, and under a true equilibrium opponent the play-cost factor could differ: an equilibrium opponent might exploit the rule-blind agent more aggressively, or the omitted rule might sit off the equilibrium path entirely. We therefore keep the hedge "on the distribution the planner actually visits" throughout rather than upgrading to a distribution-free claim, and scope the "≈ constant play_cost" claim to the deployed self-play planner; substituting equilibrium reach for MCTS reach would shift the *numbers* (a rarity- and a play-cost-under-equilibrium, measured against a solver we did not run) but not the *mechanism* — a verified model can be wrong precisely where the reference distribution concentrates and the verification distribution does not. The *inference*-side coverage bound, by contrast, is *equilibrium-robust* (§6.2): there the same full-support property makes the reference-distribution question a strength rather than a caveat.

Although the *exact* value of `play_cost` stays empirical, more of it is provable than the factorization above suggests. We record the provable upper bound here and collect the full picture in the remark below.

**Proposition 2 (play-cost upper bound via query-hit mass).** *Let the true game be $M$ and let $\hat M$ be a deployed model whose contract functions agree with $M$ everywhere except on an error region $E$ (transition queries, or info-sets for the inference function). Fix any planner that is a deterministic function of its model's responses and a random seed, playing against a fixed (possibly stochastic) opponent and referee, and let $W(\cdot)$ be the expected game score of the agent deploying a model (win $=1$, draw $=\tfrac12$, loss $=0$). Let $\mu_{\mathrm{query}}(E)$ be the probability that the agent's search queries its model on $E$ at least once during a game. Then $|W(M) - W(\hat M)| \leq \mu_{\mathrm{query}}(E)$; in particular $\text{play\_cost} = W(M) - W(\hat M) \leq \mu_{\mathrm{query}}(E)$.*

*Proof.* Couple the two deployments on identical seeds (planner, opponent, referee). Until the first time the search queries the model on $E$, every model response is identical in the two runs, hence so is every planner action, every referee transition, and every opponent response — the runs are indistinguishable, so the event "the search queries $E$" has the same probability under both and $\mu_{\mathrm{query}}(E)$ is well defined on the coupled process. On sample paths where the search never queries $E$ the two games are identical and contribute zero to the difference; on the complementary event the score difference is at most 1. Taking expectations gives the bound. Note the relevant distribution is the planner's *query* distribution — MCTS consults its model on imagined states — which dominates the played-trajectory hit distribution: this is the formal counterpart of measuring adequacy on the search distribution. ∎

**Remark (how much of play_cost is provable).** Three fronts, of which only the last has a fundamental wall. *(i) Upper bounds are theorems.* Proposition 2 makes the danger law an end-to-end *upper* bound: $\text{danger} \leq \mu_{\mathrm{query}}(E) \times (1-r)^N$, an inequality with no fitted constant — $(1-r)^N$ is exact and $\mu_{\mathrm{query}}$ is a property of the deployment distribution (measurable, or boundable by the reach-ratio machinery of §6.2). Consistency check on the deployed instrument: competent trajectory reach of the cap region is 0.200–0.225 (Figure 3), a lower bound on $\mu_{\mathrm{query}}$, and the measured `play_cost` = 0.131 [0.083, 0.179] respects it; if queries roughly track trajectory reach, the omitted rule flips the outcome in about two-thirds of the games that reach the region — pivotality, which no upper bound can supply (on Beacon $\mu_{\mathrm{query}}(D) = 1$ and the bound is vacuous while the true cost is $\tfrac12$). *(ii) On solvable witnesses, play_cost is exact.* Beacon's `play_cost` $= \tfrac12$ *exactly* (Proposition 4, §6.4), by exhaustion over its four deals — so on the inference axis the danger law's predictions are fully analytic. *(iii) Lower bounds are certifiable by witness.* A lower bound needs no game-solving: exhibiting an explicit opponent strategy and measuring the deficit is a statistical certificate. Our n=600 measurement is exactly such a witness certificate: `play_cost` ≥ 0.083 at seed-clustered 95% confidence against the truth-planner opponent. What remains empirical at scale is only the *exact* constant, which equals a game-value difference — i.e., solving the game — the play-value analogue of the enumeration/sampling wall of the three-levels remark of §6.2: exact where the game is solvable (Beacon, tic-tac-toe), bounded from above and below everywhere.

### 4.2 Measured danger curve

We measure `play_cost` precisely once (play_cost ≈ 0.13; the headline `play_cost_ci.py` run returns 0.131 at cap=100, n=600, 600 sims, with independent runs corroborating: `play_cost.py` returns 0.117–0.121 at cap=100, n=240, and `law_sweep` returns 0.112 at cap=30) and sweep `rarity` cheaply by varying the ply cap (a lower cap makes the cap-and-equal-material event more common, hence a larger firing rate r; a higher cap makes it rarer). Rarity per cap is measured over 3000 random games. Results (table below, plotted in Figure 4a):

| cap | rarity | (1−r)^40 | danger@N=20 | danger@N=40 | danger@N=80 |
| --: | -----: | --------: | ----------: | ----------: | ----------: |
|  25 |  0.337 |    0.0000 |       0.000 |       0.000 |       0.000 |
|  40 |  0.208 |    0.0001 |       0.001 |       0.000 |       0.000 |
|  60 |  0.107 |    0.0107 |       0.012 |       0.001 |       0.000 |
|  80 |  0.056 |    0.0997 |       0.038 |       0.012 |       0.001 |
| 100 |  0.025 |    0.3583 |       0.072 |       0.043 |       0.015 |
| 120 |  0.011 |    0.6339 |       0.096 |       0.076 |       0.048 |
| 140 |  0.007 |    0.7652 |       0.105 |       0.092 |       0.070 |

*Measured danger curve: a threshold law in rarity. Computed with a round constant play_cost = 0.12 (the headline measurement is 0.131); the threshold shape is insensitive to this choice.*

![The danger law is a threshold in rarity](figures/danger_law.png)

*Figure 4. The danger law `danger = play_cost × (1 − r)^N` is a threshold in rarity, and the same law recurs on both halves of the CWM contract. Solid curves are the analytic law; markers are the measured operating points (the danger-curve table above for panel (a), the inference-axis table of §6.5 for panel (b)). (a) Transition axis (army5x5a + material-at-cap), one curve per gate size N ∈ {20, 40, 80}: larger N pushes the threshold toward rarer rules. The deployed army5x5a instrument (r = 0.025) sits in the danger zone. (b) Inference axis (Beacon), fixed gate N = 2000, swept over the deep-region reach ε = (1/2)^{2T}: harm climbs from ≈ 0 at T = 4 to the full play cost by T ≥ 8. The x-axes are reversed (rarer to the right) so danger rises rightward in both panels.*

The result is a threshold law in rarity. Danger is approximately zero while the rule is common enough for a size-N gate to catch it (cap ≤ 50), rises through a threshold as the rule becomes rare (cap 60–100), and plateaus at approximately the full play_cost once the rule almost always escapes the gate (cap ≥ 120). The gate size N shifts the threshold: larger N pushes it toward rarer rules.

### 4.3 Why Connect Four lies safely below the threshold

Recall the six rules tested across Connect Four and army5x5a (§3.3). All of Connect Four's consequential rules have rarity 0.12–0.38, giving $(1-r)^{40} \approx 0$ — they are caught by even a modest gate. army5x5a's material-at-cap rule at cap=100 has material-terminal rarity 0.025, giving $(1-r)^{40} \approx 0.36$ — deep in the danger zone. The structural reason is the same as before: in Connect Four, any rule a planner can force also appears regularly under random play (the rarity↔consequence tension); in army5x5a, competent play drives the game to the deep-ply-cap region that random play almost never reaches.

---

## 5. Repairing the Gap: Translation, Not Inference

If the gap is caused by a missing rule, can it be repaired by providing example transitions that demonstrate the rule? We ran a systematic set of repair attempts on army5x5a + material-at-cap, synthesized from incomplete rules.

### 5.1 Repair experiments

All conditions use the mini synthesizer unless noted; play winrate is vs the true game, 40 arena games at 400 simulations (30 for the DAgger rows), one synthesis seed per condition; baseline 0.28, fair truth-vs-truth 0.50. Discriminating examples are transitions that involve the material-at-cap rule. "Rule learned" is judged by code inspection (does the synthesized module contain the material-at-cap branch?) cross-checked against play parity with the complete-rules control; it is a binary structural fact about the synthesized code, not a winrate threshold. With one seed and 40 games per condition, each individual winrate carries a wide interval (e.g. 0.28 is Wilson 95% [0.16, 0.43]); the load-bearing signal is therefore not any single cell but the *consistent* no-learn outcome across every repair form together with the clean parity of the complete-rules control — not a precise per-condition effect size.

| Repair attempt                                     | discriminating examples | gate acc                  | rule learned  | winrate                         |
| -------------------------------------------------- | ----------------------- | ------------------------- | ------------- | ------------------------------- |
| none (random trajectories)                         | 0                       | 1.000 (false security)    | no            | 0.28                            |
| naive DAgger (dump competent trajectories)         | ~2                      | 0.9996                    | no            | 0.28                            |
| proper DAgger (flawed model's game path, iterated) | 4–5/round              | 0.993                     | no            | 0.28–0.33                      |
| targeted, artificial states                        | 120                     | mini 0.916 / large 0.004  | no            | mini 0.35 / large 0.05          |
| targeted, real (harvested on-manifold)             | 54                      | mini 0.959 / large 0.959  | no            | mini 0.35 / large 0.42          |
| COMPLETE rules + targeted (control)                | 120                     | 1.000 (0 iters)           | yes           | 0.53                            |

### 5.2 Findings

**Detection works, repair does not.** Verifying on the play/search distribution rather than on random trajectories drops the gate below 1.0, detecting the inadequacy that random-trajectory verification missed. But neither mini nor large can *infer* the missing rule from examples. Even 54 real, on-manifold discriminating transitions with 12 refinement iterations leave the gate at 0.959 and the rule unlearned.

**Spec completeness, not code-writing ability, is what binds.** Given the rule in `RULES_TEXT`, the model encodes it correctly in 0 refinement iterations and plays at parity with the baseline (0.53 ≈ 0.50). The complete-rules control isolates the cause: the limitation is not the synthesizer's code-writing ability but the absence of the rule from the specification.

**Scale helps marginally but not sufficiently — and only where there is signal to help.** The large model (0.42) exceeds mini (0.35) on real on-manifold data, but both remain far below the complete-rules baseline (0.53). The inference ceiling is not a mini-specific artifact: the marginal gain lives in the on-manifold regime, where the discriminating transitions are actually sampled and the task is *generalizing* observed rule-firings into code. In the unsampled regime the scale effect does not merely shrink — it is provably absent (Section 5.3): no model, at any scale, can prefer the correct rule from a sample that carries no evidence for it.

**Off-manifold repair data corrupts synthesis.** Artificial (unreachable) discriminating states cause catastrophic failure in the large model (accuracy collapses to 0.004, win rate 0.05). The synthesizer attempts to fit transitions that cannot arise in real play and damages the parts of the CWM it had already learned correctly.

### 5.3 Sample-identifiability: the provable core of "translation, not inference"

The repair experiments above are empirical and scoped to the GPT-5.x family. They are, however, sitting on top of a result that is *provable and universal* — and stating it does not soften "translation, not inference" but strengthens it, by separating a theorem from a conjecture.

Let a rule $R$ be omitted from the specification (the incomplete-rules / no-rules regime), so the only possible source for it is the trajectory sample. Let the true game's $R$ fire on a set of play-throughs of probability $r$ under the verification (uniform-random) distribution $D$. Write $M_R$ for the world model *with* $R$ and $M_\emptyset$ for the otherwise-identical model *without* $R$; they agree on every transition except those in the rule region. The pipeline draws $N$ i.i.d. play-throughs from $D$ (the training sample, which is also the gate — see "What $N$ counts," §4).

**Proposition 3 (sample-identifiability).** *Condition on the event $\neg E$ that no sampled play-through hits the rule region; $P(\neg E) = (1-r)^N$. On $\neg E$, $M_R$ and $M_\emptyset$ produce identical outputs on every sampled transition, so the sample is observationally equivalent under the two models: any score that is a function of the sample alone (the gate's transition accuracy, a likelihood, a program-search objective) is identical for $M_R$ and $M_\emptyset$. Hence the sample carries no evidence favouring the correct model — the gate cannot distinguish or reject $M_\emptyset$, and any preference for $M_R$ must come from a prior or from the specification, not from the sampled transitions. The omitted rule is in this sense unidentifiable from the sample, and a sample-passing $M_\emptyset$ is admissible.* $\blacksquare$

*Proof.* On $\neg E$ the two models are pointwise equal on every transition the sample contains, so any sample functional (a score computed from the sample) takes the same value on both. Any sample-only score therefore cannot order $M_R$ and $M_\emptyset$; any ordering a procedure imposes is a prior or a tie-break, not evidence carried by the sample. $\blacksquare$

**Corollary (unidentifiability probability = the danger-law gate-miss factor).** The probability that the omitted rule is unidentifiable from the $N$ samples is exactly $(1-r)^N$ — the same factor as the danger law (§4). The danger law is thus an identifiability statement: $\text{danger} = \text{play\_cost} \times P(\text{rule unidentifiable from the } N \text{ samples})$. The gate-passing-but-rule-blind seeds of §3.3 are *consistent with* this event ($\neg E$) — a property of the data rather than necessarily an LLM failure. We did not log per seed whether the rule region appeared. By contrast, in the resampling runs of §5.2 below, the gate accuracy shows the rule often *was* present and was still not learned.

This splits "translation, not inference" cleanly into a provable core and an empirical residual.

- **(a) Provable, universal.** When the rule is absent from the sample (probability $(1-r)^N$), the sample provides no evidence to infer it — for *any* learner; this is a property of the data, not a limitation of LLMs (Proposition 3). The gap-exhibiting seeds in §3.3 are consistent with this event. This part is a theorem.
- **(b) Empirical, LLM-specific.** Even when the rule *is* present in the sample (probability $1-(1-r)^N$), the LLM synthesizer does not reliably encode it: the §5.1 repair battery (proper DAgger, targeted on-manifold examples) supplies discriminating transitions and the rule is still omitted. This is the genuinely LLM-specific, scoped finding — established under the GPT-5.x family (mini, large) across the §5 regimes. Its universal-for-all-models form remains a conjecture.

  We measure (b) directly on the synthesis pipeline (`scripts/danger_synthesis_sweep.py`): synthesizing from the incomplete rules and $N$ true-game trajectories, with refinement drawing **fresh** trajectories each iteration, the fraction of seeds whose CWM is rule-blind is essentially $1$ regardless of $N$ for both model sizes:

  | $N$ (games, initial batch) | mini rule-blind | large rule-blind | initial-batch floor $(1-r)^N$ |
  |-------------|-----------------|------------------|-----------------|
  | 40  | 6/6 = 1.00 | 6/6 = 1.00 | 0.363 |
  | 120 | 6/6 = 1.00 | 6/6 = 1.00 | 0.048 |
  | 200 | 6/6 = 1.00 | 6/6 = 1.00 | 0.006 |

  **On the floor.** Two identifiability floors apply, and they bracket the result. The $(1-r)^N$ column is the *initial-batch* floor — the chance the rule is absent from the first $N$ games. But because refinement draws **fresh** batches each iteration, a run that refines for $k$ iterations is exposed to $\approx N(1+k)$ distinct games, so the *full-pipeline* exposure floor is $\approx (1-r)^{N(1+k)}$, which for the refined seeds (up to $\sim$1400 games at $N=200$, $k=6$) is effectively $0$ — i.e. the rule is present in the pipeline with probability $\approx 1$. The gate accuracy makes this concrete: for the **large** model it sits at $0.00$–$0.13$ across the $N=120$/$200$ seeds, meaning the rule-bearing transitions *are* in the sample (the rule-blind CWM mismatches them, so the gate cannot reach $1.0$), yet after six refinement iterations the CWM is still rule-blind in every seed. So the result is not an instance of the unidentifiability event $\neg E$: the rule is present ($E$ holds) and simply not learned — the pure (b) residual. (mini sometimes reached gate $1.0$, the rule happening to be absent in that run; large's low gate accuracy rules that explanation out.) This also corrects a prior pipeline detail — refinement previously re-used a fixed trajectory set; with fresh resampling the rule had every opportunity to appear and still was not learned.

So "translation, not inference" should be read as the conjunction: **(a)** an omitted rule is unidentifiable from a sample that misses it (provable, universal, exactly the danger-law gate-miss event), and **(b)** even a sample that *contains* it does not reliably teach the LLM (empirical, tested on GPT-5.x mini/large across the §5 regimes). Stating (a) as a theorem strengthens the claim: the part of the failure that looks like an LLM weakness is in fact information-theoretic and binds every possible learner; only the residual (b) is a model-specific finding, and we are explicit that its universal form is conjectural.

### 5.4 Conclusion: translation, not inference

Under the tested regimes, LLM CWM synthesis behaves as *rule translation*: it correctly encodes rules it was given and, across the two model sizes tested (mini, large) and every data regime we ran, did not infer the omitted rule, even when that rule was demonstrated by example transitions. Beneath this empirical finding sits a universal one (§5.3, Proposition 3): when the omitted rule is absent from the sample — probability $(1-r)^N$, the danger-law gate-miss event — no learner can recover it *from those sampled transitions alone*; any recovery must come from a prior or the specification, not from the sample. The actionable implication is that the specification must be complete before synthesis, and that verification on the play distribution detects incompleteness but does not repair it. Feeding example transitions is not a reliable substitute for a complete specification.

---

## 6. Imperfect Information: The Inference Function as a New Failure Surface

The danger law applies not just to the transition function (the CWM's model of how states evolve) but also to the inference function (the CWM's model of how to reconstruct hidden state from observations). We extend the contract, prove a coverage bound that explains when the inference gate is provably safe, and construct a minimal game where it is not.

### 6.1 Pipeline validation: Kuhn poker

Before constructing a gap, we validate the imperfect-information pipeline on Kuhn poker, a well-understood minimal game (3-card deck, 1 betting round per player, net-chip payoff).

| Synth | transition gate              | inference gate (obs / infer)         | CWM-vs-truth play    | fair baseline        |
| ----- | ---------------------------- | ------------------------------------ | -------------------- | -------------------- |
| large | 1.000 (0 iters)              | 1.000 / 1.000                        | 0.470 [0.422, 0.519] | 0.470 [0.422, 0.519] |
| mini  | 1.000 (0 iters)              | 0.500 / 1.000                        | 0.470 [0.422, 0.519] | 0.470 [0.422, 0.519] |

*(The mini row is from a rerun under the corrected contract — see §6.6 for the contract fix; an earlier run under the shadowing-prone contract stalled at gate 0.845 with a crashing `infer_states`.)*

Both model sizes pass the transition gate and synthesize an exact `infer_states` (inference rate 1.000), and both play at parity with the truth-vs-truth baseline — consistent with a near-zero gap, as expected when the model has the game (large recalls Kuhn; mini reconstructs it from the specification). The mini synthesis differs from the ground truth only in an *observation convention*: it places player 2's own hidden card at a different index of the observation vector (observation rate 0.500 — every player-2 observation mismatches by this relabeling), a wrong-but-running convention divergence that leaves play unaffected. An earlier version of this run reported a mini failure (gate stalled at 0.845, `infer_states` crashing with `'list' object is not callable`); that crash traced to a name collision in *our* synthesis contract, not to the model — §6.6 gives the root cause and the fix.

### 6.2 When the inference gate is provably sufficient: a coverage bound

We now formalize when the inference gate, sampled on random play, is *identifying* — that is, when every competent-play-relevant inference error would be caught by the random-trajectory gate.

**Setup.** Consider a finite two-player extensive-form game **with perfect recall**, chance (the deal) and imperfect information. We use the following notation:

- $b$ = maximum, over **player** information sets $I$, of $|A(I)|$ (the number of actions available at $I$), with chance handled separately through $p_{\text{chance}}$;
- $d(I)$ = number of player-action edges on a shortest history reaching information set $I$;
- $d_{\max} = \max_I d(I)$, the maximum such depth;
- $p_{\text{chance}}$ = minimum probability of a deal consistent with any reachable info-set;
- $\mathcal{I}$ = set of reachable info-sets;
- $\pi^\sigma(\cdot)$ = realization (reach) probability of a history or info-set under strategy profile $\sigma$;
- $\text{supp}(\cdot)$ and $\text{reach}(\cdot)$ = the histories, resp. info-sets, given positive probability.

The uniform-random policy $\rho$ plays every legal action with probability $1/|A(I)| \geq 1/b$, and therefore assigns positive probability to every legal action (full support).

**Lemma 1 (full-support inclusion).** *Because $\rho$ assigns positive probability to every legal action, $\text{supp}(\pi^\sigma) \subseteq \text{supp}(\pi^\rho)$ for every profile $\sigma$; equivalently $\text{reach}(\sigma) \subseteq \text{reach}(\rho)$.*

*Proof.* This is the standard fact that a fully-mixed strategy reaches every node reachable under any profile. Reach of an info-set is taken under the actual interactive profile (planner + opponent + chance); chance edges are shared and $\rho$ dominates each player's per-edge contribution ($\rho$-probability $\geq 1/b > 0$ on every player edge), so any history with $\pi^\sigma(h) > 0$ has $\pi^\rho(h) > 0$. ∎

**Lemma 2 (reach lower bound under $\rho$).** *Every reachable info-set $I$ has $\pi^\rho(I) \geq p_{\text{chance}} \cdot b^{-d(I)} \geq p_{\text{chance}} \cdot b^{-d_{\max}}$.*

*Proof.* Take any history $h \in I$. Along $h$ each player edge at info-set $I_t$ has $\rho$-probability $1/|A(I_t)| \geq 1/b$, so the **realization probability** of $I$ (in the sense of von Stengel's (1996) sequence form) satisfies $\pi^\rho(h) = \pi_{\text{chance}}(h) \cdot \prod_t 1/|A(I_t)| \geq p_{\text{chance}} \cdot b^{-d(h)}$, and $\pi^\rho(I) \geq \pi^\rho(h)$. ∎

**Theorem 1 (the inference gate is identifying when $N \gtrsim b^{d_{\max}}$).** *Assume **detectability**: whenever the gate visits an info-set on which `infer_states` errs, its comparison against ground truth at that info-set surfaces the error. Draw $N$ i.i.d. games under $\rho$. The probability that some reachable info-set is never visited is at most $|\mathcal{I}| \cdot \exp(-N \cdot p_{\text{chance}} \cdot b^{-d_{\max}})$ (union bound over info-sets plus Lemma 2). Hence for $N \gtrsim b^{d_{\max}} \cdot p_{\text{chance}}^{-1} \cdot \log |\mathcal{I}|$, the random sample covers every reachable info-set with high probability — and by Lemma 1, every info-set any policy (including a competent planner) relies on. An inference function whose error is confined to reachable info-sets is then detected with high probability under detectability, so no gate-passing inference function can be play-inadequate through a coverage gap.* ∎

Detectability holds for our inference gate by construction: at every visited observation history it compares the synthesized consistent-state set against the ground-truth set elementwise, so any discrepancy at a visited info-set is recorded as a mismatch. It is not automatic for an arbitrary gate — one checking only a coarse summary of `infer_states` could visit an erring info-set without surfacing the error — which is why we state it as a hypothesis.

**Remark (equilibrium-robustness).** The sufficiency direction (coverage ⇒ identifying) does not depend on the reference distribution being MCTS reach. Because $\rho$ has full support, $\text{reach}(\sigma^*) \subseteq \text{reach}(\rho)$ for the Nash / best-response profile $\sigma^*$ exactly as for any other profile (Lemma 1). The bound therefore certifies coverage of every info-set that *equilibrium* play relies on, not merely those the deployed planner happens to visit — a strength rather than a caveat. Substituting equilibrium reach for MCTS reach would change which info-sets count as relevant (and hence the numbers) but not the sufficiency argument.

**Corollary (Kuhn provably covered; Leduc's sampled competent-visited subset covered).** Carrying the exact constants — by enumerating the reachable info-sets and their reach probabilities under uniform-random play (`scripts/coverage_bound_constants.py`) — upgrades Kuhn from an order statement to a provable null, and certifies the *sampled* competent-visited subset of Leduc.

*Kuhn.* Exact enumeration gives $|\mathcal{I}| = 12$ and minimum reach probability $\pi_{\min} = 0.083$, so the tight sufficient sample size is $N_{\text{suff}} = 66$. At the deployed gate $N = 80$, the union-bound upper bound on the coverage-failure probability (computed from the exact reach probabilities) is $0.0028$ — Kuhn is therefore **provably covered**.

*Leduc.* Exact enumeration gives $|\mathcal{I}| = 576$ and $\pi_{\min} = 3.5 \times 10^{-4}$. The worst-case-depth bound needs $N \approx 7.4\text{M}$ and even the tight $\pi_{\min}$ bound needs $N \approx 27\text{k}$, so the theorem does **not** certify full coverage of all 576 reachable info-sets at the deployed $N = 8000$ — we say so honestly. However, our coverage claim concerns *only* the info-sets a competent planner relies on. We *sample* that subset with 200 determinized-MCTS self-play games (`scripts/coverage_competent_leduc.py`) — this enumerates the competent-visited info-sets we observed, not provably the entire competent support. The 146 sampled competent-visited info-sets have $\pi_{\min} = 6.9 \times 10^{-4}$, and at $N = 8000$ the union-bound upper bound on the coverage-failure probability over this subset (computed from exact random-reach probabilities) is $0.027 < 0.05$. So the **sampled** competent-visited subset is covered with high probability; combined with the measurement (0/1259 competent inference-relevant visits land on info-sets random play missed), this upgrades "empirically covered" to "covered under exact random-reach probabilities on the sampled competent-relevant subset" — short of a guarantee over the full competent support, which would require enumerating it.

**An enumeration-free companion certificate: bounding the error mass.** Theorem 1 certifies the strongest possible conclusion — every reachable info-set is visited, so *any* error pattern confined to reachable info-sets is caught — but instantiating its constants requires enumerating $\mathcal{I}$ and the exact reach probabilities. That is feasible for Kuhn and Leduc (the corollary above) and intractable in general; indeed the Leduc guarantee already stops at the *sampled* competent subset precisely because the full competent support would have to be enumerated. We therefore add a companion certificate that trades conclusion strength for generality: it certifies not that every info-set was visited, but that the *undetected error region of the accepted artifact has small sampling mass*. Its constants involve no enumeration — no $|\mathcal{I}|$, no $\pi_{\min}$, no reach probabilities — so it applies verbatim to games of arbitrary size. The two results answer different questions and neither subsumes the other (see the remark below); we keep both.

Fix a candidate inference function $f$ and let $E_f \subseteq \mathcal{I}$ be the set of reachable info-sets on which $f$ errs. For a per-game sampling distribution $\nu$ (a policy profile, or a mixture of profiles resampled per game), write $\mu_\nu(E) = \Pr_{\text{game} \sim \nu}[\text{the game visits at least one info-set of } E]$ for the per-game *hit probability* of $E \subseteq \mathcal{I}$. Let $\bar d$ denote the *player-move horizon* — the maximum number of player-action edges on any complete history — so $\bar d \geq d_{\max}$, with equality for Kuhn and Leduc ($\bar d = 3$ and $8$).

**Theorem 2 (enumeration-free error-mass bound).** *Assume detectability, and let the gate draw $N$ i.i.d. games from $\nu$ and check every visited info-set. (i) (Held-out gate.) If $f$ is fixed before the gate sample is drawn, then for any $\delta \in (0,1)$, with confidence $1-\delta$: if $f$ passes the gate, $\mu_\nu(E_f) \leq \ln(1/\delta)/N$. (ii) (Class-uniform / Occam.) If $f$ may instead depend on the gate sample — as in a pipeline whose training trajectories double as the gate — but is guaranteed to be a program of description length at most $\ell$ bits, then with confidence $1-\delta$, simultaneously every gate-passing program of length $\leq \ell$ satisfies $\mu_\nu(E_f) \leq ((\ell+1)\ln 2 + \ln(1/\delta))/N$.*

*Proof.* (i) If $\mu_\nu(E_f) > \varepsilon$, the probability that none of the $N$ games visits $E_f$ is $(1 - \mu_\nu(E_f))^N < e^{-\varepsilon N}$; under detectability any visit to $E_f$ surfaces a mismatch, so $e^{-\varepsilon N}$ upper-bounds the probability that $f$ passes. Setting $\varepsilon = \ln(1/\delta)/N$ makes this $\leq \delta$. (ii) There are fewer than $2^{\ell+1}$ binary programs of length $\leq \ell$; a union bound over the class multiplies the failure probability by $2^{\ell+1}$, and $2^{\ell+1} e^{-\varepsilon N} \leq \delta$ at $\varepsilon = ((\ell+1)\ln 2 + \ln(1/\delta))/N$. Sample-dependent selection is covered because the guarantee holds simultaneously over the class. Neither argument touches $|\mathcal{I}|$ or any reach probability. ∎

**Corollary (transfer to play: the reach ratio).** *Let $E \subseteq \mathcal{I}$ and let $\sigma$ be **any** strategy profile. (i) (Pure-random gate, $\nu = \rho$.) $\mu_\sigma(E) \leq b^{\bar d} \cdot \mu_\rho(E)$; combined with Theorem 2(i), any gate-passing $f$ has $\mu_\sigma(E_f) \leq b^{\bar d} \ln(1/\delta)/N$. (ii) (Mixture gate.) If each gate game is drawn from $\rho$ with probability $1-\lambda$ and from a reference competent profile $\hat\sigma$ (e.g. determinized-MCTS self-play on the ground truth, which the harness owns at gate time) with probability $\lambda$, then any gate-passing $f$ has $\mu_{\hat\sigma}(E_f) \leq \ln(1/\delta)/(\lambda N)$, while for arbitrary $\sigma$ the bound $\mu_\sigma(E_f) \leq b^{\bar d} \ln(1/\delta)/((1-\lambda)N)$ is retained through the $\rho$ component (full support is preserved, so Lemma 1 and the equilibrium-robustness remark survive). In the danger-law reading, any play harm mediated by consulting $f$ on an erring info-set obeys $\text{danger} \leq \text{play\_cost} \times \mu_\sigma(E_f)$ with $\sigma$ the deployment profile.*

*Proof.* (i) Let $H_E$ be the set of minimal histories entering $E$ (no proper prefix visits $E$); $H_E$ is prefix-free, so $\mu_\sigma(E) = \sum_{h \in H_E} \pi^\sigma(h)$. For each $h$, chance edges are shared and every player edge has $\sigma$-probability $\leq 1$ and $\rho$-probability $\geq 1/b$, so $\pi^\sigma(h) \leq b^{d(h)} \pi^\rho(h) \leq b^{\bar d} \pi^\rho(h)$; summing gives the claim. (ii) $\mu_\nu = (1-\lambda)\mu_\rho + \lambda\mu_{\hat\sigma}$, so $\mu_\nu \leq \ln(1/\delta)/N$ implies both $\mu_{\hat\sigma} \leq \ln(1/\delta)/(\lambda N)$ and $\mu_\rho \leq \ln(1/\delta)/((1-\lambda)N)$; apply (i) to the latter. ∎

**Corollary (constants without enumeration).** Instantiating at $\delta = 0.05$ (`scripts/error_mass_certificate.py`; the only game-dependent inputs are the rule-level constants $b$ and $\bar d$):

*Kuhn* ($N = 80$, $b = 2$, $\bar d = 3$): any gate-passing `infer_states` fixed before the gate has undetected-error hit mass $\mu_\rho(E_f) \leq 0.037$, and $\mu_\sigma(E_f) \leq 8 \times 0.037 = 0.30$ for every profile $\sigma$. This is strictly weaker than the enumerative corollary (which certifies *full coverage* at $N = 80$) — where enumeration is feasible, Theorem 1 remains the sharper tool.

*Leduc* ($N = 8000$, $b = 3$, $\bar d = 8$): $\mu_\rho(E_f) \leq 3.7 \times 10^{-4}$, but the worst-case transfer factor $b^{\bar d} = 6561$ makes the any-profile bound vacuous — consistent with Theorem 1 declining to certify Leduc at this $N$. The mixture gate is what the enumeration route could not provide: at the same $N = 8000$ with $\lambda = 1/2$, any gate-passing $f$ has $\mu_{\hat\sigma}(E_f) \leq 7.5 \times 10^{-4}$ — a certificate for the competent-play-relevant error mass with *no* enumeration of the competent support, where the enumerative route needed $N \approx 27\text{k}$ even for the random-reach guarantee and could only certify the *sampled* competent subset.

**Remark (relation between the two certificates).** Neither result subsumes the other. Theorem 1 is a *for-all* guarantee: once the sample covers $\mathcal{I}$, every error pattern confined to reachable info-sets is caught, including one chosen adversarially after the sample; its price is constants ($\pi_{\min}^{-1}\log|\mathcal{I}|$) that must be computed by enumeration and grow with the game. Theorem 2 certifies only the accepted artifact (or a description-length class), and always leaves an $\varepsilon$-mass of undetected error; its price is a hypothesis about how $f$ was chosen — but its constants are game-size-free. In practice: use the coverage route where enumeration is feasible (Kuhn: provably covered, a conclusion Theorem 2 cannot reach at any $N$), and the error-mass route everywhere else. On the choice of hypothesis in Theorem 2: for kB-scale synthesized artifacts ($\ell \sim 10^4$ bits) the class-uniform constant requires $N \gtrsim \ell$, exceeding every gate deployed in this paper, so the practical reading is (i) — draw the gate sample *after* synthesis (a held-out gate), which is cheap since the harness owns the reference implementation. This is also consonant with §5.3: when the training sample doubles as the gate, a compact wrong hypothesis consistent with the whole sample is exactly the case that the fixed-candidate argument does not exclude.

**Remark (tightness: Beacon realizes the reach ratio).** The $b^{\bar d}$ transfer factor in the reach-ratio corollary is not slack in the analysis. In Beacon (§6.4), the deep region $D$ has $\mu_\rho(D) = (1/2)^{2T}$ while optimal play reaches it with probability 1 — the reach ratio $2^{2T}$ is realized, matching $b^{\bar d}$ up to the guess rounds. So for a pure-random gate the exponential transfer factor is unavoidable, and the mixture instantiation of the corollary is the only lever that removes it — which is precisely this paper's recommendation to verify on the search distribution, now in certificate form. The mixture certifies the reference profile $\hat\sigma$ at cost $1/\lambda$; a guarantee uniform over *all* competent policies still pays $b^{\bar d}$ through the $\rho$ component, and Beacon shows this too cannot be improved.

**Design corollary (when a gap is possible).** A coverage gap requires $b^{d_{\max}} \gg N$ at feasible $N$ — large branching and/or large depth — with a competent policy that concentrates reach on a deep region of $\rho$-measure $\ll 1/N$. In game-theoretic terms, the gap lives on info-sets reached with negligible probability under the **sampling policy** but on-path under **optimal play** — off-equilibrium-path-style info-sets that the verification distribution does not constrain (it places negligible sampling mass there, so errors there go unpenalized). This is the imperfect-information analogue of the rare-rule condition: a region that random play almost never samples but competent play reliably visits. Theorem 2 makes the requirement quantitative: a gate-passing artifact's error region has sampling hit mass $\leq \ln(1/\delta)/N$, so a gap requires the deployment policy to concentrate constant hit probability on a region of sampling hit mass below $\ln(1/\delta)/N$ — a realized reach ratio $\gtrsim N$.

**Remark (three levels of conclusion, and where enumeration actually matters).** Summarizing this subsection, it helps to separate three levels of guarantee, because "requires enumeration" and "requires infeasible $N$" are different obstacles and only one of them is fundamental. *(1) Per-artifact guarantees* — is *this* accepted inference function safe to deploy? Theorem 2 answers this definitively for games of arbitrary size with no enumeration: undetected error mass $\leq \ln(1/\delta)/N$ under the gate's sampling distribution, and $\leq \ln(1/\delta)/(\lambda N)$ under the competent reference profile with a mixture gate. Operationally, this is the question that matters at deployment time. *(2) For-all-error-pattern guarantees* (coverage, Theorem 1) — *no* artifact erring on reachable info-sets can pass. Instantiating the constants requires enumeration, but enumeration is not the binding obstacle: Leduc enumerates easily ($|\mathcal{I}| = 576$) yet the *sampling* cost $N \gtrsim \pi_{\min}^{-1}\log|\mathcal{I}|$ already exceeds the deployed gate. For large games this level is out of reach at feasible $N$ even if enumeration were free. *(3) Guarantees uniform over all competent policies in deep games* — unattainable at feasible $N$ for *any* sampling gate, with or without enumeration: Beacon realizes the reach ratio, so the impossibility is itself a theorem, proved without enumeration. Net: enumeration buys sharper constants where it is feasible (Kuhn: provably covered) and nothing where it is not; the definitive conclusions available at scale are level (1) (positive, Theorem 2) and level (3) (negative, Beacon), both enumeration-free.

### 6.3 Leduc depth probe: poker depth does not create an inference gap

To confirm that poker cannot supply the necessary depth, we swept Leduc's per-round raise cap to artificially deepen the betting tree:

| raise cap | random info-sets (max depth) | competent info-sets (max depth) | uncovered inference-relevant |
| --------- | ---------------------------- | ------------------------------- | ---------------------------- |
| 2         | 574 (8)                      | 120 (6)                         | 0 / 418 = 0.0000             |
| 4         | 1090 (11)                    | 128 (7)                         | 0 / 400 = 0.0000             |
| 6         | 1210 (12)                    | 127 (9)                         | 5 / 396 = 0.0126             |

A coverage gap appears only at cap 6, and even there it is marginal (1.26% of competent visits, 5 info-sets) — insufficient for a CI-separated play deficit. The mechanism is fundamental: in poker, betting depth comes from aggression, and competent play minimizes aggression. In game-theoretic terms, the deep betting region is **off the equilibrium path**, because equilibrium folds or calls dominated hands rather than raising into them — so the deep region is off-best-response-path, not a region optimal play relies on. Competent info-sets are always a strict subset of the random-covered ones — the opposite of the structure needed for a coverage gap. Poker is the wrong family.

### 6.4 Beacon: a minimal positive imperfect-information gap

A positive gap requires a game where depth comes from *survival*: optimal play reaches a deep region by staying alive, while random play blunders out early. This is the exact imperfect-information analogue of the rare-rule gap in army5x5a, where competent play reaches the ply cap (the deep region) and random play ends much earlier.

**Hand-instrumented vs LLM-synthesized.** It is important to be explicit about which artifacts are which. Beacon (this section) and the masked-tic-tac-toe instrument of §6.6 are **hand-constructed ground-truth oracles carrying a deliberately wrong belief function** — formal counterexamples (witnesses), not LLM-synthesized world models. The LLM-synthesis evidence on the imperfect-information surface lives elsewhere: the Kuhn pipeline validation (§6.1), where the dynamics *and* the inference function are synthesized and gate-passed, and the masked-tic-tac-toe probe (§6.6), where the **dynamics** are synthesized. Beacon's belief function is never synthesized; it is an instrument we wrote by hand to prove the coverage gap can exist with the exact predicted form.

**Game construction.** Beacon is a two-player game with the following structure:

1. *Setup.* Each player is assigned a hidden type (0 or 1) uniformly at random. The game has T rounds.
2. *Survival walk (rounds 1 to T).* Players alternate; on a turn, a player of hidden type $t \in \{0,1\}$ at their own step index $k$ (the number of safe steps they have completed so far) must play the *safe* action $a = (k + t) \mod 2$ — a deterministic function of the mover's own (known) type. Any other action loses immediately. A uniformly-random player survives all T of its steps with probability $(1/2)^T$; a player who knows its type plays safely always and survives with probability 1.
3. *Final round (round T+1).* Each player guesses the opponent's hidden type (inferable from the opponent's observed moves; see below). Each scores 1 if its guess matches the opponent's type and 0 otherwise; the higher score wins and equal scores draw — so the round is a draw whenever the two guesses are *both* correct or *both* wrong, and is decided only when exactly one player is right.

The region "game reaches the final round" is called D (the deep region). Random play reaches D with probability $(1/2)^{2T}$ (both players must survive); optimal play reaches D with probability 1.

**Why the type is inferable, and why the fair baseline is a draw.** The safe action is a deterministic, invertible function of the mover's type, so a single observed move reveals it: a type-$t$ player who moved at step index $k$ played $a = (k + t) \mod 2$, hence $t = (a - k) \mod 2$. The belief is genuinely ambiguous only before a player's first move (support $\{0,1\}$) and collapses to a singleton the instant one move is seen; since D is reached only after both players complete $T \ge 1$ safe steps, at D each type is *always* pinned down, and a planner with the correct `infer_states` guesses right with probability 1. Two consequences are central to reading the numbers. *(i) Both-right and both-wrong both draw.* Scoring is comparative (higher number of correct guesses wins), so correct inference on *both* sides yields a 1–1 outcome — a draw — which is why the fair truth-vs-truth baseline scores 0.500 (*all draws*, not "wins half"); the symmetric 0–0 outcome is likewise a draw but never arises, since the fair arm has both sides correct and the instrument arm corrupts only one. *(ii) The draw baseline is the cleanest possible control, not a weakness.* Because symmetric correct inference is an *exact* draw, the game carries no structural, positional, or first-mover edge to disentangle from the inference effect; corrupting exactly one player's belief on D breaks the symmetry into a decisive 1–0 (the flipped side scores 0, the correct side scores 1 and wins every reached-final game), so the entire measured deficit 0.500 → 0.000 is attributable to the flipped `infer_states` alone. Had the baseline had a structural winner, one would have to subtract that edge to isolate the inference cost; the draw makes that subtraction trivially zero. (Corrupting *both* sides would restore the 0–0 draw — but that is not the experiment; it would merely pit two equally-wrong beliefs against each other.)

**The instrument.** A CWM whose `infer_states` is *correct* except that it flips the inferred opponent type at final-round states (`status == 1`) — wrong only on D. Random play almost never samples D, so the inference gate almost never sees the error. The correct inference function enables the determinized MCTS planner to make the right guess; the flipped inference function causes the planner to guess wrong.

**Beacon as a signaling game.** Beacon is naturally read as a Bayesian (signaling) game: Nature draws each player a type $\theta_i \in \{0,1\}$; the survival walk emits type-correlated signals (the safe move depends on the type); and the final guess is a belief-dependent action. The correct `infer_states` is the Bayesian posterior support $\mu(\theta_{-i} \mid \text{observed actions})$ over the opponent's type, while the flipped instrument encodes a wrong, non-Bayesian belief. An `infer_states` error is thus a non-Bayesian belief, and under it the planner's final action is no longer a best response to the true type distribution. This connects directly to *sequential equilibrium* (Kreps & Wilson, 1982): an assessment is a (strategy, belief) pair whose beliefs are Bayes-consistent on the equilibrium path, and an action optimal against wrong beliefs is part of no sequential equilibrium. The gate certifies the strategy component of the assessment while leaving the belief component unconstrained *off* the random-reach path — exactly the off-path region where Beacon's error lives. Two qualifications keep the picture honest: `infer_states` returns a *set-valued* belief (the support / info-set), and determinized MCTS then imposes its own weighting over that set — so even a correct `infer_states` leaves the belief *weights* to the planner.

**Why the result is planner-robust.** One might worry that the Beacon result is an artifact of determinized MCTS being a weak planner. The PIMC error decomposition (Long et al., 2010) shows the opposite. Beacon's decisive move is a pure *disambiguation* task, and determinization is weakest exactly when disambiguation dominates; but here a correct posterior makes the optimal guess deterministic, so determinized MCTS with a *correct* `infer_states` recovers the optimal action despite strategy fusion, while with the *flipped* `infer_states` it is forced to the wrong action. The result is therefore not an artifact of planner suboptimality — if anything, Beacon is the cleanest possible setting for a determinization planner to succeed in.

**Result (T=8, GATE_GAMES=2000, arena N=400×3 seeds, 100 simulations, 2 determinizations):**

| metric                                                | value                                           |
| ----------------------------------------------------- | ----------------------------------------------- |
| random reaches final round                            | 0.00000                                         |
| instrument inference mismatches on random gate sample | **0 / 8156** (passes the gate)            |
| fair baseline (truth vs truth) win rate               | 0.500 [0.472, 0.528] (all draws)                |
| instrument win rate vs truth                          | **0.000 [0.000, 0.003]**, net −1200/1200 |

The instrument passes the inference gate perfectly — 0 mismatches on 8156 sampled observations — yet loses every game. This is the imperfect-information analogue of the rare-rule gap: a verified-but-wrong inference function that is nonetheless play-inadequate.

What is proven vs measured: the reach bound $(1/2)^{2T}$, the fact that optimal play reaches D with probability 1, and the logical implication that flipping the inference on D causes the planner to guess wrong are all analytic properties of the Beacon construction. The 0/8156 gate mismatch count is measured. The play side, previously only measured, is in fact *exact*:

**Proposition 4 (Beacon's play cost is exact).** *In Beacon with any $T \geq 1$, consider agents that (a) play the safe walk action derived from their own (observed) type and (b) in the final round guess the opponent type returned by their model's `infer_states`. Then deploying the truth against the truth draws **every** deal (fair win rate exactly ½, counting draws as ½), and deploying the flipped instrument on either seat against the truth loses **every** deal (win rate exactly 0). Hence `play_cost` = ½ exactly.*

*Proof.* By exhaustion over the four equally-likely type assignments and both seatings — eight deterministic games, checked mechanically against the implementation by `scripts/play_cost_exact_beacon.py`. The argument each check instantiates: under (a) both players survive, so every game reaches D. At D each player has observed $T \geq 1$ opponent moves, so the true posterior is the singleton {true type} (invertibility of the safe map); the truth's guess is therefore correct with probability 1 while the instrument's, flipped on D, is wrong with probability 1. Truth-vs-truth scores 1–1: a draw, every deal. Instrument-vs-truth scores 0–1: the instrument seat loses, every deal. ∎

The proposition lives at the belief→guess abstraction (any planner satisfying (a)–(b)); that determinized MCTS realizes (a)–(b) is the planner-conversion fact noted above (verified by whole-branch code review, and re-verified by the same script driving the eight games with the actual determinized-MCTS policy, which reproduces all-draws / all-losses). The measured 0.000 [0.000, 0.003] over n = 1200 arena games is thus the confirmation of a theorem rather than a standalone estimate.

*Caveat.* Beacon is a minimal, strategically trivial witness. Its purpose is to prove that the coverage gap can exist and can have the exact form predicted by the coverage-bound design corollary, not to model a realistic game. The reach-probability structure is engineered specifically to satisfy $b^{d_{\max}} \gg N$; natural games with this structure would involve hidden information in genuinely complex board games.

### 6.5 The danger law on the inference axis

The danger law from §4 applies directly to the inference gap. Sweeping $T$ (so $\varepsilon = (1/2)^{2T}$, the probability that a random game reaches D) against a fixed gate $N = 2000$ and $\text{play\_cost} = 0.5$ (table below, plotted in Figure 4b). Since `play_cost` = ½ is exact on Beacon (Proposition 4) and the gate-miss factor is exact (Proposition 1), both factors of the law are analytic on this axis — the danger column below is a theorem, not a fit:

| T  | ε          | gate-miss$(1−ε)^N$ | danger |
| -- | ----------- | ---------------------- | ------ |
| 4  | 3.9×10⁻³ | 0.000                  | 0.000  |
| 6  | 2.4×10⁻⁴ | 0.614                  | 0.307  |
| 8  | 1.5×10⁻⁵ | 0.970                  | 0.485  |
| 10 | 9.5×10⁻⁷ | 0.998                  | 0.499  |

At T=4, the deep region is frequent enough that a gate of N=2000 catches the inference error (danger ≈ 0); by T ≥ 8, the gate is blind and harm saturates near play_cost (≈0.5; danger T=10 = 0.499) — the maximum possible given the game structure. The same threshold law and the same $(1−\varepsilon)^N$ factor, now instantiated on the inference half of the contract (Figure 4b shows it tracing the identical threshold as the transition axis in panel (a)).

### 6.6 The gate-blindness claim: the belief model is invisible to a transition gate

Beacon (§6.4) shows that a verified-but-wrong belief model *can lose at play* — the **play claim** (a witnessed existence result: in Beacon, decisively, with a 0.000 win rate at 0/8156 gate mismatches). The complementary verification question is whether a transition-accuracy gate could have *caught* the wrong belief model in the first place. It cannot, and for a structural reason: the belief model is invisible to a transition gate — the **gate-blindness claim** this section establishes.

**Proposition 5 (belief–transition orthogonality).** A transition dataset is a set of tuples $(s, a, s', u)$ over *full* ground-truth states, where $u$ is the reward/utility on the transition. The functions `observation(s, p)` and `infer_states(o, p)` encode the information partition — i.e. which full states player $p$ cannot tell apart (the preimages of the observation map). This partition is a *free primitive* of the extensive-form game, logically independent of the transition kernel $P(s'\mid s,a)$ and the reward $u$ — the analogue of the fact that two POMDPs with identical latent dynamics and rewards but different observation functions are different control problems. It appears in no $(s, a, s', u)$ tuple. Therefore (i) no *full-ground-state* transition dataset constrains the masking convention; (ii) a gate that scores transition accuracy cannot detect an incorrect `observation`/`infer_states`; (iii) the belief model must be specified and is verifiable only by a separate inference gate. (A dataset of observation-to-observation tuples $(o, a, o')$ *would* constrain the partition; ours is full-state by construction.) $\blacksquare$

> *This proposition is definitional rather than derived: because the information partition is not a function of the transition tuple, consequences (i)–(iii) follow immediately from the statement — there is no separate deductive step to discharge, which is why it carries a self-proved square rather than a `proof` block. The masked tic-tac-toe result below is an empirical instantiation of the proposition, not a proof of it.*

**Demonstration (masked tic-tac-toe).** We take standard tic-tac-toe dynamics (which GPT-5.4 synthesizes at transition gate 1.000 by recall) and overlay an arbitrary, non-recallable masking rule: the center cell is hidden from both players (shown as $-1$), even after it is played. We synthesize the contract two ways — with the masking rule present (*full*) and with it removed (*withheld*, leaving tic-tac-toe + an imperfect-information framing that still demands `observation`/`infer_states` but does not say what is hidden) — and gate each on transitions and on inference:

| variant               | transition gate           | observation_rate | inference_rate               |
| --------------------- | ------------------------- | ---------------- | ---------------------------- |
| full rules            | **1.000** (0 iters) | **1.000**  | **1.000**                    |
| withheld masking rule | **1.000**           | **0.020**  | **0.180**                    |

*(Both arms rerun under the corrected contract — see below; the withheld-arm rates are unchanged from the original run, and the full arm's `infer_states` — which previously crashed — is now exact.)*

The transition gate is **1.000 in both arms** — the dynamics are recalled, unaffected by the masking rule, and the gate (which calls only `apply_action`/`legal_actions`/`is_terminal`/`returns`) never invokes the belief functions. With the rule, the model masks the center correctly (`observation_rate` 1.000); without it, the synthesized `observation` does not mask the center (`observation_rate` 0.020) — a wrong belief model that the transition gate nonetheless certifies at 1.000. This is Proposition 5 instantiated: a wrong belief model is invisible to a transition gate.

Both belief-surface metrics now discriminate cleanly: `observation_rate` 1.000 vs 0.020 and `inference_rate` 1.000 vs 0.180. Given the full rules, the model synthesizes an *exact* `infer_states`; with the masking rule withheld, it synthesizes a confidently wrong one. The masked tic-tac-toe experiment therefore establishes two things: (a) the masking/observation rule is not recoverable without being specified, and (b) a transition-accuracy gate is structurally blind to it (transition gate 1.000 in both arms).

**A correction: the recurring `infer_states` crash was our contract's fault, not the model's.** An earlier version of this experiment could not report the inference-rate column cleanly: the synthesized `infer_states` raised `'list' object is not callable` *even with full rules*, recurring across three distinct games (Kuhn-mini, Beacon, masked tic-tac-toe), and we initially read it as a synthesis-robustness failure of the model. The root cause was ours. The synthesis contract prescribed the signature `infer_states(observation, player)` — a parameter named `observation` that *shadows* the contract's own `observation()` function — while the very next contract sentence instructs the model to relate `infer_states` to calls of `observation(s,p)`, inviting exactly the collision that produces this `TypeError`. After renaming the parameter (`obs`) and adding an anti-shadowing note to the contract, we reran all three games: **zero** execution errors (masked tic-tac-toe, Kuhn, Beacon), and the full-rules `infer_states` is exact. We flag this explicitly because the earlier version of the finding attributed to the LLM a fragility that our own prompt induced — a small, concrete instance of the paper's broader theme that the specification, not the model, is often the binding constraint.

**Synthesized corroboration on Beacon (single-seed probe).** The same withheld-rule construction on Beacon (T=6), with real LLM synthesis end-to-end, corroborates gate-blindness on a second game: withholding the revelation rule yields a synthesis that *passes the transition gate at 1.000* (2 refinement iterations) with `inference_rate` **0.000** — a transition-certified, belief-wrong CWM, this time synthesized rather than hand-instrumented. (The full-rules arm of this probe fails the transition gate outright — accuracy 0.456 after 10 iterations; Beacon's revelation dynamics are hard to synthesize — so the probe corroborates the gate-blindness face only, and we report it as a single-seed probe, not a headline result.)

Together, Beacon (the play claim) and masked tic-tac-toe (the gate-blindness claim) are the two faces of belief-model verification: a wrong belief **can lose at play** and is **invisible to a transition gate**.

---

## 7. Related Work

### 7.1 Objective mismatch in model-based reinforcement learning

The closest conceptual antecedent is the *objective mismatch* problem in model-based reinforcement learning identified by Lambert et al. (2020): the prediction accuracy of a learned world model and the downstream control performance of a planner using that model can diverge substantially, because they optimize different objectives. Our work is in the same spirit but differs in setting and mechanism. We work in the LLM-code-synthesis regime (the world model is a synthesized program, not a learned neural model), the verification step is a discrete sampling gate (not a continuous loss), and the failure mode we characterize is a *rule-coverage blind spot* in that gate rather than a model-capacity or distribution-shift issue. We also provide a closed-form danger law and a proof that the gate-miss probability is exact under i.i.d. Bernoulli sampling — not merely an empirical observation.

The broader literature on model-based RL world-model quality (e.g., Dreamer, Hafner et al., 2020; MBPO, Janner et al., 2019) largely focuses on learned continuous-state models where world model error is pervasive rather than localized. Our rare-rule gap is a localized, discrete failure that state-accuracy metrics mask by dilution — a point that may be worth revisiting in continuous settings as well.

### 7.2 Code World Models and LLMs for game playing

The Code World Models for General Game Playing paper (Lehrach et al., 2025) introduces the paradigm we build on: an LLM synthesizes an executable world model from rules and trajectories, which a classical planner (in their case, MCTS) then uses. Their results on a set of novel DeepMind board games show that CWM+MCTS outperforms the direct LLM policy. We reproduce this result on tic-tac-toe and Connect Four (§3.1) and extend the paradigm to ask whether the gate they use — transition accuracy on random trajectories — certifies play-adequacy. Our contribution is essentially a rigorous negative answer to that question, together with the mechanisms that explain it.

Related work on code-as-policy (e.g., Liang et al., 2023; Gao et al., 2023) uses LLMs to synthesize executable plans or robot controllers, typically verified by execution rather than by sampling. The distinction between what the LLM was told and what it can infer is implicit in much of this work but has not, to our knowledge, been studied with a controlled rare-rule instrument.

The gg-bench effort (arXiv:2505.07215) generates novel games procedurally specifically to avoid LLM contamination. Our army5x5a instrument is chosen partly for the same reason (verified non-recall of movesets, §2.6) and the gg-bench approach is an attractive complement for future scaling.

### 7.3 DAgger and dataset aggregation

Our §5 repair experiments are directly inspired by the DAgger framework of Ross et al. (2011): iteratively label, under the oracle, the states visited by the current learned policy, and retrain. In DAgger's original imitation-learning setting, this reduces covariate shift. Our finding — that DAgger fails to teach the rare rule — is consistent with the translation hypothesis: DAgger addresses *distribution mismatch* between training and test, but the bottleneck here is not distribution mismatch. The model receives discriminating examples of the rule; it simply cannot infer the rule from them. This is a different failure mode from the one DAgger was designed to address.

### 7.4 Imperfect-information planning and determinization

Determinized MCTS (also called single-observer MCTS, SOMCTS, or information-set MCTS in some formulations; Cowling et al., 2012; Whitehouse et al., 2011; determinization analysis, Long et al., 2010) resolves imperfect information by sampling a consistent complete-information game at each decision point. It is not game-theoretically optimal — it is subject to the two canonical PIMC pathologies, *strategy fusion* and *non-locality* (Frank & Basin, 1998), and in the vocabulary of Long et al. (2010) its error is governed by leaf correlation, bias, and a disambiguation factor — but it is a practical planner for moderate-sized imperfect-information games. We use it as the planner in §6, holding the planner fixed across conditions (the baseline is truth-vs-truth under the same determinized MCTS) so that the contrast isolates the CWM inference function rather than planner quality.

Two planner choices deserve a head-on discussion, because a reader will expect them.

*Information-set MCTS (ISMCTS).* ISMCTS (Cowling et al., 2012) is the natural CWM-compatible imperfect-information planner most readers would reach for over plain determinization-per-decision. We used determinization-per-decision for simplicity and to reuse the existing perfect-information harness, not because it is preferable. This choice is, if anything, conservative for the Beacon result: Beacon is pure disambiguation, the regime in which ISMCTS most cleanly outperforms determinization, so the gap would be at least as clean — likely cleaner — under ISMCTS.

*Counterfactual regret minimization (CFR).* CFR (Zinkevich et al., 2007) and its variants are the standard for Nash-equilibrium-optimal play in imperfect-information games, and CFR *is* CWM-compatible given our contract: `legal_actions`, `apply_action`, `returns`, `observation`, and `infer_states` together suffice to build the info-set tree and run external-sampling MCCFR. The honest statement is therefore not that CFR is incompatible, but that we did not run an equilibrium solver. Doing so would let us measure the gap against *equilibrium* reach rather than MCTS reach (cf. the "reading the two factors, and which reference distribution" remark in §4.1) — which is precisely the clean version of the experiment, and we frame it as the priority for future work.

### 7.5 Verification, testing, and rare events

The sampling gate at the heart of this paper is, in software-engineering terms, *random property-based testing* of a synthesized world model: it draws random inputs (uniform-random play-throughs) and checks a property (transition agreement with the oracle). Property-based testing in the QuickCheck tradition (Claessen & Hughes, 2000) is exactly this idea, and its classic, well-documented weakness is the one our danger law makes quantitative: randomly generated inputs under-sample rare-but-important corners of the input space unless the generator is biased toward them. Our $(1-r)^N$ gate-miss factor is the closed-form version of that coverage gap for a single rare rule.

Detecting a rule that fires with vanishing probability under random play is a *rare-event detection* problem, and the $(1-r)^N$ miss probability is precisely a rare-event miss. The rare-event-simulation and importance-sampling literature (e.g., Rubinstein & Kroese, *Simulation and the Monte Carlo Method*) is built around the fact that naive Monte Carlo is exponentially inefficient at estimating or surfacing rare events, and that one must tilt the sampling distribution toward the event to detect it efficiently. In our framing, verifying on the play (or equilibrium) distribution rather than the uniform-random one is exactly such a tilt: it concentrates samples on the region competent play reaches, which is where the rare rule matters.

The contrast with *formal verification* and exhaustive *conformance / model-based testing* is instructive. Where formal methods (model checking, exhaustive conformance testing of state machines) certify a property over all reachable states by construction, a sampling gate certifies only over a finite random draw — trading exhaustiveness for the cheapness that makes the CWM paradigm attractive. The coverage hole we characterize is the price of that trade, and it is fundamentally a sampling-certification phenomenon, not present under exhaustive certification. We state this contrast at the level of the area rather than attaching it to specific results.

Finally, the failure has a direct analogue in model-based reinforcement learning as *model exploitation*: a planner optimizing against a learned or synthesized model is driven toward regions where the model is most wrong, because those are where it (incorrectly) predicts the highest return. This is the mechanism behind the objective-mismatch and model-trust discussions in model-based RL (Lambert et al., 2020; the model-trust horizon limits of MBPO, Janner et al., 2019). Our rare-rule gap is a localized, adversarially-reachable instance: the planner does not merely tolerate the model's blind spot, it actively seeks the cap region the verification distribution never disciplines.

---

## 8. Limitations and Honest Assessment

**Single model family.** All synthesis experiments use Azure OpenAI GPT-5.x (mini, nano, large). Whether the translation-not-inference finding generalizes to other LLM families — especially open models or post-training variants with stronger code-reasoning abilities — is untested. The rare-rule instrument (§3.3) is carefully constructed to require true rule inference rather than recall, so we believe the finding is likely to persist at similar scales, but this is a claim rather than a measurement. More pointedly, the translation-not-inference claim is tested on a single model family and a finite set of regimes; the universal form ("no model can infer an omitted rule, regardless of scale") is a *conjecture consistent with our data*, not something established here. Throughout we state the finding as scoped to the GPT-5.x family (mini, large) and the §5 regimes, and use "rule translation" as a mechanism hypothesis consistent with the data rather than a proven universal.

**The rare-rule instrument is engineered.** The material-at-cap rule was selected specifically because it falls in the rare-and-consequential quadrant. We do not claim that all or even most rules in arbitrary games will produce this kind of gap; the rarity↔consequence tension found across our six-rule probe set on Connect Four (§3.3) shows that the gap requires a specific structural condition. The point is that the gap *can* exist and *does* exist in a game where random and competent play diverge — which is itself informative about when the sampling gate is unsafe.

**Pure-Python MCTS limits arena size.** Our MCTS implementation is a pure Python reference. This limits the number of simulations and arena games that are computationally tractable, which in turn limits the tightness of confidence intervals for some conditions. We mitigate this with the cheap/expensive separation in the danger law (§4) — rarity is swept cheaply, play_cost is measured precisely once at scale — and with Kuhn poker's small game size (tight CIs). The headline play result (rule-blind 0.376 [0.338, 0.415] vs fair baseline 0.507 [0.467, 0.547]) is reproducible across seeds, the Wilson 95% intervals do not overlap (n=600), and a seed-clustered paired interval ([0.083, 0.179], the seed as the unit) excludes zero.

**Determinized MCTS is not game-theoretically optimal.** As noted in §7.4, determinized MCTS is subject to strategy fusion and non-locality and is not a Nash-equilibrium strategy. The baseline for the imperfect-information experiments is truth-vs-truth under the same determinized MCTS (not an equilibrium baseline), so the contrast is internally consistent but not a statement about how a game-theoretically optimal player would interact with the gap. Holding the planner $\Pi$ fixed across the two arms is deliberate: any pathology intrinsic to $\Pi$ is present in both arms, so the performance *difference* is attributable to the CWM rather than to the planner. We are careful, though, not to overstate this as a theorem. The "cancellation" is really that the wrong CWM is weakly dominated *in this specific instrument* — by construction in Beacon (proven) and by measurement in army5x5a (0.507 vs 0.376) — not a general guarantee that planner pathologies cancel for arbitrary CWM perturbations; a sufficiently suboptimal planner could in principle let two wrongs cancel. None of the existence claims depends on equilibrium play.

**Beacon is a minimal, strategically trivial witness.** Beacon was designed to satisfy the coverage-bound design corollary in the smallest possible game, not to model a realistic scenario. Its survival-walk structure is artificial. The experiment establishes existence and confirms the danger law on the inference axis; it does not demonstrate that natural imperfect-information games with the same structure produce an equally clean gap. Building such a game (e.g., a partially-observable variant of army5x5a) is a natural next step.

**Scope of the gate-blindness claim.** The masked tic-tac-toe result (§6.6) establishes that a transition gate is blind to a wrong belief model, demonstrated by withholding an *observation* (masking) rule that is genuinely independent of the dynamics. It does not establish the stronger claim that the belief model could never be inferred from any richer, observation-bearing signal — indeed Proposition 5 is explicit that a dataset of observation-to-observation tuples $(o,a,o')$ *would* constrain the information partition. The claim is scoped to *full-ground-state* transition data: such data cannot constrain the belief model (Proposition 5), and withholding the rule yields a wrong, transition-certified belief model. An earlier version of this scope note was narrower still, because a recurring `infer_states` synthesis crash confounded the inference-rate column; that crash traced to a name collision in our own contract and disappeared entirely on rerun after the fix (§6.6), so both `observation_rate` and `inference_rate` now discriminate cleanly.

**Knowledge cutoff and contamination.** GPT-5.4's training cutoff is approximately 2025-08-31, and the army5x5a paper (arXiv:2510.04542) was released 2025-10-06 — after the cutoff — so the game falls outside the training window. We additionally confirmed via a declarative probe that the model does not recall the specific movesets (§2.6), and the gate-attainability difficulty (nano fails 5/5) is further evidence of genuine translation rather than recall. Even so, the "post-cutoff = uncontaminated" argument is not a hard guarantee (cutoff dates are approximate and corpora leak); readers should interpret the "no prior" label as "no detectable recall" rather than "strictly novel."

---

## 9. Conclusion

The central finding of this paper is that transition accuracy on randomly sampled play-throughs is the wrong adequacy criterion for an LLM-synthesized world model used in planning. A model can pass this gate at 100% accuracy and remain ≥99% state-accurate on the distribution the planner actually visits, yet lose systematically at play — because the less than 1% it gets wrong is exactly the pivotal dynamics.

The failure follows a quantitative law: `danger = play_cost × (1 − rarity)^N`. The gate-miss factor is proven exact under i.i.d. Bernoulli sampling; play_cost is empirical. This law identifies the condition under which sampling verification is unsafe: a rule whose random-play incidence is small enough to escape a size-N gate but whose competent-play incidence is high enough to matter.

The gap is not repaired by providing example transitions. Under the tested regimes, LLM CWM synthesis behaves as rule translation: it encodes rules it was given and, across the two model sizes tested (mini, large) and every repair-data form we tried, did not infer the omitted rule. Off-manifold repair data actively corrupts synthesis. The actionable fix is specification completeness plus verification on the play distribution; the latter detects incompleteness but does not repair it.

The same mechanism appears on the inference half of imperfect-information CWMs. We prove a coverage bound that explains why shallow poker games are safe (their inference gate is provably identifying), and construct a minimal game (Beacon) where a verified-but-wrong `infer_states` passes the gate yet loses every game, with the danger law recurring on the inference axis. Perfect-information board games (transition rules, rarity r) and imperfect-information games (inference info-sets, depth T) are the same statement on two faces of the CWM contract. We note again that the imperfect-information *play-loss* witness (Beacon) is hand-instrumented, not an LLM-synthesized CWM; the *gate-blindness* face, however, now has synthesized demonstrations on both masked tic-tac-toe and Beacon (transition-gate-passing, belief-wrong syntheses; §6.6), alongside the perfect-information synthesized-CWM study (§3–§5) and the Kuhn pipeline validation (§6.1).

Underneath both faces is a single structural diagnosis (Figure 1): the gate failure is a *reach-distribution shift* between the verification policy ($\rho$, full support, mass on shallow histories) and the deployment policy ($\Pi$, mass on deep histories). The dangerous events are *on* the deployment-reach path but *off* the verification-reach path. This is structurally the same situation as off-equilibrium-path beliefs being unconstrained in an extensive-form game — which is exactly why game theory developed equilibrium refinements (sequential equilibrium, trembling-hand perfection) to discipline off-path beliefs. A sampling gate has no such refinement: nothing forces the synthesized model to be correct where the verification distribution places negligible mass, even though the deployment distribution relies on precisely that region.

These results suggest two concrete practices. First, verify on the distribution that planning visits — or measure play directly — rather than on randomly sampled transitions. Second, ensure the specification is complete before synthesis; the model will translate what it is given, and gaps in the specification become invisible to sampling-based verification.

---

## Appendix A: Reproducibility

All code is available at <https://github.com/JaviMaligno/code-world-models>. All experimental results and exact reproduction commands are in `docs/EXPERIMENTS.md`, and all code is on the `main` branch (`cwm/` package, `scripts/`). Research narrative and formal theorem statements are in `docs/RESEARCH-DIRECTION.md`. Exact commands for the results introduced in this revision:

```bash
# Headline play-cost with Wilson CIs + seed-clustered interval (§3.3, n=600)
PYTHONPATH=src python scripts/play_cost_ci.py
# Coverage-bound exact constants — Kuhn & Leduc reachable info-sets (§6.2)
PYTHONPATH=src python scripts/coverage_bound_constants.py
# Leduc sampled competent-visited subset coverage (§6.2)
PYTHONPATH=src python scripts/coverage_competent_leduc.py
# Enumeration-free error-mass certificate — Kuhn & Leduc (§6.2)
PYTHONPATH=src python scripts/error_mass_certificate.py
# Beacon exact play_cost by exhaustion + planner check (§6.4)
PYTHONPATH=src python scripts/play_cost_exact_beacon.py
# play_cost mechanism: competent vs random reach-cap by cap knob (§4)
PYTHONPATH=src python scripts/play_cost_reach.py
# Synthesis-pipeline danger curve (§5.2), one model at a time (mini|large|nano)
PYTHONPATH=src python3.12 scripts/danger_synthesis_sweep.py large
```

The danger-curve script requires Azure OpenAI credentials in `.env`; the others are
CPU-only. These revision diagnostic scripts print their results to stdout (some
earlier scripts also write per-run JSON under `results/`, which is git-ignored); the
numbers quoted in this paper are recorded in `docs/EXPERIMENTS.md`.

Key scripts:

- `scripts/nontriviality_sweep.py` — confirms game non-triviality
- `scripts/gap_grid.py` — state-agreement gap across regimes
- `scripts/play_cost.py` — play_cost measurement at scale
- `scripts/law_curve.py` — danger law curve (rarity sweep + cost probes)
- `scripts/repair_spikes/` — DAgger and repair experiments
- `scripts/run_kuhn_validation.py` — imperfect-information pipeline validation
- `scripts/leduc_coverage_diagnostic.py` — Leduc coverage-gap measurement
- `scripts/leduc_depth_probe.py` — Leduc depth sweep
- `scripts/beacon_claimA.py` — Beacon result and danger law sweep
- `scripts/mtt_claimB_probe.py` — masked tic-tac-toe probe (full vs withheld masking)

All runs use the Azure OpenAI Global Standard deployments configured in `.env`. Per-run JSON results are in `results/` (git-ignored). Total API cost across all experiments: approximately $2.

---

## References

- Claessen, K., & Hughes, J. (2000). QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs. *ICFP 2000*, 268–279.
- Cowling, P. I., Powley, E. J., & Whitehouse, D. (2012). Information Set Monte Carlo Tree Search. *IEEE Transactions on Computational Intelligence and AI in Games*, 4(2), 120–143.
- Frank, I., & Basin, D. (1998). Search in games with incomplete information: A case study using Bridge card play. *Artificial Intelligence*, 100(1–2), 87–123.
- Gao, L., Madaan, A., Zhou, S., Alon, U., Liu, P., Yang, Y., Callan, J., & Neubig, G. (2023). PAL: Program-aided Language Models. *ICML 2023*.
- gg-bench (2025). A procedurally generated game benchmark for LLMs. arXiv:2505.07215 (repo: `vivek3141/gg-bench`).
- Hafner, D., Lillicrap, T., Ba, J., & Norouzi, M. (2020). Dream to Control: Learning Behaviors by Latent Imagination. *ICLR 2020*.
- Janner, M., Fu, J., Zhang, M., & Levine, S. (2019). When to Trust Your Model: Model-Based Policy Optimization (MBPO). *NeurIPS 2019*.
- Kreps, D. M., & Wilson, R. (1982). Sequential Equilibria. *Econometrica*, 50(4), 863–894.
- Lambert, N. O., Amos, B., Yadan, O., & Calandra, R. (2020). Objective Mismatch in Model-based Reinforcement Learning. *L4DC 2020*, PMLR 120, 761–770. arXiv:2002.04523.
- Lehrach, W., Hennes, D., Lazaro-Gredilla, M., Lou, X., Wendelken, C., Li, Z., Dedieu, A., Grau-Moya, J., Lanctot, M., Iscen, A., Schultz, J., Chiam, M., Gemp, I., Zielinski, P., Singh, S., & Murphy, K. P. (2025). Code World Models for General Game Playing. arXiv:2510.04542.
- Liang, J., Huang, W., Xia, F., Xu, P., Hausman, K., Ichter, B., Florence, P., & Zeng, A. (2023). Code as Policies: Language Model Programs for Embodied Control. *ICRA 2023*.
- Long, J. R., Sturtevant, N. R., Buro, M., & Furtak, T. (2010). Understanding the Success of Perfect Information Monte Carlo Sampling in Game Tree Search. *AAAI 2010*.
- Ross, S., Gordon, G. J., & Bagnell, J. A. (2011). A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning (DAgger). *AISTATS 2011*, PMLR 15, 627–635.
- Rubinstein, R. Y., & Kroese, D. P. (2017). *Simulation and the Monte Carlo Method* (3rd ed.). Wiley.
- von Stengel, B. (1996). Efficient Computation of Behavior Strategies. *Games and Economic Behavior*, 14(2), 220–246.
- Whitehouse, D., Powley, E. J., & Cowling, P. I. (2011). Determinization and Information Set Monte Carlo Tree Search for the Card Game Dou Di Zhu. *IEEE CIG 2011*.
- Zinkevich, M., Johanson, M., Bowling, M., & Piccione, C. (2007). Regret Minimization in Games with Incomplete Information (CFR). *NeurIPS 2007*.

*Bibliographic note: Lehrach et al. (2025) and Lambert et al. (2020) were verified against arXiv; the remaining entries are standard references filled from established venues and warrant a final citation-manager pass before submission. The gg-bench author list is not yet confirmed (cited by arXiv id).*

---

*All figures and tables are sourced from `docs/EXPERIMENTS.md` (runs of 2026-06-24 to 2026-06-27); the two theorems and their proofs are stated in `docs/RESEARCH-DIRECTION.md`. Numbers were cross-checked against EXPERIMENTS.md on 2026-06-27 (Kuhn CI, Beacon 0/8156 and 0.000/0.500, gate-blindness observation_rate, deployment strings).*
