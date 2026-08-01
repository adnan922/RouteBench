"""Thin wrapper around the Supabase Python client for logging run results.

Schema lives in sql/schema.sql — run that once in your Supabase project's SQL
editor before using this module.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from supabase import create_client


class SupabaseLogger:
    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        resolved_url = url or os.environ.get("SUPABASE_URL")
        resolved_key = key or os.environ.get("SUPABASE_KEY")
        if not resolved_url or not resolved_key:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY not set. Copy .env.example to .env "
                "and fill them in."
            )
        self._client = create_client(resolved_url, resolved_key)

    def log_run(self, **fields) -> dict:
        """Insert one row into the `runs` table.

        Pass any column from sql/schema.sql as a keyword argument, e.g.:
            logger.log_run(phase="router_baseline", provider="groq", model="llama-3.1-8b-instant", ...)
        """
        response = self._client.table("runs").insert(fields).execute()
        return response.data[0] if response.data else {}

    def ping_heartbeat(self) -> None:
        """Used by the daily keep-alive job to prevent the free Supabase project
        from auto-pausing after a week of inactivity."""
        self._client.table("heartbeat").upsert(
            {"id": 1, "pinged_at": datetime.now(timezone.utc).isoformat()}
        ).execute()
    
    def fetch_by_phase(self, phase: str) -> list[dict]:
        """Retrieve every row logged under a given phase — used by
        scripts/analyze_phase1.py to pull results back out for the Pareto
        frontier analysis."""
        response = self._client.table("runs").select("*").eq("phase", phase).execute()
        return response.data