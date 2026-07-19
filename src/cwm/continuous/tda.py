"""Minimal persistent homology (H0, H1) for small 2D point clouds — the
paper-3 TDA arm's measurement tool (docs/paper3/RESEARCH-DIRECTION.md §4.3).

Vietoris–Rips filtration over GF(2), standard boundary-matrix reduction:
vertices at filtration 0; edge (i,j) at the pairwise distance; triangle at
its max edge length. H0 via union-find (merge edges are negative); H1 via
column reduction of triangle boundaries expressed in edge indices — by the
R=DV pairing lemma a reduced triangle column's pivot edge is automatically a
positive (cycle-creating) edge, so each claimed pivot yields the bar
(f(edge), f(triangle)); positive edges never claimed yield infinite bars.

Pure Python, no dependencies; O(n^3) triangles — intended for clouds of at
most ~120 points (subsample first; `subsample` provided). The DECISION RULE
used by probes is `betti1_estimate`: number of finite-persistence H1 bars
with persistence > `factor` x median nearest-neighbor distance (default
factor 3.0) — Cohen-Steiner et al. stability is the justification for a
spacing-relative threshold; the factor is pre-registered, never tuned per
cloud.
"""
import math
import random


def _dist(p, q):
    return math.dist(p, q)


def subsample(points: list, cap: int, seed: int = 0) -> list:
    """Deterministic subsample to at most `cap` points (rng-seeded)."""
    if len(points) <= cap:
        return list(points)
    rng = random.Random(seed)
    return rng.sample(list(points), cap)


def dedupe(points: list, grid: float = 0.05) -> list:
    """Snap to a grid and keep one point per cell (contact clouds repeat
    near-identical refuted landings when a mover re-fires from rest)."""
    seen, out = set(), []
    for p in points:
        key = (round(p[0] / grid), round(p[1] / grid))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def median_nn_distance(points: list) -> float:
    if len(points) < 2:
        return 0.0
    nns = []
    for i, p in enumerate(points):
        nns.append(min(_dist(p, q) for j, q in enumerate(points) if j != i))
    nns.sort()
    m = len(nns)
    return nns[m // 2] if m % 2 else 0.5 * (nns[m // 2 - 1] + nns[m // 2])


def rips_persistence(points: list) -> dict:
    """Full-clique Rips persistence. Returns {"h0": [...], "h1": [...]} as
    lists of (birth, death) with death=None for infinite bars. Zero-
    persistence bars are dropped."""
    n = len(points)
    if n == 0:
        return {"h0": [], "h1": []}

    edges = []                      # (length, i, j)
    for i in range(n):
        for j in range(i + 1, n):
            edges.append((_dist(points[i], points[j]), i, j))
    edges.sort()
    elen = [e[0] for e in edges]

    # --- H0: union-find over edges in filtration order ---------------------
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    h0 = []
    positive = []                   # indices of cycle-creating edges
    for idx, (d, i, j) in enumerate(edges):
        ri, rj = find(i), find(j)
        if ri == rj:
            positive.append(idx)
        else:
            parent[ri] = rj
            if d > 0.0:
                h0.append((0.0, d))
    h0.append((0.0, None))          # the surviving component

    # --- H1: reduce triangle columns over edge indices ----------------------
    eidx = {}
    for idx, (d, i, j) in enumerate(edges):
        eidx[(i, j)] = idx

    def edge_index(a, b):
        return eidx[(a, b) if a < b else (b, a)]

    tris = []
    for i in range(n):
        for j in range(i + 1, n):
            dij = elen[edge_index(i, j)]
            for k in range(j + 1, n):
                f = max(dij, elen[edge_index(i, k)], elen[edge_index(j, k)])
                tris.append((f, i, j, k))
    tris.sort()

    pivot: dict = {}                # edge index -> reduced column (set)
    h1 = []
    positive_set = set(positive)
    for f, i, j, k in tris:
        col = {edge_index(i, j), edge_index(i, k), edge_index(j, k)}
        col &= positive_set         # tree edges never appear as pivots
        while col:
            piv = max(col)
            if piv not in pivot:
                break
            col ^= pivot[piv]
        if col:
            piv = max(col)
            pivot[piv] = col
            if f > elen[piv]:
                h1.append((elen[piv], f))
    for idx in positive:
        if idx not in pivot:
            h1.append((elen[idx], None))
    h1.sort(key=lambda b: (b[0], b[1] is None, b[1] or 0.0))
    return {"h0": h0, "h1": h1}


def betti1_estimate(points: list, factor: float = 3.0) -> dict:
    """Pre-registered detector: count H1 bars with persistence above
    factor x median-NN spacing (infinite bars always count). Returns the
    estimate plus diagnostics."""
    bars = rips_persistence(points)["h1"]
    tau = factor * median_nn_distance(points)
    persistent = [b for b in bars
                  if b[1] is None or (b[1] - b[0]) > tau]
    pers = sorted(((b[1] - b[0]) if b[1] is not None else float("inf")
                   for b in bars), reverse=True)
    return {"betti1": len(persistent), "tau": tau,
            "n_points": len(points),
            "top_persistence": pers[:2],
            "bars_over_tau": persistent}
