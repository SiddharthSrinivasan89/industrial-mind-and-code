"""
Base Agent
==========
Common logic for Blind and Context agents.
State management, prompt formatting, order validation.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Rolling state for a supply chain agent."""
    role: str
    current_period: int = 0
    inventory_on_hand: int = 0
    orders_in_transit: list = field(default_factory=list)
    order_history: list = field(default_factory=list)
    incoming_demand_this_period: int = 0
    lead_time_periods: int = 1
    backlog: int = 0
    time_unit: str = "month"


@dataclass
class OrderDecision:
    """Result of an agent's ordering decision."""
    period: int
    role: str
    order_quantity: int
    reasoning: str
    pattern_analysis: Optional[str] = None
    raw_response: Optional[dict] = None
    was_clamped: bool = False


class BaseAgent(ABC):
    """Abstract base for supply chain ordering agents."""

    # Generic system prompt — no geography, product, or market context.
    # Subclasses can override to add domain context (see ContextAgent).
    SYSTEM_PROMPT = (
        "You are a supply chain ordering agent. "
        "Always respond with valid JSON only. "
        "No additional text before or after the JSON object."
    )

    def __init__(self, role: str, initial_inventory: int = 180000,
                 lead_time_periods: int = 1, time_unit: str = "month"):
        """
        Args:
            role: 'oem', 'ancillary', or 'ancillary_supplier'
            initial_inventory: Starting stock (~4 months of dispatches)
            lead_time_periods: Delivery lead time in periods
            time_unit: 'month' or 'week'
        """
        self.state = AgentState(
            role=role,
            inventory_on_hand=initial_inventory,
            lead_time_periods=lead_time_periods,
            time_unit=time_unit,
        )
        self.decisions: list = []

    @abstractmethod
    def build_prompt(self, demand: int, forecast: list,
                     period_metadata: Optional[dict] = None) -> str:
        """Build the prompt for this agent category."""
        pass

    def decide_order(self, demand: int, forecast: list,
                     period_metadata: Optional[dict], client,
                     model_tier: str,
                     max_order_multiplier: float = 5.0) -> OrderDecision:
        """
        Call LLM to make ordering decision.

        Args:
            demand: This period's incoming demand
            forecast: Upcoming demand forecast (OEM only)
            period_metadata: Date/month/year info
            client: FoundryClient instance
            model_tier: Which model to use
            max_order_multiplier: Clamp ceiling as multiple of demand
        """
        self.state.incoming_demand_this_period = demand
        self.state.current_period = (
            period_metadata.get("period_number", 0) if period_metadata else 0
        )

        prompt = self.build_prompt(demand, forecast, period_metadata)
        response = client.call(model_tier, prompt, system_prompt=self.SYSTEM_PROMPT)

        # Parse response
        order_qty = int(response.get("order_quantity", demand))
        reasoning = response.get("reasoning", "No reasoning provided")
        pattern_analysis = response.get("pattern_analysis", None)

        # Clamp to bounds: floor = 0.2x demand, ceiling = 5x demand.
        # Floor prevents zero-order "inventory illusion" behaviour.
        # When demand is 0, both floor and ceiling are 0.
        was_clamped = False
        min_order = int(demand * 0.2) if demand > 0 else 0
        max_order = int(demand * max_order_multiplier) if demand > 0 else 0
        if order_qty < 0:
            logger.warning(
                f"[{self.state.role}] P{self.state.current_period}: "
                f"negative ({order_qty}) -> {min_order}"
            )
            order_qty = min_order
            was_clamped = True
        elif demand > 0 and order_qty < min_order:
            logger.warning(
                f"[{self.state.role}] P{self.state.current_period}: "
                f"below floor ({order_qty}) -> {min_order}"
            )
            order_qty = min_order
            was_clamped = True
        elif order_qty > max_order:
            logger.warning(
                f"[{self.state.role}] P{self.state.current_period}: "
                f"excessive ({order_qty}) -> {max_order}"
            )
            order_qty = max_order
            was_clamped = True

        decision = OrderDecision(
            period=self.state.current_period,
            role=self.state.role,
            order_quantity=order_qty,
            reasoning=reasoning,
            pattern_analysis=pattern_analysis,
            raw_response=response,
            was_clamped=was_clamped,
        )
        self.decisions.append(decision)
        self.state.order_history.append({
            "period": self.state.current_period,
            "quantity_ordered": order_qty,
        })
        return decision

    # ----- Prompt formatting helpers -----

    def _format_in_transit(self) -> str:
        tu = self.state.time_unit
        if not self.state.orders_in_transit:
            return "  None"
        return "\n".join(
            f"  - {o['quantity']:,} units arriving {tu} {o['arriving_period']}"
            for o in self.state.orders_in_transit
        )

    def _format_forecast(self, forecast: list, num_periods: int = 3) -> str:
        tu = self.state.time_unit.title()
        if not forecast:
            return "  Not available (you only see orders from your downstream partner)"
        display = forecast[:num_periods]
        lines = [f"  {tu:>6} | Forecast", "  ------|--------"]
        for entry in display:
            lines.append(f"  {entry['period_number']:>5} | {entry['demand']:>10,}")
        if len(forecast) > num_periods:
            lines.append(f"  ... ({len(forecast) - num_periods} more {self.state.time_unit}s)")
        return "\n".join(lines)

    def _format_order_history(self) -> str:
        tu = self.state.time_unit.title()
        recent = self.state.order_history[-6:]
        if not recent:
            return "  No orders placed yet"
        return "\n".join(
            f"  - {tu} {o['period']}: ordered {o['quantity_ordered']:,} units"
            for o in recent
        )

    def get_decision_history(self) -> list:
        return [{
            "period": d.period,
            "role": d.role,
            "order_quantity": d.order_quantity,
            "reasoning": d.reasoning,
            "pattern_analysis": d.pattern_analysis,
            "was_clamped": d.was_clamped,
        } for d in self.decisions]
