# Disc-repair confound closure + square-patch ablation

**Goal:** Close the two §10-open confounds on the PatchField2D 0/76 repair
result (richer prompting, larger iteration budget), and run the fixed-topology
**square-patch ablation** that separates *boundary curvature / predicate form*
from *2D-ness* as the cause of the repair collapse. Both are paper-2 content;
paper 3's rung-1 premise cites the 0/76 (see
`docs/paper3/RESEARCH-DIRECTION.md` §1/§6 on branch
`claude/paper-tres-topology-4w813y`), which is why they run before paper 3's
synthesis arm.

**Provenance:** infrastructure + tests + CPU calibration were built and run in
the remote session of 2026-07-19 (no LLM access there); the LLM cells below are
**ready to run locally** (Azure creds in `.env`, as for every synthesis arm).

## What is already done (this commit — no LLM needed)

- `PatchField2D` gains `patch_shape: "disc" | "square"` (default `"disc"`,
  byte-identical behavior; Chebyshev-ball membership for `"square"`). The
  square's *incomplete* contract is byte-identical to the disc's (no leak);
  the *full* contract states the `max(abs(...), abs(...)) <= R` rule.
- `build_synthesis_messages` / `refine_continuous` /`synthesize_and_evaluate`
  gain `guidance` / `max_examples` / `max_failures` knobs; defaults reproduce
  every committed prompt byte-for-byte (tested).
- `scripts/continuous_danger_synthesis.py` gains `--prompt-variant
  {default,guided,region}`, `--patch-shape {disc,square}`; non-default
  variant/budget/shape are tagged into the output filename, so nothing ever
  clobbers a committed JSON.
  - `guided` = 120 examples (vs 30) + 40 failure lines shown (vs 20) +
    describe-the-region-first process guidance.
  - `region` = guided + an explicit de-biasing sentence ("the trigger region
    may have any shape in the (x, y) plane; do not assume a 1D threshold") —
    it targets the observed failure mode (dimensional reduction) without ever
    naming the true shape.
- `scripts/continuous_patch2d.py` gains `--patch-shape` (mechanism/calibration,
  CPU-only) writing `results/continuous_patch2d_square.json`.
- Tests: 268 pass, including the cart/prompt goldens and new square +
  guidance-byte-identity tests.
- CPU calibration of the square was run remotely (600 rollouts, 20 episodes
  per cell) — committed in `results/continuous_patch2d_square.json`:

  | k1  | k2  | r1     | r2     | J_truth | J_blind | play_cost |
  |-----|-----|--------|--------|---------|---------|-----------|
  | 3.0 | 7.0 | 0.1850 | 0.0083 | 18.83   | 0.00    | 1.006     |
  | 3.0 | 9.0 | 0.1850 | 0.0033 | 16.97   | 0.00    | 1.006     |
  | 5.0 | 7.0 | 0.0567 | 0.0050 | 18.29   | 0.00    | 1.006     |
  | 5.0 | 9.0 | 0.0567 | 0.0050 | 17.72   | 0.00    | 1.006     |

  vs the disc at the shared (3,7) cell: r1 0.1417 → 0.1850 (up, as forced —
  the Chebyshev ball contains the disc), r2 identical 0.0083, and the play
  mechanism is indistinguishable (J_blind 0.00, play_cost 1.006, blind
  contact rate 1.00 on both shapes). The ablation instrument is matched:
  same regime, same exploitation, only the boundary predicate differs.

## Global constraints (unchanged discipline)

- Branch `claude/continuous-setting-feasibility-wktp6b`; never touch paper 1.
- Frozen defaults; deviations are findings, never tuned away; paper numbers
  verbatim from committed JSONs.
- Synthesis protocol constants unchanged unless the arm *is* the knob
  (N=40, eps=1e-9, 6 paired play episodes; `--max-iters` is a knob HERE).
- `bash scripts/check_latex.sh` → both papers PASS at the paper task.

---

### Task 0 (local): sanity

- [ ] `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` → all pass.
- [ ] `results/continuous_patch2d_square.json` exists (remote calibration).
      If missing: `PYTHONPATH=src python scripts/continuous_patch2d.py
      --k1 3 5 --k2 7 9 --patch-shape square` (~40 min CPU).

### Task 1 (local, LLM): confound best-shot — one run decides the shape of the rest

The most favorable treatment in a single cell. If repair stays at 0 under
BOTH confounds combined, the confound is closed in one run.

- [x] ```bash
      PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 \
          --instrument patch2d --k1 3 --k2 7 --arm incomplete \
          --prompt-variant region --max-iters 15
      ```
      DONE 2026-07-19 (run locally; mini twin too). **0/40 repair, 0 gate
      passes; artifact class moved half-plane → evidence-hull (rotated
      ellipses / rectangles / micro-disc unions), none the true disc; only
      4/40 condition on the landing variable.** Confound CLOSED — analysis
      in EXPERIMENTS.md; ablation pair not needed (nothing repaired).
      → `results/continuous_synthesis_patch2d_large_k3_7_pv-region_it15.json`
      (~1+≤15 calls/seed; play eval dominates runtime, ~1–2 min/seed CPU).
- [ ] Read the per-seed lines: the question is ONLY about mode-containing
      seeds (`sample_contains_mode_per` has a true entry): does any such seed
      end with that patch's `mode_blindness` at 0.0 behind a passed gate,
      via a *correct-shape* rule (inspect `code` — a disc, not a half-plane)?

**Decision:**
- **0/N again** → run the mini twin for family coverage:
  ```bash
  PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 20 \
      --instrument patch2d --k1 3 --k2 7 --arm incomplete \
      --prompt-variant region --max-iters 15
  ```
  then → Task 3 (paper): the confound is CLOSED — §10's "whether richer
  prompting, larger iteration budgets ... restore repair is open" becomes a
  measured negative (cite both JSONs). The 0/76 stands unconditioned.
- **any repair** → the 0/76 was protocol-scoped, not model-scoped. Attribute
  the factor with the ablation pair (same cell, 20 seeds, large):
  - [ ] `--prompt-variant region` (budget stays 5) → prompting alone?
  - [ ] `--prompt-variant default --max-iters 15` → budget alone?
  then → Task 3: §7.1's mechanism claim gets scoped to the original protocol
  and the repair-restoring treatment is reported alongside (this is a
  *finding*, not a bug — record it as the dose/guidance analogue of paper 1's
  supervision-form axis).

### Task 2 (local, LLM): square-patch ablation

Control first (translation of the max/abs clause should be clean, like every
full arm), then the ablation cells.

- [ ] ```bash
      PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 \
          --instrument patch2d --k1 3 --k2 7 --patch-shape square
      ```
      (`--arm both`: full control + incomplete in one run)
      → `results/continuous_synthesis_patch2dsq_large_k3_7.json`
- [ ] Mini twin: same command with `mini 20`.
- [ ] (Optional, if the k3_7 result is clean and cheap enough) second cell
      `--k1 5 --k2 9`, both sizes, mirroring the disc's two-cell design.

**Reading it:** the full arm must be 20/20 clean (else the pinned-integrator
premise broke on max/abs — a finding in itself, stop and inspect). On the
incomplete arm, condition on mode-containing seeds and inspect artifact shape:
- **repair recovers** (exact `max(abs(...))` rules appear) → the collapse axis
  is **boundary curvature / quadratic predicate form**, not 2D-ness: a 2D
  region with flat edges IS repairable. §7.1's "reduces the disc to a
  half-plane" mechanism gets its cause pinned; paper 3's ladder gains a
  calibrated curvature rung distinct from the topology rungs.
- **still ~0 repair** → 2D-ness / conjunction complexity is the axis (a
  square needs the same two-coordinate conjunction as a disc): §7.1's
  dimensional-reduction story strengthens; the curvature explanation is
  falsified.
Either branch also wants the same code-inspection classes as §7.1
(blind / half-plane / wrong-shape / correct).

### Task 3 (local): fold into paper 2

- [ ] EXPERIMENTS.md entry: date, commands, per-cell tables (mode-present
      conditional rates), artifact classes, calibration table for the square
      (r1/r2 vs disc).
- [ ] `docs/paper2/main.tex` + `preprint-draft.md`:
      - §7.1: add the confound-closure sentence (or the scoping correction if
        repair appeared) and the square-ablation finding with its axis
        attribution.
      - §10: replace "whether richer prompting, larger iteration budgets, or
        other geometries restore repair is open" with what is now measured;
        keep "other geometries" only for what remains untested (annulus →
        paper 3, cited as future work).
      - Abstract/§1 only if the square result *changes* the geometry-dependence
        wording (repair-recovers ⇒ "curvature-dependent" is more precise than
        "geometry-dependent").
- [ ] `bash scripts/check_latex.sh` → PASS, regenerate PDF, commit JSONs +
      paper together.
- [ ] Ping paper 3: update `docs/paper3/RESEARCH-DIRECTION.md` §1/§6 (rung-1
      datum + the "0/76 confounds" risk becomes resolved either way).

## Cost/runtime envelope (local)

Per 20-seed incomplete cell: 20 × (1 synthesis + ≤5 or ≤15 refines) LLM calls,
prompts ~1–2k tokens (region variant ~4k with 120 examples); runtime dominated
by CPU play eval (~30–40 min/cell). Task 1 + Task 2 (both sizes, one cell
each) ≈ 6 runs ≈ 3–4 h wall, LLM cost in the same range as the original
patch2d arm.
