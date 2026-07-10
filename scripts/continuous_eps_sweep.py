"""eps-sensitivity sweep of the deployment-realistic tolerance gate.

Documents that the tolerance axis is orthogonal to the identifiability hole
(design-doc risk "the deployment-realistic loose-eps arm needs a documented
eps-sensitivity sweep" — resolved by this script):

  - mode-omitted arms (cart wall@4/@8; pendulum stop@1.0/@1.4): the error is
    a discontinuity (0 off-mode at float precision, O(1) on-mode), so
    reveal-rarity — and with it pass@N = (1-r)^N — is FLAT in eps from
    float-noise scale up to the mode's own error scale. Tightening the gate
    cannot catch the mode; loosening it does not widen the hole.
  - pervasive drag-bias arms (x1.03, x2.0; both instruments): reveal-rarity
    switches 1 -> 0 as eps crosses the arm's error scale — the tolerance
    axis polices pervasive error and only pervasive error.
  - smooth-bump arms (cart only; the bump is a CartWall field): analogous
    amplitude-dependent transition.

play_cost is NOT re-measured: the model under test does not depend on eps,
so play behavior is eps-independent by construction.

Run: PYTHONPATH=src python scripts/continuous_eps_sweep.py   (~15-25 min CPU)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import (CartWall, PendulumStop, blind_of, biased_of,
                                 unbumped_of)
from cwm.continuous import gate

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--eps-grid", type=float, nargs="+",
                default=[1e-9, 1e-6, 1e-4, 1e-3, 1e-2, 3e-2, 0.1, 0.3])
ap.add_argument("--rollouts", type=int, default=2000)
ap.add_argument("--n-gate", type=int, default=40)
ap.add_argument("--gates", type=int, default=300,
                help="independent gates for pass@N (mode arms only)")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

CART4, CART8 = CartWall(x_wall=4.0), CartWall(x_wall=8.0)
PEND10, PEND14 = PendulumStop(th_stop=1.0), PendulumStop(th_stop=1.4)
BUMP_MILD = CartWall(x_wall=None, bump_amp=0.5, bump_center=4.0, bump_width=0.5)
BUMP_STRONG = CartWall(x_wall=None, bump_amp=1.0, bump_center=4.0, bump_width=0.5)

ARMS = [
    # (instrument, name, truth, model-under-test, is_mode_arm)
    ("cart", "wall@4 omitted", CART4, blind_of(CART4), True),
    ("cart", "wall@8 omitted", CART8, blind_of(CART8), True),
    ("cart", "bias x1.03", CART4, biased_of(CART4, 1.03), False),
    ("cart", "bias x2.0", CART4, biased_of(CART4, 2.0), False),
    ("cart", "bump amp0.5", BUMP_MILD, unbumped_of(BUMP_MILD), False),
    ("cart", "bump amp1.0", BUMP_STRONG, unbumped_of(BUMP_STRONG), False),
    ("pend", "stop@1.0 omitted", PEND10, blind_of(PEND10), True),
    ("pend", "stop@1.4 omitted", PEND14, blind_of(PEND14), True),
    ("pend", "bias x1.03", PEND10, biased_of(PEND10, 1.03), False),
    ("pend", "bias x2.0", PEND10, biased_of(PEND10, 2.0), False),
]

t0 = time.time()
rows = []
print(f"eps grid: {args.eps_grid}  ({args.rollouts} rollouts/arm/eps; "
      f"{args.gates} gates x N={args.n_gate} on mode arms)", flush=True)
print(f"{'inst':>4} {'arm':>18} {'eps':>8} {'rarity':>8} {'(1-r)^N':>8} "
      f"{'pass@N':>7}", flush=True)
for inst, name, truth, model, is_mode in ARMS:
    for eps in args.eps_grid:
        r, r_lo, r_hi = gate.reveal_rarity(truth, model, eps, args.rollouts,
                                           seed=args.seed + 10_000)
        row = {"instrument": inst, "arm": name, "mode_arm": is_mode,
               "eps": eps, "rarity": r, "rarity_ci": [r_lo, r_hi]}
        if is_mode:
            predicted = (1 - r) ** args.n_gate
            p, p_lo, p_hi = gate.gate_pass_rate(
                truth, model, eps, args.n_gate, args.gates,
                seed=args.seed + 500_000)
            row.update({"predicted_pass": predicted, "pass_rate": p,
                        "pass_rate_ci": [p_lo, p_hi]})
            print(f"{inst:>4} {name:>18} {eps:8.0e} {r:8.4f} "
                  f"{predicted:8.4f} {p:7.3f}", flush=True)
        else:
            print(f"{inst:>4} {name:>18} {eps:8.0e} {r:8.4f} {'-':>8} "
                  f"{'-':>7}", flush=True)
        rows.append(row)

out = pathlib.Path("results/continuous_eps_sweep.json")
out.write_text(json.dumps({"script": "continuous_eps_sweep.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
