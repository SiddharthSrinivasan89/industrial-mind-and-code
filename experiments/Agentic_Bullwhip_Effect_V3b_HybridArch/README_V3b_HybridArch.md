# Agentic Bullwhip Effect — Version 3b: Hybrid Architecture

**Status:** Code complete, ready to run
**Builds on:** V2/V2a (same 3-tier supply chain, same demand series)
**Research question:** Can LLMs improve supply chain performance by *parameterising* a deterministic ordering policy rather than making autonomous ordering decisions?

---

## Background

V2/V2a found that autonomous LLM agents produce chain-average OVAR 4.33–6.35 vs exponential smoothing at 0.54 — an 8× gap across every model and condition tested. The V2 paper concluded:

> "Hybrid systems that use LLM analysis to adjust the *parameters* of a deterministic model (e.g., modifying safety stock for a Diwali window) represent a more promising architecture than fully autonomous LLM ordering."

V3b tests this directly.

---

## Hybrid Architecture

**Two-layer structure per period per tier:**

1. **Planning layer (LLM):** receives inventory state + optional context → outputs a `safety_stock_multiplier ∈ [0.5, 3.0]`
2. **Execution layer (deterministic):** exponential smoothing with the LLM-adjusted safety stock

**Formula (OUT-style):**
```
F_t              = 0.30 × D_t + 0.70 × F_{t-1}
SS_t             = base_SS × multiplier_t         (base_SS ≈ 5,061 units)
target_position  = round(F_t) + SS_t
order_t          = max(0, target_position - inventory_position_t)
```

The LLM is shown the formula and only needs to reason about buffer sizing direction (more before Diwali, less during monsoon dip). Multiplier is clamped to [0.5, 3.0] in code; fallback to 1.0 on parse failure.

---

## Conditions

| Label | Description |
|---|---|
| `exp_smoothing` | V2 historical benchmark (OVAR 0.54) |
| `hybrid_control` | Architectural control: OUT-style formula, multiplier=1.0 fixed, no LLM |
| `hybrid_blind_local` | H-Blind, gpt-oss:120b local — no seasonal context |
| `hybrid_blind_azure` | H-Blind, gpt-4.1-mini Azure |
| `hybrid_context_local` | H-Context, gpt-oss:120b local — with calendar month + persona |
| `hybrid_context_azure` | H-Context, gpt-4.1-mini Azure |
| `hybrid_stateful_local` | H-Stateful, gpt-oss:120b local — context + 3-period history (demand, order, multiplier, backlog, stockout) |
| `hybrid_stateful_azure` | H-Stateful, gpt-4.1-mini Azure |

20 runs per LLM condition, 1 run for baselines (deterministic).

---

## Hypotheses

| H | Test | Threshold |
|---|---|---|
| H1 (Primary) | Best hybrid OVAR ≤ 0.54 AND stockouts ≤ 5 | Beats exp_smoothing |
| H2 | Hybrid-Context vs Blind: ΔOVAR ≥ 0.5 | Context helps |
| H3 | Hybrid-Stateful vs Context: ΔOVAR ≥ 0.5 | History helps |
| H4 | Hybrid-Context multiplier pattern score ≥ 0.5 | LLM parameterises correctly |
| H5 (Min bar) | Best hybrid OVAR < 4.33 | Beats best V2 autonomous LLM |

---

## Quick Start

```bash
cd code/

# 1. Copy env templates
cp env.local.template .env.local    # edit with your endpoint
cp env.azure.template .env.azure    # edit with your Azure credentials

# 2. Dry run — validate pipeline without API calls
DRY_RUN=1 python run_experiment.py --experiments baselines H1 --runs 2 --env .env.local

# 3. Verify outputs
DRY_RUN=1 python verify_outputs.py --results-dir ../results/

# 4. Smoke test (2 runs per condition, real LLM calls)
python run_experiment.py --experiments H1 H2 H3 --runs 2 --env .env.local

# 5. Production runs (in tmux with nohup)
nohup python run_experiment.py --experiments baselines H1 H2 H3 --runs 20 --env .env.local \
    > ../logs/v3b_local.log 2>&1 &

nohup python run_experiment.py --experiments H1 H2 H3 --runs 20 --env .env.azure \
    > ../logs/v3b_azure.log 2>&1 &

# 6. Generate figures (after runs complete)
python generate_figures.py --results-dir ../results/
```

---

## Directory Structure

```
Agentic_Bullwhip_Effect_V3b_HybridArch/
├── README.md
├── DESIGN.md                       # Detailed experiment specification
├── requirements.txt
├── data/
│   └── tatva_monthly_dispatches_25m.csv    # 25-month Indian automotive demand series
├── code/
│   ├── run_experiment.py           # Entry point
│   ├── simulation.py               # Hybrid + heuristic simulation loop
│   ├── agent_interface.py          # Hybrid prompts + get_ss_multiplier()
│   ├── metrics.py                  # OVAR, stockouts, multiplier metrics
│   ├── generate_figures.py         # 6 figures
│   ├── verify_outputs.py           # Post-run output validation
│   ├── alpha_sweep.py              # Exp smoothing alpha calibration (from V2a)
│   ├── backends/
│   │   ├── azure_backend.py
│   │   ├── local_backend.py
│   │   ├── dry_run_backend.py      # Returns multiplier=1.0, no API calls
│   │   └── resilience.py
│   ├── env.local.template
│   └── env.azure.template
├── results/                        # Populated after runs
└── figures/                        # Populated after generate_figures.py
```

---

## Key Differences from V2/V2a

| Aspect | V2/V2a | V3b |
|---|---|---|
| LLM output | `order_quantity` (direct order) | `safety_stock_multiplier` (parameter) |
| Execution | LLM decides entirely | exp_smoothing executes; LLM adjusts SS |
| Formula shown to LLM | No | Yes — LLM knows the mechanism |
| Stateful condition | No | Yes — H-Stateful includes last 3 periods |
| LLM output bounds | None (clamped post-hoc) | [0.5, 3.0] stated in prompt + clamped |
| Multiplier metrics | N/A | multiplier_stats, compliance_rate, multiplier_pattern_score |

---

## LLM Call Count

~8,640 calls (3 conditions × 2 models × 20 runs × 24 periods × 3 tiers).
Each call outputs ≈50-80 tokens. At gpt-4.1-mini rates, Azure cost ≈ $1.

---

## Relation to Other Versions

| Version | What it tests |
|---|---|
| V2 | Autonomous LLM ordering — 4 models, blind/context |
| V2a | Sarvam-30b and Sarvam-105b — Indian-trained models |
| V3b | **Hybrid architecture — LLM parameterises exp_smoothing** (this experiment) |
| V3 | SimPy-based realistic supply chain with disruptions |
