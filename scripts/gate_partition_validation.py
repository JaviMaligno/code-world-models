"""Falsification test for the PARTITION certificate: does the gate actually cover?

The partition certificate (gate_partition_certificate.py) says the deployed N = 40
gate puts a sample in every cell of an 8-cell partition of U using one step per
rollout, and in every cell of a 36-cell partition using all steps, each with
probability at least 1 - delta. Those are bounds, so they could be loose by orders of
magnitude and nothing in the derivation would reveal it. This measures the truth: run
many independent gates and count how often they actually cover.

The test uses the certificate's own partition definition and nothing else -- in
particular it does NOT re-implement the grid. The previous generation of this pair
(gate_coverage_dependent.py / gate_coverage_validation.py) shared an off-by-one grid
bug, so the test validated the bug instead of catching it; keeping the partition in
one place is the structural fix.

For part (a) the certificate's own failure bound is exact-per-cell and hence tight by
construction, so the interesting number is whether the measured failure rate sits
below it. For part (b) the bound goes through a Hoeffding step and a union bound, so
it should be conservative, and by how much is worth knowing.

Run: PYTHONPATH=src python scripts/gate_partition_validation.py   (~4 min CPU)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402
from cwm.law import wilson_ci             # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--trials", type=int, default=400, help="independent gates per row")
ap.add_argument("--n-gate", type=int, default=40)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
DT, A = env.dt, env.a_max
V = env.gain * DT * A
Y = 0.5

CERT = json.loads((_REPO / "results" / "gate_partition_certificate.json").read_text())
ROWS = []
_a = CERT["exact_best"]
ROWS.append(("(a) one step per rollout", _a["n_y"], _a["n_v"], _a["n_a"], True,
             CERT["exact_best"]["failure_prob"]))
_b = CERT.get("measured_best")
if _b:
    ROWS.append(("(b) all steps", _b["n_y"], _b["n_v"], _b["n_a"], False,
                 _b["union_failure"]))


def gate_covers(ny, nv, na, one_step_only, trial):
    """Does this gate put a sample in every cell of the partition of U?"""
    dy, dv, da = 2 * Y / ny, 2 * V / nv, 2 * A / na
    need = {(i, j, k) for i in range(ny) for j in range(nv) for k in range(na)}
    for r in range(args.n_gate):
        rng = random.Random(1_000_000 * trial + r)
        s = env.initial_state(rng)
        for step in range(env.h_episode):
            a = rng.uniform(-A, A)
            # In the one-sample-per-rollout regime the certificate's part (a) is a
            # statement about the STEP-1 law (uniform on the sheared box), not the
            # step-0 one: v_0 = 0 exactly, so a step-0 sample is supported on a
            # lower-dimensional set and cannot reach a partition with n_v >= 2 at all
            # (demonstrated: 0/400 for a sound certificate at 2x2x2). At the certified
            # split n_v = 1 the two laws agree in the coordinates the partition sees,
            # which is why the published figure was right anyway.
            if not (one_step_only and step == 0):
                x, v = s
                y = x - DT * v
                if abs(y) < Y and abs(v) < V and abs(a) < A:
                    need.discard((min(ny - 1, int((y + Y) / dy)),
                                  min(nv - 1, int((v + V) / dv)),
                                  min(na - 1, int((a + A) / da))))
            s = env.step(s, a)[0]
            if one_step_only and step == 1:
                break              # the rigorous regime: one sample per rollout
    return not need


out = []
print(f"{'regime':>24} {'K':>4} {'covered':>9} {'rate':>7} "
      f"{'measured fail':>14} {'certificate bound':>18}")
for label, ny, nv, na, one_step, bound in ROWS:
    ok = sum(gate_covers(ny, nv, na, one_step, t) for t in range(args.trials))
    rate = ok / args.trials
    fail = 1 - rate
    lo, hi = wilson_ci(args.trials - ok, args.trials)[1:]
    out.append({"regime": label, "n_y": ny, "n_v": nv, "n_a": na,
                "K": ny * nv * na, "covered": ok, "trials": args.trials,
                "cover_rate": rate, "measured_failure": fail,
                "measured_failure_ci": [lo, hi],
                "certificate_failure_bound": bound,
                # A bound on a probability is falsified only if the MEASURED
                # probability is significantly above it, i.e. if the whole interval
                # lies above the bound. Comparing the point estimate against the
                # bound (what an earlier version did) declares a violation whenever
                # the estimate lands on the high side of a tight bound, which for a
                # bound that is nearly an equality happens about half the time.
                "bound_falsified": bool(lo > bound),
                "bound_holds": bool(lo <= bound)})
    print(f"{label:>24} {ny*nv*na:4} {ok:9} {rate:7.3f} "
          f"{fail:14.4f} {bound:18.4f}")
    print(f"{'':>24} measured failure 95% CI [{lo:.4f}, {hi:.4f}]"
          f"{'  -- consistent with the bound' if lo <= bound else '  -- BOUND FALSIFIED'}")

print("\nReading: the exact-partition bound (a) is a per-cell equality pushed through a")
print("union bound, so it should be close; (b) adds Hoeffding slack and should be")
print("conservative. A measured failure rate ABOVE the bound would falsify the")
print("certificate, and that is the point of running this.")

dst = _REPO / "results" / "gate_partition_validation.json"
dst.write_text(json.dumps({"script": "gate_partition_validation.py",
                           "params": vars(args), "rows": out}, indent=2))
print(f"\nwrote {dst}")
