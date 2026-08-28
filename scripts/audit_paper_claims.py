#!/usr/bin/env python3
"""Lint the LaTeX sources for overclaiming and lab-notebook prose.

Motivation. Two review passes in a row raised the same two classes of defect, and
both were caught by hand: (a) claims whose *scope* is wider than the evidence --
a heading that says "cannot" when the proposition says "cannot, for L-Lipschitz
pairs, up to eta/2L"; (b) research narrative that belongs in a changelog -- "we
got this wrong first", "an earlier draft", "worth recording". Hand review misses
these because they read fine locally; they are only wrong relative to something
else (a proposition's hypotheses, a results JSON, the genre of a paper). This
script does the mechanical part.

Six rules, each independently switchable, each reported with file:line:

  process-prose      first-person research narrative / draft archaeology
  modal-scope        unquantified modal claim in a heading, bold lead-in or abstract
  soundness-scope    "sound"/"certify" without an adjacent scope qualifier
  pooled-inference   a CI in the same sentence as a pooled count
  printed-zero       a table cell that is exactly 0 with no interval/bound/footnote
  hand-constant      a >=3-significant-digit prose number absent from every results JSON

Exit codes
  0  clean, or every rule at or below its recorded baseline
  1  at least one rule above baseline (or, with no baseline file, any error)
  2  usage / configuration error (e.g. an allowlist entry with no justification)

Usage
  PYTHONPATH=src python scripts/audit_paper_claims.py
  PYTHONPATH=src python scripts/audit_paper_claims.py docs/paper2/main.tex --json
  PYTHONPATH=src python scripts/audit_paper_claims.py --baseline   # write the ratchet
  PYTHONPATH=src python scripts/audit_paper_claims.py --strict     # warnings are errors
  PYTHONPATH=src python scripts/audit_paper_claims.py --census     # per-pattern hit counts

The allowlist (docs/paper2/claims-allowlist.txt, or --allowlist PATH) exists so
that legitimate exceptions -- years, page numbers, constants that come out of a
closed form rather than a measurement -- are recorded as data with a written
justification instead of being hardcoded here. Format: one regex (or literal) per
line, optionally prefixed with "<rule-id> :: ", and EVERY entry must be preceded
by a "#" comment line giving the reason. An entry with no justification is a
configuration error, not a silent pass.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass, field

_REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = (
    _REPO / "docs" / "paper2" / "main.tex",
    _REPO / "docs" / "paper" / "main.tex",
    # paper 3 enters the ratchet 2026-08-24: its standing debt is recorded in
    # the baseline (never raise it), so new prose cannot add violations even
    # while the old ones are worked down.
    _REPO / "docs" / "paper3" / "main.tex",
)
DEFAULT_ALLOWLIST = _REPO / "docs" / "paper2" / "claims-allowlist.txt"
BASELINE_PATH = _REPO / "results" / "paper_claims_baseline.json"
RESULTS_DIR = _REPO / "results"
STATISTICS_JSON = RESULTS_DIR / "paper2_statistics.json"

RULES = (
    "process-prose",
    "modal-scope",
    "soundness-scope",
    "pooled-inference",
    "printed-zero",
    "hand-constant",
)


# --------------------------------------------------------------------------- #
# 1. LaTeX source model: comment stripping, zones, sentences                   #
# --------------------------------------------------------------------------- #

_COMMENT = re.compile(r"(?<!\\)%.*$")

# Environments whose bodies are not prose. `tabular` is separated out because
# rule 5 needs it specifically.
_TABLE_ENVS = {"tabular", "tabular*", "tabularx", "array"}
_VERBATIM_ENVS = {"verbatim", "lstlisting", "minted", "Verbatim"}
_MATH_ENVS = {"equation", "equation*", "align", "align*", "gather", "gather*",
              "gathered", "multline", "multline*", "eqnarray", "displaymath"}

_BEGIN = re.compile(r"\\begin\{([A-Za-z*]+)\}")
_END = re.compile(r"\\end\{([A-Za-z*]+)\}")


@dataclass
class Line:
    no: int
    raw: str
    text: str                       # comment-stripped
    zones: frozenset               # subset of {table, verbatim, math, abstract, preamble}


@dataclass
class Unit:
    """A prose sentence, or a heading / bold lead-in, with its source line."""
    text: str                       # LaTeX source of the unit
    line: int
    kind: str                       # sentence | section | subsection | paragraph | textbf | title
    sentence: str                   # the enclosing sentence (== text for kind == sentence)
    zones: frozenset = frozenset()


class TexDoc:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.lines: list[Line] = []
        raw_lines = path.read_text(encoding="utf-8").split("\n")

        env_stack: list[str] = []
        in_display = False           # between \[ and \]
        seen_document = False
        for i, raw in enumerate(raw_lines, start=1):
            text = _COMMENT.sub("", raw)
            if "\\begin{document}" in text:
                seen_document = True

            zones = set()
            if not seen_document:
                zones.add("preamble")
            for env in env_stack:
                if env in _TABLE_ENVS:
                    zones.add("table")
                if env in _VERBATIM_ENVS:
                    zones.add("verbatim")
                if env in _MATH_ENVS:
                    zones.add("math")
                if env == "abstract":
                    zones.add("abstract")
            if in_display:
                zones.add("math")

            # A line that opens a zone is itself outside it; a line that closes
            # one is inside it. Track opens after assigning, closes before.
            opens = _BEGIN.findall(text)
            closes = _END.findall(text)
            for env in closes:
                if env in _TABLE_ENVS or env in _VERBATIM_ENVS or env in _MATH_ENVS:
                    zones.add("table" if env in _TABLE_ENVS else
                              ("verbatim" if env in _VERBATIM_ENVS else "math"))
                if env == "abstract":
                    zones.add("abstract")
                if env in env_stack:
                    env_stack.remove(env)
            for env in opens:
                env_stack.append(env)

            # \[ ... \] display math (single- or multi-line)
            n_open = len(re.findall(r"\\\[", text))
            n_close = len(re.findall(r"\\\]", text))
            if in_display or n_open or n_close:
                zones.add("math")
            in_display = (1 if in_display else 0) + n_open - n_close > 0

            self.lines.append(Line(i, raw, text, frozenset(zones)))

    # -- prose paragraphs ---------------------------------------------------- #

    def _prose_paragraphs(self) -> list[tuple[str, list[tuple[int, int]]]]:
        """[(paragraph_text, [(offset_in_text, source_line), ...]), ...].

        An environment delimiter ends a paragraph: otherwise `\\begin{abstract}`
        would glue the abstract onto the preceding text and its sentences would
        be attributed to the wrong line (and the wrong zone).
        """
        paras: list[tuple[str, list[tuple[int, int]]]] = []
        buf: list[str] = []
        marks: list[tuple[int, int]] = []
        cursor = 0

        def flush():
            nonlocal buf, marks, cursor
            if buf:
                paras.append((" ".join(buf), marks))
            buf, marks, cursor = [], [], 0

        for ln in self.lines:
            body = ln.text.strip()
            # The title is in the preamble but is the highest-risk claim site of
            # all, so it is the one preamble line we keep.
            skip = bool(ln.zones & {"table", "verbatim", "math"}) or (
                "preamble" in ln.zones and "\\title{" not in body)
            if skip or not body:
                flush()
                continue
            core = _STRUCT_RX.sub(" ", body).strip()
            if core != body:                    # opens or closes an environment
                flush()
                if len(core) < 4:
                    continue
                body = core
            marks.append((cursor, ln.no))
            buf.append(body)
            cursor += len(body) + 1
        flush()
        return paras


# \begin{env}{arg} / \end{env}; a trailing [optional] argument is kept, because
# that is where theorem names live (\begin{proposition}[joint gate miss ...]).
_STRUCT_RX = re.compile(r"\\(?:begin|end)\{[A-Za-z*]+\}(?:\{[^{}]*\})*")


_ABBREV = (
    "i.e", "e.g", "cf", "vs", "resp", "al", "etc", "approx", "Fig", "Sec",
    "Eq", "Prop", "Cor", "Thm", "No", "vol", "pp", "ca", "St", "Mr", "Dr",
)
_SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z\\$`(\u201c])")


def split_sentences(text: str) -> list[tuple[int, str]]:
    """[(offset, sentence)], with LaTeX-aware guards against false splits."""
    out: list[tuple[int, str]] = []
    start = 0
    for m in _SPLIT.finditer(text):
        head = text[start:m.start()]
        tail_word = re.search(r"([A-Za-z.]+)\.$", head.rstrip())
        if tail_word and tail_word.group(1).rstrip(".").split(".")[-1] in _ABBREV:
            continue
        if re.search(r"\b[A-Za-z]\.$", head.rstrip()):  # single-letter initial
            continue
        out.append((start, head.strip()))
        start = m.end()
    out.append((start, text[start:].strip()))
    return [(o, s) for o, s in out if s]


def _line_for(marks: list[tuple[int, int]], offset: int) -> int:
    idx = bisect.bisect_right([m[0] for m in marks], offset) - 1
    return marks[max(idx, 0)][1] if marks else 0


def brace_arg(text: str, open_idx: int) -> tuple[str, int]:
    """Balanced {...} starting at text[open_idx] == '{'. Returns (body, end)."""
    depth = 0
    for j in range(open_idx, len(text)):
        c = text[j]
        if c == "{" and (j == 0 or text[j - 1] != "\\"):
            depth += 1
        elif c == "}" and text[j - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:j], j
    return text[open_idx + 1:], len(text)


_HEADING_CMDS = ("section", "subsection", "subsubsection", "paragraph",
                 "subparagraph", "title")


def units(doc: TexDoc) -> list[Unit]:
    """Sentences plus the high-risk spans (headings, bold lead-ins) inside them."""
    out: list[Unit] = []
    for text, marks in doc._prose_paragraphs():
        for offset, sent in split_sentences(text):
            line = _line_for(marks, offset)
            zones = doc.lines[line - 1].zones if 0 < line <= len(doc.lines) else frozenset()
            out.append(Unit(sent, line, "sentence", sent, zones))
            for cmd in _HEADING_CMDS:
                for m in re.finditer(r"\\" + cmd + r"\*?\s*\{", sent):
                    body, _ = brace_arg(sent, m.end() - 1)
                    out.append(Unit(body, line, cmd, sent, zones))
            for m in re.finditer(r"\\textbf\s*\{", sent):
                body, _ = brace_arg(sent, m.end() - 1)
                if len(strip_latex(body).split()) >= 4:      # a lead-in, not \textbf{156}
                    out.append(Unit(body, line, "textbf", sent, zones))
    return out


_STRIPPERS = (
    re.compile(r"\\(?:label|ref|eqref|cite[a-z]*|url|includegraphics|input|bibliography"
               r"|bibliographystyle|texttt|verb)\s*(\[[^\]]*\])?\{[^{}]*\}"),
    re.compile(r"\\allowbreak"),
    re.compile(r"\\[A-Za-z@]+\s*"),
    re.compile(r"[{}$~^_&\\]"),
)


def strip_latex(text: str) -> str:
    out = text
    for _ in range(3):
        out = _STRIPPERS[0].sub(" ", out)
    for rx in _STRIPPERS[1:]:
        out = rx.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


# --------------------------------------------------------------------------- #
# 2. Findings and the allowlist                                                #
# --------------------------------------------------------------------------- #

@dataclass
class Finding:
    rule: str
    file: str
    line: int
    severity: str                   # error | warning
    message: str
    excerpt: str
    pattern: str = ""

    def as_dict(self) -> dict:
        return {
            "rule": self.rule, "file": self.file, "line": self.line,
            "severity": self.severity, "message": self.message,
            "excerpt": self.excerpt, "pattern": self.pattern,
        }


@dataclass
class Allowlist:
    entries: list[tuple[str, re.Pattern, str]] = field(default_factory=list)
    source: str = "(none)"

    @classmethod
    def load(cls, path: pathlib.Path) -> "Allowlist":
        if not path.exists():
            return cls(source=f"{path} (absent)")
        entries: list[tuple[str, re.Pattern, str]] = []
        pending_comment: str | None = None
        problems: list[str] = []
        for i, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            line = raw.strip()
            if not line:
                pending_comment = None
                continue
            if line.startswith("#"):
                pending_comment = line.lstrip("#").strip()
                continue
            if not pending_comment:
                problems.append(
                    f"{path}:{i}: allowlist entry {line!r} has no justification "
                    f"comment on the line above it")
                pending_comment = None
                continue
            rule, _, pat = line.partition("::")
            if pat:
                rule, pat = rule.strip(), pat.strip()
                if rule not in RULES and rule != "*":
                    problems.append(f"{path}:{i}: unknown rule id {rule!r}")
                    continue
            else:
                rule, pat = "*", line
            try:
                rx = re.compile(pat)
            except re.error as exc:
                problems.append(f"{path}:{i}: bad regex {pat!r}: {exc}")
                continue
            entries.append((rule, rx, pending_comment))
            pending_comment = None
        if problems:
            raise ValueError("\n".join(problems))
        return cls(entries, str(path))

    def allows(self, rule: str, *contexts: str) -> bool:
        for entry_rule, rx, _ in self.entries:
            if entry_rule not in ("*", rule):
                continue
            if any(rx.search(c) for c in contexts if c):
                return True
        return False


# --------------------------------------------------------------------------- #
# 3. RULE 1 -- process / self-referential prose                                #
# --------------------------------------------------------------------------- #

# Built by grepping docs/paper2/main.tex for the first-person research register
# and generalising each hit; the per-pattern census (--census) reports how many
# hits each one currently has.
PROCESS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("got-it-wrong", r"\bwe (?:got|had got) (?:this|it|them|both)\b[^.]{0,40}\bwrong"),
    ("got-both-wrong", r"\bwe got both wrong\b"),
    ("wrong-first", r"\bwrong (?:first|in a way worth|in both wrong directions)\b"),
    ("earlier-draft", r"\ban earlier (?:draft|version)\b|\bearlier drafts\b"),
    ("earlier-inferred", r"\bearlier (?:draft|version)\b[^.]{0,60}\b(?:inferred|used|said|presented|violated|recorded)\b"),
    ("we-first-verb", r"\bwe (?:first|initially|originally|briefly) (?:read|thought|believed|tried|treated|attempted|argued|assumed|took)\b"),
    ("our-first-attempt", r"\b(?:our|the) first (?:attempt|calibration|instantiation|reading|try)\b"),
    ("honest-label", r"\bhonest (?:answer|assessment|note|notes|attempt)\b|\bhonesty notes?\b"),
    ("boast", r"\bboast\b"),
    ("worth-recording", r"\bworth (?:recording|naming|stating|nothing more)\b"),
    ("after-honest-attempt", r"\bafter an honest attempt\b"),
    ("which-is-what-it-is", r"\bwhich is what it is\b"),
    ("we-chased", r"\bwe chased\b"),
    ("it-took-us", r"\bit took us\b"),
    ("before-believing", r"\bbefore believing\b"),
    ("cost-us-numbers", r"\bcost us numbers?\b"),
    ("forced-by-counterexample", r"\bforced by counterexample rather than caution\b"),
    ("stated-too-loosely", r"\bstated too loosely\b|\btoo loosely\b"),
    ("settles-a-claim-we", r"\bsettles a claim we\b|\ba claim we had\b"),
    ("we-had-dropped", r"\bwe had dropped\b|\bthe qualifier[^.]{0,40}we had\b"),
    ("we-tried", r"\bevery learner we tried\b|\bwe tried\b"),
    ("lesson-narrative", r"\bone lesson survives\b|\blessons? (?:learned|of independent value)\b|\brecorded because they will bite\b"),
    ("ops-narrative", r"\bcredits ran out\b|\baborted after its\b|\bwas launched\b[^.]{0,60}\baborted\b"),
    ("flatters-the-gate", r"\binvisible in the direction that flatters\b"),
    ("sharpened-to-a-boast", r"\bsharpened to a boast\b"),
    ("we-say-what-that-is", r"\bwe say what that is\b"),
    ("we-predicted-we-measured", r"\bwe predicted\b[^.]{0,40};\s*we measured\b"),
    ("conflating-let-a-draft", r"\bconflating them is what let\b"),
    ("we-do-not-present", r"\bwe do not present them as evidence\b"),
    ("superseded-narrative", r"\bthat appeared in earlier drafts\b|\bthe superseded\b"),
)
_PROCESS_RX = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in PROCESS_PATTERNS]


def rule_process_prose(doc: TexDoc, us: list[Unit], allow: Allowlist) -> tuple[list[Finding], dict]:
    findings, census = [], {name: 0 for name, _ in PROCESS_PATTERNS}
    for u in us:
        if u.kind != "sentence":
            continue
        plain = strip_latex(u.text)
        for name, rx in _PROCESS_RX:
            m = rx.search(plain)
            if not m:
                continue
            census[name] += 1
            if allow.allows("process-prose", plain, name):
                continue
            findings.append(Finding(
                "process-prose", str(doc.path), u.line, "error",
                f"research-process narrative ({name}): {m.group(0)!r} -- a paper "
                f"states what is true, not how the authors got there; move this to "
                f"a changelog",
                excerpt=_clip(plain, m.start()), pattern=name))
    return findings, census


def _clip(text: str, at: int, width: int = 110) -> str:
    lo = max(0, at - width // 3)
    hi = min(len(text), lo + width)
    return ("..." if lo else "") + text[lo:hi] + ("..." if hi < len(text) else "")


# --------------------------------------------------------------------------- #
# 4. RULE 2 -- unquantified modal claims in high-risk sites                     #
# --------------------------------------------------------------------------- #

MODAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("cannot", r"\bcannot\b|\bcan ?not\b|\bcan't\b"),
    ("can-never", r"\bcan never\b|\bnever\b"),
    ("impossible", r"\bimpossible\b|\bimpossibility\b"),
    ("always", r"(?<!almost )\balways\b"),         # "almost always" is hedged
    ("exhaustive", r"\bexhaustive\b|\bexhaustiveness\b|\bexhaustively\b"),
    ("exact-law", r"\bexact law\b|\bexactly the law\b"),
    ("forces", r"\bforces?\b|\bforbids?\b"),
    ("proves", r"\bproves\b|\bproven\b"),
    ("universal", r"\buniversal(?:ly)?\b"),
    # "CPU-only" is a compound, and "only when/if" introduces a scope rather
    # than removing one; neither is the exclusivity claim this rule is after.
    ("only", r"(?<![-\w])only\b(?!\s+(?:when|if))"),
)
_MODAL_RX = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in MODAL_PATTERNS]

# What counts as carrying the quantifier: a bound, a number, a named scope, or a
# reference to the hypothesis that supplies it. Deliberately NOT included:
# "measured" (an evidence label, not a quantifier), "per", "under", and a bare
# \ref{sec:...} (a pointer, not a hypothesis).
QUANTIFIER_EVIDENCE = (
    r"\d",                                   # any number / bound / dimension tag
    r"bounded[-\s]lipschitz", r"\blipschitz\b", r"\bsmooth(?:ness)?\b",
    r"\bat fixed\b", r"\bat a fixed\b",
    r"\bon th(?:is|ese) instrument", r"\bon this arm\b", r"\bon this instrument\b",
    r"\bfor the models tested\b", r"\bmodels tested\b",
    r"\bon the gate sample\b", r"\bin[-\s]sample\b", r"\bfrom the sample\b",
    r"\bscoped\b", r"\bgeometry[-\s]scoped\b",
    r"\bup to\b", r"\bwithin\b", r"\bat a rate\b", r"\bat rate\b",
    r"\bassum\w+\b", r"\bhypothes\w+\b",
    r"\bProposition\b", r"\bCorollary\b",
    # A possessive scope phrase names what the claim is relative to, which is a
    # quantifier in the sense this rule cares about: "an invented mode its gate
    # sample cannot refute" is scoped, and flagging it would flag correct prose.
    r"\bits (?:own )?gate sample\b", r"\bits sample\b", r"\bits own sample\b",
)
_QUANT_RX = [re.compile(p, re.IGNORECASE) for p in QUANTIFIER_EVIDENCE]
# A hypothesis reference is a pointer to a numbered claim, not to a section.
_HYP_REF_RX = re.compile(r"\\(?:ref|eqref|autoref)\{(?:prop|cor|thm|lem|eq|rem|assum)[:.]")


def _carries_quantifier(*scopes: str) -> str | None:
    for scope in scopes:
        if not scope:
            continue
        if _HYP_REF_RX.search(scope):
            return "hypothesis reference"
        clean = strip_latex(scope)
        for rx in _QUANT_RX:
            m = rx.search(clean)
            if m:
                return m.group(0)
    return None


_HEADING_KINDS = {"section", "subsection", "subsubsection", "paragraph",
                  "subparagraph", "title"}
_HIGH_RISK_KINDS = _HEADING_KINDS | {"textbf"}


def rule_modal_scope(doc: TexDoc, us: list[Unit], allow: Allowlist) -> tuple[list[Finding], dict]:
    findings, census = [], {name: 0 for name, _ in MODAL_PATTERNS}
    for u in us:
        high_risk = u.kind in _HIGH_RISK_KINDS
        if not high_risk and not ("abstract" in u.zones and u.kind == "sentence"):
            continue
        plain = strip_latex(u.text)
        for name, rx in _MODAL_RX:
            m = rx.search(plain)
            if not m:
                continue
            census[name] += 1
            # A heading IS its own sentence: it has to carry its own scope, since
            # that is the unit a reader quotes. A bold lead-in may borrow the
            # scope of the sentence it opens.
            if u.kind in _HEADING_KINDS:
                carrier = _carries_quantifier(u.text)
            else:
                carrier = _carries_quantifier(u.text, u.sentence)
            if carrier:
                continue
            if allow.allows("modal-scope", plain, name):
                continue
            site = "abstract sentence" if "abstract" in u.zones and u.kind == "sentence" \
                else ("bold lead-in" if u.kind == "textbf" else f"\\{u.kind} heading")
            findings.append(Finding(
                "modal-scope", str(doc.path), u.line, "error",
                f"unquantified modal claim {m.group(0)!r} in a {site}: no bound, "
                f"scope, number or hypothesis reference in the same sentence",
                excerpt=_clip(plain, m.start()), pattern=name))
    return findings, census


# --------------------------------------------------------------------------- #
# 5. RULE 3 -- soundness vocabulary without a scope qualifier                   #
# --------------------------------------------------------------------------- #

SOUNDNESS_RX = re.compile(
    r"\b(sound|soundness|soundly|certif(?:y|ies|ied|ication|ying))\b", re.IGNORECASE)

SOUNDNESS_QUALIFIERS = (
    r"\bsample[-\s]consistent\b",
    r"\bon the gate sample\b", r"\bgate sample\b",
    r"\brelative to sampled inputs\b", r"\bsampled inputs\b",
    r"\bin the strict sense\b", r"\bstrict(?:ly)? gate\b", r"\bstrict sense\b",
    r"\bits own sample\b", r"\bits sample\b", r"\bthe sample\b", r"\bin[-\s]sample\b",
    r"\bsample[-\s]covered\b", r"\ball[-\s]or[-\s]nothing\b",
    r"\bno partial artifact\b", r"\bwrong model\b", r"\bwrong thing\b",
    r"\bsampled transitions?\b", r"\bon sampled\b",
    r"\bwithin \$?\\?varepsilon\b", r"\bat tolerance\b",
    r"\bnet radius\b", r"\bcovering\b", r"\bpacking\b",   # coverage-certificate sense
    r"\bunreachable\b", r"\bone[-\s]sided\b",
    # --- the coverage-certificate sense, where the scope IS an explicit bound -----
    # "the certificate certifies sup_U ||f - fhat|| <= 0.933" carries its scope in the
    # inequality, and "no pair with L <= 5.77 can carry ..." carries it in the
    # quantifier. A rule that flagged these would be flagging correct prose, which is
    # how a linter gets switched off, so an adjacent bound counts as a qualifier.
    r"\\leq", r"\\geq", r"<=", r">=",
    r"\bupper bound\b", r"\blower bound\b", r"\bwith probability at least\b",
    r"\bLipschitz\b", r"\bcertified region\b", r"\bcoverage certificate\b",
    r"\bwhere it looks\b",          # "the gate certifies where it looks" -- the scope
    r"\bdoes and does not\b",       # explicitly two-sided
    # --- the sentence that DEFINES the reservation is not an unscoped use ---------
    r"\bwe reserve\b", r"\bnever use it as a synonym\b",
    r"\bacceptance test certifies\b",   # the paper's framing question
    r"\bcontinuous coverage analogue\b", r"\bcoverage analogue\b",
    r"\bpartition\b", r"\bnet\b", r"\bdeployed (?:cart )?gate\b",
    r"\bstep-1 reachable\b", r"\blevel set\b", r"\bregion the\b",
    r"\bshape-free\b", r"\bper-cell\b", r"\bp_C\b", r"\bHoeffding\b",
    r"\bcertified \$?\\?rho\b", r"\bbetter certificate\b",
    r"\bcertificate bounds\b", r"\bcertificates transfer\b",
    r"\bonly to the smooth case\b", r"\bsmooth case\b",
    # --- paper 3's defined scopes. The quotient paper states certification
    # relative to the reachable set, and each of these phrases IS that scope
    # stated in the sentence: the restriction operator, the reach clause, the
    # extension class, the gauge region, the sample event that produced the
    # acceptance, or the certifier named outright. A sentence carrying one is
    # scoped prose, not an unscoped assertion. --------------------------------
    r"\brestricted to\b", r"\breachable restriction\b",
    r"\bcan reach\b",
    r"\bmode[-\s]absent\b",           # acceptance BECAUSE the sample missed the mode
    r"\bgate[-\s]certified\b",        # names the certifier
    r"\bgate[-\s]pass",               # gate-pass / gate-passes / gate-passing
    r"\bE\(f\)",                      # the extension class is the scope object
    r"\bgauge region\b",
    r"\bcertified[-\s]free\b",        # T7's compound noun: evidence certified free
                                      # by trajectories, not a soundness claim
    r"\bbounded by\b",                # an explicit bound is a scope (as \leq is)
    r"\bits own consecutive samples\b",
)
_SOUND_QUAL_RX = [re.compile(p, re.IGNORECASE) for p in SOUNDNESS_QUALIFIERS]


def rule_soundness_scope(doc: TexDoc, us: list[Unit], allow: Allowlist) -> tuple[list[Finding], dict]:
    findings, census = [], {"sound": 0, "certify": 0}
    for u in us:
        if u.kind != "sentence":
            continue          # headings are inside their sentence's text already
        plain = strip_latex(u.text)
        for m in SOUNDNESS_RX.finditer(plain):
            word = m.group(1).lower()
            census["sound" if word.startswith("sound") else "certify"] += 1
            if any(rx.search(plain) for rx in _SOUND_QUAL_RX):
                continue
            if allow.allows("soundness-scope", plain, word):
                continue
            findings.append(Finding(
                "soundness-scope", str(doc.path), u.line, "error",
                f"{m.group(1)!r} used with no adjacent scope qualifier: say what it "
                f"is sound *relative to* (the gate sample / sampled inputs / "
                f"\"in the strict sense that ...\")",
                excerpt=_clip(plain, m.start()),
                pattern="sound" if word.startswith("sound") else "certify"))
    return findings, census


# --------------------------------------------------------------------------- #
# 6. RULE 4 -- pooled inference smell                                          #
# --------------------------------------------------------------------------- #

CI_RX = re.compile(
    r"\b(Wilson|Clopper[-\s]?Pearson|Clopper|confidence interval|credible interval)\b|"
    r"\b95\\?%\s*(?:CI|interval|lower bound|upper bound)\b", re.IGNORECASE)
POOLED_WORD_RX = re.compile(r"\bpool(?:ed|ing)\b", re.IGNORECASE)
# No whitespace allowed: "20/40" is a count, "caps 30 / 60 / 100" is a list.
FRACTION_RX = re.compile(r"(?<![\d./])(\d{1,4})/(\d{1,4})(?![\d./])")
INDEPENDENCE_RX = re.compile(
    r"\bdisjoint\b|\bindependent samples?\b|\bper[-\s](?:arm|size|block)\b|"
    r"\bblock[-\s]level\b|\bper arm\b|\bdistinct\b[^.]{0,24}\bblocks?\b|"
    r"\bper sample\b", re.IGNORECASE)


def declared_blocks() -> int | None:
    """Number of distinct gate-sample blocks, if the repo declares it."""
    if not STATISTICS_JSON.exists():
        return None
    try:
        data = json.loads(STATISTICS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None
    best: int | None = None
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if re.fullmatch(r"(n_)?(distinct_)?blocks?(_n)?", k) and isinstance(v, int):
                    best = v if best is None else max(best, v)
                stack.append(v)
        elif isinstance(node, list):
            stack.extend(node)
    return best


def rule_pooled_inference(doc: TexDoc, us: list[Unit], allow: Allowlist,
                          n_blocks: int | None) -> tuple[list[Finding], dict]:
    findings = []
    census = {"pooled-word": 0, "k/N-over-blocks": 0, "ci-mentions": 0,
              "mitigated-by-independence-declaration": 0}
    for u in us:
        if u.kind != "sentence":
            continue
        plain = strip_latex(u.text)
        ci = CI_RX.search(plain)
        if not ci:
            continue
        census["ci-mentions"] += 1
        reasons = []
        if POOLED_WORD_RX.search(plain):
            reasons.append("the word 'pooled' in the same sentence")
            census["pooled-word"] += 1
        if n_blocks is not None:
            for m in FRACTION_RX.finditer(plain):
                denom = int(m.group(2))
                if denom > n_blocks:
                    reasons.append(
                        f"the count {m.group(0)} has N={denom} > {n_blocks} declared "
                        f"blocks in {STATISTICS_JSON.name}")
                    census["k/N-over-blocks"] += 1
                    break
        if not reasons:
            continue
        if INDEPENDENCE_RX.search(plain):
            census["mitigated-by-independence-declaration"] += 1
            continue
        if allow.allows("pooled-inference", plain):
            continue
        findings.append(Finding(
            "pooled-inference", str(doc.path), u.line, "error",
            f"{ci.group(0)} interval quoted alongside a pooled count ("
            f"{'; '.join(reasons)}) with no independence declaration: the "
            f"experimental unit is the seed block, so say 'disjoint' / "
            f"'independent samples' or quote the per-block bound",
            excerpt=_clip(plain, ci.start()), pattern="pooled-ci"))
    return findings, census


# --------------------------------------------------------------------------- #
# 7. RULE 5 -- printed zeros with no interval, bound or footnote                #
# --------------------------------------------------------------------------- #

ZERO_CELL_RX = re.compile(
    r"^\s*(?:\$)?\s*(?:\\mathbf|\\textbf|\\mathrm|\\bf)?\s*\{?\s*"
    r"-?0(?:\.0+)?\s*\}?\s*(?:\\?%)?\s*(?:\$)?\s*$")
# A trailing annotation on the cell -- an interval, a bound, a footnote marker --
# is stripped before asking "is this cell an exact zero?", so that a zero which
# *does* carry its bound is still recognised as a zero (and then excused by
# ROW_QUALIFIER_RX) instead of silently falling out of the rule's sight.
_CELL_ANNOT_RX = re.compile(
    r"\s*(?:\$[^$]*\$|\[[^\]]*\]|\([^)]*\)|\\footnotemark(?:\[\d+\])?|"
    r"\\textsuperscript\{[^{}]*\}|\^\{?[A-Za-z\\*\u2020]+\}?)+\s*$")
ROW_QUALIFIER_RX = re.compile(
    r"\[\s*-?\d|<|\\leq|\\le\b|\\lesssim|\\dagger|\\ast|\\footnotemark|"
    r"\\textsuperscript|\^\{?[\\*\u2020]|\\tnote|\\pm|\(\s*0\s*,")


def _zero_cell(cell: str) -> bool:
    stripped = _CELL_ANNOT_RX.sub("", cell).strip()
    return bool(ZERO_CELL_RX.match(stripped or cell))


def rule_printed_zero(doc: TexDoc, allow: Allowlist) -> tuple[list[Finding], dict]:
    findings, census = [], {"zero-rows": 0}
    for ln in doc.lines:
        if "table" not in ln.zones or "&" not in ln.text:
            continue
        body = ln.text
        if "\\multicolumn" in body and body.count("&") <= 1:
            continue
        row = body.split("\\\\")[0]
        cells = [c.strip() for c in row.split("&")]
        zeros = [c for c in cells if _zero_cell(c)]
        if not zeros:
            continue
        census["zero-rows"] += 1
        if ROW_QUALIFIER_RX.search(body):
            continue
        if "(exact)" in body:
            # A zero annotated "(exact)" is a DEMONSTRATED zero -- bit-identical returns,
            # not an absence of observations. Annotating it is precisely the remedy this
            # rule asks for, so such a row is compliant, not in violation.
            continue
        if allow.allows("printed-zero", body):
            continue
        findings.append(Finding(
            "printed-zero", str(doc.path), ln.no, "error",
            f"table row prints {len(zeros)} exact zero(s) ({', '.join(zeros[:4])}) "
            f"with no interval, '<', upper bound or footnote marker in the row: a "
            f"censored zero is not a demonstrated zero",
            excerpt=_clip(row.strip(), 0), pattern="zero-row"))
    return findings, census


# --------------------------------------------------------------------------- #
# 8. RULE 6 -- hand-computed constants absent from every results JSON           #
# --------------------------------------------------------------------------- #

NUMBER_RX = re.compile(
    r"(?<![\w.])(\d{1,3}(?:\{,\}\d{3})+|\d+)(?:\.(\d+))?"
    r"(?:\s*\\times\s*10\^\{?(-?\d+)\}?)?(?![\d])")


def _numeric_values(node, out: list[float]) -> None:
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, bool):
            continue
        if isinstance(cur, (int, float)):
            out.append(float(cur))
        elif isinstance(cur, dict):
            for k, v in cur.items():
                stack.append(v)
                m = re.fullmatch(r"-?\d+(?:\.\d+)?", str(k))
                if m:
                    out.append(float(k))
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str) and re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", cur):
            out.append(float(cur))


_PLAIN_NUM_RX = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def results_index(results_dir: pathlib.Path = RESULTS_DIR) -> list[float]:
    vals: list[float] = []
    for p in sorted(results_dir.rglob("*.json")):
        # The audit's own baseline is bookkeeping, not evidence: indexing it would
        # let a violation count launder itself into a "known constant".
        if p.name == BASELINE_PATH.name:
            continue
        try:
            _numeric_values(json.loads(p.read_text(encoding="utf-8")), vals)
        except Exception:
            continue
    # Not every versioned artifact is JSON. The Claude relay transcripts are committed
    # .txt files and the numeric audit reads constants out of them (the fitted disc
    # centre, for one), so a number backed by a transcript is backed by an artifact and
    # must not be reported as hand-computed.
    for p in sorted(results_dir.rglob("*.txt")):
        try:
            for m in _PLAIN_NUM_RX.finditer(p.read_text(encoding="utf-8", errors="ignore")):
                try:
                    vals.append(float(m.group(0)))
                except ValueError:
                    continue
        except Exception:
            continue
    return sorted(set(abs(v) for v in vals))


def index_has(index: list[float], value: float, tol: float) -> bool:
    lo = bisect.bisect_left(index, value - tol)
    return lo < len(index) and index[lo] <= value + tol


def _sig_digits(int_part: str, frac_part: str) -> int:
    digits = (int_part.replace("{,}", "") + (frac_part or "")).lstrip("0")
    if not frac_part:
        digits = digits.rstrip("0") or "0"
    return len(digits)


_MATHONLY_RX = re.compile(r"[A-Za-z]{3,}")
_PRE_STRIP = (
    re.compile(r"\\(?:label|ref|eqref|autoref|cite[a-z]*|url|includegraphics|input|texttt|verb)"
               r"\s*(\[[^\]]*\])?\{[^{}]*\}"),
    re.compile(r"\\(?:varepsilon|epsilon)\s*=\s*10\^\{?-?\d+\}?"),
    # A bare power of ten is an order of magnitude, not a measured constant --
    # but NOT when it is the exponent of a mantissa ($1.52\times10^{-4}$), which
    # NUMBER_RX must still see whole.
    re.compile(r"(?<!\\times)(?<!\\times )10\^\{?-?\d+\}?"),
    re.compile(r"\b(?:19|20)\d{2}\b"),                       # years
    re.compile(r"\\(?:section|subsection|paragraph)"),
)


def rule_hand_constant(doc: TexDoc, us: list[Unit], allow: Allowlist,
                       index: list[float], strict: bool) -> tuple[list[Finding], dict]:
    findings, census = [], {"checked": 0, "missing": 0}
    severity = "error" if strict else "warning"
    for u in us:
        if u.kind != "sentence":
            continue
        text = u.text
        for rx in _PRE_STRIP:
            text = rx.sub(" ", text)
        if not _MATHONLY_RX.search(strip_latex(text)):
            continue                     # math-only / symbol line
        for m in NUMBER_RX.finditer(text):
            int_part, frac_part, exp = m.group(1), m.group(2), m.group(3)
            if _sig_digits(int_part, frac_part) < 3:
                continue
            literal = m.group(0).strip()
            value = float(int_part.replace("{,}", "") + ("." + frac_part if frac_part else ""))
            if exp:
                value *= 10.0 ** int(exp)
            census["checked"] += 1
            decimals = len(frac_part) if frac_part else 0
            if exp:
                decimals = max(decimals - int(exp), 0)
            tol = 0.5 * 10.0 ** (-decimals) if decimals else 0.5
            if index_has(index, value, tol):
                continue
            census["missing"] += 1
            if allow.allows("hand-constant", literal, strip_latex(u.text)):
                continue
            findings.append(Finding(
                "hand-constant", str(doc.path), u.line, severity,
                f"prose constant {literal!r} (= {value:g}) appears in no JSON under "
                f"results/: hand-computed numbers are this repo's known weak class -- "
                f"have the script that derives it write it out, or allowlist it with a "
                f"justification",
                excerpt=_clip(text, m.start()), pattern=literal))
    return findings, census


# --------------------------------------------------------------------------- #
# 9. Driver                                                                    #
# --------------------------------------------------------------------------- #

def audit_file(path: pathlib.Path, allow: Allowlist, index: list[float],
               n_blocks: int | None, strict: bool,
               enabled: set[str]) -> tuple[list[Finding], dict]:
    doc = TexDoc(path)
    us = units(doc)
    findings: list[Finding] = []
    census: dict[str, dict] = {}

    if "process-prose" in enabled:
        f, c = rule_process_prose(doc, us, allow)
        findings += f
        census["process-prose"] = c
    if "modal-scope" in enabled:
        f, c = rule_modal_scope(doc, us, allow)
        findings += f
        census["modal-scope"] = c
    if "soundness-scope" in enabled:
        f, c = rule_soundness_scope(doc, us, allow)
        findings += f
        census["soundness-scope"] = c
    if "pooled-inference" in enabled:
        f, c = rule_pooled_inference(doc, us, allow, n_blocks)
        findings += f
        census["pooled-inference"] = c
    if "printed-zero" in enabled:
        f, c = rule_printed_zero(doc, allow)
        findings += f
        census["printed-zero"] = c
    if "hand-constant" in enabled:
        f, c = rule_hand_constant(doc, us, allow, index, strict)
        findings += f
        census["hand-constant"] = c

    findings.sort(key=lambda f: (f.line, f.rule))
    return findings, census


def counts_by_rule(findings: list[Finding]) -> dict[str, int]:
    out = {r: 0 for r in RULES}
    for f in findings:
        out[f.rule] = out.get(f.rule, 0) + 1
    return out


def atomic_write_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def rel(path: pathlib.Path) -> str:
    try:
        return str(pathlib.Path(path).resolve().relative_to(_REPO))
    except ValueError:
        return str(path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audit_paper_claims.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("targets", nargs="*", type=pathlib.Path,
                   help="LaTeX sources to lint (default: docs/paper2/main.tex "
                        "docs/paper/main.tex docs/paper3/main.tex)")
    p.add_argument("--json", action="store_true", help="machine-readable output for CI")
    p.add_argument("--strict", action="store_true",
                   help="treat hand-constant warnings as errors")
    p.add_argument("--census", action="store_true",
                   help="print the per-pattern hit census (how many hits each "
                        "pattern currently has in the target text)")
    p.add_argument("--baseline", action="store_true",
                   help=f"write the current per-rule violation counts to "
                        f"{rel(BASELINE_PATH)} and exit 0 (the ratchet)")
    p.add_argument("--baseline-path", type=pathlib.Path, default=BASELINE_PATH)
    p.add_argument("--no-baseline", action="store_true",
                   help="ignore any recorded baseline; every violation is a failure")
    p.add_argument("--allowlist", type=pathlib.Path, default=DEFAULT_ALLOWLIST)
    p.add_argument("--results-dir", type=pathlib.Path, default=RESULTS_DIR)
    p.add_argument("--rules", default="all",
                   help="comma-separated subset of: " + ",".join(RULES))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets = [pathlib.Path(t) for t in (args.targets or DEFAULT_TARGETS)]
    missing = [t for t in targets if not t.exists()]
    if missing:
        print("error: no such file: " + ", ".join(str(m) for m in missing), file=sys.stderr)
        return 2

    enabled = set(RULES) if args.rules == "all" else set(
        s.strip() for s in args.rules.split(",") if s.strip())
    unknown = enabled - set(RULES)
    if unknown:
        print(f"error: unknown rule(s): {sorted(unknown)}", file=sys.stderr)
        return 2

    try:
        allow = Allowlist.load(args.allowlist)
    except ValueError as exc:
        print("error: malformed allowlist -- every entry needs a one-line "
              "justification comment above it\n" + str(exc), file=sys.stderr)
        return 2

    index = results_index(args.results_dir) if "hand-constant" in enabled else []
    n_blocks = declared_blocks()

    per_file: dict[str, list[Finding]] = {}
    per_file_census: dict[str, dict] = {}
    for t in targets:
        f, c = audit_file(t, allow, index, n_blocks, args.strict, enabled)
        # POSIX-style keys always: the committed baseline was written with
        # forward slashes, and a Windows run must look its counts up under
        # the same key or every recorded number silently reads as 0.
        per_file[rel(t).replace("\\", "/")] = f
        per_file_census[rel(t).replace("\\", "/")] = c

    all_findings = [f for fs in per_file.values() for f in fs]

    if args.baseline:
        payload = {
            "_comment": "Per-rule violation counts recorded by "
                        "scripts/audit_paper_claims.py --baseline. The audit fails "
                        "only when a rule goes ABOVE its baseline, so the paper can "
                        "be ratcheted down instead of blocked on day one. Lower "
                        "these numbers; never raise them.",
            "strict": bool(args.strict),
            "rules": sorted(enabled),
            "files": {name: counts_by_rule(fs) for name, fs in per_file.items()},
            "totals": counts_by_rule(all_findings),
        }
        atomic_write_json(args.baseline_path, payload)
        print(f"wrote baseline to {rel(args.baseline_path)}")
        for name, fs in per_file.items():
            print(f"  {name}: " + ", ".join(
                f"{r}={n}" for r, n in counts_by_rule(fs).items()))
        return 0

    baseline = None
    if not args.no_baseline and args.baseline_path.exists():
        try:
            baseline = json.loads(args.baseline_path.read_text(encoding="utf-8"))
        except Exception:
            baseline = None

    regressions: list[str] = []
    for name, fs in per_file.items():
        counts = counts_by_rule(fs)
        base = (baseline or {}).get("files", {}).get(name, {}) if baseline else {}
        for rule, n in counts.items():
            if rule not in enabled:
                continue
            limit = base.get(rule, 0) if baseline else 0
            if n > limit:
                regressions.append(
                    f"{name}: {rule} {n} > baseline {limit}" if baseline
                    else f"{name}: {rule} {n}")

    errors = [f for f in all_findings if f.severity == "error"]

    if args.json:
        print(json.dumps({
            "targets": [rel(t) for t in targets],
            "rules": sorted(enabled),
            "strict": bool(args.strict),
            "allowlist": allow.source,
            "allowlist_entries": len(allow.entries),
            "declared_blocks": n_blocks,
            "baseline": rel(args.baseline_path) if baseline else None,
            "findings": [f.as_dict() for f in all_findings],
            "counts": {name: counts_by_rule(fs) for name, fs in per_file.items()},
            "totals": counts_by_rule(all_findings),
            "n_errors": len(errors),
            "n_warnings": len(all_findings) - len(errors),
            "pattern_census": per_file_census,
            "regressions": regressions,
        }, indent=2, sort_keys=True))
    else:
        for name, fs in per_file.items():
            print(f"=== {name} ===")
            if not fs:
                print("  clean")
            for f in fs:
                print(f"  {name}:{f.line}: [{f.severity}] {f.rule}: {f.message}")
                print(f"      | {f.excerpt}")
            print(f"  -- " + ", ".join(
                f"{r}={n}" for r, n in counts_by_rule(fs).items()))
            print()
        if args.census:
            print("=== pattern census (hits in the current text, before allowlist) ===")
            for name, cens in per_file_census.items():
                print(f"  {name}")
                for rule, table in cens.items():
                    hits = {k: v for k, v in table.items() if v}
                    print(f"    {rule}: " + (", ".join(f"{k}={v}" for k, v in
                                                       sorted(hits.items())) or "(none)"))
            print()
        print(f"allowlist: {allow.source} ({len(allow.entries)} entries); "
              f"declared blocks: {n_blocks}")
        print(f"totals: " + ", ".join(f"{r}={n}" for r, n in
                                      counts_by_rule(all_findings).items()))
        print(f"{len(errors)} error(s), {len(all_findings) - len(errors)} warning(s)")
        if baseline:
            print(f"baseline: {rel(args.baseline_path)}")
        if regressions:
            print("REGRESSIONS (above baseline):")
            for r in regressions:
                print(f"  {r}")

    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
