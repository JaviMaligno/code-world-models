"""Instrument-specific pieces of the synthesis contract (paper 2 LLM arms).

The contract machinery in `contract.py` is otherwise env-generic; this module
holds the ONLY parts that differ per instrument — the integrator API text, the
rules text (constants + reward + mode rule), and the mode-region probes — behind
an `InstrumentSpec` selected by `spec_for(env)`. The cart spec reproduces the
pre-refactor prompt byte-for-byte (golden test) so committed results stay valid.
"""
from dataclasses import dataclass
from typing import Callable

from .envs import CartWall, PatchField2D, PendulumStop

# --- cart (linear plant) -----------------------------------------------------
CART_API_TEXT = """\
Implement a deterministic 1D control world model as Python module-level
functions (pure, no I/O, no globals, only the `math` standard-library module).

State is a list [x, v] of two floats (position, velocity). Action is a float.

Functions to implement EXACTLY these signatures:
  def step(state: list, action: float) -> list   # next [x, v]
  def reward(state: list) -> float               # reward of a state

The integrator is FIXED and part of the contract. step() must compute, in
exactly this order, with plain Python floats:
  1. a = min(a_max, max(-a_max, action))         # clamp the action
  2. v2 = v + (gain * a - drag * v) * dt
  3. x2 = x + v2 * dt
then apply any additional dynamics rules given below, and return [x2, v2].
"""


def _cart_rules_text(env: CartWall, include_mode: bool, omit: tuple = ()) -> str:
    if omit:
        raise ValueError("omit is only supported by the patch2d instrument")
    lines = [
        "Physical constants:",
        f"  dt = {env.dt}",
        f"  gain = {env.gain}",
        f"  drag = {env.drag}",
        f"  a_max = {env.a_max}",
        "",
        "Reward (a function of the state [x, v] alone):",
        f"  left  = {env.a_left} / (1.0 + math.exp(-(({env.x_left} - x) / {env.width})))",
        f"  right = {env.a_right} / (1.0 + math.exp(-((x - {env.x_right}) / {env.width})))",
        "  reward = left + right",
    ]
    if include_mode:
        if env.x_wall is None:
            raise ValueError("env has no wall; cannot write the wall clause")
        lines += [
            "",
            "Additional dynamics rule:",
            f"  There is an immovable wall at x = {env.x_wall}. After computing",
            f"  x2 and v2 as above, if x2 >= {env.x_wall}, the cart stops at the",
            f"  wall inelastically: the next state is exactly [{env.x_wall}, 0.0].",
        ]
    return "\n".join(lines)


def _cart_mode_probes(env: CartWall):
    # states just below the wall moving right under full thrust — each fires
    # the clamp in truth.
    return {"wall": [((env.x_wall - 0.1, v), env.a_max) for v in (1.0, 2.0, 4.0)]}


# --- pendulum (nonlinear plant) ----------------------------------------------
PENDULUM_API_TEXT = """\
Implement a deterministic 1D control world model as Python module-level
functions (pure, no I/O, no globals, only the `math` standard-library module).

State is a list [th, om] of two floats (angle, angular velocity). Action is a
float.

Functions to implement EXACTLY these signatures:
  def step(state: list, action: float) -> list   # next [th, om]
  def reward(state: list) -> float               # reward of a state

The integrator is FIXED and part of the contract. step() must compute, in
exactly this order, with plain Python floats:
  1. a = min(a_max, max(-a_max, action))                  # clamp the action
  2. om2 = om + (gain * a - grav * math.sin(th) - drag * om) * dt
  3. th2 = th + om2 * dt
then apply any additional dynamics rules given below, and return [th2, om2].
"""


def _pendulum_rules_text(env: PendulumStop, include_mode: bool,
                         omit: tuple = ()) -> str:
    if omit:
        raise ValueError("omit is only supported by the patch2d instrument")
    lines = [
        "Physical constants:",
        f"  dt = {env.dt}",
        f"  gain = {env.gain}",
        f"  grav = {env.grav}",
        f"  drag = {env.drag}",
        f"  a_max = {env.a_max}",
        "",
        "Reward (a function of the state [th, om] alone):",
        f"  left  = {env.a_left} / (1.0 + math.exp(-(({env.th_left} - th) / {env.width})))",
        f"  right = {env.a_right} / (1.0 + math.exp(-((th - {env.th_right}) / {env.width})))",
        "  reward = left + right",
    ]
    if include_mode:
        if env.th_stop is None:
            raise ValueError("env has no stop; cannot write the stop clause")
        lines += [
            "",
            "Additional dynamics rule:",
            f"  There is an immovable angular stop at th = {env.th_stop}. After",
            f"  computing th2 and om2 as above, if th2 >= {env.th_stop}, the",
            f"  pendulum stops inelastically: the next state is exactly "
            f"[{env.th_stop}, 0.0].",
        ]
    return "\n".join(lines)


def _pendulum_mode_probes(env: PendulumStop):
    # states just below the stop swinging up under full torque — each fires the
    # stop in truth.
    return {"stop": [((env.th_stop - 0.1, om), env.a_max) for om in (1.0, 2.0, 4.0)]}


# --- patch2d (2D bi-modal plant) ---------------------------------------------
PATCH2D_API_TEXT = """\
Implement a deterministic 2D control world model as Python module-level
functions (pure, no I/O, no globals, only the `math` standard-library module).

State is a list [x, y, vx, vy] of four floats (position, velocity). Action is
a single float, mapped to a thrust heading.

Functions to implement EXACTLY these signatures:
  def step(state: list, action: float) -> list   # next [x, y, vx, vy]
  def reward(state: list) -> float               # reward of a state

The integrator is FIXED and part of the contract. step() must compute, in
exactly this order, with plain Python floats:
  1. a = min(a_max, max(-a_max, action))          # clamp the action
  2. phi = pi * a / a_max                         # thrust heading
  3. vx2 = vx + (gain * cos(phi) - drag * vx) * dt
  4. vy2 = vy + (gain * sin(phi) - drag * vy) * dt
  5. x2 = x + vx2 * dt
  6. y2 = y + vy2 * dt
then apply any additional dynamics rules given below, and return
[x2, y2, vx2, vy2].
"""


def _patch2d_rules_text(env: PatchField2D, include_mode: bool,
                        omit: tuple = ()) -> str:
    lines = [
        "Physical constants:",
        f"  dt = {env.dt}",
        f"  gain = {env.gain}",
        f"  drag = {env.drag}",
        f"  a_max = {env.a_max}",
        "",
        "Reward (a function of the state [x, y, vx, vy], via x and y alone):",
        f"  d1 = math.hypot(x - ({env.lode_real[0]}), y - ({env.lode_real[1]}))",
        f"  d2 = math.hypot(x - ({env.lode_phantom[0]}), y - ({env.lode_phantom[1]}))",
        f"  real    = {env.amp_real} / (1.0 + math.exp((d1 - {env.r0}) / {env.width}))",
        f"  phantom = {env.amp_phantom} / (1.0 + math.exp((d2 - {env.r0}) / {env.width}))",
        "  reward = real + phantom",
    ]
    if include_mode:
        patches = []
        if env.p1 is not None and "p1" not in omit:
            patches.append(("p1", env.p1))
        if env.p2 is not None and "p2" not in omit:
            patches.append(("p2", env.p2))
        if not patches:
            raise ValueError("env has no patches; cannot write mode clause(s)")
        for _name, c in patches:
            if env.patch_shape == "square":
                lines += [
                    "",
                    "Additional dynamics rule:",
                    f"  There is a sticky square patch centered at (x, y) = "
                    f"({c[0]}, {c[1]})",
                    f"  with half-side R = {env.R}. After computing x2 and y2 "
                    f"as above,",
                    f"  if max(abs(x2 - {c[0]}), abs(y2 - {c[1]})) <= {env.R},",
                    "  the mover sticks: the next state is exactly "
                    "[x, y, 0.0, 0.0]",
                    "  (the PREVIOUS position, with zero velocity).",
                ]
            else:
                lines += [
                    "",
                    "Additional dynamics rule:",
                    f"  There is a sticky patch centered at (x, y) = ({c[0]}, {c[1]})",
                    f"  with radius R = {env.R}. After computing x2 and y2 as above,",
                    f"  if (x2 - {c[0]}) ** 2 + (y2 - {c[1]}) ** 2 <= {env.R ** 2},",
                    "  the mover sticks: the next state is exactly [x, y, 0.0, 0.0]",
                    "  (the PREVIOUS position, with zero velocity).",
                ]
    return "\n".join(lines)


def _patch2d_probes(env: PatchField2D):
    # states just outside each patch's west edge moving east — each fires
    # only its own patch in truth.
    probes = {}
    if env.p1 is not None:
        c = env.p1
        probes["patch1"] = [((c[0] - env.R - 0.1, c[1], v, 0.0), 0.0)
                            for v in (1.0, 2.0, 3.0)]
    if env.p2 is not None:
        c = env.p2
        probes["patch2"] = [((c[0] - env.R - 0.1, c[1], v, 0.0), 0.0)
                            for v in (1.0, 2.0, 3.0)]
    return probes


def _patch2d_sample_modes(env: PatchField2D, transitions: list) -> dict:
    result = {}
    if env.p1 is not None:
        result["patch1"] = False
    if env.p2 is not None:
        result["patch2"] = False
    for t in transitions:
        c1, c2 = env.contact_modes(t["state"], t["action"])
        if result.get("patch1") is False and c1:
            result["patch1"] = True
        if result.get("patch2") is False and c2:
            result["patch2"] = True
    return result


@dataclass(frozen=True)
class InstrumentSpec:
    api_text: str
    rules_text: Callable[..., str]
    mode_probes: Callable[[object], dict]
    mode_attr: str
    sample_modes: Callable[[object, list], dict] | None = None


CART_SPEC = InstrumentSpec(
    api_text=CART_API_TEXT, rules_text=_cart_rules_text,
    mode_probes=_cart_mode_probes, mode_attr="x_wall")
PENDULUM_SPEC = InstrumentSpec(
    api_text=PENDULUM_API_TEXT, rules_text=_pendulum_rules_text,
    mode_probes=_pendulum_mode_probes, mode_attr="th_stop")
PATCH2D_SPEC = InstrumentSpec(
    api_text=PATCH2D_API_TEXT, rules_text=_patch2d_rules_text,
    mode_probes=_patch2d_probes, mode_attr="p1",
    sample_modes=_patch2d_sample_modes)


def spec_for(env) -> InstrumentSpec:
    if isinstance(env, PendulumStop):
        return PENDULUM_SPEC
    if isinstance(env, PatchField2D):
        return PATCH2D_SPEC
    return CART_SPEC
