"""Statistics by experimental unit for paper 2's synthesis campaigns.

Peer review point #5: the paper pools counts whose experimental unit is unclear
("0/156 mode-containing seeds", "109/111 repairs") and puts Wilson intervals on
them as if each were one homogeneous binomial rate.  They are not.  This script
declares the unit hierarchy, re-derives every headline count at the right unit,
and writes both the honest bound and the naive one (explicitly labelled invalid)
to results/paper2_statistics.json so the paper can cite the first and display the
second as a contrast.  It reads versioned results only -- no LLM calls, no new
compute -- so it runs in CI beside scripts/audit_paper2_numbers.py.

    Run: PYTHONPATH=src .venv/bin/python scripts/paper2_statistics.py

THE UNIT HIERARCHY
------------------
  PRIMARY UNIT -- the gate-sample BLOCK, identified by (seed_index, seed_offset).
      `cwm.continuous.contract.collect_transitions` draws its rollouts from
      `random.Random(rollout_seed + i)`, and continuous_danger_synthesis.py sets
      `rollout_seed = 10_000 * (seed_index + 1 + seed_offset)`.  Neither depends
      on the instrument, the knob, the patch shape, the prompt variant or the
      iteration budget.  So the random stream -- the initial states and the whole
      action sequence -- is shared byte for byte across every campaign that
      reuses a seed index.  Two campaigns at different knobs are therefore two
      *treatments applied to one common random draw*, not two samples.  Block id
      here is `seed // 10_000` (= seed_index + 1 + seed_offset), so blocks 1..20
      are the base runs and 21..40 the `--seed-offset 20` re-runs.

  SECONDARY UNIT -- the synthesis DRAW, (block x treatment x model).  A draw is
      one LLM synthesis+refine attempt.  Draws sharing a block are correlated by
      construction: identical evidence, identical mode-contact pattern (given the
      knob), often identical prompt.

  TREATMENT -- (instrument, knob, patch shape, prompt variant, iteration budget,
      arm).  Varying any of these adds a treatment, not a sample.  `model` is
      deliberately NOT part of the treatment key: it indexes draws within a
      treatment, which is why "both sizes" counts double the draws without
      adding a single sample.

WHAT FOLLOWS FROM IT
--------------------
* Any interval whose n counts draws while blocks are shared is anticonservative.
  `pooled_bound(..., unit="draw")` therefore RAISES `SharedBlockPoolingError`
  when the draw set contains a repeated block, unless the caller explicitly asks
  for the labelled comparator (`comparator=True`), whose output carries
  `valid_for_paper: false`.
* A per-block claim needs a scoring rule for blocks with several draws.  Two are
  reported, and they bound different estimands:
      "all"  -- the block counts as a success only if EVERY draw on it succeeded.
                Estimand: P(every treatment/model attempt on a fresh sample
                succeeds).  Conservative; this is the one to quote.
      "any"  -- the block counts as a success if ANY draw on it succeeded.
                Estimand: P(at least one attempt on a fresh sample succeeds).
                Optimistic.  The paper's current 0.851 cart figure is this one.
* Bounds are exact Clopper-Pearson (binomial inversion, implemented here from
  math.comb -- no SciPy in this environment), with the Wilson score interval
  reported alongside because the existing prose quotes Wilson.  At n = 20..40 and
  proportions at the 0/1 boundary the two differ enough to matter, and CP is the
  one that cannot undercover.
"""
import json
import math
import pathlib
import random
import sys
from collections import defaultdict

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.law import wilson_ci  # noqa: E402

R = _REPO / "results"
ALPHA = 0.05
EXPLOITED_PLAY_COST = 0.9   # "below random"; the observed values are >= 0.994


# --------------------------------------------------------------------------- #
# exact binomial intervals                                                    #
# --------------------------------------------------------------------------- #
def binom_tail_le(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Bin(n, p), summed exactly from math.comb."""
    if k >= n:
        return 1.0
    if k < 0:
        return 0.0
    return math.fsum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                     for i in range(0, k + 1))


def binom_tail_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Bin(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return math.fsum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                     for i in range(k, n + 1))


def _bisect(f, target, lo=0.0, hi=1.0, iters=200):
    """Solve f(p) = target for monotone f on [lo, hi] by bisection."""
    f_lo = f(lo)
    increasing = f(hi) > f_lo
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        v = f(mid)
        if (v < target) == increasing:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for [[a, b], [c, d]] by summing the
    hypergeometric probability of every table with the same margins whose
    probability is <= the observed one. Exact; no approximation, no SciPy."""
    n = a + b + c + d
    row1, col1 = a + b, a + c

    def prob(x):
        return (math.comb(row1, x) * math.comb(n - row1, col1 - x)
                / math.comb(n, col1))

    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    p_obs = prob(a)
    return min(1.0, math.fsum(prob(x) for x in range(lo, hi + 1)
                              if prob(x) <= p_obs * (1 + 1e-12)))


def clopper_pearson(k: int, n: int, alpha: float = ALPHA) -> tuple:
    """Exact (Clopper-Pearson) two-sided 1-alpha interval, (point, lo, hi).

    lo solves P(X >= k | p) = alpha/2 (0 when k == 0);
    hi solves P(X <= k | p) = alpha/2 (1 when k == n).
    Closed forms hold at the boundaries -- lo = (alpha/2)^(1/n) for k = n and
    hi = 1 - (alpha/2)^(1/n) for k = 0 -- and are used directly there both
    because they are exact and because they give the tests an oracle.
    """
    if n == 0:
        return (0.0, 0.0, 1.0)
    if not 0 <= k <= n:
        raise ValueError(f"k={k} out of range for n={n}")
    half = alpha / 2.0
    if k == 0:
        lo = 0.0
    elif k == n:
        lo = half ** (1.0 / n)
    else:
        lo = _bisect(lambda p: binom_tail_ge(k, n, p), half)
    if k == n:
        hi = 1.0
    elif k == 0:
        hi = 1.0 - half ** (1.0 / n)
    else:
        hi = _bisect(lambda p: binom_tail_le(k, n, p), half)
    return (k / n, lo, hi)


# --------------------------------------------------------------------------- #
# the draw table                                                              #
# --------------------------------------------------------------------------- #
class SharedBlockPoolingError(RuntimeError):
    """Raised when a draw-level interval is requested over a draw set in which
    some gate-sample block appears more than once.  Such an interval treats
    repeated attempts on one sample as independent trials and is therefore
    anticonservative; pass comparator=True to obtain it explicitly labelled as
    the invalid-if-pooled comparator."""


def block_of(seed: int) -> int:
    """(seed_index + 1 + seed_offset): the rollout-seed block id."""
    return seed // 10_000


def _size_of(model: str, declared) -> str:
    if declared:
        return declared
    return model


def _family(model: str) -> str:
    m = model.lower()
    if m.startswith("gpt"):
        return "gpt-5.x"
    if "qwen" in m:
        return "qwen"
    if "claude" in m:
        return "claude"
    return m


def _knob(instrument: str, params: dict):
    """The knob that is actually a knob FOR THIS INSTRUMENT.  The synthesis
    script serialises its whole argparse namespace, so a cart run also carries a
    th_stop and k1/k2 it never used; keying the treatment on those would invent
    treatment distinctions that do not exist."""
    if instrument == "cart":
        return {"x_wall": params["x_wall"]}
    if instrument == "pendulum":
        return {"th_stop": params["th_stop"]}
    return {"k1": params["k1"], "k2": params["k2"]}


def _blindness(cell: dict):
    """Scalar mode-blindness in [0, 1] (mean over modes for patch2d), or None
    when the gate refused the artifact and blindness was never measured."""
    mb = cell.get("mode_blindness", cell.get("wall_blindness"))
    if isinstance(mb, dict):
        return sum(mb.values()) / len(mb) if mb else None
    return mb


def classify(cell: dict, mode_present: bool, max_iters: int) -> str:
    """Outcome taxonomy.  `rejected_stalled` is the all-or-nothing gate refusing
    an artifact after the refine loop exhausted its budget -- the Qwen/patch2d
    "superstitious patch the gate refuses" case."""
    if not cell["gate_passed"]:
        if cell["refine_iterations"] >= max_iters:
            return "rejected_stalled"
        return "rejected"
    b = _blindness(cell)
    pc = cell.get("play_cost")
    if cell["arm"] == "full":
        return "control_translated" if b == 0.0 else "control_mode_wrong"
    if b == 0.0:
        return "repaired" if mode_present else "certified_mode_correct"
    if b == 1.0:
        if pc is not None and pc >= EXPLOITED_PLAY_COST:
            return "blind_and_exploited"
        return "blind_not_exploited"
    return "partial_repair"


SYNTHESIS_GLOB = "continuous_synthesis_*.json"


def load_draws(results_dir: pathlib.Path = R) -> list:
    """Flatten every synthesis campaign (plus the two agent-relayed Claude
    campaigns) into one draw table."""
    draws = []
    for path in sorted(results_dir.glob(SYNTHESIS_GLOB)):
        d = json.loads(path.read_text())
        params = d["params"]
        instrument = params.get("instrument", "cart")
        shape = (params.get("patch_shape") or "disc") if instrument == "patch2d" else None
        prompt = params.get("prompt_variant") or "default"
        max_iters = params["max_iters"]
        for cell in d["cells"]:
            per = cell.get("sample_contains_mode_per")
            present = (any(per.values()) if per is not None
                       else bool(cell["sample_contains_wall"]))
            draws.append({
                "file": path.name,
                "instrument": instrument,
                "knob": _knob(instrument, params),
                "patch_shape": shape,
                "prompt_variant": prompt,
                "max_iters": max_iters,
                "arm": cell["arm"],
                "model": d["model"],
                "size": _size_of(d["model"], d.get("size")),
                "family": _family(d["model"]),
                "seed": cell["seed"],
                "block": block_of(cell["seed"]),
                "mode_present": present,
                "mode_present_per": per,
                "n_modes_seen": sum(per.values()) if per else int(present),
                "gate_passed": bool(cell["gate_passed"]),
                "gate_accuracy": cell["gate_accuracy"],
                "blindness": _blindness(cell),
                "per_mode_blindness": (cell.get("mode_blindness")
                                       if isinstance(cell.get("mode_blindness"), dict)
                                       else None),
                "play_cost": cell.get("play_cost"),
                "refine_iterations": cell["refine_iterations"],
                "outcome": classify(cell, present, max_iters),
            })
    draws.extend(_load_claude_relay(results_dir))
    return draws


def _load_claude_relay(results_dir: pathlib.Path) -> list:
    """The agent-relayed Claude arms.  1D lives in a flat list of final cells;
    the patch2d arm is a per-iteration ledger, whose LAST iteration per (arm,
    seed) is the draw's outcome."""
    out = []
    p1 = results_dir / "continuous_claude_relay.json"
    if p1.exists():
        for cell in json.loads(p1.read_text()):
            instrument = cell["instrument"]
            present = bool(cell["sample_contains_wall"])
            knob = ({"x_wall": 8.0} if instrument == "cart"
                    else {"th_stop": 1.4})
            out.append({
                "file": p1.name, "instrument": instrument, "knob": knob,
                "patch_shape": None, "prompt_variant": "relay", "max_iters": 5,
                "arm": cell["arm"], "model": cell["model"], "size": "sonnet",
                "family": "claude", "seed": cell["seed"],
                "block": block_of(cell["seed"]), "mode_present": present,
                "mode_present_per": None, "n_modes_seen": int(present),
                "gate_passed": bool(cell["gate_passed"]),
                "gate_accuracy": cell["gate_accuracy"],
                "blindness": cell.get("wall_blindness"),
                "per_mode_blindness": None,
                "play_cost": cell.get("play_cost"),
                "refine_iterations": cell["refine_iterations"],
                "outcome": classify(cell, present, 5),
            })
    p2 = results_dir / "continuous_claude_relay_patch2d_k3_7.json"
    if p2.exists():
        d = json.loads(p2.read_text())
        by_seed = defaultdict(list)
        for row in d["rows"]:
            by_seed[(row["arm"], row["seed"])].append(row)
        for (arm, seed), rows in sorted(by_seed.items()):
            last = max(rows, key=lambda r: r["iteration"])
            per = last["sample_contains_mode_per"]
            present = any(per.values())
            gate = bool(last["gate_passed"])
            out.append({
                "file": p2.name, "instrument": "patch2d",
                "knob": {"k1": d["k1"], "k2": d["k2"]},
                "patch_shape": "disc", "prompt_variant": "relay",
                "max_iters": 5, "arm": arm,
                "model": "claude-sonnet (agent-relayed)", "size": "sonnet",
                "family": "claude", "seed": seed, "block": block_of(seed),
                "mode_present": present, "mode_present_per": per,
                "n_modes_seen": sum(per.values()),
                "gate_passed": gate, "gate_accuracy": last["gate_accuracy"],
                "blindness": (0.0 if gate and last["rule_class"] == "disc-landing"
                              else None),
                "per_mode_blindness": None, "play_cost": None,
                "refine_iterations": last["iteration"],
                "outcome": ("control_translated" if gate and arm == "full"
                            else "rejected_stalled" if not gate
                            else "repaired"),
                "rule_class": last["rule_class"],
            })
    return out


def treatment_key(d: dict) -> str:
    knob = ",".join(f"{k}={v:g}" for k, v in d["knob"].items())
    parts = [d["instrument"], knob]
    if d["patch_shape"]:
        parts.append(f"shape={d['patch_shape']}")
    parts.append(f"prompt={d['prompt_variant']}")
    parts.append(f"it={d['max_iters']}")
    parts.append(f"arm={d['arm']}")
    return " | ".join(parts)


# --------------------------------------------------------------------------- #
# bounds at the right unit                                                    #
# --------------------------------------------------------------------------- #
def by_block(d):
    """The primary cluster key: the rollout-seed block, which is shared across
    instruments too (the stream depends on the seed alone), so cart block 7 and
    pendulum block 7 are ONE cluster under this key. Conservative."""
    return d["block"]


def by_instrument_block(d):
    """The looser comparator key: a fresh instrument re-uses the block's random
    numbers but pushes them through different dynamics, so the two samples are
    dependent (common random numbers) without being identical. Treating them as
    separate clusters is the optimistic reading; it is reported beside the
    conservative one, never instead of it."""
    return (d["instrument"], d["block"])


def score_blocks(draws, predicate, scoring="all", cluster_key=by_block) -> dict:
    """{cluster_id: bool} after collapsing each cluster's draws with `scoring`."""
    if scoring not in ("all", "any"):
        raise ValueError(f"scoring must be 'all' or 'any', got {scoring!r}")
    per = defaultdict(list)
    for d in draws:
        per[cluster_key(d)].append(bool(predicate(d)))
    agg = all if scoring == "all" else any
    return {b: agg(v) for b, v in sorted(per.items(), key=lambda kv: str(kv[0]))}


def pooled_bound(draws, predicate, unit="block", scoring="all",
                 comparator=False, alpha=ALPHA, label=None,
                 cluster_key=by_block) -> dict:
    """A 1-alpha interval on the success probability of `predicate`.

    unit="block": collapse each block with `scoring`, then invert the binomial
        at n = number of DISTINCT blocks.  Always permitted.
    unit="draw":  n = number of draws.  Permitted only when no block is repeated
        in `draws` (then it coincides with the block-level count).  If some block
        IS repeated, this is the anticonservative pooling review point #5 is
        about, so it raises SharedBlockPoolingError unless comparator=True, in
        which case the result is returned with valid_for_paper=False and a
        label saying so.
    """
    if unit not in ("block", "draw"):
        raise ValueError(f"unit must be 'block' or 'draw', got {unit!r}")
    blocks_seen = defaultdict(int)
    for d in draws:
        blocks_seen[cluster_key(d)] += 1
    shared = {b: c for b, c in blocks_seen.items() if c > 1}
    treatments = sorted({treatment_key(d) for d in draws})

    if unit == "draw" and shared and not comparator:
        raise SharedBlockPoolingError(
            f"draw-level pooling over {len(draws)} draws spanning "
            f"{len(treatments)} treatment(s) but only {len(blocks_seen)} "
            f"distinct gate-sample blocks ({len(shared)} block(s) contribute "
            f"more than one draw). Trials within a block are not independent: "
            f"the rollout stream depends on (seed_index, seed_offset) alone. "
            f"Use unit='block', or pass comparator=True to get this interval "
            f"explicitly labelled as the invalid-if-pooled comparator.")

    if unit == "block":
        scored = score_blocks(draws, predicate, scoring=scoring,
                              cluster_key=cluster_key)
        k, n = sum(scored.values()), len(scored)
    else:
        k = sum(1 for d in draws if predicate(d))
        n = len(draws)
        scoring = None

    point, cp_lo, cp_hi = clopper_pearson(k, n, alpha=alpha)
    _, w_lo, w_hi = wilson_ci(k, n)
    valid = unit == "block" or not shared
    out = {
        "unit": unit,
        "cluster_key": cluster_key.__name__,
        "block_scoring": scoring,
        "k": k,
        "n": n,
        "n_draws": len(draws),
        "n_distinct_blocks": len(blocks_seen),
        "n_shared_blocks": len(shared),
        "max_draws_per_block": max(blocks_seen.values()) if blocks_seen else 0,
        "n_treatments_pooled": len(treatments),
        "treatments_pooled": treatments,
        "point": point,
        "clopper_pearson_95": [cp_lo, cp_hi],
        "wilson_95": [w_lo, w_hi],
        "valid_for_paper": valid,
        "homogeneity_assumed_across_treatments": len(treatments) > 1,
    }
    if not valid:
        out["label"] = ("INVALID-IF-POOLED COMPARATOR: n counts draws that share "
                        "gate-sample blocks; shown only to display what the naive "
                        "pooling would have said.")
    if label:
        out["claim"] = label
    return out


# --------------------------------------------------------------------------- #
# cluster-robust comparators for the 1D repair claim                          #
# --------------------------------------------------------------------------- #
def anova_icc(draws, predicate) -> dict:
    """ANOVA (Fleiss-Cuzick) intracluster correlation for a binary outcome with
    unequal cluster sizes, plus the design effect and Rao-Scott effective n.
    Returns reason=... and icc=None when the estimator is undefined, which it is
    whenever the outcome has zero total variance (every draw a success) -- the
    concrete sense in which a hierarchical model is unidentifiable here."""
    per = defaultdict(list)
    for d in draws:
        per[d["block"]].append(1.0 if predicate(d) else 0.0)
    sizes = [len(v) for v in per.values()]
    k, N = len(per), sum(sizes)
    if k < 2 or N == k:
        return {"icc": None, "reason": "fewer than 2 clusters, or no clustering",
                "n_clusters": k, "n_draws": N}
    grand = math.fsum(math.fsum(v) for v in per.values()) / N
    if grand in (0.0, 1.0):
        return {"icc": None,
                "reason": ("outcome has zero variance (every draw identical), so "
                           "MSB = MSW = 0 and the ICC is 0/0 -- undefined; a "
                           "hierarchical/GLMM fit is unidentifiable on this data"),
                "n_clusters": k, "n_draws": N, "point_estimate": grand}
    ssb = math.fsum(len(v) * (math.fsum(v) / len(v) - grand) ** 2
                    for v in per.values())
    ssw = math.fsum(math.fsum((x - math.fsum(v) / len(v)) ** 2 for x in v)
                    for v in per.values())
    msb = ssb / (k - 1)
    msw = ssw / (N - k) if N > k else 0.0
    m0 = (N - math.fsum(s * s for s in sizes) / N) / (k - 1)
    denom = msb + (m0 - 1) * msw
    icc = (msb - msw) / denom if denom > 0 else None
    if icc is None:
        return {"icc": None, "reason": "MSB + (m0-1)*MSW == 0", "n_clusters": k,
                "n_draws": N}
    icc = max(0.0, min(1.0, icc))
    m_bar = N / k
    deff = 1.0 + (m_bar - 1.0) * icc
    n_eff = N / deff
    _, lo, hi = wilson_ci(grand * n_eff, n_eff)
    out = {"icc": icc, "m_bar": m_bar, "m0": m0, "design_effect": deff,
           "n_effective": n_eff, "n_clusters": k, "n_draws": N,
           "point_estimate": grand, "rao_scott_wilson_95": [lo, hi],
           "valid_for_paper": False,
           "assumptions": ("exchangeable within-block correlation, one common "
                           "ICC across all blocks and treatments, and a normal "
                           "approximation on the effective sample size -- the "
                           "last of which is poor at a proportion this close to "
                           "1 with n_eff of this size")}
    if icc <= 0.0:
        out["warning"] = (
            "the ANOVA ICC estimate is <= 0 and was truncated to 0, so the "
            "design effect collapses to 1 and this interval is IDENTICAL to the "
            "draw-level pooled one that review point #5 rejects. That is not "
            "evidence of no clustering: with clusters of size 1-4 and an "
            "outcome pinned near the 0/1 boundary, MSW can exceed MSB by chance "
            "and the moment estimator has no power. It is recorded to show that "
            "the design-effect route silently reproduces the anticonservative "
            "answer here, which is the reason the quoted bound is the "
            "block-level exact one instead.")
    return out


def cluster_bootstrap(draws, predicate, n_boot=10000, seed=0,
                      alpha=ALPHA) -> dict:
    """Nonparametric cluster bootstrap: resample BLOCKS with replacement, take
    the pooled draw-level proportion of each resample, report percentiles.
    Deterministic given `seed`."""
    per = defaultdict(list)
    for d in draws:
        per[d["block"]].append(1.0 if predicate(d) else 0.0)
    blocks = sorted(per)
    if len(blocks) < 2:
        return {"reason": "fewer than 2 clusters", "n_clusters": len(blocks)}
    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        num = den = 0.0
        for _ in blocks:
            v = per[blocks[rng.randrange(len(blocks))]]
            num += math.fsum(v)
            den += len(v)
        stats.append(num / den)
    stats.sort()
    def q(p):
        return stats[min(len(stats) - 1, max(0, int(round(p * (len(stats) - 1)))))]
    return {"n_boot": n_boot, "seed": seed, "n_clusters": len(blocks),
            "percentile_95": [q(alpha / 2), q(1 - alpha / 2)],
            "valid_for_paper": False,
            "point_estimate": math.fsum(math.fsum(v) for v in per.values())
                              / sum(len(v) for v in per.values()),
            "assumptions": ("blocks i.i.d. from the sample-generating "
                            "distribution; no assumption on within-block "
                            "dependence. Undercovers at a boundary proportion "
                            "(a resample of all-success blocks returns exactly "
                            "1.0), so it is a comparator, not the quoted bound")}


# --------------------------------------------------------------------------- #
# predicates                                                                  #
# --------------------------------------------------------------------------- #
# Artifacts whose mode-probe score says "repaired" but whose behaviour says otherwise,
# keyed by (file, seed) and read from the two exactness audits rather than restated here.
# The probe fires only where the TRUTH's mode is active, so it cannot see an artifact that
# INVENTS a mode elsewhere (measured: 4 pendulum artifacts, results/repair_exactness_1d.json)
# or that OVER-COVERS the true one (measured: 19 of the slab campaign's 20 large-model
# artifacts are the half-plane at the near face, which scores blindness 0 while freezing
# 4.6x the true region -- results/arity_evidence_ablations.json).
# Counting either as a repair would let the paper claim a recovery that did not happen.
def _probe_false_positives() -> set:
    out = set()
    f = R / "repair_exactness_1d.json"
    if f.exists():
        for arm in json.loads(f.read_text())["arms"].values():
            for e in arm["exceptions"]:
                out.add((pathlib.Path(e["file"]).name, e["seed"]))
    f = R / "arity_evidence_ablations.json"
    if f.exists():
        rep = json.loads(f.read_text())
        for camp in rep["campaigns"].values():
            files = {sz: v["file"] for sz, v in camp["per_size"].items()}
            for a in camp["artifacts"]:
                if a["repaired_gate_and_probe"] and not a["repaired_behavioural"]:
                    out.add((files.get(a["size"], ""), a["seed"]))
    return out


_PROBE_FALSE_POSITIVES = _probe_false_positives()


def is_repair(d) -> bool:
    """Accepted by the gate AND the mode recovered.

    "Recovered" is the probe score EXCEPT where a behavioural audit has shown the probe
    to be a false positive for that artifact -- an invented extra mode, or a rule that
    over-covers the true region. See _probe_false_positives above."""
    if not (d["gate_passed"] and (d["blindness"] or 0.0) == 0.0):
        return False
    return (pathlib.Path(d["file"]).name, d["seed"]) not in _PROBE_FALSE_POSITIVES


def is_blind_exploited(d) -> bool:
    return d["outcome"] == "blind_and_exploited"


def is_partial_repair(d) -> bool:
    """PatchField2D's partial-repair event: the gate accepted an artifact that
    encodes the patch its sample revealed while staying blind to the other. It
    needs per-mode blindness, so it is only defined where the gate accepted."""
    if not d["gate_passed"] or not d["per_mode_blindness"]:
        return False
    vals = list(d["per_mode_blindness"].values())
    return any(v == 0.0 for v in vals) and any(v > 0.0 for v in vals)


def heterogeneity_across_treatments(groups: dict, predicate,
                                    scoring="all") -> dict:
    """Block-level counts per group plus an exact test of the null that one
    common success probability generated them all. 2 groups -> Fisher exact;
    >2 -> the smallest pairwise Fisher p with a Bonferroni factor, which is
    crude but exact and needs no asymptotics at these n. This is the evidence
    that decides whether pooling the groups is defensible at all."""
    counts = {}
    for name, ds in groups.items():
        scored = score_blocks(ds, predicate, scoring=scoring)
        counts[name] = {"k": sum(scored.values()), "n": len(scored),
                        "n_draws": len(ds)}
    names = [n for n in counts if counts[n]["n"] > 0]
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = counts[names[i]], counts[names[j]]
            p = fisher_exact_2x2(a["k"], a["n"] - a["k"],
                                 b["k"], b["n"] - b["k"])
            pairs.append({"groups": [names[i], names[j]], "fisher_p": p})
    if not pairs:
        return {"block_level_counts": counts, "verdict": "only one group"}
    best = min(pairs, key=lambda x: x["fisher_p"])
    n_pairs = len(pairs)
    adj = min(1.0, best["fisher_p"] * n_pairs)
    return {
        "block_level_counts": counts,
        "block_scoring": scoring,
        "pairwise_fisher": pairs,
        "min_pairwise_fisher_p": best["fisher_p"],
        "min_pair": best["groups"],
        "bonferroni_adjusted_p": adj,
        "n_pairs": n_pairs,
        "verdict": ("treatments differ at the 5% level after Bonferroni; "
                    "pooling them into one rate is not defensible"
                    if adj < 0.05 else
                    "no evidence against a common rate at the 5% level -- "
                    "pooling is not contradicted, but the exact bound is still "
                    "the block-level one"),
        "assumptions": ("the test is on the COLLAPSED per-block outcomes, so it "
                        "inherits no independence assumption about draws within "
                        "a block; it does assume blocks are independent across "
                        "groups, which holds only where the groups use disjoint "
                        "blocks -- where they share blocks (the usual case here) "
                        "the test is anticonservative and should be read as a "
                        "descriptive heterogeneity flag, not a p-value")}


# --------------------------------------------------------------------------- #
# report                                                                      #
# --------------------------------------------------------------------------- #
def treatment_table(draws) -> list:
    """PER-TREATMENT, PER-CELL rows.  A cell is (treatment, model): within a
    cell every block appears at most once, which the row asserts, so the cell's
    own bound is a block-level bound by construction."""
    cells = defaultdict(list)
    for d in draws:
        cells[(treatment_key(d), d["model"])].append(d)
    rows = []
    for (tk, model), ds in sorted(cells.items()):
        blocks = sorted({d["block"] for d in ds})
        assert len(blocks) == len(ds), (
            f"cell {tk} / {model} has {len(ds)} draws over {len(blocks)} blocks "
            f"-- a cell was assumed to be one draw per block")
        present = [d for d in ds if d["mode_present"]]
        outcomes = defaultdict(int)
        for d in ds:
            outcomes[d["outcome"]] += 1
        branches = {
            "mode_absent": sum(1 for d in ds if not d["mode_present"]),
            "mode_present": len(present),
        }
        if ds[0]["mode_present_per"] is not None:
            per_mode = defaultdict(int)
            for d in ds:
                for name, seen in d["mode_present_per"].items():
                    per_mode[f"{name}_seen"] += int(seen)
            branches["per_mode_seen"] = dict(sorted(per_mode.items()))
            branches["see_none"] = sum(1 for d in ds if d["n_modes_seen"] == 0)
            branches["see_one"] = sum(1 for d in ds if d["n_modes_seen"] == 1)
            branches["see_both"] = sum(1 for d in ds if d["n_modes_seen"] == 2)
        row = {
            "treatment": tk,
            "model": model,
            "size": ds[0]["size"],
            "family": ds[0]["family"],
            "file": sorted({d["file"] for d in ds}),
            "n_blocks": len(blocks),
            "n_draws": len(ds),
            "blocks": blocks,
            "branch_counts": branches,
            "outcome_counts": dict(sorted(outcomes.items())),
        }
        if present:
            row["repair_bound_block_level"] = pooled_bound(
                present, is_repair, unit="block", scoring="all",
                label=f"repair | {tk} | {model}")
        absent = [d for d in ds if not d["mode_present"]]
        if absent and ds[0]["arm"] == "incomplete":
            row["blind_exploited_bound_block_level"] = pooled_bound(
                absent, is_blind_exploited, unit="block", scoring="all",
                label=f"blind-and-exploited | {tk} | {model}")
        rows.append(row)
    return rows


def _select(draws, **kw):
    def ok(d):
        for key, want in kw.items():
            v = d.get(key)
            if callable(want):
                if not want(v):
                    return False
            elif isinstance(want, (list, tuple, set)):
                if v not in want:
                    return False
            elif v != want:
                return False
        return True
    return [d for d in draws if ok(d)]


def build_report(draws) -> dict:
    rep = {
        "script": "paper2_statistics.py",
        "review_point": "#5 -- statistics by experimental unit",
        "alpha": ALPHA,
        "unit_hierarchy": {
            "primary_unit": {
                "name": "gate-sample block",
                "identified_by": "(seed_index, seed_offset), i.e. seed // 10000",
                "why": ("collect_transitions draws Random(rollout_seed + i) and "
                        "rollout_seed = 10000*(seed_index + 1 + seed_offset); the "
                        "stream does not depend on instrument, knob, patch shape, "
                        "prompt variant or iteration budget, so campaigns that "
                        "reuse a seed index reuse the random draw byte for byte"),
                "evidence": "scripts/sample_stream_census.py, "
                            "src/cwm/continuous/contract.py::collect_transitions",
            },
            "secondary_unit": {
                "name": "synthesis draw",
                "identified_by": "(block, treatment, model)",
                "why": "one synthesize+refine attempt; attempts sharing a block "
                       "share their evidence and are not independent trials",
            },
            "treatment": {
                "name": "treatment",
                "identified_by": "(instrument, knob, patch shape, prompt variant, "
                                 "iteration budget, arm)",
                "why": "varying any of these adds a TREATMENT, not a sample; "
                       "model is excluded on purpose -- it indexes draws",
            },
        },
        "methods": {
            "interval": "Clopper-Pearson exact two-sided 95% (binomial "
                        "inversion via math.comb; closed forms at k=0 and k=n). "
                        "Wilson score interval reported alongside because the "
                        "current prose quotes Wilson.",
            "block_scoring": {
                "all": "block succeeds iff every draw on it succeeded; estimand "
                       "P(all attempts on a fresh sample succeed). CONSERVATIVE "
                       "-- quote this one.",
                "any": "block succeeds iff some draw on it succeeded; estimand "
                       "P(at least one attempt on a fresh sample succeeds). "
                       "OPTIMISTIC.",
            },
            "draw_level": "computed only as the labelled invalid-if-pooled "
                          "comparator whenever blocks are shared; "
                          "pooled_bound(unit='draw') raises otherwise.",
        },
        "totals": {
            "n_draws": len(draws),
            "n_distinct_blocks": len({d["block"] for d in draws}),
            "n_treatments": len({treatment_key(d) for d in draws}),
            "files": sorted({d["file"] for d in draws}),
        },
        "treatment_table": treatment_table(draws),
    }
    rep["headline"] = _headline(draws)
    rep["censored_zeros"] = _censored_zeros(draws)
    rep["paper_replacements"] = _replacements(rep)
    rep["assumptions"] = {
        "block_level_clopper_pearson": (
            "Blocks are i.i.d. draws of the gate sample (they are: distinct seed "
            "indices seed a fresh random stream) and the collapsed per-block "
            "outcome is Bernoulli. No assumption whatever is made about the "
            "dependence between draws inside a block -- collapsing removes it. "
            "Cost: the estimand becomes a per-block one ('every attempt on a "
            "fresh sample succeeds' under 'all' scoring), which is what the "
            "paper should state."),
        "why_not_a_hierarchical_model": (
            "Clusters here hold 1-4 draws and the outcome is at or next to the "
            "0/1 boundary in every cell (pendulum repair is 76/76, PatchField2D "
            "repair is 0/156). A random-intercept GLMM or a beta-binomial has no "
            "identifiable variance component on zero-variance data: the ANOVA ICC "
            "is literally 0/0 there (see headline.*.icc.reason). Where it IS "
            "defined -- the pooled 1D repair set -- the moment estimator returns "
            "ICC <= 0, so the Rao-Scott design effect collapses to 1 and hands "
            "back the very draw-level interval we are rejecting (see "
            "headline.onedim_repair.cluster_robust_comparators"
            ".rao_scott_design_effect.warning). Both failure modes point the same "
            "way: at these cluster sizes the variance component is not "
            "estimable, so we quote the conservative block-level exact bound and "
            "report the design-effect interval and a cluster bootstrap only as "
            "labelled comparators."),
        "pooling_across_treatments": (
            "Any interval whose n pools several treatments additionally assumes a "
            "common success probability across them, which the ablations were "
            "designed to vary. Each pooled bound carries "
            "homogeneity_assumed_across_treatments and the treatment list, so the "
            "assumption is visible where it is made. For a NEGATIVE result "
            "(0 successes) pooling heterogeneous treatments is the benign "
            "direction: the bound holds for the mixture actually run."),
        "exploited_threshold": (
            f"'exploited' means play_cost >= {EXPLOITED_PLAY_COST}; the observed "
            f"mode-absent play_cost values are 0.9990 (cart) and 0.9949 "
            f"(pendulum), so the classification is not near the threshold."),
    }
    return rep


def _headline(draws) -> dict:
    out = {}

    # --- 1. the 2D negative result -----------------------------------------
    p2d = _select(draws, instrument="patch2d", arm="incomplete", family="gpt-5.x",
                  mode_present=True)
    out["patch2d_repair_negative"] = {
        "paper_text": "0/156 mode-containing seeds on PatchField2D",
        "what_is_pooled": ("two model sizes (mini, large) x the two disc knobs "
                           "k=(3,7) and k=(5,9) x the zero-curvature square "
                           "ablation x the region-guided 3x-budget treatment"),
        "n_draws": len(p2d),
        "n_distinct_blocks": len({d["block"] for d in p2d}),
        "draws_per_block": {str(b): sum(1 for d in p2d if d["block"] == b)
                            for b in sorted({d["block"] for d in p2d})},
        "HONEST_block_level": pooled_bound(
            p2d, is_repair, unit="block", scoring="all",
            label="per-block probability that a fresh mode-containing gate "
                  "sample is repaired by any of the attempts run on it"),
        "INVALID_draw_level_comparator": pooled_bound(
            p2d, is_repair, unit="draw", comparator=True,
            label="what the naive pooling of 156 draws would have said"),
        "per_campaign_block_level": [
            {"campaign": name,
             "bound": pooled_bound(sel, is_repair, unit="block", scoring="all",
                                   label=f"repair | {name}")}
            for name, sel in (
                ("disc k=(3,7)", _select(p2d, patch_shape="disc",
                                         prompt_variant="default",
                                         knob=lambda k: k["k1"] == 3.0)),
                ("disc k=(5,9)", _select(p2d, patch_shape="disc",
                                         prompt_variant="default",
                                         knob=lambda k: k["k1"] == 5.0)),
                ("square k=(3,7)", _select(p2d, patch_shape="square")),
                ("guided 3x budget k=(3,7)",
                 _select(p2d, prompt_variant="region")),
            )],
    }
    inflation = (out["patch2d_repair_negative"]["HONEST_block_level"]
                 ["clopper_pearson_95"][1]
                 / out["patch2d_repair_negative"]
                 ["INVALID_draw_level_comparator"]["clopper_pearson_95"][1])
    out["patch2d_repair_negative"]["honest_over_naive_upper_bound_ratio"] = inflation

    # partial repair (the see-one-miss-the-other branch on the DISC cells,
    # which is the 66 the paper quotes)
    see1 = _select(draws, instrument="patch2d", arm="incomplete",
                   family="gpt-5.x", n_modes_seen=1, patch_shape="disc",
                   prompt_variant="default")
    out["patch2d_partial_repair_negative"] = {
        "paper_text": "0/66 partial repair",
        "n_draws": len(see1),
        "n_distinct_blocks": len({d["block"] for d in see1}),
        "HONEST_block_level": pooled_bound(
            see1, is_partial_repair, unit="block", scoring="all",
            label="per-block probability of repairing the seen patch while "
                  "staying blind to the unseen one"),
        "INVALID_draw_level_comparator": pooled_bound(
            see1, is_partial_repair, unit="draw", comparator=True),
        "note": ("the all-or-nothing gate rejected every one of these "
                 "artifacts, so partial repair is 0 for the trivial reason "
                 "that nothing was certified; the bound is on the per-block "
                 "probability of a certified partial repair"),
    }

    # is the 2D negative homogeneous across the four campaigns? (it must be:
    # every cell is 0, so pooling is the benign direction)
    out["patch2d_repair_negative"]["heterogeneity_across_campaigns"] = \
        heterogeneity_across_treatments({
            "disc k=(3,7)": _select(p2d, patch_shape="disc",
                                    prompt_variant="default",
                                    knob=lambda k: k["k1"] == 3.0),
            "disc k=(5,9)": _select(p2d, patch_shape="disc",
                                    prompt_variant="default",
                                    knob=lambda k: k["k1"] == 5.0),
            "square k=(3,7)": _select(p2d, patch_shape="square"),
            "guided 3x k=(3,7)": _select(p2d, prompt_variant="region"),
        }, is_repair)

    # the Claude 2D arm shares blocks with the GPT campaigns
    cl2d = _select(draws, instrument="patch2d", arm="incomplete",
                   family="claude", mode_present=True)
    gpt_blocks = {d["block"] for d in p2d}
    out["patch2d_claude_arm"] = {
        "paper_text": "0/3 in a Claude cross-family arm on the same cell",
        "n_draws": len(cl2d),
        "blocks": sorted({d["block"] for d in cl2d}),
        "blocks_already_in_the_gpt_campaign":
            sorted({d["block"] for d in cl2d} & gpt_blocks),
        "adds_new_blocks": len({d["block"] for d in cl2d} - gpt_blocks),
        "HONEST_block_level": pooled_bound(cl2d, is_repair, unit="block",
                                           scoring="all"),
        "note": ("this arm closes the single-family confound, and adds draws, "
                 "but adds NO new gate samples: its three seeds are blocks the "
                 "GPT-5.x campaigns already used, so the distinct-block count "
                 "behind the 2D negative result stays at "
                 f"{len(gpt_blocks)}"),
    }
    all2d = p2d + cl2d
    out["patch2d_repair_negative_with_claude"] = {
        "n_draws": len(all2d),
        "n_distinct_blocks": len({d["block"] for d in all2d}),
        "HONEST_block_level": pooled_bound(all2d, is_repair, unit="block",
                                           scoring="all"),
        "INVALID_draw_level_comparator": pooled_bound(
            all2d, is_repair, unit="draw", comparator=True),
    }

    # --- 2. the 1D 109/111 repairs -----------------------------------------
    one = _select(draws, instrument=("cart", "pendulum"), arm="incomplete",
                  family="gpt-5.x", mode_present=True)
    out["onedim_repair"] = {
        "paper_text": "GPT-5.x repaired 109 of 111 revealed modes",
        "what_is_pooled": ("two instruments x two model sizes x three cart "
                           "knob/offset cells x three pendulum knob/offset cells"),
        "n_draws": len(one),
        "n_repaired_draws": sum(1 for d in one if is_repair(d)),
        "n_distinct_blocks": len({d["block"] for d in one}),
        "n_distinct_instrument_blocks": len({(d["instrument"], d["block"])
                                             for d in one}),
        "clustered_aggregate_block_level_all_scoring": pooled_bound(
            one, is_repair, unit="block", scoring="all",
            label="per-block probability that EVERY attempt on a fresh "
                  "mode-containing sample repairs (conservative; quote this)"),
        "block_level_any_scoring": pooled_bound(
            one, is_repair, unit="block", scoring="any",
            label="per-block probability that SOME attempt repairs (optimistic)"),
        "clustered_by_instrument_block_comparator": pooled_bound(
            one, is_repair, unit="block", scoring="all",
            cluster_key=by_instrument_block,
            label="looser clustering: a fresh instrument on the same seed "
                  "counted as a fresh cluster (common random numbers, "
                  "different dynamics)"),
        "INVALID_draw_level_comparator": pooled_bound(
            one, is_repair, unit="draw", comparator=True,
            label="what pooling 111 correlated draws would have said"),
        "cluster_robust_comparators": {
            "rao_scott_design_effect": anova_icc(one, is_repair),
            "cluster_bootstrap": cluster_bootstrap(one, is_repair),
        },
        "per_instrument": {},
        "per_knob": {},
        "per_size": {},
        "exceptions": [
            {"file": d["file"], "seed": d["seed"], "block": d["block"],
             "treatment": treatment_key(d), "model": d["model"],
             "gate_accuracy": d["gate_accuracy"], "outcome": d["outcome"]}
            for d in one if not is_repair(d)],
    }
    for ins in ("cart", "pendulum"):
        sel = _select(one, instrument=ins)
        out["onedim_repair"]["per_instrument"][ins] = {
            "n_draws": len(sel),
            "n_repaired_draws": sum(1 for d in sel if is_repair(d)),
            "n_distinct_blocks": len({d["block"] for d in sel}),
            "block_level_all_scoring": pooled_bound(
                sel, is_repair, unit="block", scoring="all",
                label=f"{ins} repair, conservative block scoring"),
            "block_level_any_scoring": pooled_bound(
                sel, is_repair, unit="block", scoring="any",
                label=f"{ins} repair, optimistic block scoring"),
            "INVALID_draw_level_comparator": pooled_bound(
                sel, is_repair, unit="draw", comparator=True),
            "rao_scott_design_effect": anova_icc(sel, is_repair),
            "cluster_bootstrap": cluster_bootstrap(sel, is_repair),
        }
    knobs = defaultdict(list)
    for d in one:
        knobs[f"{d['instrument']} {treatment_key(d).split(' | ')[1]}"].append(d)
    for name, sel in sorted(knobs.items()):
        out["onedim_repair"]["per_knob"][name] = {
            "n_draws": len(sel),
            "n_repaired_draws": sum(1 for d in sel if is_repair(d)),
            "n_distinct_blocks": len({d["block"] for d in sel}),
            "block_level_all_scoring": pooled_bound(sel, is_repair,
                                                    unit="block", scoring="all"),
        }
    out["onedim_repair"]["heterogeneity_across_knobs"] = \
        heterogeneity_across_treatments(dict(knobs), is_repair)
    out["onedim_repair"]["heterogeneity_across_knobs"]["why_this_matters"] = (
        "the pooled 109/111 mixes three cells in which every block repaired "
        "with one in which 2 of 5 did not (cart x_wall=4: 3/5 blocks). The raw "
        "pairwise Fisher p against that cell is 0.023-0.033, which does NOT "
        "survive Bonferroni over the 6 pairs, so the data does not establish "
        "heterogeneity -- but it does not license the pooled number either: "
        "0.982 is an average of 1.00, 1.00, 1.00 and 0.60 weighted by how many "
        "draws each campaign happened to run, which is a design choice rather "
        "than an estimate of a rate. Report the cells.")
    out["onedim_repair"]["heterogeneity_across_sizes"] = \
        heterogeneity_across_treatments(
            {s: _select(one, size=s) for s in sorted({d["size"] for d in one})},
            is_repair)
    sizes = defaultdict(list)
    for d in one:
        sizes[d["size"]].append(d)
    for name, sel in sorted(sizes.items()):
        out["onedim_repair"]["per_size"][name] = {
            "n_draws": len(sel),
            "n_repaired_draws": sum(1 for d in sel if is_repair(d)),
            "n_distinct_blocks": len({d["block"] for d in sel}),
            # one model, several treatments -> blocks still repeat across knobs
            "block_level_all_scoring": pooled_bound(sel, is_repair,
                                                    unit="block", scoring="all"),
        }

    # --- 3. the mode-absent blind-and-exploited conditional ----------------
    for ins in ("cart", "pendulum"):
        absent = _select(draws, instrument=ins, arm="incomplete",
                         family="gpt-5.x", mode_present=False)
        out[f"{ins}_blind_and_exploited"] = {
            "paper_text": ("the wall/mode-absent conditional is 20/20 across "
                           "cart sizes and three runs" if ins == "cart"
                           else "18/18 across pendulum sizes"),
            "n_draws": len(absent),
            "n_blind_exploited_draws": sum(1 for d in absent
                                           if is_blind_exploited(d)),
            "n_distinct_blocks": len({d["block"] for d in absent}),
            "HONEST_block_level": pooled_bound(
                absent, is_blind_exploited, unit="block", scoring="all",
                label=f"{ins}: per-block probability that a mode-absent sample "
                      f"yields a certified, mode-blind, exploited artifact"),
            "INVALID_draw_level_comparator": pooled_bound(
                absent, is_blind_exploited, unit="draw", comparator=True),
        }
    return out


def _censored_zeros(draws) -> list:
    """Every printed zero in the paper that is a CENSORED zero: a count of 0
    successes whose upper confidence limit is far from 0. Keyed so prose can
    cite results/paper2_statistics.json::<key>."""
    zeros = []

    def add(key, paper_text, sel, predicate=is_repair, note=""):
        b = pooled_bound(sel, predicate, unit="block", scoring="all")
        naive = pooled_bound(sel, predicate, unit="draw", comparator=True)
        assert b["k"] == 0, f"{key} is not a zero: k={b['k']}"
        zeros.append({
            "key": key,
            "paper_text": paper_text,
            "n_draws": b["n_draws"],
            "n_distinct_blocks": b["n_distinct_blocks"],
            "block_level_upper_95_clopper_pearson": b["clopper_pearson_95"][1],
            "block_level_upper_95_wilson": b["wilson_95"][1],
            "INVALID_draw_level_upper_95_clopper_pearson":
                naive["clopper_pearson_95"][1],
            "cite_as": (f"0 of {b['n_draws']} draws over "
                        f"{b['n_distinct_blocks']} distinct gate-sample blocks; "
                        f"exact 95% upper bound on the per-block rate "
                        f"{b['clopper_pearson_95'][1]:.3f}"),
            "note": note,
        })

    p2d = _select(draws, instrument="patch2d", arm="incomplete",
                  family="gpt-5.x", mode_present=True)
    add("censored_zeros.patch2d_pooled_0_of_156",
        "0/156 mode-containing seeds recover the 2D region", p2d,
        note="pools 4 treatments over 20 blocks")
    add("censored_zeros.patch2d_disc_0_of_76",
        "0/76 mode-containing disc seeds",
        _select(p2d, patch_shape="disc", prompt_variant="default"))
    add("censored_zeros.patch2d_square_0_of_40",
        "0/40 repair in the zero-curvature square ablation",
        _select(p2d, patch_shape="square"))
    add("censored_zeros.patch2d_guided_0_of_40",
        "0/40 under region-first guidance at 3x budget",
        _select(p2d, prompt_variant="region"))
    add("censored_zeros.patch2d_partial_repair_0_of_66",
        "0/66 partial repair",
        _select(draws, instrument="patch2d", arm="incomplete",
                family="gpt-5.x", n_modes_seen=1, patch_shape="disc",
                prompt_variant="default"),
        predicate=is_partial_repair,
        note="the disc cells' see-one-miss-the-other branch; the gate refused "
             "every artifact, so no certified partial repair could exist")
    add("censored_zeros.patch2d_claude_0_of_3",
        "0/3 in the Claude cross-family arm",
        _select(draws, instrument="patch2d", arm="incomplete", family="claude",
                mode_present=True),
        note="its 3 blocks are already among the GPT campaign's 20")
    add("censored_zeros.patch2d_all_families_0_of_159",
        "0/156 pooled plus 0/3 Claude",
        p2d + _select(draws, instrument="patch2d", arm="incomplete",
                      family="claude", mode_present=True),
        note="still 20 distinct gate-sample blocks")
    qwen = _select(draws, instrument=("cart", "pendulum"), arm="incomplete",
                   family="qwen", mode_present=True)
    if qwen:
        add("censored_zeros.qwen_1d_repair_0_of_4",
            "Qwen 0/2 mode-present (superstitious patches)", qwen,
            note="the gate refused every one; n is draws over "
                 f"{len({d['block'] for d in qwen})} blocks")
    return zeros


def _replacements(rep) -> list:
    """The exact substitutions the paper should make."""
    h = rep["headline"]
    p2 = h["patch2d_repair_negative"]
    one = h["onedim_repair"]
    cart = one["per_instrument"]["cart"]
    pend = one["per_instrument"]["pendulum"]
    return [
        {"json_key": "headline.patch2d_repair_negative.HONEST_block_level",
         "paper_currently": "0/156 ... a Wilson 95% upper bound of 0.161 per "
                            "sample (quoted for the disc cells' 20 blocks)",
         "replace_with": (
             f"0 of {p2['n_draws']} mode-containing synthesis draws, over "
             f"{p2['n_distinct_blocks']} distinct gate-sample blocks: exact "
             f"(Clopper-Pearson) 95% upper bound "
             f"{p2['HONEST_block_level']['clopper_pearson_95'][1]:.3f} on the "
             f"per-block repair probability (Wilson "
             f"{p2['HONEST_block_level']['wilson_95'][1]:.3f})"),
         "naive_comparator_to_display": (
             f"pooling the {p2['n_draws']} draws as independent trials would "
             f"have claimed "
             f"{p2['INVALID_draw_level_comparator']['clopper_pearson_95'][1]:.4f}"
             f" -- {p2['honest_over_naive_upper_bound_ratio']:.1f}x tighter than "
             f"the evidence supports")},
        {"json_key": "headline.onedim_repair.per_instrument.cart",
         "paper_currently": "all-repair gives a Wilson 95% lower bound of 0.851 "
                            "on the cart",
         "replace_with": (
             f"the cart is NOT all-repair at block level: "
             f"{cart['block_level_all_scoring']['k']}/"
             f"{cart['block_level_all_scoring']['n']} blocks have every draw "
             f"repaired (and only {cart['block_level_any_scoring']['k']}/"
             f"{cart['block_level_any_scoring']['n']} have any draw repaired: "
             f"one of the two exceptions is the ONLY mode-present cart draw its "
             f"block ever produced), giving an exact 95% lower bound of "
             f"{cart['block_level_all_scoring']['clopper_pearson_95'][0]:.3f} "
             f"(Wilson {cart['block_level_all_scoring']['wilson_95'][0]:.3f}). "
             f"The 0.851 figure is the OPTIMISTIC scoring -- P(some attempt on a "
             f"fresh sample repairs) -- whose exact lower bound is "
             f"{cart['block_level_any_scoring']['clopper_pearson_95'][0]:.3f}; "
             f"quote it only with that estimand spelled out")},
        {"json_key": "headline.onedim_repair.per_instrument.pendulum",
         "paper_currently": "0.898 on the pendulum",
         "replace_with": (
             f"pendulum {pend['block_level_all_scoring']['k']}/"
             f"{pend['block_level_all_scoring']['n']} blocks all-repair, exact "
             f"95% lower bound "
             f"{pend['block_level_all_scoring']['clopper_pearson_95'][0]:.3f} "
             f"(Wilson {pend['block_level_all_scoring']['wilson_95'][0]:.3f})")},
        {"json_key": "headline.onedim_repair"
                     ".clustered_aggregate_block_level_all_scoring",
         "paper_currently": "109 of 111 revealed modes",
         "replace_with": (
             f"{one['n_repaired_draws']} of {one['n_draws']} synthesis draws "
             f"over {one['n_distinct_blocks']} distinct gate-sample blocks; "
             f"clustered at block level "
             f"{one['clustered_aggregate_block_level_all_scoring']['k']}/"
             f"{one['clustered_aggregate_block_level_all_scoring']['n']} blocks "
             f"repair on every attempt, exact 95% CI ["
             f"{one['clustered_aggregate_block_level_all_scoring']['clopper_pearson_95'][0]:.3f}, "
             f"{one['clustered_aggregate_block_level_all_scoring']['clopper_pearson_95'][1]:.3f}]")},
        {"json_key": "headline.cart_blind_and_exploited.HONEST_block_level",
         "paper_currently": "per size that is 10/10 (Wilson lower bound 0.72) ... "
                            "against pooled 0.84 whose trials share samples",
         "replace_with": (
             f"{h['cart_blind_and_exploited']['HONEST_block_level']['k']}/"
             f"{h['cart_blind_and_exploited']['HONEST_block_level']['n']} "
             f"distinct mode-absent gate-sample blocks yield a certified, blind, "
             f"exploited artifact on every draw: exact 95% lower bound "
             f"{h['cart_blind_and_exploited']['HONEST_block_level']['clopper_pearson_95'][0]:.3f} "
             f"(Wilson "
             f"{h['cart_blind_and_exploited']['HONEST_block_level']['wilson_95'][0]:.3f}). "
             f"This is a legitimately block-level bound because --seed-offset 20 "
             f"supplied fresh blocks, so the 0.84 survives as a BLOCK-level "
             f"figure -- but it should be stated over blocks, not over draws")},
        {"json_key": "headline.pendulum_blind_and_exploited.HONEST_block_level",
         "paper_currently": "18/18 across pendulum sizes ... 9/9 (0.70)",
         "replace_with": (
             f"{h['pendulum_blind_and_exploited']['HONEST_block_level']['k']}/"
             f"{h['pendulum_blind_and_exploited']['HONEST_block_level']['n']} "
             f"distinct mode-absent blocks, exact 95% lower bound "
             f"{h['pendulum_blind_and_exploited']['HONEST_block_level']['clopper_pearson_95'][0]:.3f} "
             f"(Wilson "
             f"{h['pendulum_blind_and_exploited']['HONEST_block_level']['wilson_95'][0]:.3f})")},
        {"json_key": "headline.patch2d_claude_arm",
         "paper_currently": "78 distinct gate samples each given two independent "
                            "synthesis draws (38 disc + 20 square + 20 guided)",
         "replace_with": (
             f"{p2['n_distinct_blocks']} distinct rollout-seed blocks; the disc "
             f"knob change reuses the block's random stream, so k=(3,7) and "
             f"k=(5,9) are two treatments on the same 20 blocks rather than 38 "
             f"samples. {p2['n_draws']} draws over "
             f"{p2['n_distinct_blocks']} blocks")},
    ]


def main() -> int:
    draws = load_draws()
    rep = build_report(draws)
    dst = R / "paper2_statistics.json"
    tmp = dst.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rep, indent=2, sort_keys=False))
    tmp.replace(dst)

    print(f"{len(draws)} synthesis draws over "
          f"{rep['totals']['n_distinct_blocks']} distinct gate-sample blocks in "
          f"{rep['totals']['n_treatments']} treatments\n")
    print("PER-TREATMENT, PER-CELL (block-level bounds; one draw per block "
          "inside a cell)")
    print(f"{'treatment':<62} {'model':<28} {'bl':>3} {'dr':>3}  outcomes")
    for row in rep["treatment_table"]:
        oc = ", ".join(f"{k}={v}" for k, v in row["outcome_counts"].items())
        print(f"{row['treatment']:<62} {row['model']:<28} "
              f"{row['n_blocks']:3} {row['n_draws']:3}  {oc}")

    h = rep["headline"]
    p2 = h["patch2d_repair_negative"]
    print("\nHEADLINE 1 -- the PatchField2D negative result")
    print(f"  draws {p2['n_draws']}, DISTINCT BLOCKS {p2['n_distinct_blocks']}")
    print(f"  honest (block-level, exact): upper 95% "
          f"{p2['HONEST_block_level']['clopper_pearson_95'][1]:.4f}  "
          f"(Wilson {p2['HONEST_block_level']['wilson_95'][1]:.4f})")
    print(f"  invalid-if-pooled comparator (draw level): upper 95% "
          f"{p2['INVALID_draw_level_comparator']['clopper_pearson_95'][1]:.4f}"
          f"  -> honest bound is "
          f"{p2['honest_over_naive_upper_bound_ratio']:.1f}x wider")
    one = h["onedim_repair"]
    print("\nHEADLINE 2 -- the 1D repairs")
    print(f"  {one['n_repaired_draws']}/{one['n_draws']} draws over "
          f"{one['n_distinct_blocks']} blocks")
    agg = one["clustered_aggregate_block_level_all_scoring"]
    print(f"  clustered (block, conservative 'all' scoring): {agg['k']}/{agg['n']}"
          f" -> exact 95% [{agg['clopper_pearson_95'][0]:.4f}, "
          f"{agg['clopper_pearson_95'][1]:.4f}]")
    opt = one["block_level_any_scoring"]
    print(f"  optimistic 'any' scoring: {opt['k']}/{opt['n']} -> lower "
          f"{opt['clopper_pearson_95'][0]:.4f}")
    print(f"  invalid draw-level comparator: lower "
          f"{one['INVALID_draw_level_comparator']['clopper_pearson_95'][0]:.4f}")
    for ins in ("cart", "pendulum"):
        pi = one["per_instrument"][ins]
        print(f"    {ins:<9} all-scoring {pi['block_level_all_scoring']['k']}/"
              f"{pi['block_level_all_scoring']['n']} lower "
              f"{pi['block_level_all_scoring']['clopper_pearson_95'][0]:.4f} | "
              f"any-scoring {pi['block_level_any_scoring']['k']}/"
              f"{pi['block_level_any_scoring']['n']} lower "
              f"{pi['block_level_any_scoring']['clopper_pearson_95'][0]:.4f}")
    print("\nCENSORED ZEROS")
    for z in rep["censored_zeros"]:
        print(f"  {z['key']:<52} {z['cite_as']}")
    print("\nREPLACEMENTS THE PAPER SHOULD MAKE")
    for r in rep["paper_replacements"]:
        print(f"  [{r['json_key']}]\n    was: {r['paper_currently']}\n"
              f"    now: {r['replace_with']}")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
