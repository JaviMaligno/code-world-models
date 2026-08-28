"""TDA arm, first measurement: can the CONTACT SET reveal the mode's
topology — and whose topology does it actually carry? (paper 3 §4.3)

Contact evidence per transition = the refuted integrator landing (what a
repair loop sees as a failure; what mitigation fences). Clouds from random
rollouts on three configurations:

  ring_out   RingField2D gap=0, start outside  — mode has beta1 = 1
  disc_out   PatchField2D single patch R=5 at the same center, start outside
             — mode has beta1 = 0, same outer radius
  ring_in    RingField2D gap=0, start inside   — same beta1 = 1 mode,
             evidence now lands on the INNER boundary

Prediction (reachability-relative topology, §2): ring_out and disc_out are
topologically INDISTINGUISHABLE from their evidence — both clouds are the
reachable west-facing arc of the same circle (this is why paper 2's
dimensional reduction to a half-plane is *rational given the evidence*);
ring_in recovers beta1 = 1 once N clears the coverage threshold (the
NSW-style density condition, A.1). Detector pre-registered in
`cwm.continuous.tda.betti1_estimate` (3 x median-NN persistence threshold),
dedupe grid 0.05, subsample cap 90.

Run: PYTHONPATH=src python scripts/ring2d_tda_probe.py   (~5-10 min CPU)
"""
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import PatchField2D, RingField2D
from cwm.continuous.tda import betti1_estimate, dedupe, subsample

N_SWEEP = [40, 160, 640, 2560]
CAP = 90
CONFIGS = {
    "ring_out": RingField2D(),
    "disc_out": PatchField2D(p1=(12.0, 0.0), p2=None, R=5.0),
    "ring_in": RingField2D(x0_center=(12.0, 0.0)),
}
CENTER = (12.0, 0.0)


def contact_cloud(env, n_rollouts, seed):
    pts = []
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            x2, y2, _, _ = env._integrate(s, a)
            s2, _, c = env.step(s, a)
            if c:
                pts.append((x2, y2))    # the refuted landing
            s = s2
    return pts


def angular_coverage(points):
    """Diagnostic only (uses the known center — the detector does not):
    fraction of 36 angular bins around CENTER hit by the cloud."""
    bins = set()
    for x, y in points:
        ang = math.atan2(y - CENTER[1], x - CENTER[0]) % (2 * math.pi)
        bins.add(int(ang / (2 * math.pi) * 36))
    return len(bins) / 36


t0 = time.time()
rows = []
print(f"{'config':>9} {'N':>5} {'raw':>6} {'dedup':>6} {'used':>5} "
      f"{'b1':>3} {'top_pers':>18} {'ang_cov':>7}", flush=True)
for name, env in CONFIGS.items():
    for n in N_SWEEP:
        raw = contact_cloud(env, n, seed=70_000)
        dd = dedupe(raw, grid=0.05)
        pts = subsample(dd, CAP, seed=1)
        est = (betti1_estimate(pts) if len(pts) >= 4
               else {"betti1": 0, "tau": None, "n_points": len(pts),
                     "top_persistence": []})
        cov = angular_coverage(dd)
        row = {"config": name, "n_rollouts": n, "raw_contacts": len(raw),
               "deduped": len(dd), "used": len(pts),
               "betti1": est["betti1"], "tau": est["tau"],
               "top_persistence": est["top_persistence"],
               "angular_coverage": cov}
        rows.append(row)
        tp = ",".join(f"{p:.3f}" if p != float("inf") else "inf"
                      for p in est["top_persistence"]) or "-"
        print(f"{name:>9} {n:>5} {len(raw):>6} {len(dd):>6} {len(pts):>5} "
              f"{est['betti1']:>3} {tp:>18} {cov:>7.2f}", flush=True)

out = {"script": "ring2d_tda_probe.py",
       "detector": "betti1_estimate factor=3.0, dedupe 0.05, cap 90",
       "rows": rows, "elapsed_s": round(time.time() - t0, 1)}
path = pathlib.Path("results/continuous_ring2d_tda_probe.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
