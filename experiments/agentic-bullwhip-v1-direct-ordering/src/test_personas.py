"""
test_personas.py
Smoke-test for all three persona agents before committing to a full run.

Makes one LLM call per tier agent (3 calls total) with realistic state data,
validates that each returns parseable JSON with order_quantity and reasoning,
and exits 0 on success or 1 on any failure.

Usage:
    .venv/bin/python3 src/test_personas.py                    # thinking off
    LOCAL_THINK=true .venv/bin/python3 src/test_personas.py   # thinking on
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import requests

sys.path.insert(0, str(Path(__file__).parent))

import persona_agents
from supply_chain import TierState

# ---------------------------------------------------------------------------
# Config (mirrors run_experiment_local.py)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_MODEL: str = os.environ.get("LOCAL_MODEL", "qwen3.5:latest")
LOCAL_TEMPERATURE: float = float(os.environ.get("LOCAL_TEMPERATURE", "0.4"))
LOCAL_THINK: bool = os.environ.get("LOCAL_THINK", "false").lower() in ("true", "1", "yes")
LOCAL_MAX_TOKENS: int = int(os.environ.get("LOCAL_MAX_TOKENS", "2500" if LOCAL_THINK else "2000"))

# Realistic mid-run state: some inventory, no backlog, one order in transit
_TEST_STATE = TierState(
    inventory=38_500,
    backlog=0,
    in_transit=[{"quantity": 5_000, "arriving_period": 3}],
)
_TEST_DEMAND = 6_200
_TEST_MONTH = "October"
_TEST_YEAR = 2025
_TEST_PERIOD = 2

TIERS = ["oem", "ancillary", "component"]


# ---------------------------------------------------------------------------
# Single call (same logic as call_ollama in run_experiment_local)
# ---------------------------------------------------------------------------

def _call(system_prompt: str, user_prompt: str) -> dict:
    payload = {
        "model": LOCAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "think": LOCAL_THINK,
        "stream": False,
        "options": {
            "num_predict": LOCAL_MAX_TOKENS,
            "num_ctx": 8192,
            "temperature": LOCAL_TEMPERATURE,
        },
    }
    t0 = time.perf_counter()
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=None)
    resp.raise_for_status()
    data = resp.json()
    latency = round(time.perf_counter() - t0, 1)

    raw: str = data.get("message", {}).get("content", "")
    thinking: str = data.get("message", {}).get("thinking", "")
    return {"raw": raw, "thinking": thinking, "latency": latency}


def _parse(raw: str) -> dict | None:
    content = raw.strip()
    if content.startswith("```"):
        content = "\n".join(l for l in content.splitlines() if not l.startswith("```")).strip()
    brace = content.rfind("}")
    if brace != -1:
        content = content[: brace + 1]
    content = re.sub(r"(?<=\d),(?=\d)", "", content)
    content = re.sub(r"(?<=\d)_(?=\d)", "", content)
    try:
        parsed = json.loads(content)
        if "order_quantity" not in parsed:
            return None
        return {"order_quantity": int(parsed["order_quantity"]), "reasoning": str(parsed.get("reasoning", ""))}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n{'='*60}")
    print(f"  Persona smoke-test | model: {LOCAL_MODEL} | think: {LOCAL_THINK}")
    print(f"  num_predict: {LOCAL_MAX_TOKENS} | temperature: {LOCAL_TEMPERATURE}")
    print(f"{'='*60}\n")

    # Connection check
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if LOCAL_MODEL not in models:
            print(f"[WARN] {LOCAL_MODEL} not found in ollama list: {models}")
        else:
            print(f"[OK]   Ollama reachable — {LOCAL_MODEL} available\n")
    except Exception as exc:
        print(f"[FAIL] Cannot reach Ollama: {exc}")
        sys.exit(1)

    failures = []

    for tier_key in TIERS:
        agent_name = {
            "oem": "TATVA-OEM-PROCUREMENT-AGENT",
            "ancillary": "BRIGHTARC-SUPPLY-AGENT",
            "component": "LUMICORE-PRODUCTION-AGENT",
        }[tier_key]

        print(f"--- {agent_name} ({tier_key}) ---")

        system_p = persona_agents.build_system_prompt(tier_key)
        user_p = persona_agents.build_user_prompt(
            tier_key, _TEST_STATE, _TEST_DEMAND,
            _TEST_MONTH, _TEST_YEAR, _TEST_PERIOD,
        )

        print(f"  Sending call... ", end="", flush=True)
        result = _call(system_p, user_p)
        print(f"done ({result['latency']}s)")

        raw = result["raw"]

        if not raw.strip():
            print(f"  [FAIL] Empty response — thinking likely consumed all {LOCAL_MAX_TOKENS} tokens")
            if result["thinking"]:
                think_len = len(result["thinking"].split())
                print(f"         Thinking block: ~{think_len} words")
            failures.append(tier_key)
            print()
            continue

        parsed = _parse(raw)
        if parsed is None:
            print(f"  [FAIL] JSON parse error")
            print(f"         Raw (first 300 chars): {raw[:300]!r}")
            failures.append(tier_key)
            print()
            continue

        print(f"  [OK]   order_quantity = {parsed['order_quantity']:,}")
        print(f"         reasoning      = {parsed['reasoning'][:120]}")
        if result["thinking"]:
            think_words = len(result["thinking"].split())
            print(f"         thinking words = ~{think_words}")
        print()

    print(f"{'='*60}")
    if failures:
        print(f"  RESULT: FAILED — {len(failures)}/3 agents failed: {failures}")
        print(f"  Tip: increase LOCAL_MAX_TOKENS (current: {LOCAL_MAX_TOKENS})")
        print(f"{'='*60}\n")
        sys.exit(1)
    else:
        print(f"  RESULT: PASSED — all 3 agent personas validated")
        print(f"{'='*60}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
