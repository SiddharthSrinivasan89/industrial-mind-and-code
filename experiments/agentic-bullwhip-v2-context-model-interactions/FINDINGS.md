# Findings — Agentic Bullwhip V2: LLM Ordering Agents vs Deterministic Heuristics

## What I tested

I asked one question: can an LLM ordering agent match a simple deterministic rule at keeping order swings small while still keeping the shelves stocked, in a three-tier supply chain?

The chain runs OEM (Tatva Motors) to Ancillary (lighting manufacturer) to Component (LED supplier), with a one-month fixed lead time at every tier. Demand is a synthetic 25-month series (24 active ordering months) shaped on real Indian automotive seasonality — festive-season peaks, monsoon dips, Diwali surges. The series and the opening stock were the same on every run.

I ran a 2x2 design — model tier (lightweight vs reasoning) crossed with prompt treatment (blind vs context) — across two backends (frontier on Azure, local on Ollama), giving 8 model-condition cells, plus three deterministic baselines:

- Lightweight: gpt-4.1-mini (Azure), phi4:14b (local)
- Reasoning: o4-mini (Azure), gpt-oss:120b (local)
- Heuristics: exponential smoothing (alpha = 0.30), naive passthrough, Order-Up-To

The agents are stateless — each ordering decision is a fresh single-turn call with no memory of prior orders. "Blind" prompts give numbers only; "context" prompts add a tier persona (company, product, role) and the current calendar month name. The same four numeric state variables go to every agent and to the heuristics.

## How I measured it

Two primary metrics, always reported together:

- **OVAR** = Var(orders placed) / Var(demand received), computed per tier and averaged across the chain. Below 1.0 means the agent is smoothing; above 1.0 means it is amplifying (bullwhip). I treated a chain-level difference as practically meaningful only if it was at least 0.5 OVAR units (my MPRD threshold).
- **Stockout count** = number of tier-periods where on-hand stock could not cover demand plus backlog, out of 75 possible per run (25 periods x 3 tiers).

I never count a lower OVAR bought with more stockouts (or vice versa) as an improvement.

A secondary **pattern score** (0.0 to 1.0) averages a keyword sub-score (did the rationale name the relevant seasonal event?) and an elevation sub-score (did the order quantity move in the right direction at that event?).

Execution: 20 runs per LLM condition, 1 run per deterministic heuristic, 11,520 total LLM calls. Exponential backoff (10 retries, 60s cap) with per-condition checkpointing. The observed retry rate was 0.0% across all 11,520 calls — no run needed replacement.

## Key results

### The deterministic baselines

| Heuristic | Chain OVAR | Stockouts (of 75) |
|---|---|---|
| Exponential smoothing | 0.54 | 5 |
| Naive passthrough | 1.00 | 3 |
| Order-Up-To | 1.71 | 14 |

Exponential smoothing does not merely hold OVAR at 1.0 — it actively dampens variance to 0.54, below demand variance. This is the bar to clear.

### Every LLM configuration lost on both metrics at once

| Condition | Backend | Chain OVAR (mean +/- std) | Stockouts (mean +/- std) |
|---|---|---|---|
| L-Blind | Azure | 4.70 +/- 0.14 | 40.5 +/- 0.83 |
| L-Context | Azure | 4.47 +/- 0.07 | 39.0 +/- 0.83 |
| L-Blind | Local | 4.33 +/- 0.00 | 41.0 +/- 0.00 |
| L-Context | Local | 6.35 +/- 2.53 | 37.2 +/- 3.11 |
| R-Blind | Azure | 4.72 +/- 1.12 | 42.9 +/- 3.85 |
| R-Context | Azure | 4.52 +/- 0.08 | 40.1 +/- 0.85 |
| R-Blind | Local | 4.52 +/- 0.00 | 40.0 +/- 0.00 |
| R-Context | Local | 4.52 +/- 0.05 | 39.6 +/- 0.76 |

L = lightweight (gpt-4.1-mini / phi4:14b). R = reasoning (o4-mini / gpt-oss:120b).

The best LLM configuration (local L-Blind, OVAR 4.33, 41 stockouts) is about 8x worse than exponential smoothing on OVAR (0.54) and about 8x worse on stockouts (5) at the same time. No OVAR/stockout trade-off rescues the LLMs — they are strictly worse on both dimensions. Across all LLM cells, OVAR ranged 4.33 to 6.35 (8-12x the best heuristic, 4-6x naive passthrough) and stockouts ranged 37 to 43 (7-8x the best heuristic).

By tier, the Ancillary (middle) tier amplifies most — consistent with classic bullwhip dynamics. Exponential smoothing held tier OVAR at OEM 0.41, Ancillary 0.65, Component 0.58.

### Context did not reliably help and sometimes hurt

For frontier lightweight (gpt-4.1-mini), context nudged chain OVAR down 4.70 to 4.47 (delta 0.23) — below my 0.5 threshold, so not practically meaningful. For local lightweight (phi4:14b), the same context made things dramatically worse: chain OVAR rose 4.33 to 6.35 (+47%) with std 2.53, and Ancillary-tier OVAR reached 10.82 +/- 8.14 — some runs near normal, some catastrophic. For reasoning models on both backends, context gave no meaningful change (Azure 4.72 to 4.52, delta 0.20; local 4.52 to 4.52).

### Reasoning models gave no ordering advantage

Best lightweight vs best reasoning OVAR: Azure 4.47 vs 4.52, local 4.33 vs 4.52. o4-mini generated 1,083,968 reasoning tokens against gpt-4.1-mini's 101,879 completion tokens, with no measurable OVAR or stockout improvement. I treat this as directional, not causal — the comparison conflates model family, quantisation, serving stack, and (on Azure) temperature.

### Determinism vs instability

Both local blind conditions ran at temperature 0.0 and produced effectively zero inter-run variance (std at machine epsilon). Greedy decoding fixes a single ordering pattern that never adapts to evolving state, so it generates bullwhip by construction. At the other extreme, o4-mini at its API-fixed temperature (~1.0) was the most variable configuration (chain OVAR std 1.12, blind). High stochasticity did not improve outcomes — it just made them unpredictable.

### Seasonal recognition was weak and flat

Pattern scores were indistinguishable across every condition (0.20 to 0.23). Blind matched context, lightweight matched reasoning, local matched cloud. The calendar-month signal made no measurable difference to whether agents acted correctly at event months. The composite of 0.22 reflects a gap between naming a seasonal event and sizing the order to match it.

### Hypothesis verdicts

All seven hypotheses were rejected.

| Hypothesis | Result | Verdict |
|---|---|---|
| H1: an LLM beats exp smoothing (OVAR 0.54, <=5 stockouts) | Best LLM OVAR 4.33, 41 stockouts | REJECTED |
| H2: context helps lightweight by >=0.5 | delta 0.23 (below MPRD) | REJECTED |
| H3: context helps reasoning by >=0.5 | delta 0.20 (below MPRD) | REJECTED |
| H4: blind reasoning beats blind lightweight by >=0.5 | delta -0.02 (opposite) | REJECTED |
| H5: context reasoning beats context lightweight by >=0.5 | delta -0.05 (opposite) | REJECTED |
| H6: context benefit larger for reasoning | -0.03 (opposite) | REJECTED |
| H7: local context lightweight within +/-0.5 of frontier | delta 1.88 (outside bounds) | REJECTED |

## Why the gap is structural

A stateless agent sees only the current period. It has no memory that the high backlog it inherited was partly its own doing last period, so there is no mechanism to self-correct a drift. Exponential smoothing carries one weighted-average forecast forward and partially self-corrects every period — that single state variable, which the stateless agent lacks, accounts for most of the gap. On top of that, an LLM picks a number that reads as plausible rather than one tuned to minimise variance, and every fresh judgement call adds variance, which shows up directly as order variance. A formula has zero within-run variance by construction.

I should not over-state this as a verdict on LLMs: the planning-side rationale capability is real, and the more promising shape is hybrid — an LLM adjusting the parameters of a deterministic policy (e.g. a Diwali safety-stock bump) rather than placing orders directly.

## Limitations

This experiment is deliberately narrow: single product, single chain topology, fixed deterministic lead times, stateless agents, no inter-tier communication, and no unstructured context (no forecasts, market reports, or knowledge bases). The correct scope of the finding is that LLM agents do not outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no memory. It does not generalise to supply chain management broadly, nor to settings with exceptions, disruptions, multi-supplier negotiation, or unstructured signals — those remain open questions. Whether a stateful LLM architecture would narrow the gap is outside what this design can establish. The demand series is synthetic (calibrated to real seasonality but not real dispatch data). The frontier/local comparison is not fully ceteris paribus — temperature, hardware, and quantisation differ — so backend results should not be read as a controlled infrastructure test.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
