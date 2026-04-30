# Agentic Bullwhip Effect — Version 3b: Hybrid Architecture

## Abstract

Version 3b (V3b) tests whether a hybrid supply chain architecture — where a large language model (LLM) adjusts the safety stock multiplier of a deterministic ordering formula rather than determining order quantities directly — can outperform mathematical heuristics. Three models (gpt-4.1-mini, o4-mini, nemotron-super-3:120b) were evaluated across three information conditions (blind, context, stateful) over a 25-month Indian automotive demand series. All four hypotheses were rejected. Every AI hybrid condition produced higher order variance amplification than the mathematical baseline (exp_smoothing, chain OVAR 0.5446), and every AI condition also exceeded the fixed-multiplier control with no AI involvement (hybrid_control, chain OVAR 1.7097). Context worsened performance for two of three models; order history caused the reasoning model to reach the worst OVAR in the experiment (o4-mini stateful: 3.1211).

## Research Question

Can LLM agents improve supply chain ordering performance by parameterising a deterministic policy — adjusting a safety stock multiplier — rather than making autonomous ordering decisions? The hybrid architecture hypothesis was that confining AI to a single scalar output would exploit its qualitative context-reading capability while limiting its quantitative weaknesses. Prior experiments in this series (V1, V2) established that fully autonomous LLM agents perform substantially worse than simple heuristics in stable environments. V3b tests whether architectural constraint closes that gap.

## Experimental Design

### Supply Chain Structure

A three-tier serial supply chain (OEM → Ancillary Supplier → Component Supplier) simulated over 25 months using a synthetic demand series calibrated to Indian automotive seasonal patterns: FY-end peaks in March, monsoon trough June–August, Diwali peak in November. All companies, products, and supply chain configurations are fictional.

**Hybrid formula (per period, per tier):**

```
F_t             = 0.30 * D_t + 0.70 * F_{t-1}      (exponential smoothing forecast)
SS_t            = base_SS * multiplier_t             (base_SS = 5,061 units)
target_position = round(F_t) + SS_t
order_t         = max(0, target_position - inventory_position_t)
```

The LLM is shown the formula and asked only to choose a `safety_stock_multiplier` in the range [0.5, 3.0]. The deterministic formula executes the resulting order quantity. The multiplier is clamped to [0.5, 3.0] in code; any parse failure falls back to 1.0 (neutral).

**Key simulation parameters:**

| Parameter | Value |
|---|---|
| Simulation length | 25 months |
| Lead time | 1 month, deterministic at all tiers |
| Smoothing alpha | 0.30 (inherited from V2 empirical sweep) |
| Multiplier range | [0.5, 3.0], clamped in code |
| Multiplier fallback | 1.0 on parse failure |
| LLM replications | 20 per condition |
| Heuristic replications | 1 (deterministic series) |

### Conditions and Models

| Label | Policy | Context | Backend | Model |
|---|---|---|---|---|
| exp_smoothing | heuristic | — | — | — |
| hybrid_control | hybrid (fixed 1.0x multiplier) | — | — | — |
| hybrid_blind_local | hybrid | none | Local (Ollama) | nemotron-super-3:120b |
| hybrid_blind_azure | hybrid | none | Azure OpenAI | gpt-4.1-mini |
| hybrid_context_local | hybrid | calendar month | Local (Ollama) | nemotron-super-3:120b |
| hybrid_context_azure | hybrid | calendar month | Azure OpenAI | gpt-4.1-mini |
| hybrid_stateful_local | hybrid | calendar + 3-period history | Local (Ollama) | nemotron-super-3:120b |
| hybrid_stateful_azure | hybrid | calendar + 3-period history | Azure OpenAI | gpt-4.1-mini |

The o4-mini reasoning model was run across all three conditions. Results are reported by model x condition in the results tables below.

**hybrid_control** serves as the architectural baseline: the same formula, the same execution path, multiplier permanently fixed at 1.0 with no AI involvement. Any AI condition scoring above 1.7097 on OVAR demonstrates that the model's active adjustments degrade rather than improve the base formula.

**Information conditions:**

- H1 Blind: inventory state and order quantity inputs only; no date or seasonal context
- H2 Context: adds calendar month and Indian seasonal event flags (e.g., "Diwali approaching")
- H3 Stateful: adds context plus the last 3 periods of (demand, order, multiplier, backlog, stockout) history

### Hypotheses

**H1 (Primary):** At least one AI hybrid condition achieves lower chain OVAR and fewer stockouts than exp_smoothing simultaneously (within-experiment benchmark). Threshold: beats exp_smoothing on both metrics.

**H2 (Context benefit):** The Context condition (H2) improves chain OVAR over Blind (H1) by at least 0.5 OVAR units for at least two models. The hypothesis is that seasonal awareness allows agents to reduce unnecessary buffering.

**H3 (Memory benefit):** The Stateful condition (H3) improves chain OVAR over Context (H2) by at least 0.5 OVAR units for at least two models. The hypothesis is that order history reduces repeat-error over-ordering.

**H4 (Directional accuracy):** The LLM's chosen multiplier correlates with the correct directional response to seasonal demand at least 50% of the time (Multiplier Pattern Score, MPS >= 0.50). This tests whether AI understands the direction of seasonal variation even if it cannot calibrate the magnitude.

## Results

### Key Metrics

Primary metric: chain OVAR (Order Variance Amplification Ratio = Var(orders) / Var(demand), aggregated across all three tiers). Reported jointly with stockout count; neither metric is reported in isolation.

The best AI result (gpt-4.1-mini, Blind: OVAR 2.3325, 10.6 stockouts) was 4.3x worse on OVAR than exp_smoothing (0.5446, 5.0 stockouts) and 2.1x worse than the stockout count. Every AI condition also exceeded hybrid_control (OVAR 1.7097), proving that active multiplier adjustments degraded the base formula rather than adding to it.

The best observed Multiplier Pattern Score was 0.3977, below the H4 threshold of 0.50. Models identified the correct directional signal for seasonal demand fewer than 40% of the time on average.

### Results Tables

**Mathematical baselines:**

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---|---|---|
| exp_smoothing | 0.5446 | 5.0 | 4,769 |
| hybrid_control (fixed 1.0x, no AI) | 1.7097 | 14.0 | 5,142 |

**AI hybrid conditions (20 runs per condition; mean +- std):**

| Model | Condition | Chain OVAR | OVAR std | Stockouts | Multiplier Mean |
|---|---|---|---|---|---|
| nemotron-super-3:120b | H1 Blind | 2.4178 | 0.2814 | 12.2 | 1.2249 |
| nemotron-super-3:120b | H2 Context | 2.7629 | 0.2319 | 12.3 | 1.3489 |
| nemotron-super-3:120b | H3 Stateful | 2.6846 | 0.2413 | 9.6 | 1.3671 |
| gpt-4.1-mini | H1 Blind | 2.3325 | 0.1108 | 10.6 | 1.1298 |
| gpt-4.1-mini | H2 Context | 2.9763 | 0.0958 | 11.0 | 1.3103 |
| gpt-4.1-mini | H3 Stateful | 2.7226 | 0.1512 | 11.6 | 1.4291 |
| o4-mini | H1 Blind | 2.5232 | 0.2791 | 8.9 | 1.4808 |
| o4-mini | H2 Context | 2.4395 | 0.1616 | 11.7 | 1.2447 |
| o4-mini | H3 Stateful | 3.1211 | 0.1320 | 10.7 | 1.3488 |

Lower OVAR and lower stockouts are better. Multiplier Mean = average safety stock multiplier chosen across all runs and periods for that condition.

### Hypothesis Verdicts

| Hypothesis | Prediction | Verdict |
|---|---|---|
| H1 | At least one AI condition beats exp_smoothing on OVAR and stockouts simultaneously | REJECTED — best AI OVAR 2.3325 vs. baseline 0.5446 |
| H2 | Context improves OVAR over Blind for at least two models by >= 0.5 OVAR units | REJECTED — context worsened OVAR for nemotron-super-3:120b and gpt-4.1-mini |
| H3 | Stateful improves OVAR over Context for at least two models by >= 0.5 OVAR units | REJECTED — memory caused o4-mini to reach the worst OVAR in the experiment (3.1211) |
| H4 | LLM multiplier pattern score >= 0.50 (correct directional response to seasonal demand) | REJECTED — best observed MPS 0.3977 |

## Discussion

The results reveal a structural disconnect between two capabilities that appear related but are operationally distinct. Qualitative inspection of model outputs confirmed that all three models correctly recognised approaching high-demand seasons and reasoned that increased buffer stock was warranted. This is semantic alignment: the model understands the concept of what is happening. What the models failed to do was choose the exact multiplier value required to stabilise the system. An agent that correctly identifies "December needs more buffer" and outputs 1.45x when 1.05x would have sufficed is not an operational controller — it is a semantic reasoner operating in the wrong role.

The over-buffering bias was consistent and measurable. With a fixed 1.0 multiplier and no AI involvement, chain OVAR is 1.7097. Every AI condition exceeded this. Models averaged multipliers between 1.13 and 1.48 across all runs and conditions, indicating a systemic tendency toward caution that produced worse outcomes than not acting at all. When in doubt, all models added buffer; adding buffer amplified variance rather than damping it.

The o4-mini Stateful result is particularly informative. At OVAR 3.1211 it was the worst configuration in the experiment despite o4-mini being the highest-capability model tested. Inspection of internal reasoning logs showed the mechanism: the model anchored heavily on recent negative signals, treating minor backlogs as evidence of systematic under-ordering. A small backlog from two periods prior prompted a large over-order; that over-order appeared in the following period's history as excess inventory, triggering a different over-correction. This is the bullwhip effect operating within the model's reasoning process rather than across supply chain tiers — a novel and concerning failure mode for stateful AI planners.

The finding that context worsened performance for two of three models replicates and extends the V2 finding (where phi4:14b was catastrophically destabilised by calendar context). In V3b, even frontier models (gpt-4.1-mini) increased OVAR substantially when given seasonal context. More information produced more confident buffering, not more precise buffering.

The next logical architectural step is to restrict the output further: instead of a free-form multiplier in a continuous range, the AI selects from a small set of pre-defined text labels (STRONG_INCREASE, MODERATE_INCREASE, NEUTRAL, MODERATE_DECREASE, STRONG_DECREASE), with a hard-coded translation layer mapping each label to a fixed multiplier value. This converts the task from numerical calibration to classification, targeting the directional capability that does appear to exist while removing the quantitative precision task where these models consistently fail. The empirical multiplier range observed here (mean 1.13–1.48 across all conditions) provides a concrete basis for setting guardrails in any production deployment.

## Limitations

- **Single-product, fixed-topology supply chain.** Results are scoped to a stylised three-tier serial chain with deterministic lead times and a single Indian automotive product. Generalisations to multi-product, multi-echelon, or internationally distributed networks are not supported by this data.
- **Continuous scalar multiplier output.** The AI's task was to choose a real-valued multiplier in [0.5, 3.0]. This is still a numerical precision task; whether a classification-based output resolves the calibration problem is untested in this experiment.
- **Synthetic demand series.** The demand series is not derived from proprietary production data. It is calibrated to published Indian automotive seasonal patterns and therefore captures structural seasonality but not idiosyncratic firm-level variation.
- **Stateless heuristic baselines.** Heuristics ran once (deterministic). LLM conditions ran 20 replications. Comparison is internally valid but does not account for heuristic parameter sensitivity.
- **Fixed smoothing alpha.** The alpha=0.30 parameter was empirically selected during V2 on the same demand series. Performance sensitivity to alpha is not evaluated in V3b.
- **No disruption conditions.** V3b used a clean 25-month environment with no supply disruptions, stochastic lead times, or demand shocks. Whether the hybrid architecture performs differently under disrupted conditions is addressed in the V3 design but was not tested in production runs.

## How to Reproduce

### Prerequisites

- Python 3.10+
- For Azure conditions: an Azure OpenAI resource with `gpt-4.1-mini` deployed at `GlobalStandard`. Review deployment capacity before running — at 1 req/60s the full Azure run requires approximately 37 hours. Estimated cost: $5–6 USD total.
- For local conditions: Ollama running with `nemotron-super-3:120b` pulled (`ollama pull nemotron-super-3:120b`). Estimated wall time at local GPU speeds: 50–100 hours for full H1+H2+H3.

### Environment Setup

Credentials are never hardcoded. Copy the appropriate template and fill in your own values:

```bash
cd experiments/Agentic_Bullwhip_Effect_V3b_HybridArch_COMPLETED/code/

# Azure backend
cp env.azure.template .env.azure
# Edit .env.azure: set AZURE_ENDPOINT and AZURE_API_KEY

# Local backend
cp env.local.template .env.local
# Edit .env.local: confirm LOCAL_ENDPOINT and MODEL_LOCAL match your Ollama instance
```

Key fields in `env.azure.template`:

- `AZURE_ENDPOINT`: base URL of your Azure OpenAI resource (`https://<your-resource>.openai.azure.com/`)
- `AZURE_API_KEY`: rotate via Azure Portal → Keys and Endpoint
- `MODEL_LIGHTWEIGHT`: deployment name for gpt-4.1-mini (must match Azure Portal exactly, case-sensitive)
- `AZURE_API_VERSION`: `2025-01-01-preview` or later

Key fields in `env.local.template`:

- `LOCAL_ENDPOINT`: Ollama endpoint (default `http://localhost:11434/v1`)
- `MODEL_LOCAL`: model tag as shown by `ollama list`
- `TEMP_HYBRID`: 0.3 (do not set to 0.0 — identical outputs across 20 runs eliminates statistical power)

### Running the Experiment

Each backend is a separate invocation. The `BACKEND` environment variable controls which conditions execute; a local run skips all `*_azure` conditions and vice versa.

**Step 1 — Dry run (zero API cost, validates pipeline):**

```bash
DRY_RUN=1 BACKEND=local  python run_experiment.py --experiments baselines H1 --runs 2 --env .env.local
DRY_RUN=1 BACKEND=azure  python run_experiment.py --experiments baselines H1 --runs 2 --env .env.azure
```

**Step 2 — Verify dry-run outputs:**

```bash
DRY_RUN=1 python verify_outputs.py --results-dir ../results/
```

**Step 3 — Smoke test (2 runs, live API calls):**

```bash
BACKEND=local  python run_experiment.py --experiments H1 --runs 2 --env .env.local
BACKEND=azure  python run_experiment.py --experiments H1 --runs 2 --env .env.azure
```

**Step 4 — Production runs (20 runs, all hypothesis groups):**

Run each backend in its own tmux session with nohup. Confirm `DRY_RUN` is unset before launching.

```bash
# Confirm DRY_RUN is unset
echo "DRY_RUN=${DRY_RUN:-<unset, good>}"

# Local backend (nemotron-super-3:120b)
tmux new-session -s prod_local
BACKEND=local nohup python run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.local \
    > ../logs/v3b_local_prod.log 2>&1

# Azure backend (gpt-4.1-mini)
tmux new-session -s prod_azure
BACKEND=azure nohup python run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.azure \
    > ../logs/v3b_azure_prod.log 2>&1
```

Results are written to timestamped subdirectories under `results/`, e.g., `results/H1/20260414T063108/`. The local and Azure backends write to separate directories; analysis must draw from both.

**Step 5 — Validate outputs before interpreting results:**

```bash
python verify_outputs.py --results-dir ../results/ 2>&1 | tee ../logs/verify_prod.log
```

Confirm: `dry_run: false`, model names match the conditions table, `n_runs == 20`, `llm_compliance_rate >= 0.95`, `latency_ms > 0` for all active rows.

**Step 6 — Generate figures:**

```bash
python generate_figures.py --results-dir ../results/ --output-dir ../figures/
```

## Citation

```
Srinivasan, Siddharth. "Hybrid AI Safety Stock Control in Supply Chain Replenishment."
Agentic Bullwhip Effect Series, Version 3b. industrialmindandcode.ai, April 2026.
https://industrialmindandcode.ai/blog/agentic-bullwhip-v3b
```

Full code, data, and raw results are available in this repository. The accompanying blog writeup with extended discussion and figures is at `https://industrialmindandcode.ai/blog/agentic-bullwhip-v3b`.
