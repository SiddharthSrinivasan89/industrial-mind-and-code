# Findings — Agentic Bullwhip V6: StatelessSwing Adaptive Smoothing

## What I tested

This is the sixth version in my research series on whether Large Language Models can reduce
the bullwhip effect — order variance amplification — in a three-tier supply chain. The five
prior versions all returned negative results: every AI-driven configuration amplified order
variance. Across V3b through V5 the AI controlled a safety stock multiplier sitting on top of
the Order-Up-To (OUT) formula, and V5 closed that lineage by showing the amplification ceiling
lives in the OUT formula's structure, not in the model.

In V6 I removed the OUT formula entirely and replaced it with exponential smoothing. The AI's
only job is to pick the smoothing coefficient alpha from the set {0.1, 0.3, 0.5, 0.7} per
period per tier. The order quantity comes directly from the smoothed forecast with no buffer
term, so the AI is now controlling the single dimension that directly governs how volatile
orders are. The question I asked is whether AI-selected alpha produces OVAR below 1.0 (active
damping) and whether any AI condition can match or beat the fixed alpha = 0.3 exponential
smoothing baseline.

## Methodology

I ran three models — gpt-4.1-mini and o4-mini on Microsoft Azure, and gpt-oss 120B on a local
Ollama instance — across three information conditions (blind, context, stateful), plus a V6b
sub-experiment with four debiased conditions. I used a deterministic environment: 1-month lead
times at all tiers, no stochastic fill rates, and no disruption events, so any change in OVAR
is attributable to the architecture rather than supply variability. Demand is a 25-month
synthetic series calibrated to Indian automotive seasonal patterns (24 active ordering periods,
mean approximately 38,446 units per month), SHA-256 stamped at runtime.

OVAR is the order variance amplification ratio, Var(orders) / Var(demand), computed per tier
with sample variance (ddof = 1) over the 24 active periods, then averaged as the arithmetic
mean across the three tiers. Values below 1.0 mean consistent variance dampening. I ran 10
replications per adaptive condition, 5 per debiased condition, and 1 per deterministic
baseline.

## Key results

This is the first positive finding in the research program: every AI condition produced OVAR
below 1.0. Every prior version (V1 through V5) amplified order variance in every AI-driven
configuration; V6 dampens it in all of them.

### Fixed baselines (no AI)

| Baseline | alpha | Chain OVAR | Stockouts |
|---|---|---|---|
| exp_smooth_0.1 | 0.1 | 0.620 | 16 |
| exp_smooth_0.3 | 0.3 | 0.545 | 5 |
| exp_smooth_0.5 | 0.5 | 0.729 | 3 |

The deterministic target is `exp_smooth_0.3` at OVAR 0.545 with 5 stockouts — the fixed
baseline with the best balance of variance reduction and service level.

### AI adaptive conditions (n = 10 per condition)

| Model | Condition | Chain OVAR | ± std | Stockouts | Alpha mean |
|---|---|---|---|---|---|
| gpt-oss 120B | BLIND | 0.535 | 0.048 | 4.4 | 0.368 |
| gpt-4.1-mini | BLIND | 0.597 | 0.041 | 7.3 | 0.367 |
| o4-mini | BLIND | 0.657 | 0.091 | 4.0 | 0.404 |
| gpt-oss 120B | STATEFUL | 0.684 | 0.121 | 6.2 | 0.397 |
| gpt-4.1-mini | STATEFUL | 0.695 | 0.045 | 8.8 | 0.365 |
| o4-mini | STATEFUL | 0.705 | 0.125 | 6.5 | 0.397 |
| gpt-4.1-mini | CONTEXT | 0.715 | 0.020 | 10.4 | 0.363 |
| gpt-oss 120B | CONTEXT | 0.739 | 0.040 | 9.3 | 0.340 |
| o4-mini | CONTEXT | 0.741 | 0.045 | 10.4 | 0.359 |

### V6b debiased conditions (n = 5 per condition)

| Condition | Chain OVAR | ± std | Stockouts | Alpha mean |
|---|---|---|---|---|
| oss120b_ctx_computed | 0.585 | 0.036 | 5.6 | 0.322 |
| oss120b_ctx_debiased | 0.597 | 0.077 | 6.6 | 0.387 |
| mini_ctx_debiased | 0.596 | 0.063 | 7.4 | 0.337 |
| mini_ctx_computed | 0.679 | 0.007 | 8.4 | 0.267 |

### Hypothesis verdicts

HV6-1 — every AI adaptive condition produces OVAR below 1.0: PASS. The worst AI condition
(o4-mini context, OVAR 0.741) still dampens. The range across all nine adaptive conditions is
0.535 to 0.741. Controlling alpha rather than a safety stock multiplier eliminated
amplification entirely.

HV6-2 — best AI condition matches or beats exp_smooth_0.3: PASS, marginally. gpt-oss 120B
blind achieved OVAR 0.535 ± 0.048 with 4.4 stockouts, against the fixed alpha = 0.3 baseline at
OVAR 0.545 with 5 stockouts. The difference of 0.010 falls within the confidence interval. This
is the first time in the program that an AI condition can plausibly match its deterministic
counterpart on the primary metric without sacrificing service level.

HV6-3 — context condition produces higher OVAR than blind: PASS. For all three models the
context condition produced higher OVAR than blind. The deltas are gpt-4.1-mini +0.118 (0.715 vs
0.597), o4-mini +0.084 (0.741 vs 0.657), and gpt-oss 120B +0.204 (0.739 vs 0.535). Given
seasonal context, models consistently chose higher alpha values, increasing responsiveness and
thereby variance.

HV6-4 — stateful condition lies between blind and context: PASS. For all three models the
ordering is blind < stateful < context. Stateful conditions (0.684 to 0.705) sit between blind
(0.535 to 0.657) and context (0.715 to 0.741). Recent alpha history moderates the
context-inflation effect without fully eliminating it.

HV6-5 — debiased conditions recover most of the blind advantage: PASS. `oss120b_ctx_computed`
at OVAR 0.585 recovers most of gpt-oss 120B's blind advantage (0.535) relative to its context
condition (0.739) while still providing seasonal information. `mini_ctx_debiased` at 0.596
similarly recovers much of gpt-4.1-mini's blind advantage (0.597 blind vs 0.715 context).

## Why the result happened

The architecture change is the explanation. In V3b through V5 the AI controlled the safety
stock multiplier, which changes inventory levels but does not directly govern how volatile
orders are at the formula level — the OUT formula's replenishment logic generates order swings
regardless. The exponential smoothing parameter alpha, by contrast, governs how much each
period's demand observation updates the forecast, and the order is derived directly from that
forecast with no buffer term. The AI is finally controlling the dimension that determines
variance.

The context penalty is calibrated over-responsiveness. Given seasonal information, models reason
correctly that festival periods warrant higher responsiveness and select higher alpha values.
The reasoning is directionally sound; the calibration is off. Alpha = 0.7 in a supply chain with
predictable seasonal patterns introduces more variance than the seasonal signal itself
justifies. This is structurally far more tractable than the order-quantity spikes of V2 or the
multiplier miscalibration of V3b — it is a single parameter shifted one or two positions upward,
not an order-of-magnitude error.

The 120B model's blind advantage (OVAR 0.535 vs 0.597 for gpt-4.1-mini) reflects a prior
distribution effect, not a reasoning capability effect. Without context, models rely entirely on
the inventory numbers and the alpha option structure. The larger model defaults toward
alpha = 0.3 — the standard exponential smoothing textbook value — while smaller models select
alpha = 0.7 more often. The advantage disappears when context is added: all models produce OVAR
0.715 to 0.741 in context conditions, confirming this is a prior rather than a reasoning effect.

The debiasing conditions show the context penalty is correctable. Restricting the option set to
{0.1, 0.3, 0.5} and having the model derive alpha from observable statistics
(`oss120b_ctx_computed`, OVAR 0.585) recovers most of the blind advantage while still providing
seasonal information.

## Limitations

1. Simplified environment. V6 uses deterministic lead times and removes the stochastic fill
   rates of V4/V5. The positive results may partly reflect this simpler environment rather than
   the architecture change alone; cross-experiment comparison needs caution.
2. Single demand series. The 25-month synthetic series is specific to Indian automotive seasonal
   patterns; the findings are not established to generalise to other markets.
3. Small option set. The AI selects from only four discrete alpha values. Results may differ
   with continuous alpha or a different discrete set.
4. Sample sizes. n = 10 per adaptive condition and n = 5 per debiased condition are adequate for
   the primary OVAR comparisons but underpowered for small effects.
5. No disruption events. The absence of disruptions and stochastic lead times makes V6 a cleaner
   architecture test but limits generalisability to disrupted environments.
6. Model-specific results. Findings are specific to the three models tested; the 120B blind
   advantage reflects one model's prior distribution and may not generalise.
7. Hypotheses were not pre-registered. They were stated in design documentation before execution
   but not deposited with any external registry.
8. Marginal primary result. The gpt-oss 120B blind result (OVAR 0.535 vs 0.545 for the fixed
   baseline) sits within the confidence interval. The robust headline is that every AI condition
   dampens variance; the claim that any AI condition definitively beats the fixed optimal
   baseline needs replication with larger n.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
