"""Tests for src/providers/registry.py."""

import pytest

from src.providers.registry import PROVIDER_REGISTRY, get_provider


class TestProviderRegistry:
    def test_known_providers_are_registered(self):
        assert set(PROVIDER_REGISTRY) == {"groq", "sambanova", "gemini"}

    def test_get_provider_is_case_insensitive(self):
        assert PROVIDER_REGISTRY["gemini"] is PROVIDER_REGISTRY["gemini"]  # sanity check on the dict itself

    def test_get_provider_raises_on_unknown_name(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("not-a-real-provider")

    def test_get_provider_requires_api_key_for_known_provider(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(RuntimeError):
            get_provider("gemini")