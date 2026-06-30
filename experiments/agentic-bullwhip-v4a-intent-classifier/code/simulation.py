"""
Supply chain simulation — V4 Intent Classifier.

Identical to V3b except for the intent policy:
  policy == "intent"  — LLM classifies buffer intent (5 labels) → lookup → multiplier → OUT formula
  policy == "hybrid"  — V3b float multiplier (kept for comparison if needed)
  policy == "hybrid_control" / "exp_smoothing" / "order_up_to" / "naive" — deterministic baselines

Intent policy formula (per period, per tier):
  F_t = alpha × D_t + (1 - alpha) × F_{t-1}
  SS_t = base_ss × INTENT_MULTIPLIER_MAP[intent_class]
  order_t = max(0, round(F_t) + SS_t - inventory_position_t)

25-month demand series: periods 1-24 active ordering, period 25 fulfilment-only.
"""

import logging
import os
import uuid

import pandas as pd

from agent_interface import (
    INTENT_MULTIPLIER_MAP,
    get_intent_class,
)

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

MULTIPLIER_MIN      = 0.5
MULTIPLIER_MAX      = 3.0
MULTIPLIER_FALLBACK = 1.0

HISTORY_WINDOW = 3


# ---------------------------------------------------------------------------
# Heuristic policies
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
    forecast: float,
    demand: int,
    backlog: int,
    alpha: float = 0.30,
) -> tuple[int, float]:
    new_forecast = alpha * demand + (1 - alpha) * forecast
    order = max(0, round(new_forecast) + backlog)
    return order, new_forecast


def policy_smoothed_out_with_ss(
    forecast: float,
    demand: int,
    inventory_position: int,
    safety_stock: int,
    alpha: float = 0.30,
) -> tuple[int, float]:
    """OUT-style formula shared by hybrid and intent policies."""
    new_forecast = alpha * demand + (1 - alpha) * forecast
    target_position = round(new_forecast) + safety_stock
    order = max(0, target_position - inventory_position)
    return order, new_forecast


# ---------------------------------------------------------------------------
# Fulfilment
# ---------------------------------------------------------------------------

def apply_fulfilment(on_hand: int, demand: int, backlog_prev: int) -> dict:
    total_obligation = demand + backlog_prev
    fulfilled = min(on_hand, total_obligation)
    shortfall = max(0, total_obligation - on_hand)
    return {
        "fulfilled":     fulfilled,
        "shortfall":     shortfall,
        "on_hand_after": on_hand - fulfilled,
        "backlog":       shortfall,
        "stockout":      shortfall > 0,
    }


# ---------------------------------------------------------------------------
# Per-tier state
# ---------------------------------------------------------------------------

class TierState:
    def __init__(self, initial_inventory: int):
        self.on_hand = initial_inventory
        self.backlog = 0
        self.last_order = 0
        self.exp_forecast = None
        self.history: list[dict] = []        # hybrid stateful window
        self.intent_history: list[dict] = [] # intent stateful window


# ---------------------------------------------------------------------------
# Main simulation runner
# ---------------------------------------------------------------------------

def run_simulation(
    demand_series: pd.DataFrame,
    condition: str,
    model_tier: str,
    policy: str,
    S: int,
    safety_stock: int,
    initial_inventory: int,
    condition_label: str = "",
    model_name: str | None = None,
    run_id: str | None = None,
    backend: str | None = None,
) -> list[dict]:
    """
    Run one complete 25-period simulation and return all records.

    Parameters
    ----------
    demand_series     : DataFrame with [period, calendar_month, retail_demand], 25 rows.
    condition         : "blind" | "context" | "stateful" (for intent policy)
                        or "blind" | "context" for legacy heuristic/hybrid.
    model_tier        : "lightweight"
    policy            : "intent" | "hybrid" | "hybrid_control" | "naive" |
                        "order_up_to" | "exp_smoothing"
    S                 : Initial inventory (mean + 1.65σ).
    safety_stock      : Base safety stock (S - mean_demand).
    initial_inventory : Starting on_hand at all tiers (= S).
    backend           : "azure" | None (falls back to BACKEND env var)

    Returns list of dicts — 75 records per run (25 periods × 3 tiers).
    """
    if run_id is None:
        run_id = str(uuid.uuid4())[:8]

    states = {tier: TierState(initial_inventory) for tier in TIERS}
    first_demand = int(demand_series.iloc[0]["retail_demand"])
    for tier in TIERS:
        states[tier].exp_forecast = float(first_demand)

    records = []

    active_periods = demand_series[demand_series["period"] < demand_series["period"].max()]

    for _, row in active_periods.iterrows():
        period         = int(row["period"])
        calendar_month = str(row["calendar_month"])
        retail_demand  = int(row["retail_demand"])

        for tier in TIERS:
            states[tier].on_hand += states[tier].last_order

        downstream_order = retail_demand

        for tier in TIERS:
            st = states[tier]

            f = apply_fulfilment(st.on_hand, downstream_order, st.backlog)
            st.on_hand = f["on_hand_after"]
            st.backlog = f["backlog"]
            inventory_position = st.on_hand - st.backlog

            # Telemetry defaults
            call_latency_ms     = 0.0
            call_ttft_ms        = 0.0
            call_prompt_tok     = 0
            call_completion_tok = 0
            call_attempt        = 0
            rationale           = ""
            order_clamped       = False
            raw_order_quantity  = 0

            # Intent-specific columns
            intent_class    = None
            intent_mult     = None
            intent_fallback = None

            # Hybrid-specific columns
            ss_multiplier         = None
            raw_ss_multiplier     = None
            ss_multiplier_clamped = False
            llm_fallback          = False
            adjusted_ss           = None

            # ----------------------------------------------------------------
            # Order decision
            # ----------------------------------------------------------------

            if policy == "intent":
                ic_result = get_intent_class(
                    tier=tier,
                    condition=condition,
                    period=period,
                    calendar_month=calendar_month,
                    demand_received=downstream_order,
                    on_hand=st.on_hand,
                    backlog=st.backlog,
                    inventory_position=inventory_position,
                    base_ss=safety_stock,
                    model_tier=model_tier,
                    run_id=run_id,
                    model_name=model_name,
                    temperature=None,
                    history=st.intent_history if condition == "stateful" else None,
                    backend=backend,
                )

                intent_class    = ic_result["intent_class"]
                intent_fallback = ic_result["intent_fallback"]
                intent_mult     = INTENT_MULTIPLIER_MAP.get(intent_class, 1.0)
                adj_ss          = round(safety_stock * intent_mult)

                rationale           = ic_result.get("rationale", "")
                call_attempt        = ic_result.get("attempt_number", 1)
                call_latency_ms     = ic_result.get("latency_ms", 0.0)
                call_ttft_ms        = ic_result.get("ttft_ms", 0.0)
                call_prompt_tok     = ic_result.get("prompt_tokens", 0)
                call_completion_tok = ic_result.get("completion_tokens", 0)

                order, st.exp_forecast = policy_smoothed_out_with_ss(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=adj_ss,
                )

                if condition == "stateful":
                    st.intent_history.append({
                        "period":  period,
                        "demand":  downstream_order,
                        "order":   order,
                        "intent":  intent_class,
                        "backlog": f["backlog"],
                        "stockout": f["stockout"],
                    })
                    st.intent_history = st.intent_history[-HISTORY_WINDOW:]

            elif policy == "hybrid_control":
                order, st.exp_forecast = policy_smoothed_out_with_ss(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=safety_stock,
                )

            elif policy == "naive":
                order = policy_naive_passthrough(demand=downstream_order)

            elif policy == "order_up_to":
                order, st.exp_forecast = policy_order_up_to(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=safety_stock,
                )

            elif policy == "exp_smoothing":
                order, st.exp_forecast = policy_exp_smoothing(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    backlog=st.backlog,
                )

            else:
                raise ValueError(f"Unknown policy: {policy!r}")

            st.last_order = order

            records.append({
                "run_id":               run_id,
                "condition":            condition,
                "condition_label":      condition_label,
                "model_tier":           model_tier,
                "policy":               policy,
                "period":               period,
                "calendar_month":       calendar_month,
                "tier":                 tier,
                "demand_received":      downstream_order,
                "on_hand_before_order": st.on_hand,
                "backlog":              st.backlog,
                "inventory_position":   inventory_position,
                "order_placed":         order,
                "stockout":             f["stockout"],
                "shortfall":            f["shortfall"],
                "rationale":            rationale,
                "raw_order_quantity":   raw_order_quantity,
                "attempt_number":       call_attempt,
                "latency_ms":           call_latency_ms,
                "ttft_ms":              call_ttft_ms,
                "prompt_tokens":        call_prompt_tok,
                "completion_tokens":    call_completion_tok,
                "order_clamped":        order_clamped,
                # Intent columns (None for non-intent runs)
                "intent_class":         intent_class,
                "intent_multiplier":    intent_mult,
                "intent_fallback":      intent_fallback,
                # Hybrid columns kept for schema compatibility
                "ss_multiplier":        ss_multiplier,
                "raw_ss_multiplier":    raw_ss_multiplier,
                "ss_multiplier_clamped": ss_multiplier_clamped,
                "llm_fallback":         llm_fallback,
                "adjusted_ss":          adjusted_ss,
            })

            downstream_order = order

    # -----------------------------------------------------------------------
    # Period 25 — fulfilment only, no orders
    # -----------------------------------------------------------------------
    last_row       = demand_series[demand_series["period"] == demand_series["period"].max()].iloc[0]
    period         = int(last_row["period"])
    calendar_month = str(last_row["calendar_month"])
    retail_demand  = int(last_row["retail_demand"])

    for tier in TIERS:
        states[tier].on_hand += states[tier].last_order

    downstream_order = retail_demand
    for tier in TIERS:
        st = states[tier]
        f = apply_fulfilment(st.on_hand, downstream_order, st.backlog)
        st.on_hand = f["on_hand_after"]
        st.backlog = f["backlog"]

        records.append({
            "run_id":               run_id,
            "condition":            condition,
            "condition_label":      condition_label,
            "model_tier":           model_tier,
            "policy":               policy,
            "period":               period,
            "calendar_month":       calendar_month,
            "tier":                 tier,
            "demand_received":      downstream_order,
            "on_hand_before_order": st.on_hand,
            "backlog":              st.backlog,
            "inventory_position":   st.on_hand - st.backlog,
            "order_placed":         0,
            "stockout":             f["stockout"],
            "shortfall":            f["shortfall"],
            "rationale":            "",
            "raw_order_quantity":   0,
            "attempt_number":       0,
            "latency_ms":           0.0,
            "ttft_ms":              0.0,
            "prompt_tokens":        0,
            "completion_tokens":    0,
            "order_clamped":        False,
            "intent_class":         None,
            "intent_multiplier":    None,
            "intent_fallback":      None,
            "ss_multiplier":        None,
            "raw_ss_multiplier":    None,
            "ss_multiplier_clamped": False,
            "llm_fallback":         False,
            "adjusted_ss":          None,
        })

        downstream_order = 0

    return records
