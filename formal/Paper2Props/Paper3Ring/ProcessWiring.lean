/-
Paper 3, ninth tranche: the freeze-trajectory map is measurable in the
action sequence — the last technical hypothesis of Theorem T4's wiring.

`CapBound.pi_union_slice_bound` composes the h-step modulus from
(a) measurability of the per-step events and (b) the per-slice bound. This
file supplies (a): the trajectory of the freeze dynamics, driven through an
action-indexed tentative step `G`, is a measurable function of the action
sequence — an induction over the freeze branches with `Measurable.ite` —
and so are the landing map and every landing event.

  * `measurable_freezeTraj_param` — ω ↦ freezeTraj with steps `G (ω k)` is
                                    measurable for every time t.
  * `measurable_landing_param`    — so is the landing map
                                    ω ↦ pos (G (ω t) (traj ω t)).
  * `measurableSet_landing_event` — and every landing event
                                    {ω | landing ∈ D} is measurable.

Everything is stated over ω : ℕ → ℝ with the product σ-algebra; the
`Fin h → ℝ` version used by `pi_union_slice_bound` follows by composing
with a coordinate-extension map. With this, Theorem T4's remaining gap is
the single per-slice computation (landing ∈ sliver ⟹ rotated-strip event
through `lemmaS_landing_eq`, `lemmaW_sliver_in_strip`,
`lemmaA_part_i_rotated`) — geometry already proved, wiring only.
-/
import Paper3Ring.Basic
import Mathlib.MeasureTheory.Constructions.BorelSpace.Basic

namespace Paper3Ring

section ProcessMeasurability

variable {E σ : Type*} [MeasurableSpace E] [MeasurableSpace σ]
variable {pos : σ → E} {freeze : σ → σ} {M : Set E} {s₀ : σ}
variable {G : ℝ → σ → σ}

/-- **The freeze trajectory is measurable in the action sequence.** With a
measurable position projection, freeze map, mode set, and (jointly
measurable) action-indexed tentative step, the map
`ω ↦ freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ t` is measurable for
every `t` — an induction over the freeze branches. -/
theorem measurable_freezeTraj_param
    (hpos : Measurable pos) (hfreeze : Measurable freeze)
    (hM : MeasurableSet M)
    (hG : Measurable fun p : ℝ × σ => G p.1 p.2) (t : ℕ) :
    Measurable fun ω : ℕ → ℝ =>
      freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ t := by
  classical
  induction t with
  | zero =>
    simp only [freezeTraj]
    exact measurable_const
  | succ n ih =>
    have hΨ : Measurable fun ω : ℕ → ℝ =>
        G (ω n) (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ n) :=
      hG.comp ((measurable_pi_apply n).prodMk ih)
    have hC : MeasurableSet {ω : ℕ → ℝ |
        pos (G (ω n) (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ n))
          ∈ M} := (hpos.comp hΨ) hM
    have hgoal : (fun ω : ℕ → ℝ =>
        freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ (n + 1))
        = fun ω : ℕ → ℝ =>
          if pos (G (ω n)
              (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ n)) ∈ M
          then freeze (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ n)
          else G (ω n)
            (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ n) := by
      funext ω
      exact freezeTraj_succ pos (fun k s => G (ω k) s) freeze M s₀ n
    rw [hgoal]
    exact Measurable.ite hC (hfreeze.comp ih) hΨ

/-- **The landing map is measurable in the action sequence.** -/
theorem measurable_landing_param
    (hpos : Measurable pos) (hfreeze : Measurable freeze)
    (hM : MeasurableSet M)
    (hG : Measurable fun p : ℝ × σ => G p.1 p.2) (t : ℕ) :
    Measurable fun ω : ℕ → ℝ =>
      pos (G (ω t)
        (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ t)) :=
  hpos.comp (hG.comp ((measurable_pi_apply t).prodMk
    (measurable_freezeTraj_param hpos hfreeze hM hG t)))

/-- **Every landing event is measurable**: `{ω | landing_t(ω) ∈ D}` is a
measurable set of action sequences, for every measurable target `D` — the
form `pi_union_slice_bound` consumes. -/
theorem measurableSet_landing_event
    (hpos : Measurable pos) (hfreeze : Measurable freeze)
    (hM : MeasurableSet M) {D : Set E} (hD : MeasurableSet D)
    (hG : Measurable fun p : ℝ × σ => G p.1 p.2) (t : ℕ) :
    MeasurableSet {ω : ℕ → ℝ |
      pos (G (ω t)
        (freezeTraj pos (fun k s => G (ω k) s) freeze M s₀ t)) ∈ D} :=
  (measurable_landing_param hpos hfreeze hM hG t) hD

end ProcessMeasurability

end Paper3Ring
