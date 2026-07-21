"""Phase 1 full sweep: trains the router on a training split, then runs all
four strategies (always-cheap, always-expensive, random, cascade) on a held-
out test split, logging every run to Supabase.

The functions here are the building blocks; scripts/run_phase1_sweep.py is
the actual runnable entry point that wires real providers, a real embedder,
and a real Supabase connection together.
"""

from __future__ import annotations

import random

from src.eval.budget import CostTracker
from src.eval.dataset import Task
from src.eval.runners import Provider, RunResult, run_always_cheap
from src.router.classifier import RouterModel, train_router
from src.router.features import EmbedderLike, combined_features_batch


def split_tasks(
    tasks: list[Task], train_fraction: float = 0.7, seed: int = 42
) -> tuple[list[Task], list[Task]]:
    """Split into a training set (used only to train the router) and a held-
    out test set (used to evaluate every strategy, including the cascade).

    Keeping these disjoint matters: training and evaluating the router on the
    same data it learned from would inflate how good it looks, and RQ1's
    whole point is an honest cost/quality comparison.
    """
    shuffled = tasks.copy()
    random.Random(seed).shuffle(shuffled)
    split_index = int(len(shuffled) * train_fraction)
    return shuffled[:split_index], shuffled[split_index:]


def train_router_from_baseline(
    train_tasks: list[Task],
    cheap_provider: Provider,
    embedder: EmbedderLike,
    cost_tracker: CostTracker | None = None,
) -> tuple[RouterModel, list[RunResult]]:
    """Run the cheap-tier baseline on the training split to get ground-truth
    labels (did the cheap model get it right?), extract features for the
    same queries, and train the router on that pairing.

    If the budget guard stops the baseline sweep early, `baseline_results`
    will be a strict prefix of `train_tasks` (run_always_cheap processes
    tasks in order and stops at the first budget failure) — features are
    built from that same prefix so they stay aligned with the labels.
    """
    baseline_results = run_always_cheap(train_tasks, cheap_provider, cost_tracker=cost_tracker)
    completed_tasks = train_tasks[: len(baseline_results)]
    queries = [task.question for task in completed_tasks]
    features = combined_features_batch(queries, embedder)
    labels = [result.correct for result in baseline_results]
    router = train_router(features, labels)
    return router, baseline_results


def log_results(results: list[RunResult], phase: str, logger) -> None:
    """Push every run to Supabase — one row per task, ready for the Pareto
    frontier analysis to query back out. `logger` just needs a `.log_run()`
    method matching SupabaseLogger — tests substitute a fake."""
    for result in results:
        logger.log_run(
            phase=phase,
            provider=result.provider,
            model=result.model,
            task_id=result.task_id,
            query=result.query,
            response=result.response,
            correct=result.correct,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            latency_s=result.latency_s,
            estimated_cost_usd=result.estimated_cost_usd,
            route_decision=result.route_decision,
            metadata={
                "dataset": result.dataset,
                "subject": result.subject,
                "router_confidence": result.router_confidence,
            },
        )