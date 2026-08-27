"""The H2 intervention arm's contract (docs/paper3/INTERVENTION-DESIGN.md):
the flipped summary negates EXACTLY the topology claim — the beta_1 line and
its one interpretive sentence — and nothing else. If the two arms ever
differ on a diagnostic line, the paired contrast no longer isolates the
claim, so this is pinned."""
import math

from cwm.continuous.tda import topological_summary, topological_summary_flipped


def _circle(n=40, arc=2 * math.pi):
    return [(5 * math.cos(i * arc / n), 5 * math.sin(i * arc / n))
            for i in range(n)]


def _claim_lines(text):
    return [l for l in text.splitlines()
            if "beta_1" in l or "CLOSED LOOP" in l or "open arc" in l]


def _diagnostic_lines(text):
    return [l for l in text.splitlines()
            if "beta_1" not in l and "CLOSED LOOP" not in l
            and "open arc" not in l]


def test_flip_negates_the_claim_and_only_the_claim():
    for pts, honest_b1 in ((_circle(), 1), (_circle(arc=math.pi), 0)):
        h = topological_summary(pts)
        f = topological_summary_flipped(pts)
        assert f"beta_1 = {honest_b1}" in h
        assert f"beta_1 = {1 - honest_b1}" in f
        # every non-claim byte is identical between the arms
        assert _diagnostic_lines(h) == _diagnostic_lines(f)
        # both arms carry a claim (the flip never silently drops it)
        assert _claim_lines(h) and _claim_lines(f)


def test_flip_is_honest_below_the_point_floor():
    # with < 4 points there is no topology claim to negate: the arms must
    # coincide so the contrast stays zero where no claim exists
    pts = [(0.0, 0.0), (1.0, 0.0)]
    assert topological_summary(pts) == topological_summary_flipped(pts)
