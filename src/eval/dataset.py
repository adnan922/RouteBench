"""Phase 1 benchmark dataset: a mixed GSM8K + MMLU subset for the router to learn on.

GSM8K (openai/gsm8k, config "main") is grade-school math requiring multi-step
reasoning — used as the "hard" half. MMLU (cais/mmlu, config "all") is
multiple-choice factual recall — used as the "easy" half. Both are auto-gradable
without an LLM judge, which matters: the router's training labels need to be
exact and cheap to compute, not another model's opinion.

`difficulty` below is a coarse proxy based only on dataset source — the real
difficulty signal for training the router comes from the baseline sweep
(Phase 1's next piece), not from this label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from datasets import load_dataset

_MMLU_LETTERS = ["A", "B", "C", "D"]


@dataclass
class Task:
    task_id: str
    dataset: str  # "gsm8k" | "mmlu"
    question: str
    answer: str  # normalized ground truth: a number as string (gsm8k) or a letter A-D (mmlu)
    difficulty: str  # coarse proxy only, see module docstring
    subject: str | None = None  # MMLU subject, e.g. "anatomy" — None for gsm8k


def load_benchmark(n_gsm8k: int = 40, n_mmlu: int = 40, seed: int = 42) -> list[Task]:
    """Load and normalize a mixed-difficulty benchmark subset.

    Requires network access to the Hugging Face Hub the first time it's
    called; results are cached locally afterward by the `datasets` library.
    """
    tasks: list[Task] = []

    gsm8k = load_dataset("openai/gsm8k", "main", split="test")
    gsm8k = gsm8k.shuffle(seed=seed).select(range(min(n_gsm8k, len(gsm8k))))
    for i, row in enumerate(gsm8k):
        match = re.search(r"####\s*([-\d,\.]+)", row["answer"])
        if not match:
            continue  # skip any malformed row rather than crash the whole load
        ground_truth = match.group(1).replace(",", "")
        tasks.append(
            Task(
                task_id=f"gsm8k-{i}",
                dataset="gsm8k",
                question=row["question"],
                answer=ground_truth,
                difficulty="hard",
            )
        )

    mmlu = load_dataset("cais/mmlu", "all", split="test")
    mmlu = mmlu.shuffle(seed=seed).select(range(min(n_mmlu, len(mmlu))))
    for i, row in enumerate(mmlu):
        choices_block = "\n".join(
            f"{letter}. {choice}" for letter, choice in zip(_MMLU_LETTERS, row["choices"])
        )
        tasks.append(
            Task(
                task_id=f"mmlu-{i}",
                dataset="mmlu",
                question=f"{row['question']}\n{choices_block}",
                answer=_MMLU_LETTERS[row["answer"]],
                difficulty="easy",
                subject=row["subject"],
            )
        )

    return tasks


def extract_final_number(text: str) -> str | None:
    """Pull the last number-like token out of free text, normalized for comparison.

    Handles negatives, decimals, and comma thousand-separators (e.g. "1,234"
    -> "1234"). Returns None if no number is found.
    """
    matches = re.findall(r"-?\d[\d,]*\.?\d*", text)
    if not matches:
        return None
    normalized = matches[-1].replace(",", "")
    return normalized[:-1] if normalized.endswith(".") else normalized


def extract_mmlu_choice(text: str) -> str | None:
    """Pull the model's selected letter (A-D) out of free text.

    Prefers an explicit "answer: X" / "answer is X" pattern; falls back to
    the first standalone A-D letter in the text.
    """
    explicit = re.search(r"answer\s*(?:is|:)?\s*\(?([A-D])\)?", text, re.IGNORECASE)
    if explicit:
        return explicit.group(1).upper()

    standalone = re.search(r"\b([A-D])\b", text)
    return standalone.group(1).upper() if standalone else None


def grade(task: Task, model_response: str) -> bool:
    """Score a model's raw response against a task's ground truth.

    Both extraction functions are deliberately permissive about formatting,
    since we don't control exactly how a model phrases its final answer.
    """
    if task.dataset == "gsm8k":
        predicted = extract_final_number(model_response)
        if predicted is None:
            return False
        try:
            return abs(float(predicted) - float(task.answer)) < 1e-6
        except ValueError:
            return False

    if task.dataset == "mmlu":
        return extract_mmlu_choice(model_response) == task.answer

    raise ValueError(f"Unknown dataset type: {task.dataset!r}")
