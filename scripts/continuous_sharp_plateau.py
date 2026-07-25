"""Sharp-plateau variant of the two 1D instruments (paper 2, sec:mechanism).

Why: on the default instruments the mode-blind planner scores *above* the random
policy at the widest knobs (cart x_wall=10: J_blind 0.94 vs J_random 0.53; the
three farthest pendulum stops likewise), so "exploited below random at EVERY
knob" is false as stated. The cause is not the mechanism — contact rate stays
1.00 and play_cost stays ~1 — but the far plateau's sigmoid TAIL: a planner
pinned at x=10 still collects 1/(1+exp((12-10)/width)) per step, which at
width=0.5 is 0.018 and over 80 steps is most of J_blind.

This variant narrows the reward-plateau width (cart 0.5 -> 0.2, pendulum
0.25 -> 0.1) and re-runs the same sweeps into sibling JSONs. It changes nothing
in the default instruments (the committed sweeps and every synthesis artifact,
whose contract text embeds the default width, stay valid): it is added evidence,
not a re-calibration.

Prediction (pre-registered): the tail leak disappears, so J_blind falls below
J_random at every knob while contact rate stays 1.00 and play_cost stays ~1. The
risk is the other side: a sharper plateau gives random-shooting MPC less gradient
to follow, so J_truth may drop — reported either way.

Run: PYTHONPATH=src python scripts/continuous_sharp_plateau.py   (~10 min CPU)
"""
import json
import pathlib
import runpy
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "src"))

CART_WIDTH = 0.2        # default 0.5
PEND_WIDTH = 0.1        # default 0.25
RUNS = (("continuous_reach.py", CART_WIDTH, "continuous_reach"),
        ("continuous_pendulum.py", PEND_WIDTH, "continuous_pendulum"))


def _delegate(script, width):
    sys.argv = [str(_HERE / script), "--width", str(width),
                "--out-suffix", "_sharp"]
    runpy.run_path(str(_HERE / script), run_name="__main__")


for script, width, stem in RUNS:
    print(f"\n=== {script} at width={width} ===", flush=True)
    _delegate(script, width)

# --- the comparison the variant exists to make -----------------------------
print("\n=== below-random check: default vs sharp ===")
print(f"{'instrument':>10} {'knob':>6} {'J_blind':>9} {'J_rand':>8} "
      f"{'below?':>7} {'pc':>6} {'contact':>8}")
verdict = {}
for _, _, stem in RUNS:
    for tag, path in (("default", f"results/{stem}.json"),
                      ("sharp", f"results/{stem}_sharp.json")):
        rows = json.loads((_REPO / path).read_text())["rows"]
        knob_key = "x_wall" if stem.endswith("reach") else "th_stop"
        below = 0
        for r in rows:
            ok = r["j_blind"] < r["j_random"]
            below += ok
            print(f"{tag:>10} {r[knob_key]:6.1f} {r['j_blind']:9.4f} "
                  f"{r['j_random']:8.4f} {'yes' if ok else 'NO':>7} "
                  f"{r['play_cost']:6.3f} {r['blind_contact_rate']:8.2f}")
        verdict[(stem, tag)] = (below, len(rows))
print()
for k, (below, n) in verdict.items():
    print(f"{k[0]} [{k[1]}]: blind below random at {below}/{n} knobs")
