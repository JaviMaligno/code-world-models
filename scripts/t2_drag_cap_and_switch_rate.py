"""Emit T2's drag-cap verification and the argmax switch rate p(eps).

Two numbers quoted in docs/paper3/THEORY.md with no artifact:

  (a) the drag cap's tightness, quoted as "the integrator over 400 random
      states x 200 steps: worst observed 1.9956 against the cap 2.0600". The
      committed guard in tests/test_t3_funnel_bound.py runs 60 x 150, so the
      quoted sample size described no run. This emits the sweep at several
      sizes, so the number in the paper names a size that exists and the guard
      can cite the same artifact.

  (b) p(eps), the probability that a velocity perturbation of size eps flips
      the planner's argmax. It is the factor in the fixed point
        L_v * delta <= A * delta + p(delta) * L_v * (2 * gain * dt),
      whose closure condition is p(delta) * 2 * gain * dt < delta -- a
      displacement against a displacement. Because the condition is
      delta-DEPENDENT, p must be emitted as a CURVE, not as a single "p ~ 0.5":
      at small delta the condition fails, and that is only visible from the
      curve.

Resumable: each cell is keyed by its parameters and written as it finishes.

  PYTHONPATH=src python scripts/t2_drag_cap_and_switch_rate.py
"""
import argparse
import json
import math
import pathlib
import random
import sys
import time

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

from cwm.continuous.envs import RingField2D, integrate_2d, blind_of  # noqa: E402
from cwm.continuous import mpc                                       # noqa: E402

OUT = _REPO / "results" / "t2_drag_cap_and_switch_rate.json"
HOR, NS, BLOCK = 40, 48, 10
t0 = time.time()


def drag_cap(n_states, n_steps, seed):
    """(a) Worst observed separation under IDENTICAL actions, against the cap.

    The affine plant gives ||dx_t|| <= ||dx_0|| + ||dv_0||/drag for all t --
    bounded, not exponential. Reported with the worst case's step index, since
    a cap attained only at t = 0 would say nothing about the tail.
    """
    env = RingField2D()
    dx0, dv0 = 2 * env.gain * env.dt ** 2, 2 * env.gain * env.dt
    cap = dx0 + dv0 / env.drag
    rng = random.Random(seed)
    worst, worst_at = 0.0, None
    for _ in range(n_states):
        s1 = (rng.uniform(-2, 14), rng.uniform(-6, 6),
              rng.uniform(-9, 9), rng.uniform(-9, 9))
        th, th2 = (rng.uniform(-math.pi, math.pi),
                   rng.uniform(-math.pi, math.pi))
        s2 = (s1[0] + dx0 * math.cos(th), s1[1] + dx0 * math.sin(th),
              s1[2] + dv0 * math.cos(th2), s1[3] + dv0 * math.sin(th2))
        for t in range(n_steps):
            a = rng.uniform(-env.a_max, env.a_max)
            s1 = integrate_2d(s1, a, env.dt, env.gain, env.drag, env.a_max)
            s2 = integrate_2d(s2, a, env.dt, env.gain, env.drag, env.a_max)
            d = math.hypot(s1[0] - s2[0], s1[1] - s2[1])
            if d > worst:
                worst, worst_at = d, t
    return {"n_states": n_states, "n_steps": n_steps, "seed": seed,
            "dx0": dx0, "dv0": dv0, "cap": cap,
            "worst_observed": worst, "worst_at_step": worst_at,
            "tightness": worst / cap}


def switch_rate(eps_list, n_draws, seed, gap):
    """(b) p(eps): does an eps velocity perturbation flip the argmax?

    Unit = candidate draw. The perturbation is applied to the velocity only,
    with the SAME candidate set on both sides (common random numbers), so a
    flip is attributable to the perturbation rather than to planner noise.
    """
    truth = RingField2D(gap=gap, gap_center=math.pi, x0_center=(0.0, 0.0))
    rows = []
    for eps in eps_list:
        rng = random.Random(seed)
        flips = 0
        for k in range(n_draws):
            s = truth.initial_state(random.Random(seed + 17 * k))
            th = rng.uniform(-math.pi, math.pi)
            s2 = (s[0], s[1], s[2] + eps * math.cos(th),
                  s[3] + eps * math.sin(th))
            cands = list(mpc._candidates(truth.a_max,
                                         random.Random(seed + 31 * k),
                                         HOR, NS, BLOCK, 1))
            best1 = best2 = -float("inf")
            a1 = a2 = None
            for acts in cands:
                v1, v2 = 0.0, 0.0
                p1, p2 = s, s2
                for a in acts:
                    p1, r1, _ = truth.step(p1, a)
                    p2, r2, _ = truth.step(p2, a)
                    v1 += r1
                    v2 += r2
                if v1 > best1:
                    best1, a1 = v1, acts[0]
                if v2 > best2:
                    best2, a2 = v2, acts[0]
            flips += (a1 != a2)
        p = flips / n_draws
        # The closure condition is p(delta)*2*gain*dt < delta, comparing a
        # displacement against a displacement -- emit both sides per eps so
        # nobody has to recompute which way it goes.
        lhs = p * 2 * truth.gain * truth.dt
        rows.append({"eps": eps, "n_draws": n_draws, "flips": flips,
                     "p": p, "p_times_2_gain_dt": lhs,
                     "closes": bool(lhs < eps),
                     "L_v_multiplier": (eps / (eps - lhs)) if lhs < eps
                     else None})
    return {"gap": gap, "seed": seed, "planner":
            {"horizon": HOR, "n_samples": NS, "block": BLOCK},
            "unit": "candidate draw", "rows": rows,
            "closure_note": (
                "closure needs p(delta)*2*gain*dt < delta. The condition is "
                "delta-dependent: it holds at coarse perturbations and fails "
                "at fine ones, so there is no uniform-in-delta fixed point and "
                "the delta -> 0 limit (the natural reading of a Lipschitz "
                "constant) diverges.")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap-sizes", type=int, nargs="*",
                    default=[60, 150, 400, 200],
                    help="pairs: n_states n_steps n_states n_steps ...")
    ap.add_argument("--eps", type=float, nargs="*",
                    default=[0.05, 0.1, 0.2, 0.4, 0.6, 0.8])
    ap.add_argument("--n-draws", type=int, default=200)
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {}
    cells = state.setdefault("cells", {})

    pairs = list(zip(args.cap_sizes[0::2], args.cap_sizes[1::2]))
    for n_states, n_steps in pairs:
        key = f"drag_cap|{n_states}x{n_steps}"
        if key not in cells:
            print(f"(a) drag cap at {n_states} states x {n_steps} steps",
                  flush=True)
            cells[key] = drag_cap(n_states, n_steps, 7)
            OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
            c = cells[key]
            print(f"    worst {c['worst_observed']:.4f} vs cap "
                  f"{c['cap']:.4f} ({100 * c['tightness']:.1f}% tight, "
                  f"attained at step {c['worst_at_step']})", flush=True)

    key = f"switch_rate|0.6|{args.n_draws}"
    if key not in cells:
        print(f"(b) argmax switch rate over {len(args.eps)} perturbations, "
              f"n={args.n_draws} draws each", flush=True)
        cells[key] = switch_rate(args.eps, args.n_draws, 5_000, 0.6)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
        for r in cells[key]["rows"]:
            print(f"    eps={r['eps']:.2f}  p={r['p']:.3f}  "
                  f"p*2*gain*dt={r['p_times_2_gain_dt']:.3f}  "
                  f"{'closes' if r['closes'] else 'DOES NOT CLOSE'}",
                  flush=True)

    OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
    print(f"\nwrote {OUT}  ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
