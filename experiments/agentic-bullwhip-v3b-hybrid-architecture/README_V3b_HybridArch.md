# Agentic Bullwhip Effect — Version 3b: Hybrid Architecture

**Status:** Smoke-tested, ready for production runs
**Supply chain structure:** Three-tier serial cascade (OEM → Ancillary → Component), 25-month Indian automotive demand series
**Research question:** Can LLMs improve supply chain performance by *parameterising* a deterministic ordering policy rather than making autonomous ordering decisions?

---

## Background

Supply chain literature shows that autonomous AI agents can amplify order variance rather than dampen it. V3b tests whether a hybrid architecture — where the LLM adjusts the *parameter* of a deterministic ordering policy rather than deciding orders directly — avoids this failure mode. The LLM's task is reduced to directional reasoning (should I hold more or less buffer this month?) while the deterministic formula handles the arithmetic.

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

## Conditions and Models

| Label | Policy | Context | Backend | Model |
|---|---|---|---|---|
| `exp_smoothing` | heuristic | — | — | — |
| `hybrid_control` | hybrid_control | — | — | — (multiplier=1.0 fixed) |
| `hybrid_blind_local` | hybrid | none | local (Ollama) | nemotron-3-super:120b |
| `hybrid_blind_azure` | hybrid | none | Azure OpenAI | gpt-4.1-mini |
| `hybrid_context_local` | hybrid | calendar month | local (Ollama) | nemotron-3-super:120b |
| `hybrid_context_azure` | hybrid | calendar month | Azure OpenAI | gpt-4.1-mini |
| `hybrid_stateful_local` | hybrid | calendar + 3-period history | local (Ollama) | nemotron-3-super:120b |
| `hybrid_stateful_azure` | hybrid | calendar + 3-period history | Azure OpenAI | gpt-4.1-mini |

20 runs per LLM condition, 1 run for baselines (deterministic).

> **Model names are canonical.** Check `.env.local` (`MODEL_LOCAL`) and `.env.azure`
> (`MODEL_LIGHTWEIGHT`) before each run to confirm they match the table above.

---

## Hypotheses

| H | Test | Threshold |
|---|---|---|
| H1 (Primary) | Best hybrid OVAR ≤ exp_smoothing OVAR (this experiment) AND stockouts ≤ exp_smoothing stockouts (this experiment) | Beats within-experiment benchmark |
| H2 | Hybrid-Context vs Blind: ΔOVAR ≥ 0.5 | Context helps |
| H3 | Hybrid-Stateful vs Context: ΔOVAR ≥ 0.5 | History helps |
| H4 | Hybrid-Context multiplier pattern score ≥ 0.5 | LLM parameterises correctly |

---

## Execution Model — Two Separate Invocations

**Each backend is a separate job.** The `BACKEND` env var controls which conditions
are executed. A local run skips all `*_azure` conditions; an Azure run skips all
`*_local` conditions. You cannot produce both in a single invocation.

```
Local job  → writes results/baselines/..., results/H1/.../hybrid_blind_local, ...
Azure job  → writes results/H1/.../hybrid_blind_azure, ...
```

Analysis must draw from both result folders. Do not expect a single output directory
to contain both `*_local` and `*_azure` conditions.

---

## Quick Start

```bash
cd code/

# 1. Copy env templates (once)
cp env.local.template .env.local
cp env.azure.template .env.azure    # fill in AZURE_ENDPOINT, AZURE_API_KEY

# 2. Dry run — validate pipeline, zero API cost
DRY_RUN=1 BACKEND=local  /usr/bin/python3 run_experiment.py --experiments baselines H1 --runs 2 --env .env.local
DRY_RUN=1 BACKEND=azure  /usr/bin/python3 run_experiment.py --experiments baselines H1 --runs 2 --env .env.azure

# 3. Verify dry-run outputs
DRY_RUN=1 /usr/bin/python3 verify_outputs.py --results-dir ../results/

# 4. Smoke test (2 runs, real LLM calls — one backend at a time)
BACKEND=local /usr/bin/python3 run_experiment.py --experiments H1 --runs 2 --env .env.local
BACKEND=azure /usr/bin/python3 run_experiment.py --experiments H1 --runs 2 --env .env.azure
```

---

## Production Runs

> Run each backend in its own tmux session with nohup. Confirm `DRY_RUN` is unset
> before launching.

```bash
# Confirm DRY_RUN is off
echo "DRY_RUN=${DRY_RUN:-<unset, good>}"

# --- Local (nemotron-3-super:120b) ---
tmux new-session -s prod_local
BACKEND=local nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.local \
    > ../logs/v3b_local_prod.log 2>&1

# --- Azure (gpt-4.1-mini) ---
tmux new-session -s prod_azure
BACKEND=azure nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.azure \
    > ../logs/v3b_azure_prod.log 2>&1
```

Results land in timestamped subdirectories, e.g.:
```
results/H1/20260414T063108/   ← one experiment batch, one timestamp
results/H2/20260414T080000/
...
```

---

## Smoke vs Production Separation

Smoke-test results are **not** production evidence. They have 2 runs vs the required
20 and were generated during pipeline validation. Keep them for reference but exclude
them from any hypothesis evaluation.

| Folder pattern | Purpose |
|---|---|
| `results/H1/20260414T06*/` | Smoke test — 2 runs |
| `results/H1/20260414T08*/` or later | Production — 20 runs |

Before analysis, verify run counts with:
```bash
/usr/bin/python3 verify_outputs.py --results-dir ../results/
```

---

## Post-Run Review Checklist

Run this checklist before accepting any result set as evidence.

### 1. Provenance and structure
```bash
# Verify all output dirs
/usr/bin/python3 verify_outputs.py --results-dir ../results/ 2>&1 | tee ../logs/verify_$(date +%Y%m%dT%H%M%S).log
cat results/<exp>/<timestamp>/provenance.json   # confirm dry_run=false, model names, checksum
```
Confirm: `dry_run: false`, model names match table above, demand checksum unchanged.

### 2. Inference signatures (real LLM calls only)
For each hybrid condition in `records.parquet`:
- `latency_ms > 0` for all active rows (zero = dry-run-equivalent)
- `rationale` is non-blank for all active rows
- `ss_multiplier` varies across periods — spread should be nontrivial (std >> 0)
- `ss_multiplier` must not collapse toward 1.0 across all runs

### 3. Quality metrics (from summary.json)
Check per condition:
- `llm_compliance_rate ≥ 0.95` (fallback rate < 5%)
- `multiplier_stats.mean_n_fallback` is low
- `multiplier_stats.mean_n_clamped` is low (clamping indicates extreme inputs)
- `n_runs == 20` (confirm all runs completed)

### 4. Primary metrics — report together, never in isolation
Always report OVAR alongside:
- `chain_stockouts.mean` — OVAR alone can look good while stockouts are high
- `mean_on_hand.mean` — low OVAR from inventory starvation is not a win

### 5. Control integrity
- `hybrid_control` is the architectural baseline (fixed multiplier=1.0, same formula)
- Do not merge `hybrid_control` with live hybrid conditions in OVAR comparisons
- `exp_smoothing` is the within-experiment performance benchmark
- Backend comparison (local vs azure) is only valid when both backends produced
  complete, separately-stored result sets

### 6. Archive the verifier log
Save `verify_outputs.py` stdout for each production batch:
```bash
/usr/bin/python3 verify_outputs.py --results-dir ../results/ \
    2>&1 | tee ../logs/verify_prod_$(date +%Y%m%dT%H%M%S).log
```
This is the auditable pass/fail record for each result set.

---

## LLM Call Count (Production)

~4,320 calls per backend (3 conditions × 20 runs × 24 active periods × 3 tiers).

**Azure (gpt-4.1-mini, GlobalStandard capacity=1):**
- Rate limit: 10 req/min, 1,000 TPM
- Estimated wall time: ~37 hours at current capacity
- Estimated cost: ~$5–6 total (input $1.25/M, output $10/M)
- To reduce wall time: increase deployment capacity in Azure portal

**Local (nemotron-3-super:120b via Ollama):**
- ~40–90s per call on local GPU
- Estimated wall time: ~50–100 hours for full H1+H2+H3

---

## Directory Structure

```
Agentic_Bullwhip_Effect_V3b_HybridArch/
├── README_V3b_HybridArch.md
├── DESIGN_V3b_HybridArch.md           # Detailed experiment specification
├── requirements.txt
├── data/
│   └── tatva_monthly_dispatches_25m.csv    # 25-month Indian automotive demand series
├── code/
│   ├── run_experiment.py           # Entry point
│   ├── simulation.py               # Hybrid + heuristic simulation loop
│   ├── agent_interface.py          # Hybrid prompts + get_ss_multiplier()
│   ├── metrics.py                  # OVAR, stockouts, multiplier metrics
│   ├── verify_outputs.py           # Post-run output validation
│   ├── backends/
│   │   ├── azure_backend.py        # gpt-4.1-mini (non-streaming for get_ss_multiplier)
│   │   ├── local_backend.py        # nemotron-3-super:120b via Ollama
│   │   ├── dry_run_backend.py      # Returns multiplier=1.0, no API calls
│   │   └── resilience.py           # Exponential backoff (10 retries, cap 60s)
│   ├── .env.local                  # MODEL_LOCAL=nemotron-3-super:120b
│   ├── .env.azure                  # MODEL_LIGHTWEIGHT=gpt-4.1-mini
│   ├── env.local.template
│   └── env.azure.template
├── results/                        # Populated after runs
│   ├── baselines/
│   ├── H1/
│   ├── H2/
│   └── H3/
├── figures/                        # Populated after generate_figures.py
└── logs/                           # Run logs + archived verifier output
```

---

## Design Notes

| Aspect | This experiment (V3b) |
|---|---|
| LLM output | `safety_stock_multiplier` in [0.5, 3.0] — a parameter, not an order quantity |
| Execution | Deterministic OUT-style formula; LLM adjusts the safety stock buffer only |
| Formula visibility | Yes — LLM is shown the formula so it reasons about buffer direction, not arithmetic |
| Stateful condition | H-Stateful includes last 3 periods of (demand, order, multiplier, backlog, stockout) |
| LLM output bounds | [0.5, 3.0] stated in prompt + enforced in code; fallback to 1.0 on parse failure |
| Multiplier metrics | multiplier_stats, compliance_rate, multiplier_pattern_score (see DESIGN doc) |
| Backend routing | Per-condition `backend` field in spec; BACKEND env var filters which conditions run |
