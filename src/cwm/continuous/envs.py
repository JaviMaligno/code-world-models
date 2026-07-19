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


@dataclass(frozen=True)
class PendulumStop:
    """Second hybrid instrument: pendulum with a hard angular stop.

    The base plant is NONLINEAR (gravity term sin(theta); theta = 0 hanging
    down), so this checks the mechanism is not an artifact of the cart's
    linear off-mode dynamics. Rarity is natural here: gravity confines the
    random walk near the bottom and climbing is rare. Same interface as
    CartWall (state (theta, omega)); the mode is an inelastic stop at
    th_stop, and blind_of() removes it.
    """
    dt: float = 0.1
    gain: float = 3.0          # torque gain; > grav so directed swing-up works
    grav: float = 2.0
    drag: float = 0.3
    a_max: float = 1.0
    th_stop: float | None = 1.2
    th_left: float = -2.0
    a_left: float = 0.3
    th_right: float = 3.0
    a_right: float = 1.0
    width: float = 0.25
    h_episode: int = 80
    th0_range: float = 0.3

    def initial_state(self, rng) -> State:
        return (rng.uniform(-self.th0_range, self.th0_range), 0.0)

    def reward(self, state: State) -> float:
        th = state[0]
        left = self.a_left / (1.0 + math.exp(-((self.th_left - th) / self.width)))
        right = self.a_right / (1.0 + math.exp(-((th - self.th_right) / self.width)))
        return left + right

    def step(self, state: State, action: float) -> tuple[State, float, bool]:
        th, om = state
        a = max(-self.a_max, min(self.a_max, action))
        om2 = om + (self.gain * a - self.grav * math.sin(th)
                    - self.drag * om) * self.dt
        th2 = th + om2 * self.dt
        contact = False
        if self.th_stop is not None and th2 >= self.th_stop:
            th2, om2, contact = self.th_stop, 0.0, True
        s2 = (th2, om2)
        return s2, self.reward(s2), contact


@dataclass(frozen=True)
class PatchField2D:
    """Third instrument: 2D navigation with two sticky patches (bi-modal).

    4D state (x, y, vx, vy); SCALAR action a in [-a_max, a_max] mapped to a
    thrust heading phi = pi*a/a_max, so every planner (mpc, cem, harness)
    works unchanged. Each patch is an independent hard mode: a step whose
    next position falls inside disc(p_i, R) freezes at the PREVIOUS position
    with zero velocity (inelastic stop at the edge). blind_of removes both
    patches; blind_of_modes removes a subset. Reward is two radial sigmoid
    lodes: a small real one behind the start and a large phantom one beyond
    the patches (the lure). Patch centers are the rarity knobs
    (calibration 2026-07-16: r1=0.1417, r2=0.0083 at the defaults).
    """
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    p1: tuple | None = (3.0, 0.0)
    p2: tuple | None = (7.0, 0.0)
    R: float = 1.0
    lode_real: tuple = (-6.0, 0.0)
    amp_real: float = 0.3
    lode_phantom: tuple = (12.0, 0.0)
    amp_phantom: float = 1.0
    r0: float = 2.0
    width: float = 0.5
    h_episode: int = 80
    x0_range: float = 0.5

    def initial_state(self, rng) -> State:
        return (rng.uniform(-self.x0_range, self.x0_range),
                rng.uniform(-self.x0_range, self.x0_range), 0.0, 0.0)

    def _lode(self, x: float, y: float, lode: tuple, amp: float) -> float:
        d = math.hypot(x - lode[0], y - lode[1])
        return amp / (1.0 + math.exp((d - self.r0) / self.width))

    def reward(self, state: State) -> float:
        x, y = state[0], state[1]
        return (self._lode(x, y, self.lode_real, self.amp_real)
                + self._lode(x, y, self.lode_phantom, self.amp_phantom))

    def _inside(self, x: float, y: float, c: tuple | None) -> bool:
        return (c is not None
                and (x - c[0]) ** 2 + (y - c[1]) ** 2 <= self.R ** 2)

    def _integrate(self, state: State, action: float):
        x, y, vx, vy = state
        a = max(-self.a_max, min(self.a_max, action))
        phi = math.pi * a / self.a_max
        vx2 = vx + (self.gain * math.cos(phi) - self.drag * vx) * self.dt
        vy2 = vy + (self.gain * math.sin(phi) - self.drag * vy) * self.dt
        return x + vx2 * self.dt, y + vy2 * self.dt, vx2, vy2

    def contact_modes(self, state: State, action: float) -> tuple:
        x2, y2, _, _ = self._integrate(state, action)
        return self._inside(x2, y2, self.p1), self._inside(x2, y2, self.p2)

    def step(self, state: State, action: float):
        x2, y2, vx2, vy2 = self._integrate(state, action)
        if self._inside(x2, y2, self.p1) or self._inside(x2, y2, self.p2):
            s2 = (state[0], state[1], 0.0, 0.0)
            return s2, self.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.reward(s2), False


def blind_of_modes(env: "PatchField2D", omit: tuple) -> "PatchField2D":
    """Mode-selective blind model for the 2D instrument."""
    kw = {}
    if "p1" in omit:
        kw["p1"] = None
    if "p2" in omit:
        kw["p2"] = None
    return replace(env, **kw)


def blind_of(env):
    """The mode-omitting model of `env`: identical plant, no wall/stop."""
    if isinstance(env, PendulumStop):
        return replace(env, th_stop=None)
    if isinstance(env, PatchField2D):
        return replace(env, p1=None, p2=None)
    return replace(env, x_wall=None)


def biased_of(env: CartWall, drag_scale: float) -> CartWall:
    """The pervasive-error control: globally mis-scaled drag, wall intact.
    Its error is everywhere (every transition with v != 0) and nowhere large —
    the opposite error geometry to the localized mode omission."""
    return replace(env, drag=env.drag * drag_scale)


def unbumped_of(env: CartWall) -> CartWall:
    """The smooth-contrast blind model: omits the localized drag bump."""
    return replace(env, bump_amp=0.0)
