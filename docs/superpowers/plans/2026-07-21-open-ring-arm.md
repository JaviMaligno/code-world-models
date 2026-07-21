# Open-Ring Registered Arm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the registered open-ring arm (spec
`docs/superpowers/specs/2026-07-21-open-ring-arm-design.md`): the danger curve
pc(gap) facing-vs-hidden, the topology-tracking attribution across the
detector flip, and the parameter-identifiability boundary.

**Architecture:** Three small code deliverables reuse the existing pipeline
untouched: (1) an opt-in refine-history recorder inside the existing
`refine_continuous`; (2) a sweep driver that SHELLS OUT to
`scripts/continuous_danger_synthesis.py` (whose per-seed checkpoint/resume,
provider handling and file naming stay the single source of truth) plus a
CPU-only dense pc_blind(gap) curve; (3) an aggregator that imports the
per-cell instruments from the committed audit script. Experiment execution
(Tasks 4–7) is controller-run, not subagent-run.

**Tech Stack:** Python 3.12, pytest, existing `cwm.continuous` package,
Azure OpenAI via the existing harness. No new dependencies.

## Global Constraints (from spec §6 — binding for every task)

- ε=1e-9, N=40 rollouts, ≤5 refines, incomplete arm: UNCHANGED.
- The topological summary (wording + Rips detector: dedup 0.05, cap 90,
  3×median-NN) is pre-registered: DO NOT tune it.
- `src/cwm/continuous/envs.py` (`RingField2D`) is NOT modified.
- The full test suite must stay green and prior outputs byte-identical:
  `keep_history` defaults to False everywhere; with the flag off, every
  emitted JSON schema is unchanged.
- Every run resumable: per-seed (existing harness) and per-cell (driver
  skips complete files). Long-running/money-costing runs MUST checkpoint
  per unit (hard project rule).
- gap-0 and gap-0.6 existing result files are REUSED (topped up, never
  recomputed): the driver must resume into them, not move them aside.
- Worktree `/Users/javieraguilarmartin1/Documents/repos/cwm-wt-paper3`,
  branch `claude/paper-tres-topology-4w813y`. Run tests with
  `PYTHONPATH=src python -m pytest`.

## File Map

| file | role |
|---|---|
| `src/cwm/continuous/contract.py` (modify ~lines 180–320) | `keep_history` in `RefineResult`/`refine_continuous`/`synthesize_and_evaluate` |
| `scripts/continuous_danger_synthesis.py` (modify) | `--keep-history` CLI flag threaded into `run_synthesis` |
| `scripts/continuous_ring2d_open_sweep.py` (create) | sweep driver: grid, phases, shell-out, resume-skip, `--cpu-curve`, `--dry-run` |
| `scripts/ring2d_open_aggregate.py` (create) | summary builder importing audit instruments |
| `scripts/ring2d_artifact_audit.py` (unchanged) | per-cell instruments (already module-level importable) |
| `tests/test_continuous_contract.py` (extend) | history tests |
| `tests/test_ring2d_open_sweep_driver.py` (create) | naming/skip/dry-run tests |
| `tests/test_ring2d_open_aggregate.py` (create) | classifier oracle tests + aggregate smoke |

---

### Task 1: `keep_history` opt-in recording (golden-safe)

**Files:**
- Modify: `src/cwm/continuous/contract.py` (RefineResult ~line 180;
  `refine_continuous` ~line 188; `synthesize_and_evaluate` ~line 273)
- Modify: `scripts/continuous_danger_synthesis.py` (`run_synthesis` ~line 90;
  argparse in `__main__` ~line 245)
- Test: `tests/test_continuous_contract.py` (append)

**Interfaces:**
- Consumes: existing `refine_continuous(provider, model, contract, code,
  transitions, eps, max_iters=5, guidance="", max_failures=20) -> RefineResult`
  and `RefineResult(code, accuracy, iterations, usages)`.
- Produces: `refine_continuous(..., keep_history: bool = False)`;
  `RefineResult` gains field `history: list | None = None` where each entry is
  `(code_str, accuracy_float)`, first entry = the initial synthesis, one more
  per refine iteration; `synthesize_and_evaluate(..., keep_history: bool =
  False)` which, when True, adds `cell["history"] =
  [{"code": c, "gate_accuracy": a} for (c, a) in refined.history]`;
  `run_synthesis(..., keep_history=False)`; CLI flag `--keep-history`.
  Task 2's driver passes `--keep-history`; Task 3 reads `cell["history"]`.

- [ ] **Step 1: Write the failing tests** (append to
  `tests/test_continuous_contract.py`; it already imports `FakeProvider`,
  `refine_continuous`, `synthesize_and_evaluate`, `collect_transitions`,
  `build_contract`, `CartWall`, and defines `ENV`, `FULL_CODE`,
  `INCOMPLETE_CODE`)

```python
def test_refine_history_off_by_default():
    near_env = CartWall(x_wall=0.5)
    tr = collect_transitions(near_env, n_rollouts=20, seed=0)
    contract = build_contract(near_env, include_wall=False)
    provider = FakeProvider([f"```python\n{FULL_CODE}```"])
    res = refine_continuous(provider, "fake", contract,
                            INCOMPLETE_CODE, tr, eps=1e-9)
    assert res.history is None
    cell = synthesize_and_evaluate(
        FakeProvider([f"```python\n{FULL_CODE}```"]), "fake", ENV,
        include_mode=True, n_rollouts=5, seed=0)
    assert "history" not in cell


def test_refine_history_records_initial_and_each_iteration():
    near_env = CartWall(x_wall=0.5)
    tr = collect_transitions(near_env, n_rollouts=20, seed=0)
    assert sample_contains_wall(tr)
    contract = build_contract(near_env, include_wall=False)
    provider = FakeProvider([f"```python\n{FULL_CODE}```"])
    res = refine_continuous(provider, "fake", contract,
                            INCOMPLETE_CODE, tr, eps=1e-9,
                            keep_history=True)
    # initial (incomplete, acc<1) + one refine (full, acc==1)
    assert res.history is not None and len(res.history) == 2
    (code0, acc0), (code1, acc1) = res.history
    assert code0 == INCOMPLETE_CODE and acc0 < 1.0
    assert acc1 == res.accuracy == 1.0 and code1 == res.code


def test_synthesize_history_lands_in_cell():
    cell = synthesize_and_evaluate(
        FakeProvider([f"```python\n{FULL_CODE}```"]), "fake", ENV,
        include_mode=True, n_rollouts=5, seed=0, keep_history=True)
    assert cell["gate_passed"]
    assert [h["gate_accuracy"] for h in cell["history"]] == [1.0]
    assert cell["history"][0]["code"] == cell["code"]
```

Note for the implementer: `build_contract`'s mode-omission kwarg in this repo
is whatever `tests/test_continuous_contract.py` already uses at line ~80
(`include_wall=False` shown here — copy the existing call form from the test
file, do not guess).

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/test_continuous_contract.py -k history -v`
Expected: FAIL — `refine_continuous() got an unexpected keyword argument
'keep_history'` (and `res.history` AttributeError for the default test).

- [ ] **Step 3: Implement in `src/cwm/continuous/contract.py`**

RefineResult (exact replacement):

```python
@dataclass
class RefineResult:
    code: str
    accuracy: float
    iterations: int
    usages: list
    history: list | None = None   # [(code, accuracy)] when keep_history
```

`refine_continuous`: add `keep_history: bool = False` to the signature (after
`max_failures`), and modify the body exactly like this:

```python
    usages = []
    acc, failures = contract_accuracy(code, transitions, eps)
    history = [(code, acc)] if keep_history else None
    iterations = 0
    while acc < 1.0 and iterations < max_iters:
        ...  # message build + provider call: UNCHANGED
        code = extract_code(completion.text)
        acc, failures = contract_accuracy(code, transitions, eps)
        if keep_history:
            history.append((code, acc))
        iterations += 1
    return RefineResult(code=code, accuracy=acc, iterations=iterations,
                        usages=usages, history=history)
```

`synthesize_and_evaluate`: add `keep_history: bool = False` to the signature
(after `max_failures`), pass `keep_history=keep_history` in its
`refine_continuous(...)` call, and immediately after the `cell = {...}`
literal add:

```python
    if keep_history:
        cell["history"] = [{"code": c, "gate_accuracy": a}
                           for c, a in refined.history]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/test_continuous_contract.py -v`
Expected: all PASS (new + pre-existing).

- [ ] **Step 5: Thread the CLI flag in `scripts/continuous_danger_synthesis.py`**

Three edits:
1. `run_synthesis` signature: add keyword `keep_history=False` (in the
   keyword-only group after `max_failures`), and pass
   `keep_history=keep_history` in its `synthesize_and_evaluate(...)` call.
2. argparse: `ap.add_argument("--keep-history", action="store_true",
   help="record per-iteration (code, gate) in each cell as 'history' "
   "(additive metadata; off by default so existing outputs are "
   "byte-identical)")`.
3. The `run_synthesis(...)` call in `__main__`: add
   `keep_history=args.keep_history`.

Do NOT add `keep_history` to `_RESULT_KEYS` (the resume-mismatch guard):
history is additive metadata, and phase-1 runs must be able to top up the
existing gap-0.6 files (recorded without history) — a mixed file is expected
and documented in the spec.

- [ ] **Step 6: Run the full suite (golden gate)**

Run: `PYTHONPATH=src python -m pytest -q`
Expected: 369 + 3 = 372 passed (zero failures; cart golden byte-identical).

- [ ] **Step 7: Commit**

```bash
git add src/cwm/continuous/contract.py scripts/continuous_danger_synthesis.py tests/test_continuous_contract.py
git commit -m "feat(paper3): opt-in per-iteration refine history (keep_history, golden-safe)"
```

---

### Task 2: sweep driver `scripts/continuous_ring2d_open_sweep.py`

**Files:**
- Create: `scripts/continuous_ring2d_open_sweep.py`
- Test: `tests/test_ring2d_open_sweep_driver.py`

**Interfaces:**
- Consumes: `scripts/continuous_danger_synthesis.py` CLI (positional `size
  n_seeds`, flags `--instrument ring2d --arm incomplete --gap G --channel C
  --start S --prompt-variant V --keep-history`); its output naming
  `results/continuous_synthesis_ring2d_{size}_gap{gap:g}{-hid?}{-in?}{_pv-V?}.json`;
  its per-seed resume (`seed = 10_000 * (seed_index + 1)`);
  `cwm.continuous.harness.play_cost(truth, blind, n_episodes, seed=0)` and
  `cwm.continuous.envs.{RingField2D, blind_of}` for the CPU curve.
- Produces: CLI `python scripts/continuous_ring2d_open_sweep.py --phase {0,1,2}
  [--dry-run]` and `--cpu-curve`; module-level functions
  `target_path(size, gap, channel, start, variant) -> str`,
  `plan_for_phase(phase) -> list[dict]` (each dict: size, gap, channel, start,
  variant, n_seeds, path), `seeds_missing(path, n_seeds) -> bool`;
  CPU-curve output `results/continuous_ring2d_pcblind_curve.json`
  (list of rows `{gap, play_cost, j_truth, j_blind, j_random,
  blind_contact_rate, episodes}`, resumable per gap). Task 3 reads both.

- [ ] **Step 1: Write the failing tests** (`tests/test_ring2d_open_sweep_driver.py`)

```python
"""Driver tests: naming must match the harness's real files; resume must
skip complete cells; --dry-run must plan without spending money."""
import json
import pathlib
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

import continuous_ring2d_open_sweep as drv


def test_target_path_matches_existing_harness_files():
    # These two files exist in results/ — produced by the harness itself.
    assert drv.target_path("mini", 0.6, "facing", "inside", "tda") == \
        "results/continuous_synthesis_ring2d_mini_gap0.6-in_pv-tda.json"
    assert drv.target_path("mini", 0.6, "facing", "outside", "default") == \
        "results/continuous_synthesis_ring2d_mini_gap0.6.json"
    assert drv.target_path("large", 1.2, "hidden", "outside", "default") == \
        "results/continuous_synthesis_ring2d_large_gap1.2-hid.json"


def test_phase_grids_match_spec():
    p0 = plan_index(drv.plan_for_phase(0))
    assert p0 == {("mini", 1.8, "facing", "inside", "tda", 3),
                  ("mini", 0.2, "facing", "outside", "default", 3)}
    p1 = plan_index(drv.plan_for_phase(1))
    assert ("mini", 0.05, "facing", "outside", "default", 20) in p1
    assert ("mini", 1.8, "facing", "inside", "tda", 30) in p1
    assert ("mini", 0.6, "hidden", "outside", "default", 10) in p1
    assert len([c for c in p1 if c[2] == "hidden"]) == 2
    p2 = plan_index(drv.plan_for_phase(2))
    assert p2 == {("large", 0.1, "facing", "outside", "default", 20),
                  ("large", 0.6, "facing", "outside", "default", 20),
                  ("large", 0.6, "facing", "inside", "tda", 20),
                  ("large", 2.4, "facing", "inside", "tda", 20)}


def plan_index(plan):
    return {(c["size"], c["gap"], c["channel"], c["start"], c["variant"],
             c["n_seeds"]) for c in plan}


def test_seeds_missing_skips_complete_files(tmp_path):
    f = tmp_path / "cells.json"
    cells = [{"arm": "incomplete", "seed": 10_000 * (i + 1)} for i in range(3)]
    f.write_text(json.dumps({"cells": cells}))
    assert drv.seeds_missing(str(f), 3) is False      # complete -> skip
    assert drv.seeds_missing(str(f), 5) is True       # top-up needed
    assert drv.seeds_missing(str(tmp_path / "nope.json"), 1) is True


def test_dry_run_spends_nothing():
    out = subprocess.run(
        [sys.executable, "scripts/continuous_ring2d_open_sweep.py",
         "--phase", "1", "--dry-run"],
        cwd=_REPO, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0
    # every planned cell appears as RUN or SKIP with its target file
    assert "continuous_synthesis_ring2d_mini_gap0.05.json" in out.stdout
    assert "RUN" in out.stdout and "gap1.8-in_pv-tda" in out.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/test_ring2d_open_sweep_driver.py -v`
Expected: FAIL with `ModuleNotFoundError: continuous_ring2d_open_sweep`.

- [ ] **Step 3: Implement the driver**

```python
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
```

Implementer note: verify `blind_of` exists in `cwm.continuous.envs` (it is
imported by `scripts/continuous_ring2d_mechanism.py:31`) and that
`harness.play_cost`'s dict keys match the test's expectations
(`src/cwm/continuous/harness.py:61-75`). If `play_cost` lacks a key used
here, adapt the row construction — do NOT modify harness.py.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/test_ring2d_open_sweep_driver.py -v`
Expected: 4 PASS (dry-run test takes <2 min, no network).

- [ ] **Step 5: Commit**

```bash
git add scripts/continuous_ring2d_open_sweep.py tests/test_ring2d_open_sweep_driver.py
git commit -m "feat(paper3): open-ring sweep driver (phases, resume-skip, CPU pc_blind curve)"
```

---

### Task 3: aggregator `scripts/ring2d_open_aggregate.py`

**Files:**
- Create: `scripts/ring2d_open_aggregate.py`
- Test: `tests/test_ring2d_open_aggregate.py`

**Interfaces:**
- Consumes: `scripts/ring2d_artifact_audit.py` module-level functions
  (`freeze_mask_class(code) -> (cls, stats)`, `env_for(params)`,
  `guidance_beta1(cell)`, `BLIND_CODE`), `cwm.continuous.contract.{
  collect_transitions, contract_accuracy}`, `cwm.law.wilson_ci`,
  sweep result files named per Task 2's `target_path` plus the legacy gap-0
  files, and `results/continuous_ring2d_pcblind_curve.json`.
- Produces: `results/continuous_ring2d_open_sweep_summary.json` with keys
  `pc_blind_curve` (verbatim curve rows), `danger` (per gap×channel:
  `mode_absent`, `n`, `wilson`, `pc_values`), `synthesis` (per gap:
  `gate_pass`, `n`, `mean_terminal_gate`, `mean_blind_ref`, `classes`,
  `classes_by_guidance_beta1`), `artifacts` (per-cell rows incl.
  `history_classes` when history present and `boundary_params` for posed
  structures); function `freeze_boundary_params(code) -> dict` with keys
  `{r_lo, r_hi, ang_cov, max_ang_gap_rad}` (None when no frozen points).

- [ ] **Step 1: Write the failing oracle tests**
  (`tests/test_ring2d_open_aggregate.py`)

The classifier oracle tests use handcrafted artifacts whose true class is
known by construction — this is the brute-force-oracle pattern (project
testing rule).

```python
"""Oracle tests for the freeze-mask classifier and boundary-parameter
extraction, plus an end-to-end aggregate smoke test on a fixture file."""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

from ring2d_artifact_audit import freeze_mask_class
import ring2d_open_aggregate as agg

_INTEGRATOR = '''
import math
def step(state, action):
    x, y, vx, vy = state
    a = min(1.0, max(-1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0*math.cos(phi) - 0.3*vx)*0.1
    vy2 = vy + (3.0*math.sin(phi) - 0.3*vy)*0.1
    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]
def reward(state):
    return 0.0
'''


def _with_freeze(condition):
    """Integrator + freeze when `condition` (an expression in x, y) holds."""
    return _INTEGRATOR.replace(
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
        f"    if {condition}:\n"
        f"        return [x, y, 0.0, 0.0]\n"
        f"    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]")


def test_classifier_oracle_classes():
    cases = {
        "blind": _INTEGRATOR,
        "loop": _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1"),
        "disc": _with_freeze("math.hypot(x-12.0, y) <= 5.1"),
        "complement": _with_freeze("math.hypot(x-12.0, y) >= 3.5"),
        "fill-unbounded": _with_freeze("x >= 7.0"),
        "arc": _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1 "
                            "and abs(math.atan2(y, x-12.0)) <= 1.0"),
    }
    for expected, code in cases.items():
        got, _ = freeze_mask_class(code)
        assert got == expected, f"{expected}: classifier said {got}"


def test_classifier_vdep_velocity_superstition():
    code = _INTEGRATOR.replace(
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]",
        "    if math.hypot(vx2, vy2) > 1.0:\n"
        "        return [x, y, 0.0, 0.0]\n"
        "    return [x+vx2*0.1, y+vy2*0.1, vx2, vy2]")
    got, _ = freeze_mask_class(code)
    assert got == "vdep"


def test_boundary_params_recover_the_annulus():
    p = agg.freeze_boundary_params(
        _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1"))
    assert abs(p["r_lo"] - 3.4) < 0.25 and abs(p["r_hi"] - 5.1) < 0.25
    assert p["ang_cov"] >= 0.97 and p["max_ang_gap_rad"] < 0.4


def test_boundary_params_see_the_arc_gap():
    p = agg.freeze_boundary_params(
        _with_freeze("3.4 <= math.hypot(x-12.0, y) <= 5.1 "
                     "and not (abs(math.atan2(y, x-12.0) - math.pi) < 0.6 "
                     "or abs(math.atan2(y, x-12.0) + math.pi) < 0.6)"))
    # a 1.2-rad channel centered at pi must show up as the largest gap
    assert p["max_ang_gap_rad"] > 0.8


def test_aggregate_smoke(tmp_path, monkeypatch):
    fixture = {
        "params": {"gap": 0.2, "channel": "facing", "start": "inside",
                   "prompt_variant": "tda"},
        "size": "mini", "model": "gpt-test",
        "j_truth": 10.0, "j_random": 1.0,
        "cells": [
            {"arm": "incomplete", "seed": 10000, "n_rollouts": 40,
             "eps": 1e-9, "sample_contains_wall": True,
             "gate_accuracy": 0.5, "gate_passed": False,
             "wall_blindness": None,
             "code": agg.BLIND_CODE,
             "guidance_text": "- persistent-homology check: beta_1 = 1.",
             "history": [{"code": agg.BLIND_CODE, "gate_accuracy": 0.5}]},
        ],
    }
    f = tmp_path / "continuous_synthesis_ring2d_mini_gap0.2-in_pv-tda.json"
    f.write_text(json.dumps(fixture))
    summary = agg.build_summary([str(f)], curve_path=None)
    row = summary["synthesis"]["0.2"]
    assert row["n"] == 1 and row["gate_pass"] == 0
    art = summary["artifacts"][0]
    assert art["class"] == "blind" and art["guidance_beta1"] == 1
    assert art["history_classes"] == ["blind"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/test_ring2d_open_aggregate.py -v`
Expected: FAIL with `ModuleNotFoundError: ring2d_open_aggregate` (the
classifier-oracle tests may already pass — they exercise the committed audit
module; that is fine and expected).

- [ ] **Step 3: Implement the aggregator**

```python
"""Open-ring sweep summary builder (spec §4).

Reads every ring2d synthesis result file (sweep + legacy gap-0), runs the
audit instruments per cell (freeze-mask class, canonical blind-reference
gate, guidance beta_1), extracts freeze-boundary parameters for posed
structures, and emits results/continuous_ring2d_open_sweep_summary.json
with the three headline analyses. Pure CPU, deterministic, safe to re-run.
"""
import glob
import json
import math
import os
import sys
from collections import Counter

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ring2d_artifact_audit import (BLIND_CODE, env_for,          # noqa: E402
                                   freeze_mask_class, guidance_beta1,
                                   integrator_step)
from cwm.continuous.contract import (collect_transitions,        # noqa: E402
                                     contract_accuracy)
from cwm.law import wilson_ci                                    # noqa: E402

CX = 12.0
DEFAULT_GLOBS = [
    "results/continuous_synthesis_ring2d_mini_gap*.json",
    "results/continuous_synthesis_ring2d_large_gap*.json",
]
CURVE_PATH = "results/continuous_ring2d_pcblind_curve.json"
OUT_PATH = "results/continuous_ring2d_open_sweep_summary.json"
POSED = {"loop", "disc", "complement", "fill-unbounded", "arc"}


def freeze_boundary_params(code):
    """Fitted geometry of the frozen set on the v=0 probe grid: radial
    band [r_lo, r_hi] (band+outer zones only, r <= 8), angular coverage,
    and the largest angular gap — comparable to truth r_in=3.5 and channel
    edges pi +- gap/2."""
    ns = {}
    exec(code, ns)  # noqa: S102 — audited synthesis artifacts
    step = ns["step"]
    rs, angs = [], []
    for i in range(81):
        for j in range(81):
            x = 4.0 + 16.0 * i / 80.0
            y = -8.0 + 16.0 * j / 80.0
            got = step([x, y, 0.0, 0.0], 0.3)
            exp = integrator_step(x, y, 0.0, 0.0, 0.3)
            if max(abs(g - e) for g, e in zip(got, exp)) > 1e-6:
                r = math.hypot(x - CX, y)
                if 3.0 <= r <= 8.0:
                    rs.append(r)
                    angs.append(math.atan2(y, x - CX) % (2 * math.pi))
    if not rs:
        return {"r_lo": None, "r_hi": None, "ang_cov": 0.0,
                "max_ang_gap_rad": None}
    angs.sort()
    gaps = [b - a for a, b in zip(angs, angs[1:])]
    gaps.append(angs[0] + 2 * math.pi - angs[-1])
    bins = {int(a / (2 * math.pi) * 72) for a in angs}
    return {"r_lo": min(rs), "r_hi": max(rs), "ang_cov": len(bins) / 72,
            "max_ang_gap_rad": max(gaps)}


def build_summary(paths, curve_path=CURVE_PATH):
    blind_cache = {}
    artifacts, danger, synthesis = [], {}, {}
    for path in sorted(paths):
        raw = json.loads(open(path).read())
        params = raw.get("params", {}) or {}
        gap = params.get("gap", 0.0) or 0.0
        channel = params.get("channel", "facing") or "facing"
        start = params.get("start", "outside") or "outside"
        env = env_for(params)
        for c in raw.get("cells", []):
            if c.get("arm") != "incomplete":
                continue
            key = ((gap, channel, start), c["seed"])
            if key not in blind_cache:
                tr = collect_transitions(env, c.get("n_rollouts", 40),
                                         seed=c["seed"])
                blind_cache[key] = contract_accuracy(
                    BLIND_CODE, tr, c.get("eps", 1e-9))[0]
            cls, st = freeze_mask_class(c["code"])
            row = {
                "path": os.path.basename(path), "gap": gap,
                "channel": channel, "start": start,
                "size": raw.get("size"), "seed": c["seed"],
                "sample_contains_wall": c["sample_contains_wall"],
                "gate_accuracy": c["gate_accuracy"],
                "gate_passed": c["gate_passed"],
                "blind_ref_gate": blind_cache[key],
                "class": cls, "band_cov": st.get("cov"),
                "guidance_beta1": guidance_beta1(c),
                "play_cost": c.get("play_cost"),
            }
            if cls in POSED:
                row["boundary_params"] = freeze_boundary_params(c["code"])
            if "history" in c:
                row["history_classes"] = [
                    freeze_mask_class(h["code"])[0] for h in c["history"]]
            artifacts.append(row)

    for r in artifacts:
        if r["start"] == "outside":
            d = danger.setdefault(f"{r['gap']}|{r['channel']}",
                                  {"gap": r["gap"], "channel": r["channel"],
                                   "n": 0, "mode_absent": 0, "pc_values": []})
            d["n"] += 1
            if not r["sample_contains_wall"]:
                d["mode_absent"] += 1
            if r["play_cost"] is not None:
                d["pc_values"].append(r["play_cost"])
        else:
            s = synthesis.setdefault(str(r["gap"]), {
                "gap": r["gap"], "n": 0, "gate_pass": 0, "gates": [],
                "blind_refs": [], "classes": Counter(),
                "classes_by_guidance_beta1": {}})
            s["n"] += 1
            s["gate_pass"] += r["gate_passed"]
            s["gates"].append(r["gate_accuracy"])
            s["blind_refs"].append(r["blind_ref_gate"])
            s["classes"][r["class"]] += 1
            gb = str(r["guidance_beta1"])
            s["classes_by_guidance_beta1"].setdefault(
                gb, Counter())[r["class"]] += 1
    for d in danger.values():
        d["wilson"] = wilson_ci(d["mode_absent"], d["n"])
    for s in synthesis.values():
        s["mean_terminal_gate"] = sum(s.pop("gates")) / s["n"]
        s["mean_blind_ref"] = sum(s.pop("blind_refs")) / s["n"]
        s["classes"] = dict(s["classes"])
        s["classes_by_guidance_beta1"] = {
            k: dict(v) for k, v in s["classes_by_guidance_beta1"].items()}

    curve = (json.loads(open(curve_path).read())
             if curve_path and os.path.exists(curve_path) else [])
    return {"pc_blind_curve": curve, "danger": danger,
            "synthesis": synthesis, "artifacts": artifacts}


def main():
    paths = [p for g in DEFAULT_GLOBS for p in glob.glob(g)]
    summary = build_summary(paths)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(summary, f, indent=1)
    os.replace(tmp, OUT_PATH)
    print(f"wrote {OUT_PATH}: {len(summary['artifacts'])} artifacts, "
          f"{len(summary['danger'])} danger cells, "
          f"{len(summary['synthesis'])} synthesis gaps")


if __name__ == "__main__":
    main()
```

Implementer note: `integrator_step` must be importable from
`ring2d_artifact_audit` (it is module-level there). `wilson_ci` lives in
`cwm.law` (see `src/cwm/continuous/gate.py:24` for the import form). The
smoke test passes `curve_path=None` — keep that parameter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/test_ring2d_open_aggregate.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Run the aggregator over the EXISTING files (regression sanity)**

Run: `PYTHONPATH=src python scripts/ring2d_open_aggregate.py`
Expected: writes `results/continuous_ring2d_open_sweep_summary.json`;
synthesis gap "0.0" shows gate_pass 1 (large) + 0 (mini) over n=40, and gap
"0.6" shows n=5 gate_pass 0 — matching the audit numbers already in
EXPERIMENTS.md. Do NOT commit this JSON yet (it will be regenerated after
the sweep); commit only code+tests.

- [ ] **Step 6: Full suite + commit**

Run: `PYTHONPATH=src python -m pytest -q` — expected all pass.

```bash
git add scripts/ring2d_open_aggregate.py tests/test_ring2d_open_aggregate.py
git commit -m "feat(paper3): open-ring sweep aggregator (classifier oracle-tested, boundary params, H2 contingency)"
```

---

### Task 4 (CONTROLLER-RUN — do not dispatch to a subagent): Phase 0 validation

Experiment tasks 4–7 spend Azure money and need monitoring; the session
controller runs them directly (project rule from the ShellField sessions).

- [ ] Run `python scripts/continuous_ring2d_open_sweep.py --phase 0 --dry-run`
  — verify plan: 2 cells, both RUN.
- [ ] Run `python scripts/continuous_ring2d_open_sweep.py --phase 0`
  (background, waiter loop). Expected ≈ 5–10 min.
- [ ] Verify gates: both result files exist; cells carry `history`; the
  D-1.8 cells' `guidance_text` parses to β̂₁ ∈ {0, 1}; re-running the same
  command prints `[SKIP]` twice and exits (resume no-op).
- [ ] Run `PYTHONPATH=src python scripts/ring2d_open_aggregate.py`; check the
  new gap rows appear with classes and `history_classes`.
- [ ] Commit result JSONs + summary:
  `git add results/ && git commit -m "paper3: open-ring arm phase 0 (validation cells)"`
  and push.

### Task 5 (CONTROLLER-RUN): Phase 1 mini sweep + CPU curve

- [ ] Launch `python scripts/continuous_ring2d_open_sweep.py --cpu-curve`
  (CPU, ~30 min) and, after it finishes,
  `python scripts/continuous_ring2d_open_sweep.py --phase 1` (Azure,
  ~2–3 h; background with waiter; resumable — on any failure re-run the same
  command).
- [ ] Aggregate, sanity-read the three headline tables (danger knee visible;
  H2 contingency populated at 1.8), commit + push results.

### Task 6 (CONTROLLER-RUN): Phase 2 large + Claude relay spots

- [ ] `python scripts/continuous_ring2d_open_sweep.py --phase 2` (Azure large).
- [ ] Claude spots via the existing relay protocol
  (`scripts/continuous_claude_step.py`), 3 seeds each, context-free
  subagents, replies written to files (this session's established protocol):
  - D at 2.4: `init {10000,20000,30000} results/claude_relay_ring2d
    --instrument ring2d --arm incomplete --gap 2.4 --start inside
    --prompt-variant tda`
  - A at the knee: gap = CPU-curve knee rounded to the nearest A-facing grid
    gap; `init ... --gap {knee} --arm incomplete`
- [ ] Aggregate, commit + push (relay transcripts + classified JSONs included).

### Task 7 (CONTROLLER-RUN): Phase 3 folds

- [ ] EXPERIMENTS.md fold with the pre-registered analyses (§4 of the spec):
  pc(gap) facing vs hidden + knee + corridor geometry; class × guidance β̂₁ ×
  truth β₁ contingency incl. the gap-1.8 within-gap split; gate-pass(gap) +
  boundary-params distance-to-truth; history trajectories; r(gap) alongside.
  State each H1/H2/H3 verdict per spec §8 wording.
- [ ] Update `docs/paper3/RESEARCH-DIRECTION.md` and `docs/paper3/THEORY.md`
  pointers (detector flip as "sensor resolution" instrument; H1 as thesis
  statement).
- [ ] Commit + push.

---

## Self-review notes

- Spec coverage: §3 grid → Task 2 `plan_for_phase` (+ tests pinning it);
  §4 metrics 1–6 → Task 3 outputs + Task 1 history; §5.1→Task 1, §5.2→Task 2,
  §5.3→Task 3, §5.4→Task 6; §6 guardrails → Global Constraints; §7 phases →
  Tasks 4–6; §8 → Task 7.
- The gap-0.6 top-up: phase 1 includes ("mini", 0.6, facing, outside/inside,
  20) whose files exist with 5 seeds → `seeds_missing` returns True → the
  harness subprocess resumes into the same file (its own per-seed skip).
  Mixed history presence in those files is expected (spec §5, Task 1 note).
- `build_contract` kwarg name in Task 1 tests flagged for the implementer to
  copy from the existing test file rather than trust this plan.
