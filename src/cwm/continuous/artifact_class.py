"""Sandboxed triple-classification of synthesized artifacts, plus a
sandboxed dynamic (forbidden-set) mask.

`classify_artifact` puts every candidate artifact into exactly one of three
buckets:

  invalid       -- unparseable code, OR the code has no callable `step`/
                   `reward` at module scope, OR calling `step`/`reward` on a
                   trivial (real) input raises. Checked via `ast.parse`
                   (which only builds a syntax tree -- it never executes the
                   candidate) plus a single sandboxed preflight call. This is
                   deliberately distinct from `gate_failing`: an artifact
                   that doesn't even run should never be scored as "ran but
                   got the physics wrong".
  gate_failing  -- the code runs (passes the preflight) but `contract_accuracy`
                   over the given sample is < 1.0.
  gate_passing  -- `contract_accuracy` == 1.0.

Binding constraint: NEVER in-process `exec`/`eval` non-accepted candidate
code. Every execution of untrusted code -- the preflight call, the gate
accuracy check, and the dynamic mask -- runs inside `contract.run_in_sandbox`
(an isolated `python -I` subprocess). `ast.parse` is safe to call in-process
because it only parses source into a syntax tree; it never runs the code.

`dynamic_metrics_sandboxed` computes the same endpoint-space forbidden mask
as `metrics_geom.forbidden_mask` (see that function's docstring: "For
gate-failing artifacts the design calls for a single sandbox call that
returns the whole mask at once (Task 11's path)"), but does the whole
grid_n x grid_n loop inside ONE sandbox subprocess call instead of invoking
the artifact's `step` in a per-cell in-process loop -- so a gate-failing (or
otherwise untrusted) artifact is never exec'd outside the sandbox. The
subprocess cannot return a raw `.npy` array on stdout (the sandbox is a
text-stdout runner used elsewhere for JSON), so it packs the boolean grid
into bits, base64-encodes them, and prints a single JSON envelope
`{"grid_n": N, "mask_b64": ...}`; the caller unpacks that back into a
boolean `np.ndarray` of shape `(grid_n, grid_n)`.
"""
from __future__ import annotations

import ast
import base64
import json

import numpy as np

from .contract import contract_accuracy, run_in_sandbox
from .metrics_geom import _A_MAX, _DRAG, _DT, _GAIN
from .program_features import guard_features

# The shared integrator/reward fragment representative string, used by
# guard_features to recognize (and exclude) inlined shared-physics code from
# a guard test's own complexity. Matches tests/test_program_features.py.
_INTEGRATOR_REWARD_AST = "vx2 = vx + (gain*math.cos(phi) - drag*vx)*dt"

_PREFLIGHT_TIMEOUT = 10.0
_MASK_TIMEOUT = 30.0


def _preflight_ok(code: str, trivial_state: list, trivial_action: float,
                  timeout: float = _PREFLIGHT_TIMEOUT) -> bool:
    """True iff, INSIDE THE SANDBOX, `step`/`reward` exist and are callable
    and a trivial call to both succeeds without raising."""
    call = (
        "import json\n"
        f"_s = {trivial_state!r}\n"
        f"_a = {trivial_action!r}\n"
        "_ok = True\n"
        "try:\n"
        "    if not callable(globals().get('step')) or not callable(globals().get('reward')):\n"
        "        _ok = False\n"
        "    else:\n"
        "        _ns = step(list(_s), _a)\n"
        "        _r = reward(list(_ns))\n"
        "except Exception:\n"
        "    _ok = False\n"
        "print(json.dumps({'ok': _ok}))\n"
    )
    res = run_in_sandbox(code, call, timeout=timeout)
    if not res.ok:
        return False
    lines = res.stdout.strip().splitlines()
    if not lines:
        return False
    try:
        return bool(json.loads(lines[-1]).get("ok"))
    except json.JSONDecodeError:
        return False


def classify_artifact(code: str, transitions: list[dict], eps: float) -> dict:
    """Classify `code` as exactly one of "invalid" / "gate_failing" /
    "gate_passing", scoring gate accuracy and guard/MDL features along the
    way. All execution of `code` happens inside the sandbox."""
    features = guard_features(code, _INTEGRATOR_REWARD_AST)

    # ast.parse only builds a syntax tree -- it never executes `code` -- so
    # this fast-path check is safe to run in-process.
    try:
        ast.parse(code)
    except SyntaxError:
        return {"class": "invalid", "gate_accuracy": 0.0, "features": features}

    if transitions:
        trivial_state, trivial_action = transitions[0]["state"], transitions[0]["action"]
    else:
        trivial_state, trivial_action = [0.0, 0.0], 0.0

    if not _preflight_ok(code, trivial_state, trivial_action):
        return {"class": "invalid", "gate_accuracy": 0.0, "features": features}

    accuracy, _failures = contract_accuracy(code, transitions, eps)
    cls = "gate_passing" if accuracy == 1.0 else "gate_failing"
    return {"class": cls, "gate_accuracy": accuracy, "features": features}


def _sandbox_mask_driver(box, grid_n: int, vx: float, vy: float, action: float) -> str:
    (xmin, xmax), (ymin, ymax) = box
    return (
        "import json, base64\n"
        "import numpy as np\n"
        f"_DT, _GAIN, _DRAG, _A_MAX = {_DT!r}, {_GAIN!r}, {_DRAG!r}, {_A_MAX!r}\n"
        "import math\n"
        "def _invert_integrator(endpoint_xy, vx, vy, action, dt, gain, drag, a_max):\n"
        "    a = max(-a_max, min(a_max, action))\n"
        "    phi = math.pi * a / a_max\n"
        "    vx2 = vx + (gain * math.cos(phi) - drag * vx) * dt\n"
        "    vy2 = vy + (gain * math.sin(phi) - drag * vy) * dt\n"
        "    return (endpoint_xy[0] - vx2 * dt, endpoint_xy[1] - vy2 * dt, vx, vy)\n"
        f"_grid_n = {grid_n!r}\n"
        f"_xmin, _xmax = {xmin!r}, {xmax!r}\n"
        f"_ymin, _ymax = {ymin!r}, {ymax!r}\n"
        f"_vx, _vy = {vx!r}, {vy!r}\n"
        f"_action = {action!r}\n"
        "_xs = np.linspace(_xmin, _xmax, _grid_n)\n"
        "_ys = np.linspace(_ymin, _ymax, _grid_n)\n"
        "_mask = np.zeros((_grid_n, _grid_n), dtype=bool)\n"
        "for _i, _x in enumerate(_xs):\n"
        "    for _j, _y in enumerate(_ys):\n"
        "        _prev = _invert_integrator((_x, _y), _vx, _vy, _action, _DT, _GAIN, _DRAG, _A_MAX)\n"
        "        try:\n"
        "            _nxt = step(list(_prev), _action)\n"
        "            _fired = bool(_nxt[2] == 0.0 and _nxt[3] == 0.0\n"
        "                          and _nxt[0] == _prev[0] and _nxt[1] == _prev[1])\n"
        "        except Exception:\n"
        "            _fired = False\n"
        "        _mask[_i, _j] = _fired\n"
        "_packed = np.packbits(_mask.reshape(-1))\n"
        "_mask_b64 = base64.b64encode(_packed.tobytes()).decode('ascii')\n"
        "print(json.dumps({'grid_n': _grid_n, 'mask_b64': _mask_b64}))\n"
    )


def dynamic_metrics_sandboxed(code: str, box, grid_n: int, velocity_samples: list,
                              action: float = 0.0,
                              timeout: float = _MASK_TIMEOUT) -> np.ndarray:
    """Endpoint-space forbidden mask (same semantics as
    `metrics_geom.forbidden_mask`), computed for `velocity_samples[0]` in a
    SINGLE sandbox subprocess call so an untrusted/gate-failing artifact's
    `step` is never exec'd in-process. Returns a boolean `(grid_n, grid_n)`
    array decoded from the subprocess's base64-packed-bits JSON envelope."""
    vx, vy = velocity_samples[0]
    driver = _sandbox_mask_driver(box, grid_n, vx, vy, action)
    res = run_in_sandbox(code, driver, timeout=timeout)
    if not res.ok:
        raise RuntimeError(
            f"sandbox failed computing dynamic mask: {res.stderr.strip()[-300:] or 'execution failed'}")
    lines = res.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("sandbox produced no output for dynamic mask")
    envelope = json.loads(lines[-1])
    n = envelope["grid_n"]
    raw = base64.b64decode(envelope["mask_b64"])
    packed = np.frombuffer(raw, dtype=np.uint8)
    bits = np.unpackbits(packed)[: n * n]
    return bits.astype(bool).reshape(n, n)
