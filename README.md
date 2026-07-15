# RouteBench

Does cost-aware LLM routing hold up under repeated trials?

A calibrated router sends each query to a cheap/fast model or a stronger/slower one based on predicted difficulty. It's then dropped inside a small tool-using agent to test whether routing preserves the agent's run-to-run reliability (pass^k) — not just its average accuracy.

Full design doc: [`PROJECT.md`](./PROJECT.md) · Live progress: [`PROGRESS.md`](./PROGRESS.md)

## Status

Phase 0 — infrastructure scaffolded, awaiting real credentials. See `PROGRESS.md` for the current Kanban board.

## Quick start

1. Copy `.env.example` to `.env` and fill in your own Groq, SambaNova, and Supabase credentials.
2. Run `sql/schema.sql` in your Supabase project's SQL editor.
3. `docker compose build`
4. `docker compose run app python -m scripts.verify_setup`

## Stack

Python · Groq · SambaNova Cloud · Supabase (Postgres) · Docker · GitHub Actions · Vercel (dashboard, Phase 3)

See `PROJECT.md` for the full architecture, methodology, and roadmap.
