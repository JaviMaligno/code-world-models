"""Resumability of scripts/continuous_danger_synthesis.py's per-seed
synthesis sweep (offline, FakeProvider -- no Azure/network calls).

Hard project rule: any long-running / money-costing run must checkpoint per
unit and resume, so a killed run never re-spends Azure money redoing
completed seeds. This exercises run_synthesis() -- the module's per-(arm,
seed) loop, extracted so it's importable and testable without triggering
the script's CLI/credential-requiring __main__ block."""
import importlib.util
import json
import pathlib

import pytest

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "continuous_danger_synthesis.py"
_spec = importlib.util.spec_from_file_location("continuous_danger_synthesis_mod", _SCRIPT)
synth_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(synth_mod)   # module name != "__main__" -> no argparse/CLI runs

from cwm.continuous.envs import CartWall
from cwm.llm.provider import FakeProvider

# Same hand-written full-spec artifact as tests/test_continuous_contract.py:
# float-exact against CartWall's integrator, so the gate passes on the very
# first synthesis call (0 refine iterations) -> exactly 1 provider.complete()
# call per seed. That makes "was this seed re-synthesized?" directly
# observable via FakeProvider's canned-response count (IndexError if a
# skipped seed is redone, since there'd be no response left for it).
FULL_CODE = '''\
import math
def step(state, action):
    x, v = state
    a = max(-1.0, min(1.0, action))
    v2 = v + (3.0 * a - 0.3 * v) * 0.1
    x2 = x + v2 * 0.1
    if x2 >= 8.0:
        return [8.0, 0.0]
    return [x2, v2]
def reward(state):
    x = state[0]
    left = 0.3 / (1.0 + math.exp(-((-6.0 - x) / 0.5)))
    right = 1.0 / (1.0 + math.exp(-((x - 12.0) / 0.5)))
    return left + right
'''
RESPONSE = f"```python\n{FULL_CODE}```"

ENV = CartWall(x_wall=8.0)
N_SEEDS = 3
META = {"script": "continuous_danger_synthesis.py", "model": "fake",
        "size": "mini", "tag": "mini", "params": {"n_seeds": N_SEEDS}}


def _run(provider, out_path):
    return synth_mod.run_synthesis(
        provider, "fake", ENV, ["full"], N_SEEDS, out_path,
        n_rollouts=3, eps=1e-9, max_iters=5, play_episodes=1,
        j_truth=1.0, j_random=0.0, meta=META)


def test_fresh_run_produces_all_seeds_and_expected_schema(tmp_path):
    out = tmp_path / "out.json"
    results = _run(FakeProvider([RESPONSE] * N_SEEDS), out)

    assert set(results.keys()) == {
        "script", "model", "size", "tag", "params", "j_truth", "j_random",
        "cells", "elapsed_s"}
    assert list(results.keys())[:5] == ["script", "model", "size", "tag", "params"]
    assert {(c["arm"], c["seed"] // 10_000 - 1) for c in results["cells"]} == {
        ("full", 0), ("full", 1), ("full", 2)}
    expected_cell_keys = {
        "arm", "seed", "n_rollouts", "eps", "sample_contains_wall",
        "gate_accuracy", "gate_passed", "refine_iterations", "wall_blindness",
        "code", "j_play", "play_cost", "play_contact_rate"}
    for c in results["cells"]:
        assert set(c.keys()) == expected_cell_keys
        assert c["gate_passed"] and c["refine_iterations"] == 0

    # atomic write: no stray temp file left behind
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.json"]


def test_resume_skips_completed_seeds_and_completes_the_rest(tmp_path):
    out = tmp_path / "out.json"

    # Uninterrupted reference run: 3 seeds, one provider response per seed.
    reference = _run(FakeProvider([RESPONSE] * N_SEEDS), out)
    ref_by_seed = {c["seed"] // 10_000 - 1: c for c in reference["cells"]}
    out.unlink()

    # Simulate a kill after seed 1: pre-seed a checkpoint with only seeds
    # 0 and 1 (byte-identical cells to the reference run).
    partial = dict(META)
    partial["j_truth"] = 1.0
    partial["j_random"] = 0.0
    partial["cells"] = [ref_by_seed[0], ref_by_seed[1]]
    out.write_text(json.dumps(partial, indent=2))

    # Only ONE canned response available: if the resumed run re-synthesizes
    # seed 0 or 1 instead of skipping them, FakeProvider raises IndexError
    # (exhausted) before ever reaching seed 2 -- the test would fail loudly.
    resumed = _run(FakeProvider([RESPONSE]), out)

    got = {c["seed"] // 10_000 - 1: c for c in resumed["cells"]}
    assert set(got) == {0, 1, 2}
    # seeds 0/1 were NOT re-synthesized: identical cell contents (same code,
    # same gate stats) to the uninterrupted reference run.
    assert got[0] == ref_by_seed[0]
    assert got[1] == ref_by_seed[1]
    assert got[2]["gate_passed"] and got[2]["arm"] == "full"

    # atomic write: no stray temp file left behind after the resumed run
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.json"]


def test_resumed_run_provider_exhaustion_if_it_wrongly_redoes_a_seed(tmp_path):
    """Negative control: confirms the FakeProvider-exhaustion trip-wire above
    actually fires, i.e. it isn't a silent no-op guard. A provider with only
    one response, fed to a run that (incorrectly) tries to redo 2 seeds,
    must raise."""
    out = tmp_path / "out.json"
    with pytest.raises(IndexError):
        synth_mod.run_synthesis(
            FakeProvider([RESPONSE]), "fake", ENV, ["full"], 2, out,
            n_rollouts=3, eps=1e-9, max_iters=5, play_episodes=1,
            j_truth=1.0, j_random=0.0, meta=META)


def test_atomic_write_helper_leaves_no_tmp_on_success(tmp_path):
    out = tmp_path / "atomic.json"
    synth_mod._atomic_write_json(out, {"a": 1})
    assert out.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["atomic.json"]
    assert json.loads(out.read_text()) == {"a": 1}
