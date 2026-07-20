# RouteBench — Progress Tracker

*Last updated: 2026-07-15 — update this line every time you touch this file.*

This is the living half of the project documentation. `PROJECT.md` explains what the project is and why; this file tracks where it actually stands right now. If you're handing this project to an AI assistant, share both — but if you only have room for one, share this one and it can ask for `PROJECT.md` if it needs the deeper why.

---

## Current Status (read this first)

**Phase:** 1 — Router / Cascade, in progress.
**Last thing done:** Switched expensive tier default to Gemini 3.1 Flash Lite (15 RPM / 250K TPM / 500 RPD free tier — RPD comfortably covers a full sweep) after SambaNova kept failing and Gemini 3.5 Flash's 20/day cap proved too small. Model string, pricing, and throttle all verified/tuned for this specific tier. 87 tests passing.
**Next thing to do:** Run `scripts/run_phase1_sweep.py` for real with `EXPENSIVE_PROVIDER=gemini`. If it completes: Pareto frontier plot + findings write-up closes out Phase 1. SambaNova's root cause is still an open thread — worth sharing the exact new error text if you want to revisit it later, but it's not blocking anymore.
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
- [ ] Compute + plot cost-quality-latency Pareto frontier vs. baselines
- [ ] Write up Phase 1 findings
- [ ] *Optional:* add a prompted-LLM router as a second variant for comparison

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

---

## Hypothesis Log

Prediction logged *before* running the experiment; result filled in *after*. The point is to catch yourself if you'd quietly rationalize whatever the data shows.

| Date | Question | Prediction (before) | Result (after) |
|---|---|---|---|
| — | RQ1: calibrated cascade router | Should approach the strong tier's quality at meaningfully lower cost, similar in shape to published cost-quality frontiers — exact numbers will differ since the model pool and benchmark are custom | *pending* |
| — | RQ2: does routing hurt agent reliability (pass^k)? | Genuinely uncertain going in — cheaper per-step models could add variance, or a well-calibrated router could hold steady. This is the real open question of the project. | *pending* |
| — | RQ3 (stretch): simulated-user sensitivity | Expect measurable shifts in pass^k when the simulated-user model changes, based on prior critique in the literature | *pending* |

---

## Dev Log

Freeform, dated, append-only. Write what actually happened, including dead ends — those are exactly what an AI assistant (or future you) needs to avoid repeating them.

**2026-07-15 — Kickoff**
Planning phase complete. Journey: started with a local vLLM-on-Colab serving benchmark, hit repeated environment friction, abandoned it. Pivoted to a self-hosted personal RAG assistant, fully architected, then set aside for being an oversaturated portfolio pattern. Landed on RouteBench: a calibrated LLM router evaluated on cost/quality/latency, combined with an agent built on top of it and evaluated on pass^k reliability rather than one-shot accuracy. Chose Kanban-managed Iterative & Incremental Development as the methodology. `PROJECT.md` and `PROGRESS.md` written. Phase 0 not yet started.

**2026-07-15 — Phase 0 scaffolding**
Confirmed Phase 1 dataset (GSM8K + MMLU-style mix) and Phase 2 domain (Retail Pharmacy Inventory & Procurement, scoped to back-office logistics). Verified Groq's and SambaNova's current OpenAI-compatible base URLs against their docs rather than assuming. Scaffolded the full repo: Docker setup, a shared `OpenAICompatibleProvider` base class with thin Groq/SambaNova subclasses, a Supabase client + schema (`runs` + `heartbeat` tables), GitHub Actions CI and a scheduled keep-alive ping, and `scripts/verify_setup.py`. Everything was syntax-checked, lint-checked, and unit-tested in isolation; live integration tests are marked to skip automatically without real API keys. Handed off as a zip — remaining Phase 0 items all require your own accounts/credentials, which is out of reach for an AI assistant by design.

---

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

## Open Questions

- [ ] Exact current model names/tiers available on Groq and SambaNova — fallback defaults are set in code (`llama-3.1-8b-instant`, `Meta-Llama-3.3-70B-Instruct`) based on current docs, but confirm against each console once you have real API keys, since free-tier catalogs change
- [x] ~~Final Phase 1 benchmark dataset~~ — resolved: GSM8K + MMLU-style mix
- [x] ~~Phase 2 domain~~ — resolved: Retail Pharmacy Inventory & Procurement