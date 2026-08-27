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
