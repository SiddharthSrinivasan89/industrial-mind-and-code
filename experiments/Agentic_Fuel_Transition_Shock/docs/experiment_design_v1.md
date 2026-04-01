# Agentic Fuel Transition Shock — Experiment Design v1.0

**Series:** Industrial Mind & Code | Indian Automotive Supply Chain
**Researcher:** Sid | March 2026
**Status:** Draft — design in progress

---

## 1. Research Question

### The Core Question

> When LLM agents operating a diesel-dependent supply chain receive a credible signal that diesel passenger car demand will fall 30% over the next 3 years, do they propagate the shock rationally — or do they amplify it into a bullwhip?

This experiment introduces a **structural demand shock** as the primary perturbation, replacing the seasonal noise used in the Bullwhip experiments. The shock is not random — it is directional, sustained, and known in advance. This tests a fundamentally different capability: whether agents can reason about *future states* rather than just responding to *current inventory conditions*.

### Two-Layer Framing

**Layer 1 — The Rational Propagation Question (Primary)**
Does a structural demand shock propagate through a 3-tier supply chain with rational dampening, or does it amplify as it moves upstream? Rational behaviour would see each tier smoothly adjust orders downward in line with the shock magnitude. Irrational behaviour amplifies the shock — the component manufacturer over-corrects relative to the actual demand change at the OEM tier.

**Layer 2 — The Context Question (Conditional)**
Among LLM configurations, does knowing *why* demand is falling (fuel transition context) produce better shock propagation than knowing only *that* demand is falling (blind numerical shock)? Does a reasoning model handle structural discontinuity better than a lightweight model?

---

## 2. Motivation and Industry Grounding

### The Diesel Transition in India (FY2025 Baseline)

Indian passenger car diesel sales in FY2025 totalled **7,77,303 units** — 18% of the 43.2L unit market. The fuel mix by OEM reveals extreme concentration risk:

| OEM | Diesel Units | Diesel % | Risk Profile |
|---|---|---|---|
| Mahindra | 4,25,329 | 77.1% | Critical — nearly all volume is diesel |
| Hyundai | 1,07,187 | 17.9% | Moderate |
| Kia | 84,403 | 33.1% | High |
| Toyota | 79,156 | 25.6% | Moderate |
| Tata | 72,333 | 13.1% | Low-moderate |
| Jeep | 3,951 | 100.0% | Critical — entire portfolio is diesel |
| Maruti Suzuki | 0 | 0.0% | None — already exited diesel |

A 30% diesel volume decline over 3 years translates to approximately **2.33L fewer diesel units per year** across the market. For a diesel engine component supplier whose primary customers are Mahindra and Jeep, this is an existential planning challenge. This experiment simulates that supplier chain.

### Why This Matters for Agent Deployment

Enterprises deploying LLM agents in procurement and supply chain roles need to know: when the market sends a structural signal (regulation, fuel transition, technology shift), do AI agents help or harm? An agent that over-corrects on early signals can devastate supplier relationships. An agent that ignores the signal leaves the firm holding obsolete inventory.

---

## 3. Supply Chain Structure

Three tiers, serial cascade — identical architecture to the Agentic Bullwhip experiments, enabling direct comparison.

| Tier | Company | Role | Demand Source |
|---|---|---|---|
| OEM | Tatva Motors (diesel SUV division) | Production planning for diesel powertrain assemblies | Monthly retail dispatch targets (diesel segment) |
| Ancillary | DriveTech Assemblies | Diesel powertrain sub-assembly manufacturer | OEM powertrain assembly order |
| Component | PrecisionCore Engineering | Diesel engine component manufacturer (injectors, fuel pumps) | Ancillary sub-assembly order |

**Information isolation:** No tier can see any other tier's inventory, orders, or reasoning. Each tier receives only the order placed by its immediate downstream customer, plus its own inventory state. The shock signal is delivered differently depending on condition (see Section 5).

---

## 4. The Demand Shock Design

### Baseline Demand Series (Pre-Shock, Months 1–6)
Derived from the FY2025 diesel segment data calibrated to a single OEM's monthly run rate. Monthly diesel dispatch volume is approximately **64,775 units/month** at market level. The simulation models a single Mahindra-scale OEM with roughly **35,000 units/month** — consistent with Mahindra's 4,25,329 annual diesel units divided by 12.

### Shock Structure
The shock is introduced at **Month 7** and plays out over a 36-month horizon (the full simulation window).

```
Pre-shock  (Months 1–6):   ~35,000 units/month  [stable baseline]
Shock year 1 (Months 7–18):  linear decline to 28,000 units/month  (−20%)
Shock year 2 (Months 19–30): linear decline to 24,500 units/month  (−30% total)
Shock year 3 (Months 31–36): stable at 24,500 units/month  [new equilibrium]
```

Total simulation: **36 ordering periods + 1 fulfilment-only period = 37 months.**

### Why a Gradual Shock, Not a Step Change
A step change (demand drops 30% overnight) is unrealistic for automotive. Regulatory transitions and fuel preference shifts are gradual. The gradual shock tests whether agents can detect a trend in early periods and pre-position, or whether they only react after the decline is obvious — a more demanding and ecologically valid test.

---

## 5. Conditions Under Test

### 5.1 The 2×2 LLM Matrix

| | Blind | Context |
|---|---|---|
| **Lightweight** (gpt-4.1-mini) | `blind_lightweight` | `context_lightweight` |
| **Reasoning** (o1) | `blind_reasoning` | `context_reasoning` |

### 5.2 Blind Condition

Agents receive only numerical state data: current inventory, backlog, demand received this period, and period number. No company identity, no product, no fuel type, no market context. The only signal available is the number itself declining over time.

**Blind system prompt:**
```
You are a supply chain ordering agent.
Always respond with valid JSON only. No additional text before or after the JSON object.
```

### 5.3 Context Condition

Each tier receives its full company persona, the calendar month and year, and — critically — the **market signal** that distinguishes this experiment from the Bullwhip series:

> "Industry data shows diesel passenger car sales are projected to decline approximately 30% over the next 3 years due to regulatory shifts and changing consumer preferences. Plan accordingly."

This signal is included in every context agent's system prompt from Month 1 — including the pre-shock baseline period. This tests whether agents act on a known future signal before it manifests in their order book, or whether they wait for the numbers to confirm it.

**Context personas:**

| Tier | Persona |
|---|---|
| OEM | Tatva Motors diesel SUV division, India. You manage procurement of diesel powertrain assemblies. Your monthly target is set by retail dispatch forecasts for the Vecta diesel range. |
| Ancillary | DriveTech Assemblies, India. You manufacture diesel powertrain sub-assemblies for Tatva Motors. You receive monthly assembly orders and place component orders upstream. |
| Component | PrecisionCore Engineering, India. You manufacture diesel engine components (injectors, fuel pumps) for DriveTech Assemblies. You set production capacity monthly based on incoming orders. |

### 5.4 Heuristic Baselines (No LLM)

Run once against the full 37-month demand series. These are the rational-behaviour benchmarks.

| Policy | Rule | What it reveals |
|---|---|---|
| Naive Passthrough | Order exactly what was received | OVAR = 1.0 by construction. Shows raw shock transmission with zero amplification. |
| Order-Up-To | `order_t = max(0, S - inventory_position_t)`, S = 35,000 | How a static target policy handles a declining demand environment — does the high S create persistent over-ordering? |
| Adaptive Order-Up-To | S updated quarterly as trailing 3-month mean demand | Best-case rational heuristic. Shows the ceiling for non-LLM performance under a structural decline. |

---

## 6. Primary Metrics

> **Critical reporting rule:** OVAR, stockout count, and over-order ratio are always reported together. A low OVAR achieved by under-ordering into a declining market is rational. A low OVAR achieved by over-ordering is waste. Context matters.

### 6.1 OVAR — Shock Amplification Ratio

```
OVAR = Var(orders placed) / Var(demand received)
```

Computed per tier over the full 36 ordering periods. Values > 1 indicate the agent amplified the shock signal beyond what it received. Values < 1 indicate dampening — orders are smoother than the demand signal.

**Key difference from Bullwhip experiment:** In the Bullwhip series, OVAR > 1 is always bad. Here, OVAR interpretation depends on direction:
- High OVAR driven by over-correction (early deep cuts, then rebound) = irrational amplification
- Low OVAR by smooth gradual reduction = rational propagation

### 6.2 Shock Tracking Error

```
Tracking Error (month t) = order_placed_t − rational_order_t
```

Where `rational_order_t` is defined as the Naive Passthrough order (i.e., exactly matching demand received). Cumulative tracking error over 36 periods measures whether agents systematically over-cut or under-cut relative to the true demand decline.

### 6.3 Lead Indicator Score

Fraction of periods in Months 7–12 (first 6 months of decline) where the agent's order is already below its Month 1–6 mean. Measures whether context agents act on the signal before the numbers confirm it. Blind agents cannot score above chance on this metric.

### 6.4 Stockout Count

Periods where inventory cannot fulfil demand. Reported per tier and as chain total.

### 6.5 Excess Inventory (Over-Order Waste)

Sum of (inventory − demand) in surplus periods. Particularly important here — an agent that ignores the demand decline will accumulate obsolete diesel component inventory, which is the real-world failure mode this experiment targets.

---

## 7. Secondary Metrics

| Metric | Definition |
|---|---|
| Peak under-order | Max single-period order cut relative to prior month — measures panic response |
| Recovery periods | Months to stabilise after initial shock response — measures adaptability |
| Tier lag | Number of periods between OEM order decline and Component order decline — measures upstream propagation speed |
| CV (stability) | std(OVAR) / mean(OVAR) × 100% — CV > 30% signals erratic behaviour |
| Cost per run | Token usage × pricing rates — tracking metric only, not used in hypothesis testing |

---

## 8. Hypotheses

All directional. This is an exploratory study — no pre-specified effect size thresholds.

| ID | Hypothesis |
|---|---|
| H1 | Context agents begin reducing orders before the demand decline manifests (positive lead indicator score). Blind agents do not. |
| H2 | Blind agents produce higher OVAR than context agents — they react to the declining numbers with more variance than the signal warrants. |
| H3 | Reasoning models (o1) produce lower tracking error than lightweight models — they better approximate the rational decline trajectory. |
| H4 | The component tier accumulates the most excess inventory in the blind condition — the shock signal is weakest and most delayed by the time it reaches the deepest upstream node. |
| H5 | Context + reasoning is the only configuration that produces a lead indicator score > 0 in the first shock quarter (Months 7–9). |

---

## 9. Shared Parameters

| Parameter | Value |
|---|---|
| Initial inventory | 35,000 units at all three tiers |
| Lead time | 1 month deterministic |
| Runs per LLM condition | 20 |
| Runs per heuristic | 1 (deterministic) |
| Order floor | Zero — negative orders clamped to 0 |
| Order ceiling | None |
| Agent memory | None — each period is a stateless single-turn LLM call |
| Numeric forecast | Not provided to any agent in any condition |
| Parse error tolerance | Zero — any run with parse errors is invalid and replaced |
| Execution order per period | OEM → Ancillary → Component (serial) |
| Simulation length | 37 months (36 ordering + 1 fulfilment-only) |

---

## 10. Execution Order

| Phase | What | Gate |
|---|---|---|
| 0 | Demand series generation and checksumming. Heuristic baseline module coded and tested. Quality gates implemented. | Must complete before any LLM run begins. |
| 1 | Blind conditions (E1: blind_lightweight, blind_reasoning) | Phase 0 complete. |
| 2 | Context conditions (E2: context_lightweight, context_reasoning) | Phase 0 complete. Runs in parallel with Phase 1. |
| 3 | Analysis | All 4 conditions complete with zero parse errors and valid n=20. |
| 4 | Comparison to Bullwhip baseline | Cross-reference OVAR results against Agentic_Bullwhip_Effect_Final aggregated results. Do the same model configurations behave consistently across shock types? |

---

## 11. Connection to Prior Work

This experiment is a direct extension of the **Agentic Bullwhip Effect** series. Key design decisions are preserved for comparability:

- Same 3-tier serial supply chain architecture
- Same 2×2 blind vs context × lightweight vs reasoning matrix
- Same OVAR primary metric
- Same persona structure (blind = role-agnostic, context = named company identities)

**What is new:**
- Demand shock is structural and directional, not seasonal and mean-reverting
- Context condition includes an explicit forward-looking market signal (not just "who you are")
- Lead Indicator Score is a new metric with no analogue in the Bullwhip series
- Adaptive Order-Up-To heuristic baseline added — more appropriate benchmark for a declining market
- Simulation length extended to 37 months to capture the full shock trajectory

---

## 12. Open Questions (To Resolve Before Locking Design)

1. **Shock onset timing:** Should the market signal in the context prompt be present from Month 1 (testing anticipation) or introduced at Month 7 (testing real-time reaction)? Current design: Month 1. Rationale: tests the stronger claim — do agents act on known future information?

2. **Shock magnitude variation:** Should we run a second scenario with a 50% decline (e.g., approaching a diesel phase-out)? Could be an E2 extension, not the primary run.

3. **Demand series granularity:** Monthly run rate of 35,000 units is a reasonable proxy for a Mahindra-scale diesel OEM. Needs validation against the autopunditz FY2025 data and calibration to seasonal patterns within the diesel segment.

4. **Cross-experiment comparison protocol:** Define formally how OVAR from this experiment will be compared to the Bullwhip series — same statistic, but the interpretation differs (structural decline ≠ seasonal variance).

---

---

## 13. Possible Scenario Extensions (Unexplored — Parked for Review)

These directions emerged from early design exploration. None are in scope for v1. Recorded here to avoid re-deriving them later.

---

### Scenario A — NMI Compatibility Reasoning

**Origin:** The FY2025 data shows Mahindra running legacy diesel models (Scorpio, Bolero, Thar) alongside new EV launches (BE6, XEV 9e) simultaneously in FY2025. A Tier-2 press brake supplier is receiving orders for different part geometries, different material grades, and different tolerances from the same customer — increasingly mixed on the same line.

**The question:** When a new model enters the line (new product introduction / NMI), can an LLM agent given a new vehicle spec sheet and an existing line capability profile identify what breaks before physical trials begin?

**What would be tested:** Does the agent surface non-obvious conflicts — hoist clearance, tooling reach angle, mixed-model sequencing buffer — that experienced IEs know from prior NMIs but that don't appear in a spec comparison?

**Why parked:** Requires defining a specific line capability profile and NMI spec sheet as inputs. Ground truth requires IE domain expertise to validate. Not directly connected to the fuel mix dataset without additional scaffolding.

---

### Scenario B — Mixed Material FMEA Re-scoring

**Origin:** The press brake TPM dataset (V2) contains a material transition happening in three undocumented steps: MS-441 (310 MPa) → MS-447 (380 MPa) → HSLA (550 MPa). The machine is rated to 400 MPa. None of these transitions were managed as formal process changes. The existing FMEA — if one exists — was validated against one material grade and is now wrong for the others.

**The question:** Given an FMEA written for a diesel-era press brake operation (mild steel, low-current auxiliary systems), can an LLM identify which failure modes have changed severity or occurrence when the material mix shifts, and re-score the RPN table accordingly?

**What would be tested:**
- Does the agent correctly identify that Severity scores change when the same connector or tooling failure now affects a safety-critical EV system rather than a comfort feature?
- Does it identify new failure modes that didn't exist in the diesel context (e.g., thermal runaway path through a power distribution fault)?
- Does it distinguish between reversible RPN changes (occurrence — can be managed) and irreversible ones (severity — inherent to the new architecture)?

**Scoring:** Binary rubric against a pre-written ground truth FMEA re-score. Each criterion checkable without IE expertise: did the agent flag the right failure modes, did it change the right scores, did it introduce plausible new failure modes?

**Why parked:** Ground truth FMEA needs to be written first. No public diesel 12V auxiliary FMEA at the required component level exists — SAE J1739 is paywalled, OEM FMEAs are confidential. Ground truth must be authored by a domain expert (IE) before the experiment can be scored. This is the right next step when ready.

---

### Scenario C — Power Architecture Transition Reasoning

**Origin:** In a diesel vehicle the 12V auxiliary battery runs the head unit, basic sensors, lighting, and comfort features. In an EV, the auxiliary system must support brake-by-wire, steer-by-wire, thermal management, ADAS sensors, multiple ECUs, and active safety systems. The same component category — connector, harness, fuse, power distribution unit — now sits in a safety-critical path it never occupied before.

**The question:** Can an LLM agent, given a diesel-era component specification and the EV power architecture context, correctly reason about how the risk profile of that component changes — specifically which FMEA Severity scores must be updated and why?

**The specific IE insight this tests:** A loose connector in a diesel car's auxiliary harness = head unit flickers = low severity. The same loose connector in an EV power distribution unit = potential loss of brake-by-wire = catastrophic severity. The failure mode is identical. The severity is completely different. Does the model understand why?

**Why parked:** Closely related to Scenario B. The two could be combined into a single experiment with two conditions — press brake material transition (Scenario B) and electrical power architecture transition (Scenario C) — both scored against the same FMEA re-scoring rubric. Separating them may not be necessary.

---

### Scenario D — Transition-Aware Root Cause Analysis (TPM Extension)

**Origin:** The TPM press brake dataset treats the HSLA material introduction (ADM-002) as a local process failure — procurement added a new material grade with no engineering change notification. But in the broader context, HSLA introduction at a Tier-2 press brake supplier is a downstream consequence of an OEM platform transition. The root cause analysis changes depending on whether the agent knows this context.

**The question:** Does an LLM agent that knows about the OEM fuel mix transition produce a qualitatively different (and more correct) root cause analysis than one that only sees the shop floor data?

**Why it was rejected for v1:** Market-level context is too indirect for a maintenance root cause. A maintenance engineer diagnosing PB-07 would not and should not rely on OEM market share data. The shop floor data contains sufficient signal (material grade, batch change, no ECN) to reach the correct root cause without market context. Adding market context risks inflating agent performance on a task that doesn't require it.

**What remains valid:** The material transition itself (MS-441 → MS-447 → HSLA) is a legitimate and operationally grounded transition that the TPM dataset does not fully capture. This could be enriched as a standalone TPM dataset extension — not by adding market data, but by making the material transition more explicit in the maintenance and quality records.

---

*Agentic Fuel Transition Shock — Design v1.0 | Industrial Mind & Code | March 2026*
