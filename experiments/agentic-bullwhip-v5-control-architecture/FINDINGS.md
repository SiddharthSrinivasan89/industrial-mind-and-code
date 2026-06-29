# Agentic Bullwhip Effect V5 — Findings

## What I Tested

This is Version 5 of a five-experiment series on whether Large Language Models (LLMs) can reduce order variance amplification in a three-tier supply chain. V5 tests no LLM at all. Version 4 had shown an "Equaliser Effect": every LLM I tried, regardless of size or reasoning ability, clustered at an Order Variance Amplification Ratio (OVAR) of roughly 1.73 to 1.78. That left an open question — was the ceiling caused by the models not being good enough, or by the architecture they were plugged into? In V5 I answered this by removing the LLM and replacing its labels with two deterministic sources: perfect ground-truth "oracle" labels, and a hand-written rule-based "causal" classifier. If even perfect labels could not beat the simple formula, the ceiling would be architectural rather than a model-quality problem.

I ran 14 conditions across six ablation groups (oracle label quality, multiplier map range, NEUTRAL-class redefinition, order dampening, forecast oracle, and causal rule-based classification), n=20 runs each. The two baselines I compare against throughout are the Order-Up-To (OUT) formula (`order_up_to`) and exponential smoothing (`exp_smoothing`).

## Methodology

The supply chain, demand series, world events (a pandemic, a geopolitical conflict, and a port strike), and stochastic lead times and fill rates are identical to V4, so OVAR is directly comparable across experiments. The execution architecture keeps V4's three layers — label source, multiplier lookup, OUT formula — but swaps the LLM label source for either a perfect oracle schedule or a rule-based causal classifier. OVAR is Var(orders) / Var(demand) computed per tier with sample variance (ddof=1) over active ordering periods, then averaged across the three tiers. The secondary metric is the chain-level stockout count over 36 periods, averaged over 20 runs. The full design, parameters, and condition list are in DESIGN.md.

The Phase 1 gate criterion was set in advance: for Phase 2 LLM experiments to be justified, some V5 condition had to beat `order_up_to` (about 1.75) by more than 0.10, or come within 0.30 of `exp_smoothing` (about 1.19).

## Key Results

The best result across all 14 conditions is `neutral_smoothed_forecast` at OVAR 1.7334. It beats the OUT baseline `order_up_to` (1.7527) by only 0.019, and it stays 0.540 above the exponential smoothing baseline (1.1931). The most direct test of the model-quality hypothesis, `oracle_v4map` (perfect labels on the V4 map), lands at OVAR 1.7759 — worse than the OUT formula with no classification layer at all (1.7527). A hypothetical model that classified every period perfectly would not even match the plain formula baseline.

Complete results (lower OVAR is better; stockouts are the mean chain-level count over 36 periods across 20 runs):

| Condition | n | Chain OVAR | Chain Stockouts |
|---|---|---|---|
| naive_passthrough | 20 | 0.9961 | 95.4 |
| exp_smoothing | 20 | 1.1931 | 89.5 |
| neutral_smoothed_forecast | 20 | 1.7334 | 89.5 |
| causal_context | 20 | 1.7493 | 87.2 |
| order_up_to | 20 | 1.7527 | 87.3 |
| dampened_beta50 | 20 | 1.7654 | 93.5 |
| causal_unstructured | 20 | 1.7686 | 87.0 |
| oracle_v4map | 20 | 1.7759 | 87.0 |
| oracle_moderate | 20 | 1.7979 | 87.2 |
| dampened_beta25 | 20 | 1.8216 | 96.3 |
| oracle_asymmetric | 20 | 1.8314 | 87.0 |
| oracle_aggressive | 20 | 1.8593 | 87.0 |
| dampened_beta75 | 20 | 1.9628 | 89.0 |
| neutral_dampened_out | 20 | 2.0001 | 89.7 |
| forecast_oracle_events | 20 | 2.0094 | 85.3 |
| neutral_repeat_last | 20 | 2.2231 | 88.2 |
| neutral_floor_only | 20 | 2.3129 | 89.2 |

(There is one figure to note for transparency: the README and the report give slightly different OVAR values for `dampened_beta25` and `dampened_beta75`. The report's Section 7 complete table lists `dampened_beta25` at 1.9628 and `dampened_beta75` at 1.8216, while the report's own summary block and the README list `dampened_beta50` at 1.7654, `dampened_beta75` at 1.9628, and `dampened_beta25` at 1.8216. I have used the README/summary ordering above. The discrepancy is confined to the two dampening variants and does not affect any conclusion.)

The gap structure is the central result:

```
exp_smoothing              1.1931  (benchmark)
                           ------  gap: 0.540  ------
neutral_smoothed_forecast  1.7334  (best Phase 1 result)
order_up_to                1.7527  (V4 architecture floor)
oracle_v4map               1.7759  (perfect labels, still above order_up_to)
```

### Hypothesis verdicts

- HV5-1 (any condition beats order_up_to by >= 0.10): FAIL. The best margin was 0.019 (`neutral_smoothed_forecast`).
- HV5-2 (perfect oracle labels reduce OVAR below order_up_to): FAIL. `oracle_v4map` at 1.7759 is worse than `order_up_to` at 1.7527.
- HV5-3 (any multiplier map variant beats the V4 conservative map): FAIL. All three wider maps (moderate 1.7979, asymmetric 1.8314, aggressive 1.8593) are worse than the V4 map (1.7759). Larger safety-stock swings compound variance further upstream regardless of label accuracy.
- HV5-4 (any NEUTRAL redefinition produces meaningful OVAR reduction): PARTIAL. `neutral_smoothed_forecast` (NEUTRAL mapped to a forecast-only order with no safety stock) gains 0.019 over `order_up_to`, the only V5 condition that mechanically approaches exponential smoothing during NEUTRAL periods. All other NEUTRAL redefinitions were substantially worse (2.0 to 2.3). The gain is real but well short of the 0.10 threshold.
- HV5-5 (causal rule-based classifier outperforms oracle): FAIL (within noise). `causal_context` (1.7493) is marginally better than `oracle_v4map` (1.7759), but both sit in the same noise band and both are worse than `order_up_to`. A hand-written rule matches perfect machine-generated labels, confirming that calendar and event labels carry essentially no predictive value for variance reduction in this architecture.

Gate verdict: FAIL. Phase 2 LLM experiments are not justified for this architecture.

## What This Means

The oracle experiment resolves the ambiguity V4 left open. Perfect classifications produce OVAR 1.7759 — worse than the OUT formula with no classification layer (1.7527). That rules out the model-quality hypothesis. The 0.540 gap between the intent-classifier architecture and exponential smoothing comes from the structure of the OUT formula, not from label quality. The intent classifier always applies safety stock (multiplier times base safety stock), which adds an inventory-based signal on top of the forecast; even at multiplier 1.0 (NEUTRAL) the base safety stock generates order volatility that compounds upstream. Exponential smoothing uses only an EMA forecast (alpha = 0.30) with no safety-stock buffer, which attenuates variance at every tier. The two architectures solve different problems — exponential smoothing optimises variance stability, the OUT formula optimises service level through buffering — so they are not equivalent alternatives. This is not a shortcoming of the language models; they comprehend the supply-chain context well (V3b and V4 showed that). The limit is the formula they feed, not the intelligence supplying the labels.

The `neutral_smoothed_forecast` result confirms this by exception: removing the safety-stock component during the majority NEUTRAL periods is exactly what produces the only marginal gain, because it makes those periods behave like exponential smoothing. Extending that logic fully — replacing the OUT formula with an EMA-based policy — became the candidate for the next experiment line (implemented as V6 StatelessSwing). On that basis I closed the intent-classification lineage that ran from V1 through V5.

## Limitations

1. The conclusions are specific to this architecture: discrete intent classification, a five-label lookup table, and an OUT-style ordering formula. They do not generalise to all AI-augmented supply chain designs.
2. The 0.540 gap figure is specific to this stochastic simulation environment (the same lead-time and fill-rate parameterisation as V4).
3. A single supply chain topology was used — a three-tier serial cascade, simplified relative to real chains.
4. A single demand profile was used — the 36-month Indian automotive seasonal series with three injected disruption types.
5. n=20 per condition is adequate for detecting effects at the defined threshold; smaller effects may be underpowered.
6. The hypotheses were stated in the design document before execution but were not pre-registered with any external registry.
7. Closing the V1 to V5 line at Phase 1 reflects the absence of any finding that would justify continued investment in this architectural direction. It is not a claim that no AI-augmented supply chain architecture can outperform exponential smoothing; it is a claim that this specific five-label intent classifier with the OUT formula cannot.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
