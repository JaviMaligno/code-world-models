"""T7 (second half): the relative evidence estimator, measured against
plain Rips and the censored filtration
(docs/paper3/THEORY.md, "T7 (second half)": Propositions R1/R2/R3).

Estimator: rank ker(H0(VR(free paths)) -> H0(VR(contact + free paths))),
i.e. how many certified-free components the contact evidence glues
together. Equals rank H1(K, L) when H1(K) = 0 (Prop R2), and has no
infinite bars by construction (Prop R1) — the pathology that sank naive
edge censoring.

The experiment has two arms, because Proposition R3 predicts they differ:
  - ONE-SIDED (inside starts only, the committed censored-filtration
    setting): the interior is reach-null at gamma = 0, so no evidence
    exists outside; enclosure is then GAUGE and no estimator can see it.
    Prediction: the estimator reports 0 everywhere, including gamma = 0.
  - TWO-SIDED (inside AND outside starts pooled): both sides are
    witnessed, so enclosure is identifiable. Prediction: 1 at gamma = 0,
    0 at every gamma > 0 — the answer plain Rips gets wrong.

Free evidence enters as PATHS (per-rollout position polylines), not a
point cloud: consecutive samples on one trajectory are joined at scale 0
because the trajectory itself certifies free passage between them. Path
subsampling is therefore lossless for the connectivity certificate.

Run: PYTHONPATH=src python scripts/t7_relative_estimator.py  (~2 min)
"""
import json
import math
import os
import pathlib
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import RingField2D                     # noqa: E402
from cwm.continuous.contract import collect_transitions         # noqa: E402
from cwm.continuous.tda import (betti1_estimate, dedupe,        # noqa: E402
                                relative_betti1_estimate, subsample)

GAPS = [0.0, 0.6, 1.2, 1.8, 2.4]
SEEDS = [10000, 20000, 30000, 40000, 50000]
CAP = 90            # the pre-registered contact budget, unchanged
PATH_STRIDE = 10    # keep every 10th position along each free polyline
OUT = "results/t7_relative_estimator.json"
t0 = time.time()


def evidence(env, seed, n_roll=40):
    """Contact landings, and free polylines (one path per rollout).

    `collect_transitions` returns a flat transition list; a new rollout
    starts wherever the next transition's state is not the previous
    transition's next_state, which is how we cut the paths.
    """
    landings, paths, cur = [], [], []
    prev_next = None
    for tr in collect_transitions(env, n_roll, seed=seed):
        s, ns = tr["state"], tr["next_state"]
        if prev_next is None or (s[0], s[1]) != (prev_next[0], prev_next[1]):
            if len(cur) > 1:
                paths.append(cur)
            cur = [(s[0], s[1])]
        cur.append((ns[0], ns[1]))
        prev_next = ns
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(s, tr["action"])
            landings.append((x2, y2))
    if len(cur) > 1:
        paths.append(cur)
    paths = [p[::PATH_STRIDE] if len(p) > PATH_STRIDE else [p[0], p[-1]]
             for p in paths]
    return landings, paths


def main():
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["gap"], r["seed"], r["arm"]) for r in rows}
    for gap in GAPS:
        inside = RingField2D(gap=gap, gap_center=math.pi,
                             x0_center=RingField2D().center)
        outside = RingField2D(gap=gap, gap_center=math.pi)
        for seed in SEEDS:
            for arm in ("one_sided", "two_sided"):
                if (gap, seed, arm) in done:
                    continue
                land_i, path_i = evidence(inside, seed)
                if arm == "one_sided":
                    land, paths = land_i, path_i
                else:
                    land_o, path_o = evidence(outside, seed + 7)
                    land, paths = land_i + land_o, path_i + path_o
                pts = subsample(dedupe(land, 0.05), CAP, 0)
                if len(pts) < 4:
                    continue
                plain = betti1_estimate(pts)["betti1"]
                rel = relative_betti1_estimate(pts, paths)
                rows.append({"gap": gap, "seed": seed, "arm": arm,
                             "n_contact": len(pts),
                             "n_free_paths": len(paths),
                             "n_free_pts": rel["n_free"],
                             "betti1_plain": plain,
                             "betti1_rel": rel["betti1_rel"],
                             "max_rank": rel["max_rank"],
                             "n_bars": len(rel["bars"])})
                tmp = OUT + ".tmp"
                with open(tmp, "w") as fh:
                    json.dump(rows, fh, indent=1)
                os.replace(tmp, OUT)
                print(f"gap={gap} seed={seed} {arm}: plain={plain} "
                      f"rel={rel['betti1_rel']} (maxrank {rel['max_rank']}, "
                      f"{len(rel['bars'])} finite bars)", flush=True)

    print("\n===== summary (true beta1 = 1 at gap 0, else 0) =====")
    for arm in ("one_sided", "two_sided"):
        for gap in GAPS:
            sel = [r for r in rows if r["gap"] == gap and r["arm"] == arm]
            pl = [r["betti1_plain"] for r in sel]
            re = [r["betti1_rel"] for r in sel]
            truth = 1 if gap == 0.0 else 0
            print(f"{arm:10s} gap={gap}: plain={pl} rel={re} "
                  f"(rel correct {sum(1 for v in re if v == truth)}/{len(re)})")
    # Proposition R1 is structural: no run may produce an infinite bar.
    # free_merge_persistence asserts it internally; reaching here confirms it.
    print("\nProposition R1 (no infinite relative bars): held in all cells")
    pathlib.Path(OUT).write_text(json.dumps(rows, indent=1))
    print(f"wrote {OUT}  ({time.time() - t0:.0f}s)")


def shell_geometry_arm():
    """Proposition R4: freeze evidence hugs the two band faces, so the
    relative bar's length saturates while tau grows with the sample.
    Run: PYTHONPATH=src python scripts/t7_relative_estimator.py --r4
    """
    from cwm.continuous.tda import free_merge_persistence, median_nn_distance
    C = RingField2D().center
    rows = []
    for n_roll in (40, 120, 320):
        inside = RingField2D(gap=0.0, gap_center=math.pi, x0_center=C)
        # a start distribution reaching the OUTER face, so the evidence is
        # two-faced (random rollouts from far away almost never contact)
        near = RingField2D(gap=0.0, gap_center=math.pi,
                           x0_center=(C[0] - 6.5, 0.0))
        li, pi_ = evidence(inside, 10000, n_roll=n_roll)
        lo, po = evidence(near, 10007, n_roll=n_roll)
        pts = subsample(dedupe(li + lo, 0.05), CAP, 0)
        res = free_merge_persistence(pts, pi_ + po)
        tau = 3 * median_nn_distance(pts)
        ri = [math.hypot(p[0] - C[0], p[1] - C[1]) for p in li]
        ro = [math.hypot(p[0] - C[0], p[1] - C[1]) for p in lo]
        longest = max((b[1] - b[0] for b in res["bars"]), default=0.0)
        rows.append({"n_roll": n_roll, "n_contacts": len(li) + len(lo),
                     "inner_shell": [min(ri), max(ri)],
                     "outer_shell": [min(ro), max(ro)],
                     "longest_bar": longest, "tau": tau,
                     "fires": longest > tau})
        print(f"n_roll={n_roll:3d}: inner [{min(ri):.2f},{max(ri):.2f}] "
              f"outer [{min(ro):.2f},{max(ro):.2f}] longest bar "
              f"{longest:.3f} vs tau {tau:.3f} -> "
              f"{'fires' if longest > tau else 'sub-threshold'}", flush=True)
    assert not any(r["fires"] for r in rows), "R4 predicts sub-threshold"
    assert rows[-1]["tau"] / rows[0]["tau"] > rows[-1]["longest_bar"] / \
        rows[0]["longest_bar"], "R4 predicts tau grows faster than the bar"
    print("\nProposition R4 confirmed: the bar saturates (shell-limited) "
          "while tau grows — more evidence makes gamma=0 harder, so no "
          "threshold calibration recovers it.")
    p = pathlib.Path("results/t7_shell_geometry.json")
    p.write_text(json.dumps(rows, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    if "--r4" in sys.argv:
        shell_geometry_arm()
    else:
        main()
