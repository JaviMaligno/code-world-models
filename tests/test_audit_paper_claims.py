"""Tests for scripts/audit_paper_claims.py.

Two things these tests are careful about.

(1) NON-VACUITY. Every rule test asserts that the *specific* rule fired with the
    *specific* pattern id on a crafted positive, and that the matched negative
    (the same claim, correctly scoped) produces no finding from that rule. A test
    that only asserts "some finding exists" would pass even if the rule that was
    supposed to fire were deleted, so each assertion names the rule and, where
    the rule has named patterns, the pattern.

(2) INDEPENDENT ORACLES. The script has three pieces of real derivation --
    significant-digit counting, the tolerance lookup into the results index, and
    the balanced-brace matcher. Each is checked against a brute-force oracle
    written here from the definition, importing nothing from the module it
    validates (`_oracle_*` functions below use only the stdlib).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import random
import re
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "audit_paper_claims.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_paper_claims", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod            # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


apc = _load_module()


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #

PREAMBLE = "\\documentclass{article}\n\\begin{document}\n"
POSTAMBLE = "\n\\end{document}\n"


def write_tex(tmp_path: pathlib.Path, body: str, name: str = "t.tex") -> pathlib.Path:
    p = tmp_path / name
    p.write_text(PREAMBLE + body + POSTAMBLE, encoding="utf-8")
    return p


def parse(tmp_path: pathlib.Path, body: str):
    path = write_tex(tmp_path, body)
    doc = apc.TexDoc(path)
    return doc, apc.units(doc)


EMPTY_ALLOW = apc.Allowlist()


def patterns(findings, rule=None):
    return sorted(f.pattern for f in findings if rule is None or f.rule == rule)


# --------------------------------------------------------------------------- #
# 0. independent brute-force oracles                                           #
# --------------------------------------------------------------------------- #

def _oracle_sig_digits(literal: str) -> int:
    """Significant digits of a printed decimal, from the definition.

    Leading zeros never count. Trailing zeros count iff the literal has a
    decimal point (they are then printed precision). Written from scratch; does
    not call into audit_paper_claims.
    """
    s = literal.replace("{,}", "").replace(",", "")
    if "." in s:
        head, _, tail = s.partition(".")
        digits = (head + tail).lstrip("0")
        return len(digits)
    digits = s.lstrip("0").rstrip("0")
    return len(digits) if digits else 1


@pytest.mark.parametrize("literal, expected", [
    ("0.0114", 3), ("17.77", 4), ("156", 3), ("1.00", 3), ("20", 1),
    ("30{,}000", 1), ("0.999", 3), ("1.0463", 5), ("0.1375", 4),
    ("100", 1), ("0.50", 2), ("2510.04542", 9),
])
def test_sig_digits_matches_oracle_and_table(literal, expected):
    m = apc.NUMBER_RX.fullmatch(literal) or apc.NUMBER_RX.search(literal)
    assert m is not None, f"NUMBER_RX failed to match {literal!r}"
    got = apc._sig_digits(m.group(1), m.group(2))
    assert got == _oracle_sig_digits(literal) == expected, (
        f"{literal!r}: script={got} oracle={_oracle_sig_digits(literal)} "
        f"expected={expected}")


def test_sig_digits_matches_oracle_on_random_literals():
    rng = random.Random(20260727)
    checked = 0
    for _ in range(2000):
        int_part = str(rng.randint(0, 99999))
        if rng.random() < 0.5:
            frac = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(1, 5)))
            literal = f"{int_part}.{frac}"
        else:
            literal = int_part
        m = apc.NUMBER_RX.fullmatch(literal)
        assert m is not None
        assert apc._sig_digits(m.group(1), m.group(2)) == _oracle_sig_digits(literal), literal
        checked += 1
    assert checked == 2000       # non-vacuous: the loop really ran


def _oracle_index_has(index, value, tol) -> bool:
    """Linear scan -- the definition of 'some value within tol'."""
    return any(abs(v - value) <= tol for v in index)


def test_index_has_matches_linear_scan_oracle():
    rng = random.Random(11)
    index = sorted({round(rng.uniform(0, 20), 4) for _ in range(500)})
    hits = misses = ties = 0
    for _ in range(4000):
        value = round(rng.uniform(0, 20), 3)
        tol = rng.choice([0.0, 5e-5, 5e-4, 0.5])
        nearest = min(abs(v - value) for v in index)
        if abs(nearest - tol) < 1e-9:
            ties += 1          # exactly on the tolerance boundary: float-noise
            continue
        got = apc.index_has(index, value, tol)
        assert got == _oracle_index_has(index, value, tol), (value, tol, nearest)
        hits += got
        misses += not got
    assert hits > 50 and misses > 50, (
        f"degenerate oracle comparison: {hits} hits / {misses} misses")
    assert ties < 40, f"too many boundary skips ({ties}) for the comparison to bite"


def _oracle_brace_arg(text: str, open_idx: int) -> str:
    """Balanced-brace scan written independently, ignoring escaped braces."""
    depth, out = 0, []
    i = open_idx
    while i < len(text):
        c = text[i]
        escaped = i > 0 and text[i - 1] == "\\"
        if c == "{" and not escaped:
            depth += 1
            if depth == 1:
                i += 1
                continue
        elif c == "}" and not escaped:
            depth -= 1
            if depth == 0:
                return "".join(out)
        out.append(c)
        i += 1
    return "".join(out)


@pytest.mark.parametrize("text", [
    r"\paragraph{plain title}",
    r"\paragraph{What the gate \emph{does} certify, and where}",
    r"\section{A \textbf{nested \emph{deeply}} heading}",
    r"\paragraph{play\_cost $> 1$ is a normalization artifact}",
    r"\textbf{a \{literal\} brace}",
])
def test_brace_arg_matches_oracle(text):
    open_idx = text.index("{")
    body, end = apc.brace_arg(text, open_idx)
    assert body == _oracle_brace_arg(text, open_idx)
    assert text[end] == "}"
    assert body, "oracle comparison would be vacuous on an empty body"


# --------------------------------------------------------------------------- #
# 1. source model: zones and sentence splitting                                 #
# --------------------------------------------------------------------------- #

def test_zones_separate_tables_math_and_abstract(tmp_path):
    doc = apc.TexDoc(write_tex(tmp_path, "\n".join([
        r"\begin{abstract}",
        r"We always win.",
        r"\end{abstract}",
        r"Prose line.",
        r"\begin{tabular}{rr}",
        r"a & 0 \\",
        r"\end{tabular}",
        r"\[ x = 0.000 \]",
    ])))
    by_line = {ln.no: ln.zones for ln in doc.lines}
    abstract_lines = [n for n, z in by_line.items() if "abstract" in z]
    table_lines = [n for n, z in by_line.items() if "table" in z]
    math_lines = [n for n, z in by_line.items() if "math" in z]
    assert abstract_lines and table_lines and math_lines
    # the row "a & 0 \\" must be inside the table zone, and the prose line outside
    row = next(ln for ln in doc.lines if ln.text.strip() == r"a & 0 \\")
    prose = next(ln for ln in doc.lines if ln.text.strip() == "Prose line.")
    assert "table" in row.zones
    assert not (prose.zones & {"table", "math", "abstract", "preamble"})


def test_comments_are_stripped_and_not_linted(tmp_path):
    body = "Real prose.\n% we got this wrong in an earlier draft\n"
    doc, us = parse(tmp_path, body)
    found, census = apc.rule_process_prose(doc, us, EMPTY_ALLOW)
    assert found == [] and sum(census.values()) == 0
    # control: the same text uncommented DOES fire, so the test is not vacuous
    doc2, us2 = parse(tmp_path, "We got this wrong in an earlier draft.")
    found2, _ = apc.rule_process_prose(doc2, us2, EMPTY_ALLOW)
    assert "got-it-wrong" in patterns(found2, "process-prose")


@pytest.mark.parametrize("text, n", [
    ("Rarity is 0.0114. The gate passes.", 2),
    (r"See Section~\ref{sec:x}. Then it fails.", 2),
    (r"We use i.e.\ the gate policy here, and nothing else.", 1),
    ("A value of 17.77 is measured at 0.53 units.", 1),
])
def test_sentence_splitting_does_not_split_on_decimals_or_abbreviations(text, n):
    assert len(apc.split_sentences(text)) == n, apc.split_sentences(text)


# --------------------------------------------------------------------------- #
# 2. RULE process-prose                                                        #
# --------------------------------------------------------------------------- #

PROCESS_POSITIVES = [
    ("We got this wrong first, and the fix is below.", "got-it-wrong"),
    ("An earlier draft presented a sample statistic as an instrument property.",
     "earlier-draft"),
    ("We first believed a diagnostic that showed a hard floor.", "we-first-verb"),
    ("Two honest notes follow.", "honest-label"),
    ("The claim was sharpened to a boast on the 1D instruments.", "boast"),
    ("That control is clean and worth recording.", "worth-recording"),
    ("Section 5 gives the result after an honest attempt at the mechanism.",
     "after-honest-attempt"),
    ("The threshold reports an in-sample identity, which is what it is.",
     "which-is-what-it-is"),
    ("We chased it in both wrong directions before getting it right.", "we-chased"),
    ("It took us three tries to see the sorted-prefix bug.", "it-took-us"),
    ("A box's infimum is zero, and we measured that before believing it.",
     "before-believing"),
    ("Two discipline points, both of which cost us numbers.", "cost-us-numbers"),
    ("Both were forced by counterexample rather than caution.",
     "forced-by-counterexample"),
]


@pytest.mark.parametrize("sentence, pattern", PROCESS_POSITIVES)
def test_process_prose_fires_with_the_named_pattern(tmp_path, sentence, pattern):
    doc, us = parse(tmp_path, sentence)
    found, census = apc.rule_process_prose(doc, us, EMPTY_ALLOW)
    assert pattern in patterns(found, "process-prose"), (sentence, patterns(found))
    assert census[pattern] >= 1
    assert all(f.severity == "error" for f in found)
    assert all(f.line >= 1 for f in found), "diagnostics must carry a line number"


@pytest.mark.parametrize("sentence", [
    "The reveal-rarity is flat below the in-sample threshold.",
    "The joint gate-miss factor is bracketed by the Frechet--Hoeffding bounds.",
    "Rarity is measured on 30{,}000 random rollouts.",
])
def test_process_prose_silent_on_statements_of_fact(tmp_path, sentence):
    doc, us = parse(tmp_path, sentence)
    found, census = apc.rule_process_prose(doc, us, EMPTY_ALLOW)
    assert found == [], [f.message for f in found]
    assert sum(census.values()) == 0


def test_process_prose_reports_a_per_pattern_census(tmp_path):
    doc, us = parse(tmp_path, "\n".join(s for s, _ in PROCESS_POSITIVES))
    _, census = apc.rule_process_prose(doc, us, EMPTY_ALLOW)
    fired = {k for k, v in census.items() if v}
    expected = {p for _, p in PROCESS_POSITIVES}
    assert expected <= fired, expected - fired
    assert set(census) == {name for name, _ in apc.PROCESS_PATTERNS}


# --------------------------------------------------------------------------- #
# 3. RULE modal-scope                                                          #
# --------------------------------------------------------------------------- #

def test_modal_scope_fires_on_unquantified_heading(tmp_path):
    doc, us = parse(tmp_path, r"\paragraph{The constant is universal.}" "\nBody text.")
    found, census = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert patterns(found, "modal-scope") == ["universal"]
    assert census["universal"] == 1
    assert "\\paragraph heading" in found[0].message


def test_modal_scope_accepts_a_heading_that_carries_its_own_scope(tmp_path):
    doc, us = parse(tmp_path, r"\paragraph{The constant is universal for L-Lipschitz pairs.}")
    found, census = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert found == []
    assert census["universal"] == 1, "the modal word must still have been *seen*"


def test_modal_scope_heading_may_not_borrow_scope_from_the_body(tmp_path):
    """A heading is quoted alone, so it must carry its own quantifier.

    The body here supplies a bound and a hypothesis reference; the heading does
    not, and the heading is still flagged. The paired test below shows the same
    sentence-level scope DOES excuse a bold lead-in, so this is not just a test
    that "cannot" always fires.
    """
    body = (r"\section{The planner cannot escape}" "\n"
            r"The bound is $(\eta-\varepsilon)/2L$ on 3200 rows, "
            r"by Proposition~\ref{prop:lipschitz}.")
    doc, us = parse(tmp_path, body)
    found, _ = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert patterns(found, "modal-scope") == ["cannot"], [f.message for f in found]
    assert "\\section heading" in found[0].message


def test_modal_scope_bold_lead_in_may_borrow_scope_from_its_sentence(tmp_path):
    borrowed = (r"\textbf{The planner cannot escape the fence} --- "
                r"for $L$-Lipschitz pairs, by Proposition~\ref{prop:lipschitz}.")
    doc, us = parse(tmp_path, borrowed)
    found, census = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert found == []
    assert census["cannot"] >= 1
    # and with the scope removed from the sentence it does fire
    doc2, us2 = parse(tmp_path, r"\textbf{The planner cannot escape the fence} "
                                r"--- as the next paragraph shows.")
    found2, _ = apc.rule_modal_scope(doc2, us2, EMPTY_ALLOW)
    assert patterns(found2, "modal-scope") == ["cannot"]
    assert "bold lead-in" in found2[0].message


def test_modal_scope_accepts_a_heading_that_names_its_learner_class(tmp_path):
    """"Smooth learners cannot localize" names its scope in the subject."""
    doc, us = parse(tmp_path, r"\section{Smooth learners cannot localize}")
    found, census = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert found == []
    assert census["cannot"] == 1


def test_modal_scope_ignores_short_bold_emphasis(tmp_path):
    doc, us = parse(tmp_path, r"The pooled count is \textbf{always} 0/156 here.")
    found, _ = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert found == [], "\\textbf{always} is emphasis, not a lead-in claim"


def test_modal_scope_scans_abstract_sentences(tmp_path):
    body = ("\\begin{abstract}\n"
            "The gate is exhaustive.\n"
            "\\end{abstract}")
    doc, us = parse(tmp_path, body)
    found, _ = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert patterns(found, "modal-scope") == ["exhaustive"]
    assert "abstract sentence" in found[0].message
    # the identical sentence in the body is NOT a high-risk site
    doc2, us2 = parse(tmp_path, "The gate is exhaustive.")
    found2, _ = apc.rule_modal_scope(doc2, us2, EMPTY_ALLOW)
    assert found2 == []


@pytest.mark.parametrize("heading", [
    r"\paragraph{Everything is CPU-only.}",
    r"\paragraph{The gate passes only when the mode is absent.}",
    r"\paragraph{The blind planner almost always escapes.}",
])
def test_modal_scope_does_not_fire_on_hedges_and_compounds(tmp_path, heading):
    doc, us = parse(tmp_path, heading)
    found, _ = apc.rule_modal_scope(doc, us, EMPTY_ALLOW)
    assert found == [], [f.message for f in found]


# --------------------------------------------------------------------------- #
# 4. RULE soundness-scope                                                      #
# --------------------------------------------------------------------------- #

def test_soundness_scope_fires_without_a_qualifier(tmp_path):
    doc, us = parse(tmp_path, "Certification stayed sound throughout.")
    found, census = apc.rule_soundness_scope(doc, us, EMPTY_ALLOW)
    assert {f.pattern for f in found} == {"sound", "certify"}
    assert census["sound"] >= 1 and census["certify"] >= 1


@pytest.mark.parametrize("sentence", [
    "The gate is sound relative to sampled inputs.",
    "The artifact is sample-consistent, so certification is sound in that sense.",
    "The all-or-nothing gate certified no partial artifact.",
    "Certification is sound in the strict sense that no accepted artifact errs on "
    "the gate sample.",
])
def test_soundness_scope_accepts_a_scoped_use(tmp_path, sentence):
    doc, us = parse(tmp_path, sentence)
    found, census = apc.rule_soundness_scope(doc, us, EMPTY_ALLOW)
    assert found == [], [f.message for f in found]
    assert census["sound"] + census["certify"] >= 1, "the vocabulary must be seen"


# --------------------------------------------------------------------------- #
# 5. RULE pooled-inference                                                     #
# --------------------------------------------------------------------------- #

def test_pooled_inference_fires_on_pooled_word_next_to_a_ci(tmp_path):
    doc, us = parse(tmp_path, "Pooling the two arms gives a Wilson 95\\% lower "
                              "bound of 0.84 on the conditional.")
    found, census = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, None)
    assert patterns(found, "pooled-inference") == ["pooled-ci"]
    assert census["pooled-word"] == 1 and census["ci-mentions"] == 1


def test_pooled_inference_fires_when_N_exceeds_declared_blocks(tmp_path):
    doc, us = parse(tmp_path, "The repair rate is 109/111 with a Wilson 95\\% "
                              "lower bound of 0.9.")
    found, census = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, n_blocks=40)
    assert patterns(found, "pooled-inference") == ["pooled-ci"]
    assert census["k/N-over-blocks"] == 1
    assert "> 40 declared blocks" in found[0].message
    # with enough declared blocks the same sentence is fine
    found2, census2 = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, n_blocks=200)
    assert found2 == [] and census2["k/N-over-blocks"] == 0
    # and without a declared block count the N-based branch is not used at all
    found3, census3 = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, n_blocks=None)
    assert found3 == [] and census3["k/N-over-blocks"] == 0


def test_pooled_inference_mitigated_by_an_independence_declaration(tmp_path):
    doc, us = parse(tmp_path, "Pooling the two disjoint blocks gives 20/20 on 20 "
                              "independent samples and a Wilson 95\\% lower bound "
                              "of 0.84.")
    found, census = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, n_blocks=40)
    assert found == []
    assert census["mitigated-by-independence-declaration"] == 1, (
        "the mitigation branch must actually have been taken")


def test_pooled_inference_silent_without_a_ci(tmp_path):
    doc, us = parse(tmp_path, "Pooling the two arms gives 20/20.")
    found, census = apc.rule_pooled_inference(doc, us, EMPTY_ALLOW, n_blocks=1)
    assert found == [] and census["ci-mentions"] == 0


def test_declared_blocks_reads_the_statistics_json(tmp_path, monkeypatch):
    stats = tmp_path / "paper2_statistics.json"
    stats.write_text(json.dumps({"unit": {"n_distinct_blocks": 40},
                                 "other": {"n_blocks": 5}}), encoding="utf-8")
    monkeypatch.setattr(apc, "STATISTICS_JSON", stats)
    assert apc.declared_blocks() == 40
    monkeypatch.setattr(apc, "STATISTICS_JSON", tmp_path / "absent.json")
    assert apc.declared_blocks() is None


# --------------------------------------------------------------------------- #
# 6. RULE printed-zero                                                         #
# --------------------------------------------------------------------------- #

def test_printed_zero_fires_on_a_bare_zero_row(tmp_path):
    body = "\n".join([
        r"\begin{tabular}{lrr}",
        r"cart & 1.031 & 0.000 \\",
        r"\end{tabular}",
    ])
    doc, _ = parse(tmp_path, body)
    found, census = apc.rule_printed_zero(doc, EMPTY_ALLOW)
    assert patterns(found, "printed-zero") == ["zero-row"]
    assert census["zero-rows"] == 1
    assert "0.000" in found[0].message


@pytest.mark.parametrize("row", [
    r"cart & 1.031 & 0.000 & $[0, 0.16]$ \\",       # bound in a sibling cell
    r"cart & 1.031 & 0.000 $[0, 0.16]$ \\",         # bound in the same cell
    r"cart & 1.031 & 0.000$^\dagger$ \\",           # footnote marker
    r"cart & 1.031 & 0.000 ($\leq 0.013$) \\",      # explicit upper bound
    r"cart & 1.031 & 0.000 & $< 0.0019$ \\",        # "<" elsewhere in the row
])
def test_printed_zero_accepts_a_row_that_carries_its_bound(tmp_path, row):
    body = "\n".join([r"\begin{tabular}{lrr}", row, r"\end{tabular}"])
    doc, _ = parse(tmp_path, body)
    found, census = apc.rule_printed_zero(doc, EMPTY_ALLOW)
    assert found == [], found[0].message if found else ""
    assert census["zero-rows"] == 1, (
        "the zero cell must still have been detected -- otherwise the rule is "
        "passing by blindness rather than by the qualifier")


def test_printed_zero_ignores_zeros_outside_tables(tmp_path):
    doc, _ = parse(tmp_path, "The play cost is 0.000 and the contact rate is 0.")
    found, census = apc.rule_printed_zero(doc, EMPTY_ALLOW)
    assert found == [] and census["zero-rows"] == 0


def test_printed_zero_ignores_nonzero_rows(tmp_path):
    body = "\n".join([r"\begin{tabular}{lrr}", r"cart & 1.031 & 0.001 \\",
                      r"\end{tabular}"])
    doc, _ = parse(tmp_path, body)
    found, census = apc.rule_printed_zero(doc, EMPTY_ALLOW)
    assert found == [] and census["zero-rows"] == 0


# --------------------------------------------------------------------------- #
# 7. RULE hand-constant                                                        #
# --------------------------------------------------------------------------- #

@pytest.fixture()
def results_dir(tmp_path):
    d = tmp_path / "results"
    d.mkdir()
    (d / "a.json").write_text(json.dumps(
        {"play_cost": 1.031, "rarity": 0.0114, "rows": [{"J_truth": 17.77}]}),
        encoding="utf-8")
    (d / "b.json").write_text(json.dumps({"counts": {"repaired": 109}}),
                              encoding="utf-8")
    return d


def test_hand_constant_flags_only_numbers_absent_from_results(tmp_path, results_dir):
    index = apc.results_index(results_dir)
    assert index, "the fixture index must be non-empty"
    body = ("The measured play cost is 1.031 at rarity 0.0114, against a "
            "hand-derived ceiling of 1.0463 and a return of 17.77.")
    doc, us = parse(tmp_path, body)
    found, census = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, strict=False)
    assert [f.pattern for f in found] == ["1.0463"], [f.pattern for f in found]
    assert census["checked"] == 4 and census["missing"] == 1
    assert found[0].severity == "warning"


def test_hand_constant_becomes_an_error_under_strict(tmp_path, results_dir):
    index = apc.results_index(results_dir)
    doc, us = parse(tmp_path, "A hand-derived ceiling of 1.0463 appears here.")
    found, _ = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, strict=True)
    assert [f.severity for f in found] == ["error"]


def test_hand_constant_ignores_low_precision_years_and_refs(tmp_path, results_dir):
    index = apc.results_index(results_dir)
    body = (r"See Section~\ref{sec:patch2d} and \texttt{scripts/gap\_grid.py}; "
            r"the 2026 run used 20 seeds and $\varepsilon = 10^{-9}$.")
    doc, us = parse(tmp_path, body)
    found, census = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, strict=False)
    assert found == [], [f.pattern for f in found]
    assert census["checked"] == 0


def test_hand_constant_skips_tables_and_display_math(tmp_path, results_dir):
    index = apc.results_index(results_dir)
    body = "\n".join([
        r"\begin{tabular}{rr}",
        r"8 & 3.14159 \\",
        r"\end{tabular}",
        r"\[ C = 222.222 \]",
    ])
    doc, us = parse(tmp_path, body)
    found, census = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, strict=False)
    assert found == [] and census["checked"] == 0
    # control: the same constant in prose IS checked
    doc2, us2 = parse(tmp_path, "The constant is 222.222 on these parameters.")
    found2, census2 = apc.rule_hand_constant(doc2, us2, EMPTY_ALLOW, index, False)
    assert [f.pattern for f in found2] == ["222.222"] and census2["checked"] == 1


def test_hand_constant_matches_scientific_notation(tmp_path):
    d = tmp_path / "res"
    d.mkdir()
    (d / "x.json").write_text(json.dumps({"invariance": 0.000152}), encoding="utf-8")
    index = apc.results_index(d)
    doc, us = parse(tmp_path, r"knob-invariant to $1.52\times10^{-4}$ on this arm.")
    found, census = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, strict=False)
    assert census["checked"] == 1, "the scientific-notation literal must be parsed"
    assert found == [], [f.message for f in found]


# --------------------------------------------------------------------------- #
# 8. allowlist                                                                 #
# --------------------------------------------------------------------------- #

def test_allowlist_requires_a_justification_comment(tmp_path):
    p = tmp_path / "allow.txt"
    p.write_text("^2510\\.04542$\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no justification comment"):
        apc.Allowlist.load(p)


def test_allowlist_accepts_a_justified_entry_and_scopes_it_to_one_rule(tmp_path):
    p = tmp_path / "allow.txt"
    p.write_text("# arXiv ids are bibliographic, not measurements\n"
                 "hand-constant :: ^2510\\.04542$\n", encoding="utf-8")
    allow = apc.Allowlist.load(p)
    assert len(allow.entries) == 1
    assert allow.entries[0][2] == "arXiv ids are bibliographic, not measurements"
    assert allow.allows("hand-constant", "2510.04542")
    assert not allow.allows("process-prose", "2510.04542")
    assert not allow.allows("hand-constant", "1.0463")


def test_allowlist_suppresses_a_finding_it_matches(tmp_path, results_dir):
    index = apc.results_index(results_dir)
    doc, us = parse(tmp_path, "A hand-derived ceiling of 1.0463 appears here.")
    unsuppressed, _ = apc.rule_hand_constant(doc, us, EMPTY_ALLOW, index, False)
    assert len(unsuppressed) == 1, "precondition: the finding must exist first"

    p = tmp_path / "allow.txt"
    p.write_text("# derived in closed form by prop:normalizers, checked by hand\n"
                 "hand-constant :: ^1\\.0463$\n", encoding="utf-8")
    allow = apc.Allowlist.load(p)
    suppressed, census = apc.rule_hand_constant(doc, us, allow, index, False)
    assert suppressed == []
    assert census["missing"] == 1, "the census must still record the raw hit"


def test_allowlist_rejects_an_unknown_rule_id_and_a_bad_regex(tmp_path):
    p = tmp_path / "allow.txt"
    p.write_text("# why\nnot-a-rule :: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown rule"):
        apc.Allowlist.load(p)
    p.write_text("# why\nhand-constant :: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad regex"):
        apc.Allowlist.load(p)


def test_absent_allowlist_is_not_an_error(tmp_path):
    allow = apc.Allowlist.load(tmp_path / "nope.txt")
    assert allow.entries == [] and "absent" in allow.source


# --------------------------------------------------------------------------- #
# 9. CLI: exit codes, --json, --baseline ratchet                                #
# --------------------------------------------------------------------------- #

DIRTY = "\n".join([
    r"\paragraph{The constant is universal.}",
    r"We got this wrong in an earlier draft.",
])
CLEAN = "The reveal-rarity is flat below the in-sample threshold."


def run_cli(argv, capsys):
    code = apc.main(argv)
    out = capsys.readouterr().out
    return code, out


def test_cli_exits_nonzero_on_violations_and_zero_when_clean(tmp_path, capsys):
    dirty = write_tex(tmp_path, DIRTY, "dirty.tex")
    clean = write_tex(tmp_path, CLEAN, "clean.tex")
    common = ["--no-baseline", "--results-dir", str(tmp_path / "results"),
              "--allowlist", str(tmp_path / "absent.txt")]
    code, out = run_cli([str(dirty)] + common, capsys)
    assert code == 1
    assert f"{dirty.name}:" in out or str(dirty) in out
    assert "process-prose" in out and "modal-scope" in out
    code, out = run_cli([str(clean)] + common, capsys)
    assert code == 0, out
    assert "clean" in out


def test_cli_reports_file_and_line(tmp_path, capsys):
    p = write_tex(tmp_path, "Padding line.\n" * 3 + "We chased it in both wrong "
                            "directions before getting it right.", "x.tex")
    code, out = run_cli([str(p), "--no-baseline", "--allowlist",
                         str(tmp_path / "absent.txt"), "--rules", "process-prose"],
                        capsys)
    assert code == 1
    m = re.search(r"x\.tex:(\d+): \[error\] process-prose", out)
    assert m, out
    reported = int(m.group(1))
    assert p.read_text().split("\n")[reported - 1].startswith("We chased")


def test_cli_json_output_is_wellformed(tmp_path, capsys):
    p = write_tex(tmp_path, DIRTY, "d.tex")
    code, out = run_cli([str(p), "--json", "--no-baseline", "--allowlist",
                         str(tmp_path / "absent.txt"), "--results-dir",
                         str(tmp_path / "results")], capsys)
    assert code == 1
    payload = json.loads(out)
    assert set(payload) >= {"findings", "counts", "totals", "pattern_census",
                            "regressions", "n_errors", "n_warnings"}
    assert payload["totals"]["process-prose"] >= 1
    assert payload["totals"]["modal-scope"] >= 1
    rules = {f["rule"] for f in payload["findings"]}
    assert {"process-prose", "modal-scope"} <= rules
    assert all(f["line"] >= 1 for f in payload["findings"])


def test_cli_baseline_ratchet(tmp_path, capsys):
    p = write_tex(tmp_path, DIRTY, "d.tex")
    baseline = tmp_path / "baseline.json"
    common = ["--allowlist", str(tmp_path / "absent.txt"),
              "--results-dir", str(tmp_path / "results"),
              "--baseline-path", str(baseline)]

    code, out = run_cli([str(p), "--baseline"] + common, capsys)
    assert code == 0 and baseline.exists()
    recorded = json.loads(baseline.read_text())
    assert recorded["files"][apc.rel(p)]["process-prose"] >= 1

    # unchanged text is now at baseline -> pass
    code, out = run_cli([str(p)] + common, capsys)
    assert code == 0, out

    # one more violation -> regression, exit 1, and the regression is named
    p.write_text(p.read_text().replace(r"\end{document}",
                                       "It took us three tries.\n\\end{document}"))
    code, out = run_cli([str(p)] + common, capsys)
    assert code == 1
    assert "REGRESSIONS" in out and "process-prose" in out

    # removing violations below baseline still passes (the ratchet only tightens
    # when --baseline is re-run)
    write_tex(tmp_path, CLEAN, "d.tex")
    code, out = run_cli([str(p)] + common, capsys)
    assert code == 0, out


def test_cli_rejects_unknown_rule_and_missing_file(tmp_path, capsys):
    p = write_tex(tmp_path, CLEAN, "c.tex")
    assert apc.main([str(p), "--rules", "no-such-rule"]) == 2
    assert apc.main([str(tmp_path / "missing.tex")]) == 2


def test_cli_exits_2_on_a_malformed_allowlist(tmp_path, capsys):
    p = write_tex(tmp_path, CLEAN, "c.tex")
    bad = tmp_path / "bad.txt"
    bad.write_text("entry-with-no-justification\n", encoding="utf-8")
    assert apc.main([str(p), "--allowlist", str(bad)]) == 2


def test_cli_census_prints_per_pattern_counts(tmp_path, capsys):
    p = write_tex(tmp_path, DIRTY, "d.tex")
    code, out = run_cli([str(p), "--census", "--no-baseline", "--allowlist",
                         str(tmp_path / "absent.txt"), "--rules",
                         "process-prose,modal-scope"], capsys)
    assert "pattern census" in out
    assert "earlier-draft=" in out or "got-it-wrong=" in out
    assert "universal=1" in out


# --------------------------------------------------------------------------- #
# 10. the real papers: the linter must run on them and find its own register    #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("target", ["docs/paper2/main.tex", "docs/paper/main.tex"])
def test_runs_on_the_real_paper_without_crashing(target):
    path = _REPO / target
    if not path.exists():
        pytest.skip(f"{target} not present")
    allow = apc.Allowlist.load(apc.DEFAULT_ALLOWLIST)
    findings, census = apc.audit_file(
        path, allow, apc.results_index(apc.RESULTS_DIR), apc.declared_blocks(),
        strict=False, enabled=set(apc.RULES))
    assert set(census) == set(apc.RULES)
    n_lines = len(path.read_text(encoding="utf-8").split("\n"))
    for f in findings:
        assert 1 <= f.line <= n_lines, (f.rule, f.line)
        assert f.rule in apc.RULES
        assert f.severity in {"error", "warning"}
        assert f.message and f.excerpt
    # non-vacuous: the modal and soundness vocabularies genuinely occur in these
    # sources, so the censuses cannot be empty even if every hit is scoped.
    assert sum(census["soundness-scope"].values()) > 0
    assert sum(census["modal-scope"].values()) > 0
    assert census["hand-constant"]["checked"] > 0


def test_repo_allowlist_is_wellformed():
    if not apc.DEFAULT_ALLOWLIST.exists():
        pytest.skip("no repo allowlist")
    allow = apc.Allowlist.load(apc.DEFAULT_ALLOWLIST)   # raises if malformed
    assert all(just for _, _, just in allow.entries), "every entry needs a reason"
