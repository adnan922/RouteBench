"""Phase 1 analysis: computes the cost-quality-latency Pareto frontier and
summary stats for each strategy, from results already logged to Supabase.

The cascade curve is reconstructed across many confidence thresholds without
a single additional API call: since the always-cheap and always-expensive
baselines already ran *every* test task on *both* tiers, and the cascade run
recorded each task's calibrated confidence, whatever a different threshold
would have decided is fully determined by data already collected — no
re-running needed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class RunRecord:
    task_id: str
    correct: bool
    estimated_cost_usd: float
    latency_s: float


@dataclass
class StrategySummary:
    name: str
    n_tasks: int
    accuracy: float
    total_cost_usd: float
    mean_cost_usd: float
    mean_latency_s: float


def summarize(name: str, records: list[RunRecord]) -> StrategySummary:
    n = len(records)
    if n == 0:
        return StrategySummary(
            name=name, n_tasks=0, accuracy=0.0, total_cost_usd=0.0, mean_cost_usd=0.0, mean_latency_s=0.0
        )
    total_cost = sum(r.estimated_cost_usd for r in records)
    return StrategySummary(
        name=name,
        n_tasks=n,
        accuracy=sum(r.correct for r in records) / n,
        total_cost_usd=total_cost,
        mean_cost_usd=total_cost / n,
        mean_latency_s=sum(r.latency_s for r in records) / n,
    )


def reconstruct_cascade_at_threshold(
    cheap_by_task: dict[str, RunRecord],
    expensive_by_task: dict[str, RunRecord],
    confidence_by_task: dict[str, float],
    threshold: float,
) -> list[RunRecord]:
    """For every task with a known confidence, pick the cheap or expensive
    tier's already-collected result based on whether confidence clears the
    given threshold — same decision rule as CascadeRouter.decide(), just
    applied after the fact against data we already have for both tiers."""
    results = []
    for task_id, confidence in confidence_by_task.items():
        if task_id not in cheap_by_task or task_id not in expensive_by_task:
            continue  # only reconstruct tasks with both tiers' results available
        record = cheap_by_task[task_id] if confidence >= threshold else expensive_by_task[task_id]
        results.append(record)
    return results


def pareto_frontier(
    cheap_by_task: dict[str, RunRecord],
    expensive_by_task: dict[str, RunRecord],
    confidence_by_task: dict[str, float],
    thresholds: list[float] | None = None,
) -> list[dict]:
    """Sweep confidence thresholds and summarize the reconstructed cascade
    at each one — this is the actual Pareto frontier curve."""
    if thresholds is None:
        thresholds = [i / 20 for i in range(21)]  # 0.00, 0.05, ..., 1.00

    frontier = []
    for threshold in thresholds:
        records = reconstruct_cascade_at_threshold(
            cheap_by_task, expensive_by_task, confidence_by_task, threshold
        )
        summary = summarize(f"cascade@{threshold:.2f}", records)
        frontier.append({"threshold": threshold, **asdict(summary)})
    return frontier