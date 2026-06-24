# tests/test_synthesizer.py
from cwm.synthesizer import build_synthesis_messages, extract_code, synthesize_cwm
from cwm.llm.provider import FakeProvider
from cwm.world_model import CONTRACT_TEXT
from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories

def test_messages_include_contract_and_examples():
    traj = collect_trajectories(g, n_games=2, seed=1)
    msgs = build_synthesis_messages(CONTRACT_TEXT, traj, max_examples=5)
    blob = " ".join(m["content"] for m in msgs)
    assert "initial_state" in blob          # contract present
    assert "current_player" in blob         # example states present
    assert msgs[-1]["role"] == "user"

def test_extract_code_from_fence():
    text = "Sure:\n```python\ndef f():\n    return 1\n```\nDone."
    assert extract_code(text) == "def f():\n    return 1"

def test_extract_code_without_fence_returns_text():
    assert extract_code("def f():\n    return 1").startswith("def f")

def test_synthesize_returns_code_and_usage():
    traj = collect_trajectories(g, n_games=1, seed=1)
    fake = FakeProvider(["```python\ndef initial_state():\n    return {}\n```"])
    code, usage = synthesize_cwm(fake, "nano", CONTRACT_TEXT, traj)
    assert "def initial_state" in code
    assert usage.completion_tokens > 0
