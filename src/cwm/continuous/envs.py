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


def integrate_2d(state, action, dt, gain, drag, a_max):
    """One semi-implicit Euler step for the 2D thrust-heading plant, shared
    by every 2D instrument/model so off-mode agreement is exact to float
    precision (the integrator is part of the contract)."""
    x, y, vx, vy = state
    a = max(-a_max, min(a_max, action))
    phi = math.pi * a / a_max
    vx2 = vx + (gain * math.cos(phi) - drag * vx) * dt
    vy2 = vy + (gain * math.sin(phi) - drag * vy) * dt
    return x + vx2 * dt, y + vy2 * dt, vx2, vy2


def invert_integrator(endpoint_xy, vx, vy, action, dt, gain, drag, a_max):
    """The previous state whose `integrate_2d` step lands its position
    exactly at `endpoint_xy`, given the (already-updated) velocity `vx,vy`
    the step used and the action that produced it."""
    a = max(-a_max, min(a_max, action))
    phi = math.pi * a / a_max
    vx2 = vx + (gain * math.cos(phi) - drag * vx) * dt
    vy2 = vy + (gain * math.sin(phi) - drag * vy) * dt
    return (endpoint_xy[0] - vx2 * dt, endpoint_xy[1] - vy2 * dt, vx, vy)


def thrust_vector_nd(action, gain: float, a_max: float) -> tuple:
    """Norm-capped thrust vector for the n-dim instruments' action interface
    (docs/paper3/SHELLFIELD-N-DESIGN.md, "the action interface"): each
    component is clamped to [-a_max, a_max] first (mirroring the 2D
    instruments' scalar clamp), then thrust = gain * a / max(1, ||a||), so
    ||thrust|| <= gain always -- the max thrust magnitude equals the 2D
    instruments' (gain, reached at phi = 0)."""
    a = tuple(max(-a_max, min(a_max, ai)) for ai in action)
    norm = math.sqrt(sum(ai * ai for ai in a))
    scale = gain / max(1.0, norm)
    return tuple(ai * scale for ai in a)


def integrate_nd(state, action, dt, gain, drag, a_max):
    """One semi-implicit Euler step for the n-dim thrust-vector plant
    (ShellFieldN). `state` is a flat 2n-tuple (first n = position, last n =
    velocity); byte-for-byte the same per-component update as `integrate_2d`
    once `thrust_vector_nd` replaces the heading trick, so the two families
    share one integration contract."""
    n = len(state) // 2
    pos, vel = state[:n], state[n:]
    thrust = thrust_vector_nd(action, gain, a_max)
    vel2 = tuple(v + (t - drag * v) * dt for v, t in zip(vel, thrust))
    pos2 = tuple(p + v2 * dt for p, v2 in zip(pos, vel2))
    return pos2 + vel2


def _embed_xy(xy: tuple, n: int) -> tuple:
    """Embed a 2D point in R^n, first two coordinates only (the geometry-
    normalization convention of SHELLFIELD-N-DESIGN.md: c and the real lode
    live in the fixed 2-plane so n is the only knob that varies)."""
    if n < 2:
        raise ValueError("ShellFieldN requires n >= 2")
    return (xy[0], xy[1]) + (0.0,) * (n - 2)


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

    patch_shape="square" is the fixed-topology ablation (2026-07-19): the
    same two patches as axis-aligned squares of half-side R (Chebyshev ball),
    so membership is a max/abs predicate instead of a quadratic one. Both
    shapes are contractible and bi-modal; only boundary curvature and the
    predicate's descriptive form differ — the contrast that separates
    "repair fails on curved boundaries" from "repair fails on 2D regions".
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
    patch_shape: str = "disc"   # "disc" | "square" (fixed-topology ablation)

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
        if c is None:
            return False
        if self.patch_shape == "square":
            return max(abs(x - c[0]), abs(y - c[1])) <= self.R
        return (x - c[0]) ** 2 + (y - c[1]) ** 2 <= self.R ** 2

    def _integrate(self, state: State, action: float):
        return integrate_2d(state, action, self.dt, self.gain, self.drag, self.a_max)

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


@dataclass(frozen=True)
class RingField2D:
    """Paper-3 opening instrument: an annular sticky mode enclosing the lure.

    Same 4D state, scalar heading action, integrator and freeze semantics as
    PatchField2D. The mode region is an annulus r_in <= dist(pos', center)
    <= r_out around `center`, and the phantom lode sits AT `center` —
    strictly inside the hole. Knobs (docs/paper3/RESEARCH-DIRECTION.md §3):

    - `gap` (radians): angular width of a channel cut from the ring, centered
      at `gap_center` (default: facing the start). gap = 0 is the closed ring
      (beta_1 = 1): the interior is REACH-NULL — no trajectory of the true
      dynamics ever enters it (crossing lemma, docs/paper3/THEORY.md), so
      whatever a certified model says there is pure prior. gap > 0 is
      contractible and re-opens the interior through a channel of tunable
      sampling mass — the (1-r)^N regime returns continuously.
    - `filled`: the wrong-topology model (annulus completed to a disc:
      freezes the interior too). At gap = 0, planner-equivalent to the true
      ring for any planner whose imagined steps are shorter than the ring
      thickness (Proposition 3, THEORY.md) — wrong topology that is both
      unfalsifiable and harmless; gap > 0 makes it consequential.
    - `r_in = None`: the mode-blind model (no ring at all).

    Geometry defaults keep the crossing lemma's hypothesis with margin: top
    speed is gain/drag = 10, so a step moves at most 1.0 < r_out - r_in = 1.5.
    """
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    center: tuple = (12.0, 0.0)
    r_in: float | None = 3.5
    r_out: float = 5.0
    gap: float = 0.0
    gap_center: float = math.pi
    filled: bool = False
    lode_real: tuple = (-6.0, 0.0)
    amp_real: float = 0.3
    amp_phantom: float = 1.0
    r0: float = 2.0
    width: float = 0.5
    h_episode: int = 80
    x0_range: float = 0.5
    x0_center: tuple = (0.0, 0.0)   # start placement; set to `center` for
                                    # inside-the-hole episodes (mu0 knob:
                                    # moves the reachable set, Prop 1)

    def initial_state(self, rng) -> State:
        return (self.x0_center[0] + rng.uniform(-self.x0_range, self.x0_range),
                self.x0_center[1] + rng.uniform(-self.x0_range, self.x0_range),
                0.0, 0.0)

    def _lode(self, x: float, y: float, lode: tuple, amp: float) -> float:
        d = math.hypot(x - lode[0], y - lode[1])
        return amp / (1.0 + math.exp((d - self.r0) / self.width))

    def reward(self, state: State) -> float:
        x, y = state[0], state[1]
        return (self._lode(x, y, self.lode_real, self.amp_real)
                + self._lode(x, y, self.center, self.amp_phantom))

    def in_interior(self, x: float, y: float) -> bool:
        """Strictly inside the hole (call on the TRUTH env: the reach-null
        measurement is about the true geometry, not a model's)."""
        if self.r_in is None:
            return False
        return math.hypot(x - self.center[0], y - self.center[1]) < self.r_in

    def _in_mode(self, x: float, y: float) -> bool:
        if self.r_in is None:
            return False
        d = math.hypot(x - self.center[0], y - self.center[1])
        lo = 0.0 if self.filled else self.r_in
        if not (lo <= d <= self.r_out):
            return False
        if self.gap > 0.0:
            ang = math.atan2(y - self.center[1], x - self.center[0])
            delta = (ang - self.gap_center + math.pi) % (2 * math.pi) - math.pi
            if abs(delta) <= self.gap / 2.0:
                return False
        return True

    def _integrate(self, state: State, action: float):
        return integrate_2d(state, action, self.dt, self.gain, self.drag,
                            self.a_max)

    def contact_mode(self, state: State, action: float) -> bool:
        x2, y2, _, _ = self._integrate(state, action)
        return self._in_mode(x2, y2)

    def step(self, state: State, action: float):
        x2, y2, vx2, vy2 = self._integrate(state, action)
        if self._in_mode(x2, y2):
            s2 = (state[0], state[1], 0.0, 0.0)
            return s2, self.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.reward(s2), False


@dataclass(frozen=True)
class ShapeField2D:
    """Fourth instrument: single-mode 2D navigation against an arbitrary
    `Shape` (the geometry-repair generalization of PatchField2D's disc).
    Same plant/reward as PatchField2D (reuses its physics constants and
    lodes); the single hard mode is `shape.contains(next_xy)` instead of a
    hardcoded disc test. `shape=None` is the blind variant. `_integrate`
    delegates to the shared `integrate_2d` so this stays bit-exact with
    every other 2D instrument off-mode."""
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    shape: "object | None" = None
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

    def _inside(self, x: float, y: float) -> bool:
        return self.shape is not None and self.shape.contains((x, y))

    def _integrate(self, state: State, action: float):
        return integrate_2d(state, action, self.dt, self.gain, self.drag, self.a_max)

    def contact(self, state: State, action: float) -> bool:
        x2, y2, _, _ = self._integrate(state, action)
        return self._inside(x2, y2)

    def step(self, state: State, action: float):
        x2, y2, vx2, vy2 = self._integrate(state, action)
        if self._inside(x2, y2):
            s2 = (state[0], state[1], 0.0, 0.0)
            return s2, self.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.reward(s2), False


@dataclass(frozen=True)
class ShellFieldN:
    """Paper-3 n-dim arm, step 1 (docs/paper3/SHELLFIELD-N-DESIGN.md): the
    n-dimensional generalization of RingField2D. State (x⃗, v⃗) in R^{2n},
    represented as a flat 2n-tuple (first n = position, last n = velocity).

    The action is a thrust VECTOR a⃗ in [-1,1]^n, NOT the 2D instruments'
    scalar heading (that parameterization does not generalize -- design
    note, "the action interface"): thrust = gain * a⃗ / max(1, ||a⃗||), a
    norm cap so ||thrust|| <= gain always, matching the 2D instruments' max
    thrust magnitude. Same semi-implicit Euler, same dt/gain/drag as every
    2D instrument (`integrate_nd`/`thrust_vector_nd` share the contract).

    Mode = spherical shell r_in <= ||x⃗' - c|| <= r_out (Euclidean norm in
    R^n); freeze-at-previous-position-with-zero-velocity semantics are
    bit-identical to RingField2D's. Geometry is normalized across n: `c`
    and the real lode sit in the fixed first-two-coordinates 2-plane
    (c = (12, 0, 0, ...), lode_real at (-6, 0, 0, ...)), and r_in/r_out/lode
    constants/h_episode are pinned at the 2D values, so n is the only knob
    that varies -- the r(n)/r_int(n) concentration-of-measure measurement
    (design note SS8.2) isolates the dimension effect purely.

    r_in=None is the mode-blind model (blind_of): no shell, no freeze.
    """
    n: int
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    center_xy: tuple = (12.0, 0.0)
    r_in: float | None = 3.5
    r_out: float = 5.0
    lode_real_xy: tuple = (-6.0, 0.0)
    amp_real: float = 0.3
    amp_phantom: float = 1.0
    r0: float = 2.0
    width: float = 0.5
    h_episode: int = 80
    x0_range: float = 0.5

    def __post_init__(self):
        if self.n < 2:
            raise ValueError("ShellFieldN requires n >= 2")

    def center(self) -> tuple:
        return _embed_xy(self.center_xy, self.n)

    def lode_real(self) -> tuple:
        return _embed_xy(self.lode_real_xy, self.n)

    def initial_state(self, rng) -> State:
        pos = [0.0] * self.n
        pos[0] = rng.uniform(-self.x0_range, self.x0_range)
        pos[1] = rng.uniform(-self.x0_range, self.x0_range)
        return tuple(pos) + tuple(0.0 for _ in range(self.n))

    @staticmethod
    def _dist(p: tuple, q: tuple) -> float:
        return math.sqrt(sum((pi - qi) ** 2 for pi, qi in zip(p, q)))

    def _lode(self, pos: tuple, point: tuple, amp: float) -> float:
        d = self._dist(pos, point)
        return amp / (1.0 + math.exp((d - self.r0) / self.width))

    def reward(self, state: State) -> float:
        pos = state[: self.n]
        return (self._lode(pos, self.lode_real(), self.amp_real)
                + self._lode(pos, self.center(), self.amp_phantom))

    def in_interior(self, pos: tuple) -> bool:
        """Strictly inside the hole (call on the TRUTH env, mirroring
        RingField2D.in_interior: the reach-null measurement is about the
        true geometry, not a model's)."""
        if self.r_in is None:
            return False
        return self._dist(pos, self.center()) < self.r_in

    def _in_mode(self, pos: tuple) -> bool:
        if self.r_in is None:
            return False
        d = self._dist(pos, self.center())
        return self.r_in <= d <= self.r_out

    def _integrate(self, state: State, action: tuple) -> State:
        return integrate_nd(state, action, self.dt, self.gain, self.drag,
                            self.a_max)

    def contact_mode(self, state: State, action: tuple) -> bool:
        s2 = self._integrate(state, action)
        return self._in_mode(s2[: self.n])

    def step(self, state: State, action: tuple):
        s2 = self._integrate(state, action)
        pos2 = s2[: self.n]
        if self._in_mode(pos2):
            frozen = state[: self.n] + (0.0,) * self.n
            return frozen, self.reward(frozen), True
        return s2, self.reward(s2), False


def filled_of(env: "RingField2D") -> "RingField2D":
    """The wrong-topology model: the annulus completed to a disc."""
    return replace(env, filled=True)


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
    if isinstance(env, RingField2D):
        return replace(env, r_in=None)
    if isinstance(env, ShapeField2D):
        return replace(env, shape=None)
    if isinstance(env, ShellFieldN):
        return replace(env, r_in=None)
    return replace(env, x_wall=None)


def biased_of(env: CartWall, drag_scale: float) -> CartWall:
    """The pervasive-error control: globally mis-scaled drag, wall intact.
    Its error is everywhere (every transition with v != 0) and nowhere large —
    the opposite error geometry to the localized mode omission."""
    return replace(env, drag=env.drag * drag_scale)


def unbumped_of(env: CartWall) -> CartWall:
    """The smooth-contrast blind model: omits the localized drag bump."""
    return replace(env, bump_amp=0.0)
