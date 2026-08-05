"""Prompt-variant isolation for scripts/continuous_danger_synthesis.py.

Two things must hold at once for the confound-closure arms to mean anything.

(1) The 'default' variant must reproduce the prompt of every committed run
    BYTE FOR BYTE. tests/test_continuous_contract.py already asserts that the
    empty-guidance path is byte-identical; this file asserts the stronger
    statement the paper actually relies on -- that the *variant table entry*
    named 'default' is that empty-guidance path, in all three of its knobs
    (max_examples, max_failures, guidance), for the synthesis message AND the
    refine message.

(2) Each non-default variant must add exactly the intervention it claims and
    nothing else. The new 'landing' variant (review point #4's second
    confound: 36/40 guided PatchField2D artifacts conditioned the freeze rule
    on the CURRENT position instead of the LANDING position) must therefore be
    'region' plus one sentence naming only the trigger's ARGUMENT -- it must
    not leak the region's shape, centre, radius, or count, otherwise a
    landing-arm repair would prove nothing.

Everything here runs offline with FakeProvider (no network, no Azure).
"""
import importlib.util
import json
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "continuous_danger_synthesis.py"
_spec = importlib.util.spec_from_file_location("cds_prompt_variants_mod", _SCRIPT)
synth_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(synth_mod)   # name != "__main__" -> no argparse/CLI

from cwm.continuous.contract import (build_contract, build_synthesis_messages,
                                     collect_transitions, refine_continuous,
                                     sample_contains_mode,
                                     synthesize_and_evaluate)
from cwm.continuous.envs import CartWall, PatchField2D
from cwm.llm.provider import FakeProvider

VARIANTS = synth_mod.PROMPT_VARIANTS
P2D = PatchField2D()          # the instrument the landing variant targets
CART = CartWall(x_wall=8.0)


class _CapturingProvider:
    """FakeProvider that records every message list it was handed."""

    def __init__(self, replies):
        self._inner = FakeProvider(replies)
        self.calls = []

    def complete(self, messages, model):
        self.calls.append(messages)
        return self._inner.complete(messages, model=model)


# --- (1) 'default' is the original prompt, byte for byte -------------------

def test_default_variant_entry_is_the_original_prompt_byte_for_byte():
    v = VARIANTS["default"]
    assert (v["max_examples"], v["max_failures"], v["guidance"]) == (30, 20, "")
    tr = collect_transitions(P2D, n_rollouts=2, seed=0)
    contract = build_contract(P2D, include_mode=False)
    original = build_synthesis_messages(contract, tr)      # no kwargs at all
    via_variant = build_synthesis_messages(
        contract, tr, v["max_examples"], guidance=v["guidance"])
    assert via_variant == original


def test_default_variant_refine_message_is_the_original_refine_message():
    """The refine message is the other half of the protocol; the default
    variant must not perturb it either. Compared by driving refine_continuous
    twice on the SAME failing artifact -- once with the variant's knobs, once
    with no knobs -- and diffing the captured user messages."""
    near = CartWall(x_wall=0.5)          # wall fires inside a short sample
    tr = collect_transitions(near, n_rollouts=6, seed=0)
    assert sample_contains_mode(tr), "sample must contain a mode contact"
    bad = "def step(state, action):\n    return [0.0, 0.0]\ndef reward(state):\n    return 0.0\n"
    contract = build_contract(near, include_mode=False)
    v = VARIANTS["default"]
    msgs = []
    for kwargs in ({}, {"guidance": v["guidance"],
                        "max_failures": v["max_failures"]}):
        p = _CapturingProvider([f"```python\n{bad}```"])
        res = refine_continuous(p, "fake", contract, bad, tr, eps=1e-9,
                                max_iters=1, **kwargs)
        assert res.iterations == 1, "the refine branch must actually run"
        msgs.append(p.calls[0])
    assert msgs[0] == msgs[1]


# --- (2) the 'landing' variant adds exactly one sentence ------------------

def test_landing_is_region_plus_exactly_one_appended_sentence():
    reg, land = VARIANTS["region"], VARIANTS["landing"]
    assert (land["max_examples"], land["max_failures"]) == \
           (reg["max_examples"], reg["max_failures"]) == (120, 40)
    assert land["guidance"].startswith(reg["guidance"] + "\n\n")
    delta = land["guidance"][len(reg["guidance"]) + 2:]
    assert delta, "the landing variant must actually add text"
    # exactly one sentence: one terminal period, no internal sentence break,
    # no extra paragraphs.
    assert delta.endswith(".") and "." not in delta[:-1]
    assert "\n" not in delta


def test_landing_sentence_names_the_variable_and_not_the_geometry():
    """The whole point of the arm: it removes the variable-identification
    confound WITHOUT revealing the answer. So the sentence must mention the
    landing coordinates and must not mention the region's shape, centre,
    radius or count."""
    reg, land = VARIANTS["region"]["guidance"], VARIANTS["landing"]["guidance"]
    delta = land[len(reg) + 2:]
    low = delta.lower()
    assert "x2" in delta and "y2" in delta          # the causal variable
    assert "landing" in low
    for banned in ("disc", "circle", "circular", "radius", "radial", "sphere",
                   "square", "half-side", "chebyshev", "slab", "ellipse",
                   "rectangle", "centre", "center", "two ", "both ",
                   "quadratic", "hypot", "**2"):
        assert banned not in low, f"landing sentence leaks {banned!r}"
    # no numeric constant of the truth may appear anywhere in the guidance
    for const in {str(P2D.p1[0]), str(P2D.p1[1]), str(P2D.p2[0]),
                  str(P2D.R), str(P2D.R ** 2), str(P2D.slab_half_width)}:
        assert const not in land, f"landing guidance leaks the constant {const}"


def test_landing_guidance_shares_no_line_with_the_full_arm_mode_clause():
    """Independent leak check: whatever the full (mode-stating) contract says
    that the incomplete contract does not is exactly the answer. No such line
    may appear in the guidance of any variant."""
    full = build_contract(P2D, include_mode=True)
    inc_lines = {ln.strip() for ln in build_contract(
        P2D, include_mode=False).splitlines()}
    secret = [ln.strip() for ln in full.splitlines()
              if ln.strip() and ln.strip() not in inc_lines]
    assert len(secret) >= 5, "the mode clause must be non-empty (non-vacuous)"
    assert any("radius R" in ln for ln in secret)   # it really is the answer
    for name, v in VARIANTS.items():
        for ln in secret:
            assert ln not in v["guidance"], f"{name} leaks {ln!r}"


def test_landing_guidance_inserts_cleanly_into_both_messages():
    """Non-vacuous end-to-end: the sentence reaches the synthesis message and
    the refine message, and NOTHING ELSE moves in either."""
    tr = collect_transitions(P2D, n_rollouts=3, seed=0)
    contract = build_contract(P2D, include_mode=False)
    v = VARIANTS["landing"]
    base = build_synthesis_messages(contract, tr, v["max_examples"])
    rich = build_synthesis_messages(contract, tr, v["max_examples"],
                                    guidance=v["guidance"])
    assert rich[0] == base[0]                       # system message untouched
    assert v["guidance"] in rich[1]["content"]
    assert rich[1]["content"].replace(v["guidance"] + "\n\n", "") == \
        base[1]["content"]
    # the contract itself never sees the guidance
    assert v["guidance"] not in contract

    near = CartWall(x_wall=0.5)
    tr2 = collect_transitions(near, n_rollouts=6, seed=0)
    assert sample_contains_mode(tr2)
    bad = "def step(state, action):\n    return [0.0, 0.0]\ndef reward(state):\n    return 0.0\n"
    c2 = build_contract(near, include_mode=False)
    p = _CapturingProvider([f"```python\n{bad}```"])
    res = refine_continuous(p, "fake", c2, bad, tr2, eps=1e-9, max_iters=1,
                            guidance=v["guidance"],
                            max_failures=v["max_failures"])
    assert res.iterations == 1
    msg = p.calls[0][0]["content"]
    assert msg.rstrip().endswith(v["guidance"])
    body = msg.split("FAILURES (expected vs got):\n")[1]
    body = body.split("\n\n" + v["guidance"])[0]
    assert len(body.splitlines()) <= v["max_failures"]


def test_every_variant_is_reachable_from_the_cli():
    ap = synth_mod.build_parser()
    choices = {a.dest: a.choices for a in ap._actions if a.choices}
    assert set(choices["prompt_variant"]) == set(VARIANTS)
    assert "landing" in choices["prompt_variant"]
    assert "slab" in choices["patch_shape"]
    args = ap.parse_args(["mini", "2", "--instrument", "patch2d",
                          "--patch-shape", "slab",
                          "--prompt-variant", "landing"])
    assert (args.patch_shape, args.prompt_variant) == ("slab", "landing")
    # the output filename must not collide with the disc/square campaigns
    tags = {"disc": "patch2d_", "square": "patch2dsq_", "slab": "patch2dslab_"}
    assert len(set(tags.values())) == 3


# --- the protocol fact this task publishes: calls per seed ----------------

_FULL_CART = """\
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
"""
_BAD_CART = "def step(state, action):\n    return [0.0, 0.0]\ndef reward(state):\n    return 0.0\n"


@pytest.mark.parametrize("n_bad", [0, 1, 3])
def test_llm_calls_per_seed_is_one_plus_refine_iterations(n_bad):
    """PROTOCOL-FACTS.md states calls_per_seed = 1 + refine_iterations. Verify
    it against the actual number of provider.complete() invocations, for a
    first-try success and for artifacts that need refinement."""
    replies = [f"```python\n{_BAD_CART}```"] * n_bad + \
              [f"```python\n{_FULL_CART}```"]
    p = _CapturingProvider(replies)
    cell = synthesize_and_evaluate(p, "fake", CART, include_mode=True,
                                   n_rollouts=2, seed=10_000, eps=1e-9,
                                   max_iters=5)
    assert cell["gate_passed"], "the success branch must be reached"
    assert cell["refine_iterations"] == n_bad
    assert len(p.calls) == 1 + cell["refine_iterations"]
    # memoryless: the synthesis call carries system+user, every refine call
    # carries exactly ONE user message and no history.
    assert [m["role"] for m in p.calls[0]] == ["system", "user"]
    for call in p.calls[1:]:
        assert [m["role"] for m in call] == ["user"]


def test_llm_calls_per_seed_is_capped_by_max_iters():
    p = _CapturingProvider([f"```python\n{_BAD_CART}```"] * 3)
    cell = synthesize_and_evaluate(p, "fake", CART, include_mode=True,
                                   n_rollouts=2, seed=10_000, eps=1e-9,
                                   max_iters=2)
    assert not cell["gate_passed"], "the exhausted branch must be reached"
    assert cell["refine_iterations"] == 2
    assert len(p.calls) == 3          # 1 synthesis + max_iters refinements


# --- oracle for results/llm_protocol_facts.json ---------------------------

_FACTS = _REPO / "results" / "llm_protocol_facts.json"


def test_protocol_facts_json_matches_an_independent_recount():
    """Brute-force oracle: re-derive the published call totals straight from
    the campaign JSONs with a loop written here, importing NOTHING from the
    script that produced the file."""
    if not _FACTS.exists():
        pytest.skip("results/llm_protocol_facts.json not generated yet")
    facts = json.loads(_FACTS.read_text())
    total = 0
    n_cells = 0
    for camp in facts["campaigns"]:
        path = _REPO / camp["path"]
        cells = json.loads(path.read_text())["cells"]
        calls = [1 + c["refine_iterations"] for c in cells]
        assert camp["n_cells"] == len(calls)
        assert camp["llm_calls_total"] == sum(calls)
        assert camp["llm_calls_min"] == min(calls)
        assert camp["llm_calls_max"] == max(calls)
        srt = sorted(calls)
        med = (srt[len(srt) // 2] if len(srt) % 2
               else (srt[len(srt) // 2 - 1] + srt[len(srt) // 2]) / 2)
        assert camp["llm_calls_median"] == med
        total += sum(calls)
        n_cells += len(calls)
    assert facts["totals"]["llm_calls_all_campaigns"] == total
    assert facts["totals"]["n_cells_all_campaigns"] == n_cells
    assert total > 0 and n_cells > 0


def test_protocol_facts_doc_quotes_the_live_prompt_text():
    """The appendix fragment must stay in sync with the code: the exact system
    message and the refine message's fixed phrases are quoted there, so a
    prompt edit that forgets the doc fails here."""
    doc = (_REPO / "docs" / "paper2" / "PROTOCOL-FACTS.md")
    if not doc.exists():
        pytest.skip("PROTOCOL-FACTS.md not written yet")
    text = doc.read_text()
    tr = collect_transitions(CART, n_rollouts=1, seed=0)
    msgs = build_synthesis_messages(build_contract(CART, include_mode=False), tr)
    system = msgs[0]["content"]
    assert system in text, "system message not quoted verbatim"
    for phrase in ("Here are observed transitions (ground truth) to match exactly:",
                   "Output only one ```python code block.",
                   "FAILURES (expected vs got):",
                   "The current implementation is below."):
        assert phrase in text, f"missing protocol phrase {phrase!r}"
