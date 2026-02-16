# Experiment Report: The Agentic Bullwhip Effect

## 1. Research Question

Can LLM-powered supply chain agents make better ordering decisions when given real-world contextual knowledge — product identity, market geography, calendar awareness, and seasonal patterns — or does the information environment have no meaningful effect on demand distortion?

Specifically, this experiment measures whether contextual grounding reduces the **bullwhip effect** (progressive amplification of order variance upstream through a supply chain) in LLM agents, and whether model capability (lightweight vs reasoning) interacts with the information environment to produce qualitatively different ordering behaviors.

---

## 2. Background

### 2.1 The Bullwhip Effect

The bullwhip effect is a well-documented supply chain phenomenon where small fluctuations in end-consumer demand get progressively amplified as orders move upstream. A 5% increase in retail sales can become a 40% increase at the raw material supplier. The classical causes identified by Lee, Padmanabhan, and Whang (1997) are:

1. **Demand signal processing** — each tier forecasts independently from its own observed demand, not from end-consumer data
2. **Order batching** — orders are grouped into periodic batches rather than placed continuously
3. **Price fluctuations** — promotions cause forward-buying
4. **Rationing and shortage gaming** — participants over-order when supply is tight

This experiment isolates the first cause (demand signal processing) by constructing a chain where each tier makes independent ordering decisions based on incomplete information.

### 2.2 Why LLM Agents?

Traditional bullwhip experiments use human participants (the MIT Beer Game) or mathematical models (base-stock policies, (s,S) policies). LLM agents occupy a novel middle ground: they can process numerical state like a mathematical model, but they can also incorporate qualitative context (domain knowledge, seasonal awareness, market understanding) like a human planner. This experiment tests whether that qualitative reasoning capacity translates into better supply chain decisions.

---

## 3. Methodology

### 3.1 Supply Chain Model

A 3-tier linear supply chain simulating the LED headlight assembly supply chain for a fictional Indian automaker (Tatva Motors, Vecta model):

| Tier | Role | Receives demand from | Orders from |
|------|------|---------------------|-------------|
| Tier 1 | OEM (Tatva Motors) | Consumer production targets | Lighting Manufacturer |
| Tier 2 | Lighting Manufacturer | OEM's order quantity | LED Module Supplier |
| Tier 3 | LED Module Supplier | Lighting Mfr's order quantity | Production (infinite capacity) |

**Information asymmetry**: Each tier sees only the orders from its immediate customer. The Lighting Manufacturer does not see consumer demand — it sees the OEM's order quantity, which may be amplified or dampened. The LED Supplier sees only the Lighting Manufacturer's orders, two steps removed from consumer reality.

**No inter-tier communication**: Tiers cannot share forecasts, inventory levels, reasoning, or any other information. This recreates the classical information asymmetry that drives the bullwhip effect.

### 3.2 Demand Data

13 months of synthetic monthly production targets for the Tatva Motors Vecta (December 2024 to December 2025):

| Period | Month | Dispatches | Seasonal Context |
|--------|-------|-----------|-----------------|
| 1 | December 2024 | 43,812 | Year-end |
| 2 | January 2025 | 46,318 | Post-holiday recovery |
| 3 | February 2025 | 47,095 | Steady state |
| 4 | March 2025 | 49,287 | FY-end push |
| 5 | April 2025 | 44,653 | New FY transition |
| 6 | May 2025 | 39,841 | Pre-monsoon slowdown |
| 7 | June 2025 | 36,478 | Monsoon trough |
| 8 | July 2025 | 38,193 | Monsoon continued |
| 9 | August 2025 | 40,756 | Recovery begins |
| 10 | September 2025 | 56,892 | Navratri / festive surge |
| 11 | October 2025 | 59,608 | Diwali peak |
| 12 | November 2025 | 55,347 | Wedding season |
| 13 | December 2025 | 48,491 | Festive wind-down |

**Summary statistics**:
- Total demand: 606,771 units
- Mean monthly demand: 46,675 units
- Standard deviation: 7,093 units
- Coefficient of variation: 15.2%
- Range: 36,478 to 59,608 units

**Embedded patterns**:
- **FY-end push** (March): Elevated dispatches before the April financial year boundary
- **Monsoon dip** (June–July): Reduced dispatches during India's rainy season
- **Festive surge** (September–November): Peak dispatches driven by Navratri, Diwali, and the wedding season
- **Moderate volatility**: CV of ~15% is realistic for Indian automotive monthly dispatches

The data is modelled after publicly available industry patterns (SIAM monthly dispatch data, seasonal indices) but is entirely synthetic. No proprietary data was used.

### 3.3 Experimental Design

A **2 x 2 factorial design** crossing two independent variables:

| Factor | Levels | Description |
|--------|--------|-------------|
| **Information environment** | Blind, Context | What the agent sees in its prompt |
| **Model capability** | Lightweight (gpt-4.1-mini), Reasoning (o1) | The LLM making the decision |

This produces four configurations:

| Configuration | Information | Model | Temperature | Max Tokens |
|---|---|---|---|---|
| Blind Lightweight | Numbers only | gpt-4.1-mini | 0.4 | 600 |
| Blind Reasoning | Numbers only | o1 | 1.0 (fixed) | 16,000 |
| Context Lightweight | Full domain context | gpt-4.1-mini | 0.4 | 600 |
| Context Reasoning | Full domain context | o1 | 1.0 (fixed) | 16,000 |

Each configuration is run **3 times** to provide directional signal and cross-run variance estimates. Total: 12 simulation runs, each spanning 13 ordering periods across 3 tiers = 468 LLM ordering decisions.

### 3.4 Agent Design

#### Blind Agent

The blind agent receives a prompt containing only numerical state:

- Inventory on hand (units)
- Backlog of unfulfilled orders (units)
- Orders currently in transit (quantity and arrival period)
- Lead time (1 month)
- This period's demand (a single number)
- Last 6 order quantities placed

The system prompt is generic: *"You are a supply chain ordering agent. Always respond with valid JSON only."*

The agent has no knowledge of what it is ordering, who it is ordering for, what month or year it is, or what market it operates in. It sees demand as a raw number with no temporal or contextual anchor.

**Expected JSON response**:
```json
{"order_quantity": <number>, "reasoning": "<brief explanation>"}
```

#### Context Agent

The context agent receives everything the blind agent sees, plus:

- **Role identity**: A specific role description (e.g., "Supply Chain Planner at Tatva Motors in India. You manage headlight assembly procurement for the Vecta.")
- **Product**: "LED headlight assembly for the Tatva Motors Vecta"
- **Market**: "India"
- **Calendar**: Month name and year (e.g., "January 2025, period 2")
- **Demand forecast**: 3-month lookahead of upcoming demand (OEM only; downstream tiers receive no forecast)
- **Pattern analysis instruction**: "Before placing your order, analyze the production and ordering data for patterns you recognize — seasonal, cultural, financial calendar, promotional, or otherwise."

The system prompt is domain-grounded: *"You are a supply chain ordering agent in the Indian automotive component industry. Always respond with valid JSON only."*

**Expected JSON response**:
```json
{"pattern_analysis": "<analysis>", "order_quantity": <number>, "reasoning": "<explanation>"}
```

#### Stateless Design

Every ordering decision is an independent, single-turn LLM call. There is no conversation memory, no message history, no chain-of-thought carried across periods. Each period, the agent receives a fresh prompt containing a current-state snapshot and must decide how many units to order.

The agent's only window into its own past is the `order_history` field — the last 6 order quantities as raw numbers, with no accompanying demand context, reasoning trace, or outcome feedback.

This is a deliberate design choice. It isolates the question the experiment asks: *given a snapshot of supply chain state, does contextual knowledge improve a single ordering decision?* A multi-turn conversational agent that accumulates context might perform differently, but would conflate the effects of memory and context.

### 3.5 Inventory Mechanics

Each tier's inventory is managed by an `InventoryManager` that processes each period in three deterministic steps:

1. **Receive deliveries**: Orders placed in prior periods arrive after the lead time (1 month). The order quantity is added to inventory.
2. **Fulfill demand**: The tier attempts to satisfy incoming demand plus any accumulated backlog from prior periods. If inventory is sufficient, the full amount is fulfilled and inventory is decremented. If insufficient, the tier fulfills as much as possible, records a stockout, and carries the unfulfilled portion as backlog into the next period.
3. **Place order**: The agent's order quantity is placed in transit, to arrive next period.

**Key mechanics**:
- Lead time is fixed at 1 month (orders placed in period N arrive in period N+1)
- There is no capacity constraint — upstream supply is infinite
- There is no partial fulfillment signaling — the downstream tier does not know how much of its order was filled vs backordered
- Backlog accumulates and must be fulfilled before new demand
- All arithmetic is exact integer operations — no stochastic elements in the simulation itself

### 3.6 Experiment Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Initial inventory (all tiers) | 23,000 units | ~2 weeks of average monthly demand (~46,700). Forces active ordering from period 1. Eliminates the "inventory illusion" where agents coast on a large buffer. |
| Lead time | 1 month | Single-period lead time simplifies the decision problem. Orders placed now arrive next period. |
| Ordering periods | 13 months | Covers a full Indian fiscal year cycle including all major seasonal patterns. |
| Runs per configuration | 3 | Provides directional signal and variance estimates. Not sufficient for statistical significance — this is acknowledged as a limitation. |
| Order floor | None | Agents can order zero units. |
| Order ceiling | None | Agents can order any quantity. The only validation is clamping negative orders to zero. |
| Cost model | None | No holding cost, no backlog penalty. Agents receive no cost feedback. Ordering behavior reflects intrinsic supply chain intuition rather than penalty avoidance. |
| Forecast horizon (OEM only) | 3 months | The OEM sees upcoming demand for the next 3 periods. Downstream tiers receive no forecast. |
| Order history window | 6 periods | Agents see their last 6 order quantities (no demand or outcome context). |

### 3.7 Primary Metric: OVAR

**Order Variance Amplification Ratio**:

```
OVAR = Variance(orders placed by tier) / Variance(demand received by tier)
```

- **OVAR = 1.0**: No amplification — orders mirror demand variability exactly
- **OVAR > 1.0**: Bullwhip amplification — orders are more variable than incoming demand
- **OVAR < 1.0**: Dampening — orders are smoother than incoming demand

OVAR is computed per tier, per run, then averaged across the 3 runs per configuration. Standard deviation across runs provides a stability estimate.

### 3.8 Secondary Metrics

| Metric | Definition | Purpose |
|--------|-----------|---------|
| **Stockout count** | Number of periods (out of 13) where a tier cannot fully fulfill demand + backlog | Measures service level |
| **Excess inventory** | Sum of (inventory - demand) across periods where inventory exceeds demand | Measures over-ordering waste |
| **Total ordered** | Sum of all orders placed across 13 periods | Compared against total demand (606,771) to measure systematic over/under-ordering |
| **Peak overshoot** | Max single-period order / max single-period demand | Measures worst-case order spike |
| **Recovery speed** | Number of periods until a tier achieves consecutive stockout-free operation | Measures how quickly agents adapt to the initial inventory deficit |

### 3.9 Execution Environment

- **Platform**: Azure OpenAI Service (Azure AI Foundry)
- **Lightweight model**: gpt-4.1-mini, temperature 0.4, max_tokens 600
- **Reasoning model**: o1, temperature 1.0 (fixed by API, not configurable), max_completion_tokens 16,000
- **Rate limiting**: 1s inter-call delay for gpt-4.1-mini, 5s for o1
- **Retry policy**: 3 attempts with exponential backoff on API failure
- **Response format**: JSON parsed from LLM text output (handling markdown fences, comma-formatted numbers, freetext preamble)

---

## 4. Assumptions

### 4.1 Supply Chain Assumptions

1. **Linear, single-product chain**: One SKU (LED headlight assembly) flows through three tiers. Real supply chains involve hundreds of SKUs with shared capacity, substitution, and multi-sourcing.
2. **Fixed lead time**: 1 month, deterministic. Real lead times are variable and often demand-dependent.
3. **Infinite upstream capacity**: The LED Supplier's orders are always fulfilled. There is no capacity constraint, no supply shortage, and no allocation mechanism.
4. **No partial shipment signaling**: Tiers do not know whether their orders were fully fulfilled or backordered by the upstream tier. They only observe their own inventory changes.
5. **No inter-tier communication**: Tiers share no information. In practice, supply chains increasingly share forecasts, inventory positions, and collaborative planning data.
6. **No demand shaping**: Tiers cannot negotiate order quantities, delay shipments, or split orders across periods.
7. **Period-based ordering**: One ordering decision per tier per month. No continuous replenishment or event-driven ordering.

### 4.2 Agent Assumptions

1. **Stateless**: No memory across periods. Each decision is independent.
2. **Single-turn**: No iterative reasoning, no self-correction, no reflection on past decisions.
3. **Honest reporting**: The agent always receives accurate state data (inventory, backlog, in-transit). There is no noise, no reporting delay, and no measurement error.
4. **JSON compliance**: Agents are instructed to respond with JSON only. The inference layer has robust parsing to handle non-compliant responses (markdown fences, preamble text).
5. **No strategic behavior**: Agents do not anticipate the behavior of other tiers. Each agent optimises its own ordering decision in isolation.

### 4.3 Experimental Assumptions

1. **Representativeness of demand**: The 13-month synthetic series captures major Indian automotive seasonal patterns (monsoon, festive, FY-end) but represents a single demand trajectory. Different demand shapes (high volatility, trending, shock events) might produce different relative rankings.
2. **Model availability**: The experiment depends on specific Azure OpenAI model deployments (gpt-4.1-mini, o1). Model behavior may change across API versions.
3. **Temperature effects**: gpt-4.1-mini at temperature 0.4 provides some stochasticity; o1's temperature is fixed at 1.0 by the API. Cross-run variance captures this non-determinism but 3 runs per configuration provide directional signal only, not statistical significance.
4. **Prompt design**: Results are specific to the prompt templates used. Different prompt structures, instructions, or framing could produce different behaviors.

---

## 5. Results Summary

### 5.1 OVAR Scorecard

Mean OVAR across 3 runs (standard deviation in parentheses):

| Configuration | OEM | Lighting Mfr | LED Supplier |
|---|---|---|---|
| Blind Lightweight | 1.30 (0.44) | 1.56 (0.80) | 2.61 (1.22) |
| Blind Reasoning | **10.47** (4.06) | 2.39 (0.98) | 2.31 (2.02) |
| Context Lightweight | 3.60 (1.91) | 3.19 (0.89) | 3.73 (1.09) |
| Context Reasoning | **1.50** (0.11) | 6.42 (2.11) | 2.93 (2.02) |

### 5.2 Stockout Performance

Mean stockout periods out of 13:

| Configuration | OEM | Lighting Mfr | LED Supplier |
|---|---|---|---|
| Blind Lightweight | 13.0 | 12.7 | 11.0 |
| Blind Reasoning | 7.3 | 8.0 | 8.0 |
| Context Lightweight | 5.3 | 3.3 | 4.0 |
| Context Reasoning | **1.0** | **1.7** | **2.7** |

### 5.3 Total Ordering vs Total Demand (606,771 units)

| Configuration | OEM | Lighting Mfr | LED Supplier |
|---|---|---|---|
| Blind Lightweight | 598,640 (-1%) | 608,324 (+0%) | 621,324 (+2%) |
| Blind Reasoning | 644,959 (+6%) | 660,293 (+9%) | 678,016 (+12%) |
| Context Lightweight | 656,382 (+8%) | 788,666 (+30%) | **1,029,060 (+70%)** |
| Context Reasoning | 634,057 (+4%) | 666,667 (+10%) | 727,333 (+20%) |

### 5.4 Recovery Speed

| Configuration | Periods to OEM Stockout-Free | Periods to Full Chain Stockout-Free |
|---|---|---|
| Blind Lightweight | Never (13/13 stockout) | Never |
| Blind Reasoning | ~11 periods | Never (supplier: 8/13) |
| Context Lightweight | ~6 periods | ~4 periods |
| Context Reasoning | **1 period** | **~3 periods** |

### 5.5 Bullwhip Cascade Patterns

| Configuration | OEM → Mfr → Supplier | Pattern |
|---|---|---|
| Blind Lightweight | 1.30 → 1.56 → 2.61 | Classical (progressive amplification) |
| Blind Reasoning | 10.47 → 2.39 → 2.31 | Inverted (OEM spike, downstream dampening) |
| Context Lightweight | 3.60 → 3.19 → 3.73 | Flat (consistent across tiers) |
| Context Reasoning | 1.50 → 6.42 → 2.93 | Mid-chain spike |

---

## 6. Key Findings

### 6.1 The Pass-Through Illusion

Blind Lightweight achieves the lowest OEM OVAR (1.30) but stocks out in all 13 periods across all 3 runs. Its low OVAR is an artifact of passivity: the agent mirrors demand as orders without adding safety stock or recovery logic. It transmits demand faithfully while failing to fulfill any order in full. Low OVAR without service-level context is misleading.

### 6.2 Reasoning Without Context Is Dangerous

Blind Reasoning produces the worst OEM OVAR in the experiment: 10.47 — nearly 7x worse than Context Reasoning. The o1 model detects patterns in noise, overcorrects aggressively, and oscillates between extremes (106,513 units in one period, near-zero the next). Reasoning capacity without contextual grounding becomes a source of volatility rather than stability.

### 6.3 Context Without Reasoning Creates Inventory Bloat

Context Lightweight recognises seasonal patterns but lacks the capacity to moderate its response. The LED Supplier orders 1,029,060 units over 13 months — 70% above total consumer demand. Single-period orders reached 268,154 units against ~47,000 consumer demand. Context without reasoning produces a chain that avoids stockouts but drowns in inventory.

### 6.4 Context Plus Reasoning Is the Only Viable Configuration

Context Reasoning achieves OEM OVAR of 1.50 (std = 0.11, tightest in experiment) with only 1.0/13 OEM stockouts. It recovers from the initial inventory deficit in a single period by deliberately front-loading 67,130 units against 43,812 demand, then tracking demand stably for the remaining 12 periods. Total upstream over-ordering is 20% — elevated but controlled.

### 6.5 Non-Classical Bullwhip Patterns

Only Blind Lightweight follows the textbook progressive amplification pattern. The other three configurations produce non-classical patterns: inverted (Blind Reasoning), flat (Context Lightweight), and mid-chain spike (Context Reasoning). LLM agents distort demand differently than human participants — the pattern depends on where the most reactive agent sits and what information it has, not on the classical information-asymmetry dynamics.

### 6.6 The Interaction Effect

The most important finding is that the interaction between model capability and information environment matters more than either factor alone. The most capable model (o1) produces the worst outcome when deployed blind, and the least capable model (gpt-4.1-mini) produces the most stable (if useless) outcome when deployed blind. Neither "better model" nor "more information" is independently sufficient — it is the combination that produces viable performance.

---

## 7. Limitations

### 7.1 Statistical Power

With n=3 runs per configuration, results provide directional signal but not statistical significance. Standard deviations on key metrics remain high (Blind Reasoning OEM OVAR: 10.47 ± 4.06). Larger sample sizes would be needed for hypothesis testing.

### 7.2 Single Demand Series

All results reflect one specific demand pattern with moderate seasonality (~15% CV). Different demand characteristics — higher volatility, trend, structural breaks, demand shocks — could produce different relative rankings between configurations.

### 7.3 Prompt Sensitivity

Agent behavior is shaped by prompt design. The specific framing of the context prompt (Indian market, Vecta product, seasonal awareness instruction) may produce different results with different prompt structures. The findings reflect this particular prompt design, not a universal property of LLM-based supply chain agents.

### 7.4 Stateless Design

The stateless single-turn design prevents agents from learning within a run. A multi-turn conversational agent with episodic memory might produce less oscillation, particularly for the reasoning model which appears to benefit most from additional context.

### 7.5 Simplified Chain

The 3-tier, single-product, fixed-lead-time chain is a controlled experimental setup, not a realistic supply chain model. Real-world applicability would require validation with multiple products, variable lead times, capacity constraints, and information-sharing mechanisms.

### 7.6 No Cost Model

Agents receive no cost information. Without penalties for over-ordering or stockouts, agent behavior reflects intrinsic ordering intuition rather than optimised cost-service tradeoffs. A cost-aware agent might significantly reduce the inventory bloat observed in Context Lightweight.

### 7.7 Model Non-Determinism

gpt-4.1-mini at temperature 0.4 produces variable outputs across runs. The o1 model's temperature is fixed at 1.0 by the API, adding further variance. This non-determinism is an inherent property of LLM-based decision agents and represents a deployment consideration beyond the scope of this experiment.

---

## 8. Reproducibility

### 8.1 Running the Experiment

```bash
cd dev/bullwhip-effect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

Execute:
```bash
cd src

# Single configuration, 1 validation run
python run_experiment.py --category blind --model lightweight --runs 1

# Single configuration, 3 runs
python run_experiment.py --category context --model reasoning --runs 3

# All 4 configurations (12 runs total)
python run_experiment.py --all

# Analyse existing results (no API calls)
python run_experiment.py --analyze
```

### 8.2 Output Structure

```
results/
├── raw/                          # Per-run JSON: full decision traces, agent reasoning
│   ├── blind_lightweight_run01.json
│   ├── blind_lightweight_run02.json
│   ├── blind_lightweight_run03.json
│   ├── blind_reasoning_run01.json
│   ├── ...
│   └── context_reasoning_run03.json
├── aggregated/                   # Cross-run mean/std metrics
│   ├── blind_lightweight_aggregated.json
│   ├── blind_reasoning_aggregated.json
│   ├── context_lightweight_aggregated.json
│   └── context_reasoning_aggregated.json
├── figures/                      # Visualizations
│   ├── cascade_*.png             # Order cascade per configuration
│   ├── comparison_*.png          # Blind vs Context overlay
│   ├── ovar_*.png                # OVAR bar charts
│   └── architecture_*.png        # System architecture diagrams
└── experiment.log                # Execution log
```

### 8.3 Raw Data Inspection

Each raw JSON file contains, for every tier:
- `period_records`: Per-period inventory state (before/after), deliveries, fulfillment, backlog, stockout flag
- `decisions`: The LLM's order quantity, reasoning text, pattern analysis (context agents), and whether any clamping was applied
- `orders_placed`: Array of order quantities across all periods
- `incoming_demands`: Array of demand received across all periods
- `inventory_levels`: Array of end-of-period inventory levels
- `stockout_periods`: List of period numbers where a stockout occurred

### 8.4 Known Reproducibility Constraints

1. **LLM non-determinism**: Even with identical prompts and parameters, LLM outputs vary between calls. Results will not be numerically identical across re-runs.
2. **Model versioning**: Azure OpenAI model deployments may be updated. Behavior observed with a specific model checkpoint may not replicate with a newer deployment.
3. **Rate limits**: Azure subscription tier affects available throughput. The experiment uses inter-call delays (1s lightweight, 5s reasoning) to respect rate limits.

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **OVAR** | Order Variance Amplification Ratio. Variance of orders placed divided by variance of demand received. Measures bullwhip amplification. |
| **Bullwhip effect** | Progressive amplification of order variance as orders move upstream through a supply chain. |
| **Stockout** | A period where a tier cannot fully fulfill incoming demand plus backlog from available inventory. |
| **Backlog** | Accumulated unfulfilled demand carried forward from prior periods. Must be satisfied before new demand. |
| **Lead time** | Time between placing an order and receiving delivery. Fixed at 1 month in this experiment. |
| **Blind agent** | An agent that sees only numerical state: inventory, backlog, in-transit orders, demand, and order history. No domain context. |
| **Context agent** | An agent that additionally sees role identity, product details, market geography, calendar, forecast, and a pattern-analysis instruction. |
| **Tier** | A stage in the supply chain. Tier 1 = OEM (closest to consumer), Tier 3 = raw material supplier (furthest from consumer). |
| **OEM** | Original Equipment Manufacturer. In this experiment, Tatva Motors — the vehicle assembler that receives consumer production targets. |
| **Cascade** | The sequential flow of ordering decisions through the supply chain: OEM → Lighting Mfr → LED Supplier. |
| **Front-loading** | Deliberately ordering more than current demand to build buffer inventory, typically observed in the first 1–3 periods. |
| **CV** | Coefficient of Variation. Standard deviation divided by mean, expressed as a percentage. Measures relative volatility. |
