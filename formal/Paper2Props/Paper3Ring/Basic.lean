/-
Formalization of paper 3's metric core (docs/paper3/THEORY.md), first tranche.

Why this exists: the same reason as `Paper2Props` — hand-written proofs in this
project have been wrong before in ways numeric audits cannot catch, and the
foundational results here carry the rest of the paper. Under a checker, a false
"by induction" does not compile.

Mapping to THEORY.md (the statement of record stays in THEORY.md; this file is
the machine check of the mathematical content, at the realization level — the
measure-theoretic wrappers, which only add a.s.-quantification over seeds, are
noted per item in docs/paper3/FORMALIZATION.md):

  * `lemma2_crossing`            — Lemma 2, crossing half: a discrete path with
                                   steps ≤ Δ < r_out − r_in cannot pass from
                                   outside the annulus to inside the hole
                                   without an intermediate point IN the annulus.
  * `freeze_stays_outside`       — Lemma 2, freeze half: under freeze-on-landing
                                   semantics an outside start keeps distance
                                   > r_out forever (invariant, by induction).
  * `lemma2_interior_unreachable`— the corollary the paper's knob statement
                                   rests on: the open interior is unreachable —
                                   r_int(0) = 0 pathwise, not merely rare.
  * `disc_annulus_traj_eq`,
    `disc_annulus_contact_iff`   — Lemma 2's corollary (evidence equivalence):
                                   from outside starts, the filled-disc mode and
                                   the annulus mode produce IDENTICAL
                                   trajectories and fire on exactly the same
                                   steps — the contact processes, hence all
                                   evidence any gate or TDA pass extracts, are
                                   pathwise identical.
  * `disc_annulus_same_return`   — Proposition 3(ii)'s engine: any return
                                   functional (hence any deterministic planner's
                                   imagined value of any candidate) coincides
                                   under the two models.
  * `prop1_traj_eq`,
    `prop1_gate_quotient`,
    `prop1_no_statistic_distinguishes`
                                 — Proposition 1 (gate quotient) at realization
                                   level: a model agreeing with the truth on a
                                   set containing every query of the truth's
                                   trajectory produces the identical trajectory,
                                   so no gate statistic distinguishes them.
  * `speed_invariant`,
    `ringF_step_dist`            — "Constants at the frozen defaults": the
                                   integrator's speed bound ‖v‖ ≤ gain/drag is
                                   invariant, so every position step has length
                                   ≤ gain·dt/drag.
  * `ring_interior_unreachable`  — the capstone: the concrete RingField2D-shaped
                                   dynamics (semi-implicit integrator, freeze on
                                   annulus landing, bounded heading input) from
                                   an outside start never enters the interior.
  * `ring2d_frozen_defaults_step_lt_thickness`, `ring2d_interior_unreachable_at_defaults`
                                 — the numeric instantiation at the frozen
                                   defaults gain=3, drag=0.3, dt=0.1, r_in=3.5,
                                   r_out=5: Δ ≤ 1.0 < 1.5 = w, hypotheses hold
                                   with margin.

Honesty note (mirrors THEORY.md's): everything here is metric, not topological
— the proofs use only that distance-to-center is 1-Lipschitz, exactly as the
paper says. The genuinely topological items (T1's Rips lemmas, T7's relative
estimator) are future tranches.
-/
import Mathlib.Topology.MetricSpace.Basic
import Mathlib.Analysis.Normed.Module.Basic
import Mathlib.Data.Nat.Find
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Module
import Mathlib.Tactic.GCongr
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.NormNum

namespace Paper3Ring

/-! ## The annulus, and the one-step exterior lemma -/

variable {E : Type*} [PseudoMetricSpace E]

/-- The closed annulus (RingField2D's mode region): `r_in ≤ dist p c ≤ r_out`. -/
def annulus (c : E) (rIn rOut : ℝ) : Set E :=
  {p | rIn ≤ dist p c ∧ dist p c ≤ rOut}

lemma mem_annulus {c p : E} {rIn rOut : ℝ} :
    p ∈ annulus c rIn rOut ↔ rIn ≤ dist p c ∧ dist p c ≤ rOut := Iff.rfl

/-- One step of length ≤ Δ < r_out − r_in from strictly outside the annulus either
lands IN the annulus or stays strictly outside: it cannot leap the ring. This is
the single inequality both halves of Lemma 2 and the disc≡annulus corollary run on. -/
lemma step_cannot_leap {c p q : E} {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hp : rOut < dist p c) (hq : dist q p ≤ Δ) :
    rIn < dist q c := by
  have htri : dist p c ≤ dist p q + dist q c := dist_triangle p q c
  have hpq : dist p q ≤ Δ := by rwa [dist_comm]
  linarith

/-- ...and therefore a step from outside that does NOT land in the annulus is still
strictly outside. -/
lemma step_stays_out {c p q : E} {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hp : rOut < dist p c) (hq : dist q p ≤ Δ)
    (hnot : q ∉ annulus c rIn rOut) : rOut < dist q c := by
  have h1 : rIn < dist q c := step_cannot_leap hΔw hp hq
  rcases not_and_or.mp hnot with h | h
  · exact absurd h1.le h
  · exact not_le.mp h

/-! ## Lemma 2, crossing half (free dynamics: discrete intermediate-value) -/

/-- **Lemma 2 (metric crossing / no jump-over), crossing half.** Positions moving in
discrete steps of length ≤ Δ, with annulus thickness `r_out − r_in > Δ`: a path from
strictly outside to strictly inside the hole has an intermediate point in the annulus. -/
theorem lemma2_crossing (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    {p : ℕ → E} (hstep : ∀ t, dist (p (t + 1)) (p t) ≤ Δ)
    {T : ℕ} (h0 : rOut < dist (p 0) c) (hT : dist (p T) c < rIn) :
    ∃ t ≤ T, p t ∈ annulus c rIn rOut := by
  classical
  have hΔ0 : 0 ≤ Δ := le_trans dist_nonneg (hstep 0)
  have hio : rIn < rOut := by linarith
  have hex : ∃ t, dist (p t) c < rOut := ⟨T, lt_trans hT hio⟩
  set t₀ := Nat.find hex with ht₀def
  have ht₀ : dist (p t₀) c < rOut := Nat.find_spec hex
  have ht₀ne : t₀ ≠ 0 := by
    intro h
    rw [h] at ht₀
    exact absurd ht₀ (not_lt.mpr h0.le)
  obtain ⟨s, hs⟩ := Nat.exists_eq_succ_of_ne_zero ht₀ne
  have hprev : rOut ≤ dist (p s) c := by
    have hmin : ¬ dist (p s) c < rOut := Nat.find_min hex (by omega)
    exact not_lt.mp hmin
  have hdrop : dist (p s) c - Δ ≤ dist (p t₀) c := by
    have htri : dist (p s) c ≤ dist (p s) (p t₀) + dist (p t₀) c := dist_triangle _ _ _
    have hstep' : dist (p s) (p t₀) ≤ Δ := by
      rw [hs, dist_comm]
      exact hstep s
    linarith
  have hlow : rIn ≤ dist (p t₀) c := by linarith
  have hle : t₀ ≤ T := Nat.find_min' hex (lt_trans hT hio)
  exact ⟨t₀, hle, hlow, ht₀.le⟩

/-! ## Lemma 2, freeze half (RingField2D semantics), over an abstract state space

The dynamics carry more than a position (RingField2D: position and velocity), so
the trajectory is over an abstract state `σ` with a position projection. `F t s`
is the free (tentative) step; a tentative landing whose position falls in the
mode set `M` is replaced by `freeze s` (RingField2D: same position, velocity
zeroed) — exactly the instrument's mode semantics. -/

variable {σ : Type*}

open Classical in
/-- The freeze trajectory: tentative step `F t`, mode set `M` on the landing
position, `freeze` on contact. -/
noncomputable def freezeTraj (pos : σ → E) (F : ℕ → σ → σ) (freeze : σ → σ)
    (M : Set E) (s₀ : σ) : ℕ → σ
  | 0 => s₀
  | t + 1 =>
      if pos (F t (freezeTraj pos F freeze M s₀ t)) ∈ M then
        freeze (freezeTraj pos F freeze M s₀ t)
      else F t (freezeTraj pos F freeze M s₀ t)

variable {pos : σ → E} {F : ℕ → σ → σ} {freeze : σ → σ}

omit [PseudoMetricSpace E] in
open Classical in
/-- The successor-step unfolding of `freezeTraj`, as an explicit rewrite rule (the
`if` carries the classical instance from the definition, so proofs rewrite through
this lemma and `if_pos`/`if_neg` rather than unfolding blindly). -/
lemma freezeTraj_succ (pos : σ → E) (F : ℕ → σ → σ) (freeze : σ → σ)
    (M : Set E) (s₀ : σ) (t : ℕ) :
    freezeTraj pos F freeze M s₀ (t + 1)
      = if pos (F t (freezeTraj pos F freeze M s₀ t)) ∈ M then
          freeze (freezeTraj pos F freeze M s₀ t)
        else F t (freezeTraj pos F freeze M s₀ t) := by
  simp only [freezeTraj]

/-- **Lemma 2, freeze half.** If every tentative step moves the position by at most
Δ < r_out − r_in and freezing preserves the position, a trajectory started strictly
outside stays strictly outside the annulus forever. -/
theorem freeze_stays_outside (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, rOut < dist (pos (freezeTraj pos F freeze (annulus c rIn rOut) s₀ t)) c := by
  intro t
  induction t with
  | zero => simpa [freezeTraj] using h₀
  | succ n ih =>
    classical
    by_cases h :
        pos (F n (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n)) ∈ annulus c rIn rOut
    · rw [freezeTraj_succ, if_pos h, hfreeze]
      exact ih
    · rw [freezeTraj_succ, if_neg h]
      exact step_stays_out hΔw ih (hstep n _) h

/-- **The interior is unreachable, not merely rare** — the corollary the paper's knob
statement rests on (`r_int(0) = 0` pathwise): no trajectory from an outside start ever
produces a position with `dist < r_in`. -/
theorem lemma2_interior_unreachable (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hΔ0 : 0 ≤ Δ)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, ¬ dist (pos (freezeTraj pos F freeze (annulus c rIn rOut) s₀ t)) c < rIn := by
  intro t
  have hio : rIn < rOut := by linarith
  have hout := freeze_stays_outside c hΔw hstep hfreeze h₀ t
  exact not_lt.mpr (le_of_lt (lt_trans hio hout))

/-! ### The thin-neck generalization (the local crossing lemma)

RingField2D's `neck` knob thins the band from outside inside an angular
sector, so the mode set is no longer an annulus — but it still CONTAINS the
thin annulus `[r_in, r_in + neck]` at every angle, and that inclusion is all
the invariant needs. The lemma below says: however the mode set is shaped,
containing a thin annulus of thickness `w > Δ` makes the hole unreachable
from outside. Its contrapositive is the instrument's design statement:
interior entry requires a single step longer than the neck — and with the
integrator's max step `(gain/drag)·dt = 1.0`, a neck ≥ 1.2 keeps the interior
exactly unreachable while a thinner one admits leap-through at speed
(witnessed deterministically in `tests/test_ring2d_thin_neck.py`). -/

/-- **Local crossing lemma (thin neck).** If the mode set `M` contains the
annulus `[rIn, rIn + w]` about `c`, every tentative step moves the position by
at most `Δ < w`, and freezing preserves position, then a trajectory started at
distance `> rIn + w` keeps distance `> rIn + w` forever. -/
theorem freeze_stays_outside_of_superset (c : E) {rIn w Δ : ℝ} (hΔw : Δ < w)
    {M : Set E} (hM : annulus c rIn (rIn + w) ⊆ M)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rIn + w < dist (pos s₀) c) :
    ∀ t, rIn + w < dist (pos (freezeTraj pos F freeze M s₀ t)) c := by
  intro t
  induction t with
  | zero => simpa [freezeTraj] using h₀
  | succ n ih =>
    classical
    by_cases h : pos (F n (freezeTraj pos F freeze M s₀ n)) ∈ M
    · rw [freezeTraj_succ, if_pos h, hfreeze]
      exact ih
    · rw [freezeTraj_succ, if_neg h]
      exact step_stays_out (by linarith : Δ < (rIn + w) - rIn) ih (hstep n _)
        (fun hin => h (hM hin))

/-- **The neck threshold, as unreachability.** Under the same hypotheses the
open hole `dist < rIn` is never visited: with max step Δ, a neck of thickness
`w > Δ` seals the interior exactly, whatever the rest of the mode set looks
like. -/
theorem neck_interior_unreachable (c : E) {rIn w Δ : ℝ} (hΔw : Δ < w)
    (hΔ0 : 0 ≤ Δ) {M : Set E} (hM : annulus c rIn (rIn + w) ⊆ M)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rIn + w < dist (pos s₀) c) :
    ∀ t, ¬ dist (pos (freezeTraj pos F freeze M s₀ t)) c < rIn := by
  intro t
  have h := freeze_stays_outside_of_superset c hΔw hM hstep hfreeze h₀ t
  exact not_lt.mpr (le_of_lt (lt_of_le_of_lt (by linarith) h))

/-! ## The corollary: disc and annulus are evidence-equivalent from outside -/

/-- **Disc ≡ annulus, trajectory half (Lemma 2's corollary).** From an outside start,
the freeze dynamics with the ANNULUS mode and with the FILLED-DISC mode (the closed
ball of radius r_out) produce the identical state trajectory: a tentative landing can
never have distance < r_in (that would leap the ring), so the two mode sets agree at
every landing the trajectory ever queries. -/
theorem disc_annulus_traj_eq (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, freezeTraj pos F freeze (annulus c rIn rOut) s₀ t
        = freezeTraj pos F freeze (Metric.closedBall c rOut) s₀ t := by
  intro t
  induction t with
  | zero => rfl
  | succ n ih =>
    have hout : rOut < dist (pos (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n)) c :=
      freeze_stays_outside c hΔw hstep hfreeze h₀ n
    have h1 : rIn < dist (pos (F n (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n))) c :=
      step_cannot_leap hΔw hout (hstep n _)
    have hiff :
        pos (F n (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n)) ∈ annulus c rIn rOut
          ↔ pos (F n (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n))
              ∈ Metric.closedBall c rOut := by
      simp only [mem_annulus, Metric.mem_closedBall]
      exact ⟨fun ⟨_, h2⟩ => h2, fun h2 => ⟨h1.le, h2⟩⟩
    classical
    by_cases h :
        pos (F n (freezeTraj pos F freeze (annulus c rIn rOut) s₀ n)) ∈ annulus c rIn rOut
    · rw [freezeTraj_succ, freezeTraj_succ, ← ih, if_pos h, if_pos (hiff.mp h)]
    · rw [freezeTraj_succ, freezeTraj_succ, ← ih, if_neg h,
        if_neg (fun hD => h (hiff.mpr hD))]

/-- **Disc ≡ annulus, contact half.** The two modes FIRE on exactly the same steps of
the (shared) trajectory: the contact processes — and hence all evidence any gate,
repair loop, or TDA pass extracts — are pathwise identical. -/
theorem disc_annulus_contact_iff (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, (pos (F t (freezeTraj pos F freeze (annulus c rIn rOut) s₀ t))
            ∈ annulus c rIn rOut)
        ↔ (pos (F t (freezeTraj pos F freeze (Metric.closedBall c rOut) s₀ t))
            ∈ Metric.closedBall c rOut) := by
  intro t
  have hout : rOut < dist (pos (freezeTraj pos F freeze (annulus c rIn rOut) s₀ t)) c :=
    freeze_stays_outside c hΔw hstep hfreeze h₀ t
  have h1 : rIn < dist (pos (F t (freezeTraj pos F freeze (annulus c rIn rOut) s₀ t))) c :=
    step_cannot_leap hΔw hout (hstep t _)
  rw [← disc_annulus_traj_eq c hΔw hstep hfreeze h₀ t]
  simp only [mem_annulus, Metric.mem_closedBall]
  exact ⟨fun ⟨_, h2⟩ => h2, fun h2 => ⟨h1.le, h2⟩⟩

/-- **Proposition 3(ii)'s engine.** Any return functional of the trajectory — hence any
deterministic planner's imagined value of any candidate action sequence — takes the
same value under the wrong-topology (filled-disc) model as under the true annulus:
the wrong topology is harmless from outside. The full Prop 3 statement adds only the
planner/environment loop around this identity. -/
theorem disc_annulus_same_return {β : Type*} (J : (ℕ → σ) → β)
    (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ t s, dist (pos (F t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    J (freezeTraj pos F freeze (annulus c rIn rOut) s₀)
      = J (freezeTraj pos F freeze (Metric.closedBall c rOut) s₀) :=
  congrArg J (funext (disc_annulus_traj_eq c hΔw hstep hfreeze h₀))

/-! ## Proposition 1 (gate quotient), at realization level -/

section GateQuotient

variable {S A : Type*}

/-- Deterministic rollout of a model `f` from `s₀` under an action stream. -/
def traj (f : S → A → S) (s₀ : S) (acts : ℕ → A) : ℕ → S
  | 0 => s₀
  | t + 1 => f (traj f s₀ acts t) (acts t)

/-- **Proposition 1, induction core**: a model agreeing with the truth at every query
the truth's own trajectory makes produces the identical trajectory (with the same
realizations — here, the same action stream). -/
theorem prop1_traj_eq (f fhat : S → A → S) (s₀ : S) (acts : ℕ → A)
    (h : ∀ t, fhat (traj f s₀ acts t) (acts t) = f (traj f s₀ acts t) (acts t)) :
    ∀ t, traj fhat s₀ acts t = traj f s₀ acts t := by
  intro t
  induction t with
  | zero => rfl
  | succ n ih => simp only [traj, ih, h n]

/-- **Proposition 1 (gate quotient).** If `f̂` agrees with `f` on a set `R` that
contains every query of `f`'s trajectory (the reachable query set), the trajectories
coincide. Every member of the extension class `E(f) = {f̂ : f̂|𝓡 = f|𝓡}` is therefore
indistinguishable along gate rollouts. -/
theorem prop1_gate_quotient (f fhat : S → A → S) (R : Set (S × A))
    (hR : ∀ s a, (s, a) ∈ R → fhat s a = f s a) (s₀ : S) (acts : ℕ → A)
    (hqueries : ∀ t, (traj f s₀ acts t, acts t) ∈ R) :
    ∀ t, traj fhat s₀ acts t = traj f s₀ acts t :=
  prop1_traj_eq f fhat s₀ acts fun t => hR _ _ (hqueries t)

/-- **No gate statistic distinguishes** two members of the extension class: any
function of the realized trajectory takes the same value. -/
theorem prop1_no_statistic_distinguishes {β : Type*} (stat : (ℕ → S) → β)
    (f fhat : S → A → S) (R : Set (S × A))
    (hR : ∀ s a, (s, a) ∈ R → fhat s a = f s a) (s₀ : S) (acts : ℕ → A)
    (hqueries : ∀ t, (traj f s₀ acts t, acts t) ∈ R) :
    stat (traj fhat s₀ acts) = stat (traj f s₀ acts) :=
  congrArg stat (funext (prop1_gate_quotient f fhat R hR s₀ acts hqueries))

end GateQuotient

/-! ## Constants at the frozen defaults: the speed bound, and the capstone -/

section Instrument

variable {V : Type*} [SeminormedAddCommGroup V] [NormedSpace ℝ V]

/-- One semi-implicit integrator step keeps the speed below `gain/drag`:
`‖v + dt•(gain•u − drag•v)‖ ≤ gain/drag` whenever `‖u‖ ≤ 1` and `‖v‖ ≤ gain/drag`. -/
theorem speed_invariant {gain drag dt : ℝ} (hg : 0 ≤ gain) (hd : 0 < drag)
    (hdt : 0 ≤ dt) (h1 : drag * dt ≤ 1) {v u : V} (hu : ‖u‖ ≤ 1)
    (hv : ‖v‖ ≤ gain / drag) :
    ‖v + dt • (gain • u - drag • v)‖ ≤ gain / drag := by
  have hrw : v + dt • (gain • u - drag • v)
      = (1 - drag * dt) • v + (dt * gain) • u := by module
  rw [hrw]
  have h1' : (0 : ℝ) ≤ 1 - drag * dt := by linarith
  calc ‖(1 - drag * dt) • v + (dt * gain) • u‖
      ≤ ‖(1 - drag * dt) • v‖ + ‖(dt * gain) • u‖ := norm_add_le _ _
    _ = (1 - drag * dt) * ‖v‖ + (dt * gain) * ‖u‖ := by
        rw [norm_smul, norm_smul, Real.norm_of_nonneg h1',
          Real.norm_of_nonneg (mul_nonneg hdt hg)]
    _ ≤ (1 - drag * dt) * (gain / drag) + (dt * gain) * 1 :=
        add_le_add (mul_le_mul_of_nonneg_left hv h1')
          (mul_le_mul_of_nonneg_left hu (mul_nonneg hdt hg))
    _ = gain / drag := by field_simp; ring

variable (gain drag dt : ℝ) (u : ℕ → V)

/-- The RingField2D-shaped free step on states `(position, velocity)`:
semi-implicit integrator with heading input `u t` (in the instrument,
`u t = (cos φ_t, sin φ_t)`, so `‖u t‖ = 1`). -/
def ringF (t : ℕ) (s : V × V) : V × V :=
  (s.1 + dt • (s.2 + dt • (gain • u t - drag • s.2)),
   s.2 + dt • (gain • u t - drag • s.2))

/-- RingField2D's freeze: stay at the previous position with zero velocity. -/
def ringFreeze (s : V × V) : V × V := (s.1, 0)

/-- Each tentative step moves the position by at most `dt · ‖v'‖`. -/
lemma ringF_step_dist (t : ℕ) (s : V × V) :
    dist ((ringF gain drag dt u t s).1) s.1
      = ‖dt • (s.2 + dt • (gain • u t - drag • s.2))‖ := by
  simp only [ringF]
  rw [dist_eq_norm, add_sub_cancel_left]

/-- **The capstone (Lemma 2 instantiated on the instrument's own dynamics).** For the
concrete freeze dynamics with bounded heading input, hypotheses `drag·dt ≤ 1` and step
bound `dt·gain/drag < r_out − r_in`: from an outside start at admissible speed, the
trajectory keeps `dist > r_out` and speed ≤ `gain/drag` forever — so the interior is
unreachable and, by `disc_annulus_traj_eq`, the filled disc is pathwise equivalent. -/
theorem ring_interior_unreachable {rIn rOut : ℝ}
    (hg : 0 ≤ gain) (hd : 0 < drag) (hdt : 0 ≤ dt) (h1 : drag * dt ≤ 1)
    (hΔw : dt * (gain / drag) < rOut - rIn)
    (hu : ∀ t, ‖u t‖ ≤ 1) (c p₀ v₀ : V)
    (h₀ : rOut < dist p₀ c) (hv₀ : ‖v₀‖ ≤ gain / drag) :
    ∀ t, rOut < dist ((freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze
          (annulus c rIn rOut) (p₀, v₀) t).1) c
        ∧ ‖(freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze
          (annulus c rIn rOut) (p₀, v₀) t).2‖ ≤ gain / drag := by
  intro t
  induction t with
  | zero => exact ⟨h₀, hv₀⟩
  | succ n ih =>
    obtain ⟨hp, hv⟩ := ih
    set s := freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze
      (annulus c rIn rOut) (p₀, v₀) n with hs
    have hv' : ‖s.2 + dt • (gain • u n - drag • s.2)‖ ≤ gain / drag :=
      speed_invariant hg hd hdt h1 (hu n) hv
    have hstepn : dist ((ringF gain drag dt u n s).1) s.1 ≤ dt * (gain / drag) := by
      rw [ringF_step_dist]
      rw [norm_smul, Real.norm_of_nonneg hdt]
      exact mul_le_mul_of_nonneg_left hv' hdt
    by_cases h : (ringF gain drag dt u n s).1 ∈ annulus c rIn rOut
    · have hnext : freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze
          (annulus c rIn rOut) (p₀, v₀) (n + 1) = ringFreeze s := by
        simp only [freezeTraj, ← hs, if_pos h]
      rw [hnext]
      refine ⟨hp, ?_⟩
      simp only [ringFreeze, norm_zero]
      exact div_nonneg hg hd.le
    · have hnext : freezeTraj Prod.fst (ringF gain drag dt u) ringFreeze
          (annulus c rIn rOut) (p₀, v₀) (n + 1) = ringF gain drag dt u n s := by
        simp only [freezeTraj, ← hs, if_neg h]
      rw [hnext]
      exact ⟨step_stays_out hΔw hp hstepn h, hv'⟩

/-- **The frozen defaults satisfy the hypotheses with margin**: gain = 3, drag = 0.3,
dt = 0.1, r_in = 3.5, r_out = 5 give top speed 10, step bound Δ = 1.0, and thickness
w = 1.5: `Δ < w`. (THEORY.md, "Constants at the frozen defaults".) -/
theorem ring2d_frozen_defaults_step_lt_thickness :
    (0 : ℝ) ≤ 3 ∧ (0 : ℝ) < 0.3 ∧ (0 : ℝ) ≤ 0.1 ∧ (0.3 : ℝ) * 0.1 ≤ 1 ∧
      (0.1 : ℝ) * (3 / 0.3) < 5 - 3.5 := by norm_num

/-- **r_int(0) = 0 pathwise at the frozen defaults**: with gain = 3, drag = 0.3,
dt = 0.1 and the ring at r_in = 3.5, r_out = 5, no trajectory of the freeze dynamics
started strictly outside (at admissible speed, e.g. from rest) ever has a position in
the open interior. -/
theorem ring2d_interior_unreachable_at_defaults
    (u : ℕ → V) (hu : ∀ t, ‖u t‖ ≤ 1) (c p₀ v₀ : V)
    (h₀ : (5 : ℝ) < dist p₀ c) (hv₀ : ‖v₀‖ ≤ 10) :
    ∀ t, ¬ dist ((freezeTraj Prod.fst (ringF (3 : ℝ) 0.3 0.1 u) ringFreeze
          (annulus c 3.5 5) (p₀, v₀) t).1) c < 3.5 := by
  intro t
  have h := (ring_interior_unreachable (V := V) 3 0.3 0.1 u
    (rIn := 3.5) (rOut := 5)
    (by norm_num) (by norm_num) (by norm_num) (by norm_num)
    (by norm_num) hu c p₀ v₀ h₀ (hv₀.trans (by norm_num)) t).1
  exact not_lt.mpr (le_of_lt (lt_trans (by norm_num) h))

end Instrument

end Paper3Ring
