"""Integration tests for budget enforcement across all four Phase 1 runners.

Fully network-free — FakeProvider stands in for real API calls throughout.
"""

from src.eval.budget import CostTracker
from src.eval.dataset import Task
from src.eval.pricing import estimate_cost
from src.eval.runners import run_always_cheap, run_always_expensive, run_random
from src.router.cascade import CascadeRouter, run_cascade
from tests.fakes import FakeEmbedder, FakeProvider, FakeRouterModel

TASKS = [
    Task(
        task_id=f"g{i}",
        dataset="gsm8k",
        question=f"What is {i}+{i}?",
        answer=str(i * 2),
        difficulty="hard",
    )
    for i in range(10)
]


def _tiny_budget(provider_name: str, model: str) -> float:
    """FakeProvider always reports 10 prompt / 5 completion tokens per call —
    size the budget to allow roughly 3 calls through, regardless of which
    provider's price table is used."""
    return estimate_cost(provider_name, model, 10, 5) * 3


class TestRunAlwaysCheapBudget:
    def test_stops_early_when_budget_exhausted(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        tracker = CostTracker(budget_usd=_tiny_budget("groq", "llama-3.1-8b-instant"))

        results = run_always_cheap(TASKS, cheap, cost_tracker=tracker)

        assert 0 < len(results) < len(TASKS)
        assert tracker.is_exceeded()

    def test_completes_fully_with_generous_budget(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        tracker = CostTracker(budget_usd=1000.0)

        results = run_always_cheap(TASKS, cheap, cost_tracker=tracker)

        assert len(results) == len(TASKS)

    def test_works_unchanged_with_no_tracker_at_all(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")

        results = run_always_cheap(TASKS, cheap)

        assert len(results) == len(TASKS)
        assert all(r.estimated_cost_usd is not None and r.estimated_cost_usd >= 0 for r in results)


class TestRunAlwaysExpensiveBudget:
    def test_stops_early_when_budget_exhausted(self):
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        tracker = CostTracker(budget_usd=_tiny_budget("sambanova", "Meta-Llama-3.3-70B-Instruct"))

        results = run_always_expensive(TASKS, expensive, cost_tracker=tracker)

        assert 0 < len(results) < len(TASKS)
        assert tracker.is_exceeded()


class TestRunRandomBudget:
    def test_stops_early_when_budget_exhausted(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        tracker = CostTracker(budget_usd=_tiny_budget("groq", "llama-3.1-8b-instant"))

        results = run_random(TASKS, cheap, expensive, cost_tracker=tracker)

        assert 0 < len(results) < len(TASKS)
        assert tracker.is_exceeded()


class TestRunCascadeBudget:
    def test_stops_early_when_budget_exhausted(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        cascade_router = CascadeRouter(FakeRouterModel(0.9), FakeEmbedder(), confidence_threshold=0.5)
        tracker = CostTracker(budget_usd=_tiny_budget("groq", "llama-3.1-8b-instant"))

        results = run_cascade(TASKS, cheap, expensive, cascade_router, cost_tracker=tracker)

        assert 0 < len(results) < len(TASKS)
        assert tracker.is_exceeded()