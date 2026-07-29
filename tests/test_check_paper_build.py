"""Tests for the structural paper guard.

A guard whose detections are untested is a guard you hope works. Each test below plants the
exact defect the guard was written for, and one guards the other direction: the rule that
flags empty sections was WRONG in its first form -- it treated a \\section followed by a
\\subsection as a defect, which is ordinary structure, and fired on three sections of paper 1.
"""
import pathlib
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

from check_paper_build import check                                  # noqa: E402

CLEAN = r"""\documentclass{article}
\begin{document}
\section{One}
\label{sec:one}
Some content that refers to Proposition~\ref{prop:a} and Section~\ref{sec:one}.
\begin{proposition}[a]
\label{prop:a}
A statement.
\end{proposition}
\subsection{A subsection}
\label{sub:x}
More content.
\section{Two}
\label{sec:two}
Content pointing at Section~\ref{sec:two}.
\end{document}
"""


def _write(tmp_path, body, log=""):
    tex = tmp_path / "main.tex"
    tex.write_text(body)
    (tmp_path / "main.log").write_text(log or "Output written on main.pdf (1 page).\n")
    return tex


def _kinds(findings):
    return [f.split("[", 1)[1].split("]", 1)[0] for f in findings if "[" in f]


def test_a_clean_document_is_clean(tmp_path):
    assert check(_write(tmp_path, CLEAN)) == []


def test_a_section_followed_by_a_subsection_is_not_a_defect(tmp_path):
    """The first version of this rule got this wrong. A section whose content begins with a
    subsection is ordinary structure."""
    src = CLEAN.replace("Some content that refers to Proposition~\\ref{prop:a} and "
                        "Section~\\ref{sec:one}.\n", "")
    assert "empty-section" not in _kinds(check(_write(tmp_path, src)))


def test_a_section_wrapping_only_another_section_is_flagged(tmp_path):
    """The real defect: the restructuring script left a heading whose entire content was the
    next heading."""
    src = CLEAN.replace("\\section{Two}\n\\label{sec:two}\n",
                        "\\section{Wrapper}\n\\label{sec:wrap}\n\n"
                        "\\section{Two}\n\\label{sec:two}\n")
    f = check(_write(tmp_path, src))
    assert "empty-section" in _kinds(f)
    assert "Wrapper" in " ".join(f)


def test_a_duplicate_label_is_flagged(tmp_path):
    src = CLEAN.replace("\\label{sec:two}", "\\label{sec:one}")
    f = check(_write(tmp_path, src))
    assert "duplicate-label" in _kinds(f)
    assert "sec:one" in " ".join(f)


def test_an_orphaned_numbered_result_is_flagged(tmp_path):
    """The defect LaTeX never warns about, and the mechanical form of 'too many
    contributions': a proposition nothing cites."""
    src = CLEAN.replace("refers to Proposition~\\ref{prop:a} and ", "refers to ")
    f = check(_write(tmp_path, src))
    assert "orphan-result" in _kinds(f)
    assert "prop:a" in " ".join(f)


def test_an_orphan_can_be_allowlisted_but_needs_a_reason(tmp_path):
    import check_paper_build as m
    src = CLEAN.replace("refers to Proposition~\\ref{prop:a} and ", "refers to ")
    m.ORPHAN_ALLOWLIST["prop:a"] = "stated for completeness; see the reason here"
    try:
        assert "orphan-result" not in _kinds(check(_write(tmp_path, src)))
    finally:
        del m.ORPHAN_ALLOWLIST["prop:a"]


@pytest.mark.parametrize("line,kind", [
    ("! Undefined control sequence.", "latex-error"),
    ("LaTeX Warning: Label `sec:x' multiply defined.", "multiply-defined"),
    ("LaTeX Warning: Reference `sec:y' on page 3 undefined on input line 9.",
     "undefined-reference"),
    ("LaTeX Warning: Citation `smith2020' on page 3 undefined on input line 9.",
     "undefined-citation"),
    ("Overfull \\hbox (12.5pt too wide) in paragraph at lines 1--2", "overfull"),
])
def test_each_log_pattern_is_detected(tmp_path, line, kind):
    f = check(_write(tmp_path, CLEAN, log=line + "\n"))
    assert kind in _kinds(f), f


def test_a_missing_log_is_itself_a_finding(tmp_path):
    """Otherwise a guard silently passes on a document that was never built."""
    tex = tmp_path / "main.tex"
    tex.write_text(CLEAN)
    assert any("no .log" in x for x in check(tex))


def test_labels_inside_input_files_are_seen(tmp_path):
    """The paper keeps related work and three appendices in \\input files; a label defined
    there must count as defined, or the duplicate check would miss collisions across them."""
    (tmp_path / "part.tex").write_text("\\section{Extra}\n\\label{sec:one}\nText.\n")
    src = CLEAN.replace("\\end{document}", "\\input{part}\n\\end{document}")
    f = check(_write(tmp_path, src))
    assert "duplicate-label" in _kinds(f), f


def test_the_committed_paper2_is_clean():
    """The guard is only worth having if the paper it guards passes it."""
    tex = _REPO / "docs" / "paper2" / "main.tex"
    if not (tex.with_suffix(".log")).exists():
        pytest.skip("build docs/paper2/main.tex first")
    assert check(tex) == []
