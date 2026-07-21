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

from src.eval.budget import BudgetExceededError, CostTracker
from src.eval.dataset import Task, grade
from src.eval.pricing import estimate_cost


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
    query: str
    subject: str | None = None  # MMLU subject, carried through for later analysis
    router_confidence: float | None = None  # set for cascade runs, None for the baselines
    estimated_cost_usd: float | None = None


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


def run_single(
    task: Task,
    provider: Provider,
    route_decision: str,
    router_confidence: float | None = None,
    cost_tracker: CostTracker | None = None,
) -> RunResult:
    """Run one task through one provider and package a graded result.

    Public (not prefixed `_`) because src/router/cascade.py reuses it
    directly — the cascade needs the exact same single-task execution and
    grading logic as the baselines, just with a routing decision that comes
    from a classifier instead of a fixed strategy.

    If `cost_tracker` is given, raises BudgetExceededError *before* making
    the call if the budget is already spent — callers (the run_* functions
    below) catch this to stop early without losing whatever completed so far.
    """
    if cost_tracker is not None:
        cost_tracker.check_before_call()

    result = provider.complete(build_prompt(task))
    cost_usd = estimate_cost(
        result.provider, result.model, result.prompt_tokens, result.completion_tokens
    )
    if cost_tracker is not None:
        cost_tracker.record(cost_usd)

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
        query=task.question,
        subject=task.subject,
        router_confidence=router_confidence,
        estimated_cost_usd=cost_usd,
    )


def run_always_cheap(
    tasks: list[Task], cheap_provider: Provider, cost_tracker: CostTracker | None = None
) -> list[RunResult]:
    """Every task goes to the cheap/fast tier. Upper bound on cost savings, lower bound on quality.

    Stops early (keeping whatever completed so far) if cost_tracker's budget
    is exhausted partway through, rather than losing all progress.
    """
    results = []
    for task in tasks:
        try:
            results.append(
                run_single(task, cheap_provider, route_decision="cheap", cost_tracker=cost_tracker)
            )
        except BudgetExceededError:
            break
    return results


def run_always_expensive(
    tasks: list[Task], expensive_provider: Provider, cost_tracker: CostTracker | None = None
) -> list[RunResult]:
    """Every task goes to the strong/slow tier. Upper bound on quality, upper bound on cost."""
    results = []
    for task in tasks:
        try:
            results.append(
                run_single(
                    task, expensive_provider, route_decision="expensive", cost_tracker=cost_tracker
                )
            )
        except BudgetExceededError:
            break
    return results


def run_random(
    tasks: list[Task],
    cheap_provider: Provider,
    expensive_provider: Provider,
    p_expensive: float = 0.5,
    seed: int = 42,
    cost_tracker: CostTracker | None = None,
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
        provider, decision = (
            (expensive_provider, "expensive")
            if rng.random() < p_expensive
            else (cheap_provider, "cheap")
        )
        try:
            results.append(
                run_single(task, provider, route_decision=decision, cost_tracker=cost_tracker)
            )
        except BudgetExceededError:
            break
    return results