"""Standalone keep-alive ping, run daily by .github/workflows/keepalive.yml.

Needs SUPABASE_URL / SUPABASE_KEY set as environment variables — GitHub repo
secrets in CI, or your local .env when run manually.

Run as a module: `python -m scripts.keepalive` (not `python scripts/keepalive.py`
— see the note in verify_setup.py for why).
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from src.db.supabase_client import SupabaseLogger  # noqa: E402

SupabaseLogger().ping_heartbeat()
print("Supabase heartbeat pinged.")
