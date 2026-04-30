# V3 — Realistic Supply Chain Simulation with SimPy

**Experiment:** `Agentic_Bullwhip_Effect_V3_WorldEvents`
**Researcher:** Sid
**Date:** March 2026
**Status:** Code complete, ready to run

---

## Goal

V3 asks a more demanding version of the V2 research question:

> **Do LLM agents outperform heuristics when the supply chain is no longer ideal?**

V2 ran in a clean, controlled environment — fixed lead times, no disruptions, 100% fill rates, deterministic demand. Heuristics won decisively. V3 removes those idealisations one by one and observes whether the gap closes, reverses, or holds.

The hypothesis going in: heuristics are calibrated for stable conditions. When the world breaks — pandemics, wars, port crises — their fixed parameters become liabilities. LLMs, which carry world knowledge and can reason about novel events, may have a structural advantage in disrupted environments that they lacked in stable ones.

---

## V2 Results — The Baseline V3 Tries to Move

V2 ran 11,520 API calls across four models (gpt-4.1-mini, phi4:14b, o4-mini, gpt-oss:120b) in a clean 25-month environment with fixed lead times, 100% fill rates, and deterministic demand. All seven hypotheses were rejected. The key numbers:

| Condition | Model | Chain OVAR | Stockouts |
|---|---|---|---|
| **exp_smoothing** (best heuristic) | — | **0.54** | **5** |
| naive_passthrough | — | 1.00 | 3 |
| order_up_to | — | 1.71 | 14 |
| Best LLM (L-Blind) | phi4:14b | 4.33 ± 0.00 | 41.0 ± 0.00 |
| Best frontier LLM (L-Context) | gpt-4.1-mini | 4.47 ± 0.07 | 39.0 ± 0.83 |
| Reasoning blind | o4-mini | 4.72 ± 1.12 | 42.9 ± 3.85 |
| Reasoning context | o4-mini | 4.52 ± 0.08 | 40.1 ± 0.85 |

**The gap: 8x on both metrics simultaneously.** The best LLM condition (OVAR 4.33, 41 stockouts) was 8x worse than the best heuristic (OVAR 0.54, 5 stockouts). This is not a tradeoff — LLMs failed on both dimensions.

**Five structural findings that shape V3's design:**

1. **Context was harmful for smaller models.** Adding calendar month + persona to phi4:14b increased OVAR from 4.33 to 6.35 (+47%) with standard deviation exploding from 0.00 to 2.53. For gpt-4.1-mini the effect was marginal (4.70 to 4.47). V3 adds an even richer context signal (unstructured news headline) — will this destabilise smaller models further, or does the disruption-relevance of the signal change the dynamic?

2. **Reasoning models provided no advantage.** o4-mini generated 1.08M reasoning tokens but achieved the same OVAR as gpt-4.1-mini (4.52 vs 4.47). Additional computational cost bought nothing. V3 tests whether this changes when reasoning about disruption events requires genuine inference (pandemic reopening implies supply lag implies rebuild strategy).

3. **Pattern scores were uniformly low (0.20-0.23).** Agents could articulate seasonal events ("Diwali approaching") but did not order accordingly. V3's unstructured condition provides explicit disruption signals — a stronger test of whether agents can translate knowledge into action.

4. **Statelessness was the core structural limitation.** Each period was a fresh decision with no memory of prior orders or outcomes. The agent could not learn that high backlog resulted from its own prior over-ordering. V3 retains this constraint (by design — it isolates the agent's single-period reasoning quality).

5. **Local and frontier models were conditionally equivalent** in reasoning conditions (delta OVAR = 0.00-0.20) but diverged in lightweight context (delta = 1.88). V3 continues testing both backends.

---

## What Changes from V2

| Dimension | V2 | V3 |
|---|---|---|
| Simulation engine | Period-loop | SimPy discrete-event |
| Simulation length | 25 months | **36 months (3 years)** |
| Lead times | Fixed: 1 period | **Stochastic: LogNormal(μ=1, σ=0.3), disruption-aware** |
| Fill rates | 100% always | **Stochastic: Beta(9,1) baseline, disruption-modulated** |
| Demand | Fixed seasonal series | **Seasonal baseline + Gaussian noise + event shocks** |
| World events | None | **Pandemic, geopolitical conflict, port disruption** |
| Context signal | Calendar month + persona | **+ optional unstructured event signal (news headline)** |
| Capacity constraints | None | **Per-tier production cap** |

---

## Why SimPy

SimPy models time as a continuous event queue rather than fixed period steps. This matters for V3 because:

- **Variable lead times** are natural — a replenishment subprocess yields `env.timeout(sampled_lead_time)`. An order placed at t=5 with lead_time=2.3 arrives at t=7.3.
- **Disruption events** fire at arbitrary points in the timeline without restructuring the simulation loop.
- **Capacity constraints** model as SimPy Resources — a tier requests capacity units before producing.
- **Partial deliveries** handled in the `_deliver()` subprocess before inventory is credited.

Libraries reviewed: InventOpt (hardcoded policy, not suitable), supplychainpy (analysis-focused, not suitable), SimPy directly — best choice.

---

## Demand Series — 36 Months

### Baseline Seasonal Pattern

Extend the V2 Tatva Motors Vecta series from 25 to 36 months (Jan 2025 — Dec 2027), applying +5% YoY growth each year. The same Indian automotive seasonal structure applies: FY-end peaks in March, monsoon trough June–August, Diwali peak in November.

### Demand Noise

Real retail demand is never a clean curve. Add multiplicative Gaussian noise on top of the seasonal baseline each run:

```python
noise_factor = np.random.normal(loc=1.0, scale=0.08)  # CV = 8%
demand_t = round(baseline_t * noise_factor)
```

This means each of the 20 runs per condition sees a genuinely different demand realisation — the 20 runs become a proper Monte Carlo sample rather than 20 identical runs.

### World Event Demand Shocks

Layered on top of the noisy seasonal baseline. Implemented as multiplicative demand multipliers applied to specific period windows.

---

## World Events

Three event types, each parameterised to reflect real historical magnitudes.

### Event 1 — Pandemic (modelled on COVID-19, 2020–2022)

**What happened in reality:** Initial demand collapse as consumers froze spending. Simultaneous supply collapse as factories shut and logistics networks broke down. Demand then surged as stimulus money arrived and pent-up buying released — but supply couldn't keep up, creating 6–18 month shortages.

**In simulation (periods 7–12, Jul–Dec 2025):**

| Phase | Periods | Demand multiplier | Fill rate | Lead time multiplier |
|---|---|---|---|---|
| Shock — demand collapse | 7–9 | 0.55 | 0.40 | 2.5× |
| Reopening — demand surge | 10–11 | 1.35 | 0.55 | 2.0× |
| Recovery lag | 12 | 1.10 | 0.75 | 1.3× |

**What this tests:** During the shock, blind heuristics will keep ordering at near-normal levels (their smoothed forecast reacts slowly). During the surge, they risk under-ordering because their forecast is anchored to the collapse period. LLMs with world knowledge may recognise "pandemic reopening" as a signal to build stock aggressively or cut orders — if they do so correctly, they gain an advantage.

**Unstructured news headline shown to agents:**
- Shock: *"Global pandemic declared. Factory closures widespread. Logistics severely disrupted. Consumer demand has collapsed."*
- Surge: *"Economies reopening. Consumer demand surging strongly. Supply chains remain constrained — factories not yet at full capacity."*
- Recovery: *"Pandemic recovery underway. Demand elevated. Supply chains gradually normalising — lead times improving."*

### Event 2 — Geopolitical Conflict / War (modelled on Russia-Ukraine 2022 + broader supply disruption)

**What happened in reality:** Commodity supply shocks (palladium, neon gas, rare earth metals). Logistics rerouting added weeks to lead times. Energy cost spikes reduced production output. Demand was relatively less affected but production capacity was throttled.

**In simulation (periods 19–21, Jul–Sep 2026):**

| Phase | Periods | Demand multiplier | Fill rate | Lead time multiplier |
|---|---|---|---|---|
| Supply shock onset | 19 | 0.95 | 0.45 | 2.0× |
| Sustained disruption | 20–21 | 0.90 | 0.50 | 1.8× |

**What this tests:** Demand barely changes but supply collapses. Heuristics that chase demand will keep ordering heavily — and receive far less than ordered, building massive backlog. A context agent told the month and year may draw on knowledge of the geopolitical situation, though it is never told directly. An unstructured context agent receiving a news headline will have explicit signal.

**Unstructured news headline shown to agents:**
- Onset: *"Major geopolitical conflict disrupting raw material supply. Semiconductor and rare earth shortages reported. Logistics rerouting adds weeks."*
- Sustained: *"Geopolitical conflict ongoing. Component supply severely constrained. Energy costs elevated. Production capacity curtailed across the sector."*

### Event 3 — Port / Logistics Disruption (modelled on Suez Canal blockage, LA port strikes)

**What happened in reality:** Sudden, acute disruption to shipping routes. Lead times spiked by 2–6 weeks. Demand unaffected. Fill rates drop temporarily but recover faster than pandemic or war scenarios.

**In simulation (periods 28–30, Apr–Jun 2027):**

| Phase | Periods | Demand multiplier | Fill rate | Lead time multiplier |
|---|---|---|---|---|
| Acute disruption | 28 | 1.00 | 0.65 | 3.0× |
| Tail — backlog clearing | 29–30 | 1.00 | 0.70 | 2.0× |

**What this tests:** A short, sharp disruption. Heuristics have no mechanism to anticipate it — they react after it happens. LLMs with context or unstructured news may build buffer stock ahead of a known logistics disruption window.

**Unstructured news headline shown to agents:**
- Acute: *"Major port strike halting shipments. Lead times tripling. Demand unaffected — supply side only. Build buffer stock if possible."*
- Tail: *"Port dispute partially resolved. Backlog clearing. Lead times remain elevated — full normalisation expected next month."*

---

## Stochastic Parameters

### Lead Time

Each replenishment subprocess draws a lead time from a LogNormal distribution, then applies the disruption multiplier for the current period:

```python
base_lead_time = max(1, round(np.random.lognormal(mean=0.0, sigma=0.25)))
# mean ≈ 1.03 periods, most draws = 1, occasional 2 or 3

disruption_multiplier = world_events.get_lead_time_multiplier(current_period)
actual_lead_time = round(base_lead_time * disruption_multiplier)
```

Normal operations: ~90% of orders arrive in 1 period, ~10% in 2. During pandemic shock: mean ≈ 2.5 periods, some orders take 4–5.

### Fill Rate

Each `_deliver()` subprocess draws a fill rate from a Beta distribution, then applies the disruption fill rate floor:

```python
base_fill = np.random.beta(a=9, b=1)    # mean=0.90, mostly 0.85–0.98
disruption_fill = world_events.get_fill_rate(current_period)
fill_rate = min(base_fill, disruption_fill)  # disruption caps the draw
actual_delivery = int(ordered_quantity * fill_rate)
```

Normal operations: mean 90% fill, occasionally 85%. During pandemic shock: fill rate hard-capped at 40%.

### Capacity Constraints

Each tier has a maximum units-per-period production capacity. Orders above capacity are partially fulfilled from stock and partially backordered at the supplier:

```python
CAPACITY = {
    "OEM":       60_000,   # units/period
    "Ancillary": 65_000,
    "Component": 70_000,
}
```

Calibrated so that capacity is not binding in normal operations but becomes binding during demand surges (pandemic reopening, Diwali peaks).

---

## Architecture

### SimPy Process Design

```
simpy.Environment()
│
├── WorldEvents               # fires disruption state changes at scheduled periods
├── TierProcess("OEM")        # simpy.Process — receive → fulfil → order → deliver
├── TierProcess("Ancillary")  # simpy.Process
└── TierProcess("Component")  # simpy.Process
```

Each `TierProcess` is a generator yielding `env.timeout(1)` per period.
Each order triggers a `_deliver()` subprocess: `env.process(self._deliver(qty, lead_time))`.

### Key Classes

```python
class WorldEvents:
    """
    Holds the event schedule. Returns disruption multipliers for any period.
    Configurable — events can be enabled/disabled, moved, or parameterised
    via the experiment config without touching simulation code.
    """
    def get_lead_time_multiplier(self, period: int) -> float: ...
    def get_fill_rate_cap(self, period: int) -> float: ...
    def get_demand_multiplier(self, period: int) -> float: ...
    def get_event_label(self, period: int) -> str: ...   # for prompts + records

class InventoryState:
    """Tracks on_hand, backlog, pipeline (orders in transit)."""

class TierProcess:
    """
    SimPy process for one tier.
    Each period:
      1. receive_replenishment()   — credit arrived pipeline orders
      2. fulfil()                  — serve demand + backlog, record stockout
      3. order()                   — LLM or heuristic decides quantity
      4. _deliver(qty, lead_time)  — subprocess: draws fill rate, waits, credits inventory
    """

class SupplyChainSim:
    """
    Top-level. Owns environment, WorldEvents, all TierProcesses, demand series.
    Runs env.run(until=36).
    Returns records in same schema as V2 — compatible with metrics.py unchanged.
    """
```

### LLM Agent Hook

Order decision fires inside `TierProcess.order()`. The prompt now includes the current world event label when unstructured context is enabled:

```python
def order(self, period, demand, on_hand, backlog, event_label=None):
    if self.policy == "llm":
        result = get_order_decision(
            ...,
            event_signal=event_label if self.context_mode == "unstructured" else None
        )
```

`agent_interface.py` gains one optional field in the user prompt — `event_signal`. All other fields unchanged.

---

## Experimental Conditions

V3 expands the 2×2 V2 matrix to a 2×3:

| | Blind | Context (calendar + persona) | Unstructured (+ news headline) |
|---|---|---|---|
| **Lightweight** | blind_lightweight | context_lightweight | unstructured_lightweight |
| **Reasoning** | blind_reasoning | context_reasoning | unstructured_reasoning |

**Unstructured condition — what the agent receives:**

During an active world event, the user prompt includes one additional line:

```
Current conditions: [Pandemic — global logistics severely disrupted, factory closures widespread]
```

During normal periods, this line is absent. The agent is never told what to do with this information — it must reason about it and decide whether to order more, less, or normally.

---

## Models

| Backend | Condition | Model | Env var | Temperature |
|---|---|---|---|---|
| **Local** | Lightweight (E1) | `nemotron-cascade-2:30b` | `MODEL_LIGHTWEIGHT` | 0.4 |
| **Local** | Reasoning (E2) | `gpt-oss:120b` | `MODEL_REASONING` | 0.0 (blind) / 0.3 (context, unstructured) |
| **Azure** | Lightweight (E1) | `gpt-5-nano` | `MODEL_LIGHTWEIGHT` | 0.4 |
| **Azure** | Reasoning (E2) | `o4-mini` | `MODEL_REASONING` | 1.0 (Azure-enforced) |

**Local inference:** Ollama serving both models. Nemotron Cascade 2 30B replaces phi4:14b from V2 — larger parameter count and hybrid SSM/transformer architecture for stronger seasonal pattern recognition at reasonable inference cost.

**Azure note:** `gpt-5-nano` is deployed at `GlobalStandard` with 1 request/60s default capacity. **Scale up capacity to ≥ 100 tokens-per-minute before running production conditions** — at 1 req/60s the full Azure run would take ~9 days. API key required in `.env.azure`.

---

## Simulation Parameters

| Parameter | Value | Notes |
|---|---|---|
| Periods | **36** | 3 years: Jan 2025 — Dec 2027 |
| Lead time (normal) | LogNormal(μ=0, σ=0.25) | Mean ≈ 1 period; occasional 2–3 |
| Lead time (disrupted) | Base × event multiplier | Up to 3× during acute events |
| Fill rate (normal) | Beta(9, 1) | Mean ≈ 90%, min ~80% |
| Fill rate (disrupted) | Capped by event schedule | Down to 40% during pandemic shock |
| Demand noise | Gaussian, CV=8% | Applied multiplicatively each period |
| Demand shocks | Per event schedule | Pandemic, conflict, port disruption |
| Initial inventory | S derived from 36m demand | Same formula as V2 |
| Capacity constraints | Per tier (see above) | Binding only during surges |
| Runs per LLM condition | 20 | Each run = different noise realisation |
| Heuristic runs | 100 | Monte Carlo over noise; report mean ± std |

**Note on heuristic runs:** In V2, heuristics ran once (deterministic). In V3, demand noise means each run is different — heuristics should run 100 times to characterise their distribution under uncertainty, not once.

---

## Demand Data

New CSV required: `tatva_monthly_dispatches_36m_annotated.csv`

Extend the V2 series programmatically:
- Apply +5% YoY growth for 2026 (already done in V2) and +5% again for 2027
- Add world event demand multipliers to the annotated columns
- Add noise in the simulation at runtime (not baked into CSV — preserves clean baseline)

Script: `code/generate_demand_36m.py`

---

## Files to Create

```
experiments/Agentic_Bullwhip_Effect_V3_WorldEvents/
├── DESIGN.md                       ← this file
└── code/
    ├── generate_demand_36m.py      ← extend V2 CSV to 36 months
    ├── world_events.py             ← WorldEvents class + event schedule
    ├── simulation.py               ← SimPy-based simulation
    ├── agent_interface.py          ← V2 copy + event_signal field
    ├── metrics.py                  ← V2 copy, unchanged
    ├── run_experiment.py           ← updated for 36 periods + new conditions
    ├── env.azure.template          ← V2 copy + unstructured condition temps
    └── env.local.template          ← V2 copy + unstructured condition temps
```

---

## Implementation Plan

### Step 1 — Demand data
- Run `generate_demand_36m.py` to produce the 36-month annotated CSV
- Validate: same seasonal structure, +5% YoY 2026→2027, correct event labels at disruption periods

### Step 2 — WorldEvents module
- Implement `WorldEvents` with configurable event schedule (dict of period → multipliers)
- Unit test: verify correct multipliers returned at boundary periods

### Step 3 — SimPy scaffold
- `SupplyChainSim` with `simpy.Environment()` and `WorldEvents`
- Wire demand series and event schedule as shared resources

### Step 4 — TierProcess
- Implement receive → fulfil → order → `_deliver()` subprocess
- `_deliver()` draws fill rate, waits `lead_time` periods, credits inventory
- Record `actual_delivered`, `fill_rate_drawn`, `lead_time_drawn` in output schema

### Step 5 — LLM agent hook
- Extend `agent_interface.py` user prompt with optional `event_signal`
- Add `unstructured` condition to experiment spec

### Step 6 — Parity validation
- Run V3 with world events disabled, noise disabled, fixed lead time = 1
- OVAR and stockouts must match V2 exactly (deterministic parity check)

### Step 7 — Run experiment
- 20 runs × 6 conditions × 3 tiers × 36 periods = 12,960 LLM calls per backend
- Estimate: ~14h Azure, ~12h local

---

## Alpha Parameter

Inherited from V2 sweep: **α = 0.30** for both exp_smoothing and order_up_to.
Empirically defended on the V2 deterministic series. Retained in V3 for continuity.
With stochastic demand, α sensitivity becomes a secondary analysis question — not a design variable.

---

## V2 Assumptions Addressed

| V2 Assumption | V3 Status |
|---|---|
| Fixed 1-month lead time | **Addressed** — LogNormal lead times, disruption multipliers |
| No supplier disruptions | **Addressed** — pandemic, conflict, port events modulate fill rate |
| All tiers run same policy | **Partially** — mixed deployment (LLM at OEM only) deferred to V4 |
| Single product, fixed topology | Not addressed — out of scope for V3 |
| No unstructured context | **Addressed** — new unstructured condition with news headline |
| Deterministic demand | **Addressed** — Gaussian noise, CV=8%, per-run realisation |

---

## What V3 Does NOT Change

- Core research question (heuristics vs LLMs)
- Output schema (same columns — metrics.py works unchanged)
- Agent prompt structure (same JSON response format)
- Experiment infrastructure (tmux, nohup, checkpointing, backoff)
- Alpha parameter (0.30, empirically carried forward)
