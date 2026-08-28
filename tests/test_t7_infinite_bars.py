"""T7 (first half) machine checks: infinite censoring artifacts
(docs/paper3/THEORY.md, "T7 (first half)": Propositions C1-C3). The
instrument certificate is scripts/t7_infinite_bar_certificate.py; these
are the synthetic guards for the characterization and the minimal model."""
import math

from cwm.continuous.tda import rips_persistence


def test_t7_plain_rips_has_no_infinite_h1():
    # Proposition C1(a): with no censor the limit is the full simplex
    pts = [(math.cos(2 * math.pi * k / 24) * 3.65,
            math.sin(2 * math.pi * k / 24) * 3.65) for k in range(24)]
    bars = rips_persistence(pts)["h1"]
    assert all(d is not None for _, d in bars)


def test_t7_quadrilateral_minimal_model():
    # Proposition C2: an allowed 4-cycle whose diagonals are censored is a
    # never-fillable cycle -> exactly one infinite H1 bar
    sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    def edge_ok(p, q):
        # censor the two diagonals only
        return abs(math.dist(p, q) - math.sqrt(2)) > 1e-9

    bars = rips_persistence(sq, edge_filter=edge_ok)["h1"]
    inf = [b for b in bars if b[1] is None]
    assert len(inf) == 1
    assert abs(inf[0][0] - 1.0) < 1e-9        # born at the longest side
    # and uncensored, the same square has no infinite bar
    assert all(d is not None for _, d in rips_persistence(sq)["h1"])


def test_t7_decidability_certificate_shape():
    # C1(b): "artifact-free" is one finite computation on the limit
    # complex — censoring an edge that other points cone away leaves H1
    # empty at infinity (the certificate returns clean)
    pts = [(math.cos(2 * math.pi * k / 12) * 2.0,
            math.sin(2 * math.pi * k / 12) * 2.0) for k in range(12)]
    pts.append((0.0, 0.0))                    # hub point cones everything

    def edge_ok(p, q):
        # censor one long chord between near-antipodal rim points
        pair = {(round(p[0], 6), round(p[1], 6)),
                (round(q[0], 6), round(q[1], 6))}
        bad = {(2.0, 0.0), (-2.0, 0.0)}
        return pair != {tuple(b) for b in bad}

    bars = rips_persistence(pts, edge_filter=edge_ok)["h1"]
    assert all(d is not None for _, d in bars)
