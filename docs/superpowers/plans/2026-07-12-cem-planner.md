# CEM Second-Planner-Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure that play_cost is planner-dependent exactly as Proposition 3 prescribes: CEM (competent on truth) is NOT exploited by the certified-blind model because its imagination never reaches the phantom region, in contrast to random-shooting MPC — and fold the result into paper 2.

**Architecture:** Additive module `src/cwm/continuous/cem.py` (planner + episode loop + imagined-boundary-crossing diagnostic); sweep script comparing CEM-blind vs the existing MPC-blind geometry with the query-hit proxy measured for both; paper subsection in the mechanism section + §9 rewrite. Prototype-validated hyperparameters (controller, 2026-07-12): n_iters=5, n_samples=64, elite_frac=0.125, min_std=0.05 → cart CEM-truth ≈ 97% of MPC-truth, CEM-blind pc ≈ 0.000, zero contact.

**Tech Stack:** Python 3.12, pytest, main-repo `.venv` (`/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python`), `PYTHONPATH=src`. CPU only.

## Global Constraints

- Work in the DURABLE worktree `/Users/javieraguilarmartin1/Documents/repos/cwm-wt-paper2`, branch `claude/continuous-setting-feasibility-wktp6b`. Never touch the main checkout or paper 1.
- Do NOT modify `mpc.py`, `harness.py`, `envs.py`, `mitigation.py` — cem.py is strictly additive (the script may READ `mpc._candidates` for the MPC diagnostic).
- Fixed hyperparameters (no per-knob tuning): horizon 40, n_iters 5, n_samples 64, elite_frac 0.125, min_std 0.05.
- Report measured numbers honestly: expected pc_blind(CEM) ≈ 0 knob-invariant with ≈0 crossing; deviations are findings. CEM local-optima on pendulum truth are reported, not hidden.
- Paper numbers verbatim from `results/continuous_cem.json`.
- `bash scripts/check_latex.sh` → both papers PASS at the integration task.
- Commit per task; trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `cem.py` + offline tests

**Files:**
- Create: `src/cwm/continuous/cem.py`
- Create: `tests/test_cem.py`

**Interfaces:**
- Consumes: `mpc.plan` (for the competence test), `CartWall`, `PendulumStop`, `blind_of`, `harness.run_episode`.
- Produces (Task 2 relies on these):
  - `plan_cem(model, state, rng, horizon=40, n_iters=5, n_samples=64, elite_frac=0.125, min_std=0.05, boundary=None)` → `float` when `boundary is None`, else `(float, float)` = (action, fraction of this call's sampled imagined trajectories that crossed `boundary` in position).
  - `run_episode(truth, model, seed=0, boundary=None, **plan_kw) -> CemEpisode` with fields `ret: float, contact: bool, final_state: tuple, crossing_frac: float | None` (mean over steps of the per-plan crossing fraction; None if boundary None).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cem.py`:

```python
"""Offline tests for the CEM second-planner-family experiment. Prototype-
validated expectations (2026-07-12): CEM is competent on truth (cart ~97% of
MPC-truth) and is NOT exploited by the blind model (zero contact, near-truth
return) — the other branch of Proposition 3."""
import random

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import harness, mpc
from cwm.continuous.cem import plan_cem, run_episode

CART = CartWall(x_wall=8.0)
PEND = PendulumStop(th_stop=1.4)


def test_deterministic_given_seed():
    a1 = plan_cem(CART, (0.5, 1.0), random.Random(7))
    a2 = plan_cem(CART, (0.5, 1.0), random.Random(7))
    assert a1 == a2


def test_cem_competent_on_truth_cart():
    for seed in (0, 3):
        cem_ep = run_episode(CART, CART, seed=seed)
        mpc_ep = harness.run_episode(CART, CART, "mpc", seed=seed)
        assert cem_ep.ret >= 0.9 * mpc_ep.ret, (cem_ep.ret, mpc_ep.ret)


def test_cem_blind_not_exploited_cart():
    for seed in (0, 3):
        b = run_episode(CART, blind_of(CART), seed=seed, boundary=CART.x_wall)
        t = run_episode(CART, CART, seed=seed)
        assert b.contact is False
        assert b.final_state[0] < CART.x_wall - 1.0
        assert b.ret >= 0.95 * t.ret          # prototype: identical to 2 dp
        assert b.crossing_frac is not None and b.crossing_frac < 0.05


def test_cem_blind_not_pinned_pendulum():
    b = run_episode(PEND, blind_of(PEND), seed=0, boundary=PEND.th_stop)
    assert b.contact is False
    assert b.final_state[0] < PEND.th_stop - 0.1
    assert b.crossing_frac < 0.05
```

- [ ] **Step 2: Run to verify collection failure**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/test_cem.py -v`
Expected: `ModuleNotFoundError: No module named 'cwm.continuous.cem'`.

- [ ] **Step 3: Implement `src/cwm/continuous/cem.py`**

```python
"""Cross-entropy-method planner: the second planner family (paper 2).

Per-step Gaussian action distributions refined over a few elite iterations.
Purpose in the paper: measure the OTHER branch of the play-cost bound
(Proposition 3). Random shooting with constant candidates reaches the distant
phantom plateau in imagination (high query-hit mass on the disagreement
region) and is exploited by the certified-blind model; CEM's local search
concentrates on the nearer TRUE plateau from the first elite iteration and
never discovers the phantom (near-zero query-hit mass) -- so, exactly as the
bound prescribes, it is not exploited. The optional `boundary` argument
measures this: the fraction of sampled imagined trajectories that cross the
mode boundary during planning.

Deterministic given the rng. Hyperparameters are prototype-calibrated and
fixed across knobs and instruments (no per-knob tuning).
"""
import random
from dataclasses import dataclass


def plan_cem(model, state, rng, horizon: int = 40, n_iters: int = 5,
             n_samples: int = 64, elite_frac: float = 0.125,
             min_std: float = 0.05, boundary: float | None = None):
    """Best first action by CEM. With boundary set, also returns the fraction
    of sampled imagined trajectories whose position crossed it."""
    a_max = model.a_max
    n_elite = max(2, int(n_samples * elite_frac))
    mean = [0.0] * horizon
    std = [a_max] * horizon
    crossed = total_samples = 0
    for _ in range(n_iters):
        scored = []
        for _ in range(n_samples):
            acts = [max(-a_max, min(a_max, rng.gauss(mean[t], std[t])))
                    for t in range(horizon)]
            s, total, hit = state, 0.0, False
            for a in acts:
                s, r, _ = model.step(s, a)
                total += r
                if boundary is not None and s[0] >= boundary:
                    hit = True
            scored.append((total, acts))
            total_samples += 1
            crossed += hit
        scored.sort(key=lambda x: -x[0])
        elites = [acts for _, acts in scored[:n_elite]]
        mean = [sum(e[t] for e in elites) / n_elite for t in range(horizon)]
        std = [max(min_std, (sum((e[t] - mean[t]) ** 2 for e in elites)
                             / n_elite) ** 0.5) for t in range(horizon)]
    if boundary is None:
        return mean[0]
    return mean[0], crossed / total_samples


@dataclass
class CemEpisode:
    ret: float
    contact: bool
    final_state: tuple
    crossing_frac: float | None   # mean per-plan imagined boundary-crossing


def run_episode(truth, model, seed: int = 0, boundary: float | None = None,
                **plan_kw) -> CemEpisode:
    """Play one episode in `truth`, planning on `model` with CEM. Mirrors
    harness.run_episode's rng discipline (initial_state first, then per-step
    planning draws)."""
    rng = random.Random(seed)
    s = truth.initial_state(rng)
    total, contact, fracs = 0.0, False, []
    for _ in range(truth.h_episode):
        out = plan_cem(model, s, rng, boundary=boundary, **plan_kw)
        if boundary is None:
            a = out
        else:
            a, frac = out
            fracs.append(frac)
        s, r, c = truth.step(s, a)
        total += r
        contact = contact or c
    return CemEpisode(ret=total, contact=contact, final_state=s,
                      crossing_frac=(sum(fracs) / len(fracs)) if fracs else None)
```

Note: the pendulum's boundary is on the SAME position coordinate `s[0]` (θ vs th_stop) — the `s[0] >= boundary` check is instrument-generic for both our modes.

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/test_cem.py -v`
Expected: 4 passed (a few minutes — each episode is 80 plans × 5×64 rollouts). If `test_cem_competent_on_truth_cart` fails marginally (<0.9), print both returns and report to the controller — do not tune hyperparameters unilaterally. If the pendulum test hits a truth local-optimum artifact, that test doesn't compare to truth (it only checks non-pinning), so it should still pass.

- [ ] **Step 5: No-regression + commit**

Run: `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/ -q --ignore=tests/test_continuous_contract.py`
Expected: all pass.

```bash
git add src/cwm/continuous/cem.py tests/test_cem.py
git commit -m "feat: CEM planner — the second planner family (paper 2)

Per-step Gaussian CEM with elite refinement, plus an imagined
boundary-crossing diagnostic (the query-hit proxy of Proposition 3).
Prototype-validated: competent on truth, NOT exploited by the blind model.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: sweep script + full run + results

**Files:**
- Create: `scripts/continuous_cem.py`
- Create (runtime): `results/continuous_cem.json`

**Interfaces:**
- Consumes: `cem.run_episode` (Task 1), `harness.run_episode`, `harness.mean_return`, `mpc._candidates` (READ-ONLY, for the MPC crossing diagnostic), `CartWall`, `PendulumStop`, `blind_of`.
- Produces: `results/continuous_cem.json` rows `{instrument, knob, j_truth_cem, j_blind_cem, j_random, play_cost_blind_cem, blind_contact_rate, crossing_frac_cem_blind, crossing_frac_mpc_blind, n_episodes}`.

- [ ] **Step 1: Write the script**

Create `scripts/continuous_cem.py`:

```python
"""Second planner family: CEM vs the certified-blind model.

Measures the other branch of Proposition 3: play_cost <= query-hit mass.
Random shooting (constant candidates) reaches the phantom in imagination and
is exploited (the paper's Tables); CEM's local search never discovers it.
Per knob we report CEM's blind-arm play_cost (expected ~0, knob-invariant),
contact rate, and the imagined boundary-crossing fraction for BOTH planners
on the blind model -- the measured query-hit proxy.

Run: PYTHONPATH=src python scripts/continuous_cem.py   (~30-60 min CPU)
"""
import argparse
import json
import pathlib
import random
import time

from cwm.continuous.envs import CartWall, PendulumStop, blind_of
from cwm.continuous import cem, harness, mpc

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--episodes", type=int, default=20)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cart-walls", type=float, nargs="+",
                default=[2.0, 4.0, 6.0, 8.0, 10.0])
ap.add_argument("--pend-stops", type=float, nargs="+",
                default=[0.8, 1.0, 1.2, 1.4, 1.6, 2.0])
args = ap.parse_args()


def mpc_crossing_frac(model, state, rng, boundary, horizon=40,
                      n_samples=200, block=10):
    """Fraction of random-shooting candidates whose imagined trajectory
    crosses `boundary` (read-only reuse of mpc's candidate generator)."""
    crossed = total = 0
    for acts in mpc._candidates(model.a_max, rng, horizon, n_samples, block):
        s, hit = state, False
        for a in acts:
            s, _, _ = model.step(s, a)
            if s[0] >= boundary:
                hit = True
        crossed += hit
        total += 1
    return crossed / total


t0 = time.time()
rows = []
print(f"{'inst':>4} {'knob':>5} {'J_tru':>7} {'J_bli':>7} {'J_rnd':>6} "
      f"{'pc_bli':>7} {'c_bli':>5} {'xing_cem':>8} {'xing_mpc':>8}", flush=True)
for inst, knobs, mk in (
        ("cart", args.cart_walls, lambda k: CartWall(x_wall=k)),
        ("pend", args.pend_stops, lambda k: PendulumStop(th_stop=k))):
    for k in knobs:
        truth = mk(k)
        blind = blind_of(truth)
        t, b, r, xm = [], [], [], []
        for i in range(args.episodes):
            sd = args.seed + 1000 * i
            t.append(cem.run_episode(truth, truth, seed=sd))
            b.append(cem.run_episode(truth, blind, seed=sd, boundary=k))
            r.append(harness.run_episode(truth, policy="random", seed=sd))
            # MPC crossing diagnostic: one plan from the episode's start state
            rng = random.Random(sd)
            s0 = truth.initial_state(rng)
            xm.append(mpc_crossing_frac(blind, s0, rng, k))
        j_t, j_b = harness.mean_return(t), harness.mean_return(b)
        j_r = harness.mean_return(r)
        denom = j_t - j_r
        row = {
            "instrument": inst, "knob": k,
            "j_truth_cem": j_t, "j_blind_cem": j_b, "j_random": j_r,
            "play_cost_blind_cem": (j_t - j_b) / denom if denom > 0 else 0.0,
            "blind_contact_rate": sum(e.contact for e in b) / args.episodes,
            "crossing_frac_cem_blind":
                sum(e.crossing_frac for e in b) / args.episodes,
            "crossing_frac_mpc_blind": sum(xm) / len(xm),
            "n_episodes": args.episodes,
        }
        rows.append(row)
        print(f"{inst:>4} {k:5.1f} {j_t:7.2f} {j_b:7.2f} {j_r:6.2f} "
              f"{row['play_cost_blind_cem']:7.3f} "
              f"{row['blind_contact_rate']:5.2f} "
              f"{row['crossing_frac_cem_blind']:8.4f} "
              f"{row['crossing_frac_mpc_blind']:8.4f}", flush=True)

out = pathlib.Path("results/continuous_cem.json")
out.write_text(json.dumps({"script": "continuous_cem.py",
                           "params": vars(args), "rows": rows,
                           "elapsed_s": round(time.time() - t0, 1)}, indent=2))
print(f"wrote {out}  [{round(time.time() - t0, 1)}s]", flush=True)
```

- [ ] **Step 2: Smoke (one knob per instrument, 3 episodes)**

Run:
```bash
PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python \
    scripts/continuous_cem.py --episodes 3 --cart-walls 8 --pend-stops 1.4
```
Expected: two rows; `pc_bli` ≈ 0, `c_bli` = 0.00, `xing_cem` ≈ 0 and `xing_mpc` clearly larger (the constant +a_max candidate alone guarantees a nonzero floor). Delete the smoke JSON afterward.

- [ ] **Step 3: Full run (background, ~30–90 min) + verify**

```bash
nohup bash -c '
  cd /Users/javieraguilarmartin1/Documents/repos/cwm-wt-paper2
  export PYTHONPATH=src
  /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -u \
      scripts/continuous_cem.py
  echo "CEM SWEEP DONE rc=$?"
' > results/continuous_cem.log 2>&1 &
```
Wait for `CEM SWEEP DONE rc=0` (poll patiently). Verify: 11 rows; every row `play_cost_blind_cem < 0.15` and `blind_contact_rate == 0.0` and `crossing_frac_cem_blind < crossing_frac_mpc_blind`. A row violating this is a finding — report the measured numbers, do not tune.

- [ ] **Step 4: Commit (script + tests JSON, not the log)**

```bash
git add scripts/continuous_cem.py results/continuous_cem.json
git commit -m "results: CEM sweep — play_cost is planner-dependent, per Proposition 3

CEM (competent on truth) is not exploited by the certified-blind model on
either instrument: pc ~ 0 knob-invariant, zero contact, near-zero imagined
boundary-crossing vs random-shooting's high crossing fraction. The measured
other branch of the play-cost bound.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: fold into the paper

**Files:**
- Modify: `docs/EXPERIMENTS.md`, `docs/paper2/preprint-draft.md`, `docs/paper2/main.tex`; regenerate `docs/paper2/main.pdf`.

**Interfaces:** numbers verbatim from `results/continuous_cem.json` (extract to `.superpowers/sdd/cem-measured-numbers.txt` first, same pattern as prior integrations).

- [ ] **Step 1**: extract measured numbers to `.superpowers/sdd/cem-measured-numbers.txt` and use ONLY those.
- [ ] **Step 2**: EXPERIMENTS.md dated section at top ("PAPER 2 — Second planner family (CEM): the other branch of the play-cost bound (2026-07-12)"): mechanism, hyperparams, full 11-row table, findings (pc≈0 knob-invariant, zero contact, crossing CEM vs MPC, the landmine framing, honest caveats: CEM pendulum-truth local optima if observed in the run; safety-by-limited-reach is not knowledge).
- [ ] **Step 3**: paper subsection in the mechanism section (both files) titled like "A second planner family: play\_cost is planner-dependent, as the bound prescribes" — 2 short paragraphs + compact table (knob × pc_blind-MPC (from the existing danger table) × pc_blind-CEM × crossing MPC/CEM; or the clearest compact form); tie explicitly to Prop 3 and to §2.3's design lesson iii; include the two honest caveats. §9: rewrite the planner-family limitation (two families, one per branch; remaining: gradient/tree planners; CEM's non-exploitation is reach-limited, not knowledge). Abstract: add the one-clause mention ONLY if the abstract stays ≤1920 chars — verify with a character count; otherwise skip and note it.
- [ ] **Step 4**: `bash scripts/check_latex.sh` → both papers PASS (restore docs/paper/main.pdf if dirtied). Commit ("paper2+docs: CEM second-planner-family result — planner-dependent play_cost") with trailer; push.

## Notes for the executor
- The MPC-blind play_cost values already exist in the paper's danger tables — do NOT re-run MPC play; only the crossing diagnostic is computed fresh.
- CEM hyperparameters are fixed; any deviation from expected results is reported, never tuned away.
