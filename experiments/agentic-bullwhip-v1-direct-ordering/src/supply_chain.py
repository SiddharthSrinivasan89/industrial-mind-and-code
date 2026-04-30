"""
supply_chain.py
TierState dataclass and the two-phase simulation step functions.

Each period is split into two phases so that run_experiment.py can
build the LLM prompt from the post-fulfillment state before dispatching
the order — matching the spec's Step 4 ordering:
  Phase A  (step_receive_fulfill): Steps 1-3  — receive, fulfil, update backlog
  Phase B  (step_place_order):     Step 4     — clamp & dispatch order
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inventory_manager import receive_deliveries, fulfill_demand


@dataclass
class TierState:
    inventory: int
    backlog: int = 0
    in_transit: list[dict[str, Any]] = field(default_factory=list)


def step_receive_fulfill(
    state: TierState,
    demand: int,
    period: int,
) -> tuple[TierState, dict[str, Any]]:
    """
    Steps 1-3 of the simulation for one tier in one period.

    1. Receive any deliveries whose arriving_period <= current period.
    2. Fulfil current demand + any pre-existing backlog from on-hand stock.
    3. Any shortfall stays / becomes backlog; inventory floor = 0.

    Mutates `state` in-place and also returns it.
    The returned dict is a partial period record (no order info yet).
    """
    inv_start = state.inventory
    backlog_start = state.backlog
    in_transit_start = [dict(o) for o in state.in_transit]

    # Step 1 — receive deliveries
    state.in_transit, units_received = receive_deliveries(state.in_transit, period)
    state.inventory += units_received
    inv_after_delivery = state.inventory

    # Steps 2-3 — fulfil demand + backlog
    state.inventory, state.backlog = fulfill_demand(state.inventory, state.backlog, demand)

    partial_record: dict[str, Any] = {
        "inventory_start": inv_start,
        "backlog_start": backlog_start,
        "in_transit_start": in_transit_start,
        "units_received": units_received,
        "inventory_after_delivery": inv_after_delivery,
        "demand_received": demand,
        "inventory_after_fulfillment": state.inventory,
        "backlog_after": state.backlog,
        # in_transit_mid is what the LLM actually sees in the prompt:
        # arrived orders have been removed; new order not yet dispatched.
        "in_transit_mid": [dict(o) for o in state.in_transit],
    }
    return state, partial_record


def step_place_order(
    state: TierState,
    order_qty: int | None,
    period: int,
    lead_time: int = 1,
) -> tuple[TierState, dict[str, Any]]:
    """
    Step 4 of the simulation for one tier in one period.

    Clamps negative orders to zero; appends the order to in_transit
    with arriving_period = period + lead_time.
    If order_qty is None (period 13 sentinel), the dispatch block is skipped
    entirely — state is not mutated.  Calling this function with None is
    therefore a deliberate no-op: it only produces an order_record with
    order_placed=None so the period log is complete.

    Mutates `state` in-place and also returns it.
    """
    clamp_applied = False

    if order_qty is not None:
        if order_qty < 0:
            order_qty = 0
            clamp_applied = True
        state.in_transit.append(
            {"quantity": order_qty, "arriving_period": period + lead_time}
        )

    order_record: dict[str, Any] = {
        "order_placed": order_qty,      # None for period 13
        "clamp_applied": clamp_applied,
        "in_transit_end": [dict(o) for o in state.in_transit],
    }
    return state, order_record
