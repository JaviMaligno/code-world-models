"""Trajectory-censored filtration: the sensor that resolves the channel
(V2-PROGRAM bucket-2b).

The measured failure (sensor factorial): plain Rips reports beta1_hat = 1 on
the open ring for every gamma <= 1.2 at ANY density/budget — the spurious
loop bar bridges the channel chord, a property of the shape. The fix uses
evidence Rips ignores: the FREE segments of the very trajectories that
produced the contact cloud. A Rips edge between two contact landings is
CENSORED when a free trajectory segment PROPERLY CROSSES it (transversal
intersection — not mere proximity, which would kill true-loop edges at
gap 0 where free segments end hugging the boundary): the channel bridge is
crossed exactly where free trajectories pass, so it never forms; the closed
ring's true loop is untouched (nothing free crosses the band).

Cells: gamma in {0, 0.6, 1.2, 1.8, 2.4}, inside start, 5 seeds, N=40 —
plain beta1_hat vs censored beta1_hat. Expected: plain 1/1/1/flip/0 (the
measured resolution limit); censored 1 at gamma=0 and 0 at every gamma>0
(the TRUE beta1) — resolution restored by trajectory knowledge, not budget.

Selftest: constructed C-arc + crossing free segment (censored kills the
spurious loop) and constructed closed loop + far free segment (censored
preserves the true loop).

Output: results/ring2d_censored_filtration.json. CPU, resumable per row.
"""
import json
import math
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402
from cwm.continuous.contract import collect_transitions         # noqa: E402
from cwm.continuous.tda import (betti1_estimate, dedupe,        # noqa: E402
                                rips_persistence, subsample,
                                median_nn_distance)

GAPS = [0.0, 0.6, 1.2, 1.8, 2.4]
SEEDS = [10000, 20000, 30000, 40000, 50000]
# Censor rule: PROPER segment crossing (transversal intersection), not
# proximity — proximity would kill true-loop edges at gap 0, where free
# segments end hugging the boundary without crossing it.
CAP = 90              # the pre-registered detector budget, unchanged
OUT = "results/ring2d_censored_filtration.json"


MARGIN = 0.0   # transversality margin over the edge's supporting line.
# 0.0 = v1 semantics (any proper crossing censors). The 0.3-margin refinement
# was tried against the gap-0 false negatives (pokes) and REJECTED — measured
# reason (t7_infinite_bar_certificate, 2026-07-25): it repairs gap-0 (5/5)
# but censors too few edges and RESTORES THE BRIDGE at gamma=0.6 (5/5 false
# loops, finite bars). The never-fillable-cycle phenomenon (INFINITE H1 bars,
# a topological artifact of naive edge deletion) belongs to v1 ITSELF: 4/25
# cells — the 3 gap-0 true loops (fills cross the certified-free hole) and
# the single gap-0.6 specificity failure, which is structural, not
# near-threshold. Infinite bars are per-sample decidable (THEORY.md Prop C1);
# the principled object is RELATIVE homology (contact set relative to
# certified-free space) — that estimator is the open half of T7.


def _crosses(p1, p2, q1, q2):
    """Transversal passage: the free segment q1q2 intersects the edge p1p2
    AND clears the edge's supporting LINE by MARGIN on both sides (opposite
    signs). A poke ending just past the line has small far-side clearance
    and does not censor."""
    from cwm.continuous.mitigation import _segments_intersect
    if not _segments_intersect(p1, p2, q1, q2):
        return False
    ex, ey = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(ex, ey) or 1e-12
    nx, ny = -ey / L, ex / L
    s1 = nx * (q1[0] - p1[0]) + ny * (q1[1] - p1[1])
    s2 = nx * (q2[0] - p1[0]) + ny * (q2[1] - p1[1])
    return s1 * s2 < 0 and min(abs(s1), abs(s2)) > MARGIN


def evidence(env, seed, n_roll=40):
    """Contact landings (the summary's cloud) AND free trajectory segments."""
    trans = collect_transitions(env, n_roll, seed=seed)
    landings, free = [], []
    for tr in trans:
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            landings.append((x2, y2))
        else:
            s, ns = tr["state"], tr["next_state"]
            free.append(((s[0], s[1]), (ns[0], ns[1])))
    return landings, free


def censored_betti1(points, free_segments, factor=3.0):
    """betti1_estimate with edges crossing certified-free space censored."""
    def edge_ok(p, q):
        return not any(_crosses(p, q, a, b) for a, b in free_segments)
    bars = rips_persistence(points, edge_filter=edge_ok)["h1"]
    tau = factor * median_nn_distance(points)
    persistent = [b for b in bars if b[1] is None or (b[1] - b[0]) > tau]
    return len(persistent)


def selftest():
    import random
    rnd = random.Random(0)
    # C-arc (270 degrees) of radius 4: plain Rips bridges the opening
    arc = [(4 * math.cos(a), 4 * math.sin(a))
           for a in [rnd.uniform(0.25 * math.pi, 1.75 * math.pi)
                     for _ in range(80)]]
    # a free path through the opening PLUS interior traffic (the real
    # instrument's inside-start probes fill the hole with free segments)
    crossing_free = [((5.5, 0.0), (2.5, 0.0))]
    for _ in range(60):
        a1, r1 = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 3.0)
        a2, r2 = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 3.0)
        crossing_free.append(((r1 * math.cos(a1), r1 * math.sin(a1)),
                              (r2 * math.cos(a2), r2 * math.sin(a2))))
    plain = betti1_estimate(arc)["betti1"]
    cens = censored_betti1(arc, crossing_free)
    print(f"  C-arc: plain b1={plain} censored b1={cens} (want 1 -> 0)")
    ok = plain == 1 and cens == 0
    # full loop with a free segment far away: censoring must NOT break it
    loop = [(4 * math.cos(a), 4 * math.sin(a))
            for a in [rnd.uniform(0, 2 * math.pi) for _ in range(80)]]
    far_free = [((20.0, 20.0), (22.0, 20.0))]
    plain2 = betti1_estimate(loop)["betti1"]
    cens2 = censored_betti1(loop, far_free)
    print(f"  loop:  plain b1={plain2} censored b1={cens2} (want 1 -> 1)")
    ok = ok and plain2 == 1 and cens2 == 1
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main():
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["gap"], r["seed"]) for r in rows}
    for gap in GAPS:
        env = RingField2D(gap=gap, gap_center=math.pi,
                          x0_center=RingField2D().center)
        for seed in SEEDS:
            if (gap, seed) in done:
                continue
            landings, free = evidence(env, seed)
            pts = subsample(dedupe(landings, 0.05), CAP, 0)
            plain = betti1_estimate(pts)["betti1"]
            cens = censored_betti1(pts, free)
            rows.append({"gap": gap, "seed": seed, "n_points": len(pts),
                         "n_free_segments": len(free),
                         "betti1_plain": plain, "betti1_censored": cens})
            tmp = OUT + ".tmp"
            with open(tmp, "w") as f:
                json.dump(rows, f, indent=1)
            os.replace(tmp, OUT)
            print(f"gap={gap} seed={seed}: plain={plain} censored={cens} "
                  f"(pts {len(pts)}, free {len(free)})", flush=True)
    print("\n===== summary (true beta1 = 1 at gap 0, else 0) =====")
    for gap in GAPS:
        pl = [r["betti1_plain"] for r in rows if r["gap"] == gap]
        ce = [r["betti1_censored"] for r in rows if r["gap"] == gap]
        print(f"gap={gap}: plain={pl} censored={ce}")


if __name__ == "__main__":
    sys.exit(selftest()) if "--selftest" in sys.argv else main()
