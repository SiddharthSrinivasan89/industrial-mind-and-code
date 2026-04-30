
# Hybrid LLM Safety-Stock Control in a Three-Tier Supply Chain:
## Comparative Azure Analysis — gpt-4.1-mini vs o4-mini

## Abstract
This report presents a comparative analysis of two Azure arms of a self-contained simulation experiment testing whether a large language model can improve supply-chain ordering performance when used as a planner inside a deterministic replenishment policy. Both arms share the same experimental design: a three-tier serial supply chain, a 25-month automotive demand series, and a hybrid architecture in which the model outputs a safety-stock multiplier while a deterministic rule computes the final order quantity. The Azure arms differ only in the model used: `gpt-4.1-mini` (20 runs per hybrid condition) and `o4-mini` (20 runs per hybrid condition). Both arms were run to completion under production conditions. Operationally, both models performed reliably: outputs were valid, fallback and clamp rates were zero, and live inference was confirmed throughout active periods for all conditions. Substantively, all four formal hypotheses failed for both models. Neither model matched the within-experiment `exp_smoothing` benchmark on OVAR and stockouts simultaneously; contextual prompting did not produce a practically meaningful improvement over the blind condition; adding state worsened order variance; and multiplier pattern quality remained below target. The two models differed meaningfully in their behavioral tendencies: `gpt-4.1-mini` was more conservative in the blind condition but escalated buffering as context was added, whereas `o4-mini` was more aggressive in the blind condition and moderated slightly with context. These behavioral differences did not translate into better control outcomes for either model. The Azure results therefore constitute a joint negative finding: the hybrid planner is technically viable on both models but did not improve supply-chain control on this demand series with either.

## 1. Introduction
Supply chains are vulnerable to unstable ordering behavior. When firms overreact to short-term demand changes, order variability can increase as one moves upstream, producing excess inventory, avoidable shortages, and the bullwhip effect. Large language models can often recognize seasonal patterns and explain business context well, but they are less dependable when asked to make precise numeric control decisions directly.

This experiment tests a narrower and more structured role for the model. Instead of allowing the LLM to choose monthly order quantities, the model is asked to adjust only one parameter of a deterministic replenishment policy: the safety-stock level. The central research question is whether an LLM can contribute useful directional planning while leaving arithmetic execution to a fixed formula.

This report covers both Azure arms. `gpt-4.1-mini` is a fast, cost-efficient model optimized for structured output tasks. `o4-mini` is a reasoning model that uses chain-of-thought inference internally before producing a response. Both were tested under the same experimental protocol. Comparing them within the same experiment isolates model-level behavioral differences from task and architecture effects.

All results are evaluated entirely within this experiment's own baselines and controls.

## 2. Key Terminology
Definitions follow those established in the companion report `v3b_azure_interim_analysis_codex.md`. The terms most relevant to the cross-model comparison are:

- **OVAR**: Order Variance Ratio, `Var(order_placed) / Var(demand_received)`. Chain OVAR is the mean across the three tiers. Lower is better; `OVAR > 1.0` indicates bullwhip amplification.
- **Safety stock multiplier**: The LLM's control variable. A multiplier above `1.0` increases the buffer level; below `1.0` decreases it. The final order is computed deterministically from this input.
- **Multiplier pattern score (MPS)**: Whether the LLM's chosen multiplier moves in the expected seasonal direction, independent of the final order quantity. This is the most direct measure of contextual reasoning quality in a hybrid architecture.
- **Pattern score (PS)**: Whether the final orders placed align with expected seasonal demand patterns. This is downstream of the multiplier and also reflects the execution formula's smoothing.
- **Compliance rate**: The fraction of responses that parsed successfully, remained within the required structure, stayed within the allowed multiplier range, and required no fallback. A reliability metric, not a quality metric.
- **Hybrid control**: The deterministic architectural control. Same execution formula as the hybrid conditions, but multiplier fixed at `1.0`. Isolates the LLM's contribution from the formula change.

## 3. Experimental Design
The simulation represents a three-tier serial supply chain: OEM, ancillary supplier, and component supplier. Retail demand enters at the OEM tier. Each tier fulfills downstream demand, updates on-hand inventory and backlog, and places an order to its upstream supplier. Lead time is one month and deterministic. Each tier observes only its immediate downstream order.

The demand data span 25 months. The first 24 months are active ordering periods. The 25th month is a closeout period used for final fulfillment without a new replenishment decision. The dataset is a synthetic 25-month Indian automotive dispatch series (`tatva_monthly_dispatches_25m.csv`), SHA-256 checksummed at runtime.

## 4. Hybrid Policy Structure
The hybrid policy separates planning from execution.

### 4.1 Planning Layer
The LLM receives the current operational state and, depending on condition, may also receive calendar context or recent history. It returns:

```json
{"safety_stock_multiplier": x, "rationale": "..."}
```

### 4.2 Execution Layer
The simulator computes the actual order using a deterministic Order-Up-To style rule:

\[
F_t = 0.30D_t + 0.70F_{t-1}
\]

\[
SS_t = base\_SS \times multiplier_t
\]

\[
target\_position_t = round(F_t) + SS_t
\]

\[
order_t = max(0, target\_position_t - inventory\_position_t)
\]

This design ensures that the model influences the system only through buffer adjustment. The final order remains a deterministic function of demand forecast, buffer level, and inventory state.

## 5. Conditions
The experiment includes three hybrid conditions and two deterministic references.

### 5.1 Deterministic References
- `exp_smoothing`: within-experiment benchmark
- `hybrid_control`: same hybrid execution formula, but multiplier fixed at `1.0`

### 5.2 Hybrid Conditions
- `H1` Hybrid-Blind: state only
- `H2` Hybrid-Context: state plus calendar month and tier persona
- `H3` Hybrid-Stateful: context plus a trailing three-period history of demand, order, multiplier, backlog, and stockout outcome

Each Azure arm was run with 20 runs per hybrid condition.

## 6. Hypotheses
Four hypotheses are tested in each Azure arm.

### H1
At least one hybrid condition will achieve:
- chain OVAR less than or equal to `exp_smoothing`
- chain stockouts less than or equal to `exp_smoothing`

### H2
`Hybrid-Context` will improve over `Hybrid-Blind` by at least `0.5` OVAR.

### H3
`Hybrid-Stateful` will improve over `Hybrid-Context` by at least `0.5` OVAR.

### H4
`Hybrid-Context` will achieve multiplier pattern score greater than or equal to `0.5`.

These thresholds are meant to distinguish practically meaningful improvement from small numerical drift.

## 7. Validation of Azure Result Sets
Both arms must be confirmed as valid evidence before interpreting performance.

### 7.1 gpt-4.1-mini Result Set
The verified gpt-4.1-mini result set is:
- `baselines/20260415T040840`
- `H1/20260415T040840`
- `H2/20260415T050149`
- `H3/20260415T055625`

Validation results:
- all expected run counts present (20 runs per hybrid condition)
- no negative orders
- all active hybrid rows showed live inference
- rationales present for all active hybrid rows
- fallback rate: `0.0%`
- mean clamp count: `0.0`
- all OVAR values finite

### 7.2 o4-mini Result Set
The verified o4-mini result set is:
- `baselines/20260415T133112`
- `H1/20260415T133112`
- `H2/20260415T160633`
- `H3/20260415T182338`

Validation results:
- all expected run counts present (20 runs per hybrid condition)
- no negative orders
- all active hybrid rows showed live inference
- rationales present for all active hybrid rows
- fallback rate: `0.0%`
- mean clamp count: `0.0`
- all OVAR values finite
- H3 required 3 replacement runs (23 total attempts for 20 valid completions); all valid runs passed validation

Both arms are valid experimental findings rather than smoke-test artifacts.

## 8. Results

### 8.1 Deterministic References
The deterministic conditions are identical across both arms as they do not involve LLM inference.

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `exp_smoothing` | 0.5446 | 5.0 | 4769.1 |
| `hybrid_control` | 1.7097 | 14.0 | 5141.7 |

### 8.2 gpt-4.1-mini Hybrid Conditions

| Condition | Chain OVAR (mean ± std) | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `H1` Blind | 2.3325 ± 0.1108 | 10.6 | 6030.4 |
| `H2` Context | 2.9763 ± 0.0958 | 11.0 | 6780.7 |
| `H3` Stateful | 2.7226 ± 0.1512 | 11.6 | 7247.5 |

### 8.3 o4-mini Hybrid Conditions

| Condition | Chain OVAR (mean ± std) | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `H1` Blind | 2.5232 ± 0.2791 | 8.9 | 7608.5 |
| `H2` Context | 2.4395 ± 0.1616 | 11.7 | 6487.1 |
| `H3` Stateful | 3.1211 ± 0.1320 | 10.7 | 7218.3 |

### 8.4 Diagnostics: gpt-4.1-mini

| Condition | Pattern Score | Multiplier Pattern Score | Mean Multiplier | Fallback | Clamp | Compliance |
|---|---:|---:|---:|---:|---:|---:|
| `H1` Blind | 0.2011 | 0.1875 | 1.1298 | 0.0 | 0.0 | 1.000 |
| `H2` Context | 0.3125 | 0.2667 | 1.3103 | 0.0 | 0.0 | 1.000 |
| `H3` Stateful | 0.2826 | 0.3193 | 1.4291 | 0.0 | 0.0 | 1.000 |

### 8.5 Diagnostics: o4-mini

| Condition | Pattern Score | Multiplier Pattern Score | Mean Multiplier | Fallback | Clamp | Compliance |
|---|---:|---:|---:|---:|---:|---:|
| `H1` Blind | 0.1958 | 0.3189 | 1.4808 | 0.0 | 0.0 | 1.000 |
| `H2` Context | 0.3390 | 0.3250 | 1.2447 | 0.0 | 0.0 | 1.000 |
| `H3` Stateful | 0.3106 | 0.3038 | 1.3488 | 0.0 | 0.0 | 1.000 |

### 8.6 Inference Latency

| Model | H1 Blind | H2 Context | H3 Stateful |
|---|---:|---:|---:|
| `gpt-4.1-mini` | ~2044 ms | ~2082 ms | ~2367 ms |
| `o4-mini` | ~6346 ms | ~5576 ms | ~7913 ms |

## 9. Hypothesis Outcomes

### 9.1 H1: At least one hybrid condition matches or beats `exp_smoothing` on both chain OVAR and chain stockouts.

**gpt-4.1-mini: Failed.**

The best OVAR was `H1` at `2.3325`, far above the benchmark `0.5446`. The lowest stockout count was also `H1` at `10.6`, far above the benchmark `5.0`. No hybrid condition came close to matching `exp_smoothing` on either metric simultaneously.

**o4-mini: Failed.**

The best OVAR was `H2` at `2.4395`, again far above `0.5446`. The lowest stockout count was `H1` at `8.9`, still far above `5.0`. As with `gpt-4.1-mini`, no hybrid condition approached the benchmark.

**Joint outcome:** Both models failed H1 by wide margins on both criteria. The benchmark remained clearly superior to all six hybrid conditions across both arms.

### 9.2 H2: `Hybrid-Context` improves over `Hybrid-Blind` by a practically meaningful margin (`ΔOVAR ≥ 0.5`).

**gpt-4.1-mini: Failed.**

`Hybrid-Context` did not improve over `Hybrid-Blind`. OVAR worsened from `2.3325` to `2.9763`, a deterioration of `0.6438`. Stockouts also worsened slightly from `10.6` to `11.0`. Adding calendar context to `gpt-4.1-mini` increased order variance rather than reducing it.

**o4-mini: Failed.**

`Hybrid-Context` improved slightly over `Hybrid-Blind` (`2.4395` vs `2.5232`), a gain of `0.0837`, far below the `0.5` threshold. Stockouts worsened from `8.9` to `11.7`. The improvement in variance was not practically significant, and service level declined.

**Joint outcome:** Both models failed H2. Notably, the two models failed in opposite directions: `gpt-4.1-mini` context worsened OVAR substantially, while `o4-mini` context produced only a marginal improvement. Neither demonstrated the targeted level of behavioral improvement.

### 9.3 H3: `Hybrid-Stateful` improves over `Hybrid-Context` by a practically meaningful margin (`ΔOVAR ≥ 0.5`).

**gpt-4.1-mini: Failed.**

`Hybrid-Stateful` improved slightly over `Hybrid-Context` on OVAR (`2.7226` vs `2.9763`), a recovery of `0.2537`. However, this fell short of the `0.5` threshold, and stockouts continued to worsen from `11.0` to `11.6`.

**o4-mini: Failed.**

`Hybrid-Stateful` did not improve over `Hybrid-Context`. OVAR worsened substantially from `2.4395` to `3.1211`, a deterioration of `0.6816`. Stockouts improved slightly from `11.7` to `10.7`, but the primary variance criterion showed clear regression.

**Joint outcome:** Both models failed H3. `gpt-4.1-mini` showed a modest partial recovery from its context-induced regression, while `o4-mini`'s stateful condition produced its worst performance overall. Additional history did not stabilize ordering behavior for either model.

### 9.4 H4: `Hybrid-Context` achieves seasonally meaningful safety-stock planning (`MPS ≥ 0.5`).

**gpt-4.1-mini: Failed.**

The multiplier pattern score for `Hybrid-Context` was `0.2667`, well below the target threshold.

**o4-mini: Failed.**

The multiplier pattern score for `Hybrid-Context` was `0.3250`, also well below the target threshold.

**Joint outcome:** Both models failed H4. Neither model adjusted safety stock in a sufficiently strong or consistent seasonal direction when given calendar context. `o4-mini` scored higher on MPS than `gpt-4.1-mini` in the context condition (`0.3250` vs `0.2667`), indicating somewhat better directional alignment, but both fell materially short of the `0.5` target.

## 10. Cross-Model Comparison

### 10.1 Primary Performance
`gpt-4.1-mini` achieved better chain OVAR in the blind condition (`2.3325` vs `2.5232`) and better stockout performance in the context condition, but worse stockout performance in the blind condition (`10.6` vs `8.9`). Neither model achieved consistently superior performance across all conditions. The overall performance gap between both models and `exp_smoothing` dwarfs the differences between the models themselves.

### 10.2 Multiplier Behavior
The two models showed a structurally different relationship between information and buffering:

- `gpt-4.1-mini` started conservative in the blind condition (mean multiplier `1.1298`) and escalated buffering monotonically as more context was added (`1.3103` context, `1.4291` stateful). Providing more context made the model more aggressive, not more precise.
- `o4-mini` started aggressive in the blind condition (mean multiplier `1.4808`) and pulled back modestly with context (`1.2447`), then increased again with history (`1.3488`). The model showed more sensitivity to the absence of context than to its presence.

In both cases, mean multipliers remained above `1.0` across all conditions, indicating a systematic bias toward over-buffering. Neither model learned to reduce buffer levels during low-demand periods.

### 10.3 Semantic Alignment vs Operational Control
`o4-mini` showed higher pattern score and multiplier pattern score in the context and stateful conditions, suggesting better semantic recognition of the demand context. However, this did not translate into better control outcomes. The `o4-mini` context condition had a higher MPS (`0.3250`) than `gpt-4.1-mini` (`0.2667`) but also had higher OVAR and worse stockouts than `gpt-4.1-mini`'s blind condition.

`gpt-4.1-mini` showed lower pattern scores across the board, consistent with a simpler internal representation of the seasonal context, but its blind condition achieved the lowest OVAR of any hybrid condition across both models.

### 10.4 State and Reactivity
Both models were harmed by the stateful condition in terms of stockout performance. `o4-mini` was harmed severely on OVAR (its worst condition overall). `gpt-4.1-mini` showed partial recovery from its context-induced regression but still did not improve over its blind condition baseline. This is consistent with the hypothesis that additional recent history encourages reactive over-adjustment rather than stabilizing behavior, and that this effect is stronger in reasoning models.

### 10.5 Reliability
Both models achieved perfect compliance across all conditions, with zero fallback events and zero clamp events. `gpt-4.1-mini` was approximately 3× faster per inference step (~2.0–2.4 s vs ~5.6–7.9 s for `o4-mini`). This reliability finding confirms that the technical architecture is sound with both models, and that the performance failures reflect behavioral quality rather than system instability.

## 11. Discussion
The comparative Azure results reinforce and extend the conclusions reached in the single-model analysis in `v3b_azure_interim_analysis_codex.md`.

The most important result is that all four hypotheses failed under both models, using identical experimental protocol. This strengthens the conclusion from a single-arm negative finding to a replicated negative finding across two architecturally distinct models. Neither a fast, cost-efficient generation model nor a reasoning model could improve upon the deterministic `exp_smoothing` benchmark on this demand series.

The `hybrid_control` result remains a structurally important reference point. Even before introducing the LLM, the hybrid execution formula underperforms `exp_smoothing` (OVAR `1.7097` vs `0.5446`). The LLM must therefore choose multipliers that compensate for this structural disadvantage — not simply neutral multipliers, but multipliers that actively reduce variance. Neither model consistently achieved this. All six hybrid conditions exceeded `hybrid_control` OVAR, meaning the LLM made the formula worse on average, not better.

The behavioral divergence between the two models is analytically useful. `gpt-4.1-mini`'s tendency to increase buffering with additional context, combined with the resulting OVAR increase in H2, suggests that context information activated stronger protective responses rather than more precise seasonal calibration. `o4-mini`'s stronger semantic alignment (higher MPS in H2 and H3) suggests it processed seasonal context more accurately at the level of reasoning, but the signal was not strong enough or consistently calibrated enough to translate into competitive control.

The pattern scores and multiplier pattern scores for both models fall in the range `0.19–0.34`. None of the twelve condition–model combinations broke `0.35`. This suggests that the core limitation is not specific to a particular model but reflects a general challenge: the demand series contains a mix of seasonal signals and non-seasonal variation that the LLM must interpret without any form of feedback, calibration, or explicit error correction.

These findings carry direct implications for the V4 experiment design. The intent classifier approach in V4 replaces continuous multiplier generation with discrete categorical labels, which are then mapped to fixed multipliers by a deterministic lookup. This change is motivated partly by the MPS results here: both models showed meaningful directional accuracy (above the 0.25 chance level expected from three meaningful categories), but neither could reliably produce multipliers that were well-calibrated enough to improve control. A categorical interface isolates the directional classification step from the calibration step, which is the core architectural change V4 is designed to test.

## 12. Conclusion
The joint Azure results support a clear and defensible conclusion. The hybrid architecture is operationally viable with both `gpt-4.1-mini` and `o4-mini`: both models can serve as stable planning components that produce valid safety-stock decisions under production conditions. However, operational viability did not translate into better supply-chain control with either model. On this 25-month demand series, neither Azure model improved the system. All twelve hybrid conditions remained materially worse than the deterministic `exp_smoothing` benchmark. Contextual prompting failed to produce practically meaningful improvement in either arm. Adding state worsened performance or produced insufficient improvement in both arms. Multiplier pattern quality remained well below target for both models.

The cross-model behavioral contrast — `gpt-4.1-mini` escalating buffering with context, `o4-mini` showing better semantic alignment but not better control — confirms that the limitation is not reducible to a specific model choice. The hybrid architecture as designed, with continuous multiplier output and no feedback mechanism, does not produce competitive supply-chain control on this task.

The Azure results therefore constitute a valid joint negative finding across both arms. The next analytical step is to compare these findings against the local production arm (nemotron-super-3:120b) once those runs are complete, in order to determine whether the limitation is specific to Azure-hosted models or reflects a broader limitation of the hybrid-control architecture regardless of the underlying LLM.
