"""Reorganize docs/paper2/main.tex into a main article plus Supplementary Material.

Review point #22: the manuscript is 50+ pages and mixes the central result with coverage
certificates, CEM, mitigation, epsilon-flatness, normalizer derivations and exhaustive
tables, so a reader cannot tell what the contribution is. The fix is structural, not a
rewrite: whole blocks move behind an \\appendix divider titled "Supplementary Material",
and the main article keeps the six-part arc (problem and estimand -> minimal theory ->
instruments -> LLM experiment with an independent gate -> 1D vs 2D -> limitations).

WHY A SCRIPT AND NOT HAND EDITS. The blocks are 40-100 lines each and every cross-reference
must survive; a scripted move is reviewable (it prints what it moved), idempotent, and cannot
silently drop a paragraph -- it asserts that every byte of every extracted block reappears
exactly once in the output.

BLOCKS ARE LOCATED BY ANCHOR STRINGS, never by line number: other tooling edits the same
file (scripts/apply_table_bounds.py rewrites table cells), so line numbers are stale by
construction. A missing anchor is a hard error.

Run:  PYTHONPATH=src python scripts/restructure_paper2.py --dry-run
      PYTHONPATH=src python scripts/restructure_paper2.py --apply
"""
import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
TEX = REPO / "docs" / "paper2" / "main.tex"

# (name, start_anchor, end_anchor)  -- end_anchor is EXCLUSIVE and must be the first line
# of whatever follows the block in the current file.
MOVES = [
    ("eps-flatness",
     r"\begin{proposition}[$\varepsilon$-invariance of a hard mode's reveal-rarity]",
     r"\begin{proposition}[identifiability; Proposition~3 of \citealp{aguilar2026verified}, transferred]"),
    ("normalizers",
     r"\begin{proposition}[the normalizers, derived]",
     r"\paragraph{What the gate \emph{does} certify: the continuous coverage analogue.}"),
    ("coverage",
     r"\paragraph{What the gate \emph{does} certify: the continuous coverage analogue.}",
     r"\paragraph{What is new: the localization premise is a theorem-shaped obstruction.}"),
    ("detectrate",
     r"\begin{proposition}[smooth localized error is detectable at a rate]",
     r"\section{The mechanism and the threshold law}"),
    ("cem",
     r"\subsection{A second planner family: play\_cost is planner-dependent}",
     r"\section{Axis separation:"),
    ("mitigation",
     r"\section{Mitigation: the exploitation is planner-mediated}",
     r"\section{LLM synthesis:"),
    # --- second wave of moves: the main article's own detail --------------------
    ("multimode",
     r"\begin{remark}[the bracket is tight, and exact factorization is a property of the gate]",
     r"\subsection{The estimand:"),
    ("sharp-plateau",
     r"\paragraph{The residual leak is a reward artifact",
     r"\subsection{Robustness: the same law on a nonlinear plant}"),
    ("eps-sweep",
     r"\textbf{Is $\varepsilon = 0.01$ a special setting",
     r"\section{The exploitation is planner-mediated}"),
    ("crossfamily",
     r"\paragraph{Cross-family spot-checks (two families).}",
     r"\paragraph{Second-instrument robustness"),
    ("artifact-audit",
     r"\paragraph{The mechanism: translation succeeds, induction of the boundary collapses.}",
     r"\paragraph{The gate is all-or-nothing: no partial artifact was accepted.}"),
    ("cert-limitation",
     r"\paragraph{Coverage certificates transfer, but only to the smooth case.}",
     r"\paragraph{play\_cost $> 1$ is a normalization artifact}"),
]

# Where each moved block lands in the supplement, and the heading it gets there.
SUPPLEMENT = [
    ("eps-flatness", r"The reveal-rarity's $\varepsilon$-invariance, and the rate that replaces its threshold",
     "sup:epsflat"),
    ("normalizers", r"The play-cost normalizers, and why knob-invariance is arithmetic",
     "sup:normalizers"),
    ("coverage", r"What the gate does certify: coverage certificates for Lipschitz pairs",
     "sup:coverage"),
    ("detectrate", r"The detectability rate, and the gate's visitation density",
     "sup:detect"),
    ("cem", r"A second planner family: the cross-entropy method", "sup:cem"),
    ("mitigation", r"Planner-side mitigation: distrust-region replanning", "sup:mitigation"),
    ("multimode", r"Multi-mode gates: the sharp bracket, and the measured dependence",
     "sup:multimode"),
    ("sharp-plateau", r"The residual reward leak, and the sharp-plateau variant",
     "sup:sharp"),
    ("eps-sweep", r"The $\varepsilon$-sweep: the axis separation is tolerance-invariant",
     "sup:epssweep"),
    ("crossfamily", r"Cross-family arms, and a fourth artifact class", "sup:crossfamily"),
    ("artifact-audit", r"The 2D artifacts: a code and behavioural audit, and three ablations",
     "sup:artifacts"),
    ("cert-limitation", r"The coverage certificate's scope, stated in full", "sup:certscope"),
]

# Connective sentences inserted at each block's former position, so the main article does
# not simply end mid-argument. Keyed by block name; inserted where the block was.
BRIDGES = {
    "eps-flatness": (
        "The gate's tolerance is not the axis this paper is about, and the reason is worth one "
        "sentence here and a proof in the supplement: because the mode-blind model agrees with "
        "the truth \\emph{exactly} off the mode, the probability that a rollout reveals a "
        "disagreement at tolerance $\\varepsilon$ equals the mode-firing rarity for every "
        "$\\varepsilon$ below the smallest contact disagreement, and in the population the two "
        "agree at a quadratic rate --- proved for the whole semi-implicit family in "
        "Section~\\ref{sup:epsflat}. Tightening $\\varepsilon$ therefore cannot catch a hard "
        "mode, and loosening it does not widen the hole (measured in "
        "Section~\\ref{sec:axes}).\n"),
    "normalizers": (
        "Both normalizers are \\emph{derived} rather than estimated --- explicit numbers valid at "
        "every knob and every policy --- and the knob-invariance of the reported play\\_cost is an "
        "arithmetic consequence of the exploited planner's return rather than an empirical "
        "regularity. Both derivations, with the certificate that the truth planner's own return "
        "is knob-free, are in Section~\\ref{sup:normalizers}.\n"),
    "coverage": (
        "There is a positive counterpart to all of this, and it is worth knowing exactly how far "
        "it reaches. For \\emph{Lipschitz} pairs the gate does certify something: a partition "
        "argument on the deployed cart gate excludes any pair with "
        "$L = \\max(\\mathrm{Lip} f, \\mathrm{Lip}\\hat f) \\leq 5.77$ carrying the wall's error "
        "of $4.2$, with probability at least $1-\\delta$ over the gate's draws. The same "
        "measurement shows why it does not rescue sampling verification: the certified region "
        "carries $1.9\\%$ of the exploited planner's queries. The certificates, their "
        "statistical accounting and that measurement are in "
        "Section~\\ref{sup:coverage}.\n"),
    "detectrate": (
        "The geometry also has a measure counterpart --- smoothness does not merely forbid exact "
        "localization, it forces a gate detection rate, at a Lipschitz constant that must grow "
        "like $N^{1/(d+m)}$ to keep hiding. That proposition, the closed-form visitation density "
        "it consumes, and the three scope conditions that decide what it says about \\emph{this} "
        "instrument are in Section~\\ref{sup:detect}. The short version is the one the "
        "measurements confirm: at comparable amplitude the smooth error is if anything the more "
        "detectable of the two, and its harmlessness comes from play cost rather than from "
        "hiding.\n"),
    "cem": (
        "\\paragraph{Play cost is planner-dependent, and the bound says which direction is "
        "forced.} Proposition~\\ref{prop:playcost} bounds play cost by the planner's query-hit "
        "probability on the disagreement region, so low query reach forces low play cost while "
        "high reach merely permits high cost. A second base planner family (the cross-entropy "
        "method, one fixed configuration) sits at the low-reach end on all eleven knobs of both "
        "1D instruments and on PatchField2D, with play cost statistically indistinguishable from "
        "zero and imagined boundary-crossing strictly below random-shooting MPC's. Limited reach "
        "is not knowledge, and the same search that misses phantom reward can miss real reward; "
        "the rows, the censoring of the two zero-crossing cells and the caveats are in "
        "Section~\\ref{sup:cem}.\n"),
    "mitigation": (
        "\\section{The exploitation is planner-mediated}\n"
        "\\label{sec:mitigation}\n\n"
        "The exploitation measured above is planner-mediated rather than model-mediated, and a "
        "planner-side fix collapses it without touching the model or the gate --- which does "
        "\\textbf{not} contradict the danger law, since the gate still accepts a wrong model and "
        "Proposition~\\ref{prop:ident} is untouched. Distrust-region replanning fences the "
        "positions of the model's refuted predictions and truncates any imagined trajectory that "
        "crosses a fence. On the two 1D instruments a single contact suffices to fence the mode "
        "on all eleven knob rows --- a separation fact rather than a covering one, with a "
        "measured range of validity --- and the mitigation is bit-identical to plain MPC when the "
        "model is right. On a 2D circular mode it degrades and, at the farthest knob, fails "
        "outright in $7$ of $20$ episodes, because its tie-break is an unsigned distance. The "
        "design, the packing bound on its contact cost, the dimensional reading of that bound and "
        "the 2D failure are in Section~\\ref{sup:mitigation}.\n"),
    "multimode": (
        "The bracket is \\emph{sharp} --- its ends are the Fr\\'echet--Hoeffding bounds for "
        "$P_\\rho(R_1 \\cup R_2)$ given the marginals, so no bound in $r_1, r_2$ alone can be "
        "tighter --- and the product form cannot be rescued by a fixed correction: measured at "
        "$50{,}000$ rollouts per knob, the sign of the dependence changes across the grid, "
        "negative at two knobs and positive at another with non-overlapping intervals. A "
        "stratified gate does not buy the product back either. Section~\\ref{sup:multimode} "
        "gives the sharpness argument, the stratification result and the measurements.\n"),
    "sharp-plateau": (
        "One qualification belongs with the claim. At the widest knobs the pinned planner scores "
        "\\emph{above} the uniform-random policy, because the far plateau's sigmoid tail pays a "
        "planner frozen short of it; the exploitation is what the mechanism asserts, and "
        "``below random'' is a property of the reward's shape as much as of the planner. "
        "Narrowing only the phantom plateau removes the tail and makes the strong form hold at "
        "every knob on both instruments, with play\\_cost invariant to $10^{-4}$ "
        "(Section~\\ref{sup:sharp}); we report the default instrument in the main tables and "
        "treat that variant as a robustness check rather than as the headline.\n"),
    "eps-sweep": (
        "\\textbf{The separation does not depend on the tolerance.} A sweep over $\\varepsilon "
        "\\in \\{10^{-9}, \\dots, 0.3\\}$ leaves the mode arms' reveal-rarity flat on all three "
        "instruments while the pervasive-bias arms switch sharply at their own error scale, and "
        "$\\mathrm{pass@}40 \\approx (1-r)^{40}$ continues to hold for the mode arms at every "
        "$\\varepsilon$ in the grid (Section~\\ref{sup:epssweep}). The gate's $\\varepsilon$ is a "
        "pervasive-error dial, not a mode-detection dial: tightening it cannot catch the hard "
        "mode, and loosening it does not widen the hole.\n"),
    "crossfamily": (
        "\\paragraph{Two other model families.} Spot-checks in two further families (Qwen via an "
        "open-router deployment, and Claude relayed through an agent scaffold with "
        "byte-identical pipeline messages; 3 seeds plus a control per instrument, so small-$n$) "
        "separate the two halves of the result cleanly. The mode-absent blind-and-exploited "
        "event fires in \\emph{every} family, as Proposition~\\ref{prop:ident} requires of a "
        "property of the sample. Repair-from-data instead differs in \\emph{mechanism}: GPT-5.x "
        "repairs every revealed clamp exactly, Qwen repairs none and the gate refuses its "
        "superstitious patches, and Claude repairs most through a \\emph{symmetry prior} that "
        "generalizes one-sided evidence into a symmetric pair of boundaries --- which produces a "
        "fourth artifact class the trichotomy does not cover: an artifact accepted at gate "
        "$1.000$ while carrying an \\emph{invented} mode its own sample cannot refute. That is "
        "Proposition~\\ref{prop:ident}'s prior caveat measured directly, and it is why the "
        "paper's off-sample regularity is stated as measured rather than proved. "
        "Section~\\ref{sup:crossfamily} gives the arms, the artifact and the relay caveats.\n"),
    "artifact-audit": (
        "\\paragraph{What the artifacts do instead.} A code inspection of all $76$ artifacts, "
        "confirmed by an independent behavioural audit that probes each \\texttt{step()} on a "
        "state grid, locates the failure: plant translation succeeds in ${\\approx}74/76$, and "
        "what collapses is induction of the region. The dominant class is \\textbf{dimensional "
        "reduction} --- the disc written as a half-plane at the right location and the wrong "
        "shape ($38/76$ by source, $39/76$ by behaviour) --- with pure-blind, superstitious local "
        "patch and failed-disc classes making up the rest, and \\textbf{no artifact encoding its "
        "seen patch} even where one was seen. The $\\varepsilon$-exactness alternative is "
        "falsified: no correct-form disc failed on arithmetic. Two ablations then exclude two "
        "candidate mechanisms. A guided treatment at $3\\times$ budget removes the half-plane "
        "entirely and yields bounded 2D regions instead --- ellipses, rectangles, unions of "
        "micro-discs --- fitted to the \\emph{hull of the observed freeze positions} and, in "
        "$36/40$ artifacts, conditioned on the current rather than the landing position; none is "
        "the true disc. An axis-aligned square with flat edges is not repaired either, and fails "
        "with the errors \\emph{reflected}: discs written on square evidence. A third family "
        "reproduces the same template set. Section~\\ref{sup:artifacts} gives the full audit, "
        "the three ablations and the per-iteration ledger.\n"),
    "cert-limitation": (
        "\\paragraph{The coverage certificate reaches only the smooth case.} What transfers from "
        "the companion paper's enumeration is a covering-number statement for Lipschitz pairs, "
        "and on the deployed cart gate it is informative: no pair with $L \\leq 5.77$ can carry "
        "the wall's error of $4.2$ past the gate on the certified region. The residue is that "
        "this is exactly the case the paper is \\emph{not} about --- a hybrid mode has no finite "
        "local Lipschitz constant, so no $L$ makes the certificate apply to it --- and that the "
        "certified region carries $1.9\\%$ of the exploited planner's queries. "
        "Section~\\ref{sup:certscope} states the scope in full, including what closing the "
        "within-rollout dependence and the step-$t$ density did and did not buy.\n"),
}

DIVIDER = r"""
\appendix

\part*{Supplementary Material}
\addcontentsline{toc}{part}{Supplementary Material}

\noindent The material below supports the main article and is not needed to read it. It
contains the results the main text states in one sentence and cites: the $\varepsilon$-axis
propositions, the derived play-cost normalizers, the coverage certificates and their
statistical accounting, the detectability rate, the second planner family, the planner-side
mitigation, the complete LLM protocol, the reproducibility manifest, and the
pre-specification ledger.
"""


def find(text: str, anchor: str, what: str) -> int:
    i = text.find(anchor)
    if i < 0:
        sys.exit(f"ANCHOR NOT FOUND ({what}): {anchor[:90]!r}\n"
                 f"main.tex has been edited in a way this script does not expect; "
                 f"fix the anchor rather than loosening the match.")
    if text.find(anchor, i + 1) >= 0:
        sys.exit(f"ANCHOR NOT UNIQUE ({what}): {anchor[:90]!r}")
    return i


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", default=str(TEX))
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        args.dry_run = True

    path = pathlib.Path(args.file)
    text = path.read_text()

    if r"\part*{Supplementary Material}" in text:
        print("already restructured (found the Supplementary Material divider); nothing to do")
        return

    blocks: dict[str, str] = {}
    for name, start, end in MOVES:
        i = find(text, start, f"{name} start")
        j = find(text, end, f"{name} end")
        if j <= i:
            sys.exit(f"{name}: end anchor precedes start anchor")
        blocks[name] = text[i:j]
        text = text[:i] + BRIDGES[name] + "\n" + text[j:]
        print(f"  moved {name:<14} {len(blocks[name]):>6} chars "
              f"({blocks[name].count(chr(10))} lines) -> supplement")

    # Every extracted block must reappear exactly once, byte for byte.
    supp = [DIVIDER]
    for name, heading, label in SUPPLEMENT:
        supp.append(f"\n\\section{{{heading}}}\n\\label{{{label}}}\n\n{blocks[name]}")

    # The existing Reproducibility appendix is replaced by the three new appendix files,
    # which the main session \inputs after this divider.
    old_appendix = text.find("\\appendix")
    if old_appendix < 0:
        sys.exit("no \\appendix in the file; expected the Reproducibility appendix")
    end_doc = text.find("\\bibliography{references}")
    if end_doc < 0:
        sys.exit("no \\bibliography{references} line")
    tail = text[end_doc:]
    body = text[:old_appendix]

    inputs = (
        "\n\\section{The LLM protocol, in full}\n\\label{sup:protocol}\n"
        "\\input{appendix-protocol}\n"
        "\n\\section{Reproducibility}\n\\label{sup:repro}\n"
        "\\input{appendix-repro}\n"
        "\n\\section{Pre-specification, and what was added after the result}\n"
        "\\label{sup:prespec}\n\\input{appendix-prespec}\n"
    )

    out = body + "".join(supp) + inputs + "\n" + tail
    for name, blk in blocks.items():
        if out.count(blk) != 1:
            sys.exit(f"{name}: block appears {out.count(blk)} times in the output, expected 1")

    print(f"\nmain body {len(body)} chars, supplement {sum(len(s) for s in supp)} chars")
    if args.apply:
        path.write_text(out)
        print(f"wrote {path}")
    else:
        pathlib.Path("/tmp/main_restructured.tex").write_text(out)
        print("dry run: wrote /tmp/main_restructured.tex (nothing changed in the repo)")


if __name__ == "__main__":
    main()
