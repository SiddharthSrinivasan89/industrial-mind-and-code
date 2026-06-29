# Agentic Bullwhip Effect — Version 5: Control Architecture

## Abstract

This experiment is Version 5 in a five-experiment series examining whether Large Language Models (LLMs) can reduce order variance amplification in multi-tier supply chains. V5 does not test LLMs at all. It removes the LLM classification layer entirely and replaces it with deterministic oracle labels — ground-truth perfect classifications — to determine whether the performance ceiling discovered in V4 (the "Equaliser Effect", OVAR approximately 1.73–1.78) is a consequence of model quality or a consequence of the architecture itself.

Fourteen conditions across six ablation groups were evaluated using n=20 runs each, spanning oracle label quality, multiplier map range, NEUTRAL class redefinition, order dampening, forecast oracle, and causal rule-based classification. The best result across all conditions is `neutral_smoothed_forecast` at OVAR 1.733, which improves on the Order-Up-To (OUT) baseline (1.753) by only 0.019 and remains 0.540 above the exponential smoothing baseline (1.193).

The Phase 1 gate criterion (any condition beats order_up_to by >= 0.10, or comes within 0.30 of exp_smoothing) was not met. Phase 2 LLM experiments were not warranted for this architecture. V5 closed the intent-classification lineage that ran from V1 through V5 and redirected the broader research program toward a different control architecture.

OVAR is defined as: OVAR = Var(orders) / Var(demand), computed per tier using sample variance (ddof=1) over all active ordering periods, then averaged as arithmetic mean across 3 tiers. Values below 1.0 indicate variance dampening; values above 1.0 indicate amplification.

## Repository Layout

- `README.md` — this overview, repo layout, and reproducibility instructions.
- `DESIGN.md` — design, parameters, conditions, and hypotheses.
- `FINDINGS.md` — consolidated findings with exact numbers and limitations.
- `REPORT_V5_Phase1.md` — the full Phase 1 gate report.
- `code/` — the runnable experiment: `run_experiment.py` (entry point), `simulation.py`, `agent_interface.py`, `oracle_policies.py`, `world_events.py`, `metrics.py`, `generate_demand_36m.py`, `backends/`, and `requirements.txt`.
- `code/data/synthetic/` — the synthetic 36-month demand series.
- `code/results/` — per-group result summaries (`summary.json`, `provenance.json`) for each timestamped run.

## Research Question

V4's Equaliser Effect finding left two competing interpretations:

1. **Model-quality hypothesis:** A better LLM that genuinely understood seasonal and event signals would choose labels more accurately, which would translate to lower OVAR.
2. **Architectural constraint hypothesis:** Even perfect labels cannot close the gap, because the source of variance is the OUT formula's reactive structure, not the classification quality.

**Primary question:** Do deterministic oracle labels (ground-truth perfect classifications fed directly to the intent-to-multiplier lookup) produce materially lower OVAR than the LLM conditions of V4? If yes, Phase 2 LLM experiments with improved models are warranted. If no, the ceiling is confirmed as architectural.

**Phase 1 gate criterion:** Any V5 condition must either beat `order_up_to` (OVAR approximately 1.75) by more than 0.10, or come within 0.30 of `exp_smoothing` (OVAR approximately 1.19), for Phase 2 LLM experiments to be justified.

## Experimental Design

### Supply Chain Structure

Identical to V4 WorldEvents, preserving cross-experiment OVAR comparability.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Simulation horizon:** 36 months (January 2025 through December 2027)
- **Lead times:** Stochastic (LogNormal distribution), further modified by world events
- **Fill rates:** Stochastic (Beta distribution), capped during world events
- **World events:** Pandemic (months 7–12), geopolitical conflict (months 19–21), port strike (months 28–30) — identical to V4

**Three-layer execution architecture (LLM layer replaced):**

```
Layer 1 — Label source (oracle or causal, no LLM)
  Oracle intent: ground-truth labels from GROUND_TRUTH_INTENT schedule
  Causal intent: rule-based classifier using calendar month and event signals only

Layer 2 — Lookup (deterministic, same as V4)
  Label -> multiplier value from fixed map

Layer 3 — OUT Formula (deterministic, same as V4)
  order = max(0, forecast + safety_stock * multiplier - inventory_position)
```

### Conditions and Models

No LLM was used. All conditions are deterministic (oracle or rule-based). n=20 runs per condition (Monte Carlo over stochastic lead time and fill rate draws).

**Ablation groups:**

| Group | Purpose |
|---|---|
| A1 Oracle | Oracle labels with the V4 multiplier map; the most direct test of the model-quality hypothesis |
| A2 Multiplier | Oracle labels with wider or asymmetric multiplier ranges; tests whether V4's conservative map was the bottleneck |
| A3 Neutral | Oracle labels with alternative NEUTRAL-class behaviour; tests whether NEUTRAL redefinition unlocks improvement |
| A4 Dampening | Oracle labels with order-smoothing applied post-formula; tests mechanical variance dampening |
| A5 Forecast | Event-adjusted demand forecast oracle; tests whether forecast quality is the bottleneck |
| A6 Causal | Rule-based calendar and event labels; fair deterministic benchmark matching LLM information conditions |

### Hypotheses

| Label | Hypothesis | Threshold | Verdict |
|---|---|---|---|
| **HV5-1** | Any Phase 1 condition beats order_up_to by >= 0.10 | OVAR improvement >= 0.10 over order_up_to | FAIL |
| **HV5-2** | Perfect oracle labels reduce OVAR below order_up_to | oracle_v4map OVAR < order_up_to OVAR | FAIL |
| **HV5-3** | Any multiplier map variant beats the V4 conservative map | Any A2 condition OVAR < oracle_v4map OVAR | FAIL |
| **HV5-4** | Any NEUTRAL redefinition produces meaningful OVAR reduction | OVAR improvement >= 0.10 over order_up_to | PARTIAL (marginal, 0.019) |
| **HV5-5** | Causal rule-based classifier outperforms oracle | causal_context OVAR < oracle_v4map OVAR | FAIL (within noise) |

## Results

### Key Metrics

Primary metric: Chain OVAR (arithmetic mean of per-tier OVAR). Secondary metric: chain-level stockout count across all 36 periods, mean over n=20 runs.

### Results Table

| Condition | n | Chain OVAR | Chain Stockouts | Notes |
|---|---|---|---|---|
| naive_passthrough | 20 | 0.9961 | 95.4 | Non-AI reference |
| exp_smoothing | 20 | 1.1931 | 89.5 | Target benchmark; gap = 0.000 |
| neutral_smoothed_forecast | 20 | 1.7334 | 89.5 | Best Phase 1 result; beats order_up_to by 0.019 |
| causal_context | 20 | 1.7493 | 87.2 | Rule-based calendar labels; same region as oracle |
| order_up_to | 20 | 1.7527 | 87.3 | V4 architecture floor |
| causal_unstructured | 20 | 1.7686 | 87.0 | Event signal adds noise |
| dampened_beta50 | 20 | 1.7654 | 93.5 | beta=0.50 order smoothing |
| oracle_v4map | 20 | 1.7759 | 87.0 | Perfect labels + V4 map; worse than order_up_to |
| oracle_moderate | 20 | 1.7979 | 87.2 | Perfect labels + wider map (±25/50%) |
| oracle_asymmetric | 20 | 1.8314 | 87.0 | Asymmetric map |
| oracle_aggressive | 20 | 1.8593 | 87.0 | Perfect labels + widest map (±40/80%) |
| dampened_beta75 | 20 | 1.9628 | 89.0 | beta=0.75 |
| dampened_beta25 | 20 | 1.8216 | 96.3 | beta=0.25 |
| neutral_dampened_out | 20 | 2.0001 | 89.7 | Partial dampening on NEUTRAL |
| forecast_oracle_events | 20 | 2.0094 | 85.3 | Event-adjusted F_t |
| neutral_repeat_last | 20 | 2.2231 | 88.2 | NEUTRAL -> repeat last order |
| neutral_floor_only | 20 | 2.3129 | 89.2 | NEUTRAL -> no order if stocked |

Gap structure:
```
exp_smoothing            1.1931  (benchmark)
                         ------  gap: 0.540  ------
neutral_smoothed_forecast  1.7334  (best Phase 1 result)
order_up_to                1.7527  (V4 architecture floor)
oracle_v4map               1.7759  (perfect labels, still above order_up_to)
```

### Hypothesis Verdicts

**HV5-1 — Any condition beats order_up_to by >= 0.10: FAIL**
Best margin: 0.019 (neutral_smoothed_forecast). No condition exceeded the 0.10 threshold.

**HV5-2 — Perfect oracle labels reduce OVAR below order_up_to: FAIL**
`oracle_v4map` achieves OVAR 1.7759, which is worse than `order_up_to` at 1.7527. A hypothetical classifier that correctly labels every period would still produce higher OVAR than the unmodified OUT formula with no classification layer.

**HV5-3 — Any multiplier map variant beats V4 conservative map: FAIL**
All three wider multiplier maps (moderate, aggressive, asymmetric) produced higher OVAR (1.797–1.859) than the V4 conservative map (1.776). Larger safety-stock swings compound variance further upstream regardless of label accuracy.

**HV5-4 — Any NEUTRAL redefinition produces meaningful OVAR reduction: PARTIAL**
`neutral_smoothed_forecast` (NEUTRAL mapped to forecast-only order with no safety stock) achieves OVAR 1.733, a 0.019 improvement over `order_up_to`. This is the only condition in V5 that mechanically approaches exponential smoothing behaviour during NEUTRAL periods — which constitute the majority of periods. All other NEUTRAL redefinitions produced substantially worse OVAR (2.0–2.3). The improvement is real but falls well short of the 0.10 threshold.

**HV5-5 — Causal rule-based classifier outperforms oracle: FAIL (within noise)**
`causal_context` (1.7493) is marginally better than `oracle_v4map` (1.7759), but both sit within the same noise band and both are worse than `order_up_to`. The difference is not interpretable as a meaningful effect.

**Gate verdict: FAIL.** Phase 2 LLM experiments are not justified.

## Discussion

The oracle experiment resolves the central ambiguity left by V4. The finding is unambiguous: `oracle_v4map`, which uses ground-truth perfect classifications, produces OVAR 1.7759 — worse than the Order-Up-To formula with no classification layer at all (1.7527). This rules out the model-quality hypothesis. A hypothetical LLM that classified every period perfectly would not close the gap to exponential smoothing; it would not even match the formula baseline.

The source of the 0.540 gap between the intent-classifier architecture and exponential smoothing is the structure of the OUT formula itself. The intent classifier always applies safety stock (multiplier times base safety stock), which adds an inventory-based signal on top of the forecast. Even at multiplier=1.0 (NEUTRAL), base safety stock generates order volatility that compounds at upstream tiers. Exponential smoothing uses only an EMA forecast with no safety stock buffer, which naturally attenuates variance at every tier. The two architectures solve fundamentally different problems: exponential smoothing optimises variance stability; the OUT formula optimises service level through buffering. They cannot be directly compared as equivalent alternatives.

The `neutral_smoothed_forecast` finding confirms this interpretation by exception. When NEUTRAL periods use forecast-only ordering (no safety stock), the condition partially mimics exponential smoothing behaviour and achieves the best V5 result (1.7334). The marginal traction here is precisely because it removes the safety stock component during the majority of periods. Extending this logic fully — replacing the OUT formula entirely with an EMA-based policy — is the architectural change identified as the candidate for a future experiment line (implemented as V6 StatelessSwing).

The causal rule-based result confirms that calendar and event labels carry essentially no predictive value for variance reduction within this architecture. A simple hand-written rule matches the oracle result, confirming that even if LLMs were trained specifically on this supply chain, the label quality cannot be the path to improvement.

## Limitations

1. **Architecture-specific conclusions:** The findings apply to the specific combination of discrete intent classification, five-label lookup table, and OUT-style ordering formula. They do not generalise to all possible AI-augmented supply chain architectures.
2. **Stochastic environment:** V5 uses the same stochastic lead time and fill rate parameterisation as V4 WorldEvents. The 0.540 gap figure is specific to this simulation environment.
3. **Single supply chain topology:** Three-tier serial cascade with simplified structure relative to real supply chains.
4. **Single demand profile:** Results are specific to the 36-month Indian automotive seasonal demand series with three injected disruption types.
5. **n=20 per condition:** Adequate for detecting effects at the defined MPRD threshold; smaller effects may be underpowered.
6. **Hypotheses were not pre-registered.** They were stated in the design document prior to execution but not deposited with any external registry.
7. **Lineage closure:** The decision to close the V1-V5 intent-classification line at Phase 1 reflects the absence of any finding that would justify continued investment in this architectural direction. It is not a claim that no AI-augmented supply chain architecture can outperform exponential smoothing; it is a claim that this specific five-label intent classifier approach with the OUT formula cannot. The broader research program continues by changing the control lever, beginning with V6 adaptive smoothing.

## How to Reproduce

### Prerequisites

- Python 3.10 or later
- No LLM credentials required (all V5 Phase 1 conditions are deterministic)
- A tmux session is recommended for any run exceeding a few minutes
- nohup is required for remote client environments

### Environment Setup

```bash
cd experiments/agentic-bullwhip-v5-control-architecture/code/

# Install dependencies
pip install -r requirements.txt
```

No API credentials are required for Phase 1 conditions. All label sources are deterministic (oracle schedule or causal rule).

### Running the Experiment

The entry point is `code/run_experiment.py`. Its flags are: `--experiments` (one or more group names: `baselines A1_oracle A2_multiplier A3_neutral A4_dampening A5_forecast A6_causal`), `--runs N` (overrides the per-spec run count for every condition; omit to use the per-spec defaults), `--env` (path to a `.env` file, default `.env`), `--results-dir` (output directory, default `results/`), and `--no-events` (disable all world events). The demand series at `data/synthetic/tatva_monthly_dispatches_36m.csv` is read directly; regenerate it with `python generate_demand_36m.py` if it is missing.

**All Phase 1 conditions (deterministic, no LLM calls):**
```bash
# Run all ablation groups at n=20
python run_experiment.py --experiments baselines A1_oracle A2_multiplier A3_neutral A4_dampening A5_forecast A6_causal --runs 20

# Or run a single group for inspection
python run_experiment.py --experiments A1_oracle --runs 20
```

**In tmux with nohup for a full production run:**
```bash
tmux new-session -s prod_v5
nohup python run_experiment.py \
    --experiments baselines A1_oracle A2_multiplier A3_neutral A4_dampening A5_forecast A6_causal \
    --runs 20 \
    > v5_prod.log 2>&1
```

Each run writes a timestamped directory under `results/<group>/` containing `summary.json` (the per-condition OVAR, stockout, and service-level statistics) and `provenance.json` (the dataset checksum, world-event configuration, and condition specs). Because all conditions are deterministic (no LLM calls), run time is determined by simulation steps only; the full 14-condition suite at n=20 completes within a few hours on a standard CPU.

## Citation

Srinivasan, S. (2026). *Agentic Bullwhip Effect V5: The Ceiling Is in the Formula — Oracle Labels and the End of the Intent-Classification Line.* Industrial Mind and Code. https://industrialmindandcode.ai/blog/agentic-bullwhip-v5

Related work in this series:
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). Information Distortion in a Supply Chain: The Bullwhip Effect. *Management Science*, 43(4), 546–558. https://doi.org/10.1287/mnsc.43.4.546
- Chen, F., Drezner, Z., Ryan, J.K., & Simchi-Levi, D. (2000). Quantifying the Bullwhip Effect in a Simple Supply Chain. *Management Science*, 46(3), 436–443. https://doi.org/10.1287/mnsc.46.3.436.12069
- Silver, E.A., Pyke, D.F., & Thomas, D.J. (2017). *Inventory and Production Management in Supply Chains* (4th ed.). CRC Press.
- Forrester, J.W. (1961). *Industrial Dynamics.* MIT Press.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
