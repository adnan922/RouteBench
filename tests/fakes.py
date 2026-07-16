"""Test doubles shared across the test suite — no real network or API keys involved."""

from __future__ import annotations

from src.providers.base import CompletionResult


class FakeProvider:
    """Stands in for a real provider in unit tests. Returns a fixed response
    instead of calling any real API, and counts how many times it was called."""

    def __init__(
        self,
        provider_name: str,
        model: str,
        response_text: str = "Final Answer: 42",
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self._response_text = response_text
        self.call_count = 0

    def complete(self, messages: list[dict], model: str | None = None, **kwargs) -> CompletionResult:
        self.call_count += 1
        return CompletionResult(
            content=self._response_text,
            model=model or self.model,
            provider=self.provider_name,
            prompt_tokens=10,
            completion_tokens=5,
            latency_s=0.01,
        )