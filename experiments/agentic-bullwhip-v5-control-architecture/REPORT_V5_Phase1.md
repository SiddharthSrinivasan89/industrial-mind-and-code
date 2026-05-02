# V5 Control Architecture — Phase 1 Gate Report

**Experiment:** `Agentic_Bullwhip_Effect_V5_ControlArch`
**Phase:** 1 — Deterministic Ablations (Oracle and Causal Upper Bounds)
**Date completed:** April 2026
**Verdict:** Phase 1 gate NOT passed. Phase 2 LLM conditions not justified for this architecture. Intent-classification lineage closed; broader research trajectory changed.

---

## Executive Summary

V4 WorldEvents established that an intent classification architecture produces an Order Variance Amplification Ratio (OVAR) of approximately 1.73–1.78 across all tested LLM models, regardless of model size, reasoning capability, or prompt information level. This "Equaliser Effect" raised a direct question: is the ceiling a model-quality problem (Phase 2 hypothesis) or an architectural constraint (close-out)?

V5 Phase 1 answered this question by removing the LLM entirely. Using deterministic oracle labels — perfect ground-truth classifications fed directly to the formula — V5 tested whether any combination of label quality, multiplier range, NEUTRAL redefinition, order dampening, or forecast oracle could close the 0.54-unit gap between the intent-classifier floor (~1.75) and the exponential smoothing baseline (1.19).

**None of them could.**

The best Phase 1 result across 14 conditions and 20 runs each is `neutral_smoothed_forecast` at OVAR 1.733. This barely beats `order_up_to` (1.753) — and remains 0.540 above `exp_smoothing` (1.193). The gap to exponential smoothing is preserved exactly, confirming the ceiling is architectural: the OUT formula structure generates irreducible variance that no decision-layer improvement can eliminate.

**The intent-classification lineage is closed.** The five-version chain has produced a definitive finding: LLMs with intent-classification interfaces cannot replicate the variance-dampening properties of exponential smoothing within the OUT formula architecture. This is a structural incompatibility, not a model quality or prompt engineering problem. The broader research program continues by changing the control lever rather than improving this interface.

---

## 1. Research Question

V4's Equaliser Effect finding left open two interpretations:
1. **Model-quality hypothesis:** A better LLM — one that genuinely understood seasonal and event signals — would choose labels more accurately, which would translate to lower OVAR.
2. **Architectural constraint hypothesis:** Even perfect labels cannot close the gap, because the source of variance is the OUT formula's reactive structure, not the LLM's classification quality.

V5 Phase 1 tests interpretation 2 by removing the LLM entirely. If oracle labels (ground-truth perfect classifications) produce the same OVAR as LLM labels, Phase 2 LLM experiments would add cost without theoretical upside.

**Phase 1 gate criterion:** Any V5 condition must beat `order_up_to` (OVAR ≈ 1.75) by more than 0.10, OR come within 0.30 of `exp_smoothing` (OVAR ≈ 1.19), for Phase 2 to be warranted.

---

## 2. Methodology

### 2.1 Architecture

All Phase 1 conditions use the same three-layer intent-classifier architecture as V4:

```
LABEL (oracle/causal) → LOOKUP (multiplier map) → EXECUTION (OUT formula)
```

The LLM classification layer is replaced with either:
- **Oracle intent**: Ground-truth labels from `GROUND_TRUTH_INTENT` — the theoretically perfect classifier.
- **Causal intent**: Rule-based classifier using only calendar month and event signals — a fair deterministic benchmark matching LLM information conditions.

### 2.2 Conditions Tested (14 total)

| Group | Condition | What varies | OVAR |
|---|---|---|---|
| Baselines | `exp_smoothing` | Formula baseline | **1.1931** |
| Baselines | `naive_passthrough` | Pass-through | **0.9961** |
| Baselines | `order_up_to` | OUT formula floor | **1.7527** |
| A1 Oracle | `oracle_v4map` | Perfect labels + V4 map | 1.7759 |
| A2 Multiplier | `oracle_moderate` | Perfect labels + wider map (±25/50%) | 1.7979 |
| A2 Multiplier | `oracle_aggressive` | Perfect labels + wider map (±40/80%) | 1.8593 |
| A2 Multiplier | `oracle_asymmetric` | Perfect labels + asymmetric map | 1.8314 |
| A3 Neutral | `neutral_smoothed_forecast` | NEUTRAL → forecast-only order | **1.7334** |
| A3 Neutral | `neutral_dampened_out` | NEUTRAL → 37.5%-dampened OUT | 2.0001 |
| A3 Neutral | `neutral_repeat_last` | NEUTRAL → repeat last order | 2.2231 |
| A3 Neutral | `neutral_floor_only` | NEUTRAL → no order if stocked | 2.3129 |
| A4 Dampening | `dampened_beta50` | β=0.50 order smoothing | 1.7654 |
| A4 Dampening | `dampened_beta75` | β=0.75 order smoothing | 1.9628 |
| A4 Dampening | `dampened_beta25` | β=0.25 order smoothing | 1.8216 |
| A5 Forecast | `forecast_oracle_events` | Event-adjusted F_t | 2.0094 |
| A6 Causal | `causal_context` | Rule-based calendar labels | 1.7493 |
| A6 Causal | `causal_unstructured` | Rule-based calendar + event | 1.7686 |

**Environment:** 36-month SimPy simulation, stochastic lead times (LogNormal), stochastic fill rates (Beta), world events active. Identical to V4 WorldEvents. n=20 per condition.

---

## 3. Results

### 3.1 Overall OVAR Summary

```
exp_smoothing            1.1931  ←← benchmark (gap: 0.000)
naive_passthrough        0.9961  ←← passes demand directly (low amplification by design)
─────────────────────────────── gap: 0.540 ────────────────────────────────
neutral_smoothed_forecast  1.7334  ← best Phase 1 result (beats order_up_to by 0.019)
causal_context             1.7493  ← rule-based calendar; same as oracle
order_up_to                1.7527  ← V4 architecture floor
causal_unstructured        1.7686  ← event signal adds noise, not signal
dampened_beta50            1.7654  ← β=0.50 dampening; marginal gain
oracle_v4map               1.7759  ← PERFECT labels; still worse than order_up_to
oracle_moderate            1.7979  ← wider map; worse
dampened_beta75            1.9628  ← β=0.75; worse than undampened
oracle_asymmetric          1.8314  ← asymmetric map; worse
oracle_aggressive          1.8593  ← widest map; worst oracle variant
neutral_dampened_out       2.0001  ← partial dampening on NEUTRAL; worse
forecast_oracle_events     2.0094  ← event-adjusted forecast; worse
neutral_repeat_last        2.2231  ← repeat last order; much worse
neutral_floor_only         2.3129  ← no order when stocked; worst overall
```

### 3.2 Gate Assessment

| Criterion | Value | Pass/Fail |
|---|---|---|
| Any condition beats `order_up_to` by ≥ 0.10? | Best margin: 0.019 (`neutral_smoothed_forecast`) | **FAIL** |
| Any condition within 0.30 of `exp_smoothing`? | Closest: 0.540 (`neutral_smoothed_forecast`) | **FAIL** |

**Gate verdict: FAIL.** Phase 2 LLM experiments are not justified.

---

## 4. Key Findings

### F1: Perfect labels are worth nothing on the V4 map

`oracle_v4map` uses ground-truth perfect classifications (GROUND_TRUTH_INTENT) with the V4 conservative multiplier map. It produces OVAR 1.7759 — **worse than `order_up_to` (1.7527)**. This is the most direct evidence that the bottleneck is not classification quality. A hypothetical LLM that classifies every period perfectly would still produce worse OVAR than the unmodified OUT formula.

### F2: Wider multiplier maps always make things worse

A2's oracle conditions tested the hypothesis that V4's 0.80–1.30 range was too conservative. All three wider maps (moderate ±25/50%, aggressive ±40/80%, asymmetric) produced higher OVAR (1.79–1.86). Larger safety-stock swings compound variance further upstream regardless of label accuracy.

### F3: NEUTRAL redefinition is the only lever with marginal traction

`neutral_smoothed_forecast` (NEUTRAL → `order = max(0, round(F_t))`, no safety stock) achieves OVAR 1.7334, the best Phase 1 result. This is the only condition in V5 that mechanically resembles exponential smoothing behaviour: during NEUTRAL periods (the majority of periods), the order is driven by the forecast alone. It beats `order_up_to` by 0.019. All other NEUTRAL redefinitions (repeat_last, dampened_out, floor_only) produce substantially worse OVAR (2.0–2.3).

### F4: Causal rule-based classifier equals oracle

`causal_context` (rule-based calendar labels) achieves OVAR 1.7493 — nearly identical to `oracle_v4map` (1.7759) and `order_up_to` (1.7527). This confirms that calendar and event labels carry essentially no predictive value for variance reduction in the conservative multiplier map. A hand-written rule achieves the same result as perfect machine-generated labels.

### F5: The 0.540 gap is architectural, not label-quality dependent

The gap between the best Phase 1 condition (1.7334) and `exp_smoothing` (1.1931) is 0.540. This matches, to within rounding, the gap observed in V4 between the best LLM condition (1.726) and V4's exp_smoothing (1.185). The gap is invariant to label quality, multiplier range, NEUTRAL redefinition, or forecast oracle. This identifies the source of the gap as the structure of the OUT formula itself.

### F6: Exponential smoothing dampens variance structurally

`exp_smoothing` uses an EMA forecast (α=0.30) with no safety-stock adjustments. Each tier independently smooths its orders toward a dampened estimate of upstream demand. This naturally attenuates variance at every tier and across the chain. The intent classifier architecture always applies safety stock (multiplier × base_SS), which adds an inventory-based signal on top of the forecast. Even at multiplier=1.0 (NEUTRAL), the base safety stock generates order volatility that compounds at upstream tiers. This is not a bug in the design; it is the inherent tradeoff between service level protection (safety stock) and variance stability.

---

## 5. Hypothesis Outcomes

| H | Test | Result |
|---|---|---|
| **HV5-1** | Any Phase 1 condition beats order_up_to by ≥ 0.10 | **FAIL** — best margin 0.019 |
| **HV5-2** | Perfect oracle labels reduce OVAR below order_up_to | **FAIL** — oracle_v4map 1.776 > order_up_to 1.753 |
| **HV5-3** | Any multiplier map variant beats V4 conservative map | **FAIL** — all wider maps produce higher OVAR |
| **HV5-4** | Any NEUTRAL redefinition produces meaningful OVAR reduction | **PARTIAL** — smoothed_forecast marginal gain 0.019; all others worse |
| **HV5-5** | Causal rule-based classifier outperforms oracle | **FAIL** — causal 1.749, oracle 1.776; causal marginally better but within noise |

---

## 6. Intent-Classification Lineage Close-Out

### The five-version chain and what each one proved

| Version | Architecture | Core failure / finding |
|---|---|---|
| V1 | Direct LLM order quantities, no guardrails | LLMs generate wildly unstable quantities; OVAR off-chart |
| V2 / V2a | LLM output capped, direct float quantity, 25-month | LLMs amplify order variance 4–6× above exp_smoothing |
| V3b HybridArch | LLM float multiplier × OUT formula, 25-month | Float output unreliable; context penalty; OVAR 2.3–3.1× |
| V4 WorldEvents | 5-label discrete intent → lookup → OUT formula, 36-month | Equaliser Effect; all models cluster OVAR 1.73–1.78 regardless of quality |
| **V5 Phase 1** | Oracle/causal deterministic labels, 14 architectural variants | Ceiling is architectural; perfect labels and formula variants cannot close gap to exp_smoothing |

### What the program established

1. **LLMs understand supply chain context** (V3b semantic alignment finding, V4 direction accuracy 0.72–0.80 with context). The problem is not comprehension.
2. **Discrete label interfaces fix calibration** (V4 vs V3b: OVAR drops from 2.3–3.1 to 1.73–1.78 by replacing continuous float output with 5-label lookup). But ceiling emerges immediately.
3. **The ceiling is in the formula, not the classifier.** V5 oracle proves this definitively. No improvement to the classification layer can close the 0.540 gap.
4. **Exponential smoothing is structurally better for variance reduction** than any safety-stock-based approach. The two architectures are solving different problems: exp_smoothing optimises variance stability; safety stock optimises service level. They cannot be directly compared as equivalent alternatives.

### What this means for V6 (if any)

The only architectural change that could theoretically break the ceiling is replacing the OUT formula entirely with an EMA-based forecasting policy where the LLM modifies the EMA smoothing parameter rather than the safety stock multiplier. This is a fundamentally different design space (predict-then-smooth rather than forecast-then-buffer). No evidence yet that this is tractable; it would require a new experiment lineage.

**Decision: intent-classification lineage closed at V5 Phase 1.**

---

## 7. Complete Results Table

| Condition | n | Chain OVAR | Chain Stockouts |
|---|---|---|---|
| `naive_passthrough` | 20 | **0.9961** | 95.4 |
| `exp_smoothing` | 20 | **1.1931** | 89.5 |
| `neutral_smoothed_forecast` | 20 | 1.7334 | 89.5 |
| `causal_context` | 20 | 1.7493 | 87.2 |
| `order_up_to` | 20 | 1.7527 | 87.3 |
| `causal_unstructured` | 20 | 1.7686 | 87.0 |
| `dampened_beta50` | 20 | 1.7654 | 93.5 |
| `dampened_beta75` | 20 | 1.8216 | 89.0 |
| `oracle_v4map` | 20 | 1.7759 | 87.0 |
| `oracle_moderate` | 20 | 1.7979 | 87.2 |
| `oracle_asymmetric` | 20 | 1.8314 | 87.0 |
| `oracle_aggressive` | 20 | 1.8593 | 87.0 |
| `dampened_beta25` | 20 | 1.9628 | 96.3 |
| `neutral_dampened_out` | 20 | 2.0001 | 89.7 |
| `forecast_oracle_events` | 20 | 2.0094 | 85.3 |
| `neutral_repeat_last` | 20 | 2.2231 | 88.2 |
| `neutral_floor_only` | 20 | 2.3129 | 89.2 |

*Lower OVAR = better. Stockouts measured as chain-level count across all 36 periods, mean over 20 runs.*

---

## 8. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-04-25 | Siddharth Srinivasan | Phase 1 complete; gate verdict written; intent-classification lineage closed |
