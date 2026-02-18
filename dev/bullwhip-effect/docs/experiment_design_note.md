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
