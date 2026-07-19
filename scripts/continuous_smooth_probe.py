"""Smooth-learner probe (design doc step 5, scope: probe not sweep).

Trains the two most favorable smooth learners — closed-form linear least
squares (the off-mode dynamics ARE linear) and a small tanh MLP — on the same
N=40-rollout samples the synthesis arms used (x_wall=8), one wall-free and
one wall-containing, and measures where the error lives:

  - synthesized code (paper 2 runs): off-mode error EXACTLY 0 (bit-exact),
    on-mode either omitted (blind) or repaired (exact clamp).
  - smooth learners: error is pervasive — nonzero everywhere — and the
    contact rows TILT the fit, so training on wall-containing data makes the
    off-mode error WORSE. The mode cannot be localized by a smooth
    hypothesis; it leaks. No smooth model passes any tight gate the
    synthesized code passes.

Run: PYTHONPATH=src python scripts/continuous_smooth_probe.py   (~2-4 min)
"""
import json
import pathlib
import time

from cwm.continuous.envs import CartWall
from cwm.continuous.contract import collect_transitions, sample_contains_wall
from cwm.continuous.smooth_fit import FittedModel, LinearModel, MLPModel
from cwm.continuous import gate

ENV = CartWall(x_wall=8.0)
# Same protocol/seeds as the synthesis run: seed 10000 missed the wall,
# seed 20000 contains contact transitions (verified below).
SAMPLE_FREE = collect_transitions(ENV, 40, seed=10_000)
SAMPLE_WALL = collect_transitions(ENV, 40, seed=20_000)
assert not sample_contains_wall(SAMPLE_FREE)
assert sample_contains_wall(SAMPLE_WALL)
N_CONTACT = sum(t["contact"] for t in SAMPLE_WALL)

WALL_PROBES = [((ENV.x_wall - 0.1, v), ENV.a_max) for v in (1.0, 2.0, 4.0)]


def errs(model, transitions):
    """Per-transition sup-norm state error of `model` vs recorded truth."""
    out = []
    for t in transitions:
        p = model.predict(t["state"][0], t["state"][1], t["action"])
        out.append(max(abs(p[0] - t["next_state"][0]),
                       abs(p[1] - t["next_state"][1])))
    return out


def probe_err(model):
    out = []
    for (s, a) in WALL_PROBES:
        st, _, _ = ENV.step(s, a)
        p = model.predict(s[0], s[1], a)
        out.append(max(abs(p[0] - st[0]), abs(p[1] - st[1])))
    return max(out)


def summarize(name, model, trained_on):
    off = errs(model, [t for t in SAMPLE_WALL if not t["contact"]])
    on = errs(model, [t for t in SAMPLE_WALL if t["contact"]])
    off_sorted = sorted(off)
    row = {
        "model": name, "trained_on": trained_on,
        "off_mode_mean": sum(off) / len(off),
        "off_mode_p99": off_sorted[int(0.99 * len(off))],
        "off_mode_max": off_sorted[-1],
        "on_mode_mean": (sum(on) / len(on)) if on else None,
        "wall_probe_max_err": probe_err(model),
    }
    adapter = FittedModel(model, ENV)
    for eps in (1e-9, 1e-2):
        g = gate.run_gate(ENV, adapter, n_rollouts=40, eps=eps, seed=777_000)
        row[f"gate_pass_eps{eps:g}"] = g.passed
        row[f"gate_bad_frac_eps{eps:g}"] = g.n_bad / g.n_transitions
    print(f"{name:>22} on {trained_on:>9}: off-mode mean={row['off_mode_mean']:.2e} "
          f"p99={row['off_mode_p99']:.2e} max={row['off_mode_max']:.2e} | "
          f"on-mode mean={row['on_mode_mean'] if row['on_mode_mean'] is None else format(row['on_mode_mean'], '.2e')} | "
          f"probe={row['wall_probe_max_err']:.2e} | "
          f"gate@1e-9={'PASS' if row['gate_pass_eps1e-09'] else 'fail'} "
          f"gate@1e-2={'PASS' if row['gate_pass_eps0.01'] else 'fail'}",
          flush=True)
    return row


t0 = time.time()
print(f"wall-containing sample: {N_CONTACT}/{len(SAMPLE_WALL)} contact "
      f"transitions", flush=True)
rows = [
    summarize("linear-LSQ", LinearModel(SAMPLE_FREE), "wall-free"),
    summarize("linear-LSQ", LinearModel(SAMPLE_WALL), "wall-data"),
    summarize("MLP h=8", MLPModel(SAMPLE_FREE, seed=0), "wall-free"),
    summarize("MLP h=8", MLPModel(SAMPLE_WALL, seed=0), "wall-data"),
]
out = {"script": "continuous_smooth_probe.py",
       "n_contact_rows": N_CONTACT, "n_rows": len(SAMPLE_WALL),
       "elapsed_s": round(time.time() - t0, 1), "rows": rows}
path = pathlib.Path("results/continuous_smooth_probe.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)
