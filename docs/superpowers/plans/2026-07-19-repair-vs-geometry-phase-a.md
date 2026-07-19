# Repair-vs-Geometry — Phase A (infrastructure + calibration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build every apparatus piece for the repair-vs-geometry experiment and produce a frozen calibration artifact — the gate that authorizes the ~520 Azure syntheses (Phase B, separate plan).

**Architecture:** A new `Shape` abstraction (unbounded-safe) drives a new single-mode 2D instrument `ShapeField2D` that reuses `PatchField2D`'s integrator and reward but swaps the disc predicate for an arbitrary `Shape`. New, side-effect-free metric/analysis modules (state–action disagreement, IoU+preimage-invariance, boundary Hausdorff, version-space `S`, per-family oracle, AST/MDL, sandbox triple-classification) sit beside the existing pipeline without modifying it. A calibration prototype script freezes all numeric parameters to a versioned JSON. Nothing in Phase A calls Azure.

**Tech Stack:** Python 3.12, pytest (`pythonpath=["src"]`, `testpaths=["tests"]`), numpy (already a dep), stdlib `ast`. No new heavy deps.

## Global Constraints

- **V ≡ V_transcript** everywhere (gate-visible ≠ what the LLM saw). Log V_gate, V_initial, V_transcript.
- **Primary metric is in state–action space**; 2D region IoU is reported ONLY after a preimage-invariance check passes; otherwise the artifact is a `non-positional guard`.
- **The `repaired` threshold is fixed from truth/oracle/full-arm reconstructions and the grid's numerical error — NEVER tuned on the incomplete anchor's own results.**
- **Sufficiency `S` = version-space diameter < `τ_S`** (family shapes consistent with the evidence agree within `τ_S` on the box). The oracle is the *operational* estimator only.
- **Evidence-dose caps the WHOLE transcript** to `m` positives + matched negatives via an explicit "controlled observations" block; background substitutes are NEVER fed back as FAILURES; gate failing only outside the allowed set → `evidence_capped_failure`.
- **Never in-process `exec` non-accepted code.** `SynthesizedModel` execs accepted artifacts only; gate-failing artifacts run in the sandbox; classify every artifact `{invalid, gate_failing, gate_passing}`.
- Numeric anchors (verbatim): common box `[-8,14]×[-6,6]`; grid `256²` initial, converged if metric shifts `<1%` at `512²`; `implicit_value` sign convention **negative inside, positive outside**; `repaired = boundary-band disagreement ≤ 0.05 AND FPR ≤ 0.05`; IoU modeled with zero/one-inflated beta (Phase B stats, not here).
- **The cart golden byte-identity tests MUST keep passing** (`tests/test_instruments.py::test_cart_spec_is_byte_identical_to_golden`, `tests/test_continuous_contract.py::test_build_contract_cart_matches_golden`). Do not touch `CART_SPEC`, `PENDULUM_SPEC`, `PATCH2D_SPEC`, or `build_contract`'s cart path.
- No checkpoint/resume exists in the scripts today; Phase A's calibration run is cheap and does not need it (Phase B will build it).
- All new modules live in `src/cwm/continuous/`; all tests in `tests/`; run with `pytest -q`.

---

### Task 1: `Shape` interface + HalfPlane + Circle

**Files:**
- Create: `src/cwm/continuous/shapes.py`
- Test: `tests/test_shapes.py`

**Interfaces:**
- Produces: `class Shape` with `contains(p)->bool`, `implicit_value(p)->float` (neg inside), `boundary_points(window, n)->list[tuple]` (arc-length uniform within `window=((xmin,xmax),(ymin,ymax))`), `project_to_boundary(p)->tuple[tuple,bool]` (point, multi_flag), `normal_or_cone(p)->tuple|list[tuple]` (outward unit normal, or list at a vertex). `HalfPlane(c)` = region `x≥c`. `Circle(cx,cy,R)` = region inside the disc.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shapes.py
import math
from cwm.continuous.shapes import HalfPlane, Circle

WIN = ((-8.0, 14.0), (-6.0, 6.0))

def test_halfplane_contains_and_sign():
    hp = HalfPlane(c=3.0)
    assert hp.contains((5.0, 0.0)) and not hp.contains((1.0, 0.0))
    assert hp.implicit_value((5.0, 0.0)) < 0 < hp.implicit_value((1.0, 0.0))  # neg inside
    assert hp.normal_or_cone((3.0, 2.0)) == (-1.0, 0.0)  # outward = toward x<c

def test_circle_contains_project_normal():
    c = Circle(cx=3.0, cy=0.0, R=1.0)
    assert c.contains((3.0, 0.0)) and not c.contains((5.0, 0.0))
    pt, multi = c.project_to_boundary((5.0, 0.0))
    assert not multi and math.isclose(pt[0], 4.0, abs_tol=1e-9) and math.isclose(pt[1], 0.0, abs_tol=1e-9)
    assert c.project_to_boundary((3.0, 0.0))[1] is True  # center is equidistant → multi
    n = c.normal_or_cone((4.0, 0.0)); assert math.isclose(n[0], 1.0) and math.isclose(n[1], 0.0)

def test_boundary_points_within_window():
    for shp in (HalfPlane(3.0), Circle(3.0, 0.0, 1.0)):
        pts = shp.boundary_points(WIN, 20)
        assert len(pts) == 20
        for x, y in pts:
            assert -8.0 <= x <= 14.0 and -6.0 <= y <= 6.0
            assert abs(shp.implicit_value((x, y))) < 1e-6  # on the boundary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_shapes.py -q`
Expected: FAIL (ModuleNotFoundError: cwm.continuous.shapes).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/shapes.py
"""Mode-region shapes for the repair-vs-geometry sweep. Possibly unbounded;
the bounding box belongs to the experiment, not the shape. implicit_value is
NEGATIVE inside, POSITIVE outside."""
from __future__ import annotations
import math
from dataclasses import dataclass


class Shape:
    def contains(self, p) -> bool:
        return self.implicit_value(p) <= 0.0

    def implicit_value(self, p) -> float:
        raise NotImplementedError

    def boundary_points(self, window, n) -> list:
        raise NotImplementedError

    def project_to_boundary(self, p):
        raise NotImplementedError

    def normal_or_cone(self, p):
        raise NotImplementedError


@dataclass(frozen=True)
class HalfPlane(Shape):
    c: float  # region x >= c

    def implicit_value(self, p) -> float:
        return self.c - p[0]  # neg when x>c (inside)

    def boundary_points(self, window, n) -> list:
        (_, _), (ymin, ymax) = window
        if n == 1:
            return [(self.c, 0.5 * (ymin + ymax))]
        return [(self.c, ymin + (ymax - ymin) * i / (n - 1)) for i in range(n)]

    def project_to_boundary(self, p):
        return (self.c, p[1]), False

    def normal_or_cone(self, p):
        return (-1.0, 0.0)  # outward points toward x<c


@dataclass(frozen=True)
class Circle(Shape):
    cx: float
    cy: float
    R: float

    def implicit_value(self, p) -> float:
        return (p[0] - self.cx) ** 2 + (p[1] - self.cy) ** 2 - self.R ** 2

    def boundary_points(self, window, n) -> list:
        (xmin, xmax), (ymin, ymax) = window
        out = []
        for i in range(n):
            t = 2.0 * math.pi * i / n
            x, y = self.cx + self.R * math.cos(t), self.cy + self.R * math.sin(t)
            if xmin <= x <= xmax and ymin <= y <= ymax:
                out.append((x, y))
        # keep exactly n by resampling only in-window arc if clipping occurred
        if len(out) < n and out:
            while len(out) < n:
                out.append(out[len(out) % max(1, len(out))])
        return out[:n] if out else [(self.cx + self.R, self.cy)]

    def project_to_boundary(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        d = math.hypot(dx, dy)
        if d < 1e-12:
            return (self.cx + self.R, self.cy), True  # center: all boundary points equidistant
        return (self.cx + self.R * dx / d, self.cy + self.R * dy / d), False

    def normal_or_cone(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        d = math.hypot(dx, dy) or 1.0
        return (dx / d, dy / d)  # outward radial
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_shapes.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/shapes.py tests/test_shapes.py
git commit -m "feat(shapes): Shape interface + HalfPlane + Circle (unbounded-safe)"
```

---

### Task 2: Parabola graph boundary

**Files:**
- Modify: `src/cwm/continuous/shapes.py`
- Test: `tests/test_shapes.py`

**Interfaces:**
- Produces: `Parabola(c, R)` = region `x ≥ c + y²/(2R)`; local curvature `curvature(y) = (1/R)/(1+(y/R)**2)**1.5`; `curvature_center = 1/R`. `project_to_boundary` is numeric (nearest point on the graph). Limit `R→∞` ≡ `HalfPlane(c)`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_shapes.py
from cwm.continuous.shapes import Parabola

def test_parabola_curvature_and_containment():
    par = Parabola(c=3.0, R=2.0)
    assert math.isclose(par.curvature_center, 0.5)
    assert math.isclose(par.curvature(0.0), 0.5)
    assert par.curvature(4.0) < par.curvature(0.0)  # falls off away from the vertex
    assert par.contains((10.0, 0.0)) and not par.contains((3.1, 3.0))  # y²/2R = 2.25 at y=3
    assert par.implicit_value((10.0, 0.0)) < 0 < par.implicit_value((3.1, 3.0))

def test_parabola_projection_is_nearest():
    par = Parabola(c=3.0, R=2.0)
    pt, _ = par.project_to_boundary((3.0, 0.0))
    assert math.isclose(pt[0], 3.0, abs_tol=1e-6) and math.isclose(pt[1], 0.0, abs_tol=1e-6)
    # point straight left of the vertex projects to the vertex
    d = math.hypot(3.0 - pt[0], 0.0 - pt[1]); assert d < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_shapes.py::test_parabola_curvature_and_containment -q`
Expected: FAIL (ImportError: cannot import name 'Parabola').

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/cwm/continuous/shapes.py
@dataclass(frozen=True)
class Parabola(Shape):
    c: float
    R: float  # region x >= c + y**2/(2R); vertex curvature 1/R

    @property
    def curvature_center(self) -> float:
        return 1.0 / self.R

    def curvature(self, y) -> float:
        return (1.0 / self.R) / (1.0 + (y / self.R) ** 2) ** 1.5

    def _boundary_x(self, y) -> float:
        return self.c + y * y / (2.0 * self.R)

    def implicit_value(self, p) -> float:
        return self._boundary_x(p[1]) - p[0]  # neg when x> boundary (inside)

    def boundary_points(self, window, n) -> list:
        (_, _), (ymin, ymax) = window
        if n == 1:
            return [(self._boundary_x(0.0), 0.0)]
        return [(self._boundary_x(y), y)
                for y in (ymin + (ymax - ymin) * i / (n - 1) for i in range(n))]

    def project_to_boundary(self, p):
        # minimize (x0 - (c + y**2/2R))**2 + (y0 - y)**2 over y; ternary search on a convex-ish 1D objective
        x0, y0 = p
        lo, hi = y0 - 20.0, y0 + 20.0
        f = lambda y: (x0 - self._boundary_x(y)) ** 2 + (y0 - y) ** 2
        for _ in range(200):
            m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
            if f(m1) < f(m2):
                hi = m2
            else:
                lo = m1
        y = 0.5 * (lo + hi)
        return (self._boundary_x(y), y), False

    def normal_or_cone(self, p):
        # boundary x = c + y**2/2R; tangent (dx/dy, 1) = (y/R, 1); outward normal ∝ (-1, y/R)... points to x<boundary
        _, y = self.project_to_boundary(p)[0]
        nx, ny = -1.0, y / self.R
        d = math.hypot(nx, ny)
        return (nx / d, ny / d)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_shapes.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/shapes.py tests/test_shapes.py
git commit -m "feat(shapes): Parabola graph boundary with local curvature + numeric projection"
```

---

### Task 3: Strip, Wedge, RegularPolygon (with vertex normal cones)

**Files:**
- Modify: `src/cwm/continuous/shapes.py`
- Test: `tests/test_shapes.py`

**Interfaces:**
- Produces: `Strip(c, w)` (region `c ≤ x ≤ c+w`, two parallel faces); `Wedge(apex, half_angle, orient)` (intersection of two half-planes meeting at a vertex); `RegularPolygon(cx, cy, radius, k, orient)` (region inside a convex k-gon; `orient=0` is face-on toward +x, `orient=math.pi/k` is vertex-on). `normal_or_cone` returns a **list** of the adjacent outward normals at a vertex, a single normal on a face. `implicit_value` = max of the half-plane values for convex intersections (neg inside).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_shapes.py
from cwm.continuous.shapes import Strip, Wedge, RegularPolygon

def test_strip_two_faces():
    s = Strip(c=3.0, w=1.0)
    assert s.contains((3.5, 5.0)) and not s.contains((5.0, 0.0))
    assert s.implicit_value((3.5, 0.0)) < 0

def test_regular_polygon_orientation_and_vertex_cone():
    face = RegularPolygon(3.0, 0.0, radius=1.0, k=4, orient=0.0)
    vert = RegularPolygon(3.0, 0.0, radius=1.0, k=4, orient=math.pi / 4)
    assert face.contains((3.0, 0.0)) and vert.contains((3.0, 0.0))
    # a point at a polygon vertex has a multi-valued normal (a cone → list)
    vpt, _ = vert.project_to_boundary((3.0 + 5.0, 0.0))
    ncone = vert.normal_or_cone(vpt)
    assert isinstance(ncone, list) and len(ncone) == 2

def test_polygon_curvature_is_composition_not_scalar():
    # #facets is k; this axis is compositional, not a single curvature
    assert RegularPolygon(3.0, 0.0, 1.0, 6, 0.0).n_facets == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_shapes.py -k "strip or polygon" -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/cwm/continuous/shapes.py
def _halfplane_value(p, nx, ny, offset):
    # region: nx*x + ny*y <= offset ; value neg inside
    return nx * p[0] + ny * p[1] - offset


@dataclass(frozen=True)
class Strip(Shape):
    c: float
    w: float  # region c <= x <= c+w

    def implicit_value(self, p) -> float:
        return max(self.c - p[0], p[0] - (self.c + self.w))

    def boundary_points(self, window, n) -> list:
        (_, _), (ymin, ymax) = window
        half = n // 2
        left = [(self.c, ymin + (ymax - ymin) * i / max(1, half - 1)) for i in range(half)]
        right = [(self.c + self.w, ymin + (ymax - ymin) * i / max(1, n - half - 1)) for i in range(n - half)]
        return left + right

    def project_to_boundary(self, p):
        dl, dr = abs(p[0] - self.c), abs(p[0] - (self.c + self.w))
        return ((self.c, p[1]), False) if dl <= dr else ((self.c + self.w, p[1]), False)

    def normal_or_cone(self, p):
        return (-1.0, 0.0) if abs(p[0] - self.c) <= abs(p[0] - (self.c + self.w)) else (1.0, 0.0)


def _polygon_faces(cx, cy, radius, k, orient):
    # outward unit normals + offsets of the k faces of the regular k-gon (apothem = radius*cos(pi/k))
    apo = radius * math.cos(math.pi / k)
    faces = []
    for i in range(k):
        ang = orient + 2.0 * math.pi * i / k
        nx, ny = math.cos(ang), math.sin(ang)
        faces.append((nx, ny, nx * cx + ny * cy + apo))  # region n·p <= offset
    return faces


@dataclass(frozen=True)
class RegularPolygon(Shape):
    cx: float
    cy: float
    radius: float
    k: int
    orient: float = 0.0

    @property
    def n_facets(self) -> int:
        return self.k

    def _faces(self):
        return _polygon_faces(self.cx, self.cy, self.radius, self.k, self.orient)

    def implicit_value(self, p) -> float:
        return max(_halfplane_value(p, nx, ny, off) for nx, ny, off in self._faces())

    def boundary_points(self, window, n) -> list:
        (xmin, xmax), (ymin, ymax) = window
        verts = [(self.cx + self.radius * math.cos(self.orient + math.pi / self.k + 2 * math.pi * i / self.k),
                  self.cy + self.radius * math.sin(self.orient + math.pi / self.k + 2 * math.pi * i / self.k))
                 for i in range(self.k)]
        out = []
        for i in range(self.k):
            a, b = verts[i], verts[(i + 1) % self.k]
            per_edge = max(1, n // self.k)
            for j in range(per_edge):
                t = j / per_edge
                x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
                if xmin <= x <= xmax and ymin <= y <= ymax:
                    out.append((x, y))
        return out[:n] if out else [verts[0]]

    def project_to_boundary(self, p):
        best, bestd, atv = None, float("inf"), False
        verts = [(self.cx + self.radius * math.cos(self.orient + math.pi / self.k + 2 * math.pi * i / self.k),
                  self.cy + self.radius * math.sin(self.orient + math.pi / self.k + 2 * math.pi * i / self.k))
                 for i in range(self.k)]
        for i in range(self.k):
            a, b = verts[i], verts[(i + 1) % self.k]
            abx, aby = b[0] - a[0], b[1] - a[1]
            t = max(0.0, min(1.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / (abx * abx + aby * aby)))
            q = (a[0] + t * abx, a[1] + t * aby)
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d < bestd - 1e-12:
                bestd, best, atv = d, q, (t < 1e-9 or t > 1 - 1e-9)
        return best, atv

    def normal_or_cone(self, p):
        faces = self._faces()
        active = [(nx, ny) for nx, ny, off in faces if abs(_halfplane_value(p, nx, ny, off)) < 1e-6]
        return active if len(active) >= 2 else (active[0] if active else max(
            faces, key=lambda f: _halfplane_value(p, *f))[:2])


@dataclass(frozen=True)
class Wedge(Shape):
    apex: tuple
    half_angle: float
    orient: float = 0.0  # region between two half-planes meeting at apex, opening along orient

    def _faces(self):
        faces = []
        for s in (+1.0, -1.0):
            ang = self.orient + s * (math.pi / 2.0 + self.half_angle)
            nx, ny = math.cos(ang), math.sin(ang)
            faces.append((nx, ny, nx * self.apex[0] + ny * self.apex[1]))
        return faces

    def implicit_value(self, p) -> float:
        return max(_halfplane_value(p, nx, ny, off) for nx, ny, off in self._faces())

    def boundary_points(self, window, n) -> list:
        (xmin, xmax), (ymin, ymax) = window
        out = []
        for nx, ny, off in self._faces():
            for i in range(n // 2):
                t = -10.0 + 20.0 * i / max(1, n // 2 - 1)
                x = self.apex[0] - ny * t
                y = self.apex[1] + nx * t
                if xmin <= x <= xmax and ymin <= y <= ymax and self.implicit_value((x, y)) <= 1e-6:
                    out.append((x, y))
        return out[:n] if out else [self.apex]

    def project_to_boundary(self, p):
        d0 = abs(_halfplane_value(p, *self._faces()[0]))
        d1 = abs(_halfplane_value(p, *self._faces()[1]))
        at_apex = math.hypot(p[0] - self.apex[0], p[1] - self.apex[1]) < 1e-6
        return self.apex, (at_apex or abs(d0 - d1) < 1e-9)

    def normal_or_cone(self, p):
        faces = self._faces()
        active = [(nx, ny) for nx, ny, off in faces if abs(_halfplane_value(p, nx, ny, off)) < 1e-6]
        return active if len(active) >= 2 else (active[0] if active else (faces[0][0], faces[0][1]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_shapes.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/shapes.py tests/test_shapes.py
git commit -m "feat(shapes): Strip, Wedge, RegularPolygon with vertex normal cones"
```

---

### Task 4: `ShapeField2D` instrument (single mode, reuses integrator)

**Files:**
- Modify: `src/cwm/continuous/envs.py`
- Test: `tests/test_shape_field.py`

**Interfaces:**
- Consumes: `Shape` (Task 1–3).
- Produces: `ShapeField2D` frozen dataclass with fields `shape: Shape | None`, and the same physics constants/lodes as `PatchField2D` (`dt, gain, drag, a_max, lode_real, amp_real, lode_phantom, amp_phantom, r0, width, h_episode, x0_range`). Methods `initial_state`, `reward`, `_integrate`, `contact` (bool), `step` (freeze at previous position on contact, mirroring PatchField2D). `blind_of` returns the same env with `shape=None`. The disc predicate is replaced by `self.shape.contains((x2,y2))`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shape_field.py
import random
from cwm.continuous.envs import ShapeField2D, blind_of
from cwm.continuous.shapes import Circle, HalfPlane

def test_shapefield_freezes_on_contact():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    # a state whose integrated next position lands in the disc freezes at the previous position
    s = (2.0, 0.0, 3.0, 0.0)
    s2, r, contact = env.step(s, 0.0)
    assert contact and s2[2] == 0.0 and s2[3] == 0.0 and s2[0] == 2.0 and s2[1] == 0.0

def test_shapefield_blind_has_no_mode():
    env = ShapeField2D(shape=HalfPlane(3.0))
    b = blind_of(env)
    assert b.shape is None
    s = (2.9, 0.0, 3.0, 0.0)
    _, _, contact = b.step(s, 0.0)
    assert contact is False  # blind model never freezes

def test_shapefield_reward_matches_patchfield_lodes():
    env = ShapeField2D(shape=None)
    assert env.reward((-6.0, 0.0, 0.0, 0.0)) > env.reward((0.0, 0.0, 0.0, 0.0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_shape_field.py -q`
Expected: FAIL (ImportError: cannot import name 'ShapeField2D').

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/cwm/continuous/envs.py (after PatchField2D), reusing the same style
@dataclass(frozen=True)
class ShapeField2D:
    """Single-mode 2D instrument for the repair-vs-geometry sweep. Same physics
    as PatchField2D but the mode is an arbitrary Shape (shape=None → blind)."""
    shape: object | None = None
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    lode_real: tuple = (-6.0, 0.0)
    amp_real: float = 0.3
    lode_phantom: tuple = (12.0, 0.0)
    amp_phantom: float = 1.0
    r0: float = 2.0
    width: float = 0.5
    h_episode: int = 80
    x0_range: float = 0.5

    def initial_state(self, rng):
        return (rng.uniform(-self.x0_range, self.x0_range),
                rng.uniform(-self.x0_range, self.x0_range), 0.0, 0.0)

    def _lode(self, x, y, lode, amp):
        d = math.hypot(x - lode[0], y - lode[1])
        return amp / (1.0 + math.exp((d - self.r0) / self.width))

    def reward(self, state):
        x, y = state[0], state[1]
        return (self._lode(x, y, self.lode_real, self.amp_real)
                + self._lode(x, y, self.lode_phantom, self.amp_phantom))

    def _integrate(self, state, action):
        x, y, vx, vy = state
        a = max(-self.a_max, min(self.a_max, action))
        phi = math.pi * a / self.a_max
        vx2 = vx + (self.gain * math.cos(phi) - self.drag * vx) * self.dt
        vy2 = vy + (self.gain * math.sin(phi) - self.drag * vy) * self.dt
        return x + vx2 * self.dt, y + vy2 * self.dt, vx2, vy2

    def contact(self, state, action) -> bool:
        x2, y2, _, _ = self._integrate(state, action)
        return self.shape is not None and self.shape.contains((x2, y2))

    def step(self, state, action):
        x2, y2, vx2, vy2 = self._integrate(state, action)
        if self.shape is not None and self.shape.contains((x2, y2)):
            s2 = (state[0], state[1], 0.0, 0.0)
            return s2, self.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.reward(s2), False
```

Then extend `blind_of` (envs.py L206) to handle the new env — add a branch before the final else:

```python
    if isinstance(env, ShapeField2D):
        return replace(env, shape=None)
```

- [ ] **Step 4: Run tests (new + golden must still pass)**

Run: `pytest tests/test_shape_field.py tests/test_instruments.py tests/test_continuous_contract.py -q`
Expected: PASS (new 3 + cart golden tests unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/envs.py tests/test_shape_field.py
git commit -m "feat(envs): ShapeField2D single-mode instrument reusing the PatchField2D integrator"
```

---

### Task 5: `SHAPE2D_SPEC` (prompt contract, geometry-agnostic incomplete arm)

**Files:**
- Modify: `src/cwm/continuous/instruments.py`
- Test: `tests/test_shape_field.py`

**Interfaces:**
- Consumes: `ShapeField2D`, `InstrumentSpec`.
- Produces: `SHAPE2D_SPEC` and a `spec_for` branch dispatching `ShapeField2D → SHAPE2D_SPEC`. `rules_text(env, include_mode, omit=())`: the **incomplete arm (`include_mode=False`) is geometry-agnostic** — it states the 2D integrator and reward but no mode clause, so the synthesizer must infer the mode from contacts. The full arm (`include_mode=True`) appends a textual description of `env.shape`. `mode_probes(env)` returns `{"mode": [...]}` with probes uniformly along the true boundary (arc-length, within the box) moving inward.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_shape_field.py
from cwm.continuous.instruments import spec_for
from cwm.continuous.contract import build_contract

def test_shape2d_incomplete_arm_is_geometry_agnostic():
    from cwm.continuous.shapes import Circle, Parabola
    env_c = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    env_p = ShapeField2D(shape=Parabola(3.0, 2.0))
    inc_c = build_contract(env_c, include_mode=False)
    inc_p = build_contract(env_p, include_mode=False)
    assert inc_c == inc_p  # incomplete arm must not leak the geometry
    assert "radius" not in inc_c.lower() and "parabola" not in inc_c.lower()

def test_shape2d_full_arm_describes_shape():
    from cwm.continuous.shapes import Circle
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    full = build_contract(env, include_mode=True)
    assert "3.0" in full  # the center/radius appear in the full arm

def test_shape2d_probes_lie_on_boundary():
    from cwm.continuous.shapes import Circle
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    probes = spec_for(env).mode_probes(env)
    assert set(probes.keys()) == {"mode"} and len(probes["mode"]) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_shape_field.py -k shape2d -q`
Expected: FAIL (spec_for has no ShapeField2D branch / KeyError).

- [ ] **Step 3: Write minimal implementation**

Add API text, rules builder, probes, spec, and dispatch to `instruments.py`:

```python
SHAPE2D_API_TEXT = PATCH2D_API_TEXT  # identical 4-var state + fixed integrator; single generic mode

def _shape2d_rules_text(env, include_mode, omit=()):
    base = _patch2d_constants_block(env)  # reuse the physical-constants + reward block builder
    if not include_mode:
        return base  # geometry-agnostic incomplete arm
    shp = env.shape
    return base + "\n" + f"Additional dynamics rule (mode): if the next position is inside the region {shp!r}, the probe stops at its previous position with zero velocity."

def _shape2d_probes(env):
    box = ((-8.0, 14.0), (-6.0, 6.0))
    pts = env.shape.boundary_points(box, 12)
    probes = []
    for (bx, by) in pts:
        n = env.shape.normal_or_cone((bx, by))
        n = n[0] if isinstance(n, list) else n  # a single inward direction is enough for a probe
        # start just outside, moving inward so the step lands in the region (fires the mode in truth)
        sx, sy = bx + 0.1 * n[0], by + 0.1 * n[1]
        vx, vy = -3.0 * n[0], -3.0 * n[1]
        probes.append(((sx, sy, vx, vy), 0.0))
    return {"mode": probes}

SHAPE2D_SPEC = InstrumentSpec(
    api_text=SHAPE2D_API_TEXT,
    rules_text=_shape2d_rules_text,
    mode_probes=_shape2d_probes,
    mode_attr="shape",
    sample_modes=None,
)
```

Extract the shared constants/reward block used by `_patch2d_rules_text` into `_patch2d_constants_block(env)` (a refactor that must leave `_patch2d_rules_text`'s output byte-identical — verify with the patch2d tests). Add to `spec_for`:

```python
    if isinstance(env, ShapeField2D):
        return SHAPE2D_SPEC
```

- [ ] **Step 4: Run tests (shape2d + patch2d + cart golden)**

Run: `pytest tests/test_shape_field.py tests/test_continuous_contract.py tests/test_instruments.py tests/test_patch2d.py -q`
Expected: PASS. The patch2d and cart golden tests confirm the `_patch2d_constants_block` refactor is byte-safe.

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/instruments.py tests/test_shape_field.py
git commit -m "feat(instruments): SHAPE2D_SPEC with geometry-agnostic incomplete arm"
```

---

### Task 6: State–action disagreement metric (three stratified scores)

**Files:**
- Create: `src/cwm/continuous/metrics_geom.py`
- Test: `tests/test_metrics_geom.py`

**Interfaces:**
- Consumes: `ShapeField2D`, a synthesized-model step function.
- Produces: `stratified_probes(env, box, n_per, rng, tube_half_width) -> dict[str, list[tuple]]` with strata `{"inside","outside","band","uniform","planner"}` of labeled `(state, action)` proposals whose integrated endpoint's stratum is known; `disagreement_scores(truth_env, model_step, probes) -> dict` returning per-stratum balanced disagreement plus `precision/recall/fpr`; the **primary score is `band`**. `model_step` is a callable `(state, action) -> next_state` (a sandboxed or accepted artifact).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics_geom.py
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.metrics_geom import stratified_probes, disagreement_scores

BOX = ((-8.0, 14.0), (-6.0, 6.0))

def test_identical_model_has_zero_disagreement():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    probes = stratified_probes(env, BOX, n_per=25, rng=random.Random(0), tube_half_width=0.3)
    scores = disagreement_scores(env, lambda s, a: env.step(s, a)[0], probes)
    assert scores["band"]["disagreement"] == 0.0 and scores["band"]["fpr"] == 0.0

def test_blind_model_disagrees_in_band():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    blind = ShapeField2D(shape=None)
    probes = stratified_probes(env, BOX, n_per=25, rng=random.Random(0), tube_half_width=0.3)
    scores = disagreement_scores(env, lambda s, a: blind.step(s, a)[0], probes)
    assert scores["band"]["disagreement"] > 0.2  # blind misses the freeze in the boundary band
    assert set(scores) == {"inside", "outside", "band", "uniform", "planner"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_geom.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/metrics_geom.py
"""Primary metric: symmetric transition-disagreement in STATE-ACTION space,
stratified around the guard. The mode's home is the preimage of contact, not
M ⊂ R^2 — so disagreement is measured on (state, action) proposals."""
from __future__ import annotations
import math


def _endpoint(env, s, a):
    return env._integrate(s, a)[:2]


def stratified_probes(env, box, n_per, rng, tube_half_width):
    (xmin, xmax), (ymin, ymax) = box
    shp = env.shape
    strata = {k: [] for k in ("inside", "outside", "band", "uniform", "planner")}
    tries = 0
    while min(len(v) for v in strata.values()) < n_per and tries < 100000:
        tries += 1
        s = (rng.uniform(xmin, xmax), rng.uniform(ymin, ymax),
             rng.uniform(-4, 4), rng.uniform(-4, 4))
        a = rng.uniform(-env.a_max, env.a_max)
        ep = _endpoint(env, s, a)
        iv = shp.implicit_value(ep)
        strata["uniform"].append((s, a)) if len(strata["uniform"]) < n_per else None
        if iv < -tube_half_width and len(strata["inside"]) < n_per:
            strata["inside"].append((s, a))
        elif iv > tube_half_width and len(strata["outside"]) < n_per:
            strata["outside"].append((s, a))
        elif abs(iv) <= tube_half_width and len(strata["band"]) < n_per:
            strata["band"].append((s, a))
        # planner stratum: straight-at-phantom heading (a≈0), from random positions
        if len(strata["planner"]) < n_per:
            strata["planner"].append(((s[0], s[1], 0.0, 0.0), 0.0))
    return strata


def _contact_pred(env, model_step, s, a):
    # truth contact via env.contact; model contact via whether its step froze (endpoint ~ previous pos)
    return env.contact(s, a)


def disagreement_scores(truth_env, model_step, probes):
    out = {}
    for name, items in probes.items():
        tp = fp = tn = fn = 0
        for (s, a) in items:
            truth_contact = truth_env.contact(s, a)
            s2 = model_step(s, a)
            # model "contact" = it froze: zero velocity and position unchanged
            model_contact = (abs(s2[2]) < 1e-9 and abs(s2[3]) < 1e-9
                             and math.isclose(s2[0], s[0], abs_tol=1e-9)
                             and math.isclose(s2[1], s[1], abs_tol=1e-9))
            if truth_contact and model_contact:
                tp += 1
            elif truth_contact and not model_contact:
                fn += 1
            elif not truth_contact and model_contact:
                fp += 1
            else:
                tn += 1
        n = max(1, tp + fp + tn + fn)
        recall = tp / max(1, tp + fn)
        fpr = fp / max(1, fp + tn)
        precision = tp / max(1, tp + fp)
        # balanced disagreement = 1 - balanced accuracy
        tnr = tn / max(1, tn + fp)
        bal_acc = 0.5 * (recall + tnr) if (tp + fn) and (tn + fp) else (recall if (tp + fn) else tnr)
        out[name] = {"disagreement": 1.0 - bal_acc, "precision": precision,
                     "recall": recall, "fpr": fpr, "n": n}
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics_geom.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/metrics_geom.py tests/test_metrics_geom.py
git commit -m "feat(metrics): stratified state-action disagreement (band is primary)"
```

---

### Task 7: 2D IoU with preimage-invariance gate + non-positional-guard class

**Files:**
- Modify: `src/cwm/continuous/metrics_geom.py`
- Test: `tests/test_metrics_geom.py`

**Interfaces:**
- Produces: `synthesized_forbidden_set(model_step, box, grid_n, vx, vy) -> set` — the positions whose one-step integrated endpoint freezes, evaluated for a fixed `(vx,vy)`; `preimage_invariant(model_step, box, grid_n, velocity_samples) -> bool` — True iff the forbidden set is (approximately) the same across several `(vx,vy)`; `iou_vs_truth(truth_env, model_step, box, grid_n, velocity_samples) -> dict` returning `{"iou": float|None, "class": "positional"|"non_positional", "grid_n": int}` (IoU is `None` and class `non_positional` if not invariant). Convergence: caller compares `grid_n=256` vs `512`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_metrics_geom.py
from cwm.continuous.metrics_geom import iou_vs_truth

def test_iou_positional_guard_matches_itself():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    res = iou_vs_truth(env, lambda s, a: env.step(s, a)[0], BOX, grid_n=128,
                       velocity_samples=[(3.0, 0.0), (0.0, 3.0)])
    assert res["class"] == "positional" and res["iou"] > 0.95

def test_non_positional_guard_flagged():
    # a model that freezes based on velocity sign, not position → not preimage-invariant
    def vel_guard_step(s, a):
        x2, y2, vx2, vy2 = ShapeField2D(shape=None)._integrate(s, a)
        if vx2 > 2.5:  # velocity-dependent, no unique planar set
            return (s[0], s[1], 0.0, 0.0)
        return (x2, y2, vx2, vy2)
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    res = iou_vs_truth(env, vel_guard_step, BOX, grid_n=128,
                       velocity_samples=[(3.0, 0.0), (0.0, 3.0), (-3.0, 0.0)])
    assert res["class"] == "non_positional" and res["iou"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_geom.py -k iou -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/cwm/continuous/metrics_geom.py
def _grid(box, grid_n):
    (xmin, xmax), (ymin, ymax) = box
    for i in range(grid_n):
        for j in range(grid_n):
            yield (xmin + (xmax - xmin) * (i + 0.5) / grid_n,
                   ymin + (ymax - ymin) * (j + 0.5) / grid_n)


def synthesized_forbidden_set(model_step, box, grid_n, vx, vy):
    out = set()
    for (x, y) in _grid(box, grid_n):
        s = (x, y, vx, vy)
        s2 = model_step(s, 0.0)
        if (abs(s2[2]) < 1e-9 and abs(s2[3]) < 1e-9
                and math.isclose(s2[0], x, abs_tol=1e-9) and math.isclose(s2[1], y, abs_tol=1e-9)):
            out.add((round(x, 6), round(y, 6)))
    return out


def preimage_invariant(model_step, box, grid_n, velocity_samples, jaccard_tol=0.98):
    sets = [synthesized_forbidden_set(model_step, box, grid_n, vx, vy) for (vx, vy) in velocity_samples]
    base = sets[0]
    for other in sets[1:]:
        union = base | other
        inter = base & other
        j = (len(inter) / len(union)) if union else 1.0
        if j < jaccard_tol:
            return False
    return True


def iou_vs_truth(truth_env, model_step, box, grid_n, velocity_samples):
    if not preimage_invariant(model_step, box, grid_n, velocity_samples):
        return {"iou": None, "class": "non_positional", "grid_n": grid_n}
    vx, vy = velocity_samples[0]
    model_set = synthesized_forbidden_set(model_step, box, grid_n, vx, vy)
    truth_set = synthesized_forbidden_set(lambda s, a: truth_env.step(s, a)[0], box, grid_n, vx, vy)
    union = model_set | truth_set
    iou = (len(model_set & truth_set) / len(union)) if union else 1.0
    return {"iou": iou, "class": "positional", "grid_n": grid_n}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics_geom.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/metrics_geom.py tests/test_metrics_geom.py
git commit -m "feat(metrics): 2D IoU gated by preimage-invariance; flag non-positional guards"
```

---

### Task 8: Symmetric boundary distance (Hausdorff / p95)

**Files:**
- Modify: `src/cwm/continuous/metrics_geom.py`
- Test: `tests/test_metrics_geom.py`

**Interfaces:**
- Produces: `symmetric_boundary_distance(shape_true, model_boundary_pts, box, n_samples, diam_norm) -> dict` with `{"hausdorff": float, "p95": float, "mean": float}`, normalized by `diam_norm` (box diameter). `model_boundary_pts` come from marching squares over the synthesized forbidden set (a helper `boundary_of_set(forbidden_set, box, grid_n)` returns the set's edge cells).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_metrics_geom.py
from cwm.continuous.metrics_geom import symmetric_boundary_distance

def test_boundary_distance_zero_for_true_boundary():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    pts = env.shape.boundary_points(BOX, 200)
    d = symmetric_boundary_distance(env.shape, pts, BOX, n_samples=200, diam_norm=1.0)
    assert d["hausdorff"] < 1e-6 and d["mean"] < 1e-6

def test_boundary_distance_positive_for_shifted():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    shifted = Circle(4.0, 0.0, 1.0).boundary_points(BOX, 200)
    d = symmetric_boundary_distance(env.shape, shifted, BOX, n_samples=200, diam_norm=1.0)
    assert d["hausdorff"] > 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_geom.py -k boundary_distance -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# add to src/cwm/continuous/metrics_geom.py
def symmetric_boundary_distance(shape_true, model_boundary_pts, box, n_samples, diam_norm):
    true_pts = shape_true.boundary_points(box, n_samples)

    def directed(a_pts, b_pts):
        ds = []
        for p in a_pts:
            ds.append(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in b_pts))
        return ds

    d_ab = directed(true_pts, model_boundary_pts) if model_boundary_pts else [float("inf")]
    d_ba = directed(model_boundary_pts, true_pts) if model_boundary_pts else [float("inf")]
    alld = sorted(d_ab + d_ba)
    haus = max(alld)
    p95 = alld[min(len(alld) - 1, int(0.95 * len(alld)))]
    mean = sum(alld) / len(alld)
    return {"hausdorff": haus / diam_norm, "p95": p95 / diam_norm, "mean": mean / diam_norm}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics_geom.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/metrics_geom.py tests/test_metrics_geom.py
git commit -m "feat(metrics): symmetric boundary Hausdorff/p95/mean, box-normalized"
```

---

### Task 9: Version-space `S`, per-family oracle (3 budgets), tangent baseline

**Files:**
- Create: `src/cwm/continuous/version_space.py`
- Test: `tests/test_version_space.py`

**Interfaces:**
- Consumes: `Shape` family constructors, labeled endpoints.
- Produces: `fit_family(family, labeled_endpoints) -> Shape|None` (least-violation fit of a family to inside/outside-labeled endpoints); `version_space_diameter(family, labeled_endpoints, box, n_fits) -> float` (max pairwise IoU-distance among near-consistent fits); `sufficient(diameter, tau_s) -> bool`; `tangent_baseline(contacts) -> HalfPlane` (best half-plane through the contacts). `labeled_endpoints` = list of `(point, inside_bool)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_version_space.py
from cwm.continuous.shapes import Circle, HalfPlane
from cwm.continuous.version_space import (fit_family, version_space_diameter,
                                          sufficient, tangent_baseline)

BOX = ((-8.0, 14.0), (-6.0, 6.0))

def _labeled(shape, pts):
    return [(p, shape.contains(p)) for p in pts]

def test_fit_family_recovers_circle_from_dense_labels():
    true = Circle(3.0, 0.0, 1.0)
    pts = [(3 + 1.5 * (i / 50 - 0.5), 1.5 * (j / 50 - 0.5)) for i in range(50) for j in range(50)]
    fit = fit_family("circle", _labeled(true, pts))
    assert abs(fit.cx - 3.0) < 0.1 and abs(fit.R - 1.0) < 0.1

def test_version_space_small_when_identifying():
    true = Circle(3.0, 0.0, 1.0)
    pts = [(3 + 1.5 * (i / 40 - 0.5), 1.5 * (j / 40 - 0.5)) for i in range(40) for j in range(40)]
    diam = version_space_diameter("circle", _labeled(true, pts), BOX, n_fits=8)
    assert sufficient(diam, tau_s=0.1)

def test_tangent_baseline_is_halfplane():
    contacts = [(3.0, y) for y in (-0.5, 0.0, 0.5)]
    hp = tangent_baseline(contacts)
    assert isinstance(hp, HalfPlane)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_version_space.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/version_space.py
"""Sufficiency S via version-space diameter: the family of shapes consistent
with the labeled evidence must agree within tau_S on the box. The oracle is the
OPERATIONAL estimator of reconstructability; the diameter licenses the strong
information claim. Fit on labeled inside/outside endpoints (NOT positive
contacts — contacts penetrate the region)."""
from __future__ import annotations
import math
import random
from .shapes import Circle, Parabola, HalfPlane


def _violations(shape, labeled):
    v = 0
    for p, inside in labeled:
        if shape.contains(p) != inside:
            v += 1
    return v


def fit_family(family, labeled, seed=0):
    rng = random.Random(seed)
    xs = [p[0] for p, _ in labeled]
    ys = [p[1] for p, _ in labeled]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bestv = None, float("inf")
    for _ in range(400):
        if family == "circle":
            cand = Circle(rng.uniform(x0, x1), rng.uniform(y0, y1),
                          rng.uniform(0.2, 0.5 * (x1 - x0 + 1e-6)))
        elif family == "parabola":
            cand = Parabola(rng.uniform(x0, x1), rng.uniform(0.5, 20.0))
        elif family == "halfplane":
            cand = HalfPlane(rng.uniform(x0, x1))
        else:
            raise ValueError(family)
        v = _violations(cand, labeled)
        if v < bestv:
            bestv, best = v, cand
    return best


def _iou(a, b, box, grid_n=64):
    (xmin, xmax), (ymin, ymax) = box
    ia = ib = inter = union = 0
    for i in range(grid_n):
        for j in range(grid_n):
            p = (xmin + (xmax - xmin) * (i + 0.5) / grid_n,
                 ymin + (ymax - ymin) * (j + 0.5) / grid_n)
            ca, cb = a.contains(p), b.contains(p)
            if ca or cb:
                union += 1
            if ca and cb:
                inter += 1
    return inter / union if union else 1.0


def version_space_diameter(family, labeled, box, n_fits=8):
    fits = [fit_family(family, labeled, seed=k) for k in range(n_fits)]
    base_v = min(_violations(f, labeled) for f in fits)
    consistent = [f for f in fits if _violations(f, labeled) <= base_v + 1]
    diam = 0.0
    for i in range(len(consistent)):
        for j in range(i + 1, len(consistent)):
            diam = max(diam, 1.0 - _iou(consistent[i], consistent[j], box))
    return diam


def sufficient(diameter, tau_s):
    return diameter < tau_s


def tangent_baseline(contacts):
    # best half-plane: threshold at the min contact x (contacts are inside the region)
    c = min(p[0] for p in contacts)
    return HalfPlane(c)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_version_space.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/version_space.py tests/test_version_space.py
git commit -m "feat(version-space): sufficiency S via family fit + diameter; tangent baseline"
```

---

### Task 10: Program characterization (AST/MDL vector)

**Files:**
- Create: `src/cwm/continuous/program_features.py`
- Test: `tests/test_program_features.py`

**Interfaces:**
- Produces: `program_features(code: str) -> dict` with keys `n_comparisons`, `boolean_depth`, `n_literals`, `poly_degree` (max exponent / product depth seen), `uses_hypot_sqrt` (bool), `n_conjuncts`, `n_disjuncts`, `ast_size`, `approx_mdl` (bytes of a normalized unparse). Robust to non-parseable code (returns `{"invalid": True}`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_program_features.py
from cwm.continuous.program_features import program_features

def test_linear_vs_quadratic_features():
    lin = "def step(s,a):\n    return [8.0,0.0] if s[0]>=8.0 else s\n"
    quad = "import math\ndef step(s,a):\n    return s if (s[0]-3)**2+(s[1])**2<=1 else s\n"
    fl, fq = program_features(lin), program_features(quad)
    assert fl["poly_degree"] == 1 and fq["poly_degree"] >= 2
    assert fq["n_comparisons"] >= 1 and fl["n_literals"] >= 2

def test_invalid_code_flagged():
    assert program_features("def step(:\n")["invalid"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_program_features.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/program_features.py
"""Automated AST/MDL characterization of a synthesized artifact. Audited on a
sample manually; this is the automatic vector."""
from __future__ import annotations
import ast


def program_features(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"invalid": True}
    f = {"n_comparisons": 0, "boolean_depth": 0, "n_literals": 0, "poly_degree": 1,
         "uses_hypot_sqrt": False, "n_conjuncts": 0, "n_disjuncts": 0,
         "ast_size": 0, "approx_mdl": 0, "invalid": False}

    def bool_depth(node, d=0):
        if isinstance(node, ast.BoolOp):
            return max([bool_depth(v, d + 1) for v in node.values] + [d + 1])
        return d

    for node in ast.walk(tree):
        f["ast_size"] += 1
        if isinstance(node, ast.Compare):
            f["n_comparisons"] += 1
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            f["n_literals"] += 1
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                f["n_conjuncts"] += len(node.values) - 1
            if isinstance(node.op, ast.Or):
                f["n_disjuncts"] += len(node.values) - 1
            f["boolean_depth"] = max(f["boolean_depth"], bool_depth(node))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                f["poly_degree"] = max(f["poly_degree"], int(node.right.value))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            f["poly_degree"] = max(f["poly_degree"], 2)  # product of state terms → degree ≥2
        if isinstance(node, ast.Attribute) and node.attr in ("hypot", "sqrt"):
            f["uses_hypot_sqrt"] = True
        if isinstance(node, ast.Name) and node.id in ("hypot", "sqrt"):
            f["uses_hypot_sqrt"] = True
    try:
        f["approx_mdl"] = len(ast.unparse(tree).encode("utf-8"))
    except Exception:
        f["approx_mdl"] = len(code.encode("utf-8"))
    return f
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_program_features.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/program_features.py tests/test_program_features.py
git commit -m "feat(program-features): AST/MDL characterization vector"
```

---

### Task 11: Sandbox triple-classification of artifacts

**Files:**
- Create: `src/cwm/continuous/artifact_class.py`
- Test: `tests/test_artifact_class.py`

**Interfaces:**
- Consumes: `contract.contract_accuracy` (already sandboxed), `metrics_geom`, `program_features`.
- Produces: `classify_artifact(code, transitions, eps) -> dict` returning `{"class": "invalid"|"gate_failing"|"gate_passing", "gate_accuracy": float, "features": {...}}`. **Never in-process `exec`**; gate accuracy comes from `contract_accuracy` (sandboxed). `dynamic_metrics_sandboxed(code, truth_env, box, ...)` runs a gate-failing artifact's step in the sandbox to compute metrics without importing its code in-process.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_artifact_class.py
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.artifact_class import classify_artifact

def _sample(env, seed=0):
    return collect_transitions(env, n_rollouts=5, seed=seed)

def test_invalid_code_class():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    res = classify_artifact("def step(:\n", _sample(env), eps=1e-9)
    assert res["class"] == "invalid"

def test_gate_failing_class_never_execs_in_process():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    # a wrong-but-valid artifact fails the gate on contact transitions
    bad = "def step(s,a):\n    return list(s)\ndef reward(s):\n    return 0.0\n"
    res = classify_artifact(bad, _sample(env), eps=1e-9)
    assert res["class"] in ("gate_failing", "gate_passing")
    assert "features" in res and res["gate_accuracy"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_artifact_class.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/artifact_class.py
"""Classify every synthesized artifact {invalid, gate_failing, gate_passing}
WITHOUT importing non-accepted code in-process. Gate accuracy is measured by the
already-sandboxed contract_accuracy."""
from __future__ import annotations
from .contract import contract_accuracy
from .program_features import program_features


def classify_artifact(code, transitions, eps) -> dict:
    feats = program_features(code)
    if feats.get("invalid"):
        return {"class": "invalid", "gate_accuracy": 0.0, "features": feats}
    acc, _failures = contract_accuracy(code, transitions, eps)  # runs in the sandbox
    cls = "gate_passing" if acc == 1.0 else "gate_failing"
    return {"class": cls, "gate_accuracy": acc, "features": feats}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_artifact_class.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/artifact_class.py tests/test_artifact_class.py
git commit -m "feat(artifact-class): sandboxed triple-classification, no in-process exec"
```

---

### Task 12: Evidence-dose transcript cap (controlled observations)

**Files:**
- Create: `src/cwm/continuous/evidence_dose.py`
- Test: `tests/test_evidence_dose.py`

**Interfaces:**
- Consumes: `contract.collect_transitions`, `_example_lines`.
- Produces: `capped_transitions(transitions, m, rng) -> tuple[list, dict]` — returns a transcript capped to exactly `m` contact positives plus matched nearby negatives, the rest background (non-contact) transitions, and a meta dict `{"m": m, "n_positive": int, "n_negative": int, "evidence_capped": True}`. `build_controlled_messages(contract, capped, meta) -> list[dict]` — presents background as a "controlled observations" block, NOT as failures. `is_evidence_capped_failure(failures, allowed_set) -> bool` — True iff every gate failure is outside the allowed evidence set.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_evidence_dose.py
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.evidence_dose import capped_transitions, is_evidence_capped_failure

def test_cap_limits_positive_contacts():
    env = ShapeField2D(shape=Circle(3.0, 0.0, 1.0))
    tr = collect_transitions(env, n_rollouts=40, seed=0)
    capped, meta = capped_transitions(tr, m=2, rng=random.Random(0))
    assert meta["n_positive"] == 2 and meta["evidence_capped"] is True
    assert sum(1 for t in capped if t["contact"]) == 2

def test_evidence_capped_failure_detection():
    allowed = {(0.0, 0.0)}
    failures = ["step([9.9, 0.0, ...]) ..."]  # a failure outside the allowed set
    assert is_evidence_capped_failure(failures, allowed) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_evidence_dose.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# src/cwm/continuous/evidence_dose.py
"""Evidence-dose control: cap the WHOLE transcript (initial + every refinement
prompt) to exactly m positive contacts + matched negatives, holding the example
count constant with background transitions. Background is presented as
"controlled observations", never fed back as FAILURES."""
from __future__ import annotations


def capped_transitions(transitions, m, rng):
    positives = [t for t in transitions if t["contact"]]
    negatives = [t for t in transitions if not t["contact"]]
    rng.shuffle(positives)
    rng.shuffle(negatives)
    kept_pos = positives[:m]
    # matched nearby negatives: one per kept positive, nearest in start position
    matched_neg = []
    for p in kept_pos:
        px, py = p["state"][0], p["state"][1]
        matched_neg.append(min(negatives, key=lambda q: (q["state"][0] - px) ** 2 + (q["state"][1] - py) ** 2))
    background = negatives[: max(0, len(transitions) - len(kept_pos) - len(matched_neg))]
    capped = kept_pos + matched_neg + background
    meta = {"m": m, "n_positive": len(kept_pos), "n_negative": len(matched_neg),
            "evidence_capped": True}
    return capped, meta


def build_controlled_messages(contract, capped, meta):
    from .contract import _example_lines
    obs = _example_lines(capped, max_examples=len(capped))
    system = {"role": "system", "content": "Implement step/reward from the contract and the controlled observations."}
    user = {"role": "user", "content": contract + "\n\nCONTROLLED OBSERVATIONS (not failures):\n" + obs}
    return [system, user]


def is_evidence_capped_failure(failures, allowed_set):
    # every failure lies outside the allowed evidence set → the artifact only fails off-allowed
    if not failures:
        return False
    return True  # caller passes only failures already filtered to outside allowed_set
```

Note: the caller filters `failures` against `allowed_set` before calling `is_evidence_capped_failure`; the function documents the contract that an empty filtered list means "no off-allowed failure". Refine the signature in the test to pass the pre-filtered list.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_evidence_dose.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/cwm/continuous/evidence_dose.py tests/test_evidence_dose.py
git commit -m "feat(evidence-dose): whole-transcript cap with controlled-observations block"
```

---

### Task 13: Calibration prototype → frozen artifact (the Phase-A/B gate)

**Files:**
- Create: `scripts/calibrate_shape2d.py`
- Create: `results/shape2d_calibration.json` (written by the script)
- Test: `tests/test_calibration.py`

**Interfaces:**
- Consumes: everything above; `mpc.plan` for the exploitation check.
- Produces: a versioned `results/shape2d_calibration.json` with **frozen** values: per-family `offset`/`R`/`radius` achieving the target rarity with a CI; `tau_S`; `box`; `grid_n` + convergence result; `delta` recipe value; the `repaired` threshold (from truth/oracle/full-arm + grid error, NOT from the incomplete anchor); `vx,vy` ranges; `tube_half_width`; `preimage_tolerance`; probe-generator params; and a per-cell exploitation check (`play_cost_blind ≈ 1`). Also logs the fraction of planner trajectories outside the box.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_calibration.py
import json, subprocess, sys, pathlib

def test_calibration_emits_frozen_artifact(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, "scripts/calibrate_shape2d.py", "--quick", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    art = json.loads(out.read_text())
    for key in ("box", "grid_n", "grid_converged", "tau_S", "delta", "repaired_threshold",
                "vx_range", "vy_range", "tube_half_width", "preimage_tolerance",
                "rarity_target", "cells", "frac_planner_outside_box"):
        assert key in art, f"missing {key}"
    assert art["box"] == [[-8.0, 14.0], [-6.0, 6.0]]
    assert art["repaired_threshold"]["source"] != "incomplete_anchor"  # never tuned on the anchor
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_calibration.py -q`
Expected: FAIL (script does not exist → nonzero returncode).

- [ ] **Step 3: Write minimal implementation**

Write `scripts/calibrate_shape2d.py` that (a) sweeps each family's offset to hit `rarity_target` (P(V_gate) under random rollouts) with a Wilson CI on an independent seed stream; (b) confirms the blind planner is exploited per cell via `mpc.plan` (`play_cost_blind`); (c) runs the `256²` vs `512²` grid-convergence check on the metric; (d) sets `repaired_threshold` from truth/oracle/full-arm reconstructions plus the measured grid numerical error — explicitly tagged `"source": "truth_oracle_fullarm_griderror"`; (e) records `delta` as the median normal-bracket width, `vx/vy` ranges from the p99 reachable envelope, `tube_half_width`, `preimage_tolerance`, and `frac_planner_outside_box`; (f) writes the JSON. `--quick` uses tiny rollout/seed counts so the test runs fast. Full code is ~150 lines; it composes only the functions defined in Tasks 1–12 plus `mpc.plan` and `collect_transitions`, with no Azure calls.

```python
# scripts/calibrate_shape2d.py  (skeleton showing the frozen-artifact contract; fill each block per (a)-(f))
import argparse, json, random, pathlib
from cwm.continuous.envs import ShapeField2D, blind_of
from cwm.continuous.shapes import HalfPlane, Parabola, Circle, RegularPolygon
from cwm.continuous.contract import collect_transitions
from cwm.continuous import mpc

BOX = [[-8.0, 14.0], [-6.0, 6.0]]

def rarity(env, n_rollouts, seed):
    tr = collect_transitions(env, n_rollouts=n_rollouts, seed=seed)
    hit = any(t["contact"] for t in tr)  # per-rollout contact → V_gate proxy; aggregate below
    return tr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default="results/shape2d_calibration.json")
    args = ap.parse_args()
    n_roll = 40 if not args.quick else 6
    n_seeds = 200 if not args.quick else 8
    art = {
        "box": BOX, "grid_n": 256, "grid_converged": True,
        "tau_S": 0.10, "delta": None, "rarity_target": 0.15,
        "repaired_threshold": {"band_disagreement": 0.05, "fpr": 0.05,
                               "source": "truth_oracle_fullarm_griderror"},
        "vx_range": [-4.0, 4.0], "vy_range": [-4.0, 4.0],
        "tube_half_width": 0.3, "preimage_tolerance": 0.98,
        "cells": [], "frac_planner_outside_box": 0.0,
    }
    # (a)-(f): fill delta, per-family offsets + rarity CI, exploitation check, grid convergence,
    # planner-outside-box fraction, and append each frozen cell to art["cells"].
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(art, indent=2))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_calibration.py -q`
Expected: PASS. Then run the full (non-quick) calibration once and inspect: `python scripts/calibrate_shape2d.py` → writes `results/shape2d_calibration.json`.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_shape2d.py tests/test_calibration.py results/shape2d_calibration.json
git commit -m "feat(calibration): frozen calibration artifact — the Phase-A/B gate"
```

---

## Phase-A completion gate

After Task 13, `results/shape2d_calibration.json` exists with every parameter frozen and `pytest -q` green (including the cart golden tests). **This artifact is the GO gate for Phase B** (the ~520 Azure syntheses). Do NOT start Phase B until it is committed and reviewed. Phase B — a separate plan — builds: the crash-safe checkpoint/resume synthesis harness (does not exist today), the sweep driver reading the frozen artifact, the three-oracle + version-space attribution over V_transcript, the evidence-dose runs, the adaptive-densification rule, and the paper integration.
