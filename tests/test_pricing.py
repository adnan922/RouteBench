"""Tests for src/eval/pricing.py — pure arithmetic, no network needed."""

import pytest

from src.eval.pricing import estimate_cost


class TestEstimateCost:
    def test_known_provider_and_model_input_only(self):
        cost = estimate_cost(
            "groq", "llama-3.1-8b-instant", prompt_tokens=1_000_000, completion_tokens=0
        )
        assert cost == pytest.approx(0.05)

    def test_output_tokens_priced_separately_and_usually_higher(self):
        cost = estimate_cost(
            "groq", "llama-3.1-8b-instant", prompt_tokens=0, completion_tokens=1_000_000
        )
        assert cost == pytest.approx(0.08)

    def test_combines_input_and_output(self):
        cost = estimate_cost(
            "sambanova",
            "Meta-Llama-3.3-70B-Instruct",
            prompt_tokens=500_000,
            completion_tokens=500_000,
        )
        assert cost == pytest.approx(0.30 + 0.60)

    def test_zero_tokens_costs_nothing(self):
        assert estimate_cost("groq", "llama-3.1-8b-instant", 0, 0) == 0.0

    def test_unknown_model_falls_back_to_conservative_price_not_zero(self):
        cost = estimate_cost(
            "groq", "some-brand-new-model", prompt_tokens=1_000_000, completion_tokens=0
        )
        assert cost > 0  # must never silently price an unrecognized model at zero

    def test_unknown_provider_falls_back_too(self):
        cost = estimate_cost(
            "some-new-provider", "some-model", prompt_tokens=1_000_000, completion_tokens=1_000_000
        )
        assert cost > 0

    def test_gemini_flash_lite_pricing(self):
        cost = estimate_cost(
            "gemini", "gemini-3.1-flash-lite", prompt_tokens=1_000_000, completion_tokens=1_000_000
        )
        assert cost == pytest.approx(0.25 + 1.50)