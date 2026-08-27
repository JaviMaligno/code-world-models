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
import Mathlib.Tactic.Linarith

namespace Paper3Ring

open intervalIntegral

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

end Paper3Ring
