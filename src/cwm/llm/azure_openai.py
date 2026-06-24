"""Azure OpenAI implementation of LLMProvider."""
from .provider import Completion, Usage

class AzureOpenAIProvider:
    def __init__(self, endpoint: str, api_key: str, api_version: str):
        from openai import AzureOpenAI  # lazy import so tests don't need the dep wired
        self._client = AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version
        )

    def complete(self, messages: list[dict], model: str) -> Completion:
        # NOTE: no temperature/top_p — GPT-5.4 rejects them.
        resp = self._client.chat.completions.create(model=model, messages=messages)
        u = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            usage=Usage(prompt_tokens=u.prompt_tokens,
                        completion_tokens=u.completion_tokens),
        )
