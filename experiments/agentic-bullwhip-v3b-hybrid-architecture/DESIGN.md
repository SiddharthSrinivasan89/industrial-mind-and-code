# V3b Design — Hybrid Architecture Experiment

**Experiment:** `agentic-bullwhip-v3b-hybrid-architecture`
**Version:** 1.0
**Date:** March 2026
**Status:** Code complete, pre-run

---

## 1. Research Question

Supply chain literature identifies order variance amplification — the bullwhip effect — as a primary driver of inventory inefficiency. LLMs can articulate seasonal demand patterns but may introduce additional variance when making unconstrained ordering decisions. A hybrid architecture where the LLM adjusts a *parameter* of a deterministic formula rather than deciding order quantities directly separates directional reasoning (LLM strength) from numerical precision (formula strength).

**Primary question:** Can LLMs improve supply chain ordering performance by adjusting the *safety stock parameter* of a deterministic ordering policy rather than issuing orders directly?

**Success criterion (H1):** At least one hybrid condition achieves chain-average OVAR ≤ exp_smoothing OVAR (measured in this experiment) AND chain stockouts ≤ exp_smoothing stockout count (measured in this experiment).

---

## 2. Supply Chain Structure

Three-tier serial cascade:

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Lead time:** 1 month deterministic (order placed in t arrives at start of t+1)
- **Visibility:** No cross-tier visibility. Each tier sees only its immediate downstream order.
- **Timing:** Replenishment arrives → fulfilment → ordering → records append (same period)

---

## 3. Hybrid Architecture Design

### Two-layer execution per period per tier

**Layer 1 — Planning (LLM):**
- Receives: state variables + optional seasonal context + optional order history
- Outputs: `{"safety_stock_multiplier": float, "rationale": "..."}`
- Multiplier bounded: [0.5, 3.0] stated in prompt; clamped in code regardless
- Fallback: 1.0 (neutral) if LLM parse fails — logged as `llm_fallback=True`

**Layer 2 — Execution (deterministic, OUT-style):**
```
F_t              = 0.30 × D_t + 0.70 × F_{t-1}
SS_t             = base_SS × multiplier_t
target_position  = round(F_t) + SS_t
order_t          = max(0, target_position - inventory_position_t)
```

where `inventory_position = on_hand - backlog`.

**Parameters:**
- `alpha = 0.30` — empirically optimal on this demand series
- `base_SS = S - mean_demand ≈ 5,061 units` — derived at runtime from demand CSV

### Why OUT-style (not additive backlog)?

The naive additive formula `order = F_t + SS + backlog` makes safety stock a persistent positive flow offset — the agent would spend `base_SS` units extra *every single period* regardless of current inventory level. That is not "parameterising a safety stock" in any meaningful sense; it's a constant order uplift that biases orders upward unconditionally.

The OUT-style formula `order = target_position - inventory_position` is the standard base-stock/Order-Up-To structure. When on-hand is high, less is ordered; when on-hand is low, more is ordered. The LLM's multiplier adjusts the target inventory level (how high to aim), which is precisely the definition of adjusting a safety stock parameter.

At multiplier=1.0 this is identical to `policy_order_up_to()` with `safety_stock=base_SS`.

### Why show the formula to the LLM?

Separating the planning decision (how much buffer?) from the execution arithmetic reduces the LLM's task to directional reasoning about seasonal patterns, avoiding precision errors that arise when the model must translate a qualitative assessment directly into an order quantity. By showing the formula explicitly, the LLM knows exactly how its multiplier choice maps to the order placed.

### The `hybrid_control` deterministic baseline

Because `multiplier=1.0` hybrid produces different orders than pure `exp_smoothing` (different formula structure: OUT vs. smoothed backlog), comparing hybrid directly to exp_smoothing conflates two things: the formula change AND the LLM contribution.

The `hybrid_control` condition resolves this: identical OUT-style execution with multiplier fixed at 1.0 and no LLM called. It is deterministic (run once) and establishes the architectural baseline. Any difference between `hybrid_control` and an active hybrid condition is attributable purely to the LLM's multiplier decisions.

**Two reference baselines:**
1. **Within-experiment benchmark:** `exp_smoothing` — the performance target for H1
2. **Architectural control:** `hybrid_control` (fixed multiplier=1.0) — measures the LLM's marginal contribution within the hybrid framework

### Why the multiplier bounds [0.5, 3.0]

- **0.5 lower bound:** Halves the safety stock. Even the most extreme demand dip (monsoon -8%) doesn't justify eliminating buffer entirely. 0.5 is a strong seasonal dip signal, not a zero-stock gamble.
- **3.0 upper bound:** Triples the safety stock. Diwali +19% historically — a 3× safety stock increase is generous headroom. More than 3× would indicate the LLM is using the multiplier to proxy a full order quantity rather than adjusting buffer.
- **1.0 neutral:** No change from base safety stock. Correct default for months with no expected seasonal event.

---

## 4. Experimental Conditions

### Condition 1: Hybrid-Blind (H-Blind)

**Hypothesis tested:** Does blind parameterisation (no seasonal context) reduce OVAR vs the within-experiment baselines?

**Agent sees:** 4 state variables only — demand_received, on_hand, backlog, inventory_position, base_ss.

**Why test blind?** If H-Blind beats exp_smoothing, it confirms the architectural change matters regardless of seasonal intelligence. If H-Blind is worse than H-Context, it quantifies the seasonal context contribution.

### Condition 2: Hybrid-Context (H-Context)

**Hypothesis tested (H2):** Does seasonal context (calendar month + persona) improve multiplier calibration vs blind?

**Agent sees:** State variables + current calendar month (e.g., "Nov 2025") + tier persona (company name, product).

**Primary comparison:** H-Context OVAR vs H-Blind OVAR. ΔOVAR ≥ 0.5 (MPRD threshold) needed to claim context helps.

### Condition 3: Hybrid-Stateful (H-Stateful)

**Hypothesis tested (H3):** Does order history enable self-correction beyond context alone?

**Agent sees:** State variables + calendar month + last 3 periods of `(demand, order_placed, ss_multiplier, backlog, stockout_flag)`.

**Why include ss_multiplier in history?** Enables true self-correction: "I set 2.0 last period but still got a stockout — I should go higher." Without prior multiplier, the agent can observe outcomes but not diagnose its own parameterisation decisions.

**Why include backlog and stockout_flag?** Without outcome feedback, the agent knows what it ordered but not whether that choice was adequate. Showing `backlog` and `[STOCKOUT]` gives direct evidence: "my multiplier of 1.2 last period resulted in a stockout — I should set it higher this period."

**Why 3 periods?** Covers one fiscal quarter. Long enough to observe recent trend; short enough not to bloat the prompt.

---

## 5. Demand Data

25-month synthetic series (Jan 2025 – Jan 2027) calibrated to real Indian automotive market data.

| Parameter | Value |
|---|---|
| Mean demand | 38,548 units/month |
| Std (ddof=1) | ~3,067 units |
| Initial inventory (S) | ~43,600 units (mean + 1.65σ) |
| Base safety stock | ~5,061 units (S - mean_demand) |
| Active ordering periods | 24 (periods 1–24) |
| Close-out period | 1 (period 25 — fulfilment only) |

**Seasonal events captured (both 2025 and 2026 cycles):**
- Makar Sankranti (Jan): +elevation
- Union Budget (Feb): +elevation
- FY-end (Mar): +elevation (annual structural peak)
- Wedding season (Apr–May): +elevation
- Monsoon dip (Jun–Aug): −dip
- Navratri/Dasara (Oct): +elevation
- Diwali (Nov): +elevation (largest single month, +19% YoY)
- Year-end (Dec): +elevation

---

## 6. Models

| Label | Model | Backend | Temperature |
|---|---|---|---|
| local | nemotron-3-super:120b | Ollama (local) | default |
| azure | gpt-4.1-mini | Azure OpenAI GlobalStandard | default |

**Temperature rationale:** Both models are reasoning models that only accept default temperature (1.0). Stochasticity across 20 runs is preserved via the models' sampling defaults. The constrained output space (a float in [0.5, 3.0]) limits runaway variance even at default temperature.

---

## 7. Metrics

### Primary: OVAR (Order Variance Ratio)

```
OVAR_tier = Var(order_placed) / Var(demand_received)
            sample variance (ddof=1), 24 active ordering periods

Chain OVAR = arithmetic mean across 3 tiers
```

- OVAR < 1.0: dampening (desired)
- OVAR = 1.0: passthrough
- OVAR > 1.0: bullwhip amplification (bad)
- **MPRD threshold:** |ΔOVAR| ≥ 0.5 required for practically meaningful difference

### Primary: Stockout count

Periods where on_hand < (demand + backlog), summed across all 25 periods × 3 tiers (max = 75).

**Reporting rule:** OVAR and stockout count always reported jointly. A low OVAR via chronic under-ordering (high stockouts) is not success — it is a different failure mode.

### Primary: Mean on-hand inventory

Mean `on_hand_before_order` per run × tier, averaged over 24 active periods, then averaged across tiers to chain level.

Reported alongside OVAR and stockouts to detect inventory-hoarding wins: an agent that suppresses OVAR by chronically over-ordering will show high mean on-hand with low stockouts — that is not a success, it is a different failure mode with high holding cost.

Reported as `mean_on_hand: {mean, std}` in summary.json for every condition (heuristics and hybrid).

### New: Multiplier pattern score (primary hybrid diagnostic)

```
multiplier_pattern_score = (keyword_score + mult_elevation_score) / 2

keyword_score:        fraction of event months where rationale mentions seasonal keyword
mult_elevation_score: fraction of event months where multiplier moved correctly
                      (> 1.1 at festive months, < 0.9 at monsoon dip months)
```

This isolates whether the LLM's parameterisation was directionally correct, independent of the final order outcome.

### New: LLM compliance rate

```
compliance_rate = (periods where not clamped AND not fallback) / total active hybrid periods
```

A rate below 0.95 indicates frequent invalid JSON or out-of-bounds outputs.

### New: Multiplier statistics

Per-run × tier: `mean, std, min, max` of `ss_multiplier` over 24 periods, plus `n_clamped` and `n_fallback`.

---

## 8. Hypotheses

| H | Comparison | Threshold | Decision rule |
|---|---|---|---|
| **H1 (Primary)** | Best hybrid condition | OVAR ≤ exp_smoothing OVAR (this experiment) AND stockouts ≤ exp_smoothing stockouts (this experiment) | Pass if any hybrid config meets both |
| **H2** | Hybrid-Context vs Hybrid-Blind | ΔOVAR ≥ 0.5 (context helps) | Using same model; compare mean OVAR |
| **H3** | Hybrid-Stateful vs Hybrid-Context | ΔOVAR ≥ 0.5 (history helps) | Using same model; compare mean OVAR |
| **H4** | Hybrid-Context multiplier pattern score | ≥ 0.5 | Aggregated across runs and tiers |

---

## 9. Code Architecture

```
run_experiment.py           # CLI + orchestration + output
  ↓ calls
simulation.py               # Per-run loop; hybrid branch calls agent_interface
  ↓ calls
agent_interface.py          # Prompt building; routes to backend
  ↓ calls
backends/                   # azure_backend.py | local_backend.py | dry_run_backend.py
```

**Key new entry points:**
- `get_ss_multiplier()` in agent_interface.py (new, parallel to `get_order_decision()`)
- `policy_smoothed_out_with_ss()` in simulation.py (OUT-style execution layer for hybrid)
- `compute_multiplier_stats()`, `compute_multiplier_pattern_score()`, `compute_llm_compliance_rate()` in metrics.py

---

## 10. Execution Plan

### Phase 0: Dry run validation (< 5 minutes, zero API cost)
```bash
DRY_RUN=1 BACKEND=local /usr/bin/python3 run_experiment.py --experiments baselines H1 --runs 2 --env .env.local
DRY_RUN=1 /usr/bin/python3 verify_outputs.py --results-dir ../results/
```
Expected: all checks pass, all ss_multiplier=1.0, chain OVAR < 4.0 (should match deterministic hybrid_control — not an arbitrary threshold).

### Phase 1: Smoke test (real LLM, 2 runs per condition)
```bash
BACKEND=local /usr/bin/python3 run_experiment.py --experiments H1 H2 H3 --runs 2 --env .env.local
BACKEND=azure /usr/bin/python3 run_experiment.py --experiments H1 H2 H3 --runs 2 --env .env.azure
/usr/bin/python3 verify_outputs.py --results-dir ../results/
```
Expected: llm_fallback rate < 5%, ss_multiplier varies across runs.

### Phase 2: Production runs (in tmux with nohup)
```bash
# Local backend (nemotron-3-super:120b) — run inside tmux
tmux new-session -s prod_local
BACKEND=local nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.local \
    > ../logs/v3b_local_prod.log 2>&1

# Azure backend (gpt-4.1-mini) — run inside tmux
tmux new-session -s prod_azure
BACKEND=azure nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1 H2 H3 --runs 20 --env .env.azure \
    > ../logs/v3b_azure_prod.log 2>&1
```

### Phase 3: Analysis
```bash
/usr/bin/python3 generate_figures.py --results-dir ../results/
# Review fig1 (OVAR vs stockouts), fig4 (multiplier time series), fig6 (compliance)
```
