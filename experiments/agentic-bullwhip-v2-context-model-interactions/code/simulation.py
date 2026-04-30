"""
Supply chain simulation — core experiment logic.

This module runs one complete 25-period simulation for a given experimental
condition (e.g. context_lightweight, blind_reasoning, order_up_to baseline).
It knows nothing about which backend or model is active — all LLM calls go
through agent_interface.get_order_decision().

One call to run_simulation() = one experimental run.
The caller (run_experiment.py) calls it 20 times per LLM condition and once
per heuristic condition, then aggregates the returned records.
"""

import logging
import os
import uuid

import pandas as pd

from agent_interface import (
    build_user_prompt,
    get_order_decision,
    get_system_prompt,
)

logger = logging.getLogger(__name__)

# Tier execution order is fixed and serial: OEM sees retail demand first,
# then passes its order downstream as the Ancillary's demand, and so on.
TIERS = ["OEM", "Ancillary", "Component"]


# ---------------------------------------------------------------------------
# Heuristic policies
# Each returns an integer order quantity. No LLM calls involved.
# ---------------------------------------------------------------------------

def policy_naive_passthrough(demand: int, **_) -> int:
    """
    Order exactly what your downstream customer ordered.
    This is the floor benchmark — OVAR = 1.0 by construction because order
    variance = demand variance. Expects high stockouts since no safety stock
    is built. If an LLM condition can't beat this, it is adding noise, not value.
    """
    return demand


def policy_order_up_to(
    forecast: float,
    demand: int,
    inventory_position: int,
    safety_stock: int,
    alpha: float = 0.30,
) -> tuple[int, float]:
    """
    Forecast-based Order-Up-To (OUT) policy.

    A static OUT target collapses to naive passthrough under this experiment's
    timing (replenishment arrives before fulfilment, agents order after seeing
    current demand). To keep OUT as a meaningful benchmark, the target position
    is updated each period using a smoothed one-step-ahead demand forecast.

    Formulas:
      F_t               = alpha * D_t + (1 - alpha) * F_{t-1}
      target_position_t = round(F_t) + safety_stock
      order_t           = max(0, target_position_t - inventory_position_t)

    inventory_position = on_hand - backlog  (pipeline is zero with L=1)
    safety_stock       = S - mean_demand, derived from the demand dataset

    Returns (order_quantity, updated_forecast) so the caller can store the
    forecast state in TierState for the next period.
    """
    new_forecast = alpha * demand + (1 - alpha) * forecast
    target_position = round(new_forecast) + safety_stock
    order = max(0, target_position - inventory_position)
    return order, new_forecast


def policy_exp_smoothing(forecast: float, demand: int, backlog: int, alpha: float = 0.30) -> tuple[int, float]:
    """
    Exponential smoothing forecast-based ordering.
    Formula: F_t = alpha * D_{t-1} + (1 - alpha) * F_{t-1}

    alpha = 0.30 means 30% weight on the most recent demand observation
    and 70% on the previous forecast. This makes the policy slow to react
    to sudden demand spikes (e.g. Diwali) and slow to forget them afterward.

    The order is the smoothed forecast plus any outstanding backlog, floored at 0.
    This baseline shows whether simple signal-smoothing alone captures some
    of what context agents are supposed to do with seasonal awareness.

    Returns (order_quantity, updated_forecast) — the forecast must be stored
    in TierState.exp_forecast and passed in again next period.
    """
    new_forecast = alpha * demand + (1 - alpha) * forecast
    order = max(0, round(new_forecast) + backlog)
    return order, new_forecast


# ---------------------------------------------------------------------------
# Fulfilment rule — applied identically at every tier every period
# ---------------------------------------------------------------------------

def apply_fulfilment(on_hand: int, demand: int, backlog_prev: int) -> dict:
    """
    Serves current-period demand plus any unfulfilled demand carried forward
    from previous periods (backlog).

    State equations (from experiment design Section 6.1):
      total_obligation = demand_t + backlog_{t-1}
      fulfilled_t      = min(on_hand_t, total_obligation)
      shortfall_t      = max(0, total_obligation - on_hand_t)
      backlog_t        = shortfall_t          # carries forward to t+1
      on_hand_after    = on_hand_t - fulfilled_t

    A stockout is recorded whenever shortfall_t > 0.
    on_hand_after is what the agent sees when making its order decision.
    """
    total_obligation = demand + backlog_prev      # what we owe this period
    fulfilled = min(on_hand, total_obligation)    # what we can actually ship
    shortfall = max(0, total_obligation - on_hand)  # what we cannot ship
    on_hand_after = on_hand - fulfilled           # stock remaining after shipping
    backlog_new = shortfall                       # unpaid obligation rolls forward
    stockout = shortfall > 0

    return {
        "fulfilled": fulfilled,
        "shortfall": shortfall,
        "on_hand_after": on_hand_after,
        "backlog": backlog_new,
        "stockout": stockout,
    }


# ---------------------------------------------------------------------------
# Per-tier state — one instance per tier, reset at the start of each run
# ---------------------------------------------------------------------------

class TierState:
    def __init__(self, initial_inventory: int):
        self.on_hand = initial_inventory   # units physically in stock
        self.backlog = 0                   # unfulfilled units owed to downstream
        self.last_order = 0               # order placed last period; arrives at start of next period
        self.exp_forecast = None          # running forecast for forecast-based heuristics


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
) -> list[dict]:
    """
    Run one complete 25-period simulation and return all records.

    Parameters
    ----------
    demand_series     : DataFrame with columns [period, calendar_month, retail_demand]
                        Must have exactly 25 rows. Period 25 is fulfilment-only.
    condition         : "blind" — agent gets no company/calendar info
                        "context" — agent gets persona + calendar month
    model_tier        : "lightweight" | "reasoning"
                        Selects which env var MODEL_LIGHTWEIGHT/MODEL_REASONING to use.
                        Ignored for heuristic policies.
    policy            : "llm"            — agent makes decisions via LLM
                        "naive"          — passthrough heuristic
                        "order_up_to"    — forecast-based OUT heuristic
                        "exp_smoothing"  — exponential smoothing heuristic
    S                 : Initial inventory anchor derived from demand data at runtime.
                        Used to start all tiers from the same stock position.
    safety_stock      : Fixed safety stock used by the forecast-based OUT heuristic.
    initial_inventory : Starting on_hand units at all three tiers.
                        Should equal S so all conditions share the same opening stock.
    condition_label   : Short name stored in every output record (e.g. "blind_lightweight").
                        Used by run_experiment.py to group records by condition for summaries.
    model_name        : Optional — if set, overrides the model env var.
                        Used by E4 OSS conditions (Phi-4) so they don't accidentally use
                        the proprietary MODEL_REASONING model.
    run_id            : Short identifier for log messages. Auto-generated if not provided.

    Returns
    -------
    List of dicts — one dict per (period, tier) = 25 periods × 3 tiers = 75 records per run.
    Raises RuntimeError if an LLM call fails all 3 parse attempts (caller replaces the run).
    """
    if run_id is None:
        run_id = str(uuid.uuid4())[:8]

    # Create one TierState per tier — independent state, reset each run
    states = {tier: TierState(initial_inventory) for tier in TIERS}

    # Seed exponential smoothing forecast with actual first-period demand
    # so it starts from a realistic baseline rather than zero
    first_demand = int(demand_series.iloc[0]["retail_demand"])
    for tier in TIERS:
        states[tier].exp_forecast = float(first_demand)

    records = []

    # Temperature for LLM calls — resolved once per run based on condition + model_tier.
    # blind_lightweight      → TEMP_LIGHTWEIGHT         (default 0.4, analytical)
    # context_lightweight    → TEMP_CONTEXT_LIGHTWEIGHT (default 0.4, analytical)
    # blind_reasoning        → TEMP_REASONING           (default 0.0, deterministic)
    # context_reasoning      → TEMP_CONTEXT_REASONING   (default 0.3, strategy exploration)
    # Note: Azure forces reasoning models to 1.0 regardless of this value.
    if model_tier == "reasoning":
        if condition == "context":
            llm_temperature = float(os.environ.get("TEMP_CONTEXT_REASONING", "0.3"))
        else:
            llm_temperature = float(os.environ.get("TEMP_REASONING", "0.0"))
    elif condition == "context":
        llm_temperature = float(os.environ.get("TEMP_CONTEXT_LIGHTWEIGHT", "0.4"))
    else:
        llm_temperature = float(os.environ.get("TEMP_LIGHTWEIGHT", "0.4"))

    # Order ceiling — hallucination guard, NOT a scientific constraint.
    # The experiment design specifies no order ceiling. This cap exists solely to
    # prevent a single malformed LLM output (e.g. "order_quantity": 999999999) from
    # corrupting the inventory simulation for the remaining 23 periods of a run.
    # Set to 10 × peak demand — wide enough that no plausible supply chain order
    # would ever hit it, but tight enough to catch clear hallucinations.
    # Every clamp event is logged as WARNING and recorded in the run record
    # (order_clamped=True, raw_order_quantity=<unclamped value>) so it can be
    # detected and excluded from analysis if needed.
    # If this fires in production it should be investigated, not silently accepted.
    max_demand = int(demand_series["retail_demand"].max())
    order_ceiling = 10 * max_demand

    # Periods 1–24 are active: agents make order decisions each period
    active_periods = demand_series[demand_series["period"] < demand_series["period"].max()]

    for _, row in active_periods.iterrows():
        period = int(row["period"])
        calendar_month = str(row["calendar_month"])   # e.g. "Nov 2025"
        retail_demand = int(row["retail_demand"])

        # --- Step 8 from design doc (delayed from previous period) ---
        # Replenishment arrives at the START of this period, before any fulfilment.
        # last_order was placed in period t-1 and has now arrived.
        for tier in TIERS:
            states[tier].on_hand += states[tier].last_order

        # --- Serial execution: OEM first, then Ancillary, then Component ---
        # downstream_order is what the current tier must serve.
        # It starts as retail demand at OEM, then becomes each tier's placed order
        # as we move upstream. This is how the bullwhip propagates.
        downstream_order = retail_demand

        for tier in TIERS:
            st = states[tier]

            # --- Step 2/4/6: Fulfilment (serve demand + backlog) ---
            f = apply_fulfilment(st.on_hand, downstream_order, st.backlog)
            st.on_hand = f["on_hand_after"]   # remaining stock after shipping
            st.backlog = f["backlog"]          # new backlog (zero if fully served)

            # inventory_position is what both agents and the OUT heuristic use
            # for their ordering decisions (see design doc Section 3.1)
            inventory_position = st.on_hand - st.backlog

            # --- Step 3/5/7: Order decision ---
            call_latency_ms     = 0.0
            call_ttft_ms        = 0.0
            call_prompt_tok     = 0
            call_completion_tok = 0
            order_clamped       = False
            raw_order_quantity  = 0
            call_reasoning_tok  = 0
            call_cached_tok     = 0
            call_generation_tps = 0.0
            call_attempt        = 0
            raw_order_quantity  = 0

            if policy == "llm":
                # Build prompts then call the LLM (routed through backend)
                sys_prompt = get_system_prompt(tier, condition)
                usr_prompt = build_user_prompt(
                    tier=tier,
                    condition=condition,
                    period=period,
                    calendar_month=calendar_month,
                    demand_received=downstream_order,
                    on_hand=st.on_hand,
                    backlog=st.backlog,
                    inventory_position=inventory_position,
                )
                result = get_order_decision(
                    system_prompt=sys_prompt,
                    user_prompt=usr_prompt,
                    model_tier=model_tier,
                    run_id=run_id,
                    period=period,
                    tier=tier,
                    model_name=model_name,       # None for E1/E2; set for E4 OSS
                    temperature=llm_temperature, # condition-aware: 0.0 blind, 0.3 context
                )
                # Clamp to zero: agents cannot place negative orders.
                # Cap at order_ceiling: prevents a single hallucinated value from
                # blowing up the inventory simulation.
                raw_qty = result["order_quantity"]
                order = max(0, min(raw_qty, order_ceiling))
                order_clamped = (raw_qty != order)
                if order_clamped:
                    logger.warning(
                        "run=%s period=%d tier=%s order clamped: raw=%d → %d (ceiling=%d)",
                        run_id, period, tier, raw_qty, order, order_ceiling,
                    )
                rationale           = result["rationale"]
                raw_order_quantity  = raw_qty
                call_attempt        = result.get("attempt_number", 1)
                call_latency_ms     = result.get("latency_ms", 0.0)
                call_ttft_ms        = result.get("ttft_ms", 0.0)
                call_prompt_tok     = result.get("prompt_tokens", 0)
                call_completion_tok = result.get("completion_tokens", 0)
                call_reasoning_tok  = result.get("reasoning_tokens", 0)
                call_cached_tok     = result.get("cached_tokens", 0)
                call_generation_tps = result.get("generation_tps", 0.0)

            elif policy == "naive":
                order = policy_naive_passthrough(demand=downstream_order)
                rationale = ""

            elif policy == "order_up_to":
                order, st.exp_forecast = policy_order_up_to(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=safety_stock,
                )
                rationale = ""

            elif policy == "exp_smoothing":
                # Must store updated forecast back into state for next period
                order, st.exp_forecast = policy_exp_smoothing(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    backlog=st.backlog,
                )
                rationale = ""

            else:
                raise ValueError(f"Unknown policy: {policy}")

            # Store order so it arrives as replenishment at start of next period
            st.last_order = order

            records.append({
                "run_id": run_id,
                "condition": condition,           # "blind" or "context"
                "condition_label": condition_label,  # e.g. "context_lightweight"
                "model_tier": model_tier,
                "policy": policy,
                "period": period,
                "calendar_month": calendar_month,
                "tier": tier,
                "demand_received": downstream_order,      # demand this tier had to serve
                "on_hand_before_order": st.on_hand,       # post-fulfilment, pre-order
                "backlog": st.backlog,
                "inventory_position": inventory_position,
                "order_placed": order,
                "stockout": f["stockout"],   # True if demand + backlog exceeded on_hand
                "shortfall": f["shortfall"], # units that could not be served
                "rationale": rationale,
                "raw_order_quantity": raw_order_quantity,  # pre-clamp value
                # LLM inference telemetry (0 for heuristic rows)
                "attempt_number":    call_attempt,
                "latency_ms":        call_latency_ms,
                "ttft_ms":           call_ttft_ms,
                "prompt_tokens":     call_prompt_tok,
                "completion_tokens": call_completion_tok,
                "reasoning_tokens":  call_reasoning_tok,
                "cached_tokens":     call_cached_tok,
                "generation_tps":    call_generation_tps,
                "order_clamped":     order_clamped,
                "raw_order_quantity": raw_order_quantity,
            })

            # Pass this tier's order upstream as the next tier's demand signal.
            # This is the information cascade that creates the bullwhip effect.
            downstream_order = order

    # ---------------------------------------------------------------------------
    # Period 25 — fulfilment only, no orders placed
    # ---------------------------------------------------------------------------
    # The simulation design closes out with a final period where demand is served
    # from remaining stock but no new orders are placed. This lets us measure
    # any stockouts from unfilled backlog still in the system at period 24.
    last_row = demand_series[demand_series["period"] == demand_series["period"].max()].iloc[0]
    period = int(last_row["period"])
    calendar_month = str(last_row["calendar_month"])
    retail_demand = int(last_row["retail_demand"])

    # Final replenishment: period-24 orders arrive
    for tier in TIERS:
        states[tier].on_hand += states[tier].last_order

    downstream_order = retail_demand
    for tier in TIERS:
        st = states[tier]
        f = apply_fulfilment(st.on_hand, downstream_order, st.backlog)
        st.on_hand = f["on_hand_after"]
        st.backlog = f["backlog"]

        records.append({
            "run_id": run_id,
            "condition": condition,
            "condition_label": condition_label,
            "model_tier": model_tier,
            "policy": policy,
            "period": period,
            "calendar_month": calendar_month,
            "tier": tier,
            "demand_received": downstream_order,
            "on_hand_before_order": st.on_hand,
            "backlog": st.backlog,
            "inventory_position": st.on_hand - st.backlog,
            "order_placed": 0,           # no orders in final period by design
            "stockout": f["stockout"],
            "shortfall": f["shortfall"],
            "rationale": "",
        })

        # No orders cascade in the final period — each tier gets only retail demand
        downstream_order = 0

    return records
