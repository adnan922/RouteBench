"""Shared thin wrapper around any OpenAI-compatible chat completions endpoint.

Groq and SambaNova Cloud both expose an OpenAI-compatible /v1/chat/completions
endpoint (confirmed against their current docs — see groq_client.py and
sambanova_client.py), so one base class covers both providers. Each subclass
just sets a base_url, an API key env var, and a default model.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class CompletionResult:
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float


class OpenAICompatibleProvider:
    """Base class for any provider reachable via the OpenAI client + a base_url swap."""

    provider_name: str = "unknown"
    default_base_url: str = ""
    api_key_env_var: str = ""
    model_env_var: str = ""
    fallback_model: str = ""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = base_url or self.default_base_url
        resolved_key = api_key or os.environ.get(self.api_key_env_var)
        if not resolved_key:
            raise RuntimeError(
                f"{self.api_key_env_var} is not set. Copy .env.example to .env "
                f"and fill in your {self.provider_name} key."
            )
        self.model = model or os.environ.get(self.model_env_var, self.fallback_model)
        self._client = OpenAI(base_url=self.base_url, api_key=resolved_key)

    def complete(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> CompletionResult:
        """Send a chat completion request and return a normalized result.

        Extra kwargs (temperature, max_tokens, tools, etc.) pass straight through
        to the underlying API call.
        """
        resolved_model = model or self.model
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=resolved_model, messages=messages, **kwargs
        )
        latency_s = time.perf_counter() - start

        choice = response.choices[0]
        usage = getattr(response, "usage", None)

        return CompletionResult(
            content=choice.message.content or "",
            model=resolved_model,
            provider=self.provider_name,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            latency_s=latency_s,
        )
