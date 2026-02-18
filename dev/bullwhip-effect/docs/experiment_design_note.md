# Experiment Design Note

**Date:** 2026-02-18
**Time:** (UTC)

---

## Experiment Design

**Research question:** Does contextual knowledge reduce the bullwhip effect in LLM-powered supply chains?

### The Independent Variables (What We Vary)

Two dimensions form a 2×2 matrix:

| | **Blind** | **Context** |
|---|---|---|
| **gpt-4.1-mini** (lightweight) | Blind Lightweight | Context Lightweight |
| **o1** (reasoning) | Blind Reasoning | Context Reasoning |

1. **Information treatment** — Blind vs. Context (what the agent knows)
2. **Model capability** — gpt-4.1-mini vs. o1 (how capable the agent is)

---

### The Control Variables (What Is Held Constant)

These are fixed across all configurations and runs:

| Control Variable | Fixed Value |
|---|---|
| **Supply chain structure** | 3-tier: OEM → Lighting Manufacturer → LED Module Supplier |
| **Product** | Single SKU — LED headlight assembly for the Tatva Vecta |
| **Demand series** | 13 months of synthetic Vecta dispatches (fixed CSV, same sequence every run) |
| **Ordering periods** | 13 months |
| **Initial inventory** | 23,000 units at all three tiers |
| **Lead time** | 1 month (fixed, no variability) |
| **Runs per config** | 3 |
| **Order clamps** | None — only negative orders clamped to zero |
| **Cost model** | None (holding and backlog costs both = 0) |
| **Inter-tier communication** | None — each tier sees only its immediate customer's order |
| **Agent memory** | None — each period is a stateless, single-turn LLM call |
| **Inventory mechanics** | Deterministic: receive → fulfill → order, exact integer arithmetic |
| **Random seed** | 42 |

**For the lightweight model specifically:**
- Temperature: 0.4
- Max tokens: 600

**For the reasoning model (o1):**
- Temperature: fixed at 1.0 by the API (not a design choice — o1 ignores it)
- Max tokens: 16,000

---

### Key Design Choices

- **23,000 starting inventory** (~2 weeks of average demand of ~46,700/month) is deliberately low — it forces agents to order actively from period 1 rather than coasting on a buffer.
- **No cost model** means ordering behavior reflects intrinsic supply chain intuition, not penalty avoidance.
- **No order clamps** exposes raw LLM behavior — agents can order zero or arbitrarily large quantities.
- **No multi-turn memory** is a deliberate isolation choice — the experiment tests whether a *single ordering decision* improves with context, not whether agents can learn over time.

---

### Key Metric: OVAR

**Order Variance Amplification Ratio** = Variance(orders placed) / Variance(demand received)

- OVAR = 1.0: No amplification — orders mirror demand variability exactly
- OVAR > 1.0: Bullwhip amplification — orders are more variable than demand
- OVAR < 1.0: Dampening — orders are smoother than demand

---

## How the Experiment Is Measured

### Primary Metric — OVAR (Order Variance Amplification Ratio)

```
OVAR = Variance(orders placed) / Variance(demand received)
```

Computed **per tier, per run**, then averaged across 3 runs with standard deviation reported. This is the core bullwhip measure.

| OVAR | Meaning |
|---|---|
| = 1.0 | Orders perfectly mirror demand — no distortion |
| > 1.0 | Bullwhip amplification — orders are noisier than demand |
| < 1.0 | Dampening — orders are smoother than demand |

---

### Secondary Metrics (per tier, per run)

| Metric | What It Measures |
|---|---|
| **Stockout count** | Periods (out of 13) where a tier cannot fully fulfil demand + backlog — measures service level |
| **Excess inventory** | Sum of (inventory − demand) in periods where inventory exceeds demand — measures waste from over-ordering |
| **Total ordered vs. total demand** | Whether agents systematically over- or under-order across the full 13 months (benchmark: 606,771 units) |
| **Peak overshoot** | Max single-period order ÷ max single-period demand — measures worst-case order spike |
| **Recovery speed** | Periods until a tier achieves consecutive stockout-free operation after the deliberate initial deficit |
| **Mean / std order** | Distributional shape of ordering behaviour |
| **Clamp count** | Number of times a negative order was clamped to zero — should always be 0 given the design |

---

### Cross-Run Stability Check

After aggregating the 3 runs per configuration, the code computes the **Coefficient of Variation (CV)** of OVAR across runs:

```
CV = std(OVAR) / mean(OVAR) × 100%
```

A high CV (e.g., Blind Reasoning OEM: 10.47 ± 4.06 → CV ~39%) signals that the LLM is producing highly variable behaviour run-to-run — the result is directional, not stable.

---

### Pattern Detection Score (Context Agents Only)

For context agents, each decision includes a `pattern_analysis` field. The code scans these for domain-specific keywords (Navratri, Diwali, monsoon, FY-end, wedding season, etc.) and scores how many patterns the agent correctly identified:

```
Pattern score = weighted sum of detected pattern categories / max possible score
```

This measures *qualitative reasoning quality* — did the agent actually use its context, or did it ignore it?

---

### Reasoning Audit (o1 Agents Only)

For the reasoning model, the code compares blind vs. context decisions side-by-side at **periods 1, 6, and 12** (early, mid, late simulation) across all three tiers — showing order quantities, reasoning text, and pattern analysis. This lets you audit *why* the agent ordered what it did, not just *what* it ordered.

---

### What Gets Recorded Per Run

Every run saves a JSON file with:
- Per-period inventory state (before/after), deliveries, fulfillment, backlog, stockout flag
- Every ordering decision: quantity, reasoning text, pattern analysis, clamp flag
- Full order history, demand history, and inventory level arrays
- API call logs: latency, token usage, success/failure per call

This means every single one of the **468 LLM decisions** (12 runs × 13 periods × 3 tiers) is fully traceable back to the agent's reasoning.

---

## Scientific Grounding

> *"Most problems in science and engineering require observation of the system at work and experimentation to elucidate information about why and how it works."*

### 1. Observation of the System at Work

The experiment does not theorise about what LLM agents *would* do — it puts them in a live supply chain loop and observes what actually happens. Every one of the 468 ordering decisions is executed via live Azure OpenAI API calls, recorded with the full reasoning trace, and captured alongside ground-truth inventory state before and after each decision.

The cascade plots, stockout counts, and OVAR scores are all **emergent observations** — they were not predicted, they were measured as the system ran. The blind reasoning agent's oscillation between 150,000 and zero, or the context lightweight agent accumulating 1 million excess units, were not hypothesised outcomes — they were observed.

### 2. Experimentation to Elucidate *Why* and *How*

Several mechanisms are used specifically to move from observation to explanation:

**The 2×2 factorial design isolates causation.** By independently varying information environment (blind vs. context) and model capability (lightweight vs. reasoning), the experiment can attribute outcomes to specific causes. When context reasoning outperforms blind reasoning, you know it is the information — not the model — because the model is held constant.

**The reasoning audit surfaces mechanism.** For the o1 model, blind vs. context decisions are compared side-by-side at periods 1, 6, and 12, including the agent's own explanation of its reasoning. This directly shows *how* the agent is thinking, not just what it decided.

**The pattern detection score tests whether context was used.** The `pattern_analysis` field is scored against domain keywords (Diwali, monsoon, FY-end, etc.), distinguishing between "context helped" and "context was provided but ignored."

**The cross-run stability check (CV) disciplines the findings.** A CV of ~39% for blind reasoning signals that the observation is noisy — the result is directional, not stable. The experiment quantifies its own uncertainty rather than overstating conclusions.

**The ablation treatments decompose the effect.** The `contexttext`, `forecast`, and `pattern` categories strip away one element of context at a time to identify which component drives the improvement — calendar awareness, domain role, or the explicit pattern-analysis instruction.

### 3. Where the Principle Is Acknowledged as Incomplete

The experiment is explicit about where observation alone is insufficient:

- **n=3 per configuration** — directional signal only, not statistical significance.
- **Single demand series** — one set of conditions observed; a different demand pattern may produce different rankings.
- **LLM non-determinism** — the system is stochastic; the experiment observes the *distribution* of behaviour, not a deterministic truth.
- **Prompt sensitivity** — findings reflect this specific prompt design; changing the framing would require re-observation.

### Summary

| Scientific Principle | How the Experiment Implements It |
|---|---|
| Observe the system at work | 468 live LLM decisions across 12 runs, all recorded with full state and reasoning |
| Elucidate *why* | 2×2 factorial design isolates information vs. capability as causal factors |
| Elucidate *how* | Reasoning audits and pattern scoring surface the mechanism inside the agent's decision |
| Acknowledge limits of observation | CV, n=3, single demand series — the experiment quantifies its own uncertainty |

The key design insight is that the experiment does not only measure outcomes (OVAR, stockouts) — it records the agent's own reasoning at every step, which is what allows it to move from observation toward explanation.
