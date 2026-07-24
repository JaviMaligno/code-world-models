"""Shape2D calibration artifact schema + strict anti-placeholder validator.

`validate_calibration_artifact` is the Phase-A/B gate (task-13-brief.md): the
validated `results/shape2d_calibration.json` this produces authorizes Phase
B's ~520 Azure syntheses, so it must be IMPOSSIBLE for a placeholder (empty
cells, a None field, a fabricated "measured" claim, an accidentally-certified
`sufficiency`) to pass. Every check below corresponds 1:1 to a way
`scripts/calibrate_shape2d.py`'s ledger could be faked rather than measured;
see the module docstring there for how each field is actually produced.

`validate_calibration_artifact` never raises on a malformed artifact -- it
degrades every lookup to "missing" and keeps collecting problems, so a single
call surfaces every defect at once (this is exercised directly by
`test_validator_rejects_placeholder`, which expects four independent
problems from one malformed artifact).
"""
import math

# The frozen manifest: every anchor/curvature/composition/contrast cell of
# the shape2d sweep. Frozen so the tests (and the gate) are deterministic --
# adding or dropping a cell must be a deliberate, reviewed change to this
# tuple, never a side effect of a script bug.
EXPECTED_CELL_IDS = frozenset({
    "anchor_halfplane",
    "curv_parabola_R8", "curv_parabola_R4", "curv_parabola_R2", "curv_parabola_R1",
    "comp_strip", "comp_wedge",
    "comp_triangle_face", "comp_triangle_vertex",
    "comp_square_face", "comp_square_vertex",
    "comp_hexagon_face", "comp_hexagon_vertex",
    "contrast_parabola", "contrast_circle",
})

# Fixed minimums / bounds the strict gate enforces. These are deliberately
# below what the full (non-quick) run of calibrate_shape2d.py actually
# produces, so the full run has headroom rather than sitting exactly at the
# threshold.
N_ROLLOUTS_MIN = 200
N_EPISODES_MIN = 15
PLAY_COST_BLIND_MIN = 0.8
GRID_DELTA_MAX = 0.01

REQUIRED_REPAIRED_SOURCE = "truth_oracle_fullarm_griderror"

# The uniform top-level provenance block: one entry per global parameter.
_TOP_PROVENANCE_KEYS = (
    "box", "grid_n", "rarity_target", "delta",
    "repaired_threshold", "frac_planner_outside_box",
)

_SUFFICIENCY_KEYS = {"certified", "tau_s", "reason"}

# Per-cell fields that must be present and non-placeholder.
_CELL_REQUIRED_FIELDS = (
    "rarity", "rarity_ci", "n_rollouts", "n_episodes",
    "play_cost_blind", "grid_delta_256_512", "provenance",
)

_TOP_REQUIRED_SCALARS = (
    "box", "grid_n", "rarity_target", "rarity_tol", "delta",
    "frac_planner_outside_box", "frac_outside_box_bound",
    "cal_seed_stream", "val_seed_stream",
)

_REPAIRED_THRESHOLD_FIELDS = ("band_disagreement", "fpr", "source")


def _is_placeholder(v) -> bool:
    """True for the placeholder signatures this gate must reject: missing
    (None), NaN, or an empty list/tuple. A plain 0/0.0/False/"" is NOT a
    placeholder -- those are legitimate measured values."""
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return True
    return False


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_numeric(v, label: str, problems: list[str]) -> None:
    """Append a problem if `v` is present (non-placeholder) but not a real
    number (bool counts as non-numeric here, even though bool is technically
    an int subclass) -- this is what closes the gap where a field like
    "n_rollouts": "big" would otherwise silently skip its threshold check."""
    if not _is_placeholder(v) and not _is_number(v):
        problems.append(f"{label} must be numeric, got {type(v).__name__}")


def validate_calibration_artifact(art) -> list[str]:
    """Empty list = valid. See module docstring: never raises, always
    collects every violated constraint from a single pass."""
    problems: list[str] = []

    if not isinstance(art, dict):
        return ["artifact is not a dict"]

    # --- cells: exact manifest match, no duplicates ------------------------
    cells = art.get("cells")
    if not isinstance(cells, list):
        problems.append("cells: missing or not a list")
        cells = []
    ids = [c.get("id") for c in cells if isinstance(c, dict)]
    id_set = set(ids)
    if id_set != EXPECTED_CELL_IDS:
        missing = EXPECTED_CELL_IDS - id_set
        extra = id_set - EXPECTED_CELL_IDS
        detail = []
        if missing:
            detail.append(f"missing {sorted(missing)}")
        if extra:
            detail.append(f"extra {sorted(extra)}")
        problems.append("cells: manifest mismatch (" + "; ".join(detail) + ")")
    if len(ids) != len(set(ids)):
        problems.append("cells: duplicate cell id(s) present")

    # --- top-level scalar fields: none may be a placeholder -----------------
    for f in _TOP_REQUIRED_SCALARS:
        if _is_placeholder(art.get(f)):
            problems.append(f"{f}: missing/None/NaN/empty")

    # --- calibration/validation seed streams must be independent ------------
    cal_seed, val_seed = art.get("cal_seed_stream"), art.get("val_seed_stream")
    if cal_seed is not None and val_seed is not None and cal_seed == val_seed:
        problems.append(
            "cal_seed_stream and val_seed_stream must be distinct independent "
            f"seed streams (both are {cal_seed!r})")

    # --- frac_planner_outside_box must stay under its explicit bound --------
    fpob, bound = art.get("frac_planner_outside_box"), art.get("frac_outside_box_bound")
    _check_numeric(fpob, "frac_planner_outside_box", problems)
    _check_numeric(bound, "frac_outside_box_bound", problems)
    if _is_number(fpob) and _is_number(bound) and fpob > bound:
        problems.append(
            f"frac_planner_outside_box {fpob} exceeds frac_outside_box_bound {bound}")

    # --- repaired_threshold: must be sourced from the truth-oracle grid error
    rt = art.get("repaired_threshold")
    if not isinstance(rt, dict):
        problems.append("repaired_threshold: missing or not a dict")
        rt = {}
    for f in _REPAIRED_THRESHOLD_FIELDS:
        if _is_placeholder(rt.get(f)):
            problems.append(f"repaired_threshold.{f}: missing/None/NaN/empty")
    if rt.get("source") != REQUIRED_REPAIRED_SOURCE:
        problems.append(
            f"repaired_threshold.source must be {REQUIRED_REPAIRED_SOURCE!r} "
            f"(got {rt.get('source')!r})")

    # --- uniform top-level provenance block: one entry per global param -----
    prov = art.get("provenance")
    if not isinstance(prov, dict):
        problems.append("provenance: missing or not a dict")
        prov = {}
    for f in _TOP_PROVENANCE_KEYS:
        if _is_placeholder(prov.get(f)):
            problems.append(f"provenance.{f}: missing/None/NaN/empty")

    # --- sufficiency: Phase A leaves S uncertified --------------------------
    suff = art.get("sufficiency")
    if not isinstance(suff, dict) or set(suff.keys()) != _SUFFICIENCY_KEYS:
        problems.append(
            "sufficiency: must be exactly {certified, tau_s, reason} "
            f"(got {suff!r})")
        suff = suff if isinstance(suff, dict) else {}
    if suff.get("certified") is not False:
        problems.append(
            "sufficiency.certified must be exactly False -- Phase A does not "
            "certify a sufficiency bound")
    if suff.get("tau_s") is not None:
        problems.append(
            "sufficiency.tau_s must be None -- Phase A leaves S uncertified, "
            "tau_s must never appear as a calibrated number")
    reason = suff.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        problems.append("sufficiency.reason must be a non-empty string")

    # --- per-cell checks -----------------------------------------------------
    rarity_target, rarity_tol = art.get("rarity_target"), art.get("rarity_tol")
    _check_numeric(rarity_target, "rarity_target", problems)
    _check_numeric(rarity_tol, "rarity_tol", problems)
    for c in cells:
        if not isinstance(c, dict):
            problems.append("cells: entry is not a dict")
            continue
        cid = c.get("id", "<unknown>")

        for f in _CELL_REQUIRED_FIELDS:
            if _is_placeholder(c.get(f)):
                problems.append(f"cell {cid}: {f} missing/None/NaN/empty")

        rarity_ci = c.get("rarity_ci")
        if isinstance(rarity_ci, list) and any(_is_placeholder(v) for v in rarity_ci):
            problems.append(f"cell {cid}: rarity_ci contains a placeholder value")
        if isinstance(rarity_ci, list):
            for i, v in enumerate(rarity_ci):
                _check_numeric(v, f"cell {cid}: rarity_ci[{i}]", problems)

        n_rollouts = c.get("n_rollouts")
        _check_numeric(n_rollouts, f"cell {cid}: n_rollouts", problems)
        if _is_number(n_rollouts) and n_rollouts < N_ROLLOUTS_MIN:
            problems.append(
                f"cell {cid}: n_rollouts {n_rollouts} below minimum {N_ROLLOUTS_MIN}")

        n_episodes = c.get("n_episodes")
        _check_numeric(n_episodes, f"cell {cid}: n_episodes", problems)
        if _is_number(n_episodes) and n_episodes < N_EPISODES_MIN:
            problems.append(
                f"cell {cid}: n_episodes {n_episodes} below minimum {N_EPISODES_MIN}")

        grid_delta = c.get("grid_delta_256_512")
        _check_numeric(grid_delta, f"cell {cid}: grid_delta_256_512", problems)
        if _is_number(grid_delta) and not (isinstance(grid_delta, float) and math.isnan(grid_delta)):
            if grid_delta >= GRID_DELTA_MAX:
                problems.append(
                    f"cell {cid}: grid_delta_256_512 {grid_delta} not converged "
                    f"(>= {GRID_DELTA_MAX}); grid_converged must be backed by a "
                    f"measured per-cell delta below this bound")

        play_cost_blind = c.get("play_cost_blind")
        _check_numeric(play_cost_blind, f"cell {cid}: play_cost_blind", problems)
        if _is_number(play_cost_blind) and play_cost_blind < PLAY_COST_BLIND_MIN:
            problems.append(
                f"cell {cid}: play_cost_blind {play_cost_blind} below "
                f"{PLAY_COST_BLIND_MIN} -- blind planner is not exploited")

        rarity = c.get("rarity")
        _check_numeric(rarity, f"cell {cid}: rarity", problems)
        if _is_number(rarity) and _is_number(rarity_target) and _is_number(rarity_tol):
            if abs(rarity - rarity_target) > rarity_tol:
                problems.append(
                    f"cell {cid}: rarity {rarity} outside rarity_target "
                    f"{rarity_target} +/- {rarity_tol}")

    return problems
