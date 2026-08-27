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

end Paper3Ring
