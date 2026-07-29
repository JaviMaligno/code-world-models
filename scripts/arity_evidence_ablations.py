"""The two ablations that test what the 2D repair collapse is actually about.

Review point #4 objected that "repair is geometry-dependent via a template prior" is not
identified: the cart-to-disc contrast moves the state dimension, the action
parametrization, the mode count, the dynamics, the contact distribution, the predicate,
the reward placement and the prompt all at once. Two campaigns separate two of the
candidate causes while holding the rest fixed.

  SLAB (trigger arity).  The same 4D plant, the same scalar-heading action, the same
  lodes, the same one-sided contact evidence, the same prompt and the same budget --
  only the predicate's ARITY changes, from a region in two landing coordinates to a slab
  in one. Rarity is matched the way every other instrument in this paper matches it, by
  moving the mode rather than resizing it (the calibrated impermeable knob k1 = 5.5,
  W = 0.5: r1 = 0.128 against the disc's 0.132, play_cost 1.006 against 1.006). If
  repair returns, the axis is arity. If it does not, arity is excluded and the evidence
  structure is implicated instead.

  LANDING (variable identification).  The disc, unchanged, with the region guidance plus
  ONE sentence naming the state the trigger is evaluated on -- the landing position, not
  the position the step began at. Its comparator is the region arm, matched exactly
  (120 examples, 40 failure lines, 15 iterations, incomplete arm). The base campaign's
  audit found 36 of 40 guided artifacts conditioning on the current position, so this
  isolates that confound from region induction.

WHAT COUNTS AS REPAIR. Two criteria, reported separately, because the shape classifier
alone is not enough here: a correct slab is unbounded in y and is therefore classed
`halfplane`, the same label the disc campaign's dimensional-reduction failure earns.
  (a) gate-and-probe: the artifact reached gate 1.000 AND its per-mode blindness is 0 --
      the paper's definition of repair on the 1D instruments.
  (b) behavioural: the IoU of the artifact's freeze set against the truth's exceeds 0.9
      on the audit's probe grid, which is shape-independent and oracle-tested
      (tests/test_artifact_audit_iou.py).
Neither is charged to the wrong unit: counts are reported per treatment and per model,
and the block-level bound is the one the paper quotes, since these campaigns REUSE the
disc campaign's 20 gate-sample blocks (the rollout stream depends on the seed index
alone) and therefore add treatments, not samples.

Run: PYTHONPATH=src python scripts/arity_evidence_ablations.py
Writes: results/arity_evidence_ablations.json
"""
import importlib.util
import json
import math
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D          # noqa: E402
from cwm.continuous.contract import collect_transitions  # noqa: E402

RES = _REPO / "results"

CAMPAIGNS = {
    "slab": {
        "label": "trigger arity: a one-coordinate predicate in the same 4D plant",
        "files": {"mini": "continuous_synthesis_patch2dslab_mini_k5.5_7.json",
                  "large": "continuous_synthesis_patch2dslab_large_k5.5_7.json"},
        "comparator": "disc",
        "holds_fixed": ["plant", "action parametrization", "lodes", "evidence side",
                        "prompt", "budget", "rarity (matched by moving the mode)"],
        "varies": ["predicate arity (2 landing coordinates -> 1)",
                   "mode count (2 -> 1, unavoidably: a slab screens what is behind it)"],
    },
    "landing": {
        "label": "variable identification: the trigger's argument named, shape not",
        "files": {"mini": "continuous_synthesis_patch2d_mini_k3_7_pv-landing_it15.json",
                  "large": "continuous_synthesis_patch2d_large_k3_7_pv-landing_it15.json"},
        "comparator": "region",
        "holds_fixed": ["instrument", "knob", "examples", "failure lines",
                        "iteration budget", "samples"],
        "varies": ["one sentence naming the landing state as the trigger's argument"],
    },
    "landing_effect": {
        "label": "prop:entryclass tested: the mover stops WHERE IT ENTERED, inside the "
                 "region, so the interior is witnessed and the rule is no harder to write",
        "files": {"mini": "continuous_synthesis_patch2dlanding_mini_k3_7.json",
                  "large": "continuous_synthesis_patch2dlanding_large_k3_7.json"},
        "comparator": "disc",
        "holds_fixed": ["plant", "action", "lodes", "prompt", "budget", "samples",
                        "the firing predicate, hence the rarity exactly"],
        "varies": ["the mode's post-state: the landing instead of the previous position, "
                   "which breaks prop:entryclass's premise"],
    },
    "clamp_effect": {
        "label": "prop:entryclass tested: the mover is projected onto the boundary",
        "files": {"mini": "continuous_synthesis_patch2dclamp_mini_k3_7.json",
                  "large": "continuous_synthesis_patch2dclamp_large_k3_7.json"},
        "comparator": "disc",
        "holds_fixed": ["plant", "action", "lodes", "prompt", "budget", "samples",
                        "the firing predicate, hence the rarity exactly"],
        "varies": ["the mode's post-state: the boundary projection, which breaks the "
                   "premise but makes the post-state a function of the landing"],
    },
    "hint_radius": {
        "label": "POSITIVE CONTROL: the form and the centres given, the RADIUS withheld "
                 "-- one unknown scalar, and the test of whether this pipeline can fit "
                 "constants from the contacts a sample contains at all",
        "files": {"large": "continuous_synthesis_patch2d_large_k3_7_hint-radius.json"},
        "comparator": "disc",
        "holds_fixed": ["instrument", "knob", "prompt", "budget", "samples", "the effect"],
        "varies": ["the incomplete arm's clause states the form and the centres and "
                   "withholds the radius"],
    },
    "hint_centre": {
        "label": "POSITIVE CONTROL: the form given, the CENTRES and the RADIUS withheld "
                 "-- three unknown scalars, still no form to induce",
        "files": {"large": "continuous_synthesis_patch2d_large_k3_7_hint-centre.json"},
        "comparator": "hint_radius",
        "holds_fixed": ["instrument", "knob", "prompt", "budget", "samples", "the effect"],
        "varies": ["the clause states the form only"],
    },
    "disc": {
        "label": "baseline: the disc at k = (3,7), default prompt",
        "files": {"mini": "continuous_synthesis_patch2d_mini_k3_7.json",
                  "large": "continuous_synthesis_patch2d_large_k3_7.json"},
        "comparator": None, "holds_fixed": [], "varies": [],
    },
    "region": {
        "label": "baseline: the disc with region guidance at 3x budget",
        "files": {"mini": "continuous_synthesis_patch2d_mini_k3_7_pv-region_it15.json",
                  "large": "continuous_synthesis_patch2d_large_k3_7_pv-region_it15.json"},
        "comparator": None, "holds_fixed": [], "varies": [],
    },
}

IOU_REPAIR = 0.90

# The IoU compares the artifact's freeze SET against the truth's, so it sees a wrong
# region. It cannot see a right region with the wrong POST-STATE -- an artifact that
# writes the disc but returns the previous position where the truth returns the landing
# deviates from the integrator in exactly the same cells. So every 2D campaign is also
# checked for exact agreement with the truth on a state-action grid, which subsumes both.
GRID_XS = [round(-2 + 0.4 * i, 4) for i in range(41)]
GRID_YS = [round(-4 + 0.8 * i, 4) for i in range(11)]
GRID_VS = ((0.0, 0.0), (3.0, 0.0), (0.0, 2.0), (-2.0, -1.0))
GRID_ACTS = (-1.0, -0.3, 0.0, 0.3, 1.0)


def grid_exact(code, env, tol=1e-9):
    """Exact agreement with the truth over a state-action grid: region AND post-state."""
    from cwm.continuous.contract import SynthesizedModel
    try:
        m = SynthesizedModel(code, env)
    except Exception:
        return {"grid_exact": False, "grid_error": "load failed"}
    bad = tot = fired = 0
    for x in GRID_XS:
        for y in GRID_YS:
            for vx, vy in GRID_VS:
                for a in GRID_ACTS:
                    t, _, contact = env.step((x, y, vx, vy), a)
                    try:
                        g = m.step((x, y, vx, vy), a)[0]
                    except Exception:
                        return {"grid_exact": False, "grid_error": "step raised"}
                    tot += 1
                    fired += bool(contact)
                    if max(abs(gg - tt) for gg, tt in zip(g, t)) > tol:
                        bad += 1
    return {"grid_exact": bad == 0, "grid_n": tot, "grid_mismatch": bad,
            "grid_mode_firings": fired}


def audit_module():
    spec = importlib.util.spec_from_file_location(
        "patch2d_artifact_audit", _REPO / "scripts" / "patch2d_artifact_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    if n == 0:
        return 1.0
    if k == 0:
        return 1.0 - alpha ** (1.0 / n)
    if k >= n:
        return 1.0

    def tail(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if tail(mid) > alpha else (lo, mid)
    return (lo + hi) / 2


def env_of(params: dict) -> PatchField2D:
    shape = params.get("patch_shape") or "disc"
    kw = {}
    if shape == "slab":
        kw["slab_half_width"] = params.get("slab_half_width",
                                           PatchField2D().slab_half_width)
    return PatchField2D(p1=(params.get("k1", 3.0), 0.0),
                        p2=(params.get("k2", 7.0), 0.0), patch_shape=shape,
                        mode_effect=params.get("mode_effect", "freeze"), **kw)


def main() -> None:
    A = audit_module()
    out: dict = {"script": "arity_evidence_ablations.py",
                 "review_point": 4,
                 "repair_criteria": {
                     "gate_and_probe": "gate_accuracy == 1.0 and every per-mode "
                                       "blindness == 0.0 (the paper's 1D definition)",
                     "behavioural": f"IoU of the freeze set against the truth's > "
                                    f"{IOU_REPAIR} on the audit probe grid "
                                    f"(shape-independent; oracle-tested) AND exact "
                                    f"agreement with the truth on a state-action grid, "
                                    f"which also catches a right region with the wrong "
                                    f"post-state"},
                 "campaigns": {}}

    for name, spec in CAMPAIGNS.items():
        present = {sz: RES / f for sz, f in spec["files"].items()
                   if (RES / f).exists()}
        if not present:
            print(f"[skip] {name}: no result files yet")
            continue
        camp = {"label": spec["label"], "comparator": spec["comparator"],
                "holds_fixed": spec["holds_fixed"], "varies": spec["varies"],
                "per_size": {}, "artifacts": []}
        for size, path in present.items():
            raw = json.loads(path.read_text())
            env = env_of(raw.get("params", {}) or {})
            camp["env"] = {"patch_shape": env.patch_shape, "p1": env.p1, "p2": env.p2,
                           "R": env.R,
                           "slab_half_width": getattr(env, "slab_half_width", None)}
            camp["params"] = {k: (raw.get("params") or {}).get(k) for k in
                              ("k1", "k2", "patch_shape", "prompt_variant",
                               "max_iters", "n_rollouts", "eps", "seed_offset")}
            full = [c for c in raw["cells"] if c["arm"] == "full"]
            inc = [c for c in raw["cells"] if c["arm"] == "incomplete"]
            per = {"file": path.name, "model": raw.get("model"),
                   "n_full": len(full), "n_incomplete": len(inc),
                   "full_gate_passed": sum(1 for c in full if c["gate_passed"]),
                   "full_zero_iterations": sum(1 for c in full
                                               if c["refine_iterations"] == 0),
                   "full_mode_encoded": sum(
                       1 for c in full
                       if isinstance(c.get("mode_blindness"), dict)
                       and all(v == 0.0 for v in c["mode_blindness"].values()))}
            n_mode = k_gate = k_beh = 0
            best_iou = -1.0
            for c in inc:
                if not c["sample_contains_wall"]:
                    continue
                n_mode += 1
                a = A.audit_code(c["code"], env)
                mb = c.get("mode_blindness")
                gate_ok = bool(c["gate_passed"]) and isinstance(mb, dict) \
                    and all(v == 0.0 for v in mb.values())
                iou = a.get("iou_truth")
                beh_ok = iou is not None and iou > IOU_REPAIR
                ge = grid_exact(c["code"], env)
                beh_ok = beh_ok and ge["grid_exact"]
                k_gate += gate_ok
                k_beh += beh_ok
                if iou is not None and iou > best_iou:
                    best_iou = iou
                camp["artifacts"].append({
                    "size": size, "seed": c["seed"], "block": c["seed"] // 10_000,
                    "gate_accuracy": c["gate_accuracy"],
                    "refine_iterations": c["refine_iterations"],
                    "modes_in_sample": c.get("sample_contains_mode_per"),
                    "class": a.get("class"), "iou_truth": iou,
                    "missed_frac": a.get("missed_frac"),
                    "excess_cells": a.get("excess_cells"),
                    "cover_p1": a.get("cover_p1"), "cover_p2": a.get("cover_p2"),
                    "integrator_exact": a.get("integrator_exact"),
                    **ge,
                    "repaired_gate_and_probe": gate_ok,
                    "repaired_behavioural": beh_ok})
            per.update({"n_mode_containing": n_mode,
                        "k_repaired_gate_and_probe": k_gate,
                        "k_repaired_behavioural": k_beh,
                        "best_iou": None if best_iou < 0 else round(best_iou, 4)})
            camp["per_size"][size] = per

        rows = camp["artifacts"]
        blocks = sorted({r["block"] for r in rows})
        k_blocks_beh = sum(1 for b in blocks
                           if any(r["repaired_behavioural"] for r in rows
                                  if r["block"] == b))
        camp["pooled"] = {
            "n_draws": len(rows), "n_distinct_blocks": len(blocks),
            "k_repaired_gate_and_probe": sum(r["repaired_gate_and_probe"] for r in rows),
            "k_repaired_behavioural": sum(r["repaired_behavioural"] for r in rows),
            "k_blocks_with_any_behavioural_repair": k_blocks_beh,
            "block_level_cp95_upper": cp_upper(k_blocks_beh, len(blocks)),
            "unit_note": "these campaigns reuse the disc campaign's gate-sample blocks "
                         "(the rollout stream depends on the seed index alone), so they "
                         "add TREATMENTS, not samples; the block-level bound is the one "
                         "to quote",
            "best_iou": max((r["iou_truth"] for r in rows
                             if r["iou_truth"] is not None), default=None),
            "class_counts": {},
        }
        for r in rows:
            cc = camp["pooled"]["class_counts"]
            cc[r["class"]] = cc.get(r["class"], 0) + 1
        out["campaigns"][name] = camp

    (RES / "arity_evidence_ablations.json").write_text(json.dumps(out, indent=2))

    print(f"{'campaign':10} {'draws':>6} {'blocks':>7} {'mode+':>6} "
          f"{'rep(gate)':>10} {'rep(IoU)':>9} {'bestIoU':>8}  classes")
    for name, c in out["campaigns"].items():
        p = c["pooled"]
        nm = sum(v["n_mode_containing"] for v in c["per_size"].values())
        cls = ", ".join(f"{k} {v}" for k, v in sorted(
            p["class_counts"].items(), key=lambda kv: -kv[1]))
        bi = p["best_iou"]
        print(f"{name:10} {p['n_draws']:6} {p['n_distinct_blocks']:7} {nm:6} "
              f"{p['k_repaired_gate_and_probe']:10} {p['k_repaired_behavioural']:9} "
              f"{(f'{bi:.3f}' if bi is not None else 'n/a'):>8}  {cls}")
        for sz, v in sorted(c["per_size"].items()):
            if v["n_full"]:
                print(f"           full arm ({sz}): {v['full_gate_passed']}/{v['n_full']} "
                      f"gate 1.000, {v['full_zero_iterations']} at zero iterations, "
                      f"{v['full_mode_encoded']} with every mode encoded")
    print(f"\nwrote {RES / 'arity_evidence_ablations.json'}")


if __name__ == "__main__":
    main()
