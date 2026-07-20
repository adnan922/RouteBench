"""Token pricing for cost estimation and budget enforcement.

Prices are per 1M tokens, input and output tracked separately since they
often differ substantially. Verified against public pricing pages/trackers
as of 2026-07-17 — they will drift out of date, and Gemini's in particular
had conflicting figures across sources during verification (a possible
recent price cut not yet reflected everywhere), so the more conservative
(higher) of the two was used deliberately: better to estimate cost a bit
high and stop the budget guard a bit early than the other way around.

Free-tier usage doesn't actually charge anything right now — these prices
are used purely as an internal cost proxy and a conservative basis for the
budget guard, not as a live billing signal.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPrice:
    input_per_1m: float
    output_per_1m: float


PRICING: dict[str, dict[str, TokenPrice]] = {
    "groq": {
        "llama-3.1-8b-instant": TokenPrice(input_per_1m=0.05, output_per_1m=0.08),
    },
    "sambanova": {
        "Meta-Llama-3.3-70B-Instruct": TokenPrice(input_per_1m=0.60, output_per_1m=1.20),
    },
    "gemini": {
        "gemini-2.5-flash": TokenPrice(input_per_1m=0.30, output_per_1m=2.50),
        "gemini-3.5-flash": TokenPrice(input_per_1m=1.50, output_per_1m=9.00),
        "gemini-3.1-flash-lite": TokenPrice(input_per_1m=0.25, output_per_1m=1.50),
    },
}

# Used for any provider/model combination not in the table above — a
# deliberately pessimistic guess so an unrecognized model doesn't slip past
# the budget guard silently priced at zero.
_FALLBACK_PRICE = TokenPrice(input_per_1m=2.00, output_per_1m=6.00)


def estimate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate the USD cost of one completion call."""
    price = PRICING.get(provider, {}).get(model, _FALLBACK_PRICE)
    return (prompt_tokens / 1_000_000) * price.input_per_1m + (
        completion_tokens / 1_000_000
    ) * price.output_per_1m