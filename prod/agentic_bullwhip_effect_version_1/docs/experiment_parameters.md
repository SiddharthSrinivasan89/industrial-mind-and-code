# Experiment Parameters
## Bullwhip Effect in LLM-Powered Supply Chains — Tatva Motors Vecta

**Date:** 2026-02-19
**Location:** `prod/agentic_bullwhip_effect_version_1/`

---

## Research Question

Does activating LLM domain knowledge about Indian automotive seasonality reduce bullwhip amplification — and does reasoning capability determine how effectively that knowledge is applied?

---

## 1. Scenario

**Company:** Tatva Motors — a leading Indian passenger car manufacturer.
**Product:** The Vecta — a newly launched passenger car model.

**Supply chain under study:** The lighting system for the Vecta, covering three tiers:

```
Tatva Motors (OEM)
    │  places order for Vecta Lighting Assembly
    ▼
Ancillary Assembler (Lighting Manufacturer)
    │  places order for LED Lights
    ▼
Component Manufacturer (LED Supplier)
    │  sets production capacity
```

Each tier is operated by an LLM agent. No tier can see any other tier's inventory or orders — only the order placed by its immediate downstream customer arrives each month.

---

## 2. Experimental Design — 2×2 Factorial

| | **Blind** | **Context** |
|---|---|---|
| **Lightweight** (gpt-4.1-mini) | Blind Light | Context Light |
| **Reasoning** (o1) | Blind Reasoning | Context Reasoning |

**Factor 1 — Domain knowledge activation:**

| Treatment | What the agent receives |
|---|---|
| **Blind** | Monthly despatch numbers only. No product, no geography, no calendar, no role. |
| **Context** | Monthly despatch numbers + role identity + product + market + calendar month/year |

**Factor 2 — Model capability:**

| Model tier | Deployment | Temperature | Max tokens | Inter-call delay |
|---|---|---|---|---|
| **Lightweight** | gpt-4.1-mini | 0.4 | 600 | 1.0 s |
| **Reasoning** | o1 | 1.0 (API fixed) | 16,000 | 5.0 s |

**Note — temperature:** Each model runs at its intended operating temperature. o1 is API-fixed at 1.0; gpt-4.1-mini is set to 0.4. The Factor 2 comparison reflects real-world deployment conditions for each model, not a controlled parameter match.

---

## 3. Supply Chain Tiers

Three tiers run in sequence each month. The OEM sees real consumer demand; each upstream tier sees only the order placed by the tier below it.

| Internal key | Display name | Receives | Orders from |
|---|---|---|---|
| `oem` | OEM — Tatva Motors | Monthly Vecta despatch target (consumer demand) | Ancillary Assembler |
| `ancillary` | Ancillary Assembler | OEM's order for Lighting Assemblies | Component Manufacturer |
| `component` | Component Manufacturer | Ancillary's order for LED Lights | Production line (sets capacity) |

---

## 4. Demand Data

**File:** `data/synthetic/tatva_monthly_dispatches.csv`
**Series:** 13 months — December 2024 through December 2025
**Total dispatches:** 606,771 units

| Period | Month | Dispatches | Demand event |
|---|---|---|---|
| 1 | December 2024 | 43,812 | |
| 2 | January 2025 | 46,318 | |
| 3 | February 2025 | 47,095 | **Union Budget** |
| 4 | March 2025 | 49,287 | |
| 5 | April 2025 | 44,653 | |
| 6 | May 2025 | 39,841 | |
| 7 | June 2025 | 36,478 | |
| 8 | July 2025 | 38,193 | |
| 9 | August 2025 | 40,756 | |
| 10 | September 2025 | 56,892 | |
| 11 | October 2025 | 59,608 | **Dasara** |
| 12 | November 2025 | 55,347 | **Diwali** |
| 13 | December 2025 | 48,491 |

## 5. Agent Prompts

### 5a. Blind Agent — System Prompt (all tiers)

```
You are a supply chain ordering agent.
Always respond with valid JSON only.
No additional text before or after the JSON object.
```

### 5b. Blind Agent — User Prompt

```
Decide how many units to order for the next period.

Current state:
- Inventory on hand: {X} units
- Backlog (unfulfilled orders): {Y} units
- Orders in transit:
  {list or "None"}
- Lead time: 1 month(s)

This month's demand: {Z} units

Respond with ONLY a JSON object:
{"order_quantity": <number>, "reasoning": "<brief explanation>"}
```


### 5c. Context Agent — System Prompt (all tiers)

```
You are a supply chain ordering agent in the Indian automotive component industry.
Always respond with valid JSON only.
No additional text before or after the JSON object.
```

### 5d. Context Agent — User Prompt

The prompt is assembled from two blocks. Both are always present for the `context` treatment.

**Block 1 — Role (tier-specific):**

| Tier | Role text |
|---|---|
| OEM | "Company: Tatva Motors, India. Product: Vecta Lighting Assembly. Upstream supplier: ancillary lighting manufacturer. Each month: receive a production despatch target and place a Lighting Assembly order." |
| Ancillary | "Company: Lighting manufacturer, India. Customer: Tatva Motors (Vecta Lighting Assembly orders). Upstream supplier: LED component manufacturer. Each month: receive a Lighting Assembly order and place an LED component order." |
| Component | "Company: LED component manufacturer, India. Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies. Each month: receive a component order and set production capacity." |

**Block 2 — State, demand, instruction (same structure as blind, plus month/year):**

```
Current state:
- Month: {month_name} {year} (period {N})
- Inventory on hand: {X} units
- Backlog (unfulfilled orders): {Y} units
- Orders in transit:
  {list or "None"}
- Lead time: 1 month(s)

{demand label for this tier}: {Z} units

Decide how many units to order from your {upstream partner}.

Respond with ONLY a JSON object:
{"order_quantity": <number>,
 "reasoning": "<brief explanation>"}
```

**Demand labels (tier-specific):**

| Tier | Demand label | Upstream partner |
|---|---|---|
| OEM | "This month's Vecta despatch target" | ancillary supplier |
| Ancillary | "This month's Lighting Assembly order from Tatva Motors" | LED component supplier |
| Component | "This month's LED component order from lighting manufacturer" | production line |

---

## 6. Simulation Mechanics

**Per period, per tier — in order:**
1. Receive any deliveries whose `arriving_period` ≤ current period
2. Fulfil this period's demand (incoming order) + any backlog from on-hand stock
3. Any shortfall becomes new backlog; inventory floor is zero
4. If period < 13: call LLM → get `order_quantity`; clamp negative orders to zero; dispatch order arriving after lead time (1 month)
5. If period = 13: no order placed — demand fulfilment only; simulation closes out

**Execution order within each period:** OEM → Ancillary → Component (serial, not parallel — each tier's order becomes the next tier's demand in the same period).

---

## 7. Control Variables

These are identical across all four conditions and all runs:

| Variable | Value |
|---|---|
| Supply chain structure | 3-tier serial cascade |
| Product | Single SKU — Lighting Assembly for Tatva Vecta |
| Demand series | Fixed 13-month CSV, same sequence every run |
| Ordering periods | 12 months (periods 1–12); period 13 is demand fulfilment only |
| Initial inventory | 43,000 units at all three tiers |
| Lead time | 1 month (fixed, no variability) |
| Runs per config | 5 |
| Order floor | Zero (negative orders clamped to 0) |
| Order ceiling | None |
| Cost model | None (holding and backlog costs = 0) |
| Inter-tier visibility | None — each tier sees only its customer's order |
| Agent memory | None — each period is a single-turn, stateless LLM call; no order history injected |
| Numeric forecast | Not provided to any agent in any condition |


---

## 8. Metrics

### Primary — OVAR (Order Variance Amplification Ratio)

```
OVAR = Var(orders placed by tier) / Var(demand received by tier)
```

| OVAR | Meaning |
|---|---|
| = 1.0 | Orders mirror demand variability exactly |
| > 1.0 | Bullwhip: orders are noisier than demand |
| < 1.0 | Dampening: orders are smoother than demand |

Computed per tier, per run, over the 12 ordering periods (periods 1–12). Period 13 is excluded — no orders are placed. Reported as mean ± std across 5 runs. If Var(demand received) = 0 for any tier in any run, OVAR is recorded as undefined and excluded from aggregation; undefined-count is reported per tier per config so any missingness asymmetry across conditions is visible.

### Secondary (per tier, per run)

| Metric | What it measures |
|---|---|
| Stockout count | Periods (of 13) where on-hand stock cannot fulfil demand + backlog |
| Excess inventory | Sum of (inventory − demand) in periods with surplus — measures over-ordering waste |
| Total ordered | Sum of orders placed in periods 1–12; compared against 606,771 total demand benchmark |
| Peak overshoot | max(orders) ÷ max(demand received) — worst-case single-period spike, over periods 1–12 |
| Clamp count | Number of negative orders clamped to zero (expected: 0) |

### Stability check (cross-run)

```
CV = std(OVAR) / mean(OVAR) × 100%
```

High CV (e.g. > 30%) signals the LLM is erratic run-to-run — finding is directional, not stable. If mean OVAR is near zero, CV is unstable; in that case report std directly rather than CV.

### Pattern detection score

> **Metric version note — definition changed in Version 4 (Feb 2026).**
> Original design: `pattern_score = keywords matched / max possible keywords` (keyword-only).
> Revised design: composite of `keyword_score` and `elevation_score` (see below).
> **Reason for change:** the keyword-only score returned 0.0 across all configs in the initial run — models reason arithmetically and do not verbalise festival names, so the score had no discriminating power.
> **Comparability:** results from any run using the original keyword-only definition are **not comparable** to results under this definition. All Version 4 runs use the composite definition.

A composite of two sub-scores, each in [0, 1], evaluated only at event-relevant periods — 3 (Union Budget), 10 (pre-Dasara), 11 (Dasara), 12 (Diwali). Scoring non-event months would structurally penalise correct behaviour (zero mentions in June is right, not a failure).

**keyword_score** — verbal seasonal awareness

```
keyword_score = |distinct keywords matched| / |keyword list|
```

Keyword list (16 terms): dasara, dussehra, diwali, deepawali, deepavali, navratri, festive, festival, seasonal, peak, budget, fy-end, fiscal, quarter, anticipat. Matched against the `reasoning` field of any tier's LLM response at event periods. Both context and blind agents are scored. For context agents this reveals whether domain knowledge was activated by the Indian automotive role and month/year; for blind agents it reveals whether seasonal reasoning surfaces without those triggers.

**elevation_score** — quantitative seasonal responsiveness

```
elevation_score = (tier × event-period pairs where order ≥ 110% of non-event baseline)
                  / (total tier × event-period pairs)
```

For each tier the baseline is the mean order across non-event ordering periods. Captures seasonal pre-positioning even when a model reasons arithmetically without verbalising festival names.

**Composite**

```
pattern_score = mean(keyword_score, elevation_score)
```

All three values (`keyword_score`, `elevation_score`, `pattern_score`) are reported as mean ± std across runs in aggregated output.

### Reasoning audit (Reasoning model only)

For the o1 model, blind vs. context decisions are compared side-by-side at periods 3, 10, 11, and 12 (Union Budget, pre-Dasara, Dasara, Diwali) across all three tiers. Shows the agent's own stated reasoning — not just what it ordered, but why. Period 10 is included to match the pattern score diagnostic window and to capture pre-positioning reasoning before the Dasara peak.

---

## 9. Run Configuration

| Config key | Model | Category | Runs | LLM calls |
|---|---|---|---|---|
| `blind_lightweight` | gpt-4.1-mini | blind | 5 | 180 |
| `context_lightweight` | gpt-4.1-mini | context | 5 | 180 |
| `blind_reasoning` | o1 | blind | 5 | 180 |
| `context_reasoning` | o1 | context | 5 | 180 |
| **Total** | | | **20** | **720** |

Each LLM call = 1 period × 1 tier × 1 run (12 ordering periods only — period 13 fulfils demand but places no orders). All 720 decisions are logged with full state, order quantity, reasoning text, API latency, and token usage. Two lightweight probe calls made by the connection check at startup are excluded from this count.

---

## 10. Output Structure

```
results/
├── raw/
│   ├── blind_lightweight_run01.json
│   ├── blind_lightweight_run02.json
│   ├── blind_lightweight_run03.json
│   ├── context_lightweight_run01.json
│   │   ...
│   ├── blind_reasoning_run01.json
│   └── context_reasoning_run03.json
├── aggregated/
│   ├── blind_lightweight_aggregated.json
│   ├── context_lightweight_aggregated.json
│   ├── blind_reasoning_aggregated.json
│   └── context_reasoning_aggregated.json
├── figures/
│   ├── cascade_blind_lightweight.png
│   ├── cascade_context_lightweight.png
│   ├── cascade_blind_reasoning.png
│   ├── cascade_context_reasoning.png
│   ├── comparison_lightweight.png   # Blind vs Context side-by-side
│   ├── comparison_reasoning.png
│   ├── ovar_lightweight.png         # OVAR bar chart
│   └── ovar_reasoning.png
└── experiment.log
```

Each raw JSON contains: per-period inventory state, every ordering decision with reasoning text, order and demand history arrays, and API call metadata.

---

## 11. Hypotheses

| ID | Hypothesis | Rationale |
|---|---|---|
| H1 | Context OVAR < Blind OVAR at all tiers | Domain knowledge activation produces better-calibrated ordering decisions overall; festive-season anticipation is one expected contributor |
| H2 | Reasoning OVAR ≈ Lightweight OVAR (blind condition) | Without market knowledge, deeper reasoning does not reduce structural amplification |
| H3 | Context Reasoning achieves lowest OVAR | Reasoning model best exploits domain knowledge when it has it |
| H4 | OVAR increases with tier depth in all conditions | Structural cascade: Component OVAR > Ancillary OVAR > OEM OVAR |

---

## 12. Scope and Falsifiability

**This is an exploratory, decision-support experiment — not a causal identification design.**

Each factor is a bundle comparison: context vs. blind compares the full contextual deployment package against a fully stripped one; reasoning vs. lightweight compares each model at its intended operating configuration. Gains cannot be attributed to any single element within a bundle. The experiment answers "which deployment setup performs better?" not "why does it perform better?"

Findings are directional. With 5 runs per config and non-deterministic LLM outputs, the experiment does not have the statistical power for confirmatory claims. Hypotheses use directional language (`<`, `≈`, "lowest") with no pre-specified effect size thresholds. Results should be interpreted as evidence for or against a direction, not as statistically significant differences.

**Minimal decision rubric for reproducibility:**
- H1: Context mean OVAR < Blind mean OVAR at all three tiers.
- H2: Blind-reasoning and blind-lightweight mean OVARs overlap within their respective CV ranges — if ranges overlap, treat as approximately equal.
- H3: Context-reasoning mean OVAR is the lowest of the four conditions when ranked by mean.
- H4: Component mean OVAR > Ancillary mean OVAR > OEM mean OVAR — holds if ordering is strict at all three tiers.

## What Makes This Falsifiable

- Demand series is fixed and identical across all conditions — no randomisation in inputs.
- Starting inventory is identical — no advantage from initial conditions.
- H1 is tested on overall OVAR across all 12 ordering periods. Periods 10–12 (September–November) are an interpretive window — if context agents show lower OVAR concentrated in this window, it indicates domain knowledge is doing the work. If context OVAR is lower but spread uniformly across all periods, the reduction is likely from a different mechanism than seasonal anticipation.
