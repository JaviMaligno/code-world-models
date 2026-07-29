# Paper 2 — line-by-line inventory of the review's minor points

Purpose: make every "Otros puntos menores" fix mechanical. For each item: **every** occurrence
in `docs/paper2/main.tex`, the exact current text, and a proposed replacement that preserves
the sentence's meaning. Where a fix needs a number that does not exist yet, the item says what
must be measured, by which script, and under which `results/` key.

This document is **read-only reconnaissance**: nothing in `main.tex` was edited to produce it.

## How to use this file

1. **Locate by anchor, not by line number.** `main.tex` was being edited concurrently while
   this inventory was produced (998 → 1107 lines during the session; the abstract and the
   contribution list were rewritten mid-scan). Every occurrence below carries a short unique
   **anchor**; `grep -n "<anchor>" docs/paper2/main.tex` is the authoritative locator.
2. **Scan of record:** `docs/paper2/main.tex`,
   `sha256 118001fcf12a4ee048644415ae81d8c42ef53eae60bda8bf93b7e1fe51ab5a6d`,
   215 593 bytes, 1107 lines, 2026-07-27T15:27:50. All line numbers below are that snapshot's,
   and all 41 anchors were machine-verified **unique** against it.
   **Known drift:** re-verified minutes later at `sha256 19d902f8…` (1110 lines) — all 41
   anchors still resolved uniquely, and everything below roughly line 570 had shifted by
   **+3** lines (`tab:danger` 593 → 596, `tab:pendulum` 642 → 645, `tab:patch2d` 676 → 679,
   `tab:cem` 705 → 708, `tab:axes` 737 → 740, `tab:eps-sweep` 765 → 768, `tab:mitigation`
   800 → 803, `tab:patch2d-mitigation` 862 → 865, `tab:pendulum-synthesis` 910 → 913,
   `tab:smooth` 955 → 958; figures 600/607/744/962 → 603/610/747/965). Treat line numbers as
   ±10 and trust the anchors.
3. **Before applying, re-resolve the anchors.** Three items (`m2`, `m3`, `p24`) were *partly
   closed by another agent while this scan ran*; their status columns say so. If an anchor no
   longer resolves, the sentence was rewritten — re-read it before assuming the defect is gone.
4. Item numbering follows `docs/paper2/REVIEW-RESPONSE.md` (`m1`…`m17`), with the task's own
   numbering in brackets. Two items outside the minor list are included because the task asked:
   review point 24 (`p24`) and the seed-pairing-in-the-analysis half of `m9`.

## Status legend

| Status | Meaning |
|---|---|
| `OPEN` | defect present in the scanned file; fix specified below |
| `PARTIAL` | some occurrences already fixed by a concurrent edit; residues listed |
| `CLOSED` | already fixed in the scanned file; recorded so it is not "fixed" twice |
| `NEEDS-MEASUREMENT` | the wording fix requires a number no `results/` JSON carries yet |

## Summary — occurrences per item

| Item | Review point | Occurrences | Need a change | Status |
|---|---|---|---|---|
| m1 [1] | "two independent modes" | 1 (+18 neighbouring "bi-modal"/"two modes" uses that are correct) | 1 | OPEN |
| m2 [2] | "zero-curvature square" | 3 literal (was 6; abstract + intro already fixed) | 3 | PARTIAL |
| m3 [3] | "below random" without the raw return | 12 | 7 (incl. 1 numeric inconsistency, m3-G, and 1 over-scoped abstract claim, m3-A) | OPEN |
| m4 [4] | printed zeros in tables | 38 zero-valued cells in 6 tables + 6 count-cells in `tab:pendulum-synthesis` | 44 | OPEN |
| m5 [5] | 4-decimal values the sample cannot resolve | 27 rarity + 27 `d@40` cells in `tab:patch2d`, 1 rarity cell in `tab:axes` | 55 | OPEN |
| m6 [6] | `d@N` without an interval | 60 cells in 4 tables + 2 prose sites | 60 | NEEDS-MEASUREMENT |
| m7 [7] | figures lack uncertainty bands | 4 figures | 4 | PARTIAL DATA (2 of 4 computable today) |
| m8 [8a] | are episode seeds reused across knobs/planners? | truth established from code; **0** statements in the paper | add 3 | OPEN |
| m9 [8b] | seed pairing must enter the analysis | used in 2 places (CEM only); missing in 5 | 5 | NEEDS-MEASUREMENT |
| m10 [9a] | `J_truth` called "optimal" | 5 "optimal" uses (2 need work, 1 correctly scoped, 2 an unrelated sense) | 2 | OPEN |
| m11 [9b] | "truth planner" = MPC with the true model, not optimal | 12 uses, 0 clarifications | add 2 | OPEN |
| m12 [10] | "almost-everywhere exact" | 2 | 2 | OPEN |
| m13 [11] | rarity is a rollout-level probability | 3 knob sites, 1 definition site, 0 reminders | add 2 | OPEN |
| m14 [12] | `mu_query` → `q_hit(E)` | 14 `q_hit`, **0** `mu_` left; 2 "query-hit mass" residues | 2 | PARTIAL (rename done) |
| m15 [13] | funding / COI / data availability / AI-use | **0** present | add 4 | OPEN |
| m16 [14] | anonymization | 2 hard identifiers, 8 self-citations, 18 "companion paper" | author decision | OPEN |
| m17 [15] | dangling references | 2 entries checked | 1 note + 1 verification + 1 proof to inline | PARTIAL |
| p24 | "left open" then presented | offending sentence already deleted | 0 | CLOSED |

Table/figure landmarks in the scan of record (for the m4–m7 edits):
`tab:epsstar` L280 · `tab:danger` L593 (header L581, rows L583–L589) · `tab:pendulum` L642
(header L631, rows L632–L637) · `tab:patch2d` L676 (header L662, rows L664–L672) · `tab:cem`
L705 (header L689, rows L691–L701) · `tab:axes` L737 (header L726, rows L728–L733) ·
`tab:eps-sweep` L765 (rows L757–L761) · `tab:mitigation` L800 · `tab:patch2d-mitigation` L862 ·
`tab:pendulum-synthesis` L910 (header L900, rows L902–L906) · `tab:smooth` L955.
Figures: `fig:threshold` L600 · `fig:reach` L607 · `fig:axes` L744 · `fig:smooth` L962.

---

## m1 [1] — "two independent modes": distinct but dependent

The paper *measures* the dependence (negative at `(2,6)` and `(3,7)`, positive at `(4,6)`,
undecided at `(4,7)`, at 50 000 rollouts/knob, `results/patch2d_dependence_50k.json`), and
Proposition `prop:jointmiss` exists precisely because the contact events do **not** factor.
One sentence still asserts the opposite.

**Occurrence 1/1 — L648, anchor `two independent modes`** (Section `sec:patch2d`, opening
sentence of the PatchField2D instrument description):

- current: `\textbf{PatchField2D} closes both structural gaps at once --- a 4D state and two independent modes --- and asks what the 1D instruments cannot: does the danger law compose mode-wise?`
- proposed: `\textbf{PatchField2D} closes both structural gaps at once --- a 4D state and two \emph{distinct but dependent} modes (their within-rollout contact events are measurably dependent, and the sign of the dependence varies across the knob grid; Remark~\ref{rem:bracket}) --- and asks what the 1D instruments cannot: does the danger law compose mode-wise?`

**Checked and correct — do not touch.** The abstract (L33–L35) and the introduction do **not**
contain the phrase, contrary to the review's guess; the instrument section is the only site.
The 18 neighbouring uses that are all correct: "bi-modal" at L35(new abstract), L48, L57, L78,
L651 (subsection title), L712, L768, L826, L979, L1000, L1082; "two modes" in `prop:jointmiss`
L115 and `sec:limitations` L979; "both patches"/"either patch" in `rem:bracket` L133 and the
`tab:patch2d` caption L670.

**Sibling file, same defect (out of scope, flagged so the files do not diverge):**
`docs/paper2/preprint-draft.md:144`.

---

## m2 [2] — "zero-curvature square" → "axis-aligned square with flat edges"

A square's corners are not differentiable, so curvature is undefined there; "zero curvature"
is false as stated (true only of the open edges). The ablation's actual point is that the
predicate is `max`/`abs` with straight sides.

**PARTIAL — 3 of 6 occurrences were fixed by a concurrent edit** (the abstract now reads
`an axis-aligned square` at L35, the introduction `an axis-aligned square` at L52, and L932 now
reads exactly the recommended `the axis-aligned square with flat edges fails identically`).
Three residues:

| # | Line | Anchor | Current fragment | Proposed |
|---|---|---|---|---|
| 1 | L926 | `Ablation 2: a zero-curvature square falsifies` | `\paragraph{Ablation 2: a zero-curvature square falsifies the curvature reading.}` | `\paragraph{Ablation 2: a flat-edged square falsifies the curvature reading.}` |
| 2 | L983 | `budget; zero-curvature square ---` | `two ablation campaigns (region-guidance $3\times$ budget; zero-curvature square --- 20 seeds each, both sizes)` | `...(region-guidance $3\times$ budget; axis-aligned square with flat edges --- 20 seeds each, both sizes)` |
| 3 | L1000 | `including a zero-curvature square and a guided` | `(0/156, including a zero-curvature square and a guided $3\times$-budget treatment: a template prior over region forms, not curvature)` | `(0/156, including an axis-aligned square with flat edges and a guided $3\times$-budget treatment: a template prior over region forms, not curvature)` |

**Correct as written — do not change:** L926's body already says
`an axis-aligned square patch (a Chebyshev ball, $\max(|x-c_x|,|y-c_y|) \le R$ --- a \texttt{max}/\texttt{abs} predicate, no quadratic)`;
L932's `(flattening curves, curving flats)`; the curvature *reading* references
(`the curvature out is now a measured negative`).

---

## m3 [3] — every "below random" claim needs the raw return beside it

12 occurrences of the "below random / above random / worse than random" family. 5 already carry
the returns (leave them), 5 need returns added, and 2 are worse than a missing number:
**m3-A** is now over-scoped in the rewritten abstract, and **m3-G** contradicts its own JSON.

Numbers to quote (all already versioned — quote, do not recompute):
`results/continuous_reach.json` → `rows[].j_blind` (1.38e-5 … 9.39e-1), `rows[].j_random` (0.5344);
`results/continuous_reach_sharp.json` (the sharp-plateau variant, which is where "every knob" holds);
`results/continuous_pendulum.json` → `rows[].j_random` (0.0584 / 0.0597 / 0.0590);
`results/continuous_patch2d.json` → `rows[].j_blind` (7.28e-4 / 7.73e-4 / 1.52e-3), `rows[].j_random` (0.1082 … 0.1135);
`results/continuous_axes.json` → `rows[].j_blind`, `j_random`, `j_truth`;
`results/continuous_cem.json` → `rows[].j_truth_cem`, `rows[].j_blind_cem`;
`results/continuous_synthesis_{mini,large}_xwall8.json` → `j_truth` (17.7628), `j_random` (3.5418e-4), `cells[].j_play` (0.018731).

### Needs a fix

**m3-A — L35, the rewritten abstract, anchor `below the uniform-random policy's return at every rarity knob`.**
Two defects: no raw return, **and the claim is now stronger than the default instruments
support** — on the default cart it holds at 6 of 7 knobs and on the default pendulum at 3 of 6
(`rows[].j_blind` vs `rows[].j_random`); "every knob" is true only of the sharp-plateau variant.
- current: `pinned at the boundary for the whole episode, below the uniform-random policy's return at every rarity knob.`
- proposed: `pinned at the boundary for the whole episode and, once the phantom plateau's tail is removed, below the uniform-random policy's return at every rarity knob ($J_\mathrm{blind} \leq 2.4\times10^{-3}$ against $J_\mathrm{rand} = 0.53$ on the cart, against a truth-planner $17.76$; in the default instruments the leak of that tail leaves the widest knobs above it, Section~\ref{sec:mechanism}).`

**m3-B — L610, anchor `below random at every knob but the largest (0.00 vs 0.53)`.** The numbers
are present but `0.00` is a rounded-away positive mean (also m4-A), so the claim is not checkable.
- current: `scoring below random at every knob but the largest (0.00 vs 0.53)`
- proposed: `scoring below random at every knob but the largest ($J_\mathrm{blind}$ from $1.4\times10^{-5}$ at $x_\mathrm{wall} = 2$ to $1.9\times10^{-2}$ at $8$, against $J_\mathrm{rand} = 0.534$)`

**m3-C — L655, anchor `the same below-random exploitation as the 1D instruments`.** The same
sentence asserts `$J_\mathrm{blind} = 0$ at every cell`, which is false (7.28e-4 … 1.52e-3).
- current: `($J_\mathrm{blind} = 0$ at every cell (the blind planner freezes at a patch edge every episode; $J_\mathrm{rand} = 0.11$), and play\_cost is knob-invariant at $[1.005, 1.006]$ --- the same below-random exploitation as the 1D instruments, now on a 4D plant`
- proposed: `($J_\mathrm{blind} \leq 1.6\times10^{-3}$ at every cell --- the blind planner freezes at a patch edge every episode --- against $J_\mathrm{rand} = 0.11$, and play\_cost is knob-invariant at $[1.005, 1.006]$: the same below-random exploitation as the 1D instruments, now on a 4D plant`

**m3-D — L708, anchor `does not enter MPC's pinned, below-random regime`.**
- current: `CEM contacts $\theta_\mathrm{stop}=0.8$ in 70\% of episodes and $1.0$ in 25\%, but does not enter MPC's pinned, below-random regime`
- proposed: `CEM contacts $\theta_\mathrm{stop}=0.8$ in 70\% of episodes and $1.0$ in 25\%, but does not enter MPC's pinned, below-random regime (blind-CEM returns $16.31$ and $15.89$ against truth-CEM $16.46$ and $16.29$, versus MPC's pinned $J_\mathrm{blind} = 0.012$ and $0.025$ against $J_\mathrm{rand} = 0.058$)`

**m3-E — L747, anchor `(pinned, forever, below random)`.** `tab:axes` has **no** raw-return
column, so this claim is unverifiable from its own table.
- current: `only the hard mode produces the one-way exploitation geometry (pinned, forever, below random)`
- proposed: `only the hard mode produces the one-way exploitation geometry (pinned, forever, and below random: $J_\mathrm{blind} = 1.9\times10^{-5}$ at \texttt{wall@4} and $1.9\times10^{-2}$ at \texttt{wall@8}, against $J_\mathrm{rand} = 0.534$ and $J_\mathrm{truth} = 17.77$)`
- Better and cheap: add `$J_\mathrm{blind}$` and `$J_\mathrm{rand}$` columns to `tab:axes`
  (header L726, rows L728–L733, `{lrrrrr}` → `{lrrrrrrr}`); every value is already in
  `results/continuous_axes.json`.

**m3-F — L1000, conclusion, anchor `exploited to below-random performance`.**
- proposed: `exploited to below-random performance ($J_\mathrm{blind} \approx 0$ against $J_\mathrm{rand} = 0.53$)`

### Needs a decision, not just a number

**m3-G — L878, anchor `performs worse than random`.** In the synthesis section, **the claim is
false against its own campaign's baseline**: the accepted blind artifact scores
`cells[].j_play = 0.018731` while that campaign's `j_random = 0.00035417` (6 episodes, seeds
`900 000 + 1000·i`, `scripts/continuous_danger_synthesis.py:171,385`) — the artifact is ~53×
*above* its own random baseline. `play_cost 0.999` follows only because the denominator
`j_truth - j_random` ≈ `j_truth`. The "worse than random" reading comes from the mechanism
sweep's 20-episode `j_random = 0.534`: a different seed block and a 1500× different baseline.
- current: `This is the discrete headline, synthesized end-to-end in a continuous CWM: a verified, almost-everywhere-exact model that performs worse than random.`
- proposed (also closes m12-B): `This is the discrete headline, synthesized end-to-end in a continuous CWM: a verified model, exact outside the mode region, that recovers $0.019$ of the truth planner's $17.76$ (play\_cost $0.999$) --- below the $J_\mathrm{rand} = 0.534$ of the mechanism sweep's 20 episodes, though not below this campaign's own 6-episode random baseline ($3.5\times10^{-4}$), which is why the sweep's baseline is the comparator we quote.`
- **Escalation:** the 6-episode random baseline is also review critical point 8. If point 8
  re-measures `j_random` on ≥ 20 paired episodes, m3-G folds into it; whoever fixes point 8
  should own this sentence rather than patching it twice.

### Already compliant — leave as is

- L86 (`The blind planner can score \emph{below random} (it is actively exploited)`) — the
  *definition* of the unclamped normalization; no measurement attached. Optional:
  `(measured: Tables~\ref{tab:danger} and~\ref{tab:pendulum})`.
- L612 (`cart $x_\mathrm{wall}=10$: $J_\mathrm{blind} = 0.94$ against $J_\mathrm{rand} = 0.53$`).
- L614 (`$J_\mathrm{blind}$ from $2.3\times10^{-13}$ to $2.4\times10^{-3}$ against $J_\mathrm{rand} = 0.532$`).
- L617, all three occurrences (`$J_\mathrm{blind} = 3.1\times10^{-3}$ against that collapsed baseline`;
  `$J_\mathrm{blind}$ between $4.3\times10^{-4}$ and $7.1\times10^{-4}$ against a surviving $J_\mathrm{rand} \in [0.0572, 0.0584]$`;
  the closing summary of the same bullet).

### Table-level defect behind m3

- `tab:pendulum` (header L631) has **no `$J_\mathrm{rand}$` column**, so its below-random
  reading cannot be checked per row — and per row it is not uniform: `j_random` = 0.0584 /
  0.0597 / 0.0590 / 0.0590 / 0.0590 / 0.0590 against `j_blind` = 0.0119 / 0.0251 / 0.0543 /
  0.1184 / 0.2586 / 1.2259, so only the first **three** knobs are below random in the default
  instrument. Insert `$J_\mathrm{rand}$` after `$J_\mathrm{blind}$`
  (`\begin{tabular}{rrrrrrr}` L630 → `{rrrrrrrr}`, header L631, rows L632–L637).
- `tab:patch2d` (header L662) has neither `$J_\mathrm{blind}$` nor `$J_\mathrm{rand}$`; both
  live only in the caption, where `$J_\mathrm{blind} = 0$` is wrong (m4-G). Add both columns.

---

## m4 [4] — printed zeros must carry `<` or an interval in the row

The global convention is at L574 (anchor `a printed $0$ is a \emph{censored} zero`). A per-cell
reader cannot tell which kind of zero a cell is, and **three** kinds are in fact mixed:

- **(i) censored zero** (no occurrence in a finite sample) → print the Wilson upper bound: `0 [0,0.16]` or `<0.17`;
- **(ii) rounded-away positive value** (the quantity is *not* zero) → print it in exponent form. The convention paragraph does not license these at all, and they currently masquerade as censored zeros;
- **(iii) demonstrated exact zero** (bit-identical returns) → annotate `0 (exact)` so it is not read as censored.

### tab:danger (rows L583–L589)

| ID | Cells | Kind | Actual (`results/continuous_reach.json`) | Proposed cell |
|---|---|---|---|---|
| m4-A | `$J_\mathrm{blind}$` = `0.00`, rows $x_\mathrm{wall}$ = 2,3,4,5,6 (L583–L587) | (ii) | `rows[].j_blind` = 1.38e-5, 1.27e-5, 1.86e-5, 6.29e-5, 3.78e-4 | `1.4e{-}5`, `1.3e{-}5`, `1.9e{-}5`, `6.3e{-}5`, `3.8e{-}4` |
| m4-B | `truth hit` = `0.00`, **all 7 rows** (L583–L589) | (i) | 0/20 episodes | `0 [0,0.16]` (bound already named at L574) |
| m4-C | `d@20` `0.001`→ok, `d@40`/`d@80` = `0.000` (7 cells, L583–L585) | (ii) | `rows[].danger` = 2.48e-7 / 5.96e-14 (wall 2), 6.95e-5 / 4.68e-9 (3), 9.29e-6 (4, d@80) | exponent form |

### tab:pendulum (rows L632–L637)

- **m4-D** `d@40` = `0.000` at $\theta_\mathrm{stop} = 0.8$ (L632). Kind (ii): actual `1.2857e-6`
  (`results/continuous_pendulum.json` → `rows[0].danger["40"]`). Print `1.3e{-}6`.

### tab:patch2d (rows L664–L672)

- **m4-E** `d@40 $P_1$` = `0.0000`, rows `(2,6)`, `(2,7)`, `(2,8)` (L664–L666). Kind (ii): `rows[].d40_p1` = 1.3e-5.
- **m4-F** `d@40 joint` = `0.0000`, same rows. Kind (ii): `rows[].d40_joint` = 9e-6 / 8e-6 / 9e-6.
- **m4-G** caption L670's `$J_\mathrm{blind} = 0$ at every cell`. Kind (ii): 7.28e-4 … 1.52e-3
  → `$J_\mathrm{blind} \leq 1.6\times10^{-3}$`.

### tab:cem (rows L691–L701)

- **m4-H** `pc CEM` = `0.000` on the 5 cart rows (L691–L695). Kind (iii): `play_cost_blind_cem`
  is exactly `0.0` and `play_cost_blind_cem_paired.per_seed` is `[0.0]*20` — bit-identical
  truth/blind returns. Print `0 (exact)`. The prose at L708 says "bit-identity"; the table does not.
- **m4-I** `pc CEM` = `0.000` at pendulum 2.0 (L701). Kind (ii): actual `4.96e-4` → print `0.0005`.
  As printed it reads as the same fact as the cart rows, and it is not.
- **m4-J** `contact CEM` = `0.00` in 9 rows (5 cart + pendulum 1.2/1.4/1.6/2.0). Kind (i): 0/20 → `0 [0,0.16]`.
- **m4-K** `crossing CEM` = `0.0000` at cart 8.0 and 10.0 (L694–L695). Kind (i), and
  **load-bearing**: the paper's only rigorous instantiation of the low-reach branch of
  `prop:playcost` rests on these two cells being *exactly* zero. Denominator, read from
  `scripts/continuous_cem.py` + `src/cwm/continuous/cem.py::plan_cem`: one plan per episode ×
  `n_iters = 5` × `n_samples = 64` = 320 sampled imagined trajectories per episode, 20 episodes
  ⇒ **0 / 6400**. Print `0/6400` with the exact upper bound;
  `scripts/cem_crossing_bound.py` (assigned to review point 7) should emit it, and the cell
  should quote that bound instead of `0.0000`.

### tab:axes (rows L728–L733)

- **m4-L** `pass@40 measured` = `0.000` in 3 rows (bias ×2.0 L731, bump amp 0.5 L732, bump amp 1.0 L733).
  Kind (i): 0/300 gates; `results/continuous_axes.json` → `rows[].pass_rate_ci` = `[0.0, 0.012643]`.
  Print `0 [0,0.013]`.
- **m4-M** `play\_cost` = `0.000` in 3 rows (L730–L732). Kind (iii): exactly `0.0`, because
  `j_blind == j_truth` bit-for-bit for those arms. Print `0 (exact)`.
- **m4-N** `d@40` = `0.0000` in 3 rows (L730–L732). Kind (iii), being `play_cost × (1-r)^40` with
  `play_cost = 0`. Print `0 (exact)`.
- **m4-O** `$(1-r)^{40}$` = `0.0000` for bias ×2.0 (L731). Its *input* is a censored complement:
  reveal-rarity `1.0000` is 20 000/20 000 with `rarity_ci = [0.99981, 1.0]`. Print the rarity
  cell as `1.0000 [0.9998, 1]` and this cell as `<10^{-5}`.

### tab:eps-sweep (rows L757–L761)

- **m4-P** `bias $\times$1.03 rarity` = `0.0000` at ε = 10⁻², 0.1, 0.3 (L759–L761). Kind (i):
  0/2000 rollouts → `[0, 0.0019]`, exactly the bound named at L574. Print `<0.002`.

### tab:pendulum-synthesis (rows L902–L906)

- **m4-Q** the stall counts `(0)` in 4 rows (L902–L905) — kind (i): 0/11, 0/11, 0/20, 0/20 →
  print e.g. `0 of 11 [0,0.26]`; and the `$0 \to$ ---` cells in the two caught-knob rows
  (L904–L905) — kind (i): 0/20 mode-absent seeds → `0 [0,0.16] \to$ ---`. The caught-knob zero
  is the paper's only evidence that the identifiability event "essentially never fires" there,
  so it needs its bound most.

**Follow-on for the convention paragraph (L574).** Once the rows carry their own bounds, keep
the sentence that names the three bounds but delete `We do not restate this at each cell`, so
the convention stops being load-bearing — which is the review's actual request.

---

## m5 [5] — four-decimal values the sample cannot resolve

`tab:patch2d` is measured on **600** rarity rollouts (`results/continuous_patch2d.json` →
`params.rollouts = 600`), so the resolution is `1/600 = 0.001667`: the third decimal is the last
one the sample can move and the fourth is an artifact of the division. Counts recovered from the
JSON (`round(r*600)`):

| Column (header L662) | Printed values | Count / 600 | Resolution | Wilson 95% (JSON key) | Proposed print |
|---|---|---|---|---|---|
| `$r_1$` | 0.2450 / 0.1417 / 0.0883 / 0.0850 | 147 / 85 / 53 / 51 | 0.0017 | `[0.212,0.281]`, `[0.116,0.172]`, `[0.068,0.114]`, `[0.065,0.110]` (`rows[].r1_ci`) | 3 decimals: `0.245` / `0.142` / `0.088` / `0.085`, CI in the row or a `k/600` column |
| `$r_2$` | 0.0100 / 0.0083 / 0.0067 | **6 / 5 / 4** | 0.0017 | `[0.0046,0.0216]`, `[0.0036,0.0194]`, `[0.0026,0.0170]` (`rows[].r2_ci`) | `6/600`, `5/600`, `4/600` — a 4-decimal print of a 4-count is indefensible; its CI spans a factor of ~6.5 |
| `$r_\cup$` | 0.2517 / 0.2533 / 0.1500 / 0.1483 / 0.0917 / 0.0950 / 0.0933 | 151 / 152 / 90 / 89 / 55 / 57 / 56 | 0.0017 | `rows[].r_either_ci` | 3 decimals |
| `d@40 $P_1$`, `d@40 $P_2$`, `d@40 joint` (27 cells) | 4 decimals | inherit the above | — | — | 2 significant figures + interval (m6) |

The paper concedes part of this in prose at L655 (anchor
`the four-decimal \texttt{d@40} figures in the $P_2$ and joint columns inherit that resolution`),
but only for `P_2` and `joint`, and only in prose. Extend the concession to `$r_1$`, `$r_2$`,
`$r_\cup$` and `d@40 $P_1$`, and move it into the **cells**.

**Second site, different table — m5-B: `tab:axes`, `reveal-rarity` = `0.0001` for the sub-ε bias
arm (L730).** Actual `rows[2].rarity = 0.00015` (3/20 000; `rarity_ci = [5.10e-5, 4.41e-4]`), so
`0.0001` rounds a 3-count *down* by a third. Print `1.5\times10^{-4}` or `3/20{,}000`, with the CI.

**Checked and fine — no change:** the other `tab:axes` rarities (20 000 rollouts, resolution
5e-5); `tab:danger`/`tab:pendulum` rarities (30 000, resolution 3.3e-5); `tab:eps-sweep`
(2000 rollouts, printing 0.0125 = 25/2000 and 0.0040 = 8/2000, both exactly representable).

---

## m6 [6] — every `d@N` needs an interval (it mixes two uncertainties)

`d@N = play_cost · (1-r)^N` multiplies **rarity** uncertainty by **play-cost** uncertainty. The
paper prints 60 `d@N` cells and exactly **one** interval anywhere (L655: `d@40 P_2 = 0.7700` is
`[0.51, 0.91]`, and that one is rarity-only).

| Table | Header | Columns | Cells |
|---|---|---|---|
| `tab:danger` | L581 | `d@20`, `d@40`, `d@80` | 21 |
| `tab:pendulum` | L631 | `d@40` | 6 |
| `tab:patch2d` | L662 | `d@40 $P_1$`, `d@40 $P_2$`, `d@40 joint` | 27 |
| `tab:axes` | L726 | `d@40` | 6 |
| prose L641 | `every d@40 a number rather than a bound` | claim to re-scope | — |
| prose L655 | the single existing interval | keep, extend | — |

**Available today:** the rarity half — `rows[].rarity_lo/rarity_hi` (reach, pendulum),
`rows[].rarity_ci` (axes), `rows[].r1_ci/r2_ci/r_either_ci` (patch2d).

**NEEDS-MEASUREMENT — the play-cost half.** `src/cwm/continuous/harness.py::play_cost` returns
`j_truth`, `j_blind`, `j_random` as *means* and **discards the per-episode returns**, so no
interval on `play_cost` is derivable from any current MPC JSON. Required change (shared with m9):

1. `harness.play_cost` retains `per_seed = [{seed, ret_truth, ret_blind, ret_random}, …]`;
2. it emits a seed-paired interval exactly as `scripts/continuous_cem.py::paired_play_cost_ci`
   already does for CEM (that function is the template: normalized per-seed differences with a
   common aggregate denominator, so the interval centre equals the published ratio-of-means);
3. `continuous_reach.py`, `continuous_pendulum.py`, `continuous_patch2d.py`,
   `continuous_axes.py` write `play_cost_ci` **and** `danger_ci` per row and per `N`, computed
   as `[pc_lo·(1-r_hi)^N, pc_hi·(1-r_lo)^N]` (`d@N` is monotone in both factors, so the corner
   product is the interval), so `scripts/audit_paper2_numbers.py` can re-derive the printed
   intervals instead of re-deriving bare point values.

All four are CPU-only re-runs (≈2.5 min, ≈2 min, ≈1 min, ≈3 min) with **no LLM spend**.
Interim, if (3) is deferred: print `d@N` to 2 significant figures with the **rarity-only**
interval and say exactly that in the caption. Do not keep 4 decimals with no interval.

---

## m7 [7] — figures lacking uncertainty bands

From `scripts/make_paper2_figures.py` (which reads the JSONs directly, so bands are a plotting
change, not a data change):

| Figure | Label | Quantity plotted | Band needed on | Data available today? |
|---|---|---|---|---|
| `danger_threshold.pdf` | `fig:threshold` L600 | `play_cost·(1-r)^N` vs `rarity`, N = 20/40/80 | both axes: x from the rarity Wilson interval, y from rarity **and** play-cost | x: **yes** (`rarity_lo/hi`); y: **partly** — needs `play_cost_ci` (m6) |
| `reach_mechanism.pdf` | `fig:reach` L607 | `blind_contact_rate` (1.00), `rarity`, `truth_contact_rate` (0.00) | all three curves — the two contact curves are 20-episode proportions and are exactly the saturated/censored cells of m4-B | **yes**: `rarity_lo/hi` + `cwm.law.wilson_ci(hits, 20)`. The 1.00 and 0.00 curves must be drawn as one-sided bounds ([0.84,1] and [0,0.16]), not as flat lines |
| `axis_separation.pdf` | `fig:axes` L744 | x = `predicted_pass` = (1-r)^40, y = `play_cost` | x from `rarity_ci`; y from a paired play-cost interval | x: **yes**; y: **no** (m6). Also `FLOOR = 1e-4` plots measured zeros *at* 1e-4 — replace with left-pointing upper-bound arrows so a censored zero looks censored (this is m4 in figure form) |
| `smooth_localization.pdf` | `fig:smooth` L962 | `off_mode_max` bars, log scale | MLP bars need seed-to-seed spread; the linear-LSQ bars are deterministic given the sample but vary across gate samples | **no**: `results/continuous_smooth_probe.json` holds one fit per cell (`rows[]` has no per-seed field). Needs `scripts/continuous_smooth_probe.py` re-run over ≥ 10 training seeds / gate samples writing `off_mode_max_per_seed`. Also the `synthesized code` bar is drawn at `1e-16` as a stand-in for exact 0 — annotate it as an exact zero (kind (iii)), not a measured value |

Priority: `fig:reach` and the x-axes of `fig:threshold` / `fig:axes` can be banded today from
existing keys; the y-axis bands and `fig:smooth` wait on m6/m9 and a probe re-run.

---

## m8 [8a] — are the same episode seeds reused across knobs and planners? (truth from the code)

**Yes, everywhere — and the paper never says so.** Established by reading the code:

1. `src/cwm/continuous/harness.py::play_cost(truth, blind, n_episodes, seed=0, …)` uses
   `sd = seed + 1000 * i` and runs the **truth planner, the blind planner and the random policy
   on that same `sd`** → the three arms are seed-paired within a row.
2. Every sweep passes the *same* `seed` at every knob: `scripts/continuous_reach.py:48`,
   `scripts/continuous_pendulum.py:48`, `scripts/continuous_patch2d.py:84` all call
   `harness.play_cost(..., seed=args.seed)` inside the knob loop, and `--seed` defaults to `0`
   ⇒ the episode seeds are `{0, 1000, …, 19000}` at **every knob and on every instrument**.
3. `scripts/continuous_mitigation.py:44` uses the same `sd = args.seed + 1000*i` for
   truth / blind / mitigated / random ⇒ mitigation rows are paired with the mechanism rows.
4. `scripts/continuous_cem.py::run_cem_row` uses `sd = seed + 1000*i` too, and asserts
   `cem_s0 == mpc_s0` before the crossing diagnostic ⇒ **CEM and MPC share the episode seeds and
   the initial states**, so `pc MPC` and `pc CEM` in `tab:cem` are paired columns.
5. Rarity streams are shared as well: `harness.rarity(truth, n, seed)` uses `seed + i` and the
   sweeps pass `seed = args.seed + 50_000` at every knob ⇒ the rarity estimates across knobs
   come from **one common stream of 30 000 rollouts** (identical `x_0` and action sequences;
   only post-clamp trajectories differ), so the rarity column is a nested family, not seven
   independent samples. Any statement about the *shape* of the rarity curve inherits this.
6. The synthesis campaign uses a different, also shared, block: play episodes and both baselines
   use `sd = 900_000 + 1000*i` over 6 episodes
   (`scripts/continuous_danger_synthesis.py:171, 385`), while the gate sample uses
   `10_000*(i+1+offset)` (already documented at L870/L872).

**Where `main.tex` should state it — 3 additions:**

- **Primary — Section `sec:planner`, right after the `play_cost` display (anchor
  `all measured in the true environment on paired seeds`, L86):**
  `Pairing is exhaustive and worth stating: episode $i$ uses seed $1000i$ for the truth planner, the model planner and the random policy alike, and the \emph{same} 20 seeds are reused at every knob, on every instrument, and by both planner families (\texttt{src/cwm/continuous/harness.py}, \texttt{scripts/continuous\_cem.py}), so knob-to-knob and MPC-vs-CEM differences carry no seed noise. The rarity sweeps likewise share one rollout stream across knobs (\texttt{seed + 50{,}000}), so the rarity column is a nested family rather than an independent sample per knob. The synthesis campaign uses its own shared block (seeds $900{,}000 + 1000i$).`
- **Section `sec:cem`, in the paragraph introducing the crossing columns (anchor
  `one plan from the same paired initial state per episode seed`, L682):** append
  `--- the same episode seeds as the MPC rows of Tables~\ref{tab:danger} and~\ref{tab:pendulum}, so the two planner families are compared on identical episodes`.
- **Section `sec:limitations`, in the shared-sample paragraph (anchor
  `The gate sample is drawn from the seed index alone`, L983):** add the play-side counterpart —
  the 20 play episodes are one shared seed block, so play-side conclusions rest on 20 paired
  episodes, not on 20 independent instrument draws.

---

## m9 [8b] — the seed pairing must enter the analysis

**Where pairing already enters an interval — 2 sites, both CEM:** L708
(`the seed-paired 95\% t-interval includes zero on all 11 rows`) and L712 (the PatchField2D CEM
rows), computed by `scripts/continuous_cem.py::paired_play_cost_ci`, stored at
`results/continuous_cem.json` → `rows[].play_cost_blind_cem_paired`
(`per_seed`, `sd`, `se`, `t95`, `excludes_zero`).

**Where it must enter and does not — 5 sites (NEEDS-MEASUREMENT):**

1. `tab:danger` `play_cost` column (7 rows) — currently a bare ratio of means.
2. `tab:pendulum` `play_cost` column (6 rows).
3. `tab:patch2d` `play_cost` column (9 rows), and the `$[1.005,1.006]$` knob-invariance claim at L655.
4. `tab:mitigation` (L800) `pc\_blind` vs `pc\_mit` — the headline collapse, and the site where
   pairing is worth most: blind and mitigated episodes run on the *same* seeds
   (`scripts/continuous_mitigation.py:44`), so a paired interval on `pc_blind - pc_mit` is
   strictly stronger than two point estimates, and it is currently unreported.
5. `tab:patch2d-mitigation` (L862) `pc\_mit`, plus the `7/20` lock-in count (that one needs a
   binomial interval, not a paired one).

Blocking code fact is the same as m6 (`harness.play_cost` returns means only). Recommended:
lift `paired_play_cost_ci` out of `scripts/continuous_cem.py` into
`src/cwm/continuous/harness.py` so all sweeps share one implementation and
`scripts/audit_paper2_numbers.py` has one key name to check.

---

## m10 [9a] — `J_truth` called "optimal"

5 occurrences of "optimal"; 2 need work, 1 is correctly scoped, and 2 (both on one line) are an unrelated sense.

**m10-A — L75, anchor `the truth planner's optimal play differs qualitatively`.** The only place
the *truth planner's* play is called optimal, and it is not: with the derived normalizers
`J_max ≤ 18.0359` at `x_wall = 8`, against which the paper's own L347-area text puts the
measurement at 98.5 % of the ceiling.
- current: `(c) the truth planner's optimal play differs qualitatively --- it goes left.`
- proposed: `(c) the truth planner's preferred play differs qualitatively --- it goes left (as does the return-maximizing policy of Proposition~\ref{prop:normalizers}; the truth planner is MPC with the true model and is not claimed to be optimal).`

**m10-B — L353, anchor `because the optimal policy really is`.** Here "optimal" is *earned* —
push-left attains the proved upper bound `\bar J` to within 2e-7 — but it sits two lines from
`J_truth` and the adjective transfers. Keep the claim, name the subject:
- current: `The bound is not merely valid but essentially attained, because the optimal policy really is ``push left and stay''`
- proposed: `The bound is not merely valid but essentially attained, because the \emph{return-maximizing} policy --- not to be confused with the truth planner, which is MPC with the true model --- really is ``push left and stay''`

**Leave as is:** L710 (`not a claim that CEM is globally optimal` — correctly scoped) and the two
uses on L816/L819 (`A covering number counts an \emph{optimal} cover, and the planner is not
optimal`), which are about covers, not returns. Re-check with `grep -n "optimal" main.tex` after
editing: this count moved between scans (5 → 3 → 5) as the surrounding prose was rewritten.

**Adjacent, recommended:** L349, anchor `the truth planner near the ceiling` — add the measured
slack (`98.5\% of it at $x_\mathrm{wall} = 8$`) so "near the ceiling" reads as a measurement
rather than an optimality claim.

---

## m11 [9b] — "truth planner" needs its definition at first use

12 occurrences (L75, L86, L349, L363, L379 ×3, L474, L574, L606, L641, L741); none says what it
is. Two additions suffice:

- **First use, L75:** covered by the m10-A replacement, which introduces the clarification
  parenthetically.
- **The definition — Section `sec:planner`, L86, anchor
  `are the returns of the truth-planner, the model-planner`:**
  `are the returns of the \textbf{truth planner} (the \emph{same} random-shooting MPC of this section, planning on the true model --- a strong reference policy, not an optimal one: its return sits at $98.5\%$ of the ceiling derived in Proposition~\ref{prop:normalizers}), the model planner (written $J_{\mathrm{blind}}$ in the tables when the model is the blind one), and the uniform-random policy, all measured in the true environment on paired seeds.`
- With that in place the table captions and figure captions that lean on the term
  (`tab:pendulum` caption `truth planner untouched by the mode`; `fig:reach` L606) can be left alone.

---

## m12 [10] — "almost-everywhere exact" → "exact outside the mode region"

The mode has *small but positive* measure — the paper's own `prop:epsrate` bounds
`P(0 < D ≤ ε) ≤ Cε²` and `rem:densitygeneral` is a volume ratio — so "almost everywhere",
which means "up to a null set", is wrong. 2 occurrences:

**m12-A — L43, introduction, anchor `is (in a precise sense) almost-everywhere correct`.**
- current: `a model that passes a sampling gate cleanly, is (in a precise sense) almost-everywhere correct, and is still exploited catastrophically by the planner that trusts it.`
- proposed: `a model that passes a sampling gate cleanly, is \emph{exact outside the mode region} (bit-exact there by construction --- the region itself has small but positive measure, not zero), and is still exploited catastrophically by the planner that trusts it.`

**m12-B — L878, anchor `a verified, almost-everywhere-exact model`.** Fold into the m3-G
replacement above (`a verified model, exact outside the mode region, that …`).

**The rewritten abstract is clean** — it now says `confining it \emph{exactly} requires a
discontinuity` and no longer uses "almost everywhere"; no change needed there. Wording already
correct and worth matching: `bit-exact off-mode by construction` (L74), `exact \emph{off} the
mode` in `prop:epsinv`, `off-mode err mean / max` in `tab:smooth`.

Sibling file (out of scope, flagged): `docs/paper2/preprint-draft.md` lines 24 and 273.

---

## m13 [11] — rarity is a rollout-level probability, not a region volume

The formal definition is already rollout-level (`prop:gatemiss`: `Let $R$ be any measurable set
of rollouts … with $r = P_\rho(R)$`), but every *use* invites the volume reading, and the paper
puts a genuine volume right next to it — the disc patch is `${\approx}1.2\%$ share of the probed
box` (L922) while `r_2 ≈ 0.008`. Two additions:

- **At the definition — `sec:theory`, "Measure-space setup" paragraph (L103, anchor
  `The \emph{query-hit probability} $q_{\mathrm{hit}}(E)$`), immediately before or after that
  sentence:**
  `Two probabilities here are easy to mistake for volumes and are neither: the rarity $r = P_\rho(R)$ is the probability that \emph{one rollout} enters the critical region at some step, and $q_{\mathrm{hit}}$ is the probability that \emph{one episode} issues a query there. Neither is a measure of the region: a mode of fixed volume can have any rarity in $[0,1]$ depending on where the gate policy goes, and on PatchField2D the far patch occupies ${\approx}1.2\%$ of the probed box while its rarity is ${\approx}0.008$.`
- **At the knob's introduction — L75, anchor `the wall position is the \textbf{rarity knob}`** —
  the strongest site, because moving the wall changes the *reachability* of a region whose size
  is unchanged:
  `the wall position is the \textbf{rarity knob} ($r$: the probability that a single uniform-random rollout fires the mode at some step --- a rollout-level probability, not the mode region's volume, which the knob barely changes; $r$ sweeps $0.317 \to 0.0024$ over $x_\mathrm{wall} \in [2, 10]$; Table~\ref{tab:danger})`.
- Third site, no change needed: the operational definition of reveal-rarity in `sec:axes`
  (`P(a random rollout contains a transition where truth and model differ $> \varepsilon$)`) is
  already rollout-level and correct.

---

## m14 [12] — `mu_query` → `q_hit(E)`: **rename already applied, 2 residues**

**PARTIAL** — a concurrent edit landed during this scan. Verified against the scan of record:
`grep -c "mu_" main.tex` → **0**; `grep -o "q_{\mathrm{hit}}" main.tex | wc -l` → **14**
(the L103 definition, `prop:playcost`'s statement, `cor:playcost`'s two displays, the
saturation discussion, and the surrounding proof text). The definition now also carries the
clarification the review asked for: `It is a hitting probability --- monotone and subadditive in
$E$, but not a measure --- and we name it accordingly rather than calling it a mass, as the
companion paper did` (L103).

**Residues — the word "mass", 2 sites:**

- **m14-A — L82, `sec:planner`, anchor `the play-cost upper bound via query-hit mass applies verbatim`**
  → `the play-cost upper bound via the query-hit probability $q_{\mathrm{hit}}$ applies verbatim`.
- **m14-B — L704, `tab:cem` caption, anchor `proxy for query-hit mass`**
  → `proxy for the query-hit probability $q_{\mathrm{hit}}(E)$`.

**Also re-check after editing** (not scanned for this rename): `docs/paper2/abstract-arxiv.txt`
and the figure captions, for any surviving "mass"/`\mu` usage.

---

## m15 [13] — missing front/back matter

**Nothing exists.** `grep -i "acknowledg|funding|conflict|competing interest|data
availability|declaration|ethics|AI use|author contribution"` over `main.tex` returns **0
matches**. The document runs `\maketitle` → abstract → Introduction, and ends `\appendix`
(L1002) → `Reproducibility` → `\bibliography` (L1104).

Proposed placement: an unnumbered section after the Conclusion and immediately **before**
`\appendix` (L1002) — where most venues expect it, and where the anonymization switch of m16 is
easiest to flip:

```latex
\section*{Declarations}

\paragraph{Funding.} <e.g. This work received no external funding; compute was self-funded.>

\paragraph{Competing interests.} <e.g. The author declares no competing interests.>

\paragraph{Data and code availability.} All code, the per-seed synthesized artifacts, the
result JSONs behind every table, and the figure-generating and audit scripts are in the
repository cited in Appendix~A; no data other than the generated results is used. The
agent-relayed LLM transcripts are versioned under \texttt{results/}.

\paragraph{Declaration of AI-model use.} The paper's \emph{object of study} is LLM synthesis:
the deployments, API versions and run dates are listed in Section~\ref{sec:synthesis}
(footnote), and each result JSON records its own \texttt{model} field. Separately, AI assistance
was used for <state exactly what: code, experiment scaffolding, prose editing>; the author is
responsible for all claims, and every number in the paper is re-derived from the versioned
JSONs by \texttt{scripts/audit\_paper2\_numbers.py}.
```

Two facts already in the paper that the declarations should point at rather than repeat: the
exact-deployment footnote in `sec:synthesis` and the reproducibility appendix at L1006.

---

## m16 [14] — anonymization: what would break double-blind

Hard identifiers (2):

| # | Line | Text | Note |
|---|---|---|---|
| 1 | L24 | `\author{Javier Aguilar Mart\'in\\ AGILabs (\href{https://javieraguilar.ai}{javieraguilar.ai})}` | name + affiliation + personal domain, three identifiers in one line |
| 2 | L1006 | `All code is at \url{https://github.com/JaviMaligno/code-world-models}` | the repo path contains the author's GitHub handle, and the repo is public (per `docs/paper/ARXIV-SUBMISSION.md`, since 2026-07-19), so it also de-anonymizes through commit history |

Soft identifiers (the self-citation pattern):

- `\citep{aguilar2026verified}` / `\citealp{…}`: **8** citations, plus the `references.bib` entry
  itself (author `Aguilar Mart\'in, Javier`, and a `note` field repeating the same GitHub URL).
- The phrase `companion paper`: **18** occurrences, several in a register that reads as
  same-author (`the companion paper's material-at-cap instrument`, `as the companion paper did`,
  `paper 1's discrete instrument`).
- Forward references to unpublished own work: `paper~3` (2 occurrences).

Mechanical treatment for a double-blind venue:

1. `\author{}` → the venue's anonymous macro; delete the `\href` to the personal domain.
2. L1006 → `Code and all result artifacts are available at an anonymized repository
   (\url{https://anonymous.4open.science/r/...}); the public repository is cited in the
   camera-ready.`
3. Rewrite the 18 `companion paper` mentions in the third person
   (`\citet{aguilar2026verified} established …`) and drop the `paper 1` / `paper~3` trilogy
   framing, which is itself identifying.
4. `references.bib`: keep the citation (public prior work) but strip the repository URL from the
   `note` field — that field is what ties the cited work to this submission's code.
5. Nothing else in the body is identifying: `docs/EXPERIMENTS.md`, `scripts/…` and `src/cwm/…`
   paths are generic.

For arXiv none of this applies — hence the review's phrasing: a per-venue decision, and the
list above is what the switch has to touch.

---

## m17 [15] — the two dangling-reference risks

### (a) The 2026 CWM citation — `lehrach2025cwm` (cited once, at L974, related work)

`docs/paper2/references.bib` declares it
`@inproceedings{…, booktitle = {International Conference on Learning Representations (ICLR)}, year = {2026}, note = {OpenReview id 1UoB7IWiku}, eprint = {2510.04542}}`.

- **Cosmetic:** the key says `2025` while `year = {2026}`, so `plainnat` prints
  "(Lehrach et al., 2026)" against a `2025` key. Worse, **paper 1's copy of the same entry**
  (`docs/paper/references.bib`) is a `@misc` with `year = {2025}` and no venue — the two papers
  currently cite the same work with different years and different venues. Reconcile them.
- **Substantive:** the ICLR 2026 acceptance is **asserted, not verified here** — I made no
  network call (this run has no budget for external calls). Verifiable offline: the arXiv eprint
  `2510.04542` is used throughout the repo and `docs/paper/main.tex` even dates its release to
  2025-10-06.
- **Action:** either verify the ICLR 2026 proceedings entry before submission and keep
  `@inproceedings`, or downgrade to paper 1's `@misc` arXiv form, which always resolves. Nothing
  in paper 2's argument rests on this citation (one appearance, as the paradigm reference), so
  the safe form costs nothing.

### (b) The companion paper — `aguilar2026verified` (cited 9×)

Declared `@misc{…, eprint = {2607.14169}, archivePrefix = {arXiv}, note = {Companion paper
(paper 1). arXiv:2607.14169 … repository: github.com/JaviMaligno/code-world-models}}`.

- **Offline verification:** `docs/paper/ARXIV-SUBMISSION.md` records
  `Status: v2 uploaded to arXiv:2607.14169 on 2026-07-24`, and `docs/paper2/ARXIV-SUBMISSION.md`
  says `Companion paper 1 is arXiv:2607.14169 (currently v2)`. So the reference **resolves and
  is publicly available** — but it is an **unrefereed preprint by the same author**, and paper 2
  leans on it: `prop:gatemiss`'s proof is delegated rather than reproduced (L127, anchor
  `Proved as Proposition~1 of the companion paper`).
- **Actions:** (i) record the availability status in the bib note
  (`preprint, arXiv:2607.14169v2, 2026-07-24`); (ii) **inline the delegated proof** —
  `prop:gatemiss` is two lines (a Bernoulli(`r`) event, `N` i.i.d. draws), so writing it out
  removes the last *proved* claim that depends on an unrefereed work (`prop:playcost`'s coupling
  proof and `prop:ident`'s proof are already reproduced in full); (iii) this overlaps review
  point 21 (`companion-paper dependence removed from the argumentative load-bearing path`) — one
  edit closes both.

### No other citation is at risk

The remaining 19 entries are published books, journals and proceedings: QuickCheck (ICFP 2000),
PAL (ICML 2023), Dreamer (ICLR 2020), MBPO (NeurIPS 2019), objective mismatch (L4DC 2020),
code-as-policies (ICRA 2023), Rubinstein & Kroese (3rd ed.), Paoletti (EJC 2007), Bemporad &
Morari (Automatica 1999), Nagabandi (ICRA 2018), Chua (NeurIPS 2018), Coulom (CG 2006), Kocsis &
Szepesvári (ECML 2006), Wilson (JASA 1927), Alshiekh (AAAI 2018), S-TaLiRo (TACAS 2011), Corso
(JAIR 2021), Rawlings et al. (2nd ed.), Fazeli (IJRR 2017).

---

## p24 (review point 24, asked for explicitly) — "left open" then presented: **already fixed**

The task asked to confirm the contradiction at (then) line 297 —
`covering-number analogues under Lipschitz assumptions are left open (Section~\ref{sec:limitations})`
immediately followed by a paragraph presenting that analogue — and to give the deletion.

**It is already gone in the scan of record.** The entire `\paragraph{What does not transfer.}`
paragraph has been deleted and its surviving content merged into the next paragraph, which now
reads (L381):

```
\paragraph{What the gate \emph{does} certify: the continuous coverage analogue.} The companion
paper's coverage certificates enumerate finite information-set spaces, and continuous state
spaces admit no such enumeration. A covering-number analogue is available in its place, built
from the disagreement ball of Proposition~\ref{prop:lipschitz} and the visitation density of
Remark~\ref{rem:densitygeneral} …
```

`grep -n "left open" main.tex` now returns only two *correct* retrospectives, both saying the
gap was closed — leave both alone:
- L838: `The covering-number analogue that Section~\ref{sec:limitations} once listed as open now appears on \emph{both} sides …`
- L991: `Two gaps that we had listed as open are now closed …`

**Residual check for whoever owns point 24:** `sec:limitations` (L991, anchor
`Coverage certificates transfer, but only to the smooth case`) must not still list the
covering-number analogue as open. In the scan of record it does not — it presents
`prop:coverage` and the 0.933 figure — so p24 is closed end-to-end. If the two "once listed as
open" retrospectives read as process commentary, that is review point 23, not 24.

---

## Cross-item notes for whoever applies these

1. **Three items share one blocking code change.** m6 (`d@N` intervals), m9 (paired analysis)
   and the y-axis bands of m7 all wait on `harness.play_cost` retaining per-episode returns and
   emitting a seed-paired interval. Do it once, re-run the four CPU sweeps
   (`continuous_reach.py`, `continuous_pendulum.py`, `continuous_patch2d.py`,
   `continuous_axes.py`; ≈10 min total, CPU-only, no LLM spend), and three minor points close
   together.
2. **m3, m4 and m5 overlap in the same cells.** `$J_\mathrm{blind}$ = 0.00` is simultaneously a
   missing raw return (m3-B/C), a rounded-away zero (m4-A/G), and in `tab:patch2d` a caption
   claim that is false. Fix per cell, not per item, or the same cell gets touched three times.
3. **Two items are already partly done by a concurrent editor** (m2: abstract + intro + L932;
   m14: the whole rename; p24: the deletion). Re-resolve anchors before editing so a fix is not
   applied twice or a rewritten sentence "fixed" against an old quote.
4. **Nothing here requires an LLM call.** Every number needed either already exists in
   `results/` (keys named per item) or comes from a CPU re-run. No synthesis campaign has to be
   repeated for any minor point.
5. **After editing, run** `PYTHONPATH=src .venv/bin/python scripts/audit_paper2_numbers.py`.
   Any cell whose printed *form* changes (exponent form, added interval, `k/n` counts) may need
   the audit's matcher updated in the same commit, or the audit will fail on the new formatting.
6. **Two findings in this inventory are substantive, not cosmetic**, and should be routed to the
   owners of the critical points rather than filed as minor wording: **m3-G** (the synthesis
   arm's "worse than random" is false against its own 6-episode baseline → review point 8) and
   **m3-A** (the rewritten abstract's "below … at every rarity knob" holds only for the
   sharp-plateau variant → review point 26 / point 25 scope).
