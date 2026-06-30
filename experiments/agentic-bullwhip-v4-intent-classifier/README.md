# Agentic Bullwhip Effect — Version 4: Intent Classifier (Intermediate Variant)

## Abstract

This experiment is the intermediate variant of Version 4 in a five-experiment series examining whether Large Language Models can reduce order variance amplification in multi-tier supply chains. The primary published V4 result is the WorldEvents version; the Intent Classifier variant described here established the architectural design — replacing a continuous float multiplier output with a discrete five-label classification interface — on a 25-month, no-disruption demand series before that design was carried forward into the full 36-month, world-events environment.

The core architectural claim under test is that separating qualitative seasonal reasoning (a task suited to LLMs) from order arithmetic (a task suited to deterministic formulas) improves compliance reliability and matches or surpasses the performance of the prior float-based approach (V3b HybridArch). The discrete label output also introduces a new primary metric — intent classification accuracy — alongside the established Order Variance Amplification Ratio (OVAR).

Note: This experiment produced the design, prompt architecture, and lookup table that all subsequent V4 experiments used. It was run with gpt-4.1-mini on Azure at n=20 across the three intent-classification conditions plus the deterministic baselines. Readers seeking the broader V4 finding under world-events disruptions should also consult the WorldEvents experiment in this series.

## Repository layout

| Path | Contents |
|---|---|
| `README.md` | This overview, design summary, results, and reproducibility instructions |
| `FINDINGS.md` | Plain-language consolidated findings |
| `DESIGN.md` | Full experiment design and hypotheses |
| `data/` | Synthetic demand series (`tatva_monthly_dispatches_25m.csv`), calibrated to Indian automotive seasonality and SHA-256 stamped at runtime |
| `code/` | Reproducible harness — `run_experiment.py`, `simulation.py`, `agent_interface.py`, `metrics.py`, and the Azure backend |
| `results/<group>/<timestamp>/` | Per-condition `summary.json` and `provenance.json` metric manifests (raw per-run records are not published) |

The result of record is the n=20 Azure set (timestamp `20260629T204200`); an earlier n=10 set is retained only to support the n=10→n=20 stability comparison.

## Research Question

**Primary:** Does replacing the continuous float output of V3b with a discrete five-label intent classification — where the LLM selects one of {`STRONG_INCREASE`, `MODERATE_INCREASE`, `NEUTRAL`, `MODERATE_DECREASE`, `STRONG_DECREASE`} and a deterministic lookup table converts that label to a safety stock multiplier — improve supply chain ordering performance, compliance reliability, and decision auditability relative to V3b's float-based approach?

**Secondary:** Does the intent classifier interface reduce parse failures to near zero while preserving or improving OVAR and stockout performance?

**Design principle:** The LLM's task is reduced to the simplest possible meaningful decision: which buffer direction applies this period. All arithmetic consequences of that decision — the multiplier value, the safety stock, the order quantity — are computed deterministically from a lookup table and an Order-Up-To (OUT) style formula. The LLM never produces a number.

## Experimental Design

### Supply Chain Structure

The experiment uses a three-tier serial supply chain calibrated to an Indian automotive parts context.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Lead time:** 1 month deterministic (order placed in period t arrives at start of t+1)
- **Visibility:** No cross-tier information sharing; each tier observes only its immediate downstream order
- **Timing per period:** replenishment arrives, then fulfilment, then ordering, then records append
- **Initial inventory (S):** approximately 43,600 units (mean demand plus 1.65 standard deviations)
- **Base safety stock:** approximately 5,061 units (S minus mean demand)
- **Simulation horizon:** 25 months (January 2025 through January 2027); 24 active ordering periods plus one close-out period

The demand series (`tatva_monthly_dispatches_25m.csv`, SHA-256 stamped at runtime) is calibrated to real Indian automotive market data: mean 38,446 units per month across 24 active periods, with two annual cycles of seasonal variation covering major Indian calendar events including Diwali, Navratri, monsoon slump, and financial-year-end peak.

### Conditions and Models

The three-layer execution architecture per period per tier:

```
Layer 1 — Classification (LLM)
  Input:  state variables + optional context
  Output: {"intent": "<CLASS>", "rationale": "..."}
  Task:   select one of five categorical labels

Layer 2 — Lookup (deterministic)
  Input:  intent label
  Output: multiplier_t (float from fixed lookup table)

Layer 3 — Execution (deterministic, OUT-style)
  order_t = max(0, target_position - inventory_position_t)
  where target_position = round(F_t) + base_SS * multiplier_t
  and   F_t = 0.30 * D_t + 0.70 * F_{t-1}
```

**Intent class lookup table (design values):**

| Intent class | Demand deviation band | Multiplier | Interpretation |
|---|---|---|---|
| `STRONG_INCREASE` | > +10% above mean | 2.5 | FY-end structural peak, Diwali |
| `MODERATE_INCREASE` | +3% to +10% | 1.5 | Minor festive periods |
| `NEUTRAL` | -5% to +3% | 1.0 | No material seasonal signal |
| `MODERATE_DECREASE` | -5% to -10% | 0.75 | Early and late monsoon |
| `STRONG_DECREASE` | < -10% | 0.5 | Peak monsoon |

**Experimental conditions:**

| Label | Policy | Context | Backend |
|---|---|---|---|
| `exp_smoothing` | Heuristic baseline | — | — |
| `hybrid_control` | OUT formula, multiplier=1.0 | — | — |
| `intent_blind_azure` | Intent classification | State variables only | Azure (gpt-4.1-mini) |
| `intent_context_azure` | Intent classification | State + calendar + tier persona | Azure (gpt-4.1-mini) |
| `intent_stateful_azure` | Intent classification | State + calendar + 3-period intent history | Azure (gpt-4.1-mini) |

- **Runs:** 20 per LLM condition (deterministic baselines: 1 run each)
- **Model:** gpt-4.1-mini via Azure OpenAI GlobalStandard

### Hypotheses

| Label | Hypothesis | Threshold | Decision rule |
|---|---|---|---|
| **H-IC1** | Best V4 condition OVAR does not exceed exp_smoothing OVAR and stockout count | Chain OVAR <= exp_smoothing AND stockouts <= exp_smoothing | Pass if any V4 condition meets both simultaneously |
| **H-IC2** | Intent compliance rate is near-perfect | >= 0.99 across all V4 conditions | Intent is a more reliable output interface than the float approach of V3b |
| **H-IC3** | IC-Context direction accuracy exceeds chance | >= 0.60 across event periods | Calendar context enables directionally correct classification |
| **H-IC4** | IC-Stateful accuracy exceeds IC-Context accuracy | Delta accuracy >= 0.10 | History enables self-correction of classification errors |
| **H-IC5** | IC-Context entropy exceeds IC-Blind entropy | IC-Context entropy > IC-Blind entropy | Context increases classification discrimination |

## Results

I ran this experiment with gpt-4.1-mini on Azure at n=20 across the three intent-classification conditions (IC-Blind, IC-Context, IC-Stateful) and the two deterministic baselines. **The n=20 Azure set is the result of record.** An earlier n=10 Azure set is retained only to support the documented n=10→n=20 stability comparison. Headline results below; the plain-language walkthrough is in `FINDINGS.md`.

| Condition | chain OVAR (n=20) | Chain stockouts | Intent compliance |
|---|---|---|---|
| `exp_smoothing` (baseline) | 0.545 | 5 | — |
| `hybrid_control` (baseline) | 1.710 | 14 | — |
| IC-Blind (`intent_blind_azure`) | 3.843 ± 0.129 | 12.05 ± 0.94 | 1.000 |
| IC-Context (`intent_context_azure`) | 3.268 ± 0.062 | 15.70 ± 0.80 | 1.000 |
| IC-Stateful (`intent_stateful_azure`) | 3.762 ± 0.084 | 12.05 ± 1.15 | 1.000 |

Three findings stand out. First, intent compliance was perfect — 1.000 across every condition and every run, with zero fallbacks — confirming the discrete five-label interface as a reliable output format. Second, every LLM condition amplified order-swing well above the exponential-smoothing baseline: chain OVAR of roughly 3.3 to 3.8 against the baseline's 0.545, about six to seven times larger. Third, the three information conditions barely separated, the "Equaliser Effect": forcing the decision into a small fixed label set caps how far any condition's outcome can move. The means were stable when I doubled the sample from n=10 to n=20 (every metric moved less than one standard deviation), so the picture is robust rather than a small-sample fluke.

For the same architecture tested under world-events disruptions, see the V4 WorldEvents README and report in this repository, and the writeup at `https://industrialmindandcode.ai/blog/agentic-bullwhip-v4`.

## Discussion

The design rationale for the intent classifier architecture addresses a specific failure of V3b: language models have no intrinsic number line and consistently miscalibrate continuous float outputs. The discrete label interface removes the numerical generation task entirely, confining the LLM to a classification task — an operation well within the demonstrated capability of instruction-following language models.

The five-class structure was chosen to match the five qualitatively distinct demand regimes present in the Indian automotive seasonal calendar, ensuring that the ground-truth intent distribution is empirically derivable from the demand series rather than arbitrarily imposed.

The lookup table design represents a deliberate architectural constraint: by exposing the multiplier values to the LLM in the system prompt (e.g., "STRONG_INCREASE maps to multiplier 2.5"), the model is informed of the downstream consequences of its classification, making the reasoning task concrete rather than abstract.

The key insight subsequently confirmed in the WorldEvents variant is that this constraint introduces what the V4 WorldEvents report terms the "Equaliser Effect": the discrete lookup table creates a structural ceiling and floor on OVAR that no model, prompt design, or information condition can escape, because the label-to-multiplier mapping removes the AI's capacity for fine-grained adjustment.

## Limitations

1. **Single demand series:** The 25-month synthetic series is specific to Indian automotive seasonal patterns. Findings are not established to generalise to other markets or demand structures.
2. **Single supply chain topology:** The three-tier serial cascade with unit lead time is a simplified structure relative to real multi-echelon supply chains with variable lead times and lateral flows.
3. **Synthetic calibration:** The intent-to-multiplier lookup values are either domain-logic-driven or intended to be calibrated from V3b float output medians. Neither approach is guaranteed to be globally optimal.
4. **Model-specific results:** Findings are for gpt-4.1-mini and may not generalise to other language models.
5. **No adversarial conditions:** The 25-month simulation tests seasonal variation but not demand shocks, supply disruptions, or structural mean shifts.
6. **n=20:** A sample of 20 runs provides adequate variance estimates at the defined MPRD threshold of 0.5 OVAR units; smaller effects may be underpowered.

## How to Reproduce

### Prerequisites

- Python 3.10 or later
- Access to an Azure OpenAI gpt-4.1-mini deployment
- A tmux session is recommended for the longer Azure runs
- nohup is required for remote client environments

### Environment Setup

```bash
cd experiments/agentic-bullwhip-v4-intent-classifier/code/

# Install dependencies
pip install -r requirements.txt

# Create a .env.azure file with the variables below (fill in your own values)
```

Required variables in `.env.azure`:
```
AZURE_ENDPOINT=<your-endpoint>
AZURE_API_KEY=<your-key>
AZURE_API_VERSION=<api-version>
MODEL_LIGHTWEIGHT=gpt-4.1-mini
```

### Running the Experiment

**Dry run (no LLM calls, pipeline validation):**
```bash
DRY_RUN=1 python run_experiment.py --experiments baselines H1_IC --runs 2 --env .env.azure
```

**Smoke test (2 runs, real LLM):**
```bash
BACKEND=azure python run_experiment.py --experiments H1_IC --runs 2 --env .env.azure
```

**Production runs (in tmux with nohup):**
```bash
tmux new-session -s prod_v4ic_azure
BACKEND=azure nohup python run_experiment.py \
    --experiments baselines H1_IC H2_IC H3_IC --runs 20 --env .env.azure \
    > ../logs/v4ic_azure_prod.log 2>&1
```

Each run writes a timestamped bundle under `results/<group>/<timestamp>/` containing
`records.parquet`, `summary.json`, and `provenance.json`.

## Citation

Srinivasan, S. (2026). *Agentic Bullwhip Effect V4: The Equaliser Effect — Intent Classification in Supply Chain Replenishment.* Industrial Mind and Code. https://industrialmindandcode.ai/blog/agentic-bullwhip-v4

Related work in this series:
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). Information Distortion in a Supply Chain: The Bullwhip Effect. *Management Science*, 43(4), 546–558. https://doi.org/10.1287/mnsc.43.4.546
- Chen, F., Drezner, Z., Ryan, J.K., & Simchi-Levi, D. (2000). Quantifying the Bullwhip Effect in a Simple Supply Chain. *Management Science*, 46(3), 436–443. https://doi.org/10.1287/mnsc.46.3.436.12069
- Silver, E.A., Pyke, D.F., & Thomas, D.J. (2017). *Inventory and Production Management in Supply Chains* (4th ed.). CRC Press.
