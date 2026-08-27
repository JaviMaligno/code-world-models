/-
Paper 3, fourth tranche (companion): the 1-D reduction of Proposition 8's
witness tube (docs/paper3/THEORY.md, "Proposition 8").

Prop 8 (positivity: r_int(γ) > 0 for every γ > 0, facing channel) argues
through an explicit witness: constant action a ≡ 0, so the heading input is
EXACTLY (1, 0) — no trigonometry — and the trajectory runs east along the
line y = y₀ with v_y ≡ 0. This file machine-checks that reduction at full
generality: for the instrument's own dynamics (`ringF`/`ringFreeze` from
`Basic.lean`), if every heading input lies on an axis `e` and the initial
velocity does too, then EVERY state of the freeze trajectory — freeze events
included, any mode set — has velocity on the axis and position on the line
`p₀ + ℝ·e`. The witness tube is genuinely one-dimensional.

What this does and does not cover of Prop 8, exactly:

  * COVERED — the structural reduction: the witness family never leaves its
    line, so its landings are parametrized by one scalar and the tube's
    geometry is the geometry of a line against the annulus.
  * NOT COVERED (measured, `tests/test_ring2d_positivity.py`'s witness and
    THEORY.md's chord bound): that the specific line at |y₀| ≤ η(γ) meets
    the band only inside the channel sector, and that the eastward speed-up
    reaches the interior within the horizon. Both are numeric facts about
    the frozen defaults; the channel-membership step also needs the concrete
    angular sector, which the formalization deliberately keeps abstract
    (`DirectEntries.channelMode_antitone` never uses its shape).

The probability wrapper (the start set |y₀| ≤ η has positive measure, hence
r_int(γ) > 0) is the same measure step noted throughout the package.
-/
import Paper3Ring.Basic
import Mathlib.Analysis.SpecialFunctions.Sqrt
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Bounds

namespace Paper3Ring

section WitnessTube

variable {V : Type*} [SeminormedAddCommGroup V] [NormedSpace ℝ V]

/-- **The witness tube is 1-D.** For the instrument's dynamics with every
heading input on the axis `e` and initial velocity on `e`, every state of
the freeze trajectory — any mode set `M`, freeze events included — has
position on the line `p₀ + ℝ·e` and velocity on `ℝ·e`. -/
theorem prop8_witness_stays_on_axis (gain drag dt : ℝ) (u : ℕ → V) (e : V)
    (hu : ∀ t, ∃ c : ℝ, u t = c • e) (M : Set V) (p₀ : V) {a₀ : ℝ} :
    ∀ t, ∃ b a : ℝ,
      freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze M (p₀, a₀ • e) t
        = (p₀ + b • e, a • e) := by
  intro t
  induction t with
  | zero =>
    exact ⟨0, a₀, by simp [freezeTraj]⟩
  | succ n ih =>
    obtain ⟨b, a, heq⟩ := ih
    obtain ⟨c, hc⟩ := hu n
    classical
    rw [freezeTraj_succ, heq]
    by_cases h : (ringF gain drag dt u n (p₀ + b • e, a • e)).1 ∈ M
    · refine ⟨b, 0, ?_⟩
      rw [if_pos h]
      simp [ringFreeze]
    · refine ⟨b + dt * (a + dt * (gain * c - drag * a)),
        a + dt * (gain * c - drag * a), ?_⟩
      rw [if_neg h]
      simp only [ringF, hc, Prod.mk.injEq]
      exact ⟨by module, by module⟩

end WitnessTube

/-! ## The numeric tail: the witness reaches the hole's window in-horizon

With the tube 1-D, the witness's coordinates follow one scalar recursion (the
axis lemma's witnesses with heading coefficient c ≡ 1): the frozen-defaults
integrator `v' = v + 0.1·(3 − 0.3·v)`, `b' = b + 0.1·v'`, from rest. The
lemmas below machine-check the in-horizon-entry half of Prop 8's numerics:
the offset `b` reaches the window `[9.5, 10.5)` within 53 < h = 80 steps
(speed exceeds 5 by step 34, the offset then gains ≥ 0.5 per step, and the
first crossing cannot overshoot because no step exceeds 1), and any window
landing is strictly inside the hole (`hypot < r_in = 3.5`, the instrument's
own metric). What remains measured is exactly one fact: that the line's
band-radius landings lie in the channel sector (the freeze-free hypothesis
`hfree` below) — the sine-bound geometry THEORY.md argues with the margin
η(γ), carried by the Python witness. -/

section PositivityNumerics

/-- The witness's speed recursion at the frozen defaults, from rest:
`v' = v + dt·(gain − drag·v)` with dt = 0.1, gain = 3, drag = 0.3. -/
def vSeq : ℕ → ℝ
  | 0 => 0
  | t + 1 => vSeq t + 0.1 * (3 - 0.3 * vSeq t)

/-- The witness's along-axis offset from its start: `b' = b + dt·v'`
(semi-implicit, exactly `ringF`'s position update). -/
def bSeq : ℕ → ℝ
  | 0 => 0
  | t + 1 => bSeq t + 0.1 * vSeq (t + 1)

lemma vSeq_nonneg : ∀ t, 0 ≤ vSeq t := by
  intro t
  induction t with
  | zero => simp [vSeq]
  | succ n ih => simp only [vSeq]; linarith

lemma vSeq_le_ten : ∀ t, vSeq t ≤ 10 := by
  intro t
  induction t with
  | zero => simp [vSeq]
  | succ n ih => simp only [vSeq]; linarith

/-- Below terminal speed the recursion is a ratchet: while `v ≤ 5` each step
gains at least 0.15, so by step 34 the speed is at least 5 — and stays
there. -/
lemma vSeq_lower : ∀ t : ℕ, 5 ≤ vSeq t ∨ 0.15 * (t : ℝ) ≤ vSeq t := by
  intro t
  induction t with
  | zero => right; simp [vSeq]
  | succ n ih =>
    rcases ih with h5 | hlin
    · left
      have := vSeq_le_ten n
      simp only [vSeq]
      linarith
    · by_cases h5 : 5 ≤ vSeq n
      · left
        have := vSeq_le_ten n
        simp only [vSeq]
        linarith
      · right
        have h5' := not_le.mp h5
        simp only [vSeq]
        push_cast
        linarith

lemma vSeq_ge_five : ∀ t, 34 ≤ t → 5 ≤ vSeq t := by
  intro t
  induction t with
  | zero => omega
  | succ n ih =>
    intro h
    by_cases h34 : 34 ≤ n
    · have := ih h34
      have := vSeq_le_ten n
      simp only [vSeq]
      linarith
    · have hn : n = 33 := by omega
      rcases vSeq_lower 34 with h5 | hlin
      · rw [show n + 1 = 34 by omega]
        exact h5
      · rw [show n + 1 = 34 by omega]
        norm_num at hlin
        linarith

lemma bSeq_step_le (t : ℕ) : bSeq (t + 1) ≤ bSeq t + 1 := by
  have := vSeq_le_ten (t + 1)
  simp only [bSeq]
  linarith

lemma bSeq_step_nonneg (t : ℕ) : bSeq t ≤ bSeq (t + 1) := by
  have := vSeq_nonneg (t + 1)
  simp only [bSeq]
  linarith

lemma bSeq_nonneg : ∀ t, 0 ≤ bSeq t := by
  intro t
  induction t with
  | zero => simp [bSeq]
  | succ n ih => exact le_trans ih (bSeq_step_nonneg n)

/-- Past step 34 the offset gains at least 0.5 per step. -/
lemma bSeq_growth : ∀ k : ℕ, 0.5 * (k : ℝ) ≤ bSeq (34 + k) := by
  intro k
  induction k with
  | zero => simpa using bSeq_nonneg 34
  | succ m ih =>
    have hv : 5 ≤ vSeq (34 + m + 1) := vSeq_ge_five _ (by omega)
    have : bSeq (34 + m) + 0.5 ≤ bSeq (34 + m + 1) := by
      simp only [bSeq]
      linarith
    push_cast
    have h34 : 34 + (m + 1) = 34 + m + 1 := by omega
    rw [h34]
    linarith

/-- **The scalar window theorem (Prop 8's in-horizon entry, numeric core).**
From rest, the witness's offset reaches the window `[9.5, 10.5)` within 53
steps — inside the h = 80 horizon with margin: the first crossing of 9.5
exists by step 53 and cannot overshoot past 10.5 because no step exceeds
1. -/
theorem prop8_scalar_window : ∃ T ≤ 53, 9.5 ≤ bSeq T ∧ bSeq T < 10.5 := by
  classical
  have hreach : 9.5 ≤ bSeq 53 := by
    have h := bSeq_growth 19
    norm_num at h
    linarith
  have hex : ∃ t, 9.5 ≤ bSeq t := ⟨53, hreach⟩
  set T := Nat.find hex with hT
  have hTs : 9.5 ≤ bSeq T := Nat.find_spec hex
  have hT53 : T ≤ 53 := Nat.find_min' hex hreach
  have hTne : T ≠ 0 := by
    intro h
    rw [h] at hTs
    simp only [bSeq] at hTs
    norm_num at hTs
  obtain ⟨s, hs⟩ := Nat.exists_eq_succ_of_ne_zero hTne
  have hprev : bSeq s < 9.5 := by
    have := Nat.find_min hex (by omega : s < T)
    linarith [not_le.mp this]
  have hstep : bSeq T ≤ bSeq s + 1 := by
    rw [hs]
    exact bSeq_step_le s
  exact ⟨T, hT53, hTs, by linarith⟩

/-- **A window landing is strictly inside the hole**, in the instrument's own
metric: with the start box `|x₀| ≤ 0.5`, `|y₀| ≤ 0.4` and offset `b` in the
window, `hypot(x₀ + b − 12, y₀) < 3.5 = r_in`. -/
theorem prop8_window_is_interior {x₀ y₀ b : ℝ}
    (hx : |x₀| ≤ 0.5) (hy : |y₀| ≤ 0.4) (hb₁ : 9.5 ≤ b) (hb₂ : b < 10.5) :
    Real.sqrt ((x₀ + b - 12) ^ 2 + y₀ ^ 2) < 3.5 := by
  obtain ⟨hx₁, hx₂⟩ := abs_le.mp hx
  obtain ⟨hy₁, hy₂⟩ := abs_le.mp hy
  have hsum : (x₀ + b - 12) ^ 2 + y₀ ^ 2 < 3.5 ^ 2 := by nlinarith
  have h35 : (0 : ℝ) < 3.5 := by norm_num
  calc Real.sqrt ((x₀ + b - 12) ^ 2 + y₀ ^ 2)
      < Real.sqrt (3.5 ^ 2) := by
        exact Real.sqrt_lt_sqrt (by positivity) hsum
    _ = 3.5 := by
        rw [Real.sqrt_sq h35.le]

end PositivityNumerics

/-! ## The linkage: a freeze-free witness follows the scalar recursion -/

section PositivityLinkage

variable {V : Type*} [SeminormedAddCommGroup V] [NormedSpace ℝ V]

/-- **The freeze-free witness follows the scalar recursion exactly.** For the
frozen-defaults dynamics with heading input constantly the axis vector `e`
and start at rest, if no tentative landing up to `T` falls in the mode set
(the channel fact — Prop 8's remaining measured hypothesis), then the state
at every `t ≤ T` is exactly `(p₀ + bSeq t • e, vSeq t • e)`. Composed with
`prop8_scalar_window` and `prop8_window_is_interior`, this is the in-horizon
entry of Prop 8's witness tube, conditional on channel membership alone. -/
theorem prop8_free_witness_follows_scalar (e : V) (M : Set V) (p₀ : V) {T : ℕ}
    (hfree : ∀ t < T,
      (ringF (3 : ℝ) 0.3 0.1 (fun _ => e) t
        (freezeTraj Prod.fst (ringF (3 : ℝ) 0.3 0.1 (fun _ => e)) ringFreeze M
          (p₀, 0) t)).1 ∉ M) :
    ∀ t ≤ T,
      freezeTraj Prod.fst (ringF (3 : ℝ) 0.3 0.1 (fun _ => e)) ringFreeze M
        (p₀, 0) t
        = (p₀ + bSeq t • e, vSeq t • e) := by
  intro t
  induction t with
  | zero =>
    intro _
    simp [freezeTraj, bSeq, vSeq]
  | succ n ih =>
    intro hT
    have heq := ih (by omega)
    have hnot := hfree n (by omega)
    rw [freezeTraj_succ, if_neg hnot, heq]
    simp only [ringF, Prod.mk.injEq]
    refine ⟨?_, ?_⟩
    · show p₀ + bSeq n • e
          + (0.1 : ℝ) • (vSeq n • e
            + (0.1 : ℝ) • ((3 : ℝ) • e - (0.3 : ℝ) • (vSeq n • e)))
          = p₀ + bSeq (n + 1) • e
      simp only [bSeq, vSeq]
      module
    · show vSeq n • e
          + (0.1 : ℝ) • ((3 : ℝ) • e - (0.3 : ℝ) • (vSeq n • e))
          = vSeq (n + 1) • e
      simp only [vSeq]
      module

end PositivityLinkage

/-! ## The channel membership, and the composed positivity core

The last measured ingredient becomes a lemma. The channel sector is modeled
by its SINE characterization on the west half-plane: a point west of the
center with angular offset θ from π (θ ∈ [0, π/2]) satisfies
sin θ = |y|/d, so for γ ≤ π membership in the width-γ sector is exactly
`|y| ≤ d·sin(γ/2)` — no angle API needed. Modeling note (same license as
`annulus` for `_in_mode`): this is the faithful model of the instrument's
`_in_gap_sector` restricted to the west half-plane and γ ∈ (0, π], which is
where every landing of the witness lives; for γ > π the wall is a SUBSET of
the γ = π wall (`channelMode_antitone`), so avoidance transports for free.

`prop8_positivity_core` then composes everything proved above: the witness
from the start box, with the frozen-defaults dynamics and the sine-modeled
γ-channel wall, reaches a position strictly inside the hole within 53 < 80
steps. What remains of THEORY.md's Proposition 8 is only the measure
wrapper (the start box has positive probability). -/

section ChannelMembership

/-- The instrument's own metric (its `_d`): hypot to a center. -/
noncomputable def hyp (p c : ℝ × ℝ) : ℝ :=
  Real.sqrt ((p.1 - c.1) ^ 2 + (p.2 - c.2) ^ 2)

/-- The width-γ channel sector about the facing direction, sine-modeled on
the west half-plane (see the section header's modeling note). -/
def sectorSin (γ : ℝ) : Set (ℝ × ℝ) :=
  {p | p.1 ≤ 12 ∧ |p.2| ≤ hyp p (12, 0) * Real.sin (γ / 2)}

/-- The γ-channel ring wall at the frozen defaults: the band radii minus the
channel sector. -/
def ringModeSin (γ : ℝ) : Set (ℝ × ℝ) :=
  {p | 3.5 ≤ hyp p (12, 0) ∧ hyp p (12, 0) ≤ 5} \ sectorSin γ

/-- Jordan's inequality, in the form the margin needs: `γ/8 ≤ sin(γ/2)` for
`γ ∈ [0, π]` (the paper's η-margin uses 8 > π). -/
lemma div_eight_le_sin_half {γ : ℝ} (hγ₀ : 0 ≤ γ) (hγπ : γ ≤ Real.pi) :
    γ / 8 ≤ Real.sin (γ / 2) := by
  have hpi := Real.pi_pos
  have hpi4 := Real.pi_le_four
  have hne : Real.pi ≠ 0 := ne_of_gt hpi
  have hj := Real.mul_le_sin (x := γ / 2) (by linarith) (by linarith)
  have h1 : 2 / Real.pi * (γ / 2) = γ / Real.pi := by
    field_simp
  have h2 : γ / 8 ≤ γ / Real.pi := by
    have hinv : 1 / 8 ≤ 1 / Real.pi :=
      one_div_le_one_div_of_le hpi (by linarith)
    calc γ / 8 = γ * (1 / 8) := by ring
      _ ≤ γ * (1 / Real.pi) := mul_le_mul_of_nonneg_left hinv hγ₀
      _ = γ / Real.pi := by ring
  rw [h1] at hj
  linarith

/-- **The witness line's band crossings are in the channel** — the fact that
was Prop 8's last measured ingredient: a west-half-plane point at height
`|y| ≤ 3.5·γ/8` (the η(γ) margin) is never in the γ-wall, whatever its
radius. -/
lemma witness_line_avoids_wall {γ x y : ℝ}
    (hγ₀ : 0 ≤ γ) (hγπ : γ ≤ Real.pi)
    (hx : x ≤ 12) (hy : |y| ≤ 3.5 * γ / 8) :
    (x, y) ∉ ringModeSin γ := by
  rintro ⟨⟨hd₁, _⟩, hnot⟩
  refine hnot ⟨hx, ?_⟩
  have hsin := div_eight_le_sin_half hγ₀ hγπ
  have hs0 : 0 ≤ Real.sin (γ / 2) :=
    Real.sin_nonneg_of_nonneg_of_le_pi (by linarith)
      (by linarith [Real.pi_pos])
  calc |y| ≤ 3.5 * γ / 8 := hy
    _ = 3.5 * (γ / 8) := by ring
    _ ≤ 3.5 * Real.sin (γ / 2) := by nlinarith
    _ ≤ hyp (x, y) (12, 0) * Real.sin (γ / 2) :=
        mul_le_mul_of_nonneg_right hd₁ hs0

lemma bSeq_mono : Monotone bSeq :=
  monotone_nat_of_le_succ bSeq_step_nonneg

/-- **Prop 8's positivity core, composed.** At the frozen defaults, with the
sine-modeled γ-channel wall (γ ∈ (0, π]; larger γ has a smaller wall), the
constant-thrust witness from the start box `|x₀| ≤ 0.5`,
`|y₀| ≤ min(3.5·γ/8, 0.4)` reaches a position strictly inside the hole
(`hyp < r_in = 3.5`) within 53 < h = 80 steps. All that remains of
THEORY.md's Proposition 8 is the measure wrapper: the start box has positive
probability. -/
theorem prop8_positivity_core {γ x₀ y₀ : ℝ}
    (hγ₀ : 0 < γ) (hγπ : γ ≤ Real.pi)
    (hx : |x₀| ≤ 0.5) (hy : |y₀| ≤ 3.5 * γ / 8) (hy4 : |y₀| ≤ 0.4) :
    ∃ T ≤ 53,
      hyp ((freezeTraj Prod.fst
          (ringF (3 : ℝ) 0.3 0.1 (fun _ => ((1 : ℝ), (0 : ℝ)))) ringFreeze
          (ringModeSin γ) ((x₀, y₀), 0) T).1) (12, 0) < 3.5 := by
  obtain ⟨T, hT53, hbT₁, hbT₂⟩ := prop8_scalar_window
  have hx₂ := (abs_le.mp hx).2
  -- the trajectory follows the line through T: no landing is ever in the wall
  have hline : ∀ t ≤ T,
      freezeTraj Prod.fst
          (ringF (3 : ℝ) 0.3 0.1 (fun _ => ((1 : ℝ), (0 : ℝ)))) ringFreeze
          (ringModeSin γ) ((x₀, y₀), 0) t
        = ((x₀ + bSeq t, y₀), (vSeq t, 0)) := by
    intro t
    induction t with
    | zero =>
      intro _
      have h0 : (0 : ℝ × ℝ) = ((0 : ℝ), (0 : ℝ)) := rfl
      simp [freezeTraj, bSeq, vSeq, h0]
    | succ n ih =>
      intro hT
      have heq := ih (by omega)
      have hland : (ringF (3 : ℝ) 0.3 0.1 (fun _ => ((1 : ℝ), (0 : ℝ))) n
          ((x₀ + bSeq n, y₀), (vSeq n, 0))).1 = (x₀ + bSeq (n + 1), y₀) := by
        simp only [ringF, Prod.smul_mk, Prod.mk_add_mk, Prod.mk_sub_mk,
          smul_eq_mul, Prod.mk.injEq]
        exact ⟨by simp only [bSeq, vSeq]; ring, by ring⟩
      have hxb : x₀ + bSeq (n + 1) ≤ 12 := by
        have := bSeq_mono (show n + 1 ≤ T by omega)
        linarith
      have hnot : (ringF (3 : ℝ) 0.3 0.1 (fun _ => ((1 : ℝ), (0 : ℝ))) n
          (freezeTraj Prod.fst
            (ringF (3 : ℝ) 0.3 0.1 (fun _ => ((1 : ℝ), (0 : ℝ)))) ringFreeze
            (ringModeSin γ) ((x₀, y₀), 0) n)).1 ∉ ringModeSin γ := by
        rw [heq, hland]
        exact witness_line_avoids_wall hγ₀.le hγπ hxb hy
      rw [freezeTraj_succ, if_neg hnot, heq]
      simp only [ringF, Prod.smul_mk, Prod.mk_add_mk, Prod.mk_sub_mk,
        smul_eq_mul, Prod.mk.injEq]
      refine ⟨⟨?_, ?_⟩, ?_, ?_⟩
      · simp only [bSeq, vSeq]; ring
      · ring
      · simp only [vSeq]; ring
      · ring
  -- the window landing is interior
  refine ⟨T, hT53, ?_⟩
  rw [hline T le_rfl]
  have := prop8_window_is_interior hx hy4 hbT₁ hbT₂
  simpa [hyp] using this

end ChannelMembership

end Paper3Ring
