# Paper-Craft Items Implementation Plan (approved design inline)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three approved paper-craft items for paper 2: (1) extend the LaTeX CI guard to cover `docs/paper2`; (2) add the new experiments' commands to the reproduction appendix; (3) turn the §6 pendulum-synthesis prose numbers into a compact table. (A synthesis figure was considered and REJECTED by the user — do not add one.)

**Architecture:** One mechanical task. The CI guard refactors `scripts/check_latex.sh`'s body into a loop over both paper dirs, preserving its checks; the appendix and table edits mirror across `preprint-draft.md` and `main.tex` as always.

**Tech Stack:** bash, LaTeX (system pdflatex), markdown. No Python code changes.

## Global Constraints

- Worktree `/private/tmp/claude-502/-Users-javieraguilarmartin1-Documents-repos-code-world-models/a4c5d0dc-71cf-4e5a-9e72-26305c146b56/scratchpad/wt-paper2`, branch `claude/continuous-setting-feasibility-wktp6b`. Never touch the main checkout.
- Table/appendix numbers verbatim from `.superpowers/sdd/task-6-measured-numbers.md` (pendulum synthesis) — never re-derived.
- Both papers must pass the extended guard: `bash scripts/check_latex.sh` exits 0 (this is also the verification for item 1).
- `main.bbl` files are COMMITTED artifacts in both paper dirs: the guard must not leave them deleted in the working tree (restore tracked state after the check).
- Commit message trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: CI guard + appendix + pendulum table

**Files:**
- Modify: `scripts/check_latex.sh`
- Modify: `docs/paper2/preprint-draft.md` (appendix + §6 table)
- Modify: `docs/paper2/main.tex` (appendix + §6 table)
- Regenerate: `docs/paper2/main.pdf`

- [ ] **Step 1: Extend `scripts/check_latex.sh` to both papers**

Refactor: wrap the existing per-paper logic (compile → undefined-ref checks → overfull checks → summary) in a `check_paper() { local PAPER_DIR="$1"; ... }` function using the SAME thresholds and grep logic as now, then call it for `docs/paper` and `docs/paper2`, accumulating failure across both (exit 1 if either fails). Two required behavior changes, both scoped to cleanup:
1. After the checks, instead of `rm -f "$MAIN".aux "$MAIN".bbl "$MAIN".blg "$MAIN".out`, remove aux/blg/out/log as before but RESTORE the bbl from git if tracked: `git checkout -- "$MAIN.bbl" 2>/dev/null || rm -f "$MAIN.bbl"` (both papers commit their bbl; deleting it locally dirties the tree).
2. `cd` back to the repo root between papers (run each check in a subshell `( cd "$PAPER_DIR" && ... )` or save/restore PWD).
Keep `OVERFULL_PT_THRESHOLD` behavior and the `::error::` message format identical.

- [ ] **Step 2: Run the extended guard**

Run from the worktree root: `bash scripts/check_latex.sh`
Expected: both papers compile; summary lines for BOTH dirs; `LaTeX presentation check PASSED`; exit 0; `git status` afterward shows NO modification/deletion of either `main.bbl` (and `main.pdf` regenerated only if the script writes it — the guard compiles in-place, so `docs/paper*/main.pdf` may be rebuilt; that is fine, commit paper2's if its bytes changed, and restore paper1's via `git checkout -- docs/paper/main.pdf` since paper 1 is out of scope).

- [ ] **Step 3: Reproduction appendix additions (draft + tex)**

In the appendix ("Appendix: reproduction" in `preprint-draft.md`; the corresponding appendix section in `main.tex`), after the existing synthesis commands, add the new runs (adapt formatting to each file):
```bash
# Pendulum synthesis arm (second instrument; Azure credentials as above)
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 20 --instrument pendulum --th-stop 1.4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 --instrument pendulum --th-stop 1.4
PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 20 --instrument pendulum --th-stop 1.0
PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 20 --instrument pendulum --th-stop 1.0
# Mitigation sweep (CPU only)
PYTHONPATH=src python scripts/continuous_mitigation.py
# eps-sensitivity sweep (CPU only)
PYTHONPATH=src python scripts/continuous_eps_sweep.py
```
If the appendix lists the cart cross-family command, mirror the pendulum one too (`mini 3 --instrument pendulum --th-stop 1.4 --compat-model "Qwen/Qwen3-Coder-30B-A3B-Instruct"`). Match the appendix's existing style exactly (verbatim/code-block conventions per file).

- [ ] **Step 4: §6 pendulum-synthesis compact table (draft + tex)**

In the "Second-instrument robustness" paragraph of §6 (both files), add a compact table carrying the numbers currently in prose, sourced verbatim from `.superpowers/sdd/task-6-measured-numbers.md`:

| cell (20 seeds each) | full | mode-absent → blind & exploited | mode-present → repaired (stalled) |
|---|---|---|---|
| mini θ_stop=1.4 | 20/20 | 9 → 9 (pc 0.995) | 11 → 11 (0) |
| large θ_stop=1.4 | 20/20 | 9 → 9 (pc 0.995) | 11 → 11 (0) |
| mini θ_stop=1.0 | 20/20 | 0 → — | 20 → 20 (0) |
| large θ_stop=1.0 | 20/20 | 0 → — | 20 → 20 (0) |
| Qwen θ_stop=1.4 (3 seeds) | 3/3 | 1 → 1 (pc 0.995) | 2 → 0 (2 stalled @0.9997) |

Then LIGHTEN the surrounding prose: keep the narrative sentences (identifiability event, 62/62 pooled, Wilson bounds, Qwen stalls, "not a cart artifact") but drop number runs now carried by the table where the sentence otherwise duplicates it verbatim. Do not change any claim; every number must still trace to the measured-numbers file. Use booktabs style in the tex (like the paper's other tables) with a `\label{tab:pendulum-synthesis}` and reference it from the prose.

- [ ] **Step 5: Verify with the new guard, commit, push**

```bash
bash scripts/check_latex.sh        # both papers must PASS (this re-verifies item 1 and the new table)
git status --short                 # only the 4 intended files (+ paper2 main.pdf)
git add scripts/check_latex.sh docs/paper2/preprint-draft.md docs/paper2/main.tex docs/paper2/main.pdf
git commit -m "paper2+ci: extend LaTeX guard to paper2; repro appendix; pendulum synthesis table

CI guard now compiles and checks docs/paper2 alongside docs/paper (bbl
restored, not deleted). Reproduction appendix gains the pendulum synthesis,
mitigation, and eps-sweep commands. §6's second-instrument numbers move from
prose into a compact table (tab:pendulum-synthesis), prose lightened, claims
unchanged.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin claude/continuous-setting-feasibility-wktp6b
```
If paper 1 (`docs/paper`) FAILS the extended guard for reasons unrelated to this task (pre-existing), STOP and report — do not modify paper 1.
