from cwm.baseline import build_policy_messages, parse_action, baseline_policy
from cwm.llm.provider import FakeProvider

def test_parse_plain_int():
    assert parse_action("4") == 4

def test_parse_from_sentence():
    assert parse_action("I'll play cell 7 because...") == 7

def test_parse_none_when_absent():
    assert parse_action("no number here") is None

def test_messages_mention_legal_actions():
    msgs = build_policy_messages({"board": [0]*9, "current_player": 1}, [0, 1, 2])
    assert "[0, 1, 2]" in " ".join(m["content"] for m in msgs)

def test_baseline_returns_action_and_usage():
    fake = FakeProvider(["I choose 3"])
    action, usage = baseline_policy(fake, "large",
                                    {"board": [0]*9, "current_player": 1}, [3, 4])
    assert action == 3 and usage.completion_tokens > 0

def test_baseline_illegal_returns_none():
    fake = FakeProvider(["I choose 8"])   # 8 not in legal
    action, _ = baseline_policy(fake, "large",
                                {"board": [0]*9, "current_player": 1}, [3, 4])
    assert action is None
