"""
Agent interface — the only module simulation.py talks to for LLM decisions.

Responsibilities:
  1. Hold all system prompts (blind and context variants per tier)
  2. Build the per-period user prompt from simulation state variables
  3. Load the correct backend (azure or local) from the BACKEND env var
  4. Expose a single get_order_decision() function that simulation.py calls

Simulation code never imports backends directly. Swapping backends is done
entirely by changing the BACKEND env var — no code changes required.
"""

import os
import importlib

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
# The blind prompt is the same for all three tiers — no identity, no calendar.
# This is the minimal deployment baseline: the agent knows nothing about who
# it is or what time of year it is. Only raw numbers arrive each period.

BLIND_SYSTEM_PROMPT = (
    "You are a supply chain ordering agent.\n"
    "Always respond with valid JSON only. No additional text before or after the JSON object.\n"
    'Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}'
)

# Context prompts are different per tier — each has a named company, a product,
# and a role. The calendar month is added to the user prompt (not here) so the
# agent can use its own world knowledge about seasonal demand patterns.
# The agent is never told what patterns exist — that must come from itself.

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
# Prompt builders
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
    event_signal: str | None = None,
) -> str:
    """
    Builds the user-turn message sent to the agent each period.

    The four state variables are the same for both blind and context conditions
    so that the information set is identical — the only difference is whether
    the calendar month is included.

    context condition: calendar month is included so the agent can reason about
    seasonal demand using its own world knowledge (e.g. "November = Diwali").

    blind condition: no calendar month. The agent sees only numbers. Any
    seasonal adjustment it makes must be from the numbers alone.
    """
    lines = []

    # Context / unstructured conditions include the calendar month.
    # Blind condition deliberately omits it — that is the experimental treatment.
    if condition in ("context", "unstructured"):
        lines.append(f"Current month: {calendar_month}")

    # Unstructured condition only: include the world event news headline.
    # This is the V3 addition — tests whether explicit disruption signals change ordering.
    if condition == "unstructured" and event_signal:
        lines.append(f"Current conditions: [{event_signal}]")

    lines += [
        f"Demand received this period: {demand_received:,} units",
        f"On-hand inventory (post-fulfilment): {on_hand:,} units",
        f"Backlog (unfulfilled, carried forward): {backlog:,} units",
        f"Inventory position (on_hand - backlog): {inventory_position:,} units",
        "",
        "How many units do you order from your upstream supplier this period?",
    ]
    return "\n".join(lines)


def get_system_prompt(tier: str, condition: str) -> str:
    """Returns the correct system prompt for this tier and condition."""
    if condition == "blind":
        return BLIND_SYSTEM_PROMPT      # same for all tiers in blind condition
    return CONTEXT_SYSTEM_PROMPTS[tier] # tier-specific persona in context condition


# ---------------------------------------------------------------------------
# Backend loader
# ---------------------------------------------------------------------------

def _load_backend():
    """
    Reads the BACKEND env var and imports the matching backend module.
    Using importlib (rather than a top-level import) means neither backend
    is imported unless it is actually needed, so you can run local experiments
    without having the azure SDK installed, and vice versa.

    DRY_RUN=1 short-circuits everything: the dry_run backend is loaded regardless
    of BACKEND, and returns deterministic orders (demand pass-through) with no
    API calls. Use this to sanity-check simulation + metrics logic without spend.
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
# Public interface — this is the only function simulation.py calls
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
    Ask the LLM for an order decision and return {"order_quantity": int, "rationale": str}.

    model_tier  : "lightweight" — uses MODEL_LIGHTWEIGHT from env (e.g. gpt-4.1-mini)
                  "reasoning"   — uses MODEL_REASONING from env (e.g. o4-mini)

    model_name  : Optional hard override. If provided, backends ignore the env var
                  and use this model name directly. Used for E4 OSS conditions so
                  Phi-4-reasoning-plus is used instead of the proprietary MODEL_REASONING.

    temperature : Explicit temperature override. Resolved by run_experiment.py based on
                  condition + model_tier (lightweight=0.4 all conditions,
                  reasoning blind=0.0, reasoning context/unstructured=0.3).
                  Falls back to env var if not provided.

    run_id, period, tier: passed through to backends for log messages only.

    Raises RuntimeError if all 3 parse attempts fail — caller (run_condition)
    marks the run invalid and immediately starts a replacement run.
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
