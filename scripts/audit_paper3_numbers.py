"""Audit paper 3's tables against the JSONs that produced them.

Paper 2 has `audit_paper2_numbers.py`; paper 3 had no equivalent, and that
is how a wrong cell survived every review round: `tab:ndim` printed
$r(6) = 0^{\\dagger}$ (a censored zero) while
`results/continuous_shellfield.json` records 1 contact in 600 rollouts at
$n = 6$. Nobody cross-checked the row against its own file — the claims
linter only checks the *form* of a printed zero, not whether the count
behind it is really zero.

This script parses the tabulars in `docs/paper3/main.tex` by label and
compares every cell it can source against the committed result JSONs, at
the paper's own printed precision. A censored cell (`$0^{\\dagger}$`) must
correspond to a count of exactly 0; an exact cell (`$0^{\\ast}$`) is
theorem-backed and only checked for being 0.

    python scripts/audit_paper3_numbers.py            # audit, exit 1 on mismatch
    python scripts/audit_paper3_numbers.py --verbose  # print every comparison
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
TEX = REPO / "docs" / "paper3" / "main.tex"
RES = REPO / "results"

CENSORED = "dagger"
EXACT = "ast"


class Mismatch(Exception):
    pass


def jload(name: str):
    return json.loads((RES / name).read_text())


def tables(tex: str) -> dict[str, list[list[str]]]:
    """Every tabular in the file, keyed by the \\label that follows it."""
    out: dict[str, list[list[str]]] = {}
    for block in re.findall(r"\\begin\{tabular\}(.*?)\\end\{tabular\}(.*?)(?=\\begin\{tabular\}|\Z)",
                            tex, re.S):
        body, tail = block
        m = re.search(r"\\label\{([^}]+)\}", tail)
        if not m:
            continue
        rows = []
        for line in body.split("\\\\"):
            line = re.sub(r"\\(top|mid|bottom)rule", "", line).strip()
            if not line or line.startswith("%"):
                continue
            rows.append([c.strip() for c in line.split("&")])
        out[m.group(1)] = rows
    return out


def parse_cell(cell: str) -> tuple[float, str | None]:
    """The number a cell prints, plus its marker (censored / exact / None)."""
    marker = None
    if CENSORED in cell:
        marker = CENSORED
    elif EXACT in cell:
        marker = EXACT
    s = cell
    s = re.sub(r"\^\{?\\(dagger|ast)\}?", "", s)
    s = s.replace("$", "").replace("\\,", "").replace("{,}", "").replace(",", "")
    s = s.replace("\\mathbf{", "").replace("\\textbf{", "").replace("}", "")
    sci = re.search(r"([0-9.]+)\s*\\times\s*10\^\{?(-?[0-9]+)\}?", s)
    if sci:
        return float(sci.group(1)) * 10 ** int(sci.group(2)), marker
    num = re.search(r"-?[0-9]*\.?[0-9]+", s)
    if not num:
        raise Mismatch(f"cannot parse cell {cell!r}")
    return float(num.group(0)), marker


def decimals(cell: str) -> int:
    s = cell.replace("$", "")
    m = re.search(r"\.([0-9]+)", s)
    return len(m.group(1)) if m else 0


def check(label: str, what: str, cell: str, measured: float,
          *, count: int | None = None, verbose: bool = False) -> list[str]:
    """Compare one printed cell against its measured value."""
    printed, marker = parse_cell(cell)
    problems = []
    if marker == CENSORED:
        if count is None:
            # No occurrence count for this column (e.g. an episode-rate zero):
            # all that is checkable is that the measured rate really is zero.
            if measured != 0:
                problems.append(
                    f"{label}: {what} printed as a CENSORED ZERO ({cell}) but the "
                    f"JSON records {measured:.6g}")
            elif verbose:
                print(f"  ok  {label:16s} {what:34s} censored, measured 0")
        elif count != 0:
            problems.append(
                f"{label}: {what} printed as a CENSORED ZERO ({cell}) but the JSON "
                f"records {count} occurrence(s) (rate {measured:.6g})")
        return problems
    tol = 0.5 * 10 ** (-decimals(cell)) if decimals(cell) else 0.5
    if abs(printed - measured) > tol + 1e-12:
        problems.append(
            f"{label}: {what} printed {printed:g} ({cell}) but measured "
            f"{measured:.6g} (tolerance {tol:g})")
    elif verbose:
        print(f"  ok  {label:16s} {what:34s} {printed:g} ≈ {measured:.6g}")
    return problems


def audit_ndim(t: dict, verbose: bool) -> list[str]:
    label = "tab:ndim"
    rows = t.get(label)
    if not rows:
        return [f"{label}: table not found"]
    hdr, *body = rows
    ns = [int(x) for x in hdr[1:]]
    rar = {r["n"]: r for r in jload("continuous_shellfield.json")["rows"]}
    nav = {r["n"]: r for r in jload("continuous_shellfield_nav.json")["rows"]}
    play = {r["n"]: r for r in jload("continuous_shellfield_play.json")["rows"]}
    spec = {
        "$r(n)$": (rar, "r", "contacts"),
        "$J$ truth-MPC": (nav, "j_truth_mpc", None),
        "$J$ random": (nav, "j_random", None),
        "$\\mathrm{pc}_{\\mathrm{blind}}$": (play, "play_cost", None),
        "blind contact": (play, "blind_contact_rate", None),
    }
    problems = []
    for row in body:
        name = row[0].strip()
        if name not in spec:
            continue
        src, field, count_field = spec[name]
        for n, cell in zip(ns, row[1:]):
            if n not in src:
                problems.append(f"{label}: no JSON row for n={n} ({name})")
                continue
            cnt = src[n].get(count_field) if count_field else None
            problems += check(label, f"{name} n={n}", cell, src[n][field],
                              count=cnt, verbose=verbose)
    return problems


def audit_dangercurve(t: dict, verbose: bool) -> list[str]:
    label = "tab:dangercurve"
    rows = t.get(label)
    if not rows:
        return [f"{label}: table not found"]
    hdr, *body = rows
    gaps = [float(x) for x in hdr[1:]]
    curve = {round(r["gap"], 4): r for r in
             jload("continuous_ring2d_open_sweep_summary.json")["pc_blind_curve"]}
    problems = []
    for row in body:
        name = row[0].strip()
        if "pc" not in name.lower() and "contact" not in name.lower():
            continue
        for gap, cell in zip(gaps, row[1:]):
            r = curve.get(round(gap, 4))
            if r is None:
                problems.append(f"{label}: no sweep row for gap={gap}")
                continue
            if "pc" in name.lower():
                problems += check(label, f"pc gap={gap}", cell, r["play_cost"],
                                  verbose=verbose)
            # the contact row's per-gap rate is not carried in this summary
    return problems


def audit_thinneck(t: dict, verbose: bool) -> list[str]:
    label = "tab:thinneck"
    rows = t.get(label)
    if not rows:
        return [f"{label}: table not found"]
    by_knob = {r["knob"]: r for r in jload("ring2d_thin_neck.json")["rows"]}
    cols = ["r", "r_interior", "disagree_fill_rate", "play_cost_blind", "play_cost_filled"]
    problems = []
    for row in rows[1:]:
        knob = row[0].strip()
        key = "closed" if knob == "closed" else f"nk{knob}"
        src = by_knob.get(key)
        if src is None:
            problems.append(f"{label}: no thin-neck row for {knob!r} (key {key})")
            continue
        counts = {
            "r": src.get("contacts"),
            "r_interior": src.get("interior_entries"),
            "disagree_fill_rate": src.get("disagree_transitions"),
            "play_cost_blind": None,
            "play_cost_filled": None,
        }
        for field, cell in zip(cols, row[1:]):
            measured = src.get(field)
            if measured is None:
                if field == "disagree_fill_rate" and "disagree_transitions" in src:
                    measured = src["disagree_transitions"] / src["transitions"]
                else:
                    problems.append(f"{label}: field {field} missing for {key}")
                    continue
            problems += check(label, f"{knob} {field}", cell, measured,
                              count=counts[field], verbose=verbose)
    return problems


def audit_prose(tex: str, verbose: bool) -> list[str]:
    """The counted claims that live in prose rather than a table."""
    problems = []
    audit = jload("heldout_gate_audit_ring2d.json")["aggregates"]
    tot = audit["totals"]
    cont = audit["a_contingency"]
    facts = {
        "held-out artifacts": tot["n_artifacts"],
        "synthesis conditions": tot["n_files"],
        "contingency n": cont["incomplete_arm"]["n"],
        "independent blocks": cont["n_independent_blocks"],
        "in-sample passes": tot["n_in_sample_passed"],
        "regressions": tot["n_regressions"],
    }
    for what, value in facts.items():
        # The counts are quoted in several shapes ("$903$ synthesized artifacts",
        # "$156/156$ artifacts"), so require the number in maths mode and leave
        # the wording around it to the claims linter.
        if not re.search(rf"\${value}(/|\$|\s|\\)", tex):
            problems.append(f"prose: {what} = {value} not present in the tex")
        elif verbose:
            print(f"  ok  prose            {what:34s} {value}")

    iv = jload("ring2d_summary_intervention.json")["primary_flip_vs_contemporaneous"]
    for what, value in (("discordant", iv["discordant"]),
                        ("toward claim", iv["toward_claim"]),
                        ("against", iv["against_claim"])):
        if f"${value}$" not in tex:
            problems.append(f"prose: intervention {what} = {value} not present in the tex")
        elif verbose:
            print(f"  ok  prose            intervention {what:22s} {value}")
    p = iv["p_two_sided"]
    if f"{p:.3f}" not in tex:
        problems.append(f"prose: intervention p = {p:.3f} not present in the tex")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    tex = TEX.read_text(encoding="utf-8")
    t = tables(tex)
    print(f"paper 3 tables found: {', '.join(sorted(t))}")

    problems: list[str] = []
    for fn in (audit_ndim, audit_dangercurve, audit_thinneck):
        problems += fn(t, args.verbose)
    problems += audit_prose(tex, args.verbose)

    if problems:
        print(f"\n{len(problems)} MISMATCH(ES):")
        for p in problems:
            print("  -", p)
        return 1
    print("all audited cells and counted claims agree with the JSONs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
