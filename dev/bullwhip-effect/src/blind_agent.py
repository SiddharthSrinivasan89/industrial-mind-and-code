"""
Blind Agent
===========
Sees only numbers + cost structure. No geography, no product, no dates, no role.
Must decide ordering purely from demand signals, inventory state, and cost trade-off.
"""

from typing import Optional
from base_agent import BaseAgent


class BlindAgent(BaseAgent):

    def build_prompt(self, demand: int, forecast: list,
                     period_metadata: Optional[dict] = None) -> str:

        tu = self.state.time_unit

        return f"""You are a replenishment agent. Decide how many units to order for next {tu}.

Current state:
- Inventory on hand: {self.state.inventory_on_hand:,} units
- Backlog (unfulfilled orders): {self.state.backlog:,} units
- Orders in transit:
{self._format_in_transit()}
- Lead time: {self.state.lead_time_periods} {tu}(s)

This {tu}'s demand: {demand:,} units

Recent order history:
{self._format_order_history()}

Cost structure:
- Holding cost: {self.holding_cost:,} per unit per {tu} (applied to ending inventory)
- Backlog cost: {self.backlog_cost:,} per unit per {tu} (applied to unmet demand)

Respond with ONLY a JSON object:
{{"order_quantity": <number>, "reasoning": "<brief explanation>"}}"""
