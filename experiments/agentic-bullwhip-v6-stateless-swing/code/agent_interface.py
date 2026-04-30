"""
Agent interface — V6 StatelessSwing (25-month V3b demand series).

Three prompt conditions:
  blind    — demand history + forecast only; no calendar month
  context  — calendar month + tier persona
  stateful — context + last 3 periods of (demand, alpha_chosen, forecast_error, backlog, stockout)

Public interface used by simulation.py
---------------------------------------
  ALPHA_VALUES        : list of valid alpha floats
  ALPHA_FALLBACK      : fallback alpha on parse failure (0.3)

  get_alpha_system_prompt(tier, condition) → str
  build_alpha_user_prompt(...)             → str
  get_alpha_value(...)                     → dict
"""

import importlib
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alpha selection constants — single source of truth
# ---------------------------------------------------------------------------

ALPHA_VALUES   = [0.1, 0.3, 0.5, 0.7]
ALPHA_FALLBACK = 0.3   # V2-validated optimal for this demand series

_ALPHA_SET = frozenset(ALPHA_VALUES)

_ALPHA_CHOICE_BLOCK = (
    "  0.1 → heavy smoothing  (stable demand, ignore recent spikes)\n"
    "  0.3 → moderate smoothing (near-optimal for most conditions)\n"
    "  0.5 → responsive smoothing (demand trending or accelerating)\n"
    "  0.7 → highly reactive (major demand shift in progress)"
)

_JSON_INSTRUCTION = (
    "Always respond with valid JSON only. No text before or after.\n"
    'Required format: {"alpha": <0.1|0.3|0.5|0.7>, "rationale": "<one sentence>"}'
)

# ---------------------------------------------------------------------------
# System prompts — blind condition
# ---------------------------------------------------------------------------

ALPHA_BLIND_SYSTEM_PROMPT = (
    "You are a supply chain smoothing parameter agent.\n\n"
    "Each period you receive recent demand history and the current exponential-smoothing "
    "forecast. Choose the smoothing coefficient α that best fits current demand dynamics. "
    "Higher α reacts faster to recent demand; lower α produces a more stable forecast.\n\n"
    "Choices (select exactly one):\n"
    + _ALPHA_CHOICE_BLOCK + "\n\n"
    + _JSON_INSTRUCTION
)

# ---------------------------------------------------------------------------
# System prompts — context condition (tier-specific, with seasonal guidance)
# ---------------------------------------------------------------------------

ALPHA_CONTEXT_SYSTEM_PROMPTS: dict[str, str] = {
    "OEM": (
        "You are the inventory manager for Tatva Motors (Vecta Lighting Assembly, India). "
        "Your upstream supplier is an ancillary lighting manufacturer.\n\n"
        "Each period you receive the current calendar month and recent demand history. "
        "Choose the exponential-smoothing coefficient α for your order forecast. "
        "Higher α reacts faster to recent demand; lower α is more stable.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Indian automotive demand context:\n"
        "  FY-end (Mar), Diwali (Nov): peak demand — consider higher α to track surge\n"
        "  Peak monsoon (Jun–Jul): demand trough — consider lower α to avoid over-reaction\n"
        "  Transition months: moderate — 0.3 is usually optimal\n\n"
        + _JSON_INSTRUCTION
    ),
    "Ancillary": (
        "You are the inventory manager for a lighting manufacturer in India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly). "
        "Upstream supplier: LED component manufacturer.\n\n"
        "Each period you receive the current calendar month and recent order history. "
        "Choose the exponential-smoothing coefficient α for your component order forecast.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Note: your demand comes from Tatva Motors orders, which track Indian auto retail "
        "seasonal patterns with a one-period lag.\n\n"
        + _JSON_INSTRUCTION
    ),
    "Component": (
        "You are the inventory manager for an LED component manufacturer in India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies.\n\n"
        "Each period you receive the current calendar month and recent order history. "
        "Choose the exponential-smoothing coefficient α for your production batch forecast.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Note: you are two tiers upstream of retail demand. Bullwhip amplification means "
        "your incoming orders can swing more than retail demand — lower α is often safer.\n\n"
        + _JSON_INSTRUCTION
    ),
}

# ---------------------------------------------------------------------------
# System prompts — context_debiased condition
# Same tier persona as context but seasonal guidance removed;
# explicit instruction to ignore calendar-based priors.
# Also used as base for context_computed (calendar month replaced with computed signals).
# ---------------------------------------------------------------------------

ALPHA_CONTEXT_DEBIASED_SYSTEM_PROMPTS: dict[str, str] = {
    "OEM": (
        "You are the inventory manager for Tatva Motors (Vecta Lighting Assembly, India). "
        "Your upstream supplier is an ancillary lighting manufacturer.\n\n"
        "Each period you receive the current calendar month and recent demand history. "
        "Choose the exponential-smoothing coefficient α for your order forecast. "
        "Higher α reacts faster to recent demand; lower α is more stable.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Important: ignore any seasonal or calendar-based intuitions from general knowledge. "
        "Base your α decision only on the demand numbers and forecast provided.\n\n"
        + _JSON_INSTRUCTION
    ),
    "Ancillary": (
        "You are the inventory manager for a lighting manufacturer in India. "
        "Customer: Tatva Motors (Vecta Lighting Assembly). "
        "Upstream supplier: LED component manufacturer.\n\n"
        "Each period you receive the current calendar month and recent order history. "
        "Choose the exponential-smoothing coefficient α for your component order forecast.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Important: ignore any seasonal or calendar-based intuitions from general knowledge. "
        "Base your α decision only on the demand numbers and forecast provided.\n\n"
        + _JSON_INSTRUCTION
    ),
    "Component": (
        "You are the inventory manager for an LED component manufacturer in India. "
        "Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies.\n\n"
        "Each period you receive the current calendar month and recent order history. "
        "Choose the exponential-smoothing coefficient α for your production batch forecast.\n\n"
        "Choices (select exactly one):\n"
        + _ALPHA_CHOICE_BLOCK + "\n\n"
        "Important: ignore any seasonal or calendar-based intuitions from general knowledge. "
        "Base your α decision only on the demand numbers and forecast provided.\n\n"
        + _JSON_INSTRUCTION
    ),
}

# Stateful variants: same as context but instruct the agent to use history
ALPHA_STATEFUL_SYSTEM_PROMPTS: dict[str, str] = {
    tier: prompt.replace(
        "Always respond with valid JSON only.",
        "You will also receive your last 3 periods of demand, alpha chosen, forecast error, "
        "and outcome — use this to self-correct if prior choices led to stockouts or excess.\n"
        "Always respond with valid JSON only.",
    )
    for tier, prompt in ALPHA_CONTEXT_SYSTEM_PROMPTS.items()
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def get_alpha_system_prompt(tier: str, condition: str) -> str:
    if condition == "blind":
        return ALPHA_BLIND_SYSTEM_PROMPT
    if condition == "context":
        return ALPHA_CONTEXT_SYSTEM_PROMPTS[tier]
    if condition == "stateful":
        return ALPHA_STATEFUL_SYSTEM_PROMPTS[tier]
    if condition in ("context_debiased", "context_computed"):
        return ALPHA_CONTEXT_DEBIASED_SYSTEM_PROMPTS[tier]
    raise ValueError(
        f"Unknown condition '{condition}' — expected: blind, context, stateful, "
        "context_debiased, context_computed"
    )


def _computed_signals(
    demand_history: list[int],
    forecast_error: float | None,
    period: int,
) -> list[str]:
    """Return computed demand-signal lines for context_computed condition."""
    if len(demand_history) < 3:
        insuf = f"Insufficient history (period {period})"
        lines = [
            f"Demand trend: {insuf}",
            f"Demand vs 5-period mean: {insuf}",
            f"Recent demand CV (volatility): {insuf}",
        ]
    else:
        last = demand_history[-1]
        prior_avg = sum(demand_history[-4:-1]) / 3 if len(demand_history) >= 4 else sum(demand_history[:-1]) / len(demand_history[:-1])
        trend_pct = ((last - prior_avg) / prior_avg * 100) if prior_avg > 0 else 0.0
        if trend_pct > 5:
            direction = f"rising {trend_pct:+.0f}%"
        elif trend_pct < -5:
            direction = f"falling {trend_pct:+.0f}%"
        else:
            direction = "stable"

        mean5 = sum(demand_history[-5:]) / len(demand_history[-5:])
        dev_pct = ((last - mean5) / mean5 * 100) if mean5 > 0 else 0.0
        above_below = "above" if dev_pct >= 0 else "below"

        import statistics
        cv = statistics.stdev(demand_history[-5:]) / mean5 if mean5 > 0 else 0.0

        lines = [
            f"Demand trend (last vs prior 3-period avg): {direction}",
            f"Demand vs 5-period mean: {above_below} by {abs(dev_pct):.0f}%",
            f"Recent demand CV (volatility): {cv:.2f}  [<0.1 stable, >0.3 volatile]",
        ]

    if forecast_error is None:
        fe_line = "Last forecast error: N/A (first period)"
    elif forecast_error > 1:
        fe_line = f"Last forecast error: under-forecast by {round(forecast_error)}"
    elif forecast_error < -1:
        fe_line = f"Last forecast error: over-forecast by {round(abs(forecast_error))}"
    else:
        fe_line = "Last forecast error: near-zero"
    lines.append(fe_line)
    return lines


def build_alpha_user_prompt(
    tier: str,
    condition: str,
    period: int,
    calendar_month: str,
    demand_history: list[int],
    prev_forecast: float,
    forecast_error: float | None,
    history: list[dict] | None = None,
) -> str:
    lines = []

    if condition in ("context", "stateful", "context_debiased"):
        lines.append(f"Current month: {calendar_month}")
        lines.append("")
    elif condition == "context_computed":
        lines.extend(_computed_signals(demand_history, forecast_error, period))
        lines.append("")

    if demand_history:
        lines.append(f"Recent demand (oldest → newest): {', '.join(str(d) for d in demand_history)}")
    else:
        lines.append("Recent demand: No prior demand history available (first period)")

    lines.append(f"Current forecast F_{{t-1}}: {round(prev_forecast, 1)}")

    if condition != "context_computed":
        if forecast_error is None:
            lines.append("Forecast error: N/A (first period)")
        else:
            lines.append(f"Last forecast error (D_{{t-1}} - F_{{t-2}}): {round(forecast_error, 1):+.1f}")

    if condition == "stateful" and history:
        lines.append("")
        lines.append(f"Order history (last {len(history)} period(s)):")
        for h in history:
            stockout_str = " [STOCKOUT]" if h.get("stockout") else ""
            fe = h.get("forecast_error")
            fe_str = f"{round(fe, 1):+.1f}" if fe is not None else "N/A"
            lines.append(
                f"  Period {h['period']}: demand={h['demand']:,}, "
                f"alpha={h['alpha_chosen']}, forecast_error={fe_str}, "
                f"backlog={h.get('backlog', 0):,}{stockout_str}"
            )

    lines += ["", "Choose α for this period."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backend loader
# ---------------------------------------------------------------------------

def _load_backend(backend: str | None = None):
    if os.environ.get("DRY_RUN", "").strip() == "1":
        return importlib.import_module("backends.dry_run_backend")
    resolved = (backend or os.environ.get("BACKEND", "azure")).lower()
    if resolved == "azure":
        return importlib.import_module("backends.azure_backend")
    elif resolved == "local":
        return importlib.import_module("backends.local_backend")
    else:
        raise ValueError(f"Unknown backend='{resolved}'. Must be 'azure' or 'local'.")


# ---------------------------------------------------------------------------
# Public function — called by simulation.py
# ---------------------------------------------------------------------------

def get_alpha_value(
    tier: str,
    condition: str,
    period: int,
    calendar_month: str,
    demand_history: list[int],
    prev_forecast: float,
    forecast_error: float | None,
    model_tier: str,
    run_id: str,
    model_name: str | None = None,
    temperature: float | None = None,
    history: list[dict] | None = None,
    backend: str | None = None,
) -> dict:
    """
    Ask the LLM to choose α ∈ {0.1, 0.3, 0.5, 0.7}. Falls back to ALPHA_FALLBACK on failure.

    Returns dict with keys:
      alpha, rationale, alpha_fallback, attempt_number,
      latency_ms, ttft_ms, prompt_tokens, completion_tokens, generation_tps
    """
    _backend = _load_backend(backend)

    system_prompt = get_alpha_system_prompt(tier, condition)
    user_prompt = build_alpha_user_prompt(
        tier=tier,
        condition=condition,
        period=period,
        calendar_month=calendar_month,
        demand_history=demand_history,
        prev_forecast=prev_forecast,
        forecast_error=forecast_error,
        history=history,
    )

    try:
        result = _backend.get_alpha_decision(
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
            "alpha":             result["alpha"],
            "rationale":         result.get("rationale", ""),
            "alpha_fallback":    False,
            "attempt_number":    result.get("attempt_number", 1),
            "latency_ms":        result.get("latency_ms", 0.0),
            "ttft_ms":           result.get("ttft_ms", 0.0),
            "prompt_tokens":     result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "generation_tps":    result.get("generation_tps", 0.0),
        }

    except RuntimeError as exc:
        logger.warning(
            "run=%s period=%d tier=%s alpha parse failed — defaulting to %.1f. Error: %s",
            run_id, period, tier, ALPHA_FALLBACK, exc,
        )
        return {
            "alpha":             ALPHA_FALLBACK,
            "rationale":         "",
            "alpha_fallback":    True,
            "attempt_number":    3,
            "latency_ms":        0.0,
            "ttft_ms":           0.0,
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "generation_tps":    0.0,
        }
