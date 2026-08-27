/-
Paper 3, sixth tranche: Lemma G's analytic core (docs/paper3/THEORY.md,
"Lemma G (spherical cap bound, self-contained)").

Lemma G states, for U uniform on S^{n−1} (n ≥ 3) and κ ∈ [0, 1):
  P(⟨U, e⟩ ≥ κ) ≤ ½ (1 − κ²)^{(n−2)/2}.
Its proof reduces the probability to the marginal-density integral and then
proves ONE integral inequality — the substitution u = κ + √(1−κ²)·y, the
pointwise bound 1 − u² ≤ (1−κ²)(1−y²), and the enlargement of the y-range to
[0, 1]. That inequality is where a hand-derivation could go wrong, and it is
what this file machine-checks, generalized to any real exponent p ≥ 0
(Lemma G takes p = (n−3)/2, so p + 1/2 = (n−2)/2):

  * `lemmaG_integral_core` — ∫_κ¹ (1−u²)^p du ≤
                             (1−κ²)^{p+1/2} · ∫_0¹ (1−y²)^p dy.

What is NOT formalized (noted per the ledger's convention): the reduction
from the sphere measure to the 1-D marginal (the density c_n(1−u²)^{(n−3)/2}
and P(U₁ ≥ 0) = ½ by symmetry) — standard measure theory whose assembly in
mathlib is the genuinely probabilistic work the triage records; and the
downstream Theorem T5-I, which additionally needs spherical symmetry of
independent sums. The measured complement: the cap bound is verified against
the exact cap integral at n = 3…30 (`scripts/t5_isotropic_bound.py`).
-/
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Continuity
import Mathlib.Analysis.SpecialFunctions.Sqrt
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Bounds
import Mathlib.Analysis.SpecialFunctions.Trigonometric.InverseDeriv
import Mathlib.MeasureTheory.Group.Measure
import Mathlib.MeasureTheory.Measure.Prod
import Mathlib.Tactic.Linarith

namespace Paper3Ring

open intervalIntegral
open Real (pi_pos pi_ne_zero)
open scoped Real

/-- **Lemma G's analytic core.** For any exponent `p ≥ 0` and `κ ∈ [0, 1)`,
`∫_κ¹ (1−u²)^p du ≤ (1−κ²)^{p+1/2} · ∫_0¹ (1−y²)^p dy` — the substitution
`u = κ + √(1−κ²)·y` (its Jacobian is the extra `1/2` in the exponent), the
pointwise bound `1 − u² ≤ (1−κ²)(1−y²)` on the substituted range, and the
enlargement of that range to `[0, 1]` (the integrand is nonnegative). With
`p = (n−3)/2` this is exactly the inequality Lemma G's proof runs on. -/
theorem lemmaG_integral_core {p κ : ℝ} (hp : 0 ≤ p) (hκ0 : 0 ≤ κ)
    (hκ1 : κ < 1) :
    (∫ u in κ..1, (1 - u ^ 2) ^ p)
      ≤ (1 - κ ^ 2) ^ (p + 1 / 2) * ∫ y in (0 : ℝ)..1, (1 - y ^ 2) ^ p := by
  have hκ2 : 0 < 1 - κ ^ 2 := by nlinarith
  set s := Real.sqrt (1 - κ ^ 2) with hs_def
  have hs0 : 0 < s := Real.sqrt_pos.mpr hκ2
  have hs2 : s ^ 2 = 1 - κ ^ 2 := Real.sq_sqrt hκ2.le
  set c := (1 - κ) / s with hc_def
  have hc0 : 0 ≤ c := div_nonneg (by linarith) hs0.le
  have hsc : s * c = 1 - κ := by
    rw [hc_def]
    field_simp
  have hc1 : c ≤ 1 := by
    rw [hc_def, div_le_one hs0]
    have h1 : (1 - κ) = Real.sqrt ((1 - κ) ^ 2) :=
      (Real.sqrt_sq (by linarith)).symm
    rw [h1]
    apply Real.sqrt_le_sqrt
    nlinarith
  -- the substitution
  have hsub : (∫ u in κ..1, (1 - u ^ 2) ^ p)
      = s * ∫ y in (0 : ℝ)..c, (1 - (s * y + κ) ^ 2) ^ p := by
    have h := integral_comp_mul_add (f := fun u => (1 - u ^ 2) ^ p)
      (a := 0) (b := c) (ne_of_gt hs0) κ
    simp only [mul_zero, zero_add, smul_eq_mul] at h
    rw [show s * c + κ = 1 by rw [hsc]; ring] at h
    rw [h]
    field_simp
  -- the pointwise bound on the substituted range
  have hpt : ∀ y ∈ Set.Icc (0 : ℝ) c,
      (1 - (s * y + κ) ^ 2) ^ p ≤ (1 - κ ^ 2) ^ p * (1 - y ^ 2) ^ p := by
    rintro y ⟨hy0, hyc⟩
    have hsy1 : s * y + κ ≤ 1 := by
      have h := mul_le_mul_of_nonneg_left hyc hs0.le
      linarith [hsc ▸ h]
    have hsy0 : 0 ≤ s * y + κ := by positivity
    have hbase : 0 ≤ 1 - (s * y + κ) ^ 2 := by nlinarith
    have hy1 : y ≤ 1 := le_trans hyc hc1
    have hy2 : 0 ≤ 1 - y ^ 2 := by nlinarith
    have hkey : 1 - (s * y + κ) ^ 2 ≤ (1 - κ ^ 2) * (1 - y ^ 2) := by
      nlinarith [mul_nonneg (mul_nonneg hκ0 hs0.le) hy0]
    calc (1 - (s * y + κ) ^ 2) ^ p
        ≤ ((1 - κ ^ 2) * (1 - y ^ 2)) ^ p :=
          Real.rpow_le_rpow hbase hkey hp
      _ = (1 - κ ^ 2) ^ p * (1 - y ^ 2) ^ p :=
          Real.mul_rpow hκ2.le hy2
  -- integrability of everything in sight, from continuity
  have hcont : ∀ a b : ℝ, IntervalIntegrable
      (fun y : ℝ => (1 - y ^ 2) ^ p) MeasureTheory.volume a b := by
    intro a b
    apply ContinuousOn.intervalIntegrable
    exact (Continuous.continuousOn (by fun_prop)).rpow_const
      (fun x _ => Or.inr hp)
  have hcontSub : IntervalIntegrable
      (fun y : ℝ => (1 - (s * y + κ) ^ 2) ^ p) MeasureTheory.volume 0 c := by
    apply ContinuousOn.intervalIntegrable
    exact (Continuous.continuousOn (by fun_prop)).rpow_const
      (fun x _ => Or.inr hp)
  have hcontMul : IntervalIntegrable
      (fun y : ℝ => (1 - κ ^ 2) ^ p * (1 - y ^ 2) ^ p)
      MeasureTheory.volume 0 c :=
    (hcont 0 c).const_mul _
  -- the y-range enlargement
  have hgrow : (∫ y in (0 : ℝ)..c, (1 - y ^ 2) ^ p)
      ≤ ∫ y in (0 : ℝ)..1, (1 - y ^ 2) ^ p := by
    have hadd := integral_add_adjacent_intervals (hcont 0 c) (hcont c 1)
    have hnn : 0 ≤ ∫ y in c..1, (1 - y ^ 2) ^ p := by
      apply integral_nonneg hc1
      intro y hy
      exact Real.rpow_nonneg (by nlinarith [hy.1, hy.2]) p
    linarith
  -- assemble
  calc ∫ u in κ..1, (1 - u ^ 2) ^ p
      = s * ∫ y in (0 : ℝ)..c, (1 - (s * y + κ) ^ 2) ^ p := hsub
    _ ≤ s * ((1 - κ ^ 2) ^ p * ∫ y in (0 : ℝ)..c, (1 - y ^ 2) ^ p) := by
        apply mul_le_mul_of_nonneg_left ?_ hs0.le
        calc ∫ y in (0 : ℝ)..c, (1 - (s * y + κ) ^ 2) ^ p
            ≤ ∫ y in (0 : ℝ)..c, (1 - κ ^ 2) ^ p * (1 - y ^ 2) ^ p :=
              integral_mono_on hc0 hcontSub hcontMul hpt
          _ = (1 - κ ^ 2) ^ p * ∫ y in (0 : ℝ)..c, (1 - y ^ 2) ^ p :=
              integral_const_mul _ _
    _ ≤ s * ((1 - κ ^ 2) ^ p * ∫ y in (0 : ℝ)..1, (1 - y ^ 2) ^ p) := by
        apply mul_le_mul_of_nonneg_left ?_ hs0.le
        exact mul_le_mul_of_nonneg_left hgrow (Real.rpow_nonneg hκ2.le p)
    _ = (1 - κ ^ 2) ^ (p + 1 / 2) * ∫ y in (0 : ℝ)..1, (1 - y ^ 2) ^ p := by
        rw [hs_def, Real.sqrt_eq_rpow, ← mul_assoc,
          ← Real.rpow_add hκ2, add_comm (1 / 2 : ℝ) p]

/-! ## Lemma A's analytic cores

Lemma A (circle–strip anticoncentration) reduces `P(U ∈ S)` to arc-length
computations `Leb{ψ : sin ψ ∈ I}` and then runs on arcsin/arccos estimates.
The circle-measure preimage is the measure-assembly step the triage records;
the estimates themselves are below, exactly as the paper states them:
`arccos(1−ℓ) = 2·arcsin√(ℓ/2) ≤ π·√(ℓ/2)` (part (i)'s endpoint bound, via
`arcsin u ≤ (π/2)·u` — Jordan again) and `arccos(1−ℓ/2) ≥ √ℓ` (part (iv)'s
tangency sharpness, via `arcsin u ≥ u`). -/

/-- The half-angle identity Lemma A runs on:
`arccos(1−ℓ) = 2·arcsin √(ℓ/2)` for `ℓ ∈ [0, 2]`. -/
theorem arccos_one_sub_eq {ℓ : ℝ} (h0 : 0 ≤ ℓ) (h2 : ℓ ≤ 2) :
    Real.arccos (1 - ℓ) = 2 * Real.arcsin (Real.sqrt (ℓ / 2)) := by
  set α := Real.arccos (1 - ℓ) with hα_def
  have hα0 : 0 ≤ α := Real.arccos_nonneg _
  have hαπ : α ≤ π := Real.arccos_le_pi _
  have hπ := Real.pi_pos
  have hcos : Real.cos α = 1 - ℓ :=
    Real.cos_arccos (by linarith) (by linarith)
  have hsin0 : 0 ≤ Real.sin (α / 2) :=
    Real.sin_nonneg_of_nonneg_of_le_pi (by linarith) (by linarith)
  have hsin : Real.sin (α / 2) = Real.sqrt (ℓ / 2) := by
    rw [← abs_of_nonneg hsin0, Real.abs_sin_half, hcos,
      show (1 - (1 - ℓ)) / 2 = ℓ / 2 by ring]
  have harc : Real.arcsin (Real.sin (α / 2)) = α / 2 :=
    Real.arcsin_sin (by linarith) (by linarith)
  rw [← hsin, harc]
  ring

/-- `arcsin u ≤ (π/2)·u` on `[0, 1]` — the inverse form of Jordan's
inequality. -/
theorem arcsin_le_pi_div_two_mul {u : ℝ} (h0 : 0 ≤ u) (h1 : u ≤ 1) :
    Real.arcsin u ≤ π / 2 * u := by
  have hπ := Real.pi_pos
  have hx0 : 0 ≤ π / 2 * u := by positivity
  have hx : π / 2 * u ≤ π / 2 := by nlinarith
  have hs : u ≤ Real.sin (π / 2 * u) := by
    have h := Real.mul_le_sin hx0 hx
    rw [show 2 / π * (π / 2 * u) = u from by
      field_simp] at h
    exact h
  calc Real.arcsin u ≤ Real.arcsin (Real.sin (π / 2 * u)) :=
        Real.arcsin_le_arcsin hs
    _ = π / 2 * u := Real.arcsin_sin (by linarith) hx

/-- `u ≤ arcsin u` on `[0, 1]`. -/
theorem le_arcsin {u : ℝ} (h0 : 0 ≤ u) (h1 : u ≤ 1) : u ≤ Real.arcsin u := by
  have h := Real.sin_le (Real.arcsin_nonneg.mpr h0)
  rwa [Real.sin_arcsin (by linarith) h1] at h

/-- **Lemma A(i)'s endpoint bound**: the arcsin increment over an interval of
length ℓ abutting the endpoint is `arccos(1−ℓ) ≤ π·√(ℓ/2)`. -/
theorem lemmaA_endpoint_bound {ℓ : ℝ} (h0 : 0 ≤ ℓ) (h2 : ℓ ≤ 2) :
    Real.arccos (1 - ℓ) ≤ π * Real.sqrt (ℓ / 2) := by
  have hu0 : 0 ≤ Real.sqrt (ℓ / 2) := Real.sqrt_nonneg _
  have hu1 : Real.sqrt (ℓ / 2) ≤ 1 := by
    rw [show (1 : ℝ) = Real.sqrt 1 from (Real.sqrt_one).symm]
    exact Real.sqrt_le_sqrt (by linarith)
  have h := arcsin_le_pi_div_two_mul hu0 hu1
  rw [arccos_one_sub_eq h0 h2]
  linarith

/-- **Lemma A(iv)'s tangency sharpness**: `arccos(1 − ℓ/2) ≥ √ℓ` — the
tangent strip's mass is of order √ℓ, so no per-step bound better than √w
holds without a hypothesis on the center's distance to the line. -/
theorem lemmaA_tangency_bound {ℓ : ℝ} (h0 : 0 ≤ ℓ) (h2 : ℓ ≤ 2) :
    Real.sqrt ℓ ≤ Real.arccos (1 - ℓ / 2) := by
  have h4 : 2 * Real.sqrt (ℓ / 4) = Real.sqrt ℓ := by
    have h2' : Real.sqrt 4 = 2 := by
      rw [show (4 : ℝ) = 2 ^ 2 by norm_num,
        Real.sqrt_sq (by norm_num : (0 : ℝ) ≤ 2)]
    rw [← h2', ← Real.sqrt_mul (by norm_num : (0 : ℝ) ≤ 4)]
    congr 1
    ring
  have hu0 : 0 ≤ Real.sqrt (ℓ / 4) := Real.sqrt_nonneg _
  have hu1 : Real.sqrt (ℓ / 4) ≤ 1 := by
    rw [show (1 : ℝ) = Real.sqrt 1 from (Real.sqrt_one).symm]
    exact Real.sqrt_le_sqrt (by linarith)
  have heq : Real.arccos (1 - ℓ / 2) = 2 * Real.arcsin (Real.sqrt (ℓ / 4)) := by
    rw [arccos_one_sub_eq (by linarith) (by linarith),
      show (ℓ / 2) / 2 = ℓ / 4 by ring]
  rw [heq, ← h4]
  have := le_arcsin hu0 hu1
  linarith

/-- **The endpoint-maximality of the arcsin increment** (the step Lemma A(i)
asserts as "maximized when the interval abuts an endpoint"): over ANY
`[a, b] ⊆ [−1, 1]`, `arcsin b − arcsin a ≤ arccos(1 − (b − a))` — the
increment of the abutting-endpoint interval of the same length. The proof is
elementary trigonometry, no convexity: with `α = arcsin a`, `β = arcsin b`,
sum-to-product gives `b − a = 2·sin((β−α)/2)·cos((α+β)/2)`, and
`sin((β−α)/2) ≤ cos((α+β)/2)` because `(β−α) + |β+α| ≤ π`; hence
`sin²((β−α)/2) ≤ (b−a)/2`, and the half-angle identity `arccos(1−ℓ) =
2·arcsin√(ℓ/2)` finishes. -/
theorem arcsin_increment_le_arccos {a b : ℝ} (ha : -1 ≤ a) (hb : b ≤ 1)
    (hab : a ≤ b) :
    Real.arcsin b - Real.arcsin a ≤ Real.arccos (1 - (b - a)) := by
  have hπ := pi_pos
  set α := Real.arcsin a with hα
  set β := Real.arcsin b with hβ
  have hα1 : -(π / 2) ≤ α := Real.neg_pi_div_two_le_arcsin a
  have hα2 : α ≤ π / 2 := Real.arcsin_le_pi_div_two a
  have hβ1 : -(π / 2) ≤ β := Real.neg_pi_div_two_le_arcsin b
  have hβ2 : β ≤ π / 2 := Real.arcsin_le_pi_div_two b
  have hαβ : α ≤ β := Real.arcsin_le_arcsin hab
  have hsin_a : Real.sin α = a := Real.sin_arcsin ha (le_trans hab hb)
  have hsin_b : Real.sin β = b := Real.sin_arcsin (le_trans ha hab) hb
  set u := (β - α) / 2 with hu
  set v := (α + β) / 2 with hv
  have hu0 : 0 ≤ u := by rw [hu]; linarith
  have huπ : u ≤ π / 2 := by rw [hu]; linarith
  have hv2 : |v| ≤ π / 2 := by
    rw [abs_le, hv]
    constructor <;> linarith
  -- sin u ≤ cos v, because u + |v| ≤ π/2
  have hkey : u + |v| ≤ π / 2 := by
    rcases abs_cases v with ⟨h, _⟩ | ⟨h, _⟩ <;> rw [h, hu, hv] <;> linarith
  have hsc : Real.sin u ≤ Real.cos v := by
    have h1 : Real.cos v = Real.sin (π / 2 - |v|) := by
      rw [Real.sin_pi_div_two_sub, Real.cos_abs]
    rw [h1]
    have habs0 : 0 ≤ |v| := abs_nonneg v
    exact Real.strictMonoOn_sin.monotoneOn
      ⟨by linarith, by linarith⟩ ⟨by linarith, by linarith⟩ (by linarith)
  -- sum-to-product
  have hprod : b - a = 2 * Real.sin u * Real.cos v := by
    have h := Real.sin_sub_sin β α
    rw [hsin_a, hsin_b] at h
    rw [h, hu, hv]
    ring_nf
  have hsin_u0 : 0 ≤ Real.sin u :=
    Real.sin_nonneg_of_nonneg_of_le_pi (by linarith) (by linarith)
  have hsq : Real.sin u ^ 2 ≤ (b - a) / 2 := by
    nlinarith [mul_le_mul_of_nonneg_left hsc hsin_u0]
  have hsqrt : Real.sin u ≤ Real.sqrt ((b - a) / 2) := by
    rw [← Real.sqrt_sq hsin_u0]
    exact Real.sqrt_le_sqrt hsq
  have harc : u ≤ Real.arcsin (Real.sqrt ((b - a) / 2)) := by
    calc u = Real.arcsin (Real.sin u) :=
          (Real.arcsin_sin (by linarith) (by linarith)).symm
      _ ≤ Real.arcsin (Real.sqrt ((b - a) / 2)) :=
          Real.arcsin_le_arcsin hsqrt
  rw [arccos_one_sub_eq (by linarith) (by linarith)]
  rw [hu] at harc
  linarith

/-- **Lemma A(ii)'s transversal bound**: on an interval bounded away from ±1
by `m/2`, the arcsin increment is LINEAR in the interval length —
`arcsin b − arcsin a ≤ (2/√(3m))·(b − a)` for `[a, b] ⊆ [−(1−m/2), 1−m/2]`,
`m ∈ (0, 1]` — the mean value inequality with the derivative
`(1−t²)^{-1/2} ≤ 2/√(3m)` on the interval. This is why a transversal
crossing gives a linear (not √) per-step bound. -/
theorem lemmaA_transversal_bound {m a b : ℝ} (hm0 : 0 < m) (hm1 : m ≤ 1)
    (ha : -(1 - m / 2) ≤ a) (hb : b ≤ 1 - m / 2) (hab : a ≤ b) :
    Real.arcsin b - Real.arcsin a ≤ 2 / Real.sqrt (3 * m) * (b - a) := by
  have h3m0 : (0 : ℝ) < 3 * m := by linarith
  have h3m : 0 < Real.sqrt (3 * m) := Real.sqrt_pos.mpr h3m0
  have h4 : 2 * Real.sqrt (3 * m / 4) = Real.sqrt (3 * m) := by
    have h2' : Real.sqrt 4 = 2 := by
      rw [show (4 : ℝ) = 2 ^ 2 by norm_num,
        Real.sqrt_sq (by norm_num : (0 : ℝ) ≤ 2)]
    rw [← h2', ← Real.sqrt_mul (by norm_num : (0 : ℝ) ≤ 4)]
    congr 1
    ring
  have hbound : ∀ x ∈ Set.Ico a b,
      ‖1 / Real.sqrt (1 - x ^ 2)‖ ≤ 2 / Real.sqrt (3 * m) := by
    intro x hx
    have hx1 : -(1 - m / 2) ≤ x := le_trans ha hx.1
    have hx2 : x ≤ 1 - m / 2 := le_of_lt (lt_of_lt_of_le hx.2 hb)
    have hlow : 3 * m / 4 ≤ 1 - x ^ 2 := by nlinarith
    have hs : Real.sqrt (3 * m) / 2 ≤ Real.sqrt (1 - x ^ 2) := by
      rw [← h4]
      have h := Real.sqrt_le_sqrt hlow
      linarith
    have hpos : 0 < Real.sqrt (1 - x ^ 2) := by
      have : (0 : ℝ) < Real.sqrt (3 * m) / 2 := by positivity
      linarith
    rw [Real.norm_eq_abs, abs_of_nonneg (by positivity)]
    calc 1 / Real.sqrt (1 - x ^ 2)
        ≤ 1 / (Real.sqrt (3 * m) / 2) :=
          one_div_le_one_div_of_le (by positivity) hs
      _ = 2 / Real.sqrt (3 * m) := one_div_div _ _
  have hderiv : ∀ x ∈ Set.Icc a b, HasDerivWithinAt Real.arcsin
      (1 / Real.sqrt (1 - x ^ 2)) (Set.Icc a b) x := by
    intro x hx
    have hx1 : x ≠ -1 := by
      intro h
      have := le_trans ha hx.1
      rw [h] at this
      linarith
    have hx2 : x ≠ 1 := by
      intro h
      have := le_trans hx.2 hb
      rw [h] at this
      linarith
    exact (Real.hasDerivAt_arcsin hx1 hx2).hasDerivWithinAt
  have h := norm_image_sub_le_of_norm_deriv_le_segment' hderiv hbound b
    (Set.right_mem_Icc.mpr hab)
  rw [Real.norm_eq_abs,
    abs_of_nonneg (by linarith [Real.arcsin_le_arcsin hab])] at h
  exact h

/-! ## The circle-measure preimage, and Lemma A(i) end to end -/

/-- **The circle-measure preimage** — Lemma A's last ingredient: over the
period `[−π/2, 3π/2]`, `Leb{ψ : sin ψ ∈ [a, b]} = 2·(arcsin b − arcsin a)`.
The preimage is the union of one interval on each monotone branch of sin,
and the two touch in at most the single point π/2. -/
theorem volume_sin_mem_Icc {a b : ℝ} (ha : -1 ≤ a) (hb : b ≤ 1) (hab : a ≤ b) :
    MeasureTheory.volume
        {ψ ∈ Set.Icc (-(π / 2)) (3 * π / 2) | Real.sin ψ ∈ Set.Icc a b}
      = ENNReal.ofReal (2 * (Real.arcsin b - Real.arcsin a)) := by
  have hπ := pi_pos
  have hA1 := Real.neg_pi_div_two_le_arcsin a
  have hA2 := Real.arcsin_le_pi_div_two b
  have hA1' := Real.arcsin_le_pi_div_two a
  have hA2' := Real.neg_pi_div_two_le_arcsin b
  have hmono := Real.arcsin_le_arcsin hab
  -- the preimage is the union of one interval per monotone branch
  have hset : {ψ ∈ Set.Icc (-(π / 2)) (3 * π / 2) | Real.sin ψ ∈ Set.Icc a b}
      = Set.Icc (Real.arcsin a) (Real.arcsin b)
        ∪ Set.Icc (π - Real.arcsin b) (π - Real.arcsin a) := by
    ext ψ
    simp only [Set.mem_Icc, Set.mem_union]
    constructor
    · rintro ⟨⟨hψ1, hψ2⟩, hsa, hsb⟩
      by_cases hc : ψ ≤ π / 2
      · left
        constructor
        · have h := Real.arcsin_le_arcsin hsa
          rwa [Real.arcsin_sin hψ1 hc] at h
        · have h := Real.arcsin_le_arcsin hsb
          rwa [Real.arcsin_sin hψ1 hc] at h
      · right
        rw [not_le] at hc
        have hπψ1 : -(π / 2) ≤ π - ψ := by linarith
        have hπψ2 : π - ψ ≤ π / 2 := by linarith
        have hs : Real.sin (π - ψ) = Real.sin ψ := Real.sin_pi_sub ψ
        constructor
        · have h := Real.arcsin_le_arcsin hsb
          rw [← hs, Real.arcsin_sin hπψ1 hπψ2] at h
          linarith
        · have h := Real.arcsin_le_arcsin hsa
          rw [← hs, Real.arcsin_sin hπψ1 hπψ2] at h
          linarith
    · rintro (⟨h1, h2⟩ | ⟨h1, h2⟩)
      · have hm : ψ ∈ Set.Icc (-(π / 2)) (π / 2) :=
          ⟨by linarith, by linarith⟩
        refine ⟨⟨by linarith, by linarith⟩, ?_, ?_⟩
        · have h := Real.strictMonoOn_sin.monotoneOn
            ⟨hA1, by linarith⟩ hm h1
          rwa [Real.sin_arcsin ha (le_trans hab hb)] at h
        · have h := Real.strictMonoOn_sin.monotoneOn hm
            ⟨by linarith, hA2⟩ h2
          rwa [Real.sin_arcsin (le_trans ha hab) hb] at h
      · have hπψ : π - ψ ∈ Set.Icc (-(π / 2)) (π / 2) :=
          ⟨by linarith, by linarith⟩
        have hs : Real.sin ψ = Real.sin (π - ψ) := (Real.sin_pi_sub ψ).symm
        refine ⟨⟨by linarith, by linarith⟩, ?_, ?_⟩
        · rw [hs]
          have h := Real.strictMonoOn_sin.monotoneOn
            ⟨hA1, by linarith⟩ hπψ (by linarith)
          rwa [Real.sin_arcsin ha (le_trans hab hb)] at h
        · rw [hs]
          have h := Real.strictMonoOn_sin.monotoneOn hπψ
            ⟨by linarith, hA2⟩ (by linarith)
          rwa [Real.sin_arcsin (le_trans ha hab) hb] at h
  rw [hset]
  -- the two branch intervals meet in at most the point π/2
  have hinter : MeasureTheory.volume
      (Set.Icc (Real.arcsin a) (Real.arcsin b)
        ∩ Set.Icc (π - Real.arcsin b) (π - Real.arcsin a)) = 0 := by
    refine MeasureTheory.measure_mono_null ?_
      (MeasureTheory.measure_singleton (π / 2))
    rintro x ⟨⟨_, hx2⟩, hx3, _⟩
    have h1 : x ≤ π / 2 := le_trans hx2 hA2
    have h2 : π / 2 ≤ x := by linarith
    simp [le_antisymm h1 h2]
  have hunion := MeasureTheory.measure_union_add_inter
    (μ := MeasureTheory.volume)
    (t := Set.Icc (π - Real.arcsin b) (π - Real.arcsin a))
    (Set.Icc (Real.arcsin a) (Real.arcsin b)) measurableSet_Icc
  rw [hinter, add_zero] at hunion
  rw [hunion, Real.volume_Icc, Real.volume_Icc,
    show π - Real.arcsin a - (π - Real.arcsin b)
      = Real.arcsin b - Real.arcsin a by ring,
    ← ENNReal.ofReal_add (by linarith) (by linarith)]
  congr 1
  ring

/-- **Lemma A(i), end to end**: the measure of the strip event over the full
period is at most `2π·√(ℓ/2)` — i.e. the PROBABILITY under the uniform angle
is at most `√(ℓ/2)`, with `ℓ = b − a` the interval length. Composed from the
preimage computation, the endpoint-maximality, and the arccos bound. -/
theorem lemmaA_part_i {a b : ℝ} (ha : -1 ≤ a) (hb : b ≤ 1) (hab : a ≤ b) :
    MeasureTheory.volume
        {ψ ∈ Set.Icc (-(π / 2)) (3 * π / 2) | Real.sin ψ ∈ Set.Icc a b}
      ≤ ENNReal.ofReal (2 * π * Real.sqrt ((b - a) / 2)) := by
  rw [volume_sin_mem_Icc ha hb hab]
  apply ENNReal.ofReal_le_ofReal
  have h1 := arcsin_increment_le_arccos ha hb hab
  have h2 := lemmaA_endpoint_bound (ℓ := b - a) (by linarith) (by linarith)
  linarith

/-- **The period-window glue**: the strip event carries the same mass over
Lemma S's window `[−π, π]` as over the preimage computation's window
`[−π/2, 3π/2]` — split at the shared part `(−π/2, π]` and translate the tail
by 2π (endpoints are null). -/
theorem volume_sin_window_shift {a b : ℝ} :
    MeasureTheory.volume {ψ ∈ Set.Icc (-π) π | Real.sin ψ ∈ Set.Icc a b}
      = MeasureTheory.volume
        {ψ ∈ Set.Icc (-(π / 2)) (3 * π / 2) | Real.sin ψ ∈ Set.Icc a b} := by
  have hπ := pi_pos
  set P : Set ℝ := Real.sin ⁻¹' Set.Icc a b with hP
  have hPm : MeasurableSet P := measurableSet_Icc.preimage Real.continuous_sin.measurable
  have hrepr : ∀ s : Set ℝ, {ψ ∈ s | Real.sin ψ ∈ Set.Icc a b} = s ∩ P :=
    fun _ => rfl
  -- closed windows and half-open windows carry the same mass
  have hIccIoc : ∀ c d : ℝ,
      MeasureTheory.volume (Set.Icc c d ∩ P)
        = MeasureTheory.volume (Set.Ioc c d ∩ P) := by
    intro c d
    apply le_antisymm
    · have hsub : Set.Icc c d ∩ P ⊆ (Set.Ioc c d ∩ P) ∪ {c} := by
        rintro ψ ⟨⟨h1, h2⟩, hp⟩
        rcases eq_or_lt_of_le h1 with h | h
        · exact Or.inr (by simp [← h])
        · exact Or.inl ⟨⟨h, h2⟩, hp⟩
      calc MeasureTheory.volume (Set.Icc c d ∩ P)
          ≤ MeasureTheory.volume ((Set.Ioc c d ∩ P) ∪ {c}) :=
            MeasureTheory.measure_mono hsub
        _ ≤ MeasureTheory.volume (Set.Ioc c d ∩ P)
              + MeasureTheory.volume {c} := MeasureTheory.measure_union_le _ _
        _ = MeasureTheory.volume (Set.Ioc c d ∩ P) := by
            rw [Real.volume_singleton, add_zero]
    · exact MeasureTheory.measure_mono
        (Set.inter_subset_inter_left P Set.Ioc_subset_Icc_self)
  rw [hrepr, hrepr, hIccIoc, hIccIoc]
  -- split both half-open windows at the shared middle
  have hsplit1 : Set.Ioc (-π) π ∩ P
      = (Set.Ioc (-π) (-(π / 2)) ∩ P) ∪ (Set.Ioc (-(π / 2)) π ∩ P) := by
    rw [← Set.union_inter_distrib_right,
      Set.Ioc_union_Ioc_eq_Ioc (by linarith) (by linarith)]
  have hsplit2 : Set.Ioc (-(π / 2)) (3 * π / 2) ∩ P
      = (Set.Ioc (-(π / 2)) π ∩ P) ∪ (Set.Ioc π (3 * π / 2) ∩ P) := by
    rw [← Set.union_inter_distrib_right,
      Set.Ioc_union_Ioc_eq_Ioc (by linarith) (by linarith)]
  have hdisj1 : Disjoint (Set.Ioc (-π) (-(π / 2)) ∩ P)
      (Set.Ioc (-(π / 2)) π ∩ P) := by
    rw [Set.disjoint_left]
    rintro ψ ⟨⟨_, h1⟩, _⟩ ⟨⟨h2, _⟩, _⟩
    linarith
  have hdisj2 : Disjoint (Set.Ioc (-(π / 2)) π ∩ P)
      (Set.Ioc π (3 * π / 2) ∩ P) := by
    rw [Set.disjoint_left]
    rintro ψ ⟨⟨_, h1⟩, _⟩ ⟨⟨h2, _⟩, _⟩
    linarith
  -- the two tails are 2π-translates of one another
  have htail : MeasureTheory.volume (Set.Ioc π (3 * π / 2) ∩ P)
      = MeasureTheory.volume (Set.Ioc (-π) (-(π / 2)) ∩ P) := by
    have hset : ((fun ψ : ℝ => -(2 * π) + ψ) ⁻¹'
        (Set.Ioc (-π) (-(π / 2)) ∩ P)) = Set.Ioc π (3 * π / 2) ∩ P := by
      ext ψ
      simp only [Set.mem_preimage, Set.mem_inter_iff, Set.mem_Ioc, hP,
        Set.mem_Icc]
      constructor
      · rintro ⟨⟨h1, h2⟩, hp⟩
        refine ⟨⟨by linarith, by linarith⟩, ?_⟩
        rwa [show -(2 * π) + ψ = ψ - 2 * π by ring, Real.sin_sub_two_pi] at hp
      · rintro ⟨⟨h1, h2⟩, hp⟩
        refine ⟨⟨by linarith, by linarith⟩, ?_⟩
        rwa [show -(2 * π) + ψ = ψ - 2 * π by ring, Real.sin_sub_two_pi]
    rw [← hset, MeasureTheory.measure_preimage_add]
  rw [hsplit1, hsplit2,
    MeasureTheory.measure_union hdisj1 (measurableSet_Ioc.inter hPm),
    MeasureTheory.measure_union hdisj2 (measurableSet_Ioc.inter hPm),
    htail]
  ring

/-- **Lemma A(i) in Lemma S's own window**: the per-step strip bound over the
heading's actual range `[−π, π]` — the composition T4's per-step argument
uses. -/
theorem lemmaA_part_i' {a b : ℝ} (ha : -1 ≤ a) (hb : b ≤ 1) (hab : a ≤ b) :
    MeasureTheory.volume {ψ ∈ Set.Icc (-π) π | Real.sin ψ ∈ Set.Icc a b}
      ≤ ENNReal.ofReal (2 * π * Real.sqrt ((b - a) / 2)) := by
  rw [volume_sin_window_shift]
  exact lemmaA_part_i ha hb hab

/-- **Lemma S's measure half** (THEORY.md, "Lemma S"): the heading map
`a ↦ π·a` carries the uniform action law on `[−1, 1]` to `(1/π)`·Lebesgue on
`[−π, π]` — the heading angle is EXACTLY uniform, and nothing about the state
enters. Combined with the read-off half (`lemmaS_landing_eq` in
`WitnessTube.lean`), the one-step landing law is exactly the uniform
arc-length measure on the circle of radius `gain·dt²` about the drift
center. -/
theorem lemmaS_heading_uniform :
    MeasureTheory.Measure.map (fun a : ℝ => π * a)
        (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
      = ENNReal.ofReal π⁻¹ •
        MeasureTheory.volume.restrict (Set.Icc (-π) π) := by
  have hπ := pi_pos
  have hne : (π : ℝ) ≠ 0 := ne_of_gt hπ
  have hpre : (fun a : ℝ => π * a) ⁻¹' Set.Icc (-π) π
      = Set.Icc (-1 : ℝ) 1 := by
    ext a
    simp only [Set.mem_preimage, Set.mem_Icc]
    constructor
    · rintro ⟨h1, h2⟩
      constructor <;> nlinarith
    · rintro ⟨h1, h2⟩
      constructor <;> nlinarith
  calc MeasureTheory.Measure.map (fun a : ℝ => π * a)
        (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
      = MeasureTheory.Measure.map (fun a : ℝ => π * a)
        (MeasureTheory.volume.restrict
          ((fun a : ℝ => π * a) ⁻¹' Set.Icc (-π) π)) := by rw [hpre]
    _ = (MeasureTheory.Measure.map (fun a : ℝ => π * a)
          MeasureTheory.volume).restrict (Set.Icc (-π) π) :=
        (MeasureTheory.Measure.restrict_map
          (measurable_const_mul π) measurableSet_Icc).symm
    _ = (ENNReal.ofReal |π⁻¹| • MeasureTheory.volume).restrict
          (Set.Icc (-π) π) := by rw [Real.map_volume_mul_left hne]
    _ = ENNReal.ofReal π⁻¹ •
          MeasureTheory.volume.restrict (Set.Icc (-π) π) := by
        rw [MeasureTheory.Measure.restrict_smul,
          abs_of_pos (by positivity : (0 : ℝ) < π⁻¹)]

/-! ## T4's union-bound skeleton

The two measure steps that turn the per-step strip bound into T4's modulus:
the Fubini slice bound (conditioning on the past — the prefix fixes the
state, and the current action's slice is a strip event bounded uniformly
over states by Lemma A + S + W), and the h-step union bound. What remains
for the fully composed T4 is the process-model instantiation: the h-fold
product of the action law with the trajectory map's measurability, which is
where these two lemmas get applied once per step. -/

/-- **The Fubini slice bound** (T4's conditioning step): if every `x`-slice
of a product event has `ν`-measure at most `B`, the product measure of the
event is at most `B · μ(univ)`. -/
theorem prod_slice_bound {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : MeasureTheory.Measure α) (ν : MeasureTheory.Measure β)
    [MeasureTheory.SFinite ν]
    {E : Set (α × β)} (hE : MeasurableSet E) {B : ENNReal}
    (hslice : ∀ x, ν (Prod.mk x ⁻¹' E) ≤ B) :
    (μ.prod ν) E ≤ B * μ Set.univ := by
  rw [MeasureTheory.Measure.prod_apply hE]
  calc ∫⁻ x, ν (Prod.mk x ⁻¹' E) ∂μ
      ≤ ∫⁻ _, B ∂μ := MeasureTheory.lintegral_mono hslice
    _ = B * μ Set.univ := MeasureTheory.lintegral_const B

/-- **The h-step union bound**: h events each of measure at most `B` have
union of measure at most `h·B` — the step that turns the per-step bound into
T4's `h·√(r_out·ε/(gain·dt²))` modulus. -/
theorem union_bound_le {Ω : Type*} [MeasurableSpace Ω]
    (μ : MeasureTheory.Measure Ω) (h : ℕ) (E : ℕ → Set Ω) {B : ENNReal}
    (hE : ∀ t < h, μ (E t) ≤ B) :
    μ (⋃ t ∈ Finset.range h, E t) ≤ h * B := by
  calc μ (⋃ t ∈ Finset.range h, E t)
      ≤ ∑ t ∈ Finset.range h, μ (E t) :=
        MeasureTheory.measure_biUnion_finset_le _ _
    _ ≤ ∑ _t ∈ Finset.range h, B :=
        Finset.sum_le_sum fun t ht => hE t (Finset.mem_range.mp ht)
    _ = h * B := by
        rw [Finset.sum_const, Finset.card_range, nsmul_eq_mul]

/-! ## Window invariance and rotation: Lemma A for arbitrary strips

Lemma A's proof opens with "rotating coordinates shifts the uniform ψ" —
the strip's orientation is arbitrary because the uniform angle is rotation
invariant. Machine-checked below: any length-2π window carries the same
sin-strip mass (whole-window 2π-translations plus one split-and-translate
at a representative), hence the ROTATED strip event has the same measure,
and the per-step bound applies to strips in every orientation. -/

section WindowInvariance

/-- Closed and half-open windows carry the same mass against any set: the
left endpoint is null. -/
private lemma volume_Icc_inter_eq_Ioc_inter (P : Set ℝ) (c d : ℝ) :
    MeasureTheory.volume (Set.Icc c d ∩ P)
      = MeasureTheory.volume (Set.Ioc c d ∩ P) := by
  apply le_antisymm
  · have hsub : Set.Icc c d ∩ P ⊆ (Set.Ioc c d ∩ P) ∪ {c} := by
      rintro ψ ⟨⟨h1, h2⟩, hp⟩
      rcases eq_or_lt_of_le h1 with h | h
      · exact Or.inr (by simp [← h])
      · exact Or.inl ⟨⟨h, h2⟩, hp⟩
    calc MeasureTheory.volume (Set.Icc c d ∩ P)
        ≤ MeasureTheory.volume ((Set.Ioc c d ∩ P) ∪ {c}) :=
          MeasureTheory.measure_mono hsub
      _ ≤ MeasureTheory.volume (Set.Ioc c d ∩ P)
            + MeasureTheory.volume {c} := MeasureTheory.measure_union_le _ _
      _ = MeasureTheory.volume (Set.Ioc c d ∩ P) := by
          rw [Real.volume_singleton, add_zero]
  · exact MeasureTheory.measure_mono
      (Set.inter_subset_inter_left P Set.Ioc_subset_Icc_self)

/-- Whole-window translation by `2πk` preserves the sin-strip mass — sin is
periodic and Lebesgue is translation invariant; no splitting needed. -/
private lemma volume_sin_Ioc_translate {a b : ℝ} (c d : ℝ) (k : ℤ) :
    MeasureTheory.volume (Set.Ioc c d ∩ Real.sin ⁻¹' Set.Icc a b)
      = MeasureTheory.volume
        (Set.Ioc (c + (k : ℝ) * (2 * π)) (d + (k : ℝ) * (2 * π))
          ∩ Real.sin ⁻¹' Set.Icc a b) := by
  have hset : ((fun ψ : ℝ => -((k : ℝ) * (2 * π)) + ψ) ⁻¹'
      (Set.Ioc c d ∩ Real.sin ⁻¹' Set.Icc a b))
      = Set.Ioc (c + (k : ℝ) * (2 * π)) (d + (k : ℝ) * (2 * π))
        ∩ Real.sin ⁻¹' Set.Icc a b := by
    ext ψ
    simp only [Set.mem_preimage, Set.mem_inter_iff, Set.mem_Ioc, Set.mem_Icc]
    constructor
    · rintro ⟨⟨h1, h2⟩, hp⟩
      refine ⟨⟨by linarith, by linarith⟩, ?_⟩
      rwa [show -((k : ℝ) * (2 * π)) + ψ = ψ - (k : ℝ) * (2 * π) by ring,
        Real.sin_sub_int_mul_two_pi] at hp
    · rintro ⟨⟨h1, h2⟩, hp⟩
      refine ⟨⟨by linarith, by linarith⟩, ?_⟩
      rwa [show -((k : ℝ) * (2 * π)) + ψ = ψ - (k : ℝ) * (2 * π) by ring,
        Real.sin_sub_int_mul_two_pi]
  rw [← hset, MeasureTheory.measure_preimage_add]

/-- Split-and-translate at a representative: for `c ∈ [−π, π]`, the window
`(c, c + 2π]` carries the same sin-strip mass as `(−π, π]`. -/
private lemma volume_sin_window_rep {a b c : ℝ} (hc1 : -π ≤ c) (hc2 : c ≤ π) :
    MeasureTheory.volume (Set.Ioc (-π) π ∩ Real.sin ⁻¹' Set.Icc a b)
      = MeasureTheory.volume
        (Set.Ioc c (c + 2 * π) ∩ Real.sin ⁻¹' Set.Icc a b) := by
  have hπ := pi_pos
  set P : Set ℝ := Real.sin ⁻¹' Set.Icc a b with hP
  have hPm : MeasurableSet P :=
    measurableSet_Icc.preimage Real.continuous_sin.measurable
  have hsplit1 : Set.Ioc (-π) π ∩ P
      = (Set.Ioc (-π) c ∩ P) ∪ (Set.Ioc c π ∩ P) := by
    rw [← Set.union_inter_distrib_right, Set.Ioc_union_Ioc_eq_Ioc hc1 hc2]
  have hsplit2 : Set.Ioc c (c + 2 * π) ∩ P
      = (Set.Ioc c π ∩ P) ∪ (Set.Ioc π (c + 2 * π) ∩ P) := by
    rw [← Set.union_inter_distrib_right,
      Set.Ioc_union_Ioc_eq_Ioc hc2 (by linarith)]
  have hdisj1 : Disjoint (Set.Ioc (-π) c ∩ P) (Set.Ioc c π ∩ P) := by
    rw [Set.disjoint_left]
    rintro ψ ⟨⟨_, h1⟩, _⟩ ⟨⟨h2, _⟩, _⟩
    linarith
  have hdisj2 : Disjoint (Set.Ioc c π ∩ P) (Set.Ioc π (c + 2 * π) ∩ P) := by
    rw [Set.disjoint_left]
    rintro ψ ⟨⟨_, h1⟩, _⟩ ⟨⟨h2, _⟩, _⟩
    linarith
  have htail := volume_sin_Ioc_translate (a := a) (b := b) (-π) c 1
  rw [show (-π + (1 : ℤ) * (2 * π) : ℝ) = π by push_cast; ring,
    show (c + (1 : ℤ) * (2 * π) : ℝ) = c + 2 * π by push_cast; ring] at htail
  rw [← hP] at htail
  rw [hsplit1, hsplit2,
    MeasureTheory.measure_union hdisj1 (measurableSet_Ioc.inter hPm),
    MeasureTheory.measure_union hdisj2 (measurableSet_Ioc.inter hPm),
    htail]
  ring

/-- **Any length-2π window carries the same sin-strip mass.** -/
lemma volume_sin_window_any {a b : ℝ} (c : ℝ) :
    MeasureTheory.volume
        (Set.Ioc c (c + 2 * π) ∩ Real.sin ⁻¹' Set.Icc a b)
      = MeasureTheory.volume (Set.Ioc (-π) π ∩ Real.sin ⁻¹' Set.Icc a b) := by
  have hπ := pi_pos
  set k := ⌊(c + π) / (2 * π)⌋ with hk
  have h2π : (0 : ℝ) < 2 * π := by linarith
  have hfl := Int.floor_le ((c + π) / (2 * π))
  have hfl' := Int.lt_floor_add_one ((c + π) / (2 * π))
  have hdiv : (c + π) / (2 * π) * (2 * π) = c + π := by field_simp
  have hc1 : -π ≤ c - (k : ℝ) * (2 * π) := by nlinarith
  have hc2 : c - (k : ℝ) * (2 * π) ≤ π := by nlinarith
  have htr := volume_sin_Ioc_translate (a := a) (b := b)
    (c - (k : ℝ) * (2 * π)) (c - (k : ℝ) * (2 * π) + 2 * π) k
  rw [show c - (k : ℝ) * (2 * π) + (k : ℝ) * (2 * π) = c by ring,
    show c - (k : ℝ) * (2 * π) + 2 * π + (k : ℝ) * (2 * π) = c + 2 * π
      by ring] at htr
  rw [← htr, ← volume_sin_window_rep hc1 hc2]

/-- **Rotation invariance of the strip event** — Lemma A's "rotating
coordinates shifts the uniform ψ": the strip event for the rotated angle
`φ₀ + ψ` carries the same mass over the heading window as the unrotated
one, for EVERY φ₀. -/
theorem volume_sin_rotate (φ₀ : ℝ) {a b : ℝ} :
    MeasureTheory.volume
        {ψ ∈ Set.Icc (-π) π | Real.sin (φ₀ + ψ) ∈ Set.Icc a b}
      = MeasureTheory.volume
        {ψ ∈ Set.Icc (-π) π | Real.sin ψ ∈ Set.Icc a b} := by
  have hπ := pi_pos
  set P : Set ℝ := Real.sin ⁻¹' Set.Icc a b with hP
  have hrepr1 : {ψ ∈ Set.Icc (-π) π | Real.sin (φ₀ + ψ) ∈ Set.Icc a b}
      = Set.Icc (-π) π ∩ (fun ψ => φ₀ + ψ) ⁻¹' P := rfl
  have hrepr2 : {ψ ∈ Set.Icc (-π) π | Real.sin ψ ∈ Set.Icc a b}
      = Set.Icc (-π) π ∩ P := rfl
  rw [hrepr1, hrepr2,
    volume_Icc_inter_eq_Ioc_inter ((fun ψ => φ₀ + ψ) ⁻¹' P),
    volume_Icc_inter_eq_Ioc_inter P]
  have hset : Set.Ioc (-π) π ∩ (fun ψ => φ₀ + ψ) ⁻¹' P
      = (fun ψ : ℝ => φ₀ + ψ) ⁻¹' (Set.Ioc (φ₀ - π) (φ₀ + π) ∩ P) := by
    ext ψ
    simp only [Set.mem_preimage, Set.mem_inter_iff, Set.mem_Ioc]
    constructor
    · rintro ⟨⟨h1, h2⟩, hp⟩
      exact ⟨⟨by linarith, by linarith⟩, hp⟩
    · rintro ⟨⟨h1, h2⟩, hp⟩
      exact ⟨⟨by linarith, by linarith⟩, hp⟩
  rw [hset, MeasureTheory.measure_preimage_add]
  have := volume_sin_window_any (a := a) (b := b) (φ₀ - π)
  rw [show φ₀ - π + 2 * π = φ₀ + π by ring] at this
  exact this

/-- **Lemma A(i) for arbitrarily rotated strips**: the per-step strip bound
holds whatever the strip's orientation relative to the heading's zero. -/
theorem lemmaA_part_i_rotated (φ₀ : ℝ) {a b : ℝ}
    (ha : -1 ≤ a) (hb : b ≤ 1) (hab : a ≤ b) :
    MeasureTheory.volume
        {ψ ∈ Set.Icc (-π) π | Real.sin (φ₀ + ψ) ∈ Set.Icc a b}
      ≤ ENNReal.ofReal (2 * π * Real.sqrt ((b - a) / 2)) := by
  rw [volume_sin_rotate]
  exact lemmaA_part_i' ha hb hab

end WindowInvariance

/-- **The Fubini slice bound, first-coordinate version**: conditioning on
the SECOND factor (the suffix of the action sequence, which the current
landing does not depend on). -/
theorem prod_slice_bound' {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : MeasureTheory.Measure α) (ν : MeasureTheory.Measure β)
    [MeasureTheory.SFinite μ] [MeasureTheory.SFinite ν]
    {E : Set (α × β)} (hE : MeasurableSet E) {B : ENNReal}
    (hslice : ∀ y, μ ((fun x => (x, y)) ⁻¹' E) ≤ B) :
    (μ.prod ν) E ≤ B * ν Set.univ := by
  rw [MeasureTheory.Measure.prod_apply_symm hE]
  calc ∫⁻ y, μ ((fun x => (x, y)) ⁻¹' E) ∂ν
      ≤ ∫⁻ _, B ∂ν := MeasureTheory.lintegral_mono hslice
    _ = B * ν Set.univ := MeasureTheory.lintegral_const B

/-- **T4's process wiring.** For the (n+1)-fold product of a per-step action
law: if every event `E t` has all its coordinate-`t` slices bounded by `B`
uniformly in the other coordinates — the conditional per-step bound that
Lemma A + S + W supply, since the prefix fixes the state and the landing
ignores the suffix — then the union has measure at most
`(n+1)·B·(mass of one factor)^n`. Normalizing by the total mass
`(mass)^{n+1}` this is `P(⋃ E_t) ≤ (n+1)·(B/mass)`: the h-step modulus of
Theorem T4 from the per-step conditional bound. -/
theorem pi_union_slice_bound {n : ℕ} (μ₀ : MeasureTheory.Measure ℝ)
    [MeasureTheory.SigmaFinite μ₀]
    (E : Fin (n + 1) → Set (Fin (n + 1) → ℝ))
    (hEm : ∀ t, MeasurableSet (E t)) {B : ENNReal}
    (hslice : ∀ (t : Fin (n + 1)) (rest : Fin n → ℝ),
      μ₀ {a | t.insertNth a rest ∈ E t} ≤ B) :
    MeasureTheory.Measure.pi (fun _ : Fin (n + 1) => μ₀) (⋃ t, E t)
      ≤ (n + 1 : ENNReal) * (B * μ₀ Set.univ ^ n) := by
  have hstep : ∀ t : Fin (n + 1),
      MeasureTheory.Measure.pi (fun _ : Fin (n + 1) => μ₀) (E t)
        ≤ B * μ₀ Set.univ ^ n := by
    intro t
    set e := MeasurableEquiv.piFinSuccAbove (fun _ : Fin (n + 1) => ℝ) t
      with he
    have hmp := MeasureTheory.measurePreserving_piFinSuccAbove
      (fun _ : Fin (n + 1) => μ₀) t
    rw [← he] at hmp
    have hE' : MeasurableSet (e.symm ⁻¹' E t) :=
      e.symm.measurable (hEm t)
    have hEeq : e ⁻¹' (e.symm ⁻¹' E t) = E t := by
      ext ω
      simp
    have hkey : MeasureTheory.Measure.pi (fun _ : Fin (n + 1) => μ₀) (E t)
        = (μ₀.prod (MeasureTheory.Measure.pi fun _ : Fin n => μ₀))
            (e.symm ⁻¹' E t) := by
      have h := hmp.measure_preimage hE'.nullMeasurableSet
      rw [hEeq] at h
      exact h
    rw [hkey]
    have hb := prod_slice_bound' μ₀
      (MeasureTheory.Measure.pi fun _ : Fin n => μ₀) hE' (B := B)
      (fun rest => by
        have hset : ((fun a => (a, rest)) ⁻¹' (e.symm ⁻¹' E t))
            = {a | t.insertNth a rest ∈ E t} := rfl
        rw [hset]
        exact hslice t rest)
    calc (μ₀.prod (MeasureTheory.Measure.pi fun _ : Fin n => μ₀))
          (e.symm ⁻¹' E t)
        ≤ B * (MeasureTheory.Measure.pi fun _ : Fin n => μ₀) Set.univ := hb
      _ = B * μ₀ Set.univ ^ n := by
          rw [MeasureTheory.Measure.pi_univ, Finset.prod_const,
            Finset.card_univ, Fintype.card_fin]
  calc MeasureTheory.Measure.pi (fun _ : Fin (n + 1) => μ₀) (⋃ t, E t)
      ≤ ∑ t : Fin (n + 1),
          MeasureTheory.Measure.pi (fun _ : Fin (n + 1) => μ₀) (E t) :=
        MeasureTheory.measure_iUnion_fintype_le _ _
    _ ≤ ∑ _t : Fin (n + 1), B * μ₀ Set.univ ^ n :=
        Finset.sum_le_sum fun t _ => hstep t
    _ = (n + 1 : ENNReal) * (B * μ₀ Set.univ ^ n) := by
        rw [Finset.sum_const, Finset.card_univ, Fintype.card_fin,
          nsmul_eq_mul]
        push_cast
        ring

/-- **T4's per-slice bound, fully composed**: under the uniform action law
on `[−1, 1]`, any rotated sin-interval event — the form every strip landing
event reduces to via Lemma S (landing = drift + R·heading) and Lemma W (the
sliver sits in a strip) — has mass at most `2·√(ℓ/2)`, i.e. probability
`√(ℓ/2)` after normalizing by the action mass 2, with ℓ the interval
length. Composed from `lemmaS_heading_uniform` and
`lemmaA_part_i_rotated`. -/
theorem t4_slice_bound (φ₀ : ℝ) {lo hi : ℝ}
    (hlo : -1 ≤ lo) (hhi : hi ≤ 1) (hlohi : lo ≤ hi) :
    (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
        {a : ℝ | Real.sin (φ₀ + π * a) ∈ Set.Icc lo hi}
      ≤ ENNReal.ofReal (2 * Real.sqrt ((hi - lo) / 2)) := by
  have hπ := pi_pos
  have hne : (π : ℝ) ≠ 0 := ne_of_gt hπ
  have hev : MeasurableSet {ψ : ℝ | Real.sin (φ₀ + ψ) ∈ Set.Icc lo hi} :=
    (Real.continuous_sin.comp (continuous_const.add continuous_id)).measurable
      measurableSet_Icc
  have hmap : (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
      {a : ℝ | Real.sin (φ₀ + π * a) ∈ Set.Icc lo hi}
      = (MeasureTheory.Measure.map (fun a : ℝ => π * a)
          (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1)))
        {ψ | Real.sin (φ₀ + ψ) ∈ Set.Icc lo hi} := by
    rw [MeasureTheory.Measure.map_apply (measurable_const_mul π) hev]
    rfl
  rw [hmap, lemmaS_heading_uniform, MeasureTheory.Measure.smul_apply,
    MeasureTheory.Measure.restrict_apply hev, smul_eq_mul]
  have hset : {ψ | Real.sin (φ₀ + ψ) ∈ Set.Icc lo hi} ∩ Set.Icc (-π) π
      = {ψ ∈ Set.Icc (-π) π | Real.sin (φ₀ + ψ) ∈ Set.Icc lo hi} := by
    rw [Set.inter_comm]
    rfl
  rw [hset]
  calc ENNReal.ofReal π⁻¹ * MeasureTheory.volume
        {ψ ∈ Set.Icc (-π) π | Real.sin (φ₀ + ψ) ∈ Set.Icc lo hi}
      ≤ ENNReal.ofReal π⁻¹
          * ENNReal.ofReal (2 * π * Real.sqrt ((hi - lo) / 2)) := by
        gcongr
        exact lemmaA_part_i_rotated φ₀ hlo hhi hlohi
    _ = ENNReal.ofReal (2 * Real.sqrt ((hi - lo) / 2)) := by
        rw [← ENNReal.ofReal_mul (by positivity)]
        congr 1
        field_simp

/-- **Theorem T4's modulus, composed.** For events whose coordinate slices
all have the rotated sin-interval form of length ≤ ℓ — what Lemma S and
Lemma W give every sliver-landing event — the union over `h = n + 1` steps
has action-process mass at most `(n+1)·2√(ℓ/2)·2^n`. Normalized by the
total action mass `2^{n+1}`, this reads
`P(some landing in the sliver within h steps) ≤ h·√(ℓ/2)`: with
`ℓ = w_ε/R_L`, THEORY.md's `|q(γ) − q(γ′)| ≤ h·√(r_out·ε/(gain·dt²))`
modulus. Every ingredient is machine-checked; the instrument supplies
`hform` per sliver through `lemmaS_landing_eq` and
`lemmaW_sliver_in_strip`. -/
theorem t4_modulus {n : ℕ}
    (E : Fin (n + 1) → Set (Fin (n + 1) → ℝ))
    (hEm : ∀ t, MeasurableSet (E t)) {ℓ : ℝ}
    (hform : ∀ (t : Fin (n + 1)) (rest : Fin n → ℝ),
      ∃ φ₀ lo hi, -1 ≤ lo ∧ hi ≤ 1 ∧ lo ≤ hi ∧ hi - lo ≤ ℓ ∧
        {a : ℝ | t.insertNth a rest ∈ E t}
          = {a : ℝ | Real.sin (φ₀ + π * a) ∈ Set.Icc lo hi}) :
    MeasureTheory.Measure.pi
        (fun _ : Fin (n + 1) =>
          MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
        (⋃ t, E t)
      ≤ (n + 1 : ENNReal)
        * (ENNReal.ofReal (2 * Real.sqrt (ℓ / 2)) * (2 : ENNReal) ^ n) := by
  have h2 : (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1)) Set.univ
      = (2 : ENNReal) := by
    rw [MeasureTheory.Measure.restrict_apply MeasurableSet.univ,
      Set.univ_inter, Real.volume_Icc]
    norm_num
  have h := pi_union_slice_bound
    (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1)) E hEm
    (B := ENNReal.ofReal (2 * Real.sqrt (ℓ / 2)))
    (fun t rest => by
      obtain ⟨φ₀, lo, hi, hlo, hhi, hlohi, hlen, hset⟩ := hform t rest
      rw [hset]
      calc (MeasureTheory.volume.restrict (Set.Icc (-1 : ℝ) 1))
            {a : ℝ | Real.sin (φ₀ + π * a) ∈ Set.Icc lo hi}
          ≤ ENNReal.ofReal (2 * Real.sqrt ((hi - lo) / 2)) :=
            t4_slice_bound φ₀ hlo hhi hlohi
        _ ≤ ENNReal.ofReal (2 * Real.sqrt (ℓ / 2)) := by
            apply ENNReal.ofReal_le_ofReal
            have hs := Real.sqrt_le_sqrt
              (show (hi - lo) / 2 ≤ ℓ / 2 by linarith)
            linarith)
  rw [h2] at h
  exact h

/-- **Lemma W (sliver-in-strip), the geometric core** (THEORY.md, T4's
ingredient): a point at radius `ρ ≤ r_out` and angular offset `φ` from a
line through the ring center has distance `ρ·|sin φ|` to that line, and for
`|φ| ≤ ε/4` that distance is at most `r_out·ε/4` — each γ-sliver lies in the
strip of half-width `r_out·ε/4` about its angular bisector. Together with
Lemma A (whose arcsin computations are the remaining analytic piece) and
Lemma S's exactly-uniform landing direction, this is T4's geometry. -/
theorem lemmaW_sliver_in_strip {ρ φ ε rout : ℝ} (hρ0 : 0 ≤ ρ) (hρ : ρ ≤ rout)
    (hφ : |φ| ≤ ε / 4) :
    |ρ * Real.sin φ| ≤ rout * ε / 4 := by
  have hε4 : 0 ≤ ε / 4 := le_trans (abs_nonneg φ) hφ
  have h1 : |ρ * Real.sin φ| = ρ * |Real.sin φ| := by
    rw [abs_mul, abs_of_nonneg hρ0]
  have h2 : |Real.sin φ| ≤ ε / 4 := Real.abs_sin_le_abs.trans hφ
  have h3 : ρ * |Real.sin φ| ≤ ρ * (ε / 4) :=
    mul_le_mul_of_nonneg_left h2 hρ0
  have h4 : ρ * (ε / 4) ≤ rout * (ε / 4) :=
    mul_le_mul_of_nonneg_right hρ hε4
  calc |ρ * Real.sin φ| = ρ * |Real.sin φ| := h1
    _ ≤ ρ * (ε / 4) := h3
    _ ≤ rout * (ε / 4) := h4
    _ = rout * ε / 4 := by ring

end Paper3Ring
