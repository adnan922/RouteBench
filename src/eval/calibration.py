"""Diagnostics for the router's confidence quality: is it well-calibrated
(predicted probability matches empirical frequency) and does it discriminate
(does confidence actually separate cheap-succeeds from cheap-fails)?

Both questions matter separately — a classifier can be well-calibrated on
average while still assigning nearly the same confidence to every task (poor
discrimination), which is exactly the shape that produced Phase 1's first
Pareto frontier: flat across most of the threshold range. Calibration alone
can't tell you which failure mode you're looking at; these functions are
built specifically to tell the two apart with a number instead of a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from src.eval.analysis import RunRecord


@dataclass
class CalibrationBucket:
    range_low: float
    range_high: float
    n_tasks: int
    mean_predicted_confidence: float
    empirical_accuracy: float


def calibration_table(
    cheap_by_task: dict[str, RunRecord],
    confidence_by_task: dict[str, float],
    n_buckets: int = 5,
) -> list[CalibrationBucket]:
    """Bucket tasks by predicted confidence and compare to cheap's actual
    empirical accuracy in that bucket. A well-calibrated router has
    mean_predicted_confidence close to empirical_accuracy in every bucket
    that has enough tasks to judge — buckets with very few tasks are noisy,
    check n_tasks before reading too much into any single bucket.
    """
    buckets = []
    edges = [i / n_buckets for i in range(n_buckets + 1)]
    for low, high in pairwise(edges):
        is_last = high >= 1.0
        task_ids = [
            tid
            for tid, conf in confidence_by_task.items()
            if (low <= conf < high) or (is_last and conf == high)
        ]
        task_ids = [tid for tid in task_ids if tid in cheap_by_task]
        if not task_ids:
            buckets.append(CalibrationBucket(low, high, 0, 0.0, 0.0))
            continue
        confidences = [confidence_by_task[tid] for tid in task_ids]
        accuracies = [float(cheap_by_task[tid].correct) for tid in task_ids]
        buckets.append(
            CalibrationBucket(
                range_low=low,
                range_high=high,
                n_tasks=len(task_ids),
                mean_predicted_confidence=sum(confidences) / len(confidences),
                empirical_accuracy=sum(accuracies) / len(accuracies),
            )
        )
    return buckets


def brier_score(cheap_by_task: dict[str, RunRecord], confidence_by_task: dict[str, float]) -> float:
    """Mean squared error between predicted confidence and actual outcome
    (0/1). 0 = perfect. 0.25 is the score a constant 0.5 guess gets against a
    50/50 outcome — a useful "no better than a coin flip" reference point."""
    pairs = [
        (confidence_by_task[tid], float(cheap_by_task[tid].correct))
        for tid in confidence_by_task
        if tid in cheap_by_task
    ]
    if not pairs:
        return float("nan")
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def discrimination_auc(cheap_by_task: dict[str, RunRecord], confidence_by_task: dict[str, float]) -> float:
    """AUC of predicted confidence vs actual cheap-success — measures
    whether higher confidence actually correlates with cheap succeeding,
    independent of whether the raw probabilities are well-calibrated on
    average. 0.5 = no better than random guessing; 1.0 = perfect
    discrimination. This is the number that directly answers "is the router
    overconfident, or just not discriminating" — a low Brier score with an
    AUC near 0.5 means the router got lucky on average but isn't actually
    telling easy and hard queries apart.
    """
    from sklearn.metrics import roc_auc_score

    pairs = [
        (confidence_by_task[tid], float(cheap_by_task[tid].correct))
        for tid in confidence_by_task
        if tid in cheap_by_task
    ]
    if not pairs:
        return float("nan")
    y_score = [p for p, _ in pairs]
    y_true = [y for _, y in pairs]
    if len(set(y_true)) < 2:
        return float("nan")  # AUC undefined with only one class present
    return roc_auc_score(y_true, y_score)