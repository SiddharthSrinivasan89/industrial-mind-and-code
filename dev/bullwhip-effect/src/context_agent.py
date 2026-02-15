"""
Context Agent
=============
Receives ambient context: geography, product, time of year.
Knows it's ordering LED headlight assemblies for the Tatva Motors Vecta in India.
Must use domain knowledge to inform ordering decisions.
"""

from typing import Optional
from base_agent import BaseAgent


class ContextAgent(BaseAgent):

    SYSTEM_PROMPT = (
        "You are a supply chain ordering agent in the Indian automotive component industry. "
        "Always respond with valid JSON only. "
        "No additional text before or after the JSON object."
    )

    ROLE_DESC = {
        "oem": (
            "You are a Supply Chain Planner at Tatva Motors in India. "
            "You manage headlight assembly procurement for the Vecta. "
            "Each month you receive a production target and must order "
            "LED headlight assemblies from your lighting supplier."
        ),
        "ancillary": (
            "You are a Supply Chain Planner at a lighting manufacturer in India "
            "supplying Tatva Motors. You receive headlight assembly orders for "
            "the Vecta and must order LED modules from your component supplier."
        ),
        "ancillary_supplier": (
            "You are a Supply Chain Planner at an LED module manufacturer in India. "
            "You supply the lighting manufacturer who makes headlight assemblies "
            "for the Tatva Motors Vecta. You receive component orders and must "
            "decide production volume."
        ),
    }

    ORDER_TARGET = {
        "oem": "headlight supplier",
        "ancillary": "LED module supplier",
        "ancillary_supplier": "production line",
    }

    DEMAND_LABEL = {
        "oem": "This month's Vecta production target",
        "ancillary": "This month's headlight order from Tatva Motors",
        "ancillary_supplier": "This month's LED module order from lighting manufacturer",
    }

    def build_prompt(self, demand: int, forecast: list,
                     period_metadata: Optional[dict] = None) -> str:

        role_desc = self.ROLE_DESC[self.state.role]
        target = self.ORDER_TARGET[self.state.role]
        demand_label = self.DEMAND_LABEL[self.state.role]

        month_name = period_metadata.get("month_name", "Unknown") if period_metadata else "Unknown"
        year = period_metadata.get("year", "Unknown") if period_metadata else "Unknown"

        return f"""{role_desc}

Product: LED headlight assembly for the Tatva Motors Vecta
Market: India

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

Respond with ONLY a JSON object:
{{"pattern_analysis": "<your analysis of production and ordering patterns>", "order_quantity": <number>, "reasoning": "<brief explanation>"}}"""
