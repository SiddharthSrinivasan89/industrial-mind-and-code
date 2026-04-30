"""
Supply chain simulation — V3b hybrid architecture experiment.

Implements the hybrid architecture: a planning layer (LLM sets safety_stock_multiplier)
and an execution layer (deterministic OUT-style ordering formula). The LLM only
needs to reason about direction and magnitude of seasonal buffer adjustment; the
formula handles the rest.

Two execution modes:
  policy == "exp_smoothing" | "naive" | "order_up_to"
    — deterministic heuristic baselines, no LLM calls.

  policy == "hybrid"
    — two-layer execution each period per tier:
        Layer 1 (planning): LLM receives state + optional context/history,
                            outputs a safety stock multiplier in [0.5, 3.0].
        Layer 2 (execution): policy_smoothed_out_with_ss() runs with the
                             LLM-adjusted safety stock; OUT-style:
                             order = max(0, round(F_t) + SS_t - inventory_position).

This module knows nothing about which backend or model is active. All LLM calls
go through agent_interface.get_ss_multiplier() (hybrid) or are not made at all
(heuristics).

One call to run_simulation() = one experimental run.
"""

import logging
import os
import uuid

import pandas as pd

from agent_interface import (
    build_user_prompt,
    build_hybrid_user_prompt,
    get_order_decision,
    get_ss_multiplier,
    get_system_prompt,
    get_hybrid_system_prompt,
)

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

# Multiplier bounds — enforced in code regardless of what the LLM returns.
# 0.5 halves the base safety stock (still some buffer, unlikely to catastrophically
# under-order unless demand spikes severely). 3.0 triples it (large buffer, no
# realistic seasonal event justifies more than 3× normal safety stock).
# These are intentionally wide enough not to constrain reasonable seasonal responses
# but tight enough to catch clearly erratic LLM outputs.
MULTIPLIER_MIN = 0.5
MULTIPLIER_MAX = 3.0
MULTIPLIER_FALLBACK = 1.0   # used when LLM parse fails entirely


# ---------------------------------------------------------------------------
# Heuristic policies
# ---------------------------------------------------------------------------

def policy_naive_passthrough(demand: int, **_) -> int:
    """Order exactly what the downstream customer ordered. OVAR = 1.0 by construction."""
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

    F_t               = alpha * D_t + (1 - alpha) * F_{t-1}
    target_position_t = round(F_t) + safety_stock
    order_t           = max(0, target_position_t - inventory_position_t)
    """
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
    """
    Exponential smoothing ordering. No safety stock — order = smoothed forecast + backlog.

    This is the within-experiment performance benchmark. Used here for the
    baselines condition only. The hybrid execution layer uses policy_smoothed_out_with_ss()
    which adds an explicit safety stock term.
    """
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
    """
    OUT-style exponential smoothing with LLM-adjustable safety stock.
    Used exclusively by the hybrid policy as the execution layer.

    Formula (Order-Up-To style):
      F_t              = alpha * D_t + (1 - alpha) * F_{t-1}
      target_position  = round(F_t) + safety_stock
      order_t          = max(0, target_position - inventory_position_t)

    where inventory_position = on_hand - backlog.

    The target_position is the desired stock level; ordering brings inventory
    position up to that target. The LLM's multiplier adjusts safety_stock:
      safety_stock = base_SS * multiplier_t

    This is methodologically equivalent to policy_order_up_to() with a
    dynamically adjusted safety stock, which makes the multiplier a genuine
    safety-stock parameter in the OUT sense — not a persistent additive offset.

    At multiplier=1.0 this produces the same orders as policy_order_up_to()
    with fixed safety_stock=base_SS. The deterministic hybrid_control condition
    uses this function with multiplier=1.0 fixed (no LLM), establishing the
    architectural baseline separate from pure exp_smoothing.

    Returns (order_quantity, updated_forecast).
    """
    new_forecast = alpha * demand + (1 - alpha) * forecast
    target_position = round(new_forecast) + safety_stock
    order = max(0, target_position - inventory_position)
    return order, new_forecast


# ---------------------------------------------------------------------------
# Fulfilment
# ---------------------------------------------------------------------------

def apply_fulfilment(on_hand: int, demand: int, backlog_prev: int) -> dict:
    """
    Serve current-period demand plus any unfulfilled backlog from prior periods.

    State equations:
      total_obligation = demand_t + backlog_{t-1}
      fulfilled_t      = min(on_hand_t, total_obligation)
      shortfall_t      = max(0, total_obligation - on_hand_t)
      backlog_t        = shortfall_t
      on_hand_after    = on_hand_t - fulfilled_t
    """
    total_obligation = demand + backlog_prev
    fulfilled = min(on_hand, total_obligation)
    shortfall = max(0, total_obligation - on_hand)
    on_hand_after = on_hand - fulfilled
    backlog_new = shortfall
    stockout = shortfall > 0

    return {
        "fulfilled": fulfilled,
        "shortfall": shortfall,
        "on_hand_after": on_hand_after,
        "backlog": backlog_new,
        "stockout": stockout,
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
        # Stateful hybrid: rolling window of last N periods' (demand, order, multiplier)
        self.history: list[dict] = []


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
    hybrid_condition: str | None = None,
    history_window: int = 3,
    condition_label: str = "",
    model_name: str | None = None,
    run_id: str | None = None,
    backend: str | None = None,
) -> list[dict]:
    """
    Run one complete 25-period simulation and return all records.

    Parameters
    ----------
    demand_series     : DataFrame with [period, calendar_month, retail_demand].
                        Must have exactly 25 rows. Period 25 is fulfilment-only.
    condition         : "blind" | "context" — for heuristic and legacy LLM policy only.
                        For hybrid policy, this is superseded by hybrid_condition.
    model_tier        : "lightweight" | "reasoning" — selects MODEL_LIGHTWEIGHT/REASONING env var.
    policy            : "hybrid"        — LLM parameterises exp_smoothing safety stock
                        "llm"           — legacy: LLM decides order quantity directly
                        "naive"         — passthrough heuristic
                        "order_up_to"   — forecast-based OUT heuristic
                        "exp_smoothing" — exponential smoothing heuristic (within-experiment benchmark)
    S                 : Initial inventory anchor (mean + 1.65σ from demand data).
    safety_stock      : Base safety stock (= S - mean_demand). Used by order_up_to heuristic
                        AND as base_SS for the hybrid multiplier.
    initial_inventory : Starting on_hand at all three tiers (should equal S).
    hybrid_condition  : "blind" | "context" | "stateful" — which hybrid variant to run.
                        Required when policy == "hybrid". Ignored otherwise.
    history_window    : Number of past periods to include in H-Stateful prompts (default 3).
    condition_label   : Short name stored in every output record.
    model_name        : Optional hard override for the model name.
    run_id            : Short identifier for log messages. Auto-generated if not provided.

    Returns
    -------
    List of dicts — one dict per (period, tier) = 75 records per run.
    Raises RuntimeError if the LLM backend fails all parse attempts.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())[:8]

    if policy == "hybrid" and hybrid_condition is None:
        raise ValueError("hybrid_condition must be set when policy='hybrid'")

    states = {tier: TierState(initial_inventory) for tier in TIERS}

    # Seed exp_smoothing forecast from first-period demand
    first_demand = int(demand_series.iloc[0]["retail_demand"])
    for tier in TIERS:
        states[tier].exp_forecast = float(first_demand)

    records = []

    # Temperature resolution for hybrid calls
    # All hybrid conditions use a single env var TEMP_HYBRID (default 0.3).
    # 0.3 allows multiplier variation across 20 runs without erratic outputs.
    if policy == "hybrid":
        llm_temperature = float(os.environ.get("TEMP_HYBRID", "0.3"))
    elif model_tier == "reasoning":
        if condition == "context":
            llm_temperature = float(os.environ.get("TEMP_CONTEXT_REASONING", "0.3"))
        else:
            llm_temperature = float(os.environ.get("TEMP_REASONING", "0.0"))
    elif condition == "context":
        llm_temperature = float(os.environ.get("TEMP_CONTEXT_LIGHTWEIGHT", "0.4"))
    else:
        llm_temperature = float(os.environ.get("TEMP_LIGHTWEIGHT", "0.4"))

    # Order ceiling — hallucination guard for legacy LLM policy only.
    # Hybrid policy outputs a bounded multiplier, not a raw order quantity,
    # so the ceiling is not needed there. Kept here for legacy llm policy compat.
    max_demand = int(demand_series["retail_demand"].max())
    order_ceiling = 10 * max_demand

    active_periods = demand_series[demand_series["period"] < demand_series["period"].max()]

    for _, row in active_periods.iterrows():
        period = int(row["period"])
        calendar_month = str(row["calendar_month"])
        retail_demand = int(row["retail_demand"])

        # Replenishment arrives at start of period (last_order placed in period t-1)
        for tier in TIERS:
            states[tier].on_hand += states[tier].last_order

        downstream_order = retail_demand

        for tier in TIERS:
            st = states[tier]

            # Fulfilment: serve demand + carry-forward backlog
            f = apply_fulfilment(st.on_hand, downstream_order, st.backlog)
            st.on_hand = f["on_hand_after"]
            st.backlog = f["backlog"]
            inventory_position = st.on_hand - st.backlog

            # --- Telemetry defaults (overwritten by LLM branch if called) ---
            call_latency_ms     = 0.0
            call_ttft_ms        = 0.0
            call_prompt_tok     = 0
            call_completion_tok = 0
            call_reasoning_tok  = 0
            call_cached_tok     = 0
            call_generation_tps = 0.0
            call_attempt        = 0
            order_clamped       = False
            raw_order_quantity  = 0
            rationale           = ""
            # Hybrid-specific telemetry
            ss_multiplier        = None
            raw_ss_multiplier    = None
            ss_multiplier_clamped = False
            llm_fallback         = False
            adjusted_ss          = None

            # ----------------------------------------------------------------
            # Order decision
            # ----------------------------------------------------------------

            if policy == "hybrid":
                # --- Layer 1: LLM parameterisation ---
                sys_prompt = get_hybrid_system_prompt(tier, hybrid_condition)
                usr_prompt = build_hybrid_user_prompt(
                    tier=tier,
                    hybrid_condition=hybrid_condition,
                    period=period,
                    calendar_month=calendar_month,
                    demand_received=downstream_order,
                    on_hand=st.on_hand,
                    backlog=st.backlog,
                    inventory_position=inventory_position,
                    base_ss=safety_stock,
                    history=st.history if hybrid_condition == "stateful" else None,
                )
                result = get_ss_multiplier(
                    system_prompt=sys_prompt,
                    user_prompt=usr_prompt,
                    model_tier=model_tier,
                    run_id=run_id,
                    period=period,
                    tier=tier,
                    model_name=model_name,
                    temperature=llm_temperature,
                    backend=backend,
                )

                # Parse and bound-check the multiplier
                raw_mult = result.get("safety_stock_multiplier")
                try:
                    raw_mult = float(raw_mult)
                    llm_fallback = False
                except (TypeError, ValueError):
                    logger.warning(
                        "run=%s period=%d tier=%s multiplier parse failed (raw=%r) — "
                        "falling back to %.1f",
                        run_id, period, tier, raw_mult, MULTIPLIER_FALLBACK,
                    )
                    raw_mult = MULTIPLIER_FALLBACK
                    llm_fallback = True

                clamped = max(MULTIPLIER_MIN, min(MULTIPLIER_MAX, raw_mult))
                ss_multiplier_clamped = (clamped != raw_mult)
                if ss_multiplier_clamped and not llm_fallback:
                    logger.warning(
                        "run=%s period=%d tier=%s multiplier clamped: %.3f → %.3f",
                        run_id, period, tier, raw_mult, clamped,
                    )

                ss_multiplier     = clamped
                raw_ss_multiplier = raw_mult
                adjusted_ss_val   = round(safety_stock * clamped)
                adjusted_ss       = adjusted_ss_val

                rationale           = result.get("rationale", "")
                call_attempt        = result.get("attempt_number", 1)
                call_latency_ms     = result.get("latency_ms", 0.0)
                call_ttft_ms        = result.get("ttft_ms", 0.0)
                call_prompt_tok     = result.get("prompt_tokens", 0)
                call_completion_tok = result.get("completion_tokens", 0)
                call_reasoning_tok  = result.get("reasoning_tokens", 0)
                call_cached_tok     = result.get("cached_tokens", 0)
                call_generation_tps = result.get("generation_tps", 0.0)

                # --- Layer 2: OUT-style execution with LLM-adjusted safety stock ---
                order, st.exp_forecast = policy_smoothed_out_with_ss(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=adjusted_ss_val,
                )

                # Update stateful history (H-Stateful only)
                # Include backlog and stockout_flag so the agent can assess
                # whether its last multiplier choice actually helped — not just
                # what it ordered, but whether the outcome was adequate.
                if hybrid_condition == "stateful":
                    st.history.append({
                        "period": period,
                        "demand": downstream_order,
                        "order": order,
                        "ss_multiplier": ss_multiplier,
                        "backlog": f["backlog"],
                        "stockout": f["stockout"],
                    })
                    st.history = st.history[-history_window:]

            elif policy == "llm":
                # Legacy autonomous LLM ordering (direct order quantity — included for reference)
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
                    model_name=model_name,
                    temperature=llm_temperature,
                    backend=backend,
                )
                raw_qty = result["order_quantity"]
                order = max(0, min(raw_qty, order_ceiling))
                order_clamped = (raw_qty != order)
                if order_clamped:
                    logger.warning(
                        "run=%s period=%d tier=%s order clamped: raw=%d → %d",
                        run_id, period, tier, raw_qty, order,
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

            elif policy == "hybrid_control":
                # Deterministic architectural control: same OUT-style formula as hybrid,
                # but multiplier fixed at 1.0 with no LLM call.
                # This isolates whether any improvement in hybrid conditions comes from
                # the LLM or from simply introducing the OUT-style safety stock formula.
                order, st.exp_forecast = policy_smoothed_out_with_ss(
                    forecast=st.exp_forecast,
                    demand=downstream_order,
                    inventory_position=inventory_position,
                    safety_stock=safety_stock,   # base_SS × 1.0
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
                "hybrid_condition":     hybrid_condition,
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
                # Hybrid-specific columns (null for non-hybrid rows)
                "ss_multiplier":          ss_multiplier,
                "raw_ss_multiplier":      raw_ss_multiplier,
                "ss_multiplier_clamped":  ss_multiplier_clamped,
                "llm_fallback":           llm_fallback,
                "adjusted_ss":            adjusted_ss,
            })

            downstream_order = order

    # ---------------------------------------------------------------------------
    # Period 25 — fulfilment only, no orders
    # ---------------------------------------------------------------------------
    last_row = demand_series[demand_series["period"] == demand_series["period"].max()].iloc[0]
    period = int(last_row["period"])
    calendar_month = str(last_row["calendar_month"])
    retail_demand = int(last_row["retail_demand"])

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
            "hybrid_condition":     hybrid_condition,
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
            "reasoning_tokens":     0,
            "cached_tokens":        0,
            "generation_tps":       0.0,
            "order_clamped":        False,
            "ss_multiplier":        None,
            "raw_ss_multiplier":    None,
            "ss_multiplier_clamped": False,
            "llm_fallback":         False,
            "adjusted_ss":          None,
        })

        downstream_order = 0

    return records
