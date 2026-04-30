# Agentic Bullwhip Effect — Version 2a: Sovereign Model Performance in Stateless Supply Chain Replenishment

## Abstract

This experiment tested whether sarvam-30b — India's sovereign language model, trained on Indian data — produces materially different supply chain ordering behaviour from GPT OSS 120B when given a demand series calibrated to Indian automotive market seasonality. The experiment focused specifically on whether cultural training data confers seasonal awareness in an operational ordering task. Results indicate no practically meaningful difference: sarvam-30b chain OVAR 4.504 ± 0.044 (context, think=False) versus GPT OSS 120B 4.52 ± 0.05 (Version 2 context reference), a delta of 0.02 — well within noise and below the MPRD threshold of 0.5. Neither model detected Indian seasonal demand patterns. Exponential smoothing (OVAR 0.54) outperformed both by approximately 8x, consistent with Version 2 findings.

---

## Research Question

Does sarvam-30b — a model with substantial Indian training data — produce measurably different supply chain ordering behaviour from GPT OSS 120B on a demand series calibrated to real Indian automotive market seasonality (festive peaks, monsoon troughs, fiscal year-end patterns)? Specifically, does cultural training data produce seasonal awareness in a stateless ordering task?

---

## Experimental Design

### Supply Chain Structure

A three-tier serial supply chain with deterministic, one-month lead times at all levels (identical to Agentic Bullwhip Effect Version 2):

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
| Calibration | Real Indian passenger vehicle market data — festive peaks (Oct/Nov), monsoon trough (Jul/Aug), wedding season elevation, fiscal year-end |
| Active ordering periods | 24 |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | ~43,600 units (mean + 1.65 sigma, ~95% service level) |
| Possible stockout periods | 75 (25 periods x 3 tiers) |

All scenarios, companies, and supply chain structures are fictional. The demand series is calibrated to real Indian PV market data but is itself synthetic. No proprietary data was used.

### Conditions and Models

**Primary model under test:**

| Parameter | Value |
|---|---|
| Model | sarvam-30b Q4_K_M |
| Architecture | Mixture of Experts — 2.4B active parameters of 30B total |
| Provenance | Sarvam AI — India's sovereign model |
| Inference | llama-server (llama.cpp), local, NVIDIA GB10 Blackwell |
| Temperature | 1.0 (mandated by GGUF model card; lower values cause 40–60% call failures on local inference) |

**Reference model:** gpt-oss:120b (Version 2 context results — not re-run in Version 2a).

**Conditions:**

| Condition | think flag | Note |
|---|---|---|
| E1 | think=False | API flag + prompt conflict identified (see Integration Observations) |
| E2 | think=True | Recommended configuration for local GGUF deployment |

**Blind condition:** Not run in the main experiment. Pre-experiment calibration showed ~20% per-call error rates with minimal prompts, making 10-run completion infeasible. Individual smoke runs at temperature 1.0 did complete (1/3 E1, 1/1 E2); a subsequent calibration pass produced 0/3 before being stopped. Blind results are therefore not available for sarvam-30b and cannot be directly compared to Version 2 blind conditions.

**Agent design:** Stateless. Agents receive: tier persona + current month name + demand, on-hand inventory, backlog, and inventory position. No year. No event labels. Any seasonal reasoning must originate from the model's world knowledge.

**Replications:** 10 per condition. (Version 2 used 20; confidence intervals here are correspondingly wider.)

**Canonical dataset:** sarvam_v2d (top_p=1.0 per GGUF model card). Earlier runs used llama.cpp default top_p=0.95; correcting to 1.0 produced no meaningful change in results.

**MPRD threshold:** |delta OVAR| >= 0.5 required for a practically meaningful claim.

### Hypotheses

| Label | Null Hypothesis | Alternative Hypothesis |
|---|---|---|
| H1 | sarvam-30b chain OVAR is not meaningfully different from GPT OSS 120B (within MPRD) | sarvam-30b chain OVAR differs from GPT OSS 120B by >= 0.5 |
| H2 | sarvam-30b shows no greater seasonal pattern sensitivity than GPT OSS 120B | sarvam-30b produces a higher seasonal pattern score than GPT OSS 120B on the Indian demand series |
| H3 | Enabling think=True does not materially change supply chain outcomes | think=True produces meaningfully different chain OVAR from think=False (>= 0.5 delta) |

---

## Results

### Key Metrics

**Primary metrics:**

```
OVAR = Var(orders placed) / Var(demand received)
```

Chain OVAR = arithmetic mean of per-tier OVAR across three tiers. Values below 1.0 indicate dampening; values above 1.0 indicate bullwhip amplification.

**Pattern score:** Mean of keyword score (fraction of seasonal keywords present in model reasoning text) and elevation score (fraction of tier x event-period pairs where agent ordered >= 110% of non-event baseline). Seasonal event months: October (Dasara), November (Diwali), January (wedding season peak), August (monsoon trough reference).

**Stockout count:** Number of tier-periods where backlog > 0 after fulfilment (out of 75 possible per run).

### Results Tables

**Heuristic baselines (from Version 2, identical demand series)**

| Heuristic | Chain OVAR | Stockouts (of 75 possible) |
|---|---|---|
| Exponential smoothing | 0.54 | 5 |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

**sarvam-30b vs. GPT OSS 120B (canonical sarvam_v2d dataset)**

| Condition | Chain OVAR (mean ± std) | Stockouts (mean) | Pattern score | Run replacements |
|---|---|---|---|---|
| E1 Context (think=False) | 4.504 ± 0.044 | 39.9 | 0.219 | 15 of 25 attempts |
| E2 Context (think=True) | 4.501 ± 0.093 | 40.5 | 0.232 | 0 of 10 attempts |
| GPT OSS 120B context (Version 2 reference) | 4.52 ± 0.05 | 39.6 | 0.21 | 0 of 20 attempts |

Stockouts: shortfall > 0 across all 25 periods x 3 tiers = 75 tier-periods per run. Pattern score: mean of keyword and elevation scores at event months; elevation threshold = ratio > 1.10 above per-tier median.

### Hypothesis Verdicts

| Hypothesis | Prediction | Actual result | Verdict |
|---|---|---|---|
| H1 | sarvam-30b OVAR differs from GPT OSS 120B by >= 0.5 | Delta = 0.02, well below MPRD | REJECTED |
| H2 | sarvam-30b produces higher seasonal pattern score | Pattern scores 0.219–0.232 vs 0.21 — identical within noise | REJECTED |
| H3 | think=True produces meaningfully different chain OVAR | Delta E1 vs E2 = 0.003 — negligible | REJECTED |

---

## Discussion

The seasonal awareness hypothesis was not confirmed. The experiment was motivated by the possibility that a model trained on Indian data would show stronger seasonal sensitivity on a demand series calibrated to Indian market patterns. It did not.

Agents received the current month name plus four numeric state variables. No event labels, no seasonal context, no year were provided. Any seasonal signal had to come from the model's world knowledge about what October and November mean in India. Neither sarvam-30b nor GPT OSS 120B showed it. Pattern scores of 0.22 and 0.21 indicate very low and approximately equal seasonal sensitivity in both models.

Two explanations are consistent with this result. First, the task framing may not activate seasonal world knowledge even when the model possesses it: being asked to place an inventory order may not trigger the same retrieval pathway as being asked a factual question about Indian seasonality. Second, the structural constraint is operating independently of training data: stateless agents without memory cannot self-correct drift across periods regardless of what they know about seasonality. Even if a model correctly anticipated a festive peak in period 14, it cannot carry that anticipation forward without memory of what it planned.

The think=True finding is operationally relevant despite not affecting supply chain outcomes. Enabling the reasoning flag eliminated all run-level failures in E2 (0 of 10 attempts required replacement, vs. 15 of 25 in E1). This reliability improvement cannot be fully isolated to the reasoning flag alone — E1 also had an API flag/prompt conflict where the system prompt contained a "Think silently" instruction that contradicted the think=False flag. Regardless of the causal attribution, think=True produced reliable run completion and is the recommended configuration for local GGUF deployment of sarvam-30b via llama-server.

---

## Integration Observations

Two model-specific issues required resolution before stable runs were achievable. Both are specific to local GGUF deployment of sarvam-30b via llama-server.

| Issue | What happened | Resolution |
|---|---|---|
| API flag + prompt conflict | The think=False API flag conflicts with a "Think silently" instruction in the system prompt. The model receives contradictory instructions about whether to use internal reasoning, resulting in elevated error rates in E1. | Remove "Think silently" from the system prompt when using the think=False flag. |
| Blind condition structural failure | Minimal prompts (no context, no tier persona) produced ~20% per-call error rates at temperature 1.0. 10-run completion was not feasible. | Not resolved. Context conditions used for all main runs. Blind condition not available for sarvam-30b. |

A broader calibration note: sarvam-30b is available as both a cloud API and a local GGUF. The two documentation sources give different temperature recommendations — cloud: 0.2 (non-thinking), GGUF model card: 1.0. The GGUF model card value is correct for local inference. Using cloud temperature settings for local GGUF deployment causes 40–60% call failures.

---

## Limitations

- **Context conditions only.** Blind results are not available for sarvam-30b. The V2a context results cannot be directly compared to Version 2 blind conditions.
- **10 runs per condition.** Version 2 used 20 runs; confidence intervals here are wider. The sarvam-30b standard deviation values should be interpreted accordingly.
- **Not a ceteris paribus comparison.** Version 2a uses llama-server locally at temperature 1.0, while Version 2 GPT OSS 120B used Ollama at the settings documented in that experiment. Integration surface differences are noted but not fully controlled.
- **Single product, single supply chain structure, fixed lead times.** Results should not be generalised to supply chain management broadly.
- **Stateless agents only.** No inter-tier communication. Whether a stateful architecture would change results is outside what this experiment can establish.
- **Integration findings are specific to llama-server.** Cloud API deployment of sarvam-30b is a different integration surface and was not tested in the main runs.

---

## How to Reproduce

### Prerequisites

- Python 3.11+
- Local llama-server (llama.cpp) instance with sarvam-30b Q4_K_M loaded
- NVIDIA GPU with sufficient VRAM (experiment was run on an NVIDIA GB10 Blackwell)

### Environment Setup

The experiment reads credentials and endpoint configuration from a `.env.local` file. The canonical configuration used for the sarvam_v2d dataset is provided as `.env.sarvam_v2d` in the `code/` directory. Copy it and adjust for your local endpoint:

```bash
cd code
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt

# Start from the canonical local config
cp .env.sarvam_v2d .env.local
# Edit .env.local if your endpoint, model name, or token limits differ
```

Key configuration notes:
- Use temperature 1.0 (mandated by the GGUF model card — lower values cause elevated failure rates)
- Use think=True for E2 conditions (eliminates run-level failures with no effect on supply chain outcomes)
- Do not use cloud temperature recommendations for local GGUF deployment
- Do not commit `.env.local` — it is listed in `.gitignore`

### Running the Experiment

**Verify setup without API calls:**

```bash
python run_experiment.py --experiments baselines
```

**Smoke test (1 run):**

```bash
python run_experiment.py --experiments E1 --runs 1 --env .env.local
```

**Full canonical context-only experiment:**

```bash
python run_experiment.py --experiments baselines E1 E2 --conditions context --runs 10 --env .env.local --results-dir ../results/sarvam_v2d
```

Canonical results are written to `../results/sarvam_v2d/<experiment>/<timestamp>/` — three files per run: `records.parquet`, `summary.json`, `provenance.json`.

**Note on result directories:** The top-level `results/E1/` and `results/E2/` directories are copied V2-style bundles and are not V2a canonical results. The `results/sarvam/E1/` and `results/sarvam/E2/` directories are earlier V2a runs using the llama.cpp default top_p=0.95 (superseded). The canonical V2a dataset is in `results/sarvam_v2d/` only.

---

## Repository Layout

```
Agentic_Bullwhip_Effect_Version_2a_COMPLETED/
├── README.md               This file
├── ANALYSIS.md             Full V2a analysis — methodology deltas, results, interpretation
├── DESIGN.md               Experiment design — conditions, metrics, parameter choices
├── COMPARISON.md           V2 vs V2a side-by-side results
├── requirements.txt        Python dependencies
│
├── data/
│   ├── (25-month demand series)
│   └── (calibration notes)
│
├── code/
│   ├── run_experiment.py   Entry point
│   ├── simulation.py       Per-period simulation loop and heuristic policies
│   ├── agent_interface.py  LLM abstraction — prompts, state formatting, backend dispatch
│   ├── metrics.py          OVAR, stockout count, pattern score computation
│   ├── .env.sarvam_v2d     Canonical configuration (supply your own endpoint)
│   └── backends/
│       ├── local_backend.py
│       ├── dry_run_backend.py
│       └── resilience.py   Exponential backoff and retry logic
│
└── results/
    └── sarvam_v2d/         Canonical V2a results
```

---

## Relation to Version 2

Version 2a is an extension of Version 2, not a full replication. The supply chain structure, demand series, metric definitions, and MPRD threshold are identical. Version 2a differs in:

- Model tested: sarvam-30b Q4_K_M (MoE, 2.4B active of 30B total) instead of the four V2 models
- Backend: llama-server (llama.cpp) instead of Ollama
- Conditions: context only (blind not run due to instability)
- Replications: 10 per condition instead of 20
- Temperature: 1.0 (GGUF model card requirement)

The GPT OSS 120B context reference in V2a results is taken from Version 2 directly and was not re-run.

---

## Citation

Published writeup: [https://industrialmindandcode.ai/blog/agentic-bullwhip-v2a](https://industrialmindandcode.ai/blog/agentic-bullwhip-v2a)

Author: Siddharth Srinivasan — [industrialmindandcode.ai](https://industrialmindandcode.ai)

Date: March 2026
