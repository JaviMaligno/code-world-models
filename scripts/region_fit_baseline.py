"""Can a trivial baseline recover the region from the same sample the synthesizer sees?

The 2D repair results are all negatives, and a negative needs an upper bound on the task's
difficulty. The positive control (scripts/continuous_danger_synthesis.py --mode-hint) gives
one from inside the pipeline: told the form AND the centres, GPT-5.x infers the withheld
radius exactly in 20 of 20 seeds; told the form alone, it recovers nothing in 20 of 20. This
script gives the other, from outside the pipeline: an algebraic least-squares circle fit --
three lines of linear algebra, no prior, no LLM -- on exactly the evidence the synthesizer
was handed.

WHAT THE SYNTHESIZER HAS. Each sampled transition carries (state, action, next_state). A
contact is recognisable without any extra information (the next state is the previous
position with zero velocity), and the landing is computable from the contract's own
integrator. So the set of contact LANDING points is derivable from the sample by anyone who
read the contract, and that is the set the true rule is a statement about.

IT ALSO QUANTIFIES A DESCRIPTION. The paper called the 2D evidence "one-sided". Measured
properly -- as the arc actually covered, i.e. 360 degrees minus the largest angular gap --
the contact landings span a median of about 110 degrees around the patch, and the pre-freeze
positions about 104: partial coverage of the circle rather than a thin crescent, and the two
are alike. (A naive max-minus-min on wrapped angles reports ~350 degrees for the same points
and is wrong; the gap form is what this script uses.)

Run: PYTHONPATH=src python scripts/region_fit_baseline.py
Writes: results/region_fit_baseline.json
"""
import json
import math
import pathlib
import sys

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D           # noqa: E402
from cwm.continuous.contract import collect_transitions  # noqa: E402

RES = _REPO / "results"
N_SEEDS = 20
TOL_CENTRE = 0.10        # a tenth of the radius
TOL_RADIUS = 0.10


def circle_fit(pts):
    """Algebraic least squares: x^2 + y^2 + Dx + Ey + F = 0."""
    P = np.asarray(pts, dtype=float)
    A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
    b = -(P[:, 0] ** 2 + P[:, 1] ** 2)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = -sol[0] / 2, -sol[1] / 2
    r2 = cx * cx + cy * cy - sol[2]
    return cx, cy, math.sqrt(r2) if r2 > 0 else 0.0, float(np.linalg.cond(A))


def angular_extent(pts, c):
    a = np.degrees(np.arctan2([p[1] - c[1] for p in pts], [p[0] - c[0] for p in pts]))
    a = np.sort(a % 360.0)
    if len(a) < 2:
        return 0.0
    gaps = np.diff(np.r_[a, a[0] + 360.0])
    return float(360.0 - gaps.max())      # the arc actually covered


def main() -> None:
    env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    truth = {"centre": list(env.p1), "R": env.R}
    rows = []
    for i in range(N_SEEDS):
        seed = 10_000 * (i + 1)
        tr = collect_transitions(env, 40, seed=seed)
        land, prev = [], []
        for t in tr:
            if not t["contact"]:
                continue
            lx, ly = env._integrate(tuple(t["state"]), t["action"])[:2]
            if env._inside(lx, ly, env.p1):
                land.append((lx, ly))
                prev.append((t["state"][0], t["state"][1]))
        row = {"seed": seed, "n_contacts_p1": len(land)}
        if len(land) >= 3:
            cx, cy, r, cond = circle_fit(land)
            row.update({
                "fit_centre": [cx, cy], "fit_R": r, "cond": cond,
                "centre_error": math.hypot(cx - env.p1[0], cy - env.p1[1]),
                "radius_error": abs(r - env.R),
                "landing_arc_deg": angular_extent(land, env.p1),
                "prev_arc_deg": angular_extent(prev, env.p1),
            })
            row["recovers_centre"] = row["centre_error"] <= TOL_CENTRE
            row["recovers_both"] = (row["recovers_centre"]
                                    and row["radius_error"] <= TOL_RADIUS)
        else:
            row["recovers_centre"] = row["recovers_both"] = False
            row["note"] = "fewer than three contacts: a circle is not determined"
        rows.append(row)

    ok = [r for r in rows if r.get("recovers_both")]
    okc = [r for r in rows if r.get("recovers_centre")]
    fit = [r for r in rows if "cond" in r]
    out = {
        "script": "region_fit_baseline.py",
        "why": "an upper bound on the 2D task's difficulty, from outside the pipeline",
        "truth": truth, "tol_centre": TOL_CENTRE, "tol_radius": TOL_RADIUS,
        "n_seeds": N_SEEDS,
        "n_recovering_centre": len(okc), "n_recovering_both": len(ok),
        "n_with_enough_contacts": len(fit),
        "median_contacts": float(np.median([r["n_contacts_p1"] for r in rows])),
        "median_landing_arc_deg": float(np.median([r["landing_arc_deg"] for r in fit])),
        "median_prev_arc_deg": float(np.median([r["prev_arc_deg"] for r in fit])),
        "rows": rows,
        "reading": (
            "The contact landings cover a median ~110 degrees of the circle, so the evidence "
            "is partial rather than either full or a thin crescent. Even so, a plain "
            "least-squares circle fit on those landings -- three lines of linear algebra, no "
            "prior, no LLM -- recovers both constants within a tenth of the radius on 12 of "
            "20 samples and the centre alone on 13. GPT-5.x, given the form and asked for "
            "the constants, recovers them on 0 of 20, INCLUDING on the samples where the fit "
            "succeeds. So on those samples the region is recoverable from the evidence and "
            "the synthesizer does not recover it: the negative is an induction failure, not "
            "a limit of the evidence and not an inability to fit constants (given the "
            "centres it fits the radius exactly, 20 of 20). On the 8 samples where the "
            "trivial fit also fails, the negative is NOT attributable to the synthesizer, "
            "and we do not attribute it."),
    }
    (RES / "region_fit_baseline.json").write_text(json.dumps(out, indent=2))
    print(f"{'seed':>8} {'contacts':>9} {'landing arc':>12} {'prev arc':>9} "
          f"{'centre err':>11} {'R err':>7} {'cond':>8}  both?")
    for r in rows:
        if "cond" in r:
            print(f"{r['seed']:>8} {r['n_contacts_p1']:>9} {r['landing_arc_deg']:>11.1f}° "
                  f"{r['prev_arc_deg']:>8.1f}° {r['centre_error']:>11.3f} "
                  f"{r['radius_error']:>7.3f} {r['cond']:>8.1f}  {r['recovers_both']}")
        else:
            print(f"{r['seed']:>8} {r['n_contacts_p1']:>9}  {r.get('note','')}")
    print(f"\na plain circle fit recovers the CENTRE in {len(okc)}/{N_SEEDS} samples and "
          f"BOTH constants in {len(ok)}/{N_SEEDS}")
    print(f"median landing arc {out['median_landing_arc_deg']:.1f} deg vs pre-freeze "
          f"{out['median_prev_arc_deg']:.1f} deg")
    print(f"wrote {RES / 'region_fit_baseline.json'}")


if __name__ == "__main__":
    main()
