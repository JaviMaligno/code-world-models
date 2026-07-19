# Repair-vs-Geometry — Phase A (infrastructure + calibration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build every apparatus piece for the repair-vs-geometry experiment and produce a frozen, strictly-validated calibration artifact — the gate that authorizes the ~520 Azure syntheses (Phase B, separate plan).

**Architecture:** A new `Shape` abstraction (unbounded-safe, with correct arc-length sampling, true signed distance, and multimodal projection) drives a new single-mode 2D instrument `ShapeField2D` that reuses a shared integrator with `PatchField2D`. Probes, band strata, and the IoU forbidden set are all built by **inverting the integrator** (endpoint→previous-state), never by guessing. New metric/analysis modules sit beside the existing pipeline. A calibration prototype writes a versioned JSON, and a strict validator makes an unfilled placeholder impossible to pass.

**Tech Stack:** Python 3.12, pytest (`pythonpath=["src"]`, `testpaths=["tests"]`), numpy (dep), stdlib `ast`, `bisect`. No new heavy deps.

## Rev history

rev. 2 rewrote Tasks 1–3, 5–7, 9, 11–13 after an expert NO-GO on rev. 1 (fake arc-length, unimodal projection, non-comparable tube widths, preimage-translated IoU, lower-bound-only version-space, un-capped transcript, key-presence-only calibration gate).

rev. 3 (this file) fixes the near-GO review of rev. 2: (1) oracle can't compute IoU from point labels alone → `operational_reconstructs_vs_truth(...,truth_shape,...)` + `operational_heldout_accuracy(...)`, and `tangent_baseline(labeled)` is a classifying half-plane (positives+negatives give the side/offset); (2) evidence dose gains `env`, `gate_transitions`, `source_index`, and an initial controlled-prompt builder; (3) calibration validator enforces an exact `EXPECTED_CELL_IDS` manifest, `sufficiency={certified:false,tau_s:null}`, distinct seed streams, per-parameter provenance, per-cell grid_delta, and splits smoke (`--quick`) from strict scientific validation; (4) Wedge projects onto the infinite ray; plus parabola equidistant-`multi`, disconnected-arc component handling, full-perimeter polygon resampling, all-family oracle test, base64-JSON sandbox mask, reset-condition-preferring AST, and grid-cell-bounded boundary-distance assertions.

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

def _resample_components(ordered_pts, n, gap_tol):
    """Split an ordered in-window point list into arc components at gaps > gap_tol,
    then resample n points by arc length, allocated across components proportional
    to their length. Never accumulates distance across the gap between two arcs."""
    if not ordered_pts:
        return []
    comps, cur = [], [ordered_pts[0]]
    for k in range(1, len(ordered_pts)):
        if math.hypot(ordered_pts[k][0]-ordered_pts[k-1][0], ordered_pts[k][1]-ordered_pts[k-1][1]) > gap_tol:
            comps.append(cur); cur = []
        cur.append(ordered_pts[k])
    comps.append(cur)
    lengths = []
    for comp in comps:
        L = sum(math.hypot(comp[i+1][0]-comp[i][0], comp[i+1][1]-comp[i][1]) for i in range(len(comp)-1))
        lengths.append(max(L, 1e-12))
    total = sum(lengths)
    out = []
    for comp, L in zip(comps, lengths):
        share = max(1, round(n * L / total))
        out.extend(comp[(i*len(comp))//share] for i in range(share))
    return out[:n] if len(out) >= n else out


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
        # components: a window may clip the circle into two disconnected arcs
        gap = 3.0 * (2*math.pi*self.R/M)
        return _resample_components(cand, n, gap_tol=gap)
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
        ranked = sorted(((x0-self._bx(yy))**2 + (y0-yy)**2, yy) for yy in reals)
        y = ranked[0][1]
        multi = len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) < 1e-9  # two equidistant minima
        return (self._bx(y), y), multi
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
        step = math.hypot(infoc[1][0]-infoc[0][0], infoc[1][1]-infoc[0][1])
        return _resample_components(infoc, n, gap_tol=max(3.0*step, 0.1))  # x-clip can split into arcs
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
        # dense full-perimeter trace, filter to window, resample by arc length (handles n not divisible by k)
        M = max(20*n, 400); dense = []
        for i in range(self.k):
            a, b = verts[i], verts[(i+1)%self.k]
            for j in range(M//self.k):
                t = j/(M//self.k); dense.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
        infoc = [pp for pp in dense if xmin<=pp[0]<=xmax and ymin<=pp[1]<=ymax]
        if not infoc: return [verts[0]]
        edge = math.hypot(verts[1][0]-verts[0][0], verts[1][1]-verts[0][1]) / (M//self.k)
        return _resample_components(infoc, n, gap_tol=max(3.0*edge, 0.1))

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
    def project_to_boundary(self, p):
        # project onto each INFINITE ray from the apex (t>=0), plus the apex; the window is NOT used here
        cands = [(self.apex, math.hypot(p[0]-self.apex[0], p[1]-self.apex[1]), True)]
        for d in self._edges():
            t = max(0.0, (p[0]-self.apex[0])*d[0] + (p[1]-self.apex[1])*d[1])
            q = (self.apex[0]+t*d[0], self.apex[1]+t*d[1])
            cands.append((q, math.hypot(p[0]-q[0], p[1]-q[1]), t < 1e-9))
        cands.sort(key=lambda c: c[1])
        multi = len(cands) > 1 and abs(cands[0][1]-cands[1][1]) < 1e-9
        return cands[0][0], (cands[0][2] or multi)
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

- [ ] **Step 1..5** as rev.1 Task 8 but the test asserts truth-vs-`boundary_of_set(forbidden_mask(truth_step,...))` distance is **below a grid-cell-derived bound** (`≈ 1.5 × cell_diagonal`, NOT exact zero — the marching-squares boundary is discretized), and the shifted-circle case uses `boundary_of_set`, not raw shape points. Commit `git commit -m "feat(metrics): symmetric boundary Hausdorff/p95/mean over corrected samplers + boundary_of_set"`.

---

### Task 9: Operational oracle (all families) + tangent baseline; `S` left uncertified

**Files:** Create `src/cwm/continuous/oracle.py`; Test `tests/test_oracle.py`.

**Interfaces:** `fit_family(family, labeled_endpoints, box) -> Shape|None` for **circle, parabola, halfplane, strip, wedge, polygon** (least-violation over a bounded, family-appropriate parameter grid + local polish; bounds are the box, not the observed range, so a true `R=1` circle is reachable). Because point labels alone do NOT determine the true region, the oracle exposes **two honest evaluators, never IoU-vs-implied-region**: `operational_reconstructs_vs_truth(family, labeled, truth_shape, box, iou_thresh) -> bool` (IoU of the fit against the KNOWN experiment truth on the box — valid only in calibration where `truth_shape` is known) and `operational_heldout_accuracy(family, train_labeled, test_labeled) -> float` (balanced accuracy of the fit on an independent labeled test set — the runtime-usable estimator). `tangent_baseline(labeled) -> HalfPlaneGeneral` — the best **classifying** half-plane fit to inside/outside-labeled endpoints (positives AND negatives; PCA on the points only *initializes* the orientation, then the offset and the interior side are chosen to minimize misclassification — contacts alone can't give the side or offset). **Sufficiency `S` is NOT certified in Phase A**: `oracle.py` exposes only these operational estimators and a `SUFFICIENCY_UNCERTIFIED = True` sentinel; the conservative version-space upper bound is Phase B.

- [ ] **Step 1: Write failing tests (recovers the true circle; oracle works for every family; tangent is oriented)**

```python
# tests/test_oracle.py
import math, random
from cwm.continuous.shapes import Circle, Parabola, RegularPolygon
from cwm.continuous.shapes import HalfPlane, Strip, Wedge
from cwm.continuous.oracle import (fit_family, operational_reconstructs_vs_truth,
                                   operational_heldout_accuracy, tangent_baseline, SUFFICIENCY_UNCERTIFIED)
import math
BOX = ((-8.0,14.0),(-6.0,6.0))

def _labeled(shape, seed=0, n=1500):
    rng = random.Random(seed)
    pts = [(rng.uniform(0,6), rng.uniform(-3,3)) for _ in range(n)]
    return [(p, shape.contains(p)) for p in pts]

def test_fit_recovers_true_circle_R1():
    fit = fit_family("circle", _labeled(Circle(3.0,0.0,1.0)), BOX)
    assert abs(fit.cx-3.0) < 0.15 and abs(fit.R-1.0) < 0.15  # R=1 reachable (box bounds, not observed range)

def test_oracle_vs_truth_all_families():
    for fam, shp in (("halfplane", HalfPlane(3.0)), ("strip", Strip(3.0,1.0)),
                     ("circle", Circle(3.0,0.0,1.0)), ("parabola", Parabola(3.0,2.0)),
                     ("wedge", Wedge((3.0,0.0), math.radians(30), 0.0)),
                     ("polygon", RegularPolygon(3.0,0.0,1.0,5,0.0))):
        assert operational_reconstructs_vs_truth(fam, _labeled(shp), shp, BOX, iou_thresh=0.85)

def test_oracle_heldout_accuracy():
    shp = Circle(3.0,0.0,1.0)
    assert operational_heldout_accuracy("circle", _labeled(shp, seed=0), _labeled(shp, seed=1)) > 0.9

def test_tangent_baseline_classifies_with_side_and_offset():
    shp = Circle(3.0,0.0,1.0)
    hp = tangent_baseline(_labeled(shp, n=400))
    # a clear interior point is classified inside, a clear exterior point outside
    assert hp.contains((3.0,0.0)) and not hp.contains((7.0,0.0))

def test_sufficiency_uncertified_sentinel():
    assert SUFFICIENCY_UNCERTIFIED is True
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** family fits (all six families) with box-based bounds + coordinate polish; `operational_reconstructs_vs_truth` = IoU(fit-region, `truth_shape`-region) on the box grid ≥ `iou_thresh`; `operational_heldout_accuracy` = balanced accuracy of the fit on an independent labeled set; `tangent_baseline` = PCA-initialized orientation then offset+side chosen to minimize misclassification of the labeled points, returning `HalfPlaneGeneral(nx,ny,off)` (a `Shape` with `implicit_value = nx*x+ny*y-off`); the `SUFFICIENCY_UNCERTIFIED` sentinel. **Step 4:** PASS. **Step 5:** `git commit -m "feat(oracle): six-family fits, vs-truth + held-out evaluators, classifying tangent; S uncertified in Phase A"`.

---

### Task 10: Guard-only AST/MDL features

**Files:** Create `src/cwm/continuous/program_features.py`; Test `tests/test_program_features.py`.

**Interfaces:** `guard_features(code, integrator_reward_ast) -> dict` — parses `code` and computes features on the guard conditions ONLY, **preferring the `test` expressions of branches that lead to the reset/freeze** (a branch whose body returns the previous position / zero velocity), and excluding auxiliary branches (e.g. action clamping) and the shared integrator/reward AST, so the integrator's `var*const` products don't inflate `guard_poly_degree`. Keys: `n_comparisons, boolean_depth, n_literals, guard_poly_degree, uses_hypot_sqrt, n_conjuncts, n_disjuncts, guard_ast_size, approx_mdl, invalid`.

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

**Interfaces:** `classify_artifact(code, transitions, eps) -> {"class","gate_accuracy","features"}` with class **`invalid`** when the code is unparseable OR lacks a callable `step`/`reward` OR raises on a trivial call **in the sandbox** (not `gate_failing`); `gate_failing` when it runs but gate accuracy `<1`; `gate_passing` at `1.0`. `dynamic_metrics_sandboxed(code, box, grid_n, velocity_samples) -> mask-array` — runs the artifact's `step` over the supplied grid **in a single sandbox subprocess** returning the forbidden mask, so gate-failing artifacts are never exec'd in-process. The subprocess returns the mask as **base64-encoded packed bits inside a JSON envelope** (compatible with the existing text-stdout sandbox), NOT a raw `.npy` on stdout. Executability/step-reward presence is checked in the sandbox.

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

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** using the existing sandbox runner (`contract.run_in_sandbox`): a preflight that checks parse + `step`/`reward` presence + a trivial call → `invalid`; else `contract_accuracy` for `gate_failing`/`gate_passing`; `dynamic_metrics_sandboxed` writes a tiny driver that loops the grid inside the subprocess and prints a JSON envelope `{"grid_n":N,"mask_b64":<base64 packed bits>}`, which the caller decodes to a boolean `np.ndarray`. **Step 4:** PASS. **Step 5:** `git commit -m "feat(artifact-class): invalid vs gate_failing distinguished; sandboxed dynamic mask (base64 JSON)"`.

---

### Task 12: Evidence-dose — fixed 40-example transcript cap, structured failures, refinement-integrated

**Files:** Create `src/cwm/continuous/evidence_dose.py`; Test `tests/test_evidence_dose.py`.

**Interfaces:** every transition carries a stable `source_index` (added in `collect_transitions`, referring to the original 3200 order — NOT the reshuffled 40). `build_dose_sample(env, transitions, m, span, rng) -> (controlled_examples, allowed_source_indices, meta)` — needs `env` to compute the proposed endpoint, project to `env.shape`'s boundary, measure normal distance, and select `span∈{"small","large"}` by the arc extent of the kept positives; returns exactly **40 controlled examples = m positives + m distinct matched negatives (nearest by boundary-normal distance to each kept positive's endpoint, no reuse) + (40−2m) background**, and `allowed_source_indices` = the `source_index` values the LLM may be corrected on. `build_controlled_initial_messages(contract, controlled_examples) -> list[dict]` — the INITIAL prompt, presenting the 40 as observations (not failures). `refine_capped(provider, model, contract, code, gate_transitions, controlled_examples, allowed_source_indices, eps, max_iters=5) -> RefineResult` — takes BOTH the full `gate_transitions` (all 3200, to measure the true gate and locate failures by `source_index`) and the 40 `controlled_examples`; each iteration filters failures to `allowed_source_indices`, feeds back ONLY those, and stops as `evidence_capped_failure` if every remaining gate failure is outside the allowed set. `is_evidence_capped_failure(failure_source_indices, allowed_source_indices) -> bool`.

- [ ] **Step 1: Write failing tests (exactly 40, m positives, distinct negatives, structured index membership, span)**

```python
# tests/test_evidence_dose.py
import random
from cwm.continuous.envs import ShapeField2D
from cwm.continuous.shapes import Circle
from cwm.continuous.contract import collect_transitions
from cwm.continuous.evidence_dose import build_dose_sample, is_evidence_capped_failure

def test_transitions_carry_source_index():
    tr = collect_transitions(ShapeField2D(shape=Circle(3.0,0.0,1.0)), n_rollouts=5, seed=0)
    assert [t["source_index"] for t in tr] == list(range(len(tr)))  # stable original order

def test_fixed_size_and_distinct_negatives():
    env = ShapeField2D(shape=Circle(3.0,0.0,1.0))
    tr = collect_transitions(env, n_rollouts=60, seed=0)
    ex, allowed, meta = build_dose_sample(env, tr, m=8, span="large", rng=random.Random(0))
    assert len(ex) == 40 and meta["n_positive"] == 8 and meta["n_negative"] == 8
    neg_src = [e["source_index"] for e in ex if not e["contact"]]
    assert len(set(neg_src)) == len(neg_src)  # no negative reused
    assert allowed <= {t["source_index"] for t in tr}  # allowed refers to original indices

def test_capped_failure_uses_source_indices():
    assert is_evidence_capped_failure(failure_source_indices={311, 512}, allowed_source_indices={7,8,9}) is True
    assert is_evidence_capped_failure(failure_source_indices={8, 512}, allowed_source_indices={7,8,9}) is False
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** — add `source_index` to `collect_transitions` output (stable original order); fixed-40 construction using `env`/`env.shape` for endpoint projection and normal distance; endpoint-normal matched negatives without reuse; span selection by the boundary-arc extent of the kept positives; a `contract_accuracy` wrapper returning failing `source_index` values; `build_controlled_initial_messages`; and `refine_capped` taking both `gate_transitions` and `controlled_examples`, filtering failures to `allowed_source_indices` each iteration. **Step 4:** PASS. **Step 5:** `git commit -m "feat(evidence-dose): env-aware fixed-40 cap, source_index, dual-dataset refinement, initial controlled prompt"`.

---

### Task 13: Calibration prototype + strict anti-placeholder validator (the Phase-A/B gate)

**Files:** Create `scripts/calibrate_shape2d.py`, `src/cwm/continuous/calibration.py` (the validator), `results/shape2d_calibration.json`; Test `tests/test_calibration.py`.

**Interfaces:** a frozen manifest `EXPECTED_CELL_IDS` (in `calibration.py`) enumerating every anchor, parabola, composition, and contrast cell of the sweep. `validate_calibration_artifact(art) -> list[str]` (empty = valid) **rejects** any of: `set(cell["id"] for cell in art["cells"]) != EXPECTED_CELL_IDS` (exact manifest match); any `None`/`NaN`/empty list; a cell missing `rarity`, `rarity_ci`, or `n_rollouts`/`n_episodes` below fixed minimums; `grid_converged` not backed by a measured per-cell `grid_delta_256_512 < 0.01` (or an explicit global justification field); `rarity` outside `rarity_target ± tol`; a cell whose blind planner is **not** exploited (`play_cost_blind ≥ 0.8` from truth/blind/random **episodes**, not one `mpc.plan` call); `frac_planner_outside_box` above an explicit bound; a `repaired_threshold.source != "truth_oracle_fullarm_griderror"`; equal calibration/validation seed streams; any parameter lacking a `provenance` tag; or a `sufficiency` block not exactly `{"certified": false, "tau_s": null, "reason": <str>}` (Phase A leaves S uncertified — `tau_S` must NOT appear as a calibrated number). `calibrate_shape2d.py` measures every field. `rarity` = **fraction of rollouts containing a contact** with a Wilson CI on an **independent** seed stream (distinct from the validation stream).

- [ ] **Step 1: Write failing tests — the validator REJECTS a placeholder, ACCEPTS a filled artifact**

```python
# tests/test_calibration.py
import json, subprocess, sys, math
from cwm.continuous.calibration import validate_calibration_artifact, EXPECTED_CELL_IDS

def _full_cells():
    return [{"id": cid, "family": "circle", "R": 1.0, "offset": 3.0, "rarity": 0.15,
             "rarity_ci": [0.12, 0.18], "n_rollouts": 400, "n_episodes": 30, "play_cost_blind": 0.99,
             "grid_delta_256_512": 0.004, "provenance": "measured"} for cid in EXPECTED_CELL_IDS]

def _good_artifact():
    return {"box": [[-8,14],[-6,6]], "grid_n": 256, "rarity_target": 0.15, "rarity_tol": 0.05,
            "frac_planner_outside_box": 0.01, "frac_outside_box_bound": 0.05,
            "cal_seed_stream": 1, "val_seed_stream": 2, "delta": 0.12, "delta_provenance": "median_normal_bracket",
            "sufficiency": {"certified": False, "tau_s": None, "reason": "conservative upper bound deferred to Phase B"},
            "repaired_threshold": {"band_disagreement": 0.05, "fpr": 0.05, "source": "truth_oracle_fullarm_griderror"},
            "cells": _full_cells()}

def test_validator_rejects_placeholder():
    placeholder = {"box": [[-8,14],[-6,6]], "grid_n": 256, "delta": None, "cells": [],
                   "sufficiency": {"certified": False, "tau_s": 0.1, "reason": ""},  # tau_s must be null
                   "repaired_threshold": {"source": "incomplete_anchor"}, "frac_planner_outside_box": 0.0}
    problems = validate_calibration_artifact(placeholder)
    assert any("cell" in p.lower() for p in problems)      # manifest mismatch (empty)
    assert any("delta" in p.lower() for p in problems)     # None
    assert any("source" in p.lower() for p in problems)    # bad provenance
    assert any("tau" in p.lower() or "sufficiency" in p.lower() for p in problems)  # tau_s not null

def test_validator_rejects_missing_one_cell():
    art = _good_artifact(); art["cells"] = art["cells"][:-1]  # drop a manifest cell
    assert any("cell" in p.lower() for p in validate_calibration_artifact(art))

def test_validator_rejects_equal_seed_streams():
    art = _good_artifact(); art["val_seed_stream"] = art["cal_seed_stream"]
    assert any("seed" in p.lower() for p in validate_calibration_artifact(art))

def test_validator_accepts_full_artifact():
    assert validate_calibration_artifact(_good_artifact()) == []

# --- SMOKE test: --quick fills the schema; scientific validation is only for the full artifact ---
def test_calibration_quick_smoke_schema(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, "scripts/calibrate_shape2d.py", "--quick", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    art = json.loads(out.read_text())
    assert set(c["id"] for c in art["cells"]) == EXPECTED_CELL_IDS  # schema/manifest present
    assert art["sufficiency"]["tau_s"] is None
    # NOTE: --quick may not meet rarity/play_cost tolerances with few episodes; strict
    # validate_calibration_artifact is asserted only on the FULL run, below.

def test_full_calibration_passes_strict_validation():
    # run the full (non-quick) calibration once in the repo, then:
    #   assert validate_calibration_artifact(json.load(open("results/shape2d_calibration.json"))) == []
    # Marked here as the scientific gate; executed by the implementer after the full run.
    pass
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** the validator first (pure function, fully covered by the unit tests) — define `EXPECTED_CELL_IDS`, enforce exact manifest match, NaN checks via `math.isnan`, the `sufficiency` shape, distinct seed streams, per-parameter `provenance`, per-cell `grid_delta_256_512`, and the explicit `frac_outside_box_bound`. Then `calibrate_shape2d.py` measures per cell of `EXPECTED_CELL_IDS`: offset achieving `rarity_target` (fraction-of-rollouts, Wilson CI on an independent `cal_seed_stream`), per-cell `grid_delta_256_512`, `play_cost_blind` from truth/blind/random **episodes**, `delta` (median normal-bracket width), `frac_planner_outside_box`, `sufficiency={"certified":False,"tau_s":None,...}`, and `repaired_threshold.source="truth_oracle_fullarm_griderror"`. `--quick` shrinks counts and fills the full schema/manifest but is a **smoke test only** — strict `validate_calibration_artifact` is asserted on the FULL run. **Step 4:** `pytest tests/test_calibration.py -q` → PASS; then `python scripts/calibrate_shape2d.py` and assert `validate_calibration_artifact(...) == []` on the full artifact. **Step 5:** `git commit -m "feat(calibration): manifest-checked measured artifact + strict validator + smoke/scientific split"`.

---

## Phase-A completion gate

After Task 13, `results/shape2d_calibration.json` exists, `validate_calibration_artifact` returns `[]` on it, and `pytest -q` is green (cart golden included). **This validated artifact is the GO gate for Phase B** (the ~520 Azure syntheses). Phase B — a separate plan — builds the crash-safe checkpoint/resume harness (does not exist today), the sweep driver reading the frozen artifact, the V_transcript logging + three-oracle attribution (with the conservative version-space upper bound that certifies `S`, deferred from Phase A), the evidence-dose runs, the pre-registered adaptive densification (crossover-CI for the curvature sweep, score/interaction-CI for dose & composition), the bounded-outcome statistics (zero/one-inflated beta; logistic for `repaired`), and the paper integration. Do NOT start Phase B until the artifact validates and is reviewed.
