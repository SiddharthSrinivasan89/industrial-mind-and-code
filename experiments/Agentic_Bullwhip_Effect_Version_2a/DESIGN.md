# Agentic Bullwhip Experiment — Version 2a Design

**Series:** Industrial Mind & Code | Tatva Motors Vecta
**Researcher:** Sid | March 2026
**Status:** Complete — sarvam-30b (V2a / V2d canonical dataset)

---

## 1. Research Question

This experiment asks a two-layer question about AI agents in supply chain management.

### Layer 1 — The Enterprise Question (Primary)

> Do LLM agents find a better balance between bullwhip amplification and service level than simple rule-based heuristics?

This is the foundational question. If no LLM configuration beats a simple heuristic on both OVAR and stockouts simultaneously, the case for deploying LLM agents in supply chains is weak regardless of which configuration performs best.

### Layer 2 — The AI Configuration Question (Conditional on Layer 1)

> Among LLM configurations, which deployment setup gets closest to the optimal OVAR-stockout balance — and is it driven by context, reasoning capability, or the combination?

This layer is only meaningful if at least one LLM configuration clears the Layer 1 bar. If Layer 1 holds, Layer 2 guides enterprise deployment decisions: if context helps (C1, C2), invest in rich persona prompts; if reasoning matters more (C3, C4), invest in reasoning-class models; if there is an interaction (C5), both are required together.

### Scope and Generalisability — Read Before Interpreting Results

**This experiment is intentionally narrow.** It tests whether LLM agents can outperform simple blind replenishment heuristics in a stylised three-tier supply chain with fixed lead times and limited state information. The task is:

- Single product, fixed topology
- Deterministic 1-month lead time
- No supplier disruptions, no negotiation, no exception handling
- No unstructured contextual input (regulatory text, supplier communications, weather data)
- No multi-objective tradeoff beyond inventory position and service level

**In this class of repetitive, low-information, operationally stable decision, blind heuristics may well be strong competitors — but that is itself a question this experiment is designed to answer.** Any finding, in either direction, should be read within this scope. A result showing LLMs do not outperform heuristics here does not generalise to supply chain management broadly; neither does a result showing they do.

**Settings that may produce different results** — and that remain outside the scope of this experiment — include: exception-driven replenishment, multi-supplier negotiation, regime shifts, policy and regulatory text ingestion, conflicting cross-functional objectives, and decisions requiring unstructured context in the loop. Whether LLMs add value in those settings is an open empirical question.

**The correct scope of any conclusion from this experiment is:** *"LLM agents do [or do not] outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no unstructured context."* Conclusions should not be extended to supply chain management more broadly without additional experiments in more complex settings.

---

## 2. Supply Chain Structure

Three tiers, serial cascade. Each tier is operated by either an LLM agent or a heuristic policy. No tier can see any other tier's inventory, orders, or decisions — only the order placed by its immediate downstream customer arrives each period.

| Tier | Role | Receives | Orders from |
|---|---|---|---|
| OEM | Tatva Motors — production planning | Monthly Vecta despatch target | Ancillary Assembler |
| Ancillary | Lighting Manufacturer — assembly | OEM Lighting Assembly order | Component Manufacturer |
| Component | LED Supplier — production capacity | Ancillary LED component order | Production line |

---

## 3. Agent Design — Persona Architecture

A key design decision in this version: the blind and context conditions are deliberately asymmetric in their identity structure. This asymmetry is intentional — it is what is being measured.

### 3.1 Blind Agent — Minimal Identity

No company name, no product, no geography, no calendar. The agent receives only numerical state data. This represents a fully stripped deployment — the baseline.

**State variables provided to every agent every period (identical across blind and context, identical to heuristic information set):**

| Variable | Definition |
|---|---|
| `demand_received` | Units ordered by immediate downstream customer this period |
| `on_hand` | Units remaining in stock **after** serving demand this period (post-fulfilment) |
| `backlog` | Unfulfilled units carried forward into next period (zero if demand was fully met) |
| `inventory_position` | `on_hand − backlog` — the quantity the Order-Up-To heuristic uses |

Note: with a 1-month deterministic lead time and replenishment arriving at the start of each period, there are no units in transit at decision time. Pipeline stock is always zero and is excluded from `inventory_position`.

All four variables are provided in the user prompt each period. Agents and heuristics operate on the same information set. No agent receives any other tier's state.

**Blind Agent System Prompt (all tiers identical)**

```
You are a supply chain ordering agent.
Always respond with valid JSON only. No additional text before or after the JSON object.
Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}
```

### 3.2 Context Agent — Distinct Named Personas Per Tier

Each tier has a unique, named company identity with role-specific framing. The agent also receives the calendar month name (e.g. "November") — but not the year. This represents a realistic enterprise deployment where each agent knows who it is, what it makes, and what time of year it is operating.

The persona asymmetry mirrors real-world multi-agent deployments where each node in the supply chain is a distinct business entity. This is a realistic deployment configuration — each tier receives the identity and calendar information that a real supply chain manager would naturally possess. The blind condition strips this information deliberately; the context condition restores it. The experiment measures whether that restoration changes ordering behaviour.

**Context Agent System Prompt format (per tier, see persona table below)**

```
You are <persona>.
Always respond with valid JSON only. No additional text before or after the JSON object.
Required format: {"order_quantity": <integer>, "rationale": "<one sentence explaining your decision>"}
```

| Tier | Context Agent Persona |
|---|---|
| OEM | Tatva Motors, India. Product: Vecta Lighting Assembly. Upstream supplier: ancillary lighting manufacturer. Each month: receive a production despatch target and place a Lighting Assembly order. |
| Ancillary | Lighting manufacturer, India. Customer: Tatva Motors (Vecta Lighting Assembly orders). Upstream supplier: LED component manufacturer. Each month: receive a Lighting Assembly order and place an LED component order. |
| Component | LED component manufacturer, India. Customer: lighting manufacturer supplying Tatva Motors Vecta assemblies. Each month: receive a component order and set production capacity. |

**What the context agent is NOT told:** The agent is never told what seasonal patterns exist. It is never given a demand forecast. It receives its persona, the calendar month name, and the four state variables defined in Section 3.1. No year is provided. Any seasonal reasoning must come from its own world knowledge — this is the capability being tested.

---

## 4. Policies Under Test

Two categories of policies are compared: deterministic heuristic baselines and LLM agent conditions. Both are evaluated on the same metrics. This is what enables the Layer 1 research question.

### 4.1 Heuristic Baselines — Deterministic, No LLM

These policies require no LLM calls. They are run once against the fixed demand series. They serve as the performance benchmark that LLM conditions must clear to justify their cost and complexity. The primary benchmark is the strongest blind heuristic on the actual calibrated series — not the most canonical one in textbooks.

| Policy | Role | Rule | What it reveals |
|---|---|---|---|
| Naive Passthrough | Floor reference | Order exactly what your customer ordered this period | OVAR = 1.0 by construction. High stockouts expected — no safety stock built. If an LLM cannot beat this, it is adding noise, not value. |
| Exponential Smoothing | **Primary benchmark** | `F_t = 0.30 × D_t + 0.70 × F_{t-1}`. Order smoothed forecast plus backlog coverage, floored at 0. `F_1 = D_1`. | On this calibrated demand series, exponential smoothing is the strongest blind heuristic (OVAR 0.54, stockouts 5). It is a mechanical signal-smoother with no calendar knowledge — slow to react to demand spikes and slow to forget them. LLM conditions must beat this on both OVAR and stockouts simultaneously to justify their cost and complexity. If context agents match smoothing but do not exceed it, the benefit is noise reduction alone, not genuine seasonal intelligence. |
| Order-Up-To | Secondary diagnostic | Forecast-based base-stock rule: `F_t = 0.30 × D_t + 0.70 × F_{t-1}`, `target_position_t = round(F_t) + SS`, `order_t = max(0, target_position_t - inventory_position_t)`. Fixed safety stock `SS = S − mean_demand`; `F_1 = D_1`. | Retained as a secondary comparator because it shows how a fixed safety-stock buffer can amplify orders under seasonal demand — useful for understanding why structural inventory policies can underperform adaptive smoothing on non-stationary series. OVAR 1.71, stockouts 14 on the calibrated series. |

### 4.2 LLM Conditions — V2a Configuration

V2a uses sarvam-30b for both tiers. Blind conditions were not viable (see Section 4.3 note). Only context conditions were run in the main experiment.

| | Context (run) | Blind (not run) |
|---|---|---|
| **Lightweight** (sarvam-30b, `think=False`) | `context_lightweight` Temp: 1.0 \| Max tokens: 4,096 | Abandoned — ~20% per-call error rate, not viable for 10-run experiment |
| **Reasoning** (sarvam-30b, `think=True`) | `context_reasoning` Temp: 1.0 \| Max tokens: 8,192 | Abandoned — same reason |

**Temperature:** 1.0 for all conditions. Mandated by the GGUF model card. Pre-experiment calibration showed temp=0.4 caused 40–60% parse failures and temp=0.2 (cloud API recommendation) produced ~100% failure on local GGUF — the two values behave identically in failure mode but were tested separately. See `research/models/sarvam-30b.md` for the full calibration record.

**Max tokens:** 4,096 for lightweight (direct output, no thinking overhead). 8,192 for reasoning (allows thinking pass + JSON response).

### 4.3 Note on Blind Conditions and E3/E4

**Blind conditions (E1/E2):** Pre-experiment smoke tests showed ~20% per-call parse error rates with the minimal blind prompt. Individual smoke runs did complete (1/3 E1 blind; 1/1 E2 blind at temp=1.0), but a subsequent calibration pass produced 0/3 before being stopped. The failure rate was too high to sustain a reliable 10-run experiment. Blind conditions were abandoned.

**E3:** Not applicable — requires blind conditions to compute C1–C5 contrasts.

**E4 (Local vs Azure):** Not applicable to V2a. V2a is entirely local (llama-server + sarvam-30b). E4 infrastructure comparison was scoped for Azure vs local phi4:14b in the original V2 design.

---

## 5. Demand Data

- **Series length:** 25 months. 24 active ordering periods. Month 25 is demand fulfilment only — no orders placed, simulation closes out.
- **Series start:** January 2025. Period 1 = Jan 2025, Period 25 = Jan 2027.
- **File:** `data/tatva_monthly_dispatches_25m.csv`
- **Demand events captured:** see calendar table in Section 8.3.
- **Calibration:** Synthetic data calibrated against real Indian PV market data (autopunditz.com CY2023–2025). See `data/calibration_notes.md` for derivation.

### Why 25 months (extended from 13)

- **Statistical power:** 24 ordering periods gives more stable OVAR estimates across runs — variance of variance converges more reliably.
- **Two festive cycles:** Captures Diwali Nov 2025 (period 11) and Diwali Nov 2026 (period 23), allowing the pattern detection score to be evaluated across two instances of the same event.
- **Richer baseline comparison:** Longer series gives heuristic baselines a fairer test across the full seasonal cycle, not just one rotation.

---

## 6. Shared Parameters — Fixed Across All Conditions

| Parameter | Value |
|---|---|
| Initial inventory | Set to `S ≈ 43,600` at all three tiers, derived at runtime as `mean + 1.65 × std(ddof=1)` from the demand CSV. This gives all policies the same opening stock position. The forecast-based Order-Up-To heuristic uses fixed safety stock `SS = S − mean_demand ≈ 5,061` on top of its smoothed demand forecast. |
| Lead time | 1 month deterministic — applies to replenishment (goods) only. See period sequence below. |
| Runs per LLM condition | 10 (context only; blind abandoned — see Section 4.3) |
| Runs per heuristic | 1 (deterministic — same output every run) |
| Order floor | Zero — negative orders clamped to 0 |
| Order ceiling | None (scientific constraint). A hallucination guard cap at 10× peak demand is implemented in simulation.py purely to prevent corrupted simulation state from a single malformed LLM output — it is not part of the experimental design. The cap fired 0 times in all canonical V2d runs. |
| Agent memory | None — each period is a stateless single-turn LLM call |
| Numeric forecast | Not provided to any agent in any condition |
| Parse error handling | JSON mode enforced at API level (attempt 1). Plain retry, all settings identical including JSON mode (attempt 2). `json-repair` on raw output (attempt 3). If all three fail for a given period, that run is marked invalid and a replacement run is triggered immediately. All retry events are logged per run. Temperature and settings never change between attempts. |
| Execution order per period | Serial: OEM → Ancillary → Component. See period sequence below. |

### 6.1 Period Sequence (explicit)

Every period t executes the following steps in order. This separates information flow (within-period) from physical replenishment (crosses periods).

**Fulfilment rule (applied identically at every tier):**
```
fulfilled_t   = min(on_hand_t, demand_t + backlog_{t-1})
shortfall_t   = max(0, demand_t + backlog_{t-1} − on_hand_t)
backlog_t     = shortfall_t                          # carries forward to t+1
on_hand_after = on_hand_t − fulfilled_t              # used for order decision
```
A stockout is recorded at a tier when `shortfall_t > 0`. Backlog accumulates across periods at every tier until cleared by future fulfilment.

1. **Demand arrival:** Retail demand for period t is drawn from the demand series and received at the OEM tier.
2. **OEM fulfilment:** Apply fulfilment rule at OEM. `demand_t` = retail demand. Backlog updated and carries forward.
3. **OEM order decision:** OEM agent observes `on_hand_after`, `backlog_t`, and `demand_t` (post-fulfilment state). `inventory_position = on_hand_after − backlog_t`. Places an order. This order is transmitted instantaneously — it becomes the Ancillary tier's `demand_t` within the same period.
4. **Ancillary fulfilment:** Apply fulfilment rule at Ancillary. `demand_t` = OEM's order from step 3. Backlog updated and carries forward.
5. **Ancillary order decision:** Ancillary agent observes its post-fulfilment state (`on_hand_after`, `backlog_t`, `demand_t`). Places an order. Transmitted instantaneously to Component.
6. **Component fulfilment:** Apply fulfilment rule at Component. `demand_t` = Ancillary's order from step 5. Backlog updated and carries forward.
7. **Component order decision:** Component agent observes its post-fulfilment state (`on_hand_after`, `backlog_t`, `demand_t`). Places a production order.
8. **Replenishment:** All orders placed in steps 3, 5, and 7 arrive as on-hand inventory at the **start of period t+1**. This is the 1-month deterministic lead time — it applies to physical stock movement only, not to order information.

> Information (order signals) propagates within a period. Goods (replenishment stock) cross a period boundary. These are distinct mechanisms.

---

## 7. Experiments Run in V2a

| # | Name | Primary question | LLM calls (V2a actual) |
|---|---|---|---|
| E1 | Lightweight: Context only | Does sarvam-30b (think=False) outperform heuristics with context? | 1 × 10 × 24 × 3 = 720 |
| E2 | Reasoning: Context only | Does sarvam-30b (think=True) outperform heuristics with context? | 1 × 10 × 24 × 3 = 720 |
| E3 | Full 2×2 Synthesis | Not run — requires blind conditions | — |
| E4 | Local vs Azure Inference | Not applicable to V2a (all-local experiment) | — |
| | | **Total (V2a)** | **1,440 LLM calls** |

*The 2×2 matrix (blind × context × lightweight × reasoning) is the original V2 design. V2a reduced this to two context-only conditions due to sarvam-30b's blind-condition instability.*

### 7.1 E3 — Five Primary Contrasts

All contrasts are defined as `blind_OVAR − context_OVAR` or `lightweight_OVAR − reasoning_OVAR` so that a **positive value means the treatment (context or reasoning) reduces OVAR**. This sign convention is fixed and applies to all hypotheses.

| ID | Contrast (defined as) | Positive value means | Interpretation |
|---|---|---|---|
| C1 | OVAR(blind_lightweight) − OVAR(context_lightweight) | Context reduces OVAR for lightweight models | Context effect at lightweight tier |
| C2 | OVAR(blind_reasoning) − OVAR(context_reasoning) | Context reduces OVAR for reasoning models | Context effect at reasoning tier |
| C3 | OVAR(blind_lightweight) − OVAR(blind_reasoning) | Reasoning reduces OVAR without context | Reasoning capability effect, no context |
| C4 | OVAR(context_lightweight) − OVAR(context_reasoning) | Reasoning reduces OVAR with context | Reasoning capability effect, with context |
| C5 | C2 − C1 | Context benefit is larger for reasoning models | Interaction: difference-in-differences |

---

## 8. Metrics

> **Critical reporting rule:** OVAR and stockout count are always reported together. Never cite one without the other. The research question is about the joint tradeoff — a result that looks good on OVAR but has catastrophic stockouts is not a good result.

### 8.1 Primary Metric — OVAR

```
OVAR = Var(orders placed by tier) / Var(demand received by tier)
```

Computed per tier, per run, over the 24 ordering periods (period 25 is fulfilment-only). Reported as mean ± std across 10 runs. Chain-average OVAR is the arithmetic mean across three tiers.

| Value | Meaning |
|---|---|
| OVAR = 1.0 | Orders mirror demand variability exactly — no amplification |
| OVAR > 1.0 | Bullwhip — orders are noisier than demand received |
| OVAR < 1.0 | Dampening — orders are smoother than demand received |

**Minimum practically relevant difference (MPRD):** |ΔOVAR| ≥ 0.5 at chain level for a finding to be claimed as practically meaningful.

### 8.2 Primary Metric — Stockout Count

Periods (of 25) where on-hand inventory cannot fulfil demand plus backlog. Recorded at each tier per the period sequence in Section 6.1. Reported per tier and as chain total. This is the service level measure — the cost of low OVAR achieved through under-ordering.

### 8.3 Secondary Metrics

| Metric | Definition |
|---|---|
| Excess inventory | Sum of (inventory − demand) in surplus periods — over-ordering waste |
| Total ordered | Sum of orders in periods 1–24 vs total demand benchmark |
| Peak overshoot | max(orders) ÷ max(demand received) — worst single-period spike |
| CV (stability) | std(OVAR) / mean(OVAR) × 100% — CV > 30% signals erratic behaviour; report std directly if mean OVAR near zero |
| Pattern score | Composite of keyword_score and elevation_score, evaluated at named event periods (see calendar table below). Mean ± std across 10 runs. **LLM conditions only**; heuristic baselines are reported as N/A because they do not produce semantic rationales. **keyword_score:** whether the `rationale` field in the agent's JSON response mentions event-relevant terms (e.g. "Diwali", "festive", "monsoon", "budget") in the period when that event occurs. **elevation_score:** whether the `order_quantity` in the event period is meaningfully higher (or lower for monsoon) than the agent's own baseline ordering level for that tier — did it act on the signal, not just mention it. Both components are required for a full pattern score. Evaluated by calendar month label from the dataset, not by hard-coded period index. |

**Demand event calendar — both cycles**

| Period | Calendar month | Event | Pattern score relevant |
|---|---|---|---|
| 1 | Jan 2025 | Makar Sankranti | Yes (elevation expected) |
| 2 | Feb 2025 | Union Budget | Yes (elevation expected) |
| 3 | Mar 2025 | FY-end | Yes (elevation expected) |
| 4–5 | Apr–May 2025 | Wedding season | Yes (elevation expected) |
| 6–8 | Jun–Aug 2025 | Monsoon dip | Yes (dip expected) |
| 10 | Oct 2025 | Navratri / Dasara | Yes (elevation expected) |
| 11 | Nov 2025 | Diwali — Cycle 1 | Yes (elevation expected) |
| 12 | Dec 2025 | Year-end sales | Yes (elevation expected) |
| 13 | Jan 2026 | Makar Sankranti | Yes (elevation expected) |
| 14 | Feb 2026 | Union Budget | Yes (elevation expected) |
| 15 | Mar 2026 | FY-end | Yes (elevation expected) |
| 16–17 | Apr–May 2026 | Wedding season | Yes (elevation expected) |
| 18–20 | Jun–Aug 2026 | Monsoon dip | Yes (dip expected) |
| 22 | Oct 2026 | Navratri / Dasara | Yes (elevation expected) |
| 23 | Nov 2026 | Diwali — Cycle 2 | Yes (elevation expected) |
| 24 | Dec 2026 | Year-end sales | Yes (elevation expected) |
| 25 | Jan 2027 | Fulfilment only | No — no orders placed |

The pattern score is computed by joining agent output to the dataset's `calendar_month` column, not by period index. Period indices are provided above for reference only and verified against `tatva_monthly_dispatches_25m.csv`.

---

## 9. Hypotheses

*Note: H2–H7 require both blind and context conditions. V2a abandoned blind conditions due to sarvam-30b's instability with minimal prompts (see Section 4.3). Only H1 is evaluable from V2a data.*

All claims require |ΔOVAR| ≥ 0.5 (MPRD) at chain level. OVAR and stockout count are always reported jointly. All contrasts follow the sign convention defined in Section 7.1: positive = treatment reduces OVAR.

**H1 (Layer 1 — Primary):** At least one LLM configuration achieves lower chain-average OVAR than the exponential smoothing heuristic (primary benchmark) with equal or fewer total stockouts across 25 periods. If H1 does not hold, H2–H7 are not interpreted. Note: failure to clear H1 is an expected outcome given the narrow scope of this task (see Scope and Generalisability note in Section 1), not a generalised finding against LLM utility in supply chains.

**H2 (C1 — Context effect, lightweight):** C1 > 0. `context_lightweight` will achieve lower chain-average OVAR than `blind_lightweight`, with no increase in total stockout count.

**H3 (C2 — Context effect, reasoning):** C2 > 0. `context_reasoning` will achieve lower chain-average OVAR than `blind_reasoning`, with no increase in total stockout count.

**H4 (C3 — Reasoning effect, no context):** C3 > 0. `blind_reasoning` will achieve lower chain-average OVAR than `blind_lightweight`, with no increase in total stockout count.

**H5 (C4 — Reasoning effect, with context):** C4 > 0. `context_reasoning` will achieve lower chain-average OVAR than `context_lightweight`, with no increase in total stockout count.

**H6 (C5 — Interaction):** C5 = C2 − C1 > 0. The OVAR reduction from context is larger for reasoning models than for lightweight models. Both C1 and C2 are defined as `blind_OVAR − context_OVAR` (positive = context helps), so C5 > 0 means reasoning models gain more from context than lightweight models do.

**H7 (E4 — Local/Azure replication):** The `context_lightweight` condition run locally (phi4:14b) produces chain-average OVAR within ±0.5 units of the Azure result (gpt-4.1-mini), indicating that local inference findings are practically equivalent for this task.

**Decision rule — Two One-Sided Tests (TOST):**
- Equivalence bounds: [−0.5, +0.5] OVAR units
- Let Δ = mean_OVAR(local) − mean_OVAR(azure), estimated across 20 runs each
- Test 1: H₀: Δ ≤ −0.5 vs H₁: Δ > −0.5
- Test 2: H₀: Δ ≥ +0.5 vs H₁: Δ < +0.5
- Equivalence is declared if and only if **both** one-sided tests reject at α = 0.05 (i.e., the 90% confidence interval for Δ falls entirely within [−0.5, +0.5])
- Bootstrap CI (10,000 resamples) used in place of t-test given non-normality of OVAR distributions is expected
- **Secondary reporting (infrastructure):** Mean call latency (ms), p95 latency, tokens/second, and retry rate are reported for both configurations. Local runs additionally report hardware context.
- Failure to declare equivalence is reported as "inconclusive" — not as evidence the models differ

---

## 10. Execution Order (V2a actual)

| Phase | What | Status |
|---|---|---|
| 0 | Pre-run setup | Complete. Dataset confirmed, S derived, baselines validated. |
| 1 | Calibration / smoke tests | Complete. Temperature, think flag, prompt behaviour characterised. Blind conditions abandoned. |
| 2 | E1 main run (context_lightweight, 10 runs) | Complete. V2a: top_p=0.95 implicit. V2d: top_p=1.0 explicit (canonical). |
| 3 | E2 main run (context_reasoning, 10 runs) | Complete. V2d canonical dataset. |
| 4 | Analysis | Complete. Results in ANALYSIS.md. Comparison in COMPARISON.md. |

---

## 11. Code Architecture

Two execution backends with a shared experiment core. The full experiment can be run on Azure OpenAI or any local OpenAI-compatible inference server by switching a single environment file. No model names, endpoints, or API keys are hardcoded anywhere in the experiment logic.

### 11.1 Structure

```
experiment/
├── .env.azure              # Azure OpenAI configuration
├── .env.local              # Local inference configuration
├── backends/
│   ├── azure_backend.py    # Azure OpenAI client
│   └── local_backend.py    # Local OpenAI-compatible client (Ollama, LM Studio, etc.)
├── agent_interface.py      # Common interface — both backends implement get_order_decision()
├── simulation.py           # Supply chain logic — calls agent_interface only, no backend knowledge
├── run_experiment.py       # Entry point — loads env, selects backend, runs all experiments
└── metrics.py              # OVAR, stockouts, pattern score — pure computation, no LLM
```

### 11.2 Environment Files

**.env.sarvam (V2a / V2d — sarvam-30b via llama-server)**
```
BACKEND=local
LOCAL_ENDPOINT=http://localhost:8080/v1
LOCAL_API_KEY=ollama
MODEL_LIGHTWEIGHT=sarvam-30b
MODEL_REASONING=sarvam-30b
MODEL_OSS_REASONING=sarvam-30b
MAX_TOKENS_LIGHTWEIGHT=4096
MAX_TOKENS_REASONING=8192
TEMP_LIGHTWEIGHT=1.0
TEMP_CONTEXT_LIGHTWEIGHT=1.0
TEMP_REASONING=1.0
TEMP_CONTEXT_REASONING=1.0
```

*For reproducible local setup, start from the committed sarvam env files in the `code/` directory, especially `.env.sarvam_v2d` for the canonical V2d configuration.*

### 11.3 Common Interface

Both backends expose a single function. The simulation layer calls only this — it has no knowledge of which backend is active or which model is running:

```python
def get_order_decision(system_prompt: str, user_prompt: str, model_tier: str) -> dict:
    """
    Returns {"order_quantity": int, "rationale": str}
    model_tier: "lightweight" | "reasoning"
    Handles JSON mode enforcement, retries, json-repair, and per-run logging internally.
    Temperature and settings never change between retry attempts.
    The rationale field is used by metrics.py for keyword_score computation.
    """
```

---

*Agentic Bullwhip Experiment — Version 2a | Industrial Mind & Code | March 2026*
