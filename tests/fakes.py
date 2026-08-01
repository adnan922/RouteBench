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


class FakeEmbedder:
    """Stands in for QueryEmbedder — a deterministic small vector derived
    from text length, no real model downloaded."""

    def embed_one(self, text: str) -> list[float]:
        return [float(len(text) % 10) / 10.0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]


class FakeRouterModel:
    """Stands in for RouterModel — returns a fixed confidence regardless of
    input, so cascade/sweep tests can isolate their own logic from whether
    the classifier itself learned anything (that's covered separately in
    tests/test_classifier.py)."""

    def __init__(self, fixed_confidence: float = 0.5) -> None:
        self.fixed_confidence = fixed_confidence

    def predict_confidence(self, features: list[float]) -> float:
        return self.fixed_confidence


class FakeSupabaseLogger:
    """Stands in for SupabaseLogger — records log_run() calls in memory
    instead of hitting a real database."""

    def __init__(self) -> None:
        self.logged_runs: list[dict] = []

    def log_run(self, **fields) -> dict:
        self.logged_runs.append(fields)
        return fields

    def ping_heartbeat(self) -> None:
        pass

    def fetch_by_phase(self, phase: str) -> list[dict]:
        """Retrieve every row logged under a given phase — used by
        scripts/analyze_phase1.py to pull results back out for the Pareto
        frontier analysis."""
        response = self._client.table("runs").select("*").eq("phase", phase).execute()
        return response.data