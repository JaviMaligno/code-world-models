"""Azure OpenAI implementation of LLMProvider."""
from .provider import Completion, Usage

class AzureOpenAIProvider:
    # Long synthesis sweeps issue thousands of serial calls; the SDK default of
    # max_retries=2 is not enough to ride out sustained 429s. The openai SDK
    # already does exponential backoff and honours the Retry-After header, so we
    # just raise the ceiling and lengthen the per-request timeout. Both are
    # overridable for callers that want different behaviour.
    def __init__(self, endpoint: str, api_key: str, api_version: str,
                 max_retries: int = 6, timeout: float = 120.0):
        from openai import AzureOpenAI  # lazy import so tests don't need the dep wired
        self._client = AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version,
            max_retries=max_retries, timeout=timeout,
        )

    def complete(self, messages: list[dict], model: str) -> Completion:
        # NOTE: no temperature/top_p — GPT-5.4 rejects them.
        resp = self._client.chat.completions.create(model=model, messages=messages)
        if not resp.choices:
            raise ValueError("Azure OpenAI returned no choices (possibly content-filtered)")
        u = resp.usage
        if u is None:
            raise ValueError("Azure OpenAI returned no usage metadata")
        return Completion(
            text=resp.choices[0].message.content or "",
            usage=Usage(prompt_tokens=u.prompt_tokens,
                        completion_tokens=u.completion_tokens),
        )
