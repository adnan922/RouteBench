# Phase 1 Findings — RouteBench

Generated automatically by `scripts/analyze_phase1.py`. Data tables below are
computed directly from Supabase; the interpretation section at the bottom is
intentionally left for you to fill in.

## Fixed strategies (test split, n=212 tasks)

| Strategy | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| Always-cheap | 73.6% | $0.0043 | 2.13s |
| Always-expensive | 94.8% | $0.0571 | 1.41s |
| Random routing | 82.1% | $0.0324 | 1.00s |
| Cascade (threshold=0.5, actual run) | 75.9% | $0.0055 | 1.84s |

## Cascade Pareto frontier (reconstructed across thresholds, zero extra API calls)

| Threshold | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| 0.00 | 73.6% | $0.0043 | 2.13s |
| 0.05 | 73.6% | $0.0043 | 2.13s |
| 0.10 | 73.6% | $0.0043 | 2.13s |
| 0.15 | 73.6% | $0.0043 | 2.13s |
| 0.20 | 73.6% | $0.0043 | 2.13s |
| 0.25 | 73.6% | $0.0043 | 2.13s |
| 0.30 | 73.6% | $0.0043 | 2.13s |
| 0.35 | 73.6% | $0.0047 | 2.15s |
| 0.40 | 73.6% | $0.0051 | 2.12s |
| 0.45 | 73.6% | $0.0054 | 2.13s |
| 0.50 | 73.6% | $0.0058 | 2.10s |
| 0.55 | 73.6% | $0.0059 | 2.10s |
| 0.60 | 74.1% | $0.0069 | 2.12s |
| 0.65 | 74.5% | $0.0088 | 2.10s |
| 0.70 | 76.9% | $0.0134 | 2.05s |
| 0.75 | 88.7% | $0.0400 | 1.40s |
| 0.80 | 93.4% | $0.0541 | 1.40s |
| 0.85 | 94.3% | $0.0564 | 1.41s |
| 0.90 | 94.8% | $0.0571 | 1.41s |
| 0.95 | 94.8% | $0.0571 | 1.41s |
| 1.00 | 94.8% | $0.0571 | 1.41s |

See `phase1_pareto_frontier.png` for the visual.

## Router confidence quality

- **Brier score:** 0.1960 (0 = perfect, 0.25 = no better than a coin flip)
- **Discrimination AUC:** 0.5665 (0.5 = no better than random, 1.0 = perfect)

| Confidence bucket | n tasks | Mean predicted | Actual accuracy |
|---|---|---|---|
| [0.00-0.20) | 0 | 0.00 | 0.00 |
| [0.20-0.40) | 3 | 0.35 | 0.67 |
| [0.40-0.60) | 7 | 0.52 | 0.57 |
| [0.60-0.80) | 190 | 0.73 | 0.74 |
| [0.80-1.00) | 12 | 0.84 | 0.75 |

## RQ1: Can a calibrated cascade approach strong-model quality at lower cost?

*(Your interpretation goes here.)*
