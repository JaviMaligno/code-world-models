"""Rebuild the per-iteration ledger of an agent-relayed cross-family arm.

The relay harness (scripts/continuous_claude_step.py) records the terminal cell
of each seed in claude_results.json, but the paper's claim about the refine
loop is about the WHOLE trajectory: which artifact each iteration produced and
what the gate said about it. That trajectory is fully determined by the
versioned transcripts -- pipeline message `*_msg{i}.txt` and relayed reply
`*_reply{i}.txt` -- so this script re-derives it from them instead of trusting
notes: it re-gates every reply against the same sample the harness used, and
classifies the mode rule the artifact wrote.

The rule classification is syntactic and deliberately coarse (it names the
template, it does not judge correctness -- the gate does that):
  blind          no mode rule at all
  halfplane      a 1D threshold on a coordinate (x2 > c, x2 >= c, ...)
  strip          a two-sided band on ONE coordinate (abs(y) < c, ...)
  box            two-sided bands on BOTH coordinates (the true square's form)
  disc-landing   a radial predicate on the LANDING position (x2, y2)
  disc-current   a radial predicate on the CURRENT position (x, y)
  reward-zone    a predicate on distance to a reward lode or on reward itself
  other          a mode rule none of the above patterns matched

Run (paper 2, PatchField2D Claude arm):
  PYTHONPATH=src python scripts/claude_relay_ledger.py \
      results/claude_relay_transcripts --tag patch2d_k3_7 --k1 3 --k2 7
"""
import argparse
import json
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D  # noqa: E402
from cwm.continuous.contract import (  # noqa: E402
    collect_transitions, contract_accuracy, sample_contains_mode)
from cwm.continuous.instruments import spec_for  # noqa: E402
from cwm.synthesizer import extract_code  # noqa: E402

N_ROLLOUTS = 40
EPS = 1e-9

# The mode rule is whatever step() does beyond the pinned integrator, so read
# only the part of the module before reward().
LANDING = re.compile(r"(hypot|sqrt)\s*\(\s*x2|x2\s*-\s*[^)]*\)\s*\*\*\s*2")
CURRENT = re.compile(r"(hypot|sqrt)\s*\(\s*x\s*-|\(\s*x\s*-\s*[^)]*\)\s*\*\*\s*2")
THRESH = re.compile(r"if\s+[xy]2?\s*[<>]=?")
BAND_X = re.compile(r"abs\s*\(\s*x2?\s*[-)]")
BAND_Y = re.compile(r"abs\s*\(\s*y2?\s*[-)]")
REWARD_ANCHOR = re.compile(r"-6\.0|12\.0|reward|d1\s*[<>]|d2\s*[<>]|r\s*<=")


def classify(code: str) -> str:
    body = code.split("def reward")[0]
    rule = "\n".join(l for l in body.splitlines()
                     if re.search(r"\bif\b|hypot|sqrt|\*\*\s*2|abs\s*\(", l))
    if not rule.strip():
        return "blind"
    if REWARD_ANCHOR.search(rule) and not THRESH.search(rule) \
            and not (BAND_X.search(rule) or BAND_Y.search(rule)):
        return "reward-zone"
    if LANDING.search(rule):
        return "disc-landing"
    if CURRENT.search(rule):
        return "disc-current"
    bx, by = bool(BAND_X.search(rule)), bool(BAND_Y.search(rule))
    if bx and by:
        return "box"          # the true square's max/abs form
    if bx or by:
        return "strip"        # a band on one coordinate only
    if THRESH.search(rule):
        return "halfplane"
    return "other"


def build_ledger(transcript_dir, tag, k1, k2):
    env = PatchField2D(p1=(k1, 0.0), p2=(k2, 0.0))
    rows = []
    for reply in sorted(pathlib.Path(transcript_dir).glob(f"{tag}_*_reply*.txt")):
        stem = reply.name[:-len(".txt")]
        head, _, it = stem.rpartition("_reply")
        arm = "full" if "_full_" in head else "incomplete"
        seed = int(re.search(r"seed(\d+)", head).group(1))
        transitions = collect_transitions(env, N_ROLLOUTS, seed=seed)
        code = extract_code(reply.read_text())
        acc, _ = contract_accuracy(code, transitions, EPS)
        rows.append({"arm": arm, "seed": seed, "iteration": int(it),
                     "gate_accuracy": acc, "gate_passed": acc == 1.0,
                     "rule_class": classify(code),
                     "sample_contains_mode": sample_contains_mode(transitions),
                     "sample_contains_mode_per":
                         spec_for(env).sample_modes(env, transitions),
                     "reply_file": str(reply)})
    rows.sort(key=lambda r: (r["arm"], r["seed"], r["iteration"]))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript_dir")
    ap.add_argument("--tag", default="patch2d_k3_7",
                    help="transcript filename prefix, e.g. patch2d_k3_7")
    ap.add_argument("--k1", type=float, default=3.0)
    ap.add_argument("--k2", type=float, default=7.0)
    ap.add_argument("--out", default=None,
                    help="output JSON (default results/continuous_claude_"
                         "relay_{tag}.json)")
    args = ap.parse_args(argv)

    rows = build_ledger(args.transcript_dir, args.tag, args.k1, args.k2)
    out = pathlib.Path(args.out or
                       f"results/continuous_claude_relay_{args.tag}.json")
    out.write_text(json.dumps(
        {"script": "claude_relay_ledger.py", "tag": args.tag,
         "instrument": "patch2d", "k1": args.k1, "k2": args.k2,
         "n_rollouts": N_ROLLOUTS, "eps": EPS, "rows": rows}, indent=2))

    for r in rows:
        print(f"{r['arm']:>10} seed={r['seed']} it={r['iteration']} "
              f"gate={r['gate_accuracy']:.4f} {r['rule_class']}")
    print(f"wrote {out}  [{len(rows)} relayed replies]")


if __name__ == "__main__":
    main()
