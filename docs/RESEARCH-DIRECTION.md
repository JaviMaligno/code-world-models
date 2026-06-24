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

## The original contribution we are pursuing

**The gap between "verified" and "correct."** The acceptance gate is
*transition accuracy 1.0 on random-policy trajectories*. But MCTS visits a
different distribution (search-promising states, often out-of-distribution). A
world model can pass the gate at 100% and still be wrong exactly where planning
needs it. The paper never measured this.

Refined framing (the spine of the preprint) — **three knowledge regimes**,
established empirically via a cold "declarative probe" of gpt-5.4 (ask it the
rules before giving any):

| Regime | Game | gpt-5.4's prior | What it tests |
|--------|------|-----------------|---------------|
| Correct prior | Generalized Tic-Tac-Toe 6×6 win-4 | knows it (m,n,k family) | recall baseline |
| No prior | **Generalized Chess `army5x5a`** | does NOT know the movesets (refused to guess) | clean inference from trajectories |
| **Wrong prior** | **Trike** (Erickson 2020) | knows metadata, **confabulates the mechanics** | the case where the gap should bite hardest |

The hypothesis: where the model has a *wrong* prior (Trike), the synthesized CWM
may inherit the confabulated mechanics and still pass the random-trajectory gate
(coverage doesn't hit the disagreeing states) → coverage gap demonstrated
causally. `army5x5a` measures inference without a prior; Trike measures
inference *against* a wrong prior. Ties directly to the blog article on
cognitive debt: validating on the wrong distribution = false security.

**Proposed solution if the gap exists:** search-guided synthesis — refine the
CWM on the states MCTS actually visits (DAgger/active-learning over the world
model), and measure how much it closes the gap.

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

Non-triviality (no forced first-player win) is NOT proven for Gen-TTT(6,6,4) or
army5x5a. Verify empirically via self-play / MCTS-vs-MCTS before trusting them as
skill discriminators (we already have the tools: a self-play sweep like the one
used to validate Connect Four).

## Next steps (resume here)

1. **Extract army5x5a starting setup** from Appendix H.5 of the PDF.
2. **Mini-spec the gap experiment** (brainstorming → writing-plans → subagent-
   driven, as before): MCTS visited-state logging hook + CWM-vs-ground-truth
   comparison on that distribution, across the three regimes.
3. Implement `army5x5a` and Trike ground truths via the existing multi-game
   registry; verify non-triviality by self-play sweep.
4. Run the gap measurement; if a gap exists, implement search-guided synthesis.
5. Imperfect-information round (poker + Quadranto + Hand of War).
6. **Rethink applications beyond games (open, deliberate brainstorm needed).**
   The Code World Model pattern (LLM synthesizes a verifiable executable model
   from examples + classical planning/checking on top) may transfer to non-game
   domains — e.g. business rules / pricing (connects to the author's real work
   and to the cognitive-debt blog article), workflows, operations/scheduling,
   API behavior modeling. Harder to make publishable (noisy/partial-observability
   dynamics, single-case generalization risk); likely a strong 2nd blog article
   unless a general, clean non-game domain is found. Worth a dedicated
   brainstorm — what is the most valuable, original non-game application?
