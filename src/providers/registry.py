"""Provider registry — maps a short name to its provider class, so which
provider plays "cheap" and which plays "expensive" can be swapped by
environment variable instead of by editing code.

Usage: get_provider("gemini") instead of `from src.providers import GeminiProvider; GeminiProvider()`.
"""

from __future__ import annotations

from src.providers.base import OpenAICompatibleProvider
from src.providers.gemini_client import GeminiProvider
from src.providers.groq_client import GroqProvider
from src.providers.sambanova_client import SambaNovaProvider

PROVIDER_REGISTRY: dict[str, type[OpenAICompatibleProvider]] = {
    "groq": GroqProvider,
    "sambanova": SambaNovaProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str) -> OpenAICompatibleProvider:
    """Instantiate a provider by its registry name (case-insensitive)."""
    try:
        provider_class = PROVIDER_REGISTRY[name.lower()]
    except KeyError:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(f"Unknown provider {name!r}. Available: {available}") from None
    return provider_class()