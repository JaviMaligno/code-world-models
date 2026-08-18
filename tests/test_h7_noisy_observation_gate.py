"""Tests for the pre-specified H7 bounded-observation-noise extension."""
import hashlib
import importlib.util
import json
import math
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/h7_noisy_observation_gate.py"
SPEC = importlib.util.spec_from_file_location("h7_noisy_gate", SCRIPT)
H7 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(H7)


def test_scalar_overlap_probability_covers_edges_and_interior():
    assert H7.scalar_overlap_probability(0.0, 0.0) == 1.0
    assert H7.scalar_overlap_probability(0.1, 0.0) == 0.0
    assert H7.scalar_overlap_probability(0.0, 0.5) == 1.0
    assert H7.scalar_overlap_probability(0.5, 0.5) == pytest.approx(0.5)
    assert H7.scalar_overlap_probability(1.0, 0.5) == 0.0
    assert H7.scalar_overlap_probability(2.0, 0.5) == 0.0
    with pytest.raises(ValueError):
        H7.scalar_overlap_probability(0.0, -0.1)


def test_block_overlap_multiplies_scalar_support_overlaps():
    rows = [(0.0, 0.5), (0.25,)]
    assert H7.block_overlap_probability(rows, 0.5) == pytest.approx(
        1.0 * 0.5 * 0.75)


def test_clopper_pearson_boundary_closed_forms():
    alpha = 0.05
    n = 200
    lo0, hi0 = H7.clopper_pearson(0, n, alpha)
    lon, hin = H7.clopper_pearson(n, n, alpha)
    assert lo0 == 0.0
    assert hi0 == pytest.approx(1.0 - (alpha / 2.0) ** (1.0 / n), abs=1e-12)
    assert lon == pytest.approx((alpha / 2.0) ** (1.0 / n), abs=1e-12)
    assert hin == 1.0


@pytest.fixture(scope="module")
def artifacts():
    prespec = json.loads((ROOT / "results/h7_noisy_gate_prespec_v1.json").read_text())
    committed = json.loads(
        (ROOT / "results/h7_noisy_observation_gate_v1.json").read_text())
    regenerated = H7.run_experiment(prespec)
    return prespec, committed, regenerated


def _deep_close(a, b, path="", rel=1e-9, abs_tol=1e-12):
    """Structure, strings, ints and None must match exactly; floats to 1e-9
    relative.  Exact float equality is a same-machine property (libm last-ulp
    differences across platforms), not an invariant of the computation."""
    if isinstance(a, bool) or isinstance(b, bool):
        assert a == b, f"{path}: {a!r} != {b!r}"
    elif isinstance(a, float) or isinstance(b, float):
        assert isinstance(a, (int, float)) and isinstance(b, (int, float)), path
        assert a == pytest.approx(b, rel=rel, abs=abs_tol), f"{path}: {a} != {b}"
    elif isinstance(a, dict):
        assert isinstance(b, dict) and sorted(a) == sorted(b), path
        for k in a:
            _deep_close(a[k], b[k], f"{path}/{k}", rel, abs_tol)
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _deep_close(x, y, f"{path}[{i}]", rel, abs_tol)
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


def test_prespec_hash_schema_and_stored_result_are_fresh(artifacts):
    prespec, committed, regenerated = artifacts
    expected_hash = hashlib.sha256(H7.canonical_bytes(prespec)).hexdigest()
    assert committed["prespec_sha256"] == expected_hash
    assert committed["schema_version"] == "h7-noisy-observation-gate-result-v1"
    _deep_close(committed, regenerated)


def test_truth_always_passes_bounded_support_gate(artifacts):
    _, committed, _ = artifacts
    assert all(level["truth"]["passes"] == committed["n_blocks"]
               for level in committed["levels"])
    assert all(level["truth"]["pass_rate"] == 1.0
               for level in committed["levels"])


def test_eta_zero_is_exactly_the_no_mode_block_fraction(artifacts):
    _, committed, _ = artifacts
    zero = committed["levels"][0]
    no_mode = committed["latent_panel"]["blocks_without_mode"]
    assert zero["blind"]["passes"] == no_mode
    assert zero["blind"]["analytic_conditional_pass_probability"] == (
        no_mode / committed["n_blocks"])


def test_empirical_noise_draws_match_analytic_law_with_familywise_bound(artifacts):
    """Hoeffding applies to independent, non-identical block Bernoullis."""
    prespec, committed, _ = artifacts
    levels = committed["levels"]
    alpha = prespec["analysis"]["alpha"]
    n = committed["n_blocks"]
    radius = math.sqrt(math.log(2.0 * len(levels) / alpha) / (2.0 * n))
    for level in levels:
        empirical = level["blind"]["empirical_pass_rate"]
        analytic = level["blind"]["analytic_conditional_pass_probability"]
        assert abs(empirical - analytic) <= radius


def test_prespecified_primary_and_boundary_are_reported(artifacts):
    prespec, committed, _ = artifacts
    decision = committed["prespecified_decisions"]
    assert decision["primary_eta"] == prespec["analysis"]["primary_eta"]
    assert decision["primary_criterion_met"]
    assert decision["first_boundary_eta"] in prespec["observation_model"]["eta_levels"]
