"""Derive the LLM-protocol numbers of paper 2's appendix from results/.

Review point #17: the paper has no compact, complete specification of the LLM
protocol. The prose part of that specification is extracted by hand from the
code into docs/paper2/PROTOCOL-FACTS.md (with file:line citations); the
NUMBERS have to be re-derivable, so they are computed here and written to
results/llm_protocol_facts.json — never hand-counted for prose.

What is counted. One synthesis campaign cell (one (arm, seed) pair) costs

    llm_calls = 1 (synthesis) + refine_iterations

because contract.synthesize_and_evaluate issues exactly one provider.complete
for the synthesis message and refine_continuous issues exactly one per
iteration of its while-loop, incrementing `iterations` once per call
(src/cwm/continuous/contract.py). Every campaign JSON records
`refine_iterations` per cell, so the whole call distribution is recoverable
after the fact. The agent-relayed Claude arms are counted separately (they are
not API calls through a provider wrapper) and cross-checked against the number
of versioned prompt transcripts on disk.

Pure CPU, no network, deterministic, safe to re-run:
    PYTHONPATH=src .venv/bin/python scripts/llm_protocol_facts.py
"""
import glob
import json
import os
import re
import statistics

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RESULTS = os.path.join(_REPO, "results")


def _median(xs):
    m = statistics.median(xs)
    return int(m) if float(m).is_integer() else m


def _rel(path):
    return os.path.relpath(path, _REPO).replace(os.sep, "/")


def api_campaigns():
    """Every committed provider-API synthesis campaign: the JSONs written by
    scripts/continuous_danger_synthesis.py that carry per-cell
    refine_iterations."""
    out = []
    for path in sorted(glob.glob(os.path.join(_RESULTS,
                                              "continuous_synthesis_*.json"))):
        try:
            d = json.load(open(path))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict):
            continue
        cells = d.get("cells")
        if not cells or "refine_iterations" not in cells[0]:
            continue
        p = d.get("params") or {}
        calls = [1 + c["refine_iterations"] for c in cells]
        iters = [c["refine_iterations"] for c in cells]
        max_iters = p.get("max_iters", 5)
        instrument = p.get("instrument") or "cart"
        shape = p.get("patch_shape")
        if shape is None and instrument == "patch2d":
            shape = "disc"      # the knob postdates these runs; disc was all
        out.append({
            "tag": os.path.basename(path)[len("continuous_synthesis_"):-len(".json")],
            "path": _rel(path),
            "model": d.get("model"),
            "instrument": instrument,
            "patch_shape": shape,
            # a run predating the --prompt-variant knob had empty guidance, so
            # its prompt IS the 'default' variant's prompt.
            "prompt_variant": p.get("prompt_variant") or "default",
            "max_iters": max_iters,
            "n_rollouts": p.get("n_rollouts"),
            "eps": p.get("eps"),
            "arms": sorted({c["arm"] for c in cells}),
            "n_cells": len(cells),
            "llm_calls_total": sum(calls),
            "llm_calls_min": min(calls),
            "llm_calls_median": _median(calls),
            "llm_calls_max": max(calls),
            "refine_iterations_hist": {str(k): iters.count(k)
                                       for k in sorted(set(iters))},
            "n_cells_at_iteration_cap": sum(1 for i in iters if i == max_iters),
        })
    return out


def _transcript_call_count(pattern):
    """Number of relayed prompts on disk (one msg*.txt = one LLM call).
    Files marked DISCARDED are duplicate relays of a message that was sent
    twice by accident and whose second reply was thrown away, so they are not
    protocol iterations and are excluded."""
    return len([p for p in glob.glob(os.path.join(_REPO, pattern))
                if "DISCARDED" not in os.path.basename(p)])


def _discarded_transcripts(pattern):
    return sorted(os.path.basename(p)
                  for p in glob.glob(os.path.join(_REPO, pattern))
                  if "DISCARDED" in os.path.basename(p))


def relay_campaigns():
    """The agent-relayed Claude arms. Not provider-API calls: each iteration's
    message was relayed by hand/agent and the prompt+reply versioned under
    results/claude_relay_transcripts/, so the call count is the number of
    prompt files, cross-checked against the ledger."""
    out = []
    p1 = os.path.join(_RESULTS, "continuous_claude_relay.json")
    if os.path.exists(p1):
        rows = json.load(open(p1))
        calls = [1 + r["refine_iterations"] for r in rows]
        on_disk = sum(_transcript_call_count(r["transcript_prefix"] + "_msg*.txt")
                      for r in rows)
        out.append({
            "tag": "claude_relay_1d",
            "path": _rel(p1),
            "model": sorted({r["model"] for r in rows})[0],
            "n_cells": len(rows),
            "llm_calls_total": sum(calls),
            "llm_calls_min": min(calls),
            "llm_calls_median": _median(calls),
            "llm_calls_max": max(calls),
            "llm_calls_from_transcripts_on_disk": on_disk,
            "transcripts_agree": on_disk == sum(calls),
        })
    p2 = os.path.join(_RESULTS, "continuous_claude_relay_patch2d_k3_7.json")
    if os.path.exists(p2):
        d = json.load(open(p2))
        rows = d["rows"]
        # one row = one relayed reply = one LLM call (iteration 0 = synthesis).
        per_seed = {}
        for r in rows:
            per_seed.setdefault((r["arm"], r["seed"]), 0)
            per_seed[(r["arm"], r["seed"])] += 1
        calls = sorted(per_seed.values())
        _pat = "results/claude_relay_transcripts/patch2d_k3_7_*_msg*.txt"
        on_disk = _transcript_call_count(_pat)
        out.append({
            "discarded_duplicate_relays": _discarded_transcripts(_pat),
            "tag": "claude_relay_patch2d_k3_7",
            "path": _rel(p2),
            "model": "claude-sonnet (agent-relayed)",
            "n_cells": len(per_seed),
            "llm_calls_total": sum(calls),
            "llm_calls_min": min(calls),
            "llm_calls_median": _median(calls),
            "llm_calls_max": max(calls),
            "llm_calls_from_transcripts_on_disk": on_disk,
            "transcripts_agree": on_disk == sum(calls),
        })
    return out


def provider_defaults():
    """The sampling parameters ACTUALLY sent on the wire, read off the provider
    wrappers. Anything not listed in a wrapper's create() call is not sent at
    all, i.e. it falls back to the provider-side default."""
    az = os.path.join(_REPO, "src", "cwm", "llm", "azure_openai.py")
    oc = os.path.join(_REPO, "src", "cwm", "llm", "openai_compat.py")
    az_src, oc_src = open(az).read(), open(oc).read()
    sent = {}
    for name, src in (("azure_openai", az_src), ("openai_compat", oc_src)):
        call = re.search(r"chat\.completions\.create\((.*?)\)\n", src,
                         re.DOTALL).group(1)
        sent[name] = {
            "kwargs_sent": sorted(
                re.findall(r"(\w+)\s*=", call.replace("\n", " "))),
            "temperature_sent": "temperature" in call,
            "top_p_sent": "top_p" in call,
            "seed_sent": "seed" in call,
        }
    return sent


def example_budget():
    """How much of the sample the prompt actually shows, per instrument, at
    N = 40 rollouts. Uses the REAL selection function (contract._example_lines,
    a strided pick, not a prefix) so the count includes any index collisions."""
    import sys
    sys.path.insert(0, os.path.join(_REPO, "src"))
    from cwm.continuous.contract import _example_lines, collect_transitions
    from cwm.continuous.envs import CartWall, PatchField2D, PendulumStop
    out = {}
    for name, env in (("cart", CartWall(x_wall=8.0)),
                      ("pendulum", PendulumStop(th_stop=1.4)),
                      ("patch2d", PatchField2D())):
        tr = collect_transitions(env, 40, seed=10_000)
        row = {"h_episode": env.h_episode, "n_transitions_at_N40": len(tr)}
        for me in (30, 120):
            k = len(_example_lines(tr, me).splitlines())
            row[f"n_example_lines_at_max_examples_{me}"] = k
            row[f"frac_of_sample_shown_at_{me}"] = round(k / len(tr), 5)
        out[name] = row
    return out


def main():
    api = api_campaigns()
    relay = relay_campaigns()
    facts = {
        "script": "scripts/llm_protocol_facts.py",
        "purpose": "numbers behind docs/paper2/PROTOCOL-FACTS.md (review #17)",
        "calls_per_seed_formula": "1 synthesis call + refine_iterations refine calls",
        "provider_sampling_params": provider_defaults(),
        "example_budget": example_budget(),
        "campaigns": api,
        "relay_campaigns": relay,
        "totals": {
            "n_campaigns": len(api),
            "n_cells_all_campaigns": sum(c["n_cells"] for c in api),
            "llm_calls_all_campaigns": sum(c["llm_calls_total"] for c in api),
            "n_relay_campaigns": len(relay),
            "n_relay_cells": sum(c["n_cells"] for c in relay),
            "relay_calls": sum(c["llm_calls_total"] for c in relay),
            "llm_calls_including_relay": (sum(c["llm_calls_total"] for c in api)
                                          + sum(c["llm_calls_total"] for c in relay)),
            "calls_per_cell_min": min(c["llm_calls_min"] for c in api),
            "calls_per_cell_max": max(c["llm_calls_max"] for c in api),
            "mean_calls_per_cell": round(
                sum(c["llm_calls_total"] for c in api)
                / sum(c["n_cells"] for c in api), 4),
        },
    }
    dst = os.path.join(_RESULTS, "llm_protocol_facts.json")
    tmp = dst + ".tmp"
    with open(tmp, "w") as f:
        json.dump(facts, f, indent=1)
    os.replace(tmp, dst)
    t = facts["totals"]
    for c in api:
        print(f"{c['tag']:<62} n={c['n_cells']:>3} calls={c['llm_calls_total']:>4} "
              f"min/med/max={c['llm_calls_min']}/{c['llm_calls_median']}/"
              f"{c['llm_calls_max']} cap_hits={c['n_cells_at_iteration_cap']}")
    for c in relay:
        print(f"{c['tag']:<62} n={c['n_cells']:>3} calls={c['llm_calls_total']:>4} "
              f"transcripts_agree={c['transcripts_agree']}")
    print(f"\nAPI: {t['n_campaigns']} campaigns, {t['n_cells_all_campaigns']} cells, "
          f"{t['llm_calls_all_campaigns']} LLM calls "
          f"(mean {t['mean_calls_per_cell']}/cell, range "
          f"{t['calls_per_cell_min']}-{t['calls_per_cell_max']})")
    print(f"including relay: {t['llm_calls_including_relay']} calls")
    print(f"wrote {_rel(dst)}")


if __name__ == "__main__":
    main()
