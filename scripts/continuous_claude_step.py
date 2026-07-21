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
  init SEED OUTDIR  [--instrument cart|pendulum|ring2d] [--arm incomplete|full]
      [--gap G] [--channel facing|hidden] [--start outside|inside]
      [--prompt-variant default|region|tda]   (last four: ring2d only)
      -> writes OUTDIR/{tag}_seed{S}_msg0.txt (system+user, verbatim)
  check SEED OUTDIR ITER REPLYFILE [--instrument ...] [--arm ...] [ring2d knobs]
      -> extracts the code block from REPLYFILE and gates it (same sample);
         if acc < 1.0 and ITER < 5 writes the next refinement message to
         {tag}_seed{S}_msg{ITER+1}.txt (verbatim refine_continuous format);
         else classifies the artifact (+ play if the gate passed) and appends
         the cell to OUTDIR/claude_results.json (cart/pendulum) or
         OUTDIR/claude_results_ring2d_{knob}[_pv-variant].json (ring2d, so
         different ring2d configurations sharing an OUTDIR never collide).

Protocol constants mirror the API arms: N=40 rollouts (sample doubles as the
gate), eps=1e-9, max 5 refinement iterations, 6 paired MPC play episodes.

ring2d (2026-07-21): adds the paper-3 ring instrument to the relay, mirroring
scripts/continuous_danger_synthesis.py's ring2d env construction and
prompt-variant handling EXACTLY (same code path: build_synthesis_messages,
same PROMPT_VARIANTS table, same per-seed tda guidance via
continuous_danger_synthesis._tda_guidance) so the relay arm cannot drift from
the API arm's ring2d messages. cart/pendulum are untouched: --prompt-variant
is forced to "default" for them (guarded below), which resolves to the same
max_examples=30/guidance=""/max_failures=20 the script always used, so their
init/check output is byte-identical to before this change.
"""
import argparse
import json
import math
import pathlib
import statistics
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

from cwm.continuous.envs import CartWall, PendulumStop, RingField2D  # noqa: E402
from cwm.continuous import harness  # noqa: E402
from cwm.continuous.contract import (  # noqa: E402
    SynthesizedModel, build_contract, build_synthesis_messages,
    collect_transitions, contract_accuracy, mode_blindness,
    sample_contains_mode)
from cwm.synthesizer import extract_code  # noqa: E402

# Reuse (do not reimplement) the ring2d prompt-variant table and the per-seed
# tda guidance helper from the API arm's script -- same module, same code
# path, so the two arms cannot drift apart on the ring2d prompts.
import continuous_danger_synthesis as danger_synthesis  # noqa: E402

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
ap.add_argument("--instrument", choices=["cart", "pendulum", "ring2d"],
                default="cart")
ap.add_argument("--arm", choices=["incomplete", "full"], default="incomplete")
ap.add_argument("--gap", type=float, default=0.0,
                help="ring2d: angular channel width (0 = closed ring)")
ap.add_argument("--channel", choices=["facing", "hidden"], default="facing",
                help="ring2d: channel orientation -- facing the start "
                "(gap_center=pi) or hidden on the far side (gap_center=0)")
ap.add_argument("--start", choices=["outside", "inside"], default="outside",
                help="ring2d: initial-state placement (mu0 knob); inside "
                "puts x0 at the ring center")
ap.add_argument("--prompt-variant", choices=["default", "region", "tda"],
                default="default",
                help="ring2d-only confound-closure knob (paper 2 s10 / "
                "paper 3); see continuous_danger_synthesis.py --help for the "
                "full description of each variant")
args = ap.parse_args()

if args.instrument != "ring2d" and (
        args.gap != 0.0 or args.channel != "facing" or args.start != "outside"
        or args.prompt_variant != "default"):
    ap.error("--gap/--channel/--start/--prompt-variant are ring2d knobs")

if args.instrument == "ring2d":
    ENV = RingField2D(
        gap=args.gap,
        gap_center=math.pi if args.channel == "facing" else 0.0,
        x0_center=(0.0, 0.0) if args.start == "outside"
        else RingField2D().center)
    KNOB = (f"gap{args.gap:g}"
            + ("" if args.channel == "facing" else "-hid")
            + ("" if args.start == "outside" else "-in"))
    SUFFIX = (f"_pv-{args.prompt_variant}"
              if args.prompt_variant != "default" else "")
    TAG = f"ring2d_{KNOB}{SUFFIX}_{args.arm}"
    RESULTS_NAME = f"claude_results_ring2d_{KNOB}{SUFFIX}.json"
elif args.instrument == "pendulum":
    ENV = PendulumStop(th_stop=1.4)
    TAG = f"{args.instrument}_{args.arm}"
    RESULTS_NAME = "claude_results.json"
else:
    ENV = CartWall(x_wall=8.0)
    TAG = f"{args.instrument}_{args.arm}"
    RESULTS_NAME = "claude_results.json"

# args.prompt_variant is forced to "default" for cart/pendulum by the guard
# above, so VARIANT is always {"max_examples": 30, "guidance": "",
# "max_failures": 20} there -- the exact hardcoded values this script used
# before ring2d support, so init/check stay byte-identical for those paths.
VARIANT = danger_synthesis.PROMPT_VARIANTS[args.prompt_variant]
MAX_EXAMPLES = VARIANT["max_examples"]
MAX_FAILURES = VARIANT["max_failures"]

OUT = pathlib.Path(args.outdir)
OUT.mkdir(parents=True, exist_ok=True)

transitions = collect_transitions(ENV, N_ROLLOUTS, seed=args.seed)
contract = build_contract(ENV, include_mode=(args.arm == "full"))

# Per-seed dynamic guidance (the "tda" variant computes a topological
# summary of THIS seed's own contact evidence) is resolved from the sample,
# exactly as cwm.continuous.contract.synthesize_and_evaluate does.
GUIDANCE = VARIANT["guidance"]
GUIDANCE_TEXT = GUIDANCE(ENV, transitions) if callable(GUIDANCE) else GUIDANCE


def _msg_path(i: int) -> pathlib.Path:
    return OUT / f"{TAG}_seed{args.seed}_msg{i}.txt"


if args.cmd == "init":
    msgs = build_synthesis_messages(contract, transitions, MAX_EXAMPLES,
                                    guidance=GUIDANCE_TEXT)
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
    # verbatim refine_continuous message format (single user message);
    # MAX_FAILURES/GUIDANCE_TEXT are ("", 20) for cart/pendulum (byte-
    # identical to the pre-ring2d hardcoded failures[:20]/no-guidance form)
    msg = (f"{contract}\n\nThe current implementation is below. It fails "
           f"some transitions. Fix it so every transition matches to "
           f"within {EPS} in x, v and reward. Output only one ```python "
           f"code block.\n\nCURRENT CODE:\n```python\n{code}\n```\n\n"
           f"FAILURES (expected vs got):\n" + "\n".join(failures[:MAX_FAILURES])
           + (f"\n\n{GUIDANCE_TEXT}" if GUIDANCE_TEXT else ""))
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
if args.instrument == "ring2d":
    # provenance for the knobs baked into RESULTS_NAME/TAG (paper 3
    # analysis scripts read these off the cell, not the filename)
    cell["gap"] = args.gap
    cell["channel"] = args.channel
    cell["start"] = args.start
    cell["prompt_variant"] = args.prompt_variant
if GUIDANCE_TEXT:
    cell["guidance_text"] = GUIDANCE_TEXT   # audit trail, mirrors
                                            # synthesize_and_evaluate
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

results = OUT / RESULTS_NAME
data = json.loads(results.read_text()) if results.exists() else []
data = [c for c in data
        if not (c["instrument"] == args.instrument and c["arm"] == args.arm
                and c["seed"] == args.seed)]
data.append(cell)
results.write_text(json.dumps(data, indent=2))
print(f"classified: gate_passed={cell['gate_passed']} "
      f"blind={cell['wall_blindness']} "
      f"play_cost={cell.get('play_cost', 'n/a')} -> {results}")
