"""
V3 Supply Chain Simulation — SimPy discrete-event engine.

Architecture
------------
SupplyChainSim
  └── simpy.Environment
  └── WorldEvents                    -- disruption schedule
  └── TierProcess x3                 -- OEM, Ancillary, Component
        └── _deliver() subprocess    -- stochastic lead time + fill rate

Each TierProcess runs as a SimPy generator, advancing one period per
env.timeout(1). Replenishment is a separate subprocess per order —
env.process(self._deliver(qty, lead_time)) — which credits inventory
after a stochastic delay. This is the key structural advantage over V2's
period-loop: variable lead times are natural, not special-cased.

Stochastic parameters (drawn fresh each run via rng):
  - Demand noise   : multiplicative Gaussian, CV=8%
  - Lead time      : LogNormal(mu=0, sigma=0.25), then × world_event multiplier
  - Fill rate      : Beta(9, 1), then capped at world_event fill_rate_cap

Output schema matches V2 exactly (same column names) so metrics.py works
without modification. Three new columns are added for V3 analysis:
  - world_event      : event phase label (or None)
  - lead_time_actual : periods the replenishment took (float)
  - fill_rate_actual : fraction of order actually delivered

Parity check:
  Run with noise_cv=0, fixed lead time=1, fill cap=1, no world events
  and WorldEvents(enabled_events=set()) → results must match V2 heuristics.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import numpy as np
import pandas as pd
import simpy

from agent_interface import build_user_prompt, get_order_decision, get_system_prompt
from world_events import WorldEvents

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

# Per-tier production capacity (units/period).
# Not binding in normal operations; binding during demand surges.
CAPACITY = {
    "OEM":       60_000,
    "Ancillary": 65_000,
    "Component": 70_000,
}


# ---------------------------------------------------------------------------
# Heuristic policies — unchanged from V2
# ---------------------------------------------------------------------------

def policy_naive_passthrough(demand: int, **_) -> int:
    return demand


def policy_order_up_to(
    forecast: float,
    demand: int,
    inventory_position: int,
    safety_stock: int,
    alpha: float = 0.30,
) -> tuple[int, float]:
    new_forecast = alpha * demand + (1 - alpha) * forecast
    target_position = round(new_forecast) + safety_stock
    order = max(0, target_position - inventory_position)
    return order, new_forecast


def policy_exp_smoothing(
    forecast: float, demand: int, backlog: int, alpha: float = 0.30
) -> tuple[int, float]:
    new_forecast = alpha * demand + (1 - alpha) * forecast
    order = max(0, round(new_forecast) + backlog)
    return order, new_forecast


# ---------------------------------------------------------------------------
# Fulfilment rule — identical to V2
# ---------------------------------------------------------------------------

def apply_fulfilment(on_hand: int, demand: int, backlog_prev: int) -> dict:
    total_obligation = demand + backlog_prev
    fulfilled = min(on_hand, total_obligation)
    shortfall = max(0, total_obligation - on_hand)
    on_hand_after = on_hand - fulfilled
    return {
        "fulfilled":      fulfilled,
        "shortfall":      shortfall,
        "on_hand_after":  on_hand_after,
        "backlog":        shortfall,
        "stockout":       shortfall > 0,
    }


# ---------------------------------------------------------------------------
# TierProcess
# ---------------------------------------------------------------------------

class TierProcess:
    """
    SimPy process representing one supply chain tier.

    Each period (env.timeout(1)):
      1. Receive any replenishments due this period (from pipeline)
      2. Fulfil downstream demand + backlog
      3. Decide order quantity (LLM or heuristic)
      4. Spawn _deliver() subprocess for the order

    _deliver() draws a stochastic lead time and fill rate, waits,
    then credits on_hand. This is where V3 differs structurally from V2.
    """

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        condition: str,
        model_tier: str,
        policy: str,
        safety_stock: int,
        initial_inventory: int,
        world_events: WorldEvents,
        rng: np.random.Generator,
        demand_channel: Optional[simpy.Store],   # receives demand from downstream
        order_channel: Optional[simpy.Store],     # sends orders to downstream tier's demand_channel
        demand_series: pd.DataFrame,             # only used by OEM (retail demand)
        llm_temperature: float,
        condition_label: str,
        model_name: Optional[str],
        run_id: str,
        noise_cv: float = 0.08,
    ):
        self.env = env
        self.name = name
        self.condition = condition
        self.model_tier = model_tier
        self.policy = policy
        self.safety_stock = safety_stock
        self.world_events = world_events
        self.rng = rng
        self.demand_channel = demand_channel     # simpy.Store — OEM has None (reads CSV)
        self.order_channel = order_channel       # simpy.Store — Component has None
        self.demand_series = demand_series
        self.llm_temperature = llm_temperature
        self.condition_label = condition_label
        self.model_name = model_name
        self.run_id = run_id
        self.noise_cv = noise_cv

        # Inventory state
        self.on_hand = initial_inventory
        self.backlog = 0
        self.exp_forecast: float = float(demand_series.iloc[0]["retail_demand"])

        # Records collected by this tier
        self.records: list[dict] = []

        # Start the process
        self.action = env.process(self._run())

    def _run(self):
        """Main period loop."""
        n_periods = len(self.demand_series)

        for idx in range(n_periods):
            row = self.demand_series.iloc[idx]
            period = int(row["period"])
            calendar_month = str(row["calendar_month"])

            # ----------------------------------------------------------------
            # 1. Get demand for this period
            # ----------------------------------------------------------------
            if self.name == "OEM":
                # OEM reads retail demand from CSV + applies noise + world event shock
                baseline = float(row["retail_demand"])
                noise = self.rng.normal(loc=1.0, scale=self.noise_cv)
                shock = self.world_events.demand_multiplier(period)
                demand = max(0, round(baseline * noise * shock))
            else:
                # Other tiers wait for the upstream tier's order to arrive
                demand = yield self.demand_channel.get()

            # ----------------------------------------------------------------
            # 2. Fulfil demand
            # ----------------------------------------------------------------
            result = apply_fulfilment(self.on_hand, demand, self.backlog)
            self.on_hand = result["on_hand_after"]
            self.backlog = result["backlog"]

            # ----------------------------------------------------------------
            # 3. Order decision (final period = fulfilment only)
            # ----------------------------------------------------------------
            is_final_period = (idx == n_periods - 1)
            order = 0

            if not is_final_period:
                inv_position = self.on_hand - self.backlog

                if self.policy == "llm":
                    event_signal = (
                        self.world_events.event_signal(period)
                        if self.condition == "unstructured"
                        else None
                    )
                    system_prompt = get_system_prompt(self.name, self.condition)
                    user_prompt = build_user_prompt(
                        tier=self.name,
                        condition=self.condition,
                        period=period,
                        calendar_month=calendar_month,
                        demand_received=demand,
                        on_hand=self.on_hand,
                        backlog=self.backlog,
                        inventory_position=inv_position,
                        event_signal=event_signal,
                    )
                    result_llm = get_order_decision(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_tier=self.model_tier,
                        run_id=self.run_id,
                        period=period,
                        tier=self.name,
                        model_name=self.model_name,
                        temperature=self.llm_temperature,
                    )
                    order = int(result_llm["order_quantity"])
                    rationale = result_llm.get("rationale", "")

                elif self.policy == "naive":
                    order = policy_naive_passthrough(demand)
                    rationale = ""

                elif self.policy == "exp_smoothing":
                    order, self.exp_forecast = policy_exp_smoothing(
                        self.exp_forecast, demand, self.backlog
                    )
                    rationale = ""

                elif self.policy == "order_up_to":
                    order, self.exp_forecast = policy_order_up_to(
                        self.exp_forecast, demand, inv_position, self.safety_stock
                    )
                    rationale = ""

                # Enforce capacity constraint
                order = min(order, CAPACITY[self.name])
            else:
                rationale = ""

            # ----------------------------------------------------------------
            # 4. Record
            # ----------------------------------------------------------------
            self.records.append({
                "run_id":            self.run_id,
                "condition_label":   self.condition_label,
                "tier":              self.name,
                "period":            period,
                "calendar_month":    calendar_month,
                "policy":            self.policy,
                "demand_received":   demand,
                "on_hand_before_order": self.on_hand,
                "backlog":           result["backlog"],
                "order_placed":      order,
                "fulfilled":         result["fulfilled"],
                "shortfall":         result["shortfall"],
                "stockout":          result["stockout"],
                "rationale":         rationale if self.policy == "llm" else "",
                "world_event":       self.world_events.event_label(period),
            })

            # ----------------------------------------------------------------
            # 5. Dispatch order → spawn _deliver() subprocess
            # ----------------------------------------------------------------
            if order > 0 and not is_final_period:
                self.env.process(self._deliver(order, period))

            # ----------------------------------------------------------------
            # 6. Send order downstream as next tier's demand (if not Component)
            # ----------------------------------------------------------------
            if self.order_channel is not None and not is_final_period:
                yield self.order_channel.put(order)

            # Advance one period
            yield self.env.timeout(1)

    def _deliver(self, quantity: int, ordered_period: int):
        """
        Replenishment subprocess.

        Draws a stochastic lead time and fill rate, waits the lead time,
        then credits on_hand with the actual delivered quantity.

        Lead time: LogNormal(mu=0, sigma=0.25), mean ≈ 1.03 periods.
                   Multiplied by world event lead_time_multiplier.
                   Rounded to nearest integer, minimum 1.
        Fill rate: Beta(9, 1), mean=0.90, capped at world event fill_rate_cap.
        """
        # Draw lead time
        base_lt = self.rng.lognormal(mean=0.0, sigma=0.25)
        lt_mult = self.world_events.lead_time_multiplier(ordered_period)
        lead_time = max(1, round(base_lt * lt_mult))

        # Draw fill rate
        base_fill = self.rng.beta(a=9, b=1)
        fill_cap = self.world_events.fill_rate_cap(ordered_period)
        fill_rate = min(base_fill, fill_cap)
        actual_qty = max(0, round(quantity * fill_rate))

        # Wait lead time periods then credit inventory
        yield self.env.timeout(lead_time)
        self.on_hand += actual_qty

        logger.debug(
            "run=%s tier=%s period=%d ordered=%d lead_time=%d fill=%.2f delivered=%d",
            self.run_id, self.name, ordered_period, quantity, lead_time, fill_rate, actual_qty,
        )


# ---------------------------------------------------------------------------
# SupplyChainSim — top-level runner
# ---------------------------------------------------------------------------

class SupplyChainSim:
    """
    Top-level SimPy supply chain simulation.

    Owns the environment, world events, and all three tier processes.
    Channels (simpy.Store) pass orders between tiers within each period.

    Call run() to execute one complete simulation and return records.
    """

    def __init__(
        self,
        demand_series: pd.DataFrame,
        condition: str,
        model_tier: str,
        policy: str,
        S: int,
        safety_stock: int,
        world_events: WorldEvents,
        llm_temperature: float,
        condition_label: str,
        model_name: Optional[str] = None,
        run_id: Optional[str] = None,
        noise_cv: float = 0.08,
        rng_seed: Optional[int] = None,
    ):
        self.demand_series = demand_series
        self.condition = condition
        self.model_tier = model_tier
        self.policy = policy
        self.S = S
        self.safety_stock = safety_stock
        self.world_events = world_events
        self.llm_temperature = llm_temperature
        self.condition_label = condition_label
        self.model_name = model_name
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.noise_cv = noise_cv
        self.rng = np.random.default_rng(rng_seed)

    def run(self) -> list[dict]:
        """
        Execute one complete 36-period simulation.
        Returns list of records — one per (period, tier).
        """
        env = simpy.Environment()

        # Channels: OEM orders → Ancillary demand, Ancillary orders → Component demand
        # Capacity=1 per period enforces the serial cascade (no buffering between tiers).
        oem_to_anc = simpy.Store(env, capacity=1)
        anc_to_comp = simpy.Store(env, capacity=1)

        # Common kwargs
        base_kwargs = dict(
            env=env,
            condition=self.condition,
            model_tier=self.model_tier,
            policy=self.policy,
            safety_stock=self.safety_stock,
            initial_inventory=self.S,
            world_events=self.world_events,
            rng=self.rng,
            demand_series=self.demand_series,
            llm_temperature=self.llm_temperature,
            condition_label=self.condition_label,
            model_name=self.model_name,
            run_id=self.run_id,
            noise_cv=self.noise_cv,
        )

        oem = TierProcess(
            name="OEM",
            demand_channel=None,         # reads retail demand directly from CSV
            order_channel=oem_to_anc,    # sends orders to Ancillary
            **base_kwargs,
        )
        anc = TierProcess(
            name="Ancillary",
            demand_channel=oem_to_anc,   # receives OEM orders as its demand
            order_channel=anc_to_comp,   # sends orders to Component
            **base_kwargs,
        )
        comp = TierProcess(
            name="Component",
            demand_channel=anc_to_comp,  # receives Ancillary orders as its demand
            order_channel=None,          # no upstream to notify
            **base_kwargs,
        )

        env.run()

        # Collect and sort records from all three tiers
        all_records = oem.records + anc.records + comp.records
        all_records.sort(key=lambda r: (r["period"], TIERS.index(r["tier"])))
        return all_records


# ---------------------------------------------------------------------------
# Convenience wrapper — matches V2 run_simulation() signature for drop-in use
# ---------------------------------------------------------------------------

def run_simulation(
    demand_series: pd.DataFrame,
    condition: str,
    model_tier: str,
    policy: str,
    S: int,
    safety_stock: int,
    world_events: WorldEvents,
    llm_temperature: float,
    condition_label: str = "",
    model_name: Optional[str] = None,
    run_id: Optional[str] = None,
    noise_cv: float = 0.08,
    rng_seed: Optional[int] = None,
) -> list[dict]:
    sim = SupplyChainSim(
        demand_series=demand_series,
        condition=condition,
        model_tier=model_tier,
        policy=policy,
        S=S,
        safety_stock=safety_stock,
        world_events=world_events,
        llm_temperature=llm_temperature,
        condition_label=condition_label,
        model_name=model_name,
        run_id=run_id,
        noise_cv=noise_cv,
        rng_seed=rng_seed,
    )
    return sim.run()
