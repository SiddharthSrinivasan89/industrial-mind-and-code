"""
blind_agent.py
Prompt builders for the blind treatment.

The agent receives no product name, geography, calendar context, or role.
Only raw inventory state and demand numbers are provided.
"""
from __future__ import annotations

from supply_chain import TierState
from inventory_manager import format_in_transit

SYSTEM_PROMPT = (
    "You are a supply chain ordering agent.\n"
    "Always respond with valid JSON only.\n"
    "No additional text before or after the JSON object."
)


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_prompt(state: TierState, demand: int) -> str:
    """
    Build the blind user prompt from the post-fulfillment tier state and
    the demand received this period.

    `state` must be the state AFTER step_receive_fulfill has run so that
    inventory, backlog, and in_transit_mid reflect what the agent actually
    sees at decision time.
    """
    transit_text = format_in_transit(state.in_transit)
    return (
        "Decide how many units to order for the next period.\n\n"
        "Current state:\n"
        f"- Inventory on hand: {state.inventory:,} units\n"
        f"- Backlog (unfulfilled orders): {state.backlog:,} units\n"
        "- Orders in transit:\n"
        f"  {transit_text}\n"
        "- Lead time: 1 month(s)\n\n"
        f"This month's demand: {demand:,} units\n\n"
        "Respond with ONLY a JSON object:\n"
        '{"order_quantity": <number>, "reasoning": "<brief explanation>"}'
    )
