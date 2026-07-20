"""Tests for src/router/cascade.py — fully network-free using fakes."""

from src.eval.dataset import Task
from src.router.cascade import CascadeRouter, run_cascade
from tests.fakes import FakeEmbedder, FakeProvider, FakeRouterModel

TASK = Task(task_id="g1", dataset="gsm8k", question="What is 2+2?", answer="4", difficulty="hard")


class TestCascadeRouterDecide:
    def test_high_confidence_routes_to_cheap(self):
        cascade_router = CascadeRouter(
            router_model=FakeRouterModel(0.9), embedder=FakeEmbedder(), confidence_threshold=0.5
        )
        decision, confidence = cascade_router.decide(TASK.question)
        assert decision == "cheap"
        assert confidence == 0.9

    def test_low_confidence_routes_to_expensive(self):
        cascade_router = CascadeRouter(
            router_model=FakeRouterModel(0.2), embedder=FakeEmbedder(), confidence_threshold=0.5
        )
        decision, confidence = cascade_router.decide(TASK.question)
        assert decision == "expensive"
        assert confidence == 0.2

    def test_confidence_exactly_at_threshold_routes_to_cheap(self):
        cascade_router = CascadeRouter(
            router_model=FakeRouterModel(0.5), embedder=FakeEmbedder(), confidence_threshold=0.5
        )
        decision, _ = cascade_router.decide(TASK.question)
        assert decision == "cheap"  # boundary: >= threshold counts as cheap


class TestRunCascade:
    def test_high_confidence_calls_only_cheap_provider(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        cascade_router = CascadeRouter(FakeRouterModel(0.9), FakeEmbedder(), confidence_threshold=0.5)

        results = run_cascade([TASK], cheap, expensive, cascade_router)

        assert len(results) == 1
        assert results[0].route_decision == "cheap"
        assert results[0].router_confidence == 0.9
        assert results[0].correct is True
        assert cheap.call_count == 1
        assert expensive.call_count == 0

    def test_low_confidence_calls_only_expensive_provider(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        cascade_router = CascadeRouter(FakeRouterModel(0.1), FakeEmbedder(), confidence_threshold=0.5)

        results = run_cascade([TASK], cheap, expensive, cascade_router)

        assert results[0].route_decision == "expensive"
        assert cheap.call_count == 0
        assert expensive.call_count == 1