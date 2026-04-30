"""
persona_agents.py
Three isolated agent personas for the context treatment.

Each tier agent has a distinct role identity and system prompt. Crucially, each
agent's context window contains ONLY what that actor would know in reality:
  - OEM agent (Tatva Motors) sees consumer despatch targets
  - Ancillary agent (BrightArc Lighting) sees only OEM orders — no consumer demand
  - Component agent (LumiCore Electronics) sees only BrightArc orders — deepest blindspot

Every period, each agent makes a fresh, isolated LLM call. The output
order_quantity from each tier becomes the demand input passed to the next
tier's agent — the handoff happens in the simulation loop, not here.

Agent personas:
  oem       — TATVA-OEM-PROCUREMENT-AGENT
  ancillary — BRIGHTARC-SUPPLY-AGENT
  component — LUMICORE-PRODUCTION-AGENT
"""
from __future__ import annotations

from supply_chain import TierState
from inventory_manager import format_in_transit

# ---------------------------------------------------------------------------
# System prompts — one per persona, each establishing a distinct worldview
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "oem": (
        "You are TATVA-OEM-PROCUREMENT-AGENT, an autonomous ordering agent for Tatva Motors.\n"
        "Your function: manage procurement of Vecta Lighting Assemblies for Tatva's EV production line.\n"
        "You receive a monthly production despatch target and decide how many Lighting Assemblies "
        "to order from your ancillary supplier.\n"
        "Your objectives: prevent production line stoppages, maintain lean inventory, "
        "and anticipate seasonal demand peaks in Vecta sales.\n"
        "Always respond with valid JSON only.\n"
        "No additional text before or after the JSON object."
    ),
    "ancillary": (
        "You are BRIGHTARC-SUPPLY-AGENT, an autonomous ordering agent for BrightArc Lighting Solutions.\n"
        "Your function: fulfill Lighting Assembly orders from Tatva Motors and replenish "
        "LED component stock from your upstream supplier.\n"
        "You receive only the order placed by Tatva Motors each month — "
        "you have no visibility into Tatva's end-consumer despatch volumes or market demand.\n"
        "Your objectives: fulfill incoming OEM orders reliably, avoid excess component inventory, "
        "and protect against upstream supply disruptions.\n"
        "Always respond with valid JSON only.\n"
        "No additional text before or after the JSON object."
    ),
    "component": (
        "You are LUMICORE-PRODUCTION-AGENT, an autonomous production scheduling agent for LumiCore Electronics.\n"
        "Your function: schedule LED component kit production to fulfill orders from BrightArc Lighting.\n"
        "You receive only the order placed by BrightArc each month — "
        "you have no visibility into BrightArc's customers, OEM demand, or end-consumer market.\n"
        "Your objectives: fulfill incoming orders on time, optimise batch production efficiency, "
        "and minimise finished-goods buffer inventory.\n"
        "Always respond with valid JSON only.\n"
        "No additional text before or after the JSON object."
    ),
}

# ---------------------------------------------------------------------------
# Demand labels — what each persona calls the demand they receive
# ---------------------------------------------------------------------------

_DEMAND_LABELS: dict[str, str] = {
    "oem": "This month's Vecta production despatch target",
    "ancillary": "This month's Lighting Assembly order from Tatva Motors",
    "component": "This month's LED component kit order from BrightArc",
}

# ---------------------------------------------------------------------------
# Upstream partner — what each persona orders from
# ---------------------------------------------------------------------------

_UPSTREAM_PARTNERS: dict[str, str] = {
    "oem": "BrightArc (ancillary supplier)",
    "ancillary": "LumiCore (LED component supplier)",
    "component": "your production line",
}

# ---------------------------------------------------------------------------
# Calendar context — only OEM sees the month/year (they receive a despatch
# target tied to the calendar). Ancillary and component see only the order
# quantity, matching what they would actually observe.
# ---------------------------------------------------------------------------

_SHOW_CALENDAR: dict[str, bool] = {
    "oem": True,
    "ancillary": True,   # BrightArc may infer seasonality from Tatva's orders
    "component": False,  # LumiCore has no calendar signal — purely reactive
}


def build_system_prompt(tier_key: str) -> str:
    return _SYSTEM_PROMPTS[tier_key]


def build_user_prompt(
    tier_key: str,
    state: TierState,
    demand: int,
    month_name: str,
    year: int,
    period: int,
) -> str:
    """
    Build an isolated persona prompt for one tier.

    `state` must be the state AFTER step_receive_fulfill so that
    inventory, backlog, and in_transit reflect the decision moment.
    """
    demand_label = _DEMAND_LABELS[tier_key]
    upstream = _UPSTREAM_PARTNERS[tier_key]
    transit_text = format_in_transit(state.in_transit)

    calendar_line = (
        f"- Month: {month_name} {year} (period {period})\n"
        if _SHOW_CALENDAR[tier_key]
        else ""
    )

    return (
        "Current state:\n"
        f"{calendar_line}"
        f"- Inventory on hand: {state.inventory:,} units\n"
        f"- Backlog (unfulfilled orders): {state.backlog:,} units\n"
        "- Orders in transit:\n"
        f"  {transit_text}\n"
        "- Lead time: 1 month(s)\n\n"
        f"{demand_label}: {demand:,} units\n\n"
        f"Decide how many units to order from {upstream}.\n\n"
        "Respond with ONLY a JSON object:\n"
        '{"order_quantity": <number>,\n'
        ' "reasoning": "<brief explanation>"}'
    )
