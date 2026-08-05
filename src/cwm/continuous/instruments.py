"""Instrument-specific pieces of the synthesis contract (paper 2 LLM arms).

The contract machinery in `contract.py` is otherwise env-generic; this module
holds the ONLY parts that differ per instrument — the integrator API text, the
rules text (constants + reward + mode rule), and the mode-region probes — behind
an `InstrumentSpec` selected by `spec_for(env)`. The cart spec reproduces the
pre-refactor prompt byte-for-byte (golden test) so committed results stay valid.
"""
import math
from dataclasses import dataclass
from typing import Callable

from .envs import CartWall, PatchField2D, PendulumStop, ShapeField2D, invert_integrator
from .shapes import Circle, HalfPlane, Parabola, RegularPolygon, Strip, Wedge

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


def _patch2d_constants_block(env) -> list:
    """Physical constants + reward block shared by every 2D instrument built on
    `integrate_2d` (patch2d, shape2d): identical plant, identical lode reward.
    Extracted so shape2d's incomplete arm can reuse it verbatim and stay
    byte-identical across shapes (it never touches the mode/shape at all)."""
    return [
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


def patch2d_hint_lines(env: PatchField2D, level: str) -> list:
    """A PARTIAL mode clause: the positive control for the 2D negative results.

    Every 2D repair result in this paper is a negative, and a negative is only as strong
    as the guarantee that its target is learnable by this pipeline at all. These graded
    hints withhold progressively more of the rule, so the frontier is located rather than
    merely bounded:

      radius   the form, the centre and the effect are given; only the RADIUS is withheld,
               a single unknown scalar. If the pipeline cannot fit one scalar from the
               contacts a sample contains, the failure is upstream of region induction and
               the whole 2D story needs re-scoping rather than more ablations.
      centre   the form and the effect are given; the CENTRE and the RADIUS are withheld,
               three unknown scalars, no form to induce.

    Neither states the number of patches beyond what the level says, and neither names a
    withheld constant anywhere in the text -- asserted in tests/test_mode_hint.py, since a
    leak would turn the control into a translation exercise.
    """
    if level == "radius":
        head = [f"  There is a sticky circular patch centred at (x, y) = "
                f"({env.p1[0]}, {env.p1[1]}), and a second one",
                f"  centred at (x, y) = ({env.p2[0]}, {env.p2[1]}). Both have the SAME "
                f"radius R,",
                "  whose value is NOT given: infer it from the observed transitions.",
                "  After computing x2 and y2 as above, if (x2 - cx) ** 2 + (y2 - cy) ** 2",
                "  <= R ** 2 for either patch, the mode fires."]
    elif level == "centre":
        head = ["  There are two sticky circular patches. Their centres and their common",
                "  radius are NOT given: infer all of them from the observed transitions.",
                "  After computing x2 and y2 as above, if the landing (x2, y2) lies inside",
                "  either patch, the mode fires."]
    else:
        raise ValueError(f"unknown hint level {level!r}")
    return ["", "Additional dynamics rule (INCOMPLETE -- constants withheld):"] + head \
        + _patch2d_post_state_lines(env, env.p1)


def _patch2d_post_state_lines(env: PatchField2D, c: tuple) -> list:
    """The sentence describing WHERE the mover ends up when the mode fires.

    Kept in one place because it varies with `mode_effect` and is repeated across three
    patch shapes: a variant whose contract still said "the PREVIOUS position" would make
    the full arm a control for a rule the truth does not implement, so the whole
    comparison would be void."""
    if env.mode_effect == "freeze":
        return ["  the mover sticks: the next state is exactly [x, y, 0.0, 0.0]",
                "  (the PREVIOUS position, with zero velocity)."]
    if env.mode_effect == "landing":
        return ["  the mover sticks where it entered: the next state is exactly",
                "  [x2, y2, 0.0, 0.0] (the LANDING position, with zero velocity)."]
    if env.mode_effect == "clamp":
        return [f"  the mover is pushed back to the patch's edge: the next state is",
                f"  exactly [{c[0]} + R * dx / d, {c[1]} + R * dy / d, 0.0, 0.0]",
                f"  where dx = x2 - {c[0]}, dy = y2 - {c[1]} and "
                f"d = math.hypot(dx, dy)",
                "  (the point of the boundary circle nearest the landing, with zero",
                "  velocity; if d == 0 use the direction of travel instead, and if that",
                "  is also zero use dx, dy = 1.0, 0.0)."]
    raise ValueError(f"no contract text for mode_effect {env.mode_effect!r}")


def _patch2d_rules_text(env: PatchField2D, include_mode: bool,
                        omit: tuple = (), hint: str | None = None) -> str:
    lines = _patch2d_constants_block(env)
    if hint:
        if include_mode:
            raise ValueError("a hint is a PARTIAL clause: it replaces the full one, so "
                             "include_mode must be False")
        return "\n".join(lines + patch2d_hint_lines(env, hint))
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
                ] + _patch2d_post_state_lines(env, c)
            elif env.patch_shape == "slab":
                # The rarity-matched predicate-ARITY ablation (2026-07-27):
                # membership depends on the landing x alone. Written in the same
                # shape as the square clause (one abs comparison instead of a
                # max of two) so the only textual difference between the arms is
                # how many landing coordinates the trigger names.
                lines += [
                    "",
                    "Additional dynamics rule:",
                    f"  There is a sticky vertical slab centered at x = {c[0]}",
                    f"  with half-width W = {env.slab_half_width}. After "
                    f"computing x2 and y2 as above,",
                    f"  if abs(x2 - {c[0]}) <= {env.slab_half_width}, the mover "
                    f"sticks (whatever y2 is):",
                ]
                # The committed slab campaign was run with this exact wording, so the
                # freeze branch must reproduce it byte for byte; only a NEW mode_effect
                # takes the shared post-state sentence. (Checked by
                # tests/test_mode_effect.py against `git show HEAD`.)
                if env.mode_effect == "freeze":
                    lines += ["  the next state is exactly [x, y, 0.0, 0.0]",
                              "  (the PREVIOUS position, with zero velocity)."]
                else:
                    lines += _patch2d_post_state_lines(env, c)
            else:
                lines += [
                    "",
                    "Additional dynamics rule:",
                    f"  There is a sticky patch centered at (x, y) = ({c[0]}, {c[1]})",
                    f"  with radius R = {env.R}. After computing x2 and y2 as above,",
                    f"  if (x2 - {c[0]}) ** 2 + (y2 - {c[1]}) ** 2 <= {env.R ** 2},",
                ] + _patch2d_post_state_lines(env, c)
    return "\n".join(lines)


def _slab_probes_for(env: PatchField2D, c: tuple) -> list:
    """Probes for one patch_shape="slab" patch: states whose next position lands
    exactly on the slab's center line x = c[0], at three DIFFERENT y (including
    y far from c[1]), reached by inverting the shared integrator. They fire the
    slab in truth for any positive half-width (the landing x is the center), and
    the spread in y is deliberate: a model that copied the disc/square template
    and consulted y2 is wrong on them."""
    ys = (c[1], c[1] + 2.0, c[1] - 3.0)
    return [(invert_integrator((c[0], y), 0.0, 0.0, 0.0, env.dt, env.gain,
                               env.drag, env.a_max), 0.0)
            for y in ys]


def _patch2d_probes(env: PatchField2D):
    # states just outside each patch's west edge moving east — each fires
    # only its own patch in truth.
    probes = {}
    if env.p1 is not None:
        c = env.p1
        probes["patch1"] = (
            _slab_probes_for(env, c) if env.patch_shape == "slab"
            else [((c[0] - env.R - 0.1, c[1], v, 0.0), 0.0)
                  for v in (1.0, 2.0, 3.0)])
    if env.p2 is not None:
        c = env.p2
        probes["patch2"] = (
            _slab_probes_for(env, c) if env.patch_shape == "slab"
            else [((c[0] - env.R - 0.1, c[1], v, 0.0), 0.0)
                  for v in (1.0, 2.0, 3.0)])
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


# --- shape2d (2D navigation vs. an arbitrary Shape) --------------------------
# Same plant/API as patch2d (ShapeField2D reuses integrate_2d bit-for-bit), so
# the integrator/API text is identical; only the mode clause differs (a single
# geometric predicate instead of two hardcoded discs).
SHAPE2D_API_TEXT = PATCH2D_API_TEXT


def describe_shape(shape) -> str:
    """The EXACT mathematical containment predicate for `shape`, per family —
    NOT repr(shape) — so the full-arm contract states precisely the region a
    correct synthesis must reproduce."""
    if isinstance(shape, Circle):
        return f"(x - {shape.cx})**2 + (y - {shape.cy})**2 <= {shape.R}**2"
    if isinstance(shape, Parabola):
        return f"x >= {shape.c} + y**2/(2*{shape.R})"
    if isinstance(shape, HalfPlane):
        return f"x >= {shape.c}"
    if isinstance(shape, Strip):
        return f"x >= {shape.c} and x <= {shape.c + shape.w}"
    if isinstance(shape, (RegularPolygon, Wedge)):
        # containment is implicit_value <= 0, i.e. the AND of every face's
        # half-plane nx*x + ny*y <= off (see shapes.py's `_faces`).
        return " and ".join(f"{nx}*x + {ny}*y <= {off}"
                            for nx, ny, off in shape._faces())
    raise ValueError(f"describe_shape: unsupported shape type {type(shape)!r}")


def _shape2d_rules_text(env: ShapeField2D, include_mode: bool,
                        omit: tuple = ()) -> str:
    if omit:
        raise ValueError("omit is only supported by the patch2d instrument")
    # Reuses the patch2d constants+reward block verbatim (same plant, same
    # lodes) and NEVER touches `env.shape` unless include_mode — this is what
    # keeps the incomplete arm byte-identical across every shape family.
    lines = _patch2d_constants_block(env)
    if include_mode:
        if env.shape is None:
            raise ValueError("env has no shape; cannot write the mode clause")
        lines += [
            "",
            "Additional dynamics rule:",
            "  There is a hard mode region defined by the predicate:",
            f"    {describe_shape(env.shape)}",
            "  After computing x2 and y2 as above, if that predicate holds for",
            "  (x2, y2), the mover sticks: the next state is exactly",
            "  [x, y, 0.0, 0.0] (the PREVIOUS position, with zero velocity).",
        ]
    return "\n".join(lines)


def _shape2d_probes(env: ShapeField2D):
    # Interior targets (a boundary point pushed inward along the inward
    # normal — at a vertex, the negated normalized sum of the cone normals),
    # reached exactly by inverting the integrator, so every probe fires the
    # mode in truth regardless of the shape family.
    box = ((-8.0, 14.0), (-6.0, 6.0))
    shp = env.shape
    probes = []
    for (bx, by) in shp.boundary_points(box, 12):
        n = shp.normal_or_cone((bx, by))
        if isinstance(n, list):  # vertex: inward = -(normalized sum of cone normals)
            sx = sum(c[0] for c in n); sy = sum(c[1] for c in n)
            m = math.hypot(sx, sy) or 1.0
            inward = (-sx / m, -sy / m)
        else:
            inward = (-n[0], -n[1])
        target = (bx + 0.05 * inward[0], by + 0.05 * inward[1])  # strictly interior
        if not shp.contains(target):
            target = (bx + 0.2 * inward[0], by + 0.2 * inward[1])
        state = invert_integrator(target, 0.0, 0.0, 0.0, env.dt, env.gain,
                                  env.drag, env.a_max)
        probes.append((state, 0.0))
    return {"mode": probes}


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
SHAPE2D_SPEC = InstrumentSpec(
    api_text=SHAPE2D_API_TEXT, rules_text=_shape2d_rules_text,
    mode_probes=_shape2d_probes, mode_attr="shape")


def spec_for(env) -> InstrumentSpec:
    if isinstance(env, PendulumStop):
        return PENDULUM_SPEC
    if isinstance(env, ShapeField2D):
        return SHAPE2D_SPEC
    if isinstance(env, PatchField2D):
        return PATCH2D_SPEC
    return CART_SPEC
