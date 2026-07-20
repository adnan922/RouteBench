"""Tests for src/eval/budget.py — pure logic, no network needed."""

import pytest

from src.eval.budget import BudgetExceededError, CostTracker


class TestCostTracker:
    def test_starts_at_zero_and_not_exceeded(self):
        tracker = CostTracker(budget_usd=1.0)
        assert tracker.total_cost_usd == 0.0
        assert not tracker.is_exceeded()

    def test_recording_below_budget_does_not_raise(self):
        tracker = CostTracker(budget_usd=1.0)
        tracker.record(0.5)
        tracker.check_before_call()  # should not raise

    def test_check_before_call_raises_once_budget_reached_exactly(self):
        tracker = CostTracker(budget_usd=1.0)
        tracker.record(1.0)
        assert tracker.is_exceeded()
        with pytest.raises(BudgetExceededError):
            tracker.check_before_call()

    def test_check_before_call_raises_once_budget_exceeded(self):
        tracker = CostTracker(budget_usd=1.0)
        tracker.record(1.5)
        with pytest.raises(BudgetExceededError):
            tracker.check_before_call()

    def test_multiple_records_accumulate(self):
        tracker = CostTracker(budget_usd=1.0)
        tracker.record(0.3)
        tracker.record(0.3)
        tracker.record(0.3)
        assert tracker.total_cost_usd == pytest.approx(0.9)
        assert not tracker.is_exceeded()

    def test_error_message_reports_budget_and_spend(self):
        tracker = CostTracker(budget_usd=0.5)
        tracker.record(0.6)
        with pytest.raises(BudgetExceededError, match=r"\$0.5000.*\$0.6000"):
            tracker.check_before_call()