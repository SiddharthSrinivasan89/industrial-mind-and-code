# The Agentic Bullwhip Effect

Can LLM-powered supply chain agents make smarter ordering decisions when given real-world context — or do they amplify demand distortion just like humans do?

This experiment simulates a 3-tier Indian automotive supply chain where each tier's ordering decisions are made by an LLM agent. We measure how order variance amplifies (or dampens) as it moves upstream, and whether giving agents contextual knowledge about seasons, festivals, and market patterns reduces the distortion.

> **Disclaimer**: This is a personal research project run on a personal Azure subscription. All demand data is synthetic, modelled after real-world patterns in the Indian automotive industry (monthly vehicle dispatches, seasonal trends, festive-period surges). The company "Tatva Motors" and the "Vecta" model are fictional. No proprietary or confidential data was used.

---

## What is the Bullwhip Effect?

The Bullwhip Effect is a well-documented supply chain phenomenon where small fluctuations in consumer demand get progressively amplified as orders move upstream through the supply chain. A 5% increase in retail sales might become a 10% increase at the distributor, a 20% increase at the manufacturer, and a 40% increase at the raw material supplier.

This happens because each participant in the chain makes independent ordering decisions based on incomplete information — they see their immediate customer's orders but not the end-consumer demand. They tend to over-order when demand rises (to build safety stock) and under-order when it falls (to reduce inventory), creating oscillations that grow larger at each step. The result is excess inventory, stockouts, wasted production capacity, and increased costs across the entire chain.

---

## Experiment Setup

### Supply Chain Structure

```
Consumer Demand (Tatva Motors Vecta production targets)
    |
    v
[OEM — Tatva Motors]          Tier 1: Vehicle assembly, orders headlight assemblies
    |
    v
[Lighting Manufacturer]       Tier 2: Assembles LED headlights for the Vecta
    |
    v
[LED Module Supplier]         Tier 3: Produces LED modules and components
```

### Data

13 months of synthetic monthly Vecta dispatches (December 2024 to December 2025), ranging from 36,478 to 59,608 units per month. The data embeds realistic Indian automotive patterns:

- **FY-end push** (March): Elevated dispatches before the April financial year boundary
- **Monsoon dip** (June-July): Reduced dispatches during India's rainy season
- **Festive surge** (September-November): Peak dispatches driven by Navratri, Diwali, and the wedding season

### Configurations

A 2x2 experimental matrix testing two independent variables:

| | **Blind** (no context) | **Context** (dates, product, market) |
|---|---|---|
| **gpt-4.1-mini** (lightweight) | Blind Lightweight | Context Lightweight |
| **o1** (reasoning) | Blind Reasoning | Context Reasoning |

- **Blind agents** see only: current inventory, backlog, orders in transit, demand number, and order history. No dates, no product names, no geography, no costs.
- **Context agents** additionally see: month and year, product details (LED headlight assembly for the Tatva Motors Vecta), market context (India), and are prompted to analyze patterns before ordering.

### Parameters

| Parameter | Value |
|---|---|
| Initial inventory (all tiers) | 23,000 units (~2 weeks buffer) |
| Lead time | 1 month |
| Ordering periods | 13 months |
| Runs per configuration | 3 |
| Order clamps | None — agents can order any non-negative quantity |
| Cost model | None — pure behavioral observation |

### v4 Design Rationale

Previous versions (v2/v3) used 180K initial inventory (~4 months), a 0.2x order floor, and a cost model (₹100 holding / ₹1,000 backlog). v4 strips all of these:

- **No order floor**: Agents can order zero. We observe what they naturally do without guardrails.
- **No cost model**: Costs biased agent reasoning in v3. Without them, ordering behavior reflects the agent's intrinsic supply chain intuition.
- **Low initial inventory (23K)**: Forces agents to order actively from period 1. Eliminates the "inventory illusion" where agents coast on a large buffer and defer ordering.

### Key Metric: OVAR

**Order Variance Amplification Ratio** = Variance(orders placed) / Variance(demand received)

- OVAR = 1.0: No amplification — orders mirror demand variability exactly
- OVAR > 1.0: Bullwhip amplification — orders are more variable than demand
- OVAR < 1.0: Dampening — orders are smoother than demand

---

## Key Findings

_Pending v4 experiment runs._

---

## Assumptions and Limitations

- **Single demand series**: Results reflect one specific demand pattern (moderate seasonality, ~16% coefficient of variation). Different demand volatility or trend shapes may produce different relative rankings.
- **Low initial inventory by design**: 23K starting stock (~2 weeks) forces immediate ordering but may create early stockouts that dominate agent behavior for multiple periods.
- **Simplified chain**: Real supply chains have multiple products, variable lead times, capacity constraints, and information sharing. This model isolates the ordering decision in a clean 3-tier chain.
- **LLM non-determinism**: Even at temperature 0.4, gpt-4.1-mini outputs vary between runs. The o1 model's temperature is fixed at 1.0, adding further variance. Multi-run aggregation (n=3 per config) provides directional signal but not full statistical significance.
- **No cost model**: Agents receive no cost information. Ordering behavior is unconstrained — there's no penalty for over-ordering or under-ordering beyond the natural consequences (stockouts, excess inventory).
- **No order clamps**: Agents can order zero or any large quantity. Results may include extreme values that a real procurement system would reject.

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
│   └── experiment_v2_params.txt      # Historical parameter documentation
├── results/
│   ├── raw/                          # Per-run JSON results
│   ├── aggregated/                   # Cross-run metrics
│   ├── figures/                      # Visualisations
│   └── api_logs_*.json               # API call logs
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
