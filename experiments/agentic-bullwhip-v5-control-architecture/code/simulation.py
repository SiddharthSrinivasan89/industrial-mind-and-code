"""
V5 ControlArch Supply Chain Simulation — SimPy discrete-event engine.

Extends V4 WorldEvents with deterministic ablation policies:
  oracle_intent  — uses GROUND_TRUTH_INTENT labels (diagnostic upper bound)
  causal_intent  — uses rule-based calendar/event labels (fair non-LLM baseline)

New control levers (all default to V4 behavior when not set):
  multiplier_map       — override INTENT_MULTIPLIER_MAP with a different map
  dampening_beta       — smooth orders: order_t = last + beta*(raw - last); 1.0 = no dampening
  neutral_mode         — change what NEUTRAL mechanically does
  use_forecast_oracle  — multiply F_t by world_events.demand_multiplier before computing target

Policy summary
--------------
  naive          — demand pass-through (heuristic baseline)
  exp_smoothing  — exponential smoothing (heuristic baseline)
  order_up_to    — OUT-style with fixed safety stock (heuristic baseline)
  intent         — LLM classifies intent → lookup → multiplier → OUT formula [V4]
  oracle_intent  — ground-truth labels → lookup → multiplier → OUT formula [V5 ablation]
  causal_intent  — rule-based labels  → lookup → multiplier → OUT formula [V5 ablation]

Architecture
------------
SupplyChainSim
  └── simpy.Environment
  └── WorldEvents                    — disruption schedule (pandemic/conflict/port)
  └── TierProcess × 3               — OEM, Ancillary, Component
        └── _deliver() subprocess   — stochastic lead time + fill rate

Intent policy formula (all intent-class policies):
  F_t = alpha × D_t + (1-alpha) × F_{t-1}   [standard EMA; returned as-is for clean chain]
  F_t_adj = F_t × event_forecast_multiplier  [A5 only; used for order target, not stored]
  SS_t = base_ss × multiplier_map[intent_class]
  target = round(F_t_adj) + SS_t
  raw_order = max(0, target - inventory_position)
  order_t = round(last_order + dampening_beta × (raw_order - last_order))  [A4 dampening]
  order_t = min(order_t, CAPACITY[tier])     [capacity cap]
  last_order = order_t                       [stored AFTER cap]
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

_INTENT_POLICIES = {"intent", "oracle_intent", "causal_intent"}


# ---------------------------------------------------------------------------
# Heuristic policies — unchanged from V4
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
# Intent hybrid policy — V4 + V5 extensions
# ---------------------------------------------------------------------------

def policy_intent_hybrid(
    intent_class: str,
    demand: int,
    forecast: float,
    inventory_position: int,
    safety_stock: int,
    alpha: float = 0.30,
    multiplier_map: dict | None = None,
    neutral_mode: str = "out",
    last_order: int = 0,
    event_forecast_multiplier: float = 1.0,
) -> tuple[int, float, float]:
    """
    OUT-style ordering formula driven by intent classification.

    The EMA forecast (new_forecast) is computed from the standard formula and
    returned unchanged — preserving the rolling chain for future periods.

    For A5 (use_forecast_oracle=True), event_forecast_multiplier > 1.0 adjusts
    the effective forecast used for the order target only. The unadjusted EMA
    is still returned and stored as self.exp_forecast.

    neutral_mode variants apply only when intent_class == "NEUTRAL":
      "out"               — standard OUT formula (V4 default)
      "repeat_last"       — order = last_order (true inaction)
      "smoothed_forecast" — order = max(0, round(F_t)), no safety stock
      "dampened_out"      — order = last_order + 0.375 * (OUT_raw - last_order)
      "floor_only"        — order = 0 if inv_pos >= safety_stock, else standard OUT

    Returns (order, new_forecast, multiplier_used).
    """
    active_map = multiplier_map if multiplier_map is not None else INTENT_MULTIPLIER_MAP
    multiplier = active_map.get(intent_class, 1.00)

    new_forecast = alpha * demand + (1 - alpha) * forecast
    adjusted_forecast = new_forecast * event_forecast_multiplier  # A5: local adjustment only

    # NEUTRAL mode dispatch
    if intent_class == "NEUTRAL" and neutral_mode != "out":
        if neutral_mode == "repeat_last":
            return last_order, new_forecast, multiplier
        elif neutral_mode == "smoothed_forecast":
            return max(0, round(new_forecast)), new_forecast, multiplier
        elif neutral_mode == "dampened_out":
            ss_adj = round(safety_stock * multiplier)
            out_raw = max(0, round(adjusted_forecast) + ss_adj - inventory_position)
            order = max(0, round(last_order + 0.375 * (out_raw - last_order)))
            return order, new_forecast, multiplier
        elif neutral_mode == "floor_only":
            if inventory_position >= safety_stock:
                return 0, new_forecast, multiplier
            # fall through to standard OUT

    # Standard OUT path
    ss_adjusted = round(safety_stock * multiplier)
    target = round(adjusted_forecast) + ss_adjusted
    order = max(0, target - inventory_position)
    return order, new_forecast, multiplier


# ---------------------------------------------------------------------------
# Fulfilment rule — identical to V4
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
        # V5 extensions
        multiplier_map: dict | None = None,
        dampening_beta: float = 1.0,
        neutral_mode: str = "out",
        use_forecast_oracle: bool = False,
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
        self.multiplier_map      = multiplier_map
        self.dampening_beta      = dampening_beta
        self.neutral_mode        = neutral_mode
        self.use_forecast_oracle = use_forecast_oracle

        self.on_hand   = initial_inventory
        self.backlog   = 0
        self.on_order  = 0
        self.last_order: int = 0  # V5: state for dampening and repeat_last
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
                    # V4 LLM path — unchanged
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
                        multiplier_map     = self.multiplier_map,
                        neutral_mode       = self.neutral_mode,
                        last_order         = self.last_order,
                    )

                elif self.policy == "oracle_intent":
                    # V5 A1/A2/A3/A4/A5 — oracle labels, no LLM call
                    from oracle_policies import get_oracle_intent
                    intent_class = get_oracle_intent(period)
                    intent_fallback = False
                    event_mult = (
                        self.world_events.demand_multiplier(period)
                        if self.use_forecast_oracle else 1.0
                    )
                    order, self.exp_forecast, intent_mult = policy_intent_hybrid(
                        intent_class             = intent_class,
                        demand                   = demand,
                        forecast                 = self.exp_forecast,
                        inventory_position       = inv_position,
                        safety_stock             = self.safety_stock,
                        multiplier_map           = self.multiplier_map,
                        neutral_mode             = self.neutral_mode,
                        last_order               = self.last_order,
                        event_forecast_multiplier= event_mult,
                    )

                elif self.policy == "causal_intent":
                    # V5 A6 — rule-based labels from calendar/event signal, no LLM call
                    from oracle_policies import get_causal_intent
                    event_sig = (
                        self.world_events.event_signal(period)
                        if self.condition == "unstructured" else None
                    )
                    intent_class = get_causal_intent(calendar_month, event_sig)
                    intent_fallback = False
                    order, self.exp_forecast, intent_mult = policy_intent_hybrid(
                        intent_class       = intent_class,
                        demand             = demand,
                        forecast           = self.exp_forecast,
                        inventory_position = inv_position,
                        safety_stock       = self.safety_stock,
                        multiplier_map     = self.multiplier_map,
                        neutral_mode       = self.neutral_mode,
                        last_order         = self.last_order,
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

                # V5 A4: global dampening — applied to all intent-class policies
                if self.policy in _INTENT_POLICIES and self.dampening_beta < 1.0:
                    order = max(0, round(self.last_order + self.dampening_beta * (order - self.last_order)))

                # Capacity cap BEFORE storing last_order
                order = min(order, CAPACITY[self.name])
                if self.policy in _INTENT_POLICIES:
                    self.last_order = order

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
                # V5 provenance fields
                "dampening_beta":       self.dampening_beta if self.policy in _INTENT_POLICIES else None,
                "neutral_mode":         self.neutral_mode if self.policy in _INTENT_POLICIES else None,
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
        Stochastic replenishment subprocess — identical to V4.

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
        self.on_order -= quantity
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
        # V5 extensions
        multiplier_map: dict | None = None,
        dampening_beta: float = 1.0,
        neutral_mode: str = "out",
        use_forecast_oracle: bool = False,
    ):
        self.demand_series       = demand_series
        self.condition           = condition
        self.model_tier          = model_tier
        self.policy              = policy
        self.S                   = S
        self.safety_stock        = safety_stock
        self.world_events        = world_events
        self.llm_temperature     = llm_temperature
        self.condition_label     = condition_label
        self.model_name          = model_name
        self.run_id              = run_id or str(uuid.uuid4())[:8]
        self.noise_cv            = noise_cv
        self.rng                 = np.random.default_rng(rng_seed)
        self.multiplier_map      = multiplier_map
        self.dampening_beta      = dampening_beta
        self.neutral_mode        = neutral_mode
        self.use_forecast_oracle = use_forecast_oracle

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
            multiplier_map=self.multiplier_map,
            dampening_beta=self.dampening_beta,
            neutral_mode=self.neutral_mode,
            use_forecast_oracle=self.use_forecast_oracle,
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
    # V5 extensions
    multiplier_map: dict | None = None,
    dampening_beta: float = 1.0,
    neutral_mode: str = "out",
    use_forecast_oracle: bool = False,
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
        multiplier_map=multiplier_map,
        dampening_beta=dampening_beta,
        neutral_mode=neutral_mode,
        use_forecast_oracle=use_forecast_oracle,
    )
    return sim.run()
