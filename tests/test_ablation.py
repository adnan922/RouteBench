"""Tests for src/eval/ablation.py.

Entirely network-free: builds fake Supabase-row dicts by hand (same shape
fetch_by_phase() would return) so this runs the same everywhere — this
sandbox, CI, or the home server — matching the pattern used for
src/eval/analysis.py and src/router/classifier.py.
"""

from src.eval.ablation import (
    cheap_records_by_task,
    compare,
    original_confidence_by_task,
    predict_confidence_by_task,
    rows_to_query_labels,
    train_handcrafted_only_router,
)

# GSM8K-style (longer, numeric) vs MMLU-style (shorter, has "A." marker)
# queries, so hand_crafted_vector() actually has something to separate on —
# mirrors why has_multiple_choice_markers is a strong real-world proxy per
# features.py's own docstring.
_GSM8K_LIKE = "Janet has 3 apples and buys 12 more. How many does she have in total?"
_MMLU_LIKE = "What is the capital of France?\nA. Paris\nB. Lyon\nC. Nice\nD. Tours"


def _fake_training_rows(n: int = 40) -> list[dict]:
    rows = []
    for i in range(n):
        is_hard = i % 2 == 0
        rows.append(
            {
                "task_id": f"train-{i}",
                "query": _GSM8K_LIKE if is_hard else _MMLU_LIKE,
                # cheap tier struggles on the "hard" ones, succeeds on "easy" —
                # gives the classifier genuine signal to find
                "correct": not is_hard,
            }
        )
    return rows


def _fake_test_rows(n: int = 20) -> list[dict]:
    rows = []
    for i in range(n):
        is_hard = i % 2 == 0
        rows.append(
            {
                "task_id": f"test-{i}",
                "query": _GSM8K_LIKE if is_hard else _MMLU_LIKE,
                "correct": not is_hard,
                "estimated_cost_usd": 0.001,
                "latency_s": 1.0,
            }
        )
    return rows


def _fake_cascade_rows(n: int = 20) -> list[dict]:
    """Stands in for the original router's already-logged confidence scores
    — deliberately different values from what the hand-crafted-only router
    would produce, so a test comparing the two isn't accidentally comparing
    identical numbers to themselves."""
    rows = []
    for i in range(n):
        rows.append(
            {
                "task_id": f"test-{i}",
                "metadata": {"router_confidence": 0.5},
            }
        )
    return rows


class TestRowsToQueryLabels:
    def test_extracts_in_order(self):
        rows = _fake_training_rows(n=4)
        queries, labels = rows_to_query_labels(rows)
        assert queries == [r["query"] for r in rows]
        assert labels == [r["correct"] for r in rows]


class TestTrainHandcraftedOnlyRouter:
    def test_trains_without_error(self):
        router = train_handcrafted_only_router(_fake_training_rows())
        assert router is not None

    def test_predicts_valid_probabilities(self):
        router = train_handcrafted_only_router(_fake_training_rows())
        test_rows = _fake_test_rows(n=6)
        confidences = predict_confidence_by_task(router, test_rows)
        assert set(confidences.keys()) == {r["task_id"] for r in test_rows}
        assert all(0.0 <= c <= 1.0 for c in confidences.values())


class TestOriginalConfidenceByTask:
    def test_pulls_confidence_from_metadata(self):
        cascade_rows = _fake_cascade_rows(n=3)
        result = original_confidence_by_task(cascade_rows)
        assert result == {"test-0": 0.5, "test-1": 0.5, "test-2": 0.5}

    def test_skips_rows_with_no_confidence_logged(self):
        rows = [
            {"task_id": "a", "metadata": {"router_confidence": 0.7}},
            {"task_id": "b", "metadata": {}},
            {"task_id": "c", "metadata": {"router_confidence": None}},
        ]
        result = original_confidence_by_task(rows)
        assert result == {"a": 0.7}


class TestCheapRecordsByTask:
    def test_builds_run_records(self):
        rows = _fake_test_rows(n=2)
        records = cheap_records_by_task(rows)
        assert set(records.keys()) == {"test-0", "test-1"}
        assert records["test-0"].correct == rows[0]["correct"]

    def test_missing_cost_defaults_to_zero(self):
        rows = [
            {
                "task_id": "x",
                "correct": True,
                "estimated_cost_usd": None,
                "latency_s": 1.0,
            }
        ]
        records = cheap_records_by_task(rows)
        assert records["x"].estimated_cost_usd == 0.0


class TestCompare:
    def test_returns_metrics_for_both_routers(self):
        train_rows = _fake_training_rows()
        test_rows = _fake_test_rows(n=20)
        cascade_rows = _fake_cascade_rows(n=20)

        router = train_handcrafted_only_router(train_rows)
        cheap_by_task = cheap_records_by_task(test_rows)
        original_confidence = original_confidence_by_task(cascade_rows)
        handcrafted_confidence = predict_confidence_by_task(router, test_rows)

        result = compare(cheap_by_task, original_confidence, handcrafted_confidence)

        assert 0.0 <= result.original_brier <= 1.0
        assert 0.0 <= result.handcrafted_brier <= 1.0
        # AUC can be NaN if a class is missing, but not here — both classes
        # are present in the fake data by construction
        assert 0.0 <= result.original_auc <= 1.0
        assert 0.0 <= result.handcrafted_auc <= 1.0
        assert len(result.original_calibration) == 5
        assert len(result.handcrafted_calibration) == 5

    def test_handcrafted_router_discriminates_on_separable_fake_data(self):
        """Not just 'runs without error' — the fake data is constructed so
        query format perfectly predicts correctness (mirrors features.py's
        own note that has_multiple_choice_markers is a strong proxy for
        MMLU vs GSM8K), so a working classifier should score well above
        chance here."""
        train_rows = _fake_training_rows(n=60)
        test_rows = _fake_test_rows(n=20)
        cascade_rows = _fake_cascade_rows(n=20)

        router = train_handcrafted_only_router(train_rows)
        cheap_by_task = cheap_records_by_task(test_rows)
        handcrafted_confidence = predict_confidence_by_task(router, test_rows)
        original_confidence = original_confidence_by_task(cascade_rows)

        result = compare(cheap_by_task, original_confidence, handcrafted_confidence)
        assert result.handcrafted_auc > 0.8