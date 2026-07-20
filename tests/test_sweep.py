"""Tests for src/eval/sweep.py — fully network-free, using fakes for the
provider, embedder, and Supabase logger."""

from src.eval.dataset import Task
from src.eval.runners import RunResult
from src.eval.sweep import log_results, split_tasks, train_router_from_baseline
from src.router.classifier import RouterModel
from tests.fakes import FakeEmbedder, FakeProvider, FakeSupabaseLogger

# Even/odd split gives a balanced 10/10 label mix once graded against the
# fixed "Final Answer: 0" FakeProvider response below — needed for
# CalibratedClassifierCV's stratified cross-validation to have both classes
# to work with.
TASKS = [
    Task(
        task_id=f"g{i}",
        dataset="gsm8k",
        question=f"Question number {i}?",
        answer="0" if i % 2 == 0 else "999",
        difficulty="hard",
    )
    for i in range(20)
]


class TestSplitTasks:
    def test_split_respects_fraction(self):
        train, test = split_tasks(TASKS, train_fraction=0.7)
        assert len(train) == 14
        assert len(test) == 6

    def test_split_is_disjoint_and_covers_all_tasks(self):
        train, test = split_tasks(TASKS)
        train_ids = {t.task_id for t in train}
        test_ids = {t.task_id for t in test}
        assert train_ids.isdisjoint(test_ids)
        assert train_ids | test_ids == {t.task_id for t in TASKS}

    def test_split_is_deterministic_given_seed(self):
        train_a, test_a = split_tasks(TASKS, seed=1)
        train_b, test_b = split_tasks(TASKS, seed=1)
        assert [t.task_id for t in train_a] == [t.task_id for t in train_b]
        assert [t.task_id for t in test_a] == [t.task_id for t in test_b]


class TestTrainRouterFromBaseline:
    def test_returns_trained_router_and_baseline_results(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 0")
        embedder = FakeEmbedder()

        router, baseline_results = train_router_from_baseline(TASKS, cheap, embedder)

        assert isinstance(router, RouterModel)
        assert len(baseline_results) == len(TASKS)
        assert cheap.call_count == len(TASKS)
        # sanity check the labels actually came out mixed, not degenerate
        assert any(r.correct for r in baseline_results)
        assert any(not r.correct for r in baseline_results)


class TestLogResults:
    def test_logs_one_row_per_result_with_expected_fields(self):
        results = [
            RunResult(
                task_id="g1",
                dataset="gsm8k",
                provider="groq",
                model="llama-3.1-8b-instant",
                route_decision="cheap",
                correct=True,
                prompt_tokens=10,
                completion_tokens=5,
                latency_s=0.1,
                response="Final Answer: 4",
                query="What is 2+2?",
                subject=None,
                router_confidence=0.8,
                estimated_cost_usd=0.001,
            )
        ]
        fake_logger = FakeSupabaseLogger()
        log_results(results, phase="test_phase", logger=fake_logger)

        assert len(fake_logger.logged_runs) == 1
        logged = fake_logger.logged_runs[0]
        assert logged["phase"] == "test_phase"
        assert logged["provider"] == "groq"
        assert logged["task_id"] == "g1"
        assert logged["query"] == "What is 2+2?"
        assert logged["estimated_cost_usd"] == 0.001
        assert logged["metadata"]["router_confidence"] == 0.8