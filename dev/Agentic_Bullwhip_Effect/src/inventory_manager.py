"""
inventory_manager.py
Pure helper functions for inventory, backlog, and in-transit logic.
No side effects; no local module imports.
"""
from __future__ import annotations

from typing import Any


def receive_deliveries(
    in_transit: list[dict[str, Any]], current_period: int
) -> tuple[list[dict[str, Any]], int]:
    """
    Split in_transit into arrived and still-pending batches.

    Returns:
        (remaining_in_transit, units_received)
        remaining_in_transit: orders whose arriving_period > current_period
        units_received: sum of quantities that arrived this period
    """
    arrived = [o for o in in_transit if o["arriving_period"] <= current_period]
    remaining = [o for o in in_transit if o["arriving_period"] > current_period]
    units_received = sum(o["quantity"] for o in arrived)
    return remaining, units_received


def fulfill_demand(inventory: int, backlog: int, demand: int) -> tuple[int, int]:
    """
    Attempt to fulfil current-period demand plus any existing backlog from on-hand stock.

    Inventory floor is zero; any shortfall becomes (or adds to) backlog.

    Returns:
        (new_inventory, new_backlog)
    """
    total_needed = demand + backlog
    fulfilled = min(inventory, total_needed)
    new_inventory = inventory - fulfilled  # >= 0 by construction
    new_backlog = total_needed - fulfilled  # 0 if fully met
    return new_inventory, new_backlog


def format_in_transit(in_transit: list[dict[str, Any]]) -> str:
    """
    Format in-transit orders for inclusion in an LLM prompt.

    Single item  → "12,000 units (arriving period 3)"
    Multiple     → one per line, "  "-joined so they indent cleanly under the
                   "- Orders in transit:\n  {result}" bullet.
    Empty list   → "None"
    """
    if not in_transit:
        return "None"
    return "\n  ".join(
        f"{o['quantity']:,} units (arriving period {o['arriving_period']})"
        for o in in_transit
    )
