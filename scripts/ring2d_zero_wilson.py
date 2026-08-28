"""Wilson 95% upper bounds for the thin-neck censored zeros.

The tex quotes three uppers for the per-cell censored-zero rows of the
thin-neck sweep (0 interior entries in 30,000 rollouts; 0 disagreeing
transitions in 320,000 sampled transitions; 0 leaking episodes of 16).
This script emits them from the committed sweep's own denominators so
the numbers are script-emitted rather than hand-derived
(round-3 review, finding 5).

Reads  results/ring2d_thin_neck.json
Writes results/ring2d_zero_wilson.json
"""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.law import wilson_ci  # noqa: E402

SRC = _REPO / "results" / "ring2d_thin_neck.json"
DST = _REPO / "results" / "ring2d_zero_wilson.json"


def main() -> None:
    doc = json.loads(SRC.read_text())
    rows = doc["rows"]
    denominators = {
        "rollouts": sorted({r["rollouts"] for r in rows}),
        "transitions": sorted({r["transitions"] for r in rows}),
        "episodes": sorted({r["n_episodes"] for r in rows}),
    }
    for key, vals in denominators.items():
        assert len(vals) == 1, f"non-uniform {key}: {vals}"
    out = {
        "script": "ring2d_zero_wilson.py",
        "source": "results/ring2d_thin_neck.json",
        "definition": ("Wilson 95% upper bound for a rate observed 0 "
                       "times in n trials, per censored-zero row of the "
                       "thin-neck sweep; denominators are the sweep's own "
                       "(uniform across rows)."),
        "uppers": {
            key: {"n": vals[0], "k": 0,
                  "wilson95_upper": wilson_ci(0, vals[0])[2]}
            for key, vals in denominators.items()
        },
    }
    DST.write_text(json.dumps(out, indent=1))
    for key, v in out["uppers"].items():
        print(f"{key}: 0/{v['n']} -> upper {v['wilson95_upper']:.4e}")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
