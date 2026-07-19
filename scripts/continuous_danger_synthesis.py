"""LLM synthesis arms for the continuous instrument (paper 2, step 3).

Per (arm, seed): collect N random rollouts on the truth (the sample doubles
as the gate, as in paper 1's sweep), synthesize step()/reward() from the
contract + examples, refine to gate 1.0 at eps=1e-9 (pinned integrator:
correct code matches to float precision), then classify the artifact:
  - sample_contains_wall: the identifiability event, logged per seed
    (paper 1 could not condition on it post hoc; here we can)
  - gate_passed / refine_iterations
  - wall_blindness: wall-region probe (1.0 = clamp not encoded)
  - play: J of MPC planning on the synthesized model, executed in truth,
    vs the truth-planner baseline on paired seeds -> play_cost

REQUIRES Azure OpenAI credentials in <repo-root>/.env:
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION,
  AZURE_DEPLOYMENT_MINI / AZURE_DEPLOYMENT_LARGE / AZURE_DEPLOYMENT_NANO
(same variables as the paper-1 scripts).

Run (from the repo root):
  PYTHONPATH=src python scripts/continuous_danger_synthesis.py mini 5
  PYTHONPATH=src python scripts/continuous_danger_synthesis.py large 5 --x-wall 8
Arguments: size (mini|large|nano), n_seeds; see --help for the rest.

Cross-family spot-check (HF Inference Providers router, as in paper 1's
crossfamily_probe.py; needs HF_TOKEN instead of the Azure variables):
  HF_TOKEN=... PYTHONPATH=src python scripts/continuous_danger_synthesis.py \
      mini 3 --compat-model "Qwen/Qwen3-Coder-30B-A3B-Instruct"
(the positional size is ignored when --compat-model is given; the output
filename is tagged with the model id instead).
Cost: ~2-7 LLM calls/seed (1 synthesis + refinements), prompt ~1-2k tokens —
comparable per-seed to paper 1's danger sweep cells. Runtime is dominated by
the play evaluation (~1-2 min CPU per seed at the defaults).

Predictions (design doc): full arm -> gate 1.0, wall_blindness 0.0, play at
truth parity. Incomplete arm -> when the sample misses the wall (probability
(1-r)^N; r ~ 0.013 at x_wall=8, so ~60% of seeds at N=40), gate 1.0 +
wall_blindness 1.0 + play_cost ~ 1 (pinned at the wall). When the sample DOES
contain the wall, translation-not-inference predicts the gate cannot reach
1.0 (the wall transitions are inexplicable to a wall-less program) — watch
refine behavior there; a numerically-manifested discontinuity may be easier
to induce from data than a symbolic rule (either outcome is a finding).
"""
import argparse
import json
import pathlib
import statistics
import sys
import time

from dotenv import load_dotenv

_REPO = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(_REPO / ".env", override=True)

import os  # noqa: E402

sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import CartWall, PatchField2D, PendulumStop  # noqa: E402
from cwm.continuous import harness  # noqa: E402
from cwm.continuous.contract import (  # noqa: E402
    SynthesizedModel, synthesize_and_evaluate)
from cwm.law import wilson_ci  # noqa: E402
from cwm.llm.azure_openai import AzureOpenAIProvider  # noqa: E402
from cwm.llm.openai_compat import OpenAICompatProvider  # noqa: E402


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Write JSON to `path` atomically: serialize to a temp file in the same
    directory, then os.replace() it over the destination. os.replace() is a
    single filesystem rename (POSIX guarantees it atomic), so a kill at any
    point either leaves the previous `path` untouched or the new one fully
    written -- never a truncated/corrupt file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def _seed_index(cell: dict) -> int:
    """Invert the seed-index -> rollout-seed transform used by the sweep
    loop below (rollout_seed = 10_000 * (seed_index + 1)), so a resumed run
    can tell which (arm, seed_index) pairs an existing checkpoint covers."""
    return cell["seed"] // 10_000 - 1


def run_synthesis(provider, model_name, env, arms, n_seeds, out_path, *,
                   n_rollouts, eps, max_iters, max_examples=30, guidance="",
                   max_failures=20, play_episodes=6, j_truth, j_random,
                   meta, print_fn=print) -> dict:
    """Runs the (arm, seed) synthesis grid, checkpointing atomically to
    `out_path` after EVERY cell (hard project rule: any long-running /
    money-costing run must checkpoint per unit and resume, so a killed run
    never re-spends Azure money redoing completed seeds).

    If `out_path` already exists, its cells are loaded and any (arm,
    seed_index) pair already present is SKIPPED -- no synthesize/refine
    call is made for it, only the missing pairs are computed and appended.
    A resumed run ends with the same set of cells (arm, seed_index pairs)
    as an uninterrupted run over the same (arms, n_seeds).

    `meta` supplies the fixed top-level keys (script, model, size, tag,
    params) used only when starting a fresh run (out_path does not yet
    exist); on resume the existing file's own top-level keys (including its
    j_truth/j_random baselines) are kept as-is. Returns the final results
    dict; schema is unchanged from a non-resumable run: {script, model,
    size, tag, params, j_truth, j_random, cells, elapsed_s}.

    Resume guards (2026-07-19 review): the filename does NOT encode every
    result-affecting knob (n_rollouts, eps, play_episodes, the actual
    deployment id), so a resume with different flags would silently mix
    configurations in one file. On resume we therefore (a) hard-error if any
    result-defining stored param disagrees with the current one, and (b)
    hard-error if the freshly computed baselines differ from the stored
    ones (the play environment changed between runs), else use the STORED
    baselines for the new cells so every play_cost in the file shares one
    normalization."""
    t0 = time.time()
    if out_path.exists():
        results = json.loads(out_path.read_text())
        results.setdefault("cells", [])
        stored_p = results.get("params", {}) or {}
        current_p = meta.get("params", {}) or {}
        _RESULT_KEYS = ("instrument", "x_wall", "th_stop", "k1", "k2",
                        "patch_shape", "prompt_variant", "n_rollouts", "eps",
                        "max_iters", "play_episodes", "compat_model")
        mismatch = {k: (stored_p[k], current_p[k]) for k in _RESULT_KEYS
                    if k in stored_p and k in current_p
                    and stored_p[k] != current_p[k]}
        if results.get("model") != meta.get("model"):
            mismatch["model"] = (results.get("model"), meta.get("model"))
        if mismatch:
            raise ValueError(
                f"refusing to resume {out_path}: it was produced under a "
                f"different configuration {mismatch}; rerun with matching "
                f"flags or move the file aside")
        if "j_truth" in results and (
                abs(results["j_truth"] - j_truth) > 1e-6
                or abs(results["j_random"] - j_random) > 1e-6):
            raise ValueError(
                f"refusing to resume {out_path}: recomputed baselines "
                f"(j_truth={j_truth}, j_random={j_random}) differ from the "
                f"stored ones (j_truth={results['j_truth']}, "
                f"j_random={results['j_random']}) — the play environment "
                f"changed between runs")
        j_truth = results.get("j_truth", j_truth)
        j_random = results.get("j_random", j_random)
    else:
        results = dict(meta)
        results["j_truth"] = j_truth
        results["j_random"] = j_random
        results["cells"] = []

    done = {(c["arm"], _seed_index(c)) for c in results["cells"]}

    for arm in arms:
        for seed in range(n_seeds):
            if (arm, seed) in done:
                continue
            cell = synthesize_and_evaluate(
                provider, model_name, env, include_mode=(arm == "full"),
                n_rollouts=n_rollouts, seed=10_000 * (seed + 1),
                eps=eps, max_iters=max_iters, max_examples=max_examples,
                guidance=guidance, max_failures=max_failures)
            if cell["gate_passed"]:
                model = SynthesizedModel(cell["code"], env)
                eps_play = []
                for i in range(play_episodes):
                    sd = 900_000 + 1000 * i
                    eps_play.append(harness.run_episode(env, model, "mpc", sd))
                j = statistics.mean(e.ret for e in eps_play)
                cell["j_play"] = j
                cell["play_cost"] = (j_truth - j) / (j_truth - j_random)
                cell["play_contact_rate"] = (
                    sum(e.contact for e in eps_play) / len(eps_play))
            results["cells"].append(cell)
            _atomic_write_json(out_path, results)   # per-seed checkpoint
            per_mode = ""
            if "sample_contains_mode_per" in cell:
                per_mode = (f" modes_in_sample={cell['sample_contains_mode_per']} "
                            f"mode_blind={cell['mode_blindness']}")
            print_fn(f"[{arm} seed={seed}] wall_in_sample={cell['sample_contains_wall']} "
                     f"gate={cell['gate_accuracy']:.3f} iters={cell['refine_iterations']} "
                     f"blind={cell['wall_blindness']}{per_mode} "
                     f"play_cost={cell.get('play_cost', 'n/a')}")

    results["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, results)
    return results


# Confound-closure prompt variants (paper 2 s10: "richer prompting, larger
# iteration budgets"). The guidance is methodological only — it never names
# the true region's shape; 'region' de-biases the observed failure mode
# (dimensional reduction to a 1D threshold) without revealing the answer.
_GUIDED_TEXT = (
    "Before writing code, examine the observed transitions that the base "
    "integrator alone cannot explain (transitions whose returned state is "
    "not the integrator's prediction). Characterize WHERE in state space "
    "they occur: collect the positions involved, describe the region they "
    "outline, and only then write the rule that reproduces them exactly. "
    "State your hypothesis about the region as a comment in the code.")
_REGION_TEXT = (
    "A localized rule's trigger region may have any shape in the (x, y) "
    "plane; do not assume it is a one-dimensional threshold such as "
    "x > c or an axis-aligned half-plane. Check your hypothesized region "
    "against ALL matching and non-matching transitions before settling "
    "on it.")
PROMPT_VARIANTS = {
    "default": {"max_examples": 30, "guidance": "", "max_failures": 20},
    "guided": {"max_examples": 120, "guidance": _GUIDED_TEXT,
               "max_failures": 40},
    "region": {"max_examples": 120,
               "guidance": _GUIDED_TEXT + "\n\n" + _REGION_TEXT,
               "max_failures": 40},
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("size", choices=["mini", "large", "nano"])
    ap.add_argument("n_seeds", type=int, nargs="?", default=5)
    ap.add_argument("--arm", choices=["full", "incomplete", "both"], default="both")
    ap.add_argument("--x-wall", type=float, default=8.0,
                    help="8.0: gate misses the wall ~60%% of seeds at N=40; "
                    "4.0: gate nearly always catches it")
    ap.add_argument("--instrument", choices=["cart", "pendulum", "patch2d"],
                    default="cart")
    ap.add_argument("--th-stop", type=float, default=1.4,
                    help="pendulum mode knob (1.4 headline ~balanced; 1.0 caught)")
    ap.add_argument("--k1", type=float, default=3.0,
                    help="patch2d: x of patch 1 center (nearer patch, common mode)")
    ap.add_argument("--k2", type=float, default=7.0,
                    help="patch2d: x of patch 2 center (farther patch, rare mode)")
    ap.add_argument("--patch-shape", choices=["disc", "square"], default="disc",
                    help="patch2d only. square = the fixed-topology ablation "
                    "(2026-07-19): same patches as axis-aligned squares "
                    "(max/abs membership), separating boundary curvature from "
                    "2D-ness as the cause of the 0/76 repair collapse")
    ap.add_argument("--prompt-variant", choices=["default", "guided", "region"],
                    default="default",
                    help="confound-closure arms for the 0/76 (paper 2 s10): "
                    "'guided' = 120 examples + 40 failures shown + describe-the-"
                    "region-first process guidance; 'region' = guided + an "
                    "explicit de-biasing note that a localized rule's trigger "
                    "region need not be a 1D threshold (never names the shape). "
                    "'default' is byte-identical to all committed runs")
    ap.add_argument("--n-rollouts", type=int, default=40, help="the danger-law N")
    ap.add_argument("--eps", type=float, default=1e-9,
                    help="pinned-integrator gate tolerance; loosen to 1e-6 if a "
                    "full-spec run fails only on float noise (record it if so)")
    ap.add_argument("--play-episodes", type=int, default=6)
    ap.add_argument("--max-iters", type=int, default=5)
    ap.add_argument("--compat-model", default=None,
                    help="OpenAI-compatible model id (e.g. an HF router id); "
                    "switches provider to OpenAICompatProvider with HF_TOKEN "
                    "and ignores the positional size")
    ap.add_argument("--compat-base-url", default="https://router.huggingface.co/v1")
    args = ap.parse_args()

    if args.compat_model:
        MODEL = args.compat_model
        provider = OpenAICompatProvider(base_url=args.compat_base_url,
                                        api_key=os.environ["HF_TOKEN"])
        TAG = "compat-" + MODEL.split("/")[-1].lower()
    else:
        MODEL = os.environ[{"mini": "AZURE_DEPLOYMENT_MINI",
                            "large": "AZURE_DEPLOYMENT_LARGE",
                            "nano": "AZURE_DEPLOYMENT_NANO"}[args.size]]
        provider = AzureOpenAIProvider(
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"])
        TAG = args.size

    if args.patch_shape != "disc" and args.instrument != "patch2d":
        ap.error("--patch-shape is a patch2d knob")

    if args.instrument == "pendulum":
        ENV = PendulumStop(th_stop=args.th_stop)
        KNOB = f"thstop{args.th_stop:g}"
        INSTR_TAG = "pendulum_"
    elif args.instrument == "patch2d":
        ENV = PatchField2D(p1=(args.k1, 0.0), p2=(args.k2, 0.0),
                           patch_shape=args.patch_shape)
        KNOB = f"k{args.k1:g}_{args.k2:g}"
        INSTR_TAG = "patch2d_" if args.patch_shape == "disc" else "patch2dsq_"
    else:
        ENV = CartWall(x_wall=args.x_wall)
        KNOB = f"xwall{args.x_wall:g}"
        INSTR_TAG = ""
    ARMS = ["full", "incomplete"] if args.arm == "both" else [args.arm]

    VARIANT = PROMPT_VARIANTS[args.prompt_variant]

    SUFFIX = ""
    if args.prompt_variant != "default":
        SUFFIX += f"_pv-{args.prompt_variant}"
    if args.max_iters != 5:
        SUFFIX += f"_it{args.max_iters}"

    # Truth-planner + random baselines, shared across all seeds/arms (paired).
    print(f"baselines: {args.play_episodes} truth-MPC + random episodes...", flush=True)
    _base_t, _base_r = [], []
    for i in range(args.play_episodes):
        sd = 900_000 + 1000 * i
        _base_t.append(harness.run_episode(ENV, ENV, "mpc", sd).ret)
        _base_r.append(harness.run_episode(ENV, policy="random", seed=sd).ret)
    J_TRUTH, J_RANDOM = statistics.mean(_base_t), statistics.mean(_base_r)
    print(f"J_truth={J_TRUTH:.2f}  J_random={J_RANDOM:.2f}", flush=True)

    out = pathlib.Path(
        f"results/continuous_synthesis_{INSTR_TAG}{TAG}_{KNOB}{SUFFIX}.json")
    meta = {"script": "continuous_danger_synthesis.py", "model": MODEL,
            "size": args.size, "tag": TAG, "params": vars(args)}
    results = run_synthesis(
        provider, MODEL, ENV, ARMS, args.n_seeds, out,
        n_rollouts=args.n_rollouts, eps=args.eps, max_iters=args.max_iters,
        max_examples=VARIANT["max_examples"], guidance=VARIANT["guidance"],
        max_failures=VARIANT["max_failures"], play_episodes=args.play_episodes,
        j_truth=J_TRUTH, j_random=J_RANDOM, meta=meta,
        print_fn=lambda s: print(s, flush=True))

    # Cell summary: the danger-law conditionals.
    inc = [c for c in results["cells"] if c["arm"] == "incomplete"]
    if inc and args.instrument == "patch2d":
        # Per-mode partition: the identifiability event is now per patch, so the
        # incomplete arm splits into four branches by which modes the gate sample
        # contained. Partial repair = the seen patch's blindness drops to 0 while
        # the unseen patch stays blind at 1.0 behind the same passed gate.
        def _branch(c):
            per = c["sample_contains_mode_per"]
            return (bool(per.get("patch1")), bool(per.get("patch2")))
        LABELS = {(False, False): "miss-both", (True, False): "see1-miss2",
                  (False, True): "miss1-see2", (True, True): "see-both"}
        print(f"\nincomplete arm ({len(inc)} seeds), partitioned by "
              f"sample_contains_mode_per:", flush=True)
        for key in [(False, False), (True, False), (False, True), (True, True)]:
            cells = [c for c in inc if _branch(c) == key]
            print(f"  {LABELS[key]}: {len(cells)}/{len(inc)}", flush=True)
            for c in cells:
                mb = c["mode_blindness"] or {}
                print(f"    seed={c['seed']} gate={c['gate_accuracy']:.3f} "
                      f"blind_p1={mb.get('patch1', 'n/a')} "
                      f"blind_p2={mb.get('patch2', 'n/a')} "
                      f"play_cost={c.get('play_cost', 'n/a')} "
                      f"contact={c.get('play_contact_rate', 'n/a')}", flush=True)
    elif inc:
        missed = [c for c in inc if not c["sample_contains_wall"]]
        blind_when_missed = [c for c in missed
                             if c["gate_passed"] and c["wall_blindness"] == 1.0]
        print(f"\nincomplete arm: {len(missed)}/{len(inc)} seeds had the mode "
              f"ABSENT from the sample (identifiability event); of those, "
              f"{len(blind_when_missed)} passed the gate fully wall-blind "
              f"(Wilson 95% {wilson_ci(len(blind_when_missed), len(missed))})"
              if missed else "\nincomplete arm: mode present in every sample",
              flush=True)

    print(f"wrote {out}  [{results['elapsed_s']}s]", flush=True)
