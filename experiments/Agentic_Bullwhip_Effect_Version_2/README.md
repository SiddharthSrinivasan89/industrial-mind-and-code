# Heuristic Dominance Over LLM Agents in Stateless Linear Supply Chain Replenishment: An Experimental Study

A controlled simulation testing whether LLM agents can outperform a simple statistical rule at supply chain ordering. Four model configurations — lightweight and reasoning, frontier and local — were run against a 3-tier Indian automotive supply chain over 24 ordering periods. **None came close to a basic exponential smoothing heuristic.**

---

## What We Found

- **The gap is structural, not marginal.** The best LLM result (OVAR 4.33) is 8× worse than exponential smoothing (OVAR 0.54). OVAR (Order Variance Ratio) measures how much an agent amplifies or dampens demand swings — below 1.0 is dampening, above 1.0 is amplification. Every model tested amplified demand swings by 4–6×. The heuristic dampened them.
- **Stockouts were catastrophic under LLMs.** Exponential smoothing produced 5 stockout periods out of 75 possible (7%). Every LLM condition produced 37–43 (50–57%). LLMs ordered too much in the wrong periods and too little in others.
- **Adding context helped one model, badly destabilised another.** Giving gpt-4.1-mini the company name and calendar month reduced its OVAR slightly (4.70 → 4.47). The same context caused phi4:14b to deteriorate significantly (4.33 → 6.35), with the Ancillary tier reaching OVAR 10.8 in some runs.
- **A 120B reasoning model matched a 14B lightweight model.** gpt-oss:120b and phi4:14b produced nearly identical OVAR in blind conditions. More inference compute bought nothing.
- **The results are consistent with the stateless architecture.** Each agent sees only the current period's state and places an order with no memory of prior decisions. The heuristic carries a smoothed demand estimate forward and partially self-corrects from period to period. The stateless agent cannot. Whether a stateful LLM architecture would narrow the gap is outside what this experiment can establish.

Full methodology, results, and discussion: [REPORT.md](REPORT.md)

---

## Read the Research

| Document | What it is |
|---|---|
| [REPORT.md](REPORT.md) | Full research paper — methodology, results tables, discussion, recommendations |
| [DESIGN.md](DESIGN.md) | Experiment design specification — 2×2 factorial, parameter choices, metric definitions |
| [data/](data/) | 25-month synthetic demand series + calibration notes on real Indian automotive market data |

---

## Run It Yourself

**Prerequisites:** Python 3.11+, plus either Azure OpenAI credentials or a local [Ollama](https://ollama.com) instance.

### 1. Set up the environment

```bash
cd code
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
```

### 2. Configure credentials

```bash
# Azure backend (gpt-4.1-mini, o4-mini)
cp env.azure.template .env.azure
# Edit .env.azure — fill in AZURE_ENDPOINT and AZURE_API_KEY

# Local backend (Ollama, LM Studio, vLLM, llama.cpp)
cp env.local.template .env.local
# Edit .env.local — point LOCAL_ENDPOINT at your server
```

Both templates document every variable, including the temperature design rationale.

### 3. Verify setup (no API calls, instant)

```bash
python run_experiment.py --experiments baselines
```

This runs all three heuristic baselines and writes results to `../results/baselines/`. If it completes cleanly, the data pipeline is working.

### 4. Smoke test (~5 min on Azure)

```bash
python run_experiment.py --experiments E1 --runs 3 --env .env.azure
```

### 5. Full experiment

```bash
# Azure lightweight bundle (gpt-4.1-mini)
python run_experiment.py --experiments E1 --runs 20 --env .env.azure

# Azure reasoning bundle (o4-mini)
python run_experiment.py --experiments E2 --runs 20 --env .env.azure

# Local lightweight bundle (phi4:14b)
python run_experiment.py --experiments E1 --runs 20 --env .env.local

# Local reasoning bundle (gpt-oss:120b)
python run_experiment.py --experiments E2 --runs 20 --env .env.local
```

Results are written to `../results/<experiment>/<timestamp>/` — three files per run: `records.parquet`, `summary.json`, `provenance.json`.

The experiment uses exponential backoff (10 retries, capped at 60s) and writes a checkpoint after every condition completes, so it is safe to interrupt and resume.

---

## Repository Layout

```
├── README.md                   This file
├── REPORT.md                   Full research paper
├── DESIGN.md                   Experiment design specification
├── requirements.txt            Python dependencies
│
├── data/
│   ├── tatva_monthly_dispatches_25m.csv            Demand series (25 months)
│   ├── tatva_monthly_dispatches_25m_annotated.csv  Same series with phase labels
│   ├── calibration_notes.md                        How the series was calibrated to real data
│   └── sources.md                                  Data source citations
│
├── code/
│   ├── run_experiment.py       Entry point — run this
│   ├── simulation.py           Per-period simulation loop and heuristic policies
│   ├── agent_interface.py      LLM abstraction — prompts, state formatting, backend dispatch
│   ├── metrics.py              OVAR, stockout count, pattern score computation
│   ├── alpha_sweep.py          Utility: sweep exponential smoothing alpha values
│   ├── verify_smoke_outputs.py Utility: validate smoke test output files
│   ├── run_test_azure.sh       Convenience script for Azure smoke test
│   ├── run_test_local.sh       Convenience script for local smoke test
│   ├── env.azure.template      Azure credentials template
│   ├── env.local.template      Local server credentials template
│   └── backends/
│       ├── azure_backend.py    Azure OpenAI backend
│       ├── local_backend.py    Local OpenAI-compatible server backend
│       ├── dry_run_backend.py  No-op backend for testing without API calls
│       └── resilience.py       Shared exponential backoff + retry logic
│
└── results/                    Experiment output (included for reproducibility)
    ├── baselines/              Heuristic baseline runs
    ├── E1/                     Lightweight model runs (gpt-4.1-mini, phi4:14b)
    └── E2/                     Reasoning model runs (o4-mini, gpt-oss:120b)
```

---

## Version 1 → Version 2

Version 1 imposed an order floor (0.2× demand) and ceiling (5× demand) on all agents. Those guardrails masked natural agent behaviour — they prevented the most extreme orders but also made it impossible to see how agents actually respond without constraints. Version 2 removes them entirely: agents can order any non-negative quantity. Initial inventory was also recalibrated from an arbitrary 180,000 units to a service-level-derived opening stock (mean + 1.65σ ≈ 43,600 units). The product was narrowed from multiple lamp types to a single assembly to give context agents a cleaner identity to reason with.

---

**Disclaimer:** Personal experiments. Data is synthetic. No employer, vendor, or technology partner data was used. Local compute runs on an Asus Ascent GX10 with NVIDIA GB10 Blackwell SoC — personally owned. Azure and other AI subscriptions are personal in nature.
