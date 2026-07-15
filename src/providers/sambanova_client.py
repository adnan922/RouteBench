"""SambaNova Cloud provider — https://cloud.sambanova.ai

SambaNova Cloud exposes an OpenAI-compatible endpoint at
https://api.sambanova.ai/v1 (confirmed against docs.sambanova.ai as of
2026-07-15). Persistent free tier, no card required, plus a small starter
credit; rate limits apply per-model.

Model catalogs change over time — confirm `fallback_model` below is still
current in the console before leaning on it, or just set SAMBANOVA_MODEL in
your .env to override it.
"""

from __future__ import annotations

from .base import OpenAICompatibleProvider


class SambaNovaProvider(OpenAICompatibleProvider):
    provider_name = "sambanova"
    default_base_url = "https://api.sambanova.ai/v1"
    api_key_env_var = "SAMBANOVA_API_KEY"
    model_env_var = "SAMBANOVA_MODEL"
    fallback_model = "Meta-Llama-3.3-70B-Instruct"  # SambaNova's most battle-tested model — verify in console
