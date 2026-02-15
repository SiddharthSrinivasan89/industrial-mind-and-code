# The Agentic Bullwhip Effect

Can LLM-powered supply chain agents make smarter ordering decisions when given real-world context — or do they amplify demand distortion just like humans do?

This experiment simulates a 3-tier Indian automotive supply chain where each tier's ordering decisions are made by an LLM agent. We measure how order variance amplifies (or dampens) as it moves upstream, and whether giving agents contextual knowledge about seasons, festivals, and market patterns reduces the distortion.

> **Disclaimer**: This is a personal research project run on a personal Azure subscription. All demand data is synthetic, modelled after real-world patterns in the Indian automotive industry (monthly vehicle dispatches, seasonal trends, festive-period surges). The company "Tatva Motors" is fictional. No proprietary or confidential data was used. Current results in `results/` are from pre-fix run01 (n=1). The v3 experiment design calls for 3 runs per configuration with methodology fixes applied.

---

## What is the Bullwhip Effect?

The Bullwhip Effect is a well-documented supply chain phenomenon where small fluctuations in consumer demand get progressively amplified as orders move upstream through the supply chain. A 5% increase in retail sales might become a 10% increase at the distributor, a 20% increase at the manufacturer, and a 40% increase at the raw material supplier.

This happens because each participant in the chain makes independent ordering decisions based on incomplete information — they see their immediate customer's orders but not the end-consumer demand. They tend to over-order when demand rises (to build safety stock) and under-order when it falls (to reduce inventory), creating oscillations that grow larger at each step. The result is excess inventory, stockouts, wasted production capacity, and increased costs across the entire chain.

---

## Experiment Setup

### Supply Chain Structure

```
Consumer Demand (Tatva Motors dispatches)
    |
    v
[OEM — Tatva Motors]          Tier 1: Vehicle assembly plant
    |  orders lighting assemblies
    v
[Lighting Manufacturer]       Tier 2: Headlamps, tail lamps, DRLs
    |  orders LED components
    v
[LED/Component Supplier]      Tier 3: Raw LED chips and subassemblies
```

### Data

13 months of synthetic monthly vehicle dispatches (December 2024 to December 2025), ranging from 36,478 to 59,608 units per month. The data embeds realistic Indian automotive patterns:

- **FY-end push** (March): Elevated dispatches before the April financial year boundary
- **Monsoon dip** (June-July): Reduced dispatches during India's rainy season
- **Festive surge** (September-November): Peak dispatches driven by Navratri, Diwali, and the wedding season

### Configurations

A 2x2 experimental matrix testing two independent variables:

| | **Blind** (no context) | **Context** (dates, product, market) |
|---|---|---|
| **gpt-4.1-mini** (lightweight) | Blind Lightweight | Context Lightweight |
| **o1** (reasoning) | Blind Reasoning | Context Reasoning |

- **Blind agents** see only: current inventory, backlog, orders in transit, demand history, and a demand forecast. No dates, no product names, no geography.
- **Context agents** additionally see: month and year, product details (automotive lighting for Tatva Motors vehicles), market context (India), and are prompted to analyze patterns before ordering.

### Parameters

| Parameter | Value |
|---|---|
| Initial inventory (all tiers) | 180,000 units (~4 months buffer) |
| Lead time | 1 month |
| Ordering periods | 13 months |
| Runs per configuration | 3 |

### Key Metric: OVAR

**Order Variance Amplification Ratio** = Variance(orders placed) / Variance(demand received)

- OVAR = 1.0: No amplification — orders mirror demand variability exactly
- OVAR > 1.0: Bullwhip amplification — orders are more variable than demand
- OVAR < 1.0: Dampening — orders are smoother than demand

---

## Key Findings (run01 — pre-fix, n=1)

> **Note**: The findings below are from run01 (single run, pre-methodology-fix). The blind agent system prompt leaked context and the 0.2x order floor was not enforced during these runs (see [Methodology Fixes](#methodology-fixes-post-run01)). Treat these as preliminary observations. Updated results from v3 (3 runs per config, costs, fixed prompts) will replace this section.

### 1. Domain context matters more than model capability

| Tier | Blind LW | Blind Reasoning | Context LW | Context Reasoning |
|---|:---:|:---:|:---:|:---:|
| OEM | 0.99 | 8.05 | **0.76** | 7.71 |
| Lighting Mfr | 19.46 | 2.08 | **3.16** | 2.90 |
| LED Supplier | 1.00 | 0.82 | 1.79 | **0.64** |
| **Avg OVAR** | 7.15 | 3.65 | **1.91** | 3.75 |

The cheapest configuration (gpt-4.1-mini with context) is the best overall performer. Context gave an 84% OVAR reduction at the Lighting Manufacturer for the lightweight model. The most expensive configuration (o1 with context, 86K tokens, ~15 min wall time) ranked third.

### 2. The reasoning model (o1) creates a worse bullwhip at the OEM tier

o1 ordered zero at the OEM for months 1 and 2 in both blind and context configurations. Its reasoning: "180K inventory covers near-term demand, avoid holding costs." This is locally rational but created a delayed demand signal downstream, pushing OEM OVAR from ~1.0 (lightweight) to ~8.0 (o1).

In the blind reasoning configuration, the OEM ran inventory down to just 67 units in month 11 — one forecast miss from a stockout. The context reasoning configuration was slightly less extreme, with a minimum of 2,160 units in month 12.

### 3. The "inventory illusion" is the dominant failure mode

Large initial inventory (180K units, ~4 months of buffer) created a false sense of security across all blind agents and both o1 configurations. The Lighting Manufacturer repeatedly saw abundant stock and skipped replenishment, then panic-ordered when inventory ran critically low.

| Config | Lighting Mfr zero-order months | Largest single order | Stockout months |
|---|:---:|:---:|:---:|
| Blind LW | 3 (months 1, 3, 4) | 109,808 (month 10) | 8 (months 6-13) |
| Blind Reasoning | 6 (months 1-6) | 75,000 (month 9) | 1 (month 9) |
| Context LW | 0 | 60,000 (month 10) | 0 |
| Context Reasoning | 7 (months 1-5, 7, 8) | 100,000 (month 9) | 2 (months 9, 10) |

Only the context lightweight agent avoided this pattern entirely — zero stockouts and zero skipped orders across all 13 months.

### 4. The bullwhip is not progressive across tiers

Textbook bullwhip theory predicts monotonically increasing amplification at each upstream tier. Our results show a different pattern: the amplification concentrates at the Lighting Manufacturer (tier 2) rather than growing steadily upstream. The OEM either dampens or amplifies depending on the model, and the LED Supplier mostly echoes or dampens.

### 5. Context makes the lightweight model beneficially "suggestible"

The context-aware gpt-4.1-mini agent detected seasonal patterns (Navratri/Diwali, monsoon, FY-end) and acted on them proactively — building buffer before the September-November surge, reducing orders during the monsoon dip. Pattern detection scores ranged from 6/14 (OEM) to 9/14 (Lighting Mfr and LED Supplier).

The o1 model also detected these patterns (scoring 9/14 at the OEM) but reasoned past them, treating seasonal context as one factor among many and ultimately discounting it in favour of inventory optimisation logic.

### 6. Cost-performance inversion

| Config | Avg OVAR | Tokens | Wall Time | Relative Cost |
|---|:---:|:---:|:---:|:---:|
| Context Lightweight | **1.91** | 23,591 | 141s | Low |
| Blind Reasoning | 3.65 | 60,630 | 836s | High |
| Context Reasoning | 3.75 | 86,435 | 915s | Highest |
| Blind Lightweight | 7.15 | 12,689 | 85s | Lowest |

Spending 7x more on tokens and using a stronger reasoning model does not guarantee better supply chain outcomes. The right domain context with a cheaper model outperforms raw reasoning capability without context.

---

## Assumptions and Limitations

- **Single demand series**: Results reflect one specific demand pattern (moderate seasonality, ~16% coefficient of variation). Different demand volatility or trend shapes may produce different relative rankings.
- **Fixed initial inventory**: The 180K starting buffer (~4 months) disproportionately triggers the inventory illusion. Lower initial inventory would force earlier ordering and may change the dynamics.
- **Simplified chain**: Real supply chains have multiple products, variable lead times, capacity constraints, and information sharing. This model isolates the ordering decision in a clean 3-tier chain.
- **LLM non-determinism**: Even at temperature 0.4, gpt-4.1-mini outputs vary between runs. The o1 model's temperature is fixed at 1.0, adding further variance. Multi-run aggregation (n=3 per config) provides directional signal but not full statistical significance.
- **Cost model is prompt-only**: Agents are told the ₹100/₹1,000 holding/backlog costs and the 10:1 asymmetry, but there is no reward function — the trade-off is left to the LLM's judgement. Financial impact is computed post-hoc from inventory and backlog records.

### Methodology Fixes (post-run01)

The following issues were identified during peer review and have been patched in the codebase. **Existing run01 results in `results/` predate these fixes and should be re-run for valid comparisons.**

1. **Blind agent system prompt leaked context.** The base system prompt contained "Indian automotive component industry", giving blind agents geography and product context. Fixed: blind agents now receive a generic system prompt; only context agents receive the domain-specific one.
2. **0.2x minimum order floor was not enforced.** The spec documented a 20%-of-demand floor to prevent zero orders, but the implementation only enforced a ceiling clamp. Fixed: orders below 0.2x demand are now clamped upward (when demand > 0).

---

## How to Run

### Prerequisites

```bash
cd dev/bullwhip-effect
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your Azure OpenAI credentials:

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Running Experiments

```bash
cd src

# Single config, 1 validation run
python run_experiment.py --category blind --model lightweight --runs 1

# Single config, 3 runs
python run_experiment.py --category context --model lightweight --runs 3

# All 4 configurations (2 x 2 x 3 = 12 runs)
python run_experiment.py --all

# Analyse existing results only (no API calls)
python run_experiment.py --analyze
```

### Output

Results are written to `results/`:
- `raw/` — Per-run JSON with full decision records and agent reasoning
- `aggregated/` — Mean/std metrics across runs
- `figures/` — Cascade plots, OVAR bar charts, blind-vs-context comparisons
- `api_logs_*.json` — Full API call logs with latency and token usage

---

## Repository Structure

```
bullwhip-effect/
├── config/
│   └── experiment_config.yaml        # Azure, model, and experiment parameters
├── data/
│   ├── tatva_monthly_dispatches.csv  # 13-month demand series (primary input)
│   ├── real/                         # Reference real-world data
│   └── synthetic/                    # Generated demand datasets
├── docs/
│   └── experiment_v2_params.txt      # Detailed parameter documentation
├── results/
│   ├── raw/                          # Per-run JSON results (4 files)
│   ├── aggregated/                   # Cross-run metrics (4 files)
│   ├── figures/                      # Visualisations (8 PNG files)
│   └── api_logs_*.json               # API call logs (4 files)
├── src/
│   ├── run_experiment.py             # Main orchestrator, metrics, and plotting
│   ├── supply_chain.py               # 3-tier simulation runner
│   ├── base_agent.py                 # Abstract agent with shared logic
│   ├── blind_agent.py                # Context-blind ordering agent
│   ├── context_agent.py              # Context-aware ordering agent
│   ├── inventory_manager.py          # Per-tier inventory tracking
│   └── foundry_client.py             # Azure OpenAI client wrapper
├── generate_synthetic_demand.py      # Demand data generator
├── generate_synthetic_tata_sales.py  # Sales data generator
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```
