# Phase 1 Findings — RouteBench

Generated automatically by `scripts/analyze_phase1.py`. Data tables below are
computed directly from Supabase; the interpretation section at the bottom is
intentionally left for you to fill in.

## Fixed strategies (test split, n=150 tasks)

| Strategy | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| Always-cheap | 70.7% | $0.0029 | 2.33s |
| Always-expensive | 94.7% | $0.0406 | 1.66s |
| Random routing | 82.0% | $0.0218 | 0.95s |
| Cascade (threshold=0.5, actual run) | 80.0% | $0.0097 | 1.78s |

## Cascade Pareto frontier (reconstructed across thresholds, zero extra API calls)

| Threshold | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| 0.00 | 70.7% | $0.0029 | 2.33s |
| 0.05 | 70.7% | $0.0029 | 2.33s |
| 0.10 | 70.7% | $0.0029 | 2.33s |
| 0.15 | 70.7% | $0.0029 | 2.33s |
| 0.20 | 70.7% | $0.0038 | 2.31s |
| 0.25 | 70.7% | $0.0045 | 2.32s |
| 0.30 | 70.7% | $0.0054 | 2.25s |
| 0.35 | 70.7% | $0.0066 | 2.27s |
| 0.40 | 70.7% | $0.0068 | 2.26s |
| 0.45 | 72.0% | $0.0076 | 2.24s |
| 0.50 | 72.0% | $0.0096 | 2.23s |
| 0.55 | 72.0% | $0.0109 | 2.18s |
| 0.60 | 75.3% | $0.0140 | 2.14s |
| 0.65 | 78.0% | $0.0162 | 2.16s |
| 0.70 | 80.0% | $0.0196 | 2.13s |
| 0.75 | 82.7% | $0.0232 | 2.07s |
| 0.80 | 88.0% | $0.0267 | 1.94s |
| 0.85 | 92.7% | $0.0344 | 1.76s |
| 0.90 | 94.7% | $0.0398 | 1.66s |
| 0.95 | 94.7% | $0.0406 | 1.66s |
| 1.00 | 94.7% | $0.0406 | 1.66s |

See `phase1_pareto_frontier.png` for the visual.

## Router confidence quality

- **Brier score:** 0.2382 (0 = perfect, 0.25 = no better than a coin flip)
- **Discrimination AUC:** 0.5272 (0.5 = no better than random, 1.0 = perfect)

| Confidence bucket | n tasks | Mean predicted | Actual accuracy |
|---|---|---|---|
| [0.00-0.20) | 2 | 0.18 | 1.00 |
| [0.20-0.40) | 7 | 0.31 | 1.00 |
| [0.40-0.60) | 24 | 0.51 | 0.58 |
| [0.60-0.80) | 58 | 0.71 | 0.67 |
| [0.80-1.00) | 59 | 0.85 | 0.75 |

## RQ1: Can a calibrated cascade approach strong-model quality at lower cost?

*(Your interpretation goes here.)*
