# Agentic Bullwhip Effect V5 — Design, Parameters, and Hypotheses

This is Version 5 of a five-experiment series examining whether Large Language Models (LLMs) can reduce order variance amplification in multi-tier supply chains. V5 deliberately tests no LLM. It removes the LLM classification layer and replaces it with deterministic oracle labels (ground-truth perfect classifications) and rule-based causal labels, to determine whether the performance ceiling found in V4 (the "Equaliser Effect", OVAR approximately 1.73 to 1.78) comes from model quality or from the architecture itself.

## Research Question

V4's Equaliser Effect left two competing interpretations:

1. Model-quality hypothesis: a better LLM that genuinely understood seasonal and event signals would choose labels more accurately, which would translate to lower OVAR.
2. Architectural constraint hypothesis: even perfect labels cannot close the gap, because the source of variance is the Order-Up-To (OUT) formula's reactive structure, not the classification quality.

Primary question: do deterministic oracle labels fed directly to the intent-to-multiplier lookup produce materially lower OVAR than the LLM conditions of V4? If yes, Phase 2 LLM experiments with improved models are warranted. If no, the ceiling is confirmed as architectural.

Phase 1 gate criterion: any V5 condition must either beat `order_up_to` (OVAR approximately 1.75) by more than 0.10, or come within 0.30 of `exp_smoothing` (OVAR approximately 1.19), for Phase 2 LLM experiments to be justified.

## Primary Metric

OVAR = Var(orders) / Var(demand), computed per tier using sample variance (ddof=1) over all active ordering periods, then averaged as the arithmetic mean across the three tiers. Values below 1.0 indicate variance dampening; values above 1.0 indicate amplification. The secondary metric is chain-level stockout count across all 36 periods, mean over n=20 runs.

## Supply Chain Structure

Identical to V4 WorldEvents, preserving cross-experiment OVAR comparability.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- Simulation horizon: 36 months (January 2025 through December 2027).
- Lead times: stochastic (LogNormal distribution), further modified by world events.
- Fill rates: stochastic (Beta distribution), capped during world events.
- World events: pandemic (months 7 to 12), geopolitical conflict (months 19 to 21), port strike (months 28 to 30) — identical to V4.

## Three-Layer Execution Architecture (LLM layer replaced)

```
Layer 1 — Label source (oracle or causal, no LLM)
  Oracle intent: ground-truth labels from the GROUND_TRUTH_INTENT schedule
  Causal intent: rule-based classifier using calendar month and event signals only

Layer 2 — Lookup (deterministic, same as V4)
  Label -> multiplier value from a fixed map

Layer 3 — OUT Formula (deterministic, same as V4)
  order = max(0, forecast + safety_stock * multiplier - inventory_position)
```

No LLM was used. All conditions are deterministic (oracle or rule-based). n=20 runs per condition (Monte Carlo over stochastic lead-time and fill-rate draws).

## Ablation Groups and Conditions (14 total)

| Group | Purpose |
|---|---|
| A1 Oracle | Oracle labels with the V4 multiplier map; the most direct test of the model-quality hypothesis |
| A2 Multiplier | Oracle labels with wider or asymmetric multiplier ranges; tests whether V4's conservative map was the bottleneck |
| A3 Neutral | Oracle labels with alternative NEUTRAL-class behaviour; tests whether NEUTRAL redefinition unlocks improvement |
| A4 Dampening | Oracle labels with order-smoothing applied post-formula; tests mechanical variance dampening |
| A5 Forecast | Event-adjusted demand forecast oracle; tests whether forecast quality is the bottleneck |
| A6 Causal | Rule-based calendar and event labels; fair deterministic benchmark matching LLM information conditions |

| Group | Condition | What varies |
|---|---|---|
| Baselines | `exp_smoothing` | Formula baseline (EMA forecast, alpha = 0.30, no safety stock) |
| Baselines | `naive_passthrough` | Pass-through of demand |
| Baselines | `order_up_to` | OUT formula floor, no classification layer |
| A1 Oracle | `oracle_v4map` | Perfect labels + V4 conservative map |
| A2 Multiplier | `oracle_moderate` | Perfect labels + wider map (±25/50%) |
| A2 Multiplier | `oracle_aggressive` | Perfect labels + widest map (±40/80%) |
| A2 Multiplier | `oracle_asymmetric` | Perfect labels + asymmetric map |
| A3 Neutral | `neutral_smoothed_forecast` | NEUTRAL -> forecast-only order, no safety stock |
| A3 Neutral | `neutral_dampened_out` | NEUTRAL -> 37.5%-dampened OUT |
| A3 Neutral | `neutral_repeat_last` | NEUTRAL -> repeat last order |
| A3 Neutral | `neutral_floor_only` | NEUTRAL -> no order if stocked |
| A4 Dampening | `dampened_beta25` | beta = 0.25 order smoothing |
| A4 Dampening | `dampened_beta50` | beta = 0.50 order smoothing |
| A4 Dampening | `dampened_beta75` | beta = 0.75 order smoothing |
| A5 Forecast | `forecast_oracle_events` | Event-adjusted F_t |
| A6 Causal | `causal_context` | Rule-based calendar labels |
| A6 Causal | `causal_unstructured` | Rule-based calendar + event labels |

## Hypotheses

Hypotheses were stated in the design document before execution but were not pre-registered with any external registry.

| Label | Hypothesis | Threshold |
|---|---|---|
| HV5-1 | Any Phase 1 condition beats order_up_to by >= 0.10 | OVAR improvement >= 0.10 over order_up_to |
| HV5-2 | Perfect oracle labels reduce OVAR below order_up_to | oracle_v4map OVAR < order_up_to OVAR |
| HV5-3 | Any multiplier map variant beats the V4 conservative map | Any A2 condition OVAR < oracle_v4map OVAR |
| HV5-4 | Any NEUTRAL redefinition produces meaningful OVAR reduction | OVAR improvement >= 0.10 over order_up_to |
| HV5-5 | Causal rule-based classifier outperforms oracle | causal_context OVAR < oracle_v4map OVAR |

See FINDINGS.md for the verdicts and the exact result table.
