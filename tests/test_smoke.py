"""Phase 0 smoke tests.

The import/structural tests always run in CI. The live-call tests are marked
`integration` and skip automatically unless a real API key is present in the
environment, so CI never burns free-tier rate limits and never fails just
because secrets aren't configured.
"""

import os

import pytest

from src.providers import GroqProvider, SambaNovaProvider
from src.db.supabase_client import SupabaseLogger


def test_providers_importable():
    assert GroqProvider is not None
    assert SambaNovaProvider is not None


def test_groq_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GroqProvider()


def test_sambanova_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("SAMBANOVA_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        SambaNovaProvider()


def test_supabase_logger_requires_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(RuntimeError):
        SupabaseLogger()


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="requires a real GROQ_API_KEY")
def test_groq_live_call():
    client = GroqProvider()
    result = client.complete([{"role": "user", "content": "Reply with just: pong"}])
    assert result.content


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("SAMBANOVA_API_KEY"), reason="requires a real SAMBANOVA_API_KEY"
)
def test_sambanova_live_call():
    client = SambaNovaProvider()
    result = client.complete([{"role": "user", "content": "Reply with just: pong"}])
    assert result.content
