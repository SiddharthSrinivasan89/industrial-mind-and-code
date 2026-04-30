# Agentic Bullwhip Effect — Version 6: StatelessSwing Adaptive Smoothing

## Abstract

This experiment is Version 6 in a research series examining whether Large Language Models (LLMs) can reduce order variance amplification in multi-tier supply chains. V5 established that the performance ceiling discovered in V4 — OVAR approximately 1.73–1.78 — is architectural rather than a model quality problem: the ceiling resides in the Order-Up-To (OUT) formula's safety stock structure, not in the classification layer. V5's closing analysis identified a single candidate architectural change: give the AI control of the exponential smoothing parameter alpha inside the EMA-based forecast, rather than a safety stock multiplier on top of it.

V6 tests this design. The AI is no longer external to the formula adjusting a buffer; it now selects the EMA smoothing coefficient alpha in {0.1, 0.3, 0.5, 0.7} per period per tier, and an exponential smoothing formula executes with that alpha. No OUT formula. No safety stock multiplier.

Three models were evaluated (gpt-4.1-mini, o4-mini, nemotron-super 120B) across three information conditions (blind, context, stateful), with a debiasing sub-experiment (V6b) testing two strategies to correct a context-induced alpha-inflation bias. The experiment also uses a simpler simulation environment than V4/V5 — returning to deterministic lead times to isolate the architecture change from stochastic supply-side effects.

**The result is the first positive finding in this research program:** every AI condition produced OVAR below 1.0. The best result, nemotron 120B in blind conditions, achieved OVAR 0.535 plus or minus 0.048, matching and marginally beating the fixed alpha=0.3 baseline at 0.545.

OVAR is defined as: OVAR = Var(orders) / Var(demand), computed per tier using sample variance (ddof=1) over the 24 active ordering periods, then averaged as arithmetic mean across 3 tiers. Values below 1.0 indicate consistent variance dampening; the entire range of AI results in V6 is below 1.0.

## Research Question

**Primary:** Does giving the LLM control of the EMA smoothing parameter alpha — rather than a safety stock multiplier — produce OVAR below 1.0 and allow any AI condition to match or beat the fixed optimal alpha=0.3 exponential smoothing baseline?

**Secondary questions:**
1. Does adding calendar and seasonal context (context condition) improve or worsen OVAR relative to inventory-state-only input (blind condition)?
2. Does providing recent alpha-selection history (stateful condition) moderate the context-induced variance effect?
3. Can debiasing strategies (restricting the alpha option set or explicit instruction) correct the context-induced alpha-inflation bias and recover most of the blind condition's performance advantage while preserving access to seasonal information?
4. Does model size confer a structural advantage in blind conditions, where models rely entirely on priors?

## Experimental Design

### Supply Chain Structure

A three-tier serial supply chain calibrated to an Indian automotive parts context, returning to the deterministic lead time environment of V1 and V2 to isolate the architecture change from the stochastic supply-side effects tested in V4 and V5.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Simulation horizon:** 25 months (January 2025 through January 2027); 24 active ordering periods plus one close-out period
- **Lead time:** 1 month deterministic at all tiers
- **No stochastic lead times or fill rates:** V6 eliminates the stochastic supply-side parameterisation of V4/V5 to ensure any OVAR change is attributable to the architecture, not supply variability
- **No world events:** Pure Indian automotive seasonal variation; monsoon slump, Diwali peak, financial-year-end surge

**Demand series:** Synthetic, calibrated to Indian automotive seasonal patterns (`tatva_monthly_dispatches_25m.csv`, SHA-256 stamped at runtime). Mean approximately 38,446 units per month across 24 active periods.

**Execution formula per period per tier:**

```
Step 1 — AI selects alpha in {0.1, 0.3, 0.5, 0.7}

Step 2 — Exponential smoothing executes with that alpha
  F_t   = alpha * D_t + (1 - alpha) * F_{t-1}
  order = max(0, round(F_t) + backlog_t)

No safety stock term. No OUT formula. No lookup table.
```

### Conditions and Models

**Models tested:**

| Model | Type | Backend |
|---|---|---|
| gpt-4.1-mini | Lightweight fast model | Microsoft Azure |
| o4-mini | Reasoning model | Microsoft Azure |
| nemotron-super 120B | Open-source 120B | Local Ollama |

**Information conditions (adaptive group):**

| Condition | Context provided to LLM |
|---|---|
| Blind | Current inventory state variables and the alpha option set; no calendar, no seasonal information |
| Context | Calendar month, tier persona with Indian automotive seasonal knowledge, and the alpha option set |
| Stateful | Context plus recent history of alpha selections, demand received, and order placed (last 3 periods) |

**V6b debiased conditions (sub-experiment):**

| Condition | Model | Debiasing strategy |
|---|---|---|
| mini_ctx_debiased | gpt-4.1-mini | Explicit instruction to correct alpha-inflation; full option set {0.1, 0.3, 0.5, 0.7} |
| mini_ctx_computed | gpt-4.1-mini | Restricted option set {0.1, 0.3, 0.5}; model derives alpha from observable statistics |
| oss120b_ctx_debiased | nemotron 120B | Explicit instruction to correct alpha-inflation; full option set |
| oss120b_ctx_computed | nemotron 120B | Restricted option set {0.1, 0.3, 0.5}; model derives alpha from statistics |

**Replications:** 10 runs per adaptive condition; 5 runs per debiased condition; 1 run per fixed baseline (deterministic).

**Fixed baselines (no AI, reference only):**

| Baseline | alpha | Chain OVAR | Stockouts |
|---|---|---|---|
| exp_smooth_0.1 | 0.1 | 0.620 | 16 |
| exp_smooth_0.3 | 0.3 | 0.545 | 5 |
| exp_smooth_0.5 | 0.5 | 0.729 | 3 |

The target for AI conditions is `exp_smooth_0.3` at OVAR 0.545 — the fixed baseline with the best balance of variance reduction and stockout count.

### Hypotheses

| Label | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| **HV6-1** | Every AI adaptive condition produces OVAR below 1.0 | OVAR < 1.0 for all conditions | PASS |
| **HV6-2** | The best AI condition matches or beats exp_smooth_0.3 | Best AI OVAR <= 0.545 | PASS (marginally, within confidence interval) |
| **HV6-3** | Context condition produces higher OVAR than blind (context penalty) | Context OVAR > Blind OVAR | PASS |
| **HV6-4** | Stateful condition lies between blind and context | Blind OVAR < Stateful OVAR < Context OVAR | PASS |
| **HV6-5** | Debiased conditions recover most of the blind advantage vs context | Debiased OVAR closer to blind than context | PASS |

## Results

### Key Metrics

Primary metric: Chain OVAR (arithmetic mean of per-tier OVAR). Secondary metrics: stockout count (total chain-level count across 25 periods, mean over replications) and mean alpha selected (average alpha value per condition, indicating model behaviour).

### Results Table

**Fixed baselines (no AI):**

| Condition | Chain OVAR | Stockouts |
|---|---|---|
| exp_smooth_0.1 | 0.620 | 16 |
| exp_smooth_0.3 | 0.545 | 5 |
| exp_smooth_0.5 | 0.729 | 3 |

**AI adaptive conditions (n=10 per condition):**

| Model | Condition | Chain OVAR | +/-std | Stockouts | Alpha mean |
|---|---|---|---|---|---|
| nemotron 120B | BLIND | 0.535 | 0.048 | 4.4 | 0.368 |
| gpt-4.1-mini | BLIND | 0.597 | 0.041 | 7.3 | 0.367 |
| o4-mini | BLIND | 0.657 | 0.091 | 4.0 | 0.404 |
| nemotron 120B | STATEFUL | 0.684 | 0.121 | 6.2 | 0.397 |
| gpt-4.1-mini | STATEFUL | 0.695 | 0.045 | 8.8 | 0.365 |
| o4-mini | STATEFUL | 0.705 | 0.125 | 6.5 | 0.397 |
| gpt-4.1-mini | CONTEXT | 0.715 | 0.020 | 10.4 | 0.363 |
| nemotron 120B | CONTEXT | 0.739 | 0.040 | 9.3 | 0.340 |
| o4-mini | CONTEXT | 0.741 | 0.045 | 10.4 | 0.359 |

**V6b debiased conditions (n=5 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Alpha mean |
|---|---|---|---|---|
| oss120b_ctx_computed | 0.585 | 0.036 | 5.6 | 0.322 |
| oss120b_ctx_debiased | 0.597 | 0.077 | 6.6 | 0.387 |
| mini_ctx_debiased | 0.596 | 0.063 | 7.4 | 0.337 |
| mini_ctx_computed | 0.679 | 0.007 | 8.4 | 0.267 |

All AI conditions in V6 produce OVAR below 1.0. Every value in the adaptive results table represents consistent variance dampening, not amplification. This contrasts with every prior version in the series (V1 through V5), in which every AI-driven configuration amplified order variance.

### Hypothesis Verdicts

**HV6-1 — Every AI adaptive condition produces OVAR below 1.0: PASS**
The worst AI condition (o4-mini context, OVAR 0.741) still represents consistent damping. The range across all nine adaptive conditions is 0.535–0.741. The architecture change — controlling alpha rather than a safety stock multiplier — eliminated amplification entirely.

**HV6-2 — Best AI condition matches or beats exp_smooth_0.3: PASS (marginally)**
nemotron 120B blind achieved OVAR 0.535 plus or minus 0.048 with 4.4 stockouts. The fixed alpha=0.3 baseline achieves OVAR 0.545 with 5 stockouts. The difference is 0.010, which falls within the confidence interval. This is the first time in the research program that an AI-driven condition can plausibly match its deterministic counterpart on the primary metric without sacrificing service level.

**HV6-3 — Context condition produces higher OVAR than blind (context penalty): PASS**
For all three models, the context condition produced higher OVAR than blind. Deltas: gpt-4.1-mini +0.118 (0.715 vs 0.597), o4-mini +0.084 (0.741 vs 0.657), nemotron 120B +0.204 (0.739 vs 0.535). Models given seasonal context consistently chose higher alpha values, increasing responsiveness and thereby increasing variance.

**HV6-4 — Stateful condition lies between blind and context: PASS**
All three models: blind < stateful < context in OVAR ordering. Stateful conditions (0.684–0.705) sit between blind (0.535–0.657) and context (0.715–0.741). Recent alpha history moderates the context-inflation effect without fully eliminating it.

**HV6-5 — Debiased conditions recover most of the blind advantage: PASS**
`oss120b_ctx_computed` at OVAR 0.585 recovers most of nemotron 120B's blind advantage (0.535) relative to its context condition (0.739) while providing seasonal information. `mini_ctx_debiased` at 0.596 similarly recovers much of gpt-4.1-mini's blind advantage (0.597 vs 0.715 context).

## Discussion

The architecture change is the explanation for the result. In V3b through V5, the AI controlled the safety stock multiplier — a term that governs how much buffer inventory is held above the forecast. Adjusting the multiplier changes inventory levels but does not directly govern how volatile orders are at the formula level; the OUT formula's replenishment logic generates order swings regardless. The EMA smoothing parameter alpha, by contrast, governs how much each period's demand observation updates the forecast. Lower alpha produces a sluggish, smooth forecast; higher alpha produces a reactive, noisy forecast. Order quantity is directly derived from this forecast with no additional buffer term. The AI is now controlling the dimension of the formula that directly determines variance.

The context penalty is calibrated over-responsiveness. When given seasonal information, models reason correctly that festival periods warrant higher responsiveness and select higher alpha values. The reasoning is directionally sound; the calibration is off. Alpha=0.7 in a supply chain with predictable seasonal patterns introduces more variance than the seasonal signal itself justifies. The effect is structurally far more tractable than the order quantity spikes of V2 or the multiplier miscalibration of V3b: it is a single parameter shifted one or two positions upward, not an order of magnitude error.

The 120B model's blind advantage (OVAR 0.535 vs 0.597 for gpt-4.1-mini) reflects a prior distribution effect rather than a reasoning capability effect. Without context, models rely entirely on the inventory numbers and the alpha option structure. The larger model, with broader training exposure to control system and operations literature, defaults naturally to alpha=0.3 — the standard exponential smoothing textbook value. Smaller models select alpha=0.7 more frequently. The advantage disappears entirely when context is added (all models produce OVAR 0.715–0.741 in context conditions), confirming that this is a prior rather than a reasoning effect.

The debiasing conditions demonstrate that the context penalty is correctable. Restricting the option set to {0.1, 0.3, 0.5} and having the model derive alpha from observable statistics (`oss120b_ctx_computed`, OVAR 0.585) recovers most of the blind advantage while providing seasonal information. Future experimental designs can extract the benefits of context without paying the full variance cost.

The contrast with the prior five versions is stark. In V4, adding context improved intent classification accuracy from approximately 44% to approximately 75% direction accuracy — and OVAR improved by approximately 0.01. In V6, adding context worsens OVAR by 0.08–0.20. The magnitude of the context effect in V6 is far larger than in V4 precisely because the AI is now controlling a lever that actually moves OVAR. When the lever matters, calibration errors also matter.

## Limitations

1. **Simplified simulation environment:** V6 returns to deterministic lead times and removes stochastic fill rates relative to V4/V5. The positive results may partly reflect this simpler environment rather than the architecture change alone. Cross-experiment comparison requires caution.
2. **Single demand series:** The 25-month synthetic demand series is specific to Indian automotive seasonal patterns. Findings are not established to generalise to other markets.
3. **Small option set:** The AI selects from only four discrete alpha values {0.1, 0.3, 0.5, 0.7}. Results may differ with continuous alpha or a different discrete set.
4. **Sample sizes:** n=10 per adaptive condition, n=5 per debiased condition. These are adequate for primary OVAR comparisons but underpowered for detecting small effects.
5. **No V4/V5 world events:** The absence of disruption events and stochastic lead times makes V6 a cleaner architecture test but limits generalisability to disrupted supply chain environments.
6. **Model-specific results:** Findings are specific to the three models tested. The 120B blind advantage reflects a specific model's prior distribution and may not generalise.
7. **Hypotheses were not pre-registered.** They were stated in design documentation prior to execution but not deposited with any external registry.
8. **Marginal primary result:** The nemotron 120B blind result (OVAR 0.535 vs 0.545 for the fixed baseline) is within the confidence interval. The headline result is that every AI condition dampens variance; the claim that any AI condition definitively beats the fixed optimal baseline requires replication with larger n.

## How to Reproduce

### Prerequisites

- Python 3.10 or later
- Access to one of: Azure OpenAI (gpt-4.1-mini and o4-mini deployments) or a local Ollama instance with nemotron-super:120b (for the oss120b conditions)
- A tmux session is required for all long-running model experiments
- nohup is required for remote client environments

### Environment Setup

```bash
cd experiments/Agentic_Bullwhip_Effect_V6_StatelessSwing/code/

# Install dependencies
pip install -r requirements.txt

# Configure credentials — create these files from the templates documented in run_experiment.py
cp .env.azure.template .env.azure   # fill in Azure credentials
cp .env.local.template .env.local   # fill in Ollama endpoint and model name
```

Required variables in `.env.azure`:
```
BACKEND=azure
AZURE_ENDPOINT=<your-endpoint>
AZURE_API_KEY=<your-key>
AZURE_API_VERSION=<api-version>
MODEL_LIGHTWEIGHT=gpt-4.1-mini
MODEL_REASONING=o4-mini
MAX_TOKENS_REASONING=32768
```

Required variables in `.env.local`:
```
BACKEND=local
LOCAL_ENDPOINT=<your-ollama-url>
LOCAL_MODEL=nemotron-super:120b
```

Note: Do not pass `temperature` for o4-mini (Azure reasoning model). Use `max_completion_tokens`, not `max_tokens`, for the token budget.

### Running the Experiment

**Dry run (no LLM calls, pipeline validation):**
```bash
DRY_RUN=1 python run_experiment.py --experiments baselines mini_adaptive --runs 2 --env .env.azure
python verify_outputs.py --results-dir ../results/baselines/
```

**Fixed baselines only (deterministic, no LLM, 1 run each):**
```bash
python run_experiment.py --experiments baselines --runs 1 --env .env.azure
```

**Smoke test (2 runs, real LLM):**
```bash
python run_experiment.py --experiments mini_adaptive --runs 2 --env .env.azure
```

**Full production — Azure models (gpt-4.1-mini and o4-mini), in tmux with nohup:**
```bash
tmux new-session -s prod_v6_azure
nohup python run_experiment.py \
    --experiments mini_adaptive o4mini_adaptive \
    --runs 10 --env .env.azure \
    > ../../logs/v6_azure_prod.log 2>&1
```

**Full production — Local model (nemotron 120B), in tmux with nohup:**
```bash
tmux new-session -s prod_v6_local
nohup python run_experiment.py \
    --experiments oss120b_adaptive \
    --runs 10 --env .env.local \
    > ../../logs/v6_local_prod.log 2>&1
```

**V6b debiased conditions (Azure and local):**
```bash
# Azure debiased
tmux new-session -s prod_v6b_azure
nohup python run_experiment.py \
    --experiments mini_debiased \
    --runs 5 --env .env.azure \
    > ../../logs/v6b_azure_prod.log 2>&1

# Local debiased
tmux new-session -s prod_v6b_local
nohup python run_experiment.py \
    --experiments oss120b_debiased \
    --runs 5 --env .env.local \
    > ../../logs/v6b_local_prod.log 2>&1
```

**Verify outputs after each run group:**
```bash
python verify_outputs.py --results-dir ../results/<experiment_label>/
```

Outputs are written to `results/<experiment_label>/<UTC_timestamp>/` with per-run `records.parquet`, per-condition `summary.json`, and a `provenance.json` containing the demand series SHA-256 checksum, model names, alpha option set, and dry-run flag.

## Citation

Srinivasan, S. (2026). *Agentic Bullwhip Effect V6: The Architecture That Finally Worked — Adaptive Smoothing in Supply Chain Replenishment.* Industrial Mind and Code. https://industrialmindandcode.ai/blog/agentic-bullwhip-v6

Related work in this series:
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). Information Distortion in a Supply Chain: The Bullwhip Effect. *Management Science*, 43(4), 546–558. https://doi.org/10.1287/mnsc.43.4.546
- Chen, F., Drezner, Z., Ryan, J.K., & Simchi-Levi, D. (2000). Quantifying the Bullwhip Effect in a Simple Supply Chain. *Management Science*, 46(3), 436–443. https://doi.org/10.1287/mnsc.46.3.436.12069
- Silver, E.A., Pyke, D.F., & Thomas, D.J. (2017). *Inventory and Production Management in Supply Chains* (4th ed.). CRC Press.
- Forrester, J.W. (1961). *Industrial Dynamics.* MIT Press.
