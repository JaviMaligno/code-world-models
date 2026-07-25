"""Does the dependence between two mode regions change sign? Resolved, not guessed.

Proposition "jointmiss" gives a sharp bracket for the joint gate-miss factor and a
sign rule for the error the naive product makes. Section "patch2d" measured the
ingredients on 600 rollouts per knob, and that was not enough to say anything about
the dependence: P(both) came in at 0 to 3 counts out of 600, six of the nine knobs
censored at zero. The observed -17% to +12% spread in the product's error was
therefore consistent with count noise, and the paper's claim that "the dependence
changes sign across the grid" was over-read from it. Peer review caught that
(2026-07-25).

Note what could NOT be fixed by better statistics on the same sample: r_1, r_2,
r_union and P(both) all come from the same rollouts, so inclusion-exclusion holds
identically in the plug-in estimates. "The bracket contains the measured value at all
nine knobs" is an algebraic identity with zero empirical content -- it cannot fail.
The only falsifiable question is the dependence itself, and answering it needs a
sample large enough to resolve a probability of order 1e-3.

So this measures P(both) directly at 50,000 rollouts per knob, with a Wilson interval,
and reports for each knob whether the interval excludes the independence value r_1r_2
and on which side. Three knobs suffice to settle the question of whether a single
correction factor could replace the bracket: if the sign differs between two knobs
with non-overlapping intervals, no fixed factor works and the bracket is the right
object.

Resumable: each knob's result is appended to the JSON as it completes, and a re-run
skips knobs already present. At ~10 min per knob that matters.

Run: PYTHONPATH=src python scripts/patch2d_dependence_50k.py   (~40 min CPU)
"""
import argparse
import json
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D  # noqa: E402
from cwm.law import wilson_ci                 # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--knobs", type=float, nargs="+",
                default=[2.0, 6.0, 4.0, 6.0, 4.0, 7.0, 3.0, 7.0],
                help="flattened (k1, k2) pairs")
ap.add_argument("--rollouts", type=int, default=50_000)
ap.add_argument("--seed-base", type=int, default=50_000)
args = ap.parse_args()

KNOBS = list(zip(args.knobs[0::2], args.knobs[1::2]))
OUT = _REPO / "results" / "patch2d_dependence_50k.json"

done = {}
if OUT.exists():
    prev = json.loads(OUT.read_text())
    if prev.get("params", {}).get("rollouts") == args.rollouts:
        done = {(r["k1"], r["k2"]): r for r in prev.get("rows", [])}
        if done:
            print(f"resuming: {len(done)} knob(s) already measured")


def measure(k1, k2):
    """Marginal and joint contact rates over i.i.d. gate-policy rollouts."""
    env = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
    h1 = h2 = both = union = 0
    for i in range(args.rollouts):
        rng = random.Random(args.seed_base + i)
        s = env.initial_state(rng)
        c1 = c2 = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            m1, m2 = env.contact_modes(s, a)
            c1, c2 = c1 or m1, c2 or m2
            s = env.step(s, a)[0]
        h1 += c1
        h2 += c2
        both += (c1 and c2)
        union += (c1 or c2)
    n = args.rollouts
    r1, r2, rb = h1 / n, h2 / n, both / n
    lo, hi = wilson_ci(both, n)[1:]
    ind = r1 * r2
    verdict = ("negative dependence" if hi < ind else
               "positive dependence" if lo > ind else
               "undecided at this sample size")
    return {"k1": k1, "k2": k2, "n": n, "hits1": h1, "hits2": h2,
            "hits_both": both, "hits_union": union,
            "r1": r1, "r2": r2, "P_both": rb, "P_both_ci": [lo, hi],
            "r1_times_r2": ind, "verdict": verdict,
            "interval_excludes_independence": bool(hi < ind or lo > ind)}


rows = []
for k1, k2 in KNOBS:
    if (k1, k2) in done:
        rows.append(done[(k1, k2)])
        r = done[(k1, k2)]
        print(f"({k1:.0f},{k2:.0f}): cached -> {r['verdict']}")
        continue
    r = measure(k1, k2)
    rows.append(r)
    print(f"({k1:.0f},{k2:.0f}): r1={r['r1']:.4f} r2={r['r2']:.4f} "
          f"P(both)={r['P_both']:.5f} CI=[{r['P_both_ci'][0]:.5f},"
          f"{r['P_both_ci'][1]:.5f}] vs r1*r2={r['r1_times_r2']:.5f} "
          f"-> {r['verdict']}", flush=True)
    OUT.write_text(json.dumps({"script": "patch2d_dependence_50k.py",
                               "params": vars(args), "rows": rows}, indent=2))

signs = {r["verdict"] for r in rows if r["interval_excludes_independence"]}
print(f"\nresolved knobs: {len(signs & {'negative dependence', 'positive dependence'})}"
      f" distinct signs among "
      f"{sum(1 for r in rows if r['interval_excludes_independence'])} resolved")
if {"negative dependence", "positive dependence"} <= signs:
    print("BOTH SIGNS occur with non-overlapping intervals: no fixed correction "
          "factor can replace")
    print("the bracket, because the product's error changes direction with the "
          "geometry.")
OUT.write_text(json.dumps({"script": "patch2d_dependence_50k.py",
                           "params": vars(args), "rows": rows}, indent=2))
print(f"\nwrote {OUT}")
