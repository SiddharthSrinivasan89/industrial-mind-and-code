"""
run_experiment_local.py
Variant of run_experiment.py for local Ollama models (e.g. Qwen3.5, Llama3, etc.).

Differences from the Azure version:
  - Uses the native Ollama /api/chat endpoint instead of OpenAI-compat /v1/
  - think=False by default (set LOCAL_THINK=true to enable Qwen3.x thinking mode)
  - max_tokens controls Ollama num_predict; set to -1 for unlimited when thinking
  - No inter-call delay needed (local, no rate limits)
  - Results saved to results/local/ with model name and think mode in filename

Usage:
    python src/run_experiment_local.py                        # thinking off
    LOCAL_THINK=true python src/run_experiment_local.py       # thinking on

Configuration (.env or environment):
    OLLAMA_BASE_URL    Ollama server base URL (default: http://localhost:11434)
    LOCAL_MODEL        Model name as shown in `ollama list` (default: qwen3.5:latest)
    LOCAL_MAX_TOKENS   Max output tokens per call (default: 2000; ignored if LOCAL_THINK=true)
    LOCAL_TEMPERATURE  Sampling temperature (default: 0.4)
    LOCAL_THINK        Enable model thinking mode (default: false)
    LOCAL_CONFIGS      Comma-separated configs to run (default: blind_lightweight,context_lightweight)
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).parent))

import blind_agent
import context_agent
import persona_agents
from supply_chain import TierState, step_receive_fulfill, step_place_order

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_CSV = ROOT / "data" / "synthetic" / "tatva_monthly_dispatches.csv"
RESULTS_RAW = ROOT / "results" / "raw"
RESULTS_LOCAL = ROOT / "results" / "local"
LOG_FILE = ROOT / "results" / "experiment_local.log"

RESULTS_RAW.mkdir(parents=True, exist_ok=True)
RESULTS_LOCAL.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_MODEL: str = os.environ.get("LOCAL_MODEL", "qwen3.5:latest")
LOCAL_TEMPERATURE: float = float(os.environ.get("LOCAL_TEMPERATURE", "0.4"))
LOCAL_THINK: bool = os.environ.get("LOCAL_THINK", "false").lower() in ("true", "1", "yes")
# For thinking mode cap at 3800 (just under the 4096 context window) so the model
# always finishes within context. For no-think mode 2000 is plenty.
LOCAL_MAX_TOKENS: int = int(os.environ.get("LOCAL_MAX_TOKENS", "6000" if LOCAL_THINK else "2000"))
_configs_env = os.environ.get("LOCAL_CONFIGS", "blind_lightweight,context_lightweight,persona_context")
LOCAL_CONFIGS: list[str] = [c.strip() for c in _configs_env.split(",")]
LOCAL_MAX_PERIODS: int = int(os.environ.get("LOCAL_MAX_PERIODS", "0"))  # 0 = run all periods

TIERS: list[str] = ["oem", "ancillary", "component"]
INITIAL_INVENTORY: int = 43_000
LAST_PERIOD: int = 13
ORDERING_PERIODS: set[int] = set(range(1, LAST_PERIOD))

PATTERN_KEYWORDS: list[str] = [
    "dasara", "dussehra", "diwali", "deepawali", "deepavali", "navratri",
    "festive", "festival", "seasonal", "peak",
    "budget", "fy-end", "fiscal", "quarter",
    "monsoon", "anticipat",
]
PATTERN_PERIODS: set[int] = {3, 10, 11, 12}

# ---------------------------------------------------------------------------
# Ollama native API call
# ---------------------------------------------------------------------------

def _parse_response(raw_content: str) -> tuple[int | None, str | None]:
    """
    Extract order_quantity and reasoning from raw model output.

    Handles:
      - Markdown code fences
      - Trailing chat-template tokens (e.g. <|endoftext|>)
      - Numeric separators (commas/underscores in numbers)
      - Truncated JSON: falls back to regex extraction of order_quantity

    Returns (order_quantity, reasoning) or (None, error_string) on failure.
    """
    content = raw_content.strip()
    if not content:
        return None, "empty response"

    # Strip markdown code fences
    if content.startswith("```"):
        content = "\n".join(l for l in content.splitlines() if not l.startswith("```")).strip()

    # Strip trailing chat-template tokens
    brace_pos = content.rfind("}")
    if brace_pos != -1:
        content = content[:brace_pos + 1]

    # Strip numeric separators
    content = re.sub(r'(?<=\d),(?=\d)', '', content)
    content = re.sub(r'(?<=\d)_(?=\d)', '', content)

    # Attempt full JSON parse
    try:
        parsed = json.loads(content)
        return int(parsed["order_quantity"]), str(parsed.get("reasoning", ""))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        pass

    # Fallback: regex extraction for truncated JSON
    m = re.search(r'"order_quantity"\s*:\s*(\d+)', content)
    if m:
        qty = int(m.group(1))
        r = re.search(r'"reasoning"\s*:\s*"([^"]*)', content)
        reasoning = r.group(1) if r else ""
        logger.warning("Partial JSON recovery: order_quantity=%d", qty)
        return qty, reasoning

    return None, f"unparseable: {content[:120]}"


def call_ollama(system_prompt: str, user_prompt: str, max_retries: int = 2) -> dict[str, Any]:
    """
    Call the local Ollama /api/chat endpoint.
    Retries on empty response (thinking consumed all tokens) up to max_retries times.
    Returns the same dict structure as base_agent.call_llm for compatibility.
    """
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

    total_latency = 0.0
    raw_content = ""
    thinking_content = ""
    prompt_tokens = completion_tokens = 0

    for attempt in range(1, max_retries + 2):  # attempts: 1..max_retries+1
        t0 = time.perf_counter()
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=None)
        resp.raise_for_status()
        data = resp.json()
        total_latency += round(time.perf_counter() - t0, 3)

        raw_content = data.get("message", {}).get("content", "")
        thinking_content = data.get("message", {}).get("thinking", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        if raw_content.strip():
            break  # got a response — proceed to parse

        if attempt <= max_retries:
            logger.warning("Empty response (attempt %d/%d) — thinking likely consumed tokens, retrying",
                           attempt, max_retries + 1)

    result: dict[str, Any] = {
        "latency_seconds": total_latency,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "raw_content": raw_content,
        "thinking_content": thinking_content,
        "parse_error": None,
        "order_quantity": 0,
        "reasoning": "",
        "cost_usd": 0.0,
    }

    qty, reasoning_or_err = _parse_response(raw_content)
    if qty is not None:
        result["order_quantity"] = qty
        result["reasoning"] = reasoning_or_err or ""
    else:
        result["parse_error"] = reasoning_or_err
        logger.error("Parse error [%s]: %s | raw: %.200s", LOCAL_MODEL, reasoning_or_err, raw_content)

    return result


# ---------------------------------------------------------------------------
# Demand data
# ---------------------------------------------------------------------------

def load_demand() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(DATA_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "period": int(row["period_number"]),
                "month_name": row["month_name"],
                "year": int(row["year"]),
                "dispatches": int(row["dispatches"]),
            })
    rows.sort(key=lambda r: r["period"])
    return rows


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(config_key: str, run_number: int, demand_rows: list[dict]) -> dict:
    if "blind" in config_key:
        treatment = "blind"
    elif "persona" in config_key:
        treatment = "persona"
    else:
        treatment = "context"
    logger.info("━━━ Starting %s run %02d ━━━", config_key, run_number)

    states: dict[str, TierState] = {t: TierState(inventory=INITIAL_INVENTORY) for t in TIERS}
    period_records: list[dict] = []

    for row in demand_rows:
        period = row["period"]
        month_name = row["month_name"]
        year = row["year"]
        consumer_demand = row["dispatches"]

        period_record: dict = {
            "period": period,
            "month_name": month_name,
            "year": year,
            "consumer_demand": consumer_demand,
            "tiers": {},
        }

        for i, tier_key in enumerate(TIERS):
            demand = consumer_demand if i == 0 else (
                period_record["tiers"][TIERS[i - 1]]["order_placed"] or 0
            )

            state = states[tier_key]
            state, partial_rec = step_receive_fulfill(state, demand, period)

            if period in ORDERING_PERIODS:
                if treatment == "blind":
                    system_p = blind_agent.build_system_prompt()
                    user_p = blind_agent.build_user_prompt(state, demand)
                elif treatment == "persona":
                    system_p = persona_agents.build_system_prompt(tier_key)
                    user_p = persona_agents.build_user_prompt(tier_key, state, demand, month_name, year, period)
                else:
                    system_p = context_agent.build_system_prompt()
                    user_p = context_agent.build_user_prompt(tier_key, state, demand, month_name, year, period)

                llm_result = call_ollama(system_p, user_p)
                order_qty = llm_result["order_quantity"]
            else:
                llm_result = None
                order_qty = None

            state, order_rec = step_place_order(state, order_qty, period, lead_time=1)
            states[tier_key] = state
            period_record["tiers"][tier_key] = {**partial_rec, **order_rec, "llm_response": llm_result}

        period_records.append(period_record)
        logger.info(
            "  Period %2d/%d (%s %d) — OEM ordered %s",
            period, len(demand_rows), month_name, year,
            period_record["tiers"]["oem"]["order_placed"],
        )

    metrics = _compute_metrics(period_records)
    return {
        "config": config_key,
        "run_number": run_number,
        "model": LOCAL_MODEL,
        "treatment": treatment,
        "periods": period_records,
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Metrics (same logic as run_experiment.py)
# ---------------------------------------------------------------------------

def _compute_metrics(period_records: list[dict]) -> dict:
    metrics: dict[str, Any] = {"tiers": {}}

    for tier_key in TIERS:
        stockout_count = excess_sum = clamp_count = parse_errors = 0
        orders: list[int] = []
        demands: list[int] = []

        for pr in period_records:
            tr = pr["tiers"][tier_key]
            if tr["backlog_after"] > 0:
                stockout_count += 1
            if tr["inventory_after_fulfillment"] > tr["demand_received"]:
                excess_sum += tr["inventory_after_fulfillment"] - tr["demand_received"]
            if tr["clamp_applied"]:
                clamp_count += 1
            if pr["period"] in ORDERING_PERIODS:
                orders.append(tr["order_placed"])
                demands.append(tr["demand_received"])
            llm = tr.get("llm_response") or {}
            if llm.get("parse_error") is not None:
                parse_errors += 1

        var_d = float(np.var(demands, ddof=0))
        var_o = float(np.var(orders, ddof=0))
        ovar = None if var_d == 0 else round(var_o / var_d, 6)

        metrics["tiers"][tier_key] = {
            "ovar": ovar,
            "var_orders": round(var_o, 2),
            "var_demand": round(var_d, 2),
            "stockout_count": stockout_count,
            "excess_inventory_sum": excess_sum,
            "total_ordered": int(sum(orders)),
            "peak_overshoot": round(max(orders) / max(demands), 4) if demands and max(demands) > 0 else None,
            "clamp_count": clamp_count,
            "parse_error_count": parse_errors,
            "cost_usd": 0.0,
        }

    # Pattern score
    matched: set[str] = set()
    for pr in period_records:
        if pr["period"] not in PATTERN_PERIODS:
            continue
        for tier_key in TIERS:
            reasoning = ((pr["tiers"][tier_key].get("llm_response") or {}).get("reasoning") or "").lower()
            for kw in PATTERN_KEYWORDS:
                if kw in reasoning:
                    matched.add(kw)
    keyword_score = round(len(matched) / len(PATTERN_KEYWORDS), 4)

    elevated = 0
    total_pairs = len(TIERS) * len(PATTERN_PERIODS)
    for tier_key in TIERS:
        non_event = [
            pr["tiers"][tier_key]["order_placed"]
            for pr in period_records
            if pr["period"] in ORDERING_PERIODS and pr["period"] not in PATTERN_PERIODS
            and pr["tiers"][tier_key]["order_placed"] is not None
        ]
        if not non_event:
            continue
        baseline = sum(non_event) / len(non_event)
        for pr in period_records:
            if pr["period"] not in PATTERN_PERIODS:
                continue
            order = pr["tiers"][tier_key].get("order_placed")
            if order is not None and baseline > 0 and order >= baseline * 1.1:
                elevated += 1

    elevation_score = round(elevated / total_pairs, 4) if total_pairs else 0.0
    metrics["keyword_score"] = keyword_score
    metrics["elevation_score"] = elevation_score
    metrics["pattern_score"] = round((keyword_score + elevation_score) / 2, 4)
    metrics["total_cost_usd"] = 0.0
    return metrics


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _safe_name(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Wrote %s", path.relative_to(ROOT))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    model_tag = _safe_name(LOCAL_MODEL)

    # Quick connection check
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if LOCAL_MODEL not in models:
            logger.warning("Model %s not in ollama list: %s", LOCAL_MODEL, models)
        else:
            logger.info("✓ Ollama reachable | model %s available", LOCAL_MODEL)
    except Exception as exc:
        logger.error("Cannot reach Ollama at %s: %s", OLLAMA_BASE_URL, exc)
        sys.exit(1)

    logger.info("═══ Local Experiment — model: %s | thinking: %s ═══", LOCAL_MODEL, LOCAL_THINK)
    logger.info("Configs: %s | num_predict: %d | temperature: %.2f",
                LOCAL_CONFIGS, LOCAL_MAX_TOKENS, LOCAL_TEMPERATURE)

    demand_rows = load_demand()
    if LOCAL_MAX_PERIODS > 0:
        demand_rows = demand_rows[:LOCAL_MAX_PERIODS]
        logger.info("Loaded %d demand periods (capped at %d)", len(demand_rows), LOCAL_MAX_PERIODS)
    else:
        logger.info("Loaded %d demand periods", len(demand_rows))

    for config_key in LOCAL_CONFIGS:
        run_data = run_simulation(config_key, 1, demand_rows)
        think_tag = "thinking" if LOCAL_THINK else "no_think"
        out_path = RESULTS_LOCAL / f"{config_key}_{model_tag}_{think_tag}_run01.json"
        _write_json(out_path, run_data)

        m = run_data["metrics"]
        logger.info("── %s results ──", config_key)
        for tier_key in TIERS:
            tm = m["tiers"][tier_key]
            logger.info("  %s: OVAR=%s, stockouts=%d, parse_errors=%d",
                        tier_key, tm["ovar"], tm["stockout_count"], tm["parse_error_count"])
        logger.info("  Pattern score: %.4f (keyword=%.4f, elevation=%.4f)",
                    m["pattern_score"], m["keyword_score"], m["elevation_score"])

    logger.info("═══ Local experiment complete ═══")


if __name__ == "__main__":
    main()
