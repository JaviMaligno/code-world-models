"""T8 validation: the linking dichotomy for the non-separating mode
(docs/paper3/THEORY.md, "T8 - the linking dichotomy").

Machine checks of the proved statements:
  1. Lemma X oracle: on random polylines with steps <= Delta, whenever a
     (densely sampled) interpolation point has g <= rho_t - Delta/2, some
     landing lies in the closed tube.
  2. The witnesses of Theorem T8(b): three explicit landing-free routes -
     aligned-thread, offset-thread, offset-around - all keep g > rho_t at
     every landing, and their threading numbers (signed crossings of the
     spanning disc D) are +1, +1, 0.
  3. thread = linking: each witness closed by a far arc, Gauss linking
     integral against the core circle, must round to the thread count.
  4. Corridor corollary T8(d): min over the straight start->phantom
     segment of g equals |o - R_c| exactly; the registered offset 1.5
     sits AT the boundary rho_t - Delta/2 = 0.5.
  5. Real dynamics T8(c): random episodes never place a real position in
     the tube (freeze invariant), and every real-path crossing of D goes
     through the clearance sub-disc D_m.

Run: PYTHONPATH=src python scripts/t8_linking_dichotomy.py   (~40 s CPU)
"""
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import TubeField3D

t0 = time.time()
out = {}
ENV0 = TubeField3D()                      # aligned: core_yz = (0, 0)
ENV15 = TubeField3D(core_yz=(1.5, 0.0))   # the registered offset
RHO = ENV0.tube_radius
DELTA = (ENV0.gain / ENV0.drag) * ENV0.dt          # max step length = 1.0
M = RHO - DELTA / 2                                 # clearance margin 0.5
CX, RC = ENV0.core_x, ENV0.core_radius


def subdivide(waypoints, step):
    """Polyline through the waypoints with segments <= step."""
    pts = [tuple(waypoints[0])]
    for a, b in zip(waypoints, waypoints[1:]):
        d = math.dist(a, b)
        n = max(1, math.ceil(d / step))
        for k in range(1, n + 1):
            pts.append(tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)))
    return pts


def thread_count(pts, env):
    """Signed crossings of the open spanning disc D = {x=c_x, dyz<R_c}."""
    n = 0
    for a, b in zip(pts, pts[1:]):
        if (a[0] - CX) * (b[0] - CX) < 0:
            t = (CX - a[0]) / (b[0] - a[0])
            q = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            dyz = math.hypot(q[1] - env.core_yz[0], q[2] - env.core_yz[1])
            if dyz < RC:
                n += 1 if b[0] > a[0] else -1
    return n


def gauss_link(loop_pts, env, n_core=720):
    """Gauss linking integral of a closed polyline against the core circle
    (independent check that thread = linking)."""
    core = []
    for k in range(n_core):
        th = 2 * math.pi * k / n_core
        core.append((CX, env.core_yz[0] + RC * math.cos(th),
                     env.core_yz[1] + RC * math.sin(th)))
    total = 0.0
    for a1, b1 in zip(loop_pts, loop_pts[1:]):
        m1 = tuple((a + b) / 2 for a, b in zip(a1, b1))
        d1 = tuple(b - a for a, b in zip(a1, b1))
        for j in range(n_core):
            a2, b2 = core[j], core[(j + 1) % n_core]
            m2 = tuple((a + b) / 2 for a, b in zip(a2, b2))
            d2 = tuple(b - a for a, b in zip(a2, b2))
            r = tuple(p - q for p, q in zip(m1, m2))
            rn = math.sqrt(sum(c * c for c in r)) ** 3
            cross = (d1[1] * d2[2] - d1[2] * d2[1],
                     d1[2] * d2[0] - d1[0] * d2[2],
                     d1[0] * d2[1] - d1[1] * d2[0])
            total += sum(a * b for a, b in zip(r, cross)) / rn
    return total / (4 * math.pi)


# ------------------------------------------------------------ 1. Lemma X
rng = random.Random(8001)
checked = triggered = 0
for _ in range(400):
    o = rng.uniform(-2, 2)
    env = TubeField3D(core_yz=(o, 0.0))
    pts = [(rng.uniform(4, 12), rng.uniform(-4, 4), rng.uniform(-4, 4))]
    for _ in range(30):
        v = [rng.uniform(-1, 1) for _ in range(3)]
        nv = math.sqrt(sum(c * c for c in v)) or 1.0
        step = rng.uniform(0, DELTA)
        pts.append(tuple(p + c / nv * step for p, c in zip(pts[-1], v)))
    # dense interpolation scan (conservative oracle for the hypothesis)
    hit_shrunken = False
    for a, b in zip(pts, pts[1:]):
        for k in range(21):
            q = tuple(a[i] + (b[i] - a[i]) * k / 20 for i in range(3))
            if env.dist_core(q) <= RHO - DELTA / 2:
                hit_shrunken = True
    checked += 1
    if hit_shrunken:
        triggered += 1
        assert any(env.dist_core(p) <= RHO for p in pts), "Lemma X violated"
out["lemma_X"] = {"polylines": checked, "hypothesis_triggered": triggered}
print(f"Lemma X oracle: {triggered}/{checked} polylines triggered the "
      f"hypothesis; conclusion held in all")

# ------------------------------------------- 2+3. witnesses and their lk
WITNESSES = {
    "aligned_thread": (ENV0, [(0, 0, 0), (12, 0, 0)], 1),
    "offset_thread": (ENV15, [(0, 0, 0), (0, 1.5, 0), (12, 1.5, 0),
                              (12, 0, 0)], 1),
    "offset_around": (ENV15, [(0, 0, 0), (0, 6, 0), (12, 6, 0),
                              (12, 0, 0)], 0),
}
wit = {}
for name, (env, route, expect) in WITNESSES.items():
    # generic subdivision (0.97*Delta) so no landing sits exactly on the
    # plane x = c_x -- the transversality caveat of the thread definition
    pts = subdivide(route, 0.97 * DELTA)
    assert all(abs(p[0] - CX) > 1e-9 for p in pts), name
    clear = min(env.dist_core(p) for p in pts)
    assert clear > RHO, (name, clear)                 # landing-free
    th = thread_count(pts, env)
    assert th == expect, (name, th, expect)
    # close by a far arc and Gauss-integrate
    loop = pts + subdivide([pts[-1], (12, 20, 0), (0, 20, 0), pts[0]],
                           0.5)[1:]
    lk = gauss_link(loop, env)
    assert abs(lk - expect) < 0.02, (name, lk, expect)
    wit[name] = {"landings": len(pts), "min_g": clear, "thread": th,
                 "gauss_lk": lk}
    print(f"witness {name}: min g = {clear:.3f} > {RHO}, thread = {th}, "
          f"Gauss lk = {lk:.4f}")
out["witnesses"] = wit

# --------------------------------------------------- 4. corridor minima
corr = []
for o in [0.0, 0.5, 1.0, 1.5, 1.75, 2.0]:
    env = TubeField3D(core_yz=(o, 0.0))
    # analytic minimum of g along the straight segment is at x = c_x
    ming = env.dist_core((CX, 0.0, 0.0))
    assert abs(ming - abs(o - RC)) < 1e-12, (o, ming)
    grid = min(env.dist_core((t / 50 * 12, 0.0, 0.0)) for t in range(51))
    assert grid >= ming - 1e-12
    corr.append({"offset": o, "min_g_straight": ming,
                 "queries_forced_in_corridor": ming < M})
out["corridor"] = {"margin": M, "rows": corr}
print("corridor: min g over straight segment = |o - R_c| exactly; "
      f"o=1.5 -> 0.5 = margin (degenerate boundary), o=1.75 -> 0.25 < {M}")

# ------------------------------------------------- 5. real dynamics (c)
real = {}
# random arm exercises the freeze invariant; the east-biased arm forces
# many plane crossings so Lemma Y on real paths is tested non-vacuously
for name, env, ax_lo in [("aligned", ENV0, -ENV0.a_max),
                         ("offset15", ENV15, -ENV15.a_max),
                         ("aligned_east", ENV0, 0.3),
                         ("offset15_east", ENV15, 0.3)]:
    in_tube = d_cross_out = 0
    threads = []
    crossing_dyz = []
    for i in range(300):
        rng = random.Random(90_000 + i)
        s = env.initial_state(rng)
        pos = [s[:3]]
        for _ in range(env.h_episode):
            a = (rng.uniform(ax_lo, env.a_max),
                 rng.uniform(-env.a_max, env.a_max),
                 rng.uniform(-env.a_max, env.a_max))
            s, _, _ = env.step(s, a)
            pos.append(s[:3])
        if any(env.dist_core(p) <= RHO for p in pos):
            in_tube += 1
        for p, q in zip(pos, pos[1:]):
            if (p[0] - CX) * (q[0] - CX) < 0:
                t = (CX - p[0]) / (q[0] - p[0])
                w = tuple(p[i] + (q[i] - p[i]) * t for i in range(3))
                dyz = math.hypot(w[1] - env.core_yz[0], w[2] - env.core_yz[1])
                crossing_dyz.append(dyz)
                if RC - M <= dyz <= RC:      # D outside the clearance disc
                    d_cross_out += 1
        threads.append(thread_count(pos, env))
    assert in_tube == 0, "freeze invariant violated"
    assert d_cross_out == 0, "Lemma Y violated on real paths"
    real[name] = {"episodes": 300, "real_positions_in_tube": in_tube,
                  "D_crossings_outside_clearance": d_cross_out,
                  "n_plane_crossings": len(crossing_dyz),
                  "thread_nonzero_rate":
                      sum(1 for t in threads if t != 0) / 300}
    print(f"real {name}: 0 positions in tube, 0 D-crossings outside "
          f"clearance ({len(crossing_dyz)} plane crossings), "
          f"thread!=0 rate {real[name]['thread_nonzero_rate']:.3f}")
out["real_dynamics"] = real

path = pathlib.Path("results/t8_linking_dichotomy.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  ({time.time() - t0:.0f}s)")
