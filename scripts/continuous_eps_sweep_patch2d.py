"""PatchField2D arm of the eps-sensitivity sweep (paper 2, sec:axes).

The 4D bi-modal instrument's mode-omission arms (both patches omitted, patch 1
only, patch 2 only) swept over the gate tolerance eps: reveal-rarity is flat
across the whole grid, once per mode, so the tolerance axis is orthogonal to
the per-mode identifiability hole on this instrument too.

The measurement code is NOT duplicated here. It lives in
scripts/continuous_eps_sweep.py, whose --instrument patch2d path this entry
point runs with the PatchField2D arms, so the 1D and 2D paths cannot drift
apart and this script's numbers are identical by construction to

    PYTHONPATH=src python scripts/continuous_eps_sweep.py --instrument patch2d

Extra flags (--eps-grid, --rollouts, --n-gate, --gates, --seed) are forwarded
verbatim. Output: results/continuous_eps_sweep_patch2d.json (with entry_point
recorded).

Run: PYTHONPATH=src python scripts/continuous_eps_sweep_patch2d.py  (~10 min CPU)
"""
import json
import pathlib
import runpy
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parent
_DELEGATE = _HERE / "continuous_eps_sweep.py"
_OUT = _REPO / "results" / "continuous_eps_sweep_patch2d.json"

if "--instrument" in sys.argv[1:]:
    sys.exit("continuous_eps_sweep_patch2d.py fixes --instrument patch2d; "
             "use scripts/continuous_eps_sweep.py for the 1D instruments")

sys.path.insert(0, str(_REPO / "src"))       # works without PYTHONPATH too
sys.argv = [str(_DELEGATE), "--instrument", "patch2d", *sys.argv[1:]]
runpy.run_path(str(_DELEGATE), run_name="__main__")

_payload = json.loads(_OUT.read_text())
_payload["entry_point"] = "continuous_eps_sweep_patch2d.py"
_OUT.write_text(json.dumps(_payload, indent=2))
print(f"stamped entry_point in {_OUT}", flush=True)
