"""Two-stage cascade: try the cheap tier first, escalate to the expensive
tier only when the router's calibrated confidence is below a threshold.

This is the actual system RQ1 is about — features.py and classifier.py exist
to make this one decision well.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.eval.budget import BudgetExceededError, CostTracker
from src.eval.dataset import Task
from src.eval.runners import Provider, RunResult, run_single
from src.router.classifier import RouterLike
from src.router.features import EmbedderLike, combined_features


@dataclass
class CascadeRouter:
    """Combines a trained router, an embedder, and a decision threshold into
    a single routing function. `confidence_threshold` is the calibrated
    probability of cheap-tier success below which a query escalates — 0.5 is
    a reasonable starting point, but it's exactly the knob the Pareto
    frontier analysis sweeps to trace out the cost/quality tradeoff."""

    router_model: RouterLike
    embedder: EmbedderLike
    confidence_threshold: float = 0.5

    def decide(self, query: str) -> tuple[str, float]:
        """Return (route_decision, calibrated_confidence) for a query."""
        features = combined_features(query, self.embedder)
        confidence = self.router_model.predict_confidence(features)
        decision = "cheap" if confidence >= self.confidence_threshold else "expensive"
        return decision, confidence


def run_cascade(
    tasks: list[Task],
    cheap_provider: Provider,
    expensive_provider: Provider,
    cascade_router: CascadeRouter,
    cost_tracker: CostTracker | None = None,
) -> list[RunResult]:
    """Route each task through the cascade. Same RunResult shape as the
    baselines (src/eval/runners.py), so results are directly comparable.

    Stops early (keeping whatever completed so far) if cost_tracker's budget
    is exhausted partway through.
    """
    results = []
    for task in tasks:
        decision, confidence = cascade_router.decide(task.question)
        provider = cheap_provider if decision == "cheap" else expensive_provider
        try:
            results.append(
                run_single(
                    task,
                    provider,
                    route_decision=decision,
                    router_confidence=confidence,
                    cost_tracker=cost_tracker,
                )
            )
        except BudgetExceededError:
            break
    return results