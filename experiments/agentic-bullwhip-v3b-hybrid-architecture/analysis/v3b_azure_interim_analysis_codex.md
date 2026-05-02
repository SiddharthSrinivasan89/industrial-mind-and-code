
# Hybrid LLM Safety-Stock Control in a Three-Tier Supply Chain:
## Interim Azure Results from a Self-Contained Simulation Experiment

## Abstract
This paper reports the Azure arm of a self-contained simulation experiment testing whether a large language model can improve supply-chain ordering performance when used as a planner inside a deterministic replenishment policy. The experiment simulates a three-tier serial supply chain over a 25-month automotive demand series. Rather than generating order quantities directly, the model outputs a safety-stock multiplier, and a deterministic rule computes the final order. This design isolates contextual reasoning from arithmetic execution. The Azure arm was run with `o4-mini`, with 20 runs per hybrid condition. Operationally, the system performed reliably: outputs were valid, fallback and clamp rates were zero, and live inference was observed throughout active periods. Substantively, however, all formal hypotheses failed. No hybrid condition matched the within-experiment `exp_smoothing` benchmark, contextual prompting did not yield a practically meaningful improvement over the blind condition, state/history worsened order variance, and multiplier pattern quality remained below target. The Azure results therefore support a clear conclusion: the hybrid planner is technically viable but did not improve supply-chain control on this demand series.

## 1. Introduction
Supply chains are vulnerable to unstable ordering behavior. When firms overreact to short-term demand changes, order variability can increase as one moves upstream, producing excess inventory, avoidable shortages, and the bullwhip effect. Large language models can often recognize seasonal patterns and explain business context well, but they are less dependable when asked to make precise numeric control decisions directly.

This experiment tests a narrower and more structured role for the model. Instead of allowing the LLM to choose monthly order quantities, the model is asked to adjust only one parameter of a deterministic replenishment policy: the safety-stock level. The central research question is whether an LLM can contribute useful directional planning while leaving arithmetic execution to a fixed formula.

The results reported here are from the Azure arm only. They are evaluated entirely within this experiment’s own baselines and controls.

## 2. Key Terminology

### 2.1 Bullwhip Effect
The bullwhip effect is the amplification of order variability as one moves upstream in a supply chain. Retail demand may be moderately stable while supplier and component orders become increasingly volatile.

### 2.2 OVAR
OVAR, or Order Variance Ratio, is the primary bullwhip metric in this study. It is defined as:

\[
OVAR = \frac{Var(order\_placed)}{Var(demand\_received)}
\]

Interpretation:
- `OVAR < 1.0`: orders are less variable than demand, which indicates dampening
- `OVAR = 1.0`: orders track demand variability exactly
- `OVAR > 1.0`: orders are more variable than demand, which indicates bullwhip amplification

In this experiment, lower OVAR is better, but it is never interpreted alone. A low OVAR produced by under-ordering would not count as success if stockouts are high.

### 2.3 Safety Stock
Safety stock is the inventory buffer held above expected demand to absorb uncertainty, demand spikes, or supply delays. In this experiment, the LLM does not choose the final order. It chooses a multiplier that scales the base safety-stock level up or down.

### 2.4 Inventory Position
Inventory position is the effective stock state after accounting for both available inventory and unmet demand. In this experiment:

\[
inventory\_position = on\_hand - backlog
\]

This matters because a firm with high on-hand inventory but also high backlog is not truly well stocked.

### 2.5 Backlog
Backlog is demand that could not be fulfilled in the current period and must be carried forward.

### 2.6 Exponential Smoothing
Exponential smoothing is a deterministic forecasting method that blends current demand with prior forecast to produce a stabilized demand estimate. It serves as the main within-experiment benchmark.

### 2.7 Hybrid Architecture
The hybrid architecture used here separates planning from execution:
- the LLM chooses a `safety_stock_multiplier`
- a deterministic replenishment rule computes the actual order quantity

This allows the experiment to test whether the LLM adds value through contextual reasoning without trusting it with full numeric control.

### 2.8 Hybrid Control
`hybrid_control` is the deterministic architectural control. It uses the same execution formula as the hybrid conditions, but fixes the multiplier at `1.0`. This isolates the contribution of the LLM from the contribution of the formula change itself.

### 2.9 Pattern Score
Pattern score measures whether the **final orders placed** align with expected seasonal demand patterns.

What I am looking for:
- in festive or elevated-demand months, final orders should move upward relative to the tier’s typical level
- in monsoon or dip months, final orders should move downward
- the rationale should mention the relevant seasonal signal

Pattern score therefore tests whether seasonal reasoning is visible in actual operational output.

### 2.10 Multiplier Pattern Score
Multiplier pattern score measures whether the **LLM’s chosen safety-stock multiplier** moves in the expected seasonal direction, independent of the final order quantity.

What I am looking for:
- multiplier above neutral in elevated-demand months
- multiplier below neutral in dip months
- rationale consistent with the seasonal context

This is especially important in a hybrid architecture because the multiplier is the LLM’s true control variable.

### 2.11 Compliance Rate
Compliance rate measures how often the model produces a valid, usable output without fallback or correction.

In this experiment, a compliant response is one that:
- parses successfully
- stays within the expected structure
- remains within the allowed multiplier range
- does not require fallback handling

Compliance is a technical reliability metric. It indicates whether the system worked cleanly, not whether the decisions were good.

## 3. Experimental Design
The simulation represents a three-tier serial supply chain:
- OEM
- Ancillary supplier
- Component supplier

Retail demand enters at the OEM tier. Each tier fulfills downstream demand, updates on-hand inventory and backlog, and places an order to its upstream supplier. Lead time is one month and deterministic. Each tier observes only its immediate downstream order.

The demand data span 25 months. The first 24 months are active ordering periods. The 25th month is a closeout period used for final fulfillment without a new replenishment decision.

## 4. Hybrid Policy Structure
The hybrid policy has two layers.

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

The Azure arm was run on `o4-mini` with 20 runs per hybrid condition.

## 6. Hypotheses
The Azure arm tests four hypotheses.

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

## 7. Validation of the Azure Result Set
Before interpreting performance, the Azure batch must be treated as valid evidence.

The verified Azure result set is:
- `baselines/20260415T133112`
- `H1/20260415T133112`
- `H2/20260415T160633`
- `H3/20260415T182338`

The Azure production runs passed validation cleanly:
- all expected run counts were present
- no negative orders occurred
- all active hybrid rows showed live inference
- rationales were present for all active hybrid rows
- fallback rate was `0.0%`
- mean clamp count was `0.0`
- all reported OVAR values were finite

This means the Azure results are valid experimental findings rather than smoke-test artifacts or dry-run equivalents.

## 8. Results

### 8.1 Deterministic References

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `exp_smoothing` | 0.5446 | 5.0 | 4769.1 |
| `hybrid_control` | 1.7097 | 14.0 | 5141.7 |

### 8.2 Azure Hybrid Conditions

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `H1` Blind | 2.5232 | 8.9 | 7608.5 |
| `H2` Context | 2.4395 | 11.7 | 6487.1 |
| `H3` Stateful | 3.1211 | 10.7 | 7218.3 |

### 8.3 Hybrid Diagnostics

| Condition | Pattern Score | Multiplier Pattern Score | Mean Multiplier | Compliance |
|---|---:|---:|---:|---:|
| `H1` Blind | 0.1958 | 0.3189 | 1.4808 | 1.000 |
| `H2` Context | 0.3390 | 0.3250 | 1.2447 | 1.000 |
| `H3` Stateful | 0.3106 | 0.3038 | 1.3488 | 1.000 |

## 9. Hypothesis Outcomes

### H1: At least one hybrid condition would match or beat the within-experiment `exp_smoothing` benchmark on both chain OVAR and chain stockouts.
**Result: Failed.**

No Azure hybrid condition met this criterion. The benchmark remained clearly stronger than all three hybrid conditions. `exp_smoothing` achieved `OVAR 0.5446` and `stockouts 5.0`, whereas the Azure hybrid conditions ranged from `OVAR 2.4395` to `3.1211` and `stockouts 8.9` to `11.7`.

### H2: Adding seasonal context would improve performance over the blind hybrid condition by a practically meaningful margin (`ΔOVAR ≥ 0.5`).
**Result: Failed.**

`Hybrid-Context` improved only slightly over `Hybrid-Blind` on OVAR (`2.4395` vs `2.5232`), an improvement of `0.0837`, which is far below the threshold for practical significance. Stockouts also worsened from `8.9` to `11.7`. The Azure model therefore showed a small directional improvement in variance, but not enough to support the hypothesis.

### H3: Adding short-term history/state would improve performance over the context condition by a practically meaningful margin (`ΔOVAR ≥ 0.5`).
**Result: Failed.**

`Hybrid-Stateful` did not improve over `Hybrid-Context`. Instead, OVAR worsened substantially from `2.4395` to `3.1211`, a deterioration of `0.6815`. Stockouts improved slightly, but the overall control outcome was clearly weaker on the primary variance criterion.

### H4: The context condition would achieve seasonally meaningful safety-stock planning, defined as `multiplier pattern score ≥ 0.5`.
**Result: Failed.**

`Hybrid-Context` achieved a multiplier pattern score of `0.3250`, below the target threshold. This indicates that even when given calendar context, the model did not adjust safety stock in a sufficiently strong or consistent seasonal direction.

Taken together, all four Azure hypotheses failed. These failures were not caused by technical instability: the model was fully compliant and the pipeline executed cleanly. Instead, the failures reflect the behavioral quality of the planning decisions themselves.

## 10. Discussion
The Azure arm shows a strong separation between technical reliability and supply-chain performance.

On the technical side, the model behaved very well. Outputs were valid, compliance was perfect, fallback and clamping were absent, and live inference occurred throughout the active periods. This means the experiment successfully tested the intended architecture.

On the control side, however, the Azure planner did not improve the system. Every hybrid condition was substantially worse than `exp_smoothing` on OVAR, and none matched the benchmark on stockouts. This matters because the study is not just about whether the model can respond coherently; it is about whether the model can improve replenishment behavior.

The `hybrid_control` result is important for interpretation. Even before introducing the LLM, the hybrid execution formula is weaker than `exp_smoothing` on this demand series. That means the model must choose multipliers that more than compensate for that structural disadvantage. In the Azure arm, it did not.

The mean multiplier values suggest a systematic behavioral tendency toward over-buffering. All three hybrid conditions had average multipliers above `1.0`, and all carried more inventory than either deterministic reference. This is most obvious in `H1`, which pushed mean on-hand inventory to `7608.5`, far above both `exp_smoothing` and `hybrid_control`. The model therefore leaned toward caution, but that caution did not suppress order variance effectively enough to produce competitive performance.

Context improved semantic alignment more than it improved operational control. `H2` had a noticeably higher pattern score than `H1`, which suggests better recognition of seasonal context. But that semantic gain did not translate into a sufficiently strong or sufficiently well-calibrated multiplier strategy. The stateful condition then performed worse still, suggesting that additional recent history may have encouraged reactive behavior rather than stabilizing behavior.

## 11. Conclusion
The Azure results support a clear and defensible conclusion. The hybrid architecture is operationally viable: `o4-mini` can serve as a stable planning component that produces valid safety-stock decisions under production conditions. However, operational viability did not translate into better supply-chain control. On this 25-month demand series, the Azure planner did not improve the system. All hybrid conditions remained materially worse than the deterministic `exp_smoothing` benchmark, contextual prompting produced only a small and practically insignificant improvement over the blind condition, and the addition of state/history increased order variance further.

The most accurate conclusion is therefore not that the hybrid idea failed technically, but that it failed behaviorally in the Azure arm. The architecture functioned as intended, yet the model’s safety-stock decisions did not deliver competitive control performance. This makes the Azure result a valid negative finding. The next analytical step is to compare these findings against the local production arm once those runs are complete, in order to determine whether the limitation is specific to the Azure model or reflects a broader limitation of the hybrid-control architecture itself.
