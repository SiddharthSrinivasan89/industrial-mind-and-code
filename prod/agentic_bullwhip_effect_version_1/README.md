# Agentic Bullwhip Effect

**Research question:** Can LLM agents with domain context reduce the Bullwhip Effect in a 3-tier Indian automotive supply chain?

---

## Overview

A controlled simulation in which each tier of a 3-tier supply chain (OEM → Ancillary → Component) is operated by an LLM agent. The experiment uses a **2×2 factorial design** to isolate the effects of domain context and model capability on order variability amplification.

| Factor | Levels |
|---|---|
| Context | Blind (numbers only) vs Context (company, product, supply chain role) |
| Model | Lightweight (gpt-4.1-mini) vs Reasoning (o1) |

**4 configurations × 5 runs each = 20 total runs**
**720 LLM decisions** (12 ordering periods × 3 tiers × 5 runs × 4 configs)

---

## Supply Chain Structure

```
[Tatva Motors OEM]
    ↓ orders
[Lighting Manufacturer (Ancillary)]
    ↓ orders
[LED Component Manufacturer (Component)]
```

- Demand series: 12 months of real-pattern synthetic Vecta despatch targets (Dec 2024 – Nov 2025)
- Lead time: 1 month at all tiers
- Initial inventory: 43,000 units at all tiers
- Period 13: demand-fulfilment only — no orders placed

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API credentials

Create a `.env` file in this folder (never commit it):

```
OPENAI_API_KEY=your-key-here
OPENAI_BASE_URL=https://your-azure-endpoint.openai.azure.com/
AZURE_API_VERSION=2025-01-01-preview
LIGHTWEIGHT_MODEL=gpt-4.1-mini
REASONING_MODEL=o1
LIGHTWEIGHT_INPUT_COST_PER_1M=0.40
LIGHTWEIGHT_OUTPUT_COST_PER_1M=1.60
REASONING_INPUT_COST_PER_1M=15.00
REASONING_OUTPUT_COST_PER_1M=60.00
```

### 3. Run the experiment

```bash
python src/run_experiment.py
```

Results are written to `results/raw/` (per-run JSON) and `results/aggregated/` (per-config summary JSON).

---

## Key Metrics

### Primary — OVAR (Order Variance Amplification Ratio)

```
OVAR = Var(orders placed) / Var(demand received)
```

Computed per tier over periods 1–12. Values > 1 indicate bullwhip amplification; values < 1 indicate dampening. Reported as mean ± std across 5 runs per config.

### Secondary

| Metric | Description |
|---|---|
| Stockout count | Periods where backlog > 0 after fulfilment |
| Excess inventory | Units on hand above demand at period end |
| Total ordered | Sum of orders placed over 12 periods |
| Peak overshoot | Max order / mean demand |
| Clamp count | Periods where LLM order was negative (clamped to 0) |

### Pattern detection score (v2 — composite)

Measures seasonal awareness at event periods 3, 10, 11, 12 (Union Budget, pre-Dasara, Dasara, Diwali).

- **keyword_score** — fraction of 16 seasonal keywords found in LLM reasoning text
- **elevation_score** — fraction of (tier × event-period) pairs where the agent ordered ≥ 110% of its non-event baseline

```
pattern_score = mean(keyword_score, elevation_score)
```

> **Note:** This definition (v2) changed from the original keyword-only formula after observing models reason arithmetically without verbalising festival names. Results under v1 are not comparable to v2.

### Cost (tracking metric only)

USD cost per run and per config based on token usage × pricing rates from `.env`. Not used in hypothesis testing — included for operational transparency.

---

## Hypotheses

All directional; no pre-specified effect size thresholds. This is an exploratory study.

- **H1:** Context mean OVAR < Blind mean OVAR at all three tiers
- **H2:** Blind-reasoning and blind-lightweight mean OVARs overlap within their CV ranges (context is the determining factor, not model capability)
- **H3:** Context-reasoning achieves the lowest chain-level OVAR
- **H4:** Pattern score: context agents score higher than blind agents at event periods

---

## Project Structure

```
agentic_bullwhip_effect_version_1/
├── .gitignore              # Excludes .env, results/, logs
├── README.md               # This file
├── requirements.txt
├── data/
│   └── synthetic/
│       └── tatva_monthly_dispatches.csv
├── docs/
│   └── experiment_parameters.md   # Full metric and design spec
├── results/
│   ├── aggregated/         # Per-config summary JSONs (4 files)
│   ├── raw/                # Per-run JSONs (20 files)
│   └── analysis_2026-02-27_08-05.md  # Final results analysis
└── src/
    ├── base_agent.py       # OpenAI / Azure OpenAI API wrapper
    ├── blind_agent.py      # Blind treatment prompt builders
    ├── context_agent.py    # Context treatment prompt builders
    ├── inventory_manager.py # Inventory helpers (receive, fulfil)
    ├── supply_chain.py     # TierState + two-phase simulation steps
    └── run_experiment.py   # Main orchestrator — simulation constants defined here
```

---

## Security

- `.env` is gitignored — never commit it
- All API credentials are read from environment variables at runtime
- No keys are hardcoded in source files
