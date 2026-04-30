"""
Dry-run backend for V6 StatelessSwing.

Set DRY_RUN=1 to activate. Returns alpha=0.3 (the fixed optimal) every period
so the full simulation+metrics pipeline can be validated without any API calls.

Expected dry-run results
------------------------
  alpha_fallback_rate = 0.0  (alpha=0.3 is always valid)
  alpha_chosen = 0.3 every period → OVAR should match exp_smooth_0.3 baseline (~0.545)
"""

import logging

logger = logging.getLogger(__name__)


def get_alpha_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """Always return alpha=0.3 — enables pipeline validation without API calls."""
    logger.debug("dry_run alpha: run=%s period=%d tier=%s → 0.3", run_id, period, tier)
    return {
        "alpha":             0.3,
        "rationale":         "dry-run",
        "attempt_number":    1,
        "latency_ms":        0.0,
        "ttft_ms":           0.0,
        "prompt_tokens":     0,
        "completion_tokens": 0,
        "generation_tps":    0.0,
    }
