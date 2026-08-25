/-
Paper 3, third tranche: Proposition 7 — direct entries are pathwise monotone
(docs/paper3/THEORY.md, "Proposition 7").

The paper's proof is one induction: a trajectory that is direct at γ₁ (no
landing in the wall A(γ₁) before its interior entry) has landings avoiding
A(γ₁) ⊇ A(γ₂), so under the smaller wall it is UNCHANGED — same entry, still
direct. This file machine-checks exactly that, with the induction stated once
at full generality and Prop 7 as transport along it:

  * `freezeTraj_eq_of_avoid`      — the engine: if `M₂ ⊆ M₁` and the
                                    `M₁`-trajectory's tentative landings avoid
                                    `M₁` before `T`, the `M₂`-trajectory is
                                    identical through `T` (Lemma-3-style
                                    induction, any mode sets).
  * `entersDirectlyAt`            — direct interior entry at horizon `T`: the
                                    position at `T` is strictly inside the
                                    hole and no tentative landing before `T`
                                    is in the mode (no freeze fires before
                                    entry).
  * `prop7_direct_monotone`       — **Proposition 7**: `M₂ ⊆ M₁` transports a
                                    direct entry at `M₁` to a direct entry at
                                    `M₂`, same horizon, same trajectory.
                                    Instantiated at the instrument's knob:
                                    γ₁ ≤ γ₂ gives A(γ₂) ⊆ A(γ₁), so
                                    direct(γ₁) ⊆ direct(γ₂) pathwise.
  * `prop7_first_entry_preserved` — minimality transports too: a direct FIRST
                                    entry at `M₁` is a direct first entry at
                                    `M₂` (the trajectories agree through `T`).
  * `direct_entry_traj_is_free`   — a direct trajectory IS the free
                                    trajectory through its entry (the `M₂ = ∅`
                                    case of the engine).
  * `no_wall_every_entry_direct`  — with no wall every entry is direct: the
                                    d(2π) = r_int(2π) endpoint of Prop 7.
  * `channelMode_antitone`,
    `prop7_channel`               — the knob instantiation: the wall
                                    A(γ) = annulus \ S(γ) is antitone in γ for
                                    ANY monotone sector family `S`, and Prop 7
                                    specializes to γ₁ ≤ γ₂. The instrument's
                                    concrete `S` (the angular sector of width
                                    γ about the channel center) is monotone in
                                    γ by construction; keeping `S` abstract is
                                    deliberate — nothing in the proof uses its
                                    shape, exactly as the paper says.

What this discharges elsewhere: the T3-P / T3-P″ theorems in
`Advantage.lean` take Prop 7's conclusion as the hypothesis `hdirect`
(d(γ₁) ≤ d(γ₂) over the measured rarities). This file proves the pathwise
inclusion that conclusion rests on; the step from the inclusion to the
inequality of the two d-values is the measure wrapper (monotonicity of a
measure under set inclusion over seed realizations), which as everywhere in
this package adds only a.s.-quantification and is noted, not formalized.

Honesty note: THEORY.md's counterexample (seed 50543) shows the FULL-entry
pathwise inclusion is false — only the direct component transports. That is
visible here: `prop7_direct_monotone` needs `havoid`; without it the
induction has no invariant, and no theorem of this file mentions full
entries.
-/
import Paper3Ring.Basic

namespace Paper3Ring

variable {E : Type*} [PseudoMetricSpace E]
variable {σ : Type*} {pos : σ → E} {F : ℕ → σ → σ} {freeze : σ → σ}

omit [PseudoMetricSpace E] in
/-- **The engine (Lemma-3-style induction).** Freeze-free prefixes are
mode-set monotone: if `M₂ ⊆ M₁` and the `M₁`-trajectory's tentative landings
avoid `M₁` at every step before `T`, then the `M₂`-trajectory is identical
through `T` — neither mode ever fires, so both follow the free steps. -/
lemma freezeTraj_eq_of_avoid {M₁ M₂ : Set E} (hsub : M₂ ⊆ M₁) {s₀ : σ} {T : ℕ}
    (havoid : ∀ t < T, pos (F t (freezeTraj pos F freeze M₁ s₀ t)) ∉ M₁) :
    ∀ t ≤ T, freezeTraj pos F freeze M₂ s₀ t
      = freezeTraj pos F freeze M₁ s₀ t := by
  intro t
  induction t with
  | zero => exact fun _ => rfl
  | succ n ih =>
    intro hT
    have heq := ih (by omega)
    have hnot₁ := havoid n (by omega)
    have hnot₂ : pos (F n (freezeTraj pos F freeze M₂ s₀ n)) ∉ M₂ := by
      rw [heq]
      exact fun h => hnot₁ (hsub h)
    rw [freezeTraj_succ, freezeTraj_succ, if_neg hnot₂, if_neg hnot₁, heq]

/-- Direct interior entry at horizon `T` under mode set `M`: the trajectory's
position at `T` is strictly inside the hole (`dist < rIn`) and no tentative
landing before `T` is in the mode — no freeze fires before the entry. -/
def entersDirectlyAt (pos : σ → E) (F : ℕ → σ → σ) (freeze : σ → σ)
    (M : Set E) (c : E) (rIn : ℝ) (s₀ : σ) (T : ℕ) : Prop :=
  dist (pos (freezeTraj pos F freeze M s₀ T)) c < rIn ∧
  ∀ t < T, pos (F t (freezeTraj pos F freeze M s₀ t)) ∉ M

/-- **Proposition 7 (direct entries are pathwise monotone).** Shrinking the
wall preserves a direct entry: if `M₂ ⊆ M₁` and the trajectory enters
directly at `M₁` by time `T`, it enters directly at `M₂` at the same `T` —
with the same trajectory, by `freezeTraj_eq_of_avoid`. At the instrument's
knob (`prop7_channel` below) this is direct(γ₁) ⊆ direct(γ₂) for γ₁ ≤ γ₂:
the direct component of interior entry is pathwise nondecreasing in the
channel width, so ALL non-monotone risk lives in the funnel component. -/
theorem prop7_direct_monotone {M₁ M₂ : Set E} (hsub : M₂ ⊆ M₁)
    {c : E} {rIn : ℝ} {s₀ : σ} {T : ℕ}
    (h : entersDirectlyAt pos F freeze M₁ c rIn s₀ T) :
    entersDirectlyAt pos F freeze M₂ c rIn s₀ T := by
  obtain ⟨hentry, havoid⟩ := h
  have heq := freezeTraj_eq_of_avoid hsub havoid
  refine ⟨?_, ?_⟩
  · rw [heq T le_rfl]
    exact hentry
  · intro t ht
    rw [heq t ht.le]
    exact fun hmem => havoid t ht (hsub hmem)

/-- **Minimality transports too**: a direct FIRST entry at `M₁` (no earlier
step is inside the hole) is a direct first entry at `M₂` — the trajectories
agree through `T`, so every earlier position is the same. "Same entry, still
direct", including that it is still the first. -/
theorem prop7_first_entry_preserved {M₁ M₂ : Set E} (hsub : M₂ ⊆ M₁)
    {c : E} {rIn : ℝ} {s₀ : σ} {T : ℕ}
    (h : entersDirectlyAt pos F freeze M₁ c rIn s₀ T)
    (hmin : ∀ t < T, ¬ dist (pos (freezeTraj pos F freeze M₁ s₀ t)) c < rIn) :
    entersDirectlyAt pos F freeze M₂ c rIn s₀ T ∧
      ∀ t < T, ¬ dist (pos (freezeTraj pos F freeze M₂ s₀ t)) c < rIn := by
  have heq := freezeTraj_eq_of_avoid hsub h.2
  refine ⟨prop7_direct_monotone hsub h, fun t ht => ?_⟩
  rw [heq t ht.le]
  exact hmin t ht

/-- **A direct trajectory is the free trajectory through its entry** — the
`M₂ = ∅` case of the engine: with landings avoiding the mode, the freeze
dynamics and the mode-free dynamics coincide. -/
theorem direct_entry_traj_is_free {M : Set E} {c : E} {rIn : ℝ} {s₀ : σ}
    {T : ℕ} (h : entersDirectlyAt pos F freeze M c rIn s₀ T) :
    ∀ t ≤ T, freezeTraj pos F freeze (∅ : Set E) s₀ t
      = freezeTraj pos F freeze M s₀ t :=
  freezeTraj_eq_of_avoid (Set.empty_subset M) h.2

/-- **With no wall, every entry is direct** — the endpoint d(2π) = r_int(2π):
avoidance of the empty mode set is vacuous. -/
theorem no_wall_every_entry_direct {c : E} {rIn : ℝ} {s₀ : σ} {T : ℕ}
    (hentry : dist (pos (freezeTraj pos F freeze (∅ : Set E) s₀ T)) c < rIn) :
    entersDirectlyAt pos F freeze (∅ : Set E) c rIn s₀ T :=
  ⟨hentry, fun _ _ hmem => Set.notMem_empty _ hmem⟩

/-- The channel wall A(γ) = annulus \ S(γ) is ANTITONE in the channel width
for any monotone sector family `S`: widening the channel only removes wall.
Nothing uses the sector's shape. -/
lemma channelMode_antitone (c : E) (rIn rOut : ℝ) {S : ℝ → Set E}
    (hS : Monotone S) :
    Antitone (fun γ => annulus c rIn rOut \ S γ) :=
  fun _ _ hγ => Set.sdiff_subset_sdiff_right (hS hγ)

/-- **Proposition 7 at the instrument's knob**: for γ₁ ≤ γ₂ (any monotone
sector family), a direct entry at channel width γ₁ is a direct entry at
width γ₂ — direct(γ₁) ⊆ direct(γ₂) pathwise. -/
theorem prop7_channel (c : E) (rIn' rOut : ℝ) {S : ℝ → Set E} (hS : Monotone S)
    {γ₁ γ₂ : ℝ} (hγ : γ₁ ≤ γ₂) {cHole : E} {rIn : ℝ} {s₀ : σ} {T : ℕ}
    (h : entersDirectlyAt pos F freeze (annulus c rIn' rOut \ S γ₁)
      cHole rIn s₀ T) :
    entersDirectlyAt pos F freeze (annulus c rIn' rOut \ S γ₂)
      cHole rIn s₀ T :=
  prop7_direct_monotone (channelMode_antitone c rIn' rOut hS hγ) h

end Paper3Ring
