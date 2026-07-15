"""Standalone keep-alive ping, run daily by .github/workflows/keepalive.yml.

Needs SUPABASE_URL / SUPABASE_KEY set as environment variables — GitHub repo
secrets in CI, or your local .env when run manually.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from src.db.supabase_client import SupabaseLogger  # noqa: E402

SupabaseLogger().ping_heartbeat()
print("Supabase heartbeat pinged.")
