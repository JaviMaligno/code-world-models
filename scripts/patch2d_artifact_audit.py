"""Per-artifact behavioral audit of the PatchField2D synthesis arms.

Verifies the paper's hand-inspection claims (Section patch2d-synthesis: the
38/20/9/9 class split, ~74/76 integrator exactness, zero partial repair;
the square-ablation bidirectional template claim; the region/3x-budget
confound artifacts) with the same freeze-mask instrument used on paper 3's
ring (behavioral, not textual): probe each artifact's step() on a state grid,
mark deviations from the pure integrator (the freeze/mode set), classify the
set's SHAPE, and measure per-patch coverage.

Classes:
  invalid/crash   code does not execute / wrong arity
  blind           no deviation anywhere (both velocity slices)
  vdep            deviation only at nonzero velocity (velocity superstition)
  point           tiny deviation set (< ~0.5 world-units^2)
  halfplane       unbounded set (reaches the grid's far edges) - the
                  dimensional-reduction class
  disc-form       bounded, largest component round (bbox_fill ~ pi/4,
                  radial ratio ~ 1)
  square-form     bounded, largest component fills its bbox (~1.0)
  bounded-other   bounded but neither (ellipses, hulls, unions, arcs)

Textual sub-split for empty masks: mask-empty + a conditional in step()
=> "blind (textual patch)" (the paper's superstitious class: exact-coordinate
traps are measure-zero, hence behaviorally blind); mask-empty + no
conditional => pure blind.

Also: canonical blind-reference gate per cell (contract_accuracy of the pure
integrator+reward on the cell's exact regenerated evidence) and per-patch
mask coverage (behavioral partial-repair check).

Output: results/patch2d_artifact_audit.json + a stdout comparison against
the paper's claimed numbers. Pure CPU; deterministic; safe to re-run.
Self-test: `python scripts/patch2d_artifact_audit.py --selftest` classifies
constructed oracle artifacts (known class by construction) and asserts.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter, deque

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from cwm.continuous.envs import PatchField2D                    # noqa: E402
from cwm.continuous.contract import (collect_transitions,       # noqa: E402
                                     contract_accuracy)

DT, GAIN, DRAG, AMAX = 0.1, 3.0, 0.3, 1.0
GRID_N = 81
X_LO, X_HI, Y_LO, Y_HI = -2.0, 14.0, -8.0, 8.0
EPS_DEV = 1e-6
CELL_AREA = ((X_HI - X_LO) / (GRID_N - 1)) * ((Y_HI - Y_LO) / (GRID_N - 1))

BLIND_CODE = """
import math
def step(state, action):
    x, y, vx, vy = state
    a = min(1.0, max(-1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0*math.cos(phi) - 0.3*vx)*0.1
    vy2 = vy + (3.0*math.sin(phi) - 0.3*vy)*0.1
    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x+6.0, y)
    d2 = math.hypot(x-12.0, y)
    return 0.3/(1.0+math.exp((d1-2.0)/0.5)) + 1.0/(1.0+math.exp((d2-2.0)/0.5))
"""

RESULT_FILES = {
    # the 76-artifact base (disc)
    "disc_large_k3_7": "results/continuous_synthesis_patch2d_large_k3_7.json",
    "disc_mini_k3_7": "results/continuous_synthesis_patch2d_mini_k3_7.json",
    "disc_large_k5_9": "results/continuous_synthesis_patch2d_large_k5_9.json",
    "disc_mini_k5_9": "results/continuous_synthesis_patch2d_mini_k5_9.json",
    # the strongest-joint-treatment confound cells (region guidance + 3x)
    "region_it15_large": "results/continuous_synthesis_patch2d_large_k3_7_pv-region_it15.json",
    "region_it15_mini": "results/continuous_synthesis_patch2d_mini_k3_7_pv-region_it15.json",
    # the fixed-topology square ablation
    "square_large": "results/continuous_synthesis_patch2dsq_large_k3_7.json",
    "square_mini": "results/continuous_synthesis_patch2dsq_mini_k3_7.json",
}


def integrator_step(x, y, vx, vy, a):
    a = min(AMAX, max(-AMAX, a))
    phi = math.pi * a / AMAX
    vx2 = vx + (GAIN * math.cos(phi) - DRAG * vx) * DT
    vy2 = vy + (GAIN * math.sin(phi) - DRAG * vy) * DT
    return [x + vx2 * DT, y + vy2 * DT, vx2, vy2]


def _grid_xy(i, j):
    return (X_LO + (X_HI - X_LO) * i / (GRID_N - 1),
            Y_LO + (Y_HI - Y_LO) * j / (GRID_N - 1))


def _mask(step, vx, vy):
    """Boolean deviation grid at one velocity slice (action 0.3)."""
    m = [[False] * GRID_N for _ in range(GRID_N)]
    for i in range(GRID_N):
        for j in range(GRID_N):
            x, y = _grid_xy(i, j)
            got = step([x, y, vx, vy], 0.3)
            exp = integrator_step(x, y, vx, vy, 0.3)
            dev = max(abs(g - e) for g, e in zip(got, exp))
            if dev > EPS_DEV:
                m[i][j] = True
    return m


def _components(m):
    """Connected components (4-neighbour) of a boolean grid; list of point
    lists, largest first."""
    seen = [[False] * GRID_N for _ in range(GRID_N)]
    comps = []
    for i in range(GRID_N):
        for j in range(GRID_N):
            if m[i][j] and not seen[i][j]:
                comp, q = [], deque([(i, j)])
                seen[i][j] = True
                while q:
                    a, b = q.popleft()
                    comp.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if (0 <= na < GRID_N and 0 <= nb < GRID_N
                                and m[na][nb] and not seen[na][nb]):
                            seen[na][nb] = True
                            q.append((na, nb))
                comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


def _shape_metrics(comp):
    """bbox_fill and radial max/min ratio of a component (grid points)."""
    xs = [_grid_xy(i, j)[0] for i, j in comp]
    ys = [_grid_xy(i, j)[1] for i, j in comp]
    w = max(xs) - min(xs) + (X_HI - X_LO) / (GRID_N - 1)
    h = max(ys) - min(ys) + (Y_HI - Y_LO) / (GRID_N - 1)
    bbox_fill = len(comp) * CELL_AREA / (w * h) if w * h > 0 else 0.0
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    # radial extent per angular bin (16 bins; only bins with data)
    bins = {}
    for x, y in zip(xs, ys):
        r = math.hypot(x - cx, y - cy)
        b = int((math.atan2(y - cy, x - cx) % (2 * math.pi)) / (2 * math.pi) * 16)
        bins[b] = max(bins.get(b, 0.0), r)
    radii = [v for v in bins.values() if v > 0]
    ratio = (max(radii) / min(radii)) if radii and min(radii) > 0 else None
    return {"bbox_fill": round(bbox_fill, 3),
            "radial_ratio": round(ratio, 3) if ratio else None,
            "area_units": round(len(comp) * CELL_AREA, 2),
            "centroid": (round(cx, 2), round(cy, 2))}


def _touches_far_edge(comp):
    """Unbounded proxy: the component reaches the far-east column or the
    top/bottom rows of the probe window."""
    for i, j in comp:
        if i == GRID_N - 1 or j == 0 or j == GRID_N - 1:
            return True
    return False


def _step_has_conditional(code):
    """Textual marker: any `if` in the step() body (the pure integrator has
    none — its clamp is min/max)."""
    src = code.split("def step", 1)[-1]
    src = src.split("def reward", 1)[0]
    return " if " in src or "\n    if" in src or src.strip().startswith("if")


def audit_code(code, env):
    """Behavioral class + metrics of one artifact against the PatchField2D
    integrator. Returns a dict; env supplies the patch geometry for per-patch
    coverage."""
    ns = {}
    try:
        exec(code, ns)  # noqa: S102 — audited synthesis artifacts
        step = ns["step"]
        _probe = step([0.0, 0.0, 0.0, 0.0], 0.3)
        assert len(_probe) == 4
    except Exception:
        return {"class": "invalid"}
    try:
        m0 = _mask(step, 0.0, 0.0)
        m1 = _mask(step, 1.5, 0.5)
    except Exception:
        return {"class": "crash"}
    n0 = sum(r.count(True) for r in m0)
    n1 = sum(r.count(True) for r in m1)
    out = {"n_dev_v0": n0, "n_dev_v1": n1,
           "textual_patch": _step_has_conditional(code)}
    # per-patch behavioral coverage (v0 mask over the TRUE patch regions)
    for name, c in (("p1", env.p1), ("p2", env.p2)):
        tot = hit = 0
        for i in range(GRID_N):
            for j in range(GRID_N):
                x, y = _grid_xy(i, j)
                if env._inside(x, y, c):
                    tot += 1
                    if m0[i][j]:
                        hit += 1
        out[f"cover_{name}"] = round(hit / tot, 3) if tot else None
    # integrator check on the west control strip (x < 1, away from both
    # patches): a deviation there is only evidence of WRONG ARITHMETIC if it
    # is not freeze-form. Freeze-form deviations (position preserved,
    # velocity zeroed) are a mode RULE overreaching west — the integrator
    # itself is exact. (Refinement 2026-07-23: the crude any-deviation check
    # flagged 16/76; splitting by form leaves exactly 2 numeric — matching
    # the paper's hand-inspected ~74/76.)
    west_freeze = west_numeric = 0
    for i in range(GRID_N):
        for j in range(GRID_N):
            if not m0[i][j]:
                continue
            x, y = _grid_xy(i, j)
            if x >= 1.0:
                continue
            got = step([x, y, 0.0, 0.0], 0.3)
            if (abs(got[0] - x) < 1e-9 and abs(got[1] - y) < 1e-9
                    and abs(got[2]) < 1e-9 and abs(got[3]) < 1e-9):
                west_freeze += 1
            else:
                west_numeric += 1
    out["west_control_dev"] = west_freeze + west_numeric
    out["west_numeric_dev"] = west_numeric
    out["integrator_exact"] = (west_numeric == 0)
    if n0 == 0 and n1 == 0:
        out["class"] = ("blind-textual-patch" if out["textual_patch"]
                        else "blind")
        return out
    if n0 == 0:
        out["class"] = "vdep"
        return out
    comps = _components(m0)
    main = comps[0]
    out["n_components"] = len([c for c in comps if len(c) >= 4])
    if len(main) * CELL_AREA < 0.5:
        out["class"] = "point"
        return out
    if _touches_far_edge(main):
        out["class"] = "halfplane"
        out["area_frac"] = round(n0 / (GRID_N * GRID_N), 3)
        return out
    sm = _shape_metrics(main)
    out.update(sm)
    if sm["bbox_fill"] >= 0.90:
        out["class"] = "square-form"
    elif 0.62 <= sm["bbox_fill"] < 0.90 and (sm["radial_ratio"] or 9) <= 1.30:
        out["class"] = "disc-form"
    else:
        out["class"] = "bounded-other"
    return out


def env_for(tag, params):
    shape = "square" if "square" in tag or "patch2dsq" in tag else "disc"
    k1 = params.get("k1", 3.0) or 3.0
    k2 = params.get("k2", 7.0) or 7.0
    return PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0), patch_shape=shape)


def main():
    out = {"files": {}}
    blind_cache = {}
    for tag, path in RESULT_FILES.items():
        if not os.path.exists(path):
            print(f"[skip] {tag}: missing {path}")
            continue
        raw = json.load(open(path))
        env = env_for(tag, raw.get("params", {}) or {})
        rows = []
        for c in raw["cells"]:
            if c.get("arm") != "incomplete":
                continue
            bkey = (tag.split("_")[0], env.p1, env.p2, c["seed"])
            if bkey not in blind_cache:
                tr = collect_transitions(env, c.get("n_rollouts", 40),
                                         seed=c["seed"])
                blind_cache[bkey] = contract_accuracy(
                    BLIND_CODE, tr, c.get("eps", 1e-9))[0]
            a = audit_code(c["code"], env)
            rows.append({
                "seed": c["seed"],
                "modes_in_sample": c.get("sample_contains_mode_per"),
                "any_mode": c["sample_contains_wall"],
                "gate_accuracy": c["gate_accuracy"],
                "gate_passed": c["gate_passed"],
                "blind_ref_gate": blind_cache[bkey],
                **a,
            })
        agg_all = Counter(r["class"] for r in rows)
        present = [r for r in rows if r["any_mode"]]
        agg_present = Counter(r["class"] for r in present)
        integ = sum(1 for r in present if r.get("integrator_exact"))
        out["files"][tag] = {"path": path, "cells": rows,
                             "aggregates": {
                                 "n": len(rows),
                                 "classes_all": dict(agg_all),
                                 "n_mode_present": len(present),
                                 "classes_mode_present": dict(agg_present),
                                 "integrator_exact_present": integ,
                             }}
        print(f"{tag}: n={len(rows)} present={len(present)} "
              f"classes(present)={dict(agg_present)} integ_exact={integ}")

    dst = "results/patch2d_artifact_audit.json"
    tmp = dst + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, dst)
    print(f"wrote {dst}")

    # ---- comparison against the paper's claimed numbers (disc base) ----
    disc = [r for t in ("disc_large_k3_7", "disc_mini_k3_7",
                        "disc_large_k5_9", "disc_mini_k5_9")
            if t in out["files"] for r in out["files"][t]["cells"]
            if r["any_mode"]]
    cls = Counter(r["class"] for r in disc)
    integ = sum(1 for r in disc if r.get("integrator_exact"))
    print("\n===== 76-artifact base vs paper claims =====")
    print(f"n mode-present: {len(disc)}   (paper: 76)")
    print(f"halfplane (dimensional reduction): {cls.get('halfplane', 0)}"
          f"   (paper: 38)")
    print(f"pure blind: {cls.get('blind', 0)} + blind-textual-patch: "
          f"{cls.get('blind-textual-patch', 0)} + point: {cls.get('point', 0)}"
          f" + vdep: {cls.get('vdep', 0)}   (paper: 20 blind + 9 superstitious)")
    print(f"disc-form: {cls.get('disc-form', 0)}   (paper: 9)")
    print(f"square-form/bounded-other: {cls.get('square-form', 0)}/"
          f"{cls.get('bounded-other', 0)}")
    print(f"integrator exact: {integ}/{len(disc)}   (paper: ~74/76)")
    # behavioral partial-repair check: any see-one artifact covering the
    # SEEN patch's region substantially?
    partial = 0
    for r in disc:
        per = r.get("modes_in_sample") or {}
        for pname in ("p1", "p2"):
            if per.get(pname) and (r.get(f"cover_{pname}") or 0) > 0.9:
                partial += 1
                break
    print(f"artifacts covering a seen patch >90% behaviorally: {partial} "
          f"(paper: 0 partial-repair certificates; gate-level)")


# ---------------- oracle self-test (constructed classes) -----------------
_INTEG = BLIND_CODE


def _with_freeze(cond):
    return _INTEG.replace(
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
        f"    if {cond}:\n        return [x, y, 0.0, 0.0]\n"
        f"    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]")


def selftest():
    env = PatchField2D()
    cases = {
        "blind": _INTEG,
        "halfplane": _with_freeze("x >= 4.0"),
        "disc-form": _with_freeze("(x-3.0)**2 + (y-0.0)**2 <= 1.0"),
        "square-form": _with_freeze("max(abs(x-3.0), abs(y-0.0)) <= 1.0"),
        "vdep": _INTEG.replace(
            "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
            "    if math.hypot(vx2, vy2) > 1.0:\n"
            "        return [x, y, 0.0, 0.0]\n"
            "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]"),
        "point": _with_freeze("abs(x - 3.0) <= 0.05 and abs(y) <= 0.05"),
        "blind-textual-patch": _with_freeze(
            "abs(x - 3.123456789) <= 1e-12 and abs(y) <= 1e-12"),
    }
    ok = True
    for expected, code in cases.items():
        got = audit_code(code, env)["class"]
        status = "ok" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"  [{status}] {expected:<20} -> {got}")
    # two-patch disc artifact: both components, cover both patches
    two = _with_freeze("(x-3.0)**2 + y**2 <= 1.0 or (x-7.0)**2 + y**2 <= 1.0")
    a = audit_code(two, env)
    print(f"  two-patch: class={a['class']} comps={a.get('n_components')} "
          f"cover_p1={a['cover_p1']} cover_p2={a['cover_p2']}")
    if not (a["cover_p1"] > 0.9 and a["cover_p2"] > 0.9
            and a.get("n_components") == 2):
        ok = False
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    sys.exit(selftest()) if args.selftest else main()
