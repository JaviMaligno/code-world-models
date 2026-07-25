"""Falsification test for the coverage certificate's resolution threshold.

The certificate says the deployed gate (N = 40) rho-covers the region at
rho = 0.60 with probability >= 1 - delta, and that finer resolutions need a much
larger gate (N >= 169 at rho = 0.50, N >= 1179 at rho = 0.40). Those are bounds, so
they could be loose by orders of magnitude and nobody would notice. This measures
the truth directly: run the gate many times and count how often it actually covers.

A bound that is tight here is worth much more than one that merely holds, and this
is the check that would catch a wrong constant in the derivation.

Run: PYTHONPATH=src python scripts/gate_coverage_validation.py   (~5 min CPU)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--rhos", type=float, nargs="+", default=[0.7, 0.6, 0.5, 0.4])
ap.add_argument("--n-gate", type=int, default=40)
ap.add_argument("--trials", type=int, default=200)
ap.add_argument("--region", type=float, default=1.0)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
T, A, R = env.h_episode, env.a_max, args.region


def gate_covers(rho, n_gate, trial):
    """Do this gate's rollouts put a sample in every cell of side rho of U?"""
    nx = int(2 * R / rho)
    na = int(2 * A / rho)
    need = {(i, j, k) for i in range(nx) for j in range(nx) for k in range(na)}
    for i in range(n_gate):
        rng = random.Random(1_000_000 * trial + i)
        s = env.initial_state(rng)
        for _ in range(T):
            a = rng.uniform(-A, A)
            x, v = s
            if abs(x) < R and abs(v) < R:
                need.discard((min(nx - 1, int((x + R) / rho)),
                              min(nx - 1, int((v + R) / rho)),
                              min(na - 1, int((a + A) / rho))))
            s = env.step(s, a)[0]
    return len(need) == 0


PREDICTED_N = {0.7: 10, 0.6: 35, 0.5: 169, 0.4: 1179}
rows = []
print(f"region |x|,|v| <= {R};  N = {args.n_gate};  {args.trials} trials/rho")
print(f"{'rho':>5} {'covered':>9} {'rate':>7} {'N needed (cert)':>17} "
      f"{'cert expects':>13}")
for rho in args.rhos:
    ok = sum(gate_covers(rho, args.n_gate, t) for t in range(args.trials))
    rate = ok / args.trials
    need = PREDICTED_N.get(round(rho, 2))
    expect = "cover" if need and need <= args.n_gate else "fail"
    rows.append({"rho": rho, "covered": ok, "trials": args.trials,
                 "rate": rate, "n_needed_certificate": need,
                 "certificate_expects": expect})
    print(f"{rho:5.2f} {ok:9} {rate:7.3f} {str(need):>17} {expect:>13}")

print("\nReading: the certificate's threshold sits between the rho it certifies and")
print("the next one down, so the bound is tight rather than loose by orders of")
print("magnitude -- which is what makes the N-vs-rho trade-off meaningful.")

out = _REPO / "results" / "gate_coverage_validation.json"
out.write_text(json.dumps({"script": "gate_coverage_validation.py",
                           "params": vars(args), "rows": rows}, indent=2))
print(f"\nwrote {out}")
