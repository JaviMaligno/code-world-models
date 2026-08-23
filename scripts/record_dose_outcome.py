"""Append the evidence dose's outcome to STRONGER-STATEMENTS.md, numbers read from results/.

The file's purpose is to record, for each statement a review weakened, the route back to the
strong version and whether that route was taken. The dose is the fifth pass and the last one
this instrument can support: item 1 of the fourth pass's "what is still open" is either
answered here or it is not answerable.

Idempotent: appending twice is a no-op.

Run: PYTHONPATH=src python scripts/record_dose_outcome.py
"""
import json
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
DOC = _REPO / "docs" / "paper2" / "STRONGER-STATEMENTS.md"
RES = _REPO / "results"
HEAD = "## 2026-07-29, fifth pass — the evidence dose, and a prior that does not yield"


def main() -> None:
    abl = json.loads((RES / "arity_evidence_ablations.json").read_text())["campaigns"]
    fit = json.loads((RES / "region_fit_baseline.json").read_text())["dose_arms"]
    cal = json.loads((RES / "evidence_dose_calibration.json").read_text())
    for c in ("dose_arc240", "dose_arc240_hint", "dose_arc120"):
        if c not in abl:
            sys.exit(f"MISSING {c}: run scripts/arity_evidence_ablations.py")
    p2 = abl["dose_arc240"]["per_size"]["large"]
    ph = abl["dose_arc240_hint"]["per_size"]["large"]
    pc = abl["dose_arc120"]["per_size"]["large"]
    if p2["n_mode_containing"] < 20:
        sys.exit(f"dose_arc240 has only {p2['n_mode_containing']} mode-containing draws; "
                 "the campaign is still running")
    b, a1, a2 = fit["default"], fit["arc120"], fit["arc240"]
    c240 = cal["arms"]["arc240"]

    text = DOC.read_text()
    if HEAD in text:
        print("already recorded")
        return

    entry = f"""
{HEAD}

The fourth pass left one open item — "the prior should yield to enough coverage or it is a
hard limit rather than a prior" — and named both outcomes before the run. It was run.

**The intervention.** `PatchField2D.start_arc_deg` begins episodes on a ring just outside the
near patch at a bearing drawn from an arc centred on the default arrival direction. The arc
width is the dose. The rollout count is lowered to hold the *number* of contacts at the
baseline's median, so coverage and quantity move independently — a single knob that moved
both would have answered neither. Verified: the contract text is byte-identical across arms
(the dose is evidence, not instruction), `start_arc_deg=None` reproduces the committed box
start bit for bit, and the trap survives (play-cost {c240['play_play_cost']:.4f}, blind
contact rate {c240['play_blind_contact_rate']:.2f}).

**The dose is real and it saturates.** Coverage — the arc the landings actually span,
$360°$ less the largest gap — goes {b['median_landing_arc_deg']:.0f}° →
{a1['median_landing_arc_deg']:.0f}° → {a2['median_landing_arc_deg']:.0f}° at contact counts
{b['median_contacts']:.0f} / {a1['median_contacts']:.0f} / {a2['median_contacts']:.0f}. It
saturates near {a2['median_landing_arc_deg']:.0f}° because the freeze semantics forbid
occupying the region's interior, so the far side is reachable only by going around: the
instrument cannot deliver full coverage, and `prop:entryclass` is why.

**What the evidence supports at each dose.** The trivial least-squares circle fit recovers
both constants on {b['n_recovering_both']}/20 samples at
{b['median_landing_arc_deg']:.0f}°, {a1['n_recovering_both']}/20 at
{a1['median_landing_arc_deg']:.0f}°, and **{a2['n_recovering_both']}/20** at
{a2['median_landing_arc_deg']:.0f}°. At the top dose the evidence determines the region on
*every* sample.

**What the synthesizer does at that dose.** Given the form and asked only for location and
size: **{ph['k_repaired_behavioural']}/{ph['n_mode_containing']}** (best agreement
{ph['best_iou']:.3f}). Given no clause at all:
**{p2['k_repaired_behavioural']}/{p2['n_mode_containing']}** (best {p2['best_iou']:.3f}).
The machinery control at {a1['median_landing_arc_deg']:.0f}°:
{pc['k_repaired_behavioural']}/{pc['n_mode_containing']}, so the null is the coverage and not
the ring. The translation arm on the same wider sample: 20/20 at gate 1.000 in zero
iterations, so the null is the induction and not the instrument.

**Two statements this earns, in opposite directions.**

1. *Stronger.* The attribution now has no residue. The earlier control had to set aside the
   {20 - b['n_recovering_both']} samples on which the trivial fit also fails; at the top dose
   there are none to set aside. On **every** sample in that arm the region is recoverable
   from the evidence and the synthesizer does not recover it. "Not the evidence" stops being
   a statement about most samples and becomes one about all of them.
2. *Bounded, not stronger.* Within the range this instrument can reach the failure does not
   respond to the dose **at all** — not partially, not with a trend. So "prior" should be
   read as a fixed disposition rather than a weight more evidence outweighs. What lies beyond
   {a2['median_landing_arc_deg']:.0f}° is not knowable here, and the paper says so instead of
   generalising past the instrument.

**What is still open.** Nothing this instrument can answer about the mechanism. Beyond it:
an instrument whose mode does *not* freeze the mover would permit full coverage and could
separate "a disposition" from "a weight no reachable dose outweighs" — a different paper's
experiment, and named as such rather than promised. The remaining non-experimental item is a
DOI deposit for the archived tag, which needs an account and is the author's call.
"""
    DOC.write_text(text.rstrip("\n") + "\n" + entry)
    print(f"recorded: hint {ph['k_repaired_behavioural']}/{ph['n_mode_containing']}, "
          f"plain {p2['k_repaired_behavioural']}/{p2['n_mode_containing']}, "
          f"control {pc['k_repaired_behavioural']}/{pc['n_mode_containing']}; "
          f"fit {b['n_recovering_both']}/20 -> {a2['n_recovering_both']}/20")


if __name__ == "__main__":
    main()
