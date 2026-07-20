"""Hard budget guard for a sweep: tracks cumulative estimated spend across
every provider call and stops new calls once a configured ceiling is hit.

This is a genuine safety net, not just theater — SambaNova's free tier
includes a real dollar-denominated credit, and any provider's free tier or
pricing can change. The guard can't retroactively prevent the one call that
pushes spend over budget (cost isn't known until the response comes back
with real token counts), but it guarantees no further calls start once the
ceiling is reached — worst case is budget_usd plus the cost of one
in-flight call, not an unbounded run.
"""

from __future__ import annotations


class BudgetExceededError(Exception):
    """Raised when a call is about to be made but the budget is already spent."""


class CostTracker:
    def __init__(self, budget_usd: float) -> None:
        self.budget_usd = budget_usd
        self.total_cost_usd = 0.0

    def is_exceeded(self) -> bool:
        return self.total_cost_usd >= self.budget_usd

    def check_before_call(self) -> None:
        if self.is_exceeded():
            raise BudgetExceededError(
                f"Budget of ${self.budget_usd:.4f} reached (spent ${self.total_cost_usd:.4f}) "
                "— stopping before making another call."
            )

    def record(self, cost_usd: float) -> None:
        self.total_cost_usd += cost_usd