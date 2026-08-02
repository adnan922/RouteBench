"""Phase 1 analysis — run once the sweep has completed.

    docker compose run app python -m scripts.analyze_phase1

Pulls every logged run from Supabase, reconstructs the full cost/quality
Pareto frontier for the cascade across many confidence thresholds (no new
API calls needed — see src/eval/analysis.py for why), computes calibration/
discrimination diagnostics, prints a summary, saves a plot, and writes
PHASE1_FINDINGS.md with the data tables filled in.

The findings file's interpretation section is deliberately left blank for
you to fill in — the tables are objective and safe to auto-generate, but
the actual judgment call about what the numbers mean belongs to you, not
a script that's never seen the results before this exact run.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # no display available in a container
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

from src.db.supabase_client import SupabaseLogger  # noqa: E402
from src.eval.analysis import RunRecord, pareto_frontier, summarize  # noqa: E402
from src.eval.calibration import brier_score, calibration_table, discrimination_auc  # noqa: E402


def to_records(rows: list[dict]) -> dict[str, RunRecord]:
    return {
        row["task_id"]: RunRecord(
            task_id=row["task_id"],
            correct=row["correct"],
            estimated_cost_usd=row["estimated_cost_usd"] or 0.0,
            latency_s=row["latency_s"],
        )
        for row in rows
    }


logger = SupabaseLogger()

print("Fetching results from Supabase...")
cheap_rows = logger.fetch_by_phase("router_baseline_cheap")
expensive_rows = logger.fetch_by_phase("router_baseline_expensive")
random_rows = logger.fetch_by_phase("router_baseline_random")
cascade_rows = logger.fetch_by_phase("router_cascade")

if not cheap_rows or not expensive_rows or not cascade_rows:
    raise SystemExit(
        "Missing results for one or more phases — run scripts/run_phase1_sweep.py "
        "to completion first."
    )

cheap_by_task = to_records(cheap_rows)
expensive_by_task = to_records(expensive_rows)
confidence_by_task = {
    row["task_id"]: row["metadata"]["router_confidence"]
    for row in cascade_rows
    if row.get("metadata", {}).get("router_confidence") is not None
}

cheap_summary = summarize("Always-cheap", list(cheap_by_task.values()))
expensive_summary = summarize("Always-expensive", list(expensive_by_task.values()))
random_summary = summarize("Random routing", list(to_records(random_rows).values()))
cascade_actual_summary = summarize(
    "Cascade (threshold=0.5, actual run)", list(to_records(cascade_rows).values())
)

print("\n--- Fixed strategies ---")
for s in [cheap_summary, expensive_summary, random_summary, cascade_actual_summary]:
    print(
        f"{s.name}: accuracy={s.accuracy:.1%}, total_cost=${s.total_cost_usd:.4f}, "
        f"mean_latency={s.mean_latency_s:.2f}s"
    )

frontier = pareto_frontier(cheap_by_task, expensive_by_task, confidence_by_task)

print("\n--- Cascade Pareto frontier (reconstructed, zero new API calls) ---")
for point in frontier:
    print(
        f"threshold={point['threshold']:.2f}: accuracy={point['accuracy']:.1%}, "
        f"total_cost=${point['total_cost_usd']:.4f}"
    )

# --- Calibration / discrimination diagnostics ---
brier = brier_score(cheap_by_task, confidence_by_task)
auc = discrimination_auc(cheap_by_task, confidence_by_task)
cal_table = calibration_table(cheap_by_task, confidence_by_task)

print("\n--- Router confidence quality ---")
print(f"Brier score: {brier:.4f} (0=perfect, 0.25=no better than a coin flip)")
print(f"Discrimination AUC: {auc:.4f} (0.5=no better than random, 1.0=perfect)")
print("Calibration table (predicted confidence bucket vs actual cheap-tier accuracy):")
for bucket in cal_table:
    print(
        f"  [{bucket.range_low:.2f}-{bucket.range_high:.2f}) n={bucket.n_tasks:3d}  "
        f"predicted={bucket.mean_predicted_confidence:.2f}  actual={bucket.empirical_accuracy:.2f}"
    )

# --- Plot ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

frontier_costs = [p["total_cost_usd"] for p in frontier]
frontier_acc = [p["accuracy"] for p in frontier]
ax1.plot(frontier_costs, frontier_acc, marker="o", markersize=3, label="Cascade (threshold sweep)")
ax1.scatter(
    [cheap_summary.total_cost_usd], [cheap_summary.accuracy],
    color="tab:blue", s=100, label="Always-cheap", zorder=5,
)
ax1.scatter(
    [expensive_summary.total_cost_usd], [expensive_summary.accuracy],
    color="tab:red", s=100, label="Always-expensive", zorder=5,
)
ax1.scatter(
    [random_summary.total_cost_usd], [random_summary.accuracy],
    color="tab:gray", s=100, label="Random", zorder=5,
)
ax1.set_xlabel("Total cost (USD)")
ax1.set_ylabel("Accuracy")
ax1.set_title("Cost vs Accuracy — Phase 1 Router")
ax1.legend()
ax1.grid(alpha=0.3)

frontier_latency = [p["mean_latency_s"] for p in frontier]
ax2.plot(frontier_costs, frontier_latency, marker="o", markersize=3, color="tab:purple")
ax2.set_xlabel("Total cost (USD)")
ax2.set_ylabel("Mean latency (s)")
ax2.set_title("Cost vs Latency")
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("phase1_pareto_frontier.png", dpi=150)
print("\nSaved plot to phase1_pareto_frontier.png")

# --- Findings file ---
frontier_table = "\n".join(
    f"| {p['threshold']:.2f} | {p['accuracy']:.1%} | ${p['total_cost_usd']:.4f} | {p['mean_latency_s']:.2f}s |"
    for p in frontier
)
calibration_table_md = "\n".join(
    f"| [{b.range_low:.2f}-{b.range_high:.2f}) | {b.n_tasks} | {b.mean_predicted_confidence:.2f} | {b.empirical_accuracy:.2f} |"
    for b in cal_table
)

findings_md = f"""# Phase 1 Findings — RouteBench

Generated automatically by `scripts/analyze_phase1.py`. Data tables below are
computed directly from Supabase; the interpretation section at the bottom is
intentionally left for you to fill in.

## Fixed strategies (test split, n={cheap_summary.n_tasks} tasks)

| Strategy | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| Always-cheap | {cheap_summary.accuracy:.1%} | ${cheap_summary.total_cost_usd:.4f} | {cheap_summary.mean_latency_s:.2f}s |
| Always-expensive | {expensive_summary.accuracy:.1%} | ${expensive_summary.total_cost_usd:.4f} | {expensive_summary.mean_latency_s:.2f}s |
| Random routing | {random_summary.accuracy:.1%} | ${random_summary.total_cost_usd:.4f} | {random_summary.mean_latency_s:.2f}s |
| Cascade (threshold=0.5, actual run) | {cascade_actual_summary.accuracy:.1%} | ${cascade_actual_summary.total_cost_usd:.4f} | {cascade_actual_summary.mean_latency_s:.2f}s |

## Cascade Pareto frontier (reconstructed across thresholds, zero extra API calls)

| Threshold | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
{frontier_table}

See `phase1_pareto_frontier.png` for the visual.

## Router confidence quality

- **Brier score:** {brier:.4f} (0 = perfect, 0.25 = no better than a coin flip)
- **Discrimination AUC:** {auc:.4f} (0.5 = no better than random, 1.0 = perfect)

| Confidence bucket | n tasks | Mean predicted | Actual accuracy |
|---|---|---|---|
{calibration_table_md}

## RQ1: Can a calibrated cascade approach strong-model quality at lower cost?

*(Your interpretation goes here.)*
"""

with open("PHASE1_FINDINGS.md", "w") as f:
    f.write(findings_md)

print("Wrote PHASE1_FINDINGS.md")