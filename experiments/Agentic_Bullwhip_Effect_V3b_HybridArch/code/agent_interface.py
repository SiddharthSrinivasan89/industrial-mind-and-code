"""
Agent interface — V3b hybrid architecture.

Two distinct interfaces:
  get_order_decision()  — legacy: LLM decides order quantity directly (V2 behaviour)
  get_ss_multiplier()   — new: LLM decides safety stock multiplier for exp_smoothing

Both interfaces route through the same backend (azure or local), which is
selected by the BACKEND env var. Swapping backends requires no code changes.

Prompt design rationale for hybrid:
  V2 showed that LLMs produce articulate seasonal rationales but fail to
  translate them into correct order quantities. The hybrid architecture separates
  these concerns: the LLM only needs to reason about direction and magnitude of
  seasonal buffer adjustment; the formula handles the rest. Showing the formula
  explicitly in the prompt prevents the LLM from trying to encode a full order
  quantity into the multiplier.
"""

import os
import importlib

# ---------------------------------------------------------------------------
# Legacy prompts — V2 autonomous ordering (kept for llm policy compat)
# ---------------------------------------------------------------------------

BLIND_SYSTEM_PROMPT = (
    "You are a supply chain ordering agent.\n"
    "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
    'Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}'
)

CONTEXT_SYSTEM_PROMPTS = {
    "OEM": (
        "You are a supply chain ordering agent for Tatva Motors, India. "
        "Product: Vecta Lighting Assembly. Upstream supplier: ancillary lighting manufacturer. "
        "Each month: receive a production despatch target and place a Lighting Assembly order.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        'Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}'
    ),
    "Ancillary": (
        "You are a supply chain ordering agent for a lighting manufacturer in India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly orders). "
        "Upstream supplier: LED component manufacturer. "
        "Each month: receive a Lighting Assembly order and place an LED component order.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        'Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}'
    ),
    "Component": (
        "You are a supply chain ordering agent for an LED component manufacturer in India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies. "
        "Each month: receive a component order and set production capacity.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        'Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}'
    ),
}

# ---------------------------------------------------------------------------
# Hybrid system prompts — multiplier-based parameterisation
# ---------------------------------------------------------------------------

_HYBRID_JSON_FORMAT = (
    'Required format: {"safety_stock_multiplier": <float between 0.5 and 3.0>, '
    '"rationale": "<one sentence explaining your reasoning>"}'
)

HYBRID_BLIND_SYSTEM_PROMPT = (
    "You are a supply chain parameter adjustment agent.\n"
    "Your job is to set the safety stock multiplier for an automated ordering system.\n"
    "The system uses exponential smoothing (alpha=0.30) plus a safety stock buffer.\n"
    "You control only the safety stock multiplier — the ordering arithmetic is handled automatically.\n"
    "Set multiplier = 1.0 to keep the default safety stock. "
    "Set it higher (up to 3.0) to build more buffer, lower (down to 0.5) to reduce buffer.\n"
    "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
    + _HYBRID_JSON_FORMAT
)

HYBRID_CONTEXT_SYSTEM_PROMPTS = {
    "OEM": (
        "You are a supply chain planning agent for Tatva Motors, India. "
        "Product: Vecta Lighting Assembly. Upstream supplier: ancillary lighting manufacturer.\n"
        "Each month: review inventory state and calendar context, then set a safety stock multiplier "
        "for the automated ordering system. "
        "The system uses exponential smoothing (alpha=0.30) plus your multiplier × base safety stock.\n"
        "Set multiplier = 1.0 to keep the default safety stock. "
        "Set it higher (up to 3.0) before festive seasons or demand surges, "
        "lower (down to 0.5) during expected demand dips.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        + _HYBRID_JSON_FORMAT
    ),
    "Ancillary": (
        "You are a supply chain planning agent for a lighting manufacturer in India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly). Upstream supplier: LED component manufacturer.\n"
        "Each month: review inventory state and calendar context, then set a safety stock multiplier "
        "for the automated ordering system. "
        "The system uses exponential smoothing (alpha=0.30) plus your multiplier × base safety stock.\n"
        "Set multiplier = 1.0 to keep the default safety stock. "
        "Set it higher (up to 3.0) before festive seasons or demand surges, "
        "lower (down to 0.5) during expected demand dips.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        + _HYBRID_JSON_FORMAT
    ),
    "Component": (
        "You are a supply chain planning agent for an LED component manufacturer in India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies.\n"
        "Each month: review inventory state and calendar context, then set a safety stock multiplier "
        "for the automated ordering system. "
        "The system uses exponential smoothing (alpha=0.30) plus your multiplier × base safety stock.\n"
        "Set multiplier = 1.0 to keep the default safety stock. "
        "Set it higher (up to 3.0) before festive seasons or demand surges, "
        "lower (down to 0.5) during expected demand dips.\n"
        "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
        + _HYBRID_JSON_FORMAT
    ),
}

# Stateful variants add one sentence about order history
HYBRID_STATEFUL_SYSTEM_PROMPTS = {
    tier: prompt.replace(
        "Always respond with valid JSON only.",
        "You will also receive your last 3 periods of demand, order, and multiplier history — "
        "use this to detect trends and self-correct if prior orders were mis-calibrated.\n"
        "Always respond with valid JSON only.",
    )
    for tier, prompt in HYBRID_CONTEXT_SYSTEM_PROMPTS.items()
}


# ---------------------------------------------------------------------------
# Legacy prompt builder (V2 autonomous ordering)
# ---------------------------------------------------------------------------

def build_user_prompt(
    tier: str,
    condition: str,
    period: int,
    calendar_month: str,
    demand_received: int,
    on_hand: int,
    backlog: int,
    inventory_position: int,
) -> str:
    """Builds the V2-style user prompt for autonomous order-quantity decisions."""
    lines = []
    if condition == "context":
        lines.append(f"Current month: {calendar_month}")
    lines += [
        f"Demand received this period: {demand_received:,} units",
        f"On-hand inventory (post-fulfilment): {on_hand:,} units",
        f"Backlog (unfulfilled, carried forward): {backlog:,} units",
        f"Inventory position (on_hand - backlog): {inventory_position:,} units",
        "",
        "How many units do you order from your upstream supplier this period?",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hybrid prompt builder
# ---------------------------------------------------------------------------

def build_hybrid_user_prompt(
    tier: str,
    hybrid_condition: str,
    period: int,
    calendar_month: str,
    demand_received: int,
    on_hand: int,
    backlog: int,
    inventory_position: int,
    base_ss: int,
    history: list[dict] | None = None,
) -> str:
    """
    Build the user-turn message for hybrid LLM parameterisation calls.

    The formula is shown explicitly so the LLM can reason about the effect
    of its multiplier choice without needing to guess the ordering mechanism.

    H-Blind:    no calendar month, no history
    H-Context:  calendar month prepended
    H-Stateful: calendar month + last N periods of (demand, order, ss_multiplier)
    """
    lines = []

    # Context and stateful both include the calendar month
    if hybrid_condition in ("context", "stateful"):
        lines.append(f"Current month: {calendar_month}")
        lines.append("")

    lines += [
        "Current inventory state:",
        f"  Demand received this period: {demand_received:,} units",
        f"  On-hand inventory (post-fulfilment): {on_hand:,} units",
        f"  Backlog (unfulfilled, carried forward): {backlog:,} units",
        f"  Inventory position (on_hand - backlog): {inventory_position:,} units",
        f"  Base safety stock: {base_ss:,} units",
    ]

    # Stateful: include order history with outcome feedback so the agent can
    # assess whether its prior multiplier choice was adequate.
    if hybrid_condition == "stateful" and history:
        lines.append("")
        lines.append(f"Order history (last {len(history)} period(s)):")
        for h in history:
            mult_str = f", ss_multiplier={h['ss_multiplier']:.2f}" if h.get("ss_multiplier") is not None else ""
            backlog_str = f", backlog={h['backlog']:,}" if "backlog" in h else ""
            stockout_str = " [STOCKOUT]" if h.get("stockout") else ""
            lines.append(
                f"  Period {h['period']} ({_period_to_month(h['period'], period, calendar_month)}): "
                f"demand={h['demand']:,}, order_placed={h['order']:,}"
                f"{mult_str}{backlog_str}{stockout_str}"
            )

    lines += [
        "",
        f"The ordering system formula:",
        f"  target_position = exp_smoothing_forecast + {base_ss:,} × safety_stock_multiplier",
        f"  order = max(0, target_position - inventory_position)",
        f"  (inventory_position = on_hand - backlog = {inventory_position:,} this period)",
        "Set safety_stock_multiplier = 1.0 to keep the default safety stock.",
        "Higher multiplier → higher target → more units ordered (builds buffer).",
        "Lower multiplier → lower target → fewer units ordered (reduces buffer).",
        "Range: [0.5, 3.0]. Values outside this range will be clamped.",
        "",
        "What safety_stock_multiplier do you set for this period?",
    ]
    return "\n".join(lines)


def _period_to_month(hist_period: int, current_period: int, current_month: str) -> str:
    """
    Approximate the calendar month label for a history entry.

    We know the current period's calendar_month (e.g. "Nov 2025") and the
    history entry's period number. We count backwards by the period difference
    to get an approximate month label for display purposes only — accuracy to
    within ±1 month is sufficient for the agent's self-correction reasoning.
    """
    from datetime import date
    import calendar as _cal

    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    try:
        month_abbr = current_month[:3]
        year = int(current_month.strip()[-4:])
        m_idx = months.index(month_abbr)   # 0-indexed
        delta = current_period - hist_period
        total_months = m_idx - delta
        year_adj = total_months // 12
        m_final = total_months % 12
        if m_final < 0:
            m_final += 12
            year_adj -= 1
        return f"{months[m_final]} {year + year_adj}"
    except Exception:
        return f"period {hist_period}"


# ---------------------------------------------------------------------------
# System prompt selectors
# ---------------------------------------------------------------------------

def get_system_prompt(tier: str, condition: str) -> str:
    """Returns V2-style system prompt for autonomous order decisions."""
    if condition == "blind":
        return BLIND_SYSTEM_PROMPT
    return CONTEXT_SYSTEM_PROMPTS[tier]


def get_hybrid_system_prompt(tier: str, hybrid_condition: str) -> str:
    """Returns the hybrid system prompt for safety stock multiplier decisions."""
    if hybrid_condition == "blind":
        return HYBRID_BLIND_SYSTEM_PROMPT
    elif hybrid_condition == "context":
        return HYBRID_CONTEXT_SYSTEM_PROMPTS[tier]
    elif hybrid_condition == "stateful":
        return HYBRID_STATEFUL_SYSTEM_PROMPTS[tier]
    else:
        raise ValueError(f"Unknown hybrid_condition: {hybrid_condition!r}")


# ---------------------------------------------------------------------------
# Backend loader
# ---------------------------------------------------------------------------

def _load_backend():
    """
    Load the correct backend module based on BACKEND env var.
    DRY_RUN=1 overrides all other settings and uses the dry_run backend.
    """
    if os.environ.get("DRY_RUN", "").strip() == "1":
        return importlib.import_module("backends.dry_run_backend")
    backend = os.environ.get("BACKEND", "azure").lower()
    if backend == "azure":
        return importlib.import_module("backends.azure_backend")
    elif backend == "local":
        return importlib.import_module("backends.local_backend")
    else:
        raise ValueError(f"Unknown BACKEND='{backend}'. Set to 'azure' or 'local'.")


# ---------------------------------------------------------------------------
# Public interfaces
# ---------------------------------------------------------------------------

def get_order_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """
    Legacy V2 interface: ask LLM for order quantity.
    Returns {"order_quantity": int, "rationale": str, ...telemetry}.
    """
    backend = _load_backend()
    return backend.get_order_decision(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_tier=model_tier,
        run_id=run_id,
        period=period,
        tier=tier,
        model_name=model_name,
        temperature=temperature,
    )


def get_ss_multiplier(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """
    Hybrid interface: ask LLM for a safety stock multiplier.

    Returns {"safety_stock_multiplier": float, "rationale": str, ...telemetry}.

    The backend's get_order_decision() is reused with the hybrid prompt. The
    backend returns whatever JSON the LLM produces; simulation.py extracts the
    "safety_stock_multiplier" key and applies clamping and fallback logic.

    The backend does NOT validate the multiplier — that is the simulation's job.
    This keeps the backend generic (it just calls the LLM and returns parsed JSON)
    and puts the domain-specific validation where it belongs (simulation logic).

    Note: if a model accidentally returns "order_quantity" instead of
    "safety_stock_multiplier" (using the old V2 format), the simulation.py
    fallback will catch the missing key and substitute 1.0 with a warning.
    """
    backend = _load_backend()
    # Backends implement get_order_decision() with a generic dict return.
    # We call it with the hybrid prompt — the LLM should return the
    # safety_stock_multiplier key as instructed by the system prompt.
    # The function is aliased as get_ss_multiplier in the backend interface
    # if the backend supports it; otherwise we reuse get_order_decision.
    if hasattr(backend, "get_ss_multiplier"):
        return backend.get_ss_multiplier(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_tier=model_tier,
            run_id=run_id,
            period=period,
            tier=tier,
            model_name=model_name,
            temperature=temperature,
        )
    # Fallback: backends that don't implement get_ss_multiplier natively
    # reuse get_order_decision — the LLM response contains safety_stock_multiplier
    # because of the hybrid system prompt, not order_quantity.
    return backend.get_order_decision(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_tier=model_tier,
        run_id=run_id,
        period=period,
        tier=tier,
        model_name=model_name,
        temperature=temperature,
    )
