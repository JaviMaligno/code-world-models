# Research Direction — toward a preprint

Status as of 2026-06-24. This doc is the handoff: it captures the research
direction, the validated candidates, and the concrete next steps so work can
resume without re-deriving context.

## Where the project stands

- **MVP loop (perfect information):** synthesize a world model in code → refine
  in sandbox to full-contract transition accuracy 1.0 → MCTS → arena vs a
  large-model LLM-as-policy baseline → cost meter. Implemented for **tic-tac-toe**
  and **Connect Four** via a multi-game registry (`src/cwm/games.py`,
  `CONTRACT_API` + per-game `RULES_TEXT`). 63 tests. Results in
  [EXPERIMENTS.md](EXPERIMENTS.md).
- **Cost gate decided:** running via Azure OpenAI API is trivially cheap
  (~$0.001–0.005/game baseline; synthesis is one-off). No Codex fallback needed.
- **Known-game results:** small-model CWM+MCTS dominates the large model as a
  direct policy (up to 30–0 in Connect Four). The thesis of arXiv:2510.04542
  reproduces — but reproduction alone is NOT preprint-worthy.

## The original contribution we pursued — and the null result

**The gap between "verified" and "correct."** The acceptance gate is
*transition accuracy 1.0 on random-policy trajectories*. The hypothesis was that
MCTS visits a different distribution (search-promising, often OOD) where a
gate-passing world model could still be wrong. We built the measurement harness
(`cwm/gap.py`, `run_gap.py`) and ran it across three knowledge regimes — correct
prior (Gen-TTT 6×6), no prior (army5x5a), wrong prior (Trike) — both with the
rules given (translation) and withheld (`--no-rules`, pure inference).

**Result (2026-06-24): the gap does not appear.** See EXPERIMENTS.md. In every
regime the outcome is binary — either the model produces a globally-correct CWM
(gap ≈ 0) or it fails the gate entirely. There is no "passes the gate but wrong
on the search distribution" case. Diagnosis: for these small, fully-specified
games the random-trajectory sample **identifies** the dynamics — no compact wrong
hypothesis fits 40 random games yet diverges elsewhere (no under-determination).
The gate is not weak; it is identifying. Secondary findings: the binding
constraint is **gate-attainability** (game complexity × model scale; nano fails
army5x5a 5/5), and the whole method leans on the rules being *given* (no-rules
inference collapses to 0% for novel games).

## The pivot — manufacturing under-determination (a "rare-rule" game)

A real gap needs **sample under-determination**: a rule R with
P(R triggers | random play) ≈ 0 but P(R triggers | optimal play) high, on a base
the model *can* synthesize (else it fails the gate and there is no candidate).

**Lead instrument (proposed 2026-06-24, not yet built):** Connect Four (recalled
base → gate passes) + a rarely-reached, planner-forceable instant-win rule, e.g.
"placing the disc that fills the top-centre cell (row 0, col 3) wins." Columns
rarely fill under random play (games end on a 4-in-a-row first) → R is absent
from the 40 training trajectories → a `--no-rules` CWM recalls standard CF and
**omits R** → passes the gate → MCTS on the *true* game forces R → divergence.

Two methodology notes for this experiment:
1. **Headline must be `gap_truth = agreement(D_gate) − agreement(D_truth)`.** A CWM
   that omits R never explores R's region itself, so D_cwm won't diverge; the
   correct-planner distribution D_truth exposes the omission.
2. **Validate empirically first** (as with non-triviality): confirm R fires in
   ~0/40 random games but MCTS-on-truth uses it. Fallback rules if too
   rare/un-forceable: a rule needing a near-full board, or a short advantageous
   tactic on a specific central line.

Variants: `--no-rules` (near-guaranteed omission → clear gap) as the first demo;
`--with-rules` (model is told R but the gate can't verify the rare branch, so a
subtle bug there survives) as the subtler follow-up.

**Proposed solution if the gap appears:** search-guided synthesis — refine the
CWM on the states MCTS actually visits (DAgger/active-learning), and measure how
much it closes the gap.

## Validated candidates (deep-research 2026-06-24)

- **gpt-5.4 knowledge cutoff: 2025-08-31** (snapshot gpt-5.4-2026-03-05).
  Caveat: "post-cutoff = uncontaminated" is NOT a hard guarantee — hence the
  declarative probe, which we ran.
- **Primary anchor: Generalized Chess `army5x5a`** (DeepMind, arXiv:2510.04542,
  Appendix H.5). 5×5 board, win by capturing the opponent's *general*. Probe
  result: gpt-5.4 does NOT know the movesets → clean inference target.
  Known move offsets (from deep-research extraction of the PDF):
  - general:  `[(1,0),(-1,0),(0,1),(0,-1),(0,-2),(0,2)]`
  - infantry: `[(1,0),(2,0),(1,-1),(1,1),(-1,0)]`
  - cavalry:  `[(0,3),(1,2),(2,1),(3,0)]`
  - **OPEN:** exact starting positions / army composition (how many of each
    piece and where) are NOT yet extracted — pull from Appendix H.5 of the PDF
    (https://arxiv.org/pdf/2510.04542) when implementing.
- **Secondary: Generalized Tic-Tac-Toe 6×6 win-4** (Appendix H.4). m,n,k(6,6,4).
  Probe: model knows it → weak anti-recall, use as the correct-prior baseline.
- **Generator: gg-bench** (arXiv:2505.07215, repo `vivek3141/gg-bench`) — mints
  fresh non-contaminated games on demand; safest against contamination; gives N
  games for statistics. Regenerate fresh instances (the released corpus is public).
- **Trike** (Erickson 2020) — partial contamination (knows metadata, confabulates
  mechanics). REAL rules: each turn place a disc of your color on an empty cell
  on the pawn's line (not beyond existing discs), then move the shared pawn onto
  that disc; game ends when the pawn is surrounded; score = your discs adjacent
  to the pawn; no draws. Now elevated from "obscure validation" to the
  **wrong-prior regime** — the most interesting case.
- **Imperfect-information round (separate, with inference function + ISMCTS,
  OpenSpiel):** poker (Kuhn/Leduc) + DeepMind's two imperfect-info novel games
  **Quadranto** (H.8) and **Hand of War** (H.9).

## Non-triviality caveat

Non-triviality confirmed empirically (2026-06-24, `scripts/nontriviality_sweep.py`):
MCTS beats random from both sides on Gen-TTT(6,6,4), army5x5a, and Trike (zero
losses). army5x5a is balanced under strong search (MCTS-vs-MCTS ~P1 2/P2 3/5 draws
over 10 at 800 sims). See EXPERIMENTS.md.

## Next steps (resume here)

DONE (2026-06-24): army5x5a setup defined (paper omits it; we chose our own);
gap harness specced/planned/built subagent-driven (merge 79165bf); 3 ground
truths + sweep + run_gap implemented; gap grid run with-rules AND `--no-rules`.
**Result: null — the gap does not appear** (see EXPERIMENTS.md, and the pivot
section above).

1. **Build the rare-rule instrument** (lead: Connect Four + top-centre instant
   win, run `--no-rules`; headline `gap_truth`). Brainstorm → spec → plan →
   subagent-driven, same as the harness. Empirically validate R's rarity under
   random play and its use by MCTS-on-truth BEFORE the full run.
2. If the gap appears: implement search-guided synthesis (DAgger over the world
   model) and measure how much it closes the gap. If not: the null is definitive
   — write it up (the gate is identifying; gate-attainability is the real axis).
3. Imperfect-information round (poker + Quadranto + Hand of War).
4. **Rethink applications beyond games (open, deliberate brainstorm needed).**
   The Code World Model pattern (LLM synthesizes a verifiable executable model
   from examples + classical planning/checking on top) may transfer to non-game
   domains — e.g. business rules / pricing (connects to the author's real work
   and to the cognitive-debt blog article), workflows, operations/scheduling,
   API behavior modeling. Harder to make publishable (noisy/partial-observability
   dynamics, single-case generalization risk); likely a strong 2nd blog article
   unless a general, clean non-game domain is found. Worth a dedicated
   brainstorm — what is the most valuable, original non-game application?
