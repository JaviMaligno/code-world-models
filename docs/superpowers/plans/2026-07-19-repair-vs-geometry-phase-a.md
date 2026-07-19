# Repair-vs-Geometry — Phase A (infrastructure + calibration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build every apparatus piece for the repair-vs-geometry experiment and produce a frozen, strictly-validated calibration artifact — the gate that authorizes the ~520 Azure syntheses (Phase B, separate plan).

**Architecture:** A new `Shape` abstraction (unbounded-safe, with correct arc-length sampling, true signed distance, and multimodal projection) drives a new single-mode 2D instrument `ShapeField2D` that reuses a shared integrator with `PatchField2D`. Probes, band strata, and the IoU forbidden set are all built by **inverting the integrator** (endpoint→previous-state), never by guessing. New metric/analysis modules sit beside the existing pipeline. A calibration prototype writes a versioned JSON, and a strict validator makes an unfilled placeholder impossible to pass.

**Tech Stack:** Python 3.12, pytest (`pythonpath=["src"]`, `testpaths=["tests"]`), numpy (dep), stdlib `ast`, `bisect`. No new heavy deps.

## Rev history

rev. 2 (this file) rewrites Tasks 1–3, 5–7, 9, 11–13 after an expert NO-GO on rev. 1: rev. 1's geometry did fake arc-length sampling, unimodal-only projection, non-comparable `implicit_value` tube widths, an IoU that measured the translated preimage, a version-space that only bounded `S` from below, an evidence dose that didn't cap the transcript, and a calibration gate that checked only key presence. Every one is fixed below with brute-force oracle tests.

## Global Constraints

- **V ≡ V_transcript** everywhere. Log V_gate, V_initial, V_transcript (Phase B).
- **Primary metric is in state–action space**; 2D IoU is reported ONLY after a preimage-invariance check; else the artifact is a `non_positional` guard.
- **The `repaired` threshold is fixed from truth/oracle/full-arm reconstructions + the grid's numerical error — NEVER tuned on the incomplete anchor.**
- **Sufficiency `S`:** Phase A ships only the **operational oracle** and leaves `S` *uncertified* (a conservative version-space upper bound is deferred to Phase B). Do not claim identification from the operational oracle alone.
- **Evidence-dose caps the WHOLE transcript** to a fixed size (`40 = m positives + m matched negatives + (40−2m) background`); background is a "controlled observations" block, NEVER fed back as FAILURES; failures carry **structured indices** so membership in the allowed set is decidable; the cap is enforced on EVERY refinement iteration.
- **Never in-process `exec` non-accepted code.** Accepted (gate-passing) code may be exec'd in-process for grid metrics; gate-failing artifacts are evaluated by a **single sandbox call that returns a mask** over a supplied grid, never one call per point.
- **All distances are true signed distances** (euclidean to the projected boundary point), never `implicit_value` (whose units differ across families).
- **All probes/band/IoU states are built by inverting the integrator** so that `truth.contact(state, action)` is guaranteed for intended-inside probes.
- Numeric anchors (verbatim): box `[-8,14]×[-6,6]`; grid `256²` initial, converged if the metric shifts `<1%` at `512²`; `implicit_value` sign **negative inside**; `repaired = band-disagreement ≤ 0.05 AND FPR ≤ 0.05`.
- **Cart golden byte-identity tests MUST keep passing** (`tests/test_instruments.py::test_cart_spec_is_byte_identical_to_golden`, `tests/test_continuous_contract.py::test_build_contract_cart_matches_golden`). Do not change `CART_SPEC`/`PENDULUM_SPEC`/`PATCH2D_SPEC` output or `build_contract`'s cart path.
- Shape params validated in `__post_init__`: `R>0`, `k≥3`, `w>0`, `half_angle∈(0,π/2)`.
- No checkpoint/resume exists today; Phase A's calibration run is cheap. Phase B builds the crash-safe harness.

---

### Task 1: Shared integrator + its inverse; `Shape` base with true signed distance; HalfPlane + Circle

**Files:**
- Modify: `src/cwm/continuous/envs.py` (extract `integrate_2d`, add `invert_integrator`)
- Create: `src/cwm/continuous/shapes.py`
- Test: `tests/test_shapes.py`, `tests/test_integrator_shared.py`

**Interfaces:**
- Produces: `integrate_2d(state, action, dt, gain, drag, a_max) -> (x2,y2,vx2,vy2)`; `invert_integrator(endpoint_xy, vx, vy, action, dt, gain, drag, a_max) -> (x,y,vx,vy)` (previous state whose integration lands its position exactly at `endpoint_xy`). `class Shape` with `contains`, `implicit_value` (neg inside), `project_to_boundary(p)->(pt,multi)`, `signed_distance(p)->float` (euclidean, signed by containment), `boundary_points(window,n)` (arc-length uniform, all in window), `normal_or_cone(p)`. `HalfPlane(c)`, `Circle(cx,cy,R)`.

- [ ] **Step 1: Write failing tests (shared integrator equivalence + geometry properties, with brute-force oracles)**

```python
# tests/test_integrator_shared.py
import math, random
from cwm.continuous.envs import integrate_2d, invert_integrator, PatchField2D, ShapeField2D
from cwm.continuous.shapes import Circle

def test_integrate_2d_matches_patchfield_exactly():
    env = PatchField2D()
    rng = random.Random(0)
    for _ in range(500):
        s = (rng.uniform(-8, 14), rng.uniform(-6, 6), rng.uniform(-4, 4), rng.uniform(-4, 4))
        a = rng.uniform(-1, 1)
        assert integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max) == env._integrate(s, a)

def test_invert_integrator_lands_on_endpoint():
    env = PatchField2D()
    rng = random.Random(1)
    for _ in range(500):
        p = (rng.uniform(-8, 14), rng.uniform(-6, 6)); vx, vy, a = rng.uniform(-4,4), rng.uniform(-4,4), rng.uniform(-1,1)
        s = invert_integrator(p, vx, vy, a, env.dt, env.gain, env.drag, env.a_max)
        x2, y2, _, _ = integrate_2d(s, a, env.dt, env.gain, env.drag, env.a_max)
        assert math.isclose(x2, p[0], abs_tol=1e-9) and math.isclose(y2, p[1], abs_tol=1e-9)
```

```python
# tests/test_shapes.py
import math, random
from cwm.continuous.shapes import HalfPlane, Circle
WIN = ((-8.0, 14.0), (-6.0, 6.0))

def _consecutive_uniform(pts, tol=0.25):
    ds = [math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1)]
    m = sum(ds)/len(ds)
    return all(abs(d-m) <= tol*m for d in ds)

def _brute_project(shape, p, win, n=4000):
    best, bd = None, 1e18
    for q in shape.boundary_points(win, n):
        d = math.hypot(p[0]-q[0], p[1]-q[1])
        if d < bd: bd, best = d, q
    return best, bd

def test_halfplane_sign_and_signed_distance():
    hp = HalfPlane(3.0)
    assert hp.implicit_value((5.0,0.0)) < 0 < hp.implicit_value((1.0,0.0))
    assert math.isclose(hp.signed_distance((1.0,0.0)), 2.0)   # outside, +2
    assert math.isclose(hp.signed_distance((5.0,0.0)), -2.0)  # inside,  -2

def test_circle_boundary_is_arc_length_uniform_and_in_window():
    c = Circle(3.0, 0.0, 1.0)
    pts = c.boundary_points(WIN, 60)
    assert len(pts) == 60
    for x,y in pts:
        assert -8 <= x <= 14 and -6 <= y <= 6 and abs(c.implicit_value((x,y))) < 1e-6
    assert _consecutive_uniform(pts)

def test_circle_projection_matches_bruteforce():
    c = Circle(3.0, 0.0, 1.0); rng = random.Random(0)
    for _ in range(50):
        p = (rng.uniform(-2,8), rng.uniform(-5,5))
        (px,py), _ = c.project_to_boundary(p)
        _, bd = _brute_project(c, p, WIN)
        assert math.hypot(p[0]-px, p[1]-py) <= bd + 1e-3

def test_circle_center_is_multivalued():
    assert Circle(3.0,0.0,1.0).project_to_boundary((3.0,0.0))[1] is True

def test_param_validation():
    import pytest
    with pytest.raises(ValueError):
        Circle(0.0, 0.0, -1.0)
```

- [ ] **Step 2: Run to verify they fail** — `pytest tests/test_shapes.py tests/test_integrator_shared.py -q` → FAIL (imports).

- [ ] **Step 3: Implement**

In `envs.py`, extract the integrator and add the inverse (module-level), then make `PatchField2D._integrate` and (Task 4) `ShapeField2D._integrate` call `integrate_2d`:

```python
def integrate_2d(state, action, dt, gain, drag, a_max):
    x, y, vx, vy = state
    a = max(-a_max, min(a_max, action))
    phi = math.pi * a / a_max
    vx2 = vx + (gain * math.cos(phi) - drag * vx) * dt
    vy2 = vy + (gain * math.sin(phi) - drag * vy) * dt
    return x + vx2 * dt, y + vy2 * dt, vx2, vy2

def invert_integrator(endpoint_xy, vx, vy, action, dt, gain, drag, a_max):
    a = max(-a_max, min(a_max, action))
    phi = math.pi * a / a_max
    vx2 = vx + (gain * math.cos(phi) - drag * vx) * dt
    vy2 = vy + (gain * math.sin(phi) - drag * vy) * dt
    return (endpoint_xy[0] - vx2 * dt, endpoint_xy[1] - vy2 * dt, vx, vy)
```
Change `PatchField2D._integrate` body to `return integrate_2d(state, action, self.dt, self.gain, self.drag, self.a_max)`.

`shapes.py`:

```python
from __future__ import annotations
import math
from dataclasses import dataclass

class Shape:
    def contains(self, p) -> bool: return self.implicit_value(p) <= 0.0
    def implicit_value(self, p) -> float: raise NotImplementedError
    def project_to_boundary(self, p): raise NotImplementedError
    def boundary_points(self, window, n): raise NotImplementedError
    def normal_or_cone(self, p): raise NotImplementedError
    def signed_distance(self, p) -> float:
        q, _ = self.project_to_boundary(p)
        d = math.hypot(p[0]-q[0], p[1]-q[1])
        return -d if self.contains(p) else d

@dataclass(frozen=True)
class HalfPlane(Shape):
    c: float  # region x >= c
    def implicit_value(self, p): return self.c - p[0]
    def project_to_boundary(self, p): return (self.c, p[1]), False
    def normal_or_cone(self, p): return (-1.0, 0.0)
    def boundary_points(self, window, n):
        (_, _), (ymin, ymax) = window
        if n == 1: return [(self.c, 0.5*(ymin+ymax))]
        return [(self.c, ymin + (ymax-ymin)*i/(n-1)) for i in range(n)]

@dataclass(frozen=True)
class Circle(Shape):
    cx: float; cy: float; R: float
    def __post_init__(self):
        if self.R <= 0: raise ValueError("R>0 required")
    def implicit_value(self, p): return (p[0]-self.cx)**2 + (p[1]-self.cy)**2 - self.R**2
    def project_to_boundary(self, p):
        dx, dy = p[0]-self.cx, p[1]-self.cy; d = math.hypot(dx, dy)
        if d < 1e-12: return (self.cx+self.R, self.cy), True
        return (self.cx + self.R*dx/d, self.cy + self.R*dy/d), False
    def normal_or_cone(self, p):
        dx, dy = p[0]-self.cx, p[1]-self.cy; d = math.hypot(dx, dy) or 1.0
        return (dx/d, dy/d)
    def boundary_points(self, window, n):
        (xmin,xmax),(ymin,ymax) = window
        M = 4000
        cand = []
        for i in range(M):
            t = 2*math.pi*i/M
            x, y = self.cx+self.R*math.cos(t), self.cy+self.R*math.sin(t)
            if xmin<=x<=xmax and ymin<=y<=ymax: cand.append((x,y))
        if not cand: return []
        return [cand[(i*len(cand))//n] for i in range(n)]  # even index over in-window arc = arc-length uniform
```

- [ ] **Step 4: Run** — `pytest tests/test_shapes.py tests/test_integrator_shared.py tests/test_patch2d.py -q` → PASS (patch2d confirms the `_integrate` refactor is exact).

- [ ] **Step 5: Commit**
```bash
git add src/cwm/continuous/envs.py src/cwm/continuous/shapes.py tests/test_shapes.py tests/test_integrator_shared.py
git commit -m "feat: shared integrator+inverse; Shape base with true signed distance; HalfPlane+Circle (arc-length, validated)"
```

---

### Task 2: Parabola (arc-length boundary, cubic projection)

**Files:** Modify `src/cwm/continuous/shapes.py`; Test `tests/test_shapes.py`.

**Interfaces:** `Parabola(c, R)` = region `x ≥ c + y²/(2R)`; `curvature_center = 1/R`, `curvature(y) = (1/R)/(1+(y/R)**2)**1.5`; `project_to_boundary` solves the exact cubic `y³/(2R²) + y·(1+(c−x₀)/R) − y₀ = 0` via `numpy.roots` and picks the global-min real root; `boundary_points` is resampled by cumulative arc length within the window. Limit `R→∞` ≡ `HalfPlane(c)`.

- [ ] **Step 1: Write failing tests (curvature, cubic projection vs brute force, arc-length uniformity)**

```python
# add to tests/test_shapes.py
from cwm.continuous.shapes import Parabola

def test_parabola_curvature():
    par = Parabola(3.0, 2.0)
    assert math.isclose(par.curvature_center, 0.5) and math.isclose(par.curvature(0.0), 0.5)
    assert par.curvature(4.0) < par.curvature(0.0)

def test_parabola_projection_matches_bruteforce_even_when_multimodal():
    par = Parabola(3.0, 0.5)  # small R → sharp curvature → multimodal distance for far points
    rng = random.Random(2)
    for _ in range(80):
        p = (rng.uniform(3, 12), rng.uniform(-5, 5))
        (px, py), _ = par.project_to_boundary(p)
        _, bd = _brute_project(par, p, WIN, n=6000)
        assert math.hypot(p[0]-px, p[1]-py) <= bd + 1e-2  # matches the GLOBAL minimum

def test_parabola_boundary_arclength_uniform_in_window():
    par = Parabola(3.0, 2.0)
    pts = par.boundary_points(WIN, 80)
    assert 2 <= len(pts) <= 80
    for x, y in pts: assert -8 <= x <= 14 and -6 <= y <= 6
    assert _consecutive_uniform(pts, tol=0.35)

def test_parabola_validation():
    import pytest
    with pytest.raises(ValueError): Parabola(3.0, 0.0)
```

- [ ] **Step 2: Run** → FAIL (ImportError).

- [ ] **Step 3: Implement**

```python
# add to src/cwm/continuous/shapes.py
import bisect
import numpy as np

@dataclass(frozen=True)
class Parabola(Shape):
    c: float; R: float
    def __post_init__(self):
        if self.R <= 0: raise ValueError("R>0 required")
    @property
    def curvature_center(self): return 1.0/self.R
    def curvature(self, y): return (1.0/self.R)/(1.0+(y/self.R)**2)**1.5
    def _bx(self, y): return self.c + y*y/(2.0*self.R)
    def implicit_value(self, p): return self._bx(p[1]) - p[0]
    def project_to_boundary(self, p):
        x0, y0 = p; R = self.R
        # d/dy[(x0-c-y^2/2R)^2 + (y0-y)^2] = 0  →  y^3/(2R^2) + y(1+(c-x0)/R) - y0 = 0
        coeffs = [1.0/(2*R*R), 0.0, 1.0 + (self.c - x0)/R, -y0]
        roots = np.roots(coeffs)
        reals = [r.real for r in roots if abs(r.imag) < 1e-9] or [r.real for r in roots]
        y = min(reals, key=lambda yy: (x0-self._bx(yy))**2 + (y0-yy)**2)
        return (self._bx(y), y), False
    def normal_or_cone(self, p):
        (_, y), _ = self.project_to_boundary(p)
        nx, ny = -1.0, y/self.R; d = math.hypot(nx, ny)
        return (nx/d, ny/d)
    def boundary_points(self, window, n):
        (xmin,xmax),(ymin,ymax) = window
        M = 8000
        pts = [(self._bx(ymin+(ymax-ymin)*i/(M-1)), ymin+(ymax-ymin)*i/(M-1)) for i in range(M)]
        infoc = [(x,y) for (x,y) in pts if xmin<=x<=xmax and ymin<=y<=ymax]
        if len(infoc) < 2: return infoc[:n]
        cum = [0.0]
        for k in range(1, len(infoc)):
            cum.append(cum[-1] + math.hypot(infoc[k][0]-infoc[k-1][0], infoc[k][1]-infoc[k-1][1]))
        total = cum[-1]
        out = []
        for i in range(n):
            target = total*i/(n-1) if n > 1 else 0.0
            k = min(bisect.bisect_left(cum, target), len(infoc)-1)
            out.append(infoc[k])
        return out
```

- [ ] **Step 4: Run** — `pytest tests/test_shapes.py -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(shapes): Parabola with cubic global-min projection + arc-length boundary"`.

---

### Task 3: Strip, Wedge, RegularPolygon (correct projection, in-window boundary, vertex cones)

**Files:** Modify `shapes.py`; Test `tests/test_shapes.py`.

**Interfaces:** `Strip(c,w)` (`c≤x≤c+w`); `Wedge(apex, half_angle, orient)` (two rays from the apex, opening along `orient`, `half_angle∈(0,π/2)`); `RegularPolygon(cx,cy,radius,k,orient)` (`k≥3`; `orient=0` face-on toward +x, `orient=π/k` vertex-on). Projection uses **segment/ray projection** (Wedge to its two rays + apex; polygon to its k edges). `normal_or_cone` returns a **list** of adjacent outward normals at a vertex, single on a face. Boundary points are clipped to the window and arc-length even along in-window edges.

- [ ] **Step 1: Write failing tests (projection vs brute force, vertex cone, in-window, validation)**

```python
# add to tests/test_shapes.py
from cwm.continuous.shapes import Strip, Wedge, RegularPolygon

def test_wedge_projects_to_a_ray_not_always_apex():
    w = Wedge(apex=(3.0, 0.0), half_angle=math.radians(30), orient=0.0)
    # a point beside one ray should project onto that ray, strictly farther than 0 from the apex
    p = (6.0, 1.0)
    (qx, qy), _ = w.project_to_boundary(p)
    assert math.hypot(qx-3.0, qy-0.0) > 0.5  # not the apex
    _, bd = _brute_project(w, p, WIN, n=4000)
    assert math.hypot(p[0]-qx, p[1]-qy) <= bd + 1e-2

def test_polygon_projection_and_vertex_cone_and_orientation():
    face = RegularPolygon(3.0, 0.0, 1.0, 4, 0.0)
    vert = RegularPolygon(3.0, 0.0, 1.0, 4, math.pi/4)
    assert face.n_facets == 4
    rng = random.Random(3)
    for _ in range(40):
        p = (rng.uniform(1,5), rng.uniform(-2,2))
        (qx,qy), _ = vert.project_to_boundary(p)
        _, bd = _brute_project(vert, p, WIN, n=4000)
        assert math.hypot(p[0]-qx, p[1]-qy) <= bd + 1e-2
    # a vertex point has a 2-normal cone
    vpt, _ = vert.project_to_boundary((3.0+5.0, 0.0))
    assert isinstance(vert.normal_or_cone(vpt), list) and len(vert.normal_or_cone(vpt)) == 2

def test_polygon_boundary_in_window():
    poly = RegularPolygon(3.0, 0.0, 1.0, 6, 0.0)
    for x,y in poly.boundary_points(WIN, 60):
        assert -8 <= x <= 14 and -6 <= y <= 6

def test_shape3_validation():
    import pytest
    with pytest.raises(ValueError): RegularPolygon(0,0,1,2,0.0)
    with pytest.raises(ValueError): Strip(3.0, 0.0)
    with pytest.raises(ValueError): Wedge((0,0), 0.0, 0.0)
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** (projection to edges/rays; `_project_segment` helper)

```python
# add to src/cwm/continuous/shapes.py
def _project_segment(p, a, b):
    abx, aby = b[0]-a[0], b[1]-a[1]
    denom = abx*abx + aby*aby or 1.0
    t = max(0.0, min(1.0, ((p[0]-a[0])*abx + (p[1]-a[1])*aby)/denom))
    q = (a[0]+t*abx, a[1]+t*aby)
    return q, math.hypot(p[0]-q[0], p[1]-q[1]), t

def _clip_ray_to_window(apex, direction, window):
    (xmin,xmax),(ymin,ymax) = window
    ts = [50.0]
    for comp, dc, lo, hi in ((0, direction[0], xmin, xmax), (1, direction[1], ymin, ymax)):
        if abs(dc) > 1e-12:
            for bound in (lo, hi):
                t = (bound - apex[comp]) / dc
                if t > 0: ts.append(t)
    tmax = min(ts)
    return (apex[0] + direction[0]*tmax, apex[1] + direction[1]*tmax)

@dataclass(frozen=True)
class Strip(Shape):
    c: float; w: float
    def __post_init__(self):
        if self.w <= 0: raise ValueError("w>0 required")
    def implicit_value(self, p): return max(self.c - p[0], p[0] - (self.c+self.w))
    def project_to_boundary(self, p):
        dl, dr = abs(p[0]-self.c), abs(p[0]-(self.c+self.w))
        return ((self.c, p[1]), False) if dl <= dr else ((self.c+self.w, p[1]), False)
    def normal_or_cone(self, p):
        return (-1.0,0.0) if abs(p[0]-self.c) <= abs(p[0]-(self.c+self.w)) else (1.0,0.0)
    def boundary_points(self, window, n):
        (_,_),(ymin,ymax) = window; h = n//2
        L = [(self.c, ymin+(ymax-ymin)*i/max(1,h-1)) for i in range(h)]
        Rr = [(self.c+self.w, ymin+(ymax-ymin)*i/max(1,n-h-1)) for i in range(n-h)]
        return L + Rr

def _regular_vertices(cx, cy, radius, k, orient):
    return [(cx + radius*math.cos(orient + math.pi/k + 2*math.pi*i/k),
             cy + radius*math.sin(orient + math.pi/k + 2*math.pi*i/k)) for i in range(k)]

@dataclass(frozen=True)
class RegularPolygon(Shape):
    cx: float; cy: float; radius: float; k: int; orient: float = 0.0
    def __post_init__(self):
        if self.k < 3: raise ValueError("k>=3 required")
        if self.radius <= 0: raise ValueError("radius>0 required")
    @property
    def n_facets(self): return self.k
    def _faces(self):
        apo = self.radius*math.cos(math.pi/self.k)
        out = []
        for i in range(self.k):
            ang = self.orient + 2*math.pi*i/self.k
            nx, ny = math.cos(ang), math.sin(ang)
            out.append((nx, ny, nx*self.cx + ny*self.cy + apo))  # n·p <= off inside
        return out
    def implicit_value(self, p):
        return max(nx*p[0]+ny*p[1]-off for nx,ny,off in self._faces())
    def project_to_boundary(self, p):
        verts = _regular_vertices(self.cx, self.cy, self.radius, self.k, self.orient)
        best, bd, atv = None, 1e18, False
        for i in range(self.k):
            q, d, t = _project_segment(p, verts[i], verts[(i+1)%self.k])
            if d < bd - 1e-12: bd, best, atv = d, q, (t < 1e-6 or t > 1-1e-6)
        return best, atv
    def normal_or_cone(self, p):
        act = [(nx,ny) for nx,ny,off in self._faces() if abs(nx*p[0]+ny*p[1]-off) < 1e-6]
        if len(act) >= 2: return act
        return act[0] if act else max(self._faces(), key=lambda f: f[0]*p[0]+f[1]*p[1]-f[2])[:2]
    def boundary_points(self, window, n):
        (xmin,xmax),(ymin,ymax) = window
        verts = _regular_vertices(self.cx, self.cy, self.radius, self.k, self.orient)
        out, per = [], max(1, n//self.k)
        for i in range(self.k):
            a, b = verts[i], verts[(i+1)%self.k]
            for j in range(per):
                t = j/per; x, y = a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])
                if xmin<=x<=xmax and ymin<=y<=ymax: out.append((x,y))
        return out[:n] if out else [verts[0]]

@dataclass(frozen=True)
class Wedge(Shape):
    apex: tuple; half_angle: float; orient: float = 0.0
    def __post_init__(self):
        if not (0.0 < self.half_angle < math.pi/2): raise ValueError("half_angle in (0,pi/2)")
    def _edges(self):  # two unit ray directions from the apex bounding the opening
        return [(math.cos(self.orient+s*self.half_angle), math.sin(self.orient+s*self.half_angle)) for s in (+1.0,-1.0)]
    def _faces(self):
        faces = []
        for dx, dy in self._edges():
            nx, ny = -dy, dx  # inward/outward normal to the ray; orient sign fixed so region is between rays
            # ensure normal points OUT of the wedge: flip if it points toward the opening axis
            axis = (math.cos(self.orient), math.sin(self.orient))
            if nx*axis[0] + ny*axis[1] > 0: nx, ny = -nx, -ny
            faces.append((nx, ny, nx*self.apex[0]+ny*self.apex[1]))
        return faces
    def implicit_value(self, p):
        return max(nx*p[0]+ny*p[1]-off for nx,ny,off in self._faces())
    def project_to_boundary(self, p, window=((-8.0,14.0),(-6.0,6.0))):
        cands = [(self.apex, math.hypot(p[0]-self.apex[0], p[1]-self.apex[1]), True)]
        for d in self._edges():
            far = _clip_ray_to_window(self.apex, d, window)
            q, dist, _ = _project_segment(p, self.apex, far)
            cands.append((q, dist, False))
        cands.sort(key=lambda c: c[1])
        best = cands[0]
        multi = len(cands) > 1 and abs(cands[0][1]-cands[1][1]) < 1e-9
        return best[0], (best[2] or multi)
    def normal_or_cone(self, p):
        act = [(nx,ny) for nx,ny,off in self._faces() if abs(nx*p[0]+ny*p[1]-off) < 1e-6]
        return act if len(act) >= 2 else (act[0] if act else self._faces()[0][:2])
    def boundary_points(self, window, n):
        out = []
        for d in self._edges():
            far = _clip_ray_to_window(self.apex, d, window)
            for j in range(n//2):
                t = j/max(1, n//2-1); x, y = self.apex[0]+t*(far[0]-self.apex[0]), self.apex[1]+t*(far[1]-self.apex[1])
                out.append((x, y))
        return out[:n] if out else [self.apex]
```

- [ ] **Step 4: Run** — `pytest tests/test_shapes.py -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(shapes): Strip/Wedge/RegularPolygon — segment projection, in-window boundary, vertex cones, validation"`.

---

### Task 4: `ShapeField2D` (shared integrator, exact-equivalence test)

**Files:** Modify `src/cwm/continuous/envs.py`; Test `tests/test_shape_field.py`.

**Interfaces:** `ShapeField2D(shape=None, ...)` with PatchField2D's constants; `_integrate` calls `integrate_2d`; `contact`, `step` (freeze at previous position on contact). `blind_of` → `shape=None`. Must be **exactly equivalent** to `PatchField2D` with a single disc when `shape=Circle(c)` matches a patch.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_shape_field.py
import math, random
from cwm.continuous.envs import ShapeField2D, PatchField2D, blind_of
from cwm.continuous.shapes import Circle, HalfPlane

def test_shapefield_exactly_equivalent_to_patchfield_single_disc():
    patch = PatchField2D(p1=(3.0,0.0), p2=None, R=1.0)
    shape = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    rng = random.Random(0)
    for _ in range(1000):
        s = (rng.uniform(-8,14), rng.uniform(-6,6), rng.uniform(-4,4), rng.uniform(-4,4)); a = rng.uniform(-1,1)
        assert patch.step(s,a) == shape.step(s,a)

def test_shapefield_freeze_and_blind():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    s2, _, contact = env.step((2.0,0.0,3.0,0.0), 0.0)
    assert contact and s2 == (2.0,0.0,0.0,0.0)
    assert blind_of(env).shape is None
    assert blind_of(env).step((2.9,0.0,3.0,0.0), 0.0)[2] is False
```

- [ ] **Step 2: Run** → FAIL. **Step 3:** Implement `ShapeField2D` as in rev.1 Task 4 but with `_integrate` delegating to `integrate_2d`, and add the `isinstance(env, ShapeField2D): return replace(env, shape=None)` branch to `blind_of`. **Step 4:** `pytest tests/test_shape_field.py tests/test_instruments.py tests/test_continuous_contract.py -q` → PASS (golden intact). **Step 5:** `git commit -m "feat(envs): ShapeField2D via shared integrator, exact-equivalence tested vs PatchField2D"`.

---

### Task 5: `SHAPE2D_SPEC` — integrator-inverted probes, per-family full-arm serialization

**Files:** Modify `src/cwm/continuous/instruments.py`; Test `tests/test_shape_field.py`.

**Interfaces:** `SHAPE2D_SPEC`; `spec_for(ShapeField2D)→SHAPE2D_SPEC`. Incomplete arm geometry-agnostic (byte-identical across shapes). Full arm serializes the shape **per family with its exact mathematical predicate** (`describe_shape(shape)->str`), not `repr`. `mode_probes(env)` builds each probe by choosing an interior target point (a boundary point pushed inward along the inward normal — at a vertex, the normalized sum of the cone normals) and **inverting the integrator**, so `env.contact(state, action)` holds for every probe.

- [ ] **Step 1: Write failing tests (every probe fires; incomplete arm agnostic; full arm has the predicate)**

```python
# add to tests/test_shape_field.py
from cwm.continuous.instruments import spec_for, describe_shape
from cwm.continuous.contract import build_contract
from cwm.continuous.shapes import Circle, Parabola, RegularPolygon

def test_incomplete_arm_is_geometry_agnostic():
    a = build_contract(ShapeField2D(shape=Circle(3.0,0.0,1.0)), include_mode=False)
    b = build_contract(ShapeField2D(shape=Parabola(3.0,2.0)), include_mode=False)
    assert a == b and "radius" not in a.lower() and "parabola" not in a.lower()

def test_full_arm_has_exact_predicate():
    full = build_contract(ShapeField2D(shape=Circle(3.0,0.0,1.0)), include_mode=True)
    assert "(x - 3.0)**2 + (y - 0.0)**2 <= 1.0**2" in full  # exact math, not repr

def test_every_probe_fires_the_mode():
    for shp in (Circle(3.0,0.0,1.0), Parabola(3.0,2.0), RegularPolygon(3.0,0.0,1.0,5,math.pi/5)):
        env = ShapeField2D(shape=shp)
        probes = spec_for(env).mode_probes(env)["mode"]
        assert len(probes) >= 8
        for (state, action) in probes:
            assert env.contact(state, action), f"probe must fire for {shp}"
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** Add `describe_shape(shape)` (per-family exact predicate string: Circle → `"(x - {cx})**2 + (y - {cy})**2 <= {R}**2"`, Parabola → `"x >= {c} + y**2/(2*{R})"`, HalfPlane → `"x >= {c}"`, Strip/Wedge/RegularPolygon → their exact half-plane conjunctions). `_shape2d_probes` builds interior targets and inverts the integrator:

```python
def _shape2d_probes(env):
    box = ((-8.0,14.0),(-6.0,6.0)); shp = env.shape
    probes = []
    for (bx, by) in shp.boundary_points(box, 12):
        n = shp.normal_or_cone((bx, by))
        if isinstance(n, list):  # vertex: inward = -(normalized sum of cone normals)
            sx = sum(c[0] for c in n); sy = sum(c[1] for c in n); m = math.hypot(sx, sy) or 1.0
            inward = (-sx/m, -sy/m)
        else:
            inward = (-n[0], -n[1])
        target = (bx + 0.05*inward[0], by + 0.05*inward[1])  # strictly interior
        if not shp.contains(target):
            target = (bx + 0.2*inward[0], by + 0.2*inward[1])
        from .envs import invert_integrator
        state = invert_integrator(target, 0.0, 0.0, 0.0, env.dt, env.gain, env.drag, env.a_max)
        probes.append((state, 0.0))
    return {"mode": probes}
```

Wire `SHAPE2D_SPEC` (reuse `_patch2d_constants_block` extracted byte-safely from `_patch2d_rules_text`) and `spec_for`. **Step 4:** `pytest tests/test_shape_field.py tests/test_patch2d.py tests/test_instruments.py -q` → PASS. **Step 5:** `git commit -m "feat(instruments): SHAPE2D_SPEC — integrator-inverted probes (all fire), per-family predicate serialization"`.

---

### Task 6: Primary state–action disagreement (signed-distance strata, inverted band, real planner)

**Files:** Create `src/cwm/continuous/metrics_geom.py`; Test `tests/test_metrics_geom.py`.

**Interfaces:** `stratified_probes(env, box, n_per, rng, band_d, planner_queries) -> dict` with strata `{"inside","outside","band","uniform","planner"}`. **band** is built from boundary points displaced ±`band_d` along the normal, then the integrator is inverted so the endpoint lands there (guaranteeing the intended truth-contact label); distance uses `env.shape.signed_distance` (a **true length**, comparable across families). **planner** uses supplied `(state, action)` queries recorded from a real MPC rollout (`planner_queries`), not random zeros. Raises `RuntimeError` if a stratum can't be filled to `n_per` (never silently short). `disagreement_scores(truth_env, model_step, probes) -> dict` returns per-stratum balanced disagreement + precision/recall/fpr; **primary = `band`**.

- [ ] **Step 1: Write failing tests (identity=0; blind>0 in band; strata full; band label correct)**

```python
# tests/test_metrics_geom.py
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous import mpc
from cwm.continuous.metrics_geom import stratified_probes, disagreement_scores
BOX = ((-8.0,14.0),(-6.0,6.0))

def _planner_queries(env, n, seed=0):
    rng = random.Random(seed); out = []
    s = env.initial_state(rng)
    for _ in range(n):
        a = mpc.plan(env, s, rng, horizon=20, n_samples=64, block=10)
        out.append((s, a)); s = env.step(s, a)[0]
    return out

def test_band_labels_are_correct_and_full():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    pq = _planner_queries(env, 30)
    pr = stratified_probes(env, BOX, n_per=20, rng=random.Random(0), band_d=0.15, planner_queries=pq)
    assert set(pr) == {"inside","outside","band","uniform","planner"}
    assert all(len(v) == 20 for v in pr.values())
    # every "inside"-labeled probe truly contacts, every "outside" does not
    assert all(env.contact(s,a) for (s,a) in pr["inside"])
    assert all(not env.contact(s,a) for (s,a) in pr["outside"])

def test_identity_zero_blind_positive_in_band():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0)); blind = ShapeField2D(shape=None)
    pq = _planner_queries(env, 30)
    pr = stratified_probes(env, BOX, 20, random.Random(0), 0.15, pq)
    assert disagreement_scores(env, lambda s,a: env.step(s,a)[0], pr)["band"]["disagreement"] == 0.0
    assert disagreement_scores(env, lambda s,a: blind.step(s,a)[0], pr)["band"]["disagreement"] > 0.2
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** — band via boundary displacement + `invert_integrator`; inside/outside via inverted targets pushed inward/outward until `env.contact` matches the intended label; `uniform` accepted only if the endpoint is in-box; `planner` = the supplied queries (cycled if fewer than `n_per`); `RuntimeError` if any stratum underfills after a bounded number of tries; `model_contact` detected by the freeze signature (zero velocity + unchanged position). **Step 4:** PASS. **Step 5:** `git commit -m "feat(metrics): signed-distance strata via integrator inversion; band primary; real planner queries"`.

---

### Task 7: Endpoint-space IoU + preimage-invariance (batched), boundary_of_set

**Files:** Modify `metrics_geom.py`; Test `tests/test_metrics_geom.py`.

**Interfaces:** `forbidden_mask(model_step, box, grid_n, vx, vy, action=0.0) -> np.ndarray[bool]` — for each **endpoint** grid cell `p`, build the previous state `invert_integrator(p, vx, vy, action, ...)`, run `model_step`, mark cells whose result froze at that previous state (the mode fired for endpoint `p`). `preimage_invariant(model_step, box, grid_n, velocity_samples, jaccard_tol=0.98)`; `iou_vs_truth(truth_env, model_step, box, grid_n, velocity_samples)->{"iou","class","grid_n"}` (IoU `None`, class `non_positional` if not invariant); `boundary_of_set(mask, box)->list[tuple]` (edge cells via a marching-squares-style neighbor check). Grid eval is vectorized with numpy; a single sandbox call returns the mask for gate-failing artifacts (Task 11).

- [ ] **Step 1: Write failing tests (true guard is positional & invariant; velocity guard flagged non-positional; endpoint semantics)**

```python
# add to tests/test_metrics_geom.py
from cwm.continuous.metrics_geom import iou_vs_truth, forbidden_mask
from cwm.continuous.envs import ShapeField2D, integrate_2d, invert_integrator

def test_true_guard_is_positional_and_invariant_across_velocity():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    res = iou_vs_truth(env, lambda s,a: env.step(s,a)[0], BOX, grid_n=128,
                       velocity_samples=[(3.0,0.0),(0.0,3.0),(-2.0,1.0)])
    assert res["class"] == "positional" and res["iou"] > 0.97  # endpoint-space, so velocity-invariant

def test_velocity_guard_is_non_positional():
    def vel_guard(s, a):
        x2,y2,vx2,vy2 = integrate_2d(s,a,0.1,3.0,0.3,1.0)
        return (s[0],s[1],0.0,0.0) if vx2 > 2.5 else (x2,y2,vx2,vy2)
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    res = iou_vs_truth(env, vel_guard, BOX, 128, [(3.0,0.0),(-3.0,0.0),(0.0,3.0)])
    assert res["class"] == "non_positional" and res["iou"] is None
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** the endpoint-space mask via `invert_integrator` per cell (vectorized: build all previous states with numpy, but call `model_step` per cell in a tight loop for in-process accepted code; document the single-sandbox-call-returns-mask path for gate-failing code), plus `preimage_invariant`, `iou_vs_truth`, `boundary_of_set`. **Step 4:** PASS. **Step 5:** `git commit -m "feat(metrics): endpoint-space IoU via integrator inversion, preimage-invariance gate, boundary_of_set"`.

---

### Task 8: Symmetric boundary distance (uses correct arc-length samplers + boundary_of_set)

**Files:** Modify `metrics_geom.py`; Test `tests/test_metrics_geom.py`.

**Interfaces:** `symmetric_boundary_distance(shape_true, model_boundary_pts, box, n_samples, diam_norm) -> {"hausdorff","p95","mean"}`, where `model_boundary_pts = boundary_of_set(forbidden_mask(...), box)` for a positional artifact and `shape_true.boundary_points` (now truly arc-length uniform) for truth. Normalized by `diam_norm`.

- [ ] **Step 1..5** as rev.1 Task 8 but the test also asserts the truth-vs-truth distance is ~0 using `boundary_of_set(forbidden_mask(truth_step,...))` (closing the loop with the corrected samplers), and the shifted-circle case uses `boundary_of_set`, not raw shape points. Commit `git commit -m "feat(metrics): symmetric boundary Hausdorff/p95/mean over corrected samplers + boundary_of_set"`.

---

### Task 9: Operational oracle (all families) + tangent baseline; `S` left uncertified

**Files:** Create `src/cwm/continuous/oracle.py`; Test `tests/test_oracle.py`.

**Interfaces:** `fit_family(family, labeled_endpoints, box) -> Shape|None` for **circle, parabola, halfplane, strip, wedge, polygon** (least-violation over a bounded, family-appropriate parameter grid + local polish; bounds are the box, not the observed range, so a true `R=1` circle is reachable); `operational_reconstructs(family, labeled, box, iou_thresh) -> bool` (does the best fit match the labels' implied region on the box within `iou_thresh`); `tangent_baseline(contacts) -> HalfPlane` — **best half-plane of any orientation** via PCA on the contact points (returns a general `HalfPlaneGeneral(nx,ny,off)`), quantifying "collapse to the tangent". **Sufficiency `S` is NOT certified in Phase A**: `oracle.py` exposes only the operational estimator and a `SUFFICIENCY_UNCERTIFIED = True` sentinel; the conservative version-space upper bound is Phase B.

- [ ] **Step 1: Write failing tests (recovers the true circle; oracle works for every family; tangent is oriented)**

```python
# tests/test_oracle.py
import math, random
from cwm.continuous.shapes import Circle, Parabola, RegularPolygon
from cwm.continuous.oracle import fit_family, operational_reconstructs, tangent_baseline, SUFFICIENCY_UNCERTIFIED
BOX = ((-8.0,14.0),(-6.0,6.0))

def _labeled(shape, seed=0, n=1500):
    rng = random.Random(seed)
    pts = [(rng.uniform(0,6), rng.uniform(-3,3)) for _ in range(n)]
    return [(p, shape.contains(p)) for p in pts]

def test_fit_recovers_true_circle_R1():
    fit = fit_family("circle", _labeled(Circle(3.0,0.0,1.0)), BOX)
    assert abs(fit.cx-3.0) < 0.15 and abs(fit.R-1.0) < 0.15  # R=1 is reachable (bounds not from observed range)

def test_operational_oracle_all_families():
    for fam, shp in (("circle", Circle(3.0,0.0,1.0)), ("parabola", Parabola(3.0,2.0)),
                     ("polygon", RegularPolygon(3.0,0.0,1.0,5,0.0))):
        assert operational_reconstructs(fam, _labeled(shp), BOX, iou_thresh=0.85)

def test_tangent_baseline_is_oriented():
    contacts = [(3.0 + 0.3*i, 0.3*i) for i in range(-3, 4)]  # a diagonal contact arc
    hp = tangent_baseline(contacts)
    assert abs(hp.nx) < 0.99  # not axis-aligned; PCA found the diagonal

def test_sufficiency_uncertified_sentinel():
    assert SUFFICIENCY_UNCERTIFIED is True
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** family fits with box-based bounds + coordinate polish, `operational_reconstructs` via IoU on the box, PCA tangent (`HalfPlaneGeneral`), and the sentinel. **Step 4:** PASS. **Step 5:** `git commit -m "feat(oracle): operational per-family fits + oriented tangent baseline; S left uncertified in Phase A"`.

---

### Task 10: Guard-only AST/MDL features

**Files:** Create `src/cwm/continuous/program_features.py`; Test `tests/test_program_features.py`.

**Interfaces:** `guard_features(code, integrator_reward_ast) -> dict` — parses `code`, **isolates the guard/branch conditions** (the `test` expressions of `If`/`IfExp` and boolean ops in the added mode logic) and computes features on THOSE ONLY, subtracting the shared integrator/reward AST so the integrator's `var*const` products don't inflate `poly_degree`. Keys: `n_comparisons, boolean_depth, n_literals, guard_poly_degree, uses_hypot_sqrt, n_conjuncts, n_disjuncts, guard_ast_size, approx_mdl, invalid`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_program_features.py
from cwm.continuous.program_features import guard_features

INTEG = "vx2 = vx + (gain*math.cos(phi) - drag*vx)*dt"  # representative shared-code fragment

def test_guard_degree_excludes_integrator():
    # a purely linear guard must read as degree 1 even though the integrator multiplies vars
    lin = "def step(s,a):\n    x2=s[0]+s[2]*0.1\n    return [8.0,0.0] if x2>=8.0 else [x2,s[1],s[2],s[3]]\n"
    assert guard_features(lin, INTEG)["guard_poly_degree"] == 1
    quad = "def step(s,a):\n    x2=s[0]+s[2]*0.1\n    return list(s) if (x2-3)**2+s[1]**2<=1 else [x2,s[1],s[2],s[3]]\n"
    assert guard_features(quad, INTEG)["guard_poly_degree"] >= 2

def test_invalid_flag():
    assert guard_features("def step(:\n", INTEG)["invalid"] is True
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** — parse, collect `If.test`/`IfExp.test`/comparison nodes reachable from branch tests, compute features on that sub-AST only; degree from `Pow`/`Mult` **within guard tests**. **Step 4:** PASS. **Step 5:** `git commit -m "feat(program-features): guard-only AST/MDL (integrator excluded)"`.

---

### Task 11: Sandbox triple-classification + sandboxed dynamic metrics

**Files:** Create `src/cwm/continuous/artifact_class.py`; Test `tests/test_artifact_class.py`.

**Interfaces:** `classify_artifact(code, transitions, eps) -> {"class","gate_accuracy","features"}` with class **`invalid`** when the code is unparseable OR lacks a callable `step`/`reward` OR raises on a trivial call **in the sandbox** (not `gate_failing`); `gate_failing` when it runs but gate accuracy `<1`; `gate_passing` at `1.0`. `dynamic_metrics_sandboxed(code, box, grid_n, velocity_samples) -> mask-array` — runs the artifact's `step` over the supplied grid **in a single sandbox subprocess** returning the forbidden mask, so gate-failing artifacts are never exec'd in-process. Executability/step-reward presence is checked in the sandbox.

- [ ] **Step 1: Write failing tests (exact class, invalid vs gate_failing distinguished, sandbox mask)**

```python
# tests/test_artifact_class.py
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.artifact_class import classify_artifact, dynamic_metrics_sandboxed

def _sample(seed=0): return collect_transitions(ShapeField2D(shape=Circle(3.0,0.0,1.0)), n_rollouts=5, seed=seed)

def test_missing_step_is_invalid_not_gate_failing():
    assert classify_artifact("def reward(s):\n    return 0.0\n", _sample(), 1e-9)["class"] == "invalid"

def test_valid_wrong_artifact_is_exactly_gate_failing():
    bad = "def step(s,a):\n    return list(s)\ndef reward(s):\n    return 0.0\n"
    assert classify_artifact(bad, _sample(), 1e-9)["class"] == "gate_failing"

def test_dynamic_mask_from_sandbox():
    circ = "import math\ndef step(s,a):\n    x2=s[0]+ (s[2]+ (3.0*math.cos(math.pi*max(-1,min(1,a))/1.0)-0.3*s[2])*0.1)*0.1\n    return list(s)\ndef reward(s):\n    return 0.0\n"
    mask = dynamic_metrics_sandboxed(circ, ((-8.0,14.0),(-6.0,6.0)), grid_n=32, velocity_samples=[(3.0,0.0)])
    assert mask.shape == (32, 32)
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** using the existing sandbox runner (`contract.run_in_sandbox`): a preflight that checks parse + `step`/`reward` presence + a trivial call → `invalid`; else `contract_accuracy` for `gate_failing`/`gate_passing`; `dynamic_metrics_sandboxed` writes a tiny driver that loops the grid inside the subprocess and returns the mask (numpy `.npy` via stdout/temile). **Step 4:** PASS. **Step 5:** `git commit -m "feat(artifact-class): invalid vs gate_failing distinguished; sandboxed dynamic mask"`.

---

### Task 12: Evidence-dose — fixed 40-example transcript cap, structured failures, refinement-integrated

**Files:** Create `src/cwm/continuous/evidence_dose.py`; Test `tests/test_evidence_dose.py`.

**Interfaces:** `build_dose_sample(transitions, m, span, rng) -> (examples, allowed_index_set, meta)` — returns exactly **40 examples = m positives + m distinct matched negatives + (40−2m) background**, where matched negatives are chosen by **nearest boundary-normal distance to each kept positive's endpoint** (no reuse), `span∈{"small","large"}` selects positives within a small vs large angular arc of the boundary, and `allowed_index_set` are the indices the LLM is allowed to be corrected on. `refine_capped(provider, model, contract, code, examples, allowed_index_set, eps, max_iters=5) -> RefineResult` — a refinement loop that, on every iteration, **filters gate failures to `allowed_index_set`**, presents background as "controlled observations" (never as failures), and stops as `evidence_capped_failure` if all remaining failures are outside the allowed set. `is_evidence_capped_failure(failure_indices, allowed_index_set) -> bool`.

- [ ] **Step 1: Write failing tests (exactly 40, m positives, distinct negatives, structured index membership, span)**

```python
# tests/test_evidence_dose.py
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.evidence_dose import build_dose_sample, is_evidence_capped_failure

def test_fixed_size_and_distinct_negatives():
    tr = collect_transitions(ShapeField2D(shape=Circle(3.0,0.0,1.0)), n_rollouts=60, seed=0)
    ex, allowed, meta = build_dose_sample(tr, m=8, span="large", rng=random.Random(0))
    assert len(ex) == 40 and meta["n_positive"] == 8 and meta["n_negative"] == 8
    neg_ids = [id(e) for e in ex if not e["contact"]][:8]
    assert len(set(neg_ids)) == len(neg_ids)  # no negative reused

def test_capped_failure_uses_structured_indices():
    assert is_evidence_capped_failure(failure_indices={11, 12}, allowed_index_set={0,1,2}) is True
    assert is_evidence_capped_failure(failure_indices={1, 12}, allowed_index_set={0,1,2}) is False
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** — fixed-40 construction, endpoint-normal matched negatives without reuse, span selection by boundary arc, structured `(index)` failures (extend `contract_accuracy` to return the failing transition indices, or wrap it), and `refine_capped` integrating the allowed-set filter each iteration. **Step 4:** PASS. **Step 5:** `git commit -m "feat(evidence-dose): fixed-40 transcript cap, matched distinct negatives, structured-index refinement"`.

---

### Task 13: Calibration prototype + strict anti-placeholder validator (the Phase-A/B gate)

**Files:** Create `scripts/calibrate_shape2d.py`, `src/cwm/continuous/calibration.py` (the validator), `results/shape2d_calibration.json`; Test `tests/test_calibration.py`.

**Interfaces:** `validate_calibration_artifact(art) -> list[str]` (returns a list of problems; empty = valid) that **rejects** any `None`/`NaN`/empty list, missing per-cell rarity CI, `grid_converged` not backed by a measured `grid_delta<0.01`, rarity outside tolerance, a cell whose blind planner is **not** exploited (needs `play_cost_blind ≥ 0.8` from truth/blind/random **episodes**, not a single `mpc.plan` call), out-of-box clipping fraction over a bound, or a `repaired_threshold` whose `source != "truth_oracle_fullarm_griderror"`. `calibrate_shape2d.py` measures each field and writes the JSON. `rarity` = **fraction of rollouts that contain a contact** (`sum(any-contact-per-rollout)/n_rollouts`), with a Wilson CI on an independent seed stream.

- [ ] **Step 1: Write failing tests — the validator REJECTS a placeholder, ACCEPTS a filled artifact**

```python
# tests/test_calibration.py
import json, subprocess, sys, math
from cwm.continuous.calibration import validate_calibration_artifact

def test_validator_rejects_placeholder():
    placeholder = {"box": [[-8,14],[-6,6]], "grid_n": 256, "grid_converged": True, "grid_delta": None,
                   "tau_S": 0.1, "delta": None, "cells": [], "rarity_target": 0.15,
                   "repaired_threshold": {"source": "incomplete_anchor"}, "frac_planner_outside_box": 0.0}
    problems = validate_calibration_artifact(placeholder)
    assert any("cells" in p for p in problems)
    assert any("delta" in p for p in problems)
    assert any("grid" in p.lower() for p in problems)
    assert any("source" in p for p in problems)

def test_validator_accepts_filled():
    good = {"box": [[-8,14],[-6,6]], "grid_n": 256, "grid_converged": True, "grid_delta": 0.004,
            "tau_S": 0.1, "delta": 0.12, "rarity_target": 0.15, "frac_planner_outside_box": 0.01,
            "repaired_threshold": {"band_disagreement": 0.05, "fpr": 0.05, "source": "truth_oracle_fullarm_griderror"},
            "cells": [{"family": "circle", "R": 1.0, "offset": 3.0, "rarity": 0.15,
                       "rarity_ci": [0.12, 0.18], "play_cost_blind": 0.99}]}
    assert validate_calibration_artifact(good) == []

def test_calibration_runs_and_is_valid(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, "scripts/calibrate_shape2d.py", "--quick", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert validate_calibration_artifact(json.loads(out.read_text())) == []
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** the validator first (pure function, fully covered by the two unit tests) — it enforces every rejection above and NaN checks via `math.isnan`. Then `calibrate_shape2d.py` measures: per-family offset achieving `rarity_target` (fraction-of-rollouts, Wilson CI on an independent seed stream), the `256²`↔`512²` `grid_delta`, `play_cost_blind` from truth/blind/random **episodes** per cell, `delta` (median normal-bracket width), `frac_planner_outside_box`, and sets `repaired_threshold.source="truth_oracle_fullarm_griderror"`. `--quick` shrinks rollout/seed counts but STILL fills every field (so the validator passes on a real, if small, measurement — never a hardcoded stub). **Step 4:** `pytest tests/test_calibration.py -q` → PASS; then `python scripts/calibrate_shape2d.py` for the full artifact. **Step 5:** `git commit -m "feat(calibration): measured artifact + strict anti-placeholder validator (the Phase-A/B gate)"`.

---

## Phase-A completion gate

After Task 13, `results/shape2d_calibration.json` exists, `validate_calibration_artifact` returns `[]` on it, and `pytest -q` is green (cart golden included). **This validated artifact is the GO gate for Phase B** (the ~520 Azure syntheses). Phase B — a separate plan — builds the crash-safe checkpoint/resume harness (does not exist today), the sweep driver reading the frozen artifact, the V_transcript logging + three-oracle attribution (with the conservative version-space upper bound that certifies `S`, deferred from Phase A), the evidence-dose runs, the pre-registered adaptive densification (crossover-CI for the curvature sweep, score/interaction-CI for dose & composition), the bounded-outcome statistics (zero/one-inflated beta; logistic for `repaired`), and the paper integration. Do NOT start Phase B until the artifact validates and is reviewed.
