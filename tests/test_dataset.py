"""Tests for src/eval/dataset.py.

The grading/extraction tests are pure logic — no network, no API keys, always
run. The one test that actually calls load_benchmark() needs the Hugging Face
Hub and is marked `network`, so it's opted out of environments without
internet access (like the sandbox this was developed in) but still runs on
your home server or in CI.
"""

import pytest

from src.eval.dataset import Task, extract_final_number, extract_mmlu_choice, grade, load_benchmark


class TestExtractFinalNumber:
    def test_plain_integer(self):
        assert extract_final_number("The answer is 42.") == "42"

    def test_number_with_commas(self):
        assert extract_final_number("Total sold: 1,234 units") == "1234"

    def test_negative_number(self):
        assert extract_final_number("The change was -15 dollars") == "-15"

    def test_decimal_number(self):
        assert extract_final_number("Final Answer: 3.5") == "3.5"

    def test_uses_last_number_when_multiple_present(self):
        assert extract_final_number("Step 1: 10 apples. Step 2: 10 - 3 = 7") == "7"

    def test_no_number_returns_none(self):
        assert extract_final_number("I'm not sure.") is None


class TestExtractMMLUChoice:
    def test_explicit_answer_is_pattern(self):
        assert extract_mmlu_choice("The answer is B.") == "B"

    def test_explicit_answer_colon_pattern(self):
        assert extract_mmlu_choice("Answer: C") == "C"

    def test_parenthesized_letter(self):
        assert extract_mmlu_choice("The correct answer is (D)") == "D"

    def test_falls_back_to_standalone_letter(self):
        assert extract_mmlu_choice("I believe A is correct here.") == "A"

    def test_no_letter_returns_none(self):
        assert extract_mmlu_choice("I have no idea what the answer is.") is None


class TestGrade:
    def test_gsm8k_correct(self):
        task = Task(task_id="t1", dataset="gsm8k", question="2+2?", answer="4", difficulty="hard")
        assert grade(task, "Let's see, 2+2=4. Final Answer: 4") is True

    def test_gsm8k_incorrect(self):
        task = Task(task_id="t1", dataset="gsm8k", question="2+2?", answer="4", difficulty="hard")
        assert grade(task, "Final Answer: 5") is False

    def test_gsm8k_no_extractable_number(self):
        task = Task(task_id="t1", dataset="gsm8k", question="2+2?", answer="4", difficulty="hard")
        assert grade(task, "I don't know.") is False

    def test_mmlu_correct(self):
        task = Task(
            task_id="t2", dataset="mmlu", question="...", answer="B", difficulty="easy", subject="anatomy"
        )
        assert grade(task, "The answer is B.") is True

    def test_mmlu_incorrect(self):
        task = Task(
            task_id="t2", dataset="mmlu", question="...", answer="B", difficulty="easy", subject="anatomy"
        )
        assert grade(task, "Answer: C") is False

    def test_unknown_dataset_raises(self):
        task = Task(task_id="t3", dataset="unknown", question="...", answer="X", difficulty="hard")
        with pytest.raises(ValueError):
            grade(task, "whatever")


@pytest.mark.network
def test_load_benchmark_returns_expected_counts():
    try:
        tasks = load_benchmark(n_gsm8k=5, n_mmlu=5, seed=1)
    except Exception as exc:  # network unavailable or Hugging Face Hub unreachable
        pytest.skip(f"Could not reach Hugging Face Hub: {exc}")
    assert len(tasks) == 10
    assert sum(1 for t in tasks if t.dataset == "gsm8k") == 5
    assert sum(1 for t in tasks if t.dataset == "mmlu") == 5
    assert all(t.question and t.answer for t in tasks)
