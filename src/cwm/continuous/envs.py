"""Cart-with-wall: the continuous/hybrid rare-mode instrument.

1D point mass with drag under bounded thrust, semi-implicit Euler (the
integrator is part of the contract — truth and any synthesized model share it,
so off-mode agreement can be exact to float precision). The hybrid mode is an
inelastic wall at x_wall: crossing clamps position and zeroes velocity. The
blind variant (x_wall=None) is the same code path minus the wall branch — the
hand-written on-manifold proxy for a CWM synthesized from a spec that omits
the wall, bit-exact off-mode by construction.

Reward is two plateaus: a small reachable one on the left and a large one on
the right whose approach every swept wall position blocks. The truth planner
goes left; a wall-blind planner is lured right and pinned at the wall
collecting ~nothing. Wall position is the rarity knob: random rollouts hit a
near wall often and a far wall almost never (calibration 2026-07-06: rarity
0.33 -> 0.0025 over x_wall in [2, 10] at the defaults below).

The smooth-bump contrast replaces the wall with a C-infinity localized drag
increase of comparable "size" — the arm that tests whether the localized
danger mechanism really requires a discontinuity.
"""
import math
from dataclasses import dataclass, replace


State = tuple  # (x, v)


@dataclass(frozen=True)
class CartWall:
    # plant
    dt: float = 0.1
    gain: float = 3.0          # thrust gain: dv = (gain*a - drag(x)*v) * dt
    drag: float = 0.3
    a_max: float = 1.0
    # hybrid mode: inelastic wall (None = mode absent -> the blind model)
    x_wall: float | None = 4.0
    # reward: two sigmoid plateaus
    x_left: float = -6.0
    a_left: float = 0.3
    x_right: float = 12.0
    a_right: float = 1.0
    width: float = 0.5
    # smooth-bump contrast (amp 0 = off): drag(x) = drag + amp*gauss(x)
    bump_amp: float = 0.0
    bump_center: float = 4.0
    bump_width: float = 0.5
    # episode
    h_episode: int = 80
    x0_range: float = 0.5      # x0 ~ U(-x0_range, x0_range), v0 = 0

    def initial_state(self, rng) -> State:
        return (rng.uniform(-self.x0_range, self.x0_range), 0.0)

    def drag_at(self, x: float) -> float:
        if self.bump_amp == 0.0:
            return self.drag
        z = (x - self.bump_center) / self.bump_width
        return self.drag + self.bump_amp * math.exp(-0.5 * z * z)

    def reward(self, state: State) -> float:
        x = state[0]
        left = self.a_left / (1.0 + math.exp(-((self.x_left - x) / self.width)))
        right = self.a_right / (1.0 + math.exp(-((x - self.x_right) / self.width)))
        return left + right

    def step(self, state: State, action: float) -> tuple[State, float, bool]:
        """One semi-implicit Euler step. Returns (state', reward(state'),
        contact) where contact is True iff the wall clamp fired."""
        x, v = state
        a = max(-self.a_max, min(self.a_max, action))
        v2 = v + (self.gain * a - self.drag_at(x) * v) * self.dt
        x2 = x + v2 * self.dt
        contact = False
        if self.x_wall is not None and x2 >= self.x_wall:
            x2, v2, contact = self.x_wall, 0.0, True
        s2 = (x2, v2)
        return s2, self.reward(s2), contact


def blind_of(env: CartWall) -> CartWall:
    """The mode-omitting model of `env`: identical plant, no wall."""
    return replace(env, x_wall=None)


def biased_of(env: CartWall, drag_scale: float) -> CartWall:
    """The pervasive-error control: globally mis-scaled drag, wall intact.
    Its error is everywhere (every transition with v != 0) and nowhere large —
    the opposite error geometry to the localized mode omission."""
    return replace(env, drag=env.drag * drag_scale)


def unbumped_of(env: CartWall) -> CartWall:
    """The smooth-contrast blind model: omits the localized drag bump."""
    return replace(env, bump_amp=0.0)
