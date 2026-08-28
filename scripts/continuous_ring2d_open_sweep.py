"""Registered open-ring arm sweep driver (spec
docs/superpowers/specs/2026-07-21-open-ring-arm-design.md §3, §7).

Shells out to scripts/continuous_danger_synthesis.py — one subprocess per
cell — so provider handling, per-seed checkpoint/resume and file naming
stay the harness's. Driver-level resume: a cell whose result file already
holds all requested seed indices is skipped entirely.

  python scripts/continuous_ring2d_open_sweep.py --phase 0 [--dry-run]
  python scripts/continuous_ring2d_open_sweep.py --cpu-curve

--cpu-curve computes the dense pc_blind(gap) danger curve (no LLM):
paired MPC episodes of blind_of(truth) vs truth per gap, resumable per gap,
to results/continuous_ring2d_pcblind_curve.json.
"""
import argparse
import json
import math
import os
import subprocess
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

A_FACING_GAPS = [0.05, 0.1, 0.2, 0.4, 0.6, 1.2]
A_HIDDEN_GAPS = [0.6, 1.2]
D_FACING = [(0.2, 20), (0.6, 20), (1.2, 20), (1.8, 30), (2.4, 20)]
CPU_GAPS = [0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.9, 1.2]
CPU_EPISODES = 16
CURVE_PATH = "results/continuous_ring2d_pcblind_curve.json"


def target_path(size, gap, channel, start, variant):
    knob = (f"gap{gap:g}"
            + ("" if channel == "facing" else "-hid")
            + ("" if start == "outside" else "-in"))
    suffix = "" if variant == "default" else f"_pv-{variant}"
    return f"results/continuous_synthesis_ring2d_{size}_{knob}{suffix}.json"


def _cell(size, gap, channel, start, variant, n_seeds):
    return {"size": size, "gap": gap, "channel": channel, "start": start,
            "variant": variant, "n_seeds": n_seeds,
            "path": target_path(size, gap, channel, start, variant)}


def plan_for_phase(phase):
    if phase == 0:
        return [_cell("mini", 1.8, "facing", "inside", "tda", 3),
                _cell("mini", 0.2, "facing", "outside", "default", 3)]
    if phase == 1:
        plan = [_cell("mini", g, "facing", "outside", "default", 20)
                for g in A_FACING_GAPS]
        plan += [_cell("mini", g, "hidden", "outside", "default", 10)
                 for g in A_HIDDEN_GAPS]
        plan += [_cell("mini", g, "facing", "inside", "tda", n)
                 for g, n in D_FACING]
        return plan
    if phase == 2:
        return [_cell("large", 0.1, "facing", "outside", "default", 20),
                _cell("large", 0.6, "facing", "outside", "default", 20),
                _cell("large", 0.6, "facing", "inside", "tda", 20),
                _cell("large", 2.4, "facing", "inside", "tda", 20)]
    raise ValueError(f"unknown phase {phase}")


def seeds_missing(path, n_seeds):
    """True if the result file lacks any of the first n_seeds incomplete-arm
    seed indices (harness convention: seed = 10_000 * (index + 1))."""
    if not os.path.exists(path):
        return True
    cells = json.loads(open(path).read()).get("cells", [])
    done = {c["seed"] // 10_000 - 1 for c in cells
            if c.get("arm") == "incomplete"}
    return not set(range(n_seeds)) <= done


def run_cell(cell, dry_run):
    action = "SKIP" if not seeds_missing(cell["path"], cell["n_seeds"]) \
        else "RUN"
    print(f"[{action}] {cell['path']}  n_seeds={cell['n_seeds']}", flush=True)
    if action == "SKIP" or dry_run:
        return
    cmd = [sys.executable, "-u", "scripts/continuous_danger_synthesis.py",
           cell["size"], str(cell["n_seeds"]),
           "--instrument", "ring2d", "--arm", "incomplete",
           "--gap", str(cell["gap"]), "--channel", cell["channel"],
           "--start", cell["start"], "--prompt-variant", cell["variant"],
           "--keep-history"]
    res = subprocess.run(cmd, cwd=_REPO)
    if res.returncode != 0:
        raise SystemExit(
            f"cell failed ({cell['path']}); the run is resumable — fix and "
            f"re-run the same driver command")


def cpu_curve():
    from cwm.continuous import harness
    from cwm.continuous.envs import RingField2D, blind_of
    rows = []
    if os.path.exists(CURVE_PATH):
        rows = json.loads(open(CURVE_PATH).read())
    done = {r["gap"] for r in rows}
    for gap in CPU_GAPS:
        if gap in done:
            print(f"[skip] gap={gap}", flush=True)
            continue
        truth = RingField2D(gap=gap, gap_center=math.pi,
                            x0_center=(0.0, 0.0))
        pc = harness.play_cost(truth, blind_of(truth), CPU_EPISODES, seed=0)
        rows.append({"gap": gap, "episodes": CPU_EPISODES, **pc})
        tmp = CURVE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rows, f, indent=1)
        os.replace(tmp, CURVE_PATH)          # per-gap checkpoint
        print(f"gap={gap}: pc={pc['play_cost']:.3f} "
              f"contact={pc['blind_contact_rate']:.2f}", flush=True)
    print(f"wrote {CURVE_PATH}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", type=int, choices=[0, 1, 2])
    ap.add_argument("--cpu-curve", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cpu_curve:
        cpu_curve()
        return
    if args.phase is None:
        ap.error("--phase or --cpu-curve required")
    for cell in plan_for_phase(args.phase):
        run_cell(cell, args.dry_run)


if __name__ == "__main__":
    main()
