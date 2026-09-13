"""Ablation: does the router do just as well — or better — using only the 9
hand-crafted features, with no embedding at all?

Background: the original router trained on 393 raw columns (384-dim
embedding + 9 hand-crafted), no dimensionality reduction (PCA exists in
classifier.py but was never actually exercised in a real sweep — see the
Decision Log entry dated the same day as this file). That router scored
AUC=0.5665 on the test split: barely better than random at telling which
specific queries the cheap tier will get right, despite being well
calibrated on average.

This ablation isolates one question: is the 384-dim embedding half of the
input pulling its weight? It trains a second router using *only* the 9
hand-crafted columns (char_length, word_count, etc. — see
src/router/features.py) and compares its AUC/Brier score against the
original router's, on the same test-split ground truth.

- If hand-crafted-only comes back clearly worse: the embedding was carrying
  real signal, and it's worth investigating why PCA (or something else)
  might have thrown it away.
- If hand-crafted-only comes back similar or better: the embedding wasn't
  adding much for this benchmark, and the flat discrimination problem likely
  lives elsewhere (the features themselves, or the classifier).
Either way, this alone doesn't prove anything about PCA specifically —
raw embeddings (no PCA at all) haven't been tested. See PROGRESS.md's Open
Questions for that follow-up.

Zero new API calls: every input this needs already exists in Supabase from
the real Phase 1 sweep — the training queries + correctness labels (phase
"router_training_baseline"), the test-split queries + correctness labels
(phase "router_baseline_cheap"), and the original router's per-task
confidence scores from its real cascade run (phase "router_cascade",
carried in each row's metadata.router_confidence).

This module is deliberately pure — no Supabase client, no network. The
fetch happens in scripts/ablation_handcrafted_features.py; everything here
takes plain lists/dicts in and returns plain values out, so it's fully
testable offline the same way src/eval/analysis.py is.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.eval.analysis import RunRecord
from src.eval.calibration import CalibrationBucket, brier_score, calibration_table, discrimination_auc
from src.router.classifier import RouterModel, train_router
from src.router.features import HAND_CRAFTED_FEATURE_NAMES, hand_crafted_vector


def rows_to_query_labels(rows: list[dict]) -> tuple[list[str], list[bool]]:
    """Pull (query text, correct) pairs out of raw Supabase rows, in row
    order. Used to turn the logged training-baseline rows into something
    train_handcrafted_only_router() can train on."""
    queries = [row["query"] for row in rows]
    labels = [bool(row["correct"]) for row in rows]
    return queries, labels


def train_handcrafted_only_router(train_rows: list[dict]) -> RouterModel:
    """Train a router using only the 9 hand-crafted features — no embedding
    columns at all.

    Passing n_handcrafted_features equal to the full width of X makes
    train_router() compute n_embedding_features=0 and skip the PCA/embedding
    branch entirely (see classifier.py's train_router docstring) — this is
    exactly that path, which is why it needed its own dedicated test in
    test_classifier.py before this module could be trusted.
    """
    queries, labels = rows_to_query_labels(train_rows)
    X = [hand_crafted_vector(q) for q in queries]
    n_handcrafted = len(HAND_CRAFTED_FEATURE_NAMES)
    return train_router(X, labels, n_handcrafted_features=n_handcrafted)


def predict_confidence_by_task(router: RouterModel, test_rows: list[dict]) -> dict[str, float]:
    """Recompute hand-crafted features for each test-split row (from its
    already-logged query text) and get the new router's confidence per
    task_id. No embedding call, no network — hand_crafted_vector() is pure
    text arithmetic."""
    confidences = {}
    for row in test_rows:
        features = hand_crafted_vector(row["query"])
        confidences[row["task_id"]] = router.predict_confidence(features)
    return confidences


def original_confidence_by_task(cascade_rows: list[dict]) -> dict[str, float]:
    """Pull the already-logged confidence scores from the original
    (combined-features) router's real cascade run — so the comparison is
    against what actually ran in production, not a re-simulation of it."""
    return {
        row["task_id"]: row["metadata"]["router_confidence"]
        for row in cascade_rows
        if row.get("metadata", {}).get("router_confidence") is not None
    }


def cheap_records_by_task(cheap_rows: list[dict]) -> dict[str, RunRecord]:
    """Same shape as scripts/analyze_phase1.py's to_records() — kept here
    too so this module can build its own inputs without importing a script."""
    return {
        row["task_id"]: RunRecord(
            task_id=row["task_id"],
            correct=row["correct"],
            estimated_cost_usd=row["estimated_cost_usd"] or 0.0,
            latency_s=row["latency_s"],
        )
        for row in cheap_rows
    }


@dataclass
class AblationResult:
    """Both routers' confidence quality, scored against the identical
    ground truth with the identical metric functions — so any difference
    is attributable to the features, not to the measurement."""

    original_brier: float
    original_auc: float
    original_calibration: list[CalibrationBucket]
    handcrafted_brier: float
    handcrafted_auc: float
    handcrafted_calibration: list[CalibrationBucket]


def compare(
    cheap_by_task: dict[str, RunRecord],
    original_confidence: dict[str, float],
    handcrafted_confidence: dict[str, float],
) -> AblationResult:
    """Score both confidence sets against the same test-split ground truth,
    using the same brier_score/discrimination_auc/calibration_table
    functions the original router was scored with in analyze_phase1.py."""
    return AblationResult(
        original_brier=brier_score(cheap_by_task, original_confidence),
        original_auc=discrimination_auc(cheap_by_task, original_confidence),
        original_calibration=calibration_table(cheap_by_task, original_confidence),
        handcrafted_brier=brier_score(cheap_by_task, handcrafted_confidence),
        handcrafted_auc=discrimination_auc(cheap_by_task, handcrafted_confidence),
        handcrafted_calibration=calibration_table(cheap_by_task, handcrafted_confidence),
    )