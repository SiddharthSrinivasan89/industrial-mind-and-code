"""
context_agent.py
Prompt builders for the context treatment.

The agent receives full role identity (company, product, supply chain position),
the calendar month/year, and tier-specific demand labels and upstream-partner names
in addition to the inventory state numbers.

Prompt structure:
    Block 1 — tier-specific role paragraph (always present)
    Block 2 — state snapshot + demand + instruction (same across tiers,
               with tier-specific demand label and upstream-partner name)
"""
from __future__ import annotations

from supply_chain import TierState
from inventory_manager import format_in_transit

SYSTEM_PROMPT = (
    "You are a supply chain ordering agent in the Indian automotive component industry.\n"
    "Always respond with valid JSON only.\n"
    "No additional text before or after the JSON object."
)

# Block 1 — role paragraphs (tier-specific)
_ROLE_BLOCKS: dict[str, str] = {
    "oem": (
        "Company: Tatva Motors, India. Product: Vecta Lighting Assembly. "
        "Upstream supplier: ancillary lighting manufacturer. "
        "Each month: receive a production despatch target and place a Lighting Assembly order."
    ),
    "ancillary": (
        "Company: Lighting manufacturer, India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly orders). "
        "Upstream supplier: LED component manufacturer. "
        "Each month: receive a Lighting Assembly order and place an LED component order."
    ),
    "component": (
        "Company: LED component manufacturer, India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies. "
        "Each month: receive a component order and set production capacity."
    ),
}

# Demand label shown in Block 2 (tier-specific)
_DEMAND_LABELS: dict[str, str] = {
    "oem": "This month's Vecta despatch target",
    "ancillary": "This month's Lighting Assembly order from Tatva Motors",
    "component": "This month's LED component order from lighting manufacturer",
}

# Upstream partner named in the ordering instruction (tier-specific)
_UPSTREAM_PARTNERS: dict[str, str] = {
    "oem": "ancillary supplier",
    "ancillary": "LED component supplier",
    "component": "production line",
}


def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_user_prompt(
    tier_key: str,
    state: TierState,
    demand: int,
    month_name: str,
    year: int,
    period: int,
) -> str:
    """
    Build the context user prompt from tier identity, post-fulfillment state,
    demand, and the calendar date of the period.

    `state` must be the state AFTER step_receive_fulfill has run so that
    inventory, backlog, and in_transit reflect what the agent sees at
    decision time.
    """
    role_block = _ROLE_BLOCKS[tier_key]
    demand_label = _DEMAND_LABELS[tier_key]
    upstream = _UPSTREAM_PARTNERS[tier_key]
    transit_text = format_in_transit(state.in_transit)

    return (
        f"{role_block}\n\n"
        "Current state:\n"
        f"- Month: {month_name} {year} (period {period})\n"
        f"- Inventory on hand: {state.inventory:,} units\n"
        f"- Backlog (unfulfilled orders): {state.backlog:,} units\n"
        "- Orders in transit:\n"
        f"  {transit_text}\n"
        "- Lead time: 1 month(s)\n\n"
        f"{demand_label}: {demand:,} units\n\n"
        f"Decide how many units to order from your {upstream}.\n\n"
        "Respond with ONLY a JSON object:\n"
        '{"order_quantity": <number>,\n'
        ' "reasoning": "<brief explanation>"}'
    )
