"""
Agent interface — V4 Intent Classifier (25-month V3b demand series).

Three prompt conditions:
  blind    — state variables only; no calendar month
  context  — calendar month + tier persona
  stateful — context + last 3 periods of (demand, order, intent, backlog, stockout)

Public interface used by simulation.py
---------------------------------------
  INTENT_CLASSES         : list of valid intent strings
  INTENT_MULTIPLIER_MAP  : label → safety stock multiplier

  get_intent_system_prompt(tier, condition) → str
  build_intent_user_prompt(...)             → str
  get_intent_class(...)                     → dict
"""

import importlib
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent classification constants — single source of truth
# ---------------------------------------------------------------------------

INTENT_CLASSES = [
    "STRONG_INCREASE",
    "MODERATE_INCREASE",
    "NEUTRAL",
    "MODERATE_DECREASE",
    "STRONG_DECREASE",
]

# Initial design values (V4_IC design doc §3.2).
# Calibration from V3b multiplier medians is deferred — initial values used.
INTENT_MULTIPLIER_MAP: dict[str, float] = {
    "STRONG_INCREASE":   2.50,
    "MODERATE_INCREASE": 1.50,
    "NEUTRAL":           1.00,
    "MODERATE_DECREASE": 0.75,
    "STRONG_DECREASE":   0.50,
}

_INTENT_SET = frozenset(INTENT_CLASSES)

_INTENT_LOOKUP_BLOCK = (
    "  STRONG_INCREASE   → safety stock ×2.50  "
    "(major demand elevation — FY-end peak, Diwali)\n"
    "  MODERATE_INCREASE → safety stock ×1.50  "
    "(mild demand elevation — Navratri/Dasara, pre-festive build)\n"
    "  NEUTRAL           → safety stock ×1.00  "
    "(no material seasonal signal)\n"
    "  MODERATE_DECREASE → safety stock ×0.75  "
    "(mild demand dip — early/late monsoon, post-festive slowdown)\n"
    "  STRONG_DECREASE   → safety stock ×0.50  "
    "(major demand collapse — peak monsoon)"
)

_JSON_INSTRUCTION = (
    "Always respond with valid JSON only. No text before or after.\n"
    'Required format: {"intent": "<CLASS>", "rationale": "<one sentence explaining your classification>"}'
)

# ---------------------------------------------------------------------------
# System prompts — blind condition
# ---------------------------------------------------------------------------

INTENT_BLIND_SYSTEM_PROMPT = (
    "You are a supply chain buffer classification agent.\n\n"
    "Each period you receive inventory state variables. Classify the current demand "
    "outlook into one of five categories. A deterministic formula converts your "
    "classification to a precise order quantity — you do not compute the order.\n\n"
    "Classification options (choose exactly one):\n"
    + _INTENT_LOOKUP_BLOCK + "\n\n"
    + _JSON_INSTRUCTION
)

# ---------------------------------------------------------------------------
# System prompts — context condition (tier-specific, with seasonal guidance)
# ---------------------------------------------------------------------------

INTENT_CONTEXT_SYSTEM_PROMPTS: dict[str, str] = {
    "OEM": (
        "You are the inventory manager for Tatva Motors (Vecta Lighting Assembly, India). "
        "Your upstream supplier is an ancillary lighting manufacturer.\n\n"
        "Each period you receive the current calendar month and inventory state. "
        "Classify demand outlook using your knowledge of Indian automotive seasonal patterns. "
        "A deterministic formula executes the actual order — you only classify intent.\n\n"
        "Classification options (choose exactly one):\n"
        + _INTENT_LOOKUP_BLOCK + "\n\n"
        "Indian automotive demand drivers to consider:\n"
        "  FY-end (Mar): fleet budget flush → STRONG_INCREASE\n"
        "  Diwali (Nov): largest festive peak → STRONG_INCREASE\n"
        "  Navratri/Dasara (Oct): pre-Diwali festive → MODERATE_INCREASE\n"
        "  Peak monsoon (Jun–Jul): lowest demand → STRONG_DECREASE\n"
        "  Early/late monsoon (May/Aug): mild dip → MODERATE_DECREASE\n\n"
        + _JSON_INSTRUCTION
    ),
    "Ancillary": (
        "You are the inventory manager for a lighting manufacturer in India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly). "
        "Upstream supplier: LED component manufacturer.\n\n"
        "Each period you receive the current calendar month and your inventory state. "
        "Classify demand outlook for LED components using your knowledge of Indian automotive "
        "seasonal patterns. A deterministic formula executes the actual order.\n\n"
        "Classification options (choose exactly one):\n"
        + _INTENT_LOOKUP_BLOCK + "\n\n"
        "Note: your demand comes from Tatva Motors orders, which track Indian auto retail "
        "seasonal patterns with a one-period lag.\n\n"
        + _JSON_INSTRUCTION
    ),
    "Component": (
        "You are the inventory manager for an LED component manufacturer in India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies.\n\n"
        "Each period you receive the current calendar month and your inventory state. "
        "Classify demand outlook for LED components. A deterministic formula sets your "
        "production batch — you only classify intent.\n\n"
        "Classification options (choose exactly one):\n"
        + _INTENT_LOOKUP_BLOCK + "\n\n"
        "Note: you are two tiers upstream of retail demand. Bullwhip amplification means "
        "your incoming orders can swing more than retail demand.\n\n"
        + _JSON_INSTRUCTION
    ),
}

# Stateful variants: same as context but add history instruction
INTENT_STATEFUL_SYSTEM_PROMPTS: dict[str, str] = {
    tier: prompt.replace(
        "Always respond with valid JSON only.",
        "You will also receive your last 3 periods of demand, order, intent, and outcome history — "
        "use this to self-correct if prior intent choices led to stockouts or excessive inventory.\n"
        "Always respond with valid JSON only.",
    )
    for tier, prompt in INTENT_CONTEXT_SYSTEM_PROMPTS.items()
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def get_intent_system_prompt(tier: str, condition: str) -> str:
    """Return the correct system prompt for this tier and condition."""
    if condition == "blind":
        return INTENT_BLIND_SYSTEM_PROMPT
    if condition in ("context", "stateful"):
        if condition == "stateful":
            return INTENT_STATEFUL_SYSTEM_PROMPTS[tier]
        return INTENT_CONTEXT_SYSTEM_PROMPTS[tier]
    raise ValueError(
        f"Unknown condition '{condition}' — expected one of: blind, context, stateful"
    )


def build_intent_user_prompt(
    tier: str,
    condition: str,
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
    Build the per-period user prompt for intent classification.

    blind    — state variables only
    context  — calendar month prepended
    stateful — calendar month + last N periods of (demand, order, intent, backlog, stockout)
    """
    lines = []

    if condition in ("context", "stateful"):
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

    if condition == "stateful" and history:
        lines.append("")
        lines.append(f"Order history (last {len(history)} period(s)):")
        for h in history:
            stockout_str = " [STOCKOUT]" if h.get("stockout") else ""
            lines.append(
                f"  Period {h['period']} ({_period_to_month(h['period'], period, calendar_month)}): "
                f"demand={h['demand']:,}, order_placed={h['order']:,}, "
                f"intent={h['intent']}, backlog={h.get('backlog', 0):,}"
                f"{stockout_str}"
            )

    lines += [
        "",
        "Classify the demand outlook for this period.",
    ]
    return "\n".join(lines)


def _period_to_month(hist_period: int, current_period: int, current_month: str) -> str:
    """Approximate calendar month label for a history entry (display only)."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        month_abbr = current_month[:3]
        year = int(current_month.strip()[-4:])
        m_idx = months.index(month_abbr)
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
# Backend loader
# ---------------------------------------------------------------------------

def _load_backend(backend: str | None = None):
    """
    Load the correct backend module.

    Priority: DRY_RUN=1 > explicit backend arg > BACKEND env var.
    """
    if os.environ.get("DRY_RUN", "").strip() == "1":
        return importlib.import_module("backends.dry_run_backend")
    resolved = (backend or os.environ.get("BACKEND", "azure")).lower()
    if resolved == "azure":
        return importlib.import_module("backends.azure_backend")
    else:
        raise ValueError(f"Unknown backend='{resolved}'. Must be 'azure'.")


# ---------------------------------------------------------------------------
# Public function — called by simulation.py
# ---------------------------------------------------------------------------

def get_intent_class(
    tier: str,
    condition: str,
    period: int,
    calendar_month: str,
    demand_received: int,
    on_hand: int,
    backlog: int,
    inventory_position: int,
    base_ss: int,
    model_tier: str,
    run_id: str,
    model_name: str | None = None,
    temperature: float | None = None,
    history: list[dict] | None = None,
    backend: str | None = None,
) -> dict:
    """
    Ask the LLM for an intent classification. Falls back to NEUTRAL on parse failure.

    Returns dict with keys:
      intent_class, rationale, intent_fallback, attempt_number,
      latency_ms, ttft_ms, prompt_tokens, completion_tokens, generation_tps
    """
    _backend = _load_backend(backend)

    system_prompt = get_intent_system_prompt(tier, condition)
    user_prompt = build_intent_user_prompt(
        tier=tier,
        condition=condition,
        period=period,
        calendar_month=calendar_month,
        demand_received=demand_received,
        on_hand=on_hand,
        backlog=backlog,
        inventory_position=inventory_position,
        base_ss=base_ss,
        history=history,
    )

    try:
        result = _backend.get_intent_decision(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_tier=model_tier,
            run_id=run_id,
            period=period,
            tier=tier,
            model_name=model_name,
            temperature=temperature,
        )
        return {
            "intent_class":      result["intent"],
            "rationale":         result.get("rationale", ""),
            "intent_fallback":   False,
            "attempt_number":    result.get("attempt_number", 1),
            "latency_ms":        result.get("latency_ms", 0.0),
            "ttft_ms":           result.get("ttft_ms", 0.0),
            "prompt_tokens":     result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "generation_tps":    result.get("generation_tps", 0.0),
        }

    except RuntimeError as exc:
        logger.warning(
            "run=%s period=%d tier=%s intent parse failed — defaulting to NEUTRAL. Error: %s",
            run_id, period, tier, exc,
        )
        return {
            "intent_class":      "NEUTRAL",
            "rationale":         "",
            "intent_fallback":   True,
            "attempt_number":    3,
            "latency_ms":        0.0,
            "ttft_ms":           0.0,
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "generation_tps":    0.0,
        }
