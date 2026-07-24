"""Shape base + primitives shared by the geometry-repair experiment.

Sign convention: `implicit_value` is negative inside, positive outside (a
signed potential, not necessarily a true distance). `signed_distance` is a
true euclidean distance to the projected boundary point, signed by
containment — used wherever a metric (not just a classifier) is needed.
"""
from __future__ import annotations
import bisect
import math
from dataclasses import dataclass

import numpy as np


def _resample_components(ordered_pts, n, gap_tol):
    """Split an ordered in-window point list into arc components at gaps > gap_tol,
    then resample n points by arc length, allocated across components proportional
    to their length. Never accumulates distance across the gap between two arcs.

    Within each component the n_k allocated points are placed at equally-spaced
    target cumulative arc lengths (0, L/(n_k-1), 2L/(n_k-1), ...) and interpolated
    linearly between the bracketing input samples -- this is what makes the output
    arc-length uniform even when the input samples themselves are not (e.g. a
    parabola boundary generated from a uniform y-grid, whose x-spacing stretches
    away from the vertex)."""
    if not ordered_pts:
        return []
    comps, cur = [], [ordered_pts[0]]
    for k in range(1, len(ordered_pts)):
        if math.hypot(ordered_pts[k][0]-ordered_pts[k-1][0], ordered_pts[k][1]-ordered_pts[k-1][1]) > gap_tol:
            comps.append(cur); cur = []
        cur.append(ordered_pts[k])
    comps.append(cur)
    cumlens = []
    lengths = []
    for comp in comps:
        cl = [0.0]
        for i in range(1, len(comp)):
            d = math.hypot(comp[i][0]-comp[i-1][0], comp[i][1]-comp[i-1][1])
            cl.append(cl[-1] + d)
        cumlens.append(cl)
        lengths.append(max(cl[-1], 1e-12))
    total = sum(lengths)
    # allocate exactly n across components by largest remainder, so rounding never returns < n
    raw = [n * L / total for L in lengths]
    share = [int(r) for r in raw]
    order = sorted(range(len(comps)), key=lambda k: raw[k]-share[k], reverse=True)
    for k in order[:max(0, n - sum(share))]:
        share[k] += 1

    def sample_arclength(comp, cl, s):
        if s <= 0 or not comp:
            return []
        if len(comp) == 1 or cl[-1] <= 1e-12:
            return [comp[0]] * s
        L = cl[-1]
        out = []
        for i in range(s):
            target = (L * i / (s - 1)) if s > 1 else 0.0
            j = bisect.bisect_left(cl, target)
            if j <= 0:
                out.append(comp[0])
            elif j >= len(cl):
                out.append(comp[-1])
            else:
                t0, t1 = cl[j-1], cl[j]
                frac = 0.0 if (t1 - t0) < 1e-12 else (target - t0) / (t1 - t0)
                x = comp[j-1][0] + frac*(comp[j][0]-comp[j-1][0])
                y = comp[j-1][1] + frac*(comp[j][1]-comp[j-1][1])
                out.append((x, y))
        return out

    out = []
    for comp, cl, s in zip(comps, cumlens, share):
        if s and comp:
            out.extend(sample_arclength(comp, cl, s))
    allpts = [p for comp in comps for p in comp]  # top up if a component was empty/underfilled
    i = 0
    while len(out) < n and allpts:
        out.append(allpts[i % len(allpts)]); i += 1
    return out[:n]


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
class HalfPlaneGeneral(Shape):
    """General-orientation half-plane: region nx*x + ny*y <= off (negative
    inside, matching the Shape sign convention). `HalfPlane(c)` is the
    axis-aligned special case (nx=1, ny=0, off=c); this class exists because
    the classifying tangent baseline (oracle.py) fits an arbitrarily
    oriented separating line, not just a vertical one."""
    nx: float; ny: float; off: float
    def implicit_value(self, p): return self.nx*p[0] + self.ny*p[1] - self.off
    def project_to_boundary(self, p):
        norm = math.hypot(self.nx, self.ny) or 1.0
        d = self.implicit_value(p) / norm
        return (p[0] - d*self.nx/norm, p[1] - d*self.ny/norm), False
    def normal_or_cone(self, p):
        norm = math.hypot(self.nx, self.ny) or 1.0
        return (self.nx/norm, self.ny/norm)
    def boundary_points(self, window, n):
        (xmin, xmax), (ymin, ymax) = window
        norm = math.hypot(self.nx, self.ny) or 1.0
        nxu, nyu = self.nx/norm, self.ny/norm
        cx0, cy0 = 0.5*(xmin+xmax), 0.5*(ymin+ymax)
        d = (self.nx*cx0 + self.ny*cy0 - self.off) / norm
        px, py = cx0 - d*nxu, cy0 - d*nyu
        dirx, diry = -nyu, nxu  # unit direction along the line
        ts = [50.0]
        for dc, origin, lo, hi in ((dirx, px, xmin, xmax), (diry, py, ymin, ymax)):
            if abs(dc) > 1e-12:
                for bound in (lo, hi):
                    ts.append(abs((bound-origin)/dc))
        tmax = min(ts)
        if n == 1: return [(px, py)]
        return [(px + dirx*tmax*(2*i/(n-1)-1), py + diry*tmax*(2*i/(n-1)-1)) for i in range(n)]


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


@dataclass(frozen=True)
class Parabola(Shape):
    """Region x >= c + y^2/(2R); opens toward +x, vertex at (c, 0).
    R -> infinity recovers HalfPlane(c)."""
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
        # minimize (x0-c-y^2/2R)^2 + (y0-y)^2 over y:
        # d/dy[...] = 0  ->  y^3/(2R^2) + y*(1+(c-x0)/R) - y0 = 0
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
        ys = [ymin+(ymax-ymin)*i/(M-1) for i in range(M)]
        pts = [(self._bx(y), y) for y in ys]
        infoc = [(x,y) for (x,y) in pts if xmin<=x<=xmax and ymin<=y<=ymax]
        if len(infoc) < 2: return infoc[:n]
        step = math.hypot(infoc[1][0]-infoc[0][0], infoc[1][1]-infoc[0][1])
        return _resample_components(infoc, n, gap_tol=max(3.0*step, 0.1))  # x-clip can split into arcs


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
