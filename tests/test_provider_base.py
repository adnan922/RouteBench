"""Tests for src/providers/base.py — retry/backoff and throttling logic.

Fully network-free: the underlying OpenAI client's .create() call is mocked
directly, so no real API key or network call is involved despite exercising
the actual retry/throttle code path.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest
from openai import RateLimitError

from src.providers.base import CompletionResult, OpenAICompatibleProvider


class _FakeProvider(OpenAICompatibleProvider):
    """A minimal concrete provider for testing the base class's own logic."""

    provider_name = "test"
    default_base_url = "https://fake.test/v1"
    api_key_env_var = "TEST_API_KEY"
    model_env_var = "TEST_MODEL"
    fallback_model = "test-model"
    default_min_interval_s = 0.0  # no throttling unless a test explicitly sets it


def _make_rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://fake.test/v1/chat/completions")
    response = httpx.Response(
        status_code=429, request=request, json={"error": {"message": "rate limited"}}
    )
    return RateLimitError("Rate limit exceeded", response=response, body=None)


def _make_success_response(content: str = "hello") -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    response.usage = MagicMock(prompt_tokens=5, completion_tokens=3)
    return response


class TestRetryOnRateLimit:
    def test_succeeds_after_one_rate_limit_error(self):
        provider = _FakeProvider(api_key="fake-key")
        provider.initial_backoff_s = 0.01  # keep the test fast
        provider._client.chat.completions.create = MagicMock(
            side_effect=[_make_rate_limit_error(), _make_success_response("ok")]
        )

        result = provider.complete([{"role": "user", "content": "hi"}])

        assert isinstance(result, CompletionResult)
        assert result.content == "ok"
        assert provider._client.chat.completions.create.call_count == 2

    def test_raises_after_exhausting_retries(self):
        provider = _FakeProvider(api_key="fake-key")
        provider.initial_backoff_s = 0.01
        provider.max_retries = 2
        provider._client.chat.completions.create = MagicMock(
            side_effect=[_make_rate_limit_error() for _ in range(10)]
        )

        with pytest.raises(RateLimitError):
            provider.complete([{"role": "user", "content": "hi"}])

        assert provider._client.chat.completions.create.call_count == 3  # initial attempt + 2 retries

    def test_no_retry_needed_on_first_success(self):
        provider = _FakeProvider(api_key="fake-key")
        provider._client.chat.completions.create = MagicMock(
            return_value=_make_success_response("first try")
        )

        result = provider.complete([{"role": "user", "content": "hi"}])

        assert result.content == "first try"
        assert provider._client.chat.completions.create.call_count == 1


class TestThrottle:
    def test_throttle_enforces_minimum_interval_between_calls(self):
        provider = _FakeProvider(api_key="fake-key")
        provider.min_interval_s = 0.05
        provider._client.chat.completions.create = MagicMock(return_value=_make_success_response())

        start = time.monotonic()
        provider.complete([{"role": "user", "content": "first"}])
        provider.complete([{"role": "user", "content": "second"}])
        elapsed = time.monotonic() - start

        assert elapsed >= 0.05

    def test_no_throttle_when_min_interval_is_zero(self):
        provider = _FakeProvider(api_key="fake-key")
        provider.min_interval_s = 0.0
        provider._client.chat.completions.create = MagicMock(return_value=_make_success_response())

        start = time.monotonic()
        for _ in range(5):
            provider.complete([{"role": "user", "content": "x"}])
        elapsed = time.monotonic() - start

        assert elapsed < 0.05  # near-instant with no throttling

    def test_min_interval_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "fake-key")
        monkeypatch.setenv("TEST_MIN_INTERVAL_S", "3.5")

        class _EnvConfiguredProvider(_FakeProvider):
            min_interval_env_var = "TEST_MIN_INTERVAL_S"

        provider = _EnvConfiguredProvider()

        assert provider.min_interval_s == 3.5

    def test_explicit_min_interval_beats_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_MIN_INTERVAL_S", "3.5")

        class _EnvConfiguredProvider(_FakeProvider):
            min_interval_env_var = "TEST_MIN_INTERVAL_S"

        provider = _EnvConfiguredProvider(api_key="fake-key", min_interval_s=0.2)

        assert provider.min_interval_s == 0.2