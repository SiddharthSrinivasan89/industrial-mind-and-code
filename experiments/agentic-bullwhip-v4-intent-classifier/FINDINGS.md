# Findings — V4 Intent Classifier (Intermediate Variant)

## What I tested

I tested whether replacing the continuous float output of the prior hybrid architecture (V3b) with a discrete five-label intent classification improves supply chain ordering performance and output reliability. In each period and each tier, the language model chooses exactly one of `STRONG_INCREASE`, `MODERATE_INCREASE`, `NEUTRAL`, `MODERATE_DECREASE`, `STRONG_DECREASE`. A fixed deterministic lookup table converts that label to a safety stock multiplier, and an Order-Up-To (OUT) style formula then computes the order quantity. The model never produces a number.

The lookup table used at runtime (recorded in each run's `provenance.json`) was:

| Intent class | Multiplier |
|---|---|
| `STRONG_INCREASE` | 2.5 |
| `MODERATE_INCREASE` | 1.5 |
| `NEUTRAL` | 1.0 |
| `MODERATE_DECREASE` | 0.75 |
| `STRONG_DECREASE` | 0.5 |

This is the intermediate variant of V4: it established the architecture, lookup table, prompts, ground-truth intent schedule, and metric definitions on a 25-month, no-disruption demand series, which were then carried forward into the primary V4 WorldEvents experiment. I ran it at exploratory scale, so the numbers below should be read as directional rather than as the planned production-scale result.

## Methodology

The setup is a three-tier serial supply chain (OEM to Ancillary to Component) calibrated to an Indian automotive parts context, with a one-month deterministic lead time and no cross-tier information sharing. The demand series is `tatva_monthly_dispatches_25m.csv` (SHA-256 `c9b26afdbfd551f4f88f72eb119292a3ed0e9c2619c787a26b29d63250539c4e`), 25 months covering January 2025 through January 2027 with 24 active ordering periods, a mean of 38,446 units per month, and two annual cycles of Indian-calendar seasonal variation. The base safety stock recorded in provenance is 5,061 units and the forecast smoothing weight is 0.30.

I compared two deterministic baselines against three intent conditions, each run on two backends:

- `exp_smoothing` — exponential-smoothing heuristic baseline (1 run)
- `hybrid_control` — OUT formula with the multiplier fixed at 1.0 (1 run)
- IC-Blind (H1_IC) — intent classification from state variables only
- IC-Context (H2_IC) — intent classification with calendar month and tier persona added
- IC-Stateful (H3_IC) — context plus the last three periods of intent and outcome history

The LLM conditions ran on Azure (gpt-4.1-mini) at 10 runs each and locally (nemotron-3-super:120b, and a lightweight local model labelled `_phi`) at 5 runs each. All result bundles cited here are live runs (`dry_run: false` in provenance), distinct from the dry-run pipeline checks also present under `results/`.

The primary operational metric is the Order Variance Amplification Ratio (OVAR) — order variance divided by demand variance, averaged across the three tiers — reported alongside stockout counts. The classification-specific metrics are intent compliance (share of periods returning a valid, non-fallback label), intent accuracy against the deviation-based ground-truth schedule (both direction-only and full-label-match), and intent entropy over the five classes.

## Key results

### Deterministic baselines

Exponential smoothing was the strongest policy on order variance, with chain OVAR 0.545 and 5 stockouts. The fixed-multiplier hybrid control reached chain OVAR 1.710 with 14 stockouts. Every intent condition landed above both baselines on OVAR.

### Intent conditions (live runs)

| Condition | Backend | n | Chain OVAR | Stockouts | Compliance | Direction accuracy | Full-match accuracy | Entropy |
|---|---|---|---|---|---|---|---|---|
| IC-Blind | Azure (gpt-4.1-mini) | 10 | 3.803 +/- 0.131 | 11.9 | 1.0 | 0.221 | 0.214 | 0.931 |
| IC-Blind | local (nemotron-3-super:120b) | 5 | 2.328 +/- 0.133 | 3.2 | 1.0 | 0.500 | 0.257 | 0.568 |
| IC-Blind | local (`_phi`) | 5 | 2.960 +/- 0.508 | 7.0 | 1.0 | 0.443 | 0.271 | 0.665 |
| IC-Context | Azure (gpt-4.1-mini) | 10 | 3.236 +/- 0.046 | 15.4 | 1.0 | 0.786 | 0.500 | 2.117 |
| IC-Context | local (nemotron-3-super:120b) | 5 | 3.745 +/- 0.137 | 16.4 | 1.0 | 0.786 | 0.500 | 2.117 |
| IC-Context | local (`_phi`) | 5 | 3.218 +/- 0.195 | 15.0 | 1.0 | 0.786 | 0.500 | 2.180 |
| IC-Stateful | Azure (gpt-4.1-mini) | 10 | 3.755 +/- 0.062 | 12.0 | 1.0 | 0.786 | 0.500 | 2.122 |
| IC-Stateful | local (nemotron-3-super:120b) | 5 | 4.017 +/- 0.065 | 15.0 | 1.0 | 0.786 | 0.500 | 2.197 |
| IC-Stateful | local (`_phi`) | 5 | 3.420 +/- 0.084 | 13.4 | 1.0 | 0.800 | 0.514 | 2.272 |

Accuracy is evaluated over 14 non-neutral event periods. The +/- values are standard deviations across runs.

### What the numbers say

Compliance was 1.0 in every intent condition on both backends. The discrete five-label interface eliminated the parse and calibration failures that motivated the design — the model never had to invent a number, and never produced an invalid one.

Adding calendar context clearly improved classification. Directional accuracy rose from 0.221 for blind gpt-4.1-mini to 0.786 once month and persona context were supplied, and full-label-match accuracy rose from 0.214 to 0.500. Intent entropy rose in step, from 0.931 (blind) to 2.117 (context) for gpt-4.1-mini against a maximum of log2(5) of about 2.32, confirming the context conditions spread their choices across the five classes rather than collapsing onto one label. The blind conditions clustered low.

Better classification did not translate into lower OVAR. Despite directional accuracy more than tripling from blind to context for gpt-4.1-mini, chain OVAR stayed in the 3.2 to 4.0 band across all context and stateful conditions, well above both deterministic baselines and far above the 0.5-OVAR MPRD threshold. Adding three periods of intent and outcome history (IC-Stateful) did not improve directional accuracy over IC-Context — both sat at 0.786 for the larger models — and did not lower OVAR. This is the early, in-variant signal of what the V4 WorldEvents report names the Equaliser Effect: the discrete lookup table imposes a structural ceiling and floor on OVAR, so a wide range of classification quality maps onto a narrow band of ordering behaviour. The label-to-multiplier mapping removes the model's capacity for the fine-grained adjustment that would be needed to approach the smoothing baseline.

## Limitations

These results are exploratory: 5 to 10 runs per LLM condition against single-run deterministic baselines, below the design target of 20 runs. The 0.5-OVAR MPRD threshold was defined for the n=20 design, so smaller effects are underpowered here. The findings rest on a single synthetic demand series specific to Indian automotive seasonality and a single simplified three-tier serial topology with unit lead time, and they cover gpt-4.1-mini and the two local models only; they are not established to generalise to other markets, topologies, or models. The 25-month series tests seasonal variation but no demand shocks, supply disruptions, or structural mean shifts. The intent-to-multiplier lookup values are domain-logic-driven and are not guaranteed to be globally optimal for the OUT formula. The primary, production-scale V4 evidence and hypothesis verdicts live in the V4 WorldEvents experiment; this variant carries the architecture and the exploratory-scale confirmation of the Equaliser Effect.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
