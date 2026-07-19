# PatchField2D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 2D bi-modal instrument (PatchField2D), run the full apparatus on it (mechanism, LLM synthesis with per-mode identifiability and partial repair, eps row, CEM row, 2D mitigation), and fold the results into paper 2 — closing the "one dimension, single stationary boundary" limitation.

**Architecture:** New env with 4D state and scalar heading action (planners unchanged); machinery generalized from 2-component to n-component state comparisons (golden-protected); `InstrumentSpec` gains per-mode probes (dict) and an optional per-mode sample classifier; mitigation gains `pos_dims` (fences as position tuples, segment-point crossing). Controller prototype (2026-07-16) already validated calibration: defaults p1=(3,0), p2=(7,0), R=1 give r1=0.1417, r2=0.0083, P(see1,miss2)@40=0.714; truth-MPC navigates to the real lode with UNMODIFIED mpc.plan; blind pc=1.000 exactly.

**Tech Stack:** Python 3.12, pytest, main-repo `.venv` (`/Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python`), `PYTHONPATH=src`. Azure GPT-5.x for Task 4 (creds in the worktree `.env`).

## Global Constraints

- Work in the DURABLE worktree `/Users/javieraguilarmartin1/Documents/repos/cwm-wt-paper2`, branch `claude/continuous-setting-feasibility-wktp6b`. Never touch the main checkout or paper 1.
- `mpc.py`, `harness.py`, `cem.py` bodies are NOT modified except the single backward-compatible `boundary`-predicate extension to `cem.py` in Task 5 (spelled out there). `env.step` must keep returning `(state, reward, contact: bool)`.
- The cart golden test (`test_build_contract_cart_matches_golden`, `test_cart_spec_is_byte_identical_to_golden`) must pass byte-identically after EVERY task. Existing emitted JSON keys (`wall_blindness` scalar, `sample_contains_wall` bool) unchanged for cart/pendulum. `tests/test_mitigation.py` (bitwise identity) must pass unchanged after Task 6.
- Instrument defaults (prototype-validated, FROZEN unless a run exposes degeneracy — record any change): p1=(3.0, 0.0), p2=(7.0, 0.0), R=1.0, gain=3.0, drag=0.3, dt=0.1, a_max=1.0, h_episode=80, lode_real=(−6,0) amp 0.3, lode_phantom=(12,0) amp 1.0, r0=2.0, width=0.5, x0_range=0.5 (both x0 and y0 uniform).
- Synthesis protocol constants: N=40 rollouts, eps=1e-9, max 5 refine iters, 6 paired MPC play episodes, 30 prompt examples.
- Report measured numbers honestly; deviations from expectations are findings, never tuned away. Paper numbers verbatim from committed JSONs.
- `bash scripts/check_latex.sh` → both papers PASS at the paper task.
- Commit per task; trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `PatchField2D` env + mechanism tests

**Files:**
- Modify: `src/cwm/continuous/envs.py` (append the class + extend `blind_of`)
- Create: `tests/test_patch2d.py`

**Interfaces:**
- Produces: `PatchField2D` frozen dataclass with fields exactly: `dt=0.1, gain=3.0, drag=0.3, a_max=1.0, p1: tuple | None = (3.0, 0.0), p2: tuple | None = (7.0, 0.0), R=1.0, lode_real=(-6.0, 0.0), amp_real=0.3, lode_phantom=(12.0, 0.0), amp_phantom=1.0, r0=2.0, width=0.5, h_episode=80, x0_range=0.5`. Methods: `initial_state(rng) -> (x, y, 0.0, 0.0)` (x0 AND y0 uniform in ±x0_range); `reward(state) -> float` (sum of two radial sigmoids `amp/(1+exp((dist−r0)/width))`); `step(state, action) -> (state4, reward, contact_bool)` with the heading integrator `phi = pi*clamp(a)/a_max; vx2 = vx + (gain*cos(phi) − drag*vx)*dt; vy2 = vy + (gain*sin(phi) − drag*vy)*dt; x2 = x + vx2*dt; y2 = y + vy2*dt`, then if `(x2,y2)` inside `p1` or `p2` (`(x2−cx)**2 + (y2−cy)**2 <= R**2`) the next state is `(x, y, 0.0, 0.0)` (PREVIOUS position, zero velocity) and contact=True; `contact_modes(state, action) -> (bool, bool)` — pure recomputation of which patch the step from `state` under `action` would enter (both False when no entry).
- `blind_of(env)` extended: for `PatchField2D` returns `replace(env, p1=None, p2=None)`; new helper `blind_of_modes(env, omit: tuple[str, ...]) -> PatchField2D` (e.g. `("p2",)` omits only patch 2).

- [ ] **Step 1: failing tests** — create `tests/test_patch2d.py`:

```python
"""Mechanism tests for the 2D bi-modal instrument (prototype-validated
expectations, 2026-07-16: r1~0.14, r2~0.008; truth-MPC reaches the real lode
with unmodified mpc.plan; blind-MPC freezes at patch 1, pc=1.000)."""
import random

from cwm.continuous.envs import PatchField2D, blind_of, blind_of_modes
from cwm.continuous import harness

ENV = PatchField2D()


def test_step_integrator_and_patch_semantics():
    # free step from rest heading east (a=0 -> phi=0)
    s2, r, c = ENV.step((0.0, 0.0, 0.0, 0.0), 0.0)
    assert not c and abs(s2[0] - 0.03) < 1e-12 and s2[1] == 0.0
    # a step that would enter patch 1 freezes at the PREVIOUS position
    s = (1.95, 0.0, 3.0, 0.0)   # next x2 ~ 2.24 -> inside disc((3,0),1)
    s2, r, c = ENV.step(s, 0.0)
    assert c and s2 == (1.95, 0.0, 0.0, 0.0)
    assert ENV.contact_modes(s, 0.0) == (True, False)


def test_blind_variants():
    b = blind_of(ENV)
    assert b.p1 is None and b.p2 is None
    s = (1.95, 0.0, 3.0, 0.0)
    s2, _, c = b.step(s, 0.0)
    assert not c and s2[0] > 2.0          # sails through the phantom patch
    b2 = blind_of_modes(ENV, ("p2",))
    assert b2.p1 == ENV.p1 and b2.p2 is None


def test_rarity_split():
    h1 = h2 = 0
    n = 200
    for i in range(n):
        rng = random.Random(50_000 + i)
        s = ENV.initial_state(rng)
        c1 = c2 = False
        for _ in range(ENV.h_episode):
            a = rng.uniform(-ENV.a_max, ENV.a_max)
            m1, m2 = ENV.contact_modes(s, a)
            c1, c2 = c1 or m1, c2 or m2
            s = ENV.step(s, a)[0]
        h1 += c1
        h2 += c2
    assert 0.08 < h1 / n < 0.22            # r1 ~ 0.14
    assert h2 / n < 0.05                   # r2 ~ 0.008


def test_truth_navigates_and_blind_is_pinned():
    t = harness.run_episode(ENV, ENV, "mpc", seed=0, n_samples=40)
    b = harness.run_episode(ENV, blind_of(ENV), "mpc", seed=0, n_samples=40)
    assert t.ret > 10.0                    # sits on the real lode
    assert abs(t.final_state[0] - ENV.lode_real[0]) < 2.5
    assert b.contact and b.ret < 1.0       # frozen at a patch edge
    assert b.final_state[0] < 3.0
```

- [ ] **Step 2: verify failure** — `PYTHONPATH=src /Users/javieraguilarmartin1/Documents/repos/code-world-models/.venv/bin/python -m pytest tests/test_patch2d.py -v` → ImportError (PatchField2D undefined).

- [ ] **Step 3: implement** — append to `src/cwm/continuous/envs.py` (match the file's frozen-dataclass style; tuples for points):

```python
@dataclass(frozen=True)
class PatchField2D:
    """Third instrument: 2D navigation with two sticky patches (bi-modal).

    4D state (x, y, vx, vy); SCALAR action a in [-a_max, a_max] mapped to a
    thrust heading phi = pi*a/a_max, so every planner (mpc, cem, harness)
    works unchanged. Each patch is an independent hard mode: a step whose
    next position falls inside disc(p_i, R) freezes at the PREVIOUS position
    with zero velocity (inelastic stop at the edge). blind_of removes both
    patches; blind_of_modes removes a subset. Reward is two radial sigmoid
    lodes: a small real one behind the start and a large phantom one beyond
    the patches (the lure). Patch centers are the rarity knobs
    (calibration 2026-07-16: r1=0.1417, r2=0.0083 at the defaults).
    """
    dt: float = 0.1
    gain: float = 3.0
    drag: float = 0.3
    a_max: float = 1.0
    p1: tuple | None = (3.0, 0.0)
    p2: tuple | None = (7.0, 0.0)
    R: float = 1.0
    lode_real: tuple = (-6.0, 0.0)
    amp_real: float = 0.3
    lode_phantom: tuple = (12.0, 0.0)
    amp_phantom: float = 1.0
    r0: float = 2.0
    width: float = 0.5
    h_episode: int = 80
    x0_range: float = 0.5

    def initial_state(self, rng) -> State:
        return (rng.uniform(-self.x0_range, self.x0_range),
                rng.uniform(-self.x0_range, self.x0_range), 0.0, 0.0)

    def _lode(self, x: float, y: float, lode: tuple, amp: float) -> float:
        d = math.hypot(x - lode[0], y - lode[1])
        return amp / (1.0 + math.exp((d - self.r0) / self.width))

    def reward(self, state: State) -> float:
        x, y = state[0], state[1]
        return (self._lode(x, y, self.lode_real, self.amp_real)
                + self._lode(x, y, self.lode_phantom, self.amp_phantom))

    def _inside(self, x: float, y: float, c: tuple | None) -> bool:
        return (c is not None
                and (x - c[0]) ** 2 + (y - c[1]) ** 2 <= self.R ** 2)

    def _integrate(self, state: State, action: float):
        x, y, vx, vy = state
        a = max(-self.a_max, min(self.a_max, action))
        phi = math.pi * a / self.a_max
        vx2 = vx + (self.gain * math.cos(phi) - self.drag * vx) * self.dt
        vy2 = vy + (self.gain * math.sin(phi) - self.drag * vy) * self.dt
        return x + vx2 * self.dt, y + vy2 * self.dt, vx2, vy2

    def contact_modes(self, state: State, action: float) -> tuple:
        x2, y2, _, _ = self._integrate(state, action)
        return self._inside(x2, y2, self.p1), self._inside(x2, y2, self.p2)

    def step(self, state: State, action: float):
        x2, y2, vx2, vy2 = self._integrate(state, action)
        if self._inside(x2, y2, self.p1) or self._inside(x2, y2, self.p2):
            s2 = (state[0], state[1], 0.0, 0.0)
            return s2, self.reward(s2), True
        s2 = (x2, y2, vx2, vy2)
        return s2, self.reward(s2), False


def blind_of_modes(env: "PatchField2D", omit: tuple) -> "PatchField2D":
    """Mode-selective blind model for the 2D instrument."""
    kw = {}
    if "p1" in omit:
        kw["p1"] = None
    if "p2" in omit:
        kw["p2"] = None
    return replace(env, **kw)
```

and extend `blind_of` (before its final `return replace(env, x_wall=None)`):

```python
    if isinstance(env, PatchField2D):
        return replace(env, p1=None, p2=None)
```

- [ ] **Step 4: pass** — same pytest command → 4 passed (the MPC test takes ~1 min). If `test_truth_navigates_and_blind_is_pinned` fails, report the measured returns/finals (do NOT retune the frozen defaults) — the prototype passed identical checks at seeds 0/3.
- [ ] **Step 5: no-regression + commit** — `pytest tests/ -q --ignore=tests/test_continuous_contract.py` all green, then:

```bash
git add src/cwm/continuous/envs.py tests/test_patch2d.py
git commit -m "feat: PatchField2D — 2D bi-modal instrument (heading action, sticky patches)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: n-component machinery + PATCH2D spec + offline battery

**Files:**
- Modify: `src/cwm/continuous/gate.py:28-30` (`transition_error`), `src/cwm/continuous/contract.py` (`contract_accuracy` sandbox+comparison, `SynthesizedModel.step`, `mode_blindness`, `synthesize_and_evaluate`), `src/cwm/continuous/instruments.py` (probes→dict; PATCH2D spec; per-mode sample classifier)
- Test: extend `tests/test_instruments.py` and `tests/test_continuous_contract.py`

**Interfaces (produced; later tasks rely on these exactly):**
- `gate.transition_error(truth, model, state, action)` → `max(max(|st[i]−sm[i]| for i), |rt−rm|)` over `min(len(st), len(sm))` components.
- `contract.SynthesizedModel.step` returns `(tuple(s2), reward, False)` for any state arity.
- `InstrumentSpec.mode_probes(env)` now returns `dict[str, list[(state, action)]]` — cart: `{"wall": [...]}` (same 3 probes), pendulum: `{"stop": [...]}`, patch2d: `{"patch1": [...], "patch2": [...]}` (3 probes each: states just outside the patch's west edge moving east, e.g. `((c[0]−R−0.15, c[1], v, 0.0), 0.0)` for v in (1.0, 2.0, 3.0) — each must fire that patch in truth).
- New optional spec field `sample_modes: Callable | None = None`; for PATCH2D: `sample_modes(env, transitions) -> {"patch1": bool, "patch2": bool}` by replaying each stored `(state, action)` through `env.contact_modes`.
- `contract.mode_blindness(code, env, eps=1e-6)` → scalar when the spec has ONE mode (exact current behavior/values), `dict[str, float]` when several.
- `synthesize_and_evaluate` emits for multi-mode instruments the ADDITIONAL keys `"mode_blindness": {..}` and `"sample_contains_mode_per": {..}` while keeping `"wall_blindness"` (mean of the dict) and `"sample_contains_wall"` (any-mode bool); single-mode instruments emit exactly today's schema.
- `PATCH2D` api_text (4-variable integrator with the heading mapping, stated in the same pinned-order style) and rules_text (constants incl. patch centers/R; radial-sigmoid reward formula; one "Additional dynamics rule" clause PER PRESENT patch, each stating the disc condition and the stay-at-previous-position stop; `include_mode=False` omits BOTH patch clauses; a new optional arg `omit=("p2",)` supports the mode-selective arm used by Task 4's partial-repair control).

- [ ] **Step 1: failing tests** — add to `tests/test_instruments.py`:

```python
def test_mode_probes_are_dicts_and_fire():
    from cwm.continuous.envs import PatchField2D
    from cwm.continuous.instruments import PATCH2D_SPEC, spec_for
    env = PatchField2D()
    assert spec_for(env) is PATCH2D_SPEC
    probes = PATCH2D_SPEC.mode_probes(env)
    assert set(probes) == {"patch1", "patch2"}
    for name, plist in probes.items():
        for s, a in plist:
            c1, c2 = env.contact_modes(s, a)
            assert (c1, c2) == ((name == "patch1"), (name == "patch2"))


def test_cart_probes_dict_single_mode():
    from cwm.continuous.instruments import CART_SPEC
    env = CartWall(x_wall=8.0)
    probes = CART_SPEC.mode_probes(env)
    assert list(probes) == ["wall"] and len(probes["wall"]) == 3
```

and to `tests/test_continuous_contract.py` (uses the Task-1 env; FakeProvider battery):

```python
from cwm.continuous.envs import PatchField2D, blind_of_modes

P2D = PatchField2D()
P2D_FULL_CODE = '''\
import math
def step(state, action):
    x, y, vx, vy = state
    a = max(-1.0, min(1.0, action))
    phi = math.pi * a / 1.0
    vx2 = vx + (3.0 * math.cos(phi) - 0.3 * vx) * 0.1
    vy2 = vy + (3.0 * math.sin(phi) - 0.3 * vy) * 0.1
    x2, y2 = x + vx2 * 0.1, y + vy2 * 0.1
    for cx, cy in ((3.0, 0.0), (7.0, 0.0)):
        if (x2 - cx) ** 2 + (y2 - cy) ** 2 <= 1.0:
            return [x, y, 0.0, 0.0]
    return [x2, y2, vx2, vy2]
def reward(state):
    x, y = state[0], state[1]
    d1 = math.hypot(x + 6.0, y); d2 = math.hypot(x - 12.0, y)
    return (0.3 / (1.0 + math.exp((d1 - 2.0) / 0.5))
            + 1.0 / (1.0 + math.exp((d2 - 2.0) / 0.5)))
'''
P2D_OMIT_P2_CODE = P2D_FULL_CODE.replace("((3.0, 0.0), (7.0, 0.0))",
                                         "((3.0, 0.0),)")


def test_patch2d_full_code_float_exact():
    tr = collect_transitions(P2D, n_rollouts=5, seed=0)
    acc, fails = contract_accuracy(P2D_FULL_CODE, tr, eps=1e-9)
    assert acc == 1.0, fails[:3]


def test_patch2d_per_mode_blindness():
    mb = mode_blindness(P2D_OMIT_P2_CODE, P2D)
    assert mb == {"patch1": 0.0, "patch2": 1.0}   # partial blindness!


def test_patch2d_synthesize_and_evaluate_keys():
    cell = synthesize_and_evaluate(
        FakeProvider([f"```python\n{P2D_OMIT_P2_CODE}```"]), "fake", P2D,
        include_mode=False, n_rollouts=3, seed=0)
    assert "mode_blindness" in cell and "sample_contains_mode_per" in cell
    assert isinstance(cell["wall_blindness"], float) or cell["wall_blindness"] is None
```

- [ ] **Step 2: verify failure** — pytest the two files with `-k "patch2d or probes_dict or probes_are_dicts"` → ImportError / KeyError.
- [ ] **Step 3: implement** — (a) `gate.transition_error`: `return max(max(abs(a - b) for a, b in zip(st, sm)), abs(rt - rm))`. (b) `contract_accuracy`: sandbox `_out.append({'ns': [float(v) for v in _ns], 'r': float(_r)})`; comparison `err = max(max(abs(g - e) for g, e in zip(got["ns"], t["next_state"])), abs(got["r"] - t["reward"]))`. (c) `SynthesizedModel.step`: `return tuple(s2), self._reward(list(s2)), False`. (d) `instruments.py`: cart/pendulum `mode_probes` wrap their current lists as `{"wall": [...]}` / `{"stop": [...]}`; add `PATCH2D_SPEC` (api_text with the 4-variable pinned integrator text incl. `phi = pi * a / a_max` and the two update lines; `_patch2d_rules_text(env, include_mode, omit=())` emitting constants, the radial reward formulas with the concrete lode/amp/r0/width values, and one patch clause per present-and-not-omitted patch; `_patch2d_probes(env)` as specified; `sample_modes` replaying `(state, action)` via `env.contact_modes`); `InstrumentSpec` gains `sample_modes: Callable | None = None` (default None) and `spec_for` dispatches `PatchField2D → PATCH2D_SPEC`. (e) `contract.mode_blindness`: iterate the dict; per-mode fraction wrong over that mode's probes; return the single value when `len(probes) == 1` else the dict. (f) `synthesize_and_evaluate`: after gating, if the spec has `sample_modes`, add `"sample_contains_mode_per": spec.sample_modes(env, transitions)` and `"mode_blindness": <dict>` with `"wall_blindness"` = mean of the dict (or None if gate failed); single-mode path byte-identical to today. `build_contract` passes through an optional `omit=()` kwarg to rules_text (cart/pendulum rules_text signatures unchanged — use a keyword-tolerant wrapper only in the PATCH2D rules_text).
- [ ] **Step 4: pass** — targeted tests green, THEN the full suite including `tests/test_continuous_contract.py` and the golden tests (byte-identical cart prompt) and `tests/test_mitigation.py` — all green.
- [ ] **Step 5: commit** — `git add -A src/cwm/continuous tests/test_instruments.py tests/test_continuous_contract.py && git commit -m "feat: n-component machinery + PATCH2D spec + per-mode blindness ..."` (trailer as always).

---

### Task 3: mechanism sweep + run

**Files:** Create `scripts/continuous_patch2d.py`; runtime `results/continuous_patch2d.json`.

**Interfaces:** consumes Task-1 env + `harness`/`mpc`; produces rows `{k1, k2, r1, r1_ci, r2, r2_ci, j_truth, j_blind, j_random, play_cost, blind_contact_rate, d40_joint, d40_p1, d40_p2, n_episodes}`.

- [ ] **Step 1: script** — mirror `scripts/continuous_pendulum.py`'s shape: grid `--k1 2 3 4` × `--k2 6 7 8` (patch centers on the axis), per cell: per-mode rarity from 600 random rollouts using `env.contact_modes` (Wilson CIs via `cwm.law.wilson_ci`), 20 paired MPC episodes truth/blind/random (`n_samples 200` default), `play_cost` normalized regret, per-mode and joint `d@40` = `play_cost·(1−r_i)^40` and `play_cost·(1−r1)^40·(1−r2)^40`. Print a row per cell; JSON with params+rows+elapsed. Full code follows the pendulum script verbatim in structure — write it out completely in the file (docstring stating the instrument, argparse with the grids/episodes/seed, the two loops, the same JSON dump pattern).
- [ ] **Step 2: smoke** — one cell (3,7), 5 episodes, 200 rollouts: pc ≈ 1, r1/r2 near prototype values. Delete smoke JSON.
- [ ] **Step 3: full run** (background, ~1-2h; nohup + log + poll for `DONE rc=0`), verify 9 rows, pc within [0.9, 1.1] on every row (report any outlier as a finding), commit script+JSON (not the log).

---

### Task 4: synthesis with per-mode identifiability + partial repair (Azure)

**Files:** Modify `scripts/continuous_danger_synthesis.py` (add `--instrument patch2d`, knob args `--k1/--k2`, per-mode summary); runtime `results/continuous_synthesis_patch2d_{mini,large}_k{K1}_{K2}.json`.

**Interfaces:** consumes Task-2's `synthesize_and_evaluate` (per-mode keys flow through untouched); INSTR_TAG `patch2d_`, KNOB `k{k1:g}_{k2:g}`.

- [ ] **Step 1: extend the script** — third `--instrument` choice building `PatchField2D(p1=(k1,0), p2=(k2,0))`; incomplete arm = both patches omitted (the pipeline's standard omission); summary partitions incomplete seeds by `sample_contains_mode_per` into {miss-both, see1-miss2, see-both} and prints per-branch counts with blindness/repair outcomes; cart/pendulum invocations byte-identical to before (filename check as in the CEM task).
- [ ] **Step 2: smoke** — `mini 1 --instrument patch2d` end-to-end on Azure (1 seed both arms), delete the JSON.
- [ ] **Step 3: runs** — background, sequential, caffeinate: `mini 20` and `large 20` at the headline cell (3,7) [partial-repair mass ~0.71], plus `mini 20 --k1 5 --k2 9` and `large 20 --k1 5 --k2 9` [far cell: miss-both mass]. Poll to completion; on network failure resume the missing cells (caffeinate lesson from the pendulum runs).
- [ ] **Step 4: verify + commit** — per cell: full arm 20/20 clean expected; incomplete partition table with per-branch expectations: miss-both → blind on both + exploited; see1-miss2 → the HEADLINE measurement: repaired patch1 + blind patch2 (partial repair), certified, exploited at patch 2; see-both → full repair or stalls (geometry-difficulty finding either way). All outcomes are findings — record exactly. Commit the 4 JSONs.

---

### Task 5: eps row + CEM row

**Files:** Modify `scripts/continuous_eps_sweep.py` (add patch2d arms), `src/cwm/continuous/cem.py` (boundary predicate), `scripts/continuous_cem.py` (patch2d rows); runtime: updated `results/continuous_eps_sweep.json` (rerun) and `results/continuous_cem.json` (rerun with the extra rows) — or new sibling JSONs `*_patch2d.json` if reruns are too slow; prefer NEW sibling JSONs to keep the committed 1D results untouched.

**Interfaces:** `cem.plan_cem(..., boundary=...)` now accepts float (current semantics, unchanged code path) OR `callable(state) -> bool`; crossing counts `boundary(s)` truthiness. `run_episode` passes it through unchanged.

- [ ] **Step 1: cem.py extension** — inside the sampling loop replace the check with:

```python
            if boundary is not None:
                hit = hit or (boundary(s) if callable(boundary)
                              else s[0] >= boundary)
```

(refactor the existing single check to this; the float path must remain semantically identical — `tests/test_cem.py` green). New patch2d predicate used by the script: `lambda s: env._inside(s[0], s[1], env.p1) or env._inside(s[0], s[1], env.p2)`.
- [ ] **Step 2: eps script** — add arms `("patch2d", "patches omitted", PatchField2D(), blind_of(P2D), True)` and the two single-omission arms (omit-p1-only truth vs blind via `blind_of_modes`) — mode arms only (no bias/bump analogues needed); write `results/continuous_eps_sweep_patch2d.json`. Run (~20 min), verify mode-arm flatness for eps ≤ 1e-2, commit.
- [ ] **Step 3: CEM script** — add a `--instrument patch2d` mode writing `results/continuous_cem_patch2d.json` with the same row schema (crossing predicate above; MPC crossing diagnostic reuses `mpc._candidates` with the predicate). Run (~30 min), verify pc≈0/no-contact/crossing-below-MPC (deviation = finding), commit.

---

### Task 6: 2D mitigation

**Files:** Modify `src/cwm/continuous/mitigation.py` (pos_dims generalization); extend `tests/test_mitigation.py` (2D tests; existing tests untouched); create `scripts/continuous_mitigation_patch2d.py`; runtime `results/continuous_mitigation_patch2d.json`.

**Interfaces:** `plan_mitigated(model, state, rng, fences, eps, ..., pos_dims=(0,))` and `run_mitigated_episode(..., pos_dims=(0,))`. Fences are TUPLES of the position components of refuted predictions (`tuple(pred[i] for i in pos_dims)`). `_crosses_fence(prev_pos, next_pos, fences, eps)` = segment-to-point distance ≤ eps in len(pos_dims)-space (for 1D this reduces to the exact current interval check — implement 1D as the CURRENT boolean expression verbatim and n-D as the geometric formula, so `tests/test_mitigation.py`'s bitwise assertions still pass). `_dist_to_nearest` = abs for 1D (current), euclidean otherwise. `MitigatedEpisode` unchanged.

- [ ] **Step 1: failing tests** — append to `tests/test_mitigation.py`:

```python
from cwm.continuous.envs import PatchField2D

P2D = PatchField2D()


def test_patch2d_bit_identity_on_truth():
    ref = harness.run_episode(P2D, P2D, "mpc", seed=3, n_samples=40)
    mit = run_mitigated_episode(P2D, P2D, seed=3, n_samples=40,
                                eps=0.5, pos_dims=(0, 1))
    assert mit.violations == 0 and mit.ret == ref.ret


def test_patch2d_mitigated_blind_escapes():
    b = harness.run_episode(P2D, blind_of(P2D), "mpc", seed=3, n_samples=40)
    m = run_mitigated_episode(P2D, blind_of(P2D), seed=3, n_samples=40,
                              eps=0.5, pos_dims=(0, 1))
    t = harness.run_episode(P2D, P2D, "mpc", seed=3, n_samples=40)
    assert b.ret < 1.0                       # pinned baseline
    assert m.violations >= 1
    assert m.ret > 10 * max(b.ret, 0.1)      # escaped and scored
    assert m.ret > 0.25 * t.ret
```

- [ ] **Step 2: verify failure** (TypeError: pos_dims), **Step 3: implement** exactly per the Interfaces block (1D fast-paths verbatim-current; nD segment-point distance: project the fence point onto the segment, clamp t∈[0,1], euclidean distance ≤ eps), **Step 4:** full `tests/test_mitigation.py` green INCLUDING the untouched 1D bitwise tests, **Step 5:** sweep script mirroring `scripts/continuous_mitigation.py` for the (k1,k2) grid {(2,6),(3,7),(4,8)} × 20 episodes with `pos_dims=(0,1)`, eps=0.5, reporting mean violations (the boundary-mapping transient measurement — EXPECT >1 unlike 1D's 1.0; report as measured) and play_cost collapse. Run, verify collapse on every row (mitigated ≪ blind), commit code+tests+script+JSON.

---

### Task 7: paper integration + push

**Files:** `docs/EXPERIMENTS.md`, `docs/paper2/main.tex`, `docs/paper2/preprint-draft.md`, regenerate `docs/paper2/main.pdf`.

- [ ] **Step 1:** extract measured numbers from ALL new JSONs to `.superpowers/sdd/patch2d-measured-numbers.md` (same pattern as prior integrations); every paper number comes from this file.
- [ ] **Step 2:** edits mirrored in tex+draft: (i) instrument subsection in the mechanism section (geometry, heading action, patch semantics, the 9-cell mechanism table with per-mode+joint danger law); (ii) synthesis section: per-mode identifiability paragraph + the PARTIAL-REPAIR result with its per-branch table (miss-both / see1-miss2 / see-both × sizes) and the repair-vs-geometry finding; (iii) one row/paragraph each in the eps and CEM discussions; (iv) mitigation section: the 2D generalization (fences inside the unreachable patch), the boundary-mapping transient vs 1D's single violation; (v) §9: DROP "one dimension, single stationary boundary" — residue: contact-rich manipulation, moving boundaries, 3+ modes, the boundary-mapping transient's scope; (vi) abstract: one clause (2D bi-modal instrument, per-mode law composition, partial repair) keeping rendered length ≤1920 chars (measure it); (vii) EXPERIMENTS.md dated sections per experiment.
- [ ] **Step 3:** `bash scripts/check_latex.sh` both papers PASS (restore paper-1 pdf if dirtied); commit; push `claude/continuous-setting-feasibility-wktp6b`.

## Notes for the executor

- The frozen instrument defaults are prototype-validated — resist all temptation to retune; degeneracies are reported to the controller.
- Azure runs: sequential + caffeinate + `python -u`; resume missing cells after network failures (see the pendulum-run precedent in `.superpowers/sdd/progress.md`).
- Every "expected" outcome that fails to materialize is a FINDING to report with measured numbers, not an error to fix.
