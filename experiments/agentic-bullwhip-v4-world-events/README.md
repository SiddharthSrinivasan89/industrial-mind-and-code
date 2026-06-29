# Agentic Bullwhip Effect — Version 4: Intent Classifier with World Events

## Abstract

This experiment is the primary published Version 4 result in a five-experiment series examining whether Large Language Models (LLMs) can reduce order variance amplification in multi-tier supply chains. Building on the discrete intent-classification architecture established in the V4 IntentClassifier variant, this experiment extends the simulation to 36 months and introduces three real-world disruption types — a pandemic, a geopolitical conflict, and a port strike — to stress-test the architecture under conditions that activate all five intent classes.

Four LLMs were evaluated (gpt-4.1-mini, o4-mini, phi4:14b, nemotron-super 120B) across three information conditions (blind, context, unstructured) and two ablation sub-experiments. The experiment is complete as of 23 April 2026.

The central finding is the **Equaliser Effect**: the discrete label-to-multiplier lookup table creates a structural ceiling and floor on OVAR that no model, information condition, or prompt intervention can escape. All four AI models produced OVAR in a tight band of 1.73–1.78, coinciding with the Order-Up-To (OUT) formula baseline, and no condition approached the exponential smoothing benchmark of 1.185. The architecture succeeded as a compliance guardrail — intent compliance was 1.00 (perfect) across all conditions — but failed as a performance improvement mechanism.

OVAR is defined as: OVAR = Var(orders) / Var(demand), computed per tier using sample variance (ddof=1) over all active ordering periods, then averaged to chain level. Values below 1.0 indicate variance dampening; values above 1.0 indicate amplification.

## Repository Layout

```
agentic-bullwhip-v4-world-events/
├── README.md       # this file — overview, design summary, reproduction steps
├── DESIGN.md       # full design: parameters, intent classes, hypotheses, conditions
├── FINDINGS.md     # consolidated findings with exact numbers and limitations
├── results/        # published result summaries (summary.json + provenance.json per condition)
└── code/
    ├── run_experiment.py   # entry point — EXPERIMENTS registry, CLI flags
    ├── agent_interface.py  # intent prompts + INTENT_MULTIPLIER_MAP + get_intent_class()
    ├── simulation.py       # SimPy engine, policy_intent_hybrid() + heuristic policies
    ├── world_events.py     # pandemic / conflict / port-strike injectors
    ├── metrics.py          # OVAR, stockouts, intent compliance/accuracy/entropy
    ├── generate_demand_36m.py  # regenerates the synthetic demand series
    ├── requirements.txt
    ├── backends/           # azure_backend, local_backend, dry_run_backend, resilience
    └── data/synthetic/     # tatva_monthly_dispatches_36m.csv (synthetic, 36 months)
```

For the full design and parameters see [DESIGN.md](DESIGN.md); for the consolidated results and limitations see [FINDINGS.md](FINDINGS.md).

## Research Question

**Primary:** Does intent classification — where the LLM selects one of five discrete labels that are then mapped to safety stock multipliers by a deterministic lookup table — produce lower order variance amplification (OVAR) than heuristic baselines when world events create sharp demand and supply shocks alongside seasonal variation?

**Secondary questions:**
1. Does providing explicit event-headline context (`unstructured` condition) improve intent accuracy at disruption-period boundaries relative to calendar-only context?
2. Do world event periods produce systematically different intent accuracy and entropy from normal seasonal periods?
3. Does intent compliance remain near-perfect (>= 0.99) under emotionally charged disruption headlines that could destabilise structured JSON output?
4. Does disabling world events materially alter OVAR (ablation E3)?

## Experimental Design

### Supply Chain Structure

The experiment uses a three-tier serial supply chain calibrated to an Indian automotive parts context.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Simulation horizon:** 36 months (January 2025 through December 2027)
- **Lead times:** Stochastic (LogNormal distribution), further modified by world events
- **Fill rates:** Stochastic (Beta distribution), capped during world events
- **Initial inventory:** mean demand plus 1.65 standard deviations at each tier
- **Demand:** Indian automotive seasonal pattern averaging 37,000–42,000 units per month at OEM tier

**World events injected:**

| Event | Periods | Demand effect | Supply effect |
|---|---|---|---|
| Pandemic | Months 7–12 | -45% collapse then +35% surge then recovery | Supply restriction during surge |
| Geopolitical conflict | Months 19–21 | Moderate demand suppression | Severe supply restriction |
| Port strike | Months 28–30 | None (demand unaffected) | Supply-side disruption only |

**Three-layer execution architecture per period per tier:**

```
Layer 1 — Classification (LLM)
  Input:  inventory state + optional context
  Output: {"intent": "<CLASS>", "rationale": "..."}

Layer 2 — Hard-coded Lookup (deterministic)
  STRONG_INCREASE   -> multiplier 1.30
  MODERATE_INCREASE -> multiplier 1.15
  NEUTRAL           -> multiplier 1.00
  MODERATE_DECREASE -> multiplier 0.90
  STRONG_DECREASE   -> multiplier 0.80

Layer 3 — OUT Formula (deterministic)
  order = max(0, forecast + safety_stock * multiplier - inventory_position)
```

### Conditions and Models

**Models tested:**

| Model | Type | Backend |
|---|---|---|
| gpt-4.1-mini | Lightweight fast model | Microsoft Azure |
| o4-mini | Reasoning model | Microsoft Azure |
| phi4:14b | Open-source 14B | Local Ollama |
| nemotron-super 120B | Open-source 120B | Local Ollama |

**Information conditions:**

| Condition | Context provided to LLM |
|---|---|
| Blind | Current inventory state variables only; no calendar, no event information |
| Context | Calendar month and tier persona with Indian automotive seasonal knowledge |
| Unstructured | Context plus live news-style event headlines during disruption periods |

**Sub-experiments:**

| Sub-experiment | Purpose | Models | Runs |
|---|---|---|---|
| Baselines | Non-AI heuristic reference policies | — | 100 runs each |
| E1_IC | Core intent classification, lightweight models | gpt-4.1-mini (20), phi4:14b (10) | All 3 conditions |
| E2_IC | Core intent classification, reasoning-tier models | o4-mini (20), nemotron 120B (10) | All 3 conditions |
| E3_IC | Ablation: world events disabled | phi4:14b (10) | Blind + context only |
| E4_IC | Neutral-prior prompt: AI instructed toward inaction | gpt-4.1-mini (20), o4-mini (20), phi4:14b (10) | Blind + context only |

### Hypotheses

| Label | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| **H1** | Intent classification matches or beats exp_smoothing | Best AI OVAR <= 1.185 | FAIL |
| **H2** | Unstructured context reduces OVAR vs calendar-only context | Unstructured OVAR <= Context OVAR | FAIL |
| **H3** | Unstructured context improves direction accuracy by >= 10 percentage points | Delta direction accuracy >= 0.10 | FAIL |
| **H4** | Intent compliance remains >= 0.99 under all conditions | Compliance rate >= 0.99 | PASS |
| **H5** | World events materially alter OVAR (either direction) | E1 OVAR != E3 OVAR | PASS (surprising direction) |

## Results

### Key Metrics

OVAR = Var(orders) / Var(demand), sample variance (ddof=1), computed per tier across all active ordering periods, then averaged as arithmetic mean across 3 tiers. Stockouts are cumulative chain-level counts across the 36-month simulation horizon.

Intent direction accuracy is the fraction of non-neutral event periods in which the model's chosen label matches the correct direction (increase vs. decrease), regardless of intensity level. Entropy is Shannon entropy over the label distribution across all periods, with maximum entropy of log2(5) = 2.32 for a uniform distribution.

### Results Table

**Non-AI baselines (reference):**

| Policy | Chain OVAR | Stockouts per run | Description |
|---|---|---|---|
| naive_passthrough | 0.996 | 96.0 | Orders last period's demand exactly |
| exp_smoothing | 1.185 | 89.6 | Exponential smoothing with EMA forecast |
| order_up_to (OUT) | 1.767 | 87.0 | OUT formula; the structural ceiling for all AI conditions |

**E1_IC — gpt-4.1-mini (n=20 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.747 | 0.092 | 86.3 | 0.41 | 0.81 | STRONG_INCREASE 75% |
| Context | 1.737 | 0.088 | 87.0 | 0.72 | 2.14 | NEUTRAL 40%, all 5 used |
| Unstructured | 1.771 | 0.108 | 86.8 | 0.76 | 2.16 | NEUTRAL 37%, all 5 used |

**E1_IC — phi4:14b (n=10 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.748 | 0.130 | 84.9 | 0.48 | 0.60 | STRONG_INCREASE 89% |
| Context | 1.726 | 0.093 | 86.7 | 0.80 | 2.20 | STRONG_INCREASE 34%, all 5 used |
| Unstructured | 1.780 | 0.130 | 86.2 | 0.84 | 2.17 | STRONG_INCREASE 32%, all 5 used |

**E2_IC — o4-mini (n=20 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.763 | 0.113 | 85.3 | 0.44 | 0.41 | STRONG_INCREASE 92% |
| Context | 1.748 | 0.105 | 87.0 | 0.72 | 2.17 | NEUTRAL 38%, all 5 used |
| Unstructured | 1.774 | 0.106 | 86.7 | 0.79 | 2.21 | NEUTRAL 33%, all 5 used |

**E2_IC — nemotron-super 120B (n=10 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.734 | 0.133 | 84.7 | 0.47 | 0.30 | STRONG_INCREASE 95% |
| Context | 1.745 | 0.128 | 86.7 | 0.74 | 2.21 | MOD_DECREASE 29%, MOD_INCREASE 26% |
| Unstructured | 1.775 | 0.130 | 86.7 | 0.83 | 2.21 | All 5 labels, well-spread |

**E3_IC — World events ablation, phi4:14b (n=10 per condition):**

| Condition | Chain OVAR | +/-std | Stockouts | Notes |
|---|---|---|---|---|
| Blind, no events | 2.082 | 0.199 | 50.0 | 19% worse OVAR than events-on equivalent |
| Context, no events | 2.117 | 0.205 | 53.5 | 23% worse OVAR than events-on equivalent |

**Cross-model OVAR range summary:**

| Model | OVAR range across all conditions |
|---|---|
| gpt-4.1-mini | 1.737 – 1.771 |
| o4-mini | 1.748 – 1.774 |
| phi4:14b | 1.726 – 1.780 |
| nemotron 120B | 1.734 – 1.775 |
| exp_smoothing (target) | 1.185 |
| order_up_to (structural ceiling) | 1.767 |

### Hypothesis Verdicts

**H1 — Intent classification matches or beats exp_smoothing: FAIL**
Best AI OVAR achieved: 1.726 (phi4 context). This is 46% above the exp_smoothing target of 1.185. No model in any condition approached the threshold.

**H2 — Unstructured condition reduces OVAR vs context: FAIL**
In every model tested, the unstructured condition produced higher OVAR than context. The margin was consistent: models over-committed to extreme labels when shown disruption headlines, adding noise rather than precision.

**H3 — Unstructured improves direction accuracy by >= 10 percentage points: FAIL**
Observed deltas: gpt-4.1-mini +0.04, phi4 +0.04, o4-mini +0.07, nemotron +0.09. None reached the 0.10 threshold.

**H4 — Intent compliance >= 0.99 across all conditions: PASS**
Intent compliance was 1.00 (perfect) across every condition and every model, including emotionally charged pandemic and conflict headline conditions. The structured output interface proved robust.

**H5 — World events materially alter OVAR: PASS (counterintuitive direction)**
Events-on OVAR: 1.73–1.78. Events-off OVAR: 2.08–2.12. Removing world events worsened OVAR. The disruption sequence generates correlated demand and order shocks that partially cancel each other in the OVAR ratio, creating a false impression of AI effectiveness under disruption.

## Discussion

The central finding is the Equaliser Effect: regardless of model size, reasoning capability, or information level, all AI conditions produced OVAR within a 0.05-unit band (1.73–1.78) coinciding with the Order-Up-To formula baseline. The source of this invariance is architectural. The AI controls only the safety stock multiplier, which ranges from 0.80 to 1.30. Order amplification in this simulation is primarily driven by stochastic lead times and fill rates — features of the physical supply chain, not of the AI's decision. Even perfect classification would not alter this.

Context substantially improves intent classification accuracy (direction accuracy rises from approximately 44% to approximately 75% when calendar context is added), but this improvement does not propagate through the lookup table to OVAR. The lookup table is both the architectural fix for V3b's miscalibration problem and the ceiling that prevents further improvement.

The world events ablation (E3) produces the counterintuitive finding that disruption events artificially dampen OVAR. The pandemic sequence creates correlated demand and order shocks: the sharp demand drop followed by a surge generates both the signal and the noise in a correlated way that compresses the OVAR ratio. Without disruptions, pure seasonal variation produces uncorrelated AI-generated order swings relative to a smoother demand denominator, worsening OVAR. This finding constitutes a methodological warning: evaluating AI ordering systems only during disrupted periods may overstate their effectiveness.

The neutral-prior sub-experiment (E4) confirms that prompt-layer interventions cannot reach the architectural source of amplification. Even explicitly instructing the model to prefer NEUTRAL does not reduce OVAR, because the NEUTRAL label maps to a full OUT calculation with multiplier 1.0 rather than true inaction.

## Limitations

1. **Simulation environment:** All supply chain entities, companies, and demand figures are entirely synthetic. The demand series is calibrated to Indian automotive seasonal patterns but is not real data.
2. **Stochastic lead times and fill rates:** The V4 WorldEvents environment uses LogNormal lead time and Beta fill rate distributions. Results are specific to this parameterisation. The simpler V4 IntentClassifier variant used deterministic lead times.
3. **Structural ceiling:** OVAR cannot improve beyond the OUT formula baseline without changing the formula, as established by the subsequent V5 oracle experiment.
4. **Single supply chain topology:** Three-tier serial cascade. Real supply chains involve variable lead times, lateral flows, and multi-echelon complexity.
5. **Model-specific results:** Findings are specific to the four models tested (gpt-4.1-mini, o4-mini, phi4:14b, nemotron-super 120B). Generalisation to other models is not established.
6. **Sample sizes:** LLM conditions used n=10 to n=20 runs. This provides adequate variance estimates at the MPRD threshold of 0.5 OVAR units; smaller effects may be underpowered.
7. **Hypotheses were not pre-registered.** They were stated in the design document prior to execution, but not deposited with any external registry.

## How to Reproduce

### Prerequisites

- Python 3.10 or later
- Access to one of: Azure OpenAI (gpt-4.1-mini and o4-mini deployments) or a local Ollama instance with phi4:14b and/or nemotron-super:120b
- A tmux session is required for all long-running model experiments
- nohup is required for remote client environments

### Environment Setup

```bash
cd experiments/agentic-bullwhip-v4-world-events/code/

# Install dependencies
pip install -r requirements.txt
```

Create your own credential files (they are not shipped — never commit real keys). Create `.env.azure` with your Azure OpenAI details:
```
AZURE_ENDPOINT=<your-endpoint>
AZURE_API_KEY=<your-key>
AZURE_API_VERSION=2025-01-01-preview
MODEL_LIGHTWEIGHT=gpt-4.1-mini
MODEL_REASONING=o4-mini
MAX_TOKENS_LIGHTWEIGHT=256
MAX_TOKENS_REASONING=32768
```

Create `.env.local` with your local Ollama details:
```
LOCAL_ENDPOINT=http://localhost:11434/v1
LOCAL_API_KEY=ollama
MODEL_LIGHTWEIGHT=phi4:14b
MODEL_REASONING=nemotron-super:120b
MAX_TOKENS_LIGHTWEIGHT=256
MAX_TOKENS_REASONING=512
```

### Running the Experiment

**Dry run (no LLM calls, pipeline validation):**
```bash
DRY_RUN=1 python run_experiment.py --experiments baselines E1_IC_azure --runs 2 --env .env.azure
```

**Heuristic baselines only (deterministic, no LLM):**
```bash
python run_experiment.py --experiments baselines --runs 100 --env .env.azure
```

**Azure LLM conditions (gpt-4.1-mini and o4-mini), in tmux with nohup:**
```bash
tmux new-session -s prod_v4we_azure
BACKEND=azure nohup python run_experiment.py \
    --experiments baselines E1_IC_azure E2_IC_azure E4_IC_azure E4_IC_o4mini \
    --runs 20 --env .env.azure \
    > v4we_azure_prod.log 2>&1
```

**Local LLM conditions (phi4:14b, nemotron 120B), in tmux with nohup:**
```bash
tmux new-session -s prod_v4we_local
BACKEND=local nohup python run_experiment.py \
    --experiments E1_IC_phi E2_IC_nemotron E3_IC E4_IC_phi \
    --env .env.local \
    > v4we_local_prod.log 2>&1
```

Fresh runs write per-condition output directories under `code/results/` (each with a `summary.json` and a `provenance.json` carrying the demand-file SHA-256 and per-run seeds). The published summaries used in this writeup are kept at the top-level `results/` directory.

Note: The Azure reasoning model (o4-mini) requires `MODEL_REASONING` and `MAX_TOKENS_REASONING` in the env file; do not pass `temperature` for this model. A missing key raises `KeyError` at the first API call.

## Citation

Srinivasan, S. (2026). *Agentic Bullwhip Effect V4: The Equaliser Effect — Intent Classification in Supply Chain Replenishment.* Industrial Mind and Code. https://industrialmindandcode.ai/blog/agentic-bullwhip-v4

Related work in this series:
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). Information Distortion in a Supply Chain: The Bullwhip Effect. *Management Science*, 43(4), 546–558. https://doi.org/10.1287/mnsc.43.4.546
- Chen, F., Drezner, Z., Ryan, J.K., & Simchi-Levi, D. (2000). Quantifying the Bullwhip Effect in a Simple Supply Chain. *Management Science*, 46(3), 436–443. https://doi.org/10.1287/mnsc.46.3.436.12069
- Forrester, J.W. (1961). *Industrial Dynamics.* MIT Press.
- Silver, E.A., Pyke, D.F., & Thomas, D.J. (2017). *Inventory and Production Management in Supply Chains* (4th ed.). CRC Press.

---

_Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience._
