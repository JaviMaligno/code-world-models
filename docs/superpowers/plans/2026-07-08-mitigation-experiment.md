# Mitigation Experiment (Distrust-Region Replanning) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure that a planner with online prediction-vs-observation feedback (distrust-region truncation) breaks the mode-blind exploitation loop on both instruments, and fold the result into paper 2.

**Architecture:** New module `src/cwm/continuous/mitigation.py` holds the mitigated planner (`plan_mitigated`) and episode loop (`run_mitigated_episode`); it reuses `mpc._candidates` so that with zero violations it is bit-identical to `mpc.plan`. A new sweep script `scripts/continuous_mitigation.py` measures truth/blind/mitigated arms on paired seeds across the paper's knob grids. Paper integration adds one subsection + table and rewrites the §9 planner limitation.

**Tech Stack:** Python 3.12, pytest, repo `.venv` at `/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python`, `PYTHONPATH=src`. CPU only — no LLM calls anywhere in this plan.

## Global Constraints

- Work entirely in the worktree `/private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2` on branch `claude/continuous-setting-feasibility-wktp6b`. Never touch the main checkout.
- Run Python as `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python` from the worktree root (the worktree has no `.venv`).
- The model is NEVER modified by the mitigation — planner-side only.
- Zero-cost control is exact: with a correct model, `run_mitigated_episode` must be bit-identical to `harness.run_episode(..., "mpc", ...)` (asserted in tests). `mpc.plan` and `harness.run_episode` must NOT be modified.
- Violation tol = 1e-6 (fixed). Distrust radius ε: cart 0.25, pendulum 0.1 (fixed across knobs; adjust only globally if calibration shows a bad default, and record the change).
- Knob grids (PROVISIONAL per spec; adjust only if a knob is degenerate, and record it): cart `x_wall ∈ {2, 4, 6, 8, 10}`, pendulum `th_stop ∈ {0.8, 1.0, 1.2, 1.4, 1.6, 2.0}`.
- Report measured numbers honestly: the claim is the collapse from play_cost ≈ 1 (below-random pinning) to a bounded first-contact transient — NOT that the residual is zero. The residual may grow with lure distance (far knobs); that is a finding, not a failure.
- `main.tex` recompiles with 0 overfull hbox >2pt and 0 undefined refs/cites, using the committed `main.bbl` (no bibtex).
- Commit after each task; end commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `mitigation.py` + offline test battery

**Files:**
- Create: `src/cwm/continuous/mitigation.py`
- Create: `tests/test_mitigation.py`

**Interfaces:**
- Consumes: `mpc._candidates(a_max, rng, horizon, n_samples, block)` and `mpc.plan` (for the bit-identity test) from `cwm.continuous.mpc`; `CartWall`, `PendulumStop`, `blind_of` from `cwm.continuous.envs`; `harness.run_episode`.
- Produces (Task 2 relies on these exact signatures):
  - `plan_mitigated(model, state, rng, violations: list, eps: float, horizon: int = 40, n_samples: int = 200, block: int = 10) -> float`
  - `run_mitigated_episode(truth, model, seed: int = 0, horizon: int = 40, n_samples: int = 200, block: int = 10, tol: float = 1e-6, eps: float = 0.25) -> MitigatedEpisode`
  - `MitigatedEpisode` dataclass: `ret: float, contact: bool, final_state: tuple, violations: int, first_contact_step: int | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mitigation.py`:

```python
"""Offline tests for the mitigation experiment (distrust-region replanning).

The three properties the spec demands: (1) exact zero-cost control — on a
correct model the mitigated episode is bit-identical to plain MPC; (2)
violation detection fires on the clamp and never on truth; (3) the mitigated
blind planner escapes the pin and recovers most of the truth planner's return
on both instruments."""
import random

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness, mpc
from cwm.continuous.mitigation import plan_mitigated, run_mitigated_episode

CART = CartWall(x_wall=8.0)
PEND = PendulumStop(th_stop=1.4)


def test_plan_reduces_to_mpc_without_violations():
    # Same rng seed, no violations -> identical action to mpc.plan (bitwise).
    for seed in (0, 1, 2):
        a_ref = mpc.plan(CART, (0.5, 1.0), random.Random(seed), n_samples=50)
        a_mit = plan_mitigated(CART, (0.5, 1.0), random.Random(seed), [],
                               eps=0.25, n_samples=50)
        assert a_mit == a_ref


def test_bit_identical_episode_on_truth_model():
    ep_ref = harness.run_episode(CART, CART, "mpc", seed=3, n_samples=40)
    ep_mit = run_mitigated_episode(CART, CART, seed=3, n_samples=40, eps=0.25)
    assert ep_mit.violations == 0
    assert ep_mit.ret == ep_ref.ret
    assert ep_mit.final_state == ep_ref.final_state


def test_violation_recorded_on_blind_model():
    m = run_mitigated_episode(CART, blind_of(CART), seed=3, n_samples=40,
                              eps=0.25)
    assert m.violations >= 1
    assert m.first_contact_step is not None


def test_mitigated_blind_escapes_cart():
    b = harness.run_episode(CART, blind_of(CART), "mpc", seed=3, n_samples=40)
    t = harness.run_episode(CART, CART, "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(CART, blind_of(CART), seed=3, n_samples=40,
                              eps=0.25)
    assert b.final_state[0] == CART.x_wall          # the pin (existing behavior)
    assert m.final_state[0] < CART.x_wall - 0.25    # escaped the distrust band
    assert m.ret > 10 * max(b.ret, 0.1)             # far above the pinned return
    assert m.ret > 0.4 * t.ret                      # recovers most of truth
    # (0.4 margin covers the first-contact + travel-back transient; if this
    # fails, print the three returns and investigate rather than loosen.)


def test_mitigated_blind_escapes_pendulum():
    b = harness.run_episode(PEND, blind_of(PEND), "mpc", seed=3, n_samples=40)
    t = harness.run_episode(PEND, PEND, "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(PEND, blind_of(PEND), seed=3, n_samples=40,
                              eps=0.1)
    assert b.final_state[0] == PEND.th_stop
    assert m.final_state[0] < PEND.th_stop - 0.1
    assert m.violations >= 1
    assert m.ret > 10 * max(b.ret, 0.1)
    assert m.ret > 0.4 * t.ret
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/test_mitigation.py -v`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'cwm.continuous.mitigation'`.

- [ ] **Step 3: Implement `src/cwm/continuous/mitigation.py`**

```python
"""Distrust-region replanning: the mitigation experiment (paper 2).

Planner-side only — the model is never modified. After executing each real
action the planner compares the model's prediction against the observed next
state; a mismatch beyond tol records the PRE-state as a violation point
(pinned-integrator world: a correct model matches to float precision, so any
real mode mismatch is orders of magnitude above tol=1e-6).

During imagination, a candidate rollout is TRUNCATED the first time its
imagined state comes within eps of any violation point, measured on the
position coordinate state[0] only: once the imagined trajectory reaches a
place where the model was observed wrong, nothing downstream of it is
trustworthy. (A reward mask inside the ball would NOT work: the phantom lure
lies beyond the wall, so a rollout could cross the ball and still collect the
phantom plateau on the far side.)

When the current state is already inside a distrust ball (the pinned case)
every candidate truncates immediately and ties near zero; the tie-break picks
the candidate whose FIRST imagined state is farthest from the nearest
violation — flee the distrusted region when nothing is trustworthy. Exact
float ties (e.g. the symmetric one-step displacements from a resting pinned
state) resolve to the earliest candidate, which `mpc._candidates` yields
deterministically ([-a_max]*h first).

With a correct model no violation ever fires and plan_mitigated scores and
ranks candidates exactly as mpc.plan does (same candidate generator, same rng
draws, same strict-argmax) — the zero-cost control holds by construction and
is asserted bitwise in tests/test_mitigation.py.
"""
import random
from dataclasses import dataclass

from . import mpc


def _dist_to_nearest(state, violations) -> float:
    if not violations:
        return 0.0
    return min(abs(state[0] - v[0]) for v in violations)


def plan_mitigated(model, state, rng, violations, eps,
                   horizon: int = 40, n_samples: int = 200,
                   block: int = 10) -> float:
    """mpc.plan with distrust-region truncation. With violations == [] this
    is bit-identical to mpc.plan (same candidates, same scores, same argmax)."""
    best_key, best_a0 = None, 0.0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, total, first = state, 0.0, None
        for a in acts:
            s, r, _ = model.step(s, a)
            if first is None:
                first = s
            if violations and _dist_to_nearest(s, violations) <= eps:
                break  # truncate: keep what is accumulated, drop the rest
            total += r
        key = (total, _dist_to_nearest(first, violations))
        if best_key is None or key > best_key:
            best_key, best_a0 = key, acts[0]
    return best_a0


@dataclass
class MitigatedEpisode:
    ret: float
    contact: bool
    final_state: tuple
    violations: int              # violation points recorded over the episode
    first_contact_step: int | None


def run_mitigated_episode(truth, model, seed: int = 0, horizon: int = 40,
                          n_samples: int = 200, block: int = 10,
                          tol: float = 1e-6, eps: float = 0.25) -> MitigatedEpisode:
    """Play one episode in `truth`, planning on `model` with distrust-region
    replanning. Mirrors harness.run_episode's rng discipline exactly so the
    truth-model episode is bit-identical to the plain MPC one."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact, first_contact = 0.0, False, None
    violations: list = []
    for t in range(truth.h_episode):
        a = plan_mitigated(model, s, rng, violations, eps,
                           horizon=horizon, n_samples=n_samples, block=block)
        s2, r, c = truth.step(s, a)
        pred, _, _ = model.step(s, a)
        if max(abs(pred[0] - s2[0]), abs(pred[1] - s2[1])) > tol:
            violations.append(s)  # the PRE-state: where the model's step lied
        if c and first_contact is None:
            first_contact = t
        contact = contact or c
        total += r
        s = s2
    return MitigatedEpisode(ret=total, contact=contact, final_state=s,
                            violations=len(violations),
                            first_contact_step=first_contact)
```

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/test_mitigation.py -v`
Expected: 5 passed (takes a couple of minutes — each escape test runs 3 MPC episodes of 80 steps).

If `test_mitigated_blind_escapes_cart` fails on the `0.4 * t.ret` margin: print `b.ret, m.ret, t.ret` and inspect. The transient (drive right ~10 steps, escape, travel back to the left plateau) legitimately costs return; if the measured ratio is stable but below 0.4, report the actual values to the controller BEFORE changing anything — do not silently loosen the margin.

If `test_bit_identical_episode_on_truth_model` fails: the rng discipline diverged — check that `plan_mitigated` consumes `rng` only via `mpc._candidates` (no extra draws) and that `run_mitigated_episode` calls `truth.initial_state(rng)` before the loop exactly as `harness.run_episode` does.

- [ ] **Step 5: Run the rest of the suite to confirm no regressions**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/ -q --ignore=tests/test_continuous_contract.py`
Expected: all pass. (The contract tests are slow and untouched by this task; the reviewer can rely on Task 1 not importing them.)

- [ ] **Step 6: Commit**

```bash
git add src/cwm/continuous/mitigation.py tests/test_mitigation.py
git commit -m "feat: distrust-region replanning (mitigation experiment, paper 2)

Planner-side mitigation: violation detection via predicted-vs-observed
mismatch (tol=1e-6), imagination truncation on distrust-ball entry (position
metric), flee tie-break when pinned. Bit-identical to mpc.plan on a correct
model (asserted). Offline battery: zero-cost control, violation detection,
escape on both instruments.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: sweep script + full CPU run + commit results

**Files:**
- Create: `scripts/continuous_mitigation.py`
- Create (runtime): `results/continuous_mitigation.json`

**Interfaces:**
- Consumes: `run_mitigated_episode` (Task 1 signature), `harness.run_episode`, `harness.mean_return`, `CartWall`, `PendulumStop`, `blind_of`.
- Produces: `results/continuous_mitigation.json` with one row per (instrument, knob): `{instrument, knob, j_truth, j_blind, j_mitigated, j_random, play_cost_blind, play_cost_mitigated, blind_contact_rate, mitigated_contact_rate, mean_violations, mean_first_contact_step, n_episodes}`.

- [ ] **Step 1: Write the script**

Create `scripts/continuous_mitigation.py`:

```python
"""Mitigation sweep: distrust-region replanning vs the pinned blind planner.

For each instrument and mode-position knob (the paper's existing grids), run
truth-MPC / blind-MPC / blind-MPC+mitigation on paired seeds and report the
play_cost collapse. CPU-only.

Run: PYTHONPATH=src python scripts/continuous_mitigation.py   (~10-15 min)
"""
import argparse
import json
import pathlib
import time

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness
from cwm.continuous.mitigation import run_mitigated_episode

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cart-walls", type=float, nargs="+",
                default=[2.0, 4.0, 6.0, 8.0, 10.0])
ap.add_argument("--pend-stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
ap.add_argument("--cart-eps", type=float, default=0.25)
ap.add_argument("--pend-eps", type=float, default=0.1)
args = ap.parse_args()

t0 = time.time()
rows = []
print(f"{'inst':>4} {'knob':>5} {'J_tru':>7} {'J_bli':>7} {'J_mit':>7} "
      f"{'J_rnd':>6} {'pc_bli':>7} {'pc_mit':>7} {'c_bli':>5} {'c_mit':>5} "
      f"{'viol':>5} {'t_c1':>5}", flush=True)
for inst, knobs, eps, mk in (
        ("cart", args.cart_walls, args.cart_eps,
         lambda k: CartWall(x_wall=k)),
        ("pend", args.pend_stops, args.pend_eps,
         lambda k: PendulumStop(th_stop=k))):
    for k in knobs:
        truth = mk(k)
        blind = blind_of(truth)
        t, b, m, r = [], [], [], []
        for i in range(args.episodes):
            sd = args.seed + 1000 * i
            t.append(harness.run_episode(truth, truth, "mpc", sd))
            b.append(harness.run_episode(truth, blind, "mpc", sd))
            m.append(run_mitigated_episode(truth, blind, seed=sd, eps=eps))
            r.append(harness.run_episode(truth, policy="random", seed=sd))
        j_t, j_b = harness.mean_return(t), harness.mean_return(b)
        j_m, j_r = harness.mean_return(m), harness.mean_return(r)
        denom = j_t - j_r
        fc = [e.first_contact_step for e in m if e.first_contact_step is not None]
        row = {
            "instrument": inst, "knob": k, "eps": eps,
            "j_truth": j_t, "j_blind": j_b, "j_mitigated": j_m, "j_random": j_r,
            "play_cost_blind": (j_t - j_b) / denom if denom > 0 else 0.0,
            "play_cost_mitigated": (j_t - j_m) / denom if denom > 0 else 0.0,
            "blind_contact_rate": sum(e.contact for e in b) / args.episodes,
            "mitigated_contact_rate": sum(e.contact for e in m) / args.episodes,
            "mean_violations": sum(e.violations for e in m) / args.episodes,
            "mean_first_contact_step": sum(fc) / len(fc) if fc else None,
            "n_episodes": args.episodes,
        }
        rows.append(row)
        print(f"{inst:>4} {k:5.1f} {j_t:7.2f} {j_b:7.2f} {j_m:7.2f} "
              f"{j_r:6.2f} {row['play_cost_blind']:7.3f} "
              f"{row['play_cost_mitigated']:7.3f} "
              f"{row['blind_contact_rate']:5.2f} "
              f"{row['mitigated_contact_rate']:5.2f} "
              f"{row['mean_violations']:5.1f} "
              f"{(row['mean_first_contact_step'] or -1):5.1f}", flush=True)

out = pathlib.Path("results/continuous_mitigation.json")
out.write_text(json.dumps({"script": "continuous_mitigation.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
```

- [ ] **Step 2: Calibration smoke — one knob per instrument, 5 episodes**

Run:
```bash
PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python \
    scripts/continuous_mitigation.py --episodes 5 --cart-walls 8 --pend-stops 1.4
```
Expected: two rows print; `pc_bli` ≈ 1.0 on both; `pc_mit` clearly below `pc_bli` (the exact residual is a finding — record it); `c_mit` ≈ 1.0 with `viol` small (~1-3) and `t_c1` > 0. If `pc_mit` is NOT clearly below `pc_bli`, stop and report the row to the controller (candidate causes: eps too small to catch the imagined crossing — the imagined step near the wall moves ~v·dt per step, so the band must be wider than that; or the tie-break failing to escape). Do not tune per-knob.

- [ ] **Step 3: Full run (background, ~10-25 min) and verify the JSON**

Run:
```bash
nohup bash -c '
  cd /private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2
  export PYTHONPATH=src
  /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -u \
      scripts/continuous_mitigation.py
  echo "MITIGATION DONE rc=$?"
' > results/continuous_mitigation.log 2>&1 &
```
Wait for `MITIGATION DONE rc=0` in `results/continuous_mitigation.log` (poll or Monitor). Then verify:
```bash
PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -c "
import json
d = json.load(open('results/continuous_mitigation.json'))
assert len(d['rows']) == 11, len(d['rows'])
for r in d['rows']:
    print(f\"{r['instrument']} {r['knob']}: pc_blind={r['play_cost_blind']:.3f} pc_mit={r['play_cost_mitigated']:.3f} viol={r['mean_violations']:.1f}\")
    assert r['play_cost_mitigated'] < r['play_cost_blind'] - 0.3, 'mitigation did not collapse the cost'
"
```
Expected: 11 rows, every row's mitigated cost at least 0.3 below the blind cost (blind ≈ 1.0 everywhere per the paper's tables). If a specific knob violates the assertion, that is the degenerate-knob case the spec anticipated: report the row to the controller with the measured numbers before any grid change.

- [ ] **Step 4: Commit script + results (not the log)**

```bash
git add scripts/continuous_mitigation.py results/continuous_mitigation.json
git commit -m "results: mitigation sweep — distrust-region replanning collapses play_cost

Truth/blind/mitigated arms on paired seeds across both instruments' knob
grids. Blind planner pinned at play_cost ~1 (below random) everywhere;
distrust-region replanning collapses it to a bounded first-contact transient.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: fold the mitigation result into the paper

**Files:**
- Modify: `docs/EXPERIMENTS.md`
- Modify: `docs/paper2/preprint-draft.md`
- Modify: `docs/paper2/main.tex`
- Regenerate: `docs/paper2/main.pdf`

**Interfaces:**
- Consumes: the measured rows from `results/continuous_mitigation.json` (Task 2). All numbers verbatim from that file — never invented or re-rounded.

- [ ] **Step 1: Extract the measured numbers**

Run:
```bash
PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -c "
import json
d = json.load(open('results/continuous_mitigation.json'))
for r in d['rows']:
    print(r)
" > .superpowers/sdd/mitigation-measured-numbers.txt
cat .superpowers/sdd/mitigation-measured-numbers.txt
```
Use ONLY these numbers in every document below.

- [ ] **Step 2: EXPERIMENTS.md — dated section**

Add at the top (newest-first convention): `## PAPER 2 — Mitigation: distrust-region replanning collapses the exploitation (2026-07-08)` with: one paragraph (mechanism: prediction-vs-observation violation detection, imagination truncation, flee tie-break; tol=1e-6, ε=0.25/0.1; zero-cost control bit-identical on truth — cite the test), the full 11-row table (instrument, knob, play_cost_blind, play_cost_mitigated, contact rates, mean violations, mean first-contact step), and a Findings paragraph: the collapse, how the residual scales with knob/lure distance (read it off the measured rows), and the framing sentence — the gate still certified a wrong model; what collapses is the planner-mediated exploitation, at the price of ~one unavoidable first contact (consistent with identifiability: you cannot avoid what you have never seen).

- [ ] **Step 3: Paper §6-adjacent subsection + §9 + abstract (draft AND tex)**

In `docs/paper2/preprint-draft.md` and `docs/paper2/main.tex`, mirrored edits:
1. New short subsection after the second-instrument-robustness paragraph (end of the synthesis section): title like "Mitigation: the exploitation is planner-mediated". Content: mechanism in 3-4 sentences; a compact table (one row per knob, both instruments, columns knob / play_cost_blind / play_cost_mitigated / mean violations / first-contact step) or, if 11 rows is too heavy for the flow, the cart row block plus one summary sentence for the pendulum with the table in full only in EXPERIMENTS.md — implementer's call by page flow; framing: does NOT contradict the danger law (the gate still accepted the wrong model); the planner's own prediction-vs-observation signal, free at deployment, collapses play_cost from ≈1 to the measured residual; the mitigated planner must touch the mode once (report mean first-contact step), which is identifiability operationalized; with a correct model the mitigation is bit-identical to plain MPC (zero cost when the model is right — by construction, tested).
2. §9 ("One planner family" paragraph in both files): rewrite — the mitigation claim is now MEASURED (point to the new subsection); the remaining honest scope is that random-shooting MPC is the only BASE planner family.
3. Abstract (both files): one clause added where the planner exploitation is described, e.g. "...; a planner that merely checks its own predictions against observations collapses this exploitation to a single unavoidable first contact (measured on both instruments)". Keep it to one clause; numbers stay in the body.

- [ ] **Step 4: Recompile the PDF and check**

```bash
cd docs/paper2
rm -f main.aux main.out main.log
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null 2>&1
echo "overfull>2pt:"; grep "^Overfull \\\\hbox" main.log | grep -oE "[0-9]+\.[0-9]+pt" | awk '$1+0>2.0' | wc -l | tr -d ' '
echo "undefined:"; grep -c "undefined" main.log
grep -oE "Output written on main.pdf \([0-9]+ pages" main.log
rm -f main.aux main.out main.log
cd ../..
```
Expected: `overfull>2pt: 0`, `undefined: 0`. If the new table overflows, switch it to the compact form (Step 3's fallback) until 0.

- [ ] **Step 5: Commit and push**

```bash
git add docs/EXPERIMENTS.md docs/paper2/preprint-draft.md docs/paper2/main.tex docs/paper2/main.pdf
git commit -m "paper2+docs: mitigation result — planner-mediated exploitation, measured

New subsection: distrust-region replanning collapses play_cost from ~1 to a
bounded first-contact transient on both instruments (11-knob sweep). §9's
one-planner-family limitation rewritten (mitigation now measured); abstract
gains one clause. All numbers verbatim from results/continuous_mitigation.json.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin claude/continuous-setting-feasibility-wktp6b
```

---

## Notes for the executor

- The blind planner's pinned behavior (`b.final_state[0] == x_wall`, play_cost ≈ 1.03) is established fact from the paper's tables — if the blind arm does NOT reproduce it, something is broken in the harness usage, not in the paper.
- Never modify `mpc.py`, `harness.py`, or `envs.py` — the mitigation is strictly additive.
- The residual play_cost of the mitigated arm growing with lure distance (far knobs) is expected physics (longer travel-back transient), not a bug. Report it.
- If the calibration smoke shows ε defaults failing, the fix is ONE global adjustment per instrument, recorded in the spec deltas — never per-knob tuning.
