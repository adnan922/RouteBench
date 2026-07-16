"""Phase 1 baseline runners: always-cheap, always-expensive, and random-routing.

These three strategies are the comparison points the router (built next) has
to beat. Each runner takes a list of Tasks and one or two providers, and
returns a list of RunResults — ready to be logged to Supabase in a later step,
not done here to keep this piece focused on the running/grading logic itself.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from src.eval.dataset import Task, grade


class Provider(Protocol):
    """Structural type for anything with a .complete() matching OpenAICompatibleProvider —
    lets tests substitute a fake provider without a real inheritance relationship."""

    def complete(self, messages: list[dict], model: str | None = None, **kwargs): ...


@dataclass
class RunResult:
    task_id: str
    dataset: str
    provider: str
    model: str
    route_decision: str  # "cheap" | "expensive" — which tier actually handled this task
    correct: bool
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    response: str
    subject: str | None = None  # MMLU subject, carried through for later analysis


def build_prompt(task: Task) -> list[dict]:
    """Build a chat-completion prompt that steers the model toward a gradable answer format."""
    if task.dataset == "gsm8k":
        instruction = (
            "Solve this grade-school math word problem. Show your reasoning briefly, "
            "then end your response on a new line in exactly this format: "
            "'Final Answer: <number>'."
        )
    elif task.dataset == "mmlu":
        instruction = (
            "Answer this multiple-choice question. End your response on a new line "
            "in exactly this format: 'Answer: <letter>'."
        )
    else:
        raise ValueError(f"Unknown dataset type: {task.dataset!r}")

    return [
        {"role": "system", "content": instruction},
        {"role": "user", "content": task.question},
    ]


def _run_single(task: Task, provider: Provider, route_decision: str) -> RunResult:
    result = provider.complete(build_prompt(task))
    return RunResult(
        task_id=task.task_id,
        dataset=task.dataset,
        provider=result.provider,
        model=result.model,
        route_decision=route_decision,
        correct=grade(task, result.content),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_s=result.latency_s,
        response=result.content,
        subject=task.subject,
    )


def run_always_cheap(tasks: list[Task], cheap_provider: Provider) -> list[RunResult]:
    """Every task goes to the cheap/fast tier. Upper bound on cost savings, lower bound on quality."""
    return [_run_single(task, cheap_provider, route_decision="cheap") for task in tasks]


def run_always_expensive(tasks: list[Task], expensive_provider: Provider) -> list[RunResult]:
    """Every task goes to the strong/slow tier. Upper bound on quality, upper bound on cost."""
    return [_run_single(task, expensive_provider, route_decision="expensive") for task in tasks]


def run_random(
    tasks: list[Task],
    cheap_provider: Provider,
    expensive_provider: Provider,
    p_expensive: float = 0.5,
    seed: int = 42,
) -> list[RunResult]:
    """Randomly assign each task to a tier, independent of task difficulty.

    The point of this baseline is to show what "no intelligence" routing looks
    like — the calibrated router (built next) needs to clearly beat this, not
    just beat the always-cheap floor, to prove it's actually reading the query
    rather than getting lucky at whatever ratio p_expensive happens to land on.
    """
    rng = random.Random(seed)
    results = []
    for task in tasks:
        if rng.random() < p_expensive:
            results.append(_run_single(task, expensive_provider, route_decision="expensive"))
        else:
            results.append(_run_single(task, cheap_provider, route_decision="cheap"))
    return results