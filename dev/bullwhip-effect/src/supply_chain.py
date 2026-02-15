"""
Supply Chain Orchestrator
==========================
Runs the 3-tier cascade period by period.
OEM (Tatva) -> Lighting Manufacturer -> LED/Component Supplier
"""

import calendar
import csv
import logging

from blind_agent import BlindAgent
from context_agent import ContextAgent
from inventory_manager import InventoryManager

logger = logging.getLogger(__name__)


class SupplyChain:
    """Orchestrates a 3-tier supply chain simulation."""

    def __init__(self, agent_category: str, initial_inventory: int = 23000,
                 lead_time_periods: int = 1, time_unit: str = "month",
                 holding_cost: int = 0, backlog_cost: int = 0):
        """
        Args:
            agent_category: 'blind' or 'context'
            initial_inventory: Starting stock per tier (~2 weeks of dispatches)
            lead_time_periods: Delivery lead time in periods
            time_unit: 'month' or 'week'
            holding_cost: ₹ per unit per period (v4: 0, no cost model)
            backlog_cost: ₹ per unit per period (v4: 0, no cost model)
        """
        self.agent_category = agent_category
        self.initial_inventory = initial_inventory
        self.lead_time_periods = lead_time_periods
        self.time_unit = time_unit

        AgentClass = BlindAgent if agent_category == "blind" else ContextAgent

        self.oem = AgentClass("oem", initial_inventory, lead_time_periods, time_unit, holding_cost, backlog_cost)
        self.ancillary = AgentClass("ancillary", initial_inventory, lead_time_periods, time_unit, holding_cost, backlog_cost)
        self.ancillary_supplier = AgentClass("ancillary_supplier", initial_inventory, lead_time_periods, time_unit, holding_cost, backlog_cost)

        self.inv_oem = InventoryManager("oem", initial_inventory, lead_time_periods)
        self.inv_ancillary = InventoryManager("ancillary", initial_inventory, lead_time_periods)
        self.inv_ancillary_supplier = InventoryManager("ancillary_supplier", initial_inventory, lead_time_periods)

        self.consumer_demands: list = []

    @staticmethod
    def load_demand_data(csv_path: str) -> list:
        """Load demand CSV. Auto-detects weekly or monthly format."""
        data = []
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # Detect period column
            if "period_number" in headers:
                period_col = "period_number"
            elif "week_number" in headers:
                period_col = "week_number"
            else:
                raise ValueError(f"CSV must have 'period_number' or 'week_number'. Found: {headers}")

            # Detect demand column
            demand_col = None
            for candidate in ["dispatches", "sales_units", "demand_units"]:
                if candidate in headers:
                    demand_col = candidate
                    break
            if demand_col is None:
                raise ValueError(f"CSV must have 'dispatches', 'sales_units', or 'demand_units'. Found: {headers}")

            for row in reader:
                entry = {
                    "period_number": int(row[period_col]),
                    "date": row["date"],
                    "year": int(row["year"]),
                    "month": int(row["month"]),
                    "demand": int(row[demand_col]),
                }
                # Optional fields
                if "month_name" in headers:
                    entry["month_name"] = row["month_name"]
                if "week_of_year" in headers:
                    entry["week_of_year"] = int(row["week_of_year"])
                data.append(entry)
        return data

    def run(self, demand_data: list, client, model_tier: str,
            ordering_periods: int = 13, start_period: int = 0,
            forecast_horizon: int = 3) -> dict:
        """
        Execute full simulation.

        Args:
            demand_data: List of demand dicts (monthly or weekly)
            client: FoundryClient instance
            model_tier: 'lightweight', 'reasoning', or 'open_source'
            ordering_periods: Periods to simulate
            start_period: Starting index
            forecast_horizon: Periods of forecast visible to OEM
        """
        tu = self.time_unit
        logger.info(
            f"Starting {self.agent_category} chain: "
            f"{ordering_periods} {tu}s, model={model_tier}"
        )
        end_period = min(start_period + ordering_periods, len(demand_data))

        for idx in range(start_period, end_period):
            wd = demand_data[idx]
            period_num = wd["period_number"]
            consumer = wd["demand"]
            self.consumer_demands.append(consumer)

            month_name = wd.get("month_name") or calendar.month_name[wd["month"]]
            meta = {
                "period_number": wd["period_number"],
                "date": wd["date"],
                "year": wd["year"],
                "month": wd["month"],
                "month_name": month_name,
            }

            # Forecast for OEM (upcoming periods from demand data)
            forecast = []
            for i in range(idx + 1, min(idx + 1 + forecast_horizon, len(demand_data))):
                forecast.append({
                    "period_number": demand_data[i]["period_number"],
                    "demand": demand_data[i]["demand"],
                })

            logger.info(f"--- {tu.title()} {period_num} ({month_name} {wd['year']}) | Demand: {consumer:,} ---")

            # TIER 1: OEM sees dispatch demand
            self._sync(self.oem, self.inv_oem)
            oem_dec = self.oem.decide_order(
                consumer, forecast, meta, client, model_tier
            )
            self.inv_oem.process_period(
                period_num, consumer, oem_dec.order_quantity, oem_dec.was_clamped
            )
            logger.info(f"  OEM:            dem={consumer:,}  ord={oem_dec.order_quantity:,}")

            # TIER 2: Lighting Mfr sees OEM's ORDER
            self._sync(self.ancillary, self.inv_ancillary)
            anc_dec = self.ancillary.decide_order(
                oem_dec.order_quantity, [], meta, client, model_tier
            )
            self.inv_ancillary.process_period(
                period_num, oem_dec.order_quantity,
                anc_dec.order_quantity, anc_dec.was_clamped
            )
            logger.info(f"  Lighting Mfr:   dem={oem_dec.order_quantity:,}  ord={anc_dec.order_quantity:,}")

            # TIER 3: LED Supplier sees Lighting Mfr's ORDER
            self._sync(self.ancillary_supplier, self.inv_ancillary_supplier)
            sup_dec = self.ancillary_supplier.decide_order(
                anc_dec.order_quantity, [], meta, client, model_tier
            )
            self.inv_ancillary_supplier.process_period(
                period_num, anc_dec.order_quantity,
                sup_dec.order_quantity, sup_dec.was_clamped
            )
            logger.info(f"  LED Supplier:   dem={anc_dec.order_quantity:,}  ord={sup_dec.order_quantity:,}")

        return self._compile(model_tier)

    def _sync(self, agent, inv):
        """Sync agent state from inventory manager."""
        snap = inv.get_state_snapshot()
        agent.state.inventory_on_hand = snap["inventory_on_hand"]
        agent.state.backlog = snap["backlog"]
        agent.state.orders_in_transit = snap["orders_in_transit"]

    def _compile(self, model_tier: str) -> dict:
        result = {
            "metadata": {
                "agent_category": self.agent_category,
                "model_tier": model_tier,
                "initial_inventory": self.initial_inventory,
                "lead_time_periods": self.lead_time_periods,
                "periods_simulated": len(self.consumer_demands),
                "time_unit": self.time_unit,
            },
            "consumer_demand": self.consumer_demands,
            "tiers": {},
        }
        for name, inv, agent in [
            ("oem", self.inv_oem, self.oem),
            ("ancillary", self.inv_ancillary, self.ancillary),
            ("ancillary_supplier", self.inv_ancillary_supplier, self.ancillary_supplier),
        ]:
            result["tiers"][name] = {
                "period_records": inv.export_records(),
                "decisions": agent.get_decision_history(),
                "orders_placed": inv.get_orders_placed(),
                "incoming_demands": inv.get_incoming_demands(),
                "inventory_levels": inv.get_inventory_levels(),
                "stockout_periods": inv.get_stockout_periods(),
            }
        return result
