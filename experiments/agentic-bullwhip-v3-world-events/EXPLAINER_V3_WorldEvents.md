# V3 Experiment — Complete Explainer

**Researcher:** Sid
**Date:** March 2026
**Status:** Code complete, ready to run

---

## What This Is

This is Version 3 of the Agentic Bullwhip Effect experiment. The core question the experiment tries to answer is:

> **Can LLM agents manage supply chain ordering better than mathematical heuristics — and does that answer change when the supply chain stops behaving nicely?**

Version 2 ran the same experiment in a clean, controlled environment (fixed lead times, no disruptions, 100% fill rates, deterministic demand) and found that mathematical heuristics won decisively — the best heuristic (exponential smoothing, OVAR 0.54, 5 stockouts) outperformed the best LLM (phi4:14b blind, OVAR 4.33, 41 stockouts) by 8x on both variance amplification and stockout count. V3 removes those idealisations one by one to see whether the LLM advantage emerges under realistic, disrupted conditions.

---

## Background — What Is the Bullwhip Effect?

In a supply chain, demand at the retail level is the ground truth. A car manufacturer (OEM) orders from a parts supplier (Ancillary), who orders components from a manufacturer (Component). In practice, each tier tends to over-order — they buffer against uncertainty, panic when supply tightens, and over-correct when demand spikes. By the time you reach the Component tier, tiny wiggles in retail demand have become enormous swings in production orders. This is the **bullwhip effect**.

The primary metric measuring it is **OVAR** (Order Variance Ratio):

```
OVAR = Var(orders placed) / Var(demand received)
```

- OVAR = 1.0: the tier passes demand through unchanged (neutral)
- OVAR > 1.0: the tier amplifies variance (bullwhip)
- OVAR < 1.0: the tier dampens variance (desirable)

Heuristics like exponential smoothing were designed to reduce OVAR. The question is whether LLMs — which carry world knowledge and can reason about context — can do better, especially when real-world disruptions occur.

---

## Three-Tier Supply Chain

The simulation models an Indian automotive supply chain:

```
Retail demand → OEM (Tatva Motors, Vecta Lighting Assembly)
                  ↓ orders
             Ancillary (lighting manufacturer)
                  ↓ orders
             Component (LED component manufacturer)
```

Each tier receives demand from the tier below it, decides how many units to order from its upstream supplier, and passes that order up. All three tiers can run the same policy (LLM or heuristic) simultaneously — there is no mixed deployment in V3.

---

## What V3 Changes from V2

| Dimension | V2 | V3 |
|---|---|---|
| Simulation length | 25 months | **36 months (3 years)** |
| Simulation engine | Period loop | **SimPy discrete-event** |
| Lead times | Fixed: 1 period | **Stochastic: LogNormal, disruption-aware** |
| Fill rates | 100% always | **Stochastic: Beta distribution, capped by events** |
| Demand | Fixed seasonal series | **Seasonal + Gaussian noise + event shocks** |
| World events | None | **Pandemic, geopolitical conflict, port disruption** |
| Context signal | Calendar month + persona | **+ optional unstructured news headline** |
| Heuristic runs | 1 (deterministic) | **100 Monte Carlo runs** |

The switch to SimPy (a Python discrete-event simulation library) is the core structural change. It makes stochastic lead times natural: an order placed at simulation time t=5 with a drawn lead time of 2.3 arrives at t=7.3. There is no special-casing or workaround needed — it is just how SimPy works.

---

## V2 Results — What We Know Going In

V2 tested LLM ordering agents across four models (gpt-4.1-mini, phi4:14b, o4-mini, gpt-oss:120b) in a clean, idealised supply chain over 25 months. 11,520 API calls, zero parse failures, ~$6.28 total cost. The results were decisive: mathematical heuristics outperformed every LLM condition by a wide margin.

**The numbers:**
- Best heuristic (exponential smoothing): OVAR 0.54, 5 stockouts
- Best LLM (phi4:14b blind): OVAR 4.33, 41 stockouts
- LLMs were **8x worse on both metrics simultaneously** — not a tradeoff between variance and service level, but a failure on both

**What we learned:**
- Adding context (calendar month + company persona) was marginally helpful for frontier models (gpt-4.1-mini: 4.70 to 4.47 OVAR) but **catastrophically harmful** for the local model (phi4:14b: 4.33 to 6.35 OVAR, +47%, std exploding from 0.00 to 2.53)
- Reasoning models (o4-mini, gpt-oss:120b) showed **no advantage** over lightweight models despite generating 10x more tokens (o4-mini: 1.08M reasoning tokens for the same OVAR as gpt-4.1-mini)
- Pattern scores were uniformly low (0.20-0.23) — agents could describe seasonal events in their rationale ("Diwali approaching") but did not adjust their orders accordingly
- Each LLM decision is a fresh judgement call with no memory of prior periods — this statelessness means the agent cannot learn from its own mistakes within a run
- Local and frontier models were equivalent in reasoning conditions (delta OVAR 0.00-0.20) but diverged sharply in lightweight context (delta 1.88)

**What V3 tests:** V2's heuristics were calibrated for stable conditions. When the world breaks — pandemic demand collapse, geopolitical supply shocks, port strikes — their fixed parameters become liabilities. LLMs carry world knowledge. V3 asks whether that knowledge translates to an advantage when the environment is disrupted, or whether the structural limitations identified in V2 persist regardless.

---

## World Events

Three disruption events are baked into the 36-month timeline. Each event modifies three simulation parameters for the periods it covers:

- **demand_multiplier**: scales retail demand (pandemic collapse, reopening surge)
- **fill_rate_cap**: maximum fraction of any order that can actually be delivered
- **lead_time_multiplier**: scales the stochastic lead time draw

### Event 1 — Pandemic (Periods 7–12, mid-2025)

Modelled on the COVID-19 pattern: initial demand collapse as consumers freeze, simultaneous supply collapse as factories shut, then a demand surge as economies reopen and stimulus money flows through — but supply cannot keep up.

| Phase | Periods | Demand × | Fill rate cap | Lead time × |
|---|---|---|---|---|
| Shock — factories close, demand collapses | 7–9 | 0.55 | 40% | 2.5× |
| Surge — reopening, pent-up demand releases | 10–11 | 1.35 | 55% | 2.0× |
| Recovery — gradual normalisation | 12 | 1.10 | 75% | 1.3× |

**What this tests:** During the shock, blind heuristics will keep ordering near-normal volumes (their smoothed forecast reacts slowly). During the surge, their forecast is anchored to the collapse period so they under-order. An LLM that recognises "pandemic reopening" as a signal to aggressively rebuild inventory may gain an advantage — if it can reason correctly about supply lag.

**Unstructured news headline shown to agents:**
- Shock: *"Global pandemic declared. Factory closures widespread. Logistics severely disrupted. Consumer demand has collapsed."*
- Surge: *"Economies reopening. Consumer demand surging strongly. Supply chains remain constrained — factories not yet at full capacity."*

### Event 2 — Geopolitical Conflict (Periods 19–21, mid-2026)

Modelled on the Russia-Ukraine conflict and its semiconductor/rare-earth supply shock effects. Demand barely changes — consumers keep buying — but supply collapses because component availability and logistics routing are severely disrupted.

| Phase | Periods | Demand × | Fill rate cap | Lead time × |
|---|---|---|---|---|
| Onset | 19 | 0.95 | 45% | 2.0× |
| Sustained | 20–21 | 0.90 | 50% | 1.8× |

**What this tests:** Heuristics that chase demand will keep ordering heavily — and receive far less than ordered, building a massive backlog. An LLM with context may recognise the supply-side nature of the crisis and reduce orders to match realistic delivery capacity.

**Unstructured news headline shown to agents:**
- Onset: *"Major geopolitical conflict disrupting raw material supply. Semiconductor and rare earth shortages reported. Logistics rerouting adds weeks."*
- Sustained: *"Geopolitical conflict ongoing. Component supply severely constrained. Energy costs elevated. Production capacity curtailed across the sector."*


### Event 3 — Port / Logistics Disruption (Periods 28–30, mid-2027)

Modelled on the Suez Canal blockage and LA port strikes. Short, acute, and entirely a supply-side event — demand is completely unaffected. Lead times spike immediately, fill rates drop temporarily, then recover.

| Phase | Periods | Demand × | Fill rate cap | Lead time × |
|---|---|---|---|---|
| Acute disruption | 28 | 1.00 | 65% | 3.0× |
| Tail, clearing backlog | 29–30 | 1.00 | 70% | 2.0× |

**What this tests:** A sharp, well-signalled disruption. Heuristics have no mechanism to anticipate it. An LLM receiving the news headline ("Major port strike halting shipments. Lead times tripling.") may proactively build buffer stock ahead of the disruption window.

**Unstructured news headline shown to agents:**
- Acute: *"Major port strike halting shipments. Lead times tripling. Demand unaffected — supply side only. Build buffer stock if possible."*
- Tail: *"Port dispute partially resolved. Backlog clearing. Lead times remain elevated — full normalisation expected next month."*


---

## Demand Data — 36 Months

The demand series covers January 2025 through December 2027. It is built on top of the V2 Tatva Motors Vecta series with the following structure:

- **Seasonal baseline**: Same Indian automotive seasonal pattern — FY-end peak in March, monsoon trough June–August, Diwali peak in November
- **Year-over-year growth**: +5% each year (2026 and 2027)
- **World event shocks**: Demand multipliers from the event schedule applied to the baseline
- **Gaussian noise**: Added at runtime (not baked into the CSV) — each run draws a fresh noise realisation with CV=8%. **CV** is the coefficient of variation: standard deviation divided by mean. CV=8% means the noise has a standard deviation equal to 8% of that period's baseline demand — so for a 40,000-unit month, the 1σ noise range is ±3,200 units. Because noise is applied at runtime, each of the 20 runs per condition sees a genuinely different demand sequence, making the 20 runs a proper Monte Carlo sample rather than 20 identical replays.

The demand CSV at `code/data/synthetic/tatva_monthly_dispatches_36m.csv` contains the clean seasonal baseline without noise. Noise is applied inside the simulation so that each of the 20 runs per LLM condition sees a genuinely different demand realisation — making the 20 runs a proper Monte Carlo sample rather than 20 identical runs.

---

## Stochastic Parameters

### Lead Times

Each replenishment draws a lead time from a LogNormal distribution, then multiplied by the disruption multiplier for the period the order was placed.

A **LogNormal distribution** is one where the logarithm of the variable is normally distributed. Two properties make it well-suited for lead times: it is always positive (a lead time of zero or negative is impossible), and it has a long right tail (rare but realistic spikes to 3–4× normal are possible). With `mean=0.0, sigma=0.25` in log-space, the median is exactly 1 period and the mean is ~1.03 periods — the vast majority of draws land at 1, with occasional 2s.

```python
base_lead_time = max(1, round(rng.lognormal(mean=0.0, sigma=0.25)))
# mean ≈ 1.03 periods; ~90% of draws = 1 period, ~10% = 2 periods

actual_lead_time = round(base_lead_time × world_events.lead_time_multiplier(period))
```

In normal operations most orders arrive next period. During the pandemic shock (multiplier 2.5×) the mean becomes ~2.5 periods and some orders take 4–5 periods to arrive.

### Fill Rates

Each replenishment draws a fill rate from a Beta distribution, capped by the disruption fill rate cap.

A **Beta distribution** is bounded between 0 and 1, making it a natural fit for fill rates (which are percentages). The shape is controlled by two parameters, `a` and `b`. With `a=9, b=1`, the mean is `a/(a+b) = 9/10 = 0.90` and the mass is heavily concentrated near 1.0 — most draws fall between 0.85 and 0.98. Think of it as saying "a typical order arrives 90% complete, occasionally 98%, rarely 85%." The disruption cap then hard-truncates that: during the pandemic shock (cap=0.40), even if the Beta draws 0.93, only 40% of the order is delivered.

```python
base_fill = rng.beta(a=9, b=1)         # mean=0.90, mostly 0.85–0.98
actual_fill = min(base_fill, world_events.fill_rate_cap(period))
actual_delivery = round(ordered_quantity × actual_fill)
```

In normal operations the mean delivery is 90% of ordered quantity. During the pandemic shock (cap 0.40) a maximum of 40% of any order is delivered regardless of the Beta draw.

### Demand Noise

Applied multiplicatively each period, each run:

```python
noise_factor = rng.normal(loc=1.0, scale=0.08)  # CV = 8%
demand_t = max(0, round(baseline_t × noise_factor × event_shock_t))
```

### Capacity Constraints

Each tier has a hard production ceiling. Orders above capacity are silently capped — the agent may place a large order but only up to capacity units can be dispatched:

| Tier | Capacity (units/period) |
|---|---|
| OEM | 60,000 |
| Ancillary | 65,000 |
| Component | 70,000 |

These limits are not binding in normal operations but become binding during demand surges (pandemic reopening, Diwali peaks with elevated baseline). When capacity is hit, the tier silently delivers only up to its ceiling — the downstream agent sees a smaller-than-ordered delivery but receives no explicit signal explaining why. This matters because it means aggressive ordering during a surge does not necessarily translate to more inventory: above the capacity ceiling, extra orders are wasted. An LLM that recognises this (from the news headline or calendar context) may avoid over-ordering; a heuristic with a high smoothed forecast will keep ordering past the ceiling regardless.


---

## SimPy Architecture — How the Simulation Works

SimPy models time as a continuous event queue. Rather than a fixed period loop, each process runs as a Python generator that yields control back to the simulation engine when it needs to wait.

**SimPy runs entirely locally** — it is a pure Python library with no GPU or server requirement. The simulation itself is CPU-only and fast (a full 36-period run completes in milliseconds). What runs remotely is the LLM call: each period, the agent interface posts the prompt to Azure (or a local endpoint) and waits for the order quantity in the response. The simulation is paused during that wait.

**Using a different LLM:** Yes — set `BACKEND=local` in your env file and point `LOCAL_ENDPOINT` to any OpenAI-compatible API (Ollama, LM Studio, vLLM) with `LOCAL_MODEL` set to the model name. The backend interface is model-agnostic. The paper uses `GPT-4.1-mini` (lightweight) and `o4-mini` (reasoning) on Azure, but nothing in the simulation is specific to those models.

**Flow — one simulation period, one tier:**

```
┌──────────────────────────────────────────────────────────────────┐
│  SimPy Environment (runs locally, Python)                        │
│                                                                  │
│  TierProcess.run() — one iteration per period                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. RECEIVE   ← _deliver() subprocesses credit on_hand      │  │
│  │              when their env.timeout(lead_time) fires        │  │
│  │                                                            │  │
│  │ 2. FULFIL    ← serve downstream demand + carry backlog     │  │
│  │                                                            │  │
│  │ 3. DECIDE    ← LLM call (remote) or heuristic (local)      │  │
│  │               returns: order_quantity                       │  │
│  │                                                            │  │
│  │ 4. SPAWN     ← new _deliver() subprocess created           │  │
│  │               draws lead_time, draws fill_rate             │  │
│  │               yields env.timeout(lead_time)                │  │
│  │               (runs concurrently — can overlap with        │  │
│  │                orders from previous periods)               │  │
│  │                                                            │  │
│  │ 5. SEND      ← put order into simpy.Store channel          │  │
│  │               (becomes next tier's demand signal)          │  │
│  │                                                            │  │
│  │ 6. ADVANCE   ← yield env.timeout(1) → next period         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Inter-tier channels (simpy.Store, capacity=1):                  │
│    Retail demand → OEM → [Store] → Ancillary → [Store] → Comp   │
└──────────────────────────────────────────────────────────────────┘
```

The `_deliver()` subprocess is the key innovation over V2. Because each delivery runs as an independent concurrent process, multiple in-flight orders can overlap: an order placed in period 5 with lead time 3 and an order placed in period 6 with lead time 1 both arrive in period 8, their deliveries crediting inventory independently.


```
simpy.Environment()
│
├── OEM TierProcess        → runs as SimPy generator, one env.timeout(1) per period
│     └── _deliver()      → subprocess spawned per order; waits lead_time, then credits inventory
│
├── Ancillary TierProcess  → same structure
│     └── _deliver()
│
└── Component TierProcess  → same structure
      └── _deliver()
```

**Between-tier coordination** uses `simpy.Store(capacity=1)` channels:

```
OEM → [oem_to_anc Store] → Ancillary → [anc_to_comp Store] → Component
```

OEM places an order by writing to `oem_to_anc`. Ancillary blocks on `yield demand_channel.get()` until OEM's order arrives. Capacity=1 on the Store enforces serial processing — no tier can race ahead of the others.

**What happens each period, per tier:**

1. **Receive replenishments** — any `_deliver()` subprocesses that have completed their lead time countdown credit `on_hand` automatically
2. **Fulfil demand** — serve downstream demand + any backlog from previous periods; record stockout if on_hand is insufficient
3. **Order decision** — LLM or heuristic decides how many units to order from upstream
4. **Spawn `_deliver()`** — a new subprocess is created for the order; it draws lead time and fill rate, yields `env.timeout(lead_time)`, then credits inventory
5. **Send order downstream** — puts the order quantity into the inter-tier Store channel (which becomes the next tier's demand)
6. **Advance** — `yield env.timeout(1)` moves to the next period

The `_deliver()` subprocess is the key innovation. Because it runs as a separate concurrent process that wakes up after `lead_time` periods, multiple in-flight orders can overlap. An order placed in period 5 with lead time 3 and an order placed in period 6 with lead time 1 both arrive in period 8 — their deliveries are independent and both credit inventory when they land. V2 could not model this.

---

## Experimental Conditions

V3 expands the V2 2×2 matrix to a 2×3:

| | Blind | Context | Unstructured |
|---|---|---|---|
| **Lightweight** (GPT-4.1-mini) | blind_lightweight | context_lightweight | unstructured_lightweight |
| **Reasoning** (o4-mini) | blind_reasoning | context_reasoning | unstructured_reasoning |

### Blind condition

The agent receives only raw numbers each period — demand received, on-hand inventory, backlog, inventory position. No calendar month. No company name. No persona. Any seasonal adjustment it makes must emerge from the numbers alone.

Example prompt:
```
Demand received this period: 42,150 units
On-hand inventory (post-fulfilment): 8,340 units
Backlog (unfulfilled, carried forward): 0 units
Inventory position (on_hand - backlog): 8,340 units

How many units do you order from your upstream supplier this period?
```

### Context condition

Adds the calendar month and a company-specific persona to the system prompt. The agent now knows it is Tatva Motors' ordering agent, what product it handles, who its upstream supplier is, and what month it is. It can apply its own world knowledge about Indian automotive seasonal demand without being told what patterns to look for.

Example system prompt (OEM):
```
You are a supply chain ordering agent for Tatva Motors, India.
Product: Vecta Lighting Assembly. Upstream supplier: ancillary lighting manufacturer.
Each month: receive a production despatch target and place a Lighting Assembly order.
```

Example user prompt addition:
```
Current month: Nov 2025
Demand received this period: 54,800 units
...
```

### Unstructured condition

Everything from Context, plus one additional line in the user prompt during active world event periods:

```
Current conditions: [Economies reopening. Consumer demand surging strongly.
Supply chains remain constrained — factories not yet at full capacity.]
```

In normal periods this line is absent. The agent is never told what to do with this information — it must decide whether to order more, order less, or treat it as noise. The condition tests whether explicit disruption signals change ordering behaviour beyond what calendar context alone provides.

---

## Heuristic Baselines

Three heuristics run as comparison baselines, each for 100 Monte Carlo runs (because demand noise means each run is genuinely different in V3, unlike V2 where heuristics were deterministic):

**Naive passthrough:** orders exactly what demand was this period. OVAR = 1.0 by construction at OEM (it passes through demand unchanged), but variance amplifies upstream.

**Exponential smoothing:** maintains a smoothed demand forecast, orders forecast + backlog. Parameter α=0.30 (empirically calibrated in V2).

**Order-up-to (S policy):** maintains a target inventory position (S = mean + 1.65σ of demand), orders whatever brings inventory position up to S. Parameter α=0.30 for forecast update.

---

## Experiment Labels and Run Counts

| Label | Conditions | Policy | Model tier | Runs |
|---|---|---|---|---|
| baselines | naive_passthrough, exp_smoothing, order_up_to | heuristic | — | 100 each |
| E1 | blind, context, unstructured | llm | lightweight | 20 each |
| E2 | blind, context, unstructured | llm | reasoning | 20 each |
| E3 | blind, context (ablation: no events) | llm | lightweight | 20 each |

E3 is an ablation study — the same lightweight model under the same prompt conditions but with all world events disabled. Comparing E3 to E1 isolates the effect of world events from the effect of prompt context alone.

---

## File Index

```
experiments/Agentic_Bullwhip_Effect_V3_WorldEvents/
├── DESIGN.md                          ← Architecture and design decisions
├── EXPLAINER.md                       ← This file
└── code/
    ├── generate_demand_36m.py         ← Generates the 36-month demand CSV
    ├── world_events.py                ← WorldEvents class — disruption schedule
    ├── simulation.py                  ← SimPy engine: SupplyChainSim + TierProcess
    ├── agent_interface.py             ← Prompt builder + LLM interface
    ├── metrics.py                     ← OVAR, stockout, pattern score computation
    ├── run_experiment.py              ← Entry point — runs all conditions, saves results
    ├── requirements.txt               ← Python dependencies
    ├── env.azure.template             ← Azure credential template
    ├── env.local.template             ← Local (Ollama/LM Studio) template
    ├── data/synthetic/
    │   ├── tatva_monthly_dispatches_36m.csv           ← Clean baseline (no noise)
    │   └── tatva_monthly_dispatches_36m_annotated.csv ← Same + event labels
    └── backends/
        ├── azure_backend.py           ← Azure OpenAI API calls
        ├── local_backend.py           ← Local model API calls
        ├── dry_run_backend.py         ← No-API test mode
        └── resilience.py             ← Exponential backoff (10 retries, 60s cap)
```

### `generate_demand_36m.py`

Reads the V2 25-month demand CSV and extends it to 36 months. Applies +5% YoY growth for 2026 and +5% again for 2027. Outputs two CSVs: the clean baseline (used by the simulation) and an annotated version with event labels for inspection. Run this once before the first experiment run:

```bash
cd code && python generate_demand_36m.py
```

### `world_events.py`

Holds the full disruption schedule as a list of `_EventPeriod` dataclasses. The `WorldEvents` class exposes four methods used by the simulation:

- `demand_multiplier(period)` → float (1.0 in normal periods)
- `fill_rate_cap(period)` → float (1.0 in normal periods)
- `lead_time_multiplier(period)` → float (1.0 in normal periods)
- `event_signal(period)` → str or None (news headline for unstructured condition)
- `event_label(period)` → str or None (phase name stored in output records)

You can disable specific events for ablation runs:

```python
WorldEvents(enabled_events={"pandemic"})        # pandemic only
WorldEvents(enabled_events=set())               # no events — clean baseline
WorldEvents()                                   # all three events (default)
```

### `simulation.py`

The SimPy engine. Two key classes:

**`TierProcess`**: SimPy generator for one supply chain tier. Manages inventory state (`on_hand`, `backlog`), calls the LLM or heuristic for each period's order decision, and spawns `_deliver()` subprocesses.

**`SupplyChainSim`**: Owns the SimPy environment, creates the three TierProcess instances, wires them together with `simpy.Store` channels, and runs `env.run()`. Returns a list of records identical in schema to V2 output — `metrics.py` works without modification.

**`run_simulation()`**: Convenience wrapper matching the V2 signature. This is what `run_experiment.py` calls.

### `agent_interface.py`

The only file that `simulation.py` imports for LLM decisions. Has three responsibilities:

1. Holds all system prompt strings (blind prompt, context prompts per tier, which also apply to unstructured condition)
2. Builds the per-period user prompt from simulation state variables
3. Loads the correct backend at runtime via `BACKEND` env var, calls `get_order_decision()`

The `build_user_prompt()` function accepts an optional `event_signal` parameter. When the condition is `unstructured` and an event is active, the news headline appears as one line in the user prompt. All other conditions set `event_signal=None` and the line is omitted.

### `metrics.py`

Pure computation. Takes the records DataFrame and produces:

- **OVAR** per run × tier (`compute_ovar`), and chain average across tiers (`compute_chain_ovar`)
- **Stockout count** per run × tier, and chain total per run (`compute_stockouts`)
- **Pattern score** — did the agent mention seasonal keywords? Did it order in the right direction? (`compute_pattern_score`). Only meaningful for LLM conditions.
- **`summarise_condition()`** — wraps all of the above into a single dict, called by `run_experiment.py` for each condition

### `run_experiment.py`

The entry point. Handles:
- Dataset loading and validation (SHA-256 checksum in provenance)
- Deriving S (target inventory level) and safety stock from the demand series
- Running each condition via `run_condition()`, which retries failed runs (up to 5× the target count)
- Checkpointing: `records.checkpoint.parquet` is written after every condition — if the process crashes mid-experiment, no completed condition data is lost
- Saving final results: `records.parquet`, `summary.json`, `provenance.json`

### `backends/resilience.py`

Wraps all API calls with exponential backoff: 10 retries, delays doubling from 1s to a 60s cap, with ±10% jitter to avoid thundering herd. Handles transient HTTP 429, 500, and 503 errors. This is why a single Azure 500 error no longer crashes a run.

---

## How to Run

### Prerequisites

```bash
cd code
pip install -r requirements.txt
```

Set up your environment file:

```bash
# Azure
cp env.azure.template .env.azure
# Edit .env.azure: fill in AZURE_ENDPOINT, AZURE_API_KEY, deployment names

# Local
cp env.local.template .env.local
# Edit .env.local: fill in your local model endpoint and model names
```

### Generate demand data (one-time)

```bash
python generate_demand_36m.py
```

### Dry run — validate the simulation without API calls

```bash
DRY_RUN=1 python run_experiment.py --experiments baselines --env .env.azure
```

The dry_run backend returns `demand` as the order quantity (naive passthrough) with no API calls. Use this to confirm the SimPy simulation runs end-to-end and produces valid records.

### Production run — inside tmux + nohup

```bash
# Azure: E1 + E2 (lightweight + reasoning)
tmux new-session -d -s v3_azure
tmux send-keys -t v3_azure \
  "cd /path/to/code && nohup python run_experiment.py --experiments E1 E2 --runs 20 --env .env.azure > logs/v3_azure.log 2>&1" Enter

# Local: baselines + E1
tmux new-session -d -s v3_local
tmux send-keys -t v3_local \
  "cd /path/to/code && nohup python run_experiment.py --experiments baselines E1 --runs 20 --env .env.local > logs/v3_local.log 2>&1" Enter
```

Always use tmux + nohup for production runs. On a remote machine, a disconnected terminal will kill any process not protected by nohup.

### Monitor progress

```bash
tail -f logs/v3_azure.log
```

Checkpoint files appear in `results/<experiment>/<timestamp>/records.checkpoint.parquet` as each condition completes.

---

## Output Files

After a run, results are saved to `results/<experiment_label>/<timestamp>/`:

| File | Contents |
|---|---|
| `records.parquet` | Full record for every (period, tier, run). One row per simulation step. |
| `summary.json` | OVAR, stockout count, pattern score per condition — mean and std across runs |
| `provenance.json` | SHA-256 demand checksum, model names, temperatures, world events enabled, platform |

The `records.parquet` schema:

| Column | Description |
|---|---|
| `run_id` | Unique run identifier |
| `condition_label` | e.g. `context_lightweight` |
| `tier` | OEM, Ancillary, or Component |
| `period` | 1–36 |
| `calendar_month` | e.g. `Nov 2025` |
| `policy` | `llm`, `naive`, `exp_smoothing`, `order_up_to` |
| `demand_received` | Units demanded this period (with noise + event shock) |
| `on_hand_before_order` | Inventory level after fulfilment, before ordering |
| `backlog` | Unfulfilled carry-forward demand |
| `order_placed` | Units ordered from upstream |
| `fulfilled` | Units actually served to downstream |
| `shortfall` | Unmet demand (positive → stockout) |
| `stockout` | Boolean |
| `rationale` | LLM's one-sentence reasoning (empty for heuristics) |
| `world_event` | Phase name if a disruption is active, else None |

---

## What We Are Measuring and Why

The central hypothesis: in V2's clean environment, heuristics won because their parameters were calibrated for that environment — exponential smoothing achieved OVAR 0.54 with only 5 stockouts, while the best LLM managed OVAR 4.33 with 41 stockouts. In V3's disrupted environment, the heuristic parameters become liabilities — the fixed smoothing coefficient (alpha=0.30) that worked perfectly in stable conditions anchors too slowly when demand collapses by 45% (pandemic shock), and too sluggishly when it surges by 35% (reopening). An LLM with world knowledge may recognise disruption signals and adjust more appropriately.

**H1 (replication):** Does V3 confirm V2's result under stable conditions (E3, no events)? V2 baseline: best LLM OVAR 4.33 vs best heuristic 0.54.
**H2 (disruption effect):** Does performance shift under world events (E1 vs E3)? V2 showed the gap was structural — does disruption change the structure?
**H3 (context value):** Does adding calendar month + persona (context vs blind) improve LLM performance? V2 found context marginally helpful for frontier (delta -0.23) but catastrophically harmful for local (delta +2.02).
**H4 (unstructured value):** Does the news headline (unstructured vs context) provide additional benefit during disruption events? V2's pattern scores (0.20-0.23) showed agents could not act on implicit seasonal signals — explicit disruption signals are a stronger test.
**H5 (model tier):** Does reasoning model (E2) outperform lightweight model (E1)? V2 found zero reasoning advantage (o4-mini 4.52 vs gpt-4.1-mini 4.47) in a clean environment. Disrupted environments may demand reasoning capacity that stable ones did not.
**H6 (disruption phase):** Which disruption type (pandemic, conflict, port) causes the largest divergence between LLMs and heuristics?

---

## Parity Check — V3 Must Match V2

Before running any LLM experiments, validate that V3 replicates V2 under matching conditions. Run V3 with:
- `noise_cv=0` (no demand noise)
- `WorldEvents(enabled_events=set())` (no events)
- Fixed lead time = 1 (achieved by setting LogNormal sigma=0)
- Fill rate cap = 1.0 (always full delivery)

Under these conditions, OVAR and stockout counts for naive/exp_smoothing/order_up_to must match V2's deterministic outputs: naive_passthrough OVAR=1.00 (3 stockouts), exp_smoothing OVAR=0.54 (5 stockouts), order_up_to OVAR=1.71 (14 stockouts). If they diverge, there is a bug in the simulation logic before any LLM results are collected.

---

## Assumptions and Limitations

- **Synthetic demand**: The retail demand series is calibrated against real Indian automotive seasonal patterns but is not sourced from actual Tatva Motors data. All numerical conclusions apply to the synthetic scenario.
- **Single product, single topology**: Three tiers, one product. Real supply chains have thousands of SKUs and multi-tier, multi-source networks. Mixed deployment (LLM at OEM only, heuristics upstream) is deferred to V4.
- **Simultaneous policy**: All three tiers run the same policy in the same condition. This is experimentally clean but not how real deployments would look.
- **LLM stochasticity**: At temperature > 0, LLM outputs vary across runs. The 20-run Monte Carlo captures this variance but does not fully separate model sampling noise from demand noise — that would require a matched-noise design.
- **No memory across periods**: Each LLM call is stateless. The agent receives the current period's state variables only — no access to order history or prior rationales. A conversational agent with memory might behave differently.
- **Azure temperature locking**: Azure fixes o4-mini at temperature=1.0 regardless of what is set in the config. TEMP_REASONING and TEMP_CONTEXT_REASONING values in provenance.json record the intended design, not what was enforced.

---

## Reading the Results

After running, load `summary.json` or the parquet for analysis:

```python
import pandas as pd, json

# Full records
df = pd.read_parquet("results/E1/20260319T120000/records.parquet")

# Summary
with open("results/E1/20260319T120000/summary.json") as f:
    summary = json.load(f)

# Chain OVAR for each condition
for cond in summary:
    print(cond["condition"], "chain_ovar:", cond["chain_ovar"])
```

Interpret results:

- A condition with **chain_ovar < 1.0** is dampening demand variance — the agents are smoothing, not amplifying
- A condition with **low stockouts** and **low OVAR** simultaneously is the ideal operating point
- **Pattern score** above 0.5 means the LLM is correctly recognising seasonal events in both its rationale text (keyword_score) and its order quantities (elevation_score)
- Compare E1 (with events) to E3 (no events, same model) to isolate the disruption effect from the model capability effect

---

*For architecture decisions and the hypothesis-level design rationale, see [DESIGN.md](DESIGN.md).*
