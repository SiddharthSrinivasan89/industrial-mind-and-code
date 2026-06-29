# Design — Agentic Bullwhip V6: StatelessSwing Adaptive Smoothing

## Motivation

This is Version 6 in a research series testing whether Large Language Models can reduce
order variance amplification (the bullwhip effect) in a multi-tier supply chain. The five
prior versions established one thing with certainty: the Order-Up-To (OUT) formula generates
amplification by construction, and no agent intervention at the safety-stock or multiplier
level suppresses it. V5 closed that lineage and identified a single remaining candidate
architectural change — give the AI control of the exponential smoothing parameter alpha
inside the forecast itself, rather than a safety stock multiplier sitting on top of the OUT
formula.

V6 tests that change. The OUT formula is removed entirely and replaced with exponential
smoothing. The AI's only decision per period per tier is to select the smoothing coefficient
alpha. Low alpha produces a sluggish, smooth forecast; high alpha produces a reactive, noisy
forecast. Order quantity is derived directly from the smoothed forecast with no buffer term,
so the AI now controls the one dimension of the formula that directly determines order
variance.

## Central question

Does AI-selected alpha within exponential smoothing produce OVAR below 1.0 — active demand
damping — and allow any AI condition to match or beat the fixed alpha = 0.3 exponential
smoothing baseline that the prior versions could not?

## Supply chain structure

A three-tier serial supply chain calibrated to an Indian automotive parts context. V6
returns to the deterministic lead-time environment of V1 and V2 to isolate the architecture
change from the stochastic supply-side effects tested in V4 and V5.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- Simulation horizon: 25 months (January 2025 through January 2027); 24 active ordering
  periods plus one close-out period.
- Lead time: 1 month deterministic at all tiers.
- No stochastic lead times or fill rates, and no world/disruption events — pure Indian
  automotive seasonal variation (monsoon slump, Diwali peak, financial-year-end surge).
- Demand series: synthetic, calibrated to Indian automotive seasonal patterns
  (`tatva_monthly_dispatches_25m.csv`, SHA-256 stamped at runtime). Mean approximately
  38,446 units per month across the 24 active periods.

## Execution formula (per period, per tier)

```
Step 1 — AI selects alpha in {0.1, 0.3, 0.5, 0.7}

Step 2 — Exponential smoothing executes with that alpha
  F_t   = alpha * D_t + (1 - alpha) * F_{t-1}
  order = max(0, round(F_t) + backlog_t)

No safety stock term. No OUT formula. No lookup table.
```

The AI's output is a discrete 4-way choice — no float calibration, no magnitude invention.
The agent is stateless between periods in the blind and context conditions (no memory, no
compounding bias).

## Models

| Model | Type | Backend |
|---|---|---|
| gpt-4.1-mini | Lightweight fast model | Microsoft Azure |
| o4-mini | Reasoning model | Microsoft Azure |
| gpt-oss 120B | Open-source 120B | Local Ollama |

## Information conditions (adaptive group)

| Condition | Context provided to the LLM |
|---|---|
| Blind | Current inventory state variables and the alpha option set; no calendar, no seasonal information |
| Context | Calendar month, tier persona with Indian automotive seasonal knowledge, and the alpha option set |
| Stateful | Context plus recent history of alpha selections, demand received, and order placed (last 3 periods) |

## V6b debiased conditions (sub-experiment)

V6b tests two strategies to correct a context-induced alpha-inflation bias observed in the
adaptive group.

| Condition | Model | Debiasing strategy |
|---|---|---|
| mini_ctx_debiased | gpt-4.1-mini | Explicit instruction to correct alpha-inflation; full option set {0.1, 0.3, 0.5, 0.7} |
| mini_ctx_computed | gpt-4.1-mini | Restricted option set {0.1, 0.3, 0.5}; model derives alpha from observable statistics |
| oss120b_ctx_debiased | gpt-oss 120B | Explicit instruction to correct alpha-inflation; full option set |
| oss120b_ctx_computed | gpt-oss 120B | Restricted option set {0.1, 0.3, 0.5}; model derives alpha from statistics |

## Replications

- 10 runs per adaptive condition.
- 5 runs per debiased condition.
- 1 run per fixed baseline (deterministic, no AI).

## Fixed baselines (no AI, reference only)

| Baseline | alpha | Chain OVAR | Stockouts |
|---|---|---|---|
| exp_smooth_0.1 | 0.1 | 0.620 | 16 |
| exp_smooth_0.3 | 0.3 | 0.545 | 5 |
| exp_smooth_0.5 | 0.5 | 0.729 | 3 |

The target for AI conditions is `exp_smooth_0.3` at OVAR 0.545 — the fixed baseline with the
best balance of variance reduction and stockout count.

## Primary metric

OVAR (Order Variance Amplification Ratio):

```
OVAR = Var(orders) / Var(demand)
```

computed per tier using sample variance (ddof = 1) over the 24 active ordering periods, then
averaged as the arithmetic mean across the 3 tiers. Values below 1.0 indicate consistent
variance dampening; values above 1.0 indicate amplification. Secondary metrics: stockout
count (total chain-level count across 25 periods, mean over replications) and mean alpha
selected per condition.

## Hypotheses

Hypotheses were stated in design documentation prior to execution. They were not deposited
with any external registry.

| Label | Hypothesis | Threshold |
|---|---|---|
| HV6-1 | Every AI adaptive condition produces OVAR below 1.0 | OVAR < 1.0 for all conditions |
| HV6-2 | The best AI condition matches or beats exp_smooth_0.3 | Best AI OVAR <= 0.545 |
| HV6-3 | Context condition produces higher OVAR than blind (context penalty) | Context OVAR > Blind OVAR |
| HV6-4 | Stateful condition lies between blind and context | Blind OVAR < Stateful OVAR < Context OVAR |
| HV6-5 | Debiased conditions recover most of the blind advantage vs context | Debiased OVAR closer to blind than context |

## What success and failure mean

Success: any AI condition achieves OVAR below 1.0, confirming that adaptive alpha-selection
can actively damp demand variance. If any condition also beats the fixed alpha = 0.3 baseline
(OVAR below 0.545) without sacrificing service level, the AI adds value beyond a tuned static
parameter.

Failure: if all AI conditions cluster at OVAR at or above 1.0, the alpha-selection
architecture is ruled out as a solution. Combined with V5's closure of the OUT lineage, that
would shift the program's conclusion from "wrong lever" to "no lever works at this
granularity".
