"""
Blind Agent
===========
Sees only numbers. No geography, no product context, no dates.
Must decide ordering purely from demand signals and inventory state.
"""

from typing import Optional
from base_agent import BaseAgent


class BlindAgent(BaseAgent):

    ROLE_DESC = {
        "oem": (
            "You are an OEM vehicle assembly plant. You receive vehicle "
            "production targets and must order automotive lighting assemblies "
            "from your Tier 1 supplier."
        ),
        "ancillary": (
            "You are an auto ancillary lighting manufacturer. You receive "
            "lighting assembly orders from the OEM and must order LED modules "
            "and components from your Tier 2 supplier."
        ),
        "ancillary_supplier": (
            "You are an LED module and lighting component manufacturer. "
            "You receive orders from the lighting assembler and must decide "
            "production volume."
        ),
    }

    ORDER_TARGET = {
        "oem": "lighting supplier",
        "ancillary": "LED/component supplier",
        "ancillary_supplier": "production line",
    }

    DEMAND_LABEL = {
        "oem": "This month's vehicle production target",
        "ancillary": "This month's lighting order from OEM",
        "ancillary_supplier": "This month's component order from lighting manufacturer",
    }

    def build_prompt(self, demand: int, forecast: list,
                     period_metadata: Optional[dict] = None) -> str:

        role_desc = self.ROLE_DESC[self.state.role]
        target = self.ORDER_TARGET[self.state.role]
        demand_label = self.DEMAND_LABEL[self.state.role]
        tu = self.state.time_unit.title()

        return f"""{role_desc}

Current state:
- {tu}: {self.state.current_period}
- Inventory on hand: {self.state.inventory_on_hand:,} units
- Backlog (unfulfilled orders): {self.state.backlog:,} units
- Orders in transit:
{self._format_in_transit()}
- Lead time: {self.state.lead_time_periods} {self.state.time_unit}(s)

{demand_label}: {demand:,} units

Recent order history:
{self._format_order_history()}

Demand forecast:
{self._format_forecast(forecast)}

Decide how many units to order from your {target}.
Balance avoiding stockouts against excess inventory holding costs.

Respond with ONLY a JSON object:
{{"order_quantity": <number>, "reasoning": "<brief explanation>"}}"""
