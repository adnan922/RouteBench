"""Google AI Studio (Gemini) provider — https://aistudio.google.com

Gemini exposes an OpenAI-compatible endpoint at
https://generativelanguage.googleapis.com/v1beta/openai/ (confirmed against
ai.google.dev/gemini-api/docs/openai as of 2026-07-17).

Model history in this project: gemini-2.5-flash isn't available to new
accounts; gemini-3.5-flash's free tier turned out to be a hard 20
requests/day wall (see DailyQuotaExceededError in base.py) — too small for
a multi-task sweep regardless of throttling. gemini-3.1-flash-lite is the
current default instead: free tier observed directly from a real Google AI
Studio dashboard (2026-07-19) at 15 RPM / 250K TPM / 500 RPD — RPD in
particular is generous enough that a full sweep fits comfortably, and RPM
is the only limit worth throttling for (TPM won't bind first at these token
volumes).
"""

from __future__ import annotations

from .base import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    provider_name = "gemini"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key_env_var = "GEMINI_API_KEY"
    model_env_var = "GEMINI_MODEL"
    min_interval_env_var = "GEMINI_MIN_INTERVAL_S"
    default_min_interval_s = 5.0  # ~12 RPM effective, comfortable margin under the observed 15 RPM cap
    fallback_model = "gemini-3.1-flash-lite"  # verify current availability/quotas in AI Studio