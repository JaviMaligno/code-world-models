# Statements the reviews weakened, and how to earn them back

Written 2026-07-25 at Javier's request. **STATUS 2026-07-25 (same day): items 1, 2,
4 and 5 are DONE and item 3 was superseded by a better result — see the per-item
"EARNED" notes below. This file is kept as the record of what was weak, what it
cost to fix, and what remains.**

---

## 1. Already recovered, and now stronger than the original — the joint danger factor

**Was:** "the danger law composes per mode: the joint factor is
$(1-r_1)^N(1-r_2)^N$." That silently assumed the two per-mode contact events are
independent within a rollout. They are not (measured $P(\text{both}) \in [0,
0.005]$ against $r_1r_2 \in [0.0007, 0.0025]$, dependence changing sign across
the knob grid), and the product misestimates the joint factor by $-17\%$ to
$+12\%$.

**Now:** the joint factor is *measured* at the union event, **and** the paper
proves a two-sided bracket that needs no independence assumption —
$(1-\min(1,r_1{+}r_2))^N \le (1-r_\cup)^N \le (1-\max(r_1,r_2))^N$ — plus an exact
sign rule for the product's error (over-estimates under negative dependence,
under-estimates under positive). Verified against all nine knobs in CI.

**Net:** stronger than what was there before. An assumption became a theorem. Also
note the corrected numbers are *larger* (more danger) at 3 of 9 knobs: e.g.
$k=(4,6)$ goes 0.0178 → 0.0215.

**Superseded 2026-07-25, by a better result than the one planned.** The plan was
an instrument with provably independent modes so the product form could be
*derived*. That plan was wrong on its own terms: moving modes apart makes the
events *disjoint*, which is the opposite of independent, and pushes the joint
factor to the bracket's lower end. What replaced it is a remark that says what is
actually true — both bracket ends are attained (the lower one in our data, at six
of nine knobs where no rollout out of 600 contacts both patches), and exact
factorization is a property of the **gate**, not the instrument: a *stratified*
gate spending independent budgets $N_1, N_2$ on the two mode regions has joint
miss probability exactly $(1-r_1')^{N_1}(1-r_2')^{N_2}$. That is a design
consequence for multi-mode pipelines, and it cost no compute.

---

## 2. Weakened, recoverable with Azure money — the pooled Wilson bounds

**EARNED 2026-07-25.** `--seed-offset` added (tested: blocks disjoint, resume
does not re-spend) and the large arm re-run on block $S_{20}$ for both headline
cells, 10 min each. Cart: 20/20 on **20 independent samples**, Wilson **0.8389** —
the 0.84 restored and legitimate; the $(1-r)^N$ check is now poolable too (20/40
independent samples lacked the mode against a predicted 0.63). Pendulum: 15/15
disjoint, Wilson **0.796** (was 0.701 per size). Bonus: repair goes 82/82 → 106/106
over 65 distinct samples, and the cells now carry two orthogonal replications
(same samples/different model, and different samples/same model).


**Was:** mode-absent ⇒ blind-and-exploited with Wilson lower bound **0.84**
(pooled 20/20 across the two GPT-5.x sizes); pendulum 0.824 (18/18).

**Now:** 0.72 per size (10/10) and 0.70 (9/9), because
`rollout_seed = 10⁴(i+1)` is model-independent, so the two sizes are synthesized
from *the same samples*: pooling doubles the synthesis draws, not the independent
gate samples.

**Route to the strong version:** run the second size on a *disjoint* seed block
(e.g. seed indices 20–39, i.e. `rollout_seed ∈ {210000, …, 400000}`). Then the
pooled 20 mode-absent seeds are 20 independent samples and the 0.84 bound is
legitimate. Add a `--seed-offset` flag to `continuous_danger_synthesis.py` (the
run is already per-seed checkpointed, so nothing is re-spent).

- Cost: 20 seeds × 2 arms on the cart headline cell + the same on the pendulum
  headline knob ≈ the cost of two existing cells of Azure traffic.
- Payoff: 0.72 → ~0.84 on the headline conditional, and it makes every "both
  sizes" count in the paper an honest $n$ instead of an $n/2$ with a caveat.
- Bonus: with disjoint seeds the two sizes also become an independent replication
  of the $(1-r)^N$ gate-miss rate, which currently cannot be pooled at all.

---

## 3. Weakened rhetorically, recoverable by re-calibration — "below random at every knob"

**EARNED (partly) 2026-07-25** via a non-destructive variant rather than a
re-calibration: `scripts/continuous_sharp_plateau.py` (cart width 0.5→0.2,
pendulum 0.25→0.1) into sibling JSONs, leaving the default instruments and every
paid-for synthesis artifact untouched. Cart: below random at **7/7** knobs (was
6/7), by 2–13 orders of magnitude. Pendulum: **5/6** (was 3/6). What strengthened
more than expected: `play_cost` becomes knob-invariant to ~$1.5\times10^{-4}$ on
both instruments, a **400× tightening**, i.e. the invariance the default shows
approximately is exact without the tail — and the pre-registered risk did not
materialise ($J_\mathrm{truth}$ moves 17.77→17.76 and 20.08→20.05). Honest
residue: the pendulum's widest stop still has $J_\mathrm{blind} = 3.1e{-3}$ over
$J_\mathrm{rand} = 3.6e{-4}$ — there the random baseline has itself collapsed, so
below-random stops being the informative comparison and play_cost = 1.0000 is.
Side effect: fixed a real crash (`OverflowError` in the reward when a narrow
plateau meets a free-spinning pendulum), bit-identically for every reachable
default value.


**Was:** "the mode-blind planner is exploited **below random** at every knob."

**Now:** "exploited at every knob ($\mathrm{play\_cost} \approx 1$; below random
at most)." The strong version is false as measured: $J_\mathrm{blind} >
J_\mathrm{rand}$ at cart $x_\mathrm{wall}=10$ and at the three farthest pendulum
stops — not because the exploitation weakens (contact rate stays 1.00) but because
the *far plateau's sigmoid tail* leaks reward to a planner pinned near it
($J_\mathrm{blind} = 0.94$ at $x_\mathrm{wall}=10$), and gravity does the same on
the pendulum.

**Route to the strong version:** the leak is a reward-shape artifact, not a
mechanism fact. Narrow the plateau width (`width` 0.5 → ~0.15) or move the far
plateau beyond the widest knob, so a pinned planner earns ~0 at every knob. Then
$J_\mathrm{blind} \approx 0 < J_\mathrm{rand}$ everywhere and "below random at
every knob" is true as stated.

- Cost: CPU only — recalibrate, then re-run `continuous_reach.py`,
  `continuous_pendulum.py`, `continuous_axes.py`, `continuous_mitigation.py`
  (~1 h total) plus the figure regeneration.
- Payoff: purely rhetorical. `play_cost ≈ 1` already carries the scientific
  content, and it is knob-invariant either way. **Do this only if a reviewer
  pushes on it**; it costs a re-run of four tables for a sharper sentence.
- Caveat: changing the reward shape changes every number in the mechanism tables,
  so it is a "redo the sweeps" change, not a patch.

---

## 4. Weakened, cheap to recover — the two censored zeros

**EARNED 2026-07-25.** Pendulum rarity sample 3000 → **30,000**: the censored
zero resolves to 0.0007 [0.0004, 0.0010], so every row is a point estimate and
every d@40 a number. Axes 2000 → **20,000**: the sub-eps arm resolves to 0.0001
with predicted pass 0.9940 **inside** the measured [0.9814, 0.9994]. Two bonuses
nobody asked for: wall@8's prediction moves 0.6046 → 0.6622 against a measured
0.667, so the standing "the prediction sits below the Wilson lower bound" caveat
is *gone* (it was the rarity estimate's noise, as suspected); and with the cart
also raised to 30,000, the two independent estimates of the same event agree to
the third decimal (0.1352 vs 0.1351, against 0.1430 vs 0.1385 before).


**Was:** pendulum $\theta_\mathrm{stop}=2.0$ rarity `0.0000` with
$d@40 = 0.942$; axes sub-$\varepsilon$ arm rarity `0.0000` with predicted pass
`1.0000`.

**Now:** reported as raw counts ($0/3000$, $0/2000$) with the prediction as an
upper bound, because a point estimate of 0 from a finite sample overstates
precision — and in the axes case the 1.0000 prediction sat *outside* the measured
pass-rate CI $[0.9814, 0.9994]$.

**Route to the strong version:** more rollouts. $3000 \to 30\,000$ for the
pendulum knob and $2000 \to 20\,000$ for the axes arm either finds contacts (a
real rarity, so a real prediction) or tightens the upper bound tenfold
($0.0013 \to 0.00013$), at which point the bound is tight enough that the
distinction stops mattering.

- Cost: CPU only, minutes (`--rollouts 30000` on the two scripts).
- Payoff: turns two "$\leq$" entries back into point estimates or near-exact
  bounds. Cheapest item on this list.

---

## 5. Reframed rather than weakened — "no artifact covers even its seen patch"

**Was:** "no artifact covers even its *seen* patch", backed by a check that was
**vacuous** (it read `per["p1"]` while the key is `"patch1"`, so its condition
never fired).

**Now:** on the 66 see-one-miss-the-other seeds, 28 freeze sets *do* contain the
seen patch, by freezing $15\times$–$81\times$ the patch's area (median $61\times$);
exactly one is patch-*selective*, and it achieves that with a half-plane at
$31\times$ the area. So no artifact encodes a region; the conclusion (no partial
repair) is intact and now threshold-free.

**Route to something stronger:** the interesting open question this exposed is
whether a *selective* artifact can ever be produced deliberately — i.e. does an
instrument with two patches on opposite sides of the start produce artifacts that
fence one and not the other? That is a new experiment (a cheap CPU-plus-Azure
cell), and a positive result would give the partial-repair branch its first
population instead of an emptiness claim.

---

## 6. Precision, not weakening — but with a real theorem behind it

**EARNED 2026-07-25 (the measure version exists now).** Added as a
proposition: with an $L$-Lipschitz pair differing by $\eta$ and a gate whose
step-$k$ visitation density is $\geq c$ on the guaranteed ball, one rollout reveals
the disagreement with probability $\geq c((\eta-\varepsilon)/L)^{d+m}$, so the miss
probability is $\leq (1-q)^N$ — and hiding an $\eta$-sized error from $N$ rollouts
forces $L \geq (\eta-\varepsilon)(cN/\ln(1/\delta))^{1/(d+m)}$, i.e. the required
Lipschitz constant grows like $N^{1/(d+m)}$ (hiding gets easier with dimension).
The density hypothesis is not verified per instrument and is stated as such; the
measured stand-in is the smooth bump arm's reveal-rarity (0.18 against the hard
wall's 0.14 — the smooth error is if anything *more* detectable, matching the
proposition's direction).


- "smooth pairs cannot realize the localized geometry" → "**exactly** localized".
  Proposition 5 bounds the disagreement ball's radius by $(\eta-\varepsilon)/2L$;
  what is impossible is *exact* localization, not a merely tiny region.
  **Stronger version available:** convert the metric statement into a *measure*
  one. If the gate's visitation measure has density $\geq c$ on a neighbourhood of
  the error, the reveal probability is $\geq c \cdot \mathrm{vol}(B)$, giving a
  computable $(\eta, \varepsilon, L) \mapsto$ detection-rate bound — i.e. "a smooth
  model that is wrong enough to matter is *detectable at a rate*", which is
  strictly more than "cannot be exactly localized". This is the same gap as the
  open covering-number analogue in §11 and is a theory task, no compute.
- "no learner can infer it" → "no learner can infer it **from the sample**". Not
  recoverable and should not be: a prior *can* supply the mode (Claude's symmetry
  prior did, and got one right and one phantom). The caveat is the content.

---

## Priority if we pick this up

1. **§4 (censored zeros)** — minutes of CPU, removes two "$\leq$" entries.
2. **§2 (disjoint seeds)** — one Azure session, restores the headline 0.84 bound
   and makes every pooled count honest.
3. **§1 tail (independent-mode instrument)** — CPU + design, converts the bracket
   into a factorization theorem for a designed case.
4. **§6 (measure version of the Lipschitz bound)** — pure theory, highest
   intellectual payoff, no compute; also closes a stated limitation.
5. **§3 (reward re-calibration)** — only under reviewer pressure; four tables move
   for one sharper sentence.

---

## What remains open after 2026-07-25

- ~~The pendulum's widest sharp-variant knob~~ **CLOSED 2026-07-25**: narrowing
  only the phantom plateau (per-plateau widths, `--width-right 0.08`) gives 6/6
  below random with the random baseline intact and play_cost invariant to 7.1e-5.
- ~~Verifying the visitation-density constant $c$~~ **CLOSED 2026-07-25**: exact
  for the cart's gate at step 1 ($c = 5/6$, Monte-Carlo confirmed), general form a
  volume ratio. Both covering-number analogues are now proved: mitigation-side
  (Prop 7 + Cor 2) and gate-side (Prop 9). The within-rollout dependence is also
  settled — no mixing argument needed, and worth only 2% — leaving one named gap:
  the density is derived only at step 1 of one instrument, so certifying the whole
  region the planner visits needs the density there.
- The Qwen 2D induction arm (credits; see the separate note) — the only *missing
  data* rather than missing strength.
- Not recoverable, by design: "no learner can infer it **from the sample**". A
  prior can supply the mode; that caveat is the theorem's content.

---

## Addendum 2026-07-25 (later): two more statements upgraded from measured to proved

**Knob-invariance of play\_cost is now an identity, not a regularity.** Javier
asked whether the invariance is a theorem or a measurement. It was a measurement;
it is now Proposition 8: whenever $J_\mathrm{truth}$ and $J_\mathrm{rand}$ are
knob-free, play\_cost$(k) = J_\mathrm{truth}/(J_\mathrm{truth}-J_\mathrm{rand}) -
J_\mathrm{blind}(k)/(J_\mathrm{truth}-J_\mathrm{rand})$ — affine in the exploited
planner's own return, so the whole knob-dependence *is* its residual reward over
the truth-minus-random margin. The hypotheses are measured sharply ($J_\mathrm{truth}$
knob-identical to twelve digits; $J_\mathrm{rand}$ varying by 3.9e-9 sharp / 1.2e-4
default), and the identity predicts every measured play\_cost to 2.4e-10 (sharp),
with the predicted spread 1.3615e-4 matching the measured 1.3615e-4. What the
sharp-plateau variant buys is therefore not the invariance but the vanishing of
$J_\mathrm{blind}$ that makes the identity's residual term negligible. Audited.

**The bracket is sharp, and that is the independence-free result.** The joint
gate-miss bracket's ends are exactly the Fréchet–Hoeffding bounds for
$P(R_1 \cup R_2)$ given the marginals, pushed through $x \mapsto x^N$: the interval
is the *exact* range of joint miss probabilities consistent with $r_1, r_2$, so no
bound in the marginals alone can be tighter. That — not a bespoke instrument — is
the correct theoretical statement without independence, and it was already in the
paper; the earlier "superseded" note referred only to the discarded instrument
plan and undersold it.


---

# Round 2: five adversarial peer reviews, 2026-07-25 (later the same day)

Five reviewers were run over the revised paper (core probability, claim-vs-theorem,
geometry/measure, covering-number mitigation, statistics/inference). They found
errors the first round had not, including three that flipped bolded conclusions.
What follows is the ledger: what was wrong, what it is now, and which of them is a
weakening that could be earned back.

## Fixed by making the paper WEAKER and TRUER (no path back — the earlier claim was
simply false)

1. **The wall corollary was vacuous.** "No smooth pair less than twelve times as
   sensitive as the plant can hide the wall from this gate ($L \geq 15.2$ for
   $\eta = 4.2$)" instantiated a density $c = 5/6$ that is supported on the
   one-step reachable set $|x_1| < 0.53$ — at the wall ($x \in [2,10]$) the
   step-1 density is exactly zero and the proposition says nothing. The ball does
   not bridge the gap either. Deleted; what remains at the wall is the measurement
   (reveal-rarity 0.14) and Prop lipschitz's density-free obstruction.

2. **The step-t certificate did not exclude the hard mode.** Two independent
   errors: the density was computed in 2-D $(x,v)$ and consumed as 3-D $(x,v,a)$
   (a factor $2a_{max}$ the step-1 corollary got right), and a per-cell AVERAGE was
   used where the hypothesis wants an INFIMUM. Corrected via a Minkowski erosion
   with $P$-shaped cells (a genuine pointwise infimum, oracle-tested), the step-20
   bound is 8.84, not 3.67. The bolded "still excluding the hard mode's 4.2" is
   retracted. The honest replacement is a better statement: at fixed $N$, extent is
   paid for with resolution, and NO step-$t$ region beats the step-1 corollary — so
   the step-1 restriction was never what limited the certificate.

3. **The $\varphi$ factorization was not exact.** "Conditioning on the entire state
   trajectory leaves the action indicators independent Bernoulli" is false when the
   plant is invertible in the action, which this one is. Replaced by a direct
   measurement of the per-rollout miss probability, which needs no factorization at
   all and is genuinely exact.

4. **The grid was not a grid.** `int(2R/rho)` with index clamping made the top cell
   0.8 wide at $\rho = 0.6$, so "all cells hit" certified a coarser net than
   claimed — and the falsification test shared the bug, so it validated it. Both
   fixed to `ceil`; the deployed gate certifies net radius 1.0 (bound 2.55) and
   misses 0.667 by two rollouts.

5. **The fence bound was in the wrong direction.** Coverage-adding fences are
   bounded by a PACKING number, not a covering number: 12 on the unit circle at
   $\varepsilon = 0.5$, against a covering number of 7, with the 12-point sequence
   exhibited. Cor 2's ORDER survives ($N_{pack} \leq N_{cov}(\cdot,\varepsilon/2)$).

6. **The 1D "exactly 1.00" was not the covering bound.** The fence lands at the
   refuted prediction, which overshoots the wall by up to 0.58 against
   $\varepsilon = 0.25$, so the covering hypothesis fails in 4 of 5 cart episodes
   while the conclusion holds. It is a SEPARATION fact, and it has a signature we
   measured: bit-identical outcomes over a $20\times$ $\varepsilon$ range on the
   pendulum, breaking only at $\varepsilon = 0.01$ on the cart.

7. **$J_{max}$ was incoherent.** Read as a supremum over policies of the expected
   return it is 17.697, BELOW the measured $J_{truth} = 17.772$ — the normalization
   would exceed 1 by construction. The coupling needs pointwise extremes: with
   $J_{max} = 18.009$ the bound is 1.0447 against a measured 1.0310, so the
   corollary is at 98.7% of its bound and NOT attained.

8. **"Confirmed at all nine knobs" was an identity.** $r_1$, $r_2$, $r_\cup$ and
   $P(both)$ come from the same rollouts, so inclusion-exclusion holds exactly
   in-sample and the bracket cannot fail. Zero empirical content.

9. **"Distinct gate samples" over-counted by up to $10\times$.** The rollout stream
   depends on the seed index alone, not on the instrument, knob, patch shape or
   prompt variant — so the PatchField2D campaign's 203 cells rest on 20 blocks, and
   the guided ablation reuses the disc cells' samples byte for byte.

## Earned back the same day (weakened, then recovered by measurement)

10. **"The dependence changes sign across the grid."** At 600 rollouts $P(both)$ was
    0–3 counts and the claim was noise. Re-measured at 50,000 rollouts per knob:
    negative at $(2,6)$ and $(3,7)$, POSITIVE at $(4,6)$, all three with Wilson
    intervals excluding $r_1r_2$. The claim is now earned, and it is the reason a
    fixed correction factor cannot replace the bracket.

11. **$\varepsilon^\star$ "predicts where each sweep arm dips."** It was computed on
    a different rollout stream than the sweep, and failed on 2 of 4 arms. Computed
    on the sweep's own stream it is an IDENTITY on all four — weaker in kind (an
    identity, not a prediction) but true, and now stated as such.

## Still open — a real weakening with a known path back

12. **The 2D fencing budget and the "boundary-mapping transient".** The arc
    percentages were the violation count divided by the budget (saturation assumed
    and restated), the budget ignored the second patch, and per-episode maxima
    reach 28 with 24 duplicate fences at one point. The census script now measures
    the probed arc directly and reports median/max/lock-in. **To earn a real
    claim here:** instrument which patch each violation belongs to, report the
    per-patch packing budget, and separate the lock-in failures from the transient
    — a mitigation that pins the agent 7 episodes in 20 is not a slower transient,
    it is a different failure mode.

13. **The interiority hypothesis holds on only 34% of $U$.** Prop detectrate's
    $q = c(2\rho)^{d+m}$ needs the ball unclipped; on the cart's $U$ that is
    $33.9\%$ of the volume, and elsewhere $q$ is smaller by up to $2^{d+m}$. Stated
    rather than fixed. **To earn it back:** a boundary-aware version of the ball
    volume, or a certified region taken as an interior sub-level set.
