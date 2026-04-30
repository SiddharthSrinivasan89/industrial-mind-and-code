"""
Dry-run backend for V4 WorldEvents.

Set DRY_RUN=1 to activate. agent_interface.py routes all calls here instead of the
real backends. Use this to validate the full simulation+metrics pipeline before
spending any LLM budget.

Expected dry-run results
------------------------
  intent_compliance_rate = 1.0 (NEUTRAL is always valid)
  intent_class = NEUTRAL every period → multiplier = 1.00
"""

import logging

logger = logging.getLogger(__name__)


def get_intent_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """Always return NEUTRAL intent — enables pipeline validation without API calls."""
    logger.debug("dry_run intent: run=%s period=%d tier=%s → NEUTRAL", run_id, period, tier)
    return {
        "intent":            "NEUTRAL",
        "rationale":         "",
        "attempt_number":    1,
        "latency_ms":        0.0,
        "ttft_ms":           0.0,
        "prompt_tokens":     0,
        "completion_tokens": 0,
        "generation_tps":    0.0,
    }
