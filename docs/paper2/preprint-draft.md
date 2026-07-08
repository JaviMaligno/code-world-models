# An Omitted Mode Is a Rare Rule: The Sampling-Verification Danger Law in Continuous Code World Models

**Author:** Javier Aguilar Martín — AGILabs (javieraguilar.ai)
**Status:** First draft, 2026-07-07. Numbers from `docs/EXPERIMENTS.md` (§"PAPER 2 — ..." entries) and `results/continuous_*.json` — re-verify against the log before submission. Companion to *When a Verified World Model Still Loses* (paper 1), which studies the same failure in discrete games.

---

## Abstract

In the Code World Model (CWM) paradigm, a large language model synthesizes an executable world model that a classical planner then searches over, and the model is accepted when it matches sampled transitions. Paper 1 showed, in discrete games, that this gate certifies the wrong thing: a model can pass at 100% transition accuracy and still lose systematically at play, following a quantitative law, danger = play_cost × (1−rarity)^N. This paper moves the question to continuous state spaces, where the model-based RL literature holds that world-model error is *pervasive* rather than localized — and shows that the danger law not only transfers but becomes *exhaustive*.

Three results. **(1) The law is measure-theoretic, and its continuous home is hybrid dynamics.** The gate-miss factor (1−r)^N and the identifiability argument are statements about a measurable critical region, dimension-free; what is genuinely discrete in paper 1 is the *localization premise* — the wrong model is exact off the rule region — and we prove that a smooth (Lipschitz) truth/model pair cannot satisfy it: a large error confined to a metrically small region forces a large Lipschitz constant. The premise is realizable exactly where continuous systems are hybrid (contacts, hard stops, regime switches), and an omitted mode is precisely a rare rule. On a minimal hybrid instrument — a 1D cart with an inelastic wall whose position is the rarity knob — the paper-1 phenomenology reproduces sharply: rarity sweeps 0.33 → 0.002 while the mode-blind planner's regret stays flat at ~1.03 (it scores *below random*: model-predictive control drives into the phantom region and stays pinned against the wall for the entire episode, at every knob value), and the danger threshold law appears with the entire (1−r)^N elbow inside the sweep. **(2) The gate fails only where the law says it can.** With a pinned-integrator synthesis contract, a correct synthesis matches the truth to float precision, so the gate runs at ε = 10⁻⁹, and an axis-separation experiment shows the gate polices pervasive error (a supra-tolerance global bias is rejected on every rollout; a sub-tolerance bias passes and is harmless) while missing the localized hard mode exactly (1−r)^N of the time — the empirical pass rate matches the prediction. A smooth C∞ perturbation of comparable rarity has zero (or even *negative*) play cost: smoothness kills consequence, not detectability. **(3) In this regime the danger collapses to pure identifiability.** Running real LLM synthesis (GPT-5.x mini and large, 20 seeds/cell): with the wall absent from the sample — the (1−r)^N event, logged per seed — every synthesis (20/20 across model sizes) passes the gate fully wall-blind and is exploited at play (regret 0.999). But when the wall IS in the sample, GPT-5.x *repairs* it, writing the true global clamp rule (both sizes 10/10, large in ≤1 refinement iteration, some from the synthesis examples alone), unlike paper 1's symbolic setting where demonstrated rules were not learned. The failed repairs are superstitious local patches that the gate correctly rejects. A Qwen cross-family spot-check reproduces the blind-exploited event but repairs less reliably (0/2 wall-present) — identifiability is model-independent, repair is not. With the mode in the data the synthesize–refine–gate loop is therefore *sound* (it never accepts a wrong wall-present artifact), and the only unsoundness anywhere in the pipeline is the sampling event whose probability the law gives in closed form. A smooth-learner probe completes the picture: a linear least-squares model trained on wall-free data passes the same gate equally blind (identifiability is learner-independent), while 4 contact rows in 3200 tilt the same fit by twelve orders of magnitude off-mode — the mode cannot be localized by a smooth hypothesis. Localization — and hence both the danger and the repair — is a representational property of *code*.

---

## 1. Introduction

Paper 1 established, in discrete games, that transition accuracy on randomly sampled play-throughs is the wrong adequacy criterion for a world model used in planning, and quantified the failure: danger = play_cost × (1−rarity)^N, with the gate-miss factor exact under i.i.d. sampling. Its Related Work closed with a promissory note: the rare-rule gap is "a localized, discrete failure that state-accuracy metrics mask by dilution — a point worth revisiting in continuous settings," where the model-based RL literature (objective mismatch, Lambert et al. 2020; Dreamer, Hafner et al. 2020; MBPO, Janner et al. 2019) treats world-model error as pervasive and compounding rather than localized and pivotal.

This paper is that revisit. The question is not whether continuous world models can be wrong — that literature is mature — but whether the specific, *verified-but-wrong* geometry of paper 1 exists in continuous state spaces: a model that passes a sampling gate cleanly, is (in a precise sense) almost-everywhere correct, and still gets exploited catastrophically by the planner that trusts it.

The answer is yes, and the continuous version of the story is in one respect cleaner than the discrete one. Paper 1's headline had two components: a provable one (when the rare rule is absent from the sample, no learner can infer it — an identifiability event with probability exactly (1−r)^N) and an empirical one (the LLMs tested did not infer the rule *even when it was present* — "translation, not inference"). In the continuous instrument the second component **vanishes**: the LLM infers an omitted hybrid mode from a handful of boundary-crossing transitions, writing the exact global rule. What remains is the provable core, now standing alone: the gate–synthesis loop is sound whenever the data contains the mode, and unsound exactly on the (1−r)^N event. The danger law here is not just exact; it is exhaustive.

Contributions:

1. **Theory transfer, and one new piece.** The gate-miss proposition, the identifiability proposition, and the play-cost upper bound via query-hit mass transfer to continuous state spaces with only notational change (they are measure-theoretic; §3). The genuinely discrete ingredient of paper 1 is the *localization premise*, and we prove it requires unbounded local Lipschitz structure: for L-Lipschitz truth and model differing by η at a point, the disagreement region contains a metric ball of radius (η−ε)/2L (Proposition 4). Hybrid mode boundaries are exactly where this obstruction disappears — an omitted mode is a rare rule.
2. **Two minimal hybrid instruments** — cart-with-wall (linear off-mode plant) and pendulum-with-stop (nonlinear, gravity) — on which the full paper-1 phenomenology is measured with the same harness and no per-instrument re-calibration: threshold law with the whole (1−r)^N elbow inside the knob sweep, knob-invariant play_cost ≈ 1 (the exploited planner scores below random, pinned against the phantom mode all episode), and the reach mechanism in its cleanest form (exploited-planner mode reach flat at 1.00, random reach falling two orders of magnitude, truth-planner trajectory reach 0.00). Three instrument-design lessons of independent value for continuous CWM work are recorded (§2.3).
3. **A pinned-integrator gate and a measured axis separation.** Fixing the discretization in the synthesis contract makes correct code float-exact, so the gate runs at ε = 10⁻⁹ and the classic sub-tolerance/pervasive axis is a *control*, not a confound: the gate rejects supra-tolerance global bias on every rollout, passes sub-tolerance bias harmlessly, and misses the hard mode exactly (1−r)^N of the time (empirical pass rates match the prediction; §5). A smooth localized perturbation of comparable rarity has ≈0 — at higher amplitude *negative* — play cost.
4. **The synthesis result: danger collapses to pure identifiability.** Real-LLM arms (GPT-5.x mini/large, 20 seeds/cell) with the identifiability event logged per seed: wall absent → 20/20 verified-blind-exploited (regret 0.999, Wilson lower bound 0.84); wall present → repaired to the exact global rule (both sizes 10/10, large in ≤1 iteration), never a wrong artifact accepted. A Qwen cross-family spot-check reproduces the blind-exploited event but repairs neither wall-present seed (superstitious patches the gate rejects) — repair is model-dependent, identifiability is not. §6.
5. **Smooth learners cannot localize** (§7): the most favorable smooth learner (closed-form linear least squares — the off-mode dynamics are exactly linear) trained on wall-free data passes both gates fully blind (identifiability is learner-independent), and trained on wall-containing data is tilted twelve orders of magnitude off-mode by 4 contact rows in 3200 while still missing the mode. Both the danger geometry and the repair capability are representational properties of code.

Scope up front: one 1D instrument, one planner family (random-shooting MPC), 20 seeds on the headline synthesis cell (both GPT-5.x sizes) plus a 3-seed cross-family spot-check (not full sweeps), and a probe-grade (not tuned-baseline) MLP. §9 gives the honest assessment.

## 2. The instrument

### 2.1 Cart-with-wall

State (x, v); action a ∈ [−a_max, a_max]; semi-implicit Euler with fixed dt:

    a  = clamp(action)
    v' = v + (gain·a − drag·v)·dt
    x' = x + v'·dt

with defaults dt = 0.1, gain = 3.0, drag = 0.3, a_max = 1. The **hybrid mode** is an inelastic wall at x_wall: if x' ≥ x_wall, the next state is exactly (x_wall, 0). The **blind model** is the same code path with the wall branch removed — the hand-written on-manifold proxy for a CWM synthesized from a spec that omits the wall, *bit-exact off-mode by construction* (tested: exact float equality on wall-free trajectories). Reward is two sigmoid plateaus: a small reachable one on the left (0.3, at x ≤ −6) and a large one on the right (1.0, at x ≥ 12) whose approach every swept wall position blocks. Episodes are 80 steps from x₀ ~ U(−0.5, 0.5), v₀ = 0.

The design requirements mirror paper 1's material-at-cap instrument: (a) random rollouts rarely fire the mode — the wall position is the **rarity knob** (r sweeps 0.331 → 0.0020 over x_wall ∈ [2, 10]; Table 1); (b) the omission is *exploited*, not merely mispredicted — the wall-blind model predicts coasting through the wall toward the large plateau, so the planner it advises drives right and is pinned; (c) the truth planner's optimal play differs qualitatively — it goes left.

### 2.2 Planner and play_cost

The planner is model-predictive control by random shooting: at each step, sample candidate action sequences (piecewise-constant blocks plus the three constant sequences {−a_max, 0, +a_max}), roll each out on the *model*, take the best first action, replan. The planner is a deterministic function of its model's responses and the seed, so paper 1's play-cost upper bound via query-hit mass applies verbatim (§3). Single-agent control makes play_cost a normalized regret, cleaner than the two-player arena (no opponent confound):

    play_cost = (J_truth-planner − J_model-planner) / (J_truth-planner − J_random),

all returns measured in the true environment on paired seeds. The blind planner can score *below random* (it is actively exploited), so the normalized value can exceed 1; we report it unclamped.

### 2.3 Three instrument-design lessons (recorded because they will bite any continuous CWM study)

1. **I.i.d. per-step candidate sampling silently removes the mode from imagination.** With i.i.d. candidates, imagined displacement is diffusive; no sampled sequence reaches distant reward within the horizon, so the truth model and the blind model rank all candidates *identically* and the wall never enters imagination — the two arms become indistinguishable not because the models agree but because the planner never queries where they differ. Piecewise-constant blocks plus constant candidates fix it. (The planner's query distribution, not just its trajectory distribution, is part of the instrument.)
2. **Point (Gaussian) reward lodes demand braking finesse that random shooting lacks**; sigmoid plateaus remove the parking problem and give clean imagined-value margins in both directions.
3. **The plant's drag time-constant must sit well inside the planning horizon**, or no arm can act on the reward at all (our first calibration had τ = 1/drag = 10 s against a 3 s horizon; nothing moved).

## 3. Theory: what transfers, what changes, what is new

Notation: a verification gate draws N i.i.d. rollouts from the gate policy ρ (uniform-random actions from the initial-state distribution) and accepts a model f̂ if it matches the truth f within ε in sup-norm on every visited transition.

**Proposition 1 (gate miss; transfers verbatim).** Let R be any measurable set of rollouts ("the critical event"; here: the rollout fires the wall mode) with r = P_ρ(R). The probability that N i.i.d. gate rollouts all avoid R is exactly (1−r)^N. *Nothing in paper 1's proof uses discreteness; the event is Bernoulli(r) and the draws are i.i.d.*

**Proposition 2 (identifiability; transfers verbatim).** Condition on the miss event. Any two models that agree off the mode produce identical outputs on every sampled transition, so any score that is a function of the sample (the gate, a likelihood, a refinement objective) cannot distinguish them; preference for the correct one must come from the prior or the specification. In particular this holds for *any* learner — LLM, linear regression, MLP — a point §7 instantiates empirically.

**Proposition 3 (play-cost upper bound; transfers verbatim).** For any planner that is a deterministic function of model responses and a seed, |J(f) − J(f̂)| ≤ μ_query(E) where E is the disagreement region and μ_query the probability the planner queries its model on E during an episode. The coupling proof is unchanged; MPC's imagined rollouts are the queries. (Empirically our instrument saturates it: the blind planner queries the wall region in every episode and play_cost ≈ 1.)

**What does not transfer.** Paper 1's coverage certificates enumerate finite information-set spaces. Continuous state spaces admit no such enumeration; covering-number analogues under Lipschitz assumptions are left open (§9).

**What is new: the localization premise is a theorem-shaped obstruction.**

**Proposition 4 (smoothness forbids localized error).** Let f, f̂ : S ⊂ ℝᵈ → ℝᵈ be L-Lipschitz (sup-norm), and suppose ‖f(s₀) − f̂(s₀)‖∞ = η at some s₀. Then for any tolerance ε < η, the disagreement region R_ε = {s : ‖f(s) − f̂(s)‖∞ > ε} contains the metric ball B(s₀, (η−ε)/2L).
*Proof.* g = f − f̂ is 2L-Lipschitz, so for ‖s − s₀‖∞ < (η−ε)/2L, ‖g(s)‖∞ ≥ η − 2L·‖s−s₀‖∞ > ε. ∎

Read as its contrapositive: a model error that is *large somewhere* (large enough to matter at play) and *invisible at tolerance ε outside a metrically tiny region* requires L large — in the limit, a discontinuity. This is exactly the sense in which paper 1's localization premise ("the wrong model is exact off the rule region") is discrete: it is unsatisfiable by smooth truth/model pairs, up to the ball-radius quantification. Two consequences structure the paper: (i) the natural continuous home of the danger geometry is **hybrid dynamics** — contacts, hard stops, saturations, regime switches — where the truth itself has unbounded local Lipschitz constant across a mode boundary (our wall: v jumps to 0), and an omitted mode is precisely a rare rule; (ii) the premise is *representationally* available to programs (an omitted or added branch is bit-exact off the omitted case) and not to smooth learned models, a distinction §7 measures.

A caveat, stated because it is the honest boundary of Proposition 4: the ball is metric, and its *probability* under the gate's visitation measure can still be small — smoothness bounds how spatially concentrated an error can be, not how often the gate visits it. The proposition removes the *exact* localization premise for smooth pairs; the (1−r)^N mechanism itself is representation-independent and applies to any critical region of small visitation measure.

## 4. The mechanism and the threshold law

All numbers CPU-only, with the hand-written blind model as the on-manifold proxy (`scripts/continuous_reach.py`; 3000 rarity rollouts and 20 MPC episodes/arm per knob; Wilson 95% CIs in the results JSON).

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
- **play_cost is knob-invariant and > 1.** The blind planner is not merely uninformed; it is *exploited*: MPC on the wall-less model plans into the phantom region, is pinned at the wall (final x = x_wall exactly, contact rate 1.00 at every knob), and replans the same doomed plan every step — for the entire episode. It scores below random (0.00 vs 0.53). The 0.977 at x_wall = 10 is the sigmoid tail of the far plateau leaking J_blind = 0.94; the mechanism is unchanged.
- **The reach mechanism, in its cleanest form.** Paper 1 measured competent-vs-random reach of the rule region; here the exploited planner's mode reach is flat at 1.00 across the knob while random reach falls 165× — and the *truth* planner's trajectory reach is 0.00. The mode lives on the blind planner's deployment path and on the truth planner's *query* distribution (its imagination crosses the wall while deliberating; Proposition 3's μ_query), not on truth's trajectories. The danger factorization rides two different reach distributions, exactly as in paper 1, with the query/trajectory distinction now visible.
- Gate-miss exactness is re-verified in-tests (empirical P(N rollouts miss) vs (1−r)^N within binomial error) and again, at gate scale, in §5.

### 4.1 Robustness: the same law on a nonlinear plant

The cart's off-mode dynamics are linear, which is convenient for §7 but invites the worry that the phenomenology depends on it. A second instrument — a pendulum (gravity term sin θ, θ = 0 hanging down) with a hard angular stop, same interface, same MPC, same two-plateau reward on θ — reproduces the identical picture with *no* re-calibration (rarity is natural here: gravity confines the random walk near the bottom, so climbing to the stop is rare):

| θ_stop | rarity | J_truth | J_blind | play_cost | blind hit | d@N=40 |
|-------:|-------:|--------:|--------:|----------:|----------:|-------:|
| 0.8 | 0.2970 | 20.08 | 0.01 | 1.002 | 1.00 | 0.000 |
| 1.0 | 0.1277 | 20.08 | 0.03 | 1.002 | 1.00 | 0.004 |
| 1.2 | 0.0527 | 20.08 | 0.05 | 1.000 | 1.00 | 0.115 |
| 1.4 | 0.0193 | 20.08 | 0.12 | 0.997 | 1.00 | 0.457 |
| 1.6 | 0.0073 | 20.08 | 0.26 | 0.990 | 1.00 | 0.737 |
| 2.0 | 0.0000 | 20.08 | 1.23 | 0.942 | 1.00 | 0.942 |

Threshold law, knob-invariant exploitation (pinned at the stop in every episode, at every knob), truth planner untouched by the mode. The mechanism does not care that the plant is nonlinear — only that the mode is hard and rare under the gate's measure.

## 5. Axis separation: the gate fails only where the law says it can

The classic continuous-model failure axis is pervasive sub-tolerance error; the danger law's axis is a localized hard mode. A tolerance gate (ε = 0.01, deployment-realistic) must be shown to fail *only* on the second axis, and only at the (1−r)^N rate. Five arms, one table (`scripts/continuous_axes.py`; reveal-rarity = P(a random rollout contains a transition where truth and model differ > ε), 2000 rollouts; pass@40 over 300 independent N = 40 gates; 20 MPC episodes/arm):

**Table 2 — axis separation (ε = 0.01, N = 40).**

| arm | reveal-rarity | (1−r)⁴⁰ | pass@40 measured | play_cost | danger@40 |
|-----|--------------:|--------:|-----------------:|----------:|----------:|
| wall@4 omitted | 0.1385 | 0.0026 | 0.003 | 1.031 | 0.0027 |
| wall@8 omitted | 0.0125 | 0.6046 | 0.667 | 1.030 | 0.6227 |
| drag bias ×1.03 (sub-ε) | 0.0000 | 1.0000 | 0.997 | 0.000 | 0.0000 |
| drag bias ×2.0 (supra-ε) | 1.0000 | 0.0000 | 0.000 | 0.000 | 0.0000 |
| C∞ bump@4, amp 0.5 | 0.1875 | 0.0002 | 0.000 | 0.000 | 0.0000 |
| C∞ bump@4, amp 1.0 | 0.2085 | 0.0001 | 0.000 | −0.745 | −0.0001 |

Readings:

- **Gate exactness at gate scale.** Measured pass@40 matches (1−r)⁴⁰ in both wall rows (0.003 vs 0.0026; 0.667 vs 0.605, inside the 300-gate Wilson interval). The proposition is not asymptotic decoration; it is the observed acceptance rate.
- **The gate polices the pervasive axis.** A global drag bias above tolerance is revealed on *every* rollout (rarity 1.0) and never accepted; a sub-tolerance bias is accepted (0.997; the 0.3% is the extreme velocity tail nudging the error over ε) and is harmless at play (play_cost 0.000). Verified-and-fine is a real cell, and the gate finds it.
- **Danger lives in one quadrant only**: rare ∧ hard-mode. Common hard mode (wall@4): caught, danger ≈ 0.003. Pervasive error: caught or harmless. Smooth localized: next point.
- **Smoothness kills consequence, not detectability.** The C∞ drag bump at the wall's location has *comparable rarity* to the wall (0.19 vs 0.14 — it is just as detectable, confirming that Proposition 4 is about error *geometry*, not about hiding from the gate) yet play_cost 0.000 at amplitude 0.5: both planners cross it, one of them slightly surprised. At amplitude 1.0 play_cost turns *negative* (−0.745): the truth planner, seeing the slowdown near its horizon edge, is over-pessimistic and often settles for the small plateau, while the bump-blind planner pushes through and wins. A smooth localized omission produces planner-side timing effects of ambiguous sign; only the hard mode produces the one-way exploitation geometry (pinned, forever, below random).

## 6. LLM synthesis: the danger collapses to pure identifiability

Real-LLM arms (`scripts/continuous_danger_synthesis.py`; Azure GPT-5.x mini and large; N = 40 training rollouts which double as the gate, as in paper 1's sweep; ε = 10⁻⁹ pinned-integrator gate; **20 seeds/cell on the headline x_wall = 8 cell, both sizes** (paper-1 standard); 6 MPC play episodes/seed; per-seed JSON with the synthesized code versioned in `results/`). The contract pins the integrator (§2.1's equations, stated in the spec text, constants generated from the environment instance so they cannot drift); the *full* arm includes the wall clause, the *incomplete* arm omits it. Crucially, each seed logs whether the wall fired in its training sample — the identifiability event that paper 1 could not condition on post hoc.

**Full arm (both sizes, 40 seeds): gate 1.000 in 0 refinement iterations, wall probes exact, play at truth parity — every seed.** The pinned-integrator premise holds with a real LLM: correct synthesis is float-exact through the sandbox, so ε = 10⁻⁹ costs nothing and the tolerance axis is fully disarmed. As in paper 1, given the rule, the model translates it perfectly.

**Incomplete arm.** Three-way structure, exactly as the design predicted on two of three branches and *informatively opposite* on the third:

1. **Wall absent from the sample (the (1−r)^N event; 10/20 seeds at x_wall = 8 for each size, consistent with (1−0.0125)⁴⁰ ≈ 0.60):** every such seed — **20/20 across mini and large** — passed the gate at 1.000, fully wall-blind on the probes (1.0), and was exploited at play: pinned at the wall, contact rate 1.0, **play_cost 0.999**. Wilson 95% on P(accepted-blind | wall missed): lower bound 0.72 per size, **0.84 combined (20/20)**. This is paper 1's headline, synthesized end-to-end in a continuous CWM: a verified, almost-everywhere-exact model that performs worse than random.
2. **Wall present, repaired:** the LLM does *not* stay blind. It reads the failing transitions and writes the true global rule — `if x2 >= 8.0: return [8.0, 0.0]` (or the equivalent `if x2 > 8.0: x2 = 8.0`) — not a curve fit. At 20 seeds both sizes repaired **every** wall-present seed: **large 10/10 in 0–1 iterations** (two from the synthesis examples alone, 0 iterations), **mini 10/10 in 0–5 iterations** (one at 0). This is the divergence from paper 1, where rules demonstrated by example transitions were persistently not learned ("translation, not inference"). A numerically-manifested discontinuity is learnable from data in a way a symbolic game rule was not.
3. **Wall present, not repaired:** at 20 seeds on the headline cell GPT-5.x produced **no stalls** — but stalls are real and instructive where they occur (the 5-seed x_wall = 4 cell, and the Qwen cross-family arm below). They are not near-misses of the rule but **superstitious local patches**: e.g. `if abs(x2 - 8.0) <= 0.15 and abs(v2) <= 1.1: x2 = 8.0`, or Qwen's `if x2 >= 8.0 and v2 <= 0.0: ...` — clamps fitted to the *observed manifestation* of the mode (low-speed, near-wall contacts), which mispredict other approaches to the wall. **The gate rejected every one of them** (gate 0.49–0.998, never 1.000).

**Cross-family spot-check (HF router, `Qwen/Qwen3-Coder-30B-A3B-Instruct`, 3 seeds).** The full arm is clean (3/3 gate 1.000, blind 0.0): the pinned-integrator premise is not GPT-specific. On the incomplete arm the identifiability branch reproduces (the 1/3 wall-absent seed is gate-1.000 wall-blind and exploited, play_cost 0.999) — but Qwen **repaired neither** of its two wall-present seeds (gate 0.999 and 0.491, both superstitious patches the gate refused). So repair-from-data is *model-dependent* while identifiability is not: the wall-absent blind-and-exploited event is a property of the sample (it fired for every model tried), whereas how reliably the loop recovers a *revealed* mode — and thus how much of paper 1's (b)-residual it erases — varies with the synthesizer. GPT-5.x erases it entirely on this instrument; Qwen does not.

The branches compose into the paper's central claim. With the mode in the data, the synthesize–refine–gate loop is *sound*: it either recovers the exact mode or refuses the artifact (true for every model — the gate never accepted a wrong wall-present artifact). With the mode absent, no loop can help (Proposition 2), and the acceptance of a blind artifact is not a failure of the LLM, the refinement, or the gate implementation — it is the sampling event whose probability is exactly (1−r)^N. Paper 1's danger law had a provable core plus an empirical residual (the rule not learned even when shown); in the continuous instrument the residual *can* vanish — it does for GPT-5.x, which repairs every revealed mode — so **the law becomes the entire failure surface** for a capable-enough synthesizer, and shrinks toward it even for a weaker one. The actionable consequence sharpens correspondingly: in this regime, spec completeness and gate-sample coverage are not two independent worries — coverage *is* the dominant worry, because the synthesis loop repairs what the sample reveals.

(Scope: 20 seeds/cell on the headline cell, both GPT-5.x sizes; the wall-absent conditional is 20/20 across sizes and consistent across three independent runs; the wall-present repair rate is 20/20 for GPT-5.x on this cell and 0/2 for Qwen — model-dependent, small-n on the cross-family arm. LLM synthesis is stochastic across calls; the three-way structure and the identifiability conditional are stable run-to-run, per-seed iteration counts are not.)

**Second-instrument robustness (pendulum-with-stop, §4.1, 20 seeds/cell, both sizes).** The synthesis arm is not cart-only. Running the identical pipeline on the nonlinear pendulum — headline θ_stop=1.4 (rarity 0.019) and caught θ_stop=1.0 (rarity 0.128, mode present in essentially every sample) — reproduces every branch. Full arm clean at every cell (80/80 GPT-5.x, 3/3 Qwen). At the headline knob the mode-absent identifiability event fired in 9/20 seeds per size, and every occurrence (18/18 pooled across knobs and sizes) was blind and exploited at play_cost 0.995 (Wilson 95% lower bound 0.824; per-size headline 9/9, lower bound 0.701) — the same fixed-point exploitation as the cart's play_cost ≈ 1. Pooled across both knobs and both sizes, GPT-5.x repaired **62/62** mode-present seeds to the exact angular clamp (`if th2 >= θ_stop: return [θ_stop, 0.0]`), 0 stalls (Wilson 95% lower bound 0.942) — including all 40/40 at the caught knob alone. A Qwen cross-family spot-check (3 seeds, θ_stop=1.4) reproduces the mode-absent blind-exploited event (1/1) but stalls on both mode-present seeds (gate 0.9997, 0/2 repaired), the same superstitious-patch signature as on the cart. Repair is model-dependent, identifiability is not — on this instrument too. The mechanism was already validated on two instruments (§4.1); the synthesis result now is as well: a nonlinear plant with an angular, not positional, hard stop reproduces the same danger law and the same repair capability, so the repair finding is not a cart artifact.

## 7. Smooth learners cannot localize: both halves, measured

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

## 8. Related work

*Objective mismatch and model exploitation in MBRL* (Lambert et al. 2020; Janner et al. 2019; Hafner et al. 2020): prediction accuracy and control performance diverge for learned continuous models; planners exploit model errors. Our contribution to that conversation is the *verified-but-wrong localized* regime, which smooth learned models cannot even represent (Proposition 4, Table 3), plus a closed-form acceptance-failure law confirmed at gate scale. *Hybrid systems*: mode detection and identification of piecewise/hybrid dynamics is classical (e.g., PWA system identification); our question is not identifying the mode but what a *sampling verifier certifies* when the mode is missed, and what a planner then does. *Paper 1* is the discrete companion; this paper transfers its provable core, shows the empirical residual (translation-not-inference) does not transfer, and adds the representational theorem separating code from smooth hypotheses. *Property-based testing / rare-event simulation*: the gate is random testing of a program against an oracle; (1−r)^N is the standard rare-input coverage gap, here with the planner as the adversary that finds it.

## 9. Limitations and honest assessment

- **Two minimal instruments, one dimension.** Cart-with-wall and pendulum-with-stop are minimal by design (as Beacon was in paper 1), and §4.1 shows the mechanism survives a nonlinear plant; §6 shows synthesis does too. But both modes are single stationary boundaries in a 2-dimensional state; multi-mode, moving-boundary, and higher-dimensional instruments (2D sticky patch, contact-rich manipulation) are future work. We expect the *mechanism* to survive — it is measure-theoretic — and the *repair* finding (§6) has now held on both instruments, but it could still weaken as mode geometry gets harder to induce from few examples on more complex instruments.
- **One planner family.** Random-shooting MPC with piecewise-constant candidates. The exploitation geometry (pinned forever, below random) is planner-mediated; a planner with online model-error feedback (e.g., replanning on prediction-violation) would break the loop — that is a mitigation claim consistent with our thesis (verify on the deployment distribution), not against it.
- **Synthesis cells are modest.** 20 seeds/cell on the headline x_wall = 8 cart cell for both GPT-5.x sizes, plus a 3-seed Qwen cross-family spot-check; the pendulum arm adds two knobs (headline and caught) at the same 20 seeds/cell, both sizes, plus its own 3-seed Qwen spot-check. The wall/mode-absent conditional is 20/20 across cart sizes and three runs (Wilson lower bound 0.84) and 18/18 pooled on the pendulum (lower bound 0.824); the GPT-5.x repair rate is 20/20 on the cart headline cell and 62/62 pooled on the pendulum. Both cross-family arms are small-n (3 seeds) and show repair is model-dependent (Qwen 0/2 mode-present on each instrument) — a single alternate family, not a sweep of models.
- **The MLP is a probe, not a baseline.** It substantiates the representational point at h=8/pure-Python scale; a tuned modern dynamics model would have a lower floor but the same structural inability to be bit-exact off a mode at ε = 10⁻⁹ (that is an argument, not yet a measurement, at scale).
- **Proposition 4 bounds geometry, not probability.** The ball is metric; converting to gate-visitation probability needs the gate measure on that ball, which is instrument-specific. The empirical complement (Table 3's twelve-orders tilt) carries the quantitative weight here.
- **Coverage certificates do not transfer.** Paper 1's enumeration-based guarantees have no continuous analogue in this draft; covering-number versions under Lipschitz assumptions are open.
- **play_cost > 1 is a normalization artifact** (blind < random), reported unclamped and explained; the headline claims never depend on the excess over 1.

## 10. Conclusion

Paper 1 ended by diagnosing the gate failure as a reach-distribution shift and prescribing verification on the distribution the planner visits. This paper shows the diagnosis is not about discreteness. The gate-miss law, the identifiability argument, and the play-cost bound are measure-theoretic and survive the move to continuous state spaces intact; what the move changes is *where the localized failure can live* (hybrid mode boundaries — an omitted mode is a rare rule) and *who can express it* (programs, not smooth function classes: Proposition 4 and Table 3). On a minimal hybrid instrument the entire paper-1 phenomenology reproduces — threshold law, knob-invariant exploitation, the reach mechanism — with the gate's acceptance rate matching (1−r)^N at gate scale.

The synthesis experiment then delivers this paper's own finding: the continuous regime is the one where the danger law is *everything*. Given the mode in its sample, the LLM repairs it exactly — including from the synthesis examples alone — and when it fails to repair, the gate catches the superstitious patch; given the mode absent, every learner we tried (LLM, exact linear regression) is certified blind and the planner is exploited to below-random performance. The loop is sound except on one event, and the probability of that event is in closed form. For practitioners the message is one clause sharper than paper 1's: in continuous code-world-model pipelines, *sample coverage of the mode boundaries is the whole game* — the synthesis stack will translate what it is told and repair what it is shown, and no stage of it can know about what the sample never touched.

---

## Appendix: reproduction

All CPU results (Tables 1–3 minus the LLM columns):

```bash
PYTHONPATH=src python scripts/continuous_reach.py          # Table 1 (~2.5 min)
PYTHONPATH=src python scripts/continuous_axes.py           # Table 2 (~3 min)
PYTHONPATH=src python scripts/continuous_smooth_probe.py   # Table 3 (~11 s)
PYTHONPATH=src python scripts/continuous_pendulum.py       # §4.1 (~2 min)
python scripts/make_paper2_figures.py                      # figures from the JSONs
python -m pytest tests/test_continuous*.py tests/test_smooth_fit.py  # 27 tests
```

LLM arms (Azure credentials in `.env`; see the runbook in
`docs/specs/2026-07-06-continuous-hybrid-cwm-design.md`):

```bash
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5 --x-wall 4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 5
```

Per-seed artifacts including the synthesized code: `results/continuous_synthesis_*.json`. Experiment log: `docs/EXPERIMENTS.md`, sections prefixed "PAPER 2".
