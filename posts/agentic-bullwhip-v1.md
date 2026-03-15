---
title: Agentic Bullwhip Effect — Version 1
date: February 2026
domain: SUPPLY CHAIN · EXPERIMENT WRITEUP
summary: Context improved lightweight models but degraded the reasoning model. The most capable, most expensive configuration performed worst overall.
experiment: Agentic Bullwhip Effect V1
slug: agentic-bullwhip-v1
---

## Abstract

The bullwhip effect is a foundational supply chain problem: small fluctuations in consumer demand cause progressively larger swings in orders further up the chain. This experiment placed AI agents at each tier of a 3-tier Indian automotive supply chain and tested whether giving them domain context — company identity, product, market, calendar — reduced order amplification compared to agents operating blind. A 2×2 factorial design crossed two context levels (blind vs context) against two model tiers (gpt-4.1-mini vs o1). All four configurations produced bullwhip amplification. Context reduced amplification for the lightweight model and increased it for the reasoning model. Results are directional — 5 runs per configuration.

---

## Experiment Setup

| Field | Value |
|---|---|
| Models | gpt-4.1-mini (lightweight) · o1 (reasoning) |
| Design | 2×2 factorial — model tier × context treatment |
| Replications | 5 per configuration · 20 total runs |
| Primary metric | OVAR — Order Variance Amplification Ratio |
| Supply chain | 3-tier serial: Tatva Motors (OEM) → Lighting Manufacturer (Ancillary) → LED Component Manufacturer |
| Demand series | 13 months (Dec 2024 – Dec 2025) · single SKU · 606,771 total units |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | 43,000 units at all tiers |
| LLM calls | 720 total (12 periods × 3 tiers × 5 runs × 4 configurations) |

**OVAR interpretation:** Values above 1.0 mean the agent's orders were noisier than the demand it received. Values below 1.0 mean orders were smoother. Values at 1.0 mean perfect pass-through.

The 2×2 factorial yielded four configurations:

| | Blind (numbers only) | Context (company + product + calendar) |
|---|---|---|
| **Lightweight** (gpt-4.1-mini) | blind_lightweight | context_lightweight |
| **Reasoning** (o1) | blind_reasoning | context_reasoning |

---

## Key Findings

1. **All configurations produced bullwhip amplification.** OVAR exceeded 1.0 at every tier across all four configurations.

2. **Context was associated with lower chain-average OVAR for the lightweight model.** context_lightweight achieved a chain-average OVAR of 2.929 versus blind_lightweight at 3.157. It also produced the highest seasonal elevation score, raising orders at event periods in 83% of cases.

3. **Context was associated with higher chain-average OVAR for the reasoning model.** context_reasoning reached 4.412 versus blind_reasoning at 3.835 — the highest of the four configurations.

4. **context_reasoning produced an inverted tier pattern.** Classical bullwhip analysis predicts amplification increasing with tier depth: OEM < Ancillary < Component. context_reasoning reversed this: OEM OVAR 6.349, Ancillary 4.191, Component 2.698. The other three configurations followed the expected monotone pattern.

5. **The o1 configurations showed high run-to-run variability.** Coefficient of variation for o1 OVAR ranged from 22–57%, versus under 2% for gpt-4.1-mini. With n=5, the o1 means carry wide uncertainty and should be read with caution.

6. **context_reasoning generated the highest excess inventory.** 654,728 units of excess chain inventory chain-wide — approximately 6× blind_lightweight — while producing the highest chain-average OVAR.

---

## Results

### Chain-Average OVAR by Configuration

| Configuration | Model | Treatment | Chain Avg OVAR | vs blind_lightweight |
|---|---|---|---|---|
| context_lightweight | gpt-4.1-mini | Context | 2.929 | −7.2% |
| blind_lightweight | gpt-4.1-mini | Blind | 3.157 | baseline |
| blind_reasoning | o1 | Blind | 3.835 | +21.5% |
| context_reasoning | o1 | Context | 4.412 | +39.7% |

### OVAR by Tier

| Configuration | OEM OVAR (mean ± std) | CV% | Ancillary OVAR (mean ± std) | CV% | Component OVAR (mean ± std) | CV% |
|---|---|---|---|---|---|---|
| blind_lightweight | 2.267 ± 0.009 | 0.41 | 2.938 ± 0.044 | 1.50 | 4.266 ± 0.078 | 1.82 |
| context_lightweight | 2.237 ± 0.006 | 0.29 | 3.138 ± 0.080 | 2.55 | 3.412 ± 0.347 * | 10.18 |
| blind_reasoning | 4.200 ± 2.400 | 57.15 ⚠ | 3.656 ± 1.350 | 36.94 ⚠ | 3.649 ± 0.608 | 16.66 ⚠ |
| context_reasoning | 6.349 ± 1.452 | 22.86 ⚠ | 4.191 ± 1.373 | 32.76 ⚠ | 2.698 ± 0.677 | 25.10 ⚠ |

*\* Parse error in run 5 inflates component mean by approximately +0.129. Clean estimate: 3.283 ± 0.220.*
*⚠ CV > 10% — means are directional; wide uncertainty at n=5.*

### Secondary Metrics

| Configuration | Stockouts (chain total) | Excess inventory (chain total) |
|---|---|---|
| blind_lightweight | 21.4 | 109,360 |
| context_lightweight | 19.6 | 151,246 |
| blind_reasoning | 20.0 | 330,649 |
| context_reasoning | 12.8 | 654,728 |

Note: context_reasoning's lower stockout count coincides with its highest excess inventory — orders were large enough to buffer stockouts.

### Hypothesis Verdicts

| Hypothesis | Prediction | Verdict |
|---|---|---|
| H1 | Context OVAR < Blind OVAR at all three tiers | REJECTED — context reduced OVAR only at the component tier |
| H2 | Blind_reasoning ≈ Blind_lightweight (model does not matter) | REJECTED — blind_reasoning OEM (4.20) versus blind_lightweight OEM (2.27): delta 1.93 |
| H3 | context_reasoning achieves lowest chain OVAR | REJECTED — context_reasoning produced the highest chain OVAR (4.412) |
| H4 | Context agents detect seasonal patterns better | PARTIALLY SUPPORTED — held for lightweight; reversed for reasoning |

---

## Discussion

### The context × model interaction

The most notable pattern is that the context effect runs in opposite directions depending on the model. For gpt-4.1-mini, context was associated with a modest reduction in chain-average OVAR (-0.228). For o1, context was associated with an increase (+0.577). The tier-level data adds detail: at the component tier, context reduced OVAR for both models by similar amounts (-0.855 and -0.952). At the OEM tier, the picture diverges sharply — context had a near-zero effect on gpt-4.1-mini (-0.030) and a large positive effect on o1 (+2.149).

One possible interpretation: at the OEM tier, which observes actual consumer demand directly, the o1 model with context may construct anticipatory ordering strategies around the seasonal signals in the prompt. If so, this would inject variance at the chain head that then propagates downstream. The component tier, receiving an already-distorted signal, may respond differently when given context — ordering more conservatively relative to the large fluctuations it observes. This is a hypothesis. The experiment cannot distinguish it from alternative explanations, and the high CV values for o1 configurations (22–57%) mean the OEM and ancillary means carry wide uncertainty at n=5.

### The tier inversion in context_reasoning

The fully inverted cascade in context_reasoning — OEM OVAR 6.349, Ancillary 4.191, Component 2.698 — is a departure from the pattern seen in all other configurations and from what classical bullwhip analysis would predict. Whether this pattern is structural or a product of the small sample size is an open question. Version 2 increases runs to 20 per configuration to give this more surface area.

### On the scope of these results

This experiment tested one narrow scenario: stateless agents, single product, fixed 1-month lead time, no order-smoothing constraints, no inter-tier visibility. The context treatment provided company identity, product, and calendar month — nothing about demand forecasts, seasonality patterns, or historical orders. Results reflect this specific configuration and should be read within it.

---

## Experiment Source

Code, data, and raw results for this experiment are available on GitHub: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/agentic_bullwhip_effect_version_1

---

## Methodology Note

All scenarios, companies, products, and supply chain structures in this experiment are entirely fictional and constructed for experimental purposes. No proprietary, confidential, or employer-owned data was used. This is an exploratory study — 5 runs per configuration. Results are directional. Hypotheses used directional language with no pre-specified effect size thresholds. The model-tier comparison reflects real-world deployment in a very simple manner. configurations: gpt-4.1-mini at temperature 0.4, 600 max tokens; o1 at API-fixed temperature, 16,000 max tokens. 
