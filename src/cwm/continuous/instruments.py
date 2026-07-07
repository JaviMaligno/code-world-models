"""Instrument-specific pieces of the synthesis contract (paper 2 LLM arms).

The contract machinery in `contract.py` is otherwise env-generic; this module
holds the ONLY parts that differ per instrument — the integrator API text, the
rules text (constants + reward + mode rule), and the mode-region probes — behind
an `InstrumentSpec` selected by `spec_for(env)`. The cart spec reproduces the
pre-refactor prompt byte-for-byte (golden test) so committed results stay valid.
"""
from dataclasses import dataclass
from typing import Callable

from .envs import CartWall, PendulumStop

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


def _cart_rules_text(env: CartWall, include_mode: bool) -> str:
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
    return [((env.x_wall - 0.1, v), env.a_max) for v in (1.0, 2.0, 4.0)]


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


def _pendulum_rules_text(env: PendulumStop, include_mode: bool) -> str:
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
    return [((env.th_stop - 0.1, om), env.a_max) for om in (1.0, 2.0, 4.0)]


@dataclass(frozen=True)
class InstrumentSpec:
    api_text: str
    rules_text: Callable[[object, bool], str]
    mode_probes: Callable[[object], list]
    mode_attr: str


CART_SPEC = InstrumentSpec(
    api_text=CART_API_TEXT, rules_text=_cart_rules_text,
    mode_probes=_cart_mode_probes, mode_attr="x_wall")
PENDULUM_SPEC = InstrumentSpec(
    api_text=PENDULUM_API_TEXT, rules_text=_pendulum_rules_text,
    mode_probes=_pendulum_mode_probes, mode_attr="th_stop")


def spec_for(env) -> InstrumentSpec:
    if isinstance(env, PendulumStop):
        return PENDULUM_SPEC
    return CART_SPEC
