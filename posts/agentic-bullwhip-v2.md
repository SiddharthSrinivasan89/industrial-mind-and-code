---
title: Agentic Bullwhip Effect — Version 2
date: March 2026
domain: SUPPLY CHAIN · EXPERIMENT WRITEUP
summary: Every heuristic outperformed every LLM configuration. Exponential smoothing beat state-of-the-art reasoning models 8× on order variance and 8× on stockouts — simultaneously.
experiment: Agentic Bullwhip Effect Version 2
slug: agentic-bullwhip-v2
---

## Abstract

The bullwhip effect is a foundational supply chain problem: small fluctuations in consumer demand cause progressively larger swings in orders further up the chain, leading to excess inventory, stockouts, and wasted capacity. Version 2 asks a harder question than Version 1: not which AI configuration performs best, but whether any LLM configuration outperforms a simple rule-based heuristic at all. Four LLM configurations — lightweight and reasoning models, frontier and local — were tested against three deterministic heuristic baselines across 20 independent runs per condition, totalling 11,520 LLM calls over a 25-month synthetic demand series.

Every heuristic outperformed every LLM configuration on both order variance and service level simultaneously. This is not a tradeoff result — the LLMs were strictly worse on both dimensions at once.

---

## Experiment Setup

| Field | Value |
|---|---|
| Models | gpt-4.1-mini (frontier lightweight) · o4-mini (frontier reasoning) · phi4:14b (local lightweight) · gpt-oss:120b (local reasoning) |
| Design | 2×2 factorial (context × model tier) + local inference replication |
| Replications | 20 per LLM configuration · 1 per heuristic (deterministic) |
| Primary metrics | OVAR (Order Variance Ratio) + Stockout count — always reported jointly |
| Supply chain | 3-tier serial: Tatva Motors (OEM) → Lighting Manufacturer (Ancillary) → LED Component Manufacturer |
| Demand series | 25 months (Jan 2025 – Jan 2027) · single SKU · two full Indian festive cycles |
| Lead time | 1 month deterministic at all tiers |
| Initial inventory | 43,609 units — derived as mean + 1.65σ of demand series (~95% service level) |
| LLM calls | 11,520 total (4 conditions × 20 runs × 24 periods × 3 tiers × 2 backends) |
| Heuristic baselines | Exponential smoothing (α=0.30) · Naive passthrough · Order-up-to |
| Agent design | Stateless — no memory between periods. This was deliberate: most real agentic deployments are stateless too. |

**OVAR interpretation:** < 1.0 = dampening (orders smoother than demand) · = 1.0 = pass-through · > 1.0 = bullwhip amplification. Minimum practically relevant difference (MPRD): |ΔOVAR| ≥ 0.5 at chain level.

---

## Key Findings

1. **Every heuristic outperformed every LLM on both OVAR and stockouts simultaneously.** This is not a tradeoff. The LLMs were strictly dominated across both primary metrics in every configuration tested.

2. **The gap is not marginal.** Exponential smoothing achieved chain-average OVAR 0.54 with 5 stockout periods. The best LLM (local phi4:14b, blind) achieved OVAR 4.33 with 41 stockouts — 8× worse on both dimensions.

3. **The Ancillary tier (middle) is consistently the most amplified.** Every model, every configuration. It absorbs already-distorted orders from the OEM tier and amplifies them further — the textbook bullwhip accumulation point.

4. **Context had opposite effects depending on model and backend.** For the frontier lightweight model (gpt-4.1-mini), adding business context reduced OVAR marginally (4.70 → 4.47, Δ=0.23 — below the MPRD threshold). For the local lightweight model (phi4:14b), the same context made things dramatically and unpredictably worse: chain OVAR jumped from 4.33 to 6.35, with the Ancillary tier hitting 10.82 ± 8.14 — indicating some runs were catastrophic outliers.

5. **Reasoning models showed no ordering advantage over lightweight models.** The 116B gpt-oss:120b (local reasoning) produced results statistically indistinguishable from gpt-4.1-mini across blind conditions. Additional inference compute — o4-mini generated over 1 million reasoning tokens — produced no measurable OVAR or stockout improvement.

6. **The failure is structural, not a prompting problem.** Each agent sees only the current period's state — it has no memory of what it ordered last period or what that caused. This was deliberate: most real agentic deployments are stateless. Combined with the fact that LLMs optimise for plausible text, not numerically precise outcomes, the result is an agent that picks a number that sounds reasonable rather than one that dampens variance. The heuristic doesn't reason — it just applies the formula it was built for.

---

## Results

### Heuristic Baselines

| Heuristic | Chain OVAR | Stockouts (of 75 possible) |
|---|:---:|:---:|
| Exponential smoothing | **0.54** | **5** |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

Exponential smoothing does not merely hold OVAR at 1.0 — it actively dampens order variance to 0.54, below the demand variance itself. This is the correct comparison point. Every LLM condition produced OVAR 4.33–6.35.

### Chain-Average OVAR by LLM Configuration

| Condition | Backend | Chain OVAR (mean ± std) | Stockouts (mean ± std) |
|---|---|:---:|:---:|
| **Heuristic: exp_smoothing** | — | **0.54** | **5** |
| **Heuristic: naive_passthrough** | — | 1.00 | 3 |
| **Heuristic: order_up_to** | — | 1.71 | 14 |
| L-Blind | Frontier | 4.70 ± 0.14 | 40.5 ± 0.83 |
| L-Context | Frontier | 4.47 ± 0.07 | 39.0 ± 0.83 |
| L-Blind | Local | 4.33 ± 0.00 | 41.0 ± 0.00 |
| L-Context | Local | **6.35 ± 2.53** | 37.2 ± 3.11 |
| R-Blind | Frontier | 4.72 ± 1.12 | 42.9 ± 3.85 |
| R-Context | Frontier | 4.52 ± 0.08 | 40.1 ± 0.85 |
| R-Blind | Local | 4.52 ± 0.00 | 40.0 ± 0.00 |
| R-Context | Local | 4.52 ± 0.05 | 39.6 ± 0.76 |

L = Lightweight (gpt-4.1-mini / phi4:14b) · R = Reasoning (o4-mini / gpt-oss:120b)

### OVAR by Tier

| Condition | Backend | OEM | Ancillary | Component |
|---|---|:---:|:---:|:---:|
| exp_smoothing | — | 0.41 | 0.65 | 0.58 |
| L-Blind | Frontier | 4.21 | **6.64** | 3.25 |
| L-Context | Frontier | 4.12 | 6.01 | 3.30 |
| L-Blind | Local | 3.71 | 5.89 | 3.40 |
| L-Context | Local | 4.62 | **10.82** | 3.61 |
| R-Blind | Frontier | 5.94 | 5.18 | 3.05 |
| R-Context | Frontier | 4.13 | 5.99 | 3.45 |
| R-Blind | Local | 4.13 | 5.99 | 3.45 |
| R-Context | Local | 4.13 | 6.01 | 3.43 |

### Context Effect (Frontier Lightweight vs Local Lightweight)

| Condition | Frontier OVAR | Local OVAR | |Δ| | Equivalent (±0.5)? |
|---|:---:|:---:|:---:|:---:|
| L-Blind | 4.70 | 4.33 | 0.37 | Borderline |
| L-Context | 4.47 | 6.35 | **1.88** | No — diverges significantly |
| R-Blind | 4.72 | 4.52 | 0.20 | Yes |
| R-Context | 4.52 | 4.52 | 0.00 | Yes |

---

## Hypothesis Verdicts

All hypotheses required |ΔOVAR| ≥ 0.5 (MPRD) at chain level. OVAR and stockouts reported jointly.

| Hypothesis | Prediction | Result | Verdict |
|---|---|---|:---:|
| **H1** — Primary | At least one LLM beats exp smoothing (0.54) on OVAR with ≤5 stockouts | Best LLM: 4.33 OVAR, 41 stockouts | REJECTED |
| **H2** — Context, lightweight | context_lightweight OVAR < blind_lightweight by ≥0.5 | Δ=0.23, below MPRD | REJECTED |
| **H3** — Context, reasoning | context_reasoning OVAR < blind_reasoning by ≥0.5 | Δ=0.20, below MPRD | REJECTED |
| **H4** — Reasoning, no context | blind_reasoning OVAR < blind_lightweight | Δ=−0.02, opposite direction | REJECTED |
| **H5** — Reasoning, with context | context_reasoning OVAR < context_lightweight | Δ=−0.05, opposite direction | REJECTED |
| **H6** — Interaction | Context benefit larger for reasoning than lightweight | C5=−0.03, opposite direction | REJECTED |
| **H7** — Local/frontier replication | Local context_lightweight within ±0.5 OVAR of frontier | Δ=1.88, outside equivalence bounds | REJECTED |

---

## Discussion

### Why LLMs fail to smooth

The bullwhip failure is structural. Each agent sees only the current period — no memory of what it ordered previously, no causal chain connecting its past decisions to the current state. Without this, there is no mechanism for self-correction. A stateless agent that ordered too much last period arrives at the next period without knowing it did. The supply chain inherits the consequences; the agent does not.

The second reason is that quantity estimation is not what LLMs optimise for. LLMs reason about supply chains the way a textbook does — they can describe the bullwhip effect, but that doesn't mean they can avoid causing it. The formula doesn't reason. It applies the math it was built for.

### Context as a noise amplifier

The local lightweight model result deserves specific attention. Adding business context to phi4:14b didn't help — it destabilised an otherwise rigid model. The Ancillary tier standard deviation of 8.14 OVAR across 20 runs means some runs were near-normal while others were extreme outliers. Context triggered an aggressive ordering stance in some runs that then propagated as an amplified shock upstream. The rigid blind model, repeating the same order every run, at least produced *predictable* underperformance.

### What this means for deployment

A hybrid approach is needed. LLMs alone are not ready for stateless, zero-shot ordering decisions — making quantity calls each period with no memory, no fine-tuning, and no outcome feedback. But the data points toward where they do belong. Frontier models showed marginal improvement with business context — suggesting some sensitivity to conditions. The heuristics won on execution every time.

> **The natural split: LLM reads conditions and adjusts inputs, formula executes the order.**

---

## Experiment Source

Full technical report, code, and data for this experiment are available on GitHub: [LINK]

---

## Methodology Note

All scenarios, companies, products, and supply chain structures in this experiment are entirely fictional and constructed for experimental purposes. No proprietary, confidential, or employer-owned data was used. The experiment was intentionally narrow: single product, fixed 1-month lead times, no supplier disruptions, no unstructured context, no multi-objective tradeoffs. Results reflect this specific configuration and should not be generalised to supply chain management broadly. The correct scope of any conclusion from this experiment is: *"LLM agents do not outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no unstructured context."*
