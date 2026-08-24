"""Scan the thin-neck synthesis campaigns for the claims the paper makes.

The campaign's question (THIN-NECK-DESIGN.md, EXPERIMENTS.md "Thin-neck LLM
synthesis") is structural: does any artifact WRITE a variable-thickness band —
or any angular structure, or even a uniform band?  Those are counts over
artifact code and over reproduced training samples, and the paper's rule is
that no number reaches prose without a script writing it to results/.  This
script is that script.  Everything here is deterministic re-reading of
committed JSONs (the training-sample reproduction uses the same
split_for_cell convention the audit pins): no network, no sandbox.

Emits results/ring2d_neck_synthesis_scan.json.
"""
import json
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.heldout import env_from_params, split_for_cell  # noqa: E402

RESULTS = _REPO / "results"

# Tokens any angular parameterization of the sector would need. `atan2` is the
# operational one (the truth's sector test uses it); the rest catch a model
# that names the concept without computing it.
ANGULAR = re.compile(
    r"\batan2\b|\btheta\b|\bangles?\b|\bsector\b|\barc\b|\bangular\b",
    re.IGNORECASE)

# A two-sided (band/annulus) condition on a radial variable: one line testing
# a distance both from below and from above.  The truth's mode test is
# `r_in <= d <= r_out`; any spelling of it needs two comparisons on the same
# line ('a <= d <= b', or 'd >= a and d <= b').
def _has_band_condition(code: str) -> bool:
    for line in code.splitlines():
        if "if" not in line:
            continue
        comps = re.findall(r"[<>]=?", line)
        if len(comps) >= 2 and re.search(r"\bd2?\b|\bdist\w*\b|\br\b", line):
            # both directions present (not e.g. 'a < x and b < y')
            if any(c.startswith("<") for c in comps) and \
               any(c.startswith(">") for c in comps):
                return True
            # chained 'a <= d <= b' uses same-direction comparators around d
            if re.search(r"[<>]=?\s*\w+\s*[<>]=?", line):
                return True
    return False


# An exact-coordinate point trap: equality (or tolerance below the gate's
# 1e-9 eps) against a float literal with >= 8 decimals — the "textual point
# fit" family the paper describes.
POINT_TRAP = re.compile(r"==\s*-?\d+\.\d{8,}|abs\([^)]*\)\s*<\s*1e-1\d")


def main() -> None:
    files = sorted(RESULTS.glob("continuous_synthesis_ring2d_*_gap0-nk*.json"))
    if not files:
        raise SystemExit("no thin-neck synthesis campaigns in results/")
    rows, totals = [], {"artifacts": 0, "angular": 0, "band": 0,
                        "point_traps": 0, "gate_passes": 0,
                        "gate_passes_blind": 0}
    for f in files:
        d = json.loads(f.read_text())
        env = env_from_params(d["params"])
        row = {"file": f.name, "model": d["model"],
               "neck": d["params"]["neck"], "n_artifacts": len(d["cells"]),
               "n_angular": 0, "n_band": 0, "n_point_traps": 0,
               "n_free_flight": 0, "n_gate_passes": 0,
               "n_gate_passes_blind": 0, "n_train_mode_present": 0,
               "leap_seeds": []}
        for c in d["cells"]:
            code = c["code"] or ""
            row["n_angular"] += bool(ANGULAR.search(code))
            row["n_band"] += _has_band_condition(code)
            row["n_point_traps"] += bool(POINT_TRAP.search(code))
            # free flight: no conditional at all in step()
            step_src = code.split("def reward")[0]
            row["n_free_flight"] += ("if" not in
                                     step_src.split("def step")[-1])
            row["n_gate_passes"] += bool(c["gate_passed"])
            row["n_gate_passes_blind"] += bool(
                c["gate_passed"] and c.get("wall_blindness") == 1.0)
            row["n_train_mode_present"] += bool(c["sample_contains_wall"])
            d_train, _, _ = split_for_cell(env, c, n_eval=1)
            n_leap = sum(1 for t in d_train
                         if env.in_interior(t["next_state"][0],
                                            t["next_state"][1]))
            if n_leap:
                row["leap_seeds"].append(
                    {"seed": c["seed"], "n_interior_landings": n_leap,
                     "gate_accuracy": c["gate_accuracy"],
                     "gate_passed": c["gate_passed"],
                     "artifact_has_angular": bool(ANGULAR.search(code)),
                     "artifact_has_band": _has_band_condition(code)})
        totals["artifacts"] += row["n_artifacts"]
        totals["angular"] += row["n_angular"]
        totals["band"] += row["n_band"]
        totals["point_traps"] += row["n_point_traps"]
        totals["gate_passes"] += row["n_gate_passes"]
        totals["gate_passes_blind"] += row["n_gate_passes_blind"]
        rows.append(row)
    out = RESULTS / "ring2d_neck_synthesis_scan.json"
    out.write_text(json.dumps(
        {"script": "ring2d_neck_synthesis_scan.py",
         "definitions": {
             "angular": ANGULAR.pattern,
             "band": "one if-line comparing a radial variable from both "
                     "sides (any spelling of r_in <= d <= r_out)",
             "point_trap": POINT_TRAP.pattern,
             "leap": "training transition landing strictly inside the hole "
                     "(env.in_interior on the reproduced D_train)"},
         "rows": rows, "totals": totals}, indent=1))
    print(f"wrote {out}")
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
