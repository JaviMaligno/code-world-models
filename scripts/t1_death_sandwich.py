"""T1 death sandwich: validate Lemma D+ (the filling lemma) and the
two-sided detector law on the sensor factorial
(docs/paper3/THEORY.md, "T1 - the proofs": Lemmas B, D-, D+).

Per row of results/ring2d_sensor_resolution.json: rebuild the exact
detector cloud, compute the H1 barcode, identify the winding bar (birth
inside Lemma B's interval, maximal persistence), and check
    D- = sqrt(3)*r_min  <=  death  <=  D+ = 2*r_max*sin(theta*/2)
with theta* from Lemma D+'s two regimes (hypothesis (H) checked per
sample). Also classify each row by the two-sided law (guaranteed-1 /
guaranteed-0 / undecided) and compare with the detector's report.

Run: PYTHONPATH=src python scripts/t1_death_sandwich.py   (~2 min CPU)
"""
import json
import math
import pathlib
import time

from cwm.continuous.envs import RingField2D
from cwm.continuous.contract import collect_transitions
from cwm.continuous.tda import dedupe, rips_persistence, subsample

t0 = time.time()
SQ3 = math.sqrt(3)


def cloud_for(row):
    env = RingField2D(gap=row["gap"], gap_center=math.pi,
                      x0_center=RingField2D().center)
    pts = []
    for tr in collect_transitions(env, row["n_rollouts"], seed=row["seed"]):
        if tr["contact"]:
            x2, y2, _, _ = env._integrate(tr["state"], tr["action"])
            pts.append((x2, y2))
    return subsample(dedupe(pts, 0.05), row["cap"], 0)


def geometry(pts):
    radii = [math.hypot(p[0] - 12, p[1]) for p in pts]
    angs = sorted(math.atan2(p[1], p[0] - 12) % (2 * math.pi) for p in pts)
    gaps = sorted((b - a for a, b in zip(angs, angs[1:])), reverse=True)
    gaps.append(angs[0] + 2 * math.pi - angs[-1])
    gaps.sort(reverse=True)
    return min(radii), max(radii), gaps[0], gaps[1]


def theta_star(dmax, d2):
    """Lemma D+ regimes; returns (theta*, applicable) with (H) checked."""
    cands = []
    if dmax <= 2 * math.pi / 3 and d2 < math.pi / 3:
        th = 2 * math.pi / 3 + d2
        if d2 <= th / 2:                       # (H), automatic here
            cands.append(th)
    if d2 < dmax < math.pi:
        th = max(dmax, (2 * math.pi - dmax) / 2 + d2 / 2)
        if d2 <= th / 2:                       # (H)
            cands.append(th)
    return (min(cands), True) if cands else (None, False)


rows = json.load(open("results/ring2d_sensor_resolution.json"))
out, sandwich_ok, bars_checked = [], 0, 0
g1_rows = g0_rows = g1_viol = g0_wind_viol = 0
for r in rows:
    pts = cloud_for(r)
    r_min, r_max, dmax, d2 = geometry(pts)
    b_lo = 2 * r_min * math.sin(min(dmax, math.pi) / 2)
    b_hi = 2 * r_max * math.sin(min(dmax, math.pi) / 2)
    d_lo = SQ3 * r_min
    th, ok = theta_star(dmax, d2)
    d_hi = 2 * r_max * math.sin(th / 2) if ok else 2 * r_max
    bars = rips_persistence(pts)["h1"]
    # Lemma P's window-uniqueness rank: #bars containing [B+, sqrt3*r_min)
    r0 = sum(1 for b, d in bars
             if b <= b_hi + 1e-9 and (d is None or d >= d_lo - 1e-9))
    # winding bar: birth inside Lemma B's interval (5% tolerance), longest
    wind = None
    for b, d in bars:
        if d is not None and 0.95 * b_lo <= b <= 1.05 * b_hi:
            if wind is None or (d - b) > (wind[1] - wind[0]):
                wind = (b, d)
    window_nonempty = b_hi < d_lo
    rec = {"gap": r["gap"], "cap": r["cap"], "n_rollouts": r["n_rollouts"],
           "seed": r["seed"], "r_min": round(r_min, 3),
           "r_max": round(r_max, 3), "dtheta_max": round(dmax, 3),
           "dtheta_2": round(d2, 3), "B": [round(b_lo, 3), round(b_hi, 3)],
           "D": [round(d_lo, 3), round(d_hi, 3)], "regime_ok": ok,
           "window_nonempty": window_nonempty, "r0": r0}
    if window_nonempty:
        # Lemma P(a): r0 >= 1; P(b)'s hypothesis: r0 == 1
        assert r0 >= 1, rec
        assert r0 == 1, rec
    if wind:
        bars_checked += 1
        good = d_lo - 1e-9 <= wind[1] <= d_hi + 1e-9
        sandwich_ok += good
        rec.update({"winding_bar": [round(wind[0], 3), round(wind[1], 3)],
                    "sandwich": good})
        assert good, rec
    # two-sided law classification vs the detector's report
    tau = r["tau"]
    if d_lo - b_hi > tau:
        g1_rows += 1
        if r["betti1"] < 1:
            g1_viol += 1
    elif ok and d_hi - b_lo < tau:
        g0_rows += 1
        # guaranteed: no persistent WINDING bar (spurious classes exempt)
        if wind and wind[1] - wind[0] > tau:
            g0_wind_viol += 1
        rec["guaranteed"] = "0"
    out.append(rec)
assert g1_viol == 0, g1_viol
assert g0_wind_viol == 0, g0_wind_viol
n_window = sum(1 for r in out if r["window_nonempty"])
print(f"Lemma P: r0 == 1 in {n_window}/{n_window} nonempty-window rows")
print(f"sandwich: {sandwich_ok}/{bars_checked} winding bars inside [D-, D+]")
print(f"two-sided law: guaranteed-1 rows {g1_rows} (0 violations), "
      f"guaranteed-0 rows {g0_rows} (0 winding violations), "
      f"undecided {len(rows) - g1_rows - g0_rows}")
path = pathlib.Path("results/t1_death_sandwich.json")
path.write_text(json.dumps({
    "sandwich": f"{sandwich_ok}/{bars_checked}",
    "guaranteed_1": g1_rows, "guaranteed_0": g0_rows,
    "undecided": len(rows) - g1_rows - g0_rows, "rows": out}, indent=1))
print(f"wrote {path}  ({time.time() - t0:.0f}s)")
