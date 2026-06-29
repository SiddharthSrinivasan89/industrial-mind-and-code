# V2a Experiment Analysis
## sarvam-30b on Indian Automotive Supply Chain

**Experiment:** Agentic Bullwhip Effect — Version 2a
**Dates:** March 2026
**Model tested:** sarvamai/sarvam-30b Q4_K_M (MoE, 2.4B active / 30B total)
**Inference:** llama-server (llama.cpp), local, NVIDIA GB10 (128GB unified memory)
**Reference baseline:** V2 results (GPT OSS 120B, phi4:14b)

---

## Purpose

V2a tests sarvam-30b — India's sovereign large language model — against the same supply chain task used in V2. The V2 framework (supply chain, demand series, conditions, metrics) is held constant. The model changes, and so do several operational parameters: temperature (0.0/0.3 in V2 vs 1.0 required for sarvam-30b), inference stack (Ollama vs llama-server), replications (20 per condition in V2 vs 10 in V2a), and the blind condition was dropped entirely. This is not a strict ceteris paribus swap — see COMPARISON.md for the full parameter table.

The central research question: does India's sovereign model show any India-specific behaviour when placed on an Indian industrial task? The demand series is built on real Indian automotive seasonality — festive cycles, monsoon troughs, FY-end peaks. If sarvam-30b's training encodes Indian economic patterns, those patterns should surface in how it orders: earlier recognition of Diwali season, more calibrated response to the monsoon dip, lower amplification on a series it is better suited for.

Secondary findings emerged on model integration mechanics that were not the original focus of the experiment.

---

## Setup

### Supply Chain
3-tier: **Tatva Motors (OEM) → Ancillary supplier → LED Component supplier**

Each tier is an independent agent. Agents receive orders from the tier above and place orders with the tier below. No agent has visibility into any other tier's state (no centralised information).

### Demand Series
25 months of synthetic Indian automotive demand (Jan 2025 – Jan 2027), calibrated to real Indian PV market data:
- Festive season peaks (October–November, Diwali cycle) — confirmed at +17–19% YoY in 2025
- Monsoon trough (June–August) — confirmed at −6% to −8% YoY
- March FY-end structural peak
- ~5% YoY growth baseline (aligned to actual 2025 PV market growth)
- Second partial festive cycle in the final months

Mean monthly demand: 38,548 units. Std: ~3,067 units. See `data/calibration_notes.md` for full derivation.

### Experiment Conditions

| ID | Name | Model tier | Think flag | Prompt |
|---|---|---|---|---|
| E1 | context_lightweight | Lightweight | `think=False` | Tier persona (company + product + role) · user message includes month name plus four numeric state variables (demand, on-hand inventory, backlog, inventory position) |
| E2 | context_reasoning | Reasoning | `think=True` | Same as E1 |
| Blind | (abandoned) | — | — | Minimal: "You are a supply chain ordering agent." |

The context system prompt gives the agent its tier identity (e.g. "You are a supply chain ordering agent for Tatva Motors, India. Product: Vecta Lighting Assembly…"). The user prompt adds the current month name (e.g. "Current month: November") and four numeric state variables (demand received, on-hand inventory, backlog, inventory position). No year, no explicit seasonal background, and no event labels are provided — any seasonal reasoning must come from the model's own world knowledge.

Blind conditions were abandoned as not viable for the main 10-run experiment. Pre-experiment smoke tests showed high per-call error rates (~20%) and elevated run-failure rates that made reliable 10-run completion infeasible. Individual smoke runs did complete (1/3 E1 blind, 1/1 E2 blind at temp=1.0), but a subsequent calibration attempt produced 0/3 before being stopped. Context (tier identity prompt) was used for all main experiment runs. *This is a model-specific finding — see F6.*

### Replications
10 runs per condition. Each run covers 25 periods × 3 tiers = 75 records, but period 25 is fulfilment-only — no ordering decision is made. LLM calls occur in periods 1–24 only: **72 agent calls per run**, 720 per condition. Confirmed by provenance `n_calls: 720`.

### Configuration (canonical — V2d, documented GGUF settings)
```
temperature = 1.0   (GGUF model card requirement)
top_p = 1.0         (GGUF model card, explicitly set)
ctx-size = 65536
MAX_TOKENS_LIGHTWEIGHT = 4096
MAX_TOKENS_REASONING = 8192
response_format = json_object
```

An earlier run (V2a baseline) used `top_p=0.95` (llama.cpp default, not explicitly set). It produced identical results. V2d with the documented `top_p=1.0` is the canonical dataset used throughout this analysis.

---

## Metrics

| Metric | Definition | Interpretation |
|---|---|---|
| **Chain OVAR** | Arithmetic mean of per-tier OVAR across OEM, Ancillary, Component | <1.0 = dampening · 1.0 = passthrough · >1.0 = bullwhip amplification |
| **Tier OVAR** | Var(orders) / Var(demand) computed per tier per run (ddof=1, 24 active periods) | Identifies where amplification originates |
| **Stockouts** | Count of periods where `shortfall > 0` (i.e. demand + backlog exceeded on-hand stock), summed across all tiers | Operational impact of ordering behaviour |
| **Pattern score** | Mean of keyword_score (seasonal keywords in rationale) and elevation_score (order moved in correct direction at event months) | 0 = no seasonal awareness · 1 = consistent seasonal response in both text and quantity |
| **Run replacements** | Count of entire runs that failed and were rerun | Failed runs wasted; lower = more stable condition |
| **Per-call retry rate** | Fraction of individual LLM calls that required a 2nd or 3rd attempt | From provenance `retry_rate`; independent of run replacements |

---

## Results

### Heuristic Baselines

| Heuristic | Chain OVAR | OEM | Ancillary | Component | Stockouts |
|---|:---:|:---:|:---:|:---:|:---:|
| **Exponential smoothing** | **0.545** | **0.408** | **0.647** | **0.578** | **5** |
| Naive passthrough | 1.000 | 1.000 | 1.000 | 1.000 | 3 |
| Order-up-to | 1.710 | 1.689 | 1.712 | 1.728 | 14 |

**Exponential smoothing (α=0.3):** A weighted average of recent and past demand — self-correcting and resistant to over-ordering. It reacts to demand changes but does not amplify them. This is the practical reference: any ordering agent that costs more to run must beat this.

**Naive passthrough:** Orders exactly what the upstream tier ordered, one period later. Zero amplification by construction. Low stockouts because it makes no speculative bets — it is purely reactive.

**Order-up-to:** A forecast-based base-stock policy that computes a target inventory position and orders up to fill the gap. It amplifies seasonally because it chases the forecast — when demand spikes, the target jumps and the order overreacts. The highest OVAR of the three, and the most stockouts despite the safety stock buffer.

### V2 Reference — phi4:14b and gpt-oss:120b (20 runs each)

| Condition | Model | OVAR | OEM | Ancillary | Component | Stockouts | Pattern |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| E1 Blind | phi4:14b | 4.33 ± 0.00 | 3.71 | 5.89 | 3.40 | 41.0 | 0.22 |
| E1 Context | phi4:14b | 6.35 ± 2.53 | 4.62 | 10.82 | 3.61 | 37.2 | 0.23 |
| E2 Blind | gpt-oss:120b | 4.52 ± 0.00 | 4.13 | 5.98 | 3.45 | 40.0 | 0.20 |
| E2 Context | gpt-oss:120b | 4.52 ± 0.05 | 4.13 | 6.01 | 3.43 | 39.6 | 0.21 |

gpt-oss:120b ran blind conditions without difficulty — ~100% first-attempt valid JSON. phi4:14b context runs showed high variance: Ancillary OVAR blew out to 10.82 under the richer prompt.

### sarvam-30b Results — V2d, documented settings (10 runs, context only)

| Condition | OVAR | OEM | Ancillary | Component | Stockouts | Pattern | Run replacements | Per-call retry rate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| E1 context_lightweight (think=False) | 4.504 ± 0.044 | 4.126 | 5.883 | 3.503 | 39.9 ± 0.3 | 0.219 ± 0.010 | 15 / 25 attempts | 10.4% |
| E2 context_reasoning (think=True) | 4.501 ± 0.093 | 4.126 | 5.853 | 3.524 | 40.5 ± 0.8 | 0.232 ± 0.013 | 0 / 10 attempts | 4.2% |

---

## Findings

### F1 — No India-specific ordering behaviour observed

The researcher expected sarvam-30b to show differentiated behaviour on Indian demand patterns — earlier recognition of festive cycles, more calibrated ordering during Diwali season, sensitivity to the monsoon trough. None of this was observed.

| Model | OVAR | Stockouts | Pattern |
|---|:---:|:---:|:---:|
| gpt-oss:120b E2 Context (V2) | 4.52 ± 0.05 | 39.6 | 0.21 |
| sarvam-30b E2 Context (V2d) | 4.501 ± 0.093 | 40.5 | 0.232 |
| Delta | **0.019** | 0.9 | 0.022 |

Pattern scores are identical — neither model shows any festive season awareness. The OVAR difference is well within noise.

**Conclusion:** No India-specific ordering behaviour was detected. A likely explanation is that the prompts and demand data were presented in English. Any India-specific training signal in sarvam-30b did not surface in this English-language numerical task. The experiment does not rule out that India-specific capabilities exist — it shows they did not activate here. Model origin is not a differentiating factor on this task and in this configuration.

### F2 — No LLM beats exponential smoothing

Every LLM tested across V2 and V2a amplifies demand variability by 8× relative to the exponential smoothing baseline.

| Best LLM result | OVAR | vs Exp smoothing |
|---|:---:|:---:|
| phi4:14b blind | 4.33 | **8×** |
| sarvam-30b context | 4.50 | **8×** |
| gpt-oss:120b context | 4.52 | **8×** |

Stockouts under every LLM: 37–41 periods out of 75 tier-periods per run (49–55%). Under exponential smoothing: 5 periods (7%). The gap is structural.

**Conclusion:** The failure is not a prompting problem and not a model capability problem. Stateless agents without persistent cross-period state cannot self-correct accumulated drift, even when they receive the current period's inventory state. More parameters and richer context do not help in this setup.

### F3 — Ancillary tier is the primary amplification source

sarvam-30b OVAR by tier (V2d E2): OEM = 4.126, Ancillary = 5.853, Component = 3.524. Ancillary is the highest of the three, by a significant margin.

| Condition | OEM | Ancillary | Component |
|---|:---:|:---:|:---:|
| Exp smoothing | 0.408 | 0.647 | 0.578 |
| sarvam-30b E2 (V2d) | 4.126 | 5.853 | 3.524 |
| gpt-oss:120b E2 (V2) | 4.130 | 6.010 | 3.430 |

**Why OEM is relatively lower:** The OEM agent (Tatva Motors) receives the actual consumer demand signal. Its orders are grounded in something real, even if it still amplifies. Amplification at OEM is driven by overordering relative to demand, but the signal itself is clean.

**Why Ancillary amplifies most:** The Ancillary agent receives OEM orders — which are already amplified — not the original demand. It has no visibility into what the consumer actually bought. When OEM orders vary (as they do under stochastic LLM ordering), Ancillary sees that variation as its demand signal and overreacts further. It is amplifying an already-amplified signal. This is the classic bullwhip mechanism operating at the second tier — and it is a structural property of the chain, not evidence of seasonal awareness at any tier.

**Why Component is lower than Ancillary:** The Component agent is in the same structural position (no direct demand visibility) and operates under the same 1-month deterministic lead time as the other tiers. The reason Component OVAR is lower than Ancillary's is not explained by the design parameters — all tiers are symmetric. The difference is observed consistently across both sarvam-30b and gpt-oss:120b; it may reflect how stochastic LLM ordering interacts with the specific volume levels and inventory buffers at each tier, but no causal mechanism has been confirmed.

**This pattern is identical between sarvam-30b and gpt-oss:120b.** The amplification hierarchy (Ancillary > OEM > Component) is model-independent. It is a function of chain structure and information asymmetry, not the model.

### F4 — think=True eliminates run-level failures without changing supply chain outcome

| Condition | Run replacements | Per-call retry rate | OVAR |
|---|:---:|:---:|:---:|
| E1 (think=False) | 15 / 25 attempts | 10.4% | 4.504 |
| E2 (think=True) | 0 / 10 attempts | 4.2% | 4.501 |

Same supply chain outcome (OVAR difference 0.003). The key reliability difference is at the run level: E1 required 25 attempts to produce 10 valid completed runs (15 runs failed entirely and were rerun). E2 completed all 10 runs on first attempt. Both conditions still had some per-call retries (4–10%), but think=True eliminated the run-level failures.

The thinking pass acts as a structured scratchpad that helps the model navigate from "what to order" to "format this correctly as JSON." Skipping it increases the chance of a malformed or empty response severe enough to cause an entire run to fail.

**Key model characteristic:** For sarvam-30b, enabling `think=True` is not about answer quality — the OVAR results are indistinguishable. It is about run-level stability. Disabling reasoning to cut latency or cost turns a reliable condition into one that wastes 60% of run attempts.

### F5 — Temperature is a hard constraint for sarvam-30b (local GGUF deployment)

*Note: findings in this section are integration observations from pre-experiment calibration work (my own sarvam-30b integration notes). They are not derived from the main V2d summary tables. Cloud API deployment was not tested empirically.*

| Temperature | Failure mode | Per-call error rate (observed) |
|---|---|:---:|
| 0.4 (initial test) | Token distribution degenerates, empty `content` fields | 40–60% |
| 0.2 (cloud API docs) | Same degenerate behaviour | ~100% (0/5 runs completed) |
| 1.0 (GGUF model card) | Recoverable stochastic failures | 5–10% |

A 22× swing in error rate between correct and incorrect temperature settings. Cloud API documentation and the GGUF model card give contradictory guidance for the same model (0.2 vs 1.0 for non-think mode). On local GGUF, temp=1.0 is required. Cloud documentation does not transfer to on-premises deployment.

### F6 — Prompt anchoring is a hard reliability requirement for sarvam-30b

Blind conditions (minimal prompt: "You are a supply chain ordering agent.") showed ~20% per-call error rates and elevated run-failure rates in pre-experiment calibration work. Individual smoke runs did complete (1/3 attempts E1 blind; 1/1 attempt E2 blind at temp=1.0), but a subsequent calibration pass produced 0/3 completions before being stopped. The per-call error rate was too high to make a 10-run blind experiment reliable, so blind conditions were not attempted in the main run.

Context conditions (tier identity prompt — company name, product, role — plus month name in the user message) produced per-call retry rates of 4–10% and completed all main experiment runs successfully. The canonical V2d context runs show 4.2% retry rate (E2) and 10.4% (E1).

**The contrast with V2 models is significant.** gpt-oss:120b (120B parameters, general purpose) ran blind conditions cleanly — ~100% first-attempt success. phi4:14b (14B parameters) also ran blind conditions without structural failures. sarvam-30b (30B total, 2.4B active) could not. This cannot be explained by model size alone. It is a model-specific characteristic with direct operational consequences: deployments of sarvam-30b require richer prompt scaffolding to achieve stable structured output. Minimal prompts are not sufficient.

---

## Integration Issues (model-specific, observed during pre-experiment calibration)

*These observations come from calibration and smoke-test work prior to the main V2d run (my own sarvam-30b integration notes). They are not derived from the main experiment summary tables.*

Two issues emerged that are specific to sarvam-30b's architecture and behaviour — not caused by operator error:

| # | Issue | Observed behaviour | Source | Resolution |
|---|---|---|---|---|
| 3 | System prompt conflict with `think` API flag | Adding "Think silently if needed" to system prompt conflicted with native `think=False` flag, raising per-call error rate from ~5% to ~22% | Pre-experiment calibration | Revert to original prompts; use only the API-level `think` flag |
| 4 | Blind condition high failure rate | ~20% per-call error rate with minimal prompt; run failure rate too high for 10-run main experiment | Smoke tests 2026-03-25/26 | Restrict main experiment to context conditions only |

Both issues are only discoverable by running — they cannot be anticipated from model documentation.

---

## What This Experiment Does Not Show

> **Read this before citing these results.**

- **This is not a general capability benchmark for sarvam-30b.** The OVAR ceiling in this experiment is set by the task structure — stateless agents cannot self-correct drift regardless of quality. All models cluster in a narrow 4.3–4.5 OVAR band. That band reflects the task, not the models.

- **This is not a test of LLM ordering capability in general.** An agent with access to inventory history, running orders, and cumulative error state might perform very differently. The experiment tests zero-state agents only.

- **This does not test India-specific language or reasoning.** All prompts were in English. sarvam-30b's India-specific capabilities, if any, were not activated by English-language prompts on a numerical task.

- **The reliability findings are specific to local GGUF deployment.** Temperature requirements, prompt sensitivity, and think-flag behaviour were observed with llama-server and the GGUF Q4_K_M quantisation. A managed cloud API deployment of the same model may behave differently.

---

## Data Location

| Dataset | Path |
|---|---|
| sarvam-30b E1 (V2d, think=False, top_p=1.0) | `results/sarvam_v2d/E1/20260327T180920/` |
| sarvam-30b E2 (V2d, think=True, top_p=1.0) | `results/sarvam_v2d/E2/20260328T044336/` |
| V2a E1 (top_p=0.95 implicit — superseded by V2d) | `results/sarvam/E1/20260326T160045/` |
| V2a E2 (top_p=0.95 implicit — superseded by V2d) | `results/sarvam/E2/20260327T013009/` |
| Baselines | `results/sarvam/baselines/20260326T160045/` |

Each run directory contains `records.parquet` (per-period orders and inventory), `summary.json` (aggregated metrics), and `provenance.json` (call counts, replacements, timestamps).

---

## Related Documents

| Document | Contents |
|---|---|
| [README.md](README.md) | Experiment overview and how to run |
| [DESIGN.md](DESIGN.md) | Full experiment design — conditions, metrics, hypotheses |
| [COMPARISON.md](COMPARISON.md) | V2 vs V2a side-by-side with all filled results |
| [FINDINGS.md](FINDINGS.md) | Consolidated findings — what was tested, methodology, results, limitations |
| [data/calibration_notes.md](data/calibration_notes.md) | Demand series calibration against real Indian PV market data |
| [data/sources.md](data/sources.md) | Data provenance and sources |
