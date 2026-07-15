"""Run this once you've filled in .env, to confirm all three services are reachable.

    docker compose run app python scripts/verify_setup.py

or, without Docker, from a venv with requirements.txt installed:

    python scripts/verify_setup.py
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

from src.db.supabase_client import SupabaseLogger  # noqa: E402
from src.providers import GroqProvider, SambaNovaProvider  # noqa: E402

results: dict[str, str] = {}


def check(name: str, fn) -> None:
    try:
        fn()
        results[name] = "OK"
        print(f"[PASS] {name}")
    except Exception as exc:  # noqa: BLE001 - intentionally broad for a diagnostic script
        results[name] = f"FAILED: {exc}"
        print(f"[FAIL] {name}: {exc}")


def check_groq() -> None:
    client = GroqProvider()
    result = client.complete([{"role": "user", "content": "Reply with just: pong"}])
    print(f"       -> {result.provider}/{result.model} responded in {result.latency_s:.2f}s: {result.content!r}")


def check_sambanova() -> None:
    client = SambaNovaProvider()
    result = client.complete([{"role": "user", "content": "Reply with just: pong"}])
    print(f"       -> {result.provider}/{result.model} responded in {result.latency_s:.2f}s: {result.content!r}")


def check_supabase() -> None:
    logger = SupabaseLogger()
    logger.log_run(phase="setup_verification", provider="none", model="none", query="smoke test")
    logger.ping_heartbeat()


check("Groq", check_groq)
check("SambaNova", check_sambanova)
check("Supabase", check_supabase)

print("\n--- Summary ---")
for name, status in results.items():
    print(f"{name}: {status}")

if any("FAILED" in status for status in results.values()):
    sys.exit(1)
