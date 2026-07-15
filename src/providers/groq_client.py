"""Groq provider — https://console.groq.com

Groq exposes an OpenAI-compatible endpoint at https://api.groq.com/openai/v1
(confirmed against console.groq.com/docs as of 2026-07-15). Free tier, no card
required; rate limits apply per-model and reset daily — see
console.groq.com/docs/rate-limits for current numbers.

Model catalogs on free-tier inference APIs change over time and models do get
deprecated — confirm `fallback_model` below is still current in the console
before leaning on it, or just set GROQ_MODEL in your .env to override it.
"""

from __future__ import annotations

from .base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    provider_name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
    api_key_env_var = "GROQ_API_KEY"
    model_env_var = "GROQ_MODEL"
    fallback_model = "llama-3.1-8b-instant"  # Groq's cheap/fast tier — verify in console
