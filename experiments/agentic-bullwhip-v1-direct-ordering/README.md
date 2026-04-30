# Agentic Bullwhip Effect — Version 1: Context and Model Capability in AI-Driven Supply Chain Ordering

## Abstract

This experiment tested whether providing business context (company identity, product details, and calendar month) to LLM agents reduces order variability amplification in a three-tier supply chain simulation, using a 2x2 factorial design crossing context treatment with model capability tier (lightweight vs. reasoning). Results indicate that context reduced variability for the lightweight model but increased it sharply for the reasoning model; the most capable and most expensive configuration — context with o1 — produced the highest chain-level order variance amplification of all four configurations tested. Every configuration amplified demand variability relative to the input signal.

---

## Research Question

Does providing domain-relevant business context (company identity, product, calendar month) to an LLM ordering agent reduce bullwhip amplification in a three-tier supply chain, and does the effect differ between a lightweight and a reasoning-tier model?

---

## Experimental Design

### Supply Chain Structure

A three-tier serial supply chain with deterministic, one-month lead times at all levels:

```
Tatva Motors (OEM)
    |
    v  orders
Lighting Manufacturer (Ancillary)
    |
    v  orders
LED Component Manufacturer (Component)
```

| Parameter | Value |
|---|---|
| Demand series | 13 months, Dec 2024 to Dec 2025 (single SKU, Vecta product family) |
| Active ordering periods | 12 (period 13 is demand-fulfilment only) |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | 43,000 units at all tiers |
| Total demand | 606,771 units |

All scenarios, companies, products, and supply chain structures are fictional. No proprietary data was used.

### Conditions and Models

| Factor | Level 1 | Level 2 |
|---|---|---|
| Model tier | Lightweight: gpt-4.1-mini (temp 0.4, 600 max tokens) | Reasoning: o1 (API-fixed temperature, 16,000 max tokens) |
| Context treatment | Blind: numeric state only (demand, on-hand inventory, backlog, in-transit orders, lead time) | Context: same numeric state plus company identity, product details, market position, and calendar month/year |

This produces four configurations: `blind_lightweight`, `context_lightweight`, `blind_reasoning`, `context_reasoning`.

**Agent design:** Stateless. Agents have no memory between ordering periods. This design was deliberate: most production agentic deployments are stateless.

**Replications:** 5 per configuration, 20 total runs, 720 LLM calls (12 periods x 3 tiers x 5 runs x 4 configurations).

**Scale:** This was an exploratory study designed to establish a baseline and surface unexpected behaviour before scaling.

### Hypotheses

| Label | Null Hypothesis | Alternative Hypothesis |
|---|---|---|
| H1 | Context has no effect on OVAR at any tier | Context reduces mean OVAR at all three tiers relative to the blind condition |
| H2 | Blind-reasoning and blind-lightweight OVARs differ materially | Blind-reasoning and blind-lightweight mean OVARs overlap within their CV ranges (model capability is not the determining factor when context is absent) |
| H3 | context_reasoning does not achieve the lowest chain OVAR | context_reasoning achieves the lowest chain-level OVAR of all four configurations |
| H4 | Context agents do not respond more to seasonal demand events | Context agents score higher than blind agents on the seasonal pattern detection score at event periods |

All hypotheses were directional; no pre-specified minimum effect size thresholds were applied. This is an exploratory study.

---

## Results

### Key Metrics

**Primary metric — OVAR (Order Variance Amplification Ratio):**

```
OVAR = Var(orders placed) / Var(demand received)
```

Computed per tier over periods 1–12. Values below 1.0 indicate dampening; values above 1.0 indicate bullwhip amplification. Reported as mean ± std across 5 runs per configuration.

**Secondary metrics:**

| Metric | Description |
|---|---|
| Stockout count | Periods where backlog > 0 after fulfilment (chain total across 5 runs) |
| Excess inventory | Units on hand above demand at period end (chain total across 5 runs) |
| Seasonal elevation score | Fraction of (tier x event-period) pairs where agent ordered >= 110% of non-event baseline |

### Results Tables

**Chain-average OVAR by configuration**

| Configuration | Model | Treatment | Chain avg OVAR | vs blind_lightweight |
|---|---|---|---|---|
| context_lightweight | gpt-4.1-mini | Context | 2.929 | -7.2% |
| blind_lightweight | gpt-4.1-mini | Blind | 3.157 | baseline |
| blind_reasoning | o1 | Blind | 3.835 | +21.5% |
| context_reasoning | o1 | Context | 4.412 | +39.7% |

**OVAR by tier (mean ± std, CV%)**

| Configuration | OEM OVAR | CV% | Ancillary OVAR | CV% | Component OVAR | CV% |
|---|---|---|---|---|---|---|
| blind_lightweight | 2.267 ± 0.009 | 0.41 | 2.938 ± 0.044 | 1.50 | 4.266 ± 0.078 | 1.82 |
| context_lightweight | 2.237 ± 0.006 | 0.29 | 3.138 ± 0.080 | 2.55 | 3.412 ± 0.347 * | 10.18 |
| blind_reasoning | 4.200 ± 2.400 | 57.15 (+) | 3.656 ± 1.350 | 36.94 (+) | 3.649 ± 0.608 | 16.66 (+) |
| context_reasoning | 6.349 ± 1.452 | 22.86 (+) | 4.191 ± 1.373 | 32.76 (+) | 2.698 ± 0.677 | 25.10 (+) |

\* Parse error in run 5 inflates component mean by ~+0.129. Clean estimate: 3.283 ± 0.220.
(+) CV > 10%; high run-to-run instability; means are directional, not reliable point estimates at n=5.

**Stockouts and excess inventory (chain totals across 5 runs)**

| Configuration | Stockouts | Excess inventory (units) |
|---|---|---|
| blind_lightweight | 21.4 | 109,360 |
| context_lightweight | 19.6 | 151,246 |
| blind_reasoning | 20.0 | 330,649 |
| context_reasoning | 12.8 | 654,728 |

context_reasoning had the fewest stockouts and the highest excess inventory — roughly 6x blind_lightweight. Fewer stockouts, but at significant inventory cost.

### Hypothesis Verdicts

| Hypothesis | Prediction | Verdict |
|---|---|---|
| H1 | Context reduces OVAR at all three tiers | REJECTED |
| H2 | Blind reasoning performs similarly to blind lightweight | REJECTED |
| H3 | context_reasoning achieves the lowest chain OVAR | REJECTED |
| H4 | Context agents respond better to seasonal demand | PARTIAL |

H4 held for the lightweight model (seasonal elevation score of 83% at event periods) but reversed for the reasoning model.

---

## Discussion

The context effect ran in opposite directions depending on the model. For gpt-4.1-mini, context reduced chain OVAR by 0.228. For o1, context increased it by 0.577. The sharpest divergence was at the OEM tier — the tier observing real consumer demand. Context had near-zero effect on gpt-4.1-mini there (delta -0.030). For o1 at the same tier, context pushed OVAR up by 2.149.

A model capable of reasoning about seasonality, given a month name and a market identity, appears to build forward-looking ordering strategies that inject variance at the chain head rather than reduce it. The inverted tier cascade in context_reasoning is the clearest expression of this: OEM OVAR 6.349, Ancillary 4.191, Component 2.698. Standard bullwhip theory predicts variability increasing upstream; context_reasoning flipped this entirely. The three other configurations followed the expected pattern.

The corresponding service-cost trade-off was extreme: 654,728 units of excess inventory chain-wide, while stockouts fell to 12.8. Whether this pattern holds at higher replication counts is what Agentic Bullwhip Effect Version 2 was designed to test. With CV values of 22–57% for o1 configurations, these means are directional at n=5 — sufficient to motivate follow-up, but not settled enough to conclude upon.

The more capable model also showed high run-to-run variability (CV 22–57%) compared to the lightweight model (CV under 2%). In a production context, a model that produces reasonable results in some runs and extreme results in others — from identical inputs — cannot be validated in advance of deployment. Consistent failure is at least predictable; intermittent failure is not.

---

## Limitations

- **Sample size:** 5 runs per configuration. Means for o1 configurations carry CV values of 22–57% and should be treated as directional rather than settled point estimates. The lightweight model was substantially more stable.
- **Single demand series:** 12 active ordering periods, one SKU, one supply chain structure. Results cannot be generalised beyond this design.
- **Order guardrails:** Version 1 imposed an order floor (0.2x demand) and ceiling (5x demand) on all agents. These guardrails constrained extreme behaviour and may have masked natural agent responses. Version 2 removes them.
- **Stateless architecture only:** No stateful agent design was tested. Whether memory between periods would change results is outside what this experiment can establish.
- **Single-season demand signal:** The demand series covers one calendar year with one festive cycle.
- **Fictional scenario:** All companies, products, and supply chain identities are synthetic.

---

## How to Reproduce

### Prerequisites

- Python 3.11+
- Azure OpenAI credentials with access to `gpt-4.1-mini` and `o1` deployments

### Environment Setup

The experiment reads credentials from a `.env` file. A template of required variables:

```
OPENAI_API_KEY=<your Azure OpenAI key>
OPENAI_BASE_URL=<your Azure OpenAI endpoint>
AZURE_API_VERSION=2025-01-01-preview
LIGHTWEIGHT_MODEL=<your gpt-4.1-mini deployment name>
REASONING_MODEL=<your o1 deployment name>
LIGHTWEIGHT_INPUT_COST_PER_1M=<cost in USD>
LIGHTWEIGHT_OUTPUT_COST_PER_1M=<cost in USD>
REASONING_INPUT_COST_PER_1M=<cost in USD>
REASONING_OUTPUT_COST_PER_1M=<cost in USD>
```

Create a `.env` file in this folder and fill in your own credentials. Do not commit this file — it is listed in `.gitignore`.

Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Experiment

**Test the API connection:**

```bash
python src/test_connection.py
```

**Run the full experiment:**

```bash
python src/run_experiment.py
```

Results are written to:
- `results/raw/` — per-run JSON files
- `results/aggregated/` — per-configuration summary JSON files
- `results/experiment.log` — execution log

The experiment runs all four configurations (blind_lightweight, context_lightweight, blind_reasoning, context_reasoning) for 5 runs each. Total LLM calls: 720.

---

## Citation

Published writeup: [https://industrialmindandcode.ai/blog/agentic-bullwhip-v1](https://industrialmindandcode.ai/blog/agentic-bullwhip-v1)

Author: Siddharth Srinivasan — [industrialmindandcode.ai](https://industrialmindandcode.ai)

Date: February 2026
