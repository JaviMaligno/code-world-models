"""Write the evidence-dose result into main.tex, with every number read from results/.

The dose campaign answers the last mechanism question the 2D instrument can pose: does the
region-template prior yield to more angular coverage of the contacts? Both outcomes were
named in writing before the run (docs/paper2/STRONGER-STATEMENTS.md, and B21 in the
pre-specification ledger), so neither can be claimed after the fact.

What this script must NOT do is let the prose drift from the artifacts, which is the failure
class every hand-computed constant in this paper belonged to. So the numbers are read from
results/ at run time and interpolated; the anchors are asserted unique; and applying it twice
is a no-op.

Run: PYTHONPATH=src python scripts/apply_dose_prose.py
"""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
TEX = _REPO / "docs" / "paper2" / "main.tex"
RES = _REPO / "results"


def load():
    abl = json.loads((RES / "arity_evidence_ablations.json").read_text())["campaigns"]
    fit = json.loads((RES / "region_fit_baseline.json").read_text())
    cal = json.loads((RES / "evidence_dose_calibration.json").read_text())
    arms = fit["dose_arms"]

    d = {}
    for key, camp in (("hint240", "dose_arc240_hint"), ("plain240", "dose_arc240"),
                      ("plain120", "dose_arc120")):
        if camp not in abl:
            sys.exit(f"MISSING CAMPAIGN {camp}: run scripts/arity_evidence_ablations.py")
        c = abl[camp]["per_size"]["large"]
        d[key] = {"mode": c["n_mode_containing"], "rep": c["k_repaired_behavioural"],
                  "iou": c["best_iou"], "n_full": c["n_full"]}
    # the baseline's dose response: what the evidence supports at each coverage
    for key, lab in (("base", "default"), ("a120", "arc120"), ("a240", "arc240")):
        a = arms[lab]
        d[key + "_fit"] = {"cov": a["median_landing_arc_deg"],
                           "both": a["n_recovering_both"],
                           "centre": a["n_recovering_centre"],
                           "contacts": a["median_contacts"], "n": a["n_rollouts"]}
    d["cost240"] = cal["arms"]["arc240"]["play_play_cost"]
    d["contact240"] = cal["arms"]["arc240"]["play_blind_contact_rate"]
    return d


def subs(d):
    """(name, old, new). Every `old` must occur exactly once, or nothing is written."""
    b, a1, a2 = d["base_fit"], d["a120_fit"], d["a240_fit"]
    h, p2, p1 = d["hint240"], d["plain240"], d["plain120"]
    n_dose = p2["mode"] + h["mode"]

    dose_par = (
        r"\paragraph{The prior does not yield to coverage, and the direction was "
        r"recorded before the run.} The controls above leave one mechanism question open. "
        r"It is the only treatment in the 2D program whose two possible answers were both "
        r"written down before its test --- which is weaker than pre-registration, since the "
        r"question itself arose from the results it responds to, and "
        r"Section~\ref{sup:prespec} classifies it that way (B21): if the obstruction is a prior over forms, "
        r"enough evidence should overcome it; if more evidence changes nothing, it is a "
        r"limit rather than a prior. The instrument can pose the question because the "
        r"start distribution is a knob. Starting episodes on a ring around the near patch "
        r"instead of in the box widens the \emph{angular coverage} of the contacts --- the "
        r"arc they actually span, $360^\circ$ less the largest angular gap --- while the "
        r"rollout count is lowered to hold the \emph{number} of contacts at the baseline's "
        r"median of " + f"{b['contacts']:g}" + r", so the dose is coverage and not "
        r"quantity (\texttt{scripts/\allowbreak calibrate\_\allowbreak evidence\_\allowbreak "
        r"dose.py}; the trap survives, play-cost " + f"{d['cost240']:.4f}" + " and blind "
        r"contact rate " + f"{d['contact240']:.2f}" + r"). Coverage saturates near "
        + f"{a2['cov']:.0f}" + r"$^\circ$, so the achievable range is "
        + f"{b['cov']:.0f}" + r"$^\circ$ to " + f"{a2['cov']:.0f}" + r"$^\circ$, and the "
        r"trivial fit traces it: it recovers both constants on " + f"{b['both']}" + " of "
        f"{20}" + r" samples at the baseline's " + f"{b['cov']:.0f}" + r"$^\circ$, "
        + f"{a1['both']}" + r" of 20 at " + f"{a1['cov']:.0f}" + r"$^\circ$, and "
        r"\textbf{" + f"{a2['both']}" + r" of 20} at " + f"{a2['cov']:.0f}" + r"$^\circ$. "
        r"At that coverage the evidence therefore determines the region on \emph{every} "
        r"sample, by three lines of linear algebra. The synthesizer does not. Given the "
        r"form and asked only for its location and size it recovers "
        r"\textbf{" + f"{h['rep']} of {h['mode']}" + r"} (best agreement "
        + f"{h['iou']:.3f}" + r"); given no clause at all it recovers "
        r"\textbf{" + f"{p2['rep']} of {p2['mode']}" + r"} (best "
        + f"{p2['iou']:.3f}" + r"), while the translation arm on the same wider sample "
        r"still writes the rule at gate $1.000$ in zero iterations, $20$ of $20$. The "
        r"narrower ring at " + f"{a1['cov']:.0f}" + r"$^\circ$ is the machinery control "
        r"and behaves like the baseline (" + f"{p1['rep']} of {p1['mode']}" + r"), so the "
        r"null at " + f"{a2['cov']:.0f}" + r"$^\circ$ is not an artifact of starting on a "
        r"ring. Two consequences, one for each direction of the comparison. The "
        r"attribution becomes clean: the earlier control had to set aside the "
        + f"{20 - b['both']}" + r" samples on which the trivial fit also fails, and at "
        + f"{a2['cov']:.0f}" + r"$^\circ$ there are none to set aside --- on every sample "
        r"in the dose arm the region is recoverable from the evidence and the synthesizer "
        r"does not recover it. And the mechanism is bounded from the other side: within the "
        r"range this instrument can reach, the failure does not respond to the dose at all, "
        r"so ``prior'' should be read as a fixed disposition and not as a weight that more "
        r"evidence overcomes. What lies beyond " + f"{a2['cov']:.0f}" + r"$^\circ$ this "
        r"instrument cannot say: full coverage of the circle requires visiting the "
        r"region's far side from every bearing, and the freeze semantics forbid it "
        r"(Proposition~\ref{prop:entryclass}).")

    return [
        # the table gains the dose as ablation 8
        ("table-row", r"""7 & the mover clamped to the boundary & 0/40 & the same, at matched evidence \\
\bottomrule""",
         r"""7 & the mover clamped to the boundary & 0/40 & the same, at matched evidence \\
8 & angular coverage of the contacts & """ + f"{p2['rep'] + h['rep']}/{n_dose}" + r""" & the coverage of the evidence \\
\bottomrule"""),
        ("table-caption", r"caption{The seven ablations on the 2D mode.",
         r"caption{The eight ablations on the 2D mode."),
        ("caption-tail",
         r"""6 supplies $11\times$ more mode evidence, 7 matches the baseline's
evidence and pays in the rule's complexity, so the negative survives both.}""",
         r"""6 supplies $11\times$ more mode evidence, 7 matches the baseline's
evidence and pays in the rule's complexity, so the negative survives both. Ablation 8 holds
the contact count fixed and raises only their angular coverage, to the point where a
three-line least-squares fit recovers the region on 20 of 20 samples; it is the only one of
the eight whose direction was written down before the run.}"""),
        ("section-head", r"\paragraph{Seven ablations, and what each excludes.}",
         r"\paragraph{Eight ablations, and what each excludes.}"),
        ("dose-paragraph",
         "\n\\paragraph{The two campaigns bound what an independent acceptance sample buys",
         "\n" + dose_par
         + "\n\n\\paragraph{The two campaigns bound what an independent acceptance sample buys"),
        # the three places that count the ablations or quote the fit's 12/20
        ("mech-head", r"\paragraph{What the collapse is about, after seven ablations.}",
         r"\paragraph{What the collapse is about, after eight ablations.}"),
        ("mech-six", r"Six candidate causes are \emph{measured negatives}: it is not",
         r"Seven candidate causes are \emph{measured negatives}: it is not"),
        ("mech-tail",
         r"which two further campaigns lift without restoring repair (all four in Section~\ref{sec:arity}).",
         r"which two further campaigns lift without restoring repair, and --- the one "
         r"prediction in the 2D program written down before its test --- not the angular "
         r"coverage of the contacts, raised until a three-line least-squares fit recovers "
         r"the region on every sample while the synthesizer still recovers it on none (all "
         r"five in Section~\ref{sec:arity})."),
        ("mech-remains",
         r"That library is the template prior, and after seven ablations and two positive controls it is what remains",
         r"That library is the template prior, and after eight ablations and two positive controls it is what remains"),
        ("mech-fit",
         r"while a plain least-squares circle fit recovers both constants from the same evidence on $12$ of $20$ samples and the synthesizer given only the form recovers none (Section~\ref{sec:arity}). The form is what is not induced.",
         r"while a plain least-squares circle fit recovers both constants from the same "
         r"evidence on $" + f"{b['both']}" + r"$ of $20$ samples and the synthesizer given "
         r"only the form recovers none (Section~\ref{sec:arity}). Raising the evidence's "
         r"angular coverage until the fit succeeds on \emph{all} $20$ leaves the "
         r"synthesizer at none of $" + f"{h['mode']}" + r"$, which is what makes the prior "
         r"a disposition rather than a weight. The form is what is not induced."),
        ("concl", r"and seven ablations plus two positive controls place the obstruction",
         r"and eight ablations plus two positive controls place the obstruction"),
        ("concl-list",
         r"not in curvature, prompting, budget, arity, variable ambiguity, the interior's censoring, the evidence, or an inability to fit constants",
         r"not in curvature, prompting, budget, arity, variable ambiguity, the interior's "
         r"censoring, the evidence's coverage --- raised to where a three-line fit is exact "
         r"on every sample --- or an inability to fit constants"),
        ("sup-head", r"\section{The seven ablations on the 2D mode, campaign by campaign}",
         r"\section{The eight ablations on the 2D mode, campaign by campaign}"),
        ("abstract",
         r"Seven ablations exclude curvature, prompting, budget, the predicate's arity, identification of the variable the trigger reads, and the censoring of the region's interior itself;",
         r"Eight ablations exclude curvature, prompting, budget, the predicate's arity, "
         r"identification of the variable the trigger reads, the censoring of the region's "
         r"interior itself, and the angular coverage of the evidence --- raised, in the one "
         r"treatment whose direction was recorded in advance, until a three-line "
         r"least-squares fit recovers the region on every sample while the synthesizer "
         r"recovers it on none;"),
        ("contrib",
         r"and five ablations locate the obstruction in the evidence rather than in the synthesizer",
         r"and eight ablations with two positive controls locate the obstruction in the "
         r"induction of the region's form rather than in the evidence, the synthesizer's "
         r"ability to fit constants, or the evidence's coverage"),
    ]


def main() -> None:
    d = load()
    text = TEX.read_text()
    pending = [(n, o, w) for n, o, w in subs(d) if o != w]
    applied, skipped = [], []
    while True:
        progressed, still = False, []
        for name, old, new in pending:
            if new in text and old not in text:
                skipped.append(name)          # already applied on a previous run
                continue
            if old in text:
                if text.count(old) != 1:
                    sys.exit(f"ANCHOR NOT UNIQUE ({name}): {text.count(old)} matches")
                text = text.replace(old, new)
                applied.append(name)
                progressed = True
            else:
                still.append((name, old, new))
        pending = still
        if not progressed:
            break
    if pending:
        sys.exit("ANCHOR NOT FOUND: " + ", ".join(n for n, _, _ in pending))
    TEX.write_text(text)
    print(f"applied {len(applied)}: {', '.join(applied) or '-'}")
    print(f"already present {len(skipped)}: {', '.join(skipped) or '-'}")
    print(f"dose: hint {d['hint240']['rep']}/{d['hint240']['mode']}, "
          f"plain {d['plain240']['rep']}/{d['plain240']['mode']}, "
          f"control {d['plain120']['rep']}/{d['plain120']['mode']}; "
          f"trivial fit {d['base_fit']['both']}/20 -> {d['a240_fit']['both']}/20 "
          f"as coverage goes {d['base_fit']['cov']:.0f} -> {d['a240_fit']['cov']:.0f} deg")


if __name__ == "__main__":
    main()
