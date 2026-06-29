# Agentic Bullwhip Effect — Version 2: LLM Agents Against Heuristic Baselines in Supply Chain Replenishment

## Abstract

This experiment tested whether any LLM ordering agent — across lightweight and reasoning tiers, frontier and local deployments — could match the performance of a simple deterministic heuristic on supply chain order variance and stockout frequency in a three-tier serial supply chain. Across 20 replications per LLM configuration and three heuristic baselines, every heuristic outperformed every LLM configuration on both primary metrics simultaneously. Exponential smoothing (OVAR 0.54, 5 stockouts) produced results approximately 8x better than the best LLM configuration (OVAR 4.33, 41 stockouts) on both dimensions at once. All seven hypotheses were rejected.

---

## Research Question

Do LLM ordering agents — across lightweight and reasoning model tiers, frontier and local backends, and with or without business context — outperform simple deterministic heuristics on order variance and stockout frequency in a single-product, three-tier supply chain replenishment task?

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
| Demand series | 25 months, Jan 2025 to Jan 2027 (single SKU, two full Indian festive cycles) |
| Active ordering periods | 24 |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | 43,609 units (mean + 1.65 sigma, ~95% service level) |
| Possible stockout periods | 75 (25 periods x 3 tiers) |

All scenarios, companies, products, and supply chain structures are fictional. No proprietary data was used.

### Conditions and Models

The experiment used a 2x2 factorial design (model tier x context treatment) replicated across two backends (frontier and local), producing 8 backend-specific model-condition cells plus 3 deterministic heuristic baselines.

**Models:**

| Tier | Frontier (Azure) | Local (Ollama) |
|---|---|---|
| Lightweight | gpt-4.1-mini | phi4:14b |
| Reasoning | o4-mini | gpt-oss:120b |

**Context treatments:**

| Treatment | Prompt contents |
|---|---|
| Blind | Numbers only. No tier persona, no calendar month. |
| Context | Tier persona + calendar month, same numeric state variables as blind. |

**Heuristic baselines (deterministic, 1 run each):**

| Heuristic | Description |
|---|---|
| Exponential smoothing | alpha = 0.30 |
| Naive passthrough | Order exactly what was received from downstream |
| Order-up-to | Fixed safety stock target |

**Agent design:** Stateless. No memory between ordering periods. This design was deliberate: most production agentic deployments are stateless.

**Replications:** 20 per LLM configuration, 1 per heuristic (deterministic). Total LLM calls: 11,520 (4 conditions x 20 runs x 24 periods x 3 tiers x 2 backends).

**Minimum Practically Relevant Difference (MPRD):** |delta OVAR| >= 0.5 required for a practically meaningful claim between LLM configurations. Differences below this threshold are not treated as substantively significant.

### Hypotheses

| Label | Null Hypothesis | Alternative Hypothesis |
|---|---|---|
| H1 | No LLM configuration achieves lower OVAR than exponential smoothing with <= 5 stockouts | At least one LLM achieves OVAR < 0.54 with <= 5 stockouts |
| H2 | context_lightweight OVAR does not differ from blind_lightweight by >= 0.5 | context_lightweight OVAR < blind_lightweight OVAR by >= 0.5 (MPRD) |
| H3 | context_reasoning OVAR does not differ from blind_reasoning by >= 0.5 | context_reasoning OVAR < blind_reasoning OVAR by >= 0.5 (MPRD) |
| H4 | blind_reasoning OVAR does not differ from blind_lightweight by >= 0.5 | blind_reasoning OVAR < blind_lightweight OVAR by >= 0.5 (MPRD) |
| H5 | context_reasoning OVAR does not differ from context_lightweight by >= 0.5 | context_reasoning OVAR < context_lightweight OVAR by >= 0.5 (MPRD) |
| H6 | Context benefit is not larger for reasoning tier than lightweight | The OVAR improvement from context is larger for reasoning-tier models than lightweight models |
| H7 | Local context_lightweight is not within +/- 0.5 OVAR of frontier context_lightweight | Local and frontier context_lightweight configurations produce equivalent OVAR (within MPRD bounds) |

---

## Results

### Key Metrics

**Primary metrics — always reported together:**

```
OVAR = Var(orders placed) / Var(demand received)
```

Computed per tier; chain OVAR is the arithmetic mean across three tiers. Values below 1.0 indicate dampening; values above 1.0 indicate bullwhip amplification. Reported as mean ± std across 20 runs per LLM configuration.

Stockout count: number of tier-periods where backlog > 0 after fulfilment (out of 75 possible per run).

Both metrics are always reported together. A configuration that reduces OVAR at the cost of more stockouts, or reduces stockouts at the cost of higher OVAR, is not treated as an improvement.

### Results Tables

**Heuristic baselines**

| Heuristic | Chain OVAR | Stockouts (of 75 possible) |
|---|---|---|
| Exponential smoothing | 0.54 | 5 |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

**Chain-average OVAR by LLM configuration (mean ± std)**

| Condition | Backend | Chain OVAR (mean ± std) | Stockouts (mean ± std) |
|---|---|---|---|
| exp_smoothing | HEURISTIC | 0.54 | 5 |
| naive_passthrough | HEURISTIC | 1.00 | 3 |
| order_up_to | HEURISTIC | 1.71 | 14 |
| L-Blind | FRONTIER | 4.70 ± 0.14 | 40.5 ± 0.83 |
| L-Context | FRONTIER | 4.47 ± 0.07 | 39.0 ± 0.83 |
| L-Blind | LOCAL | 4.33 ± 0.00 | 41.0 ± 0.00 |
| L-Context | LOCAL | 6.35 ± 2.53 | 37.2 ± 3.11 |
| R-Blind | FRONTIER | 4.72 ± 1.12 | 42.9 ± 3.85 |
| R-Context | FRONTIER | 4.52 ± 0.08 | 40.1 ± 0.85 |
| R-Blind | LOCAL | 4.52 ± 0.00 | 40.0 ± 0.00 |
| R-Context | LOCAL | 4.52 ± 0.05 | 39.6 ± 0.76 |

L = Lightweight (gpt-4.1-mini / phi4:14b). R = Reasoning (o4-mini / gpt-oss:120b).

**OVAR by tier**

| Condition | Backend | OEM | Ancillary | Component |
|---|---|---|---|---|
| exp_smoothing | HEURISTIC | 0.41 | 0.65 | 0.58 |
| L-Blind | FRONTIER | 4.21 | 6.64 | 3.25 |
| L-Context | FRONTIER | 4.12 | 6.01 | 3.30 |
| L-Blind | LOCAL | 3.71 | 5.89 | 3.40 |
| L-Context | LOCAL | 4.62 | 10.82 | 3.61 |
| R-Blind | FRONTIER | 5.94 | 5.18 | 3.05 |
| R-Context | FRONTIER | 4.13 | 5.99 | 3.45 |
| R-Blind | LOCAL | 4.13 | 5.98 | 3.45 |
| R-Context | LOCAL | 4.13 | 6.01 | 3.43 |

### Hypothesis Verdicts

| Hypothesis | Prediction | Actual result | Verdict |
|---|---|---|---|
| H1 | At least one LLM achieves lower OVAR than exp smoothing with <= 5 stockouts | Best LLM: OVAR 4.33, 41 stockouts | REJECTED |
| H2 | context_lightweight OVAR < blind_lightweight by >= 0.5 | Actual delta = 0.23, below MPRD | REJECTED |
| H3 | context_reasoning OVAR < blind_reasoning by >= 0.5 | Actual delta = 0.20, below MPRD | REJECTED |
| H4 | blind_reasoning OVAR < blind_lightweight by >= 0.5 | Actual delta = -0.02, opposite direction | REJECTED |
| H5 | context_reasoning OVAR < context_lightweight by >= 0.5 | Actual delta = -0.05, opposite direction | REJECTED |
| H6 | Context benefit larger for reasoning tier than lightweight | Actual: -0.03, opposite direction | REJECTED |
| H7 | Local context_lightweight within +/- 0.5 of frontier context_lightweight | Actual delta = 1.88, outside equivalence bounds | REJECTED |

---

## Discussion

The bullwhip failure is structural. Each agent sees only the current period's state with no memory of what it ordered previously. Without that causal chain, there is no self-correction mechanism. A stateless agent that over-ordered last period arrives at the next period without knowing it did. Combined with the fact that LLMs generate plausible text rather than numerically optimised outputs, the result is an agent that selects a number that sounds reasonable rather than one that dampens variance.

Exponential smoothing carries one weighted average forward and partially self-corrects from period to period. That single state variable — unavailable to a stateless LLM agent — accounts for most of the 8x performance gap.

The phi4:14b local context result warrants specific attention. The standard deviation of 8.14 on Ancillary-tier OVAR across 20 runs (L-Context LOCAL: Ancillary OVAR 10.82 ± 8.14) indicates that the business context prompt did not consistently shape ordering behaviour — it introduced variance. In some runs the context appears to have triggered aggressive anticipatory ordering; in others, conservative responses. The blind local model, by contrast, failed consistently and identically across all 20 runs (OVAR 4.33 ± 0.00). Consistent failure can be diagnosed and compensated for. Intermittent instability — where the same model with the same prompt produces order-of-magnitude different outcomes across runs — is harder to anticipate and mitigate in a real deployment.

The 120B reasoning model (gpt-oss:120b) matched the 14B lightweight (phi4:14b) in blind conditions. o4-mini generated over 1 million reasoning tokens across the experiment and produced no measurable improvement on either primary metric. Additional inference compute did not translate to better ordering decisions in this task.

---

## Limitations

- **Narrow task design:** Single product, single supply chain structure, fixed deterministic lead times, stateless agents, no inter-tier communication. Results should not be generalised to supply chain management broadly. The correct scope of the finding: LLM agents do not outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no memory.
- **Stateless architecture only:** Whether a stateful LLM architecture — one that tracks prior decisions — would narrow the gap is outside what this experiment can establish.
- **No unstructured context:** Agents received only numeric state variables and, in context conditions, a tier persona and calendar month. No demand forecasts, market reports, or structured knowledge bases were provided.
- **Fictional scenario:** All companies, products, and supply chain identities are synthetic. The demand series is calibrated to real Indian automotive market seasonality but is itself synthetic.
- **Backend comparability:** Frontier (Azure) and local (Ollama) backends were not fully ceteris paribus — temperature settings, inference hardware, and quantisation differed. Backend-specific results should not be compared directly without accounting for these differences.

---

## How to Reproduce

### Prerequisites

- Python 3.11+
- Either Azure OpenAI credentials (for frontier models: gpt-4.1-mini, o4-mini) or a local Ollama instance (for local models: phi4:14b, gpt-oss:120b)

### Environment Setup

The experiment reads credentials from separate env files for Azure and local backends. Template files are provided:

```bash
cd code

# Azure backend (gpt-4.1-mini, o4-mini)
cp env.azure.template .env.azure
# Open .env.azure and fill in AZURE_ENDPOINT and AZURE_API_KEY

# Local backend (Ollama or compatible server)
cp env.local.template .env.local
# Open .env.local and point LOCAL_ENDPOINT at your server
```

Both template files document every required variable, including the temperature design rationale. Supply your own credentials — do not commit env files.

Install dependencies:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
```

### Running the Experiment

**Verify setup without API calls (runs heuristic baselines only):**

```bash
python run_experiment.py --experiments baselines
```

This runs all three heuristic baselines and writes results to `../results/baselines/`. If it completes cleanly, the data pipeline is working.

**Smoke test (~5 minutes on Azure):**

```bash
python run_experiment.py --experiments E1 --runs 3 --env .env.azure
```

**Full experiment:**

```bash
# Frontier lightweight (gpt-4.1-mini)
python run_experiment.py --experiments E1 --runs 20 --env .env.azure

# Frontier reasoning (o4-mini)
python run_experiment.py --experiments E2 --runs 20 --env .env.azure

# Local lightweight (phi4:14b)
python run_experiment.py --experiments E1 --runs 20 --env .env.local

# Local reasoning (gpt-oss:120b)
python run_experiment.py --experiments E2 --runs 20 --env .env.local
```

Results are written to `../results/<experiment>/<timestamp>/` — three files per run: `records.parquet`, `summary.json`, `provenance.json`.

The runner uses exponential backoff (10 retries, capped at 60 seconds) and writes a checkpoint after every condition completes. It is safe to interrupt and resume.

---

## Repository Layout

```
agentic-bullwhip-v2-context-model-interactions/
├── README.md                   This file — overview, layout, reproducibility
├── FINDINGS.md                 Consolidated findings — what was tested, results, limitations
├── REPORT.md                   Full research paper — methodology, results, discussion
├── DESIGN.md                   Experiment design specification
├── requirements.txt            Python dependencies
│
├── data/
│   ├── tatva_monthly_dispatches_25m.csv            Demand series (25 months, synthetic)
│   ├── tatva_monthly_dispatches_25m_annotated.csv  Same series with phase labels
│   ├── calibration_notes.md                        How the series was calibrated
│   └── sources.md                                  Data source citations
│
├── code/
│   ├── run_experiment.py       Entry point
│   ├── simulation.py           Per-period simulation loop and heuristic policies
│   ├── agent_interface.py      LLM abstraction — prompts, state formatting, backend dispatch
│   ├── metrics.py              OVAR, stockout count, pattern score computation
│   ├── alpha_sweep.py          Exponential smoothing alpha calibration helper
│   ├── generate_figures.py     Rebuilds the charts in figures/ from results/
│   ├── verify_smoke_outputs.py Smoke-test output checker
│   ├── env.azure.template      Azure credentials template
│   ├── env.local.template      Local server credentials template
│   └── backends/
│       ├── azure_backend.py
│       ├── local_backend.py
│       ├── dry_run_backend.py
│       └── resilience.py       Exponential backoff and retry logic
│
├── figures/                    Result charts (fig1–fig4 PNGs)
│
└── results/                    Per-run summaries only (summary.json + provenance.json)
    ├── baselines/
    ├── E1/                     Lightweight model runs
    └── E2/                     Reasoning model runs
```

Per-run `records.parquet` raw outputs are not included in this public copy; the
runner regenerates them on a fresh run. `results/` retains the `summary.json` and
`provenance.json` for each condition.

---

## Version 1 to Version 2 Changes

Version 1 imposed an order floor (0.2x demand) and ceiling (5x demand) on all agents. Those guardrails masked natural agent behaviour. Version 2 removes them entirely: agents can order any non-negative quantity. Initial inventory was recalibrated from an arbitrary 180,000 units to a service-level-derived opening stock (mean + 1.65 sigma, approximately 43,600 units). The demand series was extended from 12 to 24 active ordering periods to cover two full Indian festive cycles. The product was narrowed from multiple lamp types to a single assembly to give context agents a cleaner identity to reason with. Heuristic baselines were added as an explicit comparison class.

---

## Citation

Published writeup: [https://industrialmindandcode.ai/blog/agentic-bullwhip-v2](https://industrialmindandcode.ai/blog/agentic-bullwhip-v2)

Author: Siddharth Srinivasan — [industrialmindandcode.ai](https://industrialmindandcode.ai)

Date: March 2026

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
