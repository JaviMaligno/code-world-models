"""LLM provider abstraction + a deterministic fake for tests."""
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int

@dataclass
class Completion:
    text: str
    usage: Usage

class LLMProvider(Protocol):
    def complete(self, messages: list[dict], model: str) -> Completion: ...

class FakeProvider:
    """Returns canned responses in order. Usage approximated as word counts."""
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._i = 0

    def complete(self, messages: list[dict], model: str) -> Completion:
        text = self._responses[self._i]   # IndexError when exhausted (tested)
        self._i += 1
        prompt_words = sum(len(m["content"].split()) for m in messages)
        return Completion(
            text=text,
            usage=Usage(prompt_tokens=max(1, prompt_words),
                        completion_tokens=max(1, len(text.split()))),
        )
