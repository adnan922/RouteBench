"""Phase 1 full sweep — run this once real credentials are in place.

    docker compose run app python -m scripts.run_phase1_sweep

Loads the benchmark, splits into train/test, trains the router on the
training split's always-cheap baseline, then runs all four strategies
(always-cheap, always-expensive, random, cascade) on the held-out test
split — logging every single run to Supabase along the way.

Not a pytest test on purpose: this burns real API calls against free-tier
rate limits every time it runs, which is fine to do deliberately but wrong
to run automatically on every CI push.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from src.db.supabase_client import SupabaseLogger  # noqa: E402
from src.eval.budget import CostTracker  # noqa: E402
from src.eval.dataset import load_benchmark  # noqa: E402
from src.eval.runners import run_always_cheap, run_always_expensive, run_random  # noqa: E402
from src.eval.sweep import log_results, split_tasks, train_router_from_baseline  # noqa: E402
from src.providers import get_provider  # noqa: E402
from src.router.cascade import CascadeRouter, run_cascade  # noqa: E402
from src.router.features import QueryEmbedder  # noqa: E402

CHEAP_PROVIDER_NAME = os.environ.get("CHEAP_PROVIDER", "groq")
EXPENSIVE_PROVIDER_NAME = os.environ.get("EXPENSIVE_PROVIDER", "sambanova")
BUDGET_USD = float(os.environ.get("BUDGET_USD", "1.00"))


def _stop_if_budget_exceeded(cost_tracker: CostTracker, stage_name: str) -> None:
    """Hard stop: if the budget guard has already tripped, don't start the
    next stage. Whatever completed up to this point is already logged to
    Supabase, so nothing is lost — this just refuses to spend further."""
    if cost_tracker.is_exceeded():
        print(
            f"\nBudget exhausted (${cost_tracker.total_cost_usd:.4f} of "
            f"${cost_tracker.budget_usd:.2f} spent) after {stage_name}. Stopping here — "
            "results completed so far are already logged to Supabase."
        )
        raise SystemExit(1)


print("Loading benchmark...")
tasks = load_benchmark(n_gsm8k=40, n_mmlu=40)
train_tasks, test_tasks = split_tasks(tasks)
print(f"Train: {len(train_tasks)} tasks, Test: {len(test_tasks)} tasks")

print(f"Cheap tier: {CHEAP_PROVIDER_NAME}, Expensive tier: {EXPENSIVE_PROVIDER_NAME}")
print(f"Budget guard: ${BUDGET_USD:.2f} for this entire run")
cheap = get_provider(CHEAP_PROVIDER_NAME)
expensive = get_provider(EXPENSIVE_PROVIDER_NAME)
embedder = QueryEmbedder()
logger = SupabaseLogger()
cost_tracker = CostTracker(budget_usd=BUDGET_USD)

print("Training router on the training split's cheap-tier baseline...")
router_model, train_baseline_results = train_router_from_baseline(
    train_tasks, cheap, embedder, cost_tracker=cost_tracker
)
log_results(train_baseline_results, phase="router_training_baseline", logger=logger)
_stop_if_budget_exceeded(cost_tracker, "training baseline")

cascade_router = CascadeRouter(router_model=router_model, embedder=embedder, confidence_threshold=0.5)

print("Running always-cheap baseline on test split...")
cheap_results = run_always_cheap(test_tasks, cheap, cost_tracker=cost_tracker)
log_results(cheap_results, phase="router_baseline_cheap", logger=logger)
_stop_if_budget_exceeded(cost_tracker, "always-cheap baseline")

print("Running always-expensive baseline on test split...")
expensive_results = run_always_expensive(test_tasks, expensive, cost_tracker=cost_tracker)
log_results(expensive_results, phase="router_baseline_expensive", logger=logger)
_stop_if_budget_exceeded(cost_tracker, "always-expensive baseline")

print("Running random-routing baseline on test split...")
random_results = run_random(test_tasks, cheap, expensive, cost_tracker=cost_tracker)
log_results(random_results, phase="router_baseline_random", logger=logger)
_stop_if_budget_exceeded(cost_tracker, "random-routing baseline")

print("Running cascade on test split...")
cascade_results = run_cascade(test_tasks, cheap, expensive, cascade_router, cost_tracker=cost_tracker)
log_results(cascade_results, phase="router_cascade", logger=logger)

print(
    f"\nDone. Total estimated cost: ${cost_tracker.total_cost_usd:.4f} of "
    f"${BUDGET_USD:.2f} budget. All results logged to Supabase."
)