"""Shape base + primitives shared by the geometry-repair experiment.

Sign convention: `implicit_value` is negative inside, positive outside (a
signed potential, not necessarily a true distance). `signed_distance` is a
true euclidean distance to the projected boundary point, signed by
containment — used wherever a metric (not just a classifier) is needed.
"""
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
    # allocate exactly n across components by largest remainder, so rounding never returns < n
    raw = [n * L / total for L in lengths]
    share = [int(r) for r in raw]
    order = sorted(range(len(comps)), key=lambda k: raw[k]-share[k], reverse=True)
    for k in order[:max(0, n - sum(share))]:
        share[k] += 1
    out = []
    for comp, s in zip(comps, share):
        if s and comp:
            out.extend(comp[(i*len(comp))//s] for i in range(s))
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
