"""Score every committed synthesized artifact on INDEPENDENT samples (paper 2,
review point #1).

The reviewed objection: the paper's "gate score 1.000" was computed on the same
sample the artifact was synthesized and refined on, so it measures training-set
consistency, not verification.  Every cell of results/continuous_synthesis_*.json
stores its own source `code`, its truth-env knobs (the file's top-level
`params`) and the rollout `seed` of its training sample, so the three-way split

    D_train = collect_transitions(env, cell["n_rollouts"], seed)                # reproduced
    D_gate  = collect_transitions(env, 40,  seed + 5_000_000)                   # independent gate
    D_eval  = collect_transitions(env, 100, seed + 7_000_000)                   # independent eval

can be built after the fact for zero LLM cost.  NOTHING here calls a network
API: the only external process is the same sandbox subprocess the original gate
used.

Run (from the repo root):
    PYTHONPATH=src python scripts/heldout_gate_audit.py            # all 625
    PYTHONPATH=src python scripts/heldout_gate_audit.py --limit 6  # smoke

Resumable and idempotent: results/heldout_gate_audit.json is rewritten
atomically after EVERY artifact and any (file, arm, seed) already present is
skipped, so a killed run resumes where it stopped and a completed run re-run is
a no-op (hard project rule for long runs).  A resume whose --n-gate/--n-eval
disagree with the stored ones is refused rather than silently mixed.

What it answers (all written to the JSON, all printed):
  (a) for artifacts whose TRAINING sample missed the mode, does held-out
      acceptance coincide exactly with "D_gate also missed the mode"?  -- the
      2x2 contingency test of the two-factor law
      P(blind AND accepted) = (1-r)^{N_train} (1-r)^{N_gate};
  (b) the measured P(accepted_heldout AND mode-blind) per campaign against
      that predicted product, with the r used and the JSON it was read from;
  (c) how many artifacts that passed the ORIGINAL in-sample gate FAIL the
      independent gate, split by campaign and by failure class;
  (d) out-of-sample exactness: for how many artifacts is EVERY failing
      transition of D_eval a mode contact ("exact outside the mode region") --
      the paper currently asserts this as a code-inspected regularity.
"""
import argparse
import json
import os
import pathlib
import sys
import time
from collections import Counter, defaultdict

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.contract import contract_accuracy  # noqa: E402
from cwm.continuous.heldout import (  # noqa: E402
    EVAL_SEED_OFFSET, GATE_SEED_OFFSET, N_EVAL_DEFAULT, N_GATE, R_SOURCES,
    TRAIN_N_ROLLOUTS, blind_from_cell, contingency, disjointness_report,
    env_from_params,
    env_key, failure_class, independence_surrogate, mode_presence,
    score_transitions, split_for_cell, wilson)

OUT_DEFAULT = _REPO / "results" / "heldout_gate_audit.json"
SYNTH_GLOB = "continuous_synthesis_*.json"

# The DEFAULT scope: paper 2's instruments. Its committed output
# (results/heldout_gate_audit.json) reproduces the PUBLISHED numbers, so this
# tuple never widens; completeness of that file is judged against it (see
# tests/test_heldout_gate.py::test_committed_audit_json_is_self_consistent).
# Paper 3's ring2d campaigns are audited by the SAME script under
# `--instruments ring2d` with their own --out (the rarity decision and the
# R_SOURCES entries landed 2026-08-24); the two scopes never share a file.
AUDITED_INSTRUMENTS = ("cart", "pendulum", "patch2d")


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Temp file in the same directory + os.replace (a single POSIX rename), so
    a kill at any instant leaves either the old file or the complete new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


# --- rarity provenance: re-derive every constant from its source JSON --------
def _read_row(path: pathlib.Path, match: dict) -> dict:
    d = json.loads(path.read_text())
    for row in d["rows"]:
        if all(row.get(k) == v for k, v in match.items()):
            return row
    raise KeyError(f"no row matching {match} in {path}")


def verify_r_sources() -> dict:
    """Re-read every rarity from the JSON that produced it and refuse to run if
    a hand-copied constant in heldout.R_SOURCES has drifted.  (Project rule:
    numbers that reach the paper are derived by a script from results/, never
    hand-carried.)"""
    checks = {}
    reach = _REPO / "results" / "continuous_reach.json"
    pend = _REPO / "results" / "continuous_pendulum.json"
    p2d = _REPO / "results" / "continuous_patch2d.json"
    p2dsq = _REPO / "results" / "continuous_patch2d_square.json"
    slab = _REPO / "results" / "patch2d_slab_calibration.json"
    meff = _REPO / "results" / "mode_effect_calibration.json"
    _slab = json.loads(slab.read_text())["units"]["rarity_imperm"]["measure"]
    _meff = json.loads(meff.read_text())["variants"]
    live = {
        "patch2d_k3_7_landing": _meff["landing"]["rarity"],
        "patch2d_k3_7_clamp": _meff["clamp"]["rarity"],
        "cart_xwall8": _read_row(reach, {"x_wall": 8.0})["rarity"],
        "cart_xwall4": _read_row(reach, {"x_wall": 4.0})["rarity"],
        "pendulum_thstop1.4": _read_row(pend, {"th_stop": 1.4})["rarity"],
        "pendulum_thstop1": _read_row(pend, {"th_stop": 1.0})["rarity"],
        "patch2d_k3_7": _read_row(p2d, {"k1": 3.0, "k2": 7.0})["r_either"],
    }
    per_mode_live = {
        "patch2d_k3_7": {
            "patch1": _read_row(p2d, {"k1": 3.0, "k2": 7.0})["r1"],
            "patch2": _read_row(p2d, {"k1": 3.0, "k2": 7.0})["r2"]},
        "patch2dsq_k3_7": {
            "patch1": _read_row(p2dsq, {"k1": 3.0, "k2": 7.0})["r1"],
            "patch2": _read_row(p2dsq, {"k1": 3.0, "k2": 7.0})["r2"]},
        "patch2dsq_k5_9": {
            "patch1": _read_row(p2dsq, {"k1": 5.0, "k2": 9.0})["r1"],
            "patch2": _read_row(p2dsq, {"k1": 5.0, "k2": 9.0})["r2"]},
        "patch2dslab_k5.5_7": {"patch1": _slab["r1"], "patch2": None},
    }
    # ring2d (paper 3): every entry reads results/ring2d_rarity_sweep.json by
    # its knob string, which is the env_key minus the "ring2d_" prefix and any
    # "_n{...}" dose suffix (the dose campaigns share their config's row).
    # Both r AND the carried r_interior are re-read -- a provenance field that
    # drifts is as wrong as a prediction argument that drifts.
    ring_sweep = _REPO / "results" / "ring2d_rarity_sweep.json"
    _ring_rows = {row["knob"]: row
                  for row in json.loads(ring_sweep.read_text())["rows"]}
    # Thin-neck cells were calibrated by their own 30k sweep
    # (results/ring2d_thin_neck.json), whose rows key on "nk{...}" /
    # "nk{...}-hid" without the campaign knob's "gap0-" prefix.
    thin_neck = _REPO / "results" / "ring2d_thin_neck.json"
    _thin_rows = {row["knob"]: row
                  for row in json.loads(thin_neck.read_text())["rows"]}
    ring_interior_live = {}
    for key in R_SOURCES:
        if not key.startswith("ring2d_"):
            continue
        knob = key[len("ring2d_"):].split("_n")[0]
        if "-nk" in knob:
            tail = knob.split("-nk", 1)[1]
            tknob = (f"nk{tail[:-1]}-hid" if tail.endswith("h")
                     else f"nk{tail}")
            row = _thin_rows[tknob]
        else:
            row = _ring_rows[knob]
        live[key] = row["r"]
        ring_interior_live[key] = row["r_interior"]
    drift = []
    for key, val in ring_interior_live.items():
        if R_SOURCES[key].get("r_interior") != val:
            drift.append((f"{key}.r_interior",
                          R_SOURCES[key].get("r_interior"), val))
    for key, val in live.items():
        if R_SOURCES[key]["r"] != val:
            drift.append((key, R_SOURCES[key]["r"], val))
    for key, per in per_mode_live.items():
        stored = R_SOURCES[key]["per_mode"] or {}
        for m, v in per.items():
            if stored.get(m) != v:
                drift.append((f"{key}.{m}", stored.get(m), v))
    if drift:
        raise SystemExit(f"rarity constants drifted from results/: {drift}")
    out = {}
    for key, meta in R_SOURCES.items():
        entry = dict(meta)
        entry["verified_against_source"] = key in live or key in per_mode_live
        pm = meta.get("per_mode") or {}
        if meta["r"] is None and pm.get("patch1") is not None \
                and pm.get("patch2") is not None:
            entry["r_union_independence_surrogate"] = independence_surrogate(
                pm["patch1"], pm["patch2"])
            entry["r_union_independence_surrogate_note"] = (
                "DERIVED, not measured: r1 + r2 - r1*r2 assuming the two modes "
                "fire independently within a rollout; used only because no "
                "union rarity is committed for this cell")
        elif meta["r"] is None:
            entry["r_union_independence_surrogate"] = None
            entry["r_union_independence_surrogate_note"] = (
                "ABSENT: not every per-mode rarity for this cell was measured, so "
                "even the surrogate has no inputs. Reported as null rather than "
                "filled in from a comparable cell")
        out[key] = entry
    return out


# --- one artifact -------------------------------------------------------------
def audit_artifact(path: pathlib.Path, results_doc: dict, cell: dict, *,
                   n_gate: int, n_eval: int, timeout_gate: float,
                   timeout_eval: float, validate_train: bool) -> dict:
    params = results_doc["params"]
    env = env_from_params(params)
    ek = env_key(params)
    d_train, d_gate, d_eval = split_for_cell(env, cell, n_eval=n_eval,
                                             n_gate=n_gate)
    m_train = mode_presence(env, d_train)
    m_gate = mode_presence(env, d_gate)
    m_eval = mode_presence(env, d_eval)
    sg = score_transitions(cell["code"], d_gate, cell["eps"],
                           timeout=timeout_gate)
    se = score_transitions(cell["code"], d_eval, cell["eps"],
                           timeout=timeout_eval)
    rec = {
        "file": path.name,
        "campaign": path.stem.replace("continuous_synthesis_", ""),
        "env_key": ek,
        "instrument": params.get("instrument", "cart"),
        "patch_shape": params.get("patch_shape", "disc"),
        "model": results_doc.get("model"),
        "size": results_doc.get("size"),
        "tag": results_doc.get("tag"),
        "prompt_variant": params.get("prompt_variant", "default"),
        "seed_offset": params.get("seed_offset", 0),
        "arm": cell["arm"],
        "seed": cell["seed"],
        "eps": cell["eps"],
        "n_train_rollouts": cell.get("n_rollouts"),
        "block_key": f"{ek}@{cell['seed']}",
        # the original, in-sample numbers, for the regression comparison
        "in_sample_gate_accuracy": cell["gate_accuracy"],
        "in_sample_gate_passed": cell["gate_passed"],
        "in_sample_refine_iterations": cell.get("refine_iterations"),
        "probe_blind_all_modes": blind_from_cell(cell),
        "probe_blindness": cell.get("mode_blindness", cell.get("wall_blindness")),
        "mode_in_train": m_train,
        "mode_in_gate": m_gate,
        "mode_in_eval": m_eval,
        "gate": sg.to_json(),
        "eval": se.to_json(),
        "accepted_heldout": sg.accuracy == 1.0,
        "gate_failure_class": failure_class(sg.to_json()),
        "eval_failure_class": failure_class(se.to_json()),
        # sample-based blindness surrogates: every mode contact of the held-out
        # sample is predicted wrong (the probe-based blindness is only defined
        # for artifacts whose ORIGINAL gate reached 1.0)
        "heldout_blind_gate": (
            None if m_gate["n_contact_transitions"] == 0
            else sg.n_fail_mode_contact == m_gate["n_contact_transitions"]),
        "heldout_blind_eval": (
            None if m_eval["n_contact_transitions"] == 0
            else se.n_fail_mode_contact == m_eval["n_contact_transitions"]),
    }
    if validate_train:
        # Independent confirmation that the truth env / seed reconstruction is
        # right: re-scoring the artifact on its REPRODUCED training sample must
        # give back the accuracy the original run recorded.
        acc_train, _ = contract_accuracy(cell["code"], d_train, cell["eps"],
                                         timeout=timeout_gate)
        rec["train_reproduction"] = {
            "recomputed_train_accuracy": acc_train,
            "stored_gate_accuracy": cell["gate_accuracy"],
            "matches": abs(acc_train - cell["gate_accuracy"]) < 1e-12,
            "mode_in_train_recomputed": m_train["any"],
            "mode_in_train_stored": cell["sample_contains_wall"],
            "mode_flag_matches": m_train["any"] == cell["sample_contains_wall"],
        }
    return rec


# --- aggregation --------------------------------------------------------------
def _dedupe_blocks(recs: list[dict]) -> int:
    return len({r["block_key"] for r in recs})


def _two_factor(recs: list[dict], n_train: int, n_gate: int) -> dict:
    """(b) measured P(accepted_heldout AND mode-blind) vs the predicted product
    (1-r)^{N_train} (1-r)^{N_gate}, on the incomplete arm of one campaign."""
    inc = [r for r in recs if r["arm"] == "incomplete"]
    ek = recs[0]["env_key"]
    if ek not in R_SOURCES:
        # hard error rather than a silently-null prediction: a new instrument
        # cell must get an explicit rarity entry (with provenance) or an
        # explicit "uncalibrated" entry.
        raise SystemExit(f"no rarity entry for env_key {ek!r} in "
                         f"heldout.R_SOURCES; add one (with its source JSON) "
                         f"before auditing that campaign")
    meta = R_SOURCES[ek]
    r = meta.get("r")
    surrogate = None
    _pm = meta.get("per_mode") or {}
    # Both per-mode rarities have to exist: the slab's patch-2 rarity was never
    # measured, and a surrogate built from a missing input would be a fabrication
    # dressed as a derivation.
    if r is None and _pm.get("patch1") is not None and _pm.get("patch2") is not None:
        surrogate = independence_surrogate(_pm["patch1"], _pm["patch2"])
    # blind: the paper's probe-based event (fully blind on every mode).  Cells
    # whose ORIGINAL gate failed have no probe reading -> counted as not blind
    # for the joint event, and reported separately.
    k = sum(1 for r_ in inc
            if r_["accepted_heldout"] and r_["probe_blind_all_modes"] is True)
    n = len(inc)
    k_sample = sum(1 for r_ in inc
                   if r_["accepted_heldout"] and r_["mode_in_train"]["any"] is False
                   and r_["mode_in_gate"]["any"] is False)
    r_used = r if r is not None else surrogate
    pred = None if r_used is None else (1 - r_used) ** (n_train + n_gate)
    return {
        "n_incomplete_artifacts": n,
        "n_independent_blocks": _dedupe_blocks(inc),
        "k_accepted_and_probe_blind": k,
        "measured_accepted_and_probe_blind": (k / n) if n else None,
        "wilson95": wilson(k, n),
        "k_train_miss_and_gate_miss_and_accepted": k_sample,
        "measured_train_miss_and_gate_miss_and_accepted": (
            (k_sample / n) if n else None),
        "r_used": r_used,
        "r_is_measured": r is not None,
        "r_kind": meta.get("kind"),
        "r_source": meta.get("source"),
        "r_source_path": meta.get("path"),
        "r_union_independence_surrogate": surrogate,
        "N_train": n_train, "N_gate": n_gate,
        "predicted_two_factor": pred,
        "predicted_single_factor_train_only": (
            None if r_used is None else (1 - r_used) ** n_train),
    }


def aggregate(artifacts: list[dict], n_gate: int, n_eval: int) -> dict:
    by_campaign: dict[str, list[dict]] = defaultdict(list)
    for r in artifacts:
        by_campaign[r["file"]].append(r)

    # --- (a) the 2x2 on training-mode-absent artifacts ------------------------
    absent = [r for r in artifacts if not r["mode_in_train"]["any"]]
    row = lambda r: r["mode_in_gate"]["any"]          # noqa: E731
    col = lambda r: r["accepted_heldout"]             # noqa: E731
    a = {
        "definition": (
            "restricted to artifacts whose TRAINING sample contained no mode "
            "contact; rows = D_gate contains a mode contact, cols = held-out "
            "gate accuracy == 1.0.  'coincides_exactly' is the empirical test "
            "of the two-factor law's second factor."),
        "all_arms": contingency(absent, row_key=row, col_key=col),
        "incomplete_arm": contingency(
            [r for r in absent if r["arm"] == "incomplete"],
            row_key=row, col_key=col),
        "full_arm": contingency([r for r in absent if r["arm"] == "full"],
                                row_key=row, col_key=col),
        "incomplete_arm_probe_blind_only": contingency(
            [r for r in absent if r["arm"] == "incomplete"
             and r["probe_blind_all_modes"] is True],
            row_key=row, col_key=col),
        "by_campaign": {
            f: contingency([r for r in recs if not r["mode_in_train"]["any"]
                            and r["arm"] == "incomplete"],
                           row_key=row, col_key=col)
            for f, recs in sorted(by_campaign.items())},
        "n_independent_blocks": _dedupe_blocks(absent),
    }

    # --- (b) two-factor law per campaign -------------------------------------
    b = {}
    for f, recs in sorted(by_campaign.items()):
        n_train = recs[0]["n_train_rollouts"] or 40
        b[f] = _two_factor(recs, n_train, n_gate)
        b[f]["env_key"] = recs[0]["env_key"]
        b[f]["model"] = recs[0]["model"]

    # --- (c) in-sample pass -> held-out fail ---------------------------------
    regressions = [r for r in artifacts
                   if r["in_sample_gate_passed"] and not r["accepted_heldout"]]
    # the other direction: an artifact the ORIGINAL gate refused that an
    # independent gate would have ACCEPTED (it failed only on training
    # transitions the held-out block happens not to contain).  Same coin as the
    # regressions, and equally a consequence of scoring on one sample.
    reverse = [r for r in artifacts
               if not r["in_sample_gate_passed"] and r["accepted_heldout"]]
    c = {
        "definition": ("artifacts whose ORIGINAL in-sample gate reached 1.000 "
                       "but whose independent D_gate accuracy is < 1.0"),
        "n_in_sample_passed": sum(1 for r in artifacts
                                  if r["in_sample_gate_passed"]),
        "n_regressions": len(regressions),
        "reverse_definition": ("artifacts the in-sample gate REFUSED that the "
                               "independent gate accepts"),
        "n_reverse_regressions": len(reverse),
        "reverse_detail": [
            {"file": r["file"], "arm": r["arm"], "seed": r["seed"],
             "env_key": r["env_key"], "model": r["model"],
             "in_sample_gate_accuracy": r["in_sample_gate_accuracy"],
             "heldout_gate_accuracy": r["gate"]["accuracy"],
             "mode_in_train": r["mode_in_train"]["any"],
             "mode_in_gate": r["mode_in_gate"]["any"],
             "eval_accuracy": r["eval"]["accuracy"],
             "eval_n_fail_mode_contact": r["eval"]["n_fail_mode_contact"],
             "eval_n_fail_off_mode": r["eval"]["n_fail_off_mode"]}
            for r in reverse],
        "reverse_by_campaign": dict(Counter(r["file"] for r in reverse)),
        "by_campaign": {},
        "by_failure_class": dict(Counter(r["gate_failure_class"]
                                         for r in regressions)),
        "by_campaign_and_class": {},
        "by_arm": dict(Counter(r["arm"] for r in regressions)),
        "detail": [{"file": r["file"], "arm": r["arm"], "seed": r["seed"],
                    "env_key": r["env_key"], "model": r["model"],
                    "heldout_gate_accuracy": r["gate"]["accuracy"],
                    "n_fail_mode_contact": r["gate"]["n_fail_mode_contact"],
                    "n_fail_off_mode": r["gate"]["n_fail_off_mode"],
                    "max_err_off_mode_fail": r["gate"]["max_err_off_mode_fail"],
                    "failure_class": r["gate_failure_class"],
                    "mode_in_train": r["mode_in_train"]["any"],
                    "mode_in_gate": r["mode_in_gate"]["any"],
                    "probe_blind_all_modes": r["probe_blind_all_modes"]}
                   for r in regressions],
    }
    for f, recs in sorted(by_campaign.items()):
        reg = [r for r in recs
               if r["in_sample_gate_passed"] and not r["accepted_heldout"]]
        c["by_campaign"][f] = {
            "n_artifacts": len(recs),
            "n_in_sample_passed": sum(1 for r in recs
                                      if r["in_sample_gate_passed"]),
            "n_heldout_accepted": sum(1 for r in recs if r["accepted_heldout"]),
            "n_regressions": len(reg),
            "n_reverse_regressions": sum(
                1 for r in recs if not r["in_sample_gate_passed"]
                and r["accepted_heldout"])}
        c["by_campaign_and_class"][f] = dict(
            Counter(r["gate_failure_class"] for r in reg))

    # --- (d) out-of-sample exactness on D_eval -------------------------------
    scored = [r for r in artifacts if not r["eval"]["infra_error"]]
    exceptions = [r for r in scored if r["eval"]["n_fail_off_mode"] > 0]
    d = {
        "definition": ("for each artifact, is EVERY failing transition of "
                       "D_eval a mode contact?  'exceptions' are the artifacts "
                       "with at least one OFF-mode failure, i.e. not exact "
                       "outside the mode region."),
        "n_scored": len(scored),
        "n_infra_error": sum(1 for r in artifacts if r["eval"]["infra_error"]),
        "n_exact_outside_mode": sum(1 for r in scored
                                    if r["eval"]["n_fail_off_mode"] == 0),
        "n_exceptions": len(exceptions),
        "exceptions": [{"file": r["file"], "arm": r["arm"], "seed": r["seed"],
                        "env_key": r["env_key"], "model": r["model"],
                        "eval_accuracy": r["eval"]["accuracy"],
                        "n_fail_off_mode": r["eval"]["n_fail_off_mode"],
                        "n_fail_mode_contact": r["eval"]["n_fail_mode_contact"],
                        "max_err_off_mode_fail": r["eval"]["max_err_off_mode_fail"],
                        "in_sample_gate_passed": r["in_sample_gate_passed"],
                        "failure_class": r["eval_failure_class"]}
                       for r in exceptions],
        "exceptions_by_campaign": dict(Counter(r["file"] for r in exceptions)),
        "restricted_to_in_sample_accepted": {
            "n_scored": sum(1 for r in scored if r["in_sample_gate_passed"]),
            "n_exceptions": sum(1 for r in exceptions
                                if r["in_sample_gate_passed"])},
        "restricted_to_heldout_accepted": {
            "n_scored": sum(1 for r in scored if r["accepted_heldout"]),
            "n_exceptions": sum(1 for r in exceptions if r["accepted_heldout"])},
    }

    # --- measured rarity on the held-out blocks (free internal check) --------
    # Rollout-level mode-firing rate over DISTINCT blocks only: two artifacts
    # sharing (env_key, seed) share their samples bit-for-bit, so pooling per
    # artifact would multiply-count the same rollouts.
    rarity = {}
    for f, recs in sorted(by_campaign.items()):
        seen, hit, tot = set(), 0, 0
        for r in recs:
            if r["block_key"] in seen:
                continue
            seen.add(r["block_key"])
            for which in ("mode_in_gate", "mode_in_eval"):
                hit += r[which]["n_rollouts_with_contact"]
                tot += r[which]["n_rollouts"]
        rarity[f] = {"n_blocks": len(seen), "rollouts": tot,
                     "rollouts_with_mode": hit,
                     "measured_r": (hit / tot) if tot else None,
                     "wilson95": wilson(hit, tot),
                     "env_key": recs[0]["env_key"],
                     "note": ("rollout-level mode-firing rate measured on the "
                              "held-out D_gate+D_eval blocks of this campaign, "
                              "deduplicated to distinct (env, seed) blocks; an "
                              "internal consistency check on the committed r, "
                              "not a replacement for it")}

    # --- the paper table ------------------------------------------------------
    paper_rows = []
    for f, recs in sorted(by_campaign.items()):
        inc = [r for r in recs if r["arm"] == "incomplete"]
        full = [r for r in recs if r["arm"] == "full"]
        cont = a["by_campaign"][f]
        paper_rows.append({
            "file": f, "campaign": recs[0]["campaign"],
            "env_key": recs[0]["env_key"], "model": recs[0]["model"],
            "n_artifacts": len(recs),
            "n_full": len(full), "n_incomplete": len(inc),
            "n_blocks": _dedupe_blocks(recs),
            "in_sample_accepted": sum(1 for r in recs
                                      if r["in_sample_gate_passed"]),
            "heldout_accepted": sum(1 for r in recs if r["accepted_heldout"]),
            "heldout_accepted_full": sum(1 for r in full
                                         if r["accepted_heldout"]),
            "heldout_accepted_incomplete": sum(1 for r in inc
                                               if r["accepted_heldout"]),
            "regressions": c["by_campaign"][f]["n_regressions"],
            "train_mode_absent": sum(1 for r in inc
                                     if not r["mode_in_train"]["any"]),
            "gate_mode_absent": sum(1 for r in inc
                                    if not r["mode_in_gate"]["any"]),
            "contingency_coincides": cont["coincides_exactly"],
            "contingency_n_disagree": cont["n_disagree"],
            "two_factor_measured":
                b[f]["measured_accepted_and_probe_blind"],
            "two_factor_predicted": b[f]["predicted_two_factor"],
            "two_factor_wilson95": b[f]["wilson95"],
            "r_used": b[f]["r_used"], "r_is_measured": b[f]["r_is_measured"],
            "eval_exceptions": sum(1 for r in recs
                                   if not r["eval"]["infra_error"]
                                   and r["eval"]["n_fail_off_mode"] > 0),
        })

    # --- pooled, block-deduplicated headline --------------------------------
    pooled_blocks: dict[str, list[dict]] = defaultdict(list)
    for r in artifacts:
        if r["arm"] == "incomplete":
            pooled_blocks[r["block_key"]].append(r)
    train_check = [r for r in artifacts if "train_reproduction" in r]
    return {
        "totals": {
            "n_artifacts": len(artifacts),
            "n_files": len(by_campaign),
            "n_distinct_blocks": _dedupe_blocks(artifacts),
            "n_in_sample_passed": sum(1 for r in artifacts
                                      if r["in_sample_gate_passed"]),
            "n_heldout_accepted": sum(1 for r in artifacts
                                      if r["accepted_heldout"]),
            "n_regressions": len(regressions),
            "n_reverse_regressions": len(reverse),
            "n_eval_exceptions": d["n_exceptions"],
            "n_gate_infra_error": sum(1 for r in artifacts
                                      if r["gate"]["infra_error"]),
            "n_eval_infra_error": d["n_infra_error"],
        },
        "a_contingency": a,
        "b_two_factor": b,
        "c_regressions": c,
        "d_out_of_sample_exactness": d,
        "measured_rarity_on_heldout_blocks": rarity,
        "paper_table": paper_rows,
        "train_reproduction_check": {
            "n_checked": len(train_check),
            "n_accuracy_matches": sum(1 for r in train_check
                                      if r["train_reproduction"]["matches"]),
            "n_mode_flag_matches": sum(
                1 for r in train_check
                if r["train_reproduction"]["mode_flag_matches"]),
            "mismatches": [
                {"file": r["file"], "arm": r["arm"], "seed": r["seed"],
                 **r["train_reproduction"]}
                for r in train_check
                if not (r["train_reproduction"]["matches"]
                        and r["train_reproduction"]["mode_flag_matches"])],
            "note": ("re-scoring an artifact on its REPRODUCED training sample "
                     "must return the accuracy the original run stored; this "
                     "is the check that env_from_params + the seed convention "
                     "reconstruct the original sample exactly"),
        },
    }


# --- printing -----------------------------------------------------------------
def print_report(doc: dict, out_path: pathlib.Path) -> None:
    p = print
    agg = doc["aggregates"]
    t = agg["totals"]
    p("")
    p("=" * 100)
    p("HELD-OUT GATE AUDIT  (three-way split; no LLM calls)")
    p("=" * 100)
    sp = doc["split"]
    p(f"D_train = collect_transitions(env, n_rollouts, seed)                     "
      f"[{sp['n_train']} rollouts]")
    p(f"D_gate  = collect_transitions(env, {sp['n_gate']}, seed + {GATE_SEED_OFFSET})"
      f"                 [independent gate]")
    p(f"D_eval  = collect_transitions(env, {sp['n_eval']}, seed + {EVAL_SEED_OFFSET})"
      f"                [independent eval]")
    p(f"blocks disjoint (brute-force set intersection over all "
      f"{sp['n_train_seeds']} campaign train seeds): {sp['all_disjoint']}"
      f"  train/gate={len(sp['train_gate_overlap'])} "
      f"train/eval={len(sp['train_eval_overlap'])} "
      f"gate/eval={len(sp['gate_eval_overlap'])} overlaps")
    p("")
    p(f"artifacts {t['n_artifacts']} in {t['n_files']} files, "
      f"{t['n_distinct_blocks']} distinct (env, seed) sample blocks")
    p(f"in-sample gate passed        : {t['n_in_sample_passed']}")
    p(f"INDEPENDENT gate accepted    : {t['n_heldout_accepted']}")
    p(f"regressions (passed -> fail) : {t['n_regressions']}")
    p(f"reverse (refused -> accept)  : {t['n_reverse_regressions']}")
    p(f"D_eval off-mode exceptions   : {t['n_eval_exceptions']}")
    p(f"sandbox infra errors         : gate {t['n_gate_infra_error']} "
      f"eval {t['n_eval_infra_error']}")

    tr = agg["train_reproduction_check"]
    p("")
    p(f"[train reproduction] {tr['n_accuracy_matches']}/{tr['n_checked']} "
      f"re-scored training samples reproduce the stored gate accuracy exactly; "
      f"{tr['n_mode_flag_matches']}/{tr['n_checked']} reproduce the stored "
      f"sample_contains_wall flag")
    for m in tr["mismatches"][:10]:
        p(f"   MISMATCH {m['file']} {m['arm']} seed={m['seed']}: "
          f"recomputed {m['recomputed_train_accuracy']} vs stored "
          f"{m['stored_gate_accuracy']}")

    p("")
    p("-" * 100)
    p("PAPER TABLE — per campaign")
    p("-" * 100)
    hdr = (f"{'campaign':46s} {'n':>4s} {'blk':>4s} {'inS':>4s} {'hOut':>5s} "
           f"{'reg':>4s} {'trM':>4s} {'gtM':>4s} {'2x2':>4s} "
           f"{'meas':>7s} {'pred':>7s} {'evx':>4s}")
    p(hdr)
    for row in agg["paper_table"]:
        meas = row["two_factor_measured"]
        pred = row["two_factor_predicted"]
        p(f"{row['campaign'][:46]:46s} {row['n_artifacts']:4d} "
          f"{row['n_blocks']:4d} {row['in_sample_accepted']:4d} "
          f"{row['heldout_accepted']:5d} {row['regressions']:4d} "
          f"{row['train_mode_absent']:4d} {row['gate_mode_absent']:4d} "
          f"{'Y' if row['contingency_coincides'] else 'N':>4s} "
          f"{(f'{meas:.3f}' if meas is not None else 'n/a'):>7s} "
          f"{(f'{pred:.3f}' if pred is not None else 'n/a'):>7s} "
          f"{row['eval_exceptions']:4d}")
    p("  n=artifacts blk=distinct (env,seed) blocks  inS=in-sample gate passed  "
      "hOut=independent gate accepted")
    p("  reg=in-sample pass but held-out fail  trM/gtM=incomplete-arm artifacts "
      "whose D_train/D_gate missed the mode")
    p("  2x2=held-out acceptance coincides exactly with 'D_gate missed the "
      "mode' on the train-miss subset (incomplete arm)")
    p("  meas/pred = P(accepted_heldout AND probe-blind) measured vs "
      "(1-r)^(N_train+N_gate)   evx = D_eval off-mode exceptions")

    a = agg["a_contingency"]
    p("")
    p("-" * 100)
    p("(a) 2x2 CONTINGENCY — artifacts whose TRAINING sample missed the mode")
    p("-" * 100)
    for label in ("all_arms", "incomplete_arm", "full_arm",
                  "incomplete_arm_probe_blind_only"):
        cc = a[label]
        tb = cc["table"]
        p(f"{label:34s} n={cc['n']:4d}  "
          f"gate-miss/accepted={tb['gate_mode_absent']['accepted']:4d}  "
          f"gate-miss/rejected={tb['gate_mode_absent']['rejected']:4d}  "
          f"gate-hit/accepted={tb['gate_mode_present']['accepted']:4d}  "
          f"gate-hit/rejected={tb['gate_mode_present']['rejected']:4d}  "
          f"coincides={cc['coincides_exactly']} disagree={cc['n_disagree']}")
    for od in a["incomplete_arm"]["off_diagonal"][:20]:
        p(f"   off-diagonal: {od['file']} {od['arm']} seed={od['seed']} "
          f"{od['row']}/{od['col']} acc={od['gate_accuracy_heldout']:.6f} "
          f"failmode={od['gate_n_fail_mode_contact']} "
          f"failoff={od['gate_n_fail_off_mode']}")

    p("")
    p("-" * 100)
    p("(b) TWO-FACTOR LAW — P(accepted_heldout AND probe-blind), incomplete arm")
    p("-" * 100)
    for f, bb in agg["b_two_factor"].items():
        meas = bb["measured_accepted_and_probe_blind"]
        p(f"{f}")
        p(f"    n={bb['n_incomplete_artifacts']} blocks={bb['n_independent_blocks']} "
          f"k={bb['k_accepted_and_probe_blind']} "
          f"measured={'n/a' if meas is None else f'{meas:.4f}'} "
          f"wilson95={bb['wilson95']}")
        p(f"    predicted (1-r)^({bb['N_train']}+{bb['N_gate']}) = "
          f"{bb['predicted_two_factor']}   "
          f"[r={bb['r_used']} kind={bb['r_kind']} measured_r={bb['r_is_measured']}]")
        p(f"    r source: {bb['r_source']} :: {bb['r_source_path']}")
        p(f"    single-factor (train only) (1-r)^{bb['N_train']} = "
          f"{bb['predicted_single_factor_train_only']}   "
          f"train-miss AND gate-miss AND accepted = "
          f"{bb['k_train_miss_and_gate_miss_and_accepted']}")

    c = agg["c_regressions"]
    p("")
    p("-" * 100)
    p(f"(c) REGRESSIONS: in-sample gate passed ({c['n_in_sample_passed']}) but "
      f"independent gate FAILED ({c['n_regressions']})")
    p("-" * 100)
    p(f"by failure class: {c['by_failure_class']}    by arm: {c['by_arm']}")
    for f, cnt in c["by_campaign_and_class"].items():
        if cnt:
            p(f"   {f}: {cnt}")
    for det in c["detail"][:40]:
        p(f"   {det['file']} {det['arm']} seed={det['seed']} "
          f"acc={det['heldout_gate_accuracy']:.6f} class={det['failure_class']} "
          f"fail(mode={det['n_fail_mode_contact']}, off={det['n_fail_off_mode']}) "
          f"trainmode={det['mode_in_train']} gatemode={det['mode_in_gate']} "
          f"probeblind={det['probe_blind_all_modes']}")
    if len(c["detail"]) > 40:
        p(f"   ... {len(c['detail']) - 40} more in {out_path}")
    p("")
    p(f"(c') REVERSE: in-sample gate REFUSED but independent gate ACCEPTS: "
      f"{c['n_reverse_regressions']}")
    for det in c["reverse_detail"][:20]:
        p(f"   {det['file']} {det['arm']} seed={det['seed']} "
          f"inS={det['in_sample_gate_accuracy']:.6f} -> "
          f"hGate={det['heldout_gate_accuracy']:.6f} "
          f"trainmode={det['mode_in_train']} gatemode={det['mode_in_gate']} "
          f"eval_acc={det['eval_accuracy']:.6f} "
          f"eval_fail(mode={det['eval_n_fail_mode_contact']}, "
          f"off={det['eval_n_fail_off_mode']})")
    if len(c["reverse_detail"]) > 20:
        p(f"   ... {len(c['reverse_detail']) - 20} more in {out_path}")

    d = agg["d_out_of_sample_exactness"]
    p("")
    p("-" * 100)
    p("(d) OUT-OF-SAMPLE EXACTNESS ON D_eval: is every failing transition a "
      "mode contact?")
    p("-" * 100)
    p(f"exact outside the mode region: {d['n_exact_outside_mode']}/"
      f"{d['n_scored']}   exceptions: {d['n_exceptions']}")
    p(f"   restricted to in-sample-accepted artifacts: "
      f"{d['restricted_to_in_sample_accepted']['n_exceptions']}/"
      f"{d['restricted_to_in_sample_accepted']['n_scored']} exceptions")
    p(f"   restricted to held-out-accepted artifacts : "
      f"{d['restricted_to_heldout_accepted']['n_exceptions']}/"
      f"{d['restricted_to_heldout_accepted']['n_scored']} exceptions")
    for e in d["exceptions"][:40]:
        p(f"   EXCEPTION {e['file']} {e['arm']} seed={e['seed']} "
          f"eval_acc={e['eval_accuracy']:.6f} off-mode fails="
          f"{e['n_fail_off_mode']} mode fails={e['n_fail_mode_contact']} "
          f"max_off_err={e['max_err_off_mode_fail']} "
          f"in_sample_passed={e['in_sample_gate_passed']}")
    if len(d["exceptions"]) > 40:
        p(f"   ... {len(d['exceptions']) - 40} more in {out_path}")

    p("")
    p("-" * 100)
    p("measured rollout-level rarity on the held-out blocks (internal check)")
    p("-" * 100)
    for f, rr in agg["measured_rarity_on_heldout_blocks"].items():
        mr = rr["measured_r"]
        p(f"   {f[:60]:60s} r_hat={'n/a' if mr is None else f'{mr:.5f}'} "
          f"({rr['rollouts_with_mode']}/{rr['rollouts']} rollouts, "
          f"{rr['n_blocks']} blocks)  committed r="
          f"{R_SOURCES.get(rr['env_key'], {}).get('r')}")
    p("")
    p(f"wrote {out_path}")


# --- main ---------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=OUT_DEFAULT)
    ap.add_argument("--results-dir", type=pathlib.Path,
                    default=_REPO / "results")
    ap.add_argument("--glob", default=SYNTH_GLOB)
    ap.add_argument("--n-gate", type=int, default=N_GATE,
                    help="held-out gate rollouts; NEVER below 40 (it is the "
                    "danger-law N the prediction is stated at)")
    ap.add_argument("--n-eval", type=int, default=N_EVAL_DEFAULT)
    ap.add_argument("--limit", type=int, default=None,
                    help="score at most N artifacts (smoke runs)")
    ap.add_argument("--validate-train-per-file", type=int, default=3,
                    help="additionally re-score the first K artifacts of each "
                    "file on their REPRODUCED training sample and check the "
                    "accuracy against the stored one (0 disables)")
    ap.add_argument("--timeout-gate", type=float, default=300.0)
    ap.add_argument("--timeout-eval", type=float, default=600.0)
    ap.add_argument("--instruments", nargs="+", default=None,
                    metavar="INSTRUMENT",
                    help="audit scope; default is paper 2's "
                    f"{AUDITED_INSTRUMENTS}, whose committed output "
                    "(results/heldout_gate_audit.json) reproduces the "
                    "PUBLISHED numbers and must not widen. A ring2d (paper 3) "
                    "audit passes '--instruments ring2d' together with its own "
                    "--out; the two scopes never share an output file")
    args = ap.parse_args(argv)
    instruments = tuple(args.instruments or AUDITED_INSTRUMENTS)
    if instruments != AUDITED_INSTRUMENTS and args.out == OUT_DEFAULT:
        ap.error(f"a non-default scope {instruments} must name its own --out: "
                 f"{OUT_DEFAULT.name} is paper 2's committed audit and its "
                 f"scope is fixed at {AUDITED_INSTRUMENTS}")

    if args.n_gate < N_GATE:
        ap.error(f"--n-gate must be >= {N_GATE}")

    r_sources = verify_r_sources()

    files = sorted(args.results_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"no files match {args.glob} in {args.results_dir}")
    # Out-of-scope instruments are skipped by name, loudly. Without this a
    # re-run would reach _two_factor on a ring2d campaign and die on a missing
    # R_SOURCES entry -- a real gap in paper 3's calibration, but reported as
    # if this audit were broken.
    skipped = []
    in_scope = []
    for path in files:
        params = json.loads(path.read_text()).get("params", {})
        if params.get("instrument", "cart") in instruments:
            in_scope.append(path)
        else:
            skipped.append(path.name)
    if skipped:
        print(f"skipping {len(skipped)} campaign(s) outside "
              f"instruments={instruments}: "
              f"{', '.join(skipped)}", flush=True)
    files = in_scope
    if not files:
        raise SystemExit(f"every file matching {args.glob} is out of scope "
                         f"(instruments={instruments})")

    # The disjointness proof must cover the LONGEST training block any in-scope
    # cell used, not the default 40: ring2d's dose campaigns trained on up to
    # 320 rollouts, and a proof over 40-long blocks says nothing about the
    # extra 280 seeds. For every paper-2 scope run the maximum is 40, so the
    # stored split dict is unchanged there.
    n_train_max = max((cell.get("n_rollouts", TRAIN_N_ROLLOUTS)
                       for path in files
                       for cell in json.loads(path.read_text()).get("cells", []))
                      , default=TRAIN_N_ROLLOUTS)
    split = disjointness_report(n_train=n_train_max, n_gate=args.n_gate,
                                n_eval=args.n_eval)
    if not split["all_disjoint"]:
        raise SystemExit(f"held-out blocks are NOT disjoint from the training "
                         f"blocks: {split}")

    params_now = {"n_gate": args.n_gate, "n_eval": args.n_eval,
                  "gate_seed_offset": GATE_SEED_OFFSET,
                  "eval_seed_offset": EVAL_SEED_OFFSET,
                  "glob": args.glob,
                  "instruments": list(instruments)}
    if args.out.exists():
        doc = json.loads(args.out.read_text())
        stored = doc.get("params", {})
        clash = {k: (stored.get(k), v) for k, v in params_now.items()
                 if k in stored and stored[k] != v}
        if clash:
            raise SystemExit(
                f"refusing to resume {args.out}: produced under a different "
                f"configuration {clash}; rerun with matching flags or move the "
                f"file aside")
        doc["params"] = params_now
    else:
        doc = {"script": "heldout_gate_audit.py", "params": params_now,
               "artifacts": []}
    doc["split"] = split
    doc["r_sources"] = r_sources
    doc.setdefault("artifacts", [])

    done = {(r["file"], r["arm"], r["seed"]) for r in doc["artifacts"]}
    todo = []
    for path in files:
        d = json.loads(path.read_text())
        for i, cell in enumerate(d.get("cells", [])):
            todo.append((path, d, cell, i))
    total = len(todo)
    print(f"{total} artifacts across {len(files)} files "
          f"({len(done)} already done in {args.out.name})", flush=True)

    t0 = time.time()
    n_new = 0
    for path, d, cell, idx in todo:
        key = (path.name, cell["arm"], cell["seed"])
        if key in done:
            continue
        if args.limit is not None and n_new >= args.limit:
            break
        rec = audit_artifact(
            path, d, cell, n_gate=args.n_gate, n_eval=args.n_eval,
            timeout_gate=args.timeout_gate, timeout_eval=args.timeout_eval,
            validate_train=(idx < args.validate_train_per_file))
        doc["artifacts"].append(rec)
        done.add(key)
        n_new += 1
        doc["aggregates"] = aggregate(doc["artifacts"], args.n_gate,
                                     args.n_eval)
        doc["elapsed_s"] = round(time.time() - t0, 1)
        doc["complete"] = len(doc["artifacts"]) == total
        _atomic_write_json(args.out, doc)      # per-artifact checkpoint
        print(f"[{len(doc['artifacts'])}/{total}] {path.name} {cell['arm']} "
              f"seed={cell['seed']} inS={cell['gate_accuracy']:.3f} "
              f"hGate={rec['gate']['accuracy']:.6f} "
              f"hEval={rec['eval']['accuracy']:.6f} "
              f"trainmode={rec['mode_in_train']['any']} "
              f"gatemode={rec['mode_in_gate']['any']} "
              f"accepted={rec['accepted_heldout']} "
              f"evalfail(mode={rec['eval']['n_fail_mode_contact']},"
              f"off={rec['eval']['n_fail_off_mode']})", flush=True)

    doc["aggregates"] = aggregate(doc["artifacts"], args.n_gate, args.n_eval)
    doc["elapsed_s"] = round(time.time() - t0, 1)
    doc["complete"] = len(doc["artifacts"]) == total
    _atomic_write_json(args.out, doc)
    print_report(doc, args.out)
    if not doc["complete"]:
        print(f"\nINCOMPLETE: {len(doc['artifacts'])}/{total} artifacts scored "
              f"(--limit or an interrupted run); rerun to finish", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
