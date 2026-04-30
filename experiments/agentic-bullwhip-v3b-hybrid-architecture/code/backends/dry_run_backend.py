"""
Dry-run backend — V3b hybrid architecture.

For hybrid policy: returns safety_stock_multiplier = 1.0 (neutral, no adjustment).
For legacy llm policy: returns order_quantity = demand_received (passthrough).

This lets you validate the full simulation → metrics → output pipeline with
zero LLM API calls. With multiplier=1.0 throughout, the hybrid execution layer
runs pure policy_smoothed_out_with_ss, which should produce moderate OVAR (not 4+).

Usage
-----
Set DRY_RUN=1 in your .env file or shell:
    DRY_RUN=1 python run_experiment.py --experiments baselines H1 --runs 2 --env .env.local

Expected results (dry run, hybrid policy, multiplier=1.0):
  ss_multiplier: always 1.0
  llm_fallback:  always False
  OVAR:          should match the deterministic hybrid_control run (OUT-style at multiplier=1.0)
  Stockouts:     low (inventory buffer from safety stock)

If OVAR is > 4.0 in dry run, there is a bug in simulation or metrics logic.
"""

import logging
import re

logger = logging.getLogger(__name__)


def get_order_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """
    Legacy order-quantity backend (used when policy="llm").
    Returns demand passthrough — produces OVAR ≈ 1.0.
    """
    match = re.search(r"Demand received this period:\s*([\d,]+)", user_prompt)
    if match:
        order_qty = int(match.group(1).replace(",", ""))
    else:
        logger.warning(
            "dry_run: run=%s period=%d tier=%s could not parse demand — defaulting to 0",
            run_id, period, tier,
        )
        order_qty = 0

    logger.debug("dry_run order: run=%s period=%d tier=%s → order=%d", run_id, period, tier, order_qty)
    return {"order_quantity": order_qty, "rationale": ""}


def get_ss_multiplier(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """
    Hybrid multiplier backend (used when policy="hybrid").
    Returns multiplier = 1.0 (neutral — no safety stock adjustment).

    This simulates a perfectly compliant LLM that always returns the default.
    The hybrid execution layer then runs policy_smoothed_out_with_ss at base safety stock.
    """
    logger.debug("dry_run multiplier: run=%s period=%d tier=%s → 1.0", run_id, period, tier)
    return {
        "safety_stock_multiplier": 1.0,
        "rationale": "",
        "attempt_number": 1,
        "latency_ms": 0.0,
        "ttft_ms": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "generation_tps": 0.0,
    }
