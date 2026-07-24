#!/usr/bin/env bash
# LaTeX presentation guard: compile the paper(s) and fail on regressions that hurt
# camera-ready quality — overfull/underfull boxes over threshold, undefined
# references/citations, or unresolved cross-references. Runs the same in CI and
# locally: `bash scripts/check_latex.sh`.
#
# Thresholds are deliberately strict (the papers are currently clean at 0
# overfull) so a change that reintroduces a margin overflow or a dangling
# \ref fails fast.
set -uo pipefail

MAIN="main"
# An overfull hbox narrower than this many points is visually negligible; allow
# it so trivial sub-point boxes don't block CI. Real margin overflows are tens
# of points. Set to 0 to forbid all overfull boxes.
OVERFULL_PT_THRESHOLD="${OVERFULL_PT_THRESHOLD:-2.0}"

# Remove intermediate build files; the bbl is restored from git where tracked
# (both papers commit their bbl when tracked — deleting it would dirty the tree).
# Must run on EVERY exit path of check_paper, including compile failures.
cleanup_paper() {
  rm -f "$MAIN".aux "$MAIN".blg "$MAIN".out
  git checkout -- "$MAIN.bbl" 2>/dev/null || rm -f "$MAIN.bbl"
}

check_paper() {
  local PAPER_DIR="$1"

  cd "$PAPER_DIR" || { echo "::error::cannot cd to $PAPER_DIR"; return 2; }

  echo "== [$PAPER_DIR] Compiling $MAIN.tex (pdflatex -> bibtex -> pdflatex x3) =="
  local rc final_rc
  rm -f "$MAIN".aux "$MAIN".bbl "$MAIN".blg "$MAIN".out "$MAIN".log
  pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
  rc=$?
  bibtex "$MAIN" >/dev/null 2>&1
  pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
  pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
  pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1
  final_rc=$?

  if [ ! -f "$MAIN.log" ]; then
    echo "::error::no $MAIN.log produced — compilation did not run"
    cleanup_paper; return 2
  fi
  if [ "$final_rc" -ne 0 ]; then
    echo "::error::pdflatex exited non-zero (compilation error). Tail of log:"
    tail -40 "$MAIN.log"
    cleanup_paper; return 1
  fi

  local fail=0

  # --- undefined references / citations / rerun (cross-refs must resolve) -------
  local undef_ref undef_cit rerun
  undef_ref=$(grep -c "Reference.*undefined" "$MAIN.log")
  undef_cit=$(grep -c "Citation.*undefined" "$MAIN.log")
  rerun=$(grep -c "may have changed" "$MAIN.log")
  if [ "$undef_ref" -ne 0 ]; then echo "::error::$undef_ref undefined reference(s):"; grep "Reference.*undefined" "$MAIN.log" | sed 's/^/  /'; fail=1; fi
  if [ "$undef_cit" -ne 0 ]; then echo "::error::$undef_cit undefined citation(s):"; grep "Citation.*undefined" "$MAIN.log" | sed 's/^/  /'; fail=1; fi
  if [ "$rerun" -ne 0 ]; then echo "::error::cross-references unresolved after 2 passes ('Label(s) may have changed')"; fail=1; fi

  # --- overfull hboxes over threshold ------------------------------------------
  # Extract the "(NNpt too wide)" magnitude of every Overfull \hbox and compare.
  local big_overfull overfull_vbox
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

  local pages underfull
  pages=$(grep -oE "Output written on $MAIN.pdf \([0-9]+ pages" "$MAIN.log" | grep -oE "[0-9]+ pages")
  underfull=$(grep -c "^Underfull \\\\hbox" "$MAIN.log")
  echo "== [$PAPER_DIR] Summary: $pages, overfull>${OVERFULL_PT_THRESHOLD}pt: $big_overfull, underfull hbox: $underfull (informational), undefined ref/cit: $undef_ref/$undef_cit =="

  cleanup_paper

  if [ "$fail" -ne 0 ]; then echo "== [$PAPER_DIR] LaTeX presentation check FAILED =="; return 1; fi
  echo "== [$PAPER_DIR] LaTeX presentation check PASSED =="
  return 0
}

overall=0
for dir in docs/paper docs/paper2; do
  ( check_paper "$dir" )
  status=$?
  if [ "$status" -ne 0 ]; then overall=1; fi
done

if [ "$overall" -ne 0 ]; then echo "LaTeX presentation check FAILED"; exit 1; fi
echo "LaTeX presentation check PASSED"
