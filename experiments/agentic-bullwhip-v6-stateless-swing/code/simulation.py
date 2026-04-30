"""
Supply chain simulation — V6 StatelessSwing.

Two policy families:
  policy == "adaptive_alpha"  — LLM chooses α ∈ {0.1, 0.3, 0.5, 0.7} each period
  policy == "exp_smoothing"   — fixed α (passed via `alpha` arg); deterministic baseline

Order formula (both policies):
  F_t = alpha × D_t + (1 - alpha) × F_{t-1}
  order_t = max(0, round(F_t) + backlog_t)

25-month demand series: periods 1-24 active ordering, period 25 fulfilment-only.
"""

import logging
import uuid

import pandas as pd

from agent_interface import get_alpha_value

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]
HISTORY_WINDOW = 3


# ---------------------------------------------------------------------------
# Order policy
# ---------------------------------------------------------------------------

def policy_exp_smoothing(
    forecast: float,
    demand: int,
    backlog: int,
    alpha: float = 0.30,
) -> tuple[int, float]:
    new_forecast = alpha * demand + (1 - alpha) * forecast
    order = max(0, round(new_forecast) + backlog)
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
        self.on_hand              = initial_inventory
        self.backlog              = 0
        self.last_order           = 0
        self.exp_forecast         = None
        self.demand_history: list[int]  = []   # rolling 5-period window (oldest first)
        self.alpha_history: list[dict]  = []   # stateful: last HISTORY_WINDOW entries
        self.prev_forecast_error: float | None = None  # D_{t-1} - F_{t-2}, passed next period


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
    alpha: float = 0.30,
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
    condition         : "blind" | "context" | "stateful"
    model_tier        : "lightweight" | "reasoning" | None (for baselines)
    policy            : "adaptive_alpha" | "exp_smoothing"
    S                 : Initial inventory (mean + 1.65σ).
    safety_stock      : Unused in V6 (kept for schema compatibility).
    initial_inventory : Starting on_hand at all tiers (= S).
    alpha             : Fixed smoothing coefficient for exp_smoothing baselines.
    backend           : "azure" | "local" | None (falls back to BACKEND env var)

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

            # Telemetry defaults
            call_latency_ms     = 0.0
            call_ttft_ms        = 0.0
            call_prompt_tok     = 0
            call_completion_tok = 0
            call_attempt        = 0
            rationale           = ""

            # Alpha columns — initialised for all branches before records.append
            alpha_chosen   = alpha
            alpha_fallback = False

            # ----------------------------------------------------------------
            # Order decision
            # ----------------------------------------------------------------

            if policy == "adaptive_alpha":
                # Capture error against OLD forecast BEFORE updating
                current_error = downstream_order - st.exp_forecast  # D_t - F_{t-1}

                av_result = get_alpha_value(
                    tier=tier,
                    condition=condition,
                    period=period,
                    calendar_month=calendar_month,
                    demand_history=st.demand_history,
                    prev_forecast=st.exp_forecast,
                    forecast_error=st.prev_forecast_error,
                    model_tier=model_tier,
                    run_id=run_id,
                    model_name=model_name,
                    temperature=None,
                    history=st.alpha_history if condition == "stateful" else None,
                    backend=backend,
                )

                alpha_chosen        = av_result["alpha"]
                alpha_fallback      = av_result["alpha_fallback"]
                rationale           = av_result.get("rationale", "")
                call_attempt        = av_result.get("attempt_number", 1)
                call_latency_ms     = av_result.get("latency_ms", 0.0)
                call_ttft_ms        = av_result.get("ttft_ms", 0.0)
                call_prompt_tok     = av_result.get("prompt_tokens", 0)
                call_completion_tok = av_result.get("completion_tokens", 0)

                order, st.exp_forecast = policy_exp_smoothing(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    backlog=st.backlog,
                    alpha=alpha_chosen,
                )

                st.demand_history      = (st.demand_history + [downstream_order])[-5:]
                st.prev_forecast_error = current_error

                if condition == "stateful":
                    st.alpha_history = (st.alpha_history + [{
                        "period":         period,
                        "demand":         downstream_order,
                        "alpha_chosen":   alpha_chosen,
                        "forecast_error": current_error,
                        "backlog":        f["backlog"],
                        "stockout":       f["stockout"],
                    }])[-HISTORY_WINDOW:]

            elif policy == "exp_smoothing":
                order, st.exp_forecast = policy_exp_smoothing(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    backlog=st.backlog,
                    alpha=alpha,
                )
                # alpha_chosen = alpha, alpha_fallback = False (set above)

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
                "inventory_position":   st.on_hand - st.backlog,
                "order_placed":         order,
                "stockout":             f["stockout"],
                "shortfall":            f["shortfall"],
                "rationale":            rationale,
                "attempt_number":       call_attempt,
                "latency_ms":           call_latency_ms,
                "ttft_ms":              call_ttft_ms,
                "prompt_tokens":        call_prompt_tok,
                "completion_tokens":    call_completion_tok,
                "alpha_chosen":         alpha_chosen,
                "alpha_fallback":       alpha_fallback,
            })

            downstream_order = order

    # -----------------------------------------------------------------------
    # Period 25 — fulfilment only, no orders
    # -----------------------------------------------------------------------
    last_row       = demand_series[demand_series["period"] == demand_series["period"].max()].iloc[0]
    period         = int(last_row["period"])
    calendar_month = str(last_row["calendar_month"])

    for tier in TIERS:
        states[tier].on_hand += states[tier].last_order

    downstream_order = int(last_row["retail_demand"])
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
            "attempt_number":       0,
            "latency_ms":           0.0,
            "ttft_ms":              0.0,
            "prompt_tokens":        0,
            "completion_tokens":    0,
            "alpha_chosen":         None,
            "alpha_fallback":       None,
        })

        downstream_order = 0

    return records
