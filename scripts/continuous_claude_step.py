"""Manual-transport harness for the Claude arm of the continuous cross-family
probe (paper 2; mirrors paper 1's scripts/crossfamily_claude_step.py).

Claude is reached through an agent session (subscription) rather than an API
key, so the synthesize/refine/gate loop is driven step by step: this script
emits EXACTLY the messages the pipeline would send (same contract, same
transition examples via cwm.continuous.contract.build_synthesis_messages,
same refinement format as refine_continuous), an agent relays them to a fresh
context-free Claude instance, and the returned code comes back here for the
same eps=1e-9 pinned-integrator gate and classification as
scripts/continuous_danger_synthesis.py (sample_contains_wall, gate accuracy,
mode blindness, and MPC play for gate-passing artifacts).

Usage:
  init SEED OUTDIR  [--instrument cart|pendulum] [--arm incomplete|full]
      -> writes OUTDIR/{tag}_seed{S}_msg0.txt (system+user, verbatim)
  check SEED OUTDIR ITER REPLYFILE [--instrument ...] [--arm ...]
      -> extracts the code block from REPLYFILE and gates it (same sample);
         if acc < 1.0 and ITER < 5 writes the next refinement message to
         {tag}_seed{S}_msg{ITER+1}.txt (verbatim refine_continuous format);
         else classifies the artifact (+ play if the gate passed) and appends
         the cell to OUTDIR/claude_results.json.

Protocol constants mirror the API arms: N=40 rollouts (sample doubles as the
gate), eps=1e-9, max 5 refinement iterations, 6 paired MPC play episodes.
"""
import argparse
import json
import pathlib
import statistics
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall, PendulumStop  # noqa: E402
from cwm.continuous import harness  # noqa: E402
from cwm.continuous.contract import (  # noqa: E402
    SynthesizedModel, build_contract, build_synthesis_messages,
    collect_transitions, contract_accuracy, mode_blindness,
    sample_contains_mode)
from cwm.synthesizer import extract_code  # noqa: E402

N_ROLLOUTS = 40
EPS = 1e-9
MAX_ITERS = 5
PLAY_EPISODES = 6

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("cmd", choices=["init", "check"])
ap.add_argument("seed", type=int)
ap.add_argument("outdir")
ap.add_argument("iter_or_reply", nargs="*", default=[])
ap.add_argument("--instrument", choices=["cart", "pendulum"], default="cart")
ap.add_argument("--arm", choices=["incomplete", "full"], default="incomplete")
args = ap.parse_args()

ENV = (CartWall(x_wall=8.0) if args.instrument == "cart"
       else PendulumStop(th_stop=1.4))
TAG = f"{args.instrument}_{args.arm}"
OUT = pathlib.Path(args.outdir)
OUT.mkdir(parents=True, exist_ok=True)

transitions = collect_transitions(ENV, N_ROLLOUTS, seed=args.seed)
contract = build_contract(ENV, include_mode=(args.arm == "full"))


def _msg_path(i: int) -> pathlib.Path:
    return OUT / f"{TAG}_seed{args.seed}_msg{i}.txt"


if args.cmd == "init":
    msgs = build_synthesis_messages(contract, transitions)
    text = (f"=== SYSTEM ===\n{msgs[0]['content']}\n"
            f"=== USER ===\n{msgs[1]['content']}\n")
    _msg_path(0).write_text(text)
    print(f"wrote {_msg_path(0)}  "
          f"sample_contains_mode={sample_contains_mode(transitions)}")
    sys.exit(0)

# --- check ---------------------------------------------------------------
if len(args.iter_or_reply) != 2:
    sys.exit("check needs: ITER REPLYFILE")
it = int(args.iter_or_reply[0])
reply = pathlib.Path(args.iter_or_reply[1]).read_text()
code = extract_code(reply)
acc, failures = contract_accuracy(code, transitions, EPS)
print(f"[{TAG} seed={args.seed} iter={it}] gate={acc:.4f}")

if acc < 1.0 and it < MAX_ITERS:
    # verbatim refine_continuous message format (single user message)
    msg = (f"{contract}\n\nThe current implementation is below. It fails "
           f"some transitions. Fix it so every transition matches to "
           f"within {EPS} in x, v and reward. Output only one ```python "
           f"code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
           f"FAILURES (expected vs got):\n" + "\n".join(failures[:20]))
    _msg_path(it + 1).write_text(f"=== USER ===\n{msg}\n")
    print(f"wrote {_msg_path(it + 1)}")
    sys.exit(0)

# terminal: classify (and play if the gate passed), mirroring
# synthesize_and_evaluate + the danger script's play block.
cell = {
    "model": "claude-sonnet (agent-relayed)",
    "instrument": args.instrument,
    "arm": args.arm,
    "seed": args.seed,
    "n_rollouts": N_ROLLOUTS,
    "eps": EPS,
    "sample_contains_wall": sample_contains_mode(transitions),
    "gate_accuracy": acc,
    "gate_passed": acc == 1.0,
    "refine_iterations": it,
    "wall_blindness": mode_blindness(code, ENV) if acc == 1.0 else None,
    "code": code,
    "transcript_prefix": str(_msg_path(0))[:-len("_msg0.txt")],
}
if cell["gate_passed"]:
    base_t, base_r = [], []
    for i in range(PLAY_EPISODES):
        sd = 900_000 + 1000 * i
        base_t.append(harness.run_episode(ENV, ENV, "mpc", sd).ret)
        base_r.append(harness.run_episode(ENV, policy="random", seed=sd).ret)
    j_truth, j_random = statistics.mean(base_t), statistics.mean(base_r)
    model = SynthesizedModel(code, ENV)
    eps_play = [harness.run_episode(ENV, model, "mpc", 900_000 + 1000 * i)
                for i in range(PLAY_EPISODES)]
    j = statistics.mean(e.ret for e in eps_play)
    cell["j_truth"], cell["j_random"], cell["j_play"] = j_truth, j_random, j
    cell["play_cost"] = (j_truth - j) / (j_truth - j_random)
    cell["play_contact_rate"] = (
        sum(e.contact for e in eps_play) / len(eps_play))

results = OUT / "claude_results.json"
data = json.loads(results.read_text()) if results.exists() else []
data = [c for c in data
        if not (c["instrument"] == args.instrument and c["arm"] == args.arm
                and c["seed"] == args.seed)]
data.append(cell)
results.write_text(json.dumps(data, indent=2))
print(f"classified: gate_passed={cell['gate_passed']} "
      f"blind={cell['wall_blindness']} "
      f"play_cost={cell.get('play_cost', 'n/a')} -> {results}")
