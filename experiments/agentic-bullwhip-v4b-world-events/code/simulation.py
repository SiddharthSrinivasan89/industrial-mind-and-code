"""
V4 WorldEvents Supply Chain Simulation — SimPy discrete-event engine.

Combines V3's 36-month world-events SimPy engine with V4's intent classification
output interface.

Policy summary
--------------
  naive           — demand pass-through (heuristic baseline)
  exp_smoothing   — exponential smoothing (heuristic baseline)
  order_up_to     — OUT-style with fixed safety stock (heuristic baseline)
  intent          — LLM classifies intent → lookup → multiplier → OUT formula [NEW]

The intent policy is the primary experimental treatment. Heuristics run as
Monte Carlo baselines (100 runs each, demand noise means each run differs).

Architecture
------------
SupplyChainSim
  └── simpy.Environment
  └── WorldEvents                    — disruption schedule (pandemic/conflict/port)
  └── TierProcess × 3               — OEM, Ancillary, Component
        └── _deliver() subprocess   — stochastic lead time + fill rate

Stochastic parameters:
  Demand noise   : multiplicative Gaussian, CV=8% (applied at OEM from retail series)
  Lead time      : LogNormal(mu=0, sigma=0.25), then × world_event multiplier
  Fill rate      : Beta(9, 1), capped at world_event fill_rate_cap

Intent policy formula (per period):
  F_t = alpha × D_t + (1-alpha) × F_{t-1}   [exponential forecast, alpha=0.30]
  SS_t = base_ss × INTENT_MULTIPLIER_MAP[intent_class]
  target = round(F_t) + SS_t
  order_t = max(0, target - inventory_position_t)

Output schema: compatible with V3 records, with three additional fields:
  intent_class      — chosen intent label (or None for heuristic runs)
  intent_multiplier — resolved multiplier (or None for heuristic runs)
  intent_fallback   — True if NEUTRAL was forced after parse failure (bool/None)
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import numpy as np
import pandas as pd
import simpy

from agent_interface import (
    INTENT_MULTIPLIER_MAP,
    get_intent_class,
)
from world_events import WorldEvents

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

CAPACITY = {
    "OEM":       60_000,
    "Ancillary": 65_000,
    "Component": 70_000,
}


# ---------------------------------------------------------------------------
# Heuristic policies — unchanged from V3
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
# Intent hybrid policy — V4 addition
# ---------------------------------------------------------------------------

def policy_intent_hybrid(
    intent_class: str,
    demand: int,
    forecast: float,
    inventory_position: int,
    safety_stock: int,
    alpha: float = 0.30,
) -> tuple[int, float, float]:
    """
    OUT-style ordering formula driven by intent classification.

    F_t = alpha * D_t + (1-alpha) * F_{t-1}
    SS_t = safety_stock (base) * INTENT_MULTIPLIER_MAP[intent_class]
    order = max(0, round(F_t) + SS_t - inventory_position)

    Returns (order, new_forecast, multiplier_used).
    """
    multiplier = INTENT_MULTIPLIER_MAP.get(intent_class, 1.00)
    new_forecast = alpha * demand + (1 - alpha) * forecast
    ss_adjusted = round(safety_stock * multiplier)
    target = round(new_forecast) + ss_adjusted
    order = max(0, target - inventory_position)
    return order, new_forecast, multiplier


# ---------------------------------------------------------------------------
# Fulfilment rule — identical to V3
# ---------------------------------------------------------------------------

def apply_fulfilment(on_hand: int, demand: int, backlog_prev: int) -> dict:
    total_obligation = demand + backlog_prev
    fulfilled = min(on_hand, total_obligation)
    shortfall = max(0, total_obligation - on_hand)
    on_hand_after = on_hand - fulfilled
    return {
        "fulfilled":     fulfilled,
        "shortfall":     shortfall,
        "on_hand_after": on_hand_after,
        "backlog":       shortfall,
        "stockout":      shortfall > 0,
    }


# ---------------------------------------------------------------------------
# TierProcess
# ---------------------------------------------------------------------------

class TierProcess:
    """
    SimPy process for one supply chain tier.

    Per period:
      1. Receive any replenishments due this period (from _deliver subprocesses)
      2. Fulfil downstream demand + backlog
      3. Decide order: heuristic or intent classification
      4. Spawn _deliver() subprocess for stochastic lead time + fill rate
      5. Send order downstream as next tier's demand
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
        demand_channel: Optional[simpy.Store],
        order_channel: Optional[simpy.Store],
        demand_series: pd.DataFrame,
        llm_temperature: float,
        condition_label: str,
        model_name: Optional[str],
        run_id: str,
        noise_cv: float = 0.08,
    ):
        self.env             = env
        self.name            = name
        self.condition       = condition
        self.model_tier      = model_tier
        self.policy          = policy
        self.safety_stock    = safety_stock
        self.world_events    = world_events
        self.rng             = rng
        self.demand_channel  = demand_channel
        self.order_channel   = order_channel
        self.demand_series   = demand_series
        self.llm_temperature = llm_temperature
        self.condition_label = condition_label
        self.model_name      = model_name
        self.run_id          = run_id
        self.noise_cv        = noise_cv

        self.on_hand   = initial_inventory
        self.backlog   = 0
        self.on_order  = 0   # units dispatched to _deliver() but not yet arrived
        self.exp_forecast: float = float(demand_series.iloc[0]["retail_demand"])

        self.records: list[dict] = []
        self.action = env.process(self._run())

    def _run(self):
        n_periods = len(self.demand_series)

        for idx in range(n_periods):
            row            = self.demand_series.iloc[idx]
            period         = int(row["period"])
            calendar_month = str(row["calendar_month"])

            # ----------------------------------------------------------------
            # 1. Receive demand
            # ----------------------------------------------------------------
            if self.name == "OEM":
                baseline = float(row["retail_demand"])
                noise    = self.rng.normal(loc=1.0, scale=self.noise_cv)
                shock    = self.world_events.demand_multiplier(period)
                demand   = max(0, round(baseline * noise * shock))
            else:
                demand = yield self.demand_channel.get()

            # ----------------------------------------------------------------
            # 2. Fulfil demand
            # ----------------------------------------------------------------
            result     = apply_fulfilment(self.on_hand, demand, self.backlog)
            self.on_hand = result["on_hand_after"]
            self.backlog = result["backlog"]

            # ----------------------------------------------------------------
            # 3. Order decision (skip on final period)
            # ----------------------------------------------------------------
            is_final_period   = (idx == n_periods - 1)
            order             = 0
            rationale         = ""
            intent_class      = None
            intent_mult       = None
            intent_fallback   = None
            attempt_number    = None
            latency_ms        = None
            ttft_ms           = None
            prompt_tokens     = None
            completion_tokens = None
            generation_tps    = None

            if not is_final_period:
                inv_position = self.on_hand + self.on_order - self.backlog

                if self.policy == "intent":
                    event_signal = (
                        self.world_events.event_signal(period)
                        if self.condition == "unstructured"
                        else None
                    )
                    ic_result = get_intent_class(
                        tier               = self.name,
                        condition          = self.condition,
                        period             = period,
                        calendar_month     = calendar_month,
                        demand_received    = demand,
                        on_hand            = self.on_hand,
                        backlog            = self.backlog,
                        inventory_position = inv_position,
                        base_ss            = self.safety_stock,
                        event_signal       = event_signal,
                        model_tier         = self.model_tier,
                        run_id             = self.run_id,
                        model_name         = self.model_name,
                        temperature        = self.llm_temperature,
                    )
                    intent_class      = ic_result["intent_class"]
                    intent_fallback   = ic_result["intent_fallback"]
                    rationale         = ic_result.get("rationale", "")
                    attempt_number    = ic_result.get("attempt_number")
                    latency_ms        = ic_result.get("latency_ms")
                    ttft_ms           = ic_result.get("ttft_ms")
                    prompt_tokens     = ic_result.get("prompt_tokens")
                    completion_tokens = ic_result.get("completion_tokens")
                    generation_tps    = ic_result.get("generation_tps")

                    order, self.exp_forecast, intent_mult = policy_intent_hybrid(
                        intent_class       = intent_class,
                        demand             = demand,
                        forecast           = self.exp_forecast,
                        inventory_position = inv_position,
                        safety_stock       = self.safety_stock,
                    )

                elif self.policy == "naive":
                    order = policy_naive_passthrough(demand)

                elif self.policy == "exp_smoothing":
                    order, self.exp_forecast = policy_exp_smoothing(
                        self.exp_forecast, demand, self.backlog
                    )

                elif self.policy == "order_up_to":
                    order, self.exp_forecast = policy_order_up_to(
                        self.exp_forecast, demand, inv_position, self.safety_stock
                    )

                order = min(order, CAPACITY[self.name])

            # ----------------------------------------------------------------
            # 4. Record
            # ----------------------------------------------------------------
            self.records.append({
                "run_id":               self.run_id,
                "condition_label":      self.condition_label,
                "tier":                 self.name,
                "period":               period,
                "calendar_month":       calendar_month,
                "policy":               self.policy,
                "demand_received":      demand,
                "on_hand_before_order": self.on_hand,
                "backlog":              result["backlog"],
                "order_placed":         order,
                "fulfilled":            result["fulfilled"],
                "shortfall":            result["shortfall"],
                "stockout":             result["stockout"],
                "rationale":            rationale,
                "world_event":          self.world_events.event_label(period),
                "intent_class":         intent_class,
                "intent_multiplier":    intent_mult,
                "intent_fallback":      intent_fallback,
                "attempt_number":       attempt_number,
                "latency_ms":           latency_ms,
                "ttft_ms":              ttft_ms,
                "prompt_tokens":        prompt_tokens,
                "completion_tokens":    completion_tokens,
                "generation_tps":       generation_tps,
            })

            # ----------------------------------------------------------------
            # 5. Dispatch order → spawn _deliver() subprocess
            # ----------------------------------------------------------------
            if order > 0 and not is_final_period:
                self.on_order += order
                self.env.process(self._deliver(order, period))

            if self.order_channel is not None and not is_final_period:
                yield self.order_channel.put(order)

            yield self.env.timeout(1)

    def _deliver(self, quantity: int, ordered_period: int):
        """
        Stochastic replenishment subprocess.

        Lead time : LogNormal(mu=0, sigma=0.25), multiplied by world event factor.
                    Minimum 1 period.
        Fill rate : Beta(9, 1), capped at world event fill_rate_cap.
        """
        base_lt  = self.rng.lognormal(mean=0.0, sigma=0.25)
        lt_mult  = self.world_events.lead_time_multiplier(ordered_period)
        lead_time = max(1, round(base_lt * lt_mult))

        base_fill = self.rng.beta(a=9, b=1)
        fill_cap  = self.world_events.fill_rate_cap(ordered_period)
        fill_rate = min(base_fill, fill_cap)
        actual_qty = max(0, round(quantity * fill_rate))

        yield self.env.timeout(lead_time)
        self.on_order -= quantity   # clear the manager-perceived in-transit qty at arrival
        self.on_hand  += actual_qty

        logger.debug(
            "run=%s tier=%s period=%d ordered=%d lt=%d fill=%.2f delivered=%d",
            self.run_id, self.name, ordered_period, quantity, lead_time, fill_rate, actual_qty,
        )


# ---------------------------------------------------------------------------
# SupplyChainSim — top-level runner
# ---------------------------------------------------------------------------

class SupplyChainSim:
    """Top-level SimPy supply chain simulation. Call run() for one complete 36-period sim."""

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
        self.demand_series   = demand_series
        self.condition       = condition
        self.model_tier      = model_tier
        self.policy          = policy
        self.S               = S
        self.safety_stock    = safety_stock
        self.world_events    = world_events
        self.llm_temperature = llm_temperature
        self.condition_label = condition_label
        self.model_name      = model_name
        self.run_id          = run_id or str(uuid.uuid4())[:8]
        self.noise_cv        = noise_cv
        self.rng             = np.random.default_rng(rng_seed)

    def run(self) -> list[dict]:
        env         = simpy.Environment()
        oem_to_anc  = simpy.Store(env, capacity=1)
        anc_to_comp = simpy.Store(env, capacity=1)

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

        oem  = TierProcess(name="OEM",       demand_channel=None,         order_channel=oem_to_anc,  **base_kwargs)
        anc  = TierProcess(name="Ancillary", demand_channel=oem_to_anc,   order_channel=anc_to_comp, **base_kwargs)
        comp = TierProcess(name="Component", demand_channel=anc_to_comp,  order_channel=None,        **base_kwargs)

        env.run()

        all_records = oem.records + anc.records + comp.records
        all_records.sort(key=lambda r: (r["period"], TIERS.index(r["tier"])))
        return all_records


# ---------------------------------------------------------------------------
# Convenience wrapper
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
