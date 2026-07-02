# Research Direction — toward a preprint

Status as of 2026-06-24. This doc is the handoff: it captures the research
direction, the validated candidates, and the concrete next steps so work can
resume without re-deriving context.

## Where the project stands

- **MVP loop (perfect information):** synthesize a world model in code → refine
  in sandbox to full-contract transition accuracy 1.0 → MCTS → arena vs a
  large-model LLM-as-policy baseline → cost meter. Implemented for **tic-tac-toe**
  and **Connect Four** via a multi-game registry (`src/cwm/games.py`,
  `CONTRACT_API` + per-game `RULES_TEXT`). 63 tests. Results in
  [EXPERIMENTS.md](EXPERIMENTS.md).
- **Cost gate decided:** running via Azure OpenAI API is trivially cheap
  (~$0.001–0.005/game baseline; synthesis is one-off). No Codex fallback needed.
- **Known-game results:** small-model CWM+MCTS dominates the large model as a
  direct policy (up to 30–0 in Connect Four). The thesis of arXiv:2510.04542
  reproduces — but reproduction alone is NOT preprint-worthy.

## The original contribution we pursued — and the null result

**The gap between "verified" and "correct."** The acceptance gate is
*transition accuracy 1.0 on random-policy trajectories*. The hypothesis was that
MCTS visits a different distribution (search-promising, often OOD) where a
gate-passing world model could still be wrong. We built the measurement harness
(`cwm/gap.py`, `run_gap.py`) and ran it across three knowledge regimes — correct
prior (Gen-TTT 6×6), no prior (army5x5a), wrong prior (Trike) — both with the
rules given (translation) and withheld (`--no-rules`, pure inference).

**Result (2026-06-24): the gap does not appear.** See EXPERIMENTS.md. In every
regime the outcome is binary — either the model produces a globally-correct CWM
(gap ≈ 0) or it fails the gate entirely. There is no "passes the gate but wrong
on the search distribution" case. Diagnosis: for these small, fully-specified
games the random-trajectory sample **identifies** the dynamics — no compact wrong
hypothesis fits 40 random games yet diverges elsewhere (no under-determination).
The gate is not weak; it is identifying. Secondary findings: the binding
constraint is **gate-attainability** (game complexity × model scale; nano fails
army5x5a 5/5), and the whole method leans on the rules being *given* (no-rules
inference collapses to 0% for novel games).

## The pivot — manufacturing under-determination (a "rare-rule" game)

A real gap needs **sample under-determination**: a rule R with
P(R triggers | random play) ≈ 0 but P(R triggers | optimal play) high, on a base
the model *can* synthesize (else it fails the gate and there is no candidate).

**Lead instrument (proposed 2026-06-24, not yet built):** Connect Four (recalled
base → gate passes) + a rarely-reached, planner-forceable instant-win rule, e.g.
"placing the disc that fills the top-centre cell (row 0, col 3) wins." Columns
rarely fill under random play (games end on a 4-in-a-row first) → R is absent
from the 40 training trajectories → a `--no-rules` CWM recalls standard CF and
**omits R** → passes the gate → MCTS on the *true* game forces R → divergence.

Two methodology notes for this experiment:
1. **Headline must be `gap_truth = agreement(D_gate) − agreement(D_truth)`.** A CWM
   that omits R never explores R's region itself, so D_cwm won't diverge; the
   correct-planner distribution D_truth exposes the omission.
2. **Validate empirically first** (as with non-triviality): confirm R fires in
   ~0/40 random games but MCTS-on-truth uses it. Fallback rules if too
   rare/un-forceable: a rule needing a near-full board, or a short advantageous
   tactic on a specific central line.

**RESULT (2026-06-25): the instrument worked — but the metric had to change.**
Top-centre and other Connect-Four rules failed (rarity↔consequence tension; see
EXPERIMENTS.md). A random-vs-competent **divergence** measurement selected
**army5x5a** as the base, and a **material-at-cap** rule (deep tail: at the ply
cap, more material wins instead of a draw) landed in the rare∧consequential
quadrant (~1% of random games, ~50% of competent games). Built as
`groundtruth/gen_chess_material.py` with paired `army5x5a_material` (complete) /
`army5x5a_material_incomplete` (rule withheld) specs.

Key correction to the metric: **`gap_truth` (state agreement) is the WRONG lens.**
A rare-but-pivotal rule error is *diluted* — the divergence region is <1% of
visited states, so gap_truth ≈ 0 even when the CWM is wrong, and symmetric MCTS
self-play barely visits it. The right metric is **play performance**: a
CWM+MCTS agent vs a ground-truth+MCTS agent in the true game (`run_gap
--play-games`, `_play_performance`). Result: the rule-omitting CWM (gate-passing,
gap_truth = 0, ≥99% state-accurate) **loses ~2:1** — win rate **0.383 vs a
calibrated 0.504 baseline** (`scripts/play_cost.py`), reproducible across seeds;
the complete-rules control plays near baseline.

**Headline contribution:** transition/state accuracy is the wrong adequacy
criterion for a planning world model. A model can pass sampling-based
verification and be state-accurate yet systematically lose, because the <1% it
gets wrong is the pivotal tactic. Adequacy must be measured by play. Connects to
the cognitive-debt article: verifying on the wrong signal = false security.

**Possible follow-ups:** (a) search-guided synthesis — refine the CWM on the
states MCTS actually visits (DAgger), and measure how much play performance
recovers; (b) the `--no-rules` / `--with-rules-but-buggy-rare-branch` variants;
(c) write up (blog + preprint) around the play-vs-accuracy adequacy result.

### Repair spikes (2026-06-26) — the fix is non-trivial; a dose-response

Tested on army5x5a + material-at-cap, INCOMPLETE rules (mini synthesizer). Play
winrate vs the true game (baseline 0.28; fair truth-vs-truth 0.50):

| method | discriminating examples | gate | winrate |
|--------|-------------------------|------|---------|
| baseline (random trajectories) | 0 | 1.000 (false security) | 0.28 |
| naive DAgger (dump competent traj) | ~2 | 0.9996 (detects) | 0.28 |
| proper DAgger (flawed model's game path) | 4–5 / round | 0.993 (detects) | 0.28–0.33 |
| targeted generation | 35 | 0.971 | 0.42 |
| targeted generation | 120 | (this run) | (this run) |

Key facts established: random/competent play barely generate the discriminating
cap+unequal-material transition (random ~0%; competent 2/20; the rule-BLIND
model's own game path 6/20 — 3× more, DAgger's premise). Verifying on the
play/search distribution **detects** the gap (gate drops below 1.0); **repair**
needs many discriminating examples — a dose-response (0→0.28, 35→0.42).

### If repair plateaus: diagnose the ceiling (do NOT stop at "it stalled")

Pre-registered battery (each isolates one hypothesis):
1. **Model inference limit** (mini can't infer "more material wins" from
   examples): control = COMPLETE rules + targeted (already in this run); if
   complete→0.50 but incomplete plateaus, the ceiling is inference. Sub-diagnose
   with a larger synthesizer (gpt-5.4 large), declarative rule vs examples-only,
   and a code probe (does generated code attempt the rule but buggily, or not at
   all?).
2. **Data/coverage limit**: dose-response sweep 0/35/120/300 — does the curve
   keep rising or saturate?
3. **Gate/metric limit**: final `acc` < 1.0 with refiner unable to close the
   residual failures — inspect which.
4. **Search limit**: ruled out (truth-vs-truth = 0.50 at 400 sims), keep in mind.

"Can LLMs infer rare rules from examples, and where is the ceiling by model size
/ supervision form?" is itself a complementary preprint angle.

## Validated candidates (deep-research 2026-06-24)

- **gpt-5.4 knowledge cutoff: 2025-08-31** (snapshot gpt-5.4-2026-03-05).
  Caveat: "post-cutoff = uncontaminated" is NOT a hard guarantee — hence the
  declarative probe, which we ran.
- **Primary anchor: Generalized Chess `army5x5a`** (DeepMind, arXiv:2510.04542,
  Appendix H.5). 5×5 board, win by capturing the opponent's *general*. Probe
  result: gpt-5.4 does NOT know the movesets → clean inference target.
  Known move offsets (from deep-research extraction of the PDF):
  - general:  `[(1,0),(-1,0),(0,1),(0,-1),(0,-2),(0,2)]`
  - infantry: `[(1,0),(2,0),(1,-1),(1,1),(-1,0)]`
  - cavalry:  `[(0,3),(1,2),(2,1),(3,0)]`
  - **OPEN:** exact starting positions / army composition (how many of each
    piece and where) are NOT yet extracted — pull from Appendix H.5 of the PDF
    (https://arxiv.org/pdf/2510.04542) when implementing.
- **Secondary: Generalized Tic-Tac-Toe 6×6 win-4** (Appendix H.4). m,n,k(6,6,4).
  Probe: model knows it → weak anti-recall, use as the correct-prior baseline.
- **Generator: gg-bench** (arXiv:2505.07215, repo `vivek3141/gg-bench`) — mints
  fresh non-contaminated games on demand; safest against contamination; gives N
  games for statistics. Regenerate fresh instances (the released corpus is public).
- **Trike** (Erickson 2020) — partial contamination (knows metadata, confabulates
  mechanics). REAL rules: each turn place a disc of your color on an empty cell
  on the pawn's line (not beyond existing discs), then move the shared pawn onto
  that disc; game ends when the pawn is surrounded; score = your discs adjacent
  to the pawn; no draws. Now elevated from "obscure validation" to the
  **wrong-prior regime** — the most interesting case.
- **Imperfect-information round (separate, with inference function + ISMCTS,
  OpenSpiel):** poker (Kuhn/Leduc) + DeepMind's two imperfect-info novel games
  **Quadranto** (H.8) and **Hand of War** (H.9).

## Non-triviality caveat

Non-triviality confirmed empirically (2026-06-24, `scripts/nontriviality_sweep.py`):
MCTS beats random from both sides on Gen-TTT(6,6,4), army5x5a, and Trike (zero
losses). army5x5a is balanced under strong search (MCTS-vs-MCTS ~P1 2/P2 3/5 draws
over 10 at 800 sims). See EXPERIMENTS.md.

## Next steps (resume here)

DONE (2026-06-24/25): gap harness built (merge 79165bf); state-agreement gap is
**null** across regimes; rarity↔consequence tension found (6 rules);
divergence-selected **army5x5a + material-at-cap** instrument built and run; the
**play-performance** result lands the headline — a verified, gap_truth=0,
≥99%-state-accurate CWM that omits the rule **loses ~2:1** (0.383 vs 0.504). All
in EXPERIMENTS.md; code on `main`.

DONE (2026-06-26): **quantitative law established** (EXPERIMENTS.md "Quantitative
law"). `danger = play_cost × (1−rarity)^N`; play_cost ~constant 0.12 (competent
play always reaches the rule region), rarity swept cheaply. Threshold curve: harm
≈0 while the rule is common enough for the gate to catch, rises as it gets rare,
plateaus at full play_cost once it escapes; N shifts the threshold. This is the
breadth/generality the result needed.

1. **Write it up** — the result is ready: *transition/state accuracy is the wrong
   adequacy criterion for a planning world model; adequacy must be measured by
   play* + the quantitative danger law + the translation-not-inference repair
   finding. Blog (connects to cognitive-debt) + preprint. Strongest framing we have.
2. **(Optional) Search-guided synthesis** — refine the CWM on MCTS-visited states
   (DAgger) and measure how much play performance recovers. Strengthens the
   preprint with a fix, not just a diagnosis.
3. **(Optional) Tighten the play result** — more seeds/sims, confidence intervals,
   and the synthesized-CWM (not just hand-written base) at scale.
4. Imperfect-information round (poker + Quadranto + Hand of War).
5. **Rethink applications beyond games (open, deliberate brainstorm needed).**
   The Code World Model pattern (LLM synthesizes a verifiable executable model
   from examples + classical planning/checking on top) may transfer to non-game
   domains — e.g. business rules / pricing (connects to the author's real work
   and to the cognitive-debt blog article), workflows, operations/scheduling,
   API behavior modeling. Harder to make publishable (noisy/partial-observability
   dynamics, single-case generalization risk); likely a strong 2nd blog article
   unless a general, clean non-game domain is found. Worth a dedicated
   brainstorm — what is the most valuable, original non-game application?

---

## The coverage bound (formal) — turning the imperfect-info null into a theorem

The Kuhn and Leduc nulls are not just "we ran it and found nothing." They are an
instance of a provable statement about when an inference gate sampled on random
play is **identifying**. Stating it as a bound (proof, not experiment) also yields
the design spec for a game on which Claim A *can* be positive.

**Setup.** A finite two-player extensive-form game **with perfect recall**, chance
(the deal) and imperfect information. `b` = maximum, over **player** information
sets `I`, of `|A(I)|` (the number of actions available at `I`); chance is handled
separately through `p_chance`. `d(I)` = number of player-action edges on a shortest
history reaching information set `I`; `d_max = max_I d(I)`; `p_chance` = minimum
probability of a deal consistent with any reachable info-set; `𝓘` = set of
reachable info-sets. The uniform-random policy `ρ` plays every legal action with
probability `1/|A(I)| ≥ 1/b`, and so assigns positive probability to every legal
action (full support).

**Lemma 1 (full-support inclusion).** Because `ρ` assigns positive probability to
every legal action, `supp(π^σ) ⊆ supp(π^ρ)` for every profile `σ`; equivalently,
`reach(σ) ⊆ reach(ρ)`.
*Proof.* This is the standard fact that a fully-mixed strategy reaches every node
reachable under any profile. Reach of an info-set is taken under the actual
interactive profile (planner + opponent + chance); since chance edges are shared
and `ρ` dominates each player's per-edge contribution (`ρ`-probability `≥ 1/b > 0`
on every player edge), any history `h` with `π^σ(h) > 0` has `π^ρ(h) > 0`. ∎

**Lemma 2 (reach lower bound under ρ).** Every reachable `I` has
`π^ρ(I) ≥ p_chance · b^{-d(I)} ≥ p_chance · b^{-d_max}`.
*Proof.* Take one history `h ∈ I`. Along `h` each player edge at info-set `I_t`
has `ρ`-probability `1/|A(I_t)| ≥ 1/b`, so the **realization probability** of `I`
(in the sense of von Stengel 1996's sequence form) satisfies
`π^ρ(h) = π_chance(h)·∏_t 1/|A(I_t)| ≥ p_chance · b^{-d(h)}`, and
`π^ρ(I) ≥ π^ρ(h)`. ∎

**Theorem (the gate is identifying when N ≳ b^{d_max}).** Draw `N` i.i.d. games
under `ρ`. The probability that some reachable info-set is never visited is
`≤ |𝓘| · exp(−N · p_chance · b^{-d_max})` (union bound + Lemma 2). Hence for
`N ≳ b^{d_max} · p_chance^{-1} · log|𝓘|`, the sample covers **every** reachable
info-set w.h.p. — and by Lemma 1 every info-set any policy (incl. a competent
planner) relies on. An inference function whose error is confined to reachable
info-sets is then detected w.h.p., so **no gate-passing inference function can be
play-inadequate through a coverage gap.** ∎

**Remark (equilibrium-robustness).** The sufficiency direction (coverage ⇒
identifying) does not depend on the reference distribution being MCTS reach.
Because `ρ` has full support, `reach(σ*) ⊆ reach(ρ)` for the Nash / best-response
profile `σ*` exactly as for any other profile (Lemma 1). The bound therefore
certifies coverage of every info-set that *equilibrium* play relies on, not merely
those the deployed planner visits — a strength rather than a caveat. Substituting
equilibrium reach for MCTS reach would change which info-sets are deemed relevant
(and hence the numbers) but not the sufficiency argument.

**Corollary (Kuhn, Leduc).** Kuhn: `b=2, d_max≈2` → covered at any `N`. Leduc:
`b=3, d_max≈8` → `b^{d_max}≈6561`, so `N≈8000` already covers everything —
matching the measured `0/1259` competent-only inference-relevant info-sets.

**Design corollary (the bigger game).** A coverage gap is *possible* only when
`b^{d_max} ≫ N` at feasible `N`, i.e. **large branching and/or large depth**, with
hidden information making inference non-trivial, and a competent policy that
concentrates reach on a deep region of `ρ`-measure `≪ 1/N`. Then the gate
(`ρ`-sampled) provably misses that region while the competent planner relies on
it: a wrong inference confined there passes the gate yet loses at play. In
game-theoretic terms, the gap lives on info-sets reached with negligible
probability under the **sampling policy** but on-path under **optimal play** —
off-equilibrium-path-style info-sets that the verification distribution does not
discipline. This is the exact analogue of the perfect-info rare-rule gap, which
exploited **game depth** (competent play reaches the ply cap; short random games
never do).

**Note on epistemic status of the paper's claims.** Existence claims (the
verified-vs-correct gap exists; translation-not-inference) are properly empirical —
one rigorous instance with CIs suffices. The coverage result above and the danger
law's N/rarity dependence below are genuine theorems, with the experiments as
instantiations. Only `play_cost` and its approximate rarity-invariance are
irreducibly empirical.

---

## The danger law (formal) — the gate-miss factor is exact, not a fit

`src/cwm/law.py` defines `danger(play_cost, r, N) = play_cost · (1 − r)^N`, where
`r` = rarity = the probability that a single uniform-random play-through is decided
by the rule (`rarity()` measures exactly this Bernoulli rate). The N/r dependence
is not an empirical fit — it is forced by the gate's sampling procedure.

**Proposition (gate-miss probability).** A sampling gate draws `N` i.i.d.
uniform-random play-throughs and detects the rule iff at least one of them is
decided by the rule. Since each play-through is decided by the rule independently
with probability `r`, the probability the gate observes the rule in none of its
`N` draws is exactly
`P(miss) = (1 − r)^N ≈ e^{−Nr}`.
*Proof.* Independence of the `N` i.i.d. draws; each is a Bernoulli(`r`) "rule
fired" event; `P(all N are 0) = (1−r)^N`. ∎

**Corollary (expected play-harm of a size-N gate).** Let `κ = play_cost` be the
expected play-deficit of a planner whose CWM omits the rule, conditional on the
omission surviving the gate (rule still operative in real play). The expected harm
from gating at size `N` is `danger(N) = κ · (1 − r)^N`. The `(1−r)^N` factor is
exact (Proposition); `κ` is the empirical, game- and planner-specific consequence
magnitude.

**Remark (what stays empirical).** The measured regularity is that `κ` is
approximately invariant to the rarity knob (≈ 0.12 for army5x5a material-at-cap):
competent MCTS reaches the rule region (the ply cap) regardless of how the knob
tunes `r`, so conditional on the rule being pivotal the blind planner's error
magnitude does not depend on `r`. This invariance is structural-but-empirical — it
requires the planner to reach the region, a property of the game and search budget,
not of the sampling model.

## One mechanism, two faces

The coverage bound and the danger law are the same statement on the two halves of a
CWM. A size-`N` gate of i.i.d. random play fails to certify a CWM exactly on
events of random-reach probability `≲ 1/N` that competent play nonetheless reaches;
the resulting harm is `(consequence) × P(gate miss)`, with `P(gate miss) ≈ e^{−Nr}`
for a transition rule of rarity `r` (danger law) and `≈ e^{−N·b^{−d_max}}` for an
inference info-set at depth `d_max` (coverage bound). A positive gap therefore
needs `r ≪ 1/N` (rare deep rule) or `b^{d_max} ≫ N` (deep/wide hidden game) **and**
a competent planner that reaches the region. Perfect-info board games supply the
depth (army5x5a); shallow betting games (Kuhn, Leduc) do not, which is why their
inference gate is provably identifying.

**Note (reference distribution: random-reach vs equilibrium-reach).** The
normatively correct reference distribution for play-adequacy is equilibrium /
best-response reach, not MCTS reach. Two consequences, kept distinct: (i) the
coverage bound is *equilibrium-robust* — by full support, `reach(σ*) ⊆ reach(ρ)`
for the best-response profile `σ*`, so the sufficiency direction holds against
equilibrium reach (a strength). (ii) The gap and danger results are stated w.r.t.
the **deployed planner's** reach, so the hedge "on the distribution the planner
actually visits" is retained throughout and is not upgraded to a distribution-free
claim. Substituting equilibrium reach would shift the *numbers* (rarity-under-eq,
play_cost-under-eq) but not the *mechanism*.

---

## Belief–transition orthogonality (Claim B) — proposition + result

A second failure surface in imperfect-information CWMs is the **belief model**
(`observation`, `infer_states`). It is not gateable by transition data at all.

**Proposition (belief–transition orthogonality).** A transition dataset is a set of
tuples `(s, a, s', u)` over *full* ground-truth states (`u` = the reward/utility on
the transition). `observation(s,p)` and `infer_states(o,p)` encode the information
partition — the fibers of the observation map, i.e. what player `p` can
distinguish. The information partition is a **free primitive** of the extensive-form
game, logically independent of the transition kernel `P(s'|s,a)` and the reward
`u`: it is the exact analogue of "two POMDPs with identical latent dynamics and
rewards but different observation functions are different control problems." This
partition appears in no `(s,a,s',u)` tuple. Therefore (i) no **full-ground-state**
transition dataset constrains the masking convention; (ii) a transition-accuracy
gate cannot detect an incorrect `observation`/`infer_states`; (iii) the belief
model must be specified and is verifiable only by a separate inference gate. ∎
(This is what motivates the inference gate. Note a dataset of
observation-to-observation tuples `(o, a, o')` *would* constrain the partition;
ours is full-state by construction, so it does not.)

**Demonstration (masked tic-tac-toe, GPT-5.4 large).** Standard tic-tac-toe dynamics
(synthesize at transition gate 1.000 by recall) + an arbitrary, non-recallable
masking rule (the center cell is hidden). Synthesizing with the masking rule **full**
→ transition 1.000, `observation_rate` 1.000; **withheld** → transition still 1.000
but `observation_rate` 0.020 (the belief model is wrong, yet the transition gate
certifies it). The transition gate (`contract_accuracy`) never calls
observation/infer_states, so the blindness is structural, not statistical.

**Secondary finding.** GPT-5.4's synthesized `infer_states` raises `'list' object is
not callable` across three distinct games (Kuhn-mini, Beacon, masked tic-tac-toe) —
the belief surface is also hard to synthesize, independent of the gating point. (So
the clean Claim-B discriminator is `observation_rate`, not `inference_rate`.)

**Epistemic status.** The Proposition is analytic (a statement about what transition
data contains). The demonstration and the synthesis-robustness finding are empirical.
Claim B complements Claim A (Beacon): a wrong belief both loses at play (A, with a
proven reach bound) and is invisible to a transition gate (B, by the orthogonality
proposition).

---

## Hypothesis-verification audit (2026-06-28)

Each formal statement carries hypotheses; this records that they hold at every
use-site (prompted by a reviewer concern that statements outran results).

**Proposition 1 (danger gate-miss, `(1−r)^N`).** Hypothesis: N *distinct,
independent* i.i.d. uniform-random play-throughs, each rule-deciding with prob r
(Bernoulli). Use-sites:
- army5x5a material-at-cap: the training/gate trajectories are independent random
  games. **Correction found & applied:** `refine_cwm(...)` REUSES the same
  trajectory set across iterations (verified in `src/cwm/refiner.py`), and
  `run_gap.py` uses `gate_states = [t.state for t in traj]` — the gate IS the
  training set. So N = train_games (≈40), NOT train+refinement+validation. The
  paper's "What N counts" was corrected accordingly. ✓
- Beacon inference axis: N=2000 independent gate games, each reaching the final
  round w.p. (1/2)^{2T}. ✓

**Theorem 1 (coverage bound) + Lemmas 1–2.** Hypotheses: finite extensive-form
game with PERFECT RECALL; uniform-random ρ with full support; b = max over player
info-sets of |A(I)|. Use-sites:
- Kuhn: perfect recall ✓ (own card + full betting history); b=2. ✓
- Leduc: perfect recall ✓ (own card + community + betting history); b=3, d_max≈8. ✓
- Beacon (design corollary): perfect recall ✓ — each player always knows its own
  type and the public board (step counts, last moves, guesses), so its own action
  history is recoverable; b=2. ✓
- Full support: uniform-random over legal actions has full support on every finite
  game. ✓
- Equilibrium-robustness remark relies only on full support of ρ → holds wherever ρ
  is uniform-random. ✓

**Proposition 2 (belief–transition orthogonality).** Hypothesis: the verification
dataset is *full-ground-state* transition tuples. Use-site:
- masked tic-tac-toe (Claim B): the transition gate calls `apply_action`/`returns`
  on full ground states (`contract_accuracy` in `refiner.py` operates on full
  states), so the dataset is full-ground-state and the partition is unconstrained
  by it. ✓

**One real defect found and fixed:** the N-definition (Prop 1) overstated the
sample count by including refinement and a validation gate that our pipeline does
not draw independently. All other hypotheses hold at their use-sites.

---

## Sample-identifiability of an omitted rule (strengthening "translation, not inference")

The reviewer asked whether "translation, not inference" can be *earned* rather than
softened. It can — by splitting it into a provable core and an empirical residual.

**Setup.** A rule R is omitted from the specification (incomplete rules / no-rules
regime), so the only possible source for it is the trajectory sample. Let the true
game's R fire on a set of play-throughs of probability r under the verification
(uniform-random) distribution D. Write M_R for the world model WITH R and M_∅ for
the otherwise-identical model WITHOUT R; they agree on every transition except those
in the rule region. The pipeline draws N i.i.d. play-throughs from D (the training
sample, which is also the gate — see the N-audit above).

**Proposition (sample-identifiability).** Condition on the event ¬E that no sampled
play-through hits the rule region; `P(¬E) = (1−r)^N`. On ¬E, M_R and M_∅ produce
identical outputs on every sampled transition, so the sample is *observationally
equivalent* under the two models. Hence any selection procedure that is a function
of the sample alone — LLM synthesis, gradient learning, program search, exhaustive
enumeration — assigns M_R and M_∅ the same score and cannot prefer the correct one.
The omitted rule is therefore **information-theoretically unidentifiable** from the
sample, and a sample-passing M_∅ is admissible (the gate cannot reject it). ∎

**Corollary (identifiability = the danger-law gate-miss).** The probability that the
omitted rule is unidentifiable from the N samples is exactly `(1−r)^N` — the same
factor as the danger law. The danger law is thus an identifiability statement:
`danger = play_cost × P(rule unidentifiable from the N samples)`.

**This splits the claim cleanly:**
- **(a) Provable, universal:** when the rule is absent from the sample (prob
  `(1−r)^N`), it cannot be inferred by ANY learner — not a limitation of LLMs but of
  the data. The gap-exhibiting seeds in §3.3 are this event, not an LLM failure.
- **(b) Empirical, LLM-specific:** even when the rule IS present in the sample (prob
  `1−(1−r)^N`), the LLM synthesizer does not reliably encode it — the §5 repair
  battery supplies discriminating examples (proper DAgger, targeted on-manifold) and
  the rule is still omitted. This is the genuinely LLM-specific, scoped finding.

So "translation, not inference" becomes: **(a)** an omitted rule is unidentifiable
from a sample that misses it (provable, universal, = the danger-law event), and
**(b)** even a sample that contains it does not reliably teach the LLM (empirical,
tested on GPT-5.x mini/large across the §5 regimes). The universal-for-all-models
form of (b) remains a conjecture; (a) is a theorem.

---

## Notes for a future "writing this paper with AI" article (not part of the paper)

Process/career angles to develop in a separate blog post (kept here so they aren't lost):

- **Credibility / not-incapacity:** the author had a published preprint *before* using
  AI — a pure-math thesis result (a proved theorem). So the speed here is amplification
  of an already-capable researcher, not a substitute for capability.
- **Effort/time gap, honestly:** the math preprint took **>2 years** with institutional
  backing (university / funded project); this one ~**2 weeks**, largely **independent**
  (no university or funding). But DO NOT attribute the whole gap to AI — untangle the
  confounders:
  - **Scope: pure math vs empirical AI/ML.** Proving a theorem is intrinsically slower
    and harder than an empirical ML preprint; different kind of work.
  - **Length.** The math paper is ~2× this one or longer (verify exact figures when
    writing) — more to write accounts for some of the time.
  - **Process overhead** of institutional publishing vs solo preprinting.
  Net: even normalized, the jump is large, but honesty requires separating "AI made me
  faster" from "this is a shorter, more empirical, solo project."
- **Career-transition thread:** the pure-math → applied/ML shift is itself the
  narrative spine (mathematician → AI/ML practitioner).
- See also the agent-memory note `project_blog_article_ideas` for the meta-process
  (AI-assisted reading of the source paper, agent-run experiments, multi-AI adversarial
  review, separating provable-vs-measured).

---

## Coverage applies to BOTH halves of the contract (transition + belief)

The coverage bound (Theorem 1) was stated for the inference/belief function, but the
same logic governs the transition function: a random gate certifies global
correctness exactly when its check covers the full reachable (search-relevant)
relation. We made this concrete on tic-tac-toe — the one game small enough to
enumerate — via `scripts/exhaustive_verify_tictactoe.py`: a gate-passing synthesized
CWM has 0 search-relevant mismatches over all 5478 reachable states / 16167
transitions (excluding 880 legal_actions-on-terminal convention artifacts), i.e.
*proven* globally correct by exhaustion, upgrading the §3.2 null from "no observed
divergence" to a proof where the game is enumerable. For large games (army5x5a) the
gate cannot cover the relation, so only sampled certification holds — and that is
exactly where the residual gap (0.002) and the rare-rule instrument live.

---

## Enumeration-free companion certificate (error mass, 2026-07-02)

Theorem 1's constants (π_min, |𝓘|) require enumerating the reachable info-sets —
feasible for Kuhn/Leduc, intractable in general. Theorem 2 (paper §6.2,
`scripts/error_mass_certificate.py`) removes the enumeration by weakening the
conclusion: instead of "every reachable info-set was visited" it certifies "the
undetected error region of the accepted artifact has small sampling mass". For a
candidate `infer_states` f with error set E_f, a passing size-N gate implies
per-game hit mass μ_ν(E_f) ≤ ln(1/δ)/N (held-out gate; +ℓ·ln2 for a
description-length-ℓ class if the training sample doubles as the gate). Transfer
to play is governed by the reach ratio: μ_σ ≤ b^bar_d · μ_ρ for any profile σ
(bar_d = player-move horizon), and Beacon realizes this blow-up (ratio 2^{2T}),
so it is not slack. A mixture gate ((1−λ)ρ + λ·competent-self-play) replaces
b^bar_d with 1/λ for the reference competent profile — "verify on the search
distribution" in certificate form. Neither theorem subsumes the other: coverage
is a for-all-error-patterns guarantee with enumerative, game-growing constants;
error-mass is per-artifact with game-size-free constants. The paper keeps both.

---

## play_cost: no longer purely empirical (2026-07-02)

Three provable fronts now bracket play_cost (paper §4 Prop 2 + remark, §6.4 Prop 4):
- **Upper bound (theorem, general):** play_cost ≤ μ_query(E), the probability the
  planner's search queries its model on the error region at least once per game
  (coupling argument: runs are identical until the first E-query; the relevant
  distribution is the QUERY distribution, dominating trajectory reach). Makes the
  danger law an end-to-end upper bound: danger ≤ μ_query(E)·(1−r)^N, no fitted
  constant.
- **Exact on solvable witnesses:** Beacon's play_cost = 1/2 exactly, by exhaustion
  over its 4 deals × 2 seatings (`scripts/play_cost_exact_beacon.py`, plus a
  determinized-MCTS check on the same 8 games). Both danger-law factors are now
  analytic on the inference axis; the 0.000 arena result is confirmation of a
  theorem.
- **Lower bounds by witness (no game-solving):** an explicit opponent strategy +
  arena measurement is a statistical certificate; the n=600 CI run certifies
  play_cost ≥ 0.083 (seed-clustered 95%).
What stays empirical at scale is only the exact constant — a game-value
difference, i.e. solving the game: the play-value analogue of the
enumeration/sampling wall (three-levels remark, paper §6.2).
