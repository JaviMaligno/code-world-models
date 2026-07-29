"""Sync the hand-typed numbers in docs/paper2/REPRO-FACTS.md to results/repro_manifest.json.

REPRO-FACTS.md is prose written from the manifest, and its own header says "quote the key,
not this file". That caveat is not a licence for the numbers in it to be wrong: eight new
campaigns moved the call accounting from 625 cells / 1959 calls to over a thousand cells, and
creating the release tag falsified its "the repository carries no git tag" gap. Every
hand-typed constant in this paper that a review caught was of exactly this kind, so the fix
is a script rather than an edit.

Idempotent, and it asserts each anchor is unique before touching anything.

Run: PYTHONPATH=src python scripts/repro_manifest.py && python scripts/sync_repro_facts.py
"""
import json
import pathlib
import re
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
DOC = _REPO / "docs" / "paper2" / "REPRO-FACTS.md"
MAN = _REPO / "results" / "repro_manifest.json"

CAMPAIGN_ROWS = [("LLM synthesis, PatchField2D", "LLM synthesis, PatchField2D"),
                 ("LLM synthesis, pendulum", "LLM synthesis, pendulum"),
                 ("LLM synthesis, 1D cart", "LLM synthesis, 1D cart")]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, cwd=_REPO).stdout.strip()


def main() -> None:
    man = json.loads(MAN.read_text())
    cost = man["llm_cost"]
    by = cost["by_campaign"]
    total_calls = cost["total_llm_calls_paper2_api_arms"]
    total_cells = sum(v["cells"] for v in by.values())
    tag_present = man["dependencies"]["release_tag_present"]
    tags = sh("git", "tag", "--sort=-creatordate").split("\n")
    tags = [t for t in tags if t]

    text = DOC.read_text()
    subs = []

    # the per-campaign table rows and the total
    for label, key in CAMPAIGN_ROWS:
        if key not in by:
            sys.exit(f"manifest has no campaign {key!r}")
        pat = re.compile(r"\| " + re.escape(label) + r" \| (\d+) \| (\d+) \|")
        m = pat.search(text)
        if not m:
            sys.exit(f"row not found for {label!r}")
        subs.append((f"row {label}", m.group(0),
                     f"| {label} | {by[key]['cells']} | {by[key]['llm_calls']} |"))
    m = re.search(r"\| \*\*total API arms\*\* \| \*\*\d+\*\* \| \*\*\d+\*\* \|", text)
    if not m:
        sys.exit("total row not found")
    subs.append(("total row", m.group(0),
                 f"| **total API arms** | **{total_cells}** | **{total_calls}** |"))

    # the prose that quotes the total
    for m in re.finditer(r"(\d+) of the (\d+)\.", text):
        if m.group(2) != str(total_calls):
            subs.append(("guided-prompt fraction", m.group(0),
                         f"{m.group(1)} of the {total_calls}."))
    for m in re.finditer(r"the measured (\d+) calls at", text):
        if m.group(1) != str(total_calls):
            subs.append(("measured-calls phrase", m.group(0),
                         f"the measured {total_calls} calls at"))

    # honest gap (b): the tag now exists, so the gap is the DOI alone
    old_gap = ("(b) `dependencies.release_tag_present = false`: the repository carries "
               "**no git\ntag**, so nothing citable identifies \"the code that produced "
               "Table 3\". A release\ntag (and ideally a Zenodo DOI over the tag) is still "
               "required.")
    if tag_present and old_gap in text:
        newest = tags[0] if tags else "(none)"
        subs.append(("honest gap (b)", old_gap,
                     f"(b) `dependencies.release_tag_present = true`: the repository now "
                     f"carries release\ntags ({', '.join(tags)}; newest `{newest}`), so a "
                     f"citable revision identifies the code that\nproduced each table. What "
                     f"is still absent is a DOI over the tag — a Zenodo or\nfigshare deposit, "
                     f"which no venue this is bound for requires and which needs an\naccount "
                     f"rather than a commit. Recorded as absent, not as blocking."))

    # the audit-check count, which every new campaign moves
    checks = man["audit_coverage"]["audit_checks_executed"]
    for m in re.finditer(r"re-derives \*\*(\d+)\*\*", text):
        if m.group(1) != str(checks):
            subs.append(("audit count (bold)", m.group(0), f"re-derives **{checks}**"))
    for m in re.finditer(r"`audit_coverage\.audit_checks_executed = (\d+)`", text):
        if m.group(1) != str(checks):
            subs.append(("audit count (key)", m.group(0),
                         f"`audit_coverage.audit_checks_executed = {checks}`"))
    for m in re.finditer(r"outside those (\d+) checks", text):
        if m.group(1) != str(checks):
            subs.append(("audit count (prose)", m.group(0),
                         f"outside those {checks} checks"))

    # and the snapshot header, so the file says which revision it describes
    head = sh("git", "rev-parse", "--short", "HEAD")
    when = sh("git", "log", "-1", "--date=iso", "--format=%ad")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
    m = re.search(r"Snapshot: git `[0-9a-f]+` \(`[^`]+`\), branch\n`[^`]+`", text)
    if m:
        subs.append(("snapshot header", m.group(0),
                     f"Snapshot: git `{head}` (`{when}`), branch\n`{branch}`"))
    m = re.search(r"Manifest generated 2026-\d\d-\d\d\.", text)
    if m:
        gen = man.get("generated_at", man.get("timestamp", ""))[:10] or when[:10]
        subs.append(("manifest date", m.group(0), f"Manifest generated {gen}."))

    applied = []
    for name, old, new in subs:
        if old == new:
            continue
        if text.count(old) != 1:
            sys.exit(f"ANCHOR NOT UNIQUE ({name}): {text.count(old)}")
        text = text.replace(old, new)
        applied.append(name)
    DOC.write_text(text)
    print(f"synced {len(applied)}: {', '.join(applied) or 'nothing (already current)'}")
    print(f"now: {total_cells} cells, {total_calls} calls, tag_present={tag_present}")


if __name__ == "__main__":
    main()
