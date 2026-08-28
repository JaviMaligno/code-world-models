/-
Paper 3, second tranche: Proposition 3 COMPOSED — the wrong-topology
(filled-disc) model is unfalsifiable AND harmless, with the planner/environment
loop made explicit (docs/paper3/THEORY.md, "Proposition 3").

The first tranche proved the pieces (`disc_annulus_traj_eq`,
`disc_annulus_same_return`, `prop1_gate_quotient`); what was missing was the
closed loop: a policy that REPLANS at every real step, from the real state,
with imagined rollouts of a MODEL. This file supplies that loop and composes:

  * `freezeStep`, `loopTraj`      — one environment step of the freeze
                                    semantics under a chosen action, and the
                                    closed loop of a (state, time)-policy with
                                    an environment.
  * `freezeStep_disc_annulus_agree`
                                  — at any state outside the band, the true
                                    (annulus) step and the filled-disc step
                                    agree for EVERY action: the two dynamics
                                    are indistinguishable one step at a time
                                    from outside.
  * `loop_freeze_stays_outside`   — the loop invariant: under any policy, real
                                    states stay strictly outside the band
                                    (Lemma 2's freeze half, upgraded from a
                                    fixed action stream to an arbitrary
                                    closed-loop policy).
  * `prop3_unfalsifiable_loop`,
    `prop3_no_statistic_distinguishes_loop`
                                  — Prop 3(i) composed: swapping the annulus
                                    for the filled disc changes NO rollout of
                                    any policy from outside — so no statistic
                                    of any gate rollout distinguishes them
                                    (gate rollouts are the special case of a
                                    state-independent policy).
  * `plannerPolicy`               — the planner abstraction the paper states:
                                    at real state s and step t, the action is
                                    ANY deterministic function of s, t, and
                                    the model's imagined rollouts from s over
                                    a candidate family (the seed lives in the
                                    function; the candidate family carries the
                                    contract integrator's step bound).
  * `planner_actions_agree`       — from outside, the planner on the wrong
                                    model picks the SAME action as the planner
                                    on the truth: imagination never queries
                                    the interior where they differ.
  * `prop3_harmless_loop`,
    `prop3_play_cost_zero`        — Prop 3(ii) composed: the closed-loop REAL
                                    trajectories under the two models'
                                    planners are identical
                                    realization-by-realization, so every
                                    return functional — play_cost included —
                                    coincides. The wrong topology is harmless.

Honesty note: everything is at realization level (a fixed candidate family
and a deterministic planner; the harness's seeded draws are one instance),
exactly as THEORY.md states Prop 3. Probability enters the paper's statement
only as "with probability 1 over seeds", quantifying over realizations of
this kind.
-/
import Paper3Ring.Basic

namespace Paper3Ring

variable {E : Type*} [PseudoMetricSpace E]
variable {σ : Type*} {A : Type*} {I : Type*}
variable {pos : σ → E} {freeze : σ → σ}

/-! ## The environment step and the closed loop -/

open Classical in
/-- One step of the freeze semantics as an ENVIRONMENT: tentative step `G a`,
mode set `M` on the landing position, freeze on contact. `freezeTraj` is the
special case of iterating this with a fixed action stream. -/
noncomputable def freezeStep (pos : σ → E) (G : A → σ → σ) (freeze : σ → σ)
    (M : Set E) (a : A) (s : σ) : σ :=
  if pos (G a s) ∈ M then freeze s else G a s

/-- The closed loop of a (state, time)-policy with an environment step. -/
def loopTraj (step : A → σ → σ) (π : σ → ℕ → A) (s₀ : σ) : ℕ → σ
  | 0 => s₀
  | t + 1 => step (π (loopTraj step π s₀ t) t) (loopTraj step π s₀ t)

section Loop

variable {G : A → σ → σ}

/-- One environment step from strictly outside the band stays strictly
outside, whatever the action: freeze preserves the position and a free step of
length ≤ Δ < r_out − r_in cannot leap the ring. -/
lemma freezeStep_stays_outside (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    {s : σ} (hs : rOut < dist (pos s) c) (a : A) :
    rOut < dist (pos (freezeStep pos G freeze (annulus c rIn rOut) a s)) c := by
  classical
  simp only [freezeStep]
  by_cases h : pos (G a s) ∈ annulus c rIn rOut
  · rw [if_pos h, hfreeze]; exact hs
  · rw [if_neg h]
    exact step_stays_out hΔw hs (hstep a s) h

/-- **At any outside state the true step and the filled-disc step agree, for
every action**: the tentative landing can never have distance < r_in (that
would leap the ring in one step), so membership in the annulus and in the
closed ball coincide at every query the dynamics can make from outside. -/
lemma freezeStep_disc_annulus_agree (c : E) {rIn rOut Δ : ℝ}
    (hΔw : Δ < rOut - rIn)
    (hstep : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    {s : σ} (hs : rOut < dist (pos s) c) (a : A) :
    freezeStep pos G freeze (annulus c rIn rOut) a s
      = freezeStep pos G freeze (Metric.closedBall c rOut) a s := by
  classical
  have h1 : rIn < dist (pos (G a s)) c := step_cannot_leap hΔw hs (hstep a s)
  have hiff : pos (G a s) ∈ annulus c rIn rOut
      ↔ pos (G a s) ∈ Metric.closedBall c rOut := by
    simp only [mem_annulus, Metric.mem_closedBall]
    exact ⟨fun ⟨_, h2⟩ => h2, fun h2 => ⟨h1.le, h2⟩⟩
  simp only [freezeStep]
  by_cases h : pos (G a s) ∈ annulus c rIn rOut
  · rw [if_pos h, if_pos (hiff.mp h)]
  · rw [if_neg h, if_neg (fun hD => h (hiff.mpr hD))]

/-- **The loop invariant** (Lemma 2's freeze half, for an arbitrary
closed-loop policy): real states stay strictly outside the band forever. -/
theorem loop_freeze_stays_outside (c : E) {rIn rOut Δ : ℝ}
    (hΔw : Δ < rOut - rIn)
    (hstep : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (π : σ → ℕ → A) {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, rOut < dist (pos (loopTraj
      (freezeStep pos G freeze (annulus c rIn rOut)) π s₀ t)) c := by
  intro t
  induction t with
  | zero => simpa [loopTraj] using h₀
  | succ n ih => exact freezeStep_stays_outside c hΔw hstep hfreeze ih _

/-! ## Proposition 3(i), composed: unfalsifiable in closed loop -/

/-- **Prop 3(i), composed.** Swapping the annulus environment for the
filled-disc environment changes NO closed-loop trajectory of any policy
started outside: the two dynamics agree at every (state, action) the loop
ever visits. Gate rollouts are the special case `π s t = acts t`. -/
theorem prop3_unfalsifiable_loop (c : E) {rIn rOut Δ : ℝ}
    (hΔw : Δ < rOut - rIn)
    (hstep : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (π : σ → ℕ → A) {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, loopTraj (freezeStep pos G freeze (annulus c rIn rOut)) π s₀ t
        = loopTraj (freezeStep pos G freeze (Metric.closedBall c rOut)) π s₀ t := by
  intro t
  induction t with
  | zero => rfl
  | succ n ih =>
    have hout := loop_freeze_stays_outside c hΔw hstep hfreeze π h₀ n
    simp only [loopTraj]
    rw [← ih]
    exact freezeStep_disc_annulus_agree c hΔw hstep hout _

/-- **No statistic of any closed-loop rollout distinguishes** the true annulus
from the filled disc: every sampling gate accepts the wrong topology. -/
theorem prop3_no_statistic_distinguishes_loop {β : Type*} (stat : (ℕ → σ) → β)
    (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstep : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (π : σ → ℕ → A) {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    stat (loopTraj (freezeStep pos G freeze (annulus c rIn rOut)) π s₀)
      = stat (loopTraj (freezeStep pos G freeze (Metric.closedBall c rOut)) π s₀) :=
  congrArg stat (funext (prop3_unfalsifiable_loop c hΔw hstep hfreeze π h₀))

/-! ## Proposition 3(ii), composed: the planner loop -/

variable (Fc : I → ℕ → σ → σ)

open Classical in
/-- The paper's planner abstraction: at real state `s` and step `t`, the
action is any deterministic function (`plan`, which carries the seed) of `s`,
`t`, and the MODEL's imagined rollouts from `s` over the candidate family
`Fc` — random-shooting MPC, CEM elites, and the harness planner are
instances. The model enters ONLY through the imagined rollouts. -/
noncomputable def plannerPolicy (pos : σ → E) (freeze : σ → σ)
    (Fc : I → ℕ → σ → σ) (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    (M : Set E) : σ → ℕ → A :=
  fun s t => plan t s (fun i => freezeTraj pos (Fc i) freeze M s)

/-- **From outside, the planner on the wrong model picks the same action as
the planner on the truth**: every candidate's imagined rollout is identical
under the two models (imagination never queries the interior where they
differ), and the planner is a function of those rollouts. -/
theorem planner_actions_agree (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstepFc : ∀ i t s, dist (pos (Fc i t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    {s : σ} (hs : rOut < dist (pos s) c) (t : ℕ) :
    plannerPolicy pos freeze Fc plan (annulus c rIn rOut) s t
      = plannerPolicy pos freeze Fc plan (Metric.closedBall c rOut) s t := by
  unfold plannerPolicy
  congr 1
  funext i
  exact funext (disc_annulus_traj_eq c hΔw (hstepFc i) hfreeze hs)

/-- **Prop 3(ii), composed (harmless).** In closed loop with the TRUE
environment, the planner planning on the filled-disc model produces the
identical real trajectory to the planner planning on the true model,
realization by realization. -/
theorem prop3_harmless_loop (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstepG : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hstepFc : ∀ i t s, dist (pos (Fc i t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    ∀ t, loopTraj (freezeStep pos G freeze (annulus c rIn rOut))
          (plannerPolicy pos freeze Fc plan (annulus c rIn rOut)) s₀ t
        = loopTraj (freezeStep pos G freeze (annulus c rIn rOut))
          (plannerPolicy pos freeze Fc plan (Metric.closedBall c rOut)) s₀ t := by
  intro t
  induction t with
  | zero => rfl
  | succ n ih =>
    have hout := loop_freeze_stays_outside c hΔw hstepG hfreeze
      (plannerPolicy pos freeze Fc plan (annulus c rIn rOut)) h₀ n
    simp only [loopTraj]
    rw [← ih, planner_actions_agree Fc c hΔw hstepFc hfreeze plan hout]

/-- **play_cost of the wrong topology is exactly 0**: every return functional
of the real trajectory coincides under the two planners — Proposition 3(ii)
as the paper states it, the planner/environment loop included. -/
theorem prop3_play_cost_zero {β : Type*} (J : (ℕ → σ) → β)
    (c : E) {rIn rOut Δ : ℝ} (hΔw : Δ < rOut - rIn)
    (hstepG : ∀ a s, dist (pos (G a s)) (pos s) ≤ Δ)
    (hstepFc : ∀ i t s, dist (pos (Fc i t s)) (pos s) ≤ Δ)
    (hfreeze : ∀ s, pos (freeze s) = pos s)
    (plan : ℕ → σ → (I → (ℕ → σ)) → A)
    {s₀ : σ} (h₀ : rOut < dist (pos s₀) c) :
    J (loopTraj (freezeStep pos G freeze (annulus c rIn rOut))
        (plannerPolicy pos freeze Fc plan (annulus c rIn rOut)) s₀)
      = J (loopTraj (freezeStep pos G freeze (annulus c rIn rOut))
        (plannerPolicy pos freeze Fc plan (Metric.closedBall c rOut)) s₀) :=
  congrArg J (funext
    (prop3_harmless_loop Fc c hΔw hstepG hstepFc hfreeze plan h₀))

end Loop

end Paper3Ring
