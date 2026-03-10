"""
run_experiment.py
Orchestrator for the Agentic Bullwhip experiment.

2×2 factorial design — 4 configs × 5 runs each = 20 total runs.
Each run: 13 periods, 3 tiers, serial execution OEM → Ancillary → Component.
Ordering periods: 1-12 only; period 13 fulfils demand but places no orders.

Run from the project root:
    python src/run_experiment.py

Reads configuration from .env in the project root (via python-dotenv).
Required env vars: OPENAI_API_KEY
Optional env vars: LIGHTWEIGHT_MODEL (default: gpt-4.1-mini), REASONING_MODEL (default: o1)
"""
from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from project root before anything reads os.environ
load_dotenv(Path(__file__).parent.parent / ".env")

import numpy as np

# Ensure src/ is on sys.path so sibling modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent))

import blind_agent
import context_agent
from base_agent import call_llm
from supply_chain import TierState, step_receive_fulfill, step_place_order

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_CSV = ROOT / "data" / "synthetic" / "tatva_monthly_dispatches.csv"
RESULTS_RAW = ROOT / "results" / "raw"
RESULTS_AGG = ROOT / "results" / "aggregated"
LOG_FILE = ROOT / "results" / "experiment.log"

# ---------------------------------------------------------------------------
# Logging — file + console, set up before anything else that uses logger
# ---------------------------------------------------------------------------
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
# Experiment constants
# ---------------------------------------------------------------------------
TIERS: list[str] = ["oem", "ancillary", "component"]
INITIAL_INVENTORY: int = 43_000
LEAD_TIME: int = 1
RUNS_PER_CONFIG: int = 5
LAST_PERIOD: int = 13           # inclusive; period 13 = demand-fulfil only
ORDERING_PERIODS: set[int] = set(range(1, LAST_PERIOD))   # 1-12

# Models — read from .env (or environment), with fallback defaults
_LIGHTWEIGHT_MODEL: str = os.environ.get("LIGHTWEIGHT_MODEL", "gpt-4.1-mini")
_REASONING_MODEL: str = os.environ.get("REASONING_MODEL", "o1")

# Pricing — USD per 1M tokens; edit in .env if your Azure rates differ
_PRICE: dict[str, dict[str, float]] = {
    _LIGHTWEIGHT_MODEL: {
        "input":  float(os.environ.get("LIGHTWEIGHT_INPUT_COST_PER_1M",  "0.40")),
        "output": float(os.environ.get("LIGHTWEIGHT_OUTPUT_COST_PER_1M", "1.60")),
    },
    _REASONING_MODEL: {
        "input":  float(os.environ.get("REASONING_INPUT_COST_PER_1M",  "15.00")),
        "output": float(os.environ.get("REASONING_OUTPUT_COST_PER_1M", "60.00")),
    },
}


def _call_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for one LLM call using rates from .env."""
    p = _PRICE.get(model, {"input": 0.0, "output": 0.0})
    return round((prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000, 6)


# Configs — each key maps to all parameters needed for a run
CONFIGS: dict[str, dict[str, Any]] = {
    "blind_lightweight": {
        "model": _LIGHTWEIGHT_MODEL,
        "treatment": "blind",
        "temperature": 0.4,
        "max_tokens": 600,
        "inter_call_delay": 1.0,
    },
    "context_lightweight": {
        "model": _LIGHTWEIGHT_MODEL,
        "treatment": "context",
        "temperature": 0.4,
        "max_tokens": 600,
        "inter_call_delay": 1.0,
    },
    "blind_reasoning": {
        "model": _REASONING_MODEL,
        "treatment": "blind",
        "temperature": None,    # API-fixed for o1; base_agent.py handles omission
        "max_tokens": 16_000,
        "inter_call_delay": 5.0,
    },
    "context_reasoning": {
        "model": _REASONING_MODEL,
        "treatment": "context",
        "temperature": None,
        "max_tokens": 16_000,
        "inter_call_delay": 5.0,
    },
}

# Pattern score — two sub-scores combined:
#   1. Keyword score: fraction of distinct seasonal keywords found in reasoning
#      text at event periods across all tiers.
#   2. Elevation score: fraction of (tier × event_period) pairs where the order
#      placed exceeds the tier's mean non-event-period order by ≥10%.
#      This captures seasonal responsiveness even when models don't verbalise it.
# Final pattern_score = mean(keyword_score, elevation_score)
PATTERN_KEYWORDS: list[str] = [
    # Indian festival names (multiple spellings)
    "dasara", "dussehra", "diwali", "deepawali", "deepavali", "navratri",
    # General seasonal / demand language
    "festive", "festival", "seasonal", "peak",
    # Budget / fiscal year
    "budget", "fy-end", "fiscal", "quarter",
    # Weather / agriculture
    "monsoon",
    # Forward-looking language
    "anticipat",
]
PATTERN_PERIODS: set[int] = {3, 10, 11, 12}

# ---------------------------------------------------------------------------
# Demand data
# ---------------------------------------------------------------------------

def load_demand() -> list[dict[str, Any]]:
    """Load tatva_monthly_dispatches.csv and return rows sorted by period."""
    rows: list[dict[str, Any]] = []
    with open(DATA_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "period": int(row["period_number"]),
                    "month_name": row["month_name"],
                    "year": int(row["year"]),
                    "dispatches": int(row["dispatches"]),
                }
            )
    rows.sort(key=lambda r: r["period"])
    return rows

# ---------------------------------------------------------------------------
# Single simulation run
# ---------------------------------------------------------------------------

def run_simulation(
    config_key: str,
    run_number: int,
    demand_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Execute one complete simulation run and return the raw result dict.

    Per period, per tier (serial: OEM → Ancillary → Component):
      Phase A: receive deliveries + fulfil demand (step_receive_fulfill)
      [prompt built from resulting state]
      [LLM called if period < 13]
      Phase B: clamp & dispatch order (step_place_order)

    Each tier's order_placed becomes the next tier's demand_received
    within the same period.
    """
    cfg = CONFIGS[config_key]
    treatment: str = cfg["treatment"]
    model: str = cfg["model"]
    temperature: float | None = cfg["temperature"]
    max_tokens: int = cfg["max_tokens"]
    delay: float = cfg["inter_call_delay"]

    logger.info("━━━ Starting %s run %02d ━━━", config_key, run_number)

    # Initialise states — all three tiers start identical
    states: dict[str, TierState] = {
        tier: TierState(inventory=INITIAL_INVENTORY) for tier in TIERS
    }

    period_records: list[dict[str, Any]] = []

    for row in demand_rows:
        period: int = row["period"]
        month_name: str = row["month_name"]
        year: int = row["year"]
        consumer_demand: int = row["dispatches"]

        period_record: dict[str, Any] = {
            "period": period,
            "month_name": month_name,
            "year": year,
            "consumer_demand": consumer_demand,
            "tiers": {},
        }

        # ── Serial tier execution ────────────────────────────────────────────
        for i, tier_key in enumerate(TIERS):
            # Demand this tier sees:
            #   OEM       → consumer demand from CSV
            #   Ancillary → OEM's order_placed this period
            #   Component → Ancillary's order_placed this period
            if i == 0:
                demand = consumer_demand
            else:
                upstream_key = TIERS[i - 1]
                upstream_order = period_record["tiers"][upstream_key]["order_placed"]
                # Period 13: upstream placed no order → this tier's demand = 0
                demand = upstream_order if upstream_order is not None else 0

            state = states[tier_key]

            # ── Phase A: receive deliveries + fulfil demand ──────────────────
            state, partial_rec = step_receive_fulfill(state, demand, period)
            # `state` now reflects post-fulfillment; this is what the LLM sees.

            # ── LLM call (ordering periods only) ────────────────────────────
            if period in ORDERING_PERIODS:
                if treatment == "blind":
                    system_prompt = blind_agent.build_system_prompt()
                    user_prompt = blind_agent.build_user_prompt(state, demand)
                else:
                    system_prompt = context_agent.build_system_prompt()
                    user_prompt = context_agent.build_user_prompt(
                        tier_key, state, demand, month_name, year, period
                    )

                llm_result = call_llm(
                    system_prompt, user_prompt, model, temperature, max_tokens
                )
                llm_result["cost_usd"] = _call_cost(
                    model, llm_result["prompt_tokens"], llm_result["completion_tokens"]
                )
                order_qty: int | None = llm_result["order_quantity"]
                time.sleep(delay)
            else:
                # Period 13: no order
                llm_result = None
                order_qty = None

            # ── Phase B: clamp + dispatch order ─────────────────────────────
            state, order_rec = step_place_order(state, order_qty, period, LEAD_TIME)
            states[tier_key] = state

            # Merge all sub-records into a single tier record for this period
            tier_rec: dict[str, Any] = {**partial_rec, **order_rec, "llm_response": llm_result}
            period_record["tiers"][tier_key] = tier_rec

        period_records.append(period_record)
        period_cost = sum(
            (period_record["tiers"][t].get("llm_response") or {}).get("cost_usd", 0.0)
            for t in TIERS
        )
        logger.info(
            "  Period %2d/%d (%s %d) complete — OEM ordered %s | cost $%.4f",
            period,
            len(demand_rows),
            month_name,
            year,
            period_record["tiers"]["oem"]["order_placed"],
            period_cost,
        )

    metrics = _compute_run_metrics(period_records)

    return {
        "config": config_key,
        "run_number": run_number,
        "model": model,
        "treatment": treatment,
        "periods": period_records,
        "metrics": metrics,
    }

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _compute_pattern_score(period_records: list[dict[str, Any]]) -> dict[str, float]:
    """
    Two-part seasonal-awareness score.

    keyword_score:
        Fraction of distinct PATTERN_KEYWORDS found in reasoning text at event
        periods across all tiers.  score = |matched| / |PATTERN_KEYWORDS|

    elevation_score:
        Fraction of (tier × event_period) pairs where the order placed is ≥10%
        above the tier's mean order over non-event periods.  Captures seasonal
        responsiveness even when models reason arithmetically without verbalising
        festival names.

    pattern_score:
        Mean of the two sub-scores.
    """
    # ── Keyword sub-score ────────────────────────────────────────────────────
    matched: set[str] = set()
    for pr in period_records:
        if pr["period"] not in PATTERN_PERIODS:
            continue
        for tier_key in TIERS:
            llm = pr["tiers"][tier_key].get("llm_response") or {}
            reasoning = (llm.get("reasoning") or "").lower()
            for kw in PATTERN_KEYWORDS:
                if kw in reasoning:
                    matched.add(kw)
    keyword_score = round(len(matched) / len(PATTERN_KEYWORDS), 4)

    # ── Elevation sub-score ──────────────────────────────────────────────────
    elevated = 0
    total_pairs = len(TIERS) * len(PATTERN_PERIODS)

    for tier_key in TIERS:
        # Mean order over non-event ordering periods
        non_event_orders = [
            pr["tiers"][tier_key]["order_placed"]
            for pr in period_records
            if pr["period"] in ORDERING_PERIODS
            and pr["period"] not in PATTERN_PERIODS
            and pr["tiers"][tier_key]["order_placed"] is not None
        ]
        if not non_event_orders:
            continue
        baseline = sum(non_event_orders) / len(non_event_orders)

        for pr in period_records:
            if pr["period"] not in PATTERN_PERIODS:
                continue
            order = pr["tiers"][tier_key].get("order_placed")
            if order is not None and baseline > 0 and order >= baseline * 1.1:
                elevated += 1

    elevation_score = round(elevated / total_pairs, 4) if total_pairs > 0 else 0.0

    return {
        "keyword_score": keyword_score,
        "elevation_score": elevation_score,
        "pattern_score": round((keyword_score + elevation_score) / 2, 4),
    }


def _compute_run_metrics(period_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute all per-tier metrics for a single run."""
    metrics: dict[str, Any] = {"tiers": {}}

    for tier_key in TIERS:
        # Accumulators over all 13 periods
        stockout_count = 0
        excess_inventory_sum = 0
        clamp_count = 0

        # Arrays over ordering periods 1-12 only (for OVAR)
        orders: list[int] = []
        demands: list[int] = []

        for pr in period_records:
            tr = pr["tiers"][tier_key]
            demand_recv: int = tr["demand_received"]
            inv_after: int = tr["inventory_after_fulfillment"]
            backlog_after: int = tr["backlog_after"]
            order_placed = tr["order_placed"]
            clamped: bool = tr["clamp_applied"]

            # Stockout: unfulfilled obligation remains after this period
            if backlog_after > 0:
                stockout_count += 1

            # Excess inventory in surplus periods (inventory > demand after fulfil)
            if inv_after > demand_recv:
                excess_inventory_sum += inv_after - demand_recv

            if clamped:
                clamp_count += 1

            # OVAR arrays — ordering periods only
            if pr["period"] in ORDERING_PERIODS:
                # order_placed is always an int (not None) for periods 1-12
                orders.append(order_placed)   # type: ignore[arg-type]
                demands.append(demand_recv)

        # ── OVAR ─────────────────────────────────────────────────────────────
        var_demand = float(np.var(demands, ddof=0))
        var_orders = float(np.var(orders, ddof=0))
        ovar = None if var_demand == 0.0 else round(var_orders / var_demand, 6)

        # ── Parse errors ──────────────────────────────────────────────────────
        parse_error_count = sum(
            1
            for pr in period_records
            if pr["period"] in ORDERING_PERIODS
            and (pr["tiers"][tier_key].get("llm_response") or {}).get("parse_error") is not None
        )

        # ── Secondary metrics ─────────────────────────────────────────────────
        total_ordered = int(sum(orders))
        max_order = max(orders) if orders else 0
        max_demand = max(demands) if demands else 0
        peak_overshoot = (
            round(max_order / max_demand, 4) if max_demand > 0 else None
        )

        cost_usd = round(sum(
            (pr["tiers"][tier_key].get("llm_response") or {}).get("cost_usd", 0.0)
            for pr in period_records
        ), 6)

        metrics["tiers"][tier_key] = {
            "ovar": ovar,
            "var_orders": round(var_orders, 2),
            "var_demand": round(var_demand, 2),
            "stockout_count": stockout_count,
            "excess_inventory_sum": excess_inventory_sum,
            "total_ordered": total_ordered,
            "peak_overshoot": peak_overshoot,
            "clamp_count": clamp_count,
            "parse_error_count": parse_error_count,
            "cost_usd": cost_usd,
        }

    metrics["total_cost_usd"] = round(
        sum(metrics["tiers"][t]["cost_usd"] for t in TIERS), 6
    )
    metrics.update(_compute_pattern_score(period_records))
    return metrics

# ---------------------------------------------------------------------------
# Aggregation across 5 runs
# ---------------------------------------------------------------------------

def aggregate_runs(
    run_results: list[dict[str, Any]], config_key: str
) -> dict[str, Any]:
    """Aggregate per-run metrics into a single config-level summary."""
    cfg = CONFIGS[config_key]
    agg: dict[str, Any] = {
        "config": config_key,
        "model": cfg["model"],
        "treatment": cfg["treatment"],
        "n_runs": len(run_results),
        "tiers": {},
    }

    for tier_key in TIERS:
        ovars: list[float] = []
        undefined_count = 0
        stockouts, excess_invs, totals, peak_os, clamps, parse_errors = [], [], [], [], [], []

        for run in run_results:
            tm = run["metrics"]["tiers"][tier_key]
            if tm["ovar"] is None:
                undefined_count += 1
            else:
                ovars.append(tm["ovar"])
            stockouts.append(tm["stockout_count"])
            excess_invs.append(tm["excess_inventory_sum"])
            totals.append(tm["total_ordered"])
            if tm["peak_overshoot"] is not None:
                peak_os.append(tm["peak_overshoot"])
            clamps.append(tm["clamp_count"])
            parse_errors.append(tm.get("parse_error_count", 0))

        # OVAR summary
        if ovars:
            mean_ovar = float(np.mean(ovars))
            std_ovar = float(np.std(ovars, ddof=0))
            # CV — if mean is near zero report std directly instead
            if mean_ovar > 0.01:
                cv_pct: float | None = round(std_ovar / mean_ovar * 100, 2)
                std_fallback: float | None = None
            else:
                cv_pct = None
                std_fallback = round(std_ovar, 6)
            ovar_mean_out: float | None = round(mean_ovar, 6)
            ovar_std_out: float | None = round(std_ovar, 6)
        else:
            ovar_mean_out = ovar_std_out = cv_pct = std_fallback = None

        total_parse_errors = int(sum(parse_errors))
        if total_parse_errors > 0:
            logger.warning(
                "PARSE ERRORS detected in %s / %s: %d error(s) across %d runs — "
                "affected order_quantity values were coerced to 0 and OVAR may be distorted.",
                config_key, tier_key, total_parse_errors, len(run_results),
            )

        agg["tiers"][tier_key] = {
            "ovar_mean": ovar_mean_out,
            "ovar_std": ovar_std_out,
            "ovar_undefined_count": undefined_count,
            "ovar_cv_pct": cv_pct,
            "ovar_std_fallback": std_fallback,
            "stockout_count_mean": round(float(np.mean(stockouts)), 2),
            "excess_inventory_mean": round(float(np.mean(excess_invs)), 0),
            "total_ordered_mean": round(float(np.mean(totals)), 0),
            "peak_overshoot_mean": (
                round(float(np.mean(peak_os)), 4) if peak_os else None
            ),
            "clamp_count_mean": round(float(np.mean(clamps)), 2),
            "parse_error_count_total": total_parse_errors,
        }

    for key in ("pattern_score", "keyword_score", "elevation_score"):
        vals = [r["metrics"][key] for r in run_results]
        agg[f"{key}_mean"] = round(float(np.mean(vals)), 4)
        agg[f"{key}_std"]  = round(float(np.std(vals, ddof=0)), 4)

    run_costs = [r["metrics"]["total_cost_usd"] for r in run_results]
    agg["total_cost_usd_per_run_mean"] = round(float(np.mean(run_costs)), 4)
    agg["total_cost_usd_all_runs"] = round(float(sum(run_costs)), 4)
    return agg

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=_json_default)
    logger.info("Wrote %s", path.relative_to(ROOT))


def _json_default(obj: Any) -> Any:
    """Fallback serialiser for numpy scalars that slipped through."""
    if isinstance(obj, (int,)):
        return int(obj)
    if isinstance(obj, (float,)):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def _raw_path(config_key: str, run_number: int) -> Path:
    return RESULTS_RAW / f"{config_key}_run{run_number:02d}.json"


def _agg_path(config_key: str) -> Path:
    return RESULTS_AGG / f"{config_key}_aggregated.json"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("═══ Agentic Bullwhip Experiment — Version 1 ═══")
    logger.info("Configs: %s", list(CONFIGS.keys()))
    logger.info("Runs per config: %d | Total LLM calls: %d",
                RUNS_PER_CONFIG,
                len(CONFIGS) * RUNS_PER_CONFIG * len(ORDERING_PERIODS) * len(TIERS))

    demand_rows = load_demand()
    logger.info("Loaded %d demand periods from %s", len(demand_rows), DATA_CSV.name)

    grand_total_cost: float = 0.0

    for config_key in CONFIGS:
        logger.info("▶ Config: %s", config_key)
        run_results: list[dict[str, Any]] = []

        for run_num in range(1, RUNS_PER_CONFIG + 1):
            run_data = run_simulation(config_key, run_num, demand_rows)
            logger.info("    Run %02d cost: $%.4f", run_num, run_data["metrics"]["total_cost_usd"])
            _write_json(_raw_path(config_key, run_num), run_data)
            run_results.append(run_data)

        agg = aggregate_runs(run_results, config_key)
        _write_json(_agg_path(config_key), agg)
        grand_total_cost += agg["total_cost_usd_all_runs"]

        # Quick summary to console
        logger.info("  Aggregated OVAR:")
        for tier_key in TIERS:
            t = agg["tiers"][tier_key]
            ovar_str = (
                f"{t['ovar_mean']:.3f} ± {t['ovar_std']:.3f}"
                if t["ovar_mean"] is not None
                else "undefined"
            )
            logger.info("    %s: %s", tier_key, ovar_str)
        logger.info("  Config cost: $%.4f total ($%.4f/run mean)",
                    agg["total_cost_usd_all_runs"], agg["total_cost_usd_per_run_mean"])

    logger.info("═══ Experiment complete | Grand total cost: $%.4f ═══", grand_total_cost)


if __name__ == "__main__":
    main()
