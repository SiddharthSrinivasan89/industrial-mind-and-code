"""
Context Agent
=============
Receives ambient context: geography, product category, time of year.
Never told what specific patterns exist. Must infer Navratri, Diwali,
monsoon, FY-end rush, wedding season etc. from world knowledge.
"""

from typing import Optional
from base_agent import BaseAgent


class ContextAgent(BaseAgent):

    ROLE_DESC = {
        "oem": (
            "You are Tatva Motors' vehicle assembly plant in India. You receive "
            "monthly production dispatch targets and must order automotive lighting "
            "assemblies (headlamps, tail lamps, DRLs) from your Tier 1 lighting supplier."
        ),
        "ancillary": (
            "You are an auto ancillary lighting manufacturer in India (like a leading Tier 1 "
            "auto ancillary) supplying Tatva Motors. You receive lighting assembly "
            "orders from the OEM and must order LED modules and optical components "
            "from your Tier 2 supplier."
        ),
        "ancillary_supplier": (
            "You are an LED module and lighting component manufacturer in India. "
            "You supply automotive lighting assemblers who serve Tatva Motors. "
            "You receive component orders and must decide production volume."
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

        month_name = period_metadata.get("month_name", "Unknown") if period_metadata else "Unknown"
        year = period_metadata.get("year", "Unknown") if period_metadata else "Unknown"

        return f"""{role_desc}

Product: Automotive lighting assemblies (headlamps, tail lamps, DRLs) for Tatva Motors passenger vehicles (Volta, Prism, Horizon, Savana, Arc)
Market: India (automotive component supply chain)

Current state:
- Month: {month_name} {year} (period {self.state.current_period})
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

Before placing your order, analyze the production and ordering data for patterns
you recognize — seasonal, cultural, financial calendar, promotional, or
otherwise. Consider what these patterns mean for upcoming production schedules.

Then decide how many units to order from your {target}.
Balance avoiding stockouts against excess inventory holding costs.

Respond with ONLY a JSON object:
{{"pattern_analysis": "<your analysis of production and ordering patterns>", "order_quantity": <number>, "reasoning": "<brief explanation>"}}"""
