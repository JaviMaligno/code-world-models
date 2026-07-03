# src/cwm/llm/openai_compat.py
"""Provider for any OpenAI-compatible chat endpoint (Hugging Face Inference
Providers router, vLLM, llama.cpp server, ...). Same Completion surface as
AzureOpenAIProvider, so the synthesis/refinement pipeline runs unchanged on
non-OpenAI model families."""
from .provider import Completion, Usage


class OpenAICompatProvider:
    def __init__(self, base_url: str, api_key: str,
                 max_retries: int = 6, timeout: float = 300.0,
                 max_tokens: int = 8192):
        from openai import OpenAI  # lazy import so tests don't need the dep wired
        self._client = OpenAI(base_url=base_url, api_key=api_key,
                              max_retries=max_retries, timeout=timeout)
        self._max_tokens = max_tokens

    def complete(self, messages: list[dict], model: str) -> Completion:
        resp = self._client.chat.completions.create(
            model=model, messages=messages, max_tokens=self._max_tokens)
        if not resp.choices:
            raise ValueError("endpoint returned no choices")
        usage = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            usage=Usage(prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "completion_tokens", 0) or 0),
        )
