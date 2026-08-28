"""Ring2d support in the Claude-relay harness (scripts/continuous_claude_step.py)
must never drift from the API arm's ring2d messages
(scripts/continuous_danger_synthesis.py). This test invokes the relay
script's `init` as a subprocess (it has no importable main -- it is a
CLI-only script by design, like crossfamily_claude_step.py) and compares its
msg0.txt byte-for-byte against a reference built directly from the SAME
primitives the API arm's synthesize_and_evaluate uses: collect_transitions ->
build_contract -> resolve the per-seed guidance -> build_synthesis_messages,
reusing continuous_danger_synthesis.PROMPT_VARIANTS (not reimplemented).
"""
import math
import pathlib
import subprocess
import sys

import pytest

from cwm.continuous.contract import (
    build_contract, build_synthesis_messages, collect_transitions)
from cwm.continuous.envs import RingField2D

_REPO = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"


def _reference_msg0(seed: int, arm: str, *, gap: float, channel: str,
                    start: str, prompt_variant: str) -> str:
    """The message text scripts/continuous_danger_synthesis.py's
    synthesize_and_evaluate would build for this (seed, arm, knobs) --
    computed via the exact same functions it calls, not reimplemented."""
    sys.path.insert(0, str(_SCRIPTS))
    import continuous_danger_synthesis as danger_synthesis  # noqa: E402 (test-local, path-dependent import)

    env = RingField2D(
        gap=gap, gap_center=math.pi if channel == "facing" else 0.0,
        x0_center=(0.0, 0.0) if start == "outside" else RingField2D().center)
    transitions = collect_transitions(env, 40, seed=seed)
    contract = build_contract(env, include_mode=(arm == "full"))
    variant = danger_synthesis.PROMPT_VARIANTS[prompt_variant]
    guidance = variant["guidance"]
    if callable(guidance):
        guidance = guidance(env, transitions)
    msgs = build_synthesis_messages(contract, transitions,
                                    variant["max_examples"], guidance=guidance)
    return (f"=== SYSTEM ===\n{msgs[0]['content']}\n"
            f"=== USER ===\n{msgs[1]['content']}\n")


def _run_init(tmp_path, seed: int, *, instrument: str, arm: str,
             extra_args: list) -> str:
    before = set(tmp_path.glob(f"*_seed{seed}_msg0.txt"))
    cmd = [sys.executable, str(_SCRIPTS / "continuous_claude_step.py"),
           "init", str(seed), str(tmp_path),
           "--instrument", instrument, "--arm", arm, *extra_args]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO)
    assert result.returncode == 0, result.stderr
    after = set(tmp_path.glob(f"*_seed{seed}_msg0.txt"))
    new_files = after - before
    assert len(new_files) == 1, (result.stdout, result.stderr, list(tmp_path.iterdir()))
    return next(iter(new_files)).read_text()


@pytest.mark.parametrize("gap,channel,start,prompt_variant,arm", [
    (0.0, "facing", "outside", "default", "incomplete"),   # cell A
    (0.0, "facing", "inside", "tda", "incomplete"),         # cell D
])
def test_ring2d_relay_init_matches_api_arm_messages(
        tmp_path, gap, channel, start, prompt_variant, arm):
    seed = 30000
    extra = ["--gap", str(gap), "--channel", channel, "--start", start,
             "--prompt-variant", prompt_variant]
    got = _run_init(tmp_path, seed, instrument="ring2d", arm=arm,
                    extra_args=extra)
    want = _reference_msg0(seed, arm, gap=gap, channel=channel, start=start,
                           prompt_variant=prompt_variant)
    assert got == want


def test_ring2d_filename_tag_does_not_collide_with_cart_or_pendulum(tmp_path):
    """Different ring2d knobs, and cart/pendulum, must land on distinct
    msg0 filenames within the same OUTDIR (the collision this feature adds
    tagging to prevent)."""
    seed = 12345
    _run_init(tmp_path, seed, instrument="cart", arm="incomplete",
             extra_args=[])
    _run_init(tmp_path, seed, instrument="ring2d", arm="incomplete",
             extra_args=["--gap", "0.0"])
    _run_init(tmp_path, seed, instrument="ring2d", arm="incomplete",
             extra_args=["--gap", "0.0", "--start", "inside",
                         "--prompt-variant", "tda"])
    names = sorted(p.name for p in tmp_path.glob(f"*_seed{seed}_msg0.txt"))
    assert len(names) == 3, names


def test_cart_relay_init_unchanged_by_ring2d_support(tmp_path):
    """cart/pendulum must stay byte-identical: --prompt-variant is forced to
    'default' for them, which resolves to the exact hardcoded values
    (max_examples=30, guidance='') this script always used."""
    seed = 999
    got = _run_init(tmp_path, seed, instrument="cart", arm="incomplete",
                    extra_args=[])
    from cwm.continuous.envs import CartWall
    env = CartWall(x_wall=8.0)
    transitions = collect_transitions(env, 40, seed=seed)
    contract = build_contract(env, include_mode=False)
    msgs = build_synthesis_messages(contract, transitions)
    want = (f"=== SYSTEM ===\n{msgs[0]['content']}\n"
            f"=== USER ===\n{msgs[1]['content']}\n")
    assert got == want
