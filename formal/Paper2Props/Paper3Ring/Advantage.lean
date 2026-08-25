/-
Paper 3, second tranche: Lemma T2-I (hybrid telescoping — exact) and the
T3-P / T3-P″ defect theorems (docs/paper3/THEORY.md, "EXACT IDENTITY, not a
bound" and "Theorem T3-P").

  * `polRet`, `polTraj`, `prefixRet` — return of a Markov policy over n
                                    remaining steps from a step index, the
                                    closed-loop trajectory of a policy under
                                    deterministic dynamics, and the running
                                    reward of that trajectory.
  * `advantage`                   — the per-step advantage term A_t of T2-I:
                                    the truth-continuation value of the truth
                                    planner's action minus that of the blind
                                    planner's action, both evaluated at the
                                    blind trajectory's state s_t.
  * `t2i_hybrid_telescoping`      — **Lemma T2-I**: J(π_T) − J(π_B) =
                                    Σ_{t<H} A_t, exactly. The hybrid h_t
                                    (play π_B for steps < t, π_T after) is
                                    formalized and the telescope summed.
  * `clean_step_advantage_zero`   — a clean step (equal argmax actions on the
                                    shared candidate set) contributes EXACTLY
                                    0 — definitionally, as THEORY.md notes.
  * `t2i_sum_over_dirty`          — the identity restricted to the dirty
                                    steps: the sum over ALL steps equals the
                                    sum over the dirty ones, so all of
                                    play_cost lives on the dirty steps'
                                    advantage terms.
  * `t3p_defect`, `t3p_exact_of_no_funnel`,
    `t3p_double_prime`, `t3p_double_prime_exact_of_nondecreasing`
                                  — **Theorems T3-P and T3-P″**: one-sided
                                    monotonicity of r_int with the explicit
                                    defect f(γ₁) (T3-P), sharpened to the
                                    DROP [f(γ₁) − f(γ₂)]⁺ (T3-P″); exactness
                                    when f(γ₁) = 0, and — T3-P″'s qualitative
                                    consequence — whenever f is nondecreasing
                                    on the pair.

Honesty note (T3-P): the hypotheses named `hsplit` and `hdirect` are exactly
what THEORY.md's proof cites — the pathwise event decomposition
r_int = d + f (every interior entry is direct or funnel, exclusively) and
Proposition 7's conclusion d(γ₁) ≤ d(γ₂). Proposition 7's own pathwise engine
(the coupled-trajectory inclusion direct(γ₁) ⊆ direct(γ₂)) is triage item 3
in docs/paper3/FORMALIZATION.md, not this tranche; these theorems formalize
the step from Prop 7 to M1/M2-with-defect, which is where THEORY.md records
two earlier wrong routes (the c = r·κ factorisation trap, the pathwise M1
refuted by seed 50543).
-/
import Mathlib.Data.Real.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

namespace Paper3Ring

/-! ## Lemma T2-I: the hybrid telescoping identity -/

section T2I

variable {S A : Type*} (f : S → A → S) (r : S → A → ℝ)

/-- Return of following Markov policy `π` for `n` remaining steps, starting at
step index `t` in state `s` (deterministic dynamics `f`, reward `r`). -/
def polRet (π : S → ℕ → A) : ℕ → ℕ → S → ℝ
  | 0, _, _ => 0
  | n + 1, t, s => r s (π s t) + polRet π n (t + 1) (f s (π s t))

/-- Closed-loop trajectory of a Markov policy under the dynamics. -/
def polTraj (π : S → ℕ → A) (s₀ : S) : ℕ → S
  | 0 => s₀
  | t + 1 => f (polTraj π s₀ t) (π (polTraj π s₀ t) t)

/-- Running reward of the policy's own trajectory through step `t` (so
`prefixRet π s₀ H` is the episode return `J(π)` over horizon `H`). -/
def prefixRet (π : S → ℕ → A) (s₀ : S) : ℕ → ℝ
  | 0 => 0
  | t + 1 => prefixRet π s₀ t
      + r (polTraj f π s₀ t) (π (polTraj f π s₀ t) t)

variable (πB πT : S → ℕ → A) (s₀ : S)

/-- T2-I's advantage term `A_t`, evaluated at the blind trajectory's state
`s_t = polTraj f πB s₀ t`: the truth-continuation value of the truth action
`τ_t = πT s_t t` minus that of the blind action `b_t = πB s_t t`, with
`H − t − 1` steps remaining after step `t`. -/
def advantage (H t : ℕ) : ℝ :=
  (r (polTraj f πB s₀ t) (πT (polTraj f πB s₀ t) t)
      + polRet f r πT (H - t - 1) (t + 1)
          (f (polTraj f πB s₀ t) (πT (polTraj f πB s₀ t) t)))
    - (r (polTraj f πB s₀ t) (πB (polTraj f πB s₀ t) t)
      + polRet f r πT (H - t - 1) (t + 1)
          (f (polTraj f πB s₀ t) (πB (polTraj f πB s₀ t) t)))

/-- The hybrid: play `π_B` for steps `< t`, then `π_T` for the remaining
`H − t` steps. `hybrid 0 = J(π_T)` and `hybrid H = J(π_B)`. -/
def hybrid (H t : ℕ) : ℝ :=
  prefixRet f r πB s₀ t + polRet f r πT (H - t) t (polTraj f πB s₀ t)

/-- One hybrid difference is one advantage term: `h_t − h_{t+1} = A_t` for
`t < H` — the two returns share the `π_B` prefix through `s_t` and the `π_T`
continuation, differing only in the step-`t` action. -/
lemma hybrid_sub_succ {H t : ℕ} (ht : t < H) :
    hybrid f r πB πT s₀ H t - hybrid f r πB πT s₀ H (t + 1)
      = advantage f r πB πT s₀ H t := by
  have hHt : H - t = (H - t - 1) + 1 := by omega
  have hHt' : H - (t + 1) = H - t - 1 := by omega
  simp only [hybrid]
  rw [hHt, hHt']
  simp only [polRet, prefixRet, polTraj, advantage]
  ring

/-- **Lemma T2-I (hybrid telescoping — exact).**
`J(π_T) − J(π_B) = Σ_{t<H} A_t`: the whole return gap between the truth
planner and the blind planner is exactly the sum of the per-step advantage
terms along the blind trajectory. -/
theorem t2i_hybrid_telescoping (H : ℕ) :
    polRet f r πT H 0 s₀ - prefixRet f r πB s₀ H
      = ∑ t ∈ Finset.range H, advantage f r πB πT s₀ H t := by
  have htele : ∀ n ≤ H,
      hybrid f r πB πT s₀ H 0 - hybrid f r πB πT s₀ H n
        = ∑ t ∈ Finset.range n, advantage f r πB πT s₀ H t := by
    intro n hn
    induction n with
    | zero => simp
    | succ m ih =>
      rw [Finset.sum_range_succ, ← ih (by omega),
        ← hybrid_sub_succ f r πB πT s₀ (show m < H by omega)]
      ring
  have h0 : hybrid f r πB πT s₀ H 0 = polRet f r πT H 0 s₀ := by
    simp [hybrid, prefixRet, polTraj]
  have hH : hybrid f r πB πT s₀ H H = prefixRet f r πB s₀ H := by
    simp [hybrid, polRet]
  have := htele H le_rfl
  rw [h0, hH] at this
  exact this

/-- **A clean step contributes exactly 0**: when the two planners pick the
same action at `s_t`, the advantage term vanishes definitionally. -/
theorem clean_step_advantage_zero {H t : ℕ}
    (hclean : πT (polTraj f πB s₀ t) t = πB (polTraj f πB s₀ t) t) :
    advantage f r πB πT s₀ H t = 0 := by
  simp [advantage, hclean]

open Classical in
/-- **The identity localizes on the dirty steps**: the sum over all steps
equals the sum over the steps where the planners disagree — all of the return
gap (hence all of play_cost) lives on the dirty steps' advantage terms. -/
theorem t2i_sum_over_dirty (H : ℕ) :
    polRet f r πT H 0 s₀ - prefixRet f r πB s₀ H
      = ∑ t ∈ (Finset.range H).filter
          (fun t => πT (polTraj f πB s₀ t) t ≠ πB (polTraj f πB s₀ t) t),
          advantage f r πB πT s₀ H t := by
  rw [t2i_hybrid_telescoping]
  refine (Finset.sum_filter_of_ne ?_).symm
  intro t _ hne hclean
  exact hne (clean_step_advantage_zero f r πB πT s₀ hclean)

end T2I

/-! ## Theorems T3-P and T3-P″: one-sided monotonicity with an explicit defect

The rarity decomposition: every interior entry is DIRECT or FUNNEL,
exclusively, so `r_int = d + f` pointwise in γ (hypothesis `hsplit`);
Proposition 7 gives `d` nondecreasing (hypothesis `hdirect` — its pathwise
engine is a later tranche, see the header note). Everything below is what
THEORY.md derives from those two facts. -/

section T3P

variable {Γ : Type*} {rint d f : Γ → ℝ} {γ₁ γ₂ : Γ}

/-- **Theorem T3-P (one-sided monotonicity with an explicit defect).**
`r_int(γ₂) ≥ r_int(γ₁) − f(γ₁)`: any violation of monotonicity at the pair is
at most the funnel mass at the smaller gap. -/
theorem t3p_defect (hsplit : ∀ γ, rint γ = d γ + f γ)
    (hdirect : d γ₁ ≤ d γ₂) (hf₂ : 0 ≤ f γ₂) :
    rint γ₁ - f γ₁ ≤ rint γ₂ := by
  have h1 := hsplit γ₁
  have h2 := hsplit γ₂
  linarith

/-- **T3-P(c): exactness when the funnel is empty.** If `f(γ₁) = 0` then
monotonicity holds outright at the pair — the regime γ ≥ 3.2 where the
measured funnel mass is 0/50 000. -/
theorem t3p_exact_of_no_funnel (hsplit : ∀ γ, rint γ = d γ + f γ)
    (hdirect : d γ₁ ≤ d γ₂) (hf₂ : 0 ≤ f γ₂) (hf₁ : f γ₁ = 0) :
    rint γ₁ ≤ rint γ₂ := by
  have := t3p_defect hsplit hdirect hf₂
  linarith

/-- **Theorem T3-P″ (the defect is the DROP in f, not f).** Restoring the
term T3-P discards: `r_int(γ₂) ≥ r_int(γ₁) − [f(γ₁) − f(γ₂)]⁺` — strictly
stronger at no cost. Only a drop in the funnel mass can break monotonicity. -/
theorem t3p_double_prime (hsplit : ∀ γ, rint γ = d γ + f γ)
    (hdirect : d γ₁ ≤ d γ₂) :
    rint γ₁ - max (f γ₁ - f γ₂) 0 ≤ rint γ₂ := by
  have h1 := hsplit γ₁
  have h2 := hsplit γ₂
  rcases le_total (f γ₁ - f γ₂) 0 with h | h
  · rw [max_eq_right h]; linarith
  · rw [max_eq_left h]; linarith

/-- **T3-P″'s qualitative consequence: wherever f is nondecreasing the defect
is exactly zero** and M1 holds outright, with no bound on f needed — the whole
range γ ≤ 0.9, where the earlier bounds were weakest. -/
theorem t3p_double_prime_exact_of_nondecreasing
    (hsplit : ∀ γ, rint γ = d γ + f γ)
    (hdirect : d γ₁ ≤ d γ₂) (hff : f γ₁ ≤ f γ₂) :
    rint γ₁ ≤ rint γ₂ := by
  have h := t3p_double_prime hsplit hdirect
  have hmax : max (f γ₁ - f γ₂) 0 = 0 := max_eq_right (by linarith)
  linarith

end T3P

end Paper3Ring
