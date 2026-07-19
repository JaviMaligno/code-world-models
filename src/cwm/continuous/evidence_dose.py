"""Evidence-dose: a fixed 40-example transcript cap, env-aware, with
structured (source_index-keyed) failures so refinement can be shown to be
capped by the sample rather than by the model's competence.

Design (rev-3 plan, Task 12): the WHOLE transcript the LLM ever sees is
capped at 40 examples = m positives (contact fired) + m distinct matched
negatives (near-misses, matched to each kept positive by boundary-normal
distance) + (40 - 2m) background (neither positive nor a matched near-miss).
The background block is presented as controlled OBSERVATIONS, never as
FAILURES -- `refine_capped` only ever feeds back failures whose
`source_index` is in the 40 (`allowed_source_indices`); it also measures the
REAL gate on the full (e.g. 3200-transition) `gate_transitions` sample, so it
can tell the difference between "the model is still wrong" and "the model is
now as good as it can get given the 40 it was allowed to see" (an
`evidence_capped_failure`).
"""
import math
import random
from dataclasses import dataclass

from ..synthesizer import extract_code
from .contract import RefineResult, _compare_transitions, _example_lines, _run_contract_cases


def _proposed_endpoint(env, state: list, action: float) -> tuple:
    """The position `env` would move to BEFORE any mode-contact clamp fires
    (i.e. the raw integrator output). This is what must be projected onto
    `env.shape`'s boundary to measure how deep a hit went / how close a miss
    came -- the recorded `next_state` for a positive has already been
    clamped back to the shape boundary/previous position, so it cannot be
    used directly for this measurement."""
    x2, y2, _vx2, _vy2 = env._integrate(tuple(state), action)
    return (x2, y2)


def _boundary_normal_distance(env, endpoint: tuple) -> tuple[float, tuple]:
    """Euclidean distance from `endpoint` to its projection onto
    `env.shape`'s boundary (the boundary-normal distance), plus the
    projected boundary point itself."""
    q, _ = env.shape.project_to_boundary(endpoint)
    d = math.hypot(endpoint[0] - q[0], endpoint[1] - q[1])
    return d, q


def _select_span(candidates: list, m: int, span: str, rng: random.Random) -> list:
    """Pick m of `candidates` (each a (transition, endpoint, boundary_point)
    triple) so the kept set's boundary-arc extent matches `span`: "large"
    maximizes spread (farthest-point sampling over the boundary
    projections), "small" clusters tightly around a random anchor (nearest
    neighbors by boundary-projection distance)."""
    if span not in ("small", "large"):
        raise ValueError(f"span must be 'small' or 'large', got {span!r}")
    if len(candidates) <= m:
        return list(candidates)
    if span == "large":
        start = rng.choice(candidates)
        chosen = [start]
        remaining = [c for c in candidates if c is not start]
        while len(chosen) < m and remaining:
            def min_dist_to_chosen(c):
                return min(math.hypot(c[2][0] - s[2][0], c[2][1] - s[2][1])
                          for s in chosen)
            best = max(remaining, key=min_dist_to_chosen)
            chosen.append(best)
            remaining.remove(best)
        return chosen
    anchor = rng.choice(candidates)
    others = sorted(
        (c for c in candidates if c is not anchor),
        key=lambda c: math.hypot(c[2][0] - anchor[2][0], c[2][1] - anchor[2][1]))
    return [anchor] + others[:m - 1]


def build_dose_sample(env, transitions: list[dict], m: int, span: str,
                      rng: random.Random) -> tuple[list[dict], set, dict]:
    """Build the fixed 40-example controlled dose from `transitions`
    (typically the full 3200-transition gate sample).

    Returns (controlled_examples, allowed_source_indices, meta):
      controlled_examples -- exactly 40 transition dicts: m positives + m
        distinct matched negatives + (40 - 2m) background, in that order.
      allowed_source_indices -- the `source_index` set of those 40 (the only
        indices `refine_capped` may treat as correctable failures).
      meta -- {"n_positive": m, "n_negative": m, "n_background": 40 - 2m,
        "evidence_capped": True, "span": span}.
    """
    if not (0 < 2 * m <= 40):
        raise ValueError(f"m={m} invalid: need 0 < 2*m <= 40")
    positives = [t for t in transitions if t["contact"]]
    negatives = [t for t in transitions if not t["contact"]]
    if len(positives) < m:
        raise ValueError(f"need >= {m} positive transitions, found {len(positives)}")

    pos_info = {}
    for t in positives:
        ep = _proposed_endpoint(env, t["state"], t["action"])
        d, q = _boundary_normal_distance(env, ep)
        pos_info[t["source_index"]] = (t, ep, q, d)

    candidates = [(t, ep, q) for (t, ep, q, d) in pos_info.values()]
    chosen = _select_span(candidates, m, span, rng)
    chosen_indices = [c[0]["source_index"] for c in chosen]
    kept_positive_info = [pos_info[si] for si in chosen_indices]

    # Match each kept positive to its nearest (by boundary-normal distance),
    # not-yet-used negative -- a near-miss whose "closeness to the boundary"
    # mirrors the positive's "depth past the boundary", so the pair differs
    # (as much as possible) only in whether the mode actually fired.
    neg_cache = {}
    used_neg_src = set()
    matched_negatives = []
    for (_t, _ep, _q, d_pos) in kept_positive_info:
        best_src, best_diff = None, None
        for nt in negatives:
            src = nt["source_index"]
            if src in used_neg_src:
                continue
            if src not in neg_cache:
                nep = _proposed_endpoint(env, nt["state"], nt["action"])
                nd, _nq = _boundary_normal_distance(env, nep)
                neg_cache[src] = (nt, nd)
            _nt, nd = neg_cache[src]
            diff = abs(nd - d_pos)
            if best_diff is None or diff < best_diff:
                best_src, best_diff = src, diff
        if best_src is None:
            raise ValueError("not enough distinct negative transitions to match")
        used_neg_src.add(best_src)
        matched_negatives.append(neg_cache[best_src][0])

    n_background = 40 - 2 * m
    used_source_indices = set(chosen_indices) | used_neg_src
    bg_pool = [t for t in transitions if t["source_index"] not in used_source_indices]
    if len(bg_pool) < n_background:
        raise ValueError(
            f"not enough remaining transitions for background: need "
            f"{n_background}, have {len(bg_pool)}")
    background = rng.sample(bg_pool, n_background) if n_background else []

    kept_positives = [pos_info[si][0] for si in chosen_indices]
    controlled_examples = kept_positives + matched_negatives + background
    allowed_source_indices = {t["source_index"] for t in controlled_examples}
    meta = {
        "n_positive": m,
        "n_negative": m,
        "n_background": n_background,
        "evidence_capped": True,
        "span": span,
    }
    return controlled_examples, allowed_source_indices, meta


def build_controlled_initial_messages(contract: str,
                                      controlled_examples: list[dict]) -> list[dict]:
    """The INITIAL synthesis prompt for the evidence-dose arm: presents the
    fixed 40 as controlled OBSERVATIONS to match (never framed as
    failures -- there is no code yet to have failed)."""
    system = ("You are an expert Python programmer. You write deterministic, "
              "pure code that exactly implements a specified physics world "
              "model. Output ONLY a single Python code block, no prose.")
    user = (f"{contract}\n\n"
            f"Here are observed transitions (ground truth) to match exactly "
            f"-- a fixed set of controlled observations:\n"
            f"{_example_lines(controlled_examples, len(controlled_examples))}\n\n"
            f"Write the Python module implementing the contract. "
            f"Output only one ```python code block.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def contract_accuracy_indexed(code: str, transitions: list[dict], eps: float,
                              timeout: float = 30.0) -> tuple[float, list[dict]]:
    """Like `contract.contract_accuracy`, but each failure additionally
    carries the failing transition's `source_index`, so failures can be
    filtered to an allowed set (`refine_capped`) or otherwise attributed back
    to the original sample. Returns (accuracy, failures) where failures is a
    list of {"source_index": int, "text": str} dicts, in original order."""
    if not transitions:
        return 0.0, []
    produced, err = _run_contract_cases(code, transitions, timeout=timeout)
    if produced is None:
        return 0.0, [{"source_index": None, "text": err}]
    correct, failure_texts, failed_positions = _compare_transitions(transitions, produced, eps)
    failures = [{"source_index": transitions[i]["source_index"], "text": text}
                for i, text in zip(failed_positions, failure_texts)]
    return correct / len(transitions), failures


def is_evidence_capped_failure(failure_source_indices, allowed_source_indices) -> bool:
    """True iff NONE of the real gate's failing `source_index` values lie in
    the allowed (40-example) set -- i.e. the dose the LLM was allowed to be
    corrected on cannot possibly explain, let alone fix, the remaining gate
    failures: the refinement is capped by the evidence it was given, not by
    the model's competence."""
    return not (set(failure_source_indices) & set(allowed_source_indices))


@dataclass
class CappedRefineResult(RefineResult):
    evidence_capped_failure: bool = False


def refine_capped(provider, model: str, contract: str, code: str,
                  gate_transitions: list[dict], controlled_examples: list[dict],
                  allowed_source_indices: set, eps: float,
                  max_iters: int = 5) -> CappedRefineResult:
    """Refine while the correction budget is capped to the 40-example dose.

    Each iteration measures the REAL gate against the full
    `gate_transitions` (e.g. all 3200), locates failures by `source_index`,
    and filters them to `allowed_source_indices` (the 40's indices) -- ONLY
    those may be fed back as failures; every other real failure is withheld
    (never background, never anything outside the fixed dose). If, at any
    iteration, every remaining real gate failure lies OUTSIDE the allowed
    set, the dose cannot explain them: refinement stops immediately and the
    result is tagged `evidence_capped_failure=True` rather than spending
    iterations that could not possibly help.
    """
    usages = []
    acc, failures = contract_accuracy_indexed(code, gate_transitions, eps)
    iterations = 0
    evidence_capped_failure = False
    while acc < 1.0 and iterations < max_iters:
        capped = [f for f in failures if f["source_index"] in allowed_source_indices]
        if not capped:
            evidence_capped_failure = True
            break
        msg = (f"{contract}\n\nThe current implementation is below. It fails "
               f"some of the controlled observations you were given. Fix it "
               f"so every transition matches to within {eps} in x, v and "
               f"reward. Output only one ```python code block.\n\n"
               f"CURRENT CODE:\n```python\n{code}\n```\n\n"
               f"FAILURES (expected vs got):\n" +
               "\n".join(f["text"] for f in capped[:20]))
        completion = provider.complete([{"role": "user", "content": msg}], model=model)
        usages.append(completion.usage)
        code = extract_code(completion.text)
        acc, failures = contract_accuracy_indexed(code, gate_transitions, eps)
        iterations += 1
    return CappedRefineResult(code=code, accuracy=acc, iterations=iterations,
                              usages=usages,
                              evidence_capped_failure=evidence_capped_failure)
