# Agentic Bullwhip Effect — Version 3: World Events Injection

## Abstract

Version 3 (V3) extends the Agentic Bullwhip Effect experiment series by introducing stochastic supply chain conditions and unstructured world event signals into the simulation environment. The experiment tests whether LLM agents can outperform deterministic heuristics when supply chains are disrupted by pandemic, geopolitical conflict, and port crises — conditions under which fixed-parameter heuristics are hypothesised to be most vulnerable. V3 served as the foundational design for a more targeted follow-on (V3b, Hybrid Architecture), which tested a hybrid planning layer rather than full autonomous ordering; the world events framework developed here continues to inform that lineage.

## Research Question

Do LLM-based ordering agents outperform deterministic heuristics when supply chain conditions are non-ideal — specifically when lead times are stochastic, fill rates are disrupted, and agents in the unstructured condition receive explicit real-world event signals?

The underlying hypothesis: deterministic heuristics are calibrated for stable conditions. When disruption events occur — pandemic demand collapse and subsequent surge, geopolitical supply shocks, port logistics crises — their fixed parameters become liabilities. LLM agents, which carry world knowledge and can reason about novel events, may have a structural advantage in disrupted environments that they lack in stable ones.

## Experimental Design

### Supply Chain Structure

A three-tier serial supply chain (OEM → Ancillary Supplier → Component Supplier) simulated over 36 months (January 2025 — December 2027) using SimPy discrete-event simulation. The demand series represents a synthetic Indian automotive product (Tatva Motors Vecta) with the following structure:

- Seasonal baseline: March FY-end peaks, June–August monsoon trough, November Diwali peak, with +5% year-on-year growth applied to each successive year
- Multiplicative Gaussian demand noise (CV = 8%) applied per run, yielding a genuine Monte Carlo sample across the 20 replication runs per condition
- Three world event demand shocks layered on top of the noisy seasonal baseline

**Stochastic parameters:**

| Parameter | Normal Operations | During Disruption |
|---|---|---|
| Lead time | LogNormal(mu=0, sigma=0.25); mean ~1 period | Base x event multiplier; up to 3x during acute events |
| Fill rate | Beta(9, 1); mean ~90% | Capped by event schedule; down to 40% during pandemic shock |
| Demand | Seasonal baseline x Gaussian noise (CV=8%) | Additional multiplicative shock per event phase |

**Capacity constraints (units per period):**

| Tier | Capacity |
|---|---|
| OEM | 60,000 |
| Ancillary | 65,000 |
| Component | 70,000 |

Capacity is non-binding under normal operations and becomes binding during demand surges (pandemic reopening phase, Diwali peaks).

**SimPy process architecture:** Each tier runs as a SimPy generator process yielding `env.timeout(1)` per period. Replenishment triggers a `_deliver()` subprocess that draws fill rate and lead time stochastically, then waits the sampled lead time before crediting inventory. The `WorldEvents` module fires disruption state changes at scheduled period boundaries and returns per-period multipliers to both the simulation engine and the agent prompt builder.

### World Events

Three event types modelled on historical disruptions:

**Event 1 — Pandemic (periods 7–12, Jul–Dec 2025):**

| Phase | Periods | Demand Multiplier | Fill Rate Cap | Lead Time Multiplier |
|---|---|---|---|---|
| Demand collapse | 7–9 | 0.55 | 0.40 | 2.5x |
| Demand surge (reopening) | 10–11 | 1.35 | 0.55 | 2.0x |
| Recovery lag | 12 | 1.10 | 0.75 | 1.3x |

**Event 2 — Geopolitical Conflict (periods 19–21, Jul–Sep 2026):**

| Phase | Periods | Demand Multiplier | Fill Rate Cap | Lead Time Multiplier |
|---|---|---|---|---|
| Supply shock onset | 19 | 0.95 | 0.45 | 2.0x |
| Sustained disruption | 20–21 | 0.90 | 0.50 | 1.8x |

**Event 3 — Port / Logistics Disruption (periods 28–30, Apr–Jun 2027):**

| Phase | Periods | Demand Multiplier | Fill Rate Cap | Lead Time Multiplier |
|---|---|---|---|---|
| Acute disruption | 28 | 1.00 | 0.65 | 3.0x |
| Backlog clearing | 29–30 | 1.00 | 0.70 | 2.0x |

### Conditions and Models

V3 uses a 2x3 factorial design (model tier x prompt condition):

| | Blind | Context (calendar + persona) | Unstructured (+ news headline) |
|---|---|---|---|
| Lightweight (E1) | blind_lightweight | context_lightweight | unstructured_lightweight |
| Reasoning (E2) | blind_reasoning | context_reasoning | unstructured_reasoning |

An ablation group (E3) runs blind and context conditions with world events disabled, replicating a clean 36-month environment to test whether the stochastic simulation alone — absent disruptions — changes outcomes relative to V2.

**Models:**

| Backend | Tier | Model | Env Var |
|---|---|---|---|
| Azure OpenAI | Lightweight (E1) | gpt-4.1-mini | `MODEL_LIGHTWEIGHT` |
| Azure OpenAI | Reasoning (E2) | o4-mini | `MODEL_REASONING` |
| Local (Ollama) | Lightweight (E1) | nemotron-cascade-2:30b | `MODEL_LIGHTWEIGHT` |
| Local (Ollama) | Reasoning (E2) | gpt-oss:120b | `MODEL_REASONING` |

**Temperature:** Lightweight conditions: 0.4 (all prompt variants). Reasoning conditions (local): 0.0 blind, 0.3 context and unstructured. Azure o4-mini: temperature fixed at 1.0 by platform.

**Heuristic baselines:** naive_passthrough, exp_smoothing (alpha=0.30), order_up_to (alpha=0.30). Heuristics run 100 Monte Carlo replication runs (versus 20 for LLM conditions) because demand noise means each run produces a genuinely different realisation; 100 runs provide adequate distributional characterisation of heuristic performance under uncertainty.

**Agent prompt — unstructured condition:** During an active world event, the user prompt includes one additional line:

```
Current conditions: [Pandemic — global logistics severely disrupted, factory closures widespread]
```

During normal periods this line is absent. The agent is never instructed how to use the signal; it must reason about it and determine whether to order more, less, or normally.

### Hypotheses

**H1 (Primary):** At least one LLM condition produces lower chain OVAR and fewer stockouts than the best heuristic baseline simultaneously (both metrics together). This requires matching or beating exp_smoothing on both OVAR and stockout count.

**H2 (Context effect):** The unstructured condition produces lower chain OVAR than the corresponding blind condition for at least two of the four model-backend combinations tested. The hypothesis is that explicit disruption signals allow agents to pre-position inventory before fill rate and lead time deterioration peaks.

**H3 (Disruption advantage):** The gap between LLM OVAR and heuristic OVAR is smaller in V3 (with disruption events active) than in V2 (clean environment). This tests whether disrupted conditions close the performance gap observed in V2 even if LLMs do not surpass heuristics outright.

## Results

V3 was designed and implemented as a code-complete experiment with completed smoke tests but was superseded before full production runs were executed. The experiment registry, simulation engine, world events module, and agent interface are fully functional. The design was superseded by V3b (Hybrid Architecture), which tested a more constrained AI role in the same supply chain environment and produced complete production results. Readers seeking quantitative outcomes for this experimental lineage should consult the V3b writeup at `https://industrialmindandcode.ai/blog/agentic-bullwhip-v3b`.

**V2 baseline context:** V3 was designed to move beyond the following V2 results, which constitute the performance floor the experiment aimed to overcome:

| Condition | Model | Chain OVAR | Stockouts |
|---|---|---|---|
| exp_smoothing (best heuristic) | — | 0.54 | 5 |
| naive_passthrough | — | 1.00 | 3 |
| order_up_to | — | 1.71 | 14 |
| Best LLM (blind) | phi4:14b | 4.33 | 41 |
| Best frontier LLM (context) | gpt-4.1-mini | 4.47 | 39 |

The 8x gap on both metrics simultaneously established the baseline that V3's disruption environment was designed to challenge.

## Discussion

V3's design rests on a specific mechanistic hypothesis: that LLMs have a structural advantage in disrupted environments because their world knowledge allows them to reason about events (pandemic reopening implies supply lag implies rebuild strategy) in ways that fixed-parameter heuristics cannot. The unstructured condition provides explicit disruption signal to test whether agents can translate that knowledge into correct ordering magnitude — not merely correct direction.

The design surfaced two structural tensions that shaped the V3b follow-on. First, V2 found that context was harmful for smaller local models, increasing OVAR and destabilising variance substantially. V3's unstructured condition provides an even richer context signal; whether disruption-relevance of the signal changes the dynamic compared to calendar-month context is a primary open question. Second, V2 found that reasoning tokens purchased no advantage — o4-mini's 1.08M reasoning tokens produced the same OVAR as gpt-4.1-mini. V3 was designed to test whether this changes when reasoning must span multi-phase event trajectories (collapse → surge → recovery) rather than seasonal cycles.

The decision to supersede V3 with V3b reflects a design insight: before testing whether agents can exploit disruption signals, it is valuable to establish whether they can calibrate the *magnitude* of any response. V3b isolated this question by restricting the LLM to a single scalar multiplier within a hybrid architecture, allowing directional capability and numerical calibration to be tested separately.

## Limitations

- **Production runs not executed.** The experiment is code-complete with smoke-test validation but was superseded before full 20-run production conditions. Results are therefore not available for quantitative hypothesis evaluation.
- **Single-product, single-topology supply chain.** Results should not be generalised to multi-product or multi-echelon networks.
- **Stateless agents.** Each period presents a fresh decision context with no memory of prior orders or outcomes. This isolates single-period reasoning quality but prevents agents from learning whether their prior actions caused observed outcomes.
- **Synthetic demand series.** The demand series is calibrated to published Indian automotive seasonal patterns but is not derived from proprietary production data.
- **Fixed alpha parameter.** The alpha=0.30 smoothing parameter was inherited from V2's empirical sweep on the deterministic 25-month series. With stochastic demand, alpha sensitivity becomes a secondary analysis question rather than a validated design parameter.
- **Mixed-model local backend.** V3 replaced V2's phi4:14b with nemotron-cascade-2:30b for the local lightweight tier. This breaks direct continuity with V2 local model results.

## How to Reproduce

### Prerequisites

- Python 3.10+
- For Azure conditions: an Azure OpenAI resource with `gpt-4.1-mini` and `o4-mini` deployments. Scale deployment capacity to at least 100 tokens per minute before running production conditions — at 1 req/60s the full Azure run would require approximately 9 days.
- For local conditions: Ollama running with `nemotron-cascade-2:30b` and `gpt-oss:120b` pulled (`ollama pull <model>`).

### Environment Setup

Credentials are never hardcoded. Copy the appropriate template and fill in your own values:

```bash
cd experiments/agentic-bullwhip-v3-world-events/code/

# Azure backend
cp env.azure.template .env.azure
# Edit .env.azure: set AZURE_ENDPOINT and AZURE_API_KEY

# Local backend
cp env.local.template .env.local
# Edit .env.local: confirm LOCAL_ENDPOINT and model tags match your Ollama instance
```

Key fields in `env.azure.template`:

- `AZURE_ENDPOINT`: base URL of your Azure OpenAI resource (`https://<your-resource>.openai.azure.com/`)
- `AZURE_API_KEY`: rotate via Azure Portal → Keys and Endpoint
- `MODEL_LIGHTWEIGHT`: deployment name for gpt-4.1-mini (must match Azure Portal exactly)
- `MODEL_REASONING`: deployment name for o4-mini

Key fields in `env.local.template`:

- `LOCAL_ENDPOINT`: Ollama endpoint (default `http://localhost:11434/v1`)
- `MODEL_LIGHTWEIGHT`: model tag as shown by `ollama list`
- `MODEL_REASONING`: model tag as shown by `ollama list`

### Running the Experiment

**Step 1 — Generate the 36-month demand series (once):**

```bash
python generate_demand_36m.py
# Produces: data/synthetic/tatva_monthly_dispatches_36m.csv
```

**Step 2 — Dry run (zero API cost, validates pipeline):**

```bash
DRY_RUN=1 BACKEND=azure python run_experiment.py --experiments baselines E1 --runs 2 --env .env.azure
DRY_RUN=1 BACKEND=local python run_experiment.py --experiments baselines E1 --runs 2 --env .env.local
```

**Step 3 — Smoke test (2 runs, live API calls):**

```bash
BACKEND=azure python run_experiment.py --experiments E1 --runs 2 --env .env.azure
BACKEND=local python run_experiment.py --experiments E1 --runs 2 --env .env.local
```

**Step 4 — Production runs (20 runs, all experiment groups):**

Run each backend in its own tmux session with nohup. Confirm `DRY_RUN` is unset before launching.

```bash
# Azure backend
tmux new-session -s v3_azure
BACKEND=azure nohup python run_experiment.py \
    --experiments baselines E1 E2 E3 --runs 20 --env .env.azure \
    > logs/v3_azure_prod.log 2>&1

# Local backend (separate session)
tmux new-session -s v3_local
BACKEND=local nohup python run_experiment.py \
    --experiments baselines E1 E2 E3 --runs 20 --env .env.local \
    > logs/v3_local_prod.log 2>&1

# Heuristic baselines — 100 Monte Carlo runs
BACKEND=local nohup python run_experiment.py \
    --experiments baselines --runs 100 --env .env.local \
    > logs/v3_baselines.log 2>&1
```

**Experiment labels:**

| Label | Description |
|---|---|
| `baselines` | naive_passthrough, exp_smoothing, order_up_to (deterministic heuristics) |
| `E1` | Lightweight model x {blind, context, unstructured} |
| `E2` | Reasoning model x {blind, context, unstructured} |
| `E3` | Ablation: lightweight x {blind, context} with world events disabled |

A live run writes timestamped subdirectories under `code/results/` (relative to the `code/` working directory). The local and Azure backends produce separate result directories; analysis must draw from both. The smoke-test summaries committed to this repository are kept under the top-level `results/` directory (summary and provenance JSON only — full per-step `records.parquet` files are excluded from the public copy).

## Citation

This experiment is documented as an intermediate step in the Agentic Bullwhip Effect series. The completed follow-on (V3b Hybrid Architecture) contains quantitative production results and full discussion of this experimental lineage:

```
Srinivasan, Siddharth. "Hybrid AI Safety Stock Control in Supply Chain Replenishment."
Agentic Bullwhip Effect Series, Version 3b. industrialmindandcode.ai, April 2026.
https://industrialmindandcode.ai/blog/agentic-bullwhip-v3b
```

The V3 experiment design document is available at `DESIGN.md` in this directory. A plain-language walkthrough is in `EXPLAINER.md`, and a consolidated findings note is in `FINDINGS.md`.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
