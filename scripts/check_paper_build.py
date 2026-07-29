"""Fail the build on the defects a hand-rolled grep misses.

Written 2026-07-29 after two LaTeX warnings went unnoticed for days because the check was
`grep -E "^! |Warning: Citation|Warning: Reference"` -- a filter that only looks where you
already know to look. What it missed:

  * `sec:mitigation` MULTIPLY DEFINED, once in the body and once in the supplement, because
    scripts/restructure_paper2.py inserted a new section header and moved the original one
    without merging. Consequence: a cross-reference in Limitations sent the reader to
    appendix G instead of the body summary. LaTeX warned; nobody read it.
  * an EMPTY section header left behind by the same move.

And one defect LaTeX does not warn about at all, which is the interesting one:

  * a numbered result STATED AND NEVER REFERENCED. Three of the body's thirteen were in that
    state. This is the reviewer's "too many contributions" made mechanical -- a proposition
    that nothing cites is either support that belongs behind the divider, or a claim the
    paper forgot to use.

Run: python scripts/check_paper_build.py [docs/paper2/main.tex ...]
Exit 1 on any finding. An orphan can be declared intentional in the allowlist below.
"""
import collections
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT = [_REPO / "docs" / "paper2" / "main.tex"]

# Numbered results that are deliberately stated without a cross-reference. Each entry needs
# a reason, because "nothing cites it" is normally a defect rather than a style.
ORPHAN_ALLOWLIST: dict[str, str] = {}

LOG_PATTERNS = [
    ("latex-error", re.compile(r"^! (.+)$", re.M)),
    ("multiply-defined", re.compile(r"Label `([^']+)' multiply defined")),
    ("undefined-reference", re.compile(r"Reference `([^']+)' on page \d+ undefined")),
    ("undefined-citation", re.compile(r"Citation `([^']+)' on page \d+ undefined")),
    ("missing-file", re.compile(r"No file ([\w./-]+\.(?:tex|bbl))")),
]
OVERFULL = re.compile(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)")
OVERFULL_TOLERANCE_PT = 0.0          # this paper builds at zero; keep it there


def _expand(tex: pathlib.Path, seen=None) -> str:
    """Inline \\input files so labels defined in them are visible to the checks."""
    seen = seen or set()
    if tex in seen or not tex.exists():
        return ""
    seen.add(tex)
    out = []
    for line in tex.read_text().split("\n"):
        m = re.match(r"\s*\\input\{([^}]+)\}", line)
        if m:
            child = tex.parent / m.group(1)
            if child.suffix != ".tex":
                child = child.with_suffix(".tex")
            out.append(_expand(child, seen))
        else:
            out.append(line)
    return "\n".join(out)


def check(tex: pathlib.Path) -> list[str]:
    findings = []
    src = _expand(tex)

    # --- the log, if the document has been built ---------------------------------- #
    log = tex.with_suffix(".log")
    if not log.exists():
        findings.append(f"{tex.name}: no .log beside it -- build before checking")
    else:
        text = log.read_text(errors="replace")
        for name, pat in LOG_PATTERNS:
            for m in pat.finditer(text):
                findings.append(f"{tex.name}: [{name}] {m.group(1).strip()}")
        worst = [float(m.group(1)) for m in OVERFULL.finditer(text)]
        over = [w for w in worst if w > OVERFULL_TOLERANCE_PT]
        if over:
            findings.append(f"{tex.name}: [overfull] {len(over)} box(es) over "
                            f"{OVERFULL_TOLERANCE_PT}pt, worst {max(over)}pt")

    # --- defects the log does not report ------------------------------------------ #
    dups = {k: v for k, v in collections.Counter(
        re.findall(r"\\label\{([^}]+)\}", src)).items() if v > 1}
    for lab, n in sorted(dups.items()):
        findings.append(f"{tex.name}: [duplicate-label] {lab} defined {n} times")

    # A heading with no content before the NEXT HEADING OF THE SAME OR HIGHER LEVEL.
    # A \section followed straight by a \subsection is ordinary structure, not a defect --
    # the first version of this rule flagged three such sections in paper 1 and was wrong.
    # What it must catch is the wrapper the restructuring script left behind: a \section
    # whose entire content is another \section.
    for m in re.finditer(r"\\(section|subsection)\*?\{([^}]*)\}\s*\n"
                         r"((?:\\label\{[^}]+\}\s*\n)*)\s*\n?"
                         r"(?=\\(section|subsection)\b)", src):
        level, title, _, nxt = m.group(1), m.group(2), m.group(3), m.group(4)
        same_or_higher = (nxt == level) or (level == "subsection" and nxt == "section")
        if same_or_higher:
            findings.append(f"{tex.name}: [empty-section] {title!r} has no content before "
                            f"the next \\{nxt}")

    # a numbered result stated and never referenced
    stated = re.findall(r"\\label\{((?:prop|cor|thm|lem|def|rem|table|fig):[^}]+)\}", src)
    for lab in stated:
        if lab in ORPHAN_ALLOWLIST:
            continue
        if not re.search(r"\\(?:ref|autoref|Cref|cref)\{" + re.escape(lab) + r"\}", src):
            findings.append(f"{tex.name}: [orphan-result] {lab} is stated and never "
                            f"referenced -- cite it where the paper relies on it, move it "
                            f"behind the Supplementary divider, or allowlist it with a "
                            f"reason")
    return findings


def main() -> None:
    targets = [pathlib.Path(a) for a in sys.argv[1:]] or DEFAULT
    findings = []
    for t in targets:
        findings += check(t)
    for f in findings:
        print(f)
    if findings:
        print(f"\n{len(findings)} finding(s)")
        sys.exit(1)
    print(f"clean: {', '.join(t.name for t in targets)}")


if __name__ == "__main__":
    main()
