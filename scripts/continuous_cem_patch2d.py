"""PatchField2D arm of the second-planner-family experiment (paper 2, sec:cem).

The 4D bi-modal instrument's CEM rows: the same certified-blind models under
CEM instead of random-shooting MPC, with the imagined boundary-crossing
fraction for both planners (the measured query-hit proxy of Proposition 3).

The measurement code is NOT duplicated here. It lives in
scripts/continuous_cem.py, whose --instrument patch2d path this entry point
runs with the PatchField2D configuration, so the 1D and 2D paths cannot drift
apart and this script's numbers are identical by construction to

    PYTHONPATH=src python scripts/continuous_cem.py --instrument patch2d

Extra flags (--episodes, --seed, --patch2d-knobs) are forwarded verbatim.
Output: results/continuous_cem_patch2d.json (with entry_point recorded).

Run: PYTHONPATH=src python scripts/continuous_cem_patch2d.py   (~20 min CPU)
"""
import json
import pathlib
import runpy
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parent
_DELEGATE = _HERE / "continuous_cem.py"
_OUT = _REPO / "results" / "continuous_cem_patch2d.json"

if "--instrument" in sys.argv[1:]:
    sys.exit("continuous_cem_patch2d.py fixes --instrument patch2d; "
             "use scripts/continuous_cem.py directly for the 1D instruments")

sys.path.insert(0, str(_REPO / "src"))       # works without PYTHONPATH too
sys.argv = [str(_DELEGATE), "--instrument", "patch2d", *sys.argv[1:]]
runpy.run_path(str(_DELEGATE), run_name="__main__")

# Provenance: the JSON records the implementation in "script"; name the entry
# point too, so a reader who came from the paper's citation can tell which
# command produced the file.
_payload = json.loads(_OUT.read_text())
_payload["entry_point"] = "continuous_cem_patch2d.py"
_OUT.write_text(json.dumps(_payload, indent=2))
print(f"stamped entry_point in {_OUT}", flush=True)
