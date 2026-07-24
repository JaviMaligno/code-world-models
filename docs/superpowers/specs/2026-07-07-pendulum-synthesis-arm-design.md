# Design: LLM synthesis arm for the pendulum-with-stop (paper 2, second instrument)

Date: 2026-07-07
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved (brainstorming), pending implementation plan

## Problem

Paper 2 has two hybrid instruments — cart-with-wall (primary) and
pendulum-with-stop (second, nonlinear plant) — and two experiment types:

1. **Mechanism (CPU)**: rarity sweep + MPC + danger law with a hand-written
   blind model. **Already run on both instruments** (§4.1: the pendulum
   reproduces the cart's phenomenology on a nonlinear plant).
2. **LLM synthesis (§6, the paper's own result)**: the LLM synthesizes
   `step()`/`reward()` from data; measures the collapse to identifiability and
   the **repair-from-data** finding (when the mode is in the sample, the LLM
   writes the exact global rule). **Only run on the cart.**

This asymmetry — mechanism validated on two instruments, synthesis on one — is
admitted as a limitation in §9 ("the synthesis arms have run only on the cart";
"the repair finding could weaken as mode geometry gets harder to induce from
few examples"). This project closes it by running the synthesis arm on the
pendulum, turning the admitted limitation into a measured result: does
repair-from-data generalize to a nonlinear base plant (`grav·sin θ`) with an
angular clamp?

## Goal / success criteria

- The synthesis arm runs end-to-end on `PendulumStop` through the identical
  pipeline the cart uses (contract → synthesize → refine on the sample/gate →
  classify → play), driven by the same script.
- Cells run at parity with the cart's reported apparatus:
  - **Headline** `th_stop=1.4`: 20 seeds/cell, GPT-5.x mini + large.
  - **Caught** `th_stop=1.0`: 20 seeds/cell, mini + large.
  - **Cross-family** Qwen3-Coder-30B (HF router): 3 seeds, headline `th_stop=1.4`.
  - Same params as the cart: ε=1e-9 pinned-integrator gate, N=40 rollouts,
    6 MPC play-episodes/seed, max 5 refine iters.
- The cart's existing §6 results remain valid: the refactor produces a
  **byte-identical** contract prompt for the cart (golden test).
- Offline tests (FakeProvider) cover the pendulum pipeline as they do the cart.
- Paper §6 gains a second-instrument robustness paragraph; §9 drops the
  "synthesis only on the cart" limitation; EXPERIMENTS.md gains a dated
  subsection with per-seed tables. `main.tex` recompiles clean (0 overfull).

## Calibration (CPU, measured)

Per-rollout rarity → P(mode absent from 40 rollouts) = (1−r)^40:

| cell | th_stop | rarity/rollout | P(absent@40) | role |
|------|--------:|---------------:|-------------:|------|
| headline | 1.4 | 0.019 | 0.458 (~50/50) | analogue of cart x_wall=8 |
| caught | 1.0 | 0.128 | 0.004 (mode in ~all) | analogue of cart x_wall=4 |

Both match the cart analogues well (cart headline P(absent@40)≈0.60; cart caught
"wall in every sample"). `th_stop=1.4` is already tabulated in §4.1.

## Architecture (env-agnostic refactor)

New module `src/cwm/continuous/instruments.py` with an `InstrumentSpec`
abstraction encapsulating the ONLY instrument-specific parts of the contract
machinery:

- `api_text` — the contract API block with the correct integrator:
  - cart (linear): `v2 = v + (gain*a - drag*v) * dt`; `x2 = x + v2*dt`.
  - pendulum (nonlinear): `om2 = om + (gain*a - grav*sin(th) - drag*om) * dt`;
    `th2 = th + om2*dt`.
- `rules_text(env, include_mode)` — physical constants + reward + the mode rule.
  - pendulum constants add `grav`; reward sigmoids are on `th` with
    `th_left/th_right/a_left/a_right/width`; mode rule is
    `if th2 >= th_stop: return [th_stop, 0.0]`.
- `mode_probes(env)` — states that fire the mode in truth (cart: `x_wall−0.1`
  moving right under full thrust; pendulum: `th_stop−0.1` swinging up), each
  asserted to fire `contact` in the truth env.
- `mode_attr` (`"x_wall"` | `"th_stop"`) and state-variable names for the text.

`spec_for(env)` dispatches by env type (same pattern as `blind_of` in
`envs.py`). `contract.py` becomes generic and consumes the spec:

- `build_contract(env, include_mode)` → `spec.api_text + spec.rules_text(...)`.
- `wall_blindness(...)` → renamed `mode_blindness(code, env, spec)`, using
  `spec.mode_probes(env)`.
- `synthesize_and_evaluate(...)` takes the env, derives the spec internally.
- **Already generic, minimal/no change**: `collect_transitions` (uses
  `env.step/initial_state/h_episode/a_max`), `sample_contains_wall` (renamed
  `sample_contains_mode`, reads the `contact` flag), `SynthesizedModel`
  (copies `a_max`/`h_episode` from the base env).

### Non-regression requirement

The refactor MUST produce a byte-identical contract prompt for the cart so the
committed §6 results stay reproducible. Enforced by a golden test comparing
`build_contract(CartWall(x_wall=8), include_mode=True/False)` against the
captured current strings. The output-dict schema stays compatible with the
existing analysis and `make_paper2_figures.py`: the internal function is
renamed `mode_blindness`, but the **output-dict keys stay `wall_blindness`
and `sample_contains_wall`** for both instruments (a single, backward-compatible
analysis path; the cart's committed JSONs and any figure/analysis code that
reads those keys keep working unchanged). Internal helpers may be renamed to
generic names (`mode_blindness`, `sample_contains_mode`) — only the emitted
JSON keys are held stable. A code comment documents that the value is generically
"fraction of mode-region probes the model gets wrong"; 1.0 = mode-blind.

## Tests

- Extend `tests/test_continuous_contract.py`: the offline (FakeProvider)
  battery that covers the cart now also covers the pendulum —
  - full-spec artifact passes the ε=1e-9 gate to float precision through the
    sandbox;
  - stop-omitting artifact passes iff the sample missed the stop and probes
    fully mode-blind;
  - MPC on the synthesized blind artifact is exploited (pinned at the stop).
- Golden test: cart contract prompt unchanged by the refactor.
- Keep `tests/test_continuous.py` (envs/mechanism) green.

## Execution script

Generalize `scripts/continuous_danger_synthesis.py`:
- add `--instrument {cart,pendulum}` (default `cart`) and a mode-knob flag
  (`--th-stop` for the pendulum; keep `--x-wall` for the cart) — default
  behavior for the cart is unchanged;
- output filename tagged with the instrument and mode knob:
  `results/continuous_synthesis_pendulum_{tag}_thstop{N}.json`;
- the positional size / `--compat-model` cross-family switch works as today.

## Paper integration

- **§6** (`preprint-draft.md` and `main.tex`): add a second-instrument
  robustness paragraph with the pendulum cells (headline + caught, both sizes,
  + Qwen), framed as: does repair-from-data survive a nonlinear plant and an
  angular clamp? Recompile `main.pdf` (0 overfull hbox, 0 undefined refs).
- **§9**: remove the "synthesis arms have run only on the cart" limitation;
  reframe remaining scope (e.g. still one dimension, two modes).
- **EXPERIMENTS.md**: new dated subsection with per-seed tables and the
  cross-family finding, mirroring the cart's section.

## Isolation and merge

All work happens in the isolated worktree on
`claude/continuous-setting-feasibility-wktp6b`; `main`/paper 1 is untouched.
All changes are paper-2 scoped, so there is nothing to merge to `main` unless
shared code that affects paper 1 is touched (not anticipated); if it is, that
merge is done separately.

## Out of scope (YAGNI)

- Re-running the cart cells (byte-identical prompt guarantees they still hold).
- A third instrument or higher-dimensional / moving-boundary modes.
- Tuned learned-model baselines (the MLP stays a probe, per the existing draft).
- An ε-sensitivity sweep for the pendulum (the pinned-integrator contract makes
  ε=1e-9 the same story as the cart).
