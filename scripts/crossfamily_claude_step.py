"""Manual-transport harness for the Claude arm of the cross-family probe.

Claude is reached through an agent session (subscription) rather than an API
key, so the synthesis/refinement loop is driven step by step: this script
emits EXACTLY the messages the pipeline would send (same contract, same
trajectory examples, same refinement feedback format as cwm.synthesizer /
cwm.refiner), an agent relays them to a fresh context-free Claude instance,
and the returned code comes back here for the same gate check and
rule_status classification as scripts/danger_synthesis_sweep.py.

Usage:
  init SEED OUTDIR             -> writes OUTDIR/seed{S}_msg0.txt (system+user)
  check SEED OUTDIR ITER CODE  -> gates CODE (fresh batch, like resample_fn);
                                  if acc < 1.0 and ITER < 6 writes the next
                                  refinement message to seed{S}_msg{ITER+1}.txt;
                                  else classifies rule_status and appends the
                                  outcome to OUTDIR/claude_results.json.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess_material as truth
from cwm.groundtruth import gen_chess as base
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories
from cwm.synthesizer import build_synthesis_messages
from cwm.refiner import contract_accuracy
from cwm.run_gap import _load_module_from_code

N = 200
contract = build_contract(base.RULES_TEXT)   # INCOMPLETE rules


def rule_region_states():
    S = []
    b = [0]*26; b[0]=1; b[24]=4; b[5]=2;  b[25]=100; S.append({"board": b, "current_player": 1})
    b = [0]*26; b[2]=1; b[22]=4; b[10]=3; b[25]=100; S.append({"board": b, "current_player": 2})
    b = [0]*26; b[0]=1; b[24]=4; b[20]=5; b[25]=100; S.append({"board": b, "current_player": 1})
    return S


TEST = rule_region_states()
TRUTH_RET = [truth.returns(s) for s in TEST]


def _norm_returns(r):
    """Normalize key type so a string-keyed returns dict (which passes the
    JSON-round-tripped gate) is not misclassified as blind by the in-process
    comparison (audit finding: latent gate-vs-rule_status asymmetry)."""
    try:
        return {int(k): float(v) for k, v in r.items()}
    except (ValueError, TypeError, AttributeError):
        return r


def rule_status(code):
    try:
        m = _load_module_from_code(code)
        for s, tr in zip(TEST, TRUTH_RET):
            if _norm_returns(m.returns({"board": list(s["board"]),
                          "current_player": s["current_player"]})) != tr:
                return "blind", None
        return "aware", None
    except Exception as e:
        return "crash", repr(e)[:200]


def cmd_init(seed, outdir):
    traj = collect_trajectories(truth, n_games=N, seed=seed)
    msgs = build_synthesis_messages(contract, traj)
    text = (f"[SYSTEM]\n{msgs[0]['content']}\n\n[USER]\n{msgs[1]['content']}")
    p = Path(outdir) / f"seed{seed}_msg0.txt"
    p.write_text(text)
    print(f"wrote {p} ({len(text)} chars)")


def cmd_check(seed, outdir, iteration, code_file):
    code = Path(code_file).read_text()
    # fresh batch per refinement iteration, exactly like the sweep's resample_fn
    traj = collect_trajectories(truth, n_games=N, seed=seed + 1000 * max(iteration, 1)) \
        if iteration > 0 else collect_trajectories(truth, n_games=N, seed=seed)
    acc, failures = contract_accuracy(code, traj)
    print(f"seed={seed} iter={iteration}: gate_acc={acc:.4f}")
    if acc < 1.0 and iteration < 6:
        msg = (
            f"{contract}\n\nThe current implementation is below. It fails some "
            f"transitions. Fix it so every transition matches. Output only one "
            f"```python code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
            f"FAILURES (expected vs got):\n" + "\n".join(failures[:20])
        )
        p = Path(outdir) / f"seed{seed}_msg{iteration + 1}.txt"
        p.write_text("[USER]\n" + msg)
        print(f"REFINE -> wrote {p}")
        return
    status, err = rule_status(code)
    print(f"FINAL: status={status} gate_acc={acc:.4f} iters={iteration}"
          + (f" ERR={err}" if err else ""))
    dest = Path(outdir) / "claude_results.json"
    data = json.loads(dest.read_text()) if dest.exists() else {"per_seed": []}
    data["per_seed"].append({"seed": seed, "status": status, "error": err,
                             "gate_acc": acc, "iters": iteration, "code": code})
    dest.write_text(json.dumps(data, indent=2))
    print(f"appended to {dest}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init(int(sys.argv[2]), sys.argv[3])
    elif cmd == "check":
        cmd_check(int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5])
