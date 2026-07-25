# Statements the reviews weakened, and how to earn them back

Written 2026-07-25 at Javier's request: every claim that the correctness reviews
made *weaker* than it was, why the strong version was not defensible, and the
concrete route to a strong version that would be. Ordered by how much strength is
recoverable per unit of work. Nothing here blocks the arXiv submission — the paper
as it stands claims only what the data supports.

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

**Still open (cheap, CPU-only):** an instrument where the two modes are provably
independent within a rollout (patches on orthogonal axes, far enough apart that no
rollout can reach both) would let the product form be *derived* rather than
assumed, giving a clean factorization result to sit beside the bracket.

---

## 2. Weakened, recoverable with Azure money — the pooled Wilson bounds

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
