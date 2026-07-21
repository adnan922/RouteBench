"""Shared thin wrapper around any OpenAI-compatible chat completions endpoint.

Groq, SambaNova Cloud, and Google AI Studio (Gemini) all expose an
OpenAI-compatible /v1/chat/completions endpoint (confirmed against each
provider's current docs — see groq_client.py, sambanova_client.py,
gemini_client.py), so one base class covers all three. Each subclass just
sets a base_url, an API key env var, and a default model.

Also handles two production-shaped realities of free-tier APIs: proactive
throttling (spacing calls out so you don't hit a rate limit in the first
place) and retry-with-backoff (recovering if you hit one anyway). Published
free-tier RPM limits vary by provider/model and shift over time, so the
throttle interval is a conservative, tunable default rather than a number
copied from any one provider's docs — tune it based on what you observe.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import OpenAI, RateLimitError


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
    min_interval_env_var: str = ""
    default_min_interval_s: float = 2.0
    max_retries: int = 5
    initial_backoff_s: float = 2.0

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        min_interval_s: float | None = None,
    ) -> None:
        self.base_url = base_url or self.default_base_url
        resolved_key = api_key or os.environ.get(self.api_key_env_var)
        if not resolved_key:
            raise RuntimeError(
                f"{self.api_key_env_var} is not set. Copy .env.example to .env "
                f"and fill in your {self.provider_name} key."
            )
        self.model = model or os.environ.get(self.model_env_var, self.fallback_model)

        if min_interval_s is not None:
            self.min_interval_s = min_interval_s
        elif self.min_interval_env_var and os.environ.get(self.min_interval_env_var):
            self.min_interval_s = float(os.environ[self.min_interval_env_var])
        else:
            self.min_interval_s = self.default_min_interval_s

        self._last_call_at: float | None = None
        self._client = OpenAI(base_url=self.base_url, api_key=resolved_key)

    def _throttle(self) -> None:
        """Sleep just long enough to keep calls at least min_interval_s apart."""
        if self.min_interval_s <= 0 or self._last_call_at is None:
            return
        elapsed = time.monotonic() - self._last_call_at
        remaining = self.min_interval_s - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def complete(
        self, messages: list[dict], model: str | None = None, **kwargs
    ) -> CompletionResult:
        """Send a chat completion request and return a normalized result.

        Extra kwargs (temperature, max_tokens, tools, etc.) pass straight
        through to the underlying API call. Retries on a rate-limit response
        with exponential backoff (up to max_retries times) in addition to
        the proactive throttling above — belt and suspenders, since free-tier
        limits get hit in practice no matter how conservative the estimate.
        """
        resolved_model = model or self.model
        backoff = self.initial_backoff_s
        last_error: RateLimitError | None = None

        for attempt in range(self.max_retries + 1):
            self._throttle()
            self._last_call_at = time.monotonic()
            start = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=resolved_model, messages=messages, **kwargs
                )
            except RateLimitError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                continue

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

        raise last_error