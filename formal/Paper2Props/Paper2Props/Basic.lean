/-
Formalization of paper 2's risk-factorization proposition (`prop:risk`), including a
machine-checked counterexample to the PRE-correction clause.

Why this exists: the second external review found three propositions whose hand-written
proofs were wrong, in a manuscript whose 700-value numeric audit passed. The cheap guard
for that class is the exact-arithmetic counterexample search in
`tests/test_proposition_falsification.py`; this is the expensive guard on the same
statements — under a checker, a false "in particular" does not compile.

Contents:
  * `danger_eq_setIntegral` — D = E[X·1_G] equals the set integral (the definition).
  * `covariance_expansion`  — E[(X−E X)(1_G−P G)] = ∫_G X − E[X]·P(G).
  * `risk_factorizes_iff`   — the factored form holds ⟺ that covariance vanishes
                              (the proposition's core).
  * `factored_of_const`     — corrected sufficient condition: a globally constant X
                              (the single fixed blind model) factorizes.
  * `old_clause_is_false`   — the pre-correction clause refuted: a fair coin with
                              X constant ON the acceptance event where the factored form
                              fails. The reviewer's counterexample, machine-checked.
-/
import Mathlib

open MeasureTheory
open scoped ENNReal

noncomputable section

variable {Ω : Type*} [MeasurableSpace Ω] (μ : Measure Ω) [IsProbabilityMeasure μ]

/-- The danger estimand at a fixed pipeline output: `D = E[X · 1_G]`, with `X` the shipped
cost and `G` the acceptance event. -/
def danger (X : Ω → ℝ) (G : Set Ω) : ℝ := ∫ ω, G.indicator X ω ∂μ

lemma danger_eq_setIntegral (X : Ω → ℝ) {G : Set Ω} (hG : MeasurableSet G) :
    danger μ X G = ∫ ω in G, X ω ∂μ := by
  simpa [danger] using integral_indicator (f := X) hG

/-- The covariance expansion the proposition's proof rests on:
`E[(X − E X)·(1_G − P(G))] = ∫_G X − E[X]·P(G)`. -/
lemma covariance_expansion (X : Ω → ℝ) (hX : Integrable X μ)
    {G : Set Ω} (hG : MeasurableSet G) :
    ∫ ω, (X ω - ∫ x, X x ∂μ) * (G.indicator (fun _ => (1 : ℝ)) ω - (μ G).toReal) ∂μ
      = (∫ ω in G, X ω ∂μ) - (∫ ω, X ω ∂μ) * (μ G).toReal := by
  set c : ℝ := ∫ x, X x ∂μ with hc
  set p : ℝ := (μ G).toReal with hp
  have hXG : Integrable (G.indicator X) μ := hX.indicator hG
  have h1G : Integrable (G.indicator (fun _ => (1 : ℝ))) μ :=
    (integrable_const (1 : ℝ)).indicator hG
  have expand : ∀ ω,
      (X ω - c) * (G.indicator (fun _ => (1 : ℝ)) ω - p)
        = (G.indicator X ω - p * X ω) - (c * G.indicator (fun _ => (1 : ℝ)) ω - c * p) := by
    intro ω
    by_cases hω : ω ∈ G <;> simp [Set.indicator_apply, hω] <;> ring
  have h₁ : Integrable (fun ω => G.indicator X ω - p * X ω) μ := hXG.sub (hX.const_mul p)
  have h₂ : Integrable (fun ω => c * G.indicator (fun _ => (1 : ℝ)) ω - c * p) μ :=
    (h1G.const_mul c).sub (integrable_const (c * p))
  calc
    ∫ ω, (X ω - c) * (G.indicator (fun _ => (1 : ℝ)) ω - p) ∂μ
        = ∫ ω, ((G.indicator X ω - p * X ω) -
                (c * G.indicator (fun _ => (1 : ℝ)) ω - c * p)) ∂μ :=
          integral_congr_ae (Filter.Eventually.of_forall expand)
    _ = ((∫ ω, G.indicator X ω ∂μ) - p * ∫ ω, X ω ∂μ) -
          (c * (∫ ω, G.indicator (fun _ => (1 : ℝ)) ω ∂μ) - c * p) := by
          rw [integral_sub h₁ h₂, integral_sub hXG (hX.const_mul p),
              integral_sub (h1G.const_mul c) (integrable_const (c * p)),
              integral_const_mul, integral_const_mul, integral_const]
          simp [measure_univ, smul_eq_mul]
    _ = ((∫ ω in G, X ω ∂μ) - p * c) - (c * p - c * p) := by
          rw [integral_indicator hG, integral_indicator hG]
          simp [hc, hp, setIntegral_const, smul_eq_mul, mul_comm]
          exact Or.inl rfl
    _ = (∫ ω in G, X ω ∂μ) - c * p := by ring
    _ = (∫ ω in G, X ω ∂μ) - (∫ ω, X ω ∂μ) * (μ G).toReal := by rw [hc, hp]

/-- **prop:risk, the core iff**: the factored form `D = E[X]·P(G)` holds exactly when the
covariance of the shipped cost with the acceptance indicator vanishes. -/
theorem risk_factorizes_iff (X : Ω → ℝ) (hX : Integrable X μ)
    {G : Set Ω} (hG : MeasurableSet G) :
    danger μ X G = (∫ ω, X ω ∂μ) * (μ G).toReal ↔
    ∫ ω, (X ω - ∫ x, X x ∂μ) * (G.indicator (fun _ => (1 : ℝ)) ω - (μ G).toReal) ∂μ = 0 := by
  rw [covariance_expansion μ X hX hG, danger_eq_setIntegral μ X hG, sub_eq_zero]

/-- The corrected sufficient condition: a GLOBALLY constant cost factorizes. This is the
"single fixed blind model" case of the hand-written instruments. -/
theorem factored_of_const (c : ℝ) {G : Set Ω} (hG : MeasurableSet G) :
    danger μ (fun _ => c) G = (∫ _ω, c ∂μ) * (μ G).toReal := by
  rw [danger_eq_setIntegral μ _ hG]
  simp [smul_eq_mul, mul_comm, Measure.real]

/- ------------------------------------------------------------------------------------
   The counterexample to the PRE-correction clause, machine-checked.

   Old claim (FALSE): "X almost surely constant on G" suffices for the factored form.
   Space: Bool with the fair coin; G = {true}; X = 1_G.
   X is constant (= 1) on G, yet D = 1/2 while E[X]·P(G) = 1/4.
   ------------------------------------------------------------------------------------ -/

/-- The fair coin on `Bool`. -/
def coin : Measure Bool := (2 : ℝ≥0∞)⁻¹ • (Measure.dirac true + Measure.dirac false)

instance : IsProbabilityMeasure coin := by
  constructor
  simp only [coin, Measure.smul_apply, Measure.add_apply, Measure.dirac_apply_of_mem,
    Set.mem_univ, smul_eq_mul]
  rw [show (1 : ℝ≥0∞) + 1 = 2 by norm_num, ENNReal.inv_mul_cancel] <;> norm_num

/-- The indicator cost of the counterexample. -/
def Xce : Bool → ℝ := fun ω => if ω then 1 else 0

lemma coin_integral (f : Bool → ℝ) : ∫ ω, f ω ∂coin = (f true + f false) / 2 := by
  have h1 : Integrable f (Measure.dirac true) := .of_finite
  have h2 : Integrable f (Measure.dirac false) := .of_finite
  rw [coin, integral_smul_measure, integral_add_measure h1 h2, integral_dirac,
      integral_dirac]
  simp only [ENNReal.toReal_inv, ENNReal.toReal_ofNat, smul_eq_mul]
  ring

lemma coin_true : (coin {true}).toReal = 1 / 2 := by
  simp [coin, Measure.smul_apply, Measure.add_apply, Measure.dirac_apply]

/-- **The pre-correction clause is false**: `X` constant on `G` does not give the factored
form. This is the reviewer's counterexample as a theorem. -/
theorem old_clause_is_false :
    (∀ ω ∈ ({true} : Set Bool), Xce ω = 1) ∧
      danger coin Xce {true} ≠ (∫ ω, Xce ω ∂coin) * (coin {true}).toReal := by
  constructor
  · intro ω hω; simp [Set.mem_singleton_iff] at hω; simp [Xce, hω]
  · have hind : ({true} : Set Bool).indicator Xce = Xce := by
      funext ω; cases ω <;> simp [Xce]
    have hD : danger coin Xce {true} = 1 / 2 := by
      rw [danger, hind, coin_integral]; simp [Xce]
    have hE : ∫ ω, Xce ω ∂coin = 1 / 2 := by rw [coin_integral]; simp [Xce]
    rw [hD, hE, coin_true]
    norm_num

end
