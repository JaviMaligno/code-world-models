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
