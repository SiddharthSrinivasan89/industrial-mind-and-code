# Findings — Agentic Bullwhip Version 1 (Direct Ordering)

## What I tested

I wanted to know whether giving an LLM ordering agent business context — the company identity, the product, the market, and the calendar month — would calm down the way orders get noisier as they travel up a supply chain. This noise amplification is the classic bullwhip effect: a small wobble in customer demand turns into a much bigger wobble in the orders each tier places on its supplier.

I built a three-tier serial supply chain (OEM -> Ancillary lighting assembler -> LED component maker) with one-month lead times and ran each tier as a stateless LLM agent, meaning the agent has no memory between months. I crossed two factors in a 2x2 design: context treatment (blind numeric state only, versus the same state plus business context) and model capability tier (a lightweight model, `gpt-4.1-mini`, versus a reasoning model, `o1`). Every configuration saw the identical fixed 13-month demand series for the fictional Tatva Motors "Vecta" car (606,771 units total, December 2024 to December 2025), with 43,000 units of starting inventory at every tier. I ran 5 replications per configuration, 20 runs in total, which is 720 LLM calls.

This is an exploratory study. With only 5 runs per configuration and non-deterministic LLM outputs, the results show direction, not statistically settled point estimates. I did not pre-register any hypotheses.

## How I measured it

The primary metric is OVAR, the Order Variance Amplification Ratio: the variance of the orders a tier places divided by the variance of the demand it receives, computed over the 12 active ordering periods. An OVAR of 1.0 means orders are exactly as noisy as demand; above 1.0 is bullwhip amplification; below 1.0 is dampening. I also tracked stockouts, excess inventory, total units ordered, peak overshoot, and a seasonal pattern-detection score. As a stability check I report the coefficient of variation (CV) of OVAR across runs; a high CV means the model behaves erratically from run to run.

## Key results (n = 5 per configuration)

Every configuration amplified demand variability — every OVAR was above 1.0 at every tier. The question was never whether the bullwhip appeared, but how the cascade differed by treatment.

The context effect ran in opposite directions depending on the model. Ranked by chain-average OVAR:

| Configuration | Model | Treatment | Chain avg OVAR | vs blind_lightweight |
|---|---|---|---|---|
| context_lightweight | gpt-4.1-mini | Context | 2.929 | -7.2% |
| blind_lightweight | gpt-4.1-mini | Blind | 3.157 | baseline |
| blind_reasoning | o1 | Blind | 3.835 | +21.5% |
| context_reasoning | o1 | Context | 4.412 | +39.7% |

For the lightweight model, context lowered chain OVAR by 0.228. For the reasoning model, context raised it by 0.577. The most capable and most expensive configuration — context with `o1` — produced the highest chain-level amplification of all four.

OVAR by tier (mean +/- std, with CV%):

| Configuration | OEM OVAR | CV% | Ancillary OVAR | CV% | Component OVAR | CV% |
|---|---|---|---|---|---|---|
| blind_lightweight | 2.267 +/- 0.009 | 0.41 | 2.938 +/- 0.044 | 1.50 | 4.266 +/- 0.078 | 1.82 |
| context_lightweight | 2.237 +/- 0.006 | 0.29 | 3.138 +/- 0.080 | 2.55 | 3.412 +/- 0.347 | 10.18 |
| blind_reasoning | 4.200 +/- 2.400 | 57.15 | 3.656 +/- 1.350 | 36.94 | 3.649 +/- 0.608 | 16.66 |
| context_reasoning | 6.349 +/- 1.452 | 22.86 | 4.191 +/- 1.373 | 32.76 | 2.698 +/- 0.677 | 25.10 |

A parse error in run 5 of context_lightweight inflates the component mean by about +0.129; the clean estimate is 3.283 +/- 0.220.

The sharpest divergence sat at the OEM tier — the only tier that sees real consumer demand. Context barely moved the lightweight model there (delta -0.030). For `o1` at the same tier, context pushed OVAR up by 2.149. The reasoning model, given a month name and a market identity, appears to build forward-looking ordering strategies that inject variance at the head of the chain rather than smooth it. The clearest sign of this is that context_reasoning inverted the cascade: OEM 6.349, Ancillary 4.191, Component 2.698. Standard bullwhip theory predicts variability rising as you move upstream; context_reasoning flipped that entirely, while the three other configurations followed the expected upstream-rising pattern.

The service-versus-cost trade-off in that configuration was extreme. Stockouts and excess inventory, as chain totals across 5 runs:

| Configuration | Stockouts | Excess inventory (units) |
|---|---|---|
| blind_lightweight | 21.4 | 109,360 |
| context_lightweight | 19.6 | 151,246 |
| blind_reasoning | 20.0 | 330,649 |
| context_reasoning | 12.8 | 654,728 |

context_reasoning had the fewest stockouts but the highest excess inventory — roughly six times that of blind_lightweight. It bought availability by sitting on a mountain of stock.

The reasoning model was also far less consistent. Its OVAR CV ran 22-57% across configurations, against under 2% for the lightweight model. A model that returns reasonable orders on some runs and extreme orders on others, from identical inputs, cannot be validated before deployment. Predictable behaviour, even when wrong, is easier to work with than intermittent extremes.

## What the hypotheses showed

I framed four directional hypotheses. Context reducing OVAR at every tier was rejected — it only helped the lightweight model, and only downstream. The idea that blind reasoning would perform similarly to blind lightweight was rejected: the reasoning model was both higher and much noisier. The expectation that context with the reasoning model would achieve the lowest chain OVAR was rejected — it produced the highest. The seasonal-responsiveness hypothesis held only partially: the lightweight model scored 83% on seasonal elevation at event periods, but the pattern reversed for the reasoning model.

A separate metric note: the original keyword-only pattern score returned 0.0 across all configurations, because the models reason arithmetically and do not write out festival names. I redesigned the score for later runs into a composite of a keyword sub-score and an order-elevation sub-score; results scored under the two definitions are not comparable.

## Local cross-check (qwen3.5 via Ollama, n = 1)

As an informal cross-check I ran the two lightweight configurations against `qwen3.5:latest` (9.7B, Q4_K_M) locally through Ollama, one run each. This is a single run per configuration and is directional only. It pointed the same way as the Azure lightweight results at the OEM tier: blind OEM OVAR 4.09 versus context OEM OVAR 2.21, with stockout periods dropping from 13/13 (blind) to 7/13 (context). In the blind condition this model showed an inverse-cascade pattern (OEM 4.09 -> ancillary 2.25 -> component 1.26), unlike the Azure lightweight runs. Like `gpt-4.1-mini`, it used no festival vocabulary even with calendar context (keyword score 0.0). The details are in `results/qwen3.5_local_analysis.md`.

## Limitations

The sample is small: 5 runs per configuration, and the `o1` configurations carry CV values of 22-57%, so their means are directional rather than settled. There is a single demand series — one SKU, one supply chain structure, one festive cycle across one calendar year — so the results do not generalise beyond this design. Version 1 imposed an order floor (0.2x demand) and ceiling (5x demand) on all agents; these guardrails may have masked more extreme natural behaviour, and I removed them in Version 2. Only a stateless architecture was tested; whether giving the agents memory between periods changes the picture is outside what this study can say. The scenario is entirely fictional and synthetic.

I did not include a deterministic ordering baseline in this version. The natural reference points for follow-up work are an Order-Up-To policy (order back to a fixed target stock) and exponential smoothing (forecast demand, then order to cover it). Comparing the LLM agents against these is the planned next step; Version 2 was designed to remove the guardrails and push toward that comparison.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
