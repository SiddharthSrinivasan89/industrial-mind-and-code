---
title: Agentic Bullwhip Effect: Version 2
date: March 2026
domain: SUPPLY CHAIN · EXPERIMENT WRITEUP
summary: Every heuristic outperformed every LLM configuration. Exponential smoothing beat state-of-the-art reasoning models 8x on order variance and 8x on stockouts, simultaneously.
experiment: Agentic Bullwhip Effect Version 2
slug: agentic-bullwhip-v2
---

## Abstract

Version 2 asks a harder question than Version 1: not which AI configuration performs best, but whether any LLM configuration outperforms a simple rule-based heuristic at all. Four models across lightweight and reasoning tiers, frontier and local, were tested against three deterministic heuristic baselines across 20 independent runs per condition. Every heuristic outperformed every LLM on both order variance and stockouts simultaneously. This is not a tradeoff result.

---

## Experiment Setup

| Field | Value |
|---|---|
| Models | gpt-4.1-mini (frontier lightweight) · o4-mini (frontier reasoning) · phi4:14b (local lightweight) · gpt-oss:120b (local reasoning) |
| Design | 2x2 factorial (context x model tier) + local inference replication |
| Replications | 20 per LLM configuration · 1 per heuristic (deterministic) |
| Primary metrics | OVAR (Order Variance Ratio) + Stockout count, always reported jointly. MPRD: |DOVAR| >= 0.5 required for a practically meaningful claim. |
| Supply chain | 3-tier serial: Tatva Motors (OEM) → Lighting Manufacturer (Ancillary) → LED Component Manufacturer |
| Demand series | 25 months (Jan 2025 to Jan 2027) · single SKU · two full Indian festive cycles |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | 43,609 units, derived as mean + 1.65 sigma of demand series (~95% service level) |
| LLM calls | 11,520 total (4 conditions x 20 runs x 24 periods x 3 tiers x 2 backends) |
| Heuristic baselines | Exponential smoothing (alpha=0.30) · Naive passthrough · Order-up-to |
| Agent design | Stateless, no memory between periods. Deliberate: most real agentic deployments are stateless. |

OVAR interpretation: below 1.0 = dampening · 1.0 = pass-through · above 1.0 = bullwhip amplification.

---

## Key Findings

1. **Every heuristic outperformed every LLM on both OVAR and stockouts simultaneously.** Not a tradeoff. LLMs were strictly dominated on both primary metrics in every configuration tested.

2. **The gap is not marginal.** Exponential smoothing: chain OVAR 0.54, 5 stockouts. Best LLM (local phi4:14b, blind): OVAR 4.33, 41 stockouts. 8x worse on both dimensions at once.

3. **Context had opposite effects by model and backend.** For frontier gpt-4.1-mini, adding business context reduced OVAR marginally (4.70 to 4.47, delta 0.23, below the MPRD threshold). For local phi4:14b, the same context was dramatically worse: chain OVAR jumped from 4.33 to 6.35, with the Ancillary tier hitting 10.82 +/- 8.14 across 20 runs.

4. **Reasoning models showed no ordering advantage.** The 116B gpt-oss:120b produced results indistinguishable from gpt-4.1-mini in blind conditions. o4-mini generated over 1 million reasoning tokens and produced no measurable improvement on either metric. All 7 pre-registered hypotheses were rejected.

---

## Results

### Heuristic Baselines

| Heuristic | Chain OVAR | Stockouts (of 75 possible) |
|---|:---:|:---:|
| Exponential smoothing | **0.54** | **5** |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

Exponential smoothing actively dampens order variance to 0.54, below the demand variance itself. Every LLM condition produced OVAR between 4.33 and 6.35.

### Chain-Average OVAR by LLM Configuration

| Condition | Backend | Chain OVAR (mean +/- std) | Stockouts (mean +/- std) |
|---|---|:---:|:---:|
| **exp_smoothing** | Heuristic | **0.54** | **5** |
| naive_passthrough | Heuristic | 1.00 | 3 |
| order_up_to | Heuristic | 1.71 | 14 |
| L-Blind | Frontier | 4.70 +/- 0.14 | 40.5 +/- 0.83 |
| L-Context | Frontier | 4.47 +/- 0.07 | 39.0 +/- 0.83 |
| L-Blind | Local | 4.33 +/- 0.00 | 41.0 +/- 0.00 |
| L-Context | Local | **6.35 +/- 2.53** | 37.2 +/- 3.11 |
| R-Blind | Frontier | 4.72 +/- 1.12 | 42.9 +/- 3.85 |
| R-Context | Frontier | 4.52 +/- 0.08 | 40.1 +/- 0.85 |
| R-Blind | Local | 4.52 +/- 0.00 | 40.0 +/- 0.00 |
| R-Context | Local | 4.52 +/- 0.05 | 39.6 +/- 0.76 |

L = Lightweight (gpt-4.1-mini / phi4:14b) · R = Reasoning (o4-mini / gpt-oss:120b)

### OVAR by Tier

| Condition | Backend | OEM | Ancillary | Component |
|---|---|:---:|:---:|:---:|
| exp_smoothing | Heuristic | 0.41 | 0.65 | 0.58 |
| L-Blind | Frontier | 4.21 | **6.64** | 3.25 |
| L-Context | Frontier | 4.12 | 6.01 | 3.30 |
| L-Blind | Local | 3.71 | 5.89 | 3.40 |
| L-Context | Local | 4.62 | **10.82** | 3.61 |
| R-Blind | Frontier | 5.94 | 5.18 | 3.05 |
| R-Context | Frontier | 4.13 | 5.99 | 3.45 |
| R-Blind | Local | 4.13 | 5.98 | 3.45 |
| R-Context | Local | 4.13 | 6.01 | 3.43 |

---

## Discussion

The bullwhip failure is structural. Each agent sees only the current period, with no memory of what it ordered previously. Without that causal chain, there is no self-correction mechanism. A stateless agent that over-ordered last period arrives at the next period without knowing it did. Combined with the fact that LLMs optimise for plausible text rather than numerically precise outcomes, the result is an agent that picks a number that sounds reasonable rather than one that dampens variance.

A hybrid approach is the natural path forward. LLMs alone are not ready for stateless, zero-shot ordering decisions. But the marginal context improvement for frontier models suggests some sensitivity to conditions. The natural split: LLM reads conditions and adjusts parameters, formula executes the order.

---

## Experiment Source

Full technical report, code, and data: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2

---

## Methodology Note

All scenarios, companies, products, and supply chain structures are entirely fictional. The experiment was intentionally narrow: single product, fixed lead times, stateless agents, no unstructured context. Results should not be generalised to supply chain management broadly. The correct scope: LLM agents do not outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no unstructured context.
