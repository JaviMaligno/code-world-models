from cwm.baseline import build_policy_messages, parse_action, baseline_policy
from cwm.llm.provider import FakeProvider

DESC = "You play a test game. A move is an integer."

def test_parse_plain_int():
    assert parse_action("4") == 4

def test_parse_multi_digit():
    assert parse_action("I'll play column 12") == 12

def test_parse_from_sentence():
    assert parse_action("cell 7 please") == 7

def test_parse_none_when_absent():
    assert parse_action("no number here") is None

def test_messages_include_description_and_legal():
    msgs = build_policy_messages({"board": [0]*9, "current_player": 1}, [0, 1, 2], DESC)
    blob = " ".join(m["content"] for m in msgs)
    assert "[0, 1, 2]" in blob
    assert "test game" in blob

def test_baseline_returns_action_and_usage():
    fake = FakeProvider(["I choose 3"])
    action, usage = baseline_policy(fake, "large",
                                    {"board": [0]*9, "current_player": 1}, [3, 4], DESC)
    assert action == 3 and usage.completion_tokens > 0

def test_baseline_illegal_returns_none():
    fake = FakeProvider(["I choose 8"])
    action, _ = baseline_policy(fake, "large",
                                {"board": [0]*9, "current_player": 1}, [3, 4], DESC)
    assert action is None
