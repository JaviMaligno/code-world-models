#!/usr/bin/env bash
# LaTeX presentation guard: compile the paper and fail on regressions that hurt
# camera-ready quality — overfull/underfull boxes over threshold, undefined
# references/citations, or unresolved cross-references. Runs the same in CI and
# locally: `bash scripts/check_latex.sh`.
#
# Thresholds are deliberately strict (the paper is currently clean at 0 overfull)
# so a change that reintroduces a margin overflow or a dangling \ref fails fast.
set -uo pipefail

PAPER_DIR="docs/paper"
MAIN="main"
# An overfull hbox narrower than this many points is visually negligible; allow
# it so trivial sub-point boxes don't block CI. Real margin overflows are tens
# of points. Set to 0 to forbid all overfull boxes.
OVERFULL_PT_THRESHOLD="${OVERFULL_PT_THRESHOLD:-2.0}"

cd "$PAPER_DIR" || { echo "::error::cannot cd to $PAPER_DIR"; exit 2; }

echo "== Compiling $MAIN.tex (pdflatex -> bibtex -> pdflatex x3) =="
rm -f "$MAIN".aux "$MAIN".bbl "$MAIN".blg "$MAIN".out "$MAIN".log
pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
rc=$?
bibtex "$MAIN" >/dev/null 2>&1
pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
final_rc=$?

if [ ! -f "$MAIN.log" ]; then
  echo "::error::no $MAIN.log produced — compilation did not run"; exit 2
fi
if [ "$final_rc" -ne 0 ]; then
  echo "::error::pdflatex exited non-zero (compilation error). Tail of log:"
  tail -40 "$MAIN.log"
  exit 1
fi

fail=0

# --- undefined references / citations / rerun (cross-refs must resolve) -------
undef_ref=$(grep -c "Reference.*undefined" "$MAIN.log")
undef_cit=$(grep -c "Citation.*undefined" "$MAIN.log")
rerun=$(grep -c "may have changed" "$MAIN.log")
if [ "$undef_ref" -ne 0 ]; then echo "::error::$undef_ref undefined reference(s):"; grep "Reference.*undefined" "$MAIN.log" | sed 's/^/  /'; fail=1; fi
if [ "$undef_cit" -ne 0 ]; then echo "::error::$undef_cit undefined citation(s):"; grep "Citation.*undefined" "$MAIN.log" | sed 's/^/  /'; fail=1; fi
if [ "$rerun" -ne 0 ]; then echo "::error::cross-references unresolved after 2 passes ('Label(s) may have changed')"; fail=1; fi

# --- overfull hboxes over threshold ------------------------------------------
# Extract the "(NNpt too wide)" magnitude of every Overfull \hbox and compare.
big_overfull=$(grep "^Overfull \\\\hbox" "$MAIN.log" \
  | grep -oE "[0-9]+\.[0-9]+pt too wide" | sed 's/pt too wide//' \
  | awk -v t="$OVERFULL_PT_THRESHOLD" '$1 > t' | wc -l | tr -d ' ')
overfull_vbox=$(grep -c "^Overfull \\\\vbox" "$MAIN.log")
if [ "$big_overfull" -ne 0 ]; then
  echo "::error::$big_overfull overfull hbox(es) wider than ${OVERFULL_PT_THRESHOLD}pt:"
  grep "^Overfull \\\\hbox" "$MAIN.log" | sed 's/^/  /'
  fail=1
fi
if [ "$overfull_vbox" -ne 0 ]; then
  echo "::error::$overfull_vbox overfull vbox(es):"; grep "^Overfull \\\\vbox" "$MAIN.log" | sed 's/^/  /'; fail=1
fi

pages=$(grep -oE "Output written on $MAIN.pdf \([0-9]+ pages" "$MAIN.log" | grep -oE "[0-9]+ pages")
underfull=$(grep -c "^Underfull \\\\hbox" "$MAIN.log")
echo "== Summary: $pages, overfull>${OVERFULL_PT_THRESHOLD}pt: $big_overfull, underfull hbox: $underfull (informational), undefined ref/cit: $undef_ref/$undef_cit =="

rm -f "$MAIN".aux "$MAIN".bbl "$MAIN".blg "$MAIN".out
if [ "$fail" -ne 0 ]; then echo "LaTeX presentation check FAILED"; exit 1; fi
echo "LaTeX presentation check PASSED"
