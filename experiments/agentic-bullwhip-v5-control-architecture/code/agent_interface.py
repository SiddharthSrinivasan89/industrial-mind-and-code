"""
Agent interface for V4 WorldEvents.

Combines V3's five prompt conditions
(blind / blind_neutral / context / context_neutral / unstructured) with
V4's intent classification output interface (5 discrete labels → lookup table).

Public interface used by simulation.py
---------------------------------------
  INTENT_CLASSES         : list of valid intent strings
  INTENT_MULTIPLIER_MAP  : label → safety stock multiplier

  get_intent_system_prompt(tier, condition) → str
  build_intent_user_prompt(...)             → str
  get_intent_class(...)                     → dict

The simulation never calls backends directly. All LLM routing is done here.
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

# Multiplier applied to base_ss in the OUT-style formula.
# Calibrated from V3b observed multiplier distributions (median per demand band)
# and adjusted for world event magnitudes.
# NEUTRAL is fixed at 1.00 (no-op baseline; no calibration needed).
INTENT_MULTIPLIER_MAP: dict[str, float] = {
    "STRONG_INCREASE":   1.30,
    "MODERATE_INCREASE": 1.15,
    "NEUTRAL":           1.00,
    "MODERATE_DECREASE": 0.90,
    "STRONG_DECREASE":   0.80,
}

_INTENT_SET = frozenset(INTENT_CLASSES)

_INTENT_LOOKUP_BLOCK = (
    "  STRONG_INCREASE   → safety stock ×1.30  "
    "(major demand elevation — FY-end peak, Diwali, demand surge)\n"
    "  MODERATE_INCREASE → safety stock ×1.15  "
    "(mild demand elevation — Navratri/Dasara, pre-festive build)\n"
    "  NEUTRAL           → safety stock ×1.00  "
    "(no material seasonal or disruption signal)\n"
    "  MODERATE_DECREASE → safety stock ×0.90  "
    "(mild demand dip — early/late monsoon, post-festive slowdown)\n"
    "  STRONG_DECREASE   → safety stock ×0.80  "
    "(major demand collapse — peak monsoon, pandemic shock, demand freeze)"
)

_JSON_INSTRUCTION = (
    "Always respond with valid JSON only. No text before or after.\n"
    'Required format: {"intent": "<CLASS>", "rationale": "<one sentence explaining your classification>"}'
)

_NEUTRAL_BIAS_INSTRUCTION = (
    "Default to NEUTRAL unless the signal is strong and unambiguous. "
    "Only choose INCREASE or DECREASE when the evidence is clear — "
    "a major seasonal event, a world disruption, or significant inventory stress. "
    "When in doubt, classify NEUTRAL."
)

# ---------------------------------------------------------------------------
# System prompts — blind condition (same for all tiers)
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
# System prompts — context condition (tier-specific persona + seasonal guidance)
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
        "  Early/late monsoon (May/Aug): mild dip → MODERATE_DECREASE\n"
        "  World events (conflict, pandemic, port disruption): adjust based on signal\n\n"
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
        "seasonal patterns with a one-period lag. World events can disrupt both demand "
        "and your upstream fill rate simultaneously.\n\n"
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
        "your incoming orders can swing more than retail demand. World events affecting "
        "logistics (port disruptions, conflict) can restrict your outbound fill rate.\n\n"
        + _JSON_INSTRUCTION
    ),
}

# ---------------------------------------------------------------------------
# Neutral-prior prompt variants — E4_IC sub-experiment
# ---------------------------------------------------------------------------
# Identical to blind/context prompts with one instruction added: default to
# NEUTRAL unless the signal is strong and unambiguous.

INTENT_BLIND_NEUTRAL_SYSTEM_PROMPT = (
    "You are a supply chain buffer classification agent.\n\n"
    "Each period you receive inventory state variables. Classify the current demand "
    "outlook into one of five categories. A deterministic formula converts your "
    "classification to a precise order quantity — you do not compute the order.\n\n"
    "Classification options (choose exactly one):\n"
    + _INTENT_LOOKUP_BLOCK + "\n\n"
    + _NEUTRAL_BIAS_INSTRUCTION + "\n\n"
    + _JSON_INSTRUCTION
)

INTENT_CONTEXT_NEUTRAL_SYSTEM_PROMPTS: dict[str, str] = {
    tier: prompt.replace(_JSON_INSTRUCTION,
                         _NEUTRAL_BIAS_INSTRUCTION + "\n\n" + _JSON_INSTRUCTION)
    for tier, prompt in INTENT_CONTEXT_SYSTEM_PROMPTS.items()
}

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def get_intent_system_prompt(tier: str, condition: str) -> str:
    """Return the correct system prompt for this tier and condition."""
    if condition == "blind":
        return INTENT_BLIND_SYSTEM_PROMPT
    if condition == "blind_neutral":
        return INTENT_BLIND_NEUTRAL_SYSTEM_PROMPT
    if condition == "context_neutral":
        return INTENT_CONTEXT_NEUTRAL_SYSTEM_PROMPTS[tier]
    if condition in ("context", "unstructured"):
        return INTENT_CONTEXT_SYSTEM_PROMPTS[tier]
    raise ValueError(
        f"Unknown condition '{condition}' — expected one of: "
        "blind, blind_neutral, context, context_neutral, unstructured"
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
    event_signal: str | None = None,
) -> str:
    """
    Build the per-period user prompt for intent classification.

    Conditions:
      blind        — state variables only; no calendar, no event signal
      context      — calendar month added; no event signal
      unstructured — calendar month + world event news headline when active

    The base safety stock (base_ss) is shown so the agent understands the
    scale of the classification consequence (multiplier × base_ss = SS_t).
    """
    lines = []

    if condition in ("context", "context_neutral", "unstructured"):
        lines.append(f"Current month: {calendar_month}")

    if condition == "unstructured" and event_signal:
        lines.append(f"Current conditions: [{event_signal}]")

    lines += [
        f"Demand received this period: {demand_received:,} units",
        f"On-hand inventory (post-fulfilment): {on_hand:,} units",
        f"Backlog (unfulfilled, carried forward): {backlog:,} units",
        f"Inventory position (on_hand + on_order - backlog): {inventory_position:,} units",
        f"Base safety stock: {base_ss:,} units",
        "",
        "Classify the demand outlook for this period.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backend loader
# ---------------------------------------------------------------------------

def _load_backend():
    """
    Load the active backend from the BACKEND env var.
    DRY_RUN=1 bypasses real backends for pipeline validation.
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
    event_signal: str | None,
    model_tier: str,
    run_id: str,
    model_name: str | None,
    temperature: float | None,
) -> dict:
    """
    Ask the LLM for an intent classification and return a result dict.

    On RuntimeError from the backend (all 3 parse attempts failed or invalid
    intent string), falls back to NEUTRAL and logs intent_fallback=True.
    This prevents a single classification failure from invalidating the run.

    Returns
    -------
    dict with keys:
      intent_class      (str)   — one of INTENT_CLASSES or "NEUTRAL" on fallback
      rationale         (str)
      intent_fallback   (bool)  — True if NEUTRAL was forced after parse failure
      attempt_number    (int)
      latency_ms        (float)
      ttft_ms           (float)
      prompt_tokens     (int)
      completion_tokens (int)
      generation_tps    (float)
    """
    backend = _load_backend()

    system_prompt = get_intent_system_prompt(tier, condition)
    user_prompt   = build_intent_user_prompt(
        tier=tier,
        condition=condition,
        period=period,
        calendar_month=calendar_month,
        demand_received=demand_received,
        on_hand=on_hand,
        backlog=backlog,
        inventory_position=inventory_position,
        base_ss=base_ss,
        event_signal=event_signal,
    )

    try:
        result = backend.get_intent_decision(
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
            "intent_class":    result["intent"],
            "rationale":       result.get("rationale", ""),
            "intent_fallback": False,
            "attempt_number":  result.get("attempt_number", 1),
            "latency_ms":      result.get("latency_ms", 0.0),
            "ttft_ms":         result.get("ttft_ms", 0.0),
            "prompt_tokens":   result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "generation_tps":  result.get("generation_tps", 0.0),
        }

    except RuntimeError as exc:
        logger.warning(
            "run=%s period=%d tier=%s intent parse failed — defaulting to NEUTRAL. Error: %s",
            run_id, period, tier, exc,
        )
        return {
            "intent_class":    "NEUTRAL",
            "rationale":       "",
            "intent_fallback": True,
            "attempt_number":  3,
            "latency_ms":      0.0,
            "ttft_ms":         0.0,
            "prompt_tokens":   0,
            "completion_tokens": 0,
            "generation_tps":  0.0,
        }
