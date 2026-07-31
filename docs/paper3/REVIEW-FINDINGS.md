# Paper 3 — open review findings

Five independent adversarial reviews of the T-campaign (T1–T8, the claim
contract, and the derived constants) returned **63 defects**. This file is the
work ledger for them; it is not paper content. Each entry names the file, what
is wrong, and the corrected statement the reviewer verified. Fixed items move
to `CAMPAIGN-LOG.md` with the correction recorded.

## The pattern that generates most of them

The defects are not a spray of arithmetic slips. **Forty of the 63 are one
error made repeatedly: a measured number was put where a logical direction was
required.** Six recognisable shapes:

1. **An inequality used in the wrong direction.** A necessary condition treated
   as sufficient (T3 isotropy, T3 corridor), `inf|J|` where `sup|J|` belongs
   (Lemma J's corollary), a lower bound placed on an upper bound (T(γ)), the
   maximum of a density substituted into a lower bound (ρ(π)).
2. **A tautology reported as a validation.** `T_ratio` is *defined* as
   `d/(R·ρ·γ)`, so `slope(T)+1 ≡ slope(d)`; the "agreement" of 1.64 with 1.72
   is a grid change. `c₁ := min d/γ²` makes `d ≥ c₁γ²` true by construction on
   the grid and a coin flip off it (violated on 3 of 5 fresh seed blocks).
3. **A sample statistic used as a bound.** A median (k ≈ 9) used as a horizon
   guarantee when p90 is 13–16; quantiles used as suprema; the *min* of a
   factor, not the median, binds a product.
4. **A constant pinned to a decimal expansion.** Lemma I's x₀ = 1.77809, where
   the inequality *fails* by 2.3e-6 — now the rational 7/4 with a Taylor
   existence argument, and the audit gained `endpoint` semantics plus exact
   rational comparison so this class cannot recur.
5. **A proof-of-a-superset presented as a proof.** T8(b) refutes the bound over
   step-bounded polylines, a strict superset of dynamically feasible plans; its
   offset witness needs ‖Δv‖ ≈ 13.7 in one step against a plant limit of 0.59.
6. **A hypothesis living only in the proof, or only in the code.** Lemma D⁺'s
   (H) is checked per sample but absent from the statement; Lemma B is false
   without Δθ_max ≤ π and the validator silently clamps to a formula that
   appears in no lemma.

Two structural aggravators, both worth fixing before the individual items:

- **The guard tests cannot see these errors.** `test_t3_..._quadratic` allows a
  20% fudge and only at two gaps; `test_t3_isotropy_bound_..._is_valid` asserts
  `bound ≤ measured·1.35`, so it passes when the "bound" exceeds the quantity it
  bounds by a third. A guard with a fudge factor guards nothing.
- **Numbers with no committed artifact.** Roughly 25 load-bearing values (R′,
  the |Z_t| table, the corridor table, f(0), the steering derivatives, the
  failure census, L_v's K=100 estimate, the margin-0.3 counts) appear in prose
  with no script and no `results/*.json`. `f(0)` does not reproduce at the
  obvious bandwidth and its estimator is unrecorded — the same class the
  constants emitter was built to close, one level up.

## T3 chain — 14 findings, 7 severe

| # | file | defect | corrected statement |
|---|---|---|---|
| 1 | THEORY 2421, main 1809 | isotropy bound on R′ uses `arcsin(r_out/r)` (a tangent-cone, upper-bound quantity) as a per-radius floor; the true half-angle β(ρ) **vanishes** at both window ends, and 37% of the mass in [7,17] is below the claimed floor. Labelled PROVED. | either the exact identity `P = E[β(|Z|)/π]` (needs the whole radial law, not one scalar) or the valid window form: **R′ ≥ 0.012**, 1.8× loose, not 1.1× |
| 2 | THEORY 2299 | `T ≥ 2.2γ·f(0)`: the corridor condition is *necessary*, so it bounds T from **above**; the claimed lower bound exceeds measured T by 2.1–4.3× and exceeds 1 from γ = 0.4 | `T(γ) ≤ P(\|v_tan\| ≤ r_out γ/(2k dt))`; c₁ stays **fitted**, the "derived constant" heading is unearned (2.4 derived vs 0.4695 fitted) |
| 3 | THEORY 2378 | ρ(π) ≥ 0.94 drops Lemma D's `P(root)` (measured 0.0156) *and* compares a sub-density against a per-arrival density; the two errors cancel to ~30× | `ρ_sub(π) ≥ 0.0133/rad`, per-arrival `ρ(π) ≥ 0.44`, 2.3× loose, label **measured** |
| 4 | THEORY 2441 | "the residue IS the instrument's rarity r": the quantity named is 0.20, the one equal to r(0) is R = 0.0302 (6.6×), and R is the factor the chain *superseded* | delete the identification; the residue is the radial law of `\|Z_{h−k}\|`, which is not r |
| 5 | THEORY 2276 | γ² bound is calibrated at γ = 0.6 and **violated on 3 of 5 fresh 40k blocks** there | take the constant below the sampling interval (≈ 0.0142) or state it as a property of the committed sample |
| 6 | THEORY 2352 | f(0): bound is on the **signed** density, use and measurement on the folded one (factor 2); and the arcsine step's conditional uniformity of a_t is false at ≈7σ | state the convention per row; label the arcsine step **consistent-with** and name the bias |
| 7 | THEORY 2210 | Lemma J's corollary multiplies by `inf\|J\|` (which is 0) where it must divide by `sup\|J\|` — and contradicts Lemma D two pages later | `d ≥ ¼·area/39.5·P(prefix)` |
| 8 | THEORY 2256 | "predicts γ^1.64 vs measured γ^1.72 — it closes" is an identity plus a grid change; "two independent estimates of T agree to 10%" is a one-sided 5–11% bias | the only non-tautological check is `T_counts` vs `T_ratio`, which shows a systematic gap of known sign |
| 9 | THEORY 2240 | `∫ρ ≈ ρ(π)γ` substitutes the **maximum** of ρ into a lower bound | needs `inf_{\|θ−π\|≤γ/2} ρ` |
| 10 | THEORY 2405 | horizon term "disappears by construction" on a **median** k ≈ 9 (p90 = 13–16); plus an off-by-one (8 steps left, not 9) | the deadline reduces the term by 1.4× and leaves a residue ≈ 0.1 |
| 11 | THEORY 1926 | "550 000 pathwise comparisons" — only 3 582 are informative units (154× inflation), the exact failure the section warns about | "0 violations over 3 582 direct-entry units (550 000 CRN rollout pairs)" |
| 12 | THEORY 1945 | "exactly zero in every pair where f rises" — one pair is a drop; 3 of 6 zeros are ties in a noisy estimate; 16.9×/25.5×/46.8× mix Wilson bounds with point estimates | scope to the sample; CI-consistent separation ≈ 26×, not 46.8× |
| 13 | — | the four newest commits added ~25 numbers with no script and no artifact | emit them |
| 14 | THEORY 2237, 2430, 591 | Lemma J's verification pairs series offset by one lag (0.186 vs 0.094); L is random (11.50–12.51) so [7,17] is start-dependent; a stale "the route is a local CLT" contradicts the later removal | mechanical |

## T5 — 9 findings, several severe

T5-F silently drops the Z₁ factor (the bound carries no κ; K = 10 violates
T5-T's own side condition σ₁²/m < 3.606, and the floor reappears one coordinate
over); T5-F is a **single-time** bound attributed to r(n) (needs ×h = 80, so
vacuous until n = 52); the superseded 0.12-floor and Berry–Esseen blocks are
still asserted 40 lines from the Lemma K that contradicts them; **Lemma E is
false as stated** (atom at the origin); T5-T assumes e = e₁ against Lemma F's
e ∈ span(e₁,e₂); **min ρ, not median, binds for a product** (rate ≤ 0.474, not
0.418); L random ⇒ r_out/L ≤ 0.4348, not 0.4167; 0.04/0.3 = 0.133, not 0.12;
Lemma E's "sharp" is only order-sharp (factor 9.7).

The T5-F per-dimension rate is now **0.9104**, not 0.9057 — a consequence of
making Lemma I's x₀ the rational 7/4 rather than a decimal at the first
crossing. The rate is one of the two constants the emitter labels *numerically
optimised* rather than closed-form; the rest are symbolic.

## T1 / T4 / T7 / T8 — 14 findings

Most severe: **the T7 estimator is not `rank H₁(K,L)`** — the stated inequality
is inverted, and the hypothesis that would make them agree (`H₁(K) = 0`) is
false on the committed cells (β₁(K) = 114–166 at every scale) and is never
computed. A 24-point circle plus its centre exhibits the gap: union-find 0,
brute-force relative rank 1. So the headline 20/20 vs 9/20 and the "at γ = 0 it
is vacuously zero" reading are statements about the **free-merge estimator**, a
computable lower bound, not about relative homology. Relabel throughout.

Then: T8(b)'s witnesses are not dynamically feasible (see pattern 5); **Lemma B
is false without Δθ_max ≤ π** and the validator uses an unstated clamped
formula (4 committed rows have Δθ_max > π); the death/ρ̄ interval is misquoted
([1.674, 1.816], not [1.70, 1.82]) and the radial-thickness band does not cover
its maximum; `d_bottleneck ≥ 0.317` is false (0.310) and no committed
computation supports either; Lemma D⁺'s (H) is proof-only, with 29/80 rows where
it is a genuine assumption and 4 where neither regime applies; "57/57 winding
bars" is 21 rows wider than the theorem and winding is never computed;
**a sublinear measured slope does not refute a linear bound** — `P ≤ 0.38ε`
holds on the whole measured range; the R5 interleaving map is defined two
incompatible ways; the margin-0.3 attribution has no artifact; the stated radial
range [3.5, 3.8] contradicts the section's own data (r_max = 4.94) and T7's
shells ([4.83, 5.00]); the Hölder corollary `1033√γ` is **vacuous for every
γ ≥ 9.4e-7**, i.e. every measured gap; Lemma P applies a real-valued winding
functional to an 𝔽₂ module (repairable over 𝔽₂ via integral lifts, and the
conclusion survives only because w(z₀) is *odd*).

## T2 — 4 findings

The fixed-point closure condition is dimensionally wrong (`p(δ)·2·gain·dt < δ`)
and diverges on the measured p(0.05) = 0.10; "telescopes to ONE number" is
asserted on ±60% evidence; the tail's extreme is −13.667, not +11.65. The unit
error in A (a slope used as a value) and the false "play_cost ≤ 1 holds
trivially" are **already fixed**.

## Claim contract — 8 findings

Four headings carry no scope of their own; `audit_paper_claims.py` reports 50
errors on paper 3 with no paper-3 baseline; several load-bearing measurements
have no committed script or JSON; the drag-cap test runs 60×150, not the
documented 400×200.

## Fixed so far

| # | what changed | verified by |
|---|---|---|
| pattern 4 | Lemma I's x₀ is the rational **7/4** with a Taylor existence argument, not the decimal 1.77809 (which fails the inequality by 2.3e-6). Downstream: min q 0.7782 → 0.7842, T5-F rate 0.9057 → **0.9104**. | `audit_paper3_numbers.py` gained exact-rational comparison and `endpoint` semantics |
| T3 #1 | the tangent-cone half-angle is replaced by the exact law-of-cosines β and a **partition sum** over the annulus — each summand bounds a disjoint event, and the sum converges upward to `E[β/π]`. Ladder: 0, 0, 0.0039, 0.0082, 0.0109, 0.0124, 0.0131, 0.0135, 0.0137 at m = 1…256, exact 0.0138. **R′ ≥ 0.013 PROVED** (was an invalid 0.019), 1.6× loose, and minimised over the attainable L ∈ [11.500, 12.508] rather than its midpoint. 48.9% of the annulus mass violates the old floor. | `scripts/t3_isotropy_window_bound.py` → `results/t3_isotropy_window_bound.json`, emitted and audited |
| T3 #2 | `T ≥ 2.2γ·f(0)` → **`T(γ) ≤ P(|v_tan| ≤ r_out γ/(2k dt))`**. The corridor condition is necessary, so it bounds T above; the lower-bound form exceeds measured T by 2–4× and exceeds 1 from γ = 0.4. c₁ = 0.4695 is stated as **fitted**, with the kinematic constant 2.4 named as the factor-5 discrepancy. | reviewer measurement, restated in both documents |
| T3 #4 | the "residue IS the rarity r" identification is deleted; the R = r(0) identity is kept but scoped to the *superseded* ring-free factor, with the 1.4× gap to R′ and the γ = 0-only caveat stated | — |
| T3 #7 | Lemma J's corollary now **divides by sup\|J\|** (`d ≥ ¼·area/39.5·P(prefix)`), with a note that `inf\|J\| = 0` makes the old form vacuous as well as backwards, and that this matches Lemma D's orientation | symbolic |
| T3 #8, #9 | the γ^1.64-vs-γ^1.72 "agreement" is labelled the identity it is (slope(T_ratio) + 1 ≡ slope(d), 0.6396 + 1 = 1.6396); the ratio-vs-count gap is stated as a one-sided 5–11% bias and traced to substituting ρ(π), the **maximum** of the angular density, into a lower bound | committed JSON |
| T3 #10 | the horizon term "shrinks by 1.4× but does not vanish": k ≈ 9 is the **median** (p90 = 13–16), so a residue ≈ P(crossing > k) ≈ 0.1 remains; the 8-vs-9-step off-by-one is recorded | reviewer measurement |
| T3 #11 | "550 000 pathwise comparisons" → **3 582 informative units** (the direct entries at the smaller gap are the only seeds that can falsify the inclusion), per-pair counts given, and the first pair's 0 noted as *untested* | `results/t3_funnel_bound.json` |
| aggravator 1 | the isotropy guard's `1.35` fudge is gone — a bound allowed to exceed the quantity it bounds by 35% is why the invalid version survived | `tests/test_t3_funnel_bound.py`, 25 passed |
| aggravator 2 | the audit now fails when a `MUST_APPEAR` constant vanishes from both documents (printed-form drift previously turned into a silent pass), and gained `percent` semantics | `audit_paper3_numbers.py` |

| T3 #3 | ρ(π): both dropped factors restored — `P(root) = 0.0156` (measured over 900 configurations) and the sub-density/per-arrival distinction (they differ by R ≈ 0.030, which is why the two errors cancelled). **ρ_sub(π) ≥ 0.0133/rad, per-arrival ρ(π) ≥ 0.44** against measured 1.0167, 2.3× loose, label **measured** | both documents |
| T3 #5 | the γ² constant is now **0.0136**, the pooled Wilson 95% lower limit at the binding gap over disjoint seed blocks, replacing 0.01455 (the sample's own min d/γ², violated in 3 of 5 fresh blocks at γ = 0.6). The calibration also splits the penalty into shape vs statistical **power** per gap: at 20k/block the binding gap was 0.05 purely from power, and raising the two smallest gaps to 1.1M rollouts moved it back to 0.6, whose power penalty (0.0012) is the smallest — so the shape binds, as claimed | `scripts/t3_quadratic_constant.py` → `results/t3_quadratic_constant.json`, emitted and audited; guard test now has **no fudge factor**, tests three gaps, and uses a seed base it was not calibrated on |
| T3 #6 | f(0): the signed/folded convention is stated with every number (signed bound 0.384 vs measured 0.543; folded 0.769 vs 1.087 — both 1.4× loose, not the 3× that came from mixing them), and the arcsine step is downgraded to **consistent-with** with the 7σ conditional-uniformity bias named and quantified | both documents |
| T4 #8 | "a linear bound is refuted at the measured scale" → **it is not**: sublinear growth is compatible with a linear upper bound, and `P ≤ 0.38·ε` holds across the measured range. Restated as what the data actually show, with the extrapolation labelled as one and the 19/4000 standard error given | both documents |
| T4 #12 | the Hölder corollary `1033·√γ` is labelled **vacuous for every γ ≥ 9.4·10⁻⁷**, i.e. every runnable gap; the content is stated to be the finite/explicit/uniform structure, not the number | both documents |

| T3 #14 | Lemma J's verification: the two derivative series are labelled as offset by one lag (0.186 = K·W(2), 0.094 = K·W(1)) rather than presented as agreeing; the stale "the route is a LOCAL LIMIT THEOREM" summary is replaced by the fact that Lemma J removes the exponential outright | symbolic |
| T7 #1 | **Prop R2's inequality is un-inverted**: `rank ker(H₀(L)→H₀(K)) ≤ rank H₁(K,L)`, equality iff `H₁(K) = im H₁(L)`. The estimator computes the kernel rank, i.e. the LOWER bound. The equality hypothesis is measured false on the committed cell (β₁(K) = 125/166/164/114 vs β₁(L) = 119/164/162/113 at s = 0.20–0.50), and the 24-point-circle-plus-centre exhibit is recorded. Every reported figure (20/20 vs 9/20, the γ = 0 non-firing, Prop R4's limit) is relabelled a statement about the **free-merge estimator** | both documents |
| T7 #5 | `d_bottleneck ≥ 0.317` → **= 0.310** with the matching cost derived ((1.8 − 1.1798)/2), brute-force confirmed | committed test instance |
| T8 #2 | the refutation is **scoped to step-bounded polygonal paths**, with the superset relation to feasible plans stated, the two offset witnesses' infeasibility quantified (‖Δv‖ ≈ 13.7 needed against a plant limit of 0.59), and the "property of the search, not of the geometry" reading marked UNEARNED at o = 1.5 | both documents |
| T1 #3 | **Lemma B gains its standing hypothesis Δθ_max ≤ π**, with the failure spelled out (no winding class at any scale; the consecutive-neighbours cycle has winding 0, not 1) and the validator's clamped form `2r·sin(min(Δθ_max, π)/2)` stated in the lemma instead of living only in the code. 4 committed rows have Δθ_max > π | `results/t1_death_sandwich.json` |
| T1 #4 | death/ρ̄ is **[1.674, 1.816]**, not [1.70, 1.82]; the radial-thickness band [1.661, 1.803] is stated to account for the lower part of the spread but not its maximum, and "exactly" is gone | `results/t1_bar_geometry.json`, 15 bars |
| T1 #7 | "57/57 winding bars" → **36/36 where Lemma P applies** (nonempty window, r₀ = 1), with the other 21 labelled measurement and "winding is inferred from the birth location, not computed" | `results/t1_death_sandwich.json` |
| T1 #11 | the setting's radial range is **[3.5, 5.0]** with the two-shell structure named, not [3.5, 3.8] which contradicted r_max = 4.937 | same |

**A guard-design finding, discovered while hardening the guards.** Removing the
γ² guard's fudge factor made it fail on a fresh seed block: 86/20000 = 0.00430
against the bound's 0.004896, a 2σ-low block. The bound is a claim about the
true d, but at the binding gap its slack is 8% while a 20 000-rollout block's
standard error is 10% of d — so asserting the point estimate tests the sample,
not the claim, and fails about half the time whatever the constant. The guard
now asserts against the sample's Wilson **upper** limit: a significant
violation still fails, a 2σ fluctuation does not. That is not a fudge factor
(which hides a fixed relative error at any n); it is the only statement a block
that size can make.

| T5 (rate) | the sharp rate is corrected for **L random**: a bound needs the largest ratio, so `r_out/L_min = 5/11.511 = 0.4344`, not `5/12 = 0.4167` (the mean-start value). The emitter now derives `L_min`, `L_max` and both rates from the start box's corners, and the audit gained an `"upper"` kind — a constant of an upper bound may only round UP. That kind immediately caught a hand-derived 0.4348 taken from a sampled minimum instead of the exact corner | emitted and audited |
| T5 (ρ) | **min ρ, not median, binds a product**: the per-dimension rate is ≤ 0.474 at ρ = 2.34, against 0.418 at the median; the honest cost against the isotropic 0.4167 is 5.7e-2, not 3e-3 | both documents |
| T5 (floor) | the 0.12-floor block is marked **SUPERSEDED** in place, with the arithmetic corrected (0.04/0.3 = 0.133, not 0.12) and a note that it must not be quoted beside Lemma K, which contradicts it. The "residue is two things" summary drops the floor, since Lemma K and T5-F each remove it | both documents |
| T5 (min q) | `0.7782` → `0.784`, the value at the rational x₀ = 7/4 | audited |
| T1 #13 | Lemma P states its coefficient field (**𝔽₂**, matching `tda.rips_persistence`'s symmetric-difference reduction) and supplies the lift argument w mod 2 needs, with the note that the step works only because w(z₀) is **odd** | symbolic |
| T1 #6 | Lemma D⁺ states its two standing hypotheses (Δθ_max < π and **(H) Δθ₂ ≤ θ*/2**) instead of keeping (H) in the proof, with (H)'s automaticity in regime (i) proved and the coverage given: 29/80 rows are regime (ii) only, 4/80 satisfy neither and carry only the cone bound | `results/t1_death_sandwich.json` |
| T2 (tail) | the A_t table gains a **min** column: the larger extreme at γ = 0.3 is **−13.67**, not +11.65, and since the bound controls \|A_t\| quoting only the positive side understates it by 17% | `results/t2_percontact_identity.json` |
| T2 (closure) | the fixed-point closure condition is corrected to **p(δ)·2·gain·dt < δ** (a displacement against a displacement; "< 1" was dimensionally wrong and vacuously satisfied), with `L_v ≤ A·δ/(δ − p(δ)·2·gain·dt)` and the δ-dependence spelled out: it closes at δ = 0.6 and **fails at δ = 0.05** on the measured p, so there is no uniform-in-δ fixed point and the δ → 0 limit diverges | both documents |
| T2 (telescoping) | "telescopes to ONE number" → **dominated by** one number, with the ±60% spread (ratios 0.81–1.66 over 9 episodes) stated as the claim's error bar and the display marked an approximation; the 9/9 stickiness is labelled a censored zero with its interval | both documents |
| T5-F (scope) | the theorem is restated as a **single-step** bound: `P(cone at a fixed step) ≤ 2·0.9104ⁿ`, with `r(n) ≤ 160·0.9104ⁿ` after the union over h = 80, **vacuous below n ≈ 55**. The dropped **Z₁ factor is flagged in the statement itself** (the product controls the Π_{i≥2} side; the upper-side factor is asserted, which is why no κ appears), together with K = 10 violating T5-T's side condition σ₁²/m < 3.606 — it is named as open rather than carried silently | both documents |
| T5 (Lemma E) | the lemma gains **P(Z = 0) = 0** as a hypothesis, with the demonstration that it is necessary (on {Z = 0} the event holds while the proof's |S| ≤ 2/κ² fails; Z ≡ 0 is a counterexample to the lemma as previously stated) and the note that the instrument satisfies it. "Sharp" is downgraded to **order-sharp** with the constant's factor ≈ 9.7 named | symbolic |
| T5-T | the **e = e₁ hypothesis is stated**, together with the fact that Lemma F supplies only e ∈ span(e₁,e₂), the cost of the general case, and the exchangeability that licenses rotating into e = e₁ — instead of chaining the two as if they matched | symbolic |
| provenance | THEORY.md gained a **Provenance of the numbers** header distinguishing constants (emitted + audited in CI, never transcribed) from the ~10 load-bearing measurements with no committed script or JSON, each named as an *unrecorded run* | — |

## Emitting the unrecorded measurements (aggravator 2) — done, and it changed five things

Four emitters now cover every load-bearing measurement that had no script:
`t3_unrecorded_measurements.py`, `t2_unrecorded_measurements.py`,
`t2_drag_cap_and_switch_rate.py`, `t7_margin_variant_betti.py`, each resumable
per cell, with `tests/test_unrecorded_measurements.py` guarding the structural
properties (no fudge factors: confidence limits or exact relations only).

**What reproduced exactly** — so the transcription was mostly faithful:
R = 0.03020; the |Z_t| medians 1.174/2.58/3.91/4.595; the channel-arrival
counts 594/1184/2332/3352; the failure census at γ = 0.2 in all four terms
(0.202 entered / 0.527 froze / 0.0135 out / 0.258 horizon); the drag cap's
worst 1.9956 at 400×200; crossing median 8–9 and p90 13–14; ρ(π) ≈ 1.03; the
steering derivative's median/p90/max 0.388/0.540/0.572 against the recorded
0.362/0.532/0.5865; P(root) ≈ 0.009 against 0.0156.

**What emitting changed, which is why it had to be done:**

| what | was | is |
|---|---|---|
| **L_v** | `−0.015 ± 0.078` and `+0.462 ± 0.078`, ratio `0.78 ± 0.13`, "consistent with Lipschitz scaling" | **does not reproduce.** Under CRN pairing at K = 100, `E[A_t \| s_t, C_t]` is statistically zero at both available separations (+0.003 ± 0.007 at ‖Δv‖ = 0.001, −0.006 ± 0.007 at 0.459), and the implied ratio swings 5.7/17.5/3.2 across K. A *censored* measurement. **The `pc ≤ 0.18` bound resting on it is withdrawn** from both documents |
| **p(δ), the switch rate** | `p(0.05) = 0.10`, quoted as a single "p ≈ 0.5", and (per review) the fixed point therefore fails at small δ | **p(0.05) = 0.027**, and the curve closes at **every** measured δ from 0.02 to 0.8, with the multiplier in [1.25, 1.66]. So the fixed point IS available and roughly uniform — my own earlier correction, which said it fails at δ = 0.05, was wrong and is fixed. The dimensional correction (`p·2·gain·dt < δ`, not `< 1`) stands |
| **the corridor's "non-freeze fraction"** | one column, compared against the criterion | **two different quantities**: `1 − P(froze \| arrival)` = 0.288/0.473/0.614/0.698 (what the criterion is compared against) and `P(entered \| arrival)` = 0.114/0.202/0.280/0.313. Both emitted and named |
| **ρ(π)'s substitution cost** | "overstates by 8% at γ = 0.6" | derived from the emitted profile per gap rather than by hand; the infimum over the channel, which is what a lower bound needs, is materially below the peak |
| **the steering derivative's estimand** | median/p90 over "115 steerable paths" | the filter (arrival-step-preserving pairs — the only place θ is differentiable) is now **recorded, not just applied**. The excluded jumps run to 4.55 against a differentiable sup of 0.572, and a root at a jump has no derivative for Lemma D to divide by |
| **ρ(π)'s bound** | ≥ 0.44 per arrival, 2.3× loose | **≥ 0.26**, 4.0× loose, from the emitted P(root) = 0.0089 and the observed sup 0.572 |
| **the margin-0.3 variant** | "repairs gap 0 (5/5) but restores the bridge at γ = 0.6 (5/5)" — no artifact | confirmed **5/5 and 0/5**, and the mechanism is sharper: at margin 0.3 it censors **0 edges** on average (against ~2 000 at margin 0.0), so it degenerates to plain Rips and inherits its answer |
| **the T2 counts** | 106/106, 51–71/106, 101/106, 0/30, 9/9 | **278/278, 104/278, 261/278, 0/18, 18/18** — same conclusions, real n, with Wilson intervals on the censored zeros. The worst replanning-link violation is A_t = +11.65 against a gap of +4.88, not +2.62 against +0.97 |

## T5-F's Z₁ factor — repaired (Theorem T5-F′)

The severest T5 finding. The scheme is
`P(cone|B) ≤ E[e^{λγ²Z₁²}|B]·Π_{i≥2}E[e^{−λZ_i²}|B]`, and T5-F's display
controlled only the product — which is why no κ appeared in its rate, a tell
that the cone's geometry had dropped out of a bound about the cone. Three
things had to be established, all in `scripts/t5f_z1_factor.py` →
`results/t5f_z1_factor.json`:

1. **The side condition, derived rather than quoted.** The Hoeffding form
   `E[e^{tZ₁²}|B] ≤ (1−2tσ₁²)^{−1/2}` needs `2tσ₁² < 1`, i.e.
   `σ₁²/m < K_max = 1/(cγ²)` = **3.606** (nominal L) / **3.258** (L_min).
   T5-F's `K = 10` violates it — confirmed.
2. **The truncation event, certified rather than counted or sampled.**
   Exchangeability alone gives `1/K ≈ 0.29`, a floor *worse* than the 0.12
   being removed. The repair: conditionally on the norms, `σ₁² = Σ_s A_s a_{s,1}²`
   is a sum of **independent** terms with conditional mean **exactly m**
   (within-step exchangeability gives `E[a_{s,1}²|‖a_s‖] = ‖a_s‖²/n`), each in
   `[0, b_s]`. Hoeffding applies with no further hypothesis, and on
   `{‖a_s‖² ≥ νn ∀s}` the exponent is **n-free**: `2(K−1)²ν²E_eff` with
   `E_eff = S²/Σw_s⁴ = 59.6`. Off that event, `h·e^{−nI(ν)}` with I the exact
   Chernoff rate for `‖a‖²`'s lower tail. Monte Carlo cannot certify a floor
   this small — 400 draws at n = 8 see the event zero times even at K = 1.5 —
   which is why it is derived.
3. **The assembly**, optimising (z, K, α) subject to K < K_max and then
   choosing ν so the norm tail stays subdominant:

   **P(cone at a fixed step) ≤ 1.15·10⁻¹³ + 11.7·0.9245ⁿ + 80·0.8920ⁿ**

   (nominal L; at L_min, K = 3.1, floor 7.4·10⁻¹⁰, rate 0.9285.)

**Verdict: a repair, not a refutation — with one claim withdrawn.** The
exponential survives. Carrying Z₁ costs a rate of 0.9245 instead of 0.9104
and a constant 11.7 instead of 2, and κ returns through γ² in both the Z₁
factor and K_max. What does not survive is **floor-free**, and that is now a
theorem rather than a gap: outside the truncation the exponential moment is
finite, inside it `E[(1 − cγ²σ₁²/m)^{−1/2}]` is **infinite**, so no parameter
choice makes the untruncated expectation converge. The floor is irremovable
within this scheme — it is just 10⁻¹³ rather than 0.12.

Guarded by `test_t5f_prime_respects_its_own_side_condition` (which fails if
the rate ever comes out *better* than 0.9104, i.e. if the factor is dropped
again) and `test_t5f_truncation_beats_the_counting_bound_by_orders`.

Still open, in the order the "Order of work" section sets:

1. **T3 #12** — the funnel-profile's "exactly zero" claims rest on the sign of
   small count differences; three of six zeros are ties in a noisy estimate,
   one "rise" pair is a drop, and the 16.9×/25.5×/46.8× separations mix Wilson
   bounds with point estimates.
2. **T7 #9** — the R5 interleaving map is defined two incompatible ways
   (nearest-point vs the path-matching bijection); the pair-contiguity step
   needs the stronger one.
3. **Prop R4** — the bar-length bound uses a single δ where the two shells have
   different thicknesses (0.213 and 0.167, so the bound is their sum, 0.381),
   and "set by the shells and not the sample size" sits awkwardly beside a
   realized length that grows 58% from 40 to 320 rollouts.
4. **Claim contract** — four headings carry no scope of their own;
   `audit_paper_claims.py` reports 50 errors on paper 3 with no paper-3
   baseline; and the drag-cap guard still runs 60×150 while the text quotes
   400×200 (both sizes are now emitted, so the guard can simply cite the
   artifact).

## Order of work

1. The two aggravators — remove the fudge factors from the guards, and emit the
   ~25 unbacked numbers. Both are prerequisites: without them a fix cannot be
   verified, and every later item is re-litigated by hand.
2. The seven direction errors (T3 #1, #2, #7, #9, #10; T5-F's Z₁ factor and
   per-step attribution). These change what the paper claims, not how it is
   worded.
3. The false-as-stated lemmas (Lemma B's Δθ_max ≤ π, Lemma E's atom, Lemma D⁺'s
   (H), Lemma P's coefficient field).
4. The relabelling: the T7 estimator, T8(b)'s plan class, T4's linear bound,
   the Hölder corollary, and the twelve misquoted intervals and constants.
