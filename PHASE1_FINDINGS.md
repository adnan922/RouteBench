# Phase 1 Findings — RouteBench

Generated automatically by `scripts/analyze_phase1.py`. Data tables below are
computed directly from Supabase; the interpretation section at the bottom is
intentionally left for you to fill in.

## Fixed strategies (test split, n=24 tasks)

| Strategy | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| Always-cheap | 66.7% | $0.0006 | 0.81s |
| Always-expensive | 100.0% | $0.0071 | 1.38s |
| Random routing | 79.2% | $0.0042 | 0.94s |
| Cascade (threshold=0.5, actual run) | 62.5% | $0.0005 | 0.85s |

## Cascade Pareto frontier (reconstructed across thresholds, zero extra API calls)

| Threshold | Accuracy | Total Cost | Mean Latency |
|---|---|---|---|
| 0.00 | 66.7% | $0.0006 | 0.81s |
| 0.05 | 66.7% | $0.0006 | 0.81s |
| 0.10 | 66.7% | $0.0006 | 0.81s |
| 0.15 | 66.7% | $0.0006 | 0.81s |
| 0.20 | 66.7% | $0.0006 | 0.81s |
| 0.25 | 66.7% | $0.0006 | 0.81s |
| 0.30 | 66.7% | $0.0006 | 0.81s |
| 0.35 | 66.7% | $0.0006 | 0.81s |
| 0.40 | 66.7% | $0.0006 | 0.81s |
| 0.45 | 66.7% | $0.0006 | 0.81s |
| 0.50 | 66.7% | $0.0006 | 0.81s |
| 0.55 | 66.7% | $0.0006 | 0.81s |
| 0.60 | 66.7% | $0.0006 | 0.81s |
| 0.65 | 66.7% | $0.0006 | 0.81s |
| 0.70 | 66.7% | $0.0008 | 0.78s |
| 0.75 | 66.7% | $0.0012 | 0.86s |
| 0.80 | 83.3% | $0.0041 | 1.18s |
| 0.85 | 95.8% | $0.0066 | 1.31s |
| 0.90 | 100.0% | $0.0071 | 1.38s |
| 0.95 | 100.0% | $0.0071 | 1.38s |
| 1.00 | 100.0% | $0.0071 | 1.38s |

See `phase1_pareto_frontier.png` for the visual.

## RQ1: Can a calibrated cascade approach strong-model quality at lower cost?

The cascade produces a genuine, monotonic cost-accuracy tradeoff, but the router's confidence estimates cluster tightly rather than discriminating smoothly across the full range — over 60% of threshold values behave identically to always-cheap. At comparable cost, the cascade modestly outperforms random routing (83.3% vs 79.2% at ~$0.004), though with only 24 test tasks that gap is a single flipped task and shouldn't be read as a robust result. A more concerning finding: the live cascade run at threshold=0.5 (62.5% accuracy) doesn't match the reconstructed frontier at the same threshold (66.7%) — the two should be identical, and the mismatch points to model non-determinism (no fixed temperature/seed) undermining the reconstruction's core assumption that a task routed to a given tier always produces that tier's baseline outcome. The router's narrow confidence clustering is plausibly explained by training on only 56 examples against a 393-dimensional feature vector — a steep enough ratio to invite overfitting or a degenerate decision boundary rather than genuine discrimination.