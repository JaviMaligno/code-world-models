"""Is a "repaired" 1D artifact exact, or exact-plus-a-phantom-mode?

The paper calls an artifact repaired when it passes the gate and its `mode_blindness` probe
scores 0. That probe fires only where the TRUTH's mode is active, so by construction it
cannot see a mode the artifact INVENTS elsewhere -- a limitation the paper states, and
attributes to the Claude arm. This script tests every artifact the paper counts as
repaired against the truth on a dense (state, action) grid, which no invented mode can
survive, and reports the split.

The distinction matters twice over. It is the difference between "the synthesizer recovers
the rule" and "the synthesizer recovers the rule and adds one the sample cannot refute",
and the second is an instance of Proposition prop:ident's prior caveat rather than of
repair. It is also the criterion the trigger-arity campaign needed: on the slab, a
half-plane at the near face scores blindness 0 while covering 13x the true region
(scripts/arity_evidence_ablations.py), so a probe-only criterion would have called it a
repair.

Run: PYTHONPATH=src python scripts/repair_exactness_1d.py
Writes: results/repair_exactness_1d.json
"""
import itertools
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall, PendulumStop        # noqa: E402
from cwm.continuous.contract import SynthesizedModel          # noqa: E402

RES = _REPO / "results"
TOL = 1e-9

ARMS = {
    "cart_xwall8": {
        "env": lambda: CartWall(x_wall=8.0),
        "grid": ([round(-2 + 0.25 * i, 4) for i in range(57)],
                 [-4.0, -2.0, -0.5, 0.0, 0.5, 2.0, 4.0],
                 [-1.0, -0.3, 0.0, 0.3, 1.0]),
        "files": ["continuous_synthesis_mini_xwall8.json",
                  "continuous_synthesis_large_xwall8.json",
                  "continuous_synthesis_large_xwall8_off20.json"],
    },
    "cart_xwall4": {
        "env": lambda: CartWall(x_wall=4.0),
        "grid": ([round(-2 + 0.25 * i, 4) for i in range(41)],
                 [-4.0, -2.0, -0.5, 0.0, 0.5, 2.0, 4.0],
                 [-1.0, -0.3, 0.0, 0.3, 1.0]),
        "files": ["continuous_synthesis_mini_xwall4.json"],
    },
    "pendulum_thstop1.4": {
        "env": lambda: PendulumStop(th_stop=1.4),
        "grid": ([round(-2.5 + 0.1 * i, 4) for i in range(51)],
                 [-3.0, -1.0, 0.0, 1.0, 3.0],
                 [-1.0, -0.3, 0.0, 0.3, 1.0]),
        "files": ["continuous_synthesis_pendulum_mini_thstop1.4.json",
                  "continuous_synthesis_pendulum_large_thstop1.4.json",
                  "continuous_synthesis_pendulum_large_thstop1.4_off20.json"],
    },
    "pendulum_thstop1": {
        "env": lambda: PendulumStop(th_stop=1.0),
        "grid": ([round(-2.5 + 0.1 * i, 4) for i in range(51)],
                 [-3.0, -1.0, 0.0, 1.0, 3.0],
                 [-1.0, -0.3, 0.0, 0.3, 1.0]),
        "files": ["continuous_synthesis_pendulum_mini_thstop1.json",
                  "continuous_synthesis_pendulum_large_thstop1.json"],
    },
}


def probe(code, env, grid):
    """Grid mismatch against the truth, and where the mismatches live."""
    try:
        m = SynthesizedModel(code, env)
    except Exception as e:                                   # pragma: no cover
        return {"error": repr(e)[:120]}
    xs, vs, acts = grid
    bad, tot, bad_x = 0, 0, []
    truth_mode_x, phantom_x = [], []
    for x, v, a in itertools.product(xs, vs, acts):
        t, _, contact = env.step((x, v), a)
        try:
            g = m.step((x, v), a)[0]
        except Exception as e:                               # pragma: no cover
            return {"error": repr(e)[:120]}
        tot += 1
        off = max(abs(gg - tt) for gg, tt in zip(g, t))
        if off > TOL:
            bad += 1
            bad_x.append(x)
            # a mismatch where the truth does NOT fire its mode is the artifact
            # inventing one; where the truth DOES fire, it is a missed repair
            (truth_mode_x if contact else phantom_x).append(x)
    out = {"n_grid": tot, "n_mismatch": bad, "exact": bad == 0}
    if bad:
        out.update({"mismatch_x_min": min(bad_x), "mismatch_x_max": max(bad_x),
                    "n_mismatch_where_truth_fires": len(truth_mode_x),
                    "n_mismatch_where_truth_does_not": len(phantom_x),
                    "invents_a_mode": len(phantom_x) > 0,
                    "misses_the_true_mode": len(truth_mode_x) > 0})
    return out


def rule_lines(code):
    return [l.strip()[:110] for l in code.split("\n")
            if l.strip().startswith(("if ", "elif ")) and "math" not in l]


def main() -> None:
    out = {"script": "repair_exactness_1d.py", "tolerance": TOL,
           "criterion": "an artifact the paper counts as REPAIRED (gate 1.000 and "
                        "mode_blindness 0) is re-tested against the truth on a dense "
                        "(state, action) grid; an invented mode shows up as a mismatch "
                        "where the truth does NOT fire its mode",
           "arms": {}}
    tot_rep = tot_exact = 0
    for name, spec in ARMS.items():
        env = spec["env"]()
        arm = {"n_repaired": 0, "n_exact": 0, "n_with_invented_mode": 0,
               "n_missing_true_mode": 0, "exceptions": []}
        for f in spec["files"]:
            p = RES / f
            if not p.exists():
                continue
            raw = json.loads(p.read_text())
            for c in raw["cells"]:
                if c["arm"] != "incomplete" or not c["gate_passed"]:
                    continue
                if c.get("wall_blindness") != 0.0:
                    continue
                arm["n_repaired"] += 1
                r = probe(c["code"], env, spec["grid"])
                if r.get("exact"):
                    arm["n_exact"] += 1
                    continue
                arm["n_with_invented_mode"] += bool(r.get("invents_a_mode"))
                arm["n_missing_true_mode"] += bool(r.get("misses_the_true_mode"))
                arm["exceptions"].append({
                    "file": f, "seed": c["seed"], "model": raw.get("model"),
                    "rules": rule_lines(c["code"]), **r})
        out["arms"][name] = arm
        tot_rep += arm["n_repaired"]
        tot_exact += arm["n_exact"]
        print(f"{name:20} repaired {arm['n_repaired']:3}  exact {arm['n_exact']:3}  "
              f"invented-mode {arm['n_with_invented_mode']:2}  "
              f"missed-true {arm['n_missing_true_mode']:2}")
        for e in arm["exceptions"]:
            print(f"    seed {e['seed']:>7} {e.get('model','')}: {e['rules']}")
    out["totals"] = {"n_repaired": tot_rep, "n_exact": tot_exact,
                     "n_not_exact": tot_rep - tot_exact}
    (RES / "repair_exactness_1d.json").write_text(json.dumps(out, indent=2))
    print(f"\nTOTAL: {tot_exact} of {tot_rep} artifacts the paper calls repaired are "
          f"exact on the grid; {tot_rep - tot_exact} carry an invented mode")
    print(f"wrote {RES / 'repair_exactness_1d.json'}")


if __name__ == "__main__":
    main()
