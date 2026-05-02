"""
Dry-run backend.

Returns a deterministic order quantity equal to the demand received by the agent.
This is the naive pass-through policy expressed as an LLM backend, so you can
sanity-check the full simulation→metrics→output pipeline without spending any
LLM API calls or requiring API credentials.

Usage
-----
Set DRY_RUN=1 in your .env file (or export it in the shell).  agent_interface.py
checks this flag before loading the real backend and routes all calls here instead.

The order quantity is extracted from the user_prompt (the "Demand received" line)
so the backend is self-contained — it does not need any env vars beyond DRY_RUN=1.

Expected results when using this backend
-----------------------------------------
  OVAR   ≈ 1.0   (every tier passes demand through exactly, like naive_passthrough)
  Stockouts: 0   (no amplification, inventory stays in balance)
  Pattern score: 0.0   (rationale is always empty — no keyword to detect)

If you see OVAR ≠ 1.0 or any stockouts in dry-run mode, there is a bug in the
simulation or metrics logic, not in any LLM call.
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
    Extract demand_received from the user_prompt and return it as the order quantity.

    Parsing is intentionally simple: the parser looks for the line that starts with
    "Demand received this period:" and pull the integer after it.
    If parsing fails (e.g. prompt format changed), the parser falls back to 0 and log a warning.
    """
    match = re.search(r"Demand received this period:\s*([\d,]+)", user_prompt)
    if match:
        order_qty = int(match.group(1).replace(",", ""))
    else:
        logger.warning(
            "dry_run: run=%s period=%d tier=%s could not parse demand from prompt — defaulting to 0",
            run_id, period, tier,
        )
        order_qty = 0

    logger.debug(
        "dry_run: run=%s period=%d tier=%s → order=%d",
        run_id, period, tier, order_qty,
    )
    return {"order_quantity": order_qty, "rationale": ""}
