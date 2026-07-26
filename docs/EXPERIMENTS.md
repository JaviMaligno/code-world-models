# Experiments Log

## PAPER 2 — The last gap closed: a universal Jacobian, and the certificate's own irrelevance measured (2026-07-25, closing)

Two gaps were left: the nonlinear analogue of the density argument, and the fact
that the certified region is the GATE's, not the PLANNER's. Both closed, and
closing them sharpened the conclusion rather than the guarantee.

**1. The nonlinear case is not a separate case — the constant is UNIVERSAL.** For
any plant of the semi-implicit form

    om_{t+1} = om_t + (gain*a_t + F(th_t, om_t))*dt,   th_{t+1} = th_t + om_{t+1}*dt

with F in C^1 ARBITRARY, the two-action Jacobian satisfies

    |det d(th_t, om_t)/d(a_{t-2}, a_{t-1})| = gain^2 * dt^3   identically,

independent of F, of the state and of t: substituting the partials, every
F-dependent term cancels (algebra in the tex; verified numerically against four
forces including a non-separable one, at three (gain, dt) pairs, to ten digits).
So c = 1/(4 a_max^2 gain^2 dt^3) = 27.78 is the SAME constant for the cart and the
pendulum, and the certificate's hypothesis holds for the whole instrument family.
The one exception is the expected one: wherever the mode clamp fires the two-action
map is constant, det = 0 exactly, and no density argument reaches the mode —
intrinsic, not technical. (First attempt at this measured min|det| = 0 everywhere;
that was my grid including |a| = a_max, where the action clamp kills the
derivative. Corrected to interior actions, and then the free part is exactly 0.009
with min = max.)

**2. The certified region carries 1.9% of the planner's queries.** The certificate
bounds the model where the GATE covers; play cost is driven by where the PLANNER
queries. Measured directly (`certified_region_query_mass.py`, every imagined MPC
step is a query, 1.3M queries per episode pair): of the exploited planner's
queries, **1.9%** fall inside the region certified at rho = 0.60 and **7.8%**
inside the larger step-20 region (truth planner: 2.3% and 7.3%).

So the certificate is sound and nearly irrelevant to play — not because the bound
is loose (it is tight to one grid step, measured) but because the gate covers a
couple of percent of the query mass. That is the paper's thesis restated as a
measurement instead of an argument, and it is why obtaining the continuous coverage
analogue does not rescue sampling verification: the gate certifies where it looks,
and the planner looks somewhere else. Limitations now say exactly that, and point
at the companion paper's prescription (sample the deployment distribution) as the
change that would matter.

State: 38 pp, 0 errors / 0 undefined / 0 overfull; **536 audited values**.

## PAPER 2 — Density derived at every step; certificate extended; threshold validated (2026-07-25, final)

Javier asked two things: whether the small N is a problem calling for a bigger
experiment, and to derive what was missing.

**On N = 40: it is the OBJECT OF STUDY, not our sample size.** The paper is about
what a deployed CWM gate misses, and that gate is 40 rollouts (paper 1's setting).
"This gate certifies sup <= 2.97 for 1.80-Lipschitz models" is a fact about a weak gate
— the thesis, not a limitation of our evidence. Where N *was* our measurement
budget it has already been raised (rarity 3000 -> 30000, axes 2000 -> 20000, 300
independent gates for pass@N). Running a bigger GATE would measure a different
object; what it would add is only confirmation of the arithmetic in the N-vs-rho
table, so instead we validated the threshold (below).

**Derived: the visitation density at every step t >= 2.** The plant is linear and
time-invariant, so (x_t, v_t) is an affine image of (x_0, a_0..a_{t-1}); splitting
off the LAST TWO actions gives (x_t,v_t) = W_t + M (a_{t-2}, a_{t-1}) with M
time-invariant and |det M| = 0.009 (verified against finite differences). Hence at
every t the step-t law is a convolution with the uniform law on a parallelogram of
area 0.036, so it is absolutely continuous with

    p_t(u) >= 27.78 * P( M^{-1}(u - W_t) in [-a_max, a_max]^2 ),

an exact constant times a reachability probability. `gate_density_step_t.py`.

Two things we measured before believing them:
- **The certified region must be a LEVEL SET, not a box.** A box's corners pair
  extreme x with extreme v, which the gate never reaches, so inf over a box is 0
  and the bound is vacuous. First attempt returned exactly that; the script now
  reports level sets.
- **Later steps trade density for extent.** Step 20's {p >= 0.05} has volume 6.9 in
  (x,v,a) against the one-step set's 1.2, and N = 40 certifies rho = 1.44, i.e.
  sup <= **3.67** — a region **5.7x larger, still excluding the hard mode's 4.2**.
  Step 40's {p >= 0.01} (volume 19) gives rho = 2.39 and 6.07, which no longer
  excludes it: that is the frontier of what 40 rollouts buy.

**The threshold is TIGHT, measured.** 200 independent gates per resolution
(`gate_coverage_validation.py`): the deployed gate actually covers in 200/200 at
rho = 0.70, **199/200 at rho = 0.60** (the resolution the certificate licenses),
then 128/200 at 0.50 and 10/200 at 0.40 — exactly where the certificate demands
N >= 169 and N >= 1179. So the bound is tight to one grid step, not loose by orders
of magnitude, which is what makes the N-vs-rho trade-off worth quoting.

Limitations narrowed again: the density gap is closed for all steps of this plant;
what stays open is covering the UNION over steps (or the planner's own visitation,
which is not the gate's) and the nonlinear analogue of the Jacobian argument.

State: 38 pp, 0 errors / 0 undefined / 0 overfull; **531 audited values**.

## PAPER 2 — The "mixing argument" settled: a negative result, and a better proof (2026-07-25, last)

Javier: "eso que dices del argumento de mezcla entiendo que significa que hay algo
más que hacer por ahí, si es así hazlo." There was, and the answer is negative in
an informative way.

**No mixing argument is needed — there is better structure.** The certificate's
rigorous instantiation used one step per rollout (N = 40) because steps within a
rollout are dependent, and I had flagged mixing as the route to the all-steps
figure. But under the gate policy the action a_t is i.i.d. and INDEPENDENT of s_t,
so conditioning on a rollout's whole state trajectory, the action indicators at the
visiting times are independent Bernoulli(q_a) and

    P(cell unhit by the gate) = p_C^N,  p_C = P(one rollout misses cell C)

**SUPERSEDED 2026-07-25.** The original version of this entry claimed the
conditional factorisation `P(unhit | state trajectory) = (1-q_a)^O` was EXACT, by
conditioning on the whole state trajectory and calling the visiting-time action
indicators independent Bernoulli(q_a). That is false: this plant is invertible in
the action (`a_t = ((v_{t+1}-v_t)/dt + drag*v_t)/gain`), so conditioning on the
trajectory DETERMINES every action and the conditional indicator law is degenerate.
The gate policy gives `a_t ⊥ s_t`, not `a_t ⊥ (s_0..s_T)`. Measured damage at
rho = 0.6: the model gave 0.802 against a true 0.812 at the binding cell —
anti-conservative — and up to 11.6% off elsewhere.

**The repair needed no factorisation at all.** Only the i.i.d.-ness of the N gate
ROLLOUTS is used, which is a property of the design rather than of the dynamics:
p_C is measured directly by counting rollouts that miss C, Hoeffding bounds it
above, and `p_C^N` is exact. `scripts/gate_coverage_dependent.py`.

**A second bug in the same script: the grid was not a grid.** `nx = int(2R/rho)`
with `min(nx-1, ...)` index clamping makes the TOP cell wider than rho — 0.8 at
rho = 0.6, 1.2 at rho = 0.8 — so "every cell hit" certified a coarser net than
claimed, and the action sliver [0.8, 1.0] belonged to no cell while being charged
q_a = rho/2A. Worse, `gate_coverage_validation.py` used the identical grid, so the
falsification test validated the bug instead of catching it. Both now use `ceil`
with every cell of width <= rho, and the reported bound uses the achieved width.

**What it buys, honestly: the gate is WEAKER than we said.** On the box
|x|,|v| <= 1 the deployed N = 40 certifies net radius 1.0, i.e.
sup|f - f_hat| <= **2.55**, and it misses the next resolution by two rollouts
(radius 0.667 needs N >= 42, bound 1.70). Measured N-vs-radius:

| net radius | cells K | N needed (rigorous) | N (estimate) | certifies |
|---|---|---|---|---|
| 2.000 | 1 | 1 | 1 | 5.090 |
| 1.000 | 8 | **7** | 7 | **2.550** |
| 0.667 | 27 | 42 | 37 | 1.703 |
| 0.500 | 64 | 194 | 122 | 1.280 |
| 0.400 | 125 | 2189 | 306 | 1.026 |

No percentage is quoted against the one-step-per-rollout figure (2.93), because the
two certificates cover different regions: 2.93 on the step-1 reachable slab
(vol 1.2), 2.55 on a box 6.7x larger. The qualitative conclusion is unchanged and
sharper: the mixing question was a red herring, and the all-steps-independent
resolution is unreachable at this gate size by two orders of magnitude in N.

**Tightness, on the honest grid.** 200 independent gates per resolution: 200/200
cover at radius 1.0 (licensed), 198/200 at 0.667 (which the certificate declines,
needing 42) — so the bound is conservative by about 5% in N — then 128/200 at 0.5
and 10/200 at 0.4, where it asks for 194 and 2189.

Limitations updated: the within-rollout gap is CLOSED (negatively — no mixing
needed, and little to gain), and the one that stays open is named precisely: the
visitation density is derived in closed form only at step 1 of one instrument, so
certifying a larger U (the whole region the planner visits) needs the density
there, which we have not derived.

State: 37 pp, 0 errors / 0 undefined / 0 overfull; **524 audited values**.

## PAPER 2 — A geometry error, its class, and the gate-side covering number closed (2026-07-25, later still)

Javier: "el número de recubrimiento de un círculo no es 3?" — and then, after the
answer, "revisa si se da algún otro caso de algo así o geometría que estés
fallando". Both were warranted.

**The error.** I wrote that covering a circle of radius R=1 with balls of radius
eps=0.5 needs 13 balls. It needs **7** (centres on the circle) or **6** (free
centres): I used the angular HALF-width 2*asin(eps/2R) = 0.5054 rad as the full
width, when the covered arc is 4*asin(eps/2R) = 1.0107 rad. Consequences: the
measured fence counts were then said to correspond to reachable arcs of 17/43/68%
of the circle.

**That consequence was itself wrong, twice over (2026-07-25).** The percentages are
the violation count divided by the budget — saturation ASSUMED and restated as a
percentage, then used to explain the count, which is circular; the probed arc is
now measured directly. And the budget was a covering number where the bound needs a
PACKING number (12, not 7, at R=1, eps=0.5 — with an exhibited 12-point sequence
every member of which adds coverage). So the "nearly saturated bound" reading is
retired entirely: it was built on a number that was too small and a percentage that
could not fail.

Javier's 3 is a DIFFERENT quantity, and correct in its own setting: the minimal
GOOD cover of S^1 by contractible open arcs with contractible pairwise
intersections (no radius constraint) — the nerve-theoretic count paper 3's
persistent fence is built on. The fence bound needs the metric count at the FIXED
radius the algorithm imposes. Both are now stated side by side so the distinction
is on the record, and both are verified in `scripts/circle_covering_number.py`,
which brute-forces the cover on a 200k-point discretisation AND checks that one
fewer ball fails. The audit now READS the number from that script's output instead
of trusting a hand computation.

**The class of error, and the sweep.** The failure mode was specific: a constant
computed by hand in prose, with no data source, hence invisible to a numeric audit
that compares the paper against `results/`. So I swept all 31 sentences in the tex
that combine geometry vocabulary with numbers. One more was wrong:

- **"fitted centers ... outside a patch whose west edge is at x = 2"** — FALSE.
  Claude's fitted disc has centre (2.328, -0.135), which is 0.686 from the true
  centre (3,0), i.e. INSIDE the true patch. What is true, and now what the paper
  says: the fitted disc spans x in [1.50, 3.15] against the true [2, 4] — dragged
  west onto the evidence, covering the patch's west half, missing x in [3.15, 4]
  entirely, and freezing free space over x in [1.50, 2], with radius 0.824 vs 1.

Everything else in the sweep checks out, including one pleasing cross-check: a
half-plane at x>2 covers exactly (14-2)/16 = 75% of the probed box, matching the
behavioural audit's measured median area_frac of 0.7531 independently. The
Lipschitz constant 1.27 is the max row sum of the affine step map (the correct
induced sup-norm), vol(U) = 1.2 is Monte-Carlo confirmed, and the disagreement
ball's volume (2rho)^(d+m) uses the sup-metric cube correctly.

**A third error of the same class, found while closing the gate-side certificate.**
The coverage certificate needs an UPPER bound on N_cov(U, rho/2); I had used
vol(U)/vol(B), which is a packing LOWER bound and understates it by 2^dim. Fixed
to the rigorous vol(U + B_{rho/4})/vol(B_{rho/4}) with the grown slab computed
exactly. Effect: the rigorous rho moves 0.535 -> 0.615 and the certified bound
1.37 -> 1.57. (A LATER correction of the same class — the boundary factor 2^-(d+m)
on the ball mass — moves them again, to 1.165 and 2.97; see below.)

**And the gate-side covering number is now CLOSED (Prop 9), with two further
corrections of the same 2^dim class (2026-07-25).** For L-Lipschitz f, f_hat with
f_hat passing at tolerance eps, if the visited set is a rho-net of U then
sup_U |f - f_hat| <= eps + 2*L*rho. The sample-size half needed two fixes:

  * the cardinality that enters is the PACKING number (it dominates the covering
    number, and a union bound needs the upper one);
  * the ball mass must be intersected with U, since c is hypothesised only ON U. A
    packing point on dU keeps one orthant of its sup-ball: a factor 2^-(d+m). The
    cart's U has v-extent 0.6, below rho, so corners are attained and the factor is
    real.

A THIRD correction, found on re-reading our own fix: the corner factor 2^-(d+m) is
NOT shear-invariant, and this U is a sheared box, so asserting it left the
certificate 5% optimistic. `ball_mass_fraction()` now computes the true infimum of
vol(B(u,rho/2) ∩ U)/vol(B) over U (attained at a corner, cross-checked against an
interior scan): **0.950 * 2^-(d+m)**. And for the step-t regions, which are UNIONS of
cells, there is no orthant argument at all, so those use a shape-free cell-containment
bound instead.

Instantiated on the deployed cart gate (c = 5/6, L = 1.27, eps = 0.01,
delta = 0.05): one step per rollout gives rho = **1.165** and certifies
sup <= **2.97** (was 0.615 / 1.57 before the boundary treatment); the optimistic
all-steps reading gives 0.310 / 0.797 and is doubly invalid, since it also uses the
step-1 density at steps t >= 2. The hard mode's disagreement of 4.2 exceeds 2.97,
but eps + 2*L*rho GROWS with L, so what is excluded is a pair with
L = max(Lip f, Lip f_hat) <= **1.80** carrying that error — a real but narrow class
against the plant's own 1.27. The wall passes by not being Lipschitz at all. The
continuous coverage analogue closes exactly the smooth case and is silent exactly
where the danger
lives, which is the same boundary the Lipschitz obstruction draws. Limitations
updated from "no continuous analogue" to that, with the two residual gaps named
(density verified in closed form only at step 1 of one instrument; a mixing
argument would earn the optimistic figure honestly).

State: 36 pp, 0 errors / 0 undefined / 0 overfull; **518 audited values**.

## PAPER 2 — Scope audit of the new theory + the pendulum residue closed (2026-07-25, later)

Javier's questions were about SCOPE: is the identity theory including its
boundary, is the covering result general in n, does the constant have a general
analytic form. Honest answers were "hypothesis measured", "yes, but only the
evaluation is instance-specific", "computed for one instrument". All three pushed:

**1. Prop 8's hypothesis is now a machine-checked CERTIFICATE, and the boundary
is derived.** `scripts/truth_plan_invariance_certificate.py`: a candidate's
imagined return under truth depends on the knob only if its trajectory reaches the
clamp, so it suffices to check per knob and per replanning step that (C1) the
argmax candidate stays strictly below the smallest wall in the sweep and (C2)
every clamping candidate scores strictly below it. Then the argmax is the
maximiser over a knob-free subset and the plan is identical — a proof over the
planner's own candidate set, not an observation about outputs. Result: certified at
ALL SEVEN sweep knobs, argmax never exceeding x = 0.344, clamping candidates
losing by >= 5.25. Past the sweep the margin contracts monotonically (4.12 at
x_wall = 11, **0.51** at 12) and the certificate FAILS at 12.5, where the argmax
candidate itself reaches the wall — so the boundary is derived at x_right = 12,
not merely observed via bit-identity.

**2. The covering result was already general in n; the general corollary is now
stated.** Prop 7's proof uses only that fences eps-cover the reachable boundary —
no dimension enters. What is instance-specific is the covering NUMBER. Added
Cor 2: if the reachable boundary is a p-dimensional Lipschitz piece of diameter D,
N_cov = O((D/eps)^p), so the deployment repair cost is exponential in the
BOUNDARY's dimension (p = 0 gives the exact 1 measured in 1D; p = 1 gives the
measured 1.05 -> 4.25 as the arc lengthens; p = 2 would cost O((D/eps)^2)). That
is the precise sense in which the danger is dimension-free and the repair is not.

**3. The density constant has a general closed form: a VOLUME RATIO.** Added
Remark: if the step-k law of (s,a) is uniform on a set U (as at k=1 whenever the
one-step map is affine in the randomized coordinates), then c = 1/vol(U) exactly
and the reveal probability is q >= vol(B)/vol(U) — literally the fraction of the
gate's one-step reachable volume that the guaranteed disagreement ball occupies;
for non-uniform laws c = inf p_0 / sup|det DF| by pushforward. The cart's 5/6 is
that formula evaluated: vol(U) = (2*gain*dt*a_max) * 1 * (2*a_max) = 1.2.

**4. The pendulum's below-random residue: CLOSED (the non-Qwen data item).**
Diagnosis said the symmetric sharp variant starves the random baseline too, so
narrow only the PHANTOM plateau. Added per-plateau widths to PendulumStop
(`width_left`/`width_right`, defaulting to `width` so every committed run stays
bit-identical — verified) and a `--width-right` flag. With width_right = 0.08:
**below random at 6/6 knobs**, J_blind in [4.3e-4, 7.1e-4] against a surviving
J_rand in [0.0572, 0.0584], J_truth unchanged at 20.08, contact 1.00 everywhere,
and play_cost in [1.0028, 1.0029] — spread **7.1e-5**, tighter than the symmetric
variant and 850x tighter than the default. So the strong form now holds on both
instruments: exploited, pinned, below random at EVERY knob, play_cost invariant to
1e-4.

The audit caught one of my numbers again: I wrote J_rand = 0.0577 for the
asymmetric variant when it is a range [0.0572, 0.0584]. Fixed in both places.

State: 35 pp, 0 errors / 0 undefined / 0 overfull; **501 audited values**.

## PAPER 2 — The exact measurements were theorems in disguise: four proved (2026-07-25)

Javier: "mencionas varias cosas medidas que salen completamente exactas, me pregunto
si eso es hint de algo más que se puede demostrar". It was, four times over. Each
item below started as a suspiciously exact measurement and ends as a proposition
whose hypotheses are either derived or measured to a stated precision.

**1. play_cost's knob-invariance → an identity (Prop 8).** With the two baselines
knob-free, play_cost(k) = J_truth/(J_truth-J_rand) - J_blind(k)/(J_truth-J_rand):
affine in the exploited planner's own return. So the whole knob-dependence IS its
residual reward over the truth-minus-random margin. Verification: J_truth is
knob-identical to twelve digits; the identity predicts every measured play_cost to
2.4e-10 (sharp) / 7.3e-6 (default), and BOTH residues are themselves accounted for
by first-order propagation of J_rand's knob-variation (dplay_cost/dJ_rand = 0.0598
times 3.9e-9 = 2.33e-10; times 1.226e-4 = 7.33e-6 — three digits).

**2. The hypothesis behind it has a located boundary.** Why is the truth planner
indifferent to the knob at all, given the clamp changes imagined values for
right-going candidates? Extended the sweep past its range
(`results/truth_planner_knob_regime.json`): J_truth is bit-identical at
17.659688408965 for x_wall in {8, 10, 10.5, 11, 11.5, 12} with truth contact 0.00,
then flips at 12.5 to 35.84 with contact 1.00. The boundary is structural — the
plan flips exactly once the wall stops blocking the far plateau (x_right = 12) —
so the invariance regime is "the wall lies between start and reward", and the
paper's sweep [2, 10] sits well inside it.

**3. The eps-flatness → an identity with a computable threshold (Prop 3).**
CORRECTED 2026-07-25; the earlier version of this entry claimed a cross-sample
PREDICTION and it was falsified on 2 of 4 arms. For a rollout w let D(w) be the max
sup-norm disagreement over its mode contacts. Reveal-rarity(eps) = P(D > eps)
exactly, so it equals the mode-firing rarity for every eps < eps* = min{D(w) : D(w)
> 0}. The catch: eps* is a property of a SAMPLE. `eps_invariance_threshold.py` used
`Random(0+i)` while `continuous_eps_sweep.py` draws `Random(10000+i)`, so the two
were different random quantities and agreeing was luck. It now defaults to the
sweep's own stream, where the relation is an IDENTITY:

| arm | eps* (sweep's stream) | firing | first grid eps >= eps* | same-sample sweep |
|---|---|---|---|---|
| cart wall@8 | 0.3959 | 25 | none in grid | flat through 0.3 |
| cart wall@4 | 0.1137 | 277 | 0.3 | 0.1385 to 0.1, 0.1355 at 0.3 |
| pend stop@1.0 | 0.0791 | 282 | 0.1 | 0.1410 to 3e-2, 0.1400 at 0.1 |
| pend stop@1.4 | 0.0805 | 35 | 0.1 | 0.0175 to 3e-2, 0.0170 at 0.1 |

Second correction: a minimum is unstable, upward-biased and decreasing in n, so it
must not be read to the last digit nor compared against a grid edge. Across equal-
sized independent streams eps* moves 1.8x on wall@4 (0.114 / 0.146 / 0.201) and
1.4x on wall@8 (0.396 / 0.438 / 0.538, each over only ~21-25 firing rollouts). At
10x the sample it falls further: 0.065 on wall@4 and **0.272 on wall@8** — below
the grid's top point of 0.3, so "wall@8 is flat throughout the grid" is a statement
about the 2000-rollout sample, not about the arm. The script now reports the firing
count, the second order statistic, other streams and the 10x sample, so the
resolution is visible instead of a false decimal.

Note eps* is a per-rollout MINIMUM of a per-contact MAXIMUM: a pinned rollout
contacts many times and only needs one coarse contact to be revealed, which is why
eps* sits two orders above the smallest single-contact disagreement — now COMPUTED
rather than asserted: 0.001794 over the 919 contacts on wall@4 (the field used to
be `null` in the JSON while the paper quoted 0.0017 from nowhere).

**4. "Exactly one violation on all 11 rows" → a PACKING number (Prop 7), and in 1D
an eps-dependence that is measured rather than assumed.** SUPERSEDED TWICE; this is
the current version (2026-07-25). Two corrections, both from peer review:

  * The bound is a **packing** number of the fence locus, not a covering number.
    A covering number counts an OPTIMAL cover and the planner is an adversary
    against the fence, so it can place every point of a maximal packing first.
    Verified counterexample on the unit circle at eps = 0.5: 12 equispaced fences,
    pairwise chord distance 0.5176 > eps, every one adding new coverage on a 200k
    grid sweep — against a covering number of 7. `circle_covering_number.py`
    computes both. N_pack(A,eps) <= N_cov(A,eps/2) keeps Cor 2's ORDER intact.
  * The 1D "exactly 1.00" is **not** the covering hypothesis being satisfied. The
    fence is recorded at the model's refuted PREDICTION, which overshoots the wall
    by 0.17–0.58 against eps = 0.25, so the band does not contain x_wall in 4 of 5
    cart episodes — yet the count is still 1. What the count is sensitive to is the
    strip between the boundary and the fence: `fence_separation_census.py` sweeps
    eps and finds the outcome IDENTICAL from 0.25 down to 0.05 and then moving at
    0.01 (2 violations on 2 of 4 seeds), i.e. the 1.00 holds while the band is wide
    relative to the overshoot and fails when it is not. That is a stated, checkable
    hypothesis instead of a theorem that did not apply.

Also corrected: the arc percentages (8%/21%/34%, later 17%/43%/68%) were the
violation count divided by the budget, i.e. saturation assumed and restated as a
percentage, then used to explain the count. The probed arc is now measured directly
per patch per episode. And PatchField2D is bi-modal, so a one-circle budget was half
the right one.

This is the covering/packing-number analogue delivered on the MITIGATION side; the
gate side has its own (Prop 9), so the Limitations' "open" note is retired on both.

**5. Prop 6's density hypothesis, closed for one instrument (Cor 1).** For the
cart's gate at step 1 the (x,v,a) density is CONSTANT on a sheared set (not a
product of marginals: x_1 = x_0 + dt*v_1 makes the two dependent, but the shear has
unit Jacobian so the value is the product of the normalizations):
c = 1/(2*gain*dt*a_max) * 1 * 1/(2*a_max) = **5/6**, Monte-Carlo confirmed to 1.3%
(`scripts/gate_density_constant.py`). So the detectability bound is quantitative
here: hiding an eta-sized error from the deployed gate (eps=0.01, N=40) with
probability > 1/2 needs L >= 0.33 (eta=0.1), 1.78 (eta=0.5), **15.2 (eta=4.2)**
against the plant's own sup-metric Lipschitz constant of 1.27. The last row is the
instrument's own number — 4.2 is the wall-region probe error of §9 — so no smooth
pair less than **twelve times as sensitive as the plant** can hide the wall from
this gate. That is why the smooth arms are detected (bump reveal-rarity 0.18)
rather than hidden: their harmlessness is play_cost, not invisibility.

**6. The joint bracket is Frechet-Hoeffding sharp.** Its ends are the
Frechet-Hoeffding bounds for P(R1 u R2) given the marginals, pushed through
x -> x^N, so the interval is the EXACT range consistent with r1, r2: no bound in
the marginals alone can be tighter, and it narrows only by measuring something
beyond them (which is what r_union is).

State: 34 pp, 0 errors / 0 undefined / 0 overfull; **490 audited values**.

## PAPER 2 — Reinforcing the weakened statements: 4 of 5 earned, 1 superseded (2026-07-25)

Javier: "vamos a ir reforzando esos incluido el 5". Worked the
`docs/paper2/STRONGER-STATEMENTS.md` list.

**Item 4 — censored zeros: RESOLVED.** Pendulum rarity 3000 → 30,000 rollouts
(591 s): θ_stop=2.0 goes from `0/3000` to **0.0007 [0.0004, 0.0010]**, so every
row is a point estimate and every d@40 a number instead of a bound. Axes 2000 →
20,000 (716 s): the sub-eps arm goes from `0/2000` to 0.0001, predicted pass
0.9940, **inside** the measured [0.9814, 0.9994]. Two unrequested bonuses:
wall@8's prediction moves 0.6046 → **0.6622** against a measured 0.667, killing
the standing "prediction below the Wilson lower bound" caveat (it was the rarity
estimate's noise); and with the cart raised to 30,000 too, the two independent
estimates of the same event agree to the third decimal (0.1352 vs 0.1351, versus
0.1430 vs 0.1385 before). Figures regenerated.

**Item 2 — disjoint seed blocks: 0.84 RESTORED, legitimately.** `--seed-offset`
added to `continuous_danger_synthesis.py` (+2 tests: blocks disjoint, resume does
not re-spend within an offset block). Large arm re-run at offset 20 on the cart
headline cell (605 s) and the pendulum headline knob (646 s). Cart: mini@S0 +
large@S20 = **20/20 on 20 INDEPENDENT samples, Wilson 0.8389**; the gate-miss rate
is now poolable as well (20/40 independent samples lacked the mode vs a predicted
0.63). Pendulum: 15/15 disjoint, Wilson **0.796** (was 0.701 per size). Repair
total 82/82 → **106/106** over 65 distinct samples. Each headline cell now carries
two orthogonal replications: same samples/different model (large@S0) and different
samples/same model (large@S20).

**Item 5 — sharp-plateau variant: the strong claim EARNED on the cart.** Done
non-destructively (`scripts/continuous_sharp_plateau.py`, sibling JSONs, default
instruments and every paid synthesis artifact untouched) because re-calibrating the
default reward would have invalidated the synthesis contracts. Cart width 0.5→0.2:
blind below random at **7/7** knobs (was 6/7) by 2–13 orders of magnitude.
Pendulum 0.25→0.1: **5/6** (was 3/6). What strengthened more than the target:
play_cost becomes knob-invariant to ~1.5e-4 on both instruments, a **400×
tightening** — the invariance the defaults show approximately is exact without the
tail. The pre-registered risk (a sharper plateau starving random-shooting MPC of
gradient) did not materialise: J_truth 17.77→17.76 and 20.08→20.05, contact 1.00
everywhere. Honest residue: the pendulum's widest stop still has J_blind 3.1e-3
over J_rand 3.6e-4 — there the *random* baseline collapsed to 1e-4, so below-random
stops being the informative comparison and play_cost = 1.0000 is.
**Bug found and fixed on the way:** the reward's `1 + math.exp(z)` raises
OverflowError when a narrow plateau meets a free-spinning pendulum (|z| > 709).
Replaced by `_sigmoid_denom`, bit-identical for |z| ≤ 700 (verified) and correct in
the limit beyond; the 1D mitigation golden pins passed unchanged, which is exactly
what they are for.

**Item 6 — the measure version of the Lipschitz bound: PROVED.** New proposition:
with a gate whose step-k visitation density is ≥ c on the guaranteed ball, one
rollout reveals the disagreement with probability ≥ c((η-ε)/L)^(d+m), so the miss
probability is ≤ (1-q)^N — and hiding an η-sized error from N rollouts forces
L ≥ (η-ε)(cN/ln(1/δ))^(1/(d+m)), i.e. the Lipschitz constant needed to hide grows
like N^(1/(d+m)): hiding gets *easier* with dimension. The density hypothesis is
stated, not verified per instrument (our step-1 gate law is supported on a
lower-dimensional set); the measured stand-in is the smooth bump arm's
reveal-rarity, 0.18 against the hard wall's 0.14.

**Item 3 — SUPERSEDED by a better result.** The plan (an instrument with provably
independent modes, so the product form could be derived) was wrong on its own
terms: moving modes apart makes the events *disjoint*, the opposite of independent.
Replaced by a remark stating what is true — both bracket ends are attained (the
lower one in our data, at six of nine knobs where no rollout out of 600 contacts
both patches), and exact factorization is a property of the **gate**: a stratified
gate spending independent budgets N1, N2 on the two mode regions has joint miss
probability exactly (1-r1')^N1 (1-r2')^N2. A design consequence for multi-mode
pipelines, at zero compute cost.

**Reproducibility fact worth recording.** Re-running the cart/pendulum sweeps from
HEAD did NOT reproduce the committed JSONs bit-for-bit: max **2 ULPs** (3.6e-15),
from refactors of the shared env/harness code since those sweeps were run. No
printed digit changed at any precision the paper uses (verified), and the JSONs
were regenerated so HEAD is self-consistent again. The patch2d family, by
contrast, reproduces byte-identically.

State: 32 pp, 0 errors / 0 undefined / 0 overfull; **453 audited values**; 342
tests pass.

## PAPER 2 — Reference & proof review: an independence error in the joint danger factor (2026-07-25)

Review of (a) external citations, (b) code references, (c) the proofs. Findings,
all closed by measurement or by making the statement match what is proved.

**0. The correction became a theorem.** Rather than leave the joint factor as a
measured number, the paper now proves a two-sided bracket that needs no
independence assumption — (1-min(1,r1+r2))^N ≤ (1-r_∪)^N ≤ (1-max(r1,r2))^N, with
the product inside it — plus an exact sign rule: the product over-estimates the
joint miss probability iff P(both) < r1·r2. `audit_paper2_numbers.py` checks the
bracket, the sign rule and inclusion-exclusion consistency at all nine knobs (443
values total). So the pre-review claim ("the law composes per mode") was an
assumption; what replaced it is stronger, not weaker. Everything the reviews *did*
weaken is listed with a recovery route in `docs/paper2/STRONGER-STATEMENTS.md`.

**1. The joint gate-miss factor was composed, not measured — and the product is
wrong by up to 17%.** §3.3 claimed "the danger law composes per mode: the joint
factor is (1-r1)^N (1-r2)^N". That product is the joint factor only if the two
per-mode contact events are independent WITHIN a rollout, which PatchField2D does
not satisfy. `continuous_patch2d.py` now measures the union event directly
(`r_either`, plus `r_both` to expose the dependence) and reports
d@40_joint = play_cost * (1 - r_either)^40; the product is kept alongside as
`d40_joint_indep_approx` so the error stays visible. Re-run (557 s): every
previously committed column reproduces EXACTLY (r1, r2, J_truth, J_blind,
J_random, play_cost, contact, d40_p1, d40_p2), and the joint column moves:

| k1/k2 | r_either | r1+r2 | P(both) | r1·r2 | d@40 exact | d@40 product | bias |
|---|---|---|---|---|---|---|---|
| 3/6 | 0.1500 | 0.1500 | 0.0000 | 0.00118 | 0.0015 | 0.0016 | +5.7% |
| 4/6 | 0.0917 | 0.0967 | 0.0050 | 0.00074 | 0.0215 | 0.0178 | −17.2% |
| 4/7 | 0.0950 | 0.0983 | 0.0033 | 0.00088 | 0.0185 | 0.0166 | −10.3% |
| 2/7 | 0.2533 | 0.2533 | 0.0000 | 0.00204 | 0.0000 | 0.0000 | +11.5% |

P(both) ∈ [0, 0.005] against r1·r2 ∈ [0.0007, 0.0025] — *below* independence at
some knobs (a frozen rollout has spent its travel) and *above* it at others
(reaching the far patch means passing the near one), which is why the product
errs in both directions. Prop. 1 itself is untouched: it holds for any measurable
critical event, and the union event is one.

**2. Three code quotes in the paper were not verbatim; one was fabricated.**
- The superstitious clamp was printed as `if abs(x2 - 8.0) <= 0.15 and abs(v2)
  <= 1.1: x2 = 8.0`. **No artifact contains `abs(v2) <= 1.1`.** The real one (the
  x_wall=4 cell the surrounding text cites, mini seed 20000, gate 0.9738) is
  `if abs(x2 - 4.0) <= 0.15 and abs(v2) <= 2.5: x2 = 4.0; v2 = 0.0`.
- The pendulum repair was rendered schematically (`th2 >= theta_stop`); artifacts
  write the literal knob: `if th2 >= 1.4: return [1.4, 0.0]`.
- Claude's phantom stop is the `elif` branch of a symmetric pair, not an `if`.
`audit_paper2_numbers.py` now checks every quoted snippet against the artifact
corpus (whitespace and `;` normalised) plus every cited repo path, so a quote
nobody produced fails CI.

**2b. A second vacuous check, and a metric that was silently missing.**
`patch2d_artifact_audit.py` emitted `area_frac` only on the half-plane branch, so
bounded/square/disc-form rows carried `None` and any downstream comparison had to
guess a default. Fixed (emitted for every artifact), and the partial-repair claim
restated threshold-free on the branch where it is definable: of the 66
see-one-miss-the-other seeds, 28 freeze sets contain the seen patch, by freezing
15×–81× its area (median 61×), and exactly ONE is patch-selective — seed 180000,
a half-plane at 31× the patch area, i.e. selective by where its threshold falls,
not by encoding a region. Gate rejected it like all the others.

**3. "(tested char-identical)" was not tested and not char-identical.** The n-D
generalisation rewrote 33 lines of `mitigation.py`; the 1D claim is behavioural.
Now pinned by `tests/test_mitigation_1d_regression.py` (exact ret / violations /
first-contact for cart and pendulum, plus the single-violation property), and the
paper says behavioural + names the test.

**4. Proof precision (no result changed).** Prop. 2 now instantiates Prop. 1 at
R = {rollouts visiting M} instead of relying on it implicitly; Prop. 3's coupling
notes that "no query ever lands in E" is a single coupling-measurable event, not
two model-dependent ones; Prop. 4's radius is stated for L > 0 with L = 0 as the
degenerate case (the formula divides by 2L); the corollary defines J_max/J_min as
the *realizable* return range, without which "saturated" is not well-founded —
and records that on the cart the bound is *attained* (17.77/17.24 = 1.031 both
sides) because the exploited planner sits at the realizable floor. Abstract:
"cannot realize the localized geometry" → "*exactly* localized"; "no learner can
infer it" → "from the sample".

**5. Bibliography verified against source.** 21/21 entries complete; Lehrach et
al. confirmed as ICLR 2026 with the 16-author list and OpenReview id matching;
Fazeli IJRR 36(13–14):1437–1454 and Corso JAIR 72:377–428 match exactly. Removed
one unverifiable detail ("Poster") from the Lehrach note.

**6. Also fixed: a second censored zero.** `tab:axes`'s sub-eps arm reveals a
disagreement in 0/2000 rollouts, so its predicted pass rate 1.0000 sat outside
the measured pass CI [0.9814, 0.9994]. Now reported as the raw count with the
prediction as an upper bound: at the Wilson upper rarity (0.0019) the prediction
is 0.926, and the measured 0.997 lies inside [0.926, 1.000].

## PAPER 2 — Pre-arXiv review closure: 2D cross-family arm, two missing entry points, re-run validation (2026-07-24)

A pre-submission review of paper 2 raised eleven items (3 blocking, 4 substantive,
4 minor). All were closed by measurement or by a precision fix, not by hedging.

**1. Two scripts the paper cited did not exist.** §5 cited
`scripts/continuous_cem_patch2d.py` and the §6 text cited
`scripts/continuous_eps_sweep_patch2d.py`; the actual invocations were
`continuous_cem.py --instrument patch2d` / `continuous_eps_sweep.py
--instrument patch2d` (the appendix had it right, the body did not). Both now
exist as first-class entry points that delegate to the shared implementation via
`runpy` — no duplicated measurement code, so the 1D and 2D paths cannot drift —
and stamp `entry_point` into their JSON for provenance. **Both were re-executed
from a clean invocation of the new entry points and produced output
byte-identical to the committed JSONs** (only `elapsed_s`/`entry_point` differ:
837 s vs 1144 s, 449 s vs 898 s wall-clock). So the paper's CEM row
(pc −0.022/+0.017/+0.020, crossing 0.0697<0.2076, 0.0270<0.1488,
0.0091<0.0943, contact 0.05) and the per-mode eps-flatness (0.147 / 0.142 /
0.005, constant across the whole eps grid) reproduce exactly.

**2. The 2D repair collapse was GPT-5.x-only — now it has a second family.**
The abstract/intro said "no model recovers the region rule", but PatchField2D had
been run on GPT-5.x mini+large only (with shared samples). Two arms were
attempted:

- **Qwen: ABORTED after 3 cells — partial, recorded.**
  `continuous_danger_synthesis.py mini 10 --instrument patch2d --k1 3 --k2 7
  --compat-model Qwen/Qwen3-Coder-30B-A3B-Instruct` died on HTTP 402 (HF
  Inference Providers monthly credits exhausted) after completing the arm order's
  first three cells, which are all **full-arm**:
  `results/continuous_synthesis_patch2d_compat-qwen3-coder-30b-a3b-instruct_k3_7.json`
  — 3/3 gate 1.000 at 0 refine iterations, both discs written exactly on the
  landing position `(x2-3)²+(y2-0)² <= 1.0` / `(x2-7)²+(y2-0)² <= 1.0`, per-patch
  blindness 0.0/0.0. So Qwen contributes a clean TRANSLATION control on the 2D
  instrument and **zero** incomplete-arm (induction) data. Reported as exactly
  that; the 2D induction evidence is GPT-5.x's 156 seeds + Claude's 3.
- **Claude (agent-relayed): 3 mode-containing seeds + 1 full control at k=(3,7)**,
  Sonnet, same N=40 sample, same eps=1e-9 pinned-integrator gate, same 5-iteration
  memoryless refine loop. `continuous_claude_step.py` gained patch2d support
  (per-mode blindness + `sample_contains_mode_per`, knob in the record key, and a
  `--model-label` so the arm is attributable). Seeds 10000/20000 are
  see-P1-miss-P2; seed 30000 sees BOTH patches.

  **Full control: gate 1.000 at iteration 0**, both discs written on the landing
  position, blindness 0.0, play_cost 0.0 — translation is not the problem, exactly
  as with GPT-5.x. **Incomplete arm: no repair.** The trajectory is the finding:
  every seed sits in a **period-2 cycle** between the pure-blind artifact and a
  wrong template, returning to the iteration-0 gate value on every even iteration.
  Per-iteration ledger (`scripts/claude_relay_ledger.py`, which re-derives gate
  accuracy and rule class from the versioned transcripts →
  `results/continuous_claude_relay_patch2d_k3_7.json`):

  | seed | it0 | it1 | it2 | it3 | it4 | it5 |
  |---|---|---|---|---|---|---|
  | 10000 | blind .9934 | disc-**current** .9591 | blind .9934 | halfplane .9284 | blind .9934 | reward-thresh .7044 |
  | 20000 | blind .9962 | halfplane .9406 | blind .9962 | halfplane .9406 | blind .9962 | halfplane .9406 |
  | 30000 | blind .9966 | reward-zone .6750 | blind .9966 | halfplane .8406 | blind .9966 | y-band .5328 |

  All three terminate REJECTED at iteration 5 (0/3 repair). The even iterations
  return to the iteration-0 gate value exactly, on every seed — the memoryless
  refine loop deletes the failed template and re-emits the blind artifact.

  The templates are exactly the library the GPT-5.x campaigns exhibited: 1D
  threshold (all three seeds), a radial disc conditioned on the **current**
  instead of the landing position (seed 10000 — the wrong-causal-variable error
  Ablation 1 found in 36/40 guided artifacts), and a reward-landmark freeze zone
  (seed 30000). **No incomplete iteration in any seed wrote a disc on the landing
  position** — the form this same model writes immediately when the contract
  states it. The template prior is therefore not a GPT-5.x idiosyncrasy.

  Transport note: two of seed 10000's relays (msg3, msg5) were dispatched twice
  after the first appeared to hang. Pre-registered rule: the first completed relay
  of a message wins. In both cases the original landed first and is the one used;
  both duplicates are preserved as `..._msg{3,5}_duplicate_relay_DISCARDED.txt`
  rather than deleted. Neither would have changed the finding — they wrote a
  segment/capsule distance and a disc, both on the CURRENT position. Relayed
  instances were instructed not to use tools or read files, so each artifact is a
  function of the pipeline message alone; that framing is recorded with the
  transcripts and disclosed in the paper.

**3. Precision fixes (no new data needed).** Abstract cut to 1865 ASCII chars for
arXiv's hard 1920-char metadata limit (`docs/paper2/abstract-arxiv.txt`);
mini/large **share their gate samples by construction** (`rollout_seed =
10_000*(i+1)`, model-independent) so every pooled "both sizes" count is n samples
× 2 synthesis draws — now stated once in §9 and applied everywhere, with per-size
Wilson bounds (0.72 cart, 0.70 pendulum) replacing the pooled ones (0.84, 0.824)
as the bounds relied on, and the (1−r)^N check explicitly never pooled; the
pendulum θ_stop=2.0 rarity is a censored zero (0/3000, Wilson upper 0.0013) so its
d@40 is now reported as an upper bound with the CI-implied floor (0.895); exact
Azure deployments footnoted (`gpt-5.4`, `gpt-5.4-mini`, API 2025-04-01-preview);
the 38-vs-39 half-plane count between hand inspection and the behavioral audit
reconciled to a syntax-vs-behavior reading of two named artifacts (mini k3_7
seeds 130000, 150000 — radial predicates anchored at the reward lodes);
Prop. 4's hypothesis widened to L ∈ [0,∞); Corollary 1's display made |play_cost|.

## PAPER 2 — Behavioral audit of the patch2d artifacts: the hand inspection VERIFIED (2026-07-23)

`scripts/patch2d_artifact_audit.py` (oracle-selftested: 7 constructed classes
+ a two-patch case) → `results/patch2d_artifact_audit.json`. The same
freeze-mask instrument built for paper 3's ring audit, adapted to
PatchField2D: probe each artifact's `step()` on an 81×81 grid over
[−2,14]×[−8,8] at two velocity slices, mark deviations from the pure
integrator, classify the deviation set's SHAPE (halfplane-unbounded /
disc-form / square-form / bounded-other / point / vdep / blind, with a
textual-patch sub-split for measure-zero traps), measure per-patch coverage,
and check integrator arithmetic on a west control strip (freeze-form
deviations there are mode-rule overreach, not wrong arithmetic).

**Every §7.1 hand-inspection claim is behaviorally CONFIRMED** (this matters
because on paper 3's ring the same instrument *corrected* my hand reading —
here it validates the paper's):

| paper claim (hand inspection) | behavioral audit |
|---|---|
| 76 mode-present incomplete seeds | 76 ✓ |
| 38/76 dimensional reduction (half-plane) | 39 ✓ |
| 20 pure-blind + 9 superstitious | 13 pure-blind + 7 textual-patch (measure-zero traps, behaviorally blind) + 4 point (+3 square-form, 2 bounded-other) ✓ structure |
| 9/76 disc-form attempts, none correct | 8 ✓ |
| ~74/76 integrator exact | **74/76 exact** (16 west-strip flags resolve to 14 freeze-form mode overreaches + exactly 2 numeric) ✓ |
| 0 partial repair (gate-level) | **CORRECTED 2026-07-24**: the original check was vacuous (it read `per["p1"]` while the key is `"patch1"`, so its condition never fired). Real numbers: **34/76** freeze sets DO contain a seen patch (>90% coverage) — half-planes swallowing the disc, freezing ~75% of the probed box — and **0/76** contain one while freezing little else (area within 2.5× the patch's 1.2% share). No partial repair in the sense that counts ✓, but "no artifact covers the seen patch" was wrong and is fixed in the tex. |

The two later results awaiting the tex fold are also behaviorally grounded:
- **Square ablation (bidirectional template):** on SQUARE evidence the class
  mix is the same story — halfplane dominates (20/40), and among bounded
  attempts disc-form 5 vs square-form 1: models impose the round template on
  square evidence, mirroring the half-plane imposed on disc evidence.
  Integrator exact 40/40.
- **Region+3×-budget confound cells:** the guidance ELIMINATED the half-plane
  reduction (1/40 vs 21/40 in the k3_7 base) and moved artifacts to bounded
  2D fits — point/micro-unions 15, bounded-other 6, square-form 5, disc-form
  2, blind-ish 11 — none the true disc; integrator exact 40/40. Matches the
  hull-fitting reading (RESEARCH-DIRECTION), now measured.

## PAPER 2 — PatchField2D (4D bi-modal instrument): the danger law composes; repair is geometry-dependent (2026-07-18)

The third instrument closes the two structural gaps the reviewers flagged on the 1D
instruments — a 4D state and two independent modes — by adding a `PatchField2D`
environment (`src/cwm/continuous/envs`): state `[x, y, vx, vy]`, scalar heading action
`φ = π·clamp(a)/a_max`, two circular sticky patches `P_i = disc(c_i, R)` with a
stay-at-previous-position clamp (`(x2,y2) ∈ P_i ⇒ next = [x, y, 0, 0]`), and two radial
sigmoid lodes (small real one near the start, large phantom one behind the patches).
Knobs `k1` (near patch) / `k2` (far patch) are the patch-center distances along/off the
start→lode corridor; defaults frozen once (never per cell).

### Mechanism — the danger law composes per mode (2026-07-18)

`scripts/continuous_patch2d.py` → `results/continuous_patch2d.json`. 600 rarity rollouts,
20 MPC episodes/arm per cell, 3×3 knob grid. `J_blind = 0.00` and `J_rand = 0.11` at every
cell; `play_cost` knob-invariant at [1.005, 1.006]. Per-mode rarities separate cleanly
(`r1 ∈ [0.085, 0.245]`, `r2 ∈ [0.0067, 0.0100]`). The danger law composes mode-wise:
per-mode `d@40 = pc·(1−r_i)^40`, joint `d@40 = pc·((1−r1)(1−r2))^40`.

| k1 | k2 | r1 | r2 | J_truth | J_blind | J_rand | pc | d40_p1 | d40_p2 | d40_joint |
|---:|---:|-----:|------:|-------:|-------:|------:|-----:|------:|------:|--------:|
| 2 | 6 | 0.2450 | 0.0100 | 17.98 | 0.00 | 0.11 | 1.006 | 0.0000 | 0.6732 | 0.0000 |
| 2 | 7 | 0.2450 | 0.0083 | 18.02 | 0.00 | 0.11 | 1.006 | 0.0000 | 0.7200 | 0.0000 |
| 2 | 8 | 0.2450 | 0.0067 | 18.08 | 0.00 | 0.11 | 1.006 | 0.0000 | 0.7700 | 0.0000 |
| 3 | 6 | 0.1417 | 0.0083 | 18.57 | 0.00 | 0.11 | 1.006 | 0.0022 | 0.7197 | 0.0016 |
| 3 | 7 | 0.1417 | 0.0083 | 18.47 | 0.00 | 0.11 | 1.006 | 0.0022 | 0.7197 | 0.0016 |
| 3 | 8 | 0.1417 | 0.0067 | 17.72 | 0.00 | 0.11 | 1.006 | 0.0022 | 0.7699 | 0.0017 |
| 4 | 6 | 0.0883 | 0.0083 | 20.85 | 0.00 | 0.11 | 1.005 | 0.0249 | 0.7192 | 0.0178 |
| 4 | 7 | 0.0883 | 0.0100 | 19.52 | 0.00 | 0.11 | 1.006 | 0.0249 | 0.6727 | 0.0166 |
| 4 | 8 | 0.0850 | 0.0083 | 19.08 | 0.00 | 0.11 | 1.006 | 0.0288 | 0.7196 | 0.0206 |

**Honest notes.** The `r2` knob is only weakly resolved at 600 rollouts (its trend is
under-resolved, not flat); the `k1=4` one-hit bump in `r2` is sampling noise, not a knob
effect.

### Synthesis — we predicted partial repair; we measured none (2026-07-18)

`scripts/continuous_danger_synthesis.py --instrument patch2d` (Azure GPT-5.x mini + large,
20 seeds/cell, N=40, ε=1e-9) on two bi-knob cells, k=(3,7) and k=(5,9). Per-seed JSONs:
`results/continuous_synthesis_patch2d_{mini,large}_k{3_7,5_9}.json`.

| file (model) | full | see-both | see1-miss2 | miss1-see2 | miss-both (certified) |
|---|---|---|---|---|---|
| mini_k3_7 (gpt-5.4-mini) | 20/20 | n=5 cert=0, gate [0.1663, 0.9969] | n=15 cert=0, gate [0.0312, 0.9978] | — | — |
| large_k3_7 (gpt-5.4) | 20/20 | n=5 cert=0, gate [0.0034, 0.9912] | n=15 cert=0, gate [0.5687, 0.995] | — | — |
| mini_k5_9 (gpt-5.4-mini) | 20/20 | — | n=17 cert=0, gate [0.0013, 0.9991] | n=1 cert=0, gate [0.9997] | n=2 cert=2, gate [1.0], play_cost 1.095 |
| large_k5_9 (gpt-5.4) | 20/20 | — | n=17 cert=0, gate [0.9266, 0.9997] | n=1 cert=0, gate [0.9891] | n=2 cert=2, gate [1.0], play_cost 1.095 |

**Headline (prediction-inverting).** The plan predicted PARTIAL REPAIR (a see-one-miss-other
sample yielding an artifact that repairs the seen patch and is blind+certified on the
unseen one). MEASURED: **0 partial-repair events in 66 see-one-miss-other cells**
(66 = 64 see1-miss2 + 2 miss1-see2), and **0/76 in-sample incomplete artifacts recovered
the disc rule at all** (76 = 80 incomplete seeds − 4 miss-both). Certification occurred
**iff** the sample missed ALL modes: the only certified incomplete artifacts are the
**4/80 miss-both seeds** (2 per size at k=(5,9)), blind on both patches, exploited at
play_cost 1.095, contact 1.0. The all-or-nothing gate REJECTED every partial artifact
rather than certifying it, so certification stayed sound in the strict sense (no wrong
artifact certified on a covered transition); danger still lives exactly in the
`(1−r1)^N (1−r2)^N` joint-miss event.

**Mechanism (76-artifact code inspection).** Plant translation succeeds (≈74/76 exact 4D
integrator + reward). What collapses is INDUCTION of the 2D circular boundary. The modal
failure is DIMENSIONAL REDUCTION: the disc modeled as a CartWall half-plane (right location,
wrong shape, e.g. `if x2 > 4.0`). Classification of the 76:

| class | count | description |
|---|---:|---|
| dimensional reduction (half-plane) | 38/76 | disc → 1D half-plane clamp at the right location, wrong shape |
| pure-blind | 20/76 | no patch logic at all |
| superstitious | 9/76 | local patch fitted to observed contacts, mispredicts elsewhere |
| disc-form but incorrect | 9/76 | attempts a circular form, none correct |

The ε-exactness alternative is **falsified**: no correct-form disc failed on arithmetic;
the discs that failed were the wrong shape.

**Phrasing cautions (validated).** (i) High failing gates (e.g. 0.9997) = contact RARITY
in a short rollout, NOT near-repair — more iterations would not populate a partial-repair
branch that does not exist. (ii) mini/large partitions are seed-identical by construction
(shared seeds) — not independent replication. (iii) the count is 0/66 see-one-miss-other
(66, not 64).

**The arc.** On 1D clamps the discrete paper's (b)-residual vanished (GPT-5.x repaired
82/82); on the 2D circular mode it RETURNS (0/76). Repair-from-data is geometry-dependent,
so the danger law's exhaustiveness claim is itself geometry-scoped.

### eps sweep — per-mode reveal-rarity exactly flat (2026-07-18)

`scripts/continuous_eps_sweep.py --instrument patch2d` →
`results/continuous_eps_sweep_patch2d.json`. Mode-arm reveal-rarity is EXACTLY flat across
the entire ε grid, per mode:

| arm | rarity (constant across grid) |
|---|---:|
| patches omitted | 0.147 |
| patch1 only omitted | 0.142 |
| patch2 only omitted | 0.005 |

The per-mode arms recover the per-mode rarities of the mechanism sweep — the tolerance axis
is orthogonal to the mode hole on the bi-modal instrument, separately for each mode.

### CEM row — blind CEM not exploited; the anticipated 2D competence gap did not materialize (2026-07-18)

`scripts/continuous_cem.py --instrument patch2d` → `results/continuous_cem_patch2d.json`.
horizon 40, 5 iters, 64 samples, elite 0.125, min-std 0.05 (one fixed setting).

| knob | pc | t95 | contact | crossing CEM | crossing MPC |
|---|---:|---|---:|---:|---:|
| (2,6) | −0.0224 | [−0.1189, +0.0741] | 0.05 | 0.0697 | 0.2076 |
| (3,7) | +0.0174 | [−0.0191, +0.0540] | 0.05 | 0.0270 | 0.1488 |
| (4,8) | +0.0200 | [−0.0257, +0.0658] | 0.05 | 0.0091 | 0.0943 |

pc t95 includes 0 on all 3 rows; crossing CEM < MPC on every row. CEM is competent in
aggregate (the anticipated 2D competence gap did NOT materialize) but with per-seed variance
(one truth-CEM ≈ 0.97 outlier episode). Blind contact 0.05 uniform — nonzero, unlike the
cart's 0.00, and without positive play_cost.

### Mitigation 2D — partial collapse that decays with patch distance (2026-07-18)

`scripts/continuous_mitigation_patch2d.py` → `results/continuous_mitigation_patch2d.json`.
Fences are the 2D positions of refuted predictions (inside the unreachable patch);
segment-to-point crossing (leap-proof); the 1D path is preserved bitwise (tested
char-identical). The collapse is PARTIAL and DECAYS with patch distance.

| (k1,k2) | pc_blind | pc_mit | mean_viol | first_contact | c_mit |
|---|---:|---:|---:|---:|---:|
| (2,6) | 1.006 | 0.257 | 1.05 | 8.50 | 1.00 |
| (3,7) | 1.006 | 0.541 | 2.65 | 12.35 | 1.00 |
| (4,8) | 1.006 | 0.862 | 4.25 | 15.25 | 1.00 |

The 1D single-violation sufficiency becomes a boundary-mapping transient (the planner rounds
a fence disc and re-contacts the patch edge elsewhere, accreting fences along the arc); mean
violations grow 1.05 → 4.25 vs the 1D instruments' 1.0. At (4,8) it nearly defeats the
mitigation (pc_mit 0.862 vs pc_blind 1.006). Honest scope of a hard-boundary mitigation on a
curved 2D boundary, not a failure. The escape test asserts the measured mechanism
(pc_mit < 0.80·pc_blind, single-episode pessimistic bound).

## PAPER 2 — Third model family (Claude, agent-relayed): a symmetry prior and a phantom-mode artifact (2026-07-15)

**Protocol.** We ran paper 1's agent-relay protocol on the continuous synthesis
pipeline as a third cross-family spot-check (after GPT-5.x API and the Qwen HF
arm). `scripts/continuous_claude_step.py` emits the *verbatim* pipeline messages
(the same `build_synthesis_messages` init and the `refine_continuous` check
message, byte-for-byte with the API arms) and each message is relayed to a
**fresh, context-free Claude Sonnet instance** (agent scaffold over a
subscription transport — not an API). Everything else is the API pipeline: the
ε = 1e-9 pinned-integrator gate, the mode-blindness classification, and the MPC
play evaluation against the shared truth-planner baseline. Seeds
10000/20000/30000 per instrument (the same 1-absent/2-present split as the Qwen
spot-checks), plus one full-arm control per instrument. Source of truth:
`results/continuous_claude_relay.json` (8 cells); audit-trail message/reply
transcripts under `results/claude_relay_transcripts/`; protocol spec
`docs/superpowers/specs/2026-07-15-claude-relay-crossfamily-design.md`.

**Transport honesty notes.** (a) Agent scaffold + subscription transport, not an
API; the relayed messages are byte-identical to the pipeline's. (b) Wrapper
artifacts recorded: in the two multi-iteration cells a handful of refinement
replies prefixed a one-line explanation before the code block (two distinct
sentences, repeated across the oscillation) despite the output-only-code
instruction — the code block still parsed cleanly. No relay was refused this
time (the discrete probe saw two anti-injection refusals). (c) The refine loop
is **memoryless in the API arms too**: `refine_continuous`
(`src/cwm/continuous/contract.py`) sends a single user message per iteration
with no history, so the oscillation below is protocol behavior, not a relay
artifact.

| instrument | arm | seed | mode in sample | gate acc | passed | refine iters | mode-blindness | play_cost | outcome |
|---|---|---|---|---|---|---|---|---|---|
| cart | full | 10000 | — | 1.000 | ✓ | 0 | 0.0 | 0.0 | clean control (translation exact) |
| cart | incomplete | 10000 | no | 1.000 | ✓ | 0 | 1.0 | 0.999 | **mode-absent → blind & exploited** |
| cart | incomplete | 20000 | yes | 1.000 | ✓ | 1 | 0.0 | 0.0 | repaired exact one-sided rule (1 iter) |
| cart | incomplete | 30000 | yes | 1.000 | ✓ | 5 | 0.0 | 0.0 | repaired after period-2 oscillation (iter 5) |
| pendulum | full | 10000 | — | 1.000 | ✓ | 0 | 0.0 | 0.0 | clean control (translation exact) |
| pendulum | incomplete | 10000 | no | 1.000 | ✓ | 0 | 1.0 | 0.995 | **mode-absent → blind & exploited** |
| pendulum | incomplete | 20000 | yes | 1.000 | ✓ | 1 | 0.0 | 0.0 | **certified with PHANTOM symmetric stop θ = −1.4** |
| pendulum | incomplete | 30000 | yes | 0.9972 | ✗ | 5 | (n/a) | (n/a) | **stalled**, oscillating symmetric-stop ↔ no-stop |

**Findings.**

- *Controls (2/2 clean).* Both full arms translate the mode float-exactly: gate
  1.000, blindness 0.0, play_cost 0.0. The pinned-integrator premise holds for
  Claude too.
- *Identifiability is family-independent (2/2 mode-absent blind & exploited).*
  Both mode-absent seeds were certified fully blind (blindness 1.0) at gate
  1.000 and exploited at play (cart play_cost 0.999, pendulum 0.995, contact
  rate 1.0) — the (1−r)^N event fires regardless of family, exactly as
  Proposition 2 requires.
- *Repair mechanism: a symmetry prior.* Claude generalizes one-sided boundary
  evidence into a **symmetric** pair of boundaries. Cart seed 20000: repaired
  the exact one-sided `if x2 >= 8.0` rule in 1 iteration. Cart seed 30000:
  repaired at iteration 5 after a period-2 oscillation (symmetric ±8 walls →
  both removed → symmetric → removed → one-sided correct) — the sample reaches
  x < −8, so the gate refutes the phantom left wall and the loop eventually
  lands on the truth. This mechanism is neither GPT-5.x's (repairs every
  revealed mode exactly, 62/62 + 20/20) nor Qwen's (repairs none; superstitious
  local patches).
- *A fourth artifact class — certified with an invented, unfalsifiable mode.*
  Pendulum seed 20000 "repaired" in 1 iteration and passed the gate at 1.000,
  **but the certified code carries a phantom symmetric stop at θ = −1.4**
  (`if th2 < -th_max: th2 = -th_max; om2 = 0.0`) that this seed's rollouts never
  visit. Gate 1.000 (unfalsifiable on this sample), blindness probe 0.0 (it
  probes only the true +1.4 mode's region), play_cost 0.0. This is a genuinely
  new artifact class beyond correct / blind / superstitious-patch: a
  verified-and-exact-on-sample model that encodes a mode which does not exist.
- *Natural experiment.* The **same** symmetric artifact was **refuted** at
  pendulum seed 30000 (whose rollouts reach θ < −1.4, so the gate stalls it at
  0.9972 and it oscillates) and **certified** at pendulum seed 20000 (whose
  rollouts never go below −1.4). The only difference is sample coverage of the
  invented side. This is Proposition 2's prior caveat measured directly: on
  inputs the sample never covers, the artifact's content comes from the model's
  prior and the gate cannot police it.
- *Probe limitation (mirrors paper 1's artifact-level analysis).* The
  `mode_blindness` probe fires only in the true mode's region (by construction
  the probes must fire the mode in truth), so an invented mode *elsewhere* reads
  as blindness 0.0 and is invisible to the classification. Code inspection, not
  the probe, caught the phantom. Detecting invented modes needs code inspection
  or probes seeded outside the sampled region.
- *Scope.* n is small: 3 seeds + one control per instrument, one alternate
  family. Repair-from-data is model-dependent **in mechanism**, not merely in
  rate; identifiability (the mode-absent branch) is family-independent in all
  three families tested, as the proposition requires.

Papers updated: §7 (two-family → cross-family spot-checks: added the Claude
paragraph, the phantom-mode "fourth artifact class" paragraph, and the Claude
honesty notes; qualified the "never accepted a wrong mode-present artifact"
claim to "never wrong on a sample-covered transition"), §10 limitations
(three-family scope + the mode-blindness-probe limitation), the abstract, and
the intro/conclusion regularity statements — in both `docs/paper2/main.tex` and
`docs/paper2/preprint-draft.md`. Transcripts:
`results/claude_relay_transcripts/`.

## PAPER 2 — Second planner family (CEM): the other branch of the play-cost bound (2026-07-12)

Proposition 3 says exploitation is planner-dependent: a wrong model can change
behavior only when the planner queries the disagreement region. The paper's
random-shooting MPC includes constant-action candidates that reach the distant
phantom plateau in imagination, and is therefore lured into the omitted mode.
The second family tested here is cross-entropy-method planning (CEM): per-step
Gaussian action distributions, refined over 5 elite iterations with 64 samples,
elite fraction 0.125, horizon 40, and a fixed minimum standard deviation 0.05.
These hyperparameters are identical across both instruments and all knobs.

`scripts/continuous_cem.py` runs paired truth-CEM, blind-CEM, and random-policy
episodes (20 seeds/row), and measures a query-hit proxy for both planners: the
fraction of sampled imagined trajectories that cross the omitted boundary.
The MPC diagnostic uses its ordinary candidate generator; the CEM diagnostic
accumulates all 5×64 sampled trajectories at every replanning step. Full run:
11 rows, elapsed 1719.7 s; all values below are verbatim (rounded for display)
from `results/continuous_cem.json`.

| inst | knob | J_truth CEM | J_blind CEM | J_random | pc_blind CEM | blind contact | crossing CEM | crossing MPC |
|------|-----:|------------:|------------:|---------:|-------------:|--------------:|-------------:|-------------:|
| cart | 2.0 | 17.20 | 17.20 | 0.53 | 0.000 | 0.00 | 0.0010 | 0.3865 |
| cart | 4.0 | 17.20 | 17.20 | 0.53 | 0.000 | 0.00 | 0.0001 | 0.2453 |
| cart | 6.0 | 17.20 | 17.20 | 0.53 | 0.000 | 0.00 | 0.0000 | 0.1483 |
| cart | 8.0 | 17.20 | 17.20 | 0.53 | 0.000 | 0.00 | 0.0000 | 0.0773 |
| cart | 10.0 | 17.20 | 17.20 | 0.53 | 0.000 | 0.00 | 0.0000 | 0.0369 |
| pend | 0.8 | 16.46 | 16.31 | 0.06 | 0.009 | 0.70 | 0.1092 | 0.6392 |
| pend | 1.0 | 16.29 | 15.89 | 0.06 | 0.025 | 0.25 | 0.0703 | 0.5530 |
| pend | 1.2 | 15.51 | 15.68 | 0.06 | -0.011 | 0.00 | 0.0345 | 0.4672 |
| pend | 1.4 | 15.37 | 15.68 | 0.06 | -0.021 | 0.00 | 0.0162 | 0.3842 |
| pend | 1.6 | 15.36 | 15.68 | 0.06 | -0.021 | 0.00 | 0.0085 | 0.3039 |
| pend | 2.0 | 15.69 | 15.68 | 0.06 | 0.000 | 0.00 | 0.0029 | 0.2158 |

**Findings.** The normalized blind-model play cost is near zero on all 11
rows (range -0.0213 to 0.0248), rather than ≈0.94–1.03 as under MPC. On the
cart, truth and blind returns are identical on every row, contact is zero, and
CEM's imagined crossing fraction falls from 0.0010 to exactly 0 as the wall
recedes; MPC's comparable start-state diagnostic is 0.3865→0.0369. On the
pendulum, CEM crossing remains strictly below MPC at every stop (0.1092→0.0029
vs 0.6392→0.2158), and play cost remains near zero despite honest boundary
contacts at the two nearest stops: contact rate 0.70 at θ=0.8 and 0.25 at
θ=1.0, then zero for θ≥1.2. Contact alone is therefore not exploitation: CEM
can touch a nearby real boundary without being lured into the pinned,
below-random fixed point created by MPC's phantom-reaching search.

This is the measured other branch of Proposition 3. The certified-blind model
is a landmine whose consequence depends on the planner's query reach: MPC
detonates it; this CEM configuration largely does not. The result also turns
§2.3's calibration lesson into a planner-family result: a search distribution
that does not discover the phantom cannot optimize toward it. Two caveats are
load-bearing. First, CEM truth return on the pendulum varies with stop position
(15.36–16.46 versus MPC truth 20.08), consistent with local optima; the claim
is about blind-vs-truth geometry within CEM, not CEM optimality. Second,
limited reach is not knowledge or a safety mechanism: a planner that misses a
phantom distant reward can also miss a real one. No hyperparameter sweep or
per-knob tuning was performed.

## Budget-matched synthesized-CWM play cost, with CIs — codex #1 (2026-07-07/12)

Closes the central pre-submit gap: the synthesized play evidence (Panel B) was
range-only corroboration; it is now a budget-matched, CI'd replication of Panel A
run end-to-end through the actual synthesis pipeline.

**Setup.** `scripts/play_cost_synth_ci.py mini --seeds 20 --games 120 --sims 600`
(gate N=40), GPT-5.4-mini (Azure). Per seed, per arm ∈ {incomplete, complete}:
draw 40 gate trajectories on the TRUE game (army5x5a + material-at-cap; the sample
doubles as the gate, no resampling, as deployed), synthesize + refine to gate 1.0,
and if the gate passes play the synthesized CWM (MPC/MCTS) vs truth for 120 games
at 600 sims. Paired fair baseline (truth-vs-truth) on the same seeds. Logs
`wall_in_sample` (identifiability event: did the gate sample contain a
material-at-cap terminal?). Pooled Wilson per arm + seed-clustered paired-t
play_cost (fair − arm), seed as the unit. Crash-safe: per-seed checkpoint +
resume + API retry (the run spanned several days across machine-sleep cycles).

**Result** (`results/play_cost_synth_mini.json`, log `results/play_cost_synth_run.log`):

| arm | gate-passing | pooled winrate [Wilson 95%] | play_cost [seed-clustered 95%] |
|-----|-----|-----|-----|
| incomplete | 9/20 (n=1080) | 0.345 [0.317, 0.374] | **0.154** [0.135, 0.173] (excl. 0) |
| complete | 20/20 (n=2400) | 0.471 [0.451, 0.491] | 0.024 [0.000, 0.047] (excl. 0) |

The play_cost is seed-paired; its relevant baseline is the paired fair mean over
the 9 passing seeds (0.499), not the 20-seed global mean (0.495). Key structure —
**material-terminal absence is necessary (not sufficient) for gate-pass**: all 9
gate-passing incomplete seeds are material-terminal-absent; 0/10
material-terminal-present incomplete seeds reach gate 1.0 (they stall at
0.832–0.999, the material-region transitions being inexplicable to a program that
omits the rule). Of the 10 material-terminal-absent seeds, 9 pass and 1 (seed 11)
stalls at gate 0.808 — a *base-game* synthesis failure (LLM doesn't reproduce even
the rule-free base game), distinct from all three danger-law channels (which
concern the omitted rule). When the incomplete CWM does pass, it loses: per-seed
play_cost 0.11–0.19, all 9 positive. The complete-rules control is near parity (a
small residual deficit, 0.024, CI just excluding zero). This replicates Panel A's
finding in direction and mechanism, measured through synthesis; the magnitude is
*larger* (Panel B [0.135,0.173] disjoint from Panel A [0.065,0.117]), as expected
since the synthesized program can carry imperfections beyond the omitted rule — so
the end-to-end harm is at least as large as the rule's isolated cost.

**Paper.** Panel B (§3.3, Table tab:panelB) rewritten from "ranges only,
corroboration" to this CI'd result; abstract line updated from "the synthesized
runs corroborate the direction" to the end-to-end CI'd confirmation.

**Codex re-review (2026-07-13, resolved same day):** confirmed table matches JSON;
flagged and we fixed — magnitude overclaim ("reproduces"/"same effect" → larger,
disjoint CIs), the conditional baseline (0.499 not 0.495), "near parity" not
"parity" for the complete control, seed-11 mislabel (base-game synthesis failure,
NOT channel (c)), and "precisely the sampling-miss event" → necessary-not-sufficient.
Added arena denominators and the 5-iteration refinement cap. No new experiment
required; codex judged no blocking experiment outstanding.

## PAPER 2 — ε-sensitivity sweep: the tolerance axis is orthogonal to the mode hole (2026-07-09)

The gate's tolerance ε is a knob the deployer sets, and the paper's central
claim needs it shown to be a *pervasive-error* dial, not a *mode-detection*
dial: tightening ε cannot be used to catch the hard mode, and loosening it
cannot be used to widen the hole. New module `scripts/continuous_eps_sweep.py`
(read-only w.r.t. the environment/gate contract — `gate.py`, `envs.py`,
`continuous_axes.py` untouched) sweeps `ε ∈ {1e-9, 1e-6, 1e-4, 1e-3, 1e-2,
3e-2, 0.1, 0.3}` over ten arms on both instruments: cart mode arms (`wall@4
omitted`, `wall@8 omitted`), cart pervasive arms (`bias ×1.03`, `bias ×2.0`,
`bump amp0.5`, `bump amp1.0`), and pendulum mode/pervasive arms (`stop@1.0
omitted`, `stop@1.4 omitted`, `bias ×1.03`, `bias ×2.0`). For every
arm×ε cell, reveal-rarity is measured over 2000 rollouts; on the four mode
arms, pass@40 is additionally measured over 300 independent N=40 gates and
compared against the closed-form prediction `(1−r)^40`. Contract tested
bitwise/behaviorally in `tests/test_eps_sweep.py`. Full run: grid above,
rollouts=2000, n_gate=40, gates=300, elapsed=3835.1s. All numbers verbatim
from `results/continuous_eps_sweep.json`.

**Cart mode arms — rarity / (1−r)⁴⁰ / pass@40 across the ε grid.**

| arm | metric | 1e-9 | 1e-6 | 1e-4 | 1e-3 | 1e-2 | 3e-2 | 0.1 | 0.3 |
|-----|--------|-----:|-----:|-----:|-----:|-----:|-----:|----:|----:|
| wall@4 omitted | rarity | 0.1385 | 0.1385 | 0.1385 | 0.1385 | 0.1385 | 0.1385 | 0.1385 | 0.1355 |
| wall@4 omitted | (1−r)⁴⁰ | 0.0026 | 0.0026 | 0.0026 | 0.0026 | 0.0026 | 0.0026 | 0.0026 | 0.0030 |
| wall@4 omitted | pass@40 | 0.003 | 0.003 | 0.003 | 0.003 | 0.003 | 0.003 | 0.003 | 0.007 |
| wall@8 omitted | rarity | 0.0125 | 0.0125 | 0.0125 | 0.0125 | 0.0125 | 0.0125 | 0.0125 | 0.0125 |
| wall@8 omitted | (1−r)⁴⁰ | 0.6046 | 0.6046 | 0.6046 | 0.6046 | 0.6046 | 0.6046 | 0.6046 | 0.6046 |
| wall@8 omitted | pass@40 | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 | 0.667 |

**Pendulum mode arms — rarity / (1−r)⁴⁰ / pass@40 across the ε grid.**

| arm | metric | 1e-9 | 1e-6 | 1e-4 | 1e-3 | 1e-2 | 3e-2 | 0.1 | 0.3 |
|-----|--------|-----:|-----:|-----:|-----:|-----:|-----:|----:|----:|
| stop@1.0 omitted | rarity | 0.1410 | 0.1410 | 0.1410 | 0.1410 | 0.1410 | 0.1410 | 0.1400 | 0.1240 |
| stop@1.0 omitted | (1−r)⁴⁰ | 0.0023 | 0.0023 | 0.0023 | 0.0023 | 0.0023 | 0.0023 | 0.0024 | 0.0050 |
| stop@1.0 omitted | pass@40 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.003 | 0.003 |
| stop@1.4 omitted | rarity | 0.0175 | 0.0175 | 0.0175 | 0.0175 | 0.0175 | 0.0175 | 0.0170 | 0.0155 |
| stop@1.4 omitted | (1−r)⁴⁰ | 0.4935 | 0.4935 | 0.4935 | 0.4935 | 0.4935 | 0.4935 | 0.5037 | 0.5353 |
| stop@1.4 omitted | pass@40 | 0.473 | 0.473 | 0.473 | 0.473 | 0.473 | 0.473 | 0.477 | 0.497 |

**Cart pervasive arms — rarity across the ε grid.**

| arm | 1e-9 | 1e-6 | 1e-4 | 1e-3 | 1e-2 | 3e-2 | 0.1 | 0.3 |
|-----|-----:|-----:|-----:|-----:|-----:|-----:|----:|----:|
| bias ×1.03 | 1.0000 | 1.0000 | 1.0000 | 0.6200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bias ×2.0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.7455 | 0.0040 | 0.0040 |
| bump amp0.5 | 0.4595 | 0.3615 | 0.2805 | 0.2430 | 0.1875 | 0.1345 | 0.0010 | 0.0000 |
| bump amp1.0 | 0.4685 | 0.3700 | 0.2915 | 0.2545 | 0.2085 | 0.1670 | 0.0530 | 0.0000 |

**Pendulum pervasive arms — rarity across the ε grid.**

| arm | 1e-9 | 1e-6 | 1e-4 | 1e-3 | 1e-2 | 3e-2 | 0.1 | 0.3 |
|-----|-----:|-----:|-----:|-----:|-----:|-----:|----:|----:|
| bias ×1.03 | 1.0000 | 1.0000 | 1.0000 | 0.5755 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bias ×2.0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.7150 | 0.0045 | 0.0035 |

**Findings.** Mode-arm reveal-rarity is flat in ε, and the flatness is
*stronger* than the design expectation of "flat below the mode's error
scale": the cart mode arms are flat through ε=0.1 on both `wall@4` and
`wall@8`, and `wall@8` is flat through the **entire grid**, ε=0.3 included
(rarity 0.0125 identical at all eight points, so pass@40 is 0.667
everywhere). The only tail movement is a slight *dip* at the top of the
grid — never a widening: `wall@4` rarity drops 0.1385→0.1355 at ε=0.3 (pass
ticks 0.003→0.007, still tiny); the pendulum's mode arms dip a little
earlier and a little further, consistent with the design doc's prediction
that low-speed contacts (error ≈ |v₂|) can fall under a loose ε — `stop@1.0`
0.1410→0.1400 (ε=0.1)→0.1240 (ε=0.3), pass 0.000→0.003→0.003; `stop@1.4`
0.0175→0.0170 (ε=0.1)→0.0155 (ε=0.3), pass 0.473→0.477→0.497. In every case
the movement is a *decrease* in rarity at *higher* ε, i.e. the widened gate
is, if anything, marginally *more* forgiving of the already-caught mode —
never less. Below ε=1e-2 the flatness is exact (bit-identical rarity across
1e-9…1e-2 on all four mode arms): the blind model is bit-exact off-mode, so
a reveal is a mode contact, independent of ε below the mode's own error
scale.

The pervasive (bias) arms switch, sharply, at their own error scale, on
**both** instruments. ×1.03 (a 3% pervasive drag error) is fully policed
(rarity 1.0000) through ε=1e-4, has a measured partial value at the
crossing (cart 0.6200, pendulum 0.5755 at ε=1e-3), and is fully invisible
(rarity 0.0000) by ε=1e-2 — a ×1.03 switch across roughly one order of
magnitude in ε. ×2.0 (a 2x pervasive drag error) switches an order of
magnitude higher: rarity 1.0000 through ε=1e-2, a partial value at the
crossing (cart 0.7455, pendulum 0.7150 at ε=3e-2), and near-zero (0.0040
cart, 0.0045/0.0035 pendulum) by ε=0.1–0.3. The bump arms (cart-only, C∞
localized perturbation, not a hard mode) decay smoothly with ε as expected,
and the decay is ordered by amplitude at every grid point: the stronger bump
(amp1.0) is consistently more detectable than the milder one (amp0.5) —
0.4685 vs 0.4595 at ε=1e-9, and still 0.0530 vs 0.0010 at ε=0.1 (53×) —
before both are driven to 0.0000 at ε=0.3.

**Exactness check.** pass@40 ≈ (1−r)^40 holds at every ε for both mode arms
on both instruments — this is the same gate-exactness proposition from the
axis-separation table, now shown to be ε-invariant, not a coincidence of one
setting. Honesty note: at `wall@8`, the closed-form prediction 0.6046 sits
marginally *below* the empirical pass-rate 300-gate Wilson 95% CI lower
bound (0.6115); with only 300 independent gates this is sampling noise, not
disagreement, but the two numbers are quoted plainly here rather than as
"exact" agreement.

**Conclusion.** The design doc's ε-confound risk — that the deployment-
realistic loose-ε arm needed a documented sensitivity sweep before the axis-
separation claim could be trusted at ε values other than the one tested —
is resolved. Tightening ε cannot catch the mode (rarity is flat, in the
strongest cases through the whole grid); loosening ε does not widen the hole
(the only tail movement observed is a slight narrowing, never a widening).
The tolerance axis is orthogonal to the mode hole across the entire
deployment-realistic range; ε moves the boundary of the pervasive-error
axis and nothing else.

## PAPER 2 — Mitigation: distrust-region replanning collapses the exploitation (2026-07-09)

The exploitation measured throughout this paper is planner-mediated, not
model-mediated, and a planner-side fix collapses it without touching the
model or the gate. New module `src/cwm/continuous/mitigation.py`
(`run_mitigated_episode`, `plan_mitigated`), strictly additive — `mpc.py`,
`harness.py`, `envs.py` untouched. Mechanism: after each real step from state
`s` with action `a`, compare the model's prediction `ŝ = model.step(s, a)`
against the observed `s'`; if `max(|ŝ₀−s'₀|, |ŝ₁−s'₁|) > tol` with
`tol = 1e-6`, record the **position of the model's refuted prediction**
`ŝ[0]` (not the pre-state) as a one-sided distrust fence — false predictions
always lie on/beyond the mode boundary, so the fence is one-sided by
construction. While scoring a candidate rollout, the first imagined step
whose position interval `[min(x_prev, x_next), max(x_prev, x_next)]`
overlaps a fence's ε-band (ε = 0.25 cart, ε = 0.1 pendulum, fixed per
instrument, not tuned per knob) truncates the rollout — reward so far kept,
everything downstream dropped — so the fence cannot be leapt at any imagined
speed (segment-crossing truncation, not point distance). Candidates are then
ranked by `(truncated_total, |x_final − nearest fence|)`; because fences are
one-sided, the tie-break structurally prefers the real side over the
phantom side. With zero violations the second term is a constant 0.0 and the
ranking is bit-identical to `mpc.plan` — the zero-cost control is exact by
construction and tested bitwise (`tests/test_mitigation.py`,
`test_plan_reduces_to_mpc_without_violations`,
`test_bit_identical_episode_on_truth_model`).

**Design iterations (recorded because they are themselves a finding — the
argmax planner is an adversary against any incomplete fence).** v1, first-step
flee over pre-state balls, got trapped at the local distance-maximum between
overlapping balls. v2, final-state flee over pre-state balls, was biased
*toward* the phantom, because violations can only be recorded on the truth
side of the boundary, so the far side always looks "far from where the model
lied." v3, full-state point fences at the false predictions, was dodged by
the planner probing crossing *velocities* — measured: 5 fences at
v ∈ {0.3, 1.46, 1.73, 2.25, 5.47}, episode ends before the fence wall closes.
v4 (position-band + segment crossing + one-sided fences, shipped) is
undodgeable: one violation suffices on every knob of both instruments. See
`docs/superpowers/specs/2026-07-08-mitigation-experiment-design.md` for the
full design record.

**Measurement** (`scripts/continuous_mitigation.py`; three arms — truth-MPC,
blind-MPC, blind-MPC+mitigation — on paired seeds, 20 episodes/knob;
episodes=20, cart eps=0.25, pend eps=0.1, elapsed=1770.3s):

| inst | knob | J_truth | J_blind | J_mit | J_rand | pc_blind | pc_mit | c_blind | c_mit | viol | first_contact |
|------|-----:|--------:|--------:|------:|-------:|---------:|-------:|--------:|------:|-----:|--------------:|
| cart | 2 | 17.77 | 0.00 | 12.77 | 0.53 | 1.031 | 0.290 | 1.00 | 1.00 | 1.0 | 11.6 |
| cart | 4 | 17.77 | 0.00 | 10.09 | 0.53 | 1.031 | 0.446 | 1.00 | 1.00 | 1.0 | 16.9 |
| cart | 6 | 17.77 | 0.00 | 7.80 | 0.53 | 1.031 | 0.578 | 1.00 | 1.00 | 1.0 | 21.3 |
| cart | 8 | 17.77 | 0.02 | 5.72 | 0.53 | 1.030 | 0.699 | 1.00 | 1.00 | 1.0 | 25.1 |
| cart | 10 | 17.77 | 0.94 | 3.88 | 0.53 | 0.977 | 0.806 | 1.00 | 1.00 | 1.0 | 28.7 |
| pend | 0.8 | 20.08 | 0.01 | 17.82 | 0.06 | 1.002 | 0.113 | 1.00 | 1.00 | 1.0 | 7.0 |
| pend | 1 | 20.08 | 0.03 | 17.49 | 0.06 | 1.002 | 0.129 | 1.00 | 1.00 | 1.0 | 8.1 |
| pend | 1.2 | 20.08 | 0.05 | 17.21 | 0.06 | 1.000 | 0.143 | 1.00 | 1.00 | 1.0 | 9.0 |
| pend | 1.4 | 20.08 | 0.12 | 16.88 | 0.06 | 0.997 | 0.160 | 1.00 | 1.00 | 1.0 | 10.0 |
| pend | 1.6 | 20.08 | 0.26 | 16.54 | 0.06 | 0.990 | 0.177 | 1.00 | 1.00 | 1.0 | 11.0 |
| pend | 2 | 20.08 | 1.23 | 15.84 | 0.06 | 0.942 | 0.212 | 1.00 | 1.00 | 1.0 | 13.0 |

All numbers verbatim from `results/continuous_mitigation.json`.

**Findings.** The exploitation collapses everywhere: `pc_blind` sits pinned
at ≈0.94–1.03 on all 11 rows (below random, the existing fact) while
`pc_mit` never rises above 0.81. Exactly one violation suffices to fence the
mode on *every* row (`viol` = 1.0, all 11 knobs, both instruments) — the
one-sided fence at the refuted prediction, truncated by segment crossing, is
leap-proof, so a single contact is both necessary and sufficient. The
residual `pc_mit` is not noise; it is the honest cost of the unavoidable
first contact, and it scales monotonically with the lure distance (read off
`first_contact`): cart 0.290 → 0.806 as first contact goes 11.6 → 28.7 of the
80-step horizon (knob 2 → 10); pendulum 0.113 → 0.212 as first contact goes
7.0 → 13.0 (knob 0.8 → 2.0). You cannot avoid what you have never seen —
identifiability operationalized at the planner level. The cart knob=10 row is
the least favorable in the sweep (`pc_mit` 0.806 vs. blind 0.977) because the
transient consumes most of the horizon there, but the comparison that matters
is the return, not the normalized cost: the blind planner stays pinned
*forever* at that knob (J_blind 0.94 of J_truth 17.77) while the mitigated
planner escapes and recovers most of the horizon (J_mit 3.88). Zero-cost
control on a correct model is exact, not approximate: `run_mitigated_episode`
is bit-identical to `harness.run_episode(..., "mpc", ...)` on truth/truth,
tested bitwise in `tests/test_mitigation.py`. Framing: this does **not**
contradict the danger law — the gate still certified a wrong model, and
Proposition 2's identifiability argument is untouched. What collapses is the
*planner-mediated exploitation* of that wrong model: the planner's own
prediction-vs-observation signal, free at deployment (no extra sampling, no
model change), turns a knob-invariant, below-random pin into a bounded
first-contact transient.

## PAPER 2 — Pendulum synthesis arm: repair-from-data on a nonlinear plant (2026-07-08)

Closes the gap the 2026-07-07 pendulum-mechanism section left open ("the
synthesis arms on the pendulum remain optional future work"). Same script and
contract as the cart (`scripts/continuous_danger_synthesis.py --instrument
pendulum --th-stop ...`; Azure GPT-5.x mini/large; ε=1e-9 pinned-integrator
gate; N=40 training rollouts; 6 MPC play episodes/seed; max 5 refine iters),
20 seeds/cell. Two knobs: **headline** θ_stop=1.4 (rarity 0.019 per the
2026-07-07 pendulum-mechanism table below — mode usually but not always missed
at N=40) and **caught** θ_stop=1.0 (rarity 0.128 — mode in nearly every
sample). Baselines identical across all pendulum
cells: J_truth=20.08, J_random=0.02. Per-seed JSON:
`results/continuous_synthesis_pendulum_{mini,large}_thstop{1.4,1}.json` and
`results/continuous_synthesis_pendulum_compat-qwen3-coder-30b-a3b-instruct_thstop1.4.json`.

**(1) Headline cell (θ_stop=1.4), both sizes.**

| arm | mini (gpt-5.4-mini) | large (gpt-5.4) |
|-----|---------------------|-----------------|
| full | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 |
| incomplete — mode ABSENT | 9/20 seeds; **9/9 blind & exploited**, play_cost 0.995 | 9/20 seeds; **9/9 blind & exploited**, play_cost 0.995 |
| incomplete — mode PRESENT | 11/20 seeds; **11/11 repaired**, iters {0,1,1,1,1,1,1,1,1,3,5}, **0 stalled** | 11/20 seeds; **11/11 repaired**, iters {0,1,1,1,1,1,1,1,1,1,1}, **0 stalled** |

**(2) Caught cell (θ_stop=1.0), both sizes.**

| arm | mini (gpt-5.4-mini) | large (gpt-5.4) |
|-----|---------------------|-----------------|
| full | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 |
| incomplete — mode ABSENT | 0/20 seeds (rarity 0.128 ⇒ (1−r)^40≈0.004 — essentially never missed) | 0/20 seeds |
| incomplete — mode PRESENT | 20/20 seeds; **20/20 repaired**, iters {0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, **0 stalled** | 20/20 seeds; **20/20 repaired**, iters {0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}, **0 stalled** |

**GPT-5.x combined (4 Azure cells, both sizes, both knobs, n=80 seeds):**
full 80/80 clean; mode-ABSENT 18/18 blind & exploited (Wilson 95% lower bound
0.824; per-size headline-cell 9/9, lower bound 0.701); mode-PRESENT 62/62
**repaired**, 0 stalled (Wilson 95% lower bound 0.942).

**(3) Cross-family spot-check (HF router,
`Qwen/Qwen3-Coder-30B-A3B-Instruct`, 3 seeds, θ_stop=1.4).**

- full: 3/3 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 — the pinned-integrator
  premise holds cross-family on the pendulum too.
- incomplete: 1/3 mode-ABSENT → blind & exploited, play_cost 0.995 (headline
  identifiability event reproduced in a second model family); 2/3
  mode-PRESENT → **both stalled, 0 repaired** (gate 0.9997 and 0.9997 — a
  hair below the eps=1e-9 float-exact bar, the same superstitious-patch
  signature as the cart's Qwen stalls).

### Findings

**Repair-from-data generalizes to a nonlinear plant.** Every qualitative
result from the cart's synthesis section reproduces on the pendulum's
gravity-driven (sin θ) dynamics with an angular clamp instead of a linear
positional wall: the full arm is clean at every cell (80/80 GPT-5.x, 3/3
Qwen); the mode-ABSENT identifiability event is knob- and size-invariant
(blind & exploited whenever it fires, 18/18 GPT-5.x + 1/1 Qwen, play_cost
pinned at 0.995 in every occurrence, matching the cart's fixed-point
exploitation signature); and when the mode IS in the sample, GPT-5.x repairs
it to the exact angular clamp every single time (62/62, 0 stalls) across both
knobs and both sizes — including the θ_stop=1.0 "caught" cell where the mode
is in essentially every sample (40/40 repaired there alone). The synthesis
result is therefore not a cart artifact: a nonlinear plant plus an angular
(not positional) hard stop behaves identically under the same harness.

**Cross-family: identifiability reproduces, repair does not.** As on the
cart, Qwen reproduces the mode-absent blind-and-exploited event (1/1 here)
but fails to repair either of its mode-present seeds (0/2, stalled at gate
0.9997) — consistent with the cart's cross-family finding that
**identifiability is model-independent, repair is model-dependent**. The
stalled gate values (0.9997) are closer to passing than the cart's Qwen
stalls (0.491–0.999) but still short of the eps=1e-9 bar, and the gate
correctly refuses both.

**Notes.** n_seeds=20/cell for GPT-5.x (paper-1 standard), 3 seeds for the
Qwen spot-check, matching the cart's design. Elapsed: mini θ=1.4 1081.2s,
large θ=1.4 916.3s, mini θ=1.0 1903.7s, large θ=1.0 1990.6s, Qwen 165.1s.
Reproducibility: seeds fix trajectory sampling and play; LLM synthesis is
stochastic across calls, so exact per-seed iteration counts differ run-to-run
while the three-way structure and identifiability conditional are stable.

## PAPER 2 — Second instrument (pendulum-with-stop): the law on a nonlinear plant (2026-07-07)

The design doc's last step-5 item (`scripts/continuous_pendulum.py`, 121 s
CPU; `results/continuous_pendulum.json`; env `PendulumStop` in
`cwm.continuous.envs`, same interface, blind_of removes the stop). The base
plant is NONLINEAR (gravity term sin θ, θ=0 hanging down), so this checks the
mechanism is not an artifact of the cart's linear off-mode dynamics. Rarity
is natural here — gravity confines the random walk near the bottom; no lure
engineering was needed beyond reusing the two-plateau reward on θ. First
calibration worked unchanged (same MPC, same harness).

| θ_stop | rarity [Wilson 95%] | J_truth | J_blind | J_rand | play_cost | blind hit | d@N=40 |
|-------:|---------------------|--------:|--------:|-------:|----------:|----------:|-------:|
| 0.8 | 0.297 [0.281, 0.314] | 20.08 | 0.01 | 0.06 | 1.002 | 1.00 | 0.000 |
| 1.0 | 0.128 [0.116, 0.140] | 20.08 | 0.03 | 0.06 | 1.002 | 1.00 | 0.004 |
| 1.2 | 0.053 [0.045, 0.061] | 20.08 | 0.05 | 0.06 | 1.000 | 1.00 | 0.115 |
| 1.4 | 0.019 [0.015, 0.025] | 20.08 | 0.12 | 0.06 | 0.997 | 1.00 | 0.457 |
| 1.6 | 0.007 [0.005, 0.011] | 20.08 | 0.26 | 0.06 | 0.990 | 1.00 | 0.737 |
| 2.0 | 0.000 [0.000, 0.001] | 20.08 | 1.23 | 0.06 | 0.942 | 1.00 | 0.942 |

Identical phenomenology to the cart: threshold law with the elbow inside the
sweep, play_cost ≈ 1 knob-invariant, blind planner pinned at the stop in
every episode at every knob (final θ = θ_stop exactly), truth planner never
touches it. Two-instrument robustness established CPU-only; the synthesis
arms on the pendulum remain optional future work (the contract machinery is
env-generic except for the rules text).

Also this date: paper-2 figures generated from the versioned results JSONs
(`scripts/make_paper2_figures.py` → `docs/paper2/figures/`: danger_threshold,
reach_mechanism, axis_separation, smooth_localization; Wong CVD-safe palette,
same conventions as paper 1's figures).

## PAPER 2 — Smooth-learner probe: the mode cannot be localized by a smooth hypothesis (2026-07-07)

Design-doc step-5 probe (`scripts/continuous_smooth_probe.py`, 11 s CPU;
`results/continuous_smooth_probe.json`). Trains the two most favorable smooth
learners on the SAME N=40 samples the synthesis arms used (x_wall=8; seed
10000 = wall-free, seed 20000 = wall-containing with 4/3200 contact rows):
closed-form linear least squares (off the wall the dynamics are EXACTLY
linear, so this is the smooth-learner best case) and a small tanh MLP (h=8).

| model | trained on | off-mode err (mean / max) | wall probe err | gate 1e-9 | gate 1e-2 |
|-------|-----------|---------------------------|---------------:|:---:|:---:|
| linear-LSQ | wall-free | 3.6e-15 / 1.7e-14 | 4.18 | PASS | PASS |
| linear-LSQ | wall-data | 1.9e-03 / 1.2e-02 | 4.17 | fail | fail |
| MLP h=8 | wall-free | 3.5e-03 / 5.0e-02 | 4.20 | fail | fail |
| MLP h=8 | wall-data | 6.0e-03 / 4.9e-02 | 4.19 | fail | fail |

Readings (the two halves of thesis point 3, both measured):
- **Identifiability is learner-independent, live.** The linear model trained
  on the wall-free sample recovers the off-mode dynamics to 1e-15, PASSES
  both gates (including eps=1e-9), and is exactly as wall-blind as the
  synthesized blind code (probe err 4.18 — it predicts straight through the
  wall). The (1−r)^N unsoundness is not an LLM property; ANY gate-passing
  learner in the gate-miss event is blind (paper 1's Proposition, instantiated
  on a second learner class).
- **With the mode IN the data, smooth and code part ways.** 4 contact rows
  out of 3200 tilt the linear fit by TWELVE orders of magnitude off-mode
  (1.7e-14 → 1.2e-02 max) and it fails both gates while still getting the
  mode wrong (probe 4.17): the smooth hypothesis cannot put the error ON the
  mode — it leaks everywhere. The synthesized code on the same sample wrote
  `if x2 >= 8.0: return [8.0, 0.0]` and passed at float precision. Repair is
  a *representational* capability of code, not just a data question.
- The MLP never gets its pervasive floor (~5e-3) under any gate and never
  learns the mode (probe 4.2) — the generic smooth learner combines both
  failure axes. Scope: probe, not a tuned baseline (as per the design doc).

## PAPER 2 — LLM synthesis arms executed (credentialed run per the design-doc runbook) (2026-07-07)

> **Superseded/tightened by the 20-seed + cross-family run below (2026-07-07,
> later).** This section documents the first 5-seed spot-check; the headline
> cell (x_wall=8) was subsequently run at 20 seeds/cell (paper-1 standard) on
> both sizes and a Qwen cross-family spot-check was added — see "20-seed
> tightening + Qwen cross-family". The three-way structure is unchanged; the
> tightened run sharpens the identifiability conditional and removes the
> mini stalls on the headline cell.

Ran `scripts/continuous_danger_synthesis.py` as documented in the design doc's
"Runbook — LLM arms" (Azure GPT-5.x, eps=1e-9 pinned-integrator gate, N=40
rollouts, 6 MPC play-episodes/seed, max 5 refine iters), 5 seeds/cell. Baselines
J_truth=17.76, J_random=0.00 (play_cost normalized: 1.0 = performs like random,
i.e. pinned at the wall). Per-seed JSON (one file per cell — the filename now
carries x_wall, fixed this run so cells no longer overwrite each other):
`results/continuous_synthesis_{mini_xwall8,mini_xwall4,large_xwall8}.json`;
combined stdout in `results/continuous_synthesis_llm.log`.

**Cell 1 — mini, x_wall=8 (headline; gate misses the wall ~60% at N=40).**
full: 5/5 gate 1.000 / 0 iters / blind 0.0 / play_cost 0.0. incomplete:

| seed | wall_in_sample | gate | iters | blind | play_cost |
|-----:|:--------------:|-----:|------:|------:|----------:|
| 0 | **False** | 1.000 | 0 | **1.0** | **0.999** |
| 1 | True  | 0.995 | 5 | (gate not passed) | n/a |
| 2 | True  | 1.000 | 3 | 0.0 | 0.0 |
| 3 | **False** | 1.000 | 0 | **1.0** | **0.999** |
| 4 | True  | 1.000 | 3 | 0.0 | 0.0 |

**Cell 2 — mini, x_wall=4 (caught; wall in every sample).** full 5/5 clean.
incomplete: seeds 2,3,4 repaired to gate 1.000 (blind 0.0, play_cost 0.0) in
5/2/0 iters; seeds 0,1 stalled just below within the 5-iter budget (gate 0.998,
0.974) and were left unclassified (gate not passed -> no play).

**Cell 3 — large, x_wall=8 (headline).** full 5/5 clean. incomplete: seeds 0,3
wall-absent -> gate 1.000 + blind 1.0 + play_cost 0.999 + contact 1.0; seeds
1,2,4 wall-present -> gate 1.000 + blind 0.0 + play_cost 0.0, repaired in **1
iter each** (large repairs faster and more reliably than mini).

### Findings

**1. Full arm confirms the pinned-integrator premise live.** Both sizes
synthesize correct `step`/`reward` and pass the eps=1e-9 gate to float precision
in 0 iters, blind 0.0, play at truth parity — the offline (FakeProvider)
prediction holds with a real LLM.

**2. Paper-1 headline reproduces in continuous space when the wall is absent
from the sample.** The identifiability event `wall_in_sample=False` occurred in
2/5 seeds for both mini and large (consistent with r≈0.0125 at x_wall=8,
(1−r)^40≈0.60); in EVERY such seed (4/4 across sizes) the synthesized model
passed the gate fully wall-blind (1.0) and was exploited at play — pinned at the
wall, contact 1.0, play_cost 0.999. A verified-but-wrong continuous CWM that
loses, synthesized end-to-end. This cell is rock-solid across both this run and
the 2026-07-07 first run.

**3. The DIVERGENCE from paper 1 (design doc anticipated it).** When the wall
WAS present in the sampled transitions, the model did **not** stay blind: it
inferred the discontinuity from the failing transitions and encoded the clamp.
Large repaired every wall-present seed to gate 1.000 (blind 0.0, play_cost 0.0)
in 1 iter; mini repaired most (gate 1.000, blind 0.0) in 0–3 iters but on some
seeds stalled just below 1.0 within the 5-iter budget (0.974–0.998 — most of the
clamp encoded, not nailed to eps=1e-9 float precision in time). Either way this
is the opposite of paper 1's symbolic setting, where a rule present in the
sample sat at low gate accuracy and was never learned (the (b) residual). A
**numerically-manifested** discontinuity is learnable-from-data in a way a
**symbolic** game rule was not, so in the continuous setting the gap collapses
toward a **pure identifiability/coverage (channel-(a)) phenomenon**: danger
lives in the (1−r)^N event that the sample misses the discontinuity (there it is
total, play_cost≈1), while the paper-1 (b) "translation-not-inference" residual
largely vanishes. Per the runbook this "becomes its own section" for paper 2's
write-up (not yet drafted).

**3b. Artifact-level analysis of the repairs (code inspection, 2026-07-07).**
Reading the synthesized `step()` of every wall-present incomplete seed
(`results/continuous_synthesis_*_xwall*.json`, `code` field) sharpens finding 3
into a soundness statement:
- Every *repaired* seed wrote the TRUE global rule — `if x2 >= 8.0: return
  [8.0, 0.0]` (modulo formatting; large 3/3, mini 5/8) — not a curve fit. One
  mini seed (x_wall=4, seed 50000) wrote it in **0 iterations**, i.e. inferred
  the clamp from the synthesis examples alone, before any refinement feedback.
- Every *stalled* seed is a **superstitious local patch**, not a near-miss of
  the rule: `if abs(x2 - 8.0) <= 0.15 and abs(v2) <= 1.1: x2 = 8.0` (mini@8
  seed 20000) and `if x < 4.0 and x2 >= 4.0: x2 = 4.0` (mini@4 seed 10000) —
  clamps fitted to the *observed manifestation* of the mode (low-speed,
  near-wall contact transitions), which mispredict other approaches to the
  wall. **The gate correctly rejects all of them** (0.974–0.998, never 1.000).
- Net: with the mode present in the data, the synthesize+refine+gate loop is
  *sound* — it either recovers the exact mode or refuses the artifact. The
  ONLY unsoundness anywhere in the continuous pipeline is the (1−r)^N
  identifiability event, where the wrong artifact is accepted at gate 1.000
  and exploited at play. The danger law here is not just exact; it is
  *exhaustive*.

**Notes.** n_seeds=5/cell as documented — a spot-check, not a sweep; robust on
the wall-absent cell (4/4), suggestive-with-variance on the repair rate.
Reproducibility: seeds fix the trajectory sampling and play; LLM synthesis is
stochastic across calls, so exact per-seed iters/gate differ run-to-run while
the three-way structure (full-clean / absent-blind-exploited / present-repairs)
is stable. Cost: <$1 Azure, ~9 min wall-clock (3 cells).

## PAPER 2 — 20-seed tightening + Qwen cross-family (runbook remaining runs) (2026-07-07, later)

The two "Remaining credentialed runs for the paper" from the design-doc
runbook. Same script/params as above (eps=1e-9 pinned-integrator gate, N=40
rollouts, 6 MPC play-episodes/seed, max 5 refine iters). Baselines identical
(J_truth=17.76, J_random=0.00). Per-seed JSON with the synthesized `code`
versioned: `results/continuous_synthesis_{mini,large}_xwall8.json` (now 20
seeds, overwriting the 5-seed versions) and
`results/continuous_synthesis_compat-qwen3-coder-30b-a3b-instruct_xwall8.json`.

**(1) Headline cell (x_wall=8) tightened to 20 seeds/cell, both sizes (Azure
GPT-5.x).**

| arm | mini (gpt-5.4-mini) | large (gpt-5.4) |
|-----|---------------------|-----------------|
| full | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 | 20/20 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 |
| incomplete — wall ABSENT | 10/20 seeds; **10/10 gate 1.000 + blind 1.0 + play_cost 0.999 + contact 1.0** | 10/20 seeds; **10/10 gate 1.000 + blind 1.0 + play_cost 0.999 + contact 1.0** |
| incomplete — wall PRESENT | 10/20 seeds; **10/10 repaired** (gate 1.000, blind 0.0, play_cost 0.0), iters {0,1,1,1,1,3,3,3,4,5}, **0 stalled** | 10/20 seeds; **10/10 repaired** (gate 1.000, blind 0.0, play_cost 0.0), iters {0,0,1,1,1,1,1,1,1,1}, **0 stalled** |

- **Identifiability conditional, sharpened.** At 20 seeds the wall-absent event
  fired in exactly 10/20 seeds per size (r≈0.0125 at x_wall=8 gives
  (1−r)^40≈0.60; 10/20 is within the sampling band). In EVERY wall-absent seed
  — **20/20 across sizes** — the synthesized model passed the gate fully
  wall-blind (1.0) and was exploited at play (pinned at the wall, contact 1.0,
  play_cost 0.999). Wilson 95% on P(blind | wall missed): **10/10 → lo 0.72**
  per size, **20/20 → lo 0.84** combined.
- **Repair is now clean on the headline cell (0 stalls).** Every wall-present
  seed repaired to the TRUE global clamp (`if x2 >= 8.0: return [8.0, 0.0]`, or
  the equivalent `if x2 > 8.0: x2 = 8.0` — large seeds 70000/120000/150000),
  not a curve fit. Large repaired in 0–1 iters (2 seeds in 0 iters, i.e. from
  the synthesis examples alone); mini in 0–5 iters (1 seed in 0). The 5-seed
  run's mini stalls do not recur here — with more seeds and only the x_wall=8
  cell, GPT-5.x mini nailed all 10. (The superstitious-local-patch stalls of
  the 5-seed run were on x_wall=4 and one x_wall=8 seed; the gate rejected all.)

**(2) Cross-family spot-check (HF Inference Providers router,
`Qwen/Qwen3-Coder-30B-A3B-Instruct`, 3 seeds, x_wall=8).**

- full: 3/3 gate 1.000, 0 iters, blind 0.0, play_cost 0.0 — the pinned-integrator
  premise holds cross-family too.
- incomplete: 1/3 wall-absent → gate 1.000 + blind 1.0 + play_cost 0.999
  (headline reproduced in a second model family); 2/3 wall-present → **both
  stalled, 0 repaired** (gate 0.999 and 0.491). The gate-0.999 seed is a
  superstitious partial patch (`if x2 >= 8.0 and v2 <= 0.0: ...` — clamps only
  on the observed low-speed approach, mispredicts others); the gate correctly
  rejected both.

**Finding: repair-from-data is model-dependent; identifiability is not.** The
wall-absent blind-and-exploited event reproduces in every model tried (GPT-5.x
20/20, Qwen 1/1) — it is a property of the sample, not the synthesizer. But the
wall-present *repair* is not uniform: GPT-5.x (both sizes) recovers the exact
mode reliably (20/20 here), whereas Qwen stalls on both wall-present seeds
(0/2), producing superstitious patches the gate refuses. So the continuous
danger law's structure (soundness except on the (1−r)^N event) holds
cross-family, but the *rate* at which the loop repairs a revealed mode — and
hence how much of the (b)-residual it eliminates — depends on the model.
Either outcome is a finding, as the runbook anticipated. Cost: <$1 Azure + HF
credits; ~46 min mini + ~47 min large + ~6 min Qwen wall-clock.

**Notes.** Reproducibility: seeds fix trajectory sampling and play; LLM
synthesis is stochastic across calls, so exact per-seed iters differ run-to-run
while the three-way structure and the identifiability conditional are stable.
The large cell was run in a git worktree of this branch (a parallel session
held the main checkout on `main`); results are byte-identical to a main-checkout
run modulo LLM stochasticity.

## PAPER 2 — Axis separation: localized mode vs pervasive error vs smooth bump (2026-07-06)

The design doc's step-4 controls, all CPU (`scripts/continuous_axes.py`,
eps=0.01 deployment-realistic tolerance gate, 2000 reveal-rarity rollouts,
300 independent N=40 gates, 20 MPC episodes/arm; 169 s;
`results/continuous_axes.json`). Reveal-rarity is the measure-theoretic
rarity: P(a random rollout contains a transition where truth and model
differ > eps).

| arm | rarity | (1−r)^40 | pass@40 (empirical) | play_cost | danger@40 |
|-----|-------:|---------:|--------------------:|----------:|----------:|
| wall@4 omitted | 0.1385 | 0.0026 | 0.003 | 1.031 | 0.0027 |
| wall@8 omitted | 0.0125 | 0.6046 | 0.667 | 1.030 | 0.6227 |
| drag bias ×1.03 (sub-eps) | 0.0000 | 1.0000 | 0.997 | 0.000 | 0.0000 |
| drag bias ×2.0 (supra-eps) | 1.0000 | 0.0000 | 0.000 | 0.000 | 0.0000 |
| bump@4 amp0.5 (smooth) | 0.1875 | 0.0002 | 0.000 | 0.000 | 0.0000 |
| bump@4 amp1.0 (smooth) | 0.2085 | 0.0001 | 0.000 | −0.745 | −0.0001 |

Readings:
- **Gate exactness confirmed empirically**: pass@40 matches (1−r)^40 in both
  wall rows (0.003 vs 0.0026; 0.667 vs 0.605 — correction 2026-07-10: the
  prediction is marginally BELOW the 300-gate Wilson lower bound 0.612, not
  inside the CI; sampling noise at that gate count, see the ε-sweep entry).
- **The four-quadrant separation the paper needs**: the tolerance gate
  *polices pervasive error* (supra-eps bias rejected on every rollout) and
  *tolerates harmless* sub-eps bias (pass 0.997, play_cost 0.000) — yet is
  **blind exactly (1−r)^N of the time to the localized hard mode, whose
  play_cost is ~1**. Danger lives only in the rare∧hard-mode cell.
- **Smoothness kills consequence, not detectability**: the C∞ drag bump at
  the same location has *comparable rarity* to the wall (0.19 vs 0.14) but
  play_cost exactly 0.000 at amp 0.5 — rarity without consequence (the
  Connect-Four analogue). At amp 1.0 play_cost goes *negative* (−0.745): the
  truth planner is over-pessimistic about the slowdown near its horizon edge
  and often settles for the small left plateau, while the bump-blind planner
  pushes through and wins — a smooth localized omission can even *help*.
  Smooth perturbations produce planner-side timing effects of ambiguous
  sign; only the hard mode produces the one-way exploitation geometry.
- Footnote: the sub-eps arm's 0.997 (not 1.000) pass rate is the velocity
  tail — in ~1/12,000 rollouts |v| gets large enough to push the drag-bias
  error marginally over eps. The arm is sub-eps everywhere but the extreme
  tail.

Offline validation of the LLM arms (no Azure): `tests/test_continuous_contract.py`
drives the full synthesis pipeline (`cwm.continuous.contract`) with
FakeProvider — the hand-written full-spec artifact passes the pinned-
integrator gate at eps=1e-9 **to float precision** (the pinned-integrator
premise holds through the sandbox JSON round-trip), the wall-omitting
artifact passes iff the sample missed the wall and probes fully wall-blind,
and MPC on the synthesized blind artifact is exploited (pinned at the wall).
Runbook for the credentialed run: design doc §"Runbook — LLM arms".

## PAPER 2 — Continuous/hybrid instrument: mechanism go/no-go PASSED (2026-07-06)

First run of the continuous/hybrid rare-mode instrument (cart-with-wall; spec
`docs/specs/2026-07-06-continuous-hybrid-cwm-design.md`, order-of-work step
1-2). The wall-blind model is the hand-written on-manifold proxy (same code
path minus the wall branch — **bit-exact off-mode by construction**, tested);
planner is random-shooting MPC with piecewise-constant + constant candidates.

`PYTHONPATH=src python scripts/continuous_reach.py` (3000 rarity rollouts,
20 MPC episodes/arm per knob, 146 s CPU; `results/continuous_reach.json`):

| x_wall | rarity [Wilson 95%] | J_truth | J_blind | J_rand | play_cost | blind hit | truth hit | d@N=20 | d@40 | d@80 |
|-------:|---------------------|--------:|--------:|-------:|----------:|----------:|----------:|-------:|-----:|-----:|
| 2 | 0.331 [0.315, 0.348] | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.000 | 0.000 | 0.000 |
| 3 | 0.219 [0.205, 0.234] | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.007 | 0.000 | 0.000 |
| 4 | 0.143 [0.131, 0.156] | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.047 | 0.002 | 0.000 |
| 5 | 0.084 [0.075, 0.095] | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.177 | 0.030 | 0.001 |
| 6 | 0.050 [0.043, 0.059] | 17.77 | 0.00 | 0.53 | 1.031 | 1.00 | 0.00 | 0.367 | 0.131 | 0.017 |
| 8 | 0.013 [0.009, 0.017] | 17.77 | 0.02 | 0.53 | 1.030 | 1.00 | 0.00 | 0.798 | 0.619 | 0.372 |
| 10 | 0.002 [0.001, 0.004] | 17.77 | 0.94 | 0.53 | 0.977 | 1.00 | 0.00 | 0.938 | 0.901 | 0.832 |

**The paper-1 mechanism reproduces in continuous state space, sharper:**
- **Threshold law again:** danger ≈ 0 while the wall is inside the random
  envelope, rises through the elbow, plateaus at full play_cost; N shifts the
  threshold (d@20 vs d@80 columns). The whole elbow sits inside the sweep.
- **play_cost knob-invariant** (1.031 flat; 0.977 at x_wall=10 where the
  sigmoid tail of the far lode leaks J_blind=0.94) — and **> 1**: the
  blind-model planner scores *below random* (J 0.00 vs 0.53), because MPC is
  not merely uninformed but actively exploited — it drives into the phantom
  region and stays pinned pressing against the wall for the entire episode,
  replanning the same doomed plan every step (`blind hit` = 1.00 at every
  knob; final x = x_wall exactly). The continuous analogue of "loses ~2:1",
  in stronger form.
- **The reach mechanism, cleaner than paper 1:** exploited-planner wall reach
  flat at 1.00 across the knob; random reach (= rarity) falls 0.33 → 0.002;
  truth-planner trajectory reach 0.00 (the wall is off *its* path — the mode
  lives on the blind planner's deployment path and the truth planner's *query*
  distribution, per the μ_query bound).
- Gate-miss exactness re-verified in-tests: empirical P(N rollouts miss) =
  (1−r)^N within binomial error (`tests/test_continuous.py`).

Calibration findings recorded for the paper (spikes, same date): (i) i.i.d.
per-step candidate sampling makes MPC imagination diffusive — it never reaches
distant reward, and truth/blind rank candidates *identically* (the wall never
enters imagination); piecewise-constant blocks + constant {−1,0,+1} candidates
fix it. (ii) Point (Gaussian) reward lodes demand braking finesse random
shooting lacks; sigmoid plateaus remove the confound. (iii) The plant's drag
time-constant must sit well inside the planning horizon or no arm can act.

GO for order-of-work steps 3+ (synthesis contract, exactness + pervasive-error
control, smooth-bump contrast — `envs.py` already carries the C∞ bump arm).

## Editorial de-archaeology + proper-DAgger rerun + effective-dose measurement (2026-07-05/06)

Follow-up to the concern that some audit *notes* were patches avoiding a needed
redo. Resolved on three fronts:

**1. Proper DAgger, actually run (the redo, not a note).** `spike_dagger2.py`
now aggregates the dataset across rounds (Ross et al. 2011 — the mechanism the
earlier version omitted). Reran (mini, 3 rounds): dataset grows 1249→1860,
discriminating transitions accumulate 0→3→5→11, **rule never learned** across
all rounds (winrates 0.33/0.42/0.33/0.28). One round's synthesis collapsed at
the gate (0.00); the other two reached 0.994–0.997 (<1.0 because the aggregated
dataset now holds rule transitions the rule-blind CWM can't match — same signal
as the sweep). So tab:repair's row is now "proper DAgger" by construction, and
the audit footnote is **deleted**, not kept as a disclaimer.

**2. Effective dose measured (redo, not a hedge).** The targeted-artificial
"120" was audited as a nominal count; measured directly: **115 of 120**
constructed transitions demonstrate the rule decisively (4 general-capture,
1 equal-material draw). Table now reads "120 (115 decisive)" — a number, not
"(nominal)".

**3. Editorial de-archaeology pass.** An agent inventoried every draft-history
self-reference in main.tex and classified each: (A) pure archaeology → delete
the historical clause, keep the content; (B) lesson-in-disguise → restate the
lesson directly; (C) legitimate content → keep. Applied: the `infer_states`
shadowing-crash story (told in FIVE places) collapsed to its single thematic
home (§6.6, retitled "A pitfall worth recording"); 11 pure-archaeology clauses
deleted (audit-corrected-7.4M, ≈0.7%-assumed-random, "earlier version of this
table/run/scope note", "this revision", etc.); 4 lessons rewritten as
robustness checks (seed-scaling stability, mechanism sample-robustness, median
instability under bimodality, fixed-vs-fresh resampling contrast). The two
genuinely scientific correction narratives (§5.2 feedback-channel confound →
discriminant experiment; §6.6 contract-induced crash → thesis instance) kept.
Principle codified: draft history lives in this log and git, not the manuscript.

Also: the "results/ git-ignored" phrasing in the reproducibility section is now
"versioned in the repo" (the artifacts were un-ignored in the prior commit).

PDF 40 pp, clean. Cost: ~$0.5 Azure (DAgger rerun).

## Full script audit — 4 parallel reviewers, every scripts/ + core module (2026-07-04)

Motivated by the bugs found this week (df-indexing, feedback truncation,
crash-vs-blind), all 32 scripts + core modules were audited in 4 batches
(statistics / coverage-CFR / synthesis-sweeps / probes-figures), each finding
verified by the reviewer with read-only computations and the actionable ones
re-verified by hand before fixing. **No finding reverses a published
conclusion**; the figures were verified number-by-number against the current
paper (zero stale); cfr.py's best response was validated against brute-force
enumeration (1e-10 agreement); all headline statistics recompute exactly from
raw data.

**Fixed in this commit (code):**
- `rule_status` in 4 scripts: normalize returns-dict key types before comparing
  (latent gate-vs-classifier asymmetry that could misclassify an AWARE model as
  blind on a rerun; verified never fired on the 120+ stored codes).
- `coverage_bound_constants.py`: d_max now measured per the paper's definition
  (shortest-history player-action depth per info-set) — Kuhn 2 / Leduc 6, not
  the 3/8 horizon. Corrected loose bound: Leduc N≈818k (was 7.4M, ×9 inflated).
- Stale docstrings/defaults frozen at superseded stages: play_cost_ci.py
  (headline is --seeds 20), play_cost_reach.py (--games 120), law_curve.py
  RARITY_GAMES 2000→3000 (published table back-solves to n=3000).
- leduc_coverage_diagnostic.py print labels (said 4000/120 games, ran
  8000/300); leduc_coverage.py gate 4000→8000 + stale debug-sized
  results/leduc_coverage.json regenerated; coverage_competent_leduc.py now
  asserts no competent key is silently dropped from the exact-reach dict.
- divergence/harvest/gen_chess_material docstrings corrected.

**Fixed in this commit (paper):**
- §5.2 confound paragraph: the "≈0.7%" prompt-exposure figure was WRONG — the
  prompt shows a deterministic prefix (first 30 transitions) that can NEVER
  contain a material-at-cap terminal (index ≥ 99 by construction). Probability
  is exactly 0, which sharpens the confound story. Discriminant-signature
  sentence scoped to 9/12 seeds (3 end in refinement collapse, blind too).
- §6.2: loose bound 7.4M → 818k with the d_max correction note; "bar_d = d_max
  with equality" claim corrected to strict inequality (3/8 vs 2/6); "0/1259
  inference-relevant visits" relabeled (denominator counts all visits);
  exploitability annotated as NashConv (BR₁+BR₂).
- tab:repair: "proper DAgger" row relabeled "DAgger-style iterated retraining"
  with an audit footnote — the script never aggregates datasets across rounds
  (DAgger's defining mechanism); conservative direction, labeled by what ran.
  "120" targeted examples marked nominal (pre-move validation only).

**Recorded, not fixed** (LOW/latent, documented): consecutive MCTS base seeds
across replicate seeds (second-order independence risk; replicates verified to
differ); arena.play_match dead `seed` parameter (all callers safe via stateful
agent closures); D_gate duplicate-weighting vs deduped D_cwm (small,
one-directional); visited-cap subset PYTHONHASHSEED-dependence (unbiased,
marginal irreproducibility); order-sensitive legal_actions gate comparison
(conservative); N=40/120/200 trajectory prefix-nesting per seed (cells
dependent across N, fine for a curve). Tests: 199 passed.

## Headline play-cost at 20 seeds (n=4800) — df=19, heterogeneity revealed (2026-07-03)

`python scripts/play_cost_ci.py --seeds 20` (CPU-only, $0, ~40 h wall on shared
cores). The final item of the CPU triage: 20 seeds × 120 games × 2 arms at 600
sims. Results: `results/play_cost_ci.json` (full per-seed).

| arm | pooled (n=2400) | Wilson 95% | per-seed mean ± sd |
|---|---|---|---|
| fair (truth-vs-truth) | 0.495 | [0.475, 0.515] | 0.495 ± 0.035 |
| rule-blind vs truth | 0.404 | [0.384, 0.424] | 0.404 ± 0.041 |

**play_cost = 0.091**, seed-clustered paired t95 **[0.065, 0.117]** (df=19,
sd 0.055), **excludes zero**; pooled CIs separated (0.475 > 0.424).

**Honest movements.** (1) The point estimate came DOWN from 0.131 (5 seeds) to
0.091 — consistent (0.091 ∈ [0.083, 0.179], the old CI): the first five seeds
sat on the high side. Provenance ladder now in the paper: 3 seeds 0.117-ish →
5 seeds 0.131 [0.083, 0.179] → 20 seeds 0.091 [0.065, 0.117]. (2) "Rock-steady
across seeds" is retired: per-seed differences range 0.00 (two seeds!) to 0.19
— real between-seed heterogeneity, which the clustered interval absorbs; the
effect survives anyway. (3) "Loses ~2:1" softened to "1.6 losses per win"
(725W/1187L).

Paper updated everywhere the headline appears (abstract, §1.5, contributions,
Panel A + per-seed table → 20-seed summary table, figure 2 regenerated, §4
measurement note, danger-curve caption, §6.4 consistency check → "about a
third", witness bound ≥0.065, limitations, reproduction appendix).

## Feedback-channel confound found & closed + cross-family probes (2026-07-03)

**The confound.** While relaying pipeline messages to a Claude agent for the
cross-family probe, the agent complained the failure data was truncated — and it
was right: `refiner.py` cut every failure line at 200 chars and NEVER included
the expected values ("FAILURES (expected vs got)" carried neither), and the
synthesis prompt shows only 30 random example transitions (P(contains a
material-terminal transition) ≈ 0.7%). So the rule was present in the *gate's*
trajectories but almost never reached the *model* legibly. This confounded the
strong reading of the §5.2 sweep ("the rule had every opportunity to appear and
still was not learned") — true of the pipeline, not attributable to the model.

**The fix.** `refiner.py` failure lines now show `expected=` and `got=` per
mismatched field (cap 800 chars); covered by
`test_failure_lines_carry_expected_values` (199 tests green).

**The discriminant experiment.** `scripts/refine_feedback_cell.py` — headline
cell (N=200, fresh-batch refinement) with the FIXED feedback, 6 seeds × 2 sizes:

| size | result | signature |
|---|---|---|
| mini | **6/6 blind, 0 crashes** | 5/6 stall at gate 0.999 |
| large | **6/6 blind, 0 crashes** | 4/6 stall at gate 0.999 |

With `returns: expected={1: 1.0, 2: -1.0} got={1: 0.0, 2: 0.0}` printed in the
feedback on cap states, the model repairs everything EXCEPT the rule — the
0.999 stall means exactly the material transitions stay unfixed. Finding 3 is
**deconfounded and stronger**. Results: `results/refine_feedback_cell.json`.

**Cross-family probes** (`scripts/crossfamily_probe.py` + new
`cwm/llm/openai_compat.py`; results `results/crossfamily_probe.json`):
- **Qwen3-Coder-30B** (open, HF router): **3/3 blind, 0 crashes**; 2/3 fail to
  reach gate 1.0 (gate-attainability, like nano). Cost ~$0.1 HF credits.
- **Claude Sonnet** (agent-relayed, pipeline-identical messages via
  `scripts/crossfamily_claude_step.py`): 2 single-seed probes, 1–2 refinement
  iters each, **all compositions rule-blind**; in refinement the model
  explicitly reasoned about the mismatching material states and kept the draw —
  "I cannot identify a behavioral change that alters these outputs without
  contradicting the spec" — the translation mechanism verbalized. Wrapper note:
  two relay attempts were REFUSED by the agent's anti-injection heuristics
  (file-plus-"output only code" pattern); recorded as an agent-wrapper behavior,
  resolved by embedding content directly.
- **DeepSeek-V3.2**: aborted mid-seed on HF 402 (monthly credits exhausted).

Paper updated: §5.2 confound paragraph + discriminant result; §7 "Single model
family" → "one sweep, two cross-family probes" (conjecture stays a conjecture).
Total cost: ~$1 Azure + ~$0.15 HF.

## Equilibrium-reach coverage — the §7.4 promise fulfilled (2026-07-03)

`PYTHONPATH=src python3.12 scripts/equilibrium_coverage.py` (CPU-only, $0).
New `cwm.cfr` module: external-sampling MCCFR + full-tree CFR+ over the
imperfect-info contract, exact public-tree best response, exploitability.
Validated on Kuhn against the analytic value (−1/18; tests/test_cfr.py, 5/5).
Results: `results/equilibrium_coverage.json`.

| game | solver | game value | exploitability | eq-weighted uncovered mass | union bound |
|---|---|---|---|---|---|
| Kuhn (N=80) | CFR+ 2000 iters | −0.0558 (analytic −0.0556) | 0.0068 | 0.015% | all 12 covered (0.0028) |
| Leduc (N=8000) | CFR+ 1000 iters | −0.0866 (lit. ≈−0.0856) | 0.084 (monotone ↓) | **0.013%** | eq-reach ≥1e-3: 316 covered (0.021); tail ≥1e-4 not certifiable |

**The §6.2 coverage conclusion holds against the normatively correct reference
(equilibrium reach), not just MCTS self-play** — and is robust to profile
quality (a crude profile with exploitability 0.79 gives the same conclusion).

**Technical finding worth recording (imperfect recall pitfall).** Both solvers
plateaued at ~0.6–0.8 exploitability when info-sets were keyed by the
*instantaneous* observation: Leduc's per-round counters reset between rounds,
merging distinct betting histories (check-bet-call ≡ bet-call in round 1) — the
observation-keyed game has IMPERFECT RECALL, where CFR carries no guarantee and
a per-branch best response overstates exploitation. Fix: solve on perfect-recall
keys (observation + exact public history) and project reach back onto the
observation keys the gate samples. After the fix, exploitability decreases
monotonically. Kuhn never showed the problem (its observation encodes the full
history). Zero-sum was verified exhaustively over all 5,880 Leduc leaves while
diagnosing.

Paper updated: §6.2 (equilibrium-reach upgrade), §2.3 Planning (ISMCTS/CFR
choices moved here from Related Work), §7.4 condensed to pure related work with
pointers, §8 planner paragraph (remaining gaps: CFR arena + minimax reference).
Two verified refs added (Lanctot et al. 2009; Tammelin 2014).

## Declarative recall probe persisted — question & answer now auditable (2026-07-03)

`PYTHONPATH=src python3.12 scripts/declarative_recall_probe.py large` — the
paper's two recall claims were asserted but their evidence was never persisted.
Now they are: `results/declarative_recall_probe.json` holds the verbatim
system prompt, questions, and full responses.

- **army5x5a**: asked for board size / piece counts / movement offsets / win
  condition / starting position with an explicit decline option → "I do not
  know" to **all five parts**, self-labelled [RECALL]. Confirms "no prior".
- **Trike**: declines all five parts ("I do not reliably know"), self-labelled
  [GUESS]. **Nuance found and fixed in the paper**: the old §2.5 line said the
  model "knows the name but confabulates the mechanics" — in a declarative
  probe with a decline option it does NOT confabulate, it declines; the
  confabulation appears under *synthesis pressure* (no-rules synthesis produces
  confidently wrong mechanics, 0/5 gate). §2.5 rephrased accordingly.
- **Kuhn poker (positive control)**: complete correct recall (deck, betting,
  payoffs, 6 first-player infosets) — so the army5x5a "I do not know" is
  informative, not a generic hedge.

Paper updated: §2.5 (army5x5a + Trike entries), §7 contamination paragraph,
reproduction appendix (probe command + updated sweep/mechanism flags).
Cost: <$0.05, ~1 min.

## Synthesis sweep at 20 seeds/cell — 6/6 upgraded to 20/20, zero crashes (2026-07-02)

`python3.12 scripts/danger_synthesis_sweep.py {mini,large} 20` under the new
crash/blind/aware semantics (crashes excluded from denominators) and the
corrected contract. 120 syntheses total (2 sizes × 3 N × 20 seeds), each with
≤6 fresh-batch refinement iterations. Results JSON (per-seed, auditable):
`results/danger_synthesis_{mini,large}.json`.

| N | mini rule-blind | large rule-blind | initial-batch floor (1−r)^N |
|---|---|---|---|
| 40  | **20/20 = 1.000** [Wilson LB 0.839] | **20/20 = 1.000** | 0.358 |
| 120 | **20/20 = 1.000** | **20/20 = 1.000** | 0.046 |
| 200 | **20/20 = 1.000** | **20/20 = 1.000** | 0.006 |

**Zero crashes, zero aware, in all 120 runs** — the published 6/6 table is
confirmed at 3.3× the denominator, and the crash-vs-blind methodological
concern is resolved empirically: nothing was ever conflated. Wilson 95% lower
bound on the rule-blind rate rises from ~0.61 (6/6) to **0.839** (20/20).
Gate-accuracy detail: at N=200 large, 0/20 seeds reach gate 1.0 (the rule is in
every sample) yet all 20 are blind — the cleanest (b)-residual cell. At N=120,
6/20 mini and 3/20 large reach gate 1.0 while blind, matching the compounded
per-batch miss rate (≈0.28 over up to 7 batches of (1−r)^120 = 0.046).
Paper updated: tab:synthcurve (20/20 + caption), "On the floor" paragraph
(gate-accuracy narrative re-derived from the 20-seed data). Cost: ~$3-8 Azure,
~2.5 h wall (mini+large chained).

## Mechanism reach at n=120 — the small-sample caveat is retired (2026-07-02)

`python scripts/play_cost_reach.py --games 120` (CPU-only, MCTS 300 sims). Triples
the sample of the §4 mechanism measurement (was n=40):

| cap | competent reach (n=40 → n=120) | random reach (n=40 → n=120) |
|---|---|---|
| 30  | 0.200 → 0.183 [0.124, 0.262] | 0.375 → **0.442** [0.356, 0.531] |
| 60  | 0.200 → 0.242 [0.174, 0.326] | 0.200 → 0.133 [0.084, 0.206] |
| 100 | 0.225 → 0.275 [0.203, 0.361] | 0.075 → 0.067 [0.034, 0.126] |

The story sharpens: competent reach stays flat (Wilson 95% intervals overlap
pairwise — no trend resolved), while random reach falls 6.6× (0.442 → 0.067,
CI-separated end to end; at n=40 the drop was 5×). Paper §4 remark + Figure 3
(make_paper_figures.py) + the §6.4 consistency check updated (reach at the
deployed cap is 0.275, so the omitted rule flips ~half of the games that reach
the region, not ~two-thirds). Cost: $0 (CPU), ~50 min.

## Contract-fix rerun: the `infer_states` crash is gone in all three games (2026-07-02)

Rerun of the three imperfect-info probes under the corrected contract (parameter
renamed `observation` -> `obs` + anti-shadowing note; see the root-cause entry
below). Azure GPT-5.4; single seed per probe, matching the original runs.

| Probe | arm | transition gate | observation_rate | inference_rate | exec_err |
|---|---|---|---|---|---|
| masked TTT (large) | full | 1.000 (0 iters) | 1.000 | **1.000** (was: crash) | **0** |
| masked TTT (large) | withheld | 1.000 | 0.020 | 0.180 | **0** |
| Kuhn (mini) | — | **1.000 (0 iters)** (was: 0.845 fail) | 0.500 (p2 obs-index convention, wrong-but-running) | **1.000** (was: crash) | **0** |
| Beacon T=6 (large) | full | 0.456 (10 iters, fails gate) | 1.000 | 0.200 | **0** |
| Beacon T=6 (large) | withheld revelation | **1.000** (2 iters) | 1.000 | **0.000** | **0** |

**Findings.** (1) Zero execution errors across all three games — the recurring
`'list' object is not callable` was entirely our contract's name collision, as
diagnosed; the "synthesis-robustness failure" narrative is retracted in the paper
(§6.6 correction paragraph). (2) The masked-TTT withheld rates are unchanged
(0.020/0.180) and the full arm's `infer_states` is now **exact** — inference_rate
becomes a second clean discriminator (1.000 vs 0.180). (3) Kuhn mini now passes
both gates and plays at parity (0.470 = fair 0.470); its only divergence is a
player-2 observation-index convention (obs 0.500), not a crash. (4) **Bonus:
synthesized gate-blindness corroboration on Beacon** — the withheld-revelation
arm passes the transition gate at 1.000 with inference_rate 0.000: a
transition-certified, belief-wrong CWM, synthesized end-to-end (single-seed
probe; the full arm fails the transition gate at 0.456, reported honestly).

Paper updated: tab:kuhn (mini row), tab:mtt (full-arm inference 1.000), §6.6
rewritten (both discriminators + correction paragraph + Beacon corroboration),
§8 scope note, contribution 5, §2.4 metric definitions (exec-error exclusion).
Log: scratchpad `llm_chain.log`. Cost: <$1.

## Limitations roadmap — CPU-vs-LLM triage of §7 (2026-07-02)

Triage of every paragraph in the paper's *Limitations and Honest Assessment*
(§7 of `main.tex`), split by whether follow-up work needs the LLM (Azure, must
be run locally with credentials) or is CPU-only (pure-Python MCTS, runnable in
CI/here). This commit lands the CPU-only *enablers*; the long reruns and all
LLM work are listed for local execution.

**Enablers landed in this commit (CPU-only, no result numbers changed):**
- `src/cwm/llm/azure_openai.py`: `max_retries=6` (was the SDK default 2) and a
  120 s timeout, both constructor-overridable. The openai SDK does exponential
  backoff and honours `Retry-After`; the previous ceiling was too low to ride
  out sustained 429s on multi-hour synthesis sweeps. This is the prerequisite
  for every LLM rerun below.
- `src/cwm/law.py`: new `t_crit_95(df)` — two-sided 95% Student-t critical
  values for any df (table to 120, conservative round-down, normal-ish tail).
  Removes the per-script hardcoded dicts that capped at ~6 seeds.
- `scripts/play_cost_ci.py`: `--seeds/--games/--sims` (defaults reproduce the
  published n=600); uses `t_crit_95`, so the seed-clustered interval is no
  longer limited to <=6 seeds. **Bug fixed:** the old code indexed its t table
  by the seed *count* k, i.e. it used the df=5 critical value (2.571) for a
  paired-t over 5 seeds whose correct df is 4 (2.776). The published clustered
  interval `[0.086, 0.175]` was computed with the wrong df; the correct df=4
  interval is **`[0.083, 0.179]`** (still excludes zero — the conclusion holds,
  and the lower bound moves 0.086 -> 0.083). **The paper is now corrected**:
  `main.tex`, the arXiv copy, `preprint-draft.md`, and `RESEARCH-DIRECTION.md`
  all quote `[0.083, 0.179]` / `>= 0.083`, and `main.pdf` + the arXiv tarball
  are rebuilt. (The dated entries lower in this log keep the original numbers as
  a record of what was reported at the time.)
- `scripts/play_cost_reach.py`: `--games/--sims` (defaults reproduce the n=40
  mechanism figures) so the "small-sample" mechanism reach can be raised.
- `scripts/danger_synthesis_sweep.py`: prints the Wilson 95% interval alongside
  each `blind/len(SEEDS)` (a bare 6/6=1.000 has Wilson LB ~0.61), and takes an
  optional seed-count `argv[2]` to grow the denominator.

**Per-limitation triage:**

| §7 paragraph | Follow-up | Where | Command / note |
|---|---|---|---|
| Pure-Python MCTS limits CIs | raise headline seeds 5->~20 (Azure-free) | **CPU-only, long — IN PROGRESS (2026-07-03)** | `python scripts/play_cost_ci.py --seeds 20` running (~1 h/seed on this machine, not 3-4 h total; update Table/abstract CIs + rebuild PDF when done) |
| (same) mechanism n=40 flagged small-sample | raise reach games 40->~120 | **✅ DONE (2026-07-02)** | n=120 run; §4 + Figure 3 + §6.4 consistency check updated (see entry above) |
| Determinized MCTS not GT-optimal | external-sampling MCCFR equilibrium baseline (CFR is contract-compatible, §8) | **CPU-only, large build** | new solver + validation; measures the gap vs equilibrium reach, not MCTS reach |
| Rare-rule instrument is engineered | broaden the rarity<->consequence characterization across a rule set (rarity via random games + play_cost via hand-coded rule-blind instrument, both in `cwm.law`) | **CPU-only** for the map; **LLM** to confirm the LLM reproduces a gap | extend the Connect-Four 6-rule probe |
| Single model family (GPT-5.x only) | run synthesis on other families (open models / stronger code models) | **LLM (local)** | `danger_synthesis_sweep.py` + gap grid against non-Azure providers; needs a provider adapter |
| finding-3 denominators are 6 seeds | grow `danger_synthesis_sweep` 6->~20 seeds/cell | **✅ DONE (2026-07-02)** | 20/20 in every cell, both sizes, zero crashes (see entry above) |
| Beacon is a minimal/trivial witness | synthesize a CWM for a partially-observable army5x5a variant | **LLM (local)** | game/instrument is CPU; the synthesized-CWM demonstration needs the LLM |
| Gate-blindness scope / `infer_states` crash | **root cause found & contract fixed (below)**; then rerun to confirm | **✅ CONFIRMED (2026-07-02)** | rerun of all three games: zero exec errors; §6 rewritten (see entry above) |
| Knowledge cutoff / contamination | more declarative recall probes | **✅ probe persisted (2026-07-03); inherent limit remains** | `scripts/declarative_recall_probe.py` — army5x5a/Trike/Kuhn-control Q&A verbatim in `results/declarative_recall_probe.json`; "no detectable recall", not "strictly novel" — not fully closable |

**Root cause of the recurring `'list' object is not callable` crash — very
likely OURS, not the LLM's, and not transient.** The `infer_states` crash the
paper reports across Kuhn-mini / Beacon / masked-tic-tac-toe is a deterministic
Python `TypeError`, so it is neither a rate-limit nor a flake. The mechanism: the
imperfect-info contract (`world_model.IMPERFECT_CONTRACT_API`) prescribed the
signature `def infer_states(observation: list[int], player: int)` — the
**parameter is named `observation`, which shadows the required `observation()`
function** in the same contract. The very next contract sentence tells the model
"every state in `infer_states(observation(s,p),p)` must map back to the same
observation", i.e. it invites the model to call `observation(...)` from inside
`infer_states` — where that name is now the list argument. Any such call yields
exactly `'list' object is not callable`. The reference implementation sidesteps
this by naming the parameter `obs_board` (`groundtruth/masked_tictactoe.py`),
but the *prompt* told the model to use `observation`.
**Fix applied (this commit):** the contract now names the parameter `obs`, adds
an explicit "do not shadow the `observation()` function" note, and spells out the
round-trip invariant as `observation(s',p) == observation(s,p)`. No code depends
on the old parameter name (the sandbox calls `infer_states` positionally and the
reference impls use their own names; 192 tests green). **Confirmation that this
resolves the crash needs a local LLM rerun** (`scripts/mtt_claimB_probe.py`,
`scripts/run_kuhn_validation.py`, `scripts/beacon_claimB_probe.py`) — if it does,
the paper's "GPT-5.4 cannot robustly synthesize `infer_states`" narrative is
partly an artifact of our contract and should be softened.

**Crashes no longer count as results (fixed this commit).** `is_rule_blind`
(bare `except -> True`) counted a synthesized CWM that *crashes* as rule-blind,
conflating a synthesis-robustness failure with genuine rule-blindness. Replaced
by `rule_status(code) -> ('aware'|'blind'|'crash', error)`: a crash is reported
separately and **excluded from the rule-blind denominator** (rate = blind/(blind
+aware)), unless every seed crashes (structural — the crash count makes that
visible). Principle: a crash, unless structural and unavoidable, is not a result.
The same pattern in `gap.inference_accuracy` is **now fixed too**: a crashed
`observation()`/`infer_states()` no longer lands in the rate denominator as a
non-inference. `observation_rate = obs_ok/obs_measured` and `inference_rate =
inf_ok/inf_measured` range only over cases that actually ran; exec errors are
reported separately (`obs_errors`, `inf_errors`, `n_exec_errors` = cases with any
error), and an all-crash surface reads as structural (rate 0.0 with the error
count making it visible) rather than a scored miss. This changes published
masked-TTT/Kuhn `inference_rate` numbers once rerun (e.g. the masked-TTT FULL arm
0.000 was entirely the `infer_states` crash — it will now read as structural
exec-error, and with the contract name-collision fix above the crash itself
should largely disappear). Covered by `test_inference_accuracy_excludes_exec_errors`.

**Per-seed results are now logged (fixed this commit).** The sweep previously
printed per-seed lines to stdout but persisted nothing, so crashes vs blind vs
aware could not be audited after the fact. It now writes
`results/danger_synthesis_<size>.json` with a `summary` (per-N blind/aware/crash
counts, rate + Wilson CI, identifiability floor) and a `per_seed` array (status,
error, gate_acc, iters, n_samples, and the synthesized code for each seed). The
headline play-cost sweep (`play_cost_ci.py`) already logged per-seed win rates
and the paired-difference vector to `results/play_cost_ci.json`.

## §3.2 null upgraded to a proof by exhaustion — tic-tac-toe (2026-06-29)

`scripts/exhaustive_verify_tictactoe.py` (Azure GPT-5.4-mini). Synthesize a
tic-tac-toe CWM, confirm it passes the random gate (accuracy 1.0, 0 refine iters),
then verify it against the truth over the ENTIRE reachable state space by BFS:

- reachable states: **5478**; transitions checked: **16167**
- **search-relevant mismatches: 0** (legal_actions on non-terminal states,
  apply_action on every (state, legal action), is_terminal, returns) →
  **globally correct on reachable states, by exhaustion** (not "no observed divergence").
- terminal-legal convention artifacts (excluded): **880** — the synthesized code
  omits the `is_terminal` guard in `legal_actions`, so it returns moves on won-but-
  not-full boards; a planner never queries `legal_actions` on a terminal state, so
  this is behaviourally irrelevant (the paper's `legal_terminal_divergences`,
  independently re-derived here by exhaustion).

This is the transition-function analogue of the coverage bound (Theorem 1): the
random gate certifies global correctness exactly when its check covers the full
reachable relation. For tic-tac-toe (small enough to enumerate) we make the check
exhaustive → gate-pass ⇒ globally correct, proven. For army5x5a / gen_tictactoe 6×6
the reachable space is too large to enumerate, so the null stays a statement about
the evaluated distributions — consistent with army5x5a being the one game with a
residual (gap 0.002). Result JSON: `results/exhaustive_tictactoe.json`. Tic-tac-toe is the only §3.2 game small enough: **Trike side-6 reachable space exceeds 3,000,000 states** (measured BFS, still growing at the cap), and army5x5a / gen_tictactoe 6×6 are far larger — so those stay sampled, not exhaustively proven.

## Synthesis-pipeline danger curve — translation-not-inference, earned (2026-06-28)

`scripts/danger_synthesis_sweep.py` (Azure GPT-5.4-mini). Synthesize a CWM from the
INCOMPLETE army5x5a rules + N true-game (army5x5a+material) trajectories, with the
**fixed refiner drawing FRESH trajectories each iteration** (`resample_fn`; the
reuse bug is corrected). Rule-blindness tested MCTS-free: does the CWM's `returns`
give the material winner on cap+unequal-material states (truth) or a draw (rule-blind)?

| N (games) | mini rule-blind | large rule-blind | identifiability floor (1−r)^N |
|-----------|-----------------|------------------|-------------------------------|
| 40  | **6/6 = 1.000** | **6/6 = 1.000** | 0.358 |
| 120 | **6/6 = 1.000** | **6/6 = 1.000** | 0.046 |
| 200 | **6/6 = 1.000** | **6/6 = 1.000** | 0.006 |

The rule-blind rate is ≈1.0 across N for BOTH model sizes, **far above** the
identifiability floor (1−r)^N. This is the (a)+(b) split measured on the actual
synthesis pipeline: (a) the floor (1−r)^N is the rate at which the rule is
unidentifiable (any learner); (b) the LLM is rule-blind well above the floor — it
does not infer the rule from trajectories even when present at large N with
resampling.

**large is the sharper case:** its gate accuracy is mostly LOW (0.00–0.13 across
N=120/200 seeds) — i.e. the rule IS heavily present in the sample (the rule-blind
CWM mismatches those transitions, so the gate cannot reach 1.0) — yet after six
refinement iterations the CWM is still rule-blind in every seed. The model sees the
rule en masse and still does not encode it. (mini sometimes reached gate 1.0 = the
rule happened to be absent — the identifiability event; large's low gate accuracy
rules that out, isolating the genuine learning failure.) **nano** (confounded:
gate accuracy is low everywhere because nano cannot synthesize army5x5a at all,
§3.2) is also rule-blind 6/6 at N=40; its rule-blindness reflects gate-attainability,
not the inference question.

This *earns* a strong empirical form of translation-not-inference (mini AND large,
fresh-resampling refiner, up to N=200) rather than asserting it. Fixed-refiner note:
the distinct-sample count (n_samples 1.2k–46.6k with resampling) confirms refinement
now draws fresh trajectories, so the rule had every opportunity to appear; it still
was not learned.

## Revision-2 hardening: coverage constants, identifiability, play_cost mechanism (2026-06-28)

**Coverage bound, exact constants** (`scripts/coverage_bound_constants.py`, exact
enumeration of reachable info-sets + reach probabilities under uniform-random play):
- Kuhn: |𝓘|=12, π_min=0.0833, N_suff(tight)=66; at N=80 the union-bound failure upper bound (from exact reach probs)
  = 0.0028 → **provably covered**.
- Leduc: |𝓘|=576, π_min=3.5e-4; the worst-case-depth bound needs N≈7.4M, the tight
  (π_min) bound N≈27k, and at N=8000 the union-bound failure upper bound over ALL 576 reachable
  info-sets = 2.22 → the theorem does **not** certify full coverage at 8000.
- Leduc, competent-relevant subset (`scripts/coverage_competent_leduc.py`): the 146
  info-sets competent determinized-MCTS visits have π_min=6.9e-4; at N=8000 the exact
  union-bound failure upper bound over this subset = **0.027 < 0.05 → covered w.h.p. (sampled subset)**.
  Since Claim A concerns only competent-relevant info-sets, the Leduc null is covered
  w.h.p. on the SAMPLED competent-visited subset (200 MCTS games — observed, not the
  full competent support; the full-reachable-set bound stays loose). Turns
  "empirically covered" into "covered under exact random-reach probs on the sampled
  competent-relevant subset".

**Enumeration-free error-mass certificate** (`scripts/error_mass_certificate.py`,
2026-07-02; companion to the coverage bound — no |𝓘|, no π_min, no reach
probabilities; only the rule-level constants b and bar_d enter):
- Kuhn (N=80, b=2, bar_d=3): any gate-passing `infer_states` fixed before the gate
  has undetected-error hit mass ≤ ln(1/0.05)/80 = **0.037** under ρ; any-profile
  transfer (×b^bar_d = 8) ≤ **0.30**. Weaker than the enumerative full-coverage
  certificate at the same N — where enumeration is feasible, Theorem 1 stays sharper.
- Leduc (N=8000, b=3, bar_d=8): mass under ρ ≤ **3.7e-4**, but the any-profile
  transfer factor 3^8=6561 is vacuous (consistent with Theorem 1 not certifying
  N=8000). Mixture gate (λ=1/2, same N=8000): deployed-planner error mass ≤
  **7.5e-4** — a competent-relevant certificate the enumeration route could not
  give (it needed N≈27k and only certified the SAMPLED competent subset).
- Occam/class-uniform variant needs N ≳ artifact description length (~10^4 bits
  for kB-scale code) → prefer a held-out gate (sample drawn after synthesis).

**Beacon exact play_cost by exhaustion** (`scripts/play_cost_exact_beacon.py`,
2026-07-02): play_cost on Beacon is now a THEOREM, not a measurement. Two levels,
both mechanically verified against the implementation (4 deals × 2 seatings = 8
deterministic games):
- belief→guess abstraction (the proof): fair arm draws all 8 → win rate exactly
  0.500; instrument seat loses all 8 → exactly 0.000; **play_cost = 0.500 EXACT**.
- real determinized-MCTS policy (the planner check): reproduces all-draws /
  all-losses on the same 8 games.
The arena 0.000 [0.000, 0.003] (n=1200) is now confirmation of a theorem. With
Prop 1 (gate-miss exact) this makes BOTH danger-law factors analytic on the
inference axis. Also recorded in the paper: play_cost upper bound
play_cost ≤ μ_query(E) (coupling argument, Prop 2) — consistency on army5x5a:
competent cap-reach 0.200–0.225 lower-bounds μ_query, measured play_cost 0.131
respects it; and the n=600 CI measurement re-read as a witness-certified lower
bound play_cost ≥ 0.086 (seed-clustered 95%).

**Material-at-cap rarity, two measured rates** (3000 random games, cap=100):
cap reached (both generals alive) = 5.2%; **material-terminal rarity** (the rule
decides the game; used by the danger law) = **2.5%**. (Corrects the earlier loose
"~1%" figure — the law's r=0.0253 (76/3000) is the material-terminal rate.)

**play_cost mechanism** (`scripts/play_cost_reach.py`, MCTS 300 sims, 40 games):
P(reach cap) competent vs random by cap — 30: 0.200/0.375; 60: 0.200/0.200;
100: 0.225/0.075. Competent reach-cap is roughly CONSTANT in the cap knob (~0.21)
while random reach-cap VARIES strongly. This is a (small-sample) mechanistic
correlate of the danger law's cheap/expensive split: play_cost (competent reach,
~constant) vs rarity (random reach, knob-dependent). play_cost stays an empirical
regularity, now with a measured mechanism.

## Headline play-cost with Wilson CIs + seed-clustered interval (n=600) — peer-review hardening (2026-06-30)

`scripts/play_cost_ci.py` / `scripts/play_cost_blind3.py` (Azure-free, 600 sims,
**5 seeds × 120 = 600 games/arm**, true game = army5x5a + material-at-cap). Writes
`results/play_cost_ci.json`.

| Arena | W/D/L | win rate | Wilson 95% |
|-------|-------|----------|------------|
| truth-vs-truth (fair baseline) | 197/214/189 | 0.507 | [0.467, 0.547] |
| rule-blind vs truth (play cost) | 169/113/318 | 0.376 | [0.338, 0.415] |

**Pooled separation:** fair lower bound 0.467 > rule-blind upper bound 0.415.
play_cost = 0.131 (consistent with the prior 0.117–0.121).

**Seed-clustered (the seed, not the game, as the independent unit)** — addresses the
per-game-independence objection (reviewer point #2). Per-seed win rates: fair
0.479/0.529/0.471/0.529/0.525, rule-blind 0.383/0.383/0.362/0.417/0.333. The
paired-by-seed difference (cancels start-side/budget, identical across arms) has
mean 0.131, sd 0.039, and a Student-t 95% interval **[0.086, 0.175] (df=4) that
excludes zero**. Wider than the pooled interval (only 5 clusters) but the effect
survives. Upgrades the earlier n=360 (3-seed subset: fair 0.493, rule-blind 0.376)
to n=600 with a cluster-robust interval; the rule-blind point is unchanged.

## Imperfect information — Claim B: the belief model is invisible to a transition gate (2026-06-27)

`scripts/mtt_claimB_probe.py` (Azure GPT-5.4 large). Masked tic-tac-toe = standard
tic-tac-toe dynamics + an arbitrary, non-recallable masking rule (the center cell is
hidden, shown as -1). Synthesize the contract two ways — full rules vs the masking
rule withheld — and gate each on transitions AND inference:

| variant | transition gate | observation_rate | inference_rate |
|---------|-----------------|------------------|----------------|
| FULL rules | **1.000** (0 iters) | **1.000** | 0.000 (infer_states crashes) |
| WITHHELD masking rule | **1.000** | **0.020** | 0.180 |

**The demonstrable triangle (clean on `observation_rate`):**
- **transition gate = 1.000 in BOTH arms** — tic-tac-toe dynamics synthesize by
  recall, unaffected by the masking rule. The transition gate never invokes
  `observation`/`infer_states` (verified: `contract_accuracy` calls only
  apply_action/legal_actions/is_terminal/returns), so it is **structurally blind to
  the belief model**.
- **FULL → observation_rate 1.000:** told the masking rule, the model masks the
  center correctly.
- **WITHHELD → observation_rate 0.020:** without the rule the synthesized
  `observation` does not mask the center — a wrong belief model — yet the transition
  gate still certifies it at 1.000.

This is Claim B: a belief model that fails the inference gate is invisible to a
transition-accuracy gate, because the information partition it encodes appears in no
`(s,a,s')` transition tuple (see RESEARCH-DIRECTION, belief–transition orthogonality
proposition). Complements Claim A (Beacon): a wrong belief both **loses at play** (A)
and is **invisible to a transition gate** (B).

**Caveat (honest):** `inference_rate` is NOT a clean signal here — GPT-5.4's
synthesized `infer_states` raises `'list' object is not callable` (full arm → 0.000),
the same recurring bug seen on Kuhn-mini and Beacon. So `inference_rate` is confounded
by a synthesis-robustness failure in both arms; the clean discriminator is
`observation_rate`. That recurring crash is itself a secondary finding: across three
games GPT-5.4 fails to robustly synthesize an enumeration-style `infer_states`, i.e.
the belief surface is not only un-gateable by transitions but also hard to synthesize
at all.

## Imperfect information — Beacon: a PROVABLE positive Claim A (2026-06-27)

Poker has no inference coverage gap (competent play is shallower than random).
Beacon is the minimal game engineered to have one: a survival walk (depth =
survival; `safe(k,t)=(k+t)%2`, an unsafe move loses immediately) + a final round
where each player must guess the opponent's hidden type (inferable from its observed
moves). Random play reaches the final round with probability `(1/2)^{2T}`; optimal
play with probability 1. Oracle `src/cwm/groundtruth/beacon.py`, instrument
`src/cwm/beacon_instrument.py`, driver `scripts/beacon_claimA.py`.

The Claim A instrument flips the opponent type **only at final-round states**
(`status==1`) — the deep region D a random gate never samples.

**Result (T=8, GATE_GAMES=2000, arena N=400×3 seeds, 100 sims, 2 determinizations):**

| metric | value |
|--------|-------|
| random reaches final round | 0.00000 |
| instrument inference mismatches on random sample | **0 / 8156** (passes the gate) |
| fair baseline (truth vs truth) winrate | 0.500 exact — 1200/1200 draws (deterministic by the Beacon exhaustion proof; a sampling CI is not applicable) |
| instrument winrate vs truth | **0.000 [0.000, 0.003]**, net −1200/1200 |

The instrument passes the inference gate perfectly yet loses every game — a
**verified-but-wrong inference function that is play-inadequate**, the
imperfect-information analogue of the perfect-info rare-rule gap, and the first
*positive* imperfect-info Claim A.

**Danger law on the inference axis** (`danger = play_cost·(1−ε)^N`, ε=`(1/2)^{2T}`,
N=2000, play_cost=0.5):

| T | ε | gate-miss (1−ε)^N | danger |
|---|---|-------------------|--------|
| 4 | 3.9e-3 | 0.000 | 0.000 |
| 6 | 2.4e-4 | 0.614 | 0.307 |
| 8 | 1.5e-5 | 0.970 | 0.485 |
| 10 | 9.5e-7 | 0.998 | 0.499 |

At T=4 the rule is frequent enough that the gate catches it (danger≈0); by T≥8 the
gate is blind and harm saturates at play_cost (≈0.5; danger T=10 = 0.499) — the exact `(1−ε)^N` threshold, now
instantiated on the inference half of the contract. Same gate-miss mechanism, two
faces (transition rule ↔ inference info-set).

What is proven vs measured: the reach bound `(1/2)^{2T}`, optimal-reaches-D, and
flip⇒loss are analytic (see RESEARCH-DIRECTION); the table is their instantiation.
Whole-branch review (opus) verified the oracle by hand-trace + live simulation:
instrument loses *only* because of the flipped inference; fair baseline is all-draws;
the determinized planner converts correct inference into the winning guess.

### Beacon policy-guided and adversarial belief gates (2026-07-19)

The random-gate result above diagnoses a coverage hole; this experiment tests the
mixture-gate remedy already implied by the enumeration-free certificate. Both arms
use 2000 held-out play-throughs. The control is the original 2000 uniformly-random
games. The mixed arm replaces one random game with one trajectory generated by the
trusted Beacon oracle and the deployed determinized-MCTS planner family (100
simulations, 2 determinizations). Gate-state generation never calls the candidate.

| gate | play-throughs | belief checks | inference mismatches | verdict |
|------|---------------|---------------|----------------------|---------|
| random-only | 2000 random | 8156 | **0** | pass |
| policy-guided mixture | 1999 random + 1 reference | 8190 | **4** | **reject** |
| bounded adversarial search | deepest-first oracle tree | **34** | **2** | **reject after 17 states** |

At `T=8`, random play reaches the deep final region D with probability
`2^-16 = 1.5259e-5` per game, so a 2000-game random gate misses D with probability
`0.969943`. The trusted reference policy reaches D with probability 1. Its single
trajectory contributes the two final-round pre-action states; checking both players
at each exposes four flipped posteriors. The mixed arm has only 0.4% more belief
checks because the competent trajectory survives longer, while retaining the same
2000-play-through budget.

The more general falsifier does not assume a reference policy. It expands reachable
non-terminal oracle states deepest-first, checking both players at each state, and
stops on the first belief counterexample. On Beacon it reaches D at depth 16 after
only 17 expanded states / 34 belief checks and rejects on the two flipped posteriors
at that first final-round state. This efficiency is specific to Beacon's survival
tree: every unsafe child is terminal, leaving one continuing branch. In a general
game the non-terminal frontier may grow exponentially, so a bounded search that
finds no counterexample is not a proof unless it exhausts the reachable state space.

Scope: “adversarial” means deliberate falsification on the deployment-critical
distribution, not a candidate-adaptive adversary that reads candidate code. The
mixture result closes the Beacon witness for this trusted reference policy; it does
not claim uniform coverage over every possible competent policy. The adversarial
search removes that policy assumption within the states it actually explores, in
exchange for potentially exponential search cost.

Reproduce (CPU only):

```bash
PYTHONPATH=src python scripts/beacon_adversarial_gate.py
```

Machine-readable output: `results/beacon_adversarial_gate.json`.

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

> **Reproduction note (2026-07-03).** The original run of this measurement was
> ad-hoc and its script was never persisted; `scripts/divergence.py` now exists
> (recreated) and writes `results/divergence.json`. The rerun (30 games/arm,
> 300 sims) reproduces the qualitative signature decisively but NOT the exact
> medians: army5x5a competent-play lengths are strongly bimodal (quick wins or
> cap-length games), so the median is unstable — the robust divergence metric
> is the cap-hit rate: **43% of competent games hit the 100-ply cap vs 3%
> random** (means 52 vs 32 plies); gen_tictactoe −14, trike +2, connect_four +2
> median divergence (no army-like signature anywhere else). The paper's §3.3
> sentence has been updated to the reproducible metric with a provenance note.

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

## Quantitative law: danger = consequence × P(escape) (2026-06-26)

The harm from accepting a CWM on random-trajectory accuracy is
`danger(rule, N) = play_cost × (1 − rarity)^N`. Measured efficiently by
separating the cheap, varying term (rarity = random-play incidence, no MCTS) from
the expensive, ~constant term (play_cost, MCTS): the rule-blind planner's loss is
~constant across caps because **competent play always reaches the cap region**,
while random-play rarity varies with the cap length. So we measure play_cost
precisely once and sweep rarity cheaply.

- **play_cost ≈ 0.12, ~constant** (independent runs: `play_cost.py` 0.117–0.121 at
  cap=100, n=240, 600 sims; `law_sweep` 0.112 at cap=30). Fair baseline
  truth-vs-truth = 0.504 (n=240) ✓ ≈ 0.5.
- **rarity(cap)** over 3000 random games each, and `danger = 0.12 × (1−rarity)^N`:

| cap | rarity | (1−r)^40 | danger@20 | danger@40 | danger@80 |
|----:|-------:|---------:|----------:|----------:|----------:|
|  25 | 0.3367 | 0.0000   | 0.000 | 0.000 | 0.000 |
|  40 | 0.2080 | 0.0001   | 0.001 | 0.000 | 0.000 |
|  60 | 0.1073 | 0.0107   | 0.012 | 0.001 | 0.000 |
|  80 | 0.0560 | 0.0997   | 0.038 | 0.012 | 0.001 |
| 100 | 0.0253 | 0.3583   | 0.072 | 0.043 | 0.015 |
| 120 | 0.0113 | 0.6339   | 0.096 | 0.076 | 0.048 |
| 140 | 0.0067 | 0.7652   | 0.105 | 0.092 | 0.070 |

**Result (threshold law, not an inverted-U).** Because play_cost is ~constant,
danger is ≈0 while the rule is common enough for an N-trajectory gate to catch it
(cap ≤ 50), then **rises through a threshold** as the rule becomes rare (cap
60–100), and plateaus at ≈ the full play_cost once the rule almost always escapes
the gate (cap ≥ 120). The gate size `N` shifts the threshold: more verification
trajectories push it right (a rarer rule is needed to escape).

This generalizes the single-instrument result: a rule harms a sampling-verified
planner **iff** it is rare under random play (escapes the gate) yet consequential
in competent play (high play_cost), and the expected harm is quantitatively
`play_cost × (1−rarity)^N`. Connect Four's consequential rules cannot enter the
danger zone (their rarity 0.12–0.38 keeps `(1−rarity)^40 ≈ 0`); army5x5a's
deep-tail rule can, because competent and random play diverge there.

```bash
PYTHONPATH=src python scripts/law_curve.py   # cheap rarity grid + cost probes (+ danger curve)
```

## Imperfect information — Kuhn poker pipeline validation (2026-06-26)

New machinery (contract `observation`/`infer_states`/`initial_states`,
determinized-MCTS planner, `inference_accuracy` gate, `imperfect_arena`), validated
end-to-end on Kuhn poker. `scripts/run_kuhn_validation.py {mini|large}`.

| Synth | transition gate | inference gate (obs / infer) | CWM-vs-truth play | fair baseline |
|-------|-----------------|------------------------------|-------------------|---------------|
| large | 1.000 (0 iters) | 1.000 / 1.000                | 0.470 [0.422,0.519] | 0.470 [0.422,0.519] |
| mini  | 0.845 (12 iters, fails gate) | 1.000 / 0.000 (infer_states crashes) | — | — |

- **large:** recalls Kuhn; both gates pass; CWM plays identical to the truth-vs-truth
  baseline (overlapping CIs) — gate-pass → play ≈ baseline, validating the pipeline
  (a near-zero gap is the *expected* recall result, not the contribution).
- **mini:** does NOT cleanly synthesize this (non-standard net-chip) encoding — the
  transition gate stalls at 0.845 and the synthesized `infer_states` raises
  (`'list' object is not callable`). A scale/representation dependence consistent
  with translation-not-inference.
- Determinized planner hardened to tolerate a faulty synthesized model (raising/
  empty inference, crashing dynamics) → legal fallback move, so Claim A/B runs on
  deliberately-wrong models don't abort the arena.

Next (Azure): **Claim A** (membership-valid-but-skewed `infer_states` that passes
the gate yet loses at play) and **Claim B** (synthesis with rules withheld).

## Imperfect information — Leduc coverage-gap (Claim A) is structurally NULL (2026-06-27)

Built a Leduc oracle (6-card deck, community card, 2 betting rounds with raises;
`src/cwm/groundtruth/leduc_poker.py`) to attempt Claim A via an inference
coverage gap: a CWM whose `infer_states` is wrong only on info-sets that competent
play reaches but random sampling (the gate) misses. `scripts/leduc_coverage_diagnostic.py`.

**Result — no coverage gap exists.** Random play (8000 games) vs competent
determinized-MCTS play (300 games):

| metric | value |
|--------|-------|
| random-reachable info-sets | 574 |
| competent-visited info-sets | 156 |
| competent visits on random-covered info-sets | 1259/1259 = **1.000** |
| competent visits on info-sets random missed (inference-relevant) | 0/1259 = **0.000** |
| distinct competent-only inference-relevant info-sets | **0** |

Competent info-sets are a strict **subset** of random-covered ones. Reason:
uniform-random play raises/calls indiscriminately (prob 1/3 each), so it
*over-explores* the shallow betting tree relative to selective competent play
(which folds dominated hands). Random play reaches even the deepest capped-pot
lines (`max_committed=13, total=22`) at frequency 0.0071 ≫ 1/8000.

**This is the imperfect-info analogue of the gate-is-identifying result, and it
admits a proof, not just an experiment** (see RESEARCH-DIRECTION "coverage bound"):
under uniform random play every reachable info-set at betting-depth d has reach
probability ≥ b^{-d} (b = max branching), so a sample of N ≳ b^{d_max} games covers
all reachable info-sets — hence all competent-relevant ones. A coverage gap
therefore requires b^{d_max} ≫ N (large branching and/or depth), which shallow
betting games (Kuhn b=2 d≈2; Leduc b=3 d≈8, b^d≈6561 < N) do not have. The
perfect-info rare-rule gap exploited exactly such depth (army5x5a: competent play
reaches the ply cap; short random games do not).

**Implication:** a positive imperfect-info Claim A needs a game with
b^{d_max} ≫ feasible N — a *deep/wide* imperfect-information game, not a toy poker.
The machinery (contract, determinized planner, inference gate, arena, instrument)
is built and validated; only a larger oracle is missing.

## Imperfect information — Leduc coverage-gap (Claim A) is structurally NULL (2026-06-27)

Built a Leduc oracle (6-card deck, community card, 2 betting rounds with raises;
`src/cwm/groundtruth/leduc_poker.py`) to attempt Claim A via an inference
coverage gap: a CWM whose `infer_states` is wrong only on info-sets that competent
play reaches but random sampling (the gate) misses. `scripts/leduc_coverage_diagnostic.py`.

**Result — no coverage gap exists.** Random play (8000 games) vs competent
determinized-MCTS play (300 games):

| metric | value |
|--------|-------|
| random-reachable info-sets | 574 |
| competent-visited info-sets | 156 |
| competent visits on random-covered info-sets | 1259/1259 = **1.000** |
| competent visits on info-sets random missed (inference-relevant) | 0/1259 = **0.000** |
| distinct competent-only inference-relevant info-sets | **0** |

Competent info-sets are a strict **subset** of random-covered ones. Reason:
uniform-random play raises/calls indiscriminately (prob 1/3 each), so it
*over-explores* the shallow betting tree relative to selective competent play
(which folds dominated hands). Random play reaches even the deepest capped-pot
lines (`max_committed=13, total=22`) at frequency 0.0071 ≫ 1/8000.

**This is the imperfect-info analogue of the gate-is-identifying result, and it
admits a proof, not just an experiment** (see RESEARCH-DIRECTION): under uniform
random play every reachable info-set at betting-depth d has reach probability
≥ b^{-d} (b = max branching), so a sample of N ≳ b^{d_max} games covers all
reachable info-sets — hence all competent-relevant ones. A coverage gap therefore
requires b^{d_max} ≫ N (large branching and/or depth), which shallow betting games
(Kuhn b=2 d≈2; Leduc b=3 d≈8, b^d≈6561 < N) do not have. The perfect-info
rare-rule gap exploited exactly such depth (army5x5a: competent play reaches the
ply cap; short random games do not).

**Implication:** a positive imperfect-info Claim A needs a game with
b^{d_max} ≫ feasible N — a *deep/wide* imperfect-information game, not a toy poker.
The machinery (contract, determinized planner, inference gate, arena, instrument)
is built and validated; only a larger oracle is missing.

### Depth probe — poker depth does NOT create a usable inference gap (2026-06-27)

`scripts/leduc_depth_probe.py` sweeps Leduc's per-round raise cap (deepening the
betting tree) at fixed random-gate N=8000, 100 competent determinized-MCTS games:

| raise cap | random infosets (max depth) | competent infosets (max depth) | uncovered inference-relevant |
|-----------|------------------------------|--------------------------------|------------------------------|
| 2 | 574 (8)  | 120 (6) | 0 / 418 = 0.0000 |
| 4 | 1090 (11)| 128 (7) | 0 / 400 = 0.0000 |
| 6 | 1210 (12)| 127 (9) | 5 / 396 = **0.0126** |

A gap appears only at cap 6 and is marginal (1.26% of competent visits, 5 info-sets)
— too weak for a CI-separated play deficit. Mechanism: in poker, betting **depth
comes from aggression**, which competent play *minimizes* (it calls/folds), so
competent play is always SHALLOWER than random (max depth 9 vs 12). Competent ⊆
random-covered persists. **Poker is the wrong family for an inference coverage gap.**

A usable gap needs competent play to reach a deep/rare region MORE than random —
which happens when depth = *survival* (perfect-info board games: competent reaches
the ply cap, random blunders out early; this is exactly the rare-rule gap). The
positive imperfect-info path is therefore a **partially-observable deep board
game** (hidden state over an army5x5a-like game that already exhibits the gap), not
poker.

### Claim B probe — Beacon is confounded for inference-synthesis (2026-06-27)

`scripts/beacon_claimB_probe.py` (Azure GPT-5.4 large). Synthesizing Beacon's
contract, full rules vs the type-revelation rule withheld:

| variant | transition gate | observation_rate | inference_rate |
|---------|------------------|------------------|----------------|
| FULL rules | 0.487 (fails, 10 iters) | 1.000 | 0.000 (infer_states crashes) |
| WITHHELD revelation | 0.443 (fails) | 1.000 | 0.000 |

**Beacon does not work as a Claim B (synthesis) vehicle:** GPT-5.4 large cannot
synthesize even Beacon's *transitions* (≈0.45, near random) with fully-specified
rules, and its `infer_states` crashes (`'list' object is not callable`, the same
shadowing bug seen on Kuhn-mini). With the transition function broken, the full-vs-
withheld inference comparison is confounded — we cannot separate "inference fails
because withheld" from "the model cannot synthesize this unusual game at all."
(Note: this is a synthesis-capability limit on a novel encoding, NOT translation-
not-inference — the rules were given. The hand-built Claim A positive is unaffected;
it never used synthesis.)

Implication for Claim B: it needs a vehicle whose **dynamics synthesize cleanly**
(so the only variable is the belief model) plus a **withholdable observation rule
independent of the dynamics**. Candidate: a familiar-dynamics game (synthesizes at
gate 1.0) overlaid with an arbitrary, non-recallable masking rule — see
RESEARCH-DIRECTION.

## Confound closure on the 0/76: richer prompting + 3× budget do NOT restore disc repair (2026-07-19)

Best-shot cells from the runbook
(`docs/superpowers/plans/2026-07-19-disc-confounds-square-ablation.md`, Task 1):
patch2d k=(3,7), incomplete arm, `--prompt-variant region --max-iters 15`,
20 seeds × {large, mini} — the most favorable treatment (120 examples, 40
failure lines, describe-the-region-first guidance + the explicit "the region
need not be a 1D threshold" de-bias) at 3× the original refine budget.
JSONs: `results/continuous_synthesis_patch2d_{large,mini}_k3_7_pv-region_it15.json`
(identical samples to the original run — same seed formula — so directly
comparable; patch1 in all 40 samples as r1=0.14 forces, patch2 in 5/20 and
6/20).

**Result: 0/40 repair.** No gate passes (max accuracy 0.9981 large / 0.9978
mini; every seed exhausted the 15-iteration cap; one large seed broke the
plant entirely at 0.518). Gate soundness held throughout — nothing wrong was
certified.

**But the artifact class MOVED — the guidance worked as prompt engineering
and still didn't buy repair.** Code inspection of all 40 (keyword
classification + hand spot-checks): the half-plane dimensional reduction of
the original run is GONE (0/40); the artifacts now explicitly reason "no 1D
threshold separates these; the trigger must be a bounded planar region" and
fit **rotated ellipses (~15/40), axis-aligned rectangles (~10/40), unions of
r=0.003 micro-discs (~5/40)**, and other bounded fits — none the true disc
(0/40 write a disc at (3,0) R=1 on the landing). The new failure class is
**evidence-hull fitting**, with two compounding errors:
1. They fit the hull of the OBSERVED freeze positions — which are the
   PRE-freeze states, a crescent hugging the disc's reachable (west)
   boundary from OUTSIDE — instead of inducing the generative boundary
   (fitted centers ≈ x 2.3, outside the patch whose west edge is at x = 2).
2. They condition on the wrong variable: only 4/40 test the landing
   (x2, y2) — the causal variable of the freeze rule; the rest gate on the
   current position (x, y).
The sample itself (3200 transitions) then refuses every wrong shape — the
~0.98–0.99 accuracies are shape errors, not arithmetic (consistent with the
original run's falsified ε-exactness alternative).

**Consequences.** (a) Paper 2 §10's "whether richer prompting, larger
iteration budgets ... restore repair is open" is now a measured negative at
the strongest joint treatment; per the runbook decision tree the ablation
pair (region-only / budget-only) is NOT needed — nothing repaired, so there
is no factor to attribute. (b) The mechanism sharpens: the failure is not
"cannot write 2D predicates" (they now write ellipses), it is induction of
the generative boundary from one-sided evidence — the contact evidence IS
only the reachable crescent, and paper 3's evidence-equivalence corollary
(THEORY.md on `claude/paper-tres-topology-4w813y`: outside evidence cannot
even pose the disc-vs-annulus question) says a hull-fit is the rational
response to it. (c) The paper-3 rung-1 datum (0/76, now +0/40 under
confound treatment) stands unconditioned.

## Square-patch ablation: the curvature explanation is FALSIFIED (2026-07-19/20)

Runbook Task 2 (`docs/superpowers/plans/2026-07-19-disc-confounds-square-
ablation.md`): patch2dsq k=(3,7), default prompt, it5, both arms, 20 seeds ×
{large, mini}. JSONs: `results/continuous_synthesis_patch2dsq_{large,mini}_
k3_7.json` (large incomplete arm first checkpointed at 14/20, then COMPLETED
by a resumed run — the resume layer's first production use).

**Control clean, premise holds on max/abs:** full arm 20/20 gate 1.000 at
0 refine iterations in BOTH sizes, per-mode blindness 0.0/0.0, play_cost
0.0 across the board — translating the square clause is as easy as the
disc's and the wall's.

**Incomplete arm: 0/40 repair** (every sample mode-containing — square
r1 = 0.185 forces p1 into all 40 samples; p2 in 5/20 + 6/20). No gate
passes (best 0.9962), all seeds at the 5-iteration cap; gate soundness
intact. So flat edges do NOT restore repair: 0/76 disc + 0/40 disc-with-
guidance + 0/40 square = 0/156 pooled across the three campaigns. **The
collapse axis is 2D-region induction itself (the conjunction), not
boundary curvature.** The resumed large seeds add the sharpest
evidence-hull instance of the campaign (seed 170000): thin strips
[1.9,2.0]x[-1,1] and [5.9,6.0]x[-1,1] — BOTH patches' west faces found,
correct y-extent, yet only the observed contact shell is modeled, on the
pre-position instead of the landing: the hull of the evidence, never the
generative box.

**The artifact classes sharpen the mechanism into a template prior:**
- *Half-plane reduction ON FLAT EVIDENCE*: dominant large class is
  `if x2 >= 2.0` — the square's west edge as a 1D threshold (7/14 large,
  3/20 mini). Dimensional reduction is shape-agnostic.
- *The INVERSE error — curving flat evidence*: several artifacts write
  DISCS on the square instrument (`hypot(x-2, y) <= 1.0` at the west-edge
  midpoint; r=0.25 discs at (2,0)/(6,0); micro-disc unions). On the disc
  instrument the models wrote half-planes; on the square they write discs.
- *Reward-anchored superstition* (mostly mini): freeze zones invented AT
  THE LODES (hypot to (-6,0) or (12,0) <= 2.0) — the prior anchors on
  salient reward landmarks, not on the failure geometry; one degenerate
  `if reward(...) > 0.0` artifact (gate 0.0022).
- One rectangle attempt with the wrong extent ([-2,4]x[-2,2], gate 0.35);
  ZERO artifacts write the true box [2,4]x[-1,1] or its max/abs form.

Net mechanism across the three campaigns: the synthesizer selects from a
small library of low-descriptive-complexity region templates (1D threshold,
radial ball, reward-landmark zone) and keeps whichever locally fits,
under-weighting the evidence's actual geometry in BOTH directions
(flattening curves, curving flats). "Dimensional reduction" (paper 2 §7.1)
was one face of this; the square run exposes the other. This is exactly the
regime the Phase-A curvature sweep (Shape families + AST/MDL program
features + evidence-dose) is built to characterize quantitatively — these
two cells are its anchor points, not its replacement.

Paper hooks (deferred to the Phase-A fold-in, one coherent edit): §7.1's
mechanism paragraph ("reduces the disc to a half-plane") generalizes to the
template-prior statement; §10's open items on prompting/budget and "other
geometries" are now BOTH measured negatives (confound entry above + this);
the abstract's "geometry-dependent" stays correct but "curvature" should
never be the stated axis.


---

## Round-2 peer review: three new scripts, and what each one settles

Added 2026-07-25 after five adversarial reviews. Each exists because a claim in the
paper rested on a number nobody had measured.

**`scripts/patch2d_dependence_50k.py`** (~40 min, resumable per knob). Settles the
dependence sign. At the 600 rollouts of `tab:patch2d`, P(both) was 0–3 counts per
knob and six of nine cells were censored zeros, so "the dependence changes sign
across the grid" was over-read from noise. Note also what could NOT be fixed by
better statistics on the same sample: r1, r2, r_union and P(both) all come from the
same rollouts, so inclusion–exclusion holds identically in the plug-in estimates and
"the bracket contains the measured value at all nine knobs" is an algebraic identity
with zero empirical content. At 50,000 rollouts the sign IS resolvable and does
change: negative at (2,6) and (3,7), **positive at (4,6)**, all three with Wilson
intervals excluding r1*r2, undecided at (4,7). So no fixed correction factor can
replace the bracket.

**`scripts/fence_separation_census.py`** (~12 min). Settles three things about
Prop 7. (i) The 1D fences are not where the proposition put them: the fence is the
model's refuted PREDICTION, overshooting the wall by 0.17–0.58 against eps = 0.25,
so the band misses x_wall in 4 of 5 cart episodes while the count is still exactly 1.
(ii) What explains the 1 is SEPARATION — a point beyond the boundary disconnects the
agent from the lure — and separation has a signature the covering story lacks:
eps-invariance. Measured bit-identical over a 20x range on the pendulum (0.1 →
0.005) and from 0.25 to 0.05 on the cart, breaking only at 0.01, where the unfenced
strip grows wide enough for a real contact no imagined segment crosses. (iii) In 2D
the per-episode picture is not the mean: medians 1/1/2 against means 1.05/2.65/4.25,
maxima 2/28/28, but at most **2/5/6 DISTINCT** fence positions — so the bounded
quantity (new-coverage fences) is a quarter of the 24-fence two-patch packing budget,
and the raw counts are duplicates. And 0/20, 2/20, **7/20** episodes end pinned at
blind-level return: the far-knob degradation is lock-in, not a longer transient. The
probed arc is now measured directly (median 0%/0%/87%) instead of being inferred from
count-over-budget, which was circular.

**`scripts/sample_stream_census.py`** (instant, in CI). Recounts every campaign at
rollout-seed-block level, because `collect_transitions` draws `Random(seed + i)` with
`seed = 10_000*(index + 1 + offset)` and nothing else — not the instrument, knob,
patch shape or prompt variant. So the PatchField2D campaign's 203 cells rest on 20
blocks, the guided ablation reuses the disc cells' samples byte for byte, and the
honest bounds are cluster-level: all-repair lower bounds 0.851 (cart, 22 blocks) and
0.898 (pendulum, 34 blocks), and the 2D negative result's upper bound is **0.161**
per sample rather than "never".

Two rewritten scripts worth noting: `gate_density_step_t.py` now delivers a genuine
POINTWISE density infimum via a Minkowski erosion with P-shaped cells (oracle-tested:
zero inclusion violations in 4800 trials, and the bound sits below a separately
measured density by exactly the predicted (1-lambda)^2), and it runs the certificate
itself so no rho or bound is hand-computed. `truth_plan_invariance_certificate.py`
now runs the harness's 20 episodes per knob (was 2) and reports argmax uniqueness as
a DIAGNOSTIC — it fails, ties occur because the reward saturates to 1.0 in floating
point, and the certificate rests instead on the knob-independent enumeration order.


---

## Round 3 (same day): the certificate recovered by changing the argument

`scripts/gate_partition_certificate.py` + `scripts/gate_partition_validation.py`.

Three of the four peer-review corrections to the coverage certificate landed on the
same object: a geometric factor in the PACKING instantiation (covering-vs-packing
direction; the ball's intersection with U; the corner factor's failure to be
shear-invariant). Each fix made the bound worse — 1.57 → 2.93 → 2.97 — and that was
the honest direction, but the losses are artifacts of the ARGUMENT. A packing bound
pays for the covering number twice, once in K and once in the ball mass, and both
payments are geometry that has to be estimated. That is precisely where we kept going
wrong.

**A partition bound pays neither.** Partition U into K cells of diameter <= rho; the
failure probability is sum_i (1-q_i)^M. No density constant, no covering number, no
ball-boundary intersection appears anywhere.

**(a) EXACT, no Monte Carlo.** The step-1 law is uniform on a SHEARED box, so in
y = x - dt*v it is uniform on a box and equal sub-boxes have probability exactly 1/K.
The shear costs one thing: the net radius in the original metric,
rho = max(Delta_y + dt*Delta_v, Delta_v, Delta_a). At M = N = 40 the largest
admissible partition is K = 8 (8*(7/8)^40 = 0.0383 <= delta; 9*(8/9)^40 = 0.0809 does
not), the optimum is (n_y, n_v, n_a) = (2, 1, 4), and

    rho = 0.600,  sup_U |f - f_hat| <= **1.534**   (against 2.969 by packing)

What pins rho: n_v = 1, i.e. the WHOLE reachable velocity range in one cell. At forty
independent samples the certificate cannot resolve velocity — a fact about the gate.

**(b) All steps, dependence handled by direct measurement.** The partition needs only
per-cell hitting probabilities, so use p_C = P(one rollout misses C), measured, with
P(C unhit) = p_C^N exact by rollout i.i.d.-ness. A rollout gets 80 chances at U rather
than 1, worth about SIX effective independent samples after the correlation between
consecutive steps: K grows 8 → 36 and, at 20k MC rollouts with Hoeffding (worst
p_C = 0.800, UB 0.814, 36*0.814^40 = 0.0096 <= delta/2),

    rho = 0.363,  sup_U |f - f_hat| <= **0.933**

So the readings finally line up for the right reasons: 2.969 (packing) > 1.534 (exact
partition, independent samples) > 0.933 (dependence handled) > 0.785 (the retired
all-steps-independent promise). Handling the dependence is worth 1.6x — not the 2% we
once claimed from a broken grid, and not the 4x the optimistic reading suggested.

**And the excluded Lipschitz class widens from L <= 1.80 to L <= 5.77** (4.5x the
plant's own 1.27), because eps + 2*L*rho grows with L and rho fell by 3.2x. "No smooth
pair can carry the wall's error past this gate" now covers a broad class.

**Tightness, measured against the certificate's OWN partition.** 400 independent
gates: the K = 8 exact partition is covered 385/400, a measured failure of 0.0375
against the bound's 0.0383 — **tight to 2%**, as it must be, since the per-cell
probability is an equality and only the union bound gives anything away. The K = 36
all-steps partition is covered 400/400, failure CI [0, 0.0095] against a bound of
0.0096. The validation READS the partition from the certificate's output instead of
re-implementing it: the previous generation of this pair shared a grid bug and so
validated the bug.

CI re-derives part (a) on every push with `--part-a-only`, which VERIFIES against the
versioned JSON and never writes. (An earlier version of that CI step ran the script in
a degraded mode and clobbered part (b)'s result — a reminder that a "cheap CI variant"
of a script that writes results is a footgun.)
