"""Tests for src/eval/runners.py.

The orchestration-logic tests use FakeProvider (tests/fakes.py) — no real API
calls, no keys needed, always run. The integration tests at the bottom call
real Groq/SambaNova and skip automatically without live keys.
"""

import os

import pytest

from src.eval.dataset import Task
from src.eval.runners import build_prompt, run_always_cheap, run_always_expensive, run_random
from tests.fakes import FakeProvider

GSM8K_TASK = Task(task_id="g1", dataset="gsm8k", question="What is 2+2?", answer="4", difficulty="hard")
MMLU_TASK = Task(
    task_id="m1",
    dataset="mmlu",
    question="Pick one:\nA. wrong\nB. right",
    answer="B",
    difficulty="easy",
    subject="test",
)


class TestBuildPrompt:
    def test_gsm8k_prompt_mentions_final_answer_format(self):
        messages = build_prompt(GSM8K_TASK)
        assert any("Final Answer" in m["content"] for m in messages)
        assert any(m["role"] == "user" and m["content"] == GSM8K_TASK.question for m in messages)

    def test_mmlu_prompt_mentions_answer_format(self):
        messages = build_prompt(MMLU_TASK)
        assert any("Answer:" in m["content"] for m in messages)

    def test_unknown_dataset_raises(self):
        bad_task = Task(task_id="x", dataset="unknown", question="?", answer="?", difficulty="hard")
        with pytest.raises(ValueError):
            build_prompt(bad_task)


class TestRunAlwaysCheap:
    def test_all_tasks_routed_to_cheap_provider(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        results = run_always_cheap([GSM8K_TASK], cheap)
        assert len(results) == 1
        assert results[0].route_decision == "cheap"
        assert results[0].provider == "groq"
        assert results[0].correct is True
        assert cheap.call_count == 1


class TestRunAlwaysExpensive:
    def test_all_tasks_routed_to_expensive_provider(self):
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        results = run_always_expensive([GSM8K_TASK], expensive)
        assert len(results) == 1
        assert results[0].route_decision == "expensive"
        assert results[0].provider == "sambanova"
        assert results[0].correct is True


class TestRunRandom:
    def test_deterministic_given_seed(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        tasks = [GSM8K_TASK] * 20

        run_a = run_random(tasks, cheap, expensive, seed=7)
        run_b = run_random(tasks, cheap, expensive, seed=7)

        assert [r.route_decision for r in run_a] == [r.route_decision for r in run_b]

    def test_roughly_matches_requested_ratio(self):
        cheap = FakeProvider("groq", "llama-3.1-8b-instant", response_text="Final Answer: 4")
        expensive = FakeProvider(
            "sambanova", "Meta-Llama-3.3-70B-Instruct", response_text="Final Answer: 4"
        )
        tasks = [GSM8K_TASK] * 200

        results = run_random(tasks, cheap, expensive, p_expensive=0.3, seed=1)
        expensive_fraction = sum(1 for r in results if r.route_decision == "expensive") / len(results)

        assert 0.2 < expensive_fraction < 0.4  # loose bound — it's random, not exact


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="requires a real GROQ_API_KEY")
def test_run_always_cheap_with_real_groq():
    from src.providers import GroqProvider

    results = run_always_cheap([GSM8K_TASK], GroqProvider())
    assert len(results) == 1
    assert results[0].latency_s > 0


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("SAMBANOVA_API_KEY"), reason="requires a real SAMBANOVA_API_KEY")
def test_run_always_expensive_with_real_sambanova():
    from src.providers import SambaNovaProvider

    results = run_always_expensive([GSM8K_TASK], SambaNovaProvider())
    assert len(results) == 1
    assert results[0].latency_s > 0