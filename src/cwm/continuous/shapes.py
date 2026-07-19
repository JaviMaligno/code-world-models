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
