# An Omitted Mode Is a Rare Rule: The Sampling-Verification Danger Law in Continuous Code World Models

**Author:** Javier Aguilar Martín — AGILabs (javieraguilar.ai)
**Status:** First draft, 2026-07-07. Numbers from `docs/EXPERIMENTS.md` (§"PAPER 2 — ..." entries) and `results/continuous_*.json` — re-verify against the log before submission. Companion to *When a Verified World Model Still Loses* (paper 1), which studies the same failure in discrete games.

---

## Abstract

> *Note (2026-07-12): this draft keeps the original extended abstract as a
> historical record; the submission artifact `main.tex` carries the condensed
> (~250-word) abstract.*

In the Code World Model (CWM) paradigm, a large language model synthesizes an executable world model that a classical planner then searches over, and the model is accepted when it matches sampled transitions. Paper 1 showed, in discrete games, that this gate certifies the wrong thing: a model can pass at 100% transition accuracy and still lose systematically at play, following a quantitative law, danger = play_cost × (1−rarity)^N. This paper moves the question to continuous state spaces, where the model-based RL literature holds that world-model error is *pervasive* rather than localized — and shows that the danger law not only transfers but, empirically, becomes *exhaustive*.

Three results. **(1) The law is measure-theoretic, and its continuous home is hybrid dynamics.** The gate-miss factor (1−r)^N and the identifiability argument are statements about a measurable critical region, dimension-free; what is genuinely discrete in paper 1 is the *localization premise* — the wrong model is exact off the rule region — and we prove that a smooth (Lipschitz) truth/model pair cannot satisfy it: a large error confined to a metrically small region forces a large Lipschitz constant. The premise is realizable exactly where continuous systems are hybrid (contacts, hard stops, regime switches), and an omitted mode is precisely a rare rule. On a minimal hybrid instrument — a 1D cart with an inelastic wall whose position is the rarity knob — the paper-1 phenomenology reproduces sharply: rarity sweeps 0.33 → 0.002 while the mode-blind planner's regret stays flat at ~1.03 (it scores *below random*: model-predictive control drives into the phantom region and stays pinned against the wall for the entire episode, at every knob value); a planner that merely checks its own predictions against observations collapses this exploitation to a bounded first-contact transient (measured on both instruments); and the danger threshold law appears with the entire (1−r)^N elbow inside the sweep. **(2) The gate fails only where the law says it can.** A pinned-integrator synthesis contract makes a correct synthesis match the truth to float precision — a property of code exactness, independent of the gate's tolerance — which lets the synthesis gate run at ε = 10⁻⁹. Separately, an axis-separation experiment at a deployment-realistic ε = 0.01 shows the gate polices pervasive error (a supra-tolerance global bias is rejected on every rollout; a sub-tolerance bias passes and is harmless) while missing the localized hard mode, closely tracking the predicted (1−r)^N rate (within sampling noise at gate scale; §5). A smooth C∞ perturbation of comparable rarity has zero (or even *negative*) play cost: smoothness kills consequence, not detectability. **(3) In this regime the danger collapses to pure identifiability.** Running real LLM synthesis (GPT-5.x mini and large, 20 seeds/cell): with the wall absent from the sample — the (1−r)^N event, logged per seed — every synthesis (20/20 across model sizes) passes the gate fully wall-blind and is exploited at play (regret 0.999). But when the wall IS in the sample, GPT-5.x *repairs* it, writing the true global clamp rule (both sizes 10/10, large in ≤1 refinement iteration, some from the synthesis examples alone), unlike paper 1's symbolic setting where demonstrated rules were not learned. The failed repairs are superstitious local patches that the gate correctly rejects. Identifiability is a measure-theoretic property of the *sample*, not the synthesizer (Proposition 2); empirically, cross-family spot-checks in two more families reproduce the blind-exploited event in every family but diverge on repair — Qwen repairs none (0/2 per instrument), while Claude (agent-relayed) repairs most through a symmetry prior that can certify an invented, unfalsifiable mode — so repair-from-data is model-dependent in mechanism in a way identifiability — by the proposition — is not. The whole synthesis result replicates on a second, nonlinear instrument — a pendulum with an angular hard stop — where GPT-5.x repairs 62/62 mode-present seeds and every mode-absent seed is blind and exploited, so it is not a cart artifact. For the models tested, no accepted artifact was ever wrong on a sample-covered transition — an empirical, code-inspected regularity (GPT-5.x repairs every revealed mode; Qwen stalls and the gate refuses its patches; Claude's one certified-wrong artifact, a phantom symmetric mode, errs only where its sample is silent), not a theorem — so the only unsoundness we observed on covered inputs is the sampling event whose probability the law gives in closed form. A smooth-learner probe completes the picture: a linear least-squares model trained on wall-free data passes the same gate equally blind (identifiability is learner-independent), while 4 contact rows in 3200 tilt the same fit by twelve orders of magnitude off-mode — the mode cannot be localized by a smooth hypothesis. Localization — and hence both the danger and the repair — is a representational property of *code*.

---

## 1. Introduction

Paper 1 established, in discrete games, that transition accuracy on randomly sampled play-throughs is the wrong adequacy criterion for a world model used in planning, and quantified the failure: danger = play_cost × (1−rarity)^N, with the gate-miss factor exact under i.i.d. sampling. Its Related Work closed with a promissory note: the rare-rule gap is "a localized, discrete failure that state-accuracy metrics mask by dilution — a point worth revisiting in continuous settings," where the model-based RL literature (objective mismatch, Lambert et al. 2020; Dreamer, Hafner et al. 2020; MBPO, Janner et al. 2019) treats world-model error as pervasive and compounding rather than localized and pivotal.

This paper is that revisit. The question is not whether continuous world models can be wrong — that literature is mature — but whether the specific, *verified-but-wrong* geometry of paper 1 exists in continuous state spaces: a model that passes a sampling gate cleanly, is (in a precise sense) almost-everywhere correct, and still gets exploited catastrophically by the planner that trusts it.

The answer is yes, and the continuous version of the story is in one respect cleaner than the discrete one. Paper 1's headline had two components: (a) a provable one (when the rare rule is absent from the sample, no learner can infer it — an identifiability event with probability exactly (1−r)^N) and (b) an empirical one (the LLMs tested did not infer the rule *even when it was present* — "translation, not inference"). In the continuous instrument the second component **vanishes** for the models where we measured it: GPT-5.x infers an omitted hybrid mode from a handful of boundary-crossing transitions, writing the exact global rule. What remains provable is exactly the gate-miss and identifiability propositions (§3): with the mode absent from the sample — the (1−r)^N event — no learner can recover it from the sample alone (a prior or the specification could still supply it; Proposition 2). That no accepted artifact was ever wrong on a sample-covered transition is an empirical, code-inspected regularity for the models tested (GPT-5.x repairs every revealed mode; Qwen stalls and the gate refuses its patches; Claude repairs most, but its symmetry prior can certify a mode the sample never covers — wrong only off the sample, the same prior caveat), not a theorem. The danger law here is not just exact; empirically, for the models tested, it is exhaustive.

Contributions:

1. **Theory transfer, and one new piece.** The gate-miss proposition, the identifiability proposition, and the play-cost upper bound via query-hit mass transfer to continuous state spaces with only notational change (they are measure-theoretic; §3) — and a corollary ties the bound to the paper's play_cost normalization (§3, Corollary). The genuinely discrete ingredient of paper 1 is the *localization premise*, and we prove it requires unbounded local Lipschitz structure: for L-Lipschitz truth and model differing by η at a state-action point, the disagreement region contains a metric ball of radius (η−ε)/2L in S×A (Proposition 4). Hybrid mode boundaries are exactly where this obstruction disappears — an omitted mode is a rare rule.
2. **Two minimal hybrid instruments** — cart-with-wall (linear off-mode plant) and pendulum-with-stop (nonlinear, gravity) — on which the full paper-1 phenomenology is measured with the same harness and no per-instrument re-calibration: threshold law with the whole (1−r)^N elbow inside the knob sweep, knob-invariant play_cost ≈ 1 (the exploited planner scores below random, pinned against the phantom mode all episode), and the reach mechanism in its cleanest form (exploited-planner mode reach flat at 1.00, random reach falling two orders of magnitude, truth-planner trajectory reach 0.00). Three instrument-design lessons of independent value for continuous CWM work are recorded (§2.3).
3. **A pinned-integrator contract and a measured axis separation.** Fixing the discretization in the synthesis contract makes correct code float-exact — a property of code exactness independent of the gate's tolerance — so the synthesis gate (§7) can run at ε = 10⁻⁹. Separately, at a deployment-realistic ε = 0.01 (§5), the classic sub-tolerance/pervasive axis is a *control*, not a confound: the gate rejects supra-tolerance global bias on every rollout, passes sub-tolerance bias harmlessly, and misses the hard mode at a rate that closely tracks the predicted (1−r)^N (within sampling noise at gate scale; §5). A smooth localized perturbation of comparable rarity has ≈0 — at higher amplitude *negative* — play cost.
4. **A measured planner-side mitigation** (§6): distrust-region replanning — the planner checks its model's predictions against observed transitions and fences the refuted predictions — collapses the pinned-forever, below-random exploitation to a bounded first-contact transient on all 11 knob rows across both hand-written instruments, at zero cost when the model is right (bit-identical to plain MPC, tested). The fence exploits the hard-boundary structure of these modes (§6); the gate-side law is untouched: the gate still certifies a wrong model.
5. **The synthesis result: danger collapses to pure identifiability.** Real-LLM arms (GPT-5.x mini/large, 20 seeds/cell) with the identifiability event logged per seed: wall absent → 20/20 verified-blind-exploited (regret 0.999, Wilson lower bound 0.84); wall present → repaired to the exact global rule (both sizes 10/10, large in ≤1 iteration), never a wrong artifact accepted. Cross-family spot-checks in two more families reproduce the blind-exploited event in every family but diverge on repair — Qwen repairs none (superstitious patches the gate rejects), Claude (agent-relayed) repairs most through a symmetry prior that can certify an invented, unfalsifiable mode — so repair-from-data is model-dependent in mechanism, while identifiability is a property of the sample, not the model. The whole result replicates on a second, nonlinear instrument (a pendulum with an angular hard stop): GPT-5.x repairs 62/62 mode-present seeds and every mode-absent seed is blind and exploited. §7.
6. **Smooth learners cannot localize** (§8): the most favorable smooth learner (closed-form linear least squares — the off-mode dynamics are exactly linear) trained on wall-free data passes both gates fully blind (identifiability is learner-independent), and trained on wall-containing data is tilted twelve orders of magnitude off-mode by 4 contact rows in 3200 while still missing the mode. Both the danger geometry and the repair capability are representational properties of code.

Scope up front: two 1D instruments, two base planner families (random-shooting MPC and CEM, one fixed configuration each), 20 seeds per headline synthesis cell across the two instruments (both GPT-5.x sizes; plus the caught cell on the pendulum), a 3-seed cross-family spot-check per instrument (not full sweeps), and a probe-grade (not tuned-baseline) MLP. §10 gives the honest assessment and the full seed accounting.

## 2. The instruments

This section specifies the hand-written hybrid instruments and the planner that every later experiment reuses, and records the design lessons learned while calibrating them.

### 2.1 Cart-with-wall

State (x, v); action a ∈ [−a_max, a_max]; semi-implicit Euler with fixed dt:

    a  = clamp(action)
    v' = v + (gain·a − drag·v)·dt
    x' = x + v'·dt

with defaults dt = 0.1, gain = 3.0, drag = 0.3, a_max = 1. The **hybrid mode** is an inelastic wall at x_wall: if x' ≥ x_wall, the next state is exactly (x_wall, 0). The **blind model** is the same code path with the wall branch removed — the hand-written on-manifold proxy for a CWM synthesized from a spec that omits the wall, *bit-exact off-mode by construction* (tested: exact float equality on wall-free trajectories). We call such a model **mode-blind** (the canonical term; instrument-specific synonyms like "wall-blind", or "blind" for short, mean the same thing). Reward is two sigmoid plateaus: a small reachable one on the left (0.3, at x ≤ −6) and a large one on the right (1.0, at x ≥ 12) whose approach every swept wall position blocks. Episodes are 80 steps from x₀ ~ U(−0.5, 0.5), v₀ = 0.

The design requirements mirror paper 1's material-at-cap instrument (paper 1's discrete instrument: a rare resource-cap rule likewise omittable from sampled play): (a) random rollouts rarely fire the mode — the wall position is the **rarity knob** (r sweeps 0.331 → 0.0020 over x_wall ∈ [2, 10]; Table 1); (b) the omission is *exploited*, not merely mispredicted — the wall-blind model predicts coasting through the wall toward the large plateau, so the planner it advises drives right and is pinned; (c) the truth planner's optimal play differs qualitatively — it goes left.

### 2.2 Planner and play_cost

The planner is model-predictive control (MPC) by random shooting (Nagabandi et al. 2018; Chua et al. 2018, PETS): at each step, sample candidate action sequences (piecewise-constant blocks plus the three constant sequences {−a_max, 0, +a_max}), roll each out on the *model*, take the best first action, replan. The planner is a deterministic function of its model's responses and the seed, so paper 1's play-cost upper bound via query-hit mass applies verbatim (§3; the Corollary there ties that bound to the normalization below). Single-agent control makes play_cost a normalized regret, cleaner than the two-player arena (no opponent confound):

    play_cost = (J_truth − J_model) / (J_truth − J_rand),

where J_truth, J_model, and J_rand are the returns of the truth-planner, the model-planner (written J_blind in the tables when the model is the blind one), and the uniform-random policy, all measured in the true environment on paired seeds. The blind planner can score *below random* (it is actively exploited), so the normalized value can exceed 1; we report it unclamped.

### 2.3 Three instrument-design lessons (recorded because they will bite any continuous CWM study)

1. **I.i.d. per-step candidate sampling silently removes the mode from imagination.** With i.i.d. candidates, imagined displacement is diffusive; no sampled sequence reaches distant reward within the horizon, so the truth model and the blind model rank all candidates *identically* and the wall never enters imagination — the two arms become indistinguishable not because the models agree but because the planner never queries where they differ. Piecewise-constant blocks plus constant candidates fix it. (The planner's query distribution, not just its trajectory distribution, is part of the instrument.)
2. **Point (Gaussian) reward lodes demand braking finesse that random shooting lacks**; sigmoid plateaus remove the parking problem and give clean imagined-value margins in both directions.
3. **The plant's drag time-constant must sit well inside the planning horizon**, or no arm can act on the reward at all (our first calibration had τ = 1/drag = 10 s against a 3 s horizon; nothing moved).

## 3. Theory: what transfers, what changes, what is new

Notation: a verification gate draws N i.i.d. rollouts from the gate policy ρ (uniform-random actions from the initial-state distribution) and accepts a model f̂ if it matches the truth f within ε in sup-norm on every visited transition.

**Measure-space setup.** Fix a horizon T. A trajectory is a point of (S×A)^T, equipped with the product Borel σ-algebra. The gate policy ρ together with the transition kernel induced by f defines a trajectory law P_ρ on this space (the initial-state distribution pushed forward through ρ and f). The query measure μ_query(E) (the *query-hit mass*) is the probability, under the planner's trajectory law, that at least one model query during the episode lands in E. We assume throughout that the critical region R, the disagreement region E, and the reward and dynamics maps are Borel measurable, so every probability below is well defined. With this in place paper 1's discrete arguments transfer with only notational change.

**Proposition 1 (gate miss; transfers verbatim).** Let R be any measurable set of rollouts ("the critical event"; here: the rollout fires the wall mode) with r = P_ρ(R). The probability that N i.i.d. gate rollouts all avoid R is exactly (1−r)^N. *Nothing in paper 1's proof uses discreteness; the event is Bernoulli(r) and the draws are i.i.d.*

**Proposition 2 (identifiability; transfers verbatim).** Condition on the miss event of Proposition 1. Let M ⊆ S×A be the mode region (for the cart the clamp fires depending on (s,a) through x' ≥ x_wall), and let f̂₁, f̂₂ be any two models that agree on (S×A)∖M. On the miss event the sample visits no transition in M, so f̂₁ and f̂₂ produce identical outputs on every sampled input; hence every sample-measurable score (the gate, a likelihood, a refinement objective) is constant across the two, and no such score can distinguish them — preference for the correct one must come from the prior or the specification. This holds for *any* learner — LLM, linear regression, MLP — a point §8 instantiates empirically.

**Proposition 3 (play-cost upper bound; transfers verbatim).** Assume returns are normalized to [0,1] (WLOG, by rescaling J ↦ (J − J_min)/(J_max − J_min); equivalently carry an explicit factor (J_max − J_min) throughout). For any planner that is a deterministic function of model responses and a seed, |J(f) − J(f̂)| ≤ μ_query(E) where E is the disagreement region and μ_query the probability (the query-hit mass) that the planner queries its model on E during an episode.

*Proof sketch (coupling).* Couple the two runs on a common seed. On the event that no query lands in E, f and f̂ return identical responses to every query the planner issues (they agree off E), so with shared rng the two runs select the same action sequence and traverse the same states, realizing the same return. The realized returns can differ only on the complementary event, of probability μ_query(E), where normalized returns differ by at most 1; taking expectations gives |J(f) − J(f̂)| ≤ μ_query(E). MPC's imagined rollouts are the queries. (This is paper 1's coupling argument, recorded here rather than deferred.) ∎

The raw J reported in the tables (e.g. J_truth = 17.77) is this normalized quantity rescaled by (J_max − J_min), so the bound is a statement about the normalized return. The paper's reported play_cost, however, divides by (J_truth − J_rand) (§2.2), *not* by (J_max − J_min); the following corollary states the relationship rather than silently identifying the two.

**Corollary (play_cost saturation).** With |play_cost| = |J(f) − J(f̂)| / (J_truth − J_rand), play_cost as defined (signed) in §2.2, Proposition 3 in raw units (|J(f) − J(f̂)| ≤ μ_query(E)·(J_max − J_min)) gives

    play_cost ≤ μ_query(E) · (J_max − J_min) / (J_truth − J_rand),

so the bound reads play_cost ≲ μ_query(E) exactly when J_rand ≈ J_min and J_truth ≈ J_max — the random policy near the reward floor, the truth planner near the ceiling. Both instruments are in this regime: on the cart J_rand = 0.53 against a pinned J_blind ≈ 0 and J_truth = 17.77; on the pendulum J_rand = 0.06 and J_truth = 20.08. The blind planner queries the wall region in every episode, so μ_query(E) ≈ 1 and the normalized bound is saturated — play_cost ≈ 1, as observed in §4–§5.

**What does not transfer.** Paper 1's coverage certificates enumerate finite information-set spaces. Continuous state spaces admit no such enumeration; covering-number analogues under Lipschitz assumptions are left open (§10).

**What is new: the localization premise is a theorem-shaped obstruction.**

**Proposition 4 (smoothness forbids localized error).** Let f, f̂ : S×A ⊆ ℝᵈ × ℝᵐ → ℝᵈ be L-Lipschitz on the joint state-action space in the sup-metric on S×A, with L ∈ (0,∞) (i.e. L = max(Lip f, Lip f̂)). Suppose ‖f(s₀,a₀) − f̂(s₀,a₀)‖∞ = η at some (s₀,a₀) ∈ S×A. Then for any tolerance ε < η, the disagreement region E_ε = {(s,a) ∈ S×A : ‖f(s,a) − f̂(s,a)‖∞ > ε} contains the open metric ball B((s₀,a₀), (η−ε)/2L) ∩ (S×A) (the intersection matters only when (s₀,a₀) lies near ∂(S×A)). If instead L = 0 then f − f̂ is constant and E_ε is all of S×A.
*Proof.* g = f − f̂ is 2L-Lipschitz on S×A, so for ‖(s,a) − (s₀,a₀)‖∞ < (η−ε)/2L, ‖g(s,a)‖∞ ≥ η − 2L·‖(s,a)−(s₀,a₀)‖∞ > ε; the inequality is strict, so the ball is open. The L = 0 case is immediate: g ≡ g(s₀,a₀) with ‖g(s₀,a₀)‖∞ = η > ε. ∎

The disagreement region E_ε lives in the same joint state-action space S×A as the query region E of Proposition 3, so the ball is *directly* a lower bound on the query-relevant region the planner can hit — no fixed-action slice argument is needed to bring the two together. (Restricting to a fixed action a₀ recovers the state-slice form: the open ball of radius (η−ε)/2L in S×{a₀} lies in E_ε, the version convenient when reasoning about a single instrument's mode.)

Read as its contrapositive: a model error that is *large somewhere* (large enough to matter at play) and *invisible at tolerance ε outside a metrically tiny region* requires L large — in the limit, a discontinuity. This is exactly the sense in which paper 1's localization premise ("the wrong model is exact off the rule region") is discrete: it is unsatisfiable by smooth truth/model pairs, up to the ball-radius quantification. Two consequences structure the paper: (i) the natural continuous home of the danger geometry is **hybrid dynamics** — contacts, hard stops, saturations, regime switches — where the truth itself has unbounded local Lipschitz constant across a mode boundary (our wall: v jumps to 0), and an omitted mode is precisely a rare rule; (ii) the premise is *representationally* available to programs (an omitted or added branch is bit-exact off the omitted case) and not to smooth learned models, a distinction §8 measures.

A caveat, stated because it is the honest boundary of Proposition 4: the ball is metric, and its *probability* under the gate's visitation measure can still be small — smoothness bounds how spatially concentrated an error can be, not how often the gate visits it. The proposition removes the *exact* localization premise for smooth pairs; the (1−r)^N mechanism itself is representation-independent and applies to any critical region of small visitation measure.

## 4. The mechanism and the threshold law

This section measures the danger law's full phenomenology on the hand-written instruments, before any LLM enters the loop. All numbers CPU-only, with the hand-written blind model as the on-manifold proxy (`scripts/continuous_reach.py`; 3000 rarity rollouts and 20 MPC episodes/arm per knob; Wilson 95% CIs in the results JSON).

**Table 1 — the danger curve on the wall-position knob (N = gate size in rollouts).**

| x_wall | rarity | J_truth | J_blind | J_random | play_cost | blind hit | truth hit | d@N=20 | d@40 | d@80 |
|-------:|-------:|--------:|--------:|---------:|----------:|----------:|----------:|-------:|-----:|-----:|
| 2 | 0.3313 | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.000 | 0.000 | 0.000 |
| 3 | 0.2193 | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.007 | 0.000 | 0.000 |
| 4 | 0.1430 | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.047 | 0.002 | 0.000 |
| 5 | 0.0843 | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.177 | 0.030 | 0.001 |
| 6 | 0.0503 | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.367 | 0.131 | 0.017 |
| 8 | 0.0127 | 17.77 | 0.02 | 0.53 | 1.030 | 1.00 | 0.00 | 0.798 | 0.619 | 0.372 |
| 10 | 0.0020 | 17.77 | 0.94 | 0.53 | 0.977 | 1.00 | 0.00 | 0.938 | 0.901 | 0.832 |

Readings:

- **The threshold law again.** Danger ≈ 0 while the wall sits inside the random-rollout envelope, rises through the elbow, and plateaus at full play_cost; N shifts the threshold. The entire elbow lies inside the sweep.
- **play_cost is knob-invariant and ≈ 1** (exceeding 1 at every knob except the largest, where far-plateau leakage gives 0.977). The blind planner is not merely uninformed; it is *exploited*: MPC on the wall-less model plans into the phantom region, is pinned at the wall (final x = x_wall exactly, contact rate 1.00 at every knob), and replans the same doomed plan every step — for the entire episode. It scores below random (0.00 vs 0.53). The 0.977 at x_wall = 10 is the sigmoid tail of the far plateau leaking J_blind = 0.94; the mechanism is unchanged.
- **The reach mechanism, in its cleanest form.** Paper 1 measured competent-vs-random reach of the rule region; here the exploited planner's mode reach is flat at 1.00 across the knob while random reach falls 165× — and the *truth* planner's trajectory reach is 0.00. The mode lives on the blind planner's deployment path and on the truth planner's *query* distribution (its imagination crosses the wall while deliberating; Proposition 3's μ_query), not on truth's trajectories. The danger factorization rides two different reach distributions, exactly as in paper 1, with the query/trajectory distinction now visible.
- Gate-miss exactness is re-verified in-tests (empirical P(N rollouts miss) vs (1−r)^N within binomial error) and again, at gate scale, in §5.

### 4.1 Robustness: the same law on a nonlinear plant

The cart's off-mode dynamics are linear, which is convenient for §8 but invites the worry that the phenomenology depends on it. A second instrument — a pendulum (gravity term sin θ, θ = 0 hanging down) with a hard angular stop, same interface, same MPC, same two-plateau reward on θ — reproduces the identical picture with *no* re-calibration (rarity is natural here: gravity confines the random walk near the bottom, so climbing to the stop is rare):

| θ_stop | rarity | J_truth | J_blind | play_cost | blind hit | d@N=40 |
|-------:|-------:|--------:|--------:|----------:|----------:|-------:|
| 0.8 | 0.2970 | 20.08 | 0.01 | 1.002 | 1.00 | 0.000 |
| 1.0 | 0.1277 | 20.08 | 0.03 | 1.002 | 1.00 | 0.004 |
| 1.2 | 0.0527 | 20.08 | 0.05 | 1.000 | 1.00 | 0.115 |
| 1.4 | 0.0193 | 20.08 | 0.12 | 0.997 | 1.00 | 0.457 |
| 1.6 | 0.0073 | 20.08 | 0.26 | 0.990 | 1.00 | 0.737 |
| 2.0 | 0.0000 | 20.08 | 1.23 | 0.942 | 1.00 | 0.942 |

Threshold law, knob-invariant exploitation (pinned at the stop in every episode, at every knob), truth planner untouched by the mode. The mechanism does not care that the plant is nonlinear — only that the mode is hard and rare under the gate's measure.

### 4.2 A second planner family: play_cost is planner-dependent, as the bound prescribes

Proposition 3 predicts two branches: a blind model can change behavior only to the extent that the planner queries its disagreement region. Random-shooting MPC's constant candidates reach the distant phantom plateau in imagination and produce `play_cost ≈ 1`. We therefore repeated the full 11-knob grid with a second base planner, CEM (`scripts/continuous_cem.py`; horizon 40, 5 iterations, 64 samples, elite fraction 0.125, minimum standard deviation 0.05; one fixed setting across both instruments). The crossing columns below are the fraction of sampled imagined trajectories that cross the omitted boundary, measured for BOTH planners with one plan from the same paired initial state per episode seed (episode-accumulated CEM fractions, which tell the same story, are recorded in the results JSON).

| instrument | knob | pc_blind MPC | pc_blind CEM | contact CEM | crossing CEM | crossing MPC |
|---|---:|---:|---:|---:|---:|---:|
| cart | 2.0 | 1.031 | 0.000 | 0.00 | 0.0309 | 0.3865 |
| cart | 4.0 | 1.031 | 0.000 | 0.00 | 0.0055 | 0.2453 |
| cart | 6.0 | 1.031 | 0.000 | 0.00 | 0.0003 | 0.1483 |
| cart | 8.0 | 1.030 | 0.000 | 0.00 | 0.0000 | 0.0773 |
| cart | 10.0 | 0.977 | 0.000 | 0.00 | 0.0000 | 0.0369 |
| pendulum | 0.8 | 1.002 | 0.009 | 0.70 | 0.1150 | 0.6392 |
| pendulum | 1.0 | 1.002 | 0.025 | 0.25 | 0.0483 | 0.5530 |
| pendulum | 1.2 | 1.000 | −0.011 | 0.00 | 0.0164 | 0.4672 |
| pendulum | 1.4 | 0.997 | −0.021 | 0.00 | 0.0053 | 0.3842 |
| pendulum | 1.6 | 0.990 | −0.021 | 0.00 | 0.0013 | 0.3039 |
| pendulum | 2.0 | 0.942 | 0.000 | 0.00 | 0.0002 | 0.2158 |

CEM's blind-model play cost lies in [−0.0213, 0.0248] on every row — and the seed-paired 95% t-interval includes zero on all 11 rows — while its imagined crossing fraction is strictly below MPC's throughout. On the cart, truth- and blind-model CEM returns are identical and contact is zero everywhere. The nearest pendulum stops are an honest qualification: CEM contacts θ_stop=0.8 in 70% of episodes and θ_stop=1.0 in 25%, but does not enter MPC's pinned, below-random regime; contact is zero from θ_stop≥1.2. Contact is therefore not itself exploitation. This is the other measured branch of the bound: the same certified-blind model is a landmine whose consequence depends on the planner's query reach. It also operationalizes §2.3's first lesson — if search does not discover the phantom, it cannot optimize toward it.

Two caveats prevent the wrong conclusion. CEM's pendulum truth return varies from 15.36 to 16.46 (versus MPC's 20.08), consistent with local optima; the comparison is blind-CEM against truth-CEM, not a claim that CEM is globally optimal. And limited reach is not knowledge or mitigation: a planner that misses a phantom distant reward can also miss a real one. The result is for one fixed CEM configuration, not a hyperparameter sweep.

## 5. Axis separation: the gate fails only where the law says it can

The classic continuous-model failure axis is pervasive sub-tolerance error; the danger law's axis is a localized hard mode. A tolerance gate (ε = 0.01, deployment-realistic) must be shown to fail *only* on the second axis, and only at the (1−r)^N rate. Five arms, one table (`scripts/continuous_axes.py`; reveal-rarity = P(a random rollout contains a transition where truth and model differ > ε), 2000 rollouts; pass@40 over 300 independent N = 40 gates; 20 MPC episodes/arm). For the hard mode, the mode-firing rarity of Table 1 and the pendulum table and the reveal-rarity here coincide as events — the mode error exceeds every deployment-realistic ε (the ε-sweep below), so a rollout fires the mode iff it reveals a disagreement — which licenses the shared symbol r. (The small numeric difference for wall@4 — mode-firing rarity 0.1430 at 3000 rollouts in Table 1 vs. reveal-rarity 0.1385 at 2000 rollouts in Table 2 — is resampling noise on the same event, not a different event.)

**Table 2 — axis separation (ε = 0.01, N = 40; d@N = play_cost × (1−r)^N, as in Table 1).**

| arm | reveal-rarity | (1−r)⁴⁰ | pass@40 measured | play_cost | d@40 |
|-----|--------------:|--------:|-----------------:|----------:|----------:|
| wall@4 omitted | 0.1385 | 0.0026 | 0.003 | 1.031 | 0.0027 |
| wall@8 omitted | 0.0125 | 0.6046 | 0.667 | 1.030 | 0.6227 |
| drag bias ×1.03 (sub-ε) | 0.0000 | 1.0000 | 0.997 | 0.000 | 0.0000 |
| drag bias ×2.0 (supra-ε) | 1.0000 | 0.0000 | 0.000 | 0.000 | 0.0000 |
| C∞ bump@4, amp 0.5 | 0.1875 | 0.0002 | 0.000 | 0.000 | 0.0000 |
| C∞ bump@4, amp 1.0 | 0.2085 | 0.0001 | 0.000 | −0.745 | −0.0001 |

Readings:

- **Gate exactness at gate scale.** Measured pass@40 matches (1−r)⁴⁰ in both wall rows (0.003 vs 0.0026; 0.667 vs 0.605, the prediction marginally below the 300-gate Wilson lower bound of 0.6115 — sampling noise at that gate count; see the ε-sweep note below). The proposition is not asymptotic decoration; it is the observed acceptance rate.
- **The gate polices the pervasive axis.** A global drag bias above tolerance is revealed on *every* rollout (rarity 1.0) and never accepted; a sub-tolerance bias is accepted (0.997; the 0.3% is the extreme velocity tail nudging the error over ε) and is harmless at play (play_cost 0.000). Verified-and-fine is a real cell, and the gate finds it.
- **Danger lives in one quadrant only**: rare ∧ hard-mode. Common hard mode (wall@4): caught, danger ≈ 0.003. Pervasive error: caught or harmless. Smooth localized: next point.
- **Smoothness kills consequence, not detectability.** The C∞ drag bump at the wall's location has *comparable rarity* to the wall (0.19 vs 0.14 — it is just as detectable, confirming that Proposition 4 is about error *geometry*, not about hiding from the gate) yet play_cost 0.000 at amplitude 0.5: both planners cross it, one of them slightly surprised. At amplitude 1.0 play_cost turns *negative* (−0.745): the truth planner, seeing the slowdown near its horizon edge, is over-pessimistic and often settles for the small plateau, while the bump-blind planner pushes through and wins. A smooth localized omission produces planner-side timing effects of ambiguous sign; only the hard mode produces the one-way exploitation geometry (pinned, forever, below random).

**Is ε = 0.01 a special setting, or is the axis separation itself ε-invariant?** A sweep over `ε ∈ {1e-9, 1e-6, 1e-4, 1e-3, 1e-2, 3e-2, 0.1, 0.3}` (`scripts/continuous_eps_sweep.py`; full table in `docs/EXPERIMENTS.md`) answers: ε-invariant. Mode-arm reveal-rarity is flat across the entire deployment-realistic range — on the cart, `wall@8` is bit-identically flat through the whole grid including ε = 0.3, and `wall@4` only dips slightly (never widens) at the top of the grid. The pervasive bias arms switch sharply at their own error scale on both instruments instead.

**Table 2a — reveal-rarity vs. ε (cart).**

| ε | wall@8 rarity | bias ×1.03 rarity | bias ×2.0 rarity |
|---:|---:|---:|---:|
| 1e-6 | 0.0125 | 1.0000 | 1.0000 |
| 1e-2 | 0.0125 | 0.0000 | 1.0000 |
| 0.1 | 0.0125 | 0.0000 | 0.0040 |
| 0.3 | 0.0125 | 0.0000 | 0.0040 |

The pendulum replicates both halves: its mode arms are flat too (only a slight dip at the top of the grid — `stop@1.0` rarity 0.1410 at ε ≤ 3e-2, dipping to 0.1400 at ε = 0.1 and 0.1240 at ε = 0.3), and its bias arms switch at the same error-scale boundaries as the cart's. pass@40 ≈ (1−r)⁴⁰ continues to hold for the mode arms at every ε in the grid, on both instruments (honesty note: at `wall@8` the closed-form 0.6046 sits marginally below the empirical 300-gate Wilson 95% CI lower bound of 0.6115 — sampling noise at that gate count, reported plainly rather than as exact agreement). `play_cost` is not re-measured across ε: the model under test does not depend on the gate's tolerance, so play behavior is ε-independent by construction — the sweep varies only what the gate can see. The gate's ε is a pervasive-error dial, not a mode-detection dial: tightening it cannot catch the hard mode, and loosening it does not widen the hole.

## 6. Mitigation: the exploitation is planner-mediated

The exploitation measured in §4–§5 is planner-mediated, not model-mediated, and a planner-side fix collapses it without touching the model or the gate — this does **not** contradict the danger law (the gate still certifies a wrong model; Proposition 2 is untouched). Like those sections, this one uses the hand-written instruments and blind models, not LLM synthesis. Distrust-region replanning (`src/cwm/continuous/mitigation.py`, strictly additive) compares the model's prediction against the observed transition after every real step (tol = 1e-6); a disagreement records the *position of the model's refuted prediction* — not the pre-state — as a one-sided fence, since false predictions always lie on or beyond the mode boundary. While scoring a candidate rollout, the first imagined step whose position interval crosses a fence's ε-band (ε = 0.25 cart, ε = 0.1 pendulum) truncates the rollout — reward kept, everything downstream dropped — which makes the fence leap-proof at any imagined speed; candidates are then ranked by (truncated return, distance to the nearest fence), which structurally prefers the real side. With zero violations this is bit-identical to plain MPC by construction (tested bitwise) — mitigation costs nothing when the model is right. Only this design is undodgeable: three earlier attempts (pre-state flee-balls; full-state point fences, dodged by the planner probing crossing velocities) were each defeated by the argmax planner acting as an adversary against the fence. The collapse is scoped to **hard-boundary hybrid modes**: the one-sided fence works precisely because a refuted prediction lies on or beyond the mode boundary, so fencing its far side cannot cut off any real trajectory. This structural fact is what these wall/stop instruments supply; less structured failure modes (soft or moving boundaries, errors not confined to a hard stop) do not obviously admit such a fence and are untested — this is a hard-boundary mitigation, not yet a general planner-side one.

**Table 2b — mitigation sweep (20 episodes/knob, both instruments; pc_blind / pc_mit = play_cost of the blind planner under plain MPC / under distrust-region mitigation; full 11-row table with contact rates and violation counts in `docs/EXPERIMENTS.md`).**

| knob | pc_blind | pc_mit | first-contact step |
|-----:|---------:|-------:|--------------------:|
| **cart** (x_wall) | | | |
| 2 | 1.031 | 0.290 | 11.6 |
| 4 | 1.031 | 0.446 | 16.9 |
| 6 | 1.031 | 0.578 | 21.3 |
| 8 | 1.030 | 0.699 | 25.1 |
| 10 | 0.977 | 0.806 | 28.7 |
| **pendulum** (θ_stop) | | | |
| 0.8 | 1.002 | 0.113 | 7.0 |
| 1.0 | 1.002 | 0.129 | 8.1 |
| 1.2 | 1.000 | 0.143 | 9.0 |
| 1.4 | 0.997 | 0.160 | 10.0 |
| 1.6 | 0.990 | 0.177 | 11.0 |
| 2.0 | 0.942 | 0.212 | 13.0 |

The collapse is large at every knob: `pc_blind` stays pinned at ≈0.94–1.03 everywhere (established in §4, Table 1 and the pendulum table), while `pc_mit` never exceeds 0.81. Exactly one violation suffices to fence the mode on *every* one of the 11 rows — the mitigated planner must touch the mode once, which is identifiability operationalized: you cannot avoid what you have never seen. The residual `pc_mit` is the honest cost of that unavoidable first contact, and it grows with the lure distance, read off the first-contact step: cart 0.290 → 0.806 as first contact goes 11.6 → 28.7 of 80 steps (knob 2 → 10); pendulum 0.113 → 0.212 as first contact goes 7.0 → 13.0 (knob 0.8 → 2.0). The cart knob = 10 row is the least favorable in the sweep (`pc_mit` 0.806, close to blind's 0.977) because the transient consumes most of the horizon — but the blind planner stays pinned *forever* there (J 0.94 of J_truth 17.77) while the mitigated planner escapes and recovers most of the horizon (J 3.88): the normalized cost looks modest, the actual return does not.

## 7. LLM synthesis: the danger collapses to pure identifiability

Real-LLM arms (`scripts/continuous_danger_synthesis.py`; Azure GPT-5.x mini and large; N = 40 training rollouts which double as the gate, as in paper 1's sweep; ε = 10⁻⁹ pinned-integrator gate; **20 seeds/cell on the headline x_wall = 8 cell, both sizes** (paper-1 standard); 6 MPC play episodes/seed; per-seed JSON with the synthesized code versioned in `results/`). The contract pins the integrator (§2.1's equations, stated in the spec text, constants generated from the environment instance so they cannot drift); the *full* arm includes the wall clause, the *incomplete* arm omits it. Crucially, each seed logs whether the wall fired in its training sample — the identifiability event that paper 1 could not condition on post hoc.

**Full arm (both sizes, 40 seeds): gate 1.000 in 0 refinement iterations, wall probes exact, play at truth parity — every seed.** The pinned-integrator premise holds with a real LLM: correct synthesis is float-exact through the sandbox, so ε = 10⁻⁹ costs nothing and the tolerance axis is fully disarmed. As in paper 1, given the rule, the model translates it perfectly.

**Incomplete arm.** Three-way structure, exactly as the design predicted on two of three branches and *informatively opposite* on the third:

1. **Wall absent from the sample (the (1−r)^N event; 10/20 seeds at x_wall = 8 for each size, consistent with (1−0.0125)⁴⁰ ≈ 0.60):** every such seed — **20/20 across mini and large** — passed the gate at 1.000, fully wall-blind on the probes (1.0), and was exploited at play: pinned at the wall, contact rate 1.0, **play_cost 0.999**. Wilson 95% on P(accepted-blind | wall missed): lower bound 0.72 per size, **0.84 combined (20/20)**. This is paper 1's headline, synthesized end-to-end in a continuous CWM: a verified, almost-everywhere-exact model that performs worse than random.
2. **Wall present, repaired:** the LLM does *not* stay blind. It reads the failing transitions and writes the true global rule — `if x2 >= 8.0: return [8.0, 0.0]` (or the equivalent `if x2 > 8.0: x2 = 8.0`) — not a curve fit. At 20 seeds both sizes repaired **every** wall-present seed: **large 10/10 in 0–1 iterations** (two from the synthesis examples alone, 0 iterations), **mini 10/10 in 0–5 iterations** (one at 0). This is the divergence from paper 1, where rules demonstrated by example transitions were persistently not learned (translation-not-inference). A numerically-manifested discontinuity is learnable from data in a way a symbolic game rule was not.
3. **Wall present, not repaired:** at 20 seeds on the headline cell GPT-5.x produced **no stalls** — but stalls are real and instructive where they occur (the 5-seed x_wall = 4 cell, and the Qwen cross-family arm below). They are not near-misses of the rule but **superstitious local patches**: e.g. `if abs(x2 - 8.0) <= 0.15 and abs(v2) <= 1.1: x2 = 8.0`, or Qwen's `if x2 >= 8.0 and v2 <= 0.0: ...` — clamps fitted to the *observed manifestation* of the mode (low-speed, near-wall contacts), which mispredict other approaches to the wall. **The gate rejected every one of them** (gate 0.49–0.999, never 1.000).

**Cross-family spot-checks (two families).** *Qwen* (HF router, `Qwen/Qwen3-Coder-30B-A3B-Instruct`, 3 seeds): the full arm is clean (3/3 gate 1.000, blind 0.0), so the pinned-integrator premise is not GPT-specific; on the incomplete arm the identifiability branch reproduces (the 1/3 wall-absent seed is gate-1.000 wall-blind and exploited, play_cost 0.999), but Qwen **repaired neither** of its two wall-present seeds (gate 0.999 and 0.491, both superstitious patches the gate refused). *Claude* (Sonnet, agent-relayed via paper 1's protocol on `scripts/continuous_claude_step.py` — verbatim pipeline messages relayed to fresh, context-free instances per message, same ε = 10⁻⁹ gate and MPC play as the API arms; seeds 10000/20000/30000 plus one full control per instrument; `results/continuous_claude_relay.json`, transcripts under `results/claude_relay_transcripts/`): both full controls are clean (2/2 gate 1.000, blind 0.0, play_cost 0.0), and both mode-absent seeds are certified fully blind and exploited (cart play_cost 0.999, pendulum 0.995) — the identifiability event fires family-independently, as Proposition 2 requires. On repair Claude is neither GPT-5.x nor Qwen: cart seed 20000 repaired the exact one-sided rule in 1 iteration, cart seed 30000 repaired at iteration 5 after a period-2 oscillation (symmetric ±8 walls → both removed → symmetric again → removed → one-sided correct), but pendulum seed 20000 was certified in 1 iteration carrying an invented mode (next paragraph) and pendulum seed 30000 stalled at 5 iterations (gate 0.9972), oscillating between the symmetric-stop and no-stop artifacts without finding the one-sided rule. So across three families the mode-absent blind-and-exploited event fired for every one (it is a property of the sample; Proposition 2), while repair-from-data is model-dependent *in mechanism, not merely in rate*: GPT-5.x repairs every revealed mode exactly (62/62 pendulum, 20/20 cart), Qwen repairs none (superstitious local patches), Claude repairs most but through a *symmetry prior* — it generalizes one-sided boundary evidence into a symmetric pair of boundaries.

**A fourth artifact class: certified with an invented, unfalsifiable mode.** Claude's symmetry prior produces an outcome beyond the correct/blind/superstitious-patch trichotomy. Where the training sample covers the invented side, the gate refutes the phantom and the memoryless refine loop oscillates (cart seed 30000's period-2 cycle above; pendulum seed 30000's stall at gate 0.9972). But where the sample is *silent* on the invented side, the phantom is unfalsifiable: pendulum seed 20000 was certified at gate 1.000 in a single iteration while carrying a phantom symmetric stop at θ = −1.4 that this seed's rollouts never reach (`if th2 < -th_max: th2 = -th_max; om2 = 0.0`) — a verified artifact, exact on every sampled transition, that nonetheless encodes a hard stop which does not exist. This is a clean natural experiment: the *same* symmetric artifact was refuted at pendulum seed 30000 and certified at seed 20000, the only difference being whether the sample covered θ < −1.4. It is Proposition 2's prior caveat measured directly — on inputs the sample never touches, the artifact's content comes from the model's prior, and the gate cannot police it. Note the classification did not flag it: the `mode_blindness` probe scored 0.0 (correct) because it probes only the true +1.4 mode's region; code inspection, not the probe, caught the invented mode (§10).

**Honesty notes (Claude arm).** (i) Agent-relayed means an agent scaffold over a subscription transport, not an API, though the relayed messages are byte-identical to the pipeline's; in the two multi-iteration cells a handful of refinement replies prefixed a one-line explanation before the code block (two distinct sentences, repeated across the oscillation) despite the output-only-code instruction — recorded, and the code block still parsed; no relay was refused this time (contrast the discrete probe). (ii) The refine loop is memoryless in the API arms too — `refine_continuous` sends a single user message per iteration (`src/cwm/continuous/contract.py`) — so the oscillation is protocol behavior, not a relay artifact. (iii) n is small: 3 seeds plus one control per instrument, one alternate family.

So repair-from-data is *model-dependent in mechanism* while identifiability is not: the wall-absent blind-and-exploited event fired for every model tried, whereas how reliably — and *how* — the loop recovers a *revealed* mode varies with the synthesizer. GPT-5.x erases paper 1's (b)-residual entirely on this instrument; Qwen does not; Claude erases it on covered inputs but can substitute an invented mode where the sample is silent.

The branches compose into the paper's central claim. With the mode in the data, the synthesize–refine–gate loop behaved soundly *on every transition the sample covered*: it recovers the exact mode or refuses the artifact (no accepted artifact was ever wrong on a sample-covered transition, for every model tested; the one accepted-but-wrong artifact we saw — Claude's phantom pendulum stop — errs only where its sample is silent, the Proposition 2 prior caveat, not a gate failure — an empirical, code-inspected regularity, not a theorem). With the mode absent, no loop can help (Proposition 2: the sample carries no evidence for the mode — though a prior or the specification still could supply it), and the acceptance of a blind artifact is not a failure of the LLM, the refinement, or the gate implementation — it is the sampling event whose probability is exactly (1−r)^N. Paper 1's danger law had a provable core plus an empirical residual (the rule not learned even when shown); in the continuous instrument the residual *can* vanish — it does for GPT-5.x, which repairs every revealed mode — so **the law becomes the entire failure surface** for a capable-enough synthesizer, and shrinks toward it even for a weaker one. The actionable consequence sharpens correspondingly: in this regime, spec completeness and gate-sample coverage are not two independent worries — coverage *is* the dominant worry, because the synthesis loop repairs what the sample reveals.

(Scope: 20 seeds/cell on the headline cell, both GPT-5.x sizes; the wall-absent conditional is 20/20 across sizes and consistent across three independent runs — the 5-seed first run, the 20-seed tightened run, and the 3-seed Qwen run; the wall-present repair rate is 20/20 for GPT-5.x on this cell, 0/2 for Qwen, and mechanism-dependent for Claude (exact on both cart seeds, one via a period-2 oscillation) — model-dependent, small-n on the cross-family arms. LLM synthesis is stochastic across calls; the three-way structure and the identifiability conditional are stable run-to-run, per-seed iteration counts are not.)

**Second-instrument robustness (pendulum-with-stop, §4.1, 20 seeds/cell, both sizes).** The synthesis arm is not cart-only. Running the identical pipeline on the nonlinear pendulum — headline θ_stop=1.4 (rarity 0.019) and caught θ_stop=1.0 (rarity 0.128; "caught" labels a cell whose mode is common enough that the gate sample essentially always contains it, so the identifiability event essentially never fires) — reproduces every branch, including a 3-seed Qwen cross-family spot-check at the headline knob (Table 2c):

**Table 2c — pendulum synthesis cells (20 seeds/cell, both GPT-5.x sizes; 3-seed Qwen spot-check at θ_stop=1.4). k → m = of the k seeds in that branch, m had the stated outcome (blind & exploited, resp. repaired); the parenthetical count is stalled seeds; pc = play_cost.**

| cell (20 seeds each) | full | mode-absent → blind & exploited | mode-present → repaired (stalled) |
|---|---|---|---|
| mini θ_stop=1.4 | 20/20 | 9 → 9 (pc 0.995) | 11 → 11 (0) |
| large θ_stop=1.4 | 20/20 | 9 → 9 (pc 0.995) | 11 → 11 (0) |
| mini θ_stop=1.0 | 20/20 | 0 → — | 20 → 20 (0) |
| large θ_stop=1.0 | 20/20 | 0 → — | 20 → 20 (0) |
| Qwen θ_stop=1.4 (3 seeds) | 3/3 | 1 → 1 (pc 0.995) | 2 → 0 (2 stalled @0.9997) |

Pooled across both knobs and both sizes (Table 2c), every mode-absent occurrence was blind and exploited at play_cost 0.995 (Wilson 95% lower bound 0.824 pooled; per-size headline 9/9, lower bound 0.701) — the same fixed-point exploitation as the cart's play_cost ≈ 1 — and GPT-5.x repaired **62/62** mode-present seeds to the exact angular clamp (`if th2 >= θ_stop: return [θ_stop, 0.0]`), 0 stalls (Wilson 95% lower bound 0.942). Qwen reproduces the mode-absent blind-exploited event but stalls on both its mode-present seeds, the same superstitious-patch signature as on the cart; Claude's agent-relayed spot-check on this instrument produced the phantom-mode artifact discussed in §7 (a certified stop at θ = −1.4 its sample never reaches, plus a stall at the other mode-present seed). Repair is model-dependent; identifiability, being a property of the sample, is not — on this instrument too. The mechanism was already validated on two instruments (§4.1); the synthesis result now is as well: a nonlinear plant with an angular, not positional, hard stop reproduces the same danger law and the same repair capability, so the repair finding is not a cart artifact.

## 8. Smooth learners cannot localize: both halves, measured

If localization is representational, two things must be checkable on non-code learners trained on the *same data* (`scripts/continuous_smooth_probe.py`; the two most favorable smooth learners: closed-form linear least squares — off the wall, the dynamics are *exactly linear*, so this is the smooth best case — and a small tanh MLP, probe-grade):

**Table 3 — smooth learners on the synthesis samples (x_wall = 8).**

| model | trained on | off-mode err mean / max | wall-probe err | gate ε=10⁻⁹ | gate ε=0.01 |
|-------|-----------|------------------------|---------------:|:---:|:---:|
| linear-LSQ | wall-free sample | 3.6e−15 / 1.7e−14 | 4.18 | **PASS** | **PASS** |
| linear-LSQ | wall-containing | 1.9e−03 / 1.2e−02 | 4.17 | fail | fail |
| MLP h=8 | wall-free sample | 3.5e−03 / 5.0e−02 | 4.20 | fail | fail |
| MLP h=8 | wall-containing | 6.0e−03 / 4.9e−02 | 4.19 | fail | fail |

- **Identifiability is learner-independent, live.** On the wall-free sample the linear model recovers the off-mode dynamics to 10⁻¹⁵, **passes the ε = 10⁻⁹ gate**, and is exactly as wall-blind as the synthesized blind code (probe error 4.18: it predicts straight through the wall). Proposition 2 instantiated on a second hypothesis class: in the gate-miss event, *any* accepted learner is blind. The (1−r)^N hole is not an LLM property.
- **With the mode in the data, code and smooth part ways.** Four contact rows out of 3200 tilt the linear fit by **twelve orders of magnitude** off-mode (1.7e−14 → 1.2e−02 max) — it fails both gates *and still* has the mode wrong (probe 4.17). The smooth hypothesis cannot put the error on the mode; it leaks everywhere (Proposition 4's geometry, observed as a least-squares tradeoff). The synthesized code, on the *same sample*, wrote the exact clamp and passed at float precision. The MLP combines both axes: a pervasive ~5e−3 floor that no gate accepts, and a never-learned mode.
- Consequence for the CWM paradigm: the paradigm *creates* in continuous control the localized failure class that the learned-model literature says does not dominate there — and, by the same representational fact, also creates the exact-repair capability that learned models lack. Code cuts both ways, and the gate's sampling coverage decides which way.

## 9. Related work

*Objective mismatch and model exploitation in MBRL* (Lambert et al. 2020; Janner et al. 2019; Hafner et al. 2020): prediction accuracy and control performance diverge for learned continuous models; planners exploit model errors. Our contribution to that conversation is the *verified-but-wrong localized* regime, which smooth learned models cannot even represent (Proposition 4, Table 3), plus a closed-form acceptance-failure law confirmed at gate scale. *Hybrid systems*: mode detection and identification of piecewise/hybrid dynamics is classical (e.g., PWA system identification: Paoletti, Juloski, Ferrari-Trecate & Vidal 2007; hybrid/logic-constrained control: Bemporad & Morari 1999); our question is not identifying the mode but what a *sampling verifier certifies* when the mode is missed, and what a planner then does. *Paper 1* is the discrete companion; this paper transfers its provable core, shows the empirical residual (translation-not-inference) does not transfer, and adds the representational theorem separating code from smooth hypotheses. *Property-based testing / rare-event simulation*: the gate is random testing of a program against an oracle; (1−r)^N is the standard rare-input coverage gap, here with the planner as the adversary that finds it. *Falsification and rare-event testing of hybrid and cyber-physical systems* (S-TaLiRo: Annpureddy, Liu, Fainekos & Sankaranarayanan 2011; survey: Corso, Moss, Koren, Lee & Kochenderfer 2021, JAIR): this literature searches for inputs that drive a hybrid system to violate a specification; our gate is the passive dual — uniform random testing whose blind spot is precisely the rare mode a falsifier would hunt for, and the (1−r)^N factor quantifies the coverage gap that random testing leaves. *Runtime monitoring and shielding for safe RL and control* (Alshiekh, Bloem, Ehlers, Könighofer, Niekum & Topcu 2018, AAAI): a synthesized shield overrides unsafe actions using an a-priori specification; our distrust-region fence is instead deployment-time feedback, built from observed prediction failures rather than a given safety automaton, and it corrects a certified-but-wrong model rather than an unsafe policy. *Robust MPC and planning under model uncertainty* (Rawlings, Mayne & Diehl 2017, *Model Predictive Control: Theory, Computation, and Design*): robust and tube-based MPC guarantees performance against *bounded* model error; the failure here is orthogonal — the error is unbounded but localized to an omitted mode and is certified away by the gate, so robustness margins tuned to the off-mode error do not see it. *System identification of contact-rich and discontinuous dynamics* (Paoletti et al. 2007; Fazeli, Kolbert, Tedrake & Rodriguez 2017, IJRR): estimating parameters and contact forces of rigid bodies undergoing frictional contact is a mature sysid problem; our repair-from-data result is the code analogue — given contact transitions in the sample, the synthesizer recovers the exact switching rule, whereas a smooth fit cannot localize it.

## 10. Limitations and honest assessment

- **Two minimal instruments, one dimension.** Cart-with-wall and pendulum-with-stop are minimal by design (as Beacon was in paper 1), and §4.1 shows the mechanism survives a nonlinear plant; §7 shows synthesis does too. But both modes are single stationary boundaries in a 2-dimensional state; multi-mode, moving-boundary, and higher-dimensional instruments (2D sticky patch, contact-rich manipulation) are future work. We expect the *mechanism* to survive — it is measure-theoretic — and the *repair* finding (§7) has now held on both instruments, but it could still weaken as mode geometry gets harder to induce from few examples on more complex instruments.
- **Two planner families, one fixed configuration each.** Random-shooting MPC occupies the high-query-reach/high-play-cost branch of Proposition 3; CEM occupies the low-query-reach/near-zero-play-cost branch (§4.2). This is stronger than a one-family result but not planner-universal: CEM was measured at one prototype-fixed setting, with no hyperparameter sweep, and its pendulum truth returns expose local optima. Its non-exploitation is reach-limited, not knowledgeable or safe — the same search that misses phantom reward can miss real distant reward. Gradient-based shooting and tree search (Coulom 2006; Kocsis & Szepesvári 2006) remain untested. Distrust-region replanning (§6) is a mitigation layered on MPC, not a third family; its hard-boundary guarantee and its behavior with other planners remain untested.
- **Synthesis cells are modest.** 20 seeds/cell on the headline x_wall = 8 cart cell for both GPT-5.x sizes, plus a 3-seed Qwen cross-family spot-check; the pendulum arm adds two knobs (headline and caught) at the same 20 seeds/cell, both sizes, plus its own 3-seed Qwen spot-check. The wall/mode-absent conditional is 20/20 across cart sizes and three runs (Wilson lower bound 0.84) and 18/18 pooled on the pendulum (lower bound 0.824); the GPT-5.x repair rate is 20/20 on the cart headline cell and 62/62 pooled on the pendulum. The cross-family arms are small-n (3 seeds plus one control per instrument per family) and cover two alternate families (Qwen, and Claude agent-relayed), not a sweep of models; they show repair is model-dependent *in mechanism* — Qwen 0/2 mode-present (superstitious patches), Claude repairing most but via a symmetry prior that oscillated on two seeds and certified one phantom, unfalsifiable mode.
- **The mode-blindness probe covers only the true mode's region.** By construction `mode_blindness` (`src/cwm/continuous/contract.py`) fires probes where the truth's mode is active, so it certifies whether the *revealed* mode is encoded but is blind to a mode the model *invents* elsewhere: Claude's phantom pendulum stop (§7) scored blindness 0.0 while carrying an extra, non-existent stop at θ = −1.4. Detecting invented modes needs code inspection, or probes seeded outside the sampled region — the classification alone does not suffice, and our phantom-mode finding rests on reading the certified code, as paper 1's artifact-level analysis does.
- **The MLP is a probe, not a baseline.** It substantiates the representational point at h=8/pure-Python scale; a tuned modern dynamics model would have a lower floor but the same structural inability to be bit-exact off a mode at ε = 10⁻⁹ (that is an argument, not yet a measurement, at scale).
- **Proposition 4 bounds geometry, not probability.** The ball is metric; converting to gate-visitation probability needs the gate measure on that ball, which is instrument-specific. The empirical complement (Table 3's twelve-orders tilt) carries the quantitative weight here.
- **Coverage certificates do not transfer.** Paper 1's enumeration-based guarantees have no continuous analogue in this draft; covering-number versions under Lipschitz assumptions are open.
- **play_cost > 1 is a normalization artifact** (blind < random), reported unclamped and explained; the headline claims never depend on the excess over 1.

## 11. Conclusion

Paper 1 ended by diagnosing the gate failure as a reach-distribution shift and prescribing verification on the distribution the planner visits. This paper shows the diagnosis is not about discreteness. The gate-miss law, the identifiability argument, and the play-cost bound are measure-theoretic and survive the move to continuous state spaces intact; what the move changes is *where the localized failure can live* (hybrid mode boundaries — an omitted mode is a rare rule) and *who can express it* (programs, not smooth function classes: Proposition 4 and Table 3). On two minimal hybrid instruments the entire paper-1 phenomenology reproduces — threshold law, knob-invariant exploitation, the reach mechanism — with the gate's acceptance rate closely tracking (1−r)^N at gate scale (within sampling noise; §5).

The synthesis experiment then delivers this paper's own finding: the continuous regime is the one where the danger law is *everything*. Given the mode in its sample, the LLM repairs it exactly — including from the synthesis examples alone — and when it fails to repair, the gate catches the superstitious patch; given the mode absent, every learner we tried (LLM, exact linear regression) is certified blind and the planner is exploited to below-random performance. The provable core is the gate-miss and identifiability propositions (§3): the mode-absent event is a hole no learner can close *from the sample* — a prior or the specification could still supply the mode — and its probability is in closed form. That no accepted artifact was ever wrong on a sample-covered transition is an empirical regularity of the models tested (GPT-5.x repairs; Qwen stalls and is refused; Claude repairs most, its symmetry prior certifying at most a mode the sample never covers), not a theorem. For practitioners the message is one clause sharper than paper 1's: in continuous code-world-model pipelines, *sample coverage of the mode boundaries is the whole game* — the synthesis stack will translate what it is told and repair what it is shown, and no stage of it can know about what the sample never touched.

---

## Appendix: reproduction

All CPU results (Tables 1–3 minus the LLM columns):

```bash
PYTHONPATH=src python scripts/continuous_reach.py          # danger-curve table (Table 1; ~2.5 min)
PYTHONPATH=src python scripts/continuous_axes.py           # axis-separation table (Table 2; ~3 min)
PYTHONPATH=src python scripts/continuous_smooth_probe.py   # smooth-learner table (Table 3; ~11 s)
PYTHONPATH=src python scripts/continuous_pendulum.py       # pendulum table (§4.1; ~2 min)
python scripts/make_paper2_figures.py                      # figures from the JSONs
python -m pytest tests/test_continuous*.py tests/test_smooth_fit.py  # 27 tests
```

LLM arms (Azure credentials in `.env`; see the runbook in
`docs/specs/2026-07-06-continuous-hybrid-cwm-design.md`):

```bash
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5 --x-wall 4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 5
# Pendulum synthesis arm (second instrument; Azure credentials as above)
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 20 --instrument pendulum --th-stop 1.4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 --instrument pendulum --th-stop 1.4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 20 --instrument pendulum --th-stop 1.0
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 --instrument pendulum --th-stop 1.0
# Qwen cross-family spot-checks (needs HF_TOKEN: HF Inference Providers router)
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 3 --compat-model "Qwen/Qwen3-Coder-30B-A3B-Instruct"
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 3 --instrument pendulum --th-stop 1.4 --compat-model "Qwen/Qwen3-Coder-30B-A3B-Instruct"
# Claude agent-relayed cross-family spot-check (agent scaffold relays pipeline-identical
# messages; see scripts/continuous_claude_step.py, results/continuous_claude_relay.json,
# results/claude_relay_transcripts/)
# Mitigation sweep (CPU only)
PYTHONPATH=src python scripts/continuous_mitigation.py
# eps-sensitivity sweep (CPU only)
PYTHONPATH=src python scripts/continuous_eps_sweep.py
# second planner family (CPU only)
PYTHONPATH=src python scripts/continuous_cem.py
```

Per-seed artifacts including the synthesized code: `results/continuous_synthesis_*.json`. Experiment log: `docs/EXPERIMENTS.md`, sections prefixed "PAPER 2".
