"""
Inventory Manager
==================
Tracks inventory, lead times, deliveries, and fulfillment
for a single supply chain tier.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PeriodRecord:
    period: int
    incoming_demand: int
    order_placed: int
    inventory_before: int
    inventory_after: int
    deliveries_received: int
    fulfilled: int
    backlog: int
    stockout: bool
    was_clamped: bool


class InventoryManager:
    """Manages inventory for one tier."""

    def __init__(self, role: str, initial_inventory: int = 180000,
                 lead_time_periods: int = 1):
        self.role = role
        self.inventory = initial_inventory
        self.lead_time = lead_time_periods
        self.backlog = 0
        self.orders_in_transit: list = []
        self.period_records: list = []

    def process_period(self, period: int, incoming_demand: int,
                       order_quantity: int, was_clamped: bool = False) -> PeriodRecord:
        """Process one period: receive -> fulfill -> order."""
        inv_before = self.inventory

        # 1. Receive deliveries
        deliveries = self._receive(period)

        # 2. Fulfill demand + backlog
        total = incoming_demand + self.backlog
        if self.inventory >= total:
            fulfilled = total
            self.inventory -= total
            self.backlog = 0
            stockout = False
        else:
            fulfilled = self.inventory
            self.backlog = total - fulfilled
            self.inventory = 0
            stockout = True

        # 3. Place order in transit
        self.orders_in_transit.append({
            "quantity": order_quantity,
            "arriving_period": period + self.lead_time,
        })

        record = PeriodRecord(
            period=period, incoming_demand=incoming_demand,
            order_placed=order_quantity, inventory_before=inv_before,
            inventory_after=self.inventory, deliveries_received=deliveries,
            fulfilled=fulfilled, backlog=self.backlog,
            stockout=stockout, was_clamped=was_clamped,
        )
        self.period_records.append(record)

        logger.debug(
            f"[{self.role}] P{period}: "
            f"dem={incoming_demand:,} ord={order_quantity:,} "
            f"del={deliveries:,} inv={self.inventory:,} bl={self.backlog:,}"
        )
        return record

    def _receive(self, period: int) -> int:
        arrived = 0
        remaining = []
        for o in self.orders_in_transit:
            if o["arriving_period"] <= period:
                arrived += o["quantity"]
            else:
                remaining.append(o)
        self.orders_in_transit = remaining
        self.inventory += arrived
        return arrived

    def get_state_snapshot(self) -> dict:
        return {
            "inventory_on_hand": self.inventory,
            "backlog": self.backlog,
            "orders_in_transit": [
                {"quantity": o["quantity"], "arriving_period": o["arriving_period"]}
                for o in self.orders_in_transit
            ],
        }

    def get_orders_placed(self) -> list:
        return [r.order_placed for r in self.period_records]

    def get_incoming_demands(self) -> list:
        return [r.incoming_demand for r in self.period_records]

    def get_inventory_levels(self) -> list:
        return [r.inventory_after for r in self.period_records]

    def get_stockout_periods(self) -> list:
        return [r.period for r in self.period_records if r.stockout]

    def export_records(self) -> list:
        return [{
            "period": r.period, "role": self.role,
            "incoming_demand": r.incoming_demand,
            "order_placed": r.order_placed,
            "inventory_before": r.inventory_before,
            "inventory_after": r.inventory_after,
            "deliveries_received": r.deliveries_received,
            "fulfilled": r.fulfilled, "backlog": r.backlog,
            "stockout": r.stockout, "was_clamped": r.was_clamped,
        } for r in self.period_records]
