"""The gate's visitation density constant c, computed for the cart instrument.

Proposition (smooth localized error is detectable at a rate) needs a lower bound
c on the gate's step-k visitation density over the guaranteed disagreement ball.
The paper states the proposition with c as a hypothesis because verifying it is
instrument-specific. For the cart at step k = 1 it is not merely verifiable, it is
exact, so this script closes that hypothesis for one real instrument:

  x0 ~ U(-1/2, 1/2), v0 = 0, a0 ~ U(-a_max, a_max)  (the gate policy)
  v1 = (gain*a0 - drag*v0)*dt = gain*dt*a0           ~ U(-gain*dt*a_max, +...)
  x1 = x0 + dt*v1                                    = x0 shifted by dt*v1
  a1 ~ U(-a_max, a_max), independent of the state

so on the region {|v1| < gain*dt*a_max, |x1 - dt*v1| < 1/2, |a1| < a_max} the
joint (x1, v1, a1) density factorises exactly:

  c = 1/(2*gain*dt*a_max)  *  1  *  1/(2*a_max)

For the paper's constants (gain 3, dt 0.1, a_max 1) that is 5/6. The script
verifies it by Monte Carlo and then reports what the proposition then says
QUANTITATIVELY: the Lipschitz constant a smooth pair needs in order to hide an
eta-sized error from the deployed N = 40 gate, against the plant's own Lipschitz
constant (so "how much more sensitive than the truth must a hider be").

Run: PYTHONPATH=src python scripts/gate_density_constant.py   (~1 min CPU)
"""
import argparse
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--mc-samples", type=int, default=4_000_000)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

env = CartWall(x_wall=8.0)
dt, gain, drag, a_max = env.dt, env.gain, env.drag, env.a_max

# --- the constant, in closed form -------------------------------------------
c = 1.0 / (2 * gain * dt * a_max) * 1.0 * (1.0 / (2 * a_max))

# --- Monte Carlo check on an interior box -----------------------------------
rng = random.Random(args.seed)
half = (0.05, 0.02, 0.10)          # box half-widths in (x, v, a), centred at 0
hits = 0
for _ in range(args.mc_samples):
    x0 = rng.uniform(-0.5, 0.5)
    a0 = rng.uniform(-a_max, a_max)
    v1 = (gain * a0 - drag * 0.0) * dt
    x1 = x0 + v1 * dt
    a1 = rng.uniform(-a_max, a_max)
    if abs(x1) < half[0] and abs(v1) < half[1] and abs(a1) < half[2]:
        hits += 1
vol = 8 * half[0] * half[1] * half[2]
c_mc = hits / args.mc_samples / vol

# --- the plant's own Lipschitz constant (sup-metric, exact for this linear map)
# v' = (1 - drag*dt) v + gain*dt a ;  x' = x + dt v' = x + dt(1-drag*dt) v + gain*dt^2 a
rows = [abs(1 - drag * dt) + gain * dt,                       # |dv'| row
        1.0 + dt * abs(1 - drag * dt) + gain * dt * dt]       # |dx'| row
L_plant = max(rows)

# --- what the proposition then says, in numbers ------------------------------
EPS = 0.01
N = 40
table = []
for eta in (0.05, 0.1, 0.5, 1.0, 4.2):
    # P(miss) <= (1-q)^N with q = c*((eta-eps)/L)^(d+m), d+m = 3 here (x, v, a)
    # hiding with P(miss) > delta forces L >= (eta-eps)*(c*N/ln(1/delta))^(1/3)
    row = {"eta": eta}
    for delta in (0.5, 0.1):
        q_max = math.log(1 / delta) / N
        row[f"L_min_delta{delta}"] = (eta - EPS) * (c / q_max) ** (1 / 3)
    table.append(row)

print(f"cart gate, step 1: analytic c = 1/(2*gain*dt*a_max) * 1/(2*a_max) = {c:.6f}")
print(f"  Monte Carlo ({args.mc_samples:,} samples, interior box): {c_mc:.6f} "
      f"({abs(c_mc - c) / c * 100:.2f}% off)")
print(f"  plant Lipschitz constant (sup-metric): {L_plant:.4f}")
print(f"\nWhat it takes to HIDE an eta-sized error from the deployed gate "
      f"(eps={EPS}, N={N}):")
print(f"{'eta':>6} {'L needed for P(miss)>0.5':>26} {'>0.1':>10} "
      f"{'x plant Lipschitz':>18}")
for row in table:
    print(f"{row['eta']:6.2f} {row['L_min_delta0.5']:26.3f} "
          f"{row['L_min_delta0.1']:10.3f} "
          f"{row['L_min_delta0.5'] / L_plant:18.2f}")

out = _REPO / "results" / "gate_density_constant.json"
out.write_text(json.dumps(
    {"script": "gate_density_constant.py", "params": vars(args),
     "instrument": "CartWall", "step": 1, "dims": 3,
     "c_analytic": c, "c_monte_carlo": c_mc,
     "mc_box_half_widths": half, "L_plant_sup_metric": L_plant,
     "eps": EPS, "n_gate": N, "hiding_table": table}, indent=2))
print(f"\nwrote {out}")
