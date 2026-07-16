# RouteBench — Progress Tracker

*Last updated: 2026-07-15 — update this line every time you touch this file.*

This is the living half of the project documentation. `PROJECT.md` explains what the project is and why; this file tracks where it actually stands right now. If you're handing this project to an AI assistant, share both — but if you only have room for one, share this one and it can ask for `PROJECT.md` if it needs the deeper why.

---

## Current Status (read this first)

**Phase:** 0 — Setup, functionally complete.
**Last thing done:** `scripts/verify_setup.py` passed all three checks on the real home server — Groq, SambaNova, and Supabase all confirmed reachable and working end-to-end.
**Next thing to do:** Phase 0 is fully wrapped — move into Phase 1: router baselines and feature extraction.
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
- [ ] Baseline runners: always-cheap, always-expensive, random-routing
- [ ] Query feature extraction (fastembed embeddings + hand-crafted features)
- [ ] Train initial router classifier (logistic regression baseline)
- [ ] Calibrate confidence (Platt scaling or isotonic regression, held-out split)
- [ ] Implement two-stage cascade (cheap model first, escalate on low calibrated confidence)
- [ ] Full sweep across benchmark set, every run logged to Supabase
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

## Open Questions

- [ ] Exact current model names/tiers available on Groq and SambaNova — fallback defaults are set in code (`llama-3.1-8b-instant`, `Meta-Llama-3.3-70B-Instruct`) based on current docs, but confirm against each console once you have real API keys, since free-tier catalogs change
- [x] ~~Final Phase 1 benchmark dataset~~ — resolved: GSM8K + MMLU-style mix
- [x] ~~Phase 2 domain~~ — resolved: Retail Pharmacy Inventory & Procurement
