/-
Paper 3, fourth tranche: Propositions 10 and 11 — fence and patch
sufficiency (docs/paper3/THEORY.md, "Proposition 10", "Proposition 11").

Both results have the same skeleton: hypotheses about what the mitigation
guarantees at every REACHABLE real state (coverage/margin for the fences,
certificate coverage for the patch), and the conclusion that the mitigated
planner and the truth planner choose the same action at every real step —
real trajectories identical, play_cost exactly 0. This file formalizes the
skeleton once and instantiates it twice:

  * `loopTraj_eq_of_policy_agree`  — the loop engine: two policies that agree
                                     on an invariant set of the real
                                     environment produce identical closed
                                     loops (with the invariant carried along).
  * `maximizers`,
    `maximizers_transport`         — Prop 10's step (iii): if two return
                                     vectors agree on a candidate subset `C`
                                     and every candidate outside `C` is
                                     strictly dominated by some member of `C`
                                     under BOTH, the maximizer SETS coincide —
                                     so any deterministic tie-break (least
                                     index, the harness's) picks the same
                                     candidate.
  * `prop10_fence_sufficiency`,
    `prop10_play_cost_zero`        — **Proposition 10**: with (ii) and the
                                     dominance form of (COV)+(RG-west) as
                                     named hypotheses at every reachable
                                     state, the fence-mitigated argmax planner
                                     and the truth planner produce the same
                                     real trajectory; every return functional
                                     coincides.
  * `freezeTraj_eq_of_landing_mem_iff`
                                   — the coupling engine (Remark R2's
                                     "Lemma-3 coupling", generalized): two
                                     mode sets that agree on membership at
                                     every landing the trajectory queries
                                     produce the identical trajectory. The
                                     avoid-form engine of `DirectEntries` is
                                     the special case M₂ ⊆ M₁ with landings
                                     avoiding M₁.
  * `prop11_patch_sufficiency`,
    `prop11_play_cost_zero`        — **Proposition 11**: the patched model
                                     (freeze on the invented region `B` MINUS
                                     the certified neighborhood `N`) imagines
                                     identically to the truth model whenever
                                     no queried landing falls in the residue
                                     `B \ N` — (CERT) distilled — so the
                                     planner picks the same action at every
                                     reachable real state and play_cost is
                                     exactly 0.

Honesty notes. (1) The geometric step of Prop 10 — (COV) forcing every
crossing candidate's truncation, and (RG-west)'s measured margin turning
truncation into strict dominance — enters as the dominance hypotheses
`hdomM`/`hdomT`, exactly as THEORY.md presents them ((RG-west) is "checkable
over the visited envelope": a measured hypothesis, like T3-P's `hdirect`).
What is machine-checked is the theorem's content: dominance + agreement on
the non-crossing set at every reachable state ⟹ play_cost = 0 exactly.
(2) Both propositions' measured instances carry a learning transient
(episode 1's lessons; the certificate-collection prefix) that the theorems
do not and should not cover — the formal statements quantify over states
satisfying the coverage invariant, which is exactly the post-transient
regime.
-/
import Paper3Ring.PlannerLoop
import Mathlib.Data.Real.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Tactic.Linarith

namespace Paper3Ring

/-! ## The loop engine: policy agreement on an invariant -/

section LoopEngine

variable {σ A : Type*}

/-- Two policies that agree on an invariant set `P` of the environment
produce identical closed loops, and the loop stays in `P`. -/
theorem loopTraj_eq_of_policy_agree {step : A → σ → σ} {P : σ → Prop}
    {π₁ π₂ : σ → ℕ → A} {s₀ : σ}
    (hP₀ : P s₀) (hpres : ∀ a s, P s → P (step a s))
    (hagree : ∀ s t, P s → π₁ s t = π₂ s t) :
    ∀ t, loopTraj step π₁ s₀ t = loopTraj step π₂ s₀ t
      ∧ P (loopTraj step π₁ s₀ t) := by
  intro t
  induction t with
  | zero => exact ⟨rfl, hP₀⟩
  | succ n ih =>
    obtain ⟨heq, hP⟩ := ih
    refine ⟨?_, ?_⟩
    · simp only [loopTraj]
      rw [← heq, hagree _ n hP]
    · simp only [loopTraj]
      exact hpres _ _ hP

end LoopEngine

/-! ## Prop 10's argmax transport -/

section Argmax

variable {ι : Type*}

open Classical in
/-- The maximizer set of a return vector over a finite candidate set. A
deterministic argmax planner is any tie-break function of this set (the
harness's least-index rule is an instance). -/
noncomputable def maximizers (s : Finset ι) (V : ι → ℝ) : Finset ι :=
  s.filter fun i => ∀ j ∈ s, V j ≤ V i

open Classical in
lemma mem_maximizers {s : Finset ι} {V : ι → ℝ} {i : ι} :
    i ∈ maximizers s V ↔ i ∈ s ∧ ∀ j ∈ s, V j ≤ V i := by
  simp [maximizers]

/-- One direction of the transport, factored out: under agreement on `C` and
double dominance, a `V₁`-maximizer is a `V₂`-maximizer. -/
private lemma maximizers_subset_of_agree {s C : Finset ι} {V₁ V₂ : ι → ℝ}
    (hCs : C ⊆ s)
    (hC : ∀ i ∈ C, V₁ i = V₂ i)
    (hdom₁ : ∀ i ∈ s, i ∉ C → ∃ c ∈ C, V₁ i < V₁ c)
    (hdom₂ : ∀ i ∈ s, i ∉ C → ∃ c ∈ C, V₂ i < V₂ c) :
    maximizers s V₁ ⊆ maximizers s V₂ := by
  intro i hi
  obtain ⟨his, hmax⟩ := mem_maximizers.mp hi
  have hiC : i ∈ C := by
    by_contra hiC
    obtain ⟨c, hcC, hlt⟩ := hdom₁ i his hiC
    exact absurd (hmax c (hCs hcC)) (not_le.mpr hlt)
  refine mem_maximizers.mpr ⟨his, fun j hjs => ?_⟩
  by_cases hjC : j ∈ C
  · rw [← hC j hjC, ← hC i hiC]
    exact hmax j hjs
  · obtain ⟨c, hcC, hlt⟩ := hdom₂ j hjs hjC
    have h₁ : V₂ c = V₁ c := (hC c hcC).symm
    have h₂ : V₁ c ≤ V₁ i := hmax c (hCs hcC)
    have h₃ : V₁ i = V₂ i := hC i hiC
    linarith

/-- **Argmax transport (Prop 10, step (iii)).** If the two return vectors
agree on `C` and every candidate outside `C` is strictly dominated by a
member of `C` under both, the maximizer sets coincide — so ANY deterministic
tie-break selects the same candidate under both models. -/
theorem maximizers_transport {s C : Finset ι} {V₁ V₂ : ι → ℝ}
    (hCs : C ⊆ s)
    (hC : ∀ i ∈ C, V₁ i = V₂ i)
    (hdom₁ : ∀ i ∈ s, i ∉ C → ∃ c ∈ C, V₁ i < V₁ c)
    (hdom₂ : ∀ i ∈ s, i ∉ C → ∃ c ∈ C, V₂ i < V₂ c) :
    maximizers s V₁ = maximizers s V₂ :=
  Finset.Subset.antisymm
    (maximizers_subset_of_agree hCs hC hdom₁ hdom₂)
    (maximizers_subset_of_agree hCs (fun i hi => (hC i hi).symm) hdom₂ hdom₁)

end Argmax

/-! ## Proposition 10: fence sufficiency -/

section Prop10

variable {σ A ι : Type*}

/-- **Proposition 10 (fence sufficiency).** The planner selects, at each real
state, a candidate by an arbitrary deterministic tie-break over the maximizer
set of imagined returns. Hypotheses, at every state of the reachable
envelope `P`: the mitigated and truth imagined returns agree on the
non-crossing candidates `C s` (step (ii)), and every crossing candidate is
strictly dominated by a non-crossing one under both models (the dominance
form of (COV) + (RG-west)). Then the mitigated planner and the truth planner
produce the IDENTICAL real trajectory. -/
theorem prop10_fence_sufficiency {step : A → σ → σ} {P : σ → Prop} {s₀ : σ}
    (hP₀ : P s₀) (hpres : ∀ a s, P s → P (step a s))
    (cand : Finset ι) (act : ι → A) (tiebreak : Finset ι → ι)
    (Vmit Vtruth : σ → ι → ℝ) (C : σ → Finset ι)
    (hCs : ∀ s, C s ⊆ cand)
    (hagree : ∀ s, P s → ∀ i ∈ C s, Vmit s i = Vtruth s i)
    (hdomM : ∀ s, P s → ∀ i ∈ cand, i ∉ C s → ∃ c ∈ C s, Vmit s i < Vmit s c)
    (hdomT : ∀ s, P s → ∀ i ∈ cand, i ∉ C s →
      ∃ c ∈ C s, Vtruth s i < Vtruth s c) :
    ∀ t, loopTraj step (fun s _ => act (tiebreak (maximizers cand (Vmit s)))) s₀ t
      = loopTraj step (fun s _ => act (tiebreak (maximizers cand (Vtruth s)))) s₀ t := by
  intro t
  refine (loopTraj_eq_of_policy_agree hP₀ hpres (fun s _ hP => ?_) t).1
  rw [maximizers_transport (hCs s) (hagree s hP) (hdomM s hP) (hdomT s hP)]

/-- **play_cost of the mitigated planner is exactly 0** (Prop 10's
conclusion): every return functional of the real trajectory coincides with
the truth planner's. -/
theorem prop10_play_cost_zero {β : Type*} (J : (ℕ → σ) → β)
    {step : A → σ → σ} {P : σ → Prop} {s₀ : σ}
    (hP₀ : P s₀) (hpres : ∀ a s, P s → P (step a s))
    (cand : Finset ι) (act : ι → A) (tiebreak : Finset ι → ι)
    (Vmit Vtruth : σ → ι → ℝ) (C : σ → Finset ι)
    (hCs : ∀ s, C s ⊆ cand)
    (hagree : ∀ s, P s → ∀ i ∈ C s, Vmit s i = Vtruth s i)
    (hdomM : ∀ s, P s → ∀ i ∈ cand, i ∉ C s → ∃ c ∈ C s, Vmit s i < Vmit s c)
    (hdomT : ∀ s, P s → ∀ i ∈ cand, i ∉ C s →
      ∃ c ∈ C s, Vtruth s i < Vtruth s c) :
    J (loopTraj step (fun s _ => act (tiebreak (maximizers cand (Vmit s)))) s₀)
      = J (loopTraj step (fun s _ => act (tiebreak (maximizers cand (Vtruth s)))) s₀) :=
  congrArg J (funext (prop10_fence_sufficiency hP₀ hpres cand act tiebreak
    Vmit Vtruth C hCs hagree hdomM hdomT))

end Prop10

/-! ## The coupling engine, and Proposition 11: patch sufficiency -/

section Prop11

variable {E : Type*} [PseudoMetricSpace E]
variable {σ : Type*} {pos : σ → E} {F : ℕ → σ → σ} {freeze : σ → σ}

omit [PseudoMetricSpace E] in
/-- **The coupling engine (Remark R2's "Lemma-3 coupling", generalized).**
Two mode sets that AGREE ON MEMBERSHIP at every landing the trajectory
queries produce the identical trajectory: the freeze fires at exactly the
same steps. `DirectEntries.freezeTraj_eq_of_avoid` is the special case
`M₂ ⊆ M₁` with all landings avoiding `M₁`. -/
lemma freezeTraj_eq_of_landing_mem_iff {M₁ M₂ : Set E} {s₀ : σ} {T : ℕ}
    (hiff : ∀ t < T,
      (pos (F t (freezeTraj pos F freeze M₁ s₀ t)) ∈ M₁
        ↔ pos (F t (freezeTraj pos F freeze M₁ s₀ t)) ∈ M₂)) :
    ∀ t ≤ T, freezeTraj pos F freeze M₂ s₀ t
      = freezeTraj pos F freeze M₁ s₀ t := by
  intro t
  induction t with
  | zero => exact fun _ => rfl
  | succ n ih =>
    intro hT
    have heq := ih (by omega)
    have hif := hiff n (by omega)
    rw [freezeTraj_succ, freezeTraj_succ, heq]
    by_cases h : pos (F n (freezeTraj pos F freeze M₁ s₀ n)) ∈ M₁
    · rw [if_pos (hif.mp h), if_pos h]
    · rw [if_neg (fun h₂ => h (hif.mpr h₂)), if_neg h]

omit [PseudoMetricSpace E] in
/-- **Proposition 5 (r is nonincreasing in γ), realization core.** Shrinking
the wall preserves firing: if the `M₂`-system's trajectory ever lands in
`M₂ ⊆ M₁`, the `M₁`-system's trajectory (same realizations — same tentative
steps) lands in `M₁` at the same step or earlier. One application of the
coupling engine unifies THEORY.md's two cases: take the FIRST step `w` at
which the `M₂`-trajectory's landing is in `M₁` (the firing landing is one);
before `w` the landings are in neither set, so the two trajectories agree
through `w`, and the `M₁`-trajectory's landing at `w` is the same point. The
measure wrapper (pathwise fire(γ₂) ⊆ fire(γ₁) ⟹ r(γ₂) ≤ r(γ₁) over seeds)
is monotonicity of a measure under inclusion, noted as everywhere in the
package. -/
theorem prop5_fire_monotone {M₁ M₂ : Set E} (hsub : M₂ ⊆ M₁) {s₀ : σ} {t : ℕ}
    (hfire : pos (F t (freezeTraj pos F freeze M₂ s₀ t)) ∈ M₂) :
    ∃ u ≤ t, pos (F u (freezeTraj pos F freeze M₁ s₀ u)) ∈ M₁ := by
  classical
  have hex : ∃ u, pos (F u (freezeTraj pos F freeze M₂ s₀ u)) ∈ M₁ :=
    ⟨t, hsub hfire⟩
  set w := Nat.find hex with hw_def
  have hw : pos (F w (freezeTraj pos F freeze M₂ s₀ w)) ∈ M₁ :=
    Nat.find_spec hex
  have hwt : w ≤ t := Nat.find_min' hex (hsub hfire)
  have heq : ∀ u ≤ w, freezeTraj pos F freeze M₁ s₀ u
      = freezeTraj pos F freeze M₂ s₀ u := by
    apply freezeTraj_eq_of_landing_mem_iff
    intro u hu
    have hnot := Nat.find_min hex hu
    exact ⟨fun h₂ => absurd (hsub h₂) hnot, fun h₁ => absurd h₁ hnot⟩
  refine ⟨w, hwt, ?_⟩
  rw [heq w le_rfl]
  exact hw

variable {A I : Type*}

omit [PseudoMetricSpace E] in
/-- **Proposition 11 (patch sufficiency — the dual).** The truth freezes on
`Mt`; the invented-mode model additionally freezes on `B` (where the truth
moves freely); the freedom patch removes the invented freeze on the certified
neighborhood `N`, leaving the patched mode set `Mt ∪ (B \ N)`. Hypothesis
(CERT), distilled to what the proof uses: from every reachable real state, no
candidate's patched-imagination landing falls in the residue `B \ N`. Then
the patched model imagines identically to the truth model for every
candidate, the planner — any deterministic function of the imagined rollouts
— picks the same action at every reachable real state, and the real
closed-loop trajectories are identical. -/
theorem prop11_patch_sufficiency {G : A → σ → σ} {Mt B N : Set E}
    (Fc : I → ℕ → σ → σ) (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    {P : σ → Prop} {s₀ : σ}
    (hP₀ : P s₀)
    (hpres : ∀ a s, P s → P (freezeStep pos G freeze Mt a s))
    (hcert : ∀ s, P s → ∀ i t,
      pos (Fc i t (freezeTraj pos (Fc i) freeze (Mt ∪ (B \ N)) s t)) ∉ B \ N) :
    ∀ t, loopTraj (freezeStep pos G freeze Mt)
          (plannerPolicy pos freeze Fc plan (Mt ∪ (B \ N))) s₀ t
        = loopTraj (freezeStep pos G freeze Mt)
          (plannerPolicy pos freeze Fc plan Mt) s₀ t := by
  intro t
  refine (loopTraj_eq_of_policy_agree hP₀ (fun a s hP => hpres a s hP)
    (fun s _ hP => ?_) t).1
  unfold plannerPolicy
  congr 1
  funext i
  refine funext fun τ => ?_
  refine (freezeTraj_eq_of_landing_mem_iff (T := τ) (fun u _ => ?_) τ le_rfl).symm
  constructor
  · rintro (hMt | hBN)
    · exact hMt
    · exact absurd hBN (hcert s hP i u)
  · exact fun hMt => Or.inl hMt

omit [PseudoMetricSpace E] in
/-- **play_cost of the patched model is exactly 0** (Prop 11's conclusion). -/
theorem prop11_play_cost_zero {β : Type*} (J : (ℕ → σ) → β)
    {G : A → σ → σ} {Mt B N : Set E}
    (Fc : I → ℕ → σ → σ) (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    {P : σ → Prop} {s₀ : σ}
    (hP₀ : P s₀)
    (hpres : ∀ a s, P s → P (freezeStep pos G freeze Mt a s))
    (hcert : ∀ s, P s → ∀ i t,
      pos (Fc i t (freezeTraj pos (Fc i) freeze (Mt ∪ (B \ N)) s t)) ∉ B \ N) :
    J (loopTraj (freezeStep pos G freeze Mt)
        (plannerPolicy pos freeze Fc plan (Mt ∪ (B \ N))) s₀)
      = J (loopTraj (freezeStep pos G freeze Mt)
        (plannerPolicy pos freeze Fc plan Mt) s₀) :=
  congrArg J (funext (prop11_patch_sufficiency Fc plan hP₀ hpres hcert))

end Prop11

end Paper3Ring
