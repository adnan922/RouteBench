# RouteBench — Progress Tracker

*Last updated: 2026-08-09 — update this line every time you touch this file.*

This is the living half of the project documentation. `PROJECT.md` explains what the project is and why; this file tracks where it actually stands right now. If you're handing this project to an AI assistant, share both — but if you only have room for one, share this one and it can ask for `PROJECT.md` if it needs the deeper why.

---

## Current Status (read this first)

**Phase:** 1 — Router / Cascade, complete, re-run clean on 2026-08-09 after a data-hygiene bug (see below). Hand-crafted-features ablation run for real and answered. Phase 2 not yet started.

**Last thing done:** Discovered the Supabase `runs` table had two sweeps' worth of data mixed together with no way to tell them apart (the table only ever inserts, nothing was ever cleared between runs) — this made the first real ablation result (`+0.0547`, "hand-crafted wins") untrustworthy, since the two routers it compared had silently been scored against different-sized, different test sets (150 vs 384 vs 212 rows across various phases). Fixed properly: cleared `runs` with `delete from runs;` (findings from the prior sweep were already safely captured as text in `PHASE1_FINDINGS.md`, so nothing was lost), then ran one single, complete, fresh sweep (`scripts.run_phase1_sweep` — Train: 350 tasks, Test: 150 tasks, $0.0820 total cost, all four stages completed and printed). Re-ran `scripts.analyze_phase1` and `scripts.ablation_handcrafted_features` against that clean data — both routers now confirmed scored against the identical 150 test-split rows ("Scoring both routers against 150 test-split rows" printed once, for both).

**Clean ablation result:** original router (393 features) AUC 0.5272, hand-crafted-only (9 features) AUC 0.5139 — a −0.0133 gap, within noise on 150 tasks. Read plainly: the 384-dim embedding isn't clearly helping, but it isn't clearly hurting either — both versions land in roughly the same (weak) place, barely above a coin flip. This shifts suspicion away from "which features" and toward either the classifier (plain logistic regression may be too simple) or the underlying difficulty of the prediction task itself.

**New discrepancy found in the same clean run — now resolved, not a bug:** the cascade's own actual accuracy at threshold=0.5 (80.0%) didn't match the reconstructed frontier's accuracy at threshold=0.50 (72.0%) — an 8-point gap. Two SQL queries resolved it fully. Query 2 (routing-rule check) confirmed no logic bug: every "cheap"-routed task had confidence ≥0.5003, every "expensive"-routed task had confidence ≤0.4901 — clean boundary, `cascade.py` and `analysis.py` agree. Query 1 (correctness comparison) found the real cause: 30 of 150 tasks (20%) got a *different* correct/incorrect grade in the cascade run than in the baseline run, for the identical question asked of the identical model. The net direction of those 30 flips (21 cascade-better, 9 cascade-worse) works out to exactly +12 tasks = +8.0 percentage points — a complete, exact match to the observed gap. Confirmed via web search that this is a real, well-documented limitation of LLM APIs generally: temperature=0 does not guarantee identical outputs across separate calls (OpenAI, Anthropic, and Google all say so explicitly in their own docs; underlying causes include GPU batching effects and floating-point non-associativity, not anything specific to this codebase). Since `run_single()` is the literal same function used by both the baseline run and the cascade's cheap-tier calls, this rules out a code-path inconsistency — it's genuine model-level nondeterminism. **Verdict: not a bug, and not something to fix in code.** It's a real methodological finding: the zero-extra-cost Pareto reconstruction technique assumes the model would answer identically if asked twice, and that assumption has a measurable ~20% failure rate, translating to a non-trivial approximation error (~8 points at this sample size) against a live re-run. Worth stating plainly in the eventual Phase 1 writeup as a documented limitation, not glossed over.

**Also corrected on the record this session (2026-08-02):** earlier notes had implied Run 2's AUC=0.5665 result came from a PCA-reduced classifier. That's wrong — the actual `classifier.py` used in both Run 1 and Run 2 was plain `StandardScaler + LogisticRegression`, no `ColumnTransformer`, no `PCA`, full 393 raw features every time. PCA support exists in the current `classifier.py` but has never been exercised by a real sweep. See Decision Log 2026-08-02.

**Next thing to do:** Phase 1's open threads are now genuinely closed out (ablation answered, gap explained) — decide whether to (a) spend a bit more time on Phase 1 stretch items (an actual PCA-enabled sweep, or the RQ1 plain-language interpretation section in `PHASE1_FINDINGS.md`, still marked "your interpretation goes here"), or (b) move on to starting Phase 2 (the pharmacy agent). Either is reasonable — Phase 1's core deliverables and its main open questions are both done.
**Blocked on:** Nothing.

---

## Kanban Board

Move items between sections as you work. Keep **In Progress** short — 1-2 items at a time is the point of a WIP limit; a long "in progress" list is a sign of context-switching, not productivity.

### Backlog

**Phase 0 — Setup**

*Done (scaffolded and syntax/logic-tested this session — see repo zip):*
- [x] Repo structure, README, LICENSE, `.gitignore`
- [x] Docker Compose + Dockerfile
- [x] Shared `OpenAICompatibleProvider` base class + `GroqProvider` / `SambaNovaProvider` thin subclasses
- [x] Supabase client wrapper (`log_run`, `ping_heartbeat`)
- [x] `sql/schema.sql` — `runs` table (covers both Phase 1 and Phase 2 logging) + `heartbeat` table
- [x] GitHub Actions: CI (lint + unit tests) and a scheduled Supabase keep-alive ping
- [x] `scripts/verify_setup.py` — one command to confirm all three services are reachable
- [x] Finalize Phase 1 dataset: GSM8K subset + MMLU-style factual subset
- [x] Finalize Phase 2 domain: Retail Pharmacy Inventory & Procurement (spec in `PROJECT.md` §3.1)

*Requires you specifically (accounts/credentials/physical server — not something an AI assistant can do for you):*
- [x] Confirm the GitHub repo is created and pushed — done
- [x] Get a Groq API key, add to `.env` — confirmed working (2.54s response)
- [x] Get a SambaNova Cloud API key, add to `.env` — confirmed working (1.59s response)
- [x] Create a Supabase project, run `sql/schema.sql`, add URL/key to `.env` — confirmed working (insert + upsert both succeeded)
- [x] Add `SUPABASE_URL` / `SUPABASE_KEY` as GitHub repo secrets — done
- [x] On the home server: `docker compose build`, then `docker compose run app python -m scripts.verify_setup` — all three services PASS

**Phase 1 — Router / Cascade**
- [x] Benchmark dataset (GSM8K + MMLU-style mix) + grading logic — implemented, unit-tested (18 tests), and network-verified end-to-end on the real home server
- [x] Baseline runners: always-cheap, always-expensive, random-routing — implemented, unit-tested (10 tests via a fake provider), and integration-verified end-to-end on the real home server (real Groq + SambaNova calls, correctly graded)
- [x] Query feature extraction (fastembed embeddings + hand-crafted features) — implemented, 12 unit tests passing on hand-crafted logic; embedding tests need network verification on your end
- [x] Train initial router classifier (logistic regression baseline) — done
- [x] Calibrate confidence (Platt scaling or isotonic regression, held-out split) — done via CalibratedClassifierCV, both methods supported and tested
- [x] Implement two-stage cascade (cheap model first, escalate on low calibrated confidence) — done, 5 tests passing (fake router + fake provider)
- [x] Full sweep across benchmark set, every run logged to Supabase — orchestration built (`src/eval/sweep.py`, `scripts/run_phase1_sweep.py`), wiring fully unit-tested (5 tests); the real end-to-end run against live APIs hasn't happened yet — that's the next thing to actually do
- [x] Compute + plot cost-quality-latency Pareto frontier vs. baselines — reconstructed across all thresholds from data already collected, zero new API calls (`src/eval/analysis.py`, `scripts/analyze_phase1.py`)
- [x] Write up Phase 1 findings — auto-generated data tables in `PHASE1_FINDINGS.md`, interpretation section deliberately left for you
- [x] Add PCA on embedding columns to `classifier.py` to address the features-to-samples ratio — code written, unit-tested, **but never actually run in a real sweep** (see Decision Log 2026-08-02 correction) — treat as "built, not yet validated," not "done and proven" like everything else in this list
- [x] Hand-crafted-features-only ablation built (`src/eval/ablation.py`, `scripts/ablation_handcrafted_features.py`) — trains a router on just the 9 hand-crafted features, compares its AUC/Brier against the original router's already-logged confidence, zero new API calls. 14 offline tests passing.
- [x] Added missing test coverage for `train_router()`'s zero-embedding-columns path (`test_classifier.py::TestZeroEmbeddingColumns`, 5 tests) — flagged by PM review as untested before the ablation could be trusted; includes a mock-based check that `PCA` is provably never instantiated when all input columns are hand-crafted, plus a contrast test confirming the mock actually discriminates (PCA *is* called in the normal mixed-feature case)
- [x] Ran `scripts/ablation_handcrafted_features.py` for real — first attempt (2026-08-02) was invalid (see below), re-run clean on 2026-08-09 after fixing the underlying data issue. Result: AUC 0.5272 (original) vs 0.5139 (hand-crafted-only) — within noise, embedding isn't clearly helping or hurting on this benchmark
- [x] **Found and fixed a real data-hygiene bug**: Supabase's `runs` table only ever inserts, so two different sweeps' results were silently mixed together with no way to distinguish them — the first ablation run compared the two routers against different-sized test sets (150 vs 384 vs 212 rows) without either router or the analysis code noticing. Fixed by clearing the table (`delete from runs;`) and re-running one single clean sweep end-to-end. **Standing rule going forward: always `delete from runs;` before a fresh full sweep, unless a deliberate reason exists to keep multiple sweeps' data side by side (and if so, tag them distinguishably — the `phase` column alone doesn't do this, since the same phase name gets reused sweep to sweep).**
- [x] **Diagnosed the 8-point actual-vs-reconstructed cascade accuracy gap** — fully explained, not a bug: 20% of tasks got a different correctness grade between the baseline call and the cascade call for the identical question/model, a real and well-documented LLM API limitation (temp=0 doesn't guarantee determinism, per OpenAI/Anthropic/Google's own docs). The net direction of those flips accounts for the gap exactly (+12 tasks = +8.0pp). Routing-rule logic itself confirmed correct (clean 0.5 threshold boundary, no overlap). Documented as a methodological limitation to state plainly in the Phase 1 writeup, not a code fix.
- [ ] Write the RQ1 interpretation section in `PHASE1_FINDINGS.md` (still says "Your interpretation goes here") — now that the router's discrimination weakness (AUC ~0.53) and the reconstruction technique's ~20% self-disagreement limitation are both understood, this can actually be written honestly
- [ ] *Optional/stretch, deferred:* add a prompted-LLM router as a second variant for comparison
- [ ] *Optional, given the ablation came back "within noise":* an actual PCA-enabled sweep, or an embeddings-only-no-PCA comparison — still open, but lower priority now that swapping features barely moved AUC at all; the classifier itself or the task's inherent difficulty look like more promising places to look next, if this gets revisited at all before starting Phase 2

**Phase 2 — Agent Reliability Benchmark**
- [x] Design mini tool-use domain — DONE: Retail Pharmacy Inventory & Procurement, see `PROJECT.md` §3.1
- [ ] Implement mock DB fixtures (`inventory`, `suppliers`, `orders`)
- [ ] Implement the 5 domain tools as Python functions
- [ ] Write out all 10-15 tasks with automated pass/fail checkers against final DB state
- [ ] Implement simulated user (LLM-driven, tau-bench-style)
- [ ] Implement the agent's tool-calling loop (single fixed model first, as a baseline)
- [ ] Implement pass^k scoring harness (k independent trials per task)
- [ ] Wire the Phase 1 router into the agent's per-step model choice
- [ ] Run always-cheap vs. always-expensive vs. routed agent, all scored on pass^k
- [ ] *Stretch:* swap the simulated-user model, remeasure, quantify sensitivity (RQ3)
- [ ] Write up Phase 2 findings

**Phase 3 — Synthesis & Showcase**
- [ ] Build results dashboard (Vercel, reads from Supabase)
- [ ] Trim `PROJECT.md` into a public-facing `README.md`
- [ ] Write technical article
- [ ] Write LinkedIn post
- [ ] Reproducibility check: fresh clone → documented steps → same results

**Later / Maybe** *(new ideas land here, not directly in an active phase)*
- [ ]

### In Progress
*(nothing yet)*

### Blocked
*(nothing yet)*

### Done
*(nothing yet)*

---

## Definition of Ready / Definition of Done

**Before starting a task (Ready):**
- [ ] Outcome is clear and testable
- [ ] Anything it depends on is already resolved
- [ ] You know which files/modules it touches

**Before marking a task done (Done):**
- [ ] Runs from a clean environment without errors
- [ ] Result is logged (Supabase and/or committed to the repo)
- [ ] Decision Log updated if a non-obvious choice was made
- [ ] Dev Log entry added
- [ ] *(phase-ending tasks only)* findings written up in plain language, not just left as code and numbers

---

## Decision Log

Lightweight ADRs — every non-obvious choice, logged so you (or an AI assistant) never have to guess *why* later.

| Date | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 2026-07-15 | Rejected local GPU serving (vLLM on Colab T4) as the project | Fragile on free-tier hardware, didn't differentiate from typical tutorial projects | Persisting with the original Colab/vLLM benchmarking plan |
| 2026-07-15 | Rejected RAG as the project | Market-saturated portfolio pattern; wanted differentiation | Self-hosted personal RAG assistant (fully scoped, then set aside) |
| 2026-07-15 | Use Groq + SambaNova as two remote model tiers instead of any local serving | Home server (4GB RAM, no usable GPU) can't serve models; both providers have genuinely free tiers | Local Ollama/llama.cpp serving |
| 2026-07-15 | Combine router + agent-reliability-benchmark into one project | Both need "LLM call inside a loop" infrastructure anyway; combining sharpens the question into whether routing preserves reliability, not just cost | Building only the router; building only the benchmark |
| 2026-07-15 | Methodology: Kanban-managed Iterative & Incremental Development | Solo developer, no team to run sprint ceremony for; parts of the scope (RQ2) are genuinely uncertain going in | Scrum, Waterfall, Spiral |
| 2026-07-15 | No pgvector / vector store this project | No RAG component this time — plain Postgres tables are sufficient for run logs | Reusing the vector-store setup from the earlier RAG plan |
| 2026-07-15 | Phase 1 dataset: GSM8K subset + MMLU-style factual subset | Confirmed as proposed — gives the router genuine difficulty variance, both splits auto-gradable without an LLM judge | — |
| 2026-07-15 | Phase 2 domain: Retail Pharmacy Inventory & Procurement, scoped to back-office logistics only | Clean deterministic pass/fail via final DB state; avoids clinical/regulatory complexity; plausibly useful as a real small-business prototype | Generic e-commerce or IT-helpdesk domain; tau-bench's own retail/airline domains |
| 2026-07-15 | Provider clients share one `OpenAICompatibleProvider` base class instead of two independent implementations | Groq and SambaNova are both genuinely OpenAI-compatible endpoints (confirmed against current docs) — a base_url/key/model swap is the only real difference | Two separate, duplicated client implementations |
| 2026-08-02 | **Correction:** retracted the earlier claim that Run 2's AUC=0.5665 result came from a PCA-reduced classifier | Re-read the actual `classifier.py` that ran both Run 1 and Run 2: plain `StandardScaler + LogisticRegression`, no `ColumnTransformer`, no `PCA` anywhere. PCA support was written into `classifier.py` at some point (`n_handcrafted_features`/`n_pca_components` params, `ColumnTransformer` splitting embedding vs. hand-crafted columns) but has never actually been exercised by a real sweep. The real, still-valid finding from Run 2 is narrower: going from ~56 to ~500 training examples (still 393 raw features, no reduction) didn't meaningfully move AUC — that argues against "not enough data" as the explanation, but says nothing about whether PCA specifically would help, since PCA was never in the loop | Leaving the earlier (wrong) framing uncorrected in the historical record |
| 2026-08-02 | Ablation compares "393 raw features (embedding + hand-crafted, no reduction)" vs. "9 hand-crafted features only," not "PCA vs. no-PCA" | Matches what actually ran — the original router's logged `router_cascade` confidence scores came from the no-PCA classifier, so comparing against those is only honest under the correct framing | Framing it as a PCA test (would have been actively misleading, given the correction above) |
| 2026-08-09 | Clear the Supabase `runs` table (`delete from runs;`) before every fresh full sweep, rather than letting sweeps accumulate indefinitely | `log_run()` only ever inserts — nothing distinguishes one sweep's rows from another's beyond the `phase` column, which gets reused identically sweep to sweep. A sweep run on 2026-07-19-ish and a bigger one run roughly a week later both logged rows under the same phase names with no way to tell them apart. The first ablation attempt (2026-08-02) silently compared the two routers against different-sized test sets pulled from different sweeps as a direct result, producing an untrustworthy "+0.0547, hand-crafted wins" result that had to be thrown out. Findings are captured as plain text in `PHASE1_FINDINGS.md`/`PHASE1_ABLATION_FINDINGS.md` after each real analysis run, so clearing the underlying rows doesn't lose anything already written down | Adding a `sweep_id` or timestamp-based tag to every row instead of clearing the table — more robust long-term, but bigger change; deferred unless this bites again |
| 2026-08-09 | Accepted the 8-point actual-vs-reconstructed cascade gap as a genuine, documented LLM-API limitation rather than a bug to fix — no code changes made | Root-caused via two SQL queries: the routing threshold rule was confirmed clean (no boundary overlap), and the correctness-comparison query showed the identical question, asked of the identical model via the identical shared `run_single()` code path, got a different correct/incorrect grade 20% of the time between the baseline call and the cascade call. The net direction of those flips accounted for the observed gap exactly (+12 tasks = +8.0pp, matching 80.0% vs 72.0% precisely). Confirmed via web search that temperature=0 not guaranteeing determinism is standard, explicitly documented behavior across OpenAI, Anthropic, and Google's own APIs — not something specific to Groq or this codebase | Treating it as a bug and trying to "fix" reconstruction accuracy further (would have been chasing a phantom — there's no code-level fix for inherent model nondeterminism); re-running with a fixed seed (providers here don't reliably support one for greedy decoding, per the same research — seeds help mid-temperature sampling, not temp=0 disagreement) |

---

## Hypothesis Log

Prediction logged *before* running the experiment; result filled in *after*. The point is to catch yourself if you'd quietly rationalize whatever the data shows.

| Date | Question | Prediction (before) | Result (after) |
|---|---|---|---|
| — | RQ1: calibrated cascade router | Should approach the strong tier's quality at meaningfully lower cost, similar in shape to published cost-quality frontiers — exact numbers will differ since the model pool and benchmark are custom | *pending* |
| — | RQ2: does routing hurt agent reliability (pass^k)? | Genuinely uncertain going in — cheaper per-step models could add variance, or a well-calibrated router could hold steady. This is the real open question of the project. | *pending* |
| — | RQ3 (stretch): simulated-user sensitivity | Expect measurable shifts in pass^k when the simulated-user model changes, based on prior critique in the literature | *pending* |
| 2026-08-02 | Ablation: does the router's 384-dim embedding half meaningfully outperform 9 hand-crafted features alone at discriminating cheap-tier success? | Genuinely uncertain — the flat Pareto frontier and AUC=0.5665 could mean the embedding isn't adding signal (hand-crafted-only ties or wins), or that it's carrying real signal current preprocessing is losing (hand-crafted-only loses clearly) | **First attempt (2026-08-02) invalidated** — the two routers were accidentally scored against different, mismatched test sets due to a Supabase data-hygiene bug (see Decision Log). **Re-run clean on 2026-08-09** on one single 150-task test split for both: original (393 features) AUC 0.5272, hand-crafted-only (9 features) AUC 0.5139 — a −0.0133 gap, within noise. Neither wins clearly; the embedding isn't obviously carrying signal, but this doesn't prove it's useless (raw embeddings without concatenation, or a different classifier, remain untested). The bigger open thread now is a separate, newly-found 8-point gap between the cascade's actual accuracy and the reconstructed frontier at the same threshold — under investigation. |

---

## Dev Log

Freeform, dated, append-only. Write what actually happened, including dead ends — those are exactly what an AI assistant (or future you) needs to avoid repeating them.

**2026-07-15 — Kickoff**
Planning phase complete. Journey: started with a local vLLM-on-Colab serving benchmark, hit repeated environment friction, abandoned it. Pivoted to a self-hosted personal RAG assistant, fully architected, then set aside for being an oversaturated portfolio pattern. Landed on RouteBench: a calibrated LLM router evaluated on cost/quality/latency, combined with an agent built on top of it and evaluated on pass^k reliability rather than one-shot accuracy. Chose Kanban-managed Iterative & Incremental Development as the methodology. `PROJECT.md` and `PROGRESS.md` written. Phase 0 not yet started.

**2026-07-15 — Phase 0 scaffolding**
Confirmed Phase 1 dataset (GSM8K + MMLU-style mix) and Phase 2 domain (Retail Pharmacy Inventory & Procurement, scoped to back-office logistics). Verified Groq's and SambaNova's current OpenAI-compatible base URLs against their docs rather than assuming. Scaffolded the full repo: Docker setup, a shared `OpenAICompatibleProvider` base class with thin Groq/SambaNova subclasses, a Supabase client + schema (`runs` + `heartbeat` tables), GitHub Actions CI and a scheduled keep-alive ping, and `scripts/verify_setup.py`. Everything was syntax-checked, lint-checked, and unit-tested in isolation; live integration tests are marked to skip automatically without real API keys. Handed off as a zip — remaining Phase 0 items all require your own accounts/credentials, which is out of reach for an AI assistant by design.

**2026-07-15 — First real deployment attempt**
`docker compose build` succeeded on the actual home server (~25 min — slow but it works, confirming the hardware handles this fine). `docker compose run app python scripts/verify_setup.py` then hit `ModuleNotFoundError: No module named 'src'` — running a script by file path only puts that script's own directory on `sys.path`, not the project root, so the `from src...` imports couldn't resolve. Fixed by adding `scripts/__init__.py` and switching every invocation to module style (`python -m scripts.verify_setup`), which adds the current working directory to `sys.path` automatically. Applied consistently in `README.md`, both scripts' docstrings, and the keepalive GitHub Action, since it had the identical latent bug and hadn't been run yet. Reproduced the failure and confirmed the fix in isolation before sending it back.

**2026-07-15 — Phase 0 verified end-to-end**
Applied the module-invocation fix; re-ran `docker compose run app python -m scripts.verify_setup` on the real home server. All three services passed: Groq responded in 2.54s, SambaNova in 1.59s, Supabase's insert and heartbeat upsert both succeeded — confirming the schema was applied correctly. Phase 0 is functionally done. Remaining open items are just confirming the GitHub push and adding repo secrets, neither of which blocks starting Phase 1.

**2026-07-16 — Dataset loader verified end-to-end**
Ran `docker compose run app python -m pytest -v -m network` on the home server. First attempt hit `ModuleNotFoundError: No module named 'datasets'` — the image hadn't been rebuilt since `requirements.txt` picked up the new dependency, and `docker compose run` doesn't rebuild automatically. Rebuilt (`docker compose build`), reran, and the real network test passed: GSM8K and MMLU both downloaded and validated in 53s. Documented the rebuild gotcha in the README so it doesn't repeat in Phase 2.

**2026-07-16 — Baseline runners built**
Implemented `run_always_cheap`, `run_always_expensive`, and `run_random`, plus `build_prompt()` which steers models toward a gradable answer format. Introduced `tests/fakes.py` (a `FakeProvider` test double) so the orchestration logic — routing decisions, result packaging, grading integration — is fully unit-tested without touching the network. No new dependencies this time, so no Docker rebuild needed, just the live-mounted code change. Real-API integration tests are written and marked to skip without keys; haven't been run for real yet.

**2026-07-16 — Baseline runners verified end-to-end**
Ran the full suite on the home server. `pytest -m "not integration"`: 29 passed, 4 deselected, 58.91s — confirms all orchestration logic (routing, grading, result packaging) is correct. `pytest -m integration`: 4 passed, 13.32s — real Groq and SambaNova calls, both correctly graded. Baseline runners are done and proven, not just written. Router classifier is next.

**2026-07-16 — Feature extraction built**
Implemented `hand_crafted_features()` (9 lexical signals: length, word count, digit/number/math-operator counts, multiple-choice marker detection, question marks, uppercase ratio) and `QueryEmbedder`, a lazy-loading wrapper around fastembed so importing/constructing it never triggers a network call — only actually embedding does. Also added `combined_features()`/`combined_features_batch()` to concatenate both into the classifier's real input. 12 hand-crafted-feature unit tests all pass with no network needed; caught one real test bug in the process (assumed 4 words in "What is 2 + 2?" — it's actually 5, since "+" is its own whitespace-separated token — fixed the test, not the code). The 6 embedding tests need Hugging Face Hub access to actually verify, same constraint as the dataset loader; they're written and skip gracefully without it, not yet run for real.

**2026-07-16 — Feature extraction verified end-to-end**
Ran the full suite on the home server: 37 unit tests passed (19.72s), and all 6 network-marked tests passed too (84.80s) — the fastembed model downloaded and produced correctly-shaped, deterministic embeddings for real. Feature extraction is fully proven, not just written.

**2026-07-16 — Router classifier built**
Implemented `train_router()` (StandardScaler + LogisticRegression, wrapped in `CalibratedClassifierCV`) and `RouterModel.predict_confidence()`, plus joblib-based save/load. Verified scikit-learn's calibration API before writing code against it — confirmed `estimator=` is current (sklearn 1.2+), not the deprecated `base_estimator=`, which matters since we have 1.9.0 installed. This whole chunk is pure ML on numbers, no network or API keys involved, so all 5 tests ran and passed directly in the dev sandbox — first fully-verified-here chunk since the baseline runners' fake-provider tests.

**2026-07-16 — Cascade and full sweep built**
Implemented `CascadeRouter.decide()` (threshold on calibrated confidence) and `run_cascade()`, plus `src/eval/sweep.py` (train/test split, `train_router_from_baseline()`, `log_results()`) and the runnable entry point `scripts/run_phase1_sweep.py`. Refactored `runners.py`: made `run_single` public and added `query`/`router_confidence` fields to `RunResult`, since cascade runs needed to carry their confidence score through to Supabase. Added `FakeEmbedder`, `FakeRouterModel`, and `FakeSupabaseLogger` to `tests/fakes.py` so the entire cascade+sweep wiring is testable without touching the network — 10 new tests, 52 total, all passing. Ruff caught a real bug immediately: a leftover duplicate `EmbedderLike` class definition from an in-progress edit, fixed before it ever reached a test run. The actual experiment script hasn't been run for real yet — that's next.

**2026-07-17 — Rate limit hit and fixed**
Real sweep run against SambaNova hit `openai.RateLimitError` during the always-expensive baseline (24 test tasks after earlier quota already used in integration testing). Rather than a one-off patch, added retry-with-backoff and proactive per-provider throttling directly to `OpenAICompatibleProvider` (both tunable via env var), added a `GeminiProvider` (Google AI Studio, confirmed OpenAI-compatible endpoint against current docs) as an alternative expensive tier, and a provider registry (`get_provider()`) so which provider plays which role is now env-config, not hardcoded. 11 new tests, all passing, including one that reconstructs the exact `RateLimitError` from the traceback and confirms the retry logic recovers from it. Full suite: 63 passed.

**2026-07-17 — Cost estimation and hard budget guard added**
Built `src/eval/pricing.py` (verified current per-token pricing: Groq $0.05/$0.08, SambaNova $0.60/$1.20, both confirmed against 5+ sources; Gemini had conflicting figures across sources so deliberately used the higher/more conservative $0.30/$2.50 rather than risk underestimating) and `src/eval/budget.py` (`CostTracker`/`BudgetExceededError` — checks before every call, raises once the ceiling is hit). Wired both through `run_single` and all four runners (`run_always_cheap`, `run_always_expensive`, `run_random`, `run_cascade`), each catching the budget error internally and returning whatever completed so far rather than losing progress. `scripts/run_phase1_sweep.py` now has a `BUDGET_USD` env var (default $1.00) and stops cleanly between stages if exceeded, logging a clear message rather than a raw crash. Fixed a subtle alignment issue in `train_router_from_baseline`: if the budget guard stops the training baseline early, features/labels now correctly use only the completed prefix, not the full task list. 18 new tests, 81 total, all passing — including tests that genuinely verify partial-progress preservation, not just that an exception gets raised.

**2026-07-19 — Diagnosed and fixed the real Gemini rate limit**
Screenshot from Google AI Studio's own dashboard showed the actual cause: `gemini-3.5-flash`'s free tier was capped at 20 requests **per day** (RPD 21/20), not a per-minute rate — confirmed by the error's `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`. A 1-1.5 minute delay between calls, as proposed, could not have fixed this — no amount of spacing gets you past a fixed daily total, and the sweep needs well over 20 expensive-tier calls. Added `DailyQuotaExceededError` detection to the provider base class (string-matched against the real error text, tested against it directly) so a daily-quota 429 fails fast instead of burning through 5 retries with exponential backoff pointlessly; wired it into all four runners' graceful-stop-preserve-partial-results handling alongside `BudgetExceededError`. Updated Gemini's default model to `gemini-3.5-flash` (2.5 isn't available to new accounts) and throttle to 15s given an observed 5 RPM limit, and added its real pricing ($1.50/$9.00 per 1M, confirmed). Recommendation going forward: use SambaNova as the expensive tier (RPM-based limits respond to throttling; Gemini's 20/day free-tier cap structurally doesn't). 5 new tests, 86 total, all passing.

**2026-07-19 — Switched expensive tier to Gemini 3.1 Flash Lite**
SambaNova continued failing with the same rate limit even after throttling/retry — not yet root-caused (no new error text shared to diagnose whether it's still RPM, a lingering daily/credit exhaustion from earlier testing, or something else). Given a second Google AI Studio screenshot showing `gemini-3.1-flash-lite`'s free tier at 15 RPM / 250K TPM / 500 RPD — RPD=500 comfortably covers a full sweep, unlike 3.5-flash's 20/day wall — switched the default expensive tier to Gemini Flash Lite. Confirmed the model string and pricing ($0.25/$1.50 per 1M) against 6+ current sources. Only RPM needs throttling here (set to 5s, ~12 RPM effective); TPM=250K is far more headroom than RPM could ever consume at these token volumes, so no separate token-bucket throttle was added — would be complexity with no practical effect. 1 new test, 87 total, all passing. SambaNova's failure is still an open thread if it's worth revisiting later.

**2026-07-19 — Full sweep succeeded; Pareto frontier built**
`scripts/run_phase1_sweep.py` completed end-to-end for real: benchmark loaded, router trained on the 56-task training split, all four strategies (always-cheap, always-expensive, random, cascade) ran against real Groq + Gemini on the 24-task test split, everything logged to Supabase. Total cost: $0.0138 of the $1.00 budget — nowhere close to the ceiling, confirming the budget guard's overhead-free when things go right. Built `src/eval/analysis.py`: reconstructs the cascade's accuracy/cost/latency at 21 different confidence thresholds using only the always-cheap and always-expensive baselines' already-collected results (each test task was run on *both* tiers already, so any threshold's outcome is fully determined by data already in hand) — a full Pareto curve with zero additional API calls. `scripts/analyze_phase1.py` fetches from Supabase, plots cost-vs-accuracy and cost-vs-latency, and writes `PHASE1_FINDINGS.md` with the data tables auto-filled but the RQ1 interpretation deliberately left blank. Verified the plotting and table-generation logic end-to-end with synthetic data standing in for Supabase (can't reach the real database from this sandbox). 10 new tests, 97 total, all passing. Phase 1 is functionally complete — only the optional LLM-prompted-router stretch item remains, deferred.

**2026-08-02 — Hand-crafted-features-only ablation built, and a wrong conclusion corrected**
Re-read the actual `classifier.py` that produced the AUC=0.5665 result and confirmed it has no PCA in it at all — plain `StandardScaler + LogisticRegression`, full 393 raw features. An earlier note in this file had implied the PCA fix was in place for that run; it wasn't. Retracted that framing in the Decision Log rather than leaving it wrong. The finding that survives correction: going from ~56 to ~500 training examples (same 393 raw features, still no reduction) barely moved AUC — evidence against "too little data" as the explanation, but silent on whether PCA specifically would help, since PCA was never actually run.

Built the ablation to test a narrower, answerable question: does the 384-dim embedding half of the input matter, independent of PCA entirely? `src/eval/ablation.py` (pure, offline — no Supabase client, no network) trains a second router using only the 9 hand-crafted features (`train_router()` called with `n_handcrafted_features` equal to the full input width, which makes it compute zero embedding columns and skip the PCA/ColumnTransformer branch) and scores it with the same `brier_score`/`discrimination_auc`/`calibration_table` functions the original router was scored with — reusing the *already-logged* `router_cascade` confidence scores for the original router rather than retraining or re-running it, so both sides of the comparison rest on data that's actually already in Supabase. `scripts/ablation_handcrafted_features.py` is the runnable entry point, writing a separate `PHASE1_ABLATION_FINDINGS.md` so it doesn't clobber the original `PHASE1_FINDINGS.md`.

Before trusting any of this, added the specific test case flagged in review: `train_router()`'s all-hand-crafted path (zero embedding columns) had never actually been exercised by a test, despite being exactly what the ablation depends on. Added `TestZeroEmbeddingColumns` to `test_classifier.py` (5 tests) — trains-without-error, valid confidence range, still discriminates on signal, and (the one that actually matters) a test that patches `PCA` at the import site and asserts it's never instantiated on this path, plus a contrast test on the normal mixed-feature case confirming the same mock *is* called there (so the first test isn't just "PCA is never called, period," passing for the wrong reason). First attempt at the contrast test used a bare `MagicMock` in place of `PCA`, which broke once it actually ran inside a real fitted pipeline — `ColumnTransformer` correctly rejected the mock's non-array output. Fixed by using `wraps=PCA` instead, so the real computation still happens and the call is still counted. All 19 new tests (5 classifier + 14 ablation) run and pass offline in this session.

**2026-08-02 — First real ablation run, later invalidated**
Ran `scripts/ablation_handcrafted_features.py` for real for the first time: original router AUC 0.5665 vs hand-crafted-only AUC 0.6212, a +0.0547 gap read at the time as "hand-crafted-only meaningfully better." This result turned out to be unsound — see the 2026-08-09 entry below for why and how it was fixed. Recorded here for the record, not as a trustworthy finding.

**2026-08-09 — Found the ablation was comparing mismatched data, fixed it, got a clean answer, and found a new open thread**
While reviewing the 2026-08-02 ablation output, noticed the "original router" side reproduced the *exact* Brier/AUC numbers from the old, smaller sweep (212 test tasks), despite the new sweep's `router_baseline_cheap` phase clearly holding 384 rows. Root cause: Supabase's `runs` table only ever inserts — nothing had ever cleared it between sweep runs, so `router_cascade`'s rows were still the *old* sweep's, never overwritten by the new one (the user hadn't run a fresh cascade stage since; they'd been away from the project for about a week and re-ran an old, already-completed sweep's script without realizing the table still held prior data). This meant the ablation's two routers were being scored against different, differently-sized test sets without either the code or the printed output making that visible.

Fixed properly rather than patched around: had the user run `delete from runs;` in the Supabase SQL editor (safe — findings from the prior sweep were already captured as plain text in `PHASE1_FINDINGS.md`), then a single fresh end-to-end sweep (`docker compose run app python -m scripts.run_phase1_sweep`) — completed cleanly in ~30 minutes, all four stages printed, Train: 350 / Test: 150, total cost $0.0820. Re-ran `analyze_phase1` and `ablation_handcrafted_features` against this one clean dataset; confirmed both routers were now scored against the identical 150-row test set ("Scoring both routers against 150 test-split rows" printed once for both, no longer two different counts).

Clean result: original router AUC 0.5272 vs hand-crafted-only AUC 0.5139 — a small, noise-level −0.0133 gap. Read plainly: swapping out 384 of the router's 393 input numbers barely changed anything. This is a more useful finding than the invalidated one — it points away from "which features" as the discrimination problem and toward either the classifier itself or the underlying prediction task's difficulty.

While reading the fresh `analyze_phase1` output, spotted something new and unresolved: the cascade's own actual accuracy at threshold=0.5 was 80.0%, but the reconstructed frontier's accuracy at that same threshold was 72.0% — an 8-point gap at essentially the same cost ($0.0097 vs $0.0096). A structurally similar check on the smaller Run 2 (2026-07-19) showed only a 2.3-point gap, attributed to floating-point non-associativity even at temp=0. An 8-point gap — roughly 12 of 150 tasks landing differently — is more than 3x that, and reusing the same "just floating-point noise" explanation without checking felt like exactly the kind of quiet rationalization the project's own research-hygiene principle (Section 5 of `PROJECT.md`) exists to catch. Sent two SQL queries to check directly: one comparing the cascade run's own per-task correctness against the matching baseline run's correctness for the same task+tier (tests for real model-response nondeterminism), and one checking whether `router_cascade` rows with `route_decision='expensive'` ever have `router_confidence >= 0.5` or vice versa (tests for an actual logic mismatch between `cascade.py`'s live decision rule and `analysis.py`'s reconstruction assumption).

**Same day, continued — gap fully explained, resolved as a real finding, not a bug.** Query 2 came back clean: every "cheap"-routed task had confidence ≥0.5003, every "expensive"-routed task had confidence ≤0.4901 — no overlap, no logic mismatch between `cascade.py` and `analysis.py`. Query 1 found the actual cause: 30 of 150 tasks (20%) got a different correct/incorrect grade between the cascade run and the baseline run for the identical question and model. Checked the arithmetic directly: 21 tasks where the cascade's own answer was graded correct despite the baseline being wrong, minus 9 the other way, nets to exactly +12 tasks = +8.0 percentage points on 150 tasks — a complete, exact match to the observed 80.0% vs 72.0% gap, no residual left unexplained. Since `run_single()` is the literal same function invoked by both the baseline runner and the cascade (the code comment in `runners.py` says as much), this rules out any code-path inconsistency in how the model is called. Web-searched to confirm this against something other than assumption: multiple current sources (including provider documentation from OpenAI, Anthropic, and Google, and a detailed technical writeup from Thinking Machines Lab on the underlying causes — batching effects, floating-point non-associativity in inference) confirm temperature=0 has never been a determinism guarantee for any major LLM API, this codebase included. Closed this out as a genuine methodological finding rather than a bug: the zero-extra-API-call Pareto reconstruction technique assumes the model would answer identically if asked twice, and that assumption has a real, now-measured ~20% failure rate at this benchmark's scale, worth stating plainly in the eventual Phase 1 writeup rather than treated as an embarrassing discrepancy to explain away. No code changes made — there's no code-level fix for inherent model nondeterminism, and trying to force one (e.g. a fixed seed) wouldn't have helped, since seeds govern sampling above temp=0, not disagreement at temp=0 itself.

## Open Questions

- [ ] Exact current model names/tiers available on Groq and SambaNova — fallback defaults are set in code (`llama-3.1-8b-instant`, `Meta-Llama-3.3-70B-Instruct`) based on current docs, but confirm against each console once you have real API keys, since free-tier catalogs change
- [x] ~~Final Phase 1 benchmark dataset~~ — resolved: GSM8K + MMLU-style mix
- [x] ~~Phase 2 domain~~ — resolved: Retail Pharmacy Inventory & Procurement
- [x] ~~Does the hand-crafted-features-only router genuinely match/beat the original combined router, or fall short?~~ — resolved (clean re-run, 2026-08-09): neither wins clearly, AUC 0.5139 vs 0.5272, within noise
- [x] ~~Why does the cascade's actual accuracy at threshold=0.5 not match the reconstructed frontier's accuracy at the same threshold?~~ — resolved (2026-08-09): fully explained by real LLM-API nondeterminism at temp=0 (~20% of tasks graded differently on repeat calls to the identical model/question), not a code bug. Routing-rule logic confirmed correct separately. Worth stating as a documented limitation in the Phase 1 writeup.
- [ ] Would an actual PCA-enabled sweep improve discrimination over the no-reduction baseline? Completely untested to date — PCA code exists but has never run for real. Lower priority now that the ablation shows swapping features barely moves AUC at all, and Phase 1's main open threads are otherwise closed
- [ ] Would raw embeddings alone (no hand-crafted features, no PCA) discriminate better or worse than hand-crafted-only? Not yet built — same zero-API-call reconstruction pattern would apply if this becomes worth answering, but same lower-priority note as above applies