# V4 Design — Intent Classifier Hybrid Architecture

**Experiment:** `Agentic_Bullwhip_Effect_V4_IntentClassifier`
**Version:** 0.1 (draft — to be refined with V3b results)
**Date:** April 2026
**Status:** Pre-code design. Awaiting V3b production results before finalising multiplier calibration and primary threshold.
**Lineage:** V1 → V2 → V2a → V3b (HybridArch) → **V4 (IntentClassifier)**

> **How to use this document:**
> All items marked `[TBD: V3b]` require V3b production results before they can be
> filled in. V3b supplies the within-experiment float baseline against which V4's
> intent approach is judged, and its multiplier histogram will calibrate the
> intent → multiplier lookup table. Do not finalise Section 3.2, Section 8, or
> Section 10 until V3b canonical results are available.

---

## 1. Research Question

V3b established that a hybrid architecture — where an LLM adjusts the *safety stock
multiplier* of a deterministic ordering formula rather than issuing orders directly —
separates qualitative seasonal reasoning (LLM strength) from order arithmetic
(formula strength). However, V3b requires the LLM to output a *calibrated float* in
[0.5, 3.0]. Language models have no intrinsic number line; they produce tokens, not
regression estimates. The float output conflates two sub-tasks: (1) directional
seasonal reasoning ("I should hold more buffer before Diwali") and (2) numerical
translation ("that reasoning maps to multiplier = 1.87"). LLMs are reliable at (1)
and unreliable at (2).

**Primary question:** Does replacing the continuous float output with a *discrete
intent classification* task — where the LLM selects one of five categorical labels
that are then mapped to multiplier values by a deterministic lookup — improve supply
chain ordering performance, compliance reliability, and decision auditability relative
to V3b's float-based approach?

**Secondary question:** Does the intent classifier interface reduce parse failures to
near zero while preserving or improving OVAR and stockout performance?

**Design principle (Intent Classifier):** The LLM's task is reduced to the simplest
possible meaningful decision: *"which buffer direction applies this period?"* All
arithmetic consequences of that decision — the multiplier value, the safety stock,
the order quantity — are computed deterministically from a lookup table and the
existing OUT-style formula. No number generation is required from the LLM.

---

## 2. Prior Work and Experiment Lineage

### 2.1 Internal experiment series

| Version | Architecture | Key finding | Status |
|---|---|---|---|
| V1 | Rule-based agent, simple inventory | Baseline autonomous agent characterisation | Complete |
| V2 | Autonomous LLM ordering, 3-tier serial chain, local models | LLMs amplify order variance; chain OVAR substantially above exp_smoothing benchmark | Complete |
| V2a | As V2 but with alternative local models | Model-dependent variance amplification; smaller models worse | Complete |
| V3b (HybridArch) | LLM sets `safety_stock_multiplier` (float ∈ [0.5, 3.0]); OUT-style formula executes | `[TBD: V3b — primary performance result]` | In production |
| **V4 (this document)** | LLM classifies intent (5 classes); deterministic lookup → multiplier; same OUT-style formula | TBD | Design |

### 2.2 Demand data lineage

All experiments from V3b onward use the same 25-month synthetic demand series
(`tatva_monthly_dispatches_25m.csv`, SHA-256 stamped at runtime). The series is
calibrated to real Indian automotive market data: mean 38,446 units/month (24 active
periods), with two annual cycles of seasonal variation covering major Indian calendar
events. The identical series is preserved in V4 to ensure cross-experiment OVAR
comparisons are valid.

### 2.3 Formula lineage

V3b introduced the OUT-style (Order-Up-To) execution formula. V4 uses the identical
formula unchanged — the only structural change is in how the `multiplier_t` is
determined (intent lookup vs. direct float output). This preserves the V3b →
V4 comparison: any performance difference is attributable purely to the output
interface change.

```
F_t             = 0.30 × D_t + 0.70 × F_{t-1}        [unchanged from V3b]
SS_t            = base_SS × multiplier_t               [multiplier source changes]
target_position = round(F_t) + SS_t                    [unchanged from V3b]
order_t         = max(0, target_position - inventory_position_t)   [unchanged]
```

### 2.4 External literature

**Supply chain dynamics and the bullwhip effect:**
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). The Bullwhip Effect in Supply Chains. *Sloan Management Review*, 38(3), 93–102.
- Lee, H.L., Padmanabhan, V., & Whang, S. (1997). Information Distortion in a Supply Chain: The Bullwhip Effect. *Management Science*, 43(4), 546–558. https://doi.org/10.1287/mnsc.43.4.546
- Forrester, J.W. (1961). *Industrial Dynamics*. MIT Press.
- Chen, F., Drezner, Z., Ryan, J.K., & Simchi-Levi, D. (2000). Quantifying the Bullwhip Effect in a Simple Supply Chain: The Impact of Forecasting, Lead Times, and Information. *Management Science*, 46(3), 436–443. https://doi.org/10.1287/mnsc.46.3.436.12069

**Inventory policy and safety stock:**
- Silver, E.A., Pyke, D.F., & Thomas, D.J. (2017). *Inventory and Production Management in Supply Chains* (4th ed.). CRC Press.
- Zipkin, P.H. (2000). *Foundations of Inventory Management*. McGraw-Hill.

**LLM agents in operations and planning:**
- Park, J.S., O'Brien, J.C., Cai, C.J., Morris, M.R., Liang, P., & Bernstein, M.S. (2023). Generative Agents: Interactive Simulacra of Human Behavior. In *Proceedings of UIST 2023*. https://doi.org/10.1145/3586183.3606763
- Gao, S., et al. (2024). Large Language Models in Supply Chain Management: A Survey. *(add citation when sourced)*
- Boute, R.N., Gijsbrechts, J., van Jaarsveld, W., & Vanvuchelen, N. (2022). Deep Reinforcement Learning for Inventory Optimization: Literature Review. *European Journal of Operational Research*, 298(2), 401–412.

**Structured outputs and constrained generation:**
- Guidance AI (2023). Guidance: A Guidance Language for Controlling Large Language Models. https://github.com/guidance-ai/guidance
- Willard, B.T., & Louf, R. (2023). Efficient Guided Generation for Large Language Models. *arXiv:2307.09702*.

**Intent classification:**
- Liu, B. (2012). Sentiment Analysis and Opinion Mining. *Synthesis Lectures on Human Language Technologies*, 5(1), 1–167.
- Tur, G., & De Mori, R. (Eds.) (2011). *Spoken Language Understanding: Systems for Extracting Semantic Information from Speech*. Wiley.

**Hybrid human-AI and structured decision-making:**
- Amershi, S., et al. (2019). Software Engineering for Machine Learning: A Case Study. In *ICSE-SEIP 2019*, 291–300.
- Cai, C.J., et al. (2019). Human-Centered Tools for Coping with Imperfect Algorithms During Medical Decision-Making. In *CHI 2019*. https://doi.org/10.1145/3290605.3300234

---

## 3. Architecture Design

### 3.1 Three-layer execution per period per tier

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — Classification (LLM)                         │
│  Input:  state variables + optional context             │
│  Output: {"intent": "<CLASS>", "rationale": "..."}      │
│  Task:   choose one of 5 categorical labels              │
└────────────────────┬────────────────────────────────────┘
                     │ intent label (string)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2 — Lookup (deterministic)                       │
│  Input:  intent label                                   │
│  Output: multiplier_t (float)                           │
│  Method: fixed lookup table (no computation)            │
└────────────────────┬────────────────────────────────────┘
                     │ multiplier_t
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3 — Execution (deterministic, OUT-style)         │
│  Input:  multiplier_t, demand_t, inventory_position_t   │
│  Output: order_t                                        │
│  Formula: same as V3b (unchanged)                       │
└─────────────────────────────────────────────────────────┘
```

**Key change from V3b:** Layer 2 is new. In V3b there was no lookup; the float came
directly from the LLM. In V4, the LLM produces a string label; the lookup converts it
to a float; the execution formula is identical. The LLM never produces a number.

### 3.2 Intent classes and multiplier lookup

The five classes are derived from deviation bands around the demand mean (38,446 units
across 24 active periods). Multiplier values below are the **initial design values**;
see calibration note.

| Intent class | Demand deviation band | Multiplier | Seasonal interpretation |
|---|---|---|---|
| `STRONG_INCREASE` | > +10% above mean | **[TBD: V3b]** (initial: 2.5) | FY-end structural peak, Diwali |
| `MODERATE_INCREASE` | +3% to +10% | **[TBD: V3b]** (initial: 1.5) | Navratri/Dasara, minor festive |
| `NEUTRAL` | −5% to +3% | 1.0 (fixed, no calibration needed) | No material seasonal signal |
| `MODERATE_DECREASE` | −5% to −10% | **[TBD: V3b]** (initial: 0.75) | Early and late monsoon |
| `STRONG_DECREASE` | < −10% | **[TBD: V3b]** (initial: 0.5) | Peak monsoon |

> **Calibration procedure `[TBD: V3b]`:** For each event-class (STRONG_INCREASE,
> MODERATE_INCREASE, MODERATE_DECREASE, STRONG_DECREASE), compute the median
> `ss_multiplier` chosen by V3b's best-performing hybrid condition (expected: H-Context
> or H-Stateful) across the corresponding periods. Use those medians as the lookup
> values. If a class has fewer than 4 event periods, use the initial design value.
> Document the calibration in Section 3.2 revision notes.

**Fallback:** If the LLM returns an unrecognised string or invalid JSON, the intent
defaults to `NEUTRAL` (multiplier = 1.0). This is equivalent to V3b's float fallback
of 1.0. Log as `intent_fallback=True`.

**No clamping needed:** Valid intent strings map to pre-validated multipliers. Unlike
V3b, there is no out-of-bounds float to clamp.

### 3.3 Ground-truth intent schedule (for accuracy evaluation)

Derived from the demand series using the deviation bands in Section 3.2:

| Period | Month | Demand | Dev% | Ground-truth intent |
|---|---|---|---|---|
| 1  | Jan 2025 | 37,200 | −3.2% | NEUTRAL |
| 2  | Feb 2025 | 36,200 | −5.8% | MODERATE_DECREASE |
| 3  | Mar 2025 | 43,500 | +13.1% | STRONG_INCREASE |
| 4  | Apr 2025 | 36,200 | −5.8% | MODERATE_DECREASE |
| 5  | May 2025 | 37,200 | −3.2% | NEUTRAL |
| 6  | Jun 2025 | 34,300 | −10.8% | STRONG_DECREASE |
| 7  | Jul 2025 | 33,700 | −12.3% | STRONG_DECREASE |
| 8  | Aug 2025 | 35,100 | −8.7% | MODERATE_DECREASE |
| 9  | Sep 2025 | 37,200 | −3.2% | NEUTRAL |
| 10 | Oct 2025 | 40,400 | +5.1% | MODERATE_INCREASE |
| 11 | Nov 2025 | 41,600 | +8.2% | MODERATE_INCREASE |
| 12 | Dec 2025 | 37,700 | −1.9% | NEUTRAL |
| 13 | Jan 2026 | 39,000 | +1.4% | NEUTRAL |
| 14 | Feb 2026 | 38,000 | −1.2% | NEUTRAL |
| 15 | Mar 2026 | 45,600 | +18.6% | STRONG_INCREASE |
| 16 | Apr 2026 | 38,000 | −1.2% | NEUTRAL |
| 17 | May 2026 | 39,000 | +1.4% | NEUTRAL |
| 18 | Jun 2026 | 36,000 | −6.4% | MODERATE_DECREASE |
| 19 | Jul 2026 | 35,400 | −7.9% | MODERATE_DECREASE |
| 20 | Aug 2026 | 36,800 | −4.3% | NEUTRAL |
| 21 | Sep 2026 | 39,000 | +1.4% | NEUTRAL |
| 22 | Oct 2026 | 42,400 | +10.3% | STRONG_INCREASE |
| 23 | Nov 2026 | 43,600 | +13.4% | STRONG_INCREASE |
| 24 | Dec 2026 | 39,600 | +3.0% | MODERATE_INCREASE |

**Event period distribution across 24 active ordering periods:**
- STRONG_INCREASE: 4 periods (Mar'25, Mar'26, Oct'26, Nov'26) — 16.7%
- MODERATE_INCREASE: 4 periods (Oct'25, Nov'25, Dec'26, + 1 more) — 16.7%
  - Wait: Oct'25, Nov'25, Dec'26 = 3 periods of MODERATE_INCREASE
- NEUTRAL: 11 periods — 45.8%
- MODERATE_DECREASE: 5 periods (Feb'25, Apr'25, Aug'25, Jun'26, Jul'26) — 20.8%
- STRONG_DECREASE: 2 periods (Jun'25, Jul'25) — 8.3%

Non-neutral (event) periods: 4+3+5+2 = 14/24 = 58.3% of the series is seasonally
eventful. This provides adequate signal for intent accuracy evaluation.

**Note on November 2025 (+8.2%):** This is classified MODERATE_INCREASE by deviation
band, but it represents Diwali — the largest annual festive event in the Indian
automotive market. An agent with calendar context may correctly classify this as
STRONG_INCREASE based on cultural knowledge rather than observed demand deviation.
Intent accuracy evaluation must distinguish:
- Deviation-based ground truth (MODERATE_INCREASE)
- Context-informed ground truth (STRONG_INCREASE, defensible given Diwali context)

Both interpretations are logged; accuracy is reported against both. This is a key
test of whether calendar context (H2/H3) adds signal beyond demand observations.

---

## 4. Supply Chain Structure

Identical to V3b — preserved for cross-experiment comparability.

| Tier | Identity | Customer | Upstream |
|---|---|---|---|
| OEM | Tatva Motors | Retail market | Ancillary |
| Ancillary | Lighting manufacturer | OEM | Component |
| Component | LED manufacturer | Ancillary | Production |

- **Lead time:** 1 month deterministic (order placed in t arrives at start of t+1)
- **Visibility:** No cross-tier visibility. Each tier sees only its immediate downstream order.
- **Timing:** Replenishment arrives → fulfilment → ordering → records append (same period)
- **Initial inventory:** S ≈ 43,600 units (mean + 1.65σ) — same as V3b
- **Base safety stock:** ≈ 5,061 units (S − mean_demand) — same as V3b

---

## 5. Experimental Conditions

All conditions share the same OUT-style execution formula (Layer 3). The experimental
variable is Layer 1 (LLM input context) and the output interface (Layer 2, intent
lookup). Baselines run deterministically — no LLM calls.

| Label | Policy | Context given to LLM | Backend |
|---|---|---|---|
| `exp_smoothing` | heuristic | — | — |
| `hybrid_control` | hybrid_control (multiplier=1.0) | — | — |
| `intent_blind_local` | intent | state only | local |
| `intent_blind_azure` | intent | state only | azure |
| `intent_context_local` | intent | state + calendar month + tier persona | local |
| `intent_context_azure` | intent | state + calendar month + tier persona | azure |
| `intent_stateful_local` | intent | state + calendar + 3-period intent/outcome history | local |
| `intent_stateful_azure` | intent | state + calendar + 3-period intent/outcome history | azure |

**Runs:** 20 per LLM condition; 1 per baseline (deterministic).

**V3b conditions included for cross-experiment comparison:**
The canonical V3b production results (H-Blind, H-Context, H-Stateful for both backends)
are used as comparison benchmarks. They are not re-run in V4. The shared demand series
and formula structure make the comparison valid.

### 5.1 Condition descriptions

**IC-Blind (H1_IC):** LLM sees 5 state variables only:
`demand_received, on_hand, backlog, inventory_position, base_ss`.
Tests whether blind intent classification reduces OVAR relative to baselines.
If IC-Blind beats exp_smoothing, it confirms the architectural change (intent
interface) drives performance even without seasonal intelligence.

**IC-Context (H2_IC):** Adds calendar month (e.g., "November 2025") and tier persona
(company name, product description). This gives the LLM access to cultural/seasonal
knowledge it was trained on.

**IC-Stateful (H3_IC):** Context + last 3 periods of
`(demand, order_placed, intent_chosen, backlog, stockout_flag)`.
The intent history (not a float history) enables self-correction:
*"I chose MODERATE_INCREASE last period but still got a stockout — I should
choose STRONG_INCREASE."*
This is cleaner than V3b's float history — a model can reason about
"I chose MODERATE_INCREASE three times in a row before Diwali" more reliably
than "I chose 1.43, 1.51, 1.38."

---

## 6. Demand Data

Identical to V3b — same CSV, same SHA-256 checksum, same derivation of S and base_SS.

| Parameter | Value |
|---|---|
| File | `../data/tatva_monthly_dispatches_25m.csv` |
| Horizon | 25 months: Jan 2025 – Jan 2027 |
| Active ordering periods | 24 (periods 1–24) |
| Close-out period | 1 (period 25 — fulfilment only) |
| Mean demand (24 active periods) | 38,446 units/month |
| Std (ddof=1) | ~3,067 units |
| Initial inventory (S) | ~43,600 units (mean + 1.65σ) |
| Base safety stock | ~5,061 units (S − mean_demand) |

The same series is shared across all experiments from V3b onward. This is
deliberate — it allows direct OVAR comparisons between V3b (float interface)
and V4 (intent interface) on identical inputs.

---

## 7. Models

| Label | Model | Backend | Temperature |
|---|---|---|---|
| local | nemotron-3-super:120b | Ollama (local GPU) | default |
| azure | gpt-4.1-mini | Azure OpenAI GlobalStandard | default |

Temperature rationale: same as V3b — both are reasoning models. Default temperature
is used; stochasticity across 20 runs is preserved via model sampling defaults.

The constrained output space (one of 5 string labels vs. an unbounded float) should
substantially reduce variance in outputs and compliance failures compared to V3b.
This is an explicit prediction to be validated.

---

## 8. Metrics

### 8.1 Primary operational metrics (identical to V3b)

**OVAR (Order Variance Ratio):**
```
OVAR_tier = Var(order_placed) / Var(demand_received)
            sample variance (ddof=1), 24 active ordering periods

Chain OVAR = arithmetic mean across 3 tiers
```

**Stockout count:**
Periods where on_hand < (demand + backlog), summed across all 25 periods × 3 tiers
(max = 75). Always reported alongside OVAR.

**Mean on-hand inventory:**
Mean `on_hand_before_order` per run × tier, averaged over 24 active periods, then
averaged to chain level. Prevents low-OVAR-via-starvation from appearing as a win.

### 8.2 New primary metric: Intent accuracy

```
intent_accuracy = (periods where chosen intent matches ground-truth direction)
                  / (total non-neutral event periods)
```

- Evaluated against the deviation-based ground truth (Section 3.3 table)
- Evaluated separately against the context-informed ground truth for November months
- Reported per condition per run; summarised as mean ± std across 20 runs

**Direction-only version (partial credit):**
```
intent_direction_accuracy = (periods where chosen intent direction is correct,
                             regardless of intensity)
                            / (non-neutral event periods)
```
e.g., choosing MODERATE_INCREASE when ground truth is STRONG_INCREASE counts as
correct for direction. This separates "right direction, wrong intensity" from
"wrong direction."

### 8.3 New primary metric: Intent compliance rate

```
intent_compliance_rate = (periods where LLM output was a valid intent class
                          AND not a fallback)
                         / total active hybrid periods
```

V3b target was ≥ 0.95. V4 target is ≥ 0.99 (near-perfect, since the task is
a 5-class classification not a float). A rate below 0.99 indicates systematic
prompt issues.

### 8.4 New diagnostic metric: Intent distribution

Per condition, per run:
```python
intent_counts = Counter(intents over 24 periods)
intent_entropy = -sum(p * log2(p) for p in intent_counts.values() if p > 0)
                 (max entropy = log2(5) ≈ 2.32 for uniform distribution)
```

**Entropy interpretation:**
- High entropy → model is differentiating actively across the five classes
- Low entropy → model collapses to one or two labels (poor calibration)
- Expected: IC-Context should have higher entropy than IC-Blind (context adds discrimination)

### 8.5 Cross-experiment comparison metrics `[TBD: V3b]`

Once V3b canonical results are available:

```
ΔOVAR(V4 vs V3b) = Chain_OVAR_V4 - Chain_OVAR_V3b_matched_condition
```

Matched condition = same context level (blind/context/stateful) and same backend.

```
Δcompliance(V4 vs V3b) = intent_compliance_V4 - multiplier_compliance_V3b
```

Expected direction: Δcompliance > 0 (V4 better); ΔOVAR ≈ 0 or < 0 (V4 comparable or better).

### 8.6 MPRD threshold

Minimum Practically Relevant Difference: |ΔOVAR| ≥ 0.5 for a performance claim.
Inherited from V3b. Smaller differences are within noise for a 20-run sample.

---

## 9. Hypotheses

| H | Comparison | Threshold | Decision rule |
|---|---|---|---|
| **H_IC1 (Primary)** | Best V4 condition chain OVAR vs exp_smoothing OVAR AND stockouts | OVAR ≤ exp_smoothing AND stockouts ≤ exp_smoothing (both within V4) | Pass if any V4 condition meets both |
| **H_IC1x (Cross-exp)** | Best V4 condition OVAR vs best V3b condition OVAR | ΔOVAR within MPRD (≤ 0.5) OR V4 better | V4 is competitive with or better than V3b float approach `[TBD: V3b threshold]` |
| **H_IC2** | Intent compliance rate | ≥ 0.99 across all V4 conditions | Intent is a more reliable output interface than float |
| **H_IC3** | IC-Context intent accuracy (direction) | ≥ 0.60 across event periods | Calendar context enables directionally correct classification |
| **H_IC4** | IC-Stateful intent accuracy vs IC-Context intent accuracy | Δaccuracy ≥ 0.10 | History enables self-correction of classification errors |
| **H_IC5** | IC-Context intent entropy vs IC-Blind intent entropy | IC-Context entropy > IC-Blind entropy | Context increases classification discrimination |

> **Note on H_IC1x:** The threshold `[TBD: V3b]` will be set once V3b canonical OVAR
> is available. The claim is that V4 is *at least as good* as V3b at the primary OVAR
> task, while being strictly better on compliance. If V4 achieves materially better
> OVAR (ΔOVAR ≥ 0.5), that is a bonus finding; the primary claim is competitive
> equivalence.

---

## 10. Code Architecture

V4 shares the entire simulation, metrics, and runner infrastructure from V3b.
The only new code is:

```
agent_interface.py
  └── get_intent_class()            ← NEW (parallel to get_ss_multiplier())
        - builds intent prompt
        - calls backend
        - validates response against 5-class enum
        - fallback to NEUTRAL on parse failure

simulation.py
  └── policy_intent_hybrid()        ← NEW (parallel to policy_smoothed_out_with_ss())
        - calls get_intent_class()
        - applies INTENT_MULTIPLIER_MAP lookup
        - executes OUT-style formula

run_experiment.py
  └── EXPERIMENTS["H1_IC"] / H2_IC / H3_IC    ← NEW entries
        - "policy": "intent"
        - same backend/condition structure as V3b H1/H2/H3

metrics.py
  └── compute_intent_accuracy()     ← NEW
  └── compute_intent_entropy()      ← NEW
  └── compute_intent_distribution() ← NEW
```

The `INTENT_MULTIPLIER_MAP` dict is defined in `simulation.py` (or a shared
`constants.py`) and is the single source of truth for the lookup table.

**No changes to:** backends, resilience, output schema (records.parquet), verify_outputs.py.
All new metrics are additive fields in `summary.json`.

---

## 11. Prompt Design

### 11.1 Shared structure (all conditions)

The system prompt introduces the agent, the formula, and the five intent classes
with explicit mapping to multipliers.

```
You are the inventory manager for {tier_name} ({tier_company}).

You are operating within a hybrid ordering system. Your role is to
classify the current period's buffer direction. A deterministic formula
will convert your classification to a precise order quantity.

Classification choices (choose exactly one):
  STRONG_INCREASE   → safety stock ×{SI_multiplier:.2f}   (major demand elevation)
  MODERATE_INCREASE → safety stock ×{MI_multiplier:.2f}   (mild demand elevation)
  NEUTRAL           → safety stock ×1.00  (no seasonal signal)
  MODERATE_DECREASE → safety stock ×{MD_multiplier:.2f}   (mild demand dip)
  STRONG_DECREASE   → safety stock ×{SD_multiplier:.2f}   (major demand dip)

Base safety stock = {base_ss:,} units.
```

Showing the multiplier values in the prompt makes the task concrete: the model
knows the downstream consequence of each choice. This mirrors V3b's design
principle of showing the formula to the LLM.

### 11.2 Context additions (IC-Context and IC-Stateful)

IC-Context appends:
```
Current period: {calendar_month} {year}
```

IC-Stateful additionally appends:
```
Last 3 periods of history:
  {t-3}: demand={d}, order={o}, intent={intent}, backlog={b}{stockout_flag}
  {t-2}: demand={d}, order={o}, intent={intent}, backlog={b}{stockout_flag}
  {t-1}: demand={d}, order={o}, intent={intent}, backlog={b}{stockout_flag}

[STOCKOUT] = on_hand was insufficient to meet demand that period.
```

The history shows `intent` (the label chosen), not the float. This is intentional:
reasoning about "I chose MODERATE_INCREASE for Oct and got a stockout, I should
choose STRONG_INCREASE for Nov" is more natural than reasoning about floats.

### 11.3 Output format (stricter than V3b)

```json
{"intent": "STRONG_INCREASE", "rationale": "..."}
```

The intent field must be one of exactly five strings (case-sensitive). Any other
value triggers the fallback. Parse failure rate is expected to be near zero because:
1. The field is a simple string enum, not a float
2. json_repair handles minor formatting issues
3. The 3-attempt loop handles occasional refusals

### 11.4 Prompt changes vs V3b

| Aspect | V3b prompt | V4 prompt |
|---|---|---|
| Output field | `safety_stock_multiplier: float` | `intent: enum string` |
| LLM task | Generate calibrated float in [0.5, 3.0] | Classify into one of 5 labels |
| Bounds shown | Yes — `[0.5, 3.0]` range in prompt | No bounds needed — enum is self-bounding |
| Multiplier shown | Via formula explanation | Via lookup table in system prompt |
| History field | `ss_multiplier` float values | `intent` string labels |

---

## 12. Execution Plan

> **Prerequisite:** Complete V3b canonical runs and fill in all `[TBD: V3b]` items
> before running production for V4.

### Phase 0: V3b refinement (blocking)

1. Retrieve V3b production results
2. Run `verify_outputs.py` and confirm n_runs=20 for all LLM conditions
3. Run `generate_figures.py` to produce V3b final figures
4. Extract the following from V3b summary.json:
   - Chain OVAR per condition (for H_IC1x threshold and H_IC1 exp_smoothing baseline)
   - Chain stockout count per condition
   - `multiplier_stats` histograms for each hybrid condition (for calibrating intent lookup)
   - `llm_compliance_rate` per condition (for the compliance motivation claim)
5. Fill in Section 3.2, Section 8.5, and Section 9 `[TBD]` items

### Phase 1: Code implementation

```bash
cd experiments/Agentic_Bullwhip_Effect_V4_IntentClassifier/code/
```

Priority order:
1. `agent_interface.py` — add `get_intent_class()` alongside `get_ss_multiplier()`
2. `simulation.py` — add `policy_intent_hybrid()` and `INTENT_MULTIPLIER_MAP`
3. `metrics.py` — add `compute_intent_accuracy()`, `compute_intent_entropy()`, `compute_intent_distribution()`
4. `run_experiment.py` — add `EXPERIMENTS["H1_IC"]`, `H2_IC`, `H3_IC` entries
5. `verify_outputs.py` — add intent field checks

### Phase 2: Dry run validation (zero API cost)

```bash
DRY_RUN=1 BACKEND=local /usr/bin/python3 run_experiment.py \
    --experiments baselines H1_IC --runs 2 --env .env.local
/usr/bin/python3 verify_outputs.py --results-dir ../results/
```

Expected: all records have `intent` field; `intent_compliance_rate=1.0` (dry_run backend returns NEUTRAL always).

### Phase 3: Smoke test (2 runs, real LLM)

```bash
# Local
BACKEND=local /usr/bin/python3 run_experiment.py \
    --experiments H1_IC --runs 2 --env .env.local

# Azure
BACKEND=azure /usr/bin/python3 run_experiment.py \
    --experiments H1_IC --runs 2 --env .env.azure
```

Verify: `intent` field varies across periods, `compliance_rate ≥ 0.99`, rationale non-blank.

### Phase 4: Production runs (in tmux with nohup)

```bash
# Local (nemotron-3-super:120b)
tmux new-session -s prod_v4_local
BACKEND=local nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1_IC H2_IC H3_IC --runs 20 --env .env.local \
    > ../logs/v4_local_prod.log 2>&1

# Azure (gpt-4.1-mini)
tmux new-session -s prod_v4_azure
BACKEND=azure nohup /usr/bin/python3 run_experiment.py \
    --experiments baselines H1_IC H2_IC H3_IC --runs 20 --env .env.azure \
    > ../logs/v4_azure_prod.log 2>&1
```

**Local run cool-down (built-in):**
Local runs take ~51h total (3 conditions × 20 runs × ~51 min/run). To prevent GPU
thermal throttling on multi-day continuous runs, the runner inserts a 30-minute pause
between experiment groups whenever total wall time exceeds 8 hours.

Implementation in `run_experiment.py` (code phase):
```python
COOLDOWN_THRESHOLD_H = 8.0      # hours — only triggers on long local runs
COOLDOWN_DURATION_S  = 1800     # 30 minutes

# In main(), before the experiment loop:
run_start = time.time()

# After each experiment saves (before the next group starts):
if exp_name != args.experiments[-1]:
    elapsed_h = (time.time() - run_start) / 3600
    if elapsed_h > COOLDOWN_THRESHOLD_H:
        logger.info(
            "Wall time %.1fh exceeds %.0fh threshold — cooling down %.0f min.",
            elapsed_h, COOLDOWN_THRESHOLD_H, COOLDOWN_DURATION_S / 60,
        )
        time.sleep(COOLDOWN_DURATION_S)
        logger.info("Cool-down complete. Resuming.")
```

Azure runs (~5h total) never exceed the 8h threshold — the cool-down is a no-op there.

### Phase 5: Analysis

```bash
/usr/bin/python3 generate_figures.py --results-dir ../results/
```

Key figures to add (beyond V3b's figure set):
- Intent distribution heatmap (period × intent class, per condition)
- Intent accuracy bar chart (by condition, with direction-only and full-match variants)
- Intent entropy per condition (IC-Blind vs IC-Context vs IC-Stateful)
- V4 vs V3b OVAR scatter (paired by condition type and backend)

---

## 13. Limitations

1. **Same demand series:** V4 uses the same 25-month synthetic series as V3b. Findings
   are specific to this demand profile (Indian automotive, two seasonal cycles). 
   Generalizability to other markets or demand structures is not established.

2. **Single supply chain topology:** The three-tier serial cascade with unit lead time
   is a simplified structure. Real supply chains have variable lead times, lateral
   flows, and multi-echelon complexity.

3. **Synthetic calibration:** The intent → multiplier lookup values are either
   domain-logic-driven (initial design) or calibrated from V3b float medians. Neither
   is guaranteed to be globally optimal for the OUT-style formula.

4. **Model-specific results:** Findings for nemotron-3-super:120b and gpt-4.1-mini
   may not generalise to other LLMs. The intent classification task may be easier or
   harder for models with different instruction-following capabilities.

5. **No adversarial conditions:** The experiment tests seasonal variation but not
   demand shocks, supply disruptions, or structural mean shifts. Robustness to
   out-of-distribution events is not evaluated.

6. **20-run sample:** n=20 provides adequate variance estimates for OVAR comparisons
   at the MPRD threshold of 0.5. Smaller effects may be underpowered.

---

## 14. Planned Outputs

| Artifact | Content | Location |
|---|---|---|
| `records.parquet` | Per-period, per-tier, per-run records including `intent`, `intent_fallback`, `rationale` | `results/{exp}/{timestamp}/` |
| `summary.json` | Per-condition: OVAR, stockouts, mean_on_hand, intent_accuracy, intent_entropy, compliance_rate | `results/{exp}/{timestamp}/` |
| `provenance.json` | Demand checksum, model names, lookup table, dry_run flag, backend | `results/{exp}/{timestamp}/` |
| `figures/` | OVAR scatter, intent heatmap, entropy chart, V4 vs V3b comparison | `figures/` |
| `RESULTS_V4.md` | Post-run narrative: hypothesis verdicts, cross-experiment comparison | *(to be written)* |

---

## 15. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-04-15 | Siddharth Srinivasan | Initial draft |
| 0.2 | `[TBD: V3b]` | — | Fill in Section 3.2 calibration, Section 8.5 thresholds, Section 9 H_IC1x |
| 1.0 | — | — | Code-complete, pre-run |
