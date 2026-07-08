"""Distrust-region replanning: the mitigation experiment (paper 2).

Planner-side only — the model is never modified. After executing each real
action the planner compares the model's prediction against the observed next
state; a mismatch beyond tol records the PRE-state as a violation point
(pinned-integrator world: a correct model matches to float precision, so any
real mode mismatch is orders of magnitude above tol=1e-6).

Each violation records the POSITION of the model's refuted prediction — its
"fence". False predictions always lie ON/BEYOND the mode boundary (the clamp
fires exactly when the model predicts a crossing), so fences are one-sided by
construction. During imagination, a candidate rollout is TRUNCATED the first
time an imagined STEP's position interval overlaps any fence's eps-band:
segment overlap, not point distance, makes the fence leap-proof at any
imagined speed; once the imagined trajectory crosses a place where the model
was proven wrong, nothing downstream of it is trustworthy. (Rejected designs,
kept as a finding — the argmax planner is an adversary against any incomplete
fence: flee metrics over PRE-STATE balls are either trapped between
overlapping balls (first-step) or biased toward the phantom side (final-state
— violations can only be recorded on the truth side, so the far side always
looks "far from where the model lied"); full-state POINT fences at the false
predictions are dodged by probing new crossing velocities, one contact per
dodge.)

When every candidate truncates (the pinned case) totals tie near zero; the
tie-break keeps stepping the model past the truncation point WITHOUT
accumulating reward and ranks by the FINAL imagined state's position distance
to the nearest fence. One-sided fences make this structurally away-biased:
the real side always wins. Direction-only use of the model's kinematics
beyond truncation is weaker trust than believing its reward claims; no reward
is ever accumulated there.

With a correct model no violation ever fires and plan_mitigated scores and
ranks candidates exactly as mpc.plan does (same candidate generator, same rng
draws, same strict-argmax) — the zero-cost control holds by construction and
is asserted bitwise in tests/test_mitigation.py.
"""
import random
from dataclasses import dataclass

from . import mpc


def _crosses_fence(prev_x: float, next_x: float, fences, eps: float) -> bool:
    """Does the imagined step's position interval overlap any fence's
    eps-band? Segment overlap, not point distance — leap-proof."""
    lo, hi = min(prev_x, next_x), max(prev_x, next_x)
    return any(lo <= f + eps and hi >= f - eps for f in fences)


def _dist_to_nearest(x: float, fences) -> float:
    return min(abs(x - f) for f in fences) if fences else 0.0


def plan_mitigated(model, state, rng, fences, eps,
                   horizon: int = 40, n_samples: int = 200,
                   block: int = 10) -> float:
    """mpc.plan with distrust-fence truncation. With fences == [] this is
    bit-identical to mpc.plan (same candidates, same scores, same argmax)."""
    best_key, best_a0 = None, 0.0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, total, truncated = state, 0.0, False
        for a in acts:
            prev_x = s[0]
            s, r, _ = model.step(s, a)
            if truncated:
                continue  # keep stepping for the flee tie-break; no reward
            if fences and _crosses_fence(prev_x, s[0], fences, eps):
                truncated = True  # nothing downstream is trustworthy
                continue
            total += r
        key = (total, _dist_to_nearest(s[0], fences))  # s = final imagined state
        if best_key is None or key > best_key:
            best_key, best_a0 = key, acts[0]
    return best_a0


@dataclass
class MitigatedEpisode:
    ret: float
    contact: bool
    final_state: tuple
    violations: int              # violation points recorded over the episode
    first_contact_step: int | None


def run_mitigated_episode(truth, model, seed: int = 0, horizon: int = 40,
                          n_samples: int = 200, block: int = 10,
                          tol: float = 1e-6, eps: float = 0.25) -> MitigatedEpisode:
    """Play one episode in `truth`, planning on `model` with distrust-region
    replanning. Mirrors harness.run_episode's rng discipline exactly so the
    truth-model episode is bit-identical to the plain MPC one."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact, first_contact = 0.0, False, None
    fences: list = []
    for t in range(truth.h_episode):
        a = plan_mitigated(model, s, rng, fences, eps,
                           horizon=horizon, n_samples=n_samples, block=block)
        s2, r, c = truth.step(s, a)
        pred, _, _ = model.step(s, a)
        if max(abs(pred[0] - s2[0]), abs(pred[1] - s2[1])) > tol:
            fences.append(pred[0])  # position of the FALSE prediction
        if c and first_contact is None:
            first_contact = t
        contact = contact or c
        total += r
        s = s2
    return MitigatedEpisode(ret=total, contact=contact, final_state=s,
                            violations=len(fences),
                            first_contact_step=first_contact)
