# When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models

**Authors:** Javier Aguilar (+ TBD)
**Status:** SKELETON / working draft, 2026-06-26. Sections marked ⬜ are gaps awaiting
results; ✅ have data in `docs/EXPERIMENTS.md`. Numbers below are from runs logged
there — re-verify against the log before submission.

---

## Abstract ⬜ (draft)

Large language models can synthesize the rules of a game as executable code — a
*Code World Model* (CWM) — which a classical planner (MCTS) then plays. The
synthesized model is typically accepted when it reaches high *transition accuracy*
on sampled trajectories. We show this acceptance criterion is **the wrong notion
of adequacy for planning**. Across perfect- and imperfect-information games we find:
(1) a CWM can pass a sampling gate at 100% accuracy and be ≥99% state-accurate on
the distribution a planner actually visits, yet **lose systematically at play**,
because the <1% it gets wrong is exactly the pivotal dynamics; (2) the expected
harm follows a quantitative law, `danger = play_cost × (1−rarity)^N`, that predicts
*when* sampling verification is blind; and (3) the failure is not repaired by more
data — LLM CWM synthesis is **rule translation, not rule inference**: it is correct
iff the rules are specified, and neither model scale nor on-manifold resampling
teaches a rule the specification omitted. We argue adequacy must be measured by
play (or on the search distribution), not by prediction accuracy on sampled
transitions. (4) The same failure recurs on the *inference* function of
imperfect-information CWMs: we prove a coverage bound under which a random gate is
identifying (so shallow games like Kuhn/Leduc show no gap), and construct a minimal
game that escapes it — where a verified-but-wrong `infer_states` passes the gate yet
loses every game, with harm following the identical `(1−ε)^N` law.

## 1. Introduction ⬜

- The CWM paradigm (LLM → executable world model → search) and why it is attractive
  (small model + code + search beats large model as direct policy; reproduces
  arXiv:2510.04542 on tic-tac-toe / Connect Four — see §3.1).
- The implicit trust step: accept the model on transition accuracy over sampled
  (random-policy) trajectories. **Our question: does that gate certify adequacy for
  planning?**
- Contributions (the three pieces): play-vs-accuracy gap; the danger law;
  translation-not-inference. Plus the imperfect-information extension (inference
  function as a new failure surface). ⬜ finalize once imperfect-info results land.

## 2. Setup / Methods ✅ (data exists; prose ⬜)

- **Contract.** `{board, current_player}` + `initial_state/legal_actions/
  apply_action/is_terminal/returns`; imperfect-info adds `observation` +
  `infer_states` + `initial_states` (§5).
- **Synthesis + gate.** LLM (Azure GPT-5.x: mini/nano/large) synthesizes the
  contract from rules + random trajectories; refined in a sandbox to transition
  accuracy 1.0 ("the gate").
- **Planning.** UCT MCTS over the synthesized model; determinized MCTS for
  imperfect info.
- **Metrics.** transition/state accuracy (the gate's lens) vs **play performance**
  (arena vs a ground-truth+MCTS agent, refereed by the true game), with Wilson CIs.
- **Games.** tic-tac-toe, Connect Four, generalized tic-tac-toe 6×6, generalized
  chess `army5x5a` (+ a material-at-cap rule variant), Trike, Kuhn poker.
- **Cost.** API is trivially cheap (~$2 total across all runs); the CPU bottleneck
  is MCTS — note the cheap/expensive separation used for the law (§4).

## 3. The gap: accuracy ≠ play-adequacy

### 3.1 Known games reproduce the paradigm but say nothing about the gate ✅
- mini/nano synthesize tic-tac-toe & Connect Four perfectly in 0 refinements
  (recall); CWM+MCTS dominates the LLM-as-policy baseline (up to 30–0). But recall
  ⇒ "accuracy 1.0" coincides with global correctness for the wrong reason.

### 3.2 The state-agreement gap does not appear on small complete-rules games ✅
- Three regimes (correct/none/wrong prior) × {mini,nano}, with-rules and
  `--no-rules`: whenever the gate passes, gap_truth ≈ 0; otherwise the gate fails
  outright. The random sample is *identifying* here. **Honest null** — motivates a
  sharper instrument.

### 3.3 The rare-rule instrument: verified but wrong at play ✅ (headline)
- army5x5a + "material-at-cap" rule: rare under random play (~1%), decisive in
  competent play (~50%). A gate-passing, gap_truth=0, ≥99%-state-accurate CWM
  **loses ~2:1**: win rate **0.383 vs a calibrated 0.504 baseline** (240 games,
  reproducible across seeds). State accuracy is blind to it (dilution); play is not.

## 4. A quantitative law of sampling-verification harm ✅

- `danger(rule, N) = play_cost × (1 − rarity)^N`. play_cost ≈ constant (~0.12,
  competent play always reaches the rule region); rarity varies, swept cheaply.
- **Threshold curve:** danger ≈ 0 while the rule is common enough for an
  N-trajectory gate to catch it, rises as it becomes rare, plateaus at full
  play_cost once it escapes; N shifts the threshold. (Table from EXPERIMENTS.md.)
- Connect Four cannot reach the danger zone (rarity↔consequence anti-correlation:
  6 rules tested); army5x5a can, because random and competent play diverge there.

## 5. Repairing the gap: translation, not inference ✅

- Detection works (verifying on the play/search distribution drops the gate below
  1.0) but **repair by examples does not**: naive DAgger (~2 discriminating ex.),
  proper DAgger (4–5/round), targeted on-manifold (54 real ex.) all leave the gate
  < 1.0 and the rule unlearned; play 0.35 (mini) / 0.42 (large) vs **0.53 with the
  rule written** (0 refinements). Artificial off-manifold repair data *corrupts*
  synthesis (large → acc 0.004). **Conclusion:** LLM CWM synthesis is rule
  translation; the actionable fix is spec completeness + verification on the play
  distribution.

## 6. Imperfect information: the inference function as a new failure surface ✅

The same gap appears on the *other half* of the contract — the inference function
`infer_states` that reconstructs hidden state — and it obeys the same law.

- Contract extension (`observation`, `infer_states`), determinized-MCTS planner,
  inference gate, imperfect arena — implemented & verified. [§ methods ✅]
- **Pipeline validation (Kuhn) ✅:** large synthesizes Kuhn in 0 refinements
  (transition gate 1.0, inference gate 1.0); CWM+determinized-MCTS plays at
  **0.470 [0.422,0.519]**, identical to the truth-vs-truth baseline — gate-pass →
  play ≈ baseline (recall), validating the machinery. mini does NOT recall this
  non-standard encoding (transition gate 0.845, synthesized `infer_states` crashes)
  — a scale/representation dependence consistent with translation-not-inference (§5).
- **When the gate is provably sufficient (theorem).** Under uniform-random play
  every reachable info-set at branching `b`, depth `d` has reach probability
  `≥ b^{−d}`, so a gate of `N ≳ b^{d_max}` random trajectories covers all reachable
  info-sets — hence all competent-relevant ones. The inference gate is therefore
  *provably identifying* on shallow games. **Corollary:** no coverage-gap Claim A
  exists on Kuhn (`b=2,d≈2`) or Leduc (`b=3,d≈8`); measured directly on Leduc,
  **0/1259** competent info-sets are missed by an N=8000 random gate. In poker,
  depth comes from aggression, which competent play *minimizes*, so competent play
  is strictly shallower than random — the opposite of a coverage gap.
- **Claim A, positive (Beacon) ✅ (headline of §6).** A gap needs `b^{d_max} ≫ N`
  with **depth = survival**. *Beacon* is the minimal game built to have it: a
  survival walk (an unsafe move loses immediately, so random play reaches the deep
  region D with probability `(1/2)^{2T}` while optimal play reaches it w.p. 1) + a
  final round where each player must guess the opponent's hidden type, inferable
  from its observed moves. A CWM whose `infer_states` is wrong **only on D**
  (status==1) passes the inference gate (random play never samples D) yet loses at
  play. **Result (T=8):** instrument inference mismatches on the random gate sample
  **0/8156**; instrument play winrate **0.000 [0.000,0.003]** vs fair baseline
  **0.500** (net −1200/1200). A verified-but-wrong inference function that is
  play-inadequate — the imperfect-info analogue of the rare-rule gap.
- **The danger law holds on the inference axis ✅.** Sweeping `T` (so `ε=(1/2)^{2T}`)
  against a fixed gate `N=2000`: harm `= play_cost·(1−ε)^N` traces the same
  threshold — T=4 `danger≈0` (gate catches it), T=8 `0.485`, T=10 `0.499`. Same
  gate-miss mechanism as the perfect-info danger law (§4), now on inference.
- **Claim B (translation-not-inference, hidden info):** ⬜ withhold the rules and
  test whether a synthesized `infer_states` can be inferred from play — a later
  round; Beacon establishes the existence/provability of the inference gap, the
  perfect-info §5 already shows translation-not-inference for dynamics.

**One mechanism, two faces.** §3–4 (transition rule, rarity `r`) and §6 (inference
info-set, depth `T`) are the same statement: a size-`N` random gate fails to certify
a CWM exactly on events of reach probability `≲ 1/N` that competent play reaches;
the harm is `(consequence) × P(gate miss)`, with `P(gate miss) ≈ e^{−Nr}` (dynamics)
or `≈ e^{−N b^{−d_max}}` (inference).

## 7. Related work ⬜

- Objective mismatch in model-based RL (Lambert et al. 2020 and successors) — the
  high-level "prediction accuracy ≠ control performance" precedent; our novelty is
  the *LLM-code-synthesis* setting, the *sampling-verification* blind spot, the
  quantitative danger law, and translation-not-inference.
- Code World Models / code-as-policy / LLMs for general game playing (arXiv:2510.04542).
- (I)SMCTS and determinization for imperfect information.
- DAgger / dataset aggregation (Ross et al. 2011).

## 8. Limitations & honesty ⬜

- Pure-Python MCTS limits arena size; we mitigate with the cheap/expensive split
  and exploit Kuhn's smallness for tight CIs.
- Determinized MCTS is not game-theoretic-optimal (strategy fusion); the baseline
  is by-symmetry ~0.5 and the contrast holds the planner fixed.
- Single model family (GPT-5.x via Azure); the rare-rule instrument is engineered,
  though we show natural games' rarity↔consequence frontier explains why.

## 9. Conclusion ⬜

Transition/state accuracy on sampled trajectories is the wrong adequacy criterion
for an LLM-synthesized world model used for planning. Verify on the distribution
that planning visits — or measure play directly — and make the specification
complete, because the model translates rules rather than inferring them.

---

### Appendix / reproducibility ✅
- All results + commands + seeds in `docs/EXPERIMENTS.md`; code on `main`
  (`cwm/` package, `scripts/`). Research narrative in `docs/RESEARCH-DIRECTION.md`.
