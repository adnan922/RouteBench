"""Tests for src/eval/analysis.py — pure logic on synthetic data, no
Supabase or network involved."""

import pytest

from src.eval.analysis import RunRecord, pareto_frontier, reconstruct_cascade_at_threshold, summarize


def _synthetic_data():
    cheap = {
        "t1": RunRecord("t1", correct=True, estimated_cost_usd=0.001, latency_s=0.5),
        "t2": RunRecord("t2", correct=False, estimated_cost_usd=0.001, latency_s=0.5),
    }
    expensive = {
        "t1": RunRecord("t1", correct=True, estimated_cost_usd=0.02, latency_s=1.5),
        "t2": RunRecord("t2", correct=True, estimated_cost_usd=0.02, latency_s=1.5),
    }
    confidence = {"t1": 0.8, "t2": 0.2}
    return cheap, expensive, confidence


class TestSummarize:
    def test_computes_accuracy_and_costs(self):
        records = [
            RunRecord("t1", correct=True, estimated_cost_usd=0.01, latency_s=1.0),
            RunRecord("t2", correct=False, estimated_cost_usd=0.02, latency_s=2.0),
        ]
        summary = summarize("test", records)
        assert summary.n_tasks == 2
        assert summary.accuracy == 0.5
        assert summary.total_cost_usd == pytest.approx(0.03)
        assert summary.mean_cost_usd == pytest.approx(0.015)
        assert summary.mean_latency_s == pytest.approx(1.5)

    def test_empty_records_do_not_crash(self):
        summary = summarize("empty", [])
        assert summary.n_tasks == 0
        assert summary.accuracy == 0.0
        assert summary.total_cost_usd == 0.0


class TestReconstructCascadeAtThreshold:
    def test_low_threshold_routes_everything_to_cheap(self):
        cheap, expensive, confidence = _synthetic_data()
        results = reconstruct_cascade_at_threshold(cheap, expensive, confidence, threshold=0.0)
        by_id = {r.task_id: r.correct for r in results}
        assert by_id == {"t1": True, "t2": False}  # matches cheap's actual results

    def test_high_threshold_routes_everything_to_expensive(self):
        cheap, expensive, confidence = _synthetic_data()
        results = reconstruct_cascade_at_threshold(cheap, expensive, confidence, threshold=1.01)
        by_id = {r.task_id: r.correct for r in results}
        assert by_id == {"t1": True, "t2": True}  # matches expensive's actual results

    def test_middle_threshold_splits_by_confidence(self):
        cheap, expensive, confidence = _synthetic_data()
        results = reconstruct_cascade_at_threshold(cheap, expensive, confidence, threshold=0.5)
        by_id = {r.task_id: r for r in results}
        assert by_id["t1"].estimated_cost_usd == pytest.approx(0.001)
        assert by_id["t2"].estimated_cost_usd == pytest.approx(0.02)

    def test_boundary_confidence_equal_to_threshold_counts_as_cheap(self):
        cheap, expensive, _ = _synthetic_data()
        confidence = {"t1": 0.5}
        results = reconstruct_cascade_at_threshold(cheap, expensive, confidence, threshold=0.5)
        assert results[0].estimated_cost_usd == pytest.approx(0.001)

    def test_skips_tasks_missing_from_either_baseline(self):
        cheap = {"t1": RunRecord("t1", True, 0.001, 0.5)}
        expensive = {}
        confidence = {"t1": 0.1}
        results = reconstruct_cascade_at_threshold(cheap, expensive, confidence, threshold=0.5)
        assert results == []


class TestParetoFrontier:
    def test_returns_one_entry_per_threshold(self):
        cheap, expensive, confidence = _synthetic_data()
        frontier = pareto_frontier(cheap, expensive, confidence, thresholds=[0.0, 0.5, 1.0])
        assert len(frontier) == 3
        assert [f["threshold"] for f in frontier] == [0.0, 0.5, 1.0]

    def test_default_thresholds_span_zero_to_one(self):
        cheap, expensive, confidence = _synthetic_data()
        frontier = pareto_frontier(cheap, expensive, confidence)
        assert frontier[0]["threshold"] == 0.0
        assert frontier[-1]["threshold"] == 1.0
        assert len(frontier) == 21

    def test_each_frontier_point_has_summary_fields(self):
        cheap, expensive, confidence = _synthetic_data()
        frontier = pareto_frontier(cheap, expensive, confidence, thresholds=[0.5])
        point = frontier[0]
        assert set(point) == {
            "threshold", "name", "n_tasks", "accuracy", "total_cost_usd", "mean_cost_usd", "mean_latency_s"
        }