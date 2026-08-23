#!/usr/bin/env python3
"""H7 bounded-observation-noise extension for the Paper 2 gate.

The design is frozen in ``results/h7_noisy_gate_prespec_v1.json``.  The
inferential unit is a disjoint seed block, never an individual transition.
For Uniform[-eta, eta] observation noise, the support-overlap probability of
one scalar output under a candidate displaced by ``delta`` is exact.  Products
of those overlaps give the conditional probability that a fixed latent block
accepts the candidate.

Run::

    PYTHONPATH=src .venv/bin/python scripts/h7_noisy_observation_gate.py
    PYTHONPATH=src .venv/bin/python scripts/h7_noisy_observation_gate.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
from typing import Any

from cwm.continuous.envs import CartWall, blind_of


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRESPEC_PATH = ROOT / "results/h7_noisy_gate_prespec_v1.json"
RESULT_PATH = ROOT / "results/h7_noisy_observation_gate_v1.json"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def prespec_sha256(prespec: dict) -> str:
    return hashlib.sha256(canonical_bytes(prespec)).hexdigest()


def scalar_overlap_probability(delta: float, eta: float) -> float:
    """Exact overlap probability for equal-width bounded uniform supports."""
    d = abs(float(delta))
    if eta < 0:
        raise ValueError("eta must be non-negative")
    if eta == 0:
        return 1.0 if d == 0 else 0.0
    return max(0.0, 1.0 - d / (2.0 * eta))


def block_overlap_probability(deltas: list[tuple[float, ...]], eta: float) -> float:
    """Conditional block-pass probability, evaluated stably in log space."""
    log_probability = 0.0
    for row in deltas:
        for delta in row:
            q = scalar_overlap_probability(delta, eta)
            if q == 0.0:
                return 0.0
            log_probability += math.log(q)
    return math.exp(log_probability)


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    return sum(math.comb(n, i) * p**i * (1.0 - p) ** (n - i)
               for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> list[float]:
    """Two-sided exact binomial interval, without a SciPy dependency."""
    if not 0 <= k <= n or n <= 0:
        raise ValueError("require 0 <= k <= n and n > 0")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0,1)")
    if k == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        target = alpha / 2.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            survival = 1.0 - _binomial_cdf(k - 1, n, mid)
            if survival < target:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2.0
    if k == n:
        upper = 1.0
    else:
        lo, hi = 0.0, 1.0
        target = alpha / 2.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            cdf = _binomial_cdf(k, n, mid)
            if cdf > target:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2.0
    return [lower, upper]


def _latent_block(env: CartWall, blind: CartWall, block_index: int,
                  n_rollouts: int, seed_base: int) -> dict:
    deltas: list[tuple[float, ...]] = []
    contains_mode = False
    n_contacts = 0
    for rollout_index in range(n_rollouts):
        seed = seed_base + block_index * n_rollouts + rollout_index
        rng = random.Random(seed)
        state = env.initial_state(rng)
        for _ in range(env.h_episode):
            action = rng.uniform(-env.a_max, env.a_max)
            truth_state, truth_reward, contact = env.step(state, action)
            blind_state, blind_reward, _ = blind.step(state, action)
            deltas.append(tuple(b - t for b, t in zip(
                blind_state + (blind_reward,), truth_state + (truth_reward,))))
            contains_mode = contains_mode or contact
            n_contacts += int(contact)
            state = truth_state
    return {"deltas": deltas, "contains_mode": contains_mode,
            "n_contacts": n_contacts}


def _empirical_pass(deltas: list[tuple[float, ...]], eta: float,
                    noise_seed: int, candidate: str, slack: float) -> bool:
    rng = random.Random(noise_seed)
    for row in deltas:
        for delta in row:
            noise = 0.0 if eta == 0.0 else rng.uniform(-eta, eta)
            candidate_delta = 0.0 if candidate == "truth" else delta
            if abs(noise - candidate_delta) > eta + slack:
                return False
    return True


def run_experiment(prespec: dict) -> dict:
    instrument = prespec["instrument"]
    unit = prespec["experimental_unit"]
    observation = prespec["observation_model"]
    gate = prespec["gate"]
    analysis = prespec["analysis"]
    env = CartWall(x_wall=float(instrument["x_wall"]))
    blind = blind_of(env)
    n_blocks = int(unit["n_blocks"])
    n_rollouts = int(unit["rollouts_per_block"])
    rollout_seed_base = int(unit["rollout_seed_base"])
    noise_seed_base = int(observation["noise_seed_base"])
    slack = float(gate["support_slack"])
    alpha = float(analysis["alpha"])

    latent = [_latent_block(env, blind, block_index, n_rollouts,
                            rollout_seed_base)
              for block_index in range(n_blocks)]
    levels = []
    for eta_index, eta_value in enumerate(observation["eta_levels"]):
        eta = float(eta_value)
        block_rows = []
        truth_passes = blind_passes = 0
        analytic = []
        for block_index, block in enumerate(latent):
            noise_seed = noise_seed_base + eta_index * 1_000_000 + block_index
            p_block = block_overlap_probability(block["deltas"], eta)
            truth_pass = _empirical_pass(block["deltas"], eta, noise_seed,
                                         "truth", slack)
            blind_pass = _empirical_pass(block["deltas"], eta, noise_seed,
                                         "blind", slack)
            truth_passes += int(truth_pass)
            blind_passes += int(blind_pass)
            analytic.append(p_block)
            block_rows.append({
                "block_index": block_index,
                "contains_mode": block["contains_mode"],
                "n_contacts": block["n_contacts"],
                "analytic_blind_pass_probability": p_block,
                "truth_pass": truth_pass,
                "blind_pass": blind_pass,
            })
        levels.append({
            "eta": eta,
            "truth": {
                "passes": truth_passes,
                "n_blocks": n_blocks,
                "pass_rate": truth_passes / n_blocks,
                "clopper_pearson_95": clopper_pearson(
                    truth_passes, n_blocks, alpha),
            },
            "blind": {
                "passes": blind_passes,
                "n_blocks": n_blocks,
                "empirical_pass_rate": blind_passes / n_blocks,
                "clopper_pearson_95": clopper_pearson(
                    blind_passes, n_blocks, alpha),
                "analytic_conditional_pass_probability": sum(analytic) / n_blocks,
            },
            "blocks": block_rows,
        })

    p0 = levels[0]["blind"]["analytic_conditional_pass_probability"]
    primary_eta = float(analysis["primary_eta"])
    primary = next(row for row in levels if row["eta"] == primary_eta)
    primary_increase = (
        primary["blind"]["analytic_conditional_pass_probability"] - p0)
    boundary_threshold = float(analysis["boundary_increase"])
    boundary = next((row for row in levels
                     if row["blind"]["analytic_conditional_pass_probability"]
                     - p0 >= boundary_threshold), None)
    total_contacts = sum(block["n_contacts"] for block in latent)
    mode_blocks = sum(block["contains_mode"] for block in latent)
    return {
        "schema_version": "h7-noisy-observation-gate-result-v1",
        "script": "scripts/h7_noisy_observation_gate.py",
        "prespec": "results/h7_noisy_gate_prespec_v1.json",
        "prespec_sha256": prespec_sha256(prespec),
        "experimental_unit": "disjoint_seed_block",
        "n_blocks": n_blocks,
        "rollouts_per_block": n_rollouts,
        "latent_panel": {
            "blocks_with_mode": mode_blocks,
            "blocks_without_mode": n_blocks - mode_blocks,
            "total_contact_transitions": total_contacts,
        },
        "levels": levels,
        "prespecified_decisions": {
            "primary_eta": primary_eta,
            "primary_analytic_increase": primary_increase,
            "primary_robustness_margin": analysis["primary_robustness_margin"],
            "primary_criterion_met": (
                primary_increase <= float(analysis["primary_robustness_margin"])),
            "boundary_increase": boundary_threshold,
            "first_boundary_eta": None if boundary is None else boundary["eta"],
        },
        "claim_scope": prespec["scope"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed result is stale")
    args = parser.parse_args()
    prespec = json.loads(PRESPEC_PATH.read_text())
    result = run_experiment(prespec)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not RESULT_PATH.exists() or RESULT_PATH.read_text() != rendered:
            raise SystemExit(f"stale or missing result: {RESULT_PATH}")
        print(f"fresh: {RESULT_PATH.relative_to(ROOT)}")
        return 0
    RESULT_PATH.write_text(rendered)
    print(f"wrote {RESULT_PATH.relative_to(ROOT)}")
    decisions = result["prespecified_decisions"]
    print(json.dumps(decisions, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
