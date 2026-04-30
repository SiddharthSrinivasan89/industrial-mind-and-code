"""
test_connection.py
Smoke-test for the configured OpenAI / Azure OpenAI endpoint.

Tests both LIGHTWEIGHT_MODEL and REASONING_MODEL deployments with a minimal
API call.  Exits 0 on full success, 1 on any failure.

Run standalone from the project root:
    python src/test_connection.py

Or call check_connection() from another script — it raises SystemExit(1) on
failure so the caller terminates cleanly.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ── Path setup so this file can be run standalone ───────────────────────────
_SRC = Path(__file__).parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Load .env before importing base_agent (which reads os.environ at call time)
from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from base_agent import _is_reasoning_model, get_client  # noqa: E402


def _probe_model(model: str) -> tuple[bool, str]:
    """
    Make a single minimal call to `model`.
    Returns (success, message).
    """
    client = get_client()
    reasoning = _is_reasoning_model(model)

    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
    }
    if reasoning:
        kwargs["max_completion_tokens"] = 50
    else:
        kwargs["max_tokens"] = 10
        kwargs["temperature"] = 0

    t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(**kwargs)
        latency = round(time.perf_counter() - t0, 3)
        content = (response.choices[0].message.content or "").strip()
        return True, f"OK  ({latency}s) — replied: {content!r}"
    except Exception as exc:
        latency = round(time.perf_counter() - t0, 3)
        return False, f"FAILED ({latency}s) — {exc}"


def check_connection() -> None:
    """
    Test both configured models.  Prints results and calls sys.exit(1) if
    either fails — intended to be called at the top of run_experiment.main().
    """
    lightweight = os.environ.get("LIGHTWEIGHT_MODEL", "gpt-4.1-mini")
    reasoning   = os.environ.get("REASONING_MODEL", "o1")
    endpoint    = os.environ.get("OPENAI_BASE_URL", "api.openai.com (default)")

    print("─" * 60)
    print(f"  Connection check — endpoint: {endpoint}")
    print("─" * 60)

    all_ok = True
    for label, model in [("Lightweight", lightweight), ("Reasoning  ", reasoning)]:
        ok, msg = _probe_model(model)
        status = "✓" if ok else "✗"
        print(f"  {status} {label} ({model}): {msg}")
        if not ok:
            all_ok = False

    print("─" * 60)

    if not all_ok:
        print("  Connection check FAILED — aborting.\n")
        sys.exit(1)

    print("  All models reachable. Proceeding.\n")


if __name__ == "__main__":
    check_connection()
