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


def rips_persistence(points: list, edge_filter=None) -> dict:
    """Full-clique Rips persistence. Returns {"h0": [...], "h1": [...]} as
    lists of (birth, death) with death=None for infinite bars. Zero-
    persistence bars are dropped. `edge_filter(p, q) -> bool` (optional):
    edges for which it returns False are CENSORED (excluded from the
    filtration) — the trajectory-censored variant; default None is the
    plain Rips, byte-identical."""
    n = len(points)
    if n == 0:
        return {"h0": [], "h1": []}

    edges = []                      # (length, i, j)
    for i in range(n):
        for j in range(i + 1, n):
            if edge_filter is not None and not edge_filter(points[i],
                                                           points[j]):
                continue
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
            if (i, j) not in eidx:      # censored edge: no such triangle
                continue
            dij = elen[eidx[(i, j)]]
            for k in range(j + 1, n):
                if (i, k) not in eidx or (j, k) not in eidx:
                    continue            # censored edge: no such triangle
                f = max(dij, elen[eidx[(i, k)]], elen[eidx[(j, k)]])
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


def free_merge_persistence(contact: list, free_paths: list) -> dict:
    """The RELATIVE evidence estimator (docs/paper3/THEORY.md, "T7 (second
    half)"): persistence of rank ker(H0(VR(free)) -> H0(VR(contact+free))),
    i.e. how many certified-free components the contact evidence glues
    together, as a function of scale.

    By the long exact sequence of the pair (K, L) = (VR(X u Y), VR(Y)),
    this rank equals rank H1(K, L) whenever H1(K) = 0 and lower-bounds it
    otherwise (Proposition R2). Unlike edge censoring it has NO infinite
    bars by construction (Proposition R1): at scale >= diam both complexes
    are full simplices, so the rank returns to 0.

    `free_paths` is a list of PATHS (each a list of consecutive positions
    along one certified-free trajectory segment chain), not a flat cloud:
    consecutive samples on a path are joined at scale 0 in both complexes,
    because a free trajectory certifies that its own samples are connected
    through free space. Passing a flat cloud instead makes the estimator
    measure the contact/free DENSITY MISMATCH rather than the topology --
    the refuted point-cloud instantiation (THEORY.md, T7 second half).

    Returns {"bars": [(birth, death), ...], "max_rank": int}; a bar covers
    a maximal scale interval on which the rank is >= 1. Both union-finds
    are maintained incrementally, so the cost is one sort of the pairwise
    distances.
    """
    free = [p for path in free_paths for p in path]
    pts = list(contact) + free
    nc, nf = len(contact), len(free)
    n = nc + nf
    if nf == 0 or n == 0:
        return {"bars": [], "max_rank": 0}

    events = []
    for i in range(n):
        for j in range(i + 1, n):
            events.append((_dist(pts[i], pts[j]), i, j))
    events.sort()

    par_l = list(range(n))          # union-find on FREE points only
    par_k = list(range(n))          # union-find on ALL points
    has_free = [i >= nc for i in range(n)]

    def find(par, x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    comp_l = nf                     # components of VR(free)
    comp_k_free = nf                # K-components containing a free point

    # scale-0 path edges: a free trajectory certifies its own connectivity
    off = nc
    for path in free_paths:
        for t in range(len(path) - 1):
            u, v = off + t, off + t + 1
            a, b = find(par_l, u), find(par_l, v)
            if a != b:
                par_l[a] = b
                comp_l -= 1
            a, b = find(par_k, u), find(par_k, v)
            if a != b:
                comp_k_free -= 1    # both carry free points by construction
                par_k[a] = b
                has_free[b] = True
        off += len(path)

    bars, open_at, prev_rank, max_rank = [], None, 0, 0
    for d, i, j in events:
        if i >= nc and j >= nc:     # free-free edge: merges in BOTH
            a, b = find(par_l, i), find(par_l, j)
            if a != b:
                par_l[a] = b
                comp_l -= 1
        a, b = find(par_k, i), find(par_k, j)
        if a != b:
            if has_free[a] and has_free[b]:
                comp_k_free -= 1
            par_k[a] = b
            has_free[b] = has_free[a] or has_free[b]
        rank = comp_l - comp_k_free
        max_rank = max(max_rank, rank)
        if rank != prev_rank:
            if prev_rank == 0 and rank > 0:
                open_at = d
            elif rank == 0 and open_at is not None:
                if d > open_at:
                    bars.append((open_at, d))
                open_at = None
            prev_rank = rank
    # Proposition R1: at the top scale everything is one component, so the
    # rank is back to 0 and no bar can be left open.
    assert prev_rank == 0 and open_at is None, "infinite relative bar"
    return {"bars": bars, "max_rank": max_rank}


def relative_betti1_estimate(contact: list, free_paths: list,
                             factor: float = 3.0) -> dict:
    """Detector on `free_merge_persistence`, using the SAME persistence
    rule as `betti1_estimate` (bars longer than factor x median
    nearest-neighbour spacing of the contact cloud) so the two are
    directly comparable."""
    res = free_merge_persistence(contact, free_paths)
    tau = factor * median_nn_distance(contact)
    persistent = [b for b in res["bars"] if (b[1] - b[0]) > tau]
    return {"betti1_rel": len(persistent), "tau": tau,
            "bars": res["bars"], "bars_over_tau": persistent,
            "max_rank": res["max_rank"], "n_contact": len(contact),
            "n_free": sum(len(p) for p in free_paths)}


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


def topological_summary(points: list, factor: float = 3.0, cap: int = 90,
                        grid: float = 0.05, seed: int = 0) -> str:
    """Honest, shape-agnostic text summary of a contact-evidence cloud, for
    the paper-3 TDA-informed synthesis arm. Reports only what is computable
    from the observed positions (counts, clusters, bounding box, persistent
    beta1) plus one generic mechanical fact about freeze-type evidence (it
    lies on the reachable side of its trigger region). NEVER names a shape
    family — the wording is pre-registered; do not tune it per run."""
    pts = subsample(dedupe(points, grid), cap, seed)
    if len(pts) < 4:
        return (f"Only {len(pts)} distinct anomalous landing positions were "
                f"observed — too few for a geometric characterization; treat "
                f"any hypothesized trigger region as weakly constrained.")
    bars = rips_persistence(pts)
    tau = factor * median_nn_distance(pts)
    clusters = 1 + sum(1 for b in bars["h0"]
                       if b[1] is not None and b[1] > tau)
    est = betti1_estimate(pts, factor=factor)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    lines = [
        "Diagnostics of the anomalous (non-integrator) landing positions,",
        "computed from the observed transitions alone:",
        f"- {len(pts)} distinct positions, forming {clusters} spatial "
        f"cluster(s);",
        f"- bounding box x in [{min(xs):.2f}, {max(xs):.2f}], "
        f"y in [{min(ys):.2f}, {max(ys):.2f}];",
        f"- persistent-homology check: beta_1 = {est['betti1']}.",
    ]
    if est["betti1"] >= 1:
        lines.append(
            "beta_1 >= 1 means the positions trace at least one CLOSED LOOP "
            "enclosing an area the sample never visits: a trigger region "
            "consistent with this evidence must have a boundary that closes "
            "around that enclosed area.")
    else:
        lines.append(
            "beta_1 = 0 means the positions trace an open arc/patch, not a "
            "closed loop.")
    lines.append(
        "Note: freeze-type anomalies are only ever observed on the REACHABLE "
        "side of their trigger region; the region may extend beyond the "
        "observed positions on the far side.")
    return "\n".join(lines)
