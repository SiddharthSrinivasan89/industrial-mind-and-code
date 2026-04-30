"""
Oracle and causal deterministic intent policies for V5 ControlArch.

Two classifiers:

  get_oracle_intent(period)
    Future-aware diagnostic upper bound. Uses GROUND_TRUTH_INTENT from metrics.py.
    NOT deployable — the agent cannot know future demand at decision time.
    Purpose: if perfect classification still does not improve OVAR, the controller
    is the bottleneck, not the classifier.

  get_causal_intent(calendar_month, event_signal)
    Uses only information available at decision time: calendar month and the
    world-event headline (when in unstructured mode). No current state variables.
    This is the fair deterministic baseline the LLM must beat.

All three tiers call the same function and receive the same label. This is
intentional for oracle_intent (OEM demand drives the chain) and acceptable for
causal_intent (the available signals are chain-agnostic). Document this assumption
when comparing tier-level intent distributions.

Dependency: oracle_policies → metrics (one-way). Never import oracle_policies from metrics.
"""

from metrics import GROUND_TRUTH_INTENT

# ---------------------------------------------------------------------------
# Multiplier maps — single source of truth for V5 ablations
# ---------------------------------------------------------------------------

MULTIPLIER_MAPS: dict[str, dict[str, float]] = {
    "conservative": {           # V4 original
        "STRONG_INCREASE":   1.30,
        "MODERATE_INCREASE": 1.15,
        "NEUTRAL":           1.00,
        "MODERATE_DECREASE": 0.90,
        "STRONG_DECREASE":   0.80,
    },
    "moderate": {
        "STRONG_INCREASE":   1.50,
        "MODERATE_INCREASE": 1.25,
        "NEUTRAL":           1.00,
        "MODERATE_DECREASE": 0.80,
        "STRONG_DECREASE":   0.60,
    },
    "aggressive": {
        "STRONG_INCREASE":   1.80,
        "MODERATE_INCREASE": 1.40,
        "NEUTRAL":           1.00,
        "MODERATE_DECREASE": 0.70,
        "STRONG_DECREASE":   0.40,
    },
    "asymmetric": {             # stronger decreases than increases
        "STRONG_INCREASE":   1.30,
        "MODERATE_INCREASE": 1.15,
        "NEUTRAL":           1.00,
        "MODERATE_DECREASE": 0.75,
        "STRONG_DECREASE":   0.40,
    },
}


# ---------------------------------------------------------------------------
# Oracle intent — diagnostic upper bound
# ---------------------------------------------------------------------------

def get_oracle_intent(period: int) -> str:
    """
    Return the ground-truth intent label for this period.

    Uses future demand knowledge — NOT deployable. Call this only for A1/A2/A3/A4/A5
    ablation conditions where the goal is to isolate controller leverage from
    classifier accuracy.
    """
    return GROUND_TRUTH_INTENT.get(period, "NEUTRAL")


# ---------------------------------------------------------------------------
# Causal intent — fair deterministic baseline
# ---------------------------------------------------------------------------

def get_causal_intent(calendar_month: str, event_signal: str | None) -> str:
    """
    Return a rule-based intent label using only information available at decision time:
    the calendar month and the world-event headline (when provided).

    No future demand knowledge, no current state variables.

    Event signal rules:
      pandemic + collapse/collapsed       → STRONG_DECREASE
      pandemic + recovery/elevated        → MODERATE_INCREASE  (demand +10%, winding down)
      pandemic + surge/surging/reopening  → STRONG_INCREASE
      conflict                            → MODERATE_DECREASE
      port / strike / lead times          → no demand-intent override; fall through to calendar
        (supply-side only; demand_multiplier=1.0 per V4 design)

    Calendar rules (Indian automotive seasonality):
      Mar → STRONG_INCREASE    (FY-end fleet flush)
      Nov → STRONG_INCREASE    (Diwali peak)
      Jun, Jul → STRONG_DECREASE   (peak monsoon trough)
      May, Aug → MODERATE_DECREASE (monsoon fringe)
      Oct → MODERATE_INCREASE  (Navratri/Dasara pre-festive)
      Feb → MODERATE_DECREASE  (post-budget softness)
      else → NEUTRAL

    Known limitation: June calendar maps to STRONG_DECREASE, but V4 ground-truth
    period 30 (Jun 2027 + port disruption) is MODERATE_DECREASE. Correct direction,
    wrong intensity — accepted as part of a coarse calendar heuristic.
    """
    if event_signal:
        s = event_signal.lower()
        if "pandemic" in s and ("collapsed" in s or "collapse" in s):
            return "STRONG_DECREASE"
        if "pandemic" in s and ("recovery" in s or "elevated" in s):
            return "MODERATE_INCREASE"
        if "pandemic" in s and ("surge" in s or "surging" in s or "reopening" in s):
            return "STRONG_INCREASE"
        if "conflict" in s:
            return "MODERATE_DECREASE"
        # port/strike/lead-time: supply-side only; fall through to calendar

    m = calendar_month.strip()[:3]
    return {
        "Mar": "STRONG_INCREASE",
        "Nov": "STRONG_INCREASE",
        "Jun": "STRONG_DECREASE",
        "Jul": "STRONG_DECREASE",
        "May": "MODERATE_DECREASE",
        "Aug": "MODERATE_DECREASE",
        "Oct": "MODERATE_INCREASE",
        "Feb": "MODERATE_DECREASE",
    }.get(m, "NEUTRAL")
