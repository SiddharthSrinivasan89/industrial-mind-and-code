# V4 WorldEvents Design — Intent Classifier in a Disrupted Supply Chain

**Experiment:** `Agentic_Bullwhip_Effect_V4_WorldEvents`
**Version:** 1.0
**Date:** April 2026
**Status:** Code-complete. Ready for smoke test then production runs.
**Lineage:** V1 → V2 → V2a → V3b (HybridArch) → V4 (IntentClassifier) → **V4_WorldEvents**

---

## 1. Research Question

V4 (IntentClassifier, 25-month no-events) established that replacing a continuous
float output with a discrete intent classification interface is a tractable design.
V3_WorldEvents established that world events (pandemic, geopolitical conflict, port
disruption) stress-test LLM ordering in ways seasonal variation alone cannot.

This experiment combines both: it asks whether an intent classifier can navigate a
36-month supply chain environment containing both Indian automotive seasonal demand
cycles and three real-world disruption types.

**Primary question:** Does intent classification produce lower order variance
amplification (OVAR) than heuristic baselines when world events create sharp
demand and supply shocks — conditions where the `STRONG_DECREASE` and
`STRONG_INCREASE` classes should be most useful?

**Secondary questions:**
1. Does the `unstructured` condition (explicit news-headline signal during events)
   improve intent accuracy at disruption-period boundaries compared to `context`
   (seasonal calendar only) or `blind` (no context)?
2. Do world event periods produce systematically different intent accuracy and
   entropy than normal seasonal periods?
3. Does intent compliance remain near-perfect (≥ 0.99) under disruption conditions
   where stronger emotional language in news headlines could destabilise JSON output?

---

## 2. Design Lineage

| Version | Architecture | Key finding |
|---|---|---|
| V2 | LLM orders directly, 25-month, no disruptions | LLM amplifies order variance well above exp_smoothing |
| V3b HybridArch | LLM outputs float multiplier × OUT formula, 25-month, no disruptions | Float output unreliable; context made things worse |
| V4 IntentClassifier | LLM classifies 5-label intent × lookup × OUT formula, 25-month, no disruptions | Design-complete; awaiting production runs |
| **V4_WorldEvents** | Intent classifier × 36-month × pandemic + conflict + port disruption | *This experiment* |

V4_WorldEvents deliberately introduces world events into the intent classifier
architecture. The disruption periods create unambiguous ground-truth intents
(pandemic_shock → STRONG_DECREASE; pandemic_surge → STRONG_INCREASE) that are
externally testable against model classifications.

---

## 3. Architecture

### 3.1 Three-layer execution (per period, per tier)

```
┌───────────────────────────────────────────────────────────┐
│  Layer 1 — Classification (LLM)                           │
│  Input:  state variables + optional calendar/event signal │
│  Output: {"intent": "<CLASS>", "rationale": "..."}        │
│  Task:   choose one of 5 categorical labels               │
└──────────────────────┬────────────────────────────────────┘
                       │ intent label (string)
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Layer 2 — Lookup (deterministic)                         │
│  Input:  intent label                                     │
│  Output: safety stock multiplier (float)                  │
│  Source: INTENT_MULTIPLIER_MAP (fixed, code-defined)      │
└──────────────────────┬────────────────────────────────────┘
                       │ multiplier_t
                       ▼
┌───────────────────────────────────────────────────────────┐
│  Layer 3 — Execution (deterministic, OUT-style)           │
│  F_t   = 0.30 × D_t + 0.70 × F_{t-1}                    │
│  SS_t  = base_SS × multiplier_t                          │
│  target = round(F_t) + SS_t                               │
│  order  = max(0, target − inventory_position_t)           │
└───────────────────────────────────────────────────────────┘
```

### 3.2 Intent classes and multiplier lookup

| Intent class | Demand signal | Multiplier | Prototypical trigger |
|---|---|---|---|
| `STRONG_INCREASE` | > +10% above mean | **1.30** | FY-end, Diwali, pandemic surge |
| `MODERATE_INCREASE` | +3% to +10% | **1.15** | Navratri, pre-festive build |
| `NEUTRAL` | −5% to +3% | **1.00** | Transitional months, no event |
| `MODERATE_DECREASE` | −5% to −10% | **0.90** | Early/late monsoon, conflict demand dip |
| `STRONG_DECREASE` | < −10% | **0.80** | Peak monsoon, pandemic demand collapse |

Multipliers are initial design values, not calibrated from this experiment's runs.
Cross-experiment calibration (using V3b float medians) deferred to post-analysis.

**Fallback:** If the LLM fails all 3 parse attempts, `NEUTRAL` is applied and
`intent_fallback=True` is recorded. This preserves the run rather than discarding it.

### 3.3 World events and their expected intent mappings

| Event | Periods | Expected ground-truth intent |
|---|---|---|
| Pandemic shock | 7–9 | STRONG_DECREASE (demand ×0.55 → −45% below mean) |
| Pandemic surge | 10–11 | STRONG_INCREASE (demand ×1.35 → +27–35% above mean) |
| Pandemic recovery | 12 | MODERATE_INCREASE (demand ×1.10 → +10% above mean) |
| Conflict onset | 19 | MODERATE_DECREASE (demand ×0.95, supply severely restricted) |
| Conflict sustained | 20–21 | MODERATE_DECREASE (demand ×0.90) |
| Port disruption acute | 28 | NEUTRAL (demand unaffected; lead time 3×, fill 65%) |
| Port disruption tail | 29–30 | NEUTRAL (demand unaffected; lead time 2×, fill 70%) |

Note: port disruption does NOT affect demand (multiplier = 1.00). The intent
classifier should choose NEUTRAL for demand buffer — the supply-side disruption
(lead time spike, fill rate drop) is handled by the simulation engine, not the
LLM. The `unstructured` condition includes port disruption news headlines, so
models may incorrectly over-order. This is a key hypothesis test.

---

## 4. Supply Chain Structure

Identical to V3_WorldEvents for cross-experiment comparability.

| Parameter | Value |
|---|---|
| Tiers | 3 serial: OEM → Ancillary → Component |
| Horizon | 36 months (periods 1–36, Jan 2025 – Dec 2027) |
| Demand data | `tatva_monthly_dispatches_36m.csv` (SHA-256 stamped at runtime) |
| Demand noise | Multiplicative Gaussian, CV=8%, applied at OEM |
| Lead time | LogNormal(µ=0, σ=0.25) × world event multiplier; minimum 1 period |
| Fill rate | Beta(9,1), capped at world event fill_rate_cap |
| Initial inventory (S) | Derived: mean + 1.65σ of demand series |
| Base safety stock | S − mean_demand |
| Capacity constraint | OEM: 60,000; Ancillary: 65,000; Component: 70,000 units/period |

---

## 5. Experimental Conditions

| Experiment | Label | Policy | Context given to LLM | Model |
|---|---|---|---|---|
| baselines | `naive_passthrough` | naive | — | — |
| baselines | `exp_smoothing` | exp_smoothing | — | — |
| baselines | `order_up_to` | order_up_to | — | — |
| E1_IC | `ic_blind_lightweight` | intent | state only | lightweight |
| E1_IC | `ic_context_lightweight` | intent | state + calendar + persona | lightweight |
| E1_IC | `ic_unstructured_lightweight` | intent | state + calendar + persona + event signal | lightweight |
| E2_IC | `ic_blind_reasoning` | intent | state only | reasoning |
| E2_IC | `ic_context_reasoning` | intent | state + calendar + persona | reasoning |
| E2_IC | `ic_unstructured_reasoning` | intent | state + calendar + persona + event signal | reasoning |
| E3_IC | `ic_blind_no_events_lw` | intent | state only | lightweight (no events) |
| E3_IC | `ic_context_no_events_lw` | intent | state + calendar + persona | lightweight (no events) |

**Runs:** 100 per heuristic baseline; 20 per LLM condition.
**E3_IC** is the ablation: same intent classifier with world events disabled.
Cross-comparing E1_IC vs E3_IC isolates the world events contribution to OVAR.

---

## 6. Prompt Conditions

### Blind
State variables only: demand_received, on_hand, backlog, inventory_position, base_ss.
No calendar month. No world event signal. Baseline for the intent interface.

### Context
Adds: calendar month (e.g., "Jul 2026") and tier persona (company name, product, role).
Enables the LLM to apply cultural knowledge of Indian automotive seasonal patterns.
Does NOT include world event signals — the model must infer from demand movement alone.

### Unstructured
Adds: world event news headline during disruption periods (same signals as V3_WorldEvents).
Example during pandemic_shock: "Global pandemic declared. Factory closures widespread.
Logistics severely disrupted. Consumer demand has collapsed."
Tests whether explicit disruption language causes over-reaction (panic classification)
or appropriate intent selection.

---

## 7. Hypotheses

| H | Comparison | Threshold | Question |
|---|---|---|---|
| **H1** | Best E1_IC OVAR vs exp_smoothing OVAR | Best IC OVAR ≤ exp_smoothing (both within E1_IC) | Can intent classification match or beat the formula benchmark? |
| **H2** | IC-Unstructured vs IC-Context OVAR | IC-Unstructured OVAR ≤ IC-Context OVAR | Does world event signal reduce OVAR? |
| **H3** | IC-Unstructured intent accuracy (disruption periods) vs IC-Context | Direction accuracy Δ ≥ 0.10 | Does news headline improve classification at event boundaries? |
| **H4** | Intent compliance rate | ≥ 0.99 across all conditions | Does disruption language break JSON output compliance? |
| **H5** | E1_IC OVAR vs E3_IC OVAR (matched conditions) | E1_IC OVAR ≠ E3_IC OVAR (either direction) | Does adding world events materially change OVAR? |

---

## 8. Metrics

### Primary
- **Chain OVAR:** Var(orders) / Var(demand), mean across 3 tiers, arithmetic mean
  across runs. Lower is better. Baselines establish floor.
- **Chain stockout count:** Periods where on_hand < demand + backlog, chain total.

### Intent-specific (new in V4_WorldEvents)
- **Intent compliance rate:** Fraction of intent decisions that returned a valid class
  (not fallback). Target ≥ 0.99.
- **Intent accuracy (full):** Fraction where chosen class exactly matches ground-truth
  deviation-band label, evaluated over non-neutral OEM periods.
- **Intent accuracy (direction):** Fraction where chosen class direction matches
  ground-truth direction (increase/neutral/decrease), regardless of intensity.
- **Intent entropy:** Shannon entropy of intent class distribution per run at OEM.
  High entropy → model discriminates. Low entropy → collapse to one class.

### Supporting
- Pattern score (semantic keyword + elevation score on rationale text)
- Excess inventory, peak overshoot

---

## 9. Code Architecture

```
code/
├── agent_interface.py     # Intent prompts, INTENT_MULTIPLIER_MAP, get_intent_class()
├── simulation.py          # SimPy engine: policy_intent_hybrid() + V3 heuristics
├── world_events.py        # WorldEvents — unchanged from V3_WorldEvents
├── metrics.py             # V3 metrics + intent compliance/accuracy/entropy
├── run_experiment.py      # EXPERIMENTS registry: baselines, E1_IC, E2_IC, E3_IC
├── generate_demand_36m.py # 36-month demand series generator — unchanged from V3
├── data/
│   └── synthetic/
│       └── tatva_monthly_dispatches_36m.csv
└── backends/
    ├── azure_backend.py   # get_order_decision() + get_intent_decision()
    ├── local_backend.py   # get_order_decision() + get_intent_decision()
    ├── dry_run_backend.py # get_order_decision() + get_intent_decision() (NEUTRAL)
    └── resilience.py      # call_with_backoff() — unchanged from V3_WorldEvents
```

**Key additions vs V3_WorldEvents:**
- `get_intent_class()` in agent_interface — routes to `backend.get_intent_decision()`
- `policy_intent_hybrid()` in simulation — intent → lookup → OUT formula
- `compute_intent_*` functions in metrics
- `E1_IC`, `E2_IC`, `E3_IC` experiments in run_experiment

**Key additions vs V4_IntentClassifier:**
- 36-month series (not 25-month)
- Stochastic lead times and fill rates (SimPy, not deterministic)
- WorldEvents integration (pandemic / conflict / port disruption)
- Unstructured condition (event news headlines in user prompt)

---

## 10. Execution Plan

### Setup

```bash
cd experiments/agentic-bullwhip-v4-world-events/code/

# Generate the synthetic demand series (already shipped under data/synthetic/)
python generate_demand_36m.py
```

### Phase 1: Dry-run validation (zero API cost)

```bash
DRY_RUN=1 python run_experiment.py --experiments baselines E1_IC --runs 2 --env .env
```

Expected: records have `intent_class`, `intent_multiplier`, `intent_fallback` columns;
`intent_compliance_rate = 1.0` (dry_run always returns NEUTRAL).

### Phase 2: Smoke test (real LLM, 2 runs)

```bash
# Local
BACKEND=local python run_experiment.py --experiments E1_IC --runs 2 --env .env.local

# Azure
BACKEND=azure python run_experiment.py --experiments E1_IC --runs 2 --env .env.azure
```

Verify: `intent_class` varies across periods; `compliance_rate ≥ 0.99`; rationale non-blank;
OVAR values are finite and positive.

### Phase 3: Production runs (in tmux with nohup)

```bash
# Baselines (heuristic, fast)
tmux new-session -s v4we_baselines
nohup python run_experiment.py --experiments baselines --env .env \
    > ../logs/v4we_baselines.log 2>&1 &

# Local (nemotron-super-3:120b or similar)
tmux new-session -s v4we_local
nohup python run_experiment.py \
    --experiments E1_IC E2_IC E3_IC --runs 20 --env .env.local \
    > ../logs/v4we_local.log 2>&1 &

# Azure (gpt-4.1-mini + o4-mini)
tmux new-session -s v4we_azure
nohup python run_experiment.py \
    --experiments E1_IC E2_IC E3_IC --runs 20 --env .env.azure \
    > ../logs/v4we_azure.log 2>&1 &
```

### Phase 4: Analysis

Verify using `summary.json` outputs:
1. Chain OVAR per condition vs heuristic baselines
2. Intent accuracy at world-event periods (pandemic_shock, pandemic_surge, conflict)
3. Intent compliance rate across all conditions
4. E1_IC vs E3_IC OVAR comparison (world events effect on intent classifier)

---

## 11. Env File Template

```bash
# .env.local
BACKEND=local
LOCAL_ENDPOINT=http://localhost:11434/v1
LOCAL_API_KEY=ollama
MODEL_LIGHTWEIGHT=nemotron-super-49b-instruct:latest   # or your local model
MODEL_REASONING=nemotron-super-49b-instruct:latest
MAX_TOKENS_LIGHTWEIGHT=256
MAX_TOKENS_REASONING=512
TEMP_LIGHTWEIGHT=0.4
TEMP_CONTEXT_LIGHTWEIGHT=0.4
TEMP_UNSTRUCTURED_LIGHTWEIGHT=0.4
TEMP_REASONING=0.0
TEMP_CONTEXT_REASONING=0.3
TEMP_UNSTRUCTURED_REASONING=0.3

# .env.azure
BACKEND=azure
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_VERSION=2025-01-01-preview
MODEL_LIGHTWEIGHT=gpt-4.1-mini
MODEL_REASONING=o4-mini
MAX_TOKENS_LIGHTWEIGHT=256
MAX_TOKENS_REASONING=512
```

---

## 12. Limitations

1. **Same demand series as V3b/V4:** Results are specific to the Tatva Motors
   synthetic 36-month series. Generalizability to other markets is not established.
2. **Intent classes calibrated to seasonal, not event, magnitudes:** The multiplier
   lookup was designed for seasonal variation (±10–15%). During pandemic shock
   (demand −45%), `STRONG_DECREASE` maps to ×0.80, which may be insufficient.
3. **No cross-tier communication of world event signals:** The `unstructured` event
   signal is given to each tier independently, not propagated upstream. In reality,
   all tiers would hear the same news.
4. **Fallback to NEUTRAL masks parse failure patterns:** If certain events
   systematically trigger parse failures, the fallback inflates NEUTRAL counts and
   understates the event's true impact on intent classification reliability.
5. **20 runs:** Sufficient for OVAR comparisons at MPRD ≥ 0.5 but underpowered
   for detecting smaller effects, especially in the 3-period event windows.

---

## 13. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-04-19 | Siddharth Srinivasan | Initial code-complete version |
