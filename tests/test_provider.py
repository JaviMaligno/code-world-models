# tests/test_provider.py
from cwm.llm.provider import FakeProvider, Usage, Completion

def test_fake_returns_in_order():
    p = FakeProvider(["a", "b"])
    assert p.complete([{"role": "user", "content": "x"}], model="m").text == "a"
    assert p.complete([{"role": "user", "content": "y"}], model="m").text == "b"

def test_fake_tracks_usage_nonzero():
    p = FakeProvider(["hello world"])
    c = p.complete([{"role": "user", "content": "hi"}], model="m")
    assert isinstance(c, Completion) and isinstance(c.usage, Usage)
    assert c.usage.prompt_tokens > 0 and c.usage.completion_tokens > 0

def test_fake_raises_when_exhausted():
    p = FakeProvider(["only"])
    p.complete([{"role": "user", "content": "x"}], model="m")
    try:
        p.complete([{"role": "user", "content": "x"}], model="m")
        assert False, "expected StopIteration-style error"
    except IndexError:
        pass
