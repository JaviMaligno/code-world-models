# Editorial review of paper 3 (writing quality, not mathematics)

Reviewer: OpenAI Codex CLI (gpt-5.6-sol, read-only over the repo); brief:
experienced editor/referee over legibility, flow, paper-vs-process,
abstract/intro coherence, captions, headings — with hard constraints: no
deletion of scientific content for length, no weakening of any claim's
quantifier/scope/evidence label, script/JSON/proposition citations stay.
The mathematical review cycle (REVIEW-CODEX.md) had already converged
(17 → 10 → 5 → 4 → 0) before this cycle began. Full transcripts live
outside the repo; findings are summarized here with triage.

# Round E1 (2026-08-28)

24 findings: 14 MAJOR, 10 MINOR, across six dimensions. Overall verdict
(verbatim): "The paper has a strong red thread ... Its main readability
problem is accumulation rather than lack of focus."

## Triage (2026-08-28, same session — all applied unless noted)

| # | dim | severity | disposition |
|---|---|---|---|
| 1 | process | MINOR | "Measured bitwise, as designed" → direct statement naming prop:harmless |
| 2 | process | MINOR | "the misreading we document (and correct)" → the interpretive rule, with a forward pointer |
| 3 | process | MAJOR | audit paragraph de-ledgered: "committed artifact"/"campaign" → "synthesized artifacts"/"synthesis conditions"; scripts/JSONs kept |
| 4 | process | MINOR | "manufactures, at no extra cost, the experiment H2 needs" → "supplies the contrasts H2 needs" |
| 5 | process | MINOR | intervention sentence recast as a design statement (pre-registration claim kept, chronology narration dropped) |
| 6 | process | MINOR | "One control remained" → what the control establishes |
| 7 | process | MAJOR | "The honest math ledger" heading and its ledger/routes/refutations-are-part-of-the-record language → "Proved and measured bounds on the funnel defect and the direct-entry rate", direct statements of the counterexample and the 91/91 refutation |
| 8 | flow | MAJOR | theory section opens with what it establishes; "Setup." → "Reachable queries define the gate's equivalence class." |
| 9 | flow | MAJOR | the 120-line resolution paragraph split under five scoped lead-ins (factorial invariance / barcode sandwich / counterproductive dose / relative homology / nested boundaries); no content removed |
| 10 | flow | MAJOR | "Limitations and scope" → "Boundary results and limitations" with a roadmap sentence and subsections Empirical scope / Boundary analyses |
| 11 | flow | MINOR | the fence→sensor forward reference expanded into a real transition |
| 12 | flow | MINOR | duplicated prose restatement of prop:query replaced by a bridging sentence |
| 13 | flow | MAJOR | solid-angle block split under three lead-ins (exchangeability bound / isotropic spherical-cap theorem / cube-uniform sharp rate) |
| 14 | terms | MAJOR | first-use expansions (LLM, MPC, CRN, Hugging Face, NSW, RL, tda in caption); protocol sentence defining arm/cell/seed block at the head of the synthesis section |
| 15 | terms | MAJOR | the nested Rips-law sentence recast: measured predictor first, then the exact two-sided sandwich, each clause's evidence status recoverable |
| 16 | terms | MAJOR | cube-uniform passage signposted (why the spherical proof fails / why the clean Gaussian comparison is false / what remains for the product bound) |
| 17 | abstract | MAJOR | "Two results organize the empirics" → "Three principles" (danger-relative-to-reach / repair parameter+sensor bound / mitigation matches dimension and direction); no paragraph breaks added (single-paragraph abstract kept), numbers unchanged |
| 18 | intro | MAJOR | PARTIAL: item 8's heading now carries scope ("A behavioral audit that separates absent, wrong, and unidentifiable structure"); the full re-ordering/re-formatting rejected — the list already follows Name (section) + statement, and the audit's terminal position marks the methodology contribution |
| 19 | intro | MAJOR | "six directions" counting puzzle → the full seven-item list, no count |
| 20 | tables | MAJOR | thin-neck tabular → numbered table with caption, column glossary, provenance, exact/censored notation, \label{tab:thinneck}, cited from prose |
| 21 | tables | MAJOR | fig:dangercurve caption → visual encoding only; tab:dangercurve caption → values+provenance (JSON moved here from the heading); interpretation lives once, in prose; "H1 confirmed --- with the clincher" → scoped heading |
| 22 | tables | MINOR | column glossaries added to tab:mechanism, tab:closedring (tda, present), tab:mitigation (pc_model/pc_mitigated, nerve fence, freedom patch) |
| 23 | tables | MINOR | PARTIAL: applied where duplication was literal (the dangercurve triplet); the other captions' interpretive sentences are not verbatim-duplicated and serve readers landing on the table — left for E2 to re-judge |
| 24 | headings | MAJOR | all seven headings recast to quotable results (Setup / one passer / clincher / methods note / non-separating control / honest math ledger / sensor constant) |

Linter zero after the pass; 33 pages, 0 overfull, 0 dangling refs.
