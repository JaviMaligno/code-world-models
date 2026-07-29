# Paper 2 — reproducibility FACTS (review points #18, #19)

Not appendix prose. This is the fact base an appendix can be written from: every
number below is read out of `results/repro_manifest.json`, which is generated
(never hand-typed) by the script archived at the end of this file. Regenerate
with

```
PYTHONPATH=src .venv/bin/python scripts/repro_manifest.py
```

Snapshot: git `9e4988c` (`2026-07-27 00:14:08 +0100`), branch
`paper2-major-revision`, working tree dirty (concurrent revision work in the
same checkout). Manifest generated 2026-07-27. **Where a number below could
move, the JSON key that holds it is named — quote the key, not this file.**

---

## 1. Interpreter, platform, hardware

| fact | value | manifest key |
|---|---|---|
| Python | `3.12.8 (v3.12.8:2dc476bcb91, Dec  3 2024, 14:43:20) [Clang 13.0.0 (clang-1300.0.29.30)]` | `platform.python_version` |
| implementation | CPython | `platform.python_implementation` |
| interpreter path | `<repo>/.venv/bin/python` | `platform.python_executable` |
| `pyproject` floor | `requires-python = ">=3.11"` | `dependencies.pyproject_requires_python` |
| platform string | `macOS-15.7.7-x86_64-i386-64bit` | `platform.platform` |
| OS | macOS 15.7.7, build `24G720` | `platform.sw_vers` |
| kernel | `Darwin 24.6.0 … RELEASE_X86_64 x86_64` | `platform.uname` |
| CPU | Intel Core i9-9880H @ 2.30 GHz, 16 logical cores | `platform.cpu_brand`, `platform.hw_ncpu` |
| machine | MacBookPro16,1, 17,179,869,184 B RAM (16 GiB) | `platform.hw_model`, `platform.hw_memsize_bytes` |

**Does any result depend on the machine?** Only wall-clock. Every CPU result is
pure-Python/`numpy` float64 with explicitly seeded `random.Random` / numpy
streams, single-threaded, no GPU, no BLAS-order-dependent reduction in the
sweeps, so bit-identical replay is expected on any IEEE-754 host at the same
CPython minor version. The quantities most exposed to a different `libm` are the
ones the paper prints to twelve digits (`J_truth = 17.757356407381`,
`17.772246981024`, `20.08…`) and to fifteen (`1e-15` linear-fit residuals);
those are the first to re-check on another platform. Long text in
`platform.hardware_dependence_of_results`.

*Honest gap:* the results were accumulated 2026-07-06 → 2026-07-26 on this one
machine. No second platform has ever run the sweeps, so the bit-identity claim
above is an argument from the code, not a measurement. A one-line CI job
(`audit_paper2_numbers.py` on Linux/arm64 after re-running two cheap sweeps)
would settle it and does not exist.

## 2. Dependencies — no lockfile exists

`pyproject.toml` declares three runtime dependencies and one dev extra, **all
with lower bounds only** (`dependencies.declared_bounds_are_lower_only = true`):

```
openai>=1.40.0   python-dotenv>=1.0.0   numpy>=1.24        (dev: pytest>=8.0.0)
```

Lockfile probe (`dependencies.lockfile_present`) — every candidate absent:
`uv.lock`, `poetry.lock`, `Pipfile.lock`, `requirements.txt`,
`requirements.lock`, `conda-lock.yml`, `environment.yml`, `pdm.lock`.
`dependencies.any_lockfile = false`.

Versions actually used (`dependencies.installed_versions_of_declared`):

| package | installed |
|---|---|
| numpy | 2.5.1 |
| openai | 2.43.0 |
| python-dotenv | 1.2.2 |
| pytest | 9.1.1 |

Deterministic pinned list written to **`docs/paper2/requirements-frozen.txt`**
(24 distributions, `pip freeze` of the repo `.venv`;
`dependencies.frozen_package_count`). Note `numpy 2.5.1` is two majors above the
declared floor `>=1.24`: `pip install -e .` today does **not** reproduce the
environment the results came from.

*Honest gaps.* (a) `requirements-frozen.txt` has no hashes and no resolver
metadata — it closes the version gap, not the integrity gap.
(b) `dependencies.release_tag_present = false`: the repository carries **no git
tag**, so nothing citable identifies "the code that produced Table 3". A release
tag (and ideally a Zenodo DOI over the tag) is still required.

## 3. MANIFEST — every table and figure → its backing JSON

Derived from `scripts/audit_paper2_numbers.py`, which already re-derives **628**
paper values from `results/` (`audit_coverage.audit_checks_executed = 628`,
`audit_failures = []`, exit 0 at this snapshot). That count is a moving target —
it was **621** at git `9e4988c` and rises as concurrent revision work adds
assertions — so quote the key, not the integer. The derivation is done twice and
cross-checked, and the cross-check is load-bearing: a *static* parse of the
audit's `# --- … ---` sections collects the literal `load(…)` / `synth_cells(…)`
/ `glob(…)` / `"*.json"` arguments per section, while a *dynamic* pass execs the
audit with `pathlib.Path.read_text` spied on and records every file it really
opens. `audit_coverage.static_vs_dynamic_ok = true`; the first run of the
generator had it **false** (the static parse missed the 21 files reached through
the `synth_cells` wrapper and the `continuous_synthesis_*.json` glob), which is
what the check is for.

Three coverage tiers are distinguished, because collapsing them would turn this
manifest into a false claim:

* **cell_parsed** — the audit parses the `tabular` out of `main.tex` and compares
  every cell at printed precision.
* **claims_only** — the audit does not parse it, but asserts values quoted from
  it (or, for figures, renders the same JSON its table is parsed from).
* **unaudited** — nothing in the audit refers to it.

`audit_coverage.coverage_counts = {cell_parsed: 9, claims_only: 5, unaudited: 1}`
over 15 objects.

Line numbers in the table are those of the **committed** `main.tex` at
`9e4988c` (`git show HEAD:docs/paper2/main.tex`, 998 lines). The manifest's own
`manifest[].tex_line` is read from the **working tree**, which concurrent
revision work has since grown to 1111 lines — the two disagree by construction,
and the labels, not the line numbers, are the stable key.

| # | object | tex line (at `9e4988c`) | backing `results/…json` | producing script | coverage |
|---|---|---|---|---|---|
| 1 | `tab:epsstar` | 200 | `eps_invariance_threshold.json` | `eps_invariance_threshold.py` | claims_only |
| 2 | `tab:danger` | 489 | `continuous_reach.json` | `continuous_reach.py` | cell_parsed |
| 3 | `fig:threshold` (`danger_threshold.pdf`) | 496 | `continuous_reach.json` | `continuous_reach.py` → `make_paper2_figures.py` | claims_only |
| 4 | `fig:reach` (`reach_mechanism.pdf`) | 503 | `continuous_reach.json` | idem | claims_only |
| 5 | `tab:pendulum` | 538 | `continuous_pendulum.json` | `continuous_pendulum.py` | cell_parsed |
| 6 | `tab:patch2d` | 572 | `continuous_patch2d.json` | `continuous_patch2d.py` | cell_parsed |
| 7 | `tab:cem` | 601 | `continuous_cem.json` (+ cross-source `continuous_reach`, `continuous_pendulum`) | `continuous_cem.py` | cell_parsed |
| 8 | `tab:axes` | 631 | `continuous_axes.json` | `continuous_axes.py` | cell_parsed |
| 9 | `fig:axes` (`axis_separation.pdf`) | 638 | `continuous_axes.json` | idem → `make_paper2_figures.py` | claims_only |
| 10 | `tab:eps-sweep` | 659 | `continuous_eps_sweep.json` | `continuous_eps_sweep.py` | cell_parsed |
| 11 | `tab:mitigation` | 694 | `continuous_mitigation.json` | `continuous_mitigation.py` | cell_parsed |
| 12 | `tab:patch2d-mitigation` | 756 | `continuous_mitigation_patch2d.json` | `continuous_mitigation_patch2d.py` | cell_parsed |
| 13 | **`tab:pendulum-synthesis`** | 804 | **none — see gap G1** | `continuous_danger_synthesis.py` | **unaudited** |
| 14 | `tab:smooth` | 847 | `continuous_smooth_probe.json` | `continuous_smooth_probe.py` | cell_parsed |
| 15 | `fig:smooth` (`smooth_localization.pdf`) | 854 | `continuous_smooth_probe.json` | idem → `make_paper2_figures.py` | claims_only |

Machine-readable form: `manifest[]` (one row per object, with
`audit_sections_parsing_cells`, `audit_sections_quoting_values`,
`audit_agree_call_sites`, `audit_claim_call_sites`). The audit's 39 sections and
what each reads: `audit_coverage.sections[]`. Figures:
`figures.per_figure_backing_json` — each of the four PDFs is attributed to
exactly one JSON, and `make_paper2_figures.py` runs no experiment, so every
figure inherits its table's provenance.

Beyond tables and figures, the audit's remaining sections cover propositions,
certificates and counted prose claims. `audit_coverage.results_json_read_dynamic`
is the complete list of files it opens: **53** at this snapshot, of which 12 back
the tables and figures above.

### Manifest gaps (the review asks for these explicitly)

* **G1 — `tab:pendulum-synthesis` (main.tex 789–807) is parsed by nothing.**
  Its per-row cells (`9 → 9 (pc 0.995)`, `11 → 11 (0)`, `20 → 20`, and the whole
  Qwen row `3/3`, `1 → 1 (pc 0.995)`, `2 → 0 (2 stalled @0.9997)`) are not
  compared to any JSON. The *pooled* claims the table feeds **are** checked
  (`pendulum repair 62/62`, `pooled repair 82/82`, the 109/111 all-cells count),
  but `grep -c "0.995\|0.9997" scripts/audit_paper2_numbers.py` returns **0**:
  no assertion touches the mode-absent play_cost the table prints, and the Qwen
  pendulum row is uncovered end to end. Fix = one `tabular_rows("tab:pendulum-synthesis")`
  block, ~15 lines.
* **G2 — four paper-2 evidence files the audit never opens**
  (`audit_coverage.paper2_results_json_not_read_by_audit`), each written by a
  script `main.tex` names:
  `continuous_cem_patch2d.json` (PatchField2D CEM rows, §5 prose),
  `continuous_eps_sweep_patch2d.json` (PatchField2D ε rows, §6 prose),
  `continuous_patch2d_square.json` (square-patch CPU calibration behind
  Ablation 2), `continuous_claude_relay_patch2d_k3_7.json` (the 2D Claude relay
  ledger). Every number those back is prose-only and outside those 628 checks.
* **G3 — figures are never checked, only their tables.** No assertion compares
  a plotted series to the JSON; the guarantee is indirect (same JSON, no
  transformation but `play_cost·(1-r)^N`, itself checked in `tab:danger`).
* **G4 — `results/shape2d_calibration.json`** (2026-07-19 Phase-A/B calibration)
  is committed but referenced by neither `main.tex` nor the audit.

## 4. Total runtime

37 of the 101 `results/*.json` present at generation record their own
`elapsed_s`
(`runtime.n_files_with_elapsed_s`, `runtime.n_results_json_total`). Per-file
values: `runtime.per_results_file_elapsed_s`.

| campaign (`runtime.by_campaign`) | s | min | files |
|---|---|---|---|
| LLM synthesis, PatchField2D | 8208.6 | 136.8 | 8 |
| LLM synthesis, 1D cart | 6719.5 | 112.0 | 5 |
| LLM synthesis, pendulum | 6703.0 | 111.7 | 6 |
| 1D mechanism sweeps (CPU) | 5501.3 | 91.7 | 7 |
| ε-sensitivity sweeps (CPU) | 4284.0 | 71.4 | 2 |
| second planner family, CEM (CPU) | 4115.9 | 68.6 | 2 |
| mitigation sweeps (CPU) | 2602.8 | 43.4 | 2 |
| PatchField2D mechanism (CPU) | 702.2 | 11.7 | 2 |

Subtotals (`runtime.subtotals`): CPU sweeps **4.78 h**, LLM synthesis **6.01 h**,
**paper-2 named campaigns 10.79 h**. A further `unclassified_s` bucket
(`cem_crossing_bound`, `heldout_gate_audit`, `play_cost_intervals`) belongs to
the in-progress revision running concurrently in this tree, not to the submitted
paper — hence quote `paper2_named_campaigns_h`, not `total_recorded_elapsed_h`.

**`elapsed_s` is a lower bound on what the paper cost.** It is one run of the
script that wrote the file, and therefore excludes: the 5-seed cells later
overwritten at 20 seeds, the square-ablation resume passes, every superseded
sweep before the 2026-07-25 sample-size raises, and every failed/retried LLM
call (`runtime.note`).

### Runtimes that exist only as `main.tex` estimates — unverified

`runtime.scripts_named_in_tex_verbatim` lists all 24 scripts named in the
reproducibility verbatim. Seven carry a `~N min` annotation and produce a JSON
with **no** `elapsed_s`, so their runtime is an **unverified estimate**:

| script | `main.tex` estimate | recorded? |
|---|---|---|
| `scripts/patch2d_dependence_50k.py` | ~40 min | no (`own_json_records_elapsed_s = false`) |
| `scripts/gate_partition_certificate.py` | ~25 min | no |
| `scripts/fence_separation_census.py` | ~12 min | no |
| `scripts/eps_flatness_rate.py` | ~6 min | no |
| `scripts/gate_partition_validation.py` | ~4 min | no |
| `scripts/phantom_targeting_probability.py` | ~4 min | no |
| `scripts/play_cost_proved_bounds.py` | ~3 min | no |

Plus `sample_stream_census.py` ("instant"), `make_paper2_figures.py`,
`audit_paper2_numbers.py`, `continuous_claude_step.py`, `claude_relay_ledger.py`
— no annotation and no recorded time. Sum of the seven annotated estimates =
94 min, entirely unverified; adding an `elapsed_s` to those seven scripts is the
cheap fix.

### Four `main.tex` estimates are contradicted by the recorded times

`runtime.tex_estimates_contradicted_by_recorded_elapsed_s` — the annotations
predate the 2026-07-25 censored-zero fix, which raised rarity rollouts (cart and
pendulum 3000→30,000, axes 2000→20,000) without updating them:

| script | tex says | JSON records | ratio |
|---|---|---|---|
| `continuous_pendulum.py` | ~2 min (120 s) | 591.0 s | **4.92×** |
| `continuous_reach.py` | ~2.5 min (150 s) | 641.8 s | **4.28×** |
| `continuous_axes.py` | ~3 min (180 s) | 716.0 s | **3.98×** |
| `continuous_cem.py` | ~29 min (1740 s) | 3278.9 s | **1.88×** |

(`continuous_smooth_probe.py` is the one that agrees: ~11 s vs 11.1 s.)

## 5. LLM cost — call counts are exact, tokens were never recorded

`llm_cost.token_usage_recorded_in_paper2_artifacts = **false**`. The providers do
capture tokens (`src/cwm/llm/provider.py::Usage`; `azure_openai.py` *raises* if
Azure omits usage) and `contract.refine_continuous` keeps them in
`RefineResult.usages`, but `contract.synthesize_and_evaluate` never copies them
into the emitted cell, so **no paper-2 artifact carries a token count**
(`llm_cost.why_not`). The only JSONs in the repo with dollars are paper 1's.

Exact call counts, derived per cell as `1 + refine_iterations`
(`llm_cost.per_file`, `llm_cost.by_campaign`):

| campaign | cells | LLM calls |
|---|---|---|
| LLM synthesis, PatchField2D | 283 | 1463 |
| LLM synthesis, pendulum | 206 | 293 |
| LLM synthesis, 1D cart | 136 | 203 |
| **total API arms** | **625** | **1959** |
| Claude agent-relay (subscription, not API) | — | 20 relay rounds |

The two guided-prompt files dominate: `continuous_synthesis_patch2d_{mini,large}_k3_7_pv-region_it15.json`
are 320 calls each (20 cells × 16 = 1 + 15 refine iterations, the budget-3×
treatment), i.e. 640 of the 1959.

**So cost must be stated as a range, not a point.** The design spec's own pre-run
estimate (2026-07-07, `docs/specs/2026-07-06-…md`, "Runbook — LLM arms") was
"~2–7 LLM calls per seed (1 synthesis + refinement iterations), 1–2k prompt
tokens each"; the measured 1959 calls at 1–2k prompt tokens plus completions of
comparable size brackets the API arms at roughly 10⁶–10⁷ total tokens — single
to low-double-digit US dollars at 2026 GPT-5.x-class prices. The only *measured*
dollar figures in-repo are paper 1's `cost_usd_total` fields, totalling
**\$3.73** across 20 files (`llm_cost.paper1_cost_usd_anchors`,
`paper1_cost_usd_total`) — a different campaign, useful only as an order-of-
magnitude anchor. An exact figure has to come from the Azure billing export for
the window 2026-07-07 → 2026-07-25 (`llm_cost.cost_statement_for_the_appendix`).

*Also honest:* per-cell prompts are reconstructible offline and deterministically
(`collect_transitions` + `build_contract` + `build_synthesis_messages` are pure
functions of instrument, knob, seed and `n_rollouts`), so a real token count for
the *first* call of every cell is obtainable with zero API spend. Completion
tokens for superseded refine iterations are gone. Nobody has done this.

## 6. Licence status — missing

`licence.any_licence_file = false`: no `LICENSE`, `LICENSE.md`, `LICENSE.txt`,
`LICENCE`, `COPYING` or `NOTICE`. `licence.pyproject_declares_license = false`
and `pyproject_classifiers = []`. `README.md` does not mention a licence.

Consequence, stated plainly: the code, the ~100 result artifacts (including every
synthesized program the paper quotes) and the paper source are
all-rights-reserved by default. A reviewer told to reproduce this has no licence
to redistribute anything, and the arXiv bundle ships without terms. Fix before
submission: a code licence (MIT/Apache-2.0), a data/paper licence (CC-BY-4.0),
`[project].license` in `pyproject.toml`, plus the release tag from §2.

## 7. Credentials-free config template

Written to **`docs/paper2/env.example`** — names only, no secrets. Every variable
is one the scripts read by name from `os.environ`
(`env_config.variables` maps each to its exact `file:line` sites):

| variable | read at (excerpt) |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | `src/cwm/run_experiment.py:51`, `src/cwm/run_gap.py:109`, `scripts/continuous_danger_synthesis.py:283`, +8 more |
| `AZURE_OPENAI_API_KEY` | same sites |
| `AZURE_OPENAI_API_VERSION` | same sites |
| `AZURE_DEPLOYMENT_LARGE` | `scripts/continuous_danger_synthesis.py:279` et al. |
| `AZURE_DEPLOYMENT_MINI` | idem |
| `HF_TOKEN` | `scripts/continuous_danger_synthesis.py:276`, `scripts/crossfamily_probe.py:82` |

`AZURE_DEPLOYMENT_NANO` is in the template for completeness; only paper-1 arms
use it. `env_config.load_dotenv_modules` lists the 16 modules that call
`load_dotenv`; of those, only `scripts/continuous_danger_synthesis.py` is a
paper-2 arm. **Credentials are
needed only to regenerate the synthesis JSONs.** Everything else reproduces
credentials-free from the committed artifacts: the ten CPU-sweep tables and four
figures re-run end to end, and the whole numeric audit — including every check over
the synthesis cells — reads only `results/`
(`env_config.cpu_only_reproduction_needs_no_credentials`). The one table that
cannot be regenerated without an Azure key is `tab:pendulum-synthesis`, and by G1
it is also the one the audit does not check.

Two defects in the *existing* root `.env.example`
(`env_config.existing_repo_root_template`): it omits `HF_TOKEN`
(`lists_HF_TOKEN = false`) even though the Qwen arms require it, and it pins
`AZURE_OPENAI_API_VERSION=2024-12-01-preview` while the paper's "Exact models"
footnote (main.tex 762 at `9e4988c`) states the runs used `2025-04-01-preview`
(`api_version_matches_paper = false`). One of the two is wrong; the JSONs do not
record the API version, so **which** cannot be settled from the artifacts.

---

## Appendix — generator source

Committed for provenance because `scripts/` is owned by other work in this
revision. Save verbatim as `scripts/repro_manifest.py` (no edits needed) and it
regenerates `results/repro_manifest.json`,
`docs/paper2/requirements-frozen.txt` and `docs/paper2/env.example`. Writes are
atomic (`tempfile` + `os.replace`); the run takes ~10 s, all of it the audit
re-exec.

Save the block below verbatim as `scripts/repro_manifest.py` (it needs no
edits; it locates the repo from `__file__` and falls back to the absolute
path if run from elsewhere). sha256 of the source as run for this snapshot:
`e9eeb35b6c5c7fdb5b2974956549c3ee5e5e73ecf43bc98007ab33e134b82fc2`

```python
"""Gather the reproducibility FACTS for paper 2 into results/repro_manifest.json.

Review points #18/#19 ask for an appendix that a stranger can act on: exact
interpreter and platform, a pinned dependency set, a table/figure -> JSON
manifest, total runtime, LLM cost, licence status and a credentials-free config
template. Every number this emits is READ from the repo (results/*.json,
pyproject.toml, docs/paper2/main.tex, scripts/audit_paper2_numbers.py) or from
the machine itself (sysctl/uname/pip) -- nothing is hand-typed.

The table/figure manifest is DERIVED from scripts/audit_paper2_numbers.py rather
than restated: that script already re-derives every table cell from results/, so
whatever it reads per section IS the backing evidence. Two independent routes are
used and cross-checked, which is the non-vacuous part:

  (static)  parse the audit source into its `# --- ... ---` sections and collect
            the literal load("X") / tabular_rows("Y") arguments per section;
  (dynamic) exec the audit with pathlib.Path.read_text spied on, recording every
            file it actually opens.

If the static parse missed a JSON the audit really reads, the cross-check fails
loudly (manifest["audit_coverage"]["static_vs_dynamic_ok"] is False and the
offending names are listed). Also emits, as gaps, every table/figure label in
main.tex that no audit section mentions.

Writes:
  results/repro_manifest.json
  docs/paper2/requirements-frozen.txt   (pip freeze; there is no lockfile)
  docs/paper2/env.example               (names only, no values)

Usage: PYTHONPATH=src python scripts/repro_manifest.py
"""
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
if not (REPO / "docs" / "paper2" / "main.tex").exists():          # scratchpad run
    REPO = pathlib.Path("/Users/javieraguilarmartin1/Documents/repos/code-world-models")
RESULTS = REPO / "results"
TEX = REPO / "docs" / "paper2" / "main.tex"
AUDIT = REPO / "scripts" / "audit_paper2_numbers.py"


def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=120).stdout.strip()
    except Exception as e:                                    # pragma: no cover
        return f"<unavailable: {e!r}>"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    os.replace(tmp, path)


# --------------------------------------------------------------- platform ----
def platform_facts():
    return {
        "python_version": sys.version,
        "python_version_tuple": list(sys.version_info[:3]),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable.replace(str(REPO), "<repo>"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "uname": sh("uname", "-a"),
        "sw_vers": sh("sw_vers"),
        "cpu_brand": sh("sysctl", "-n", "machdep.cpu.brand_string"),
        "hw_model": sh("sysctl", "-n", "hw.model"),
        "hw_ncpu": sh("sysctl", "-n", "hw.ncpu"),
        "hw_memsize_bytes": sh("sysctl", "-n", "hw.memsize"),
        "float_repr_style": sys.float_repr_style,
        "maxsize": sys.maxsize,
        "byteorder": sys.byteorder,
        "hardware_dependence_of_results": (
            "All CPU results are pure-Python/numpy float64 arithmetic with "
            "explicitly seeded random.Random / numpy Generator streams; no "
            "threading, no GPU, no BLAS-dependent reduction order in the "
            "sweeps. Bit-identical replay is expected on any IEEE-754 x86-64 "
            "or arm64 host with the same CPython minor version; the numbers "
            "quoted to twelve digits (J_truth) are the ones most exposed to a "
            "different libm, and are the ones to re-check first on another "
            "platform. Only WALL-CLOCK figures are hardware-dependent."),
    }


# ----------------------------------------------------------- dependencies ----
LOCKFILE_CANDIDATES = ["uv.lock", "poetry.lock", "Pipfile.lock",
                       "requirements.txt", "requirements.lock",
                       "conda-lock.yml", "environment.yml", "pdm.lock"]


def dependency_facts():
    py = (REPO / "pyproject.toml").read_text()
    deps = re.search(r"^dependencies\s*=\s*\[(.*?)\]", py,
                     re.S | re.M).group(1)
    declared = re.findall(r'"([^"]+)"', deps)
    dev = re.findall(r'"([^"]+)"',
                     re.search(r"dev\s*=\s*\[(.*?)\]", py, re.S).group(1))
    freeze = sh(sys.executable, "-m", "pip", "freeze")
    frozen_path = REPO / "docs" / "paper2" / "requirements-frozen.txt"
    header = (
        "# Pinned environment for docs/paper2 (review points #18/#19).\n"
        f"# Produced by `{pathlib.Path(sys.executable).name} -m pip freeze` on "
        f"{time.strftime('%Y-%m-%d', time.gmtime())} (UTC) inside the repo's\n"
        "# .venv, on the machine described in results/repro_manifest.json.\n"
        "# THIS IS NOT A LOCKFILE: it has no hashes and no resolver metadata,\n"
        "# and pyproject.toml declares only lower bounds. A release tag of the\n"
        "# repository is still required to make the artifact set citable.\n")
    atomic_write(frozen_path, header + freeze + "\n")
    return {
        "pyproject_requires_python": re.search(
            r'requires-python\s*=\s*"([^"]+)"', py).group(1),
        "declared_runtime_dependencies": declared,
        "declared_dev_dependencies": dev,
        "declared_bounds_are_lower_only": all(
            (">=" in d and "==" not in d) for d in declared),
        "lockfile_present": {c: (REPO / c).exists()
                             for c in LOCKFILE_CANDIDATES},
        "any_lockfile": any((REPO / c).exists() for c in LOCKFILE_CANDIDATES),
        "frozen_list_written_to": "docs/paper2/requirements-frozen.txt",
        "frozen_package_count": len([l for l in freeze.splitlines()
                                     if l and not l.startswith("#")]),
        "installed_versions_of_declared": {
            name: sh(sys.executable, "-c",
                     f"import importlib.metadata as m;print(m.version({name!r}))")
            for name in sorted({re.split(r"[<>=!\[]", d)[0].strip()
                                for d in declared + dev})},
        "release_tag_present": bool(sh("git", "-C", str(REPO), "tag").strip()),
        "gap": ("No lockfile of any kind exists and pyproject declares only "
                "lower bounds, so `pip install -e .` today resolves to newer "
                "versions than the ones the results were produced with. "
                "docs/paper2/requirements-frozen.txt closes the version gap "
                "but not the integrity gap (no hashes). A git tag / Zenodo DOI "
                "for the artifact set is still missing."),
    }


# ------------------------------------------------- audit-derived manifest ----
SECTION_RE = re.compile(r"^#\s-{2,}\s*(.*?)\s*-*\s*$", re.M)


def audit_sections():
    """(title, body) for each `# --- ... ---` section of the audit script."""
    src = AUDIT.read_text()
    marks = [(m.start(), m.group(1).strip()) for m in SECTION_RE.finditer(src)]
    out = []
    for i, (pos, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        out.append((title, src[pos:end]))
    return out


def static_audit_map():
    """label/section -> results JSONs it reads, from the audit source.

    Three routes into results/ exist in the audit and all three must be parsed,
    or the static/dynamic cross-check fails (it did, first time round, on the
    synth_cells() wrapper and the glob): the load()/synth_cells() helpers, a
    bare "<name>.json" string literal joined onto _REPO/"results", and a
    glob pattern, which is expanded against the directory here.
    """
    sections = []
    for title, body in audit_sections():
        loads = set(re.findall(r'(?:load|synth_cells)\(\s*"([^"]+)"\s*\)', body))
        loads |= {n[:-5] for n in re.findall(r'"([A-Za-z0-9_.\-]+\.json)"', body)}
        labels = sorted(set(re.findall(r'tabular_rows\(\s*"([^"]+)"\s*\)', body)))
        globs = sorted(set(re.findall(r'glob\(\s*"([^"]+)"\s*\)', body)))
        for pat in globs:
            if pat.endswith(".json"):
                loads |= {p.stem for p in RESULTS.glob(pat)}
        loads = sorted(loads)
        agree_sites = len(re.findall(r"\bagree\(", body))
        claim_sites = len(re.findall(r"\bclaim\(", body))
        sections.append({
            "audit_section": title,
            "tex_labels_parsed": labels,
            "results_json_read": loads,
            "results_globs": globs,
            "agree_call_sites": agree_sites,
            "claim_call_sites": claim_sites,
        })
    # loads that appear before the first section marker (module preamble)
    return sections


def dynamic_audit_files():
    """Every file the audit actually opens, by spying on Path.read_text."""
    seen = []
    orig = pathlib.Path.read_text

    def spy(self, *a, **k):
        seen.append(str(self))
        return orig(self, *a, **k)

    pathlib.Path.read_text = spy
    ns = {"__name__": "__main__", "__file__": str(AUDIT)}
    try:
        exec(compile(AUDIT.read_text(), str(AUDIT), "exec"), ns)  # noqa: S102
        exit_code = 0
    except SystemExit as e:
        exit_code = int(e.code or 0)
    finally:
        pathlib.Path.read_text = orig
    checks = ns.get("CHECKS", [None])[0]
    fails = ns.get("FAILS", [])
    return {
        "files_opened": sorted({p for p in seen}),
        "results_json_opened": sorted({pathlib.Path(p).stem for p in seen
                                       if "/results/" in p and p.endswith(".json")}),
        "audit_checks_executed": checks,
        "audit_failures": fails,
        "audit_exit_code": exit_code,
    }


def tex_objects():
    """Every table and figure of main.tex with its label and caption stub."""
    tex = TEX.read_text()
    lines = tex.splitlines()
    out = []
    for env in ("table", "figure"):
        for m in re.finditer(r"\\begin\{" + env + r"\}", tex):
            end = tex.index("\\end{" + env + "}", m.start())
            body = tex[m.start():end]
            lab = re.search(r"\\label\{([^}]+)\}", body)
            cap = re.search(r"\\caption\{(.{0,120})", body, re.S)
            gfx = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", body)
            out.append({
                "kind": env,
                "label": lab.group(1) if lab else None,
                "tex_line": tex[:m.start()].count("\n") + 1,
                "caption_stub": re.sub(r"\s+", " ", cap.group(1)).strip()
                                if cap else None,
                "graphics": gfx,
            })
    return sorted(out, key=lambda d: d["tex_line"]), lines


def figure_sources():
    """figure basename -> backing JSONs, from scripts/make_paper2_figures.py.

    The script binds one variable per JSON at module level and then emits each
    figure with `save(fig, "<basename>")`, so the JSONs behind a figure are the
    bound variables that appear in the text between the previous save() and this
    one. Attribution is therefore per figure, not per module.
    """
    src = (REPO / "scripts" / "make_paper2_figures.py").read_text()
    var2json = dict(re.findall(r'(\w+)\s*=\s*load\(\s*"([^"]+)\.json"\s*\)', src))
    saves = list(re.finditer(r'save\(\s*\w+\s*,\s*"([^"]+)"', src))
    # the module preamble binds every JSON, so the first figure's block must
    # start after the last binding or it inherits all of them
    last_bind = max((m.end() for m in
                     re.finditer(r'\w+\s*=\s*load\(\s*"[^"]+\.json"\s*\)', src)),
                    default=0)
    per_fig, prev = {}, last_bind
    for m in saves:
        block = src[prev:m.end()]
        per_fig[m.group(1)] = sorted({j for v, j in var2json.items()
                                      if re.search(r"\b" + re.escape(v) + r"\b",
                                                   block)})
        prev = m.end()
    return {
        "generator": "scripts/make_paper2_figures.py",
        "module_level_json": sorted(set(var2json.values())),
        "per_figure_backing_json": per_fig,
        "note": ("make_paper2_figures.py renders committed JSONs only -- it "
                 "runs no experiment, so every figure inherits the provenance "
                 "and the audit coverage of its table."),
    }


def script_of(name):
    p = RESULTS / f"{name}.json"
    if not p.exists():
        return None
    try:
        b = json.loads(p.read_text())
    except Exception:
        return None
    return b.get("script") if isinstance(b, dict) else None


def build_manifest_rows(sections, objs, figs):
    """One manifest row per table/figure of main.tex.

    Three coverage tiers are distinguished, because conflating them is how a
    "complete manifest" becomes a false claim:
      cell_parsed   the audit reads the tabular out of main.tex and compares
                    every cell (tabular_rows(label) -> agree()).
      claims_only   the audit does not parse the table, but a section of it
                    names the table and asserts values quoted from it.
      unaudited     nothing in the audit refers to it.
    """
    label_to_sections = {}
    for s in sections:
        for lab in s["tex_labels_parsed"]:
            label_to_sections.setdefault(lab, []).append(s)
    body_by_title = {t: b for t, b in audit_sections()}
    rows = []
    for o in objs:
        lab = o["label"]
        secs = label_to_sections.get(lab, [])
        jsons = sorted({j for s in secs for j in s["results_json_read"]})
        # sections that quote the table without parsing it: their comment text
        # names the label (e.g. "Values from the paper's Table epsstar")
        key = (lab or "").split(":")[-1]
        by_mention = [s for s in sections
                      if key and s not in secs
                      and (key in s["audit_section"]
                           or key in body_by_title.get(s["audit_section"], ""))]
        fig_json = []
        for g in o["graphics"]:
            fig_json += figs["per_figure_backing_json"].get(
                pathlib.PurePath(g).stem, [])
        if not jsons:
            jsons = sorted(set(fig_json)
                           or {j for s in by_mention
                               for j in s["results_json_read"]})
        tier = ("cell_parsed" if secs else
                "claims_only" if (by_mention or fig_json) else "unaudited")
        rows.append({
            "kind": o["kind"],
            "label": lab,
            "tex_line": o["tex_line"],
            "caption_stub": o["caption_stub"],
            "graphics": o["graphics"],
            "backing_results_json": jsons,
            "producing_scripts": sorted({script_of(j) for j in jsons
                                         if script_of(j)}),
            "audit_sections_parsing_cells": [s["audit_section"] for s in secs],
            "audit_sections_quoting_values": [s["audit_section"]
                                              for s in by_mention],
            "coverage": tier,
            "mechanically_audited": tier != "unaudited",
            "audit_agree_call_sites": sum(s["agree_call_sites"] for s in secs),
            "audit_claim_call_sites": sum(s["claim_call_sites"]
                                          for s in secs + by_mention),
        })
    return rows


# --------------------------------------------------------------- runtime ----
CAMPAIGN_RULES = [
    ("1D mechanism sweeps (CPU)", ("continuous_reach", "continuous_pendulum",
                                   "continuous_axes", "continuous_smooth_probe")),
    ("sharp-plateau variant (CPU)", ("continuous_reach_sharp",
                                     "continuous_pendulum_sharp",
                                     "continuous_pendulum_sharpphantom")),
    ("PatchField2D mechanism (CPU)", ("continuous_patch2d",
                                      "continuous_patch2d_square")),
    ("second planner family, CEM (CPU)", ("continuous_cem",
                                          "continuous_cem_patch2d")),
    ("eps-sensitivity sweeps (CPU)", ("continuous_eps_sweep",
                                      "continuous_eps_sweep_patch2d")),
    ("mitigation sweeps (CPU)", ("continuous_mitigation",
                                 "continuous_mitigation_patch2d")),
    ("LLM synthesis, 1D cart", ("continuous_synthesis_mini_xwall8",
                                "continuous_synthesis_large_xwall8",
                                "continuous_synthesis_large_xwall8_off20",
                                "continuous_synthesis_mini_xwall4",
                                "continuous_synthesis_compat-qwen3-coder-30b-a3b-instruct_xwall8")),
    ("LLM synthesis, pendulum", ("continuous_synthesis_pendulum_",)),
    ("LLM synthesis, PatchField2D", ("continuous_synthesis_patch2d",
                                     "continuous_synthesis_patch2dsq")),
]


def campaign_of(stem):
    for name, keys in CAMPAIGN_RULES:
        for k in keys:
            if stem == k or stem.startswith(k):
                return name
    return "other / theory certificates"


def runtime_facts():
    per_file, by_campaign = {}, {}
    for f in sorted(RESULTS.glob("*.json")):
        try:
            b = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(b, dict) or "elapsed_s" not in b:
            continue
        e = float(b["elapsed_s"])
        per_file[f.stem] = e
        c = campaign_of(f.stem)
        by_campaign.setdefault(c, {"files": [], "elapsed_s": 0.0})
        by_campaign[c]["files"].append(f.stem)
        by_campaign[c]["elapsed_s"] = round(
            by_campaign[c]["elapsed_s"] + e, 1)
    for c in by_campaign:
        by_campaign[c]["elapsed_min"] = round(by_campaign[c]["elapsed_s"] / 60, 1)
        by_campaign[c]["files"].sort()
    total = round(sum(per_file.values()), 1)

    # runtimes that exist only as "~N min" annotations in main.tex's verbatim
    tex = TEX.read_text()
    verbatim = "\n".join(re.findall(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
                                    tex, re.S))
    tex_scripts = {}
    for m in re.finditer(r"scripts/([a-z0-9_]+\.py)(.*?)(?=\n(?:PYTHONPATH|python|#|\Z))",
                         verbatim, re.S):
        name, tail = m.group(1), m.group(2)
        est = re.search(r"~\s*([0-9.]+)\s*(min|s)\b", tail)
        tex_scripts.setdefault(name, None)
        if est:
            secs = float(est.group(1)) * (60 if est.group(2) == "min" else 1)
            tex_scripts[name] = secs
    produced_by = {}
    for stem in per_file:
        s = script_of(stem)
        if s:
            produced_by.setdefault(s, []).append(stem)
    unverified, stale = [], []
    for name, est in sorted(tex_scripts.items()):
        recorded = sorted(produced_by.get(name, []))
        # a script may write a JSON named after itself while recording a
        # different producer in the "script" field (continuous_cem.py writes
        # continuous_cem_patch2d.json), so match by name as well
        own = RESULTS / (name[:-3] + ".json")
        by_name = own.stem if own.exists() and own.stem in per_file else None
        if by_name and by_name not in recorded:
            recorded.append(by_name)
        row = {
            "script": f"scripts/{name}",
            "tex_estimate_s": est,
            "own_json_exists": own.exists(),
            "own_json_records_elapsed_s": bool(by_name),
            "results_json_with_elapsed_s": recorded,
            "runtime_verified_from_json": bool(recorded),
        }
        unverified.append(row)
        if est and recorded:
            # compare against the DEFAULT run (the JSON named after the script)
            # rather than a sibling variant produced by a different invocation
            ref = by_name or max(recorded, key=lambda r: per_file[r])
            got = per_file[ref]
            if got > 1.35 * est or got < est / 1.35:
                stale.append({"script": f"scripts/{name}",
                              "tex_estimate_s": est,
                              "compared_against": f"results/{ref}.json",
                              "recorded_elapsed_s": got,
                              "ratio_recorded_over_tex": round(got / est, 2)})
    cpu = round(sum(v["elapsed_s"] for k, v in by_campaign.items()
                    if "(CPU)" in k), 1)
    llm = round(sum(v["elapsed_s"] for k, v in by_campaign.items()
                    if k.startswith("LLM")), 1)
    other = round(total - cpu - llm, 1)
    return {
        "subtotals": {
            "cpu_sweeps_s": cpu, "cpu_sweeps_h": round(cpu / 3600, 2),
            "llm_synthesis_s": llm, "llm_synthesis_h": round(llm / 3600, 2),
            "paper2_named_campaigns_h": round((cpu + llm) / 3600, 2),
            "unclassified_s": other,
            "unclassified_files": sorted(
                by_campaign.get("other / theory certificates", {})
                .get("files", [])),
            "unclassified_note": (
                "Files that match no campaign rule. As of generated_at_utc "
                "these are artifacts of the in-progress revision written by "
                "other work in the same tree, not part of the paper as "
                "committed at git.head; treat paper2_named_campaigns_h as the "
                "figure for the submitted version."),
        },
        "tex_estimates_contradicted_by_recorded_elapsed_s": stale,
        "tex_estimate_staleness_note": (
            "The appendix's ~N min annotations were written when the sweeps ran "
            "at their original sample sizes; the 2026-07-25 censored-zero fix "
            "raised rarity rollouts (cart 3000->30,000, pendulum 3000->30,000, "
            "axes 2000->20,000) without updating the annotations, so the listed "
            "estimates understate the current scripts. Use "
            "per_results_file_elapsed_s, which each script wrote itself."),
        "per_results_file_elapsed_s": per_file,
        "by_campaign": by_campaign,
        "total_recorded_elapsed_s": total,
        "total_recorded_elapsed_h": round(total / 3600, 2),
        "n_files_with_elapsed_s": len(per_file),
        "n_results_json_total": len(list(RESULTS.glob("*.json"))),
        "scripts_named_in_tex_verbatim": unverified,
        "note": ("elapsed_s is wall-clock for ONE run of the script that wrote "
                 "the file; it excludes every superseded run (the 5-seed cells "
                 "later overwritten at 20 seeds, the square-ablation resume "
                 "passes, failed LLM calls) and excludes every script that does "
                 "not record it. The total is therefore a LOWER BOUND on the "
                 "compute the paper cost."),
    }


# -------------------------------------------------------------- LLM cost ----
def llm_facts():
    rows = []
    tokens_recorded = False
    for f in sorted(RESULTS.glob("continuous_synthesis_*.json")):
        b = json.loads(f.read_text())
        cells = b.get("cells", [])
        calls = sum(1 + int(c.get("refine_iterations") or 0) for c in cells)
        if any("usage" in c for c in cells):
            tokens_recorded = True
        rows.append({
            "file": f"results/{f.name}",
            "model": b.get("model"),
            "size": b.get("size"),
            "instrument": (b.get("params") or {}).get("instrument", "cart"),
            "n_cells": len(cells),
            "llm_calls": calls,
            "refine_iterations_total": sum(int(c.get("refine_iterations") or 0)
                                           for c in cells),
            "elapsed_s": b.get("elapsed_s"),
            "campaign": campaign_of(f.stem),
            "usage_recorded": any("usage" in c for c in cells),
        })
    relay = RESULTS / "continuous_claude_relay.json"
    relay_calls = None
    if relay.exists():
        blob = json.loads(relay.read_text())
        relay_calls = sum(1 + int(c.get("refine_iterations") or 0)
                          for c in blob) if isinstance(blob, list) else None
    by_camp = {}
    for r in rows:
        d = by_camp.setdefault(r["campaign"], {"llm_calls": 0, "cells": 0,
                                              "files": 0})
        d["llm_calls"] += r["llm_calls"]
        d["cells"] += r["n_cells"]
        d["files"] += 1
    # paper-1 JSONs DO record dollar cost; carry them as the only measured
    # $/call anchor available in-repo.
    anchors = {}
    for f in sorted(RESULTS.glob("*.json")):
        try:
            b = json.loads(f.read_text())
        except Exception:
            continue
        if isinstance(b, dict) and "cost_usd_total" in b:
            anchors[f.stem] = b["cost_usd_total"]
    return {
        "per_file": rows,
        "by_campaign": by_camp,
        "total_llm_calls_paper2_api_arms": sum(r["llm_calls"] for r in rows),
        "claude_relay_calls": relay_calls,
        "token_usage_recorded_in_paper2_artifacts": tokens_recorded,
        "why_not": ("cwm.llm providers DO capture prompt/completion tokens "
                    "(src/cwm/llm/provider.py Usage; azure_openai.py raises if "
                    "Azure omits it) and contract.refine_continuous keeps them "
                    "in RefineResult.usages, but "
                    "contract.synthesize_and_evaluate does not copy them into "
                    "the emitted cell, so no paper-2 artifact carries tokens. "
                    "Paper 1's runners did record dollars (cost_usd_total)."),
        "paper1_cost_usd_anchors": anchors,
        "paper1_cost_usd_total": round(sum(anchors.values()), 4),
        "cost_statement_for_the_appendix": (
            "Report paper 2's LLM cost as a RANGE, not a point: the exact call "
            "count is known (see total_llm_calls_paper2_api_arms) but the token "
            "count is not recorded. The design spec's own pre-run estimate was "
            "'~2-7 LLM calls per seed, 1-2k prompt tokens each'; combined with "
            "the measured call count that brackets the API arms at roughly "
            "1e6-1e7 total tokens, i.e. single-digit to low-double-digit US "
            "dollars at 2026 GPT-5.x-class prices. The only measured dollar "
            "figures in the repo are paper 1's (paper1_cost_usd_anchors, "
            "$%.2f total), which are a different campaign. Anyone needing an "
            "exact figure must take it from the Azure billing export for the "
            "run window 2026-07-07 .. 2026-07-25."
            % round(sum(anchors.values()), 2)),
    }


# --------------------------------------------------------------- licence ----
def licence_facts():
    names = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING",
             "NOTICE"]
    py = (REPO / "pyproject.toml").read_text()
    return {
        "licence_files_present": {n: (REPO / n).exists() for n in names},
        "any_licence_file": any((REPO / n).exists() for n in names),
        "pyproject_declares_license": bool(re.search(r"^\s*license\s*=", py,
                                                     re.M)),
        "pyproject_classifiers": re.findall(r'"(License :: [^"]+)"', py),
        "readme_mentions_licence": bool(
            re.search(r"licen[cs]e", (REPO / "README.md").read_text(), re.I)),
        "gap": ("There is NO licence file and pyproject.toml declares no "
                "`license` field and no License classifier, so the code, the "
                "synthesized artifacts under results/ and the paper source are "
                "all-rights-reserved by default. A reviewer told to 'reproduce "
                "this' has no licence to redistribute anything. Fix before "
                "submission: add a LICENSE (e.g. MIT or Apache-2.0 for code, "
                "CC-BY-4.0 for the paper and data) and set "
                "[project].license in pyproject.toml."),
    }


# ------------------------------------------------------------- env config ----
ENV_DOC = {
    "AZURE_OPENAI_ENDPOINT": "Azure OpenAI resource endpoint URL",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI API key (secret)",
    "AZURE_OPENAI_API_VERSION": "Azure OpenAI API version; paper 2 used 2025-04-01-preview",
    "AZURE_DEPLOYMENT_LARGE": "deployment name behind the paper's \"large\" (gpt-5.4)",
    "AZURE_DEPLOYMENT_MINI": "deployment name behind the paper's \"mini\" (gpt-5.4-mini)",
    "AZURE_DEPLOYMENT_NANO": "deployment name behind \"nano\" (paper 1 arms only)",
    "HF_TOKEN": "Hugging Face token for the Inference Providers router (Qwen cross-family arm)",
}


def env_facts():
    hits = {}
    for root in ("src", "scripts", "tests"):
        for p in sorted((REPO / root).rglob("*.py")):
            txt = p.read_text()
            for m in re.finditer(r"os\.environ\[\s*\"([A-Z0-9_]+)\"\s*\]"
                                 r"|os\.environ\.get\(\s*\"([A-Z0-9_]+)\""
                                 r"|os\.getenv\(\s*\"([A-Z0-9_]+)\"", txt):
                name = m.group(1) or m.group(2) or m.group(3)
                hits.setdefault(name, []).append(
                    f"{p.relative_to(REPO)}:{txt[:m.start()].count(chr(10)) + 1}")
    dotenv_users = sorted(
        str(p.relative_to(REPO))
        for root in ("src", "scripts", "tests")
        for p in (REPO / root).rglob("*.py")
        if "load_dotenv" in p.read_text())
    lines = ["# Credentials template for docs/paper2 (review point #19).",
             "# Copy to <repo-root>/.env and fill in. NEVER commit the filled file:",
             "# .gitignore already excludes .env. No value here is a real secret.",
             "#",
             "# Every variable below is read by name from os.environ by the",
             "# scripts listed in results/repro_manifest.json -> env_config.",
             "# The CPU-only reproduction (Tables 2-9, all figures, the whole",
             "# audit) needs NONE of them; they are required only for the LLM",
             "# synthesis arms.",
             ""]
    for name in sorted(set(list(ENV_DOC) + list(hits))):
        lines.append(f"# {ENV_DOC.get(name, 'read by the scripts listed in the manifest')}")
        default = {"AZURE_OPENAI_ENDPOINT": "https://YOUR-RESOURCE.openai.azure.com/",
                   "AZURE_OPENAI_API_VERSION": "2025-04-01-preview",
                   "AZURE_DEPLOYMENT_LARGE": "gpt-5.4",
                   "AZURE_DEPLOYMENT_MINI": "gpt-5.4-mini",
                   "AZURE_DEPLOYMENT_NANO": "gpt-5.4-nano"}.get(name, "")
        lines.append(f"{name}={default}")
        lines.append("")
    atomic_write(REPO / "docs" / "paper2" / "env.example", "\n".join(lines))
    return {
        "variables": {k: sorted(v) for k, v in sorted(hits.items())},
        "documented_template": "docs/paper2/env.example",
        "load_dotenv_modules": dotenv_users,
        "existing_repo_root_template": {
            "path": ".env.example",
            "exists": (REPO / ".env.example").exists(),
            "lists_HF_TOKEN": "HF_TOKEN" in (REPO / ".env.example").read_text()
            if (REPO / ".env.example").exists() else None,
            "api_version_matches_paper": "2025-04-01-preview"
            in (REPO / ".env.example").read_text()
            if (REPO / ".env.example").exists() else None,
        },
        "cpu_only_reproduction_needs_no_credentials": True,
    }


def paper2_unaudited(dyn_json):
    """Paper-2 evidence files the audit never opens.

    "Paper-2 evidence" = written by a script main.tex names in \\texttt{} or in
    the reproducibility verbatim. That is the honest boundary: paper-1 JSONs in
    the same directory are not this paper's business.
    """
    tex = TEX.read_text()
    named = set(re.findall(r"scripts/([a-z0-9_\\]+\.py)", tex))
    named = {n.replace("\\", "") for n in named}
    named |= {n.replace("\\_", "_") for n in named}
    out = []
    for p in sorted(RESULTS.glob("*.json")):
        if p.stem in dyn_json or p.stem == "repro_manifest":
            continue
        s = script_of(p.stem)
        if s and s in named:
            out.append({"file": f"results/{p.name}", "written_by": f"scripts/{s}"})
    return out


# ------------------------------------------------------------------ main ----
def main():
    sections = static_audit_map()
    dyn = dynamic_audit_files()
    objs, _ = tex_objects()
    figs = figure_sources()
    rows = build_manifest_rows(sections, objs, figs)

    static_json = sorted({j for s in sections for j in s["results_json_read"]})
    # the audit also reads JSONs from module-level code outside any section
    dyn_json = dyn["results_json_opened"]
    missed = sorted(set(dyn_json) - set(static_json))
    extra = sorted(set(static_json) - set(dyn_json))

    manifest = {
        "what_this_is": (
            "Reproducibility facts for docs/paper2/main.tex (review points "
            "#18/#19). Generated, not hand-typed: see docs/paper2/REPRO-FACTS.md "
            "for the prose version and the generator's source."),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generator": "scripts/repro_manifest.py (source archived in docs/paper2/REPRO-FACTS.md)",
        "git": {
            "head": sh("git", "-C", str(REPO), "rev-parse", "HEAD"),
            "head_short": sh("git", "-C", str(REPO), "rev-parse", "--short", "HEAD"),
            "head_date": sh("git", "-C", str(REPO), "log", "-1", "--date=iso",
                            "--format=%ad"),
            "branch": sh("git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"),
            "describe": sh("git", "-C", str(REPO), "describe", "--always", "--dirty"),
            "note": ("A working tree with concurrent edits: the manifest is a "
                     "snapshot of results/ at generated_at_utc."),
        },
        "platform": platform_facts(),
        "dependencies": dependency_facts(),
        "manifest": rows,
        "audit_coverage": {
            "audit_script": "scripts/audit_paper2_numbers.py",
            "audit_checks_executed": dyn["audit_checks_executed"],
            "audit_failures": dyn["audit_failures"],
            "audit_exit_code": dyn["audit_exit_code"],
            "sections": sections,
            "results_json_read_static": static_json,
            "results_json_read_dynamic": dyn_json,
            "static_vs_dynamic_ok": not missed,
            "read_dynamically_but_not_matched_statically": missed,
            "matched_statically_but_not_read": extra,
            "tables_and_figures_total": len(rows),
            "coverage_counts": {
                t: sum(1 for r in rows if r["coverage"] == t)
                for t in ("cell_parsed", "claims_only", "unaudited")},
            "tables_and_figures_mechanically_audited": sum(
                1 for r in rows if r["mechanically_audited"]),
            "gaps": [
                {"label": r["label"], "kind": r["kind"], "tex_line": r["tex_line"],
                 "coverage": r["coverage"],
                 "backing_results_json": r["backing_results_json"],
                 "caption_stub": r["caption_stub"]}
                for r in rows if r["coverage"] != "cell_parsed"],
            "results_json_in_repo_not_read_by_audit": sorted(
                {p.stem for p in RESULTS.glob("*.json")} - set(dyn_json)
                - {"repro_manifest"}),
            "paper2_results_json_not_read_by_audit": paper2_unaudited(dyn_json),
            "paper2_unaudited_note": (
                "These files were written by a script main.tex names, so they "
                "are paper-2 evidence, yet no assertion in "
                "audit_paper2_numbers.py reads them: the numbers they back "
                "(PatchField2D CEM rows, PatchField2D eps rows, the "
                "square-patch CPU calibration, the 2D Claude relay ledger) are "
                "quoted in prose and are NOT covered by any of the checks "
                "audit_checks_executed counts."),
        },
        "figures": figure_sources(),
        "runtime": runtime_facts(),
        "llm_cost": llm_facts(),
        "licence": licence_facts(),
        "env_config": env_facts(),
    }
    out = RESULTS / "repro_manifest.json"
    atomic_write(out, json.dumps(manifest, indent=1, sort_keys=False) + "\n")
    print(f"wrote {out.relative_to(REPO)}")
    print(f"  audit checks executed: {dyn['audit_checks_executed']}, "
          f"failures: {len(dyn['audit_failures'])}")
    print(f"  tables+figures: {len(rows)}, mechanically audited: "
          f"{sum(1 for r in rows if r['mechanically_audited'])}")
    print(f"  static/dynamic JSON coverage match: {not missed}"
          + (f"  MISSED {missed}" if missed else ""))
    print(f"  recorded wall clock: {manifest['runtime']['total_recorded_elapsed_h']} h "
          f"over {manifest['runtime']['n_files_with_elapsed_s']} files")
    print(f"  paper-2 LLM calls: {manifest['llm_cost']['total_llm_calls_paper2_api_arms']}"
          f" (tokens recorded: {manifest['llm_cost']['token_usage_recorded_in_paper2_artifacts']})")


if __name__ == "__main__":
    main()
```
